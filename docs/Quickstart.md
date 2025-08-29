# Quickstart

HermezOS is a local-first, deterministic registry of rules your AI agents (and humans) can use to **pack** precise context for a task.

## Install
```bash
# Recommended:
pipx install hermezos
# or:
python -m pip install --upgrade hermezos
````

## Initialize a registry

```bash
hermez init
```

This creates a `registry/` with a minimal structure.

## (Optional) Add a tiny demo rule

Create `registry/examples/RULE-demo-readme-present.yml`:

```yaml
schema_version: 1
id: RULE-demo-readme-present
name: Demo: Repo has a README
version: 1
status: active
severity: info
domain: project
intent_tags: [demo, onboarding]
scope:
  file_globs: ["README.md"]
  languages: []
triggers:
  - type: file_exists
    value: "README.md"
detectors:
  - type: regex
    pattern: "(?i)hermezos|hermez"
action:
  type: manual
  steps:
    - "This is a demo rule that proves packing works locally."
hint: "Packing works — now try real rules for your codebase."
references:
  - doc_url: "./Quickstart.md"
provenance:
  author: "Archit Joshi"
  created: "2025-08-29T00:00:00Z"
```

## Validate your rules

```bash
hermez validate
```

## Pack (produce a deterministic bundle)

```bash
hermez pack --path . --intent demo --limit 10 --json -
```

Example (truncated) JSON output:

```json
{
  "pack_version": 1,
  "fingerprint": "sha256-…",
  "generated_at": "2025-08-29T00:00:00Z",
  "items": [
    {
      "id": "RULE-demo-readme-present",
      "severity": "info",
      "status": "active",
      "fingerprint": "sha256-…",
      "hint": "Packing works — now try real rules for your codebase."
    }
  ]
}
```

## Next steps

* Add more rules for your stack (Gradle/Kotlin/Android, etc).
* See **MCP** page to expose these rules to Cursor/Windsurf.
