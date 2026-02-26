from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Any

from pydantic import BaseModel, Field


class PiiClass(str, Enum):
    NONE = "none"
    PRIVATE = "private"
    SENSITIVE = "sensitive"


class Lineage(BaseModel):
    source_systems: list[str]
    transformation_summary: str
    downstream_consumers: list[str]


class UsagePolicy(BaseModel):
    allowed_use_cases: list[str]
    prohibited_use_cases: list[str]
    retention_days: int = Field(gt=0)


# --- Agent-ready additions ---

class Invocation(BaseModel):
    type: Literal["mcp", "rest", "sql"]
    # MCP fields
    server_url: Optional[str] = None
    tool_name: Optional[str] = None
    # REST fields
    method: Optional[Literal["GET", "POST", "PUT", "DELETE"]] = None
    url: Optional[str] = None
    # SQL fields (if you want)
    warehouse: Optional[str] = None
    query_template: Optional[str] = None


class Capability(BaseModel):
    name: str
    description: str
    invocation: Invocation
    # JSON Schema-ish (kept as dict for simplicity)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    # lightweight runtime hints
    policy_hints: dict[str, Any] = Field(default_factory=dict)


class DataProduct(BaseModel):
    domain: str
    name: str  # add explicit name to key it in the registry
    client: str
    version: str
    owner_team: str
    description: str
    pii: PiiClass
    lineage: Lineage
    usage_policy: UsagePolicy
    capabilities: list[Capability] = Field(default_factory=list)
    updated_at: datetime


