"""Core data models for HermezOS."""

import hashlib
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Union

from pydantic import BaseModel, Field, field_validator, model_validator


def to_canonical_json(obj: Any) -> str:
    """Convert object to canonical JSON string with sorted keys and
    consistent formatting.

    Args:
        obj: Object to serialize (typically a Pydantic model)

    Returns:
        Canonical JSON string with sorted keys, UTF-8 encoding, and
        consistent formatting
    """

    def sort_dict_recursive(d: dict[str, Any]) -> dict[str, Any]:
        """Recursively sort dictionary keys."""
        return {
            k: sort_dict_recursive(v) if isinstance(v, dict) else v
            for k, v in sorted(d.items())
        }

    if hasattr(obj, "model_dump"):
        # Pydantic model
        data = obj.model_dump(exclude_unset=True)
    else:
        # Regular dict or other object
        data = obj if isinstance(obj, dict) else obj.__dict__

    sorted_data = sort_dict_recursive(data)
    return json.dumps(
        sorted_data, separators=(",", ":"), sort_keys=True, ensure_ascii=False
    )


class Status(str, Enum):
    """Rule card status enumeration."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class Severity(str, Enum):
    """Rule card severity enumeration."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ActionType(str, Enum):
    """Action type enumeration."""

    MANUAL = "manual"
    SCRIPT = "script"
    DOC = "doc"


class TriggerType(str, Enum):
    """Trigger type enumeration."""

    PATH_CONTAINS = "path_contains"
    FILE_EXISTS = "file_exists"


class DetectorType(str, Enum):
    """Detector type enumeration."""

    REGEX = "regex"
    FILE_EXISTS = "file_exists"
    PATH_CONTAINS = "path_contains"


class Reference(BaseModel):
    """Reference model for documentation links."""

    doc_url: str = Field(..., description="URL to documentation")
    note: str | None = Field(None, description="Optional note about the reference")


class Provenance(BaseModel):
    """Provenance information for rule cards."""

    author: str = Field(..., description="Author of the rule card")
    created: str = Field(..., description="Creation timestamp in ISO format")
    last_updated: str = Field(..., description="Last update timestamp in ISO format")


class Scope(BaseModel):
    """Scope definition for rule application."""

    repo_patterns: list[str] = Field(
        default_factory=list, description="Repository pattern matches"
    )
    file_globs: list[str] = Field(
        default_factory=list, description="File glob patterns"
    )
    languages: list[str] = Field(
        default_factory=list, description="Programming languages"
    )


class Trigger(BaseModel):
    """Trigger condition for rule activation."""

    type: TriggerType = Field(..., description="Type of trigger")
    value: str = Field(..., description="Trigger value")


class Detector(BaseModel):
    """Detector for rule conditions."""

    type: DetectorType = Field(..., description="Type of detector")
    file_glob: str | None = Field(None, description="File glob pattern for detection")
    pattern: str | None = Field(None, description="Regex pattern for detection")
    value: str | None = Field(None, description="Value for detection")


class Action(BaseModel):
    """Action to take when rule is triggered."""

    type: ActionType = Field(..., description="Type of action")
    fix_command: str | None = Field(None, description="Command to fix the issue")
    steps: list[str] | None = Field(None, description="Manual steps to resolve")


