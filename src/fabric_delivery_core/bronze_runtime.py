"""Fixed notebook worker source; platform libraries are imported only at execution."""

import json
from uuid import UUID


def _quoted(identifier: str) -> str:
    return "[" + identifier.replace("]", "]]") + "]"


def run_bronze(spark, configuration: dict, batch_id: str) -> None:
    """Run only a reviewed, separately load-authorized create-only snapshot.

    The private dispatcher must authenticate the stage, grant, artifact, execution
    identity, target baseline and this batch parameter before invoking the job.
    No Python argument here is an authorization credential.
    """
    if not isinstance(batch_id, str):
        raise ValueError("invalid_batch_id")
    try:
        batch = UUID(batch_id)
    except ValueError:
        raise ValueError("invalid_batch_id") from None
    if str(batch) != batch_id or batch.version != 4:
        raise ValueError("invalid_batch_id")

    for table in configuration["tables"]:
        if spark.catalog.tableExists("bronze." + table["target_table"]):
            raise RuntimeError("target_already_exists")

    import com.microsoft.sqlserver.jdbc.spark  # Registers DataFrame.mssql.
    from azure.identity import ClientSecretCredential
    import notebookutils
    from pyspark import StorageLevel
    from pyspark.sql import functions as F

    identity = configuration["identity"]
    secret = notebookutils.credentials.getSecret(identity["vault_url"], identity["secret_name"])
    with ClientSecretCredential(
        tenant_id=identity["tenant_id"], client_id=identity["client_id"], client_secret=secret,
    ) as credential:
        del secret
        source = configuration["source"]
        url = (
            "jdbc:sqlserver://" + source["server"] + ":1433;database=" + source["database"]
            + ";encrypt=true;trustServerCertificate=false;"
        )
        for table_index, table in enumerate(configuration["tables"]):
            columns = table["columns"]
            query = (
                "SELECT TOP (" + str(table["max_rows"] + 1) + ") "
                + ", ".join(_quoted(column["name"]) for column in columns)
                + " FROM " + _quoted(table["source_schema"]) + "." + _quoted(table["source_table"])
            )
            frame = (
                spark.read.option("url", url)
                .option("accesstoken", credential.get_token("https://database.windows.net/.default").token)
                .option("query", query)
                .option("queryTimeout", str(configuration["query_timeout_seconds"]))
                .mssql()
                .persist(StorageLevel.DISK_ONLY)
            )
            try:
                actual = [(field.name, field.dataType.simpleString()) for field in frame.schema.fields]
                expected = [(column["name"], column["spark_type"]) for column in columns]
                if actual != expected:
                    raise RuntimeError("source_schema_mismatch")
                if frame.count() > table["max_rows"]:
                    raise RuntimeError("source_row_limit_exceeded")
                for column in columns:
                    if not column["nullable"] and frame.filter(
                        F.col("`" + column["name"] + "`").isNull()
                    ).limit(1).count():
                        raise RuntimeError("source_nullability_failed")
                output = (
                    frame.withColumn("_fdos_batch_id", F.lit(batch_id))
                    .withColumn("_fdos_ingested_at", F.current_timestamp())
                    .withColumn(
                        "_fdos_source_table",
                        F.lit(_quoted(table["source_schema"]) + "." + _quoted(table["source_table"])),
                    )
                )
                print(json.dumps({"event": "bronze_write_started", "table_index": table_index}), flush=True)
                spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
                output.write.format("delta").mode("errorifexists").saveAsTable(
                    "bronze." + table["target_table"]
                )
                print(json.dumps({"event": "bronze_table_created", "table_index": table_index}), flush=True)
            finally:
                frame.unpersist()
