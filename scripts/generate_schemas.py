#!/usr/bin/env python3
"""Generate JSON schemas for HermezOS models."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from hermezos.models import export_json_schemas
    export_json_schemas(Path("docs/schemas"))
except ImportError as e:
    print(f"Could not import models: {e}")
    print("Creating basic schemas manually...")

    # Create basic schemas manually
    schemas_dir = Path("docs/schemas")
    schemas_dir.mkdir(parents=True, exist_ok=True)

    # RuleCard schema
    rulecard_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "RuleCard",
        "type": "object",
        "properties": {
            "schema_version": {"type": "integer"},
            "id": {"type": "string", "pattern": "^RULE-"},
            "name": {"type": "string"},
            "version": {"type": "integer"},
            "status": {"enum": ["draft", "active", "deprecated"]},
            "severity": {"enum": ["info", "warning", "error"]},
            "domain": {"type": "string"},
            "intent_tags": {"type": "array", "items": {"type": "string"}},
            "scope": {
                "type": "object",
                "properties": {
                    "repo_patterns": {"type": "array", "items": {"type": "string"}},
                    "file_globs": {"type": "array", "items": {"type": "string"}},
                    "languages": {"type": "array", "items": {"type": "string"}}
                }
            },
            "triggers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"enum": ["path_contains", "file_exists"]},
                        "value": {"type": "string"}
                    },
                    "required": ["type", "value"]
                }
            },
            "detectors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"enum": ["regex", "file_exists", "path_contains"]},
                        "file_glob": {"type": "string"},
                        "pattern": {"type": "string"},
                        "value": {"type": "string"}
                    },
                    "required": ["type"]
                }
            },
            "action": {
                "type": "object",
                "properties": {
                    "type": {"enum": ["manual", "script", "doc"]},
                    "fix_command": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["type"]
            },
            "hint": {"type": "string"},
            "retriable": {"type": "boolean"},
            "references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "doc_url": {"type": "string"},
                        "note": {"type": "string"}
                    },
                    "required": ["doc_url"]
                }
            },
            "provenance": {
                "type": "object",
                "properties": {
                    "author": {"type": "string"},
                    "created": {"type": "string"},
                    "last_updated": {"type": "string"}
                },
                "required": ["author", "created", "last_updated"]
            }
        },
        "required": ["schema_version", "id", "name", "version", "status", "severity", "domain", "action", "provenance"]
    }

    # PackRequest schema
    packrequest_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PackRequest",
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "intent_tags": {"type": "array", "items": {"type": "string"}},
            "languages": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer"},
            "include_deprecated": {"type": "boolean"}
        },
        "required": ["path"]
    }

    # PackBundle schema
    packbundle_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PackBundle",
        "type": "object",
        "properties": {
            "pack_request": {"$ref": "#/$defs/PackRequest"},
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule": {"$ref": "#/$defs/RuleCard"},
                        "fingerprint": {"type": "string"},
                        "triggered_by": {"type": "array", "items": {"type": "string"}},
                        "detected_in": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["rule", "fingerprint"]
                }
            },
            "pack_fingerprint": {"type": "string"},
            "created_at": {"type": "string"},
            "total_rules": {"type": "integer"}
        },
        "required": ["pack_request", "rules", "pack_fingerprint", "created_at", "total_rules"],
        "$defs": {
            "RuleCard": rulecard_schema,
            "PackRequest": packrequest_schema
        }
    }

    # Write schemas
    with open(schemas_dir / "rulecard.json", 'w') as f:
        json.dump(rulecard_schema, f, indent=2)
    print(f"Created rulecard.json")

    with open(schemas_dir / "packrequest.json", 'w') as f:
        json.dump(packrequest_schema, f, indent=2)
    print(f"Created packrequest.json")

    with open(schemas_dir / "packbundle.json", 'w') as f:
        json.dump(packbundle_schema, f, indent=2)
    print(f"Created packbundle.json")

    # RuleMatch schema
    rulematch_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "RuleMatch",
        "type": "object",
        "properties": {
            "rule": {"$ref": "rulecard.json"},
            "fingerprint": {"type": "string"},
            "triggered_by": {"type": "array", "items": {"type": "string"}},
            "detected_in": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["rule", "fingerprint"]
    }

    with open(schemas_dir / "rulematch.json", 'w') as f:
        json.dump(rulematch_schema, f, indent=2)
    print(f"Created rulematch.json")

if __name__ == "__main__":
    print("Schema generation complete!")