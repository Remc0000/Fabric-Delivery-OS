"""Private-state authorization primitives; no identity verification or execution."""

from .authorization import (
    ApprovalBinding,
    AuthorizationDenied,
    ExecutionManifest,
    ExecutionReceipt,
    SQLiteAuthorizationStore,
    sha256_digest,
)
from .dispatch import DispatchClaim, DispatchDenied, DispatchProfile, SQLiteDispatchStore
from .request_registry import (
    IssueRevision, RegistryDenied, RegistryRequest, RegistrySnapshot,
    RequestPolicy, RequestRule, SQLiteRequestRegistry,
)

__all__ = [
    "ApprovalBinding",
    "AuthorizationDenied",
    "ExecutionManifest",
    "ExecutionReceipt",
    "SQLiteAuthorizationStore",
    "sha256_digest",
    "DispatchClaim",
    "DispatchDenied",
    "DispatchProfile",
    "SQLiteDispatchStore",
    "IssueRevision",
    "RegistryDenied",
    "RegistryRequest",
    "RegistrySnapshot",
    "RequestPolicy",
    "RequestRule",
    "SQLiteRequestRegistry",
]
