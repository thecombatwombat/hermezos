---
title: HermezOS - Messenger of Unwritten Rules
description: Local-first knowledge registry that transforms your team's unwritten rules into deterministic, AI-ready context packs.
---

# HermezOS
*Messenger of unwritten rules*

<div style="text-align: center; margin: 1.5rem 0;">
  <a href="https://github.com/thecombatwombat/hermezos" class="repo-link" target="_blank" rel="noopener">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
    </svg>
    View on GitHub
  </a>
</div>

## The Problem: Knowledge Trapped in Tribal Memory

Every development team has them—the unwritten rules that separate good code from great code. The patterns that prevent bugs. The conventions that make codebases maintainable. The hard-won lessons from production incidents.

But this knowledge lives in:
- **Slack threads** that get buried
- **Code review comments** that aren't searchable
- **Senior developers' heads** who might leave tomorrow
- **Wiki pages** that go stale and contradict each other

When AI agents analyze your code, they miss these crucial insights. When new team members join, they repeat old mistakes. When you're debugging at 2 AM, you can't remember if it was "always use plugins DSL" or "sometimes use apply plugin."

## The Solution: Deterministic Knowledge Packing

HermezOS transforms your team's unwritten rules into a **local-first registry** that both humans and AI agents can query with surgical precision.

### Why This Approach Works

**🎯 Contextual Intelligence**: Instead of generic linting rules, HermezOS delivers the exact knowledge needed for your specific codebase, filtered by intent, language, and scope.

**🔒 Local-First**: Your rules stay on your infrastructure. No API keys, no network dependencies, no vendor lock-in. Works offline, scales infinitely.

**🎲 Deterministic**: Same input always produces the same output, with SHA256 fingerprints for every rule and bundle. Perfect for CI/CD, caching, and reproducible builds.

**🤖 Agent-Ready**: Native MCP (Model Context Protocol) support means your AI assistants get instant access to your team's collective wisdom.

## How It Works: Three Simple Concepts

### 1. **Rule Cards**: Knowledge as Code
```yaml
id: RULE-android-plugins-dsl
name: Prefer Gradle plugins DSL
triggers:
  - type: path_contains
    value: ".gradle"
detectors:
  - type: regex
    pattern: apply\s+plugin:\s*['"]\w+['"]
action:
  type: manual
  steps:
    - Replace 'apply plugin: "com.android.application"' with plugins DSL
hint: Use plugins DSL for better performance
```

Each rule captures:
- **When** it applies (triggers)
- **What** to look for (detectors)
- **How** to fix it (actions)
- **Why** it matters (hints & references)

### 2. **Smart Packing**: Context-Aware Selection

The packer engine applies multi-stage filtering:

```
Codebase → Scope Match → Trigger Eval → Detector Eval → Sort & Limit → Bundle
```

Only rules relevant to your specific context get packed. No noise, no irrelevant suggestions.

### 3. **Deterministic Output**: Reproducible Results

Every pack operation produces a fingerprinted bundle:

```json
{
  "pack_fingerprint": "sha256-a1b2c3...",
  "rules": [...],
  "total_rules": 3,
  "created_at": "2024-01-15T10:00:00Z"
}
```

Same codebase + same rules = same fingerprint. Perfect for caching, CI/CD, and change detection.

## Integration: Works Everywhere

### Command Line
```bash
# Pack rules for current directory
hermez pack . --intent security --lang python --json -

# Add new rule interactively
hermez add android "Custom Rule"

# Validate all rules
hermez validate
```

### AI Assistants (MCP)
```json
{
  "mcpServers": {
    "HermezOS": {
      "command": "hermez",
      "args": ["mcp"]
    }
  }
}
```

### Python Library
```python
from hermezos import RulePacker, PackRequest

request = PackRequest(path="./src", intent_tags=["best-practice"])
bundle = packer.pack(request)
```

### CI/CD Pipeline
```yaml
- name: Pack rules for analysis
  run: hermez pack . --json - > hermez-report.json
```

## Ready to Start?

Transform your team's tribal knowledge into actionable, deterministic rules that both humans and AI can leverage.

**[Get Started with the Quickstart Guide →](Quickstart.md)**

---

*HermezOS helps teams capture and share the unwritten rules that make their codebases great.*