class RuleCard(BaseModel):
    """Core rule card model."""

    schema_version: int = Field(..., description="Schema version")
    id: str = Field(..., description="Unique rule identifier (RULE-<domain>-<slug>)")
    name: str = Field(..., description="Human-readable rule name")
    version: int = Field(..., description="Rule version number")
    status: Status = Field(..., description="Rule status")
    severity: Severity = Field(..., description="Rule severity level")
    domain: str = Field(..., description="Rule domain/category")
    intent_tags: list[str] = Field(
        default_factory=list, description="Intent classification tags"
    )
    scope: Scope = Field(default_factory=Scope, description="Application scope")
    triggers: list[Trigger] = Field(
        default_factory=list, description="Trigger conditions"
    )
    detectors: list[Detector] = Field(
        default_factory=list, description="Detection conditions"
    )
    action: Action = Field(..., description="Action to take")
    hint: str | None = Field(None, description="Helpful hint for the rule")
    retriable: bool | None = Field(
        None, description="Whether the action can be retried"
    )
    references: list[Reference] = Field(
        default_factory=list, description="Documentation references"
    )
    provenance: Provenance = Field(..., description="Provenance information")

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate rule ID format."""
        if not v.startswith("RULE-"):
            raise ValueError("Rule ID must start with 'RULE-'")
        parts = v.split("-")
        if len(parts) < 3:
            raise ValueError("Rule ID must have format 'RULE-<domain>-<slug>'")
        return v

    @field_validator("retriable", mode="before")
    @classmethod
    def set_default_retriable(cls, v: bool | None, info: Any) -> bool:
        """Set default retriable based on action type."""
        if v is None:
            # Get the action from the model
            action = info.data.get("action")
            if action and isinstance(action, dict):
                action_type = action.get("type")
                return bool(action_type == "script")
            return False
        return bool(v)

    def normalize(self) -> "RuleCard":
        """Normalize rule card by applying derived defaults and validations.

        Returns:
            Self with normalized values
        """
        # Set default retriable based on action type
        if self.retriable is None:
            self.retriable = self.action.type == ActionType.SCRIPT

        # Set default hint from action steps if not provided
        if not self.hint and self.action.steps:
            self.hint = self.action.steps[0][:100]  # First 100 chars of first step

        # Ensure references list exists
        if not self.references:
            self.references = []

        return self

    def compute_fingerprint(self) -> str:
        """Compute SHA256 fingerprint of the rule card using canonical JSON."""
        # Normalize the rule card first
        normalized = self.normalize()

        # Create canonical JSON representation
        canonical_json = to_canonical_json(normalized)

        # Compute SHA256 hash
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class PackRequest(BaseModel):
    """Request model for packing operations."""

    path: str = Field(..., description="Path to analyze")
    intent_tags: list[str] | None = Field(None, description="Filter by intent tags")
    languages: list[str] | None = Field(
        None, description="Filter by programming languages"
    )
    limit: int | None = Field(None, description="Maximum number of rules to return")
    include_deprecated: bool = Field(False, description="Include deprecated rules")
    file_globs: list[str] | None = Field(
        None, description="File glob patterns to constrain file walker"
    )


class RuleMatch(BaseModel):
    """Matched rule with context."""

    rule: RuleCard = Field(..., description="The matched rule card")
    fingerprint: str = Field(..., description="Rule fingerprint")
    triggered_by: list[str] = Field(
        default_factory=list, description="What triggered the match"
    )
    detected_in: list[str] = Field(
        default_factory=list, description="Files where detection occurred"
    )


class PackBundle(BaseModel):
    """Bundle of packed rules with metadata."""

    pack_request: PackRequest = Field(..., description="Original pack request")
    rules: list[RuleMatch] = Field(default_factory=list, description="Matched rules")
    pack_fingerprint: str = Field(default="", description="Bundle fingerprint")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        description="Creation timestamp in RFC3339 format",
    )
    total_rules: int = Field(
        default_factory=lambda: 0, description="Total number of rules"
    )
    hermez_version: str = Field(default="1.0.0", description="HermezOS version")
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Applied filters from pack request"
    )
    cards: list[dict[str, Any]] = Field(
        default_factory=list, description="Normalized rule cards with fingerprints"
    )
    actions_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of actions by type, severity, and domain",
    )

    @model_validator(mode="after")
    def compute_fingerprint(self) -> "PackBundle":
        """Compute pack fingerprint from rule fingerprints using canonical JSON."""
        # Sort rules by fingerprint for deterministic ordering
        sorted_rules = (
            sorted(self.rules, key=lambda r: r.fingerprint) if self.rules else []
        )
        rule_fps = [r.fingerprint for r in sorted_rules]

        # Include pack request in fingerprint computation (always generate fingerprint)
        pack_data = {
            "request": self.pack_request.model_dump(),
            "rule_fingerprints": rule_fps,
            "created_at": self.created_at,
        }

        canonical_json = to_canonical_json(pack_data)
        self.pack_fingerprint = hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()

        self.total_rules = len(self.rules)
        return self


def export_json_schemas(output_dir: Path) -> None:
    """Export JSON schemas for all models to the specified directory.

    Args:
        output_dir: Directory to export schemas to
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    schemas = {
        "RuleCard": RuleCard.model_json_schema(),
        "PackRequest": PackRequest.model_json_schema(),
        "PackBundle": PackBundle.model_json_schema(),
        "RuleMatch": RuleMatch.model_json_schema(),
    }

    for name, schema in schemas.items():
        schema_file = output_dir / f"{name.lower()}.json"
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, sort_keys=True)
        print(f"Exported {name} schema to {schema_file}")
