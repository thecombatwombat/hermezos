"""Rule packing logic for HermezOS."""

import fnmatch
import os
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .models import (
    DetectorType,
    PackBundle,
    PackRequest,
    RuleCard,
    RuleMatch,
    Severity,
    Status,
    TriggerType,
)
from .index import IndexAdapter


class RulePacker:
    """Handles rule selection and packing logic."""

    def __init__(self, hermez_version: str = "1.0.0"):
        """Initialize packer with HermezOS version."""
        self.hermez_version = hermez_version

        # Status rank for sorting (active > draft > deprecated)
        self._status_rank = {
            Status.ACTIVE: 0,
            Status.DRAFT: 1,
            Status.DEPRECATED: 2,
        }

        # Severity rank for sorting (error > warning > info)
        self._severity_rank = {
            Severity.ERROR: 0,
            Severity.WARNING: 1,
            Severity.INFO: 2,
        }

    def pack(
        self,
        rules: Iterable[RuleCard],
        request: PackRequest,
        index: IndexAdapter | None = None
    ) -> PackBundle:
        """Pack rules based on the request.

        Args:
            rules: Iterable of rule cards to evaluate
            request: Pack request with filtering criteria
            index: Optional index adapter for prefiltering

        Returns:
            PackBundle containing matched rules and metadata
        """
        # Convert iterable to list for multiple iterations
        rule_list = list(rules)

        # Apply index prefilter if available
        if index:
            try:
                candidate_ids = index.candidate_ids(request)
                if candidate_ids:
                    # Filter rules to only those in candidate set
                    id_set = set(candidate_ids)
                    rule_list = [r for r in rule_list if r.id in id_set]
            except Exception as e:
                # Log warning but continue with all rules
                print(f"WARNING: Index prefilter failed: {e}")

        # Apply filters from PackRequest
        filtered_rules = self._apply_request_filters(rule_list, request)

        # Sort rules deterministically
        sorted_rules = self._sort_rules(filtered_rules)

        # Apply limit if specified
        if request.limit:
            sorted_rules = sorted_rules[: request.limit]

        # Collect target paths to analyze
        target_paths = self._collect_target_paths(request)

        # Evaluate rules against target paths
        rule_matches = self._evaluate_rules(sorted_rules, target_paths)

        # Build actions summary
        actions_summary = self._build_actions_summary(rule_matches)

        # Create pack bundle
        bundle = PackBundle(
            pack_request=request,
            rules=rule_matches,
            hermez_version=self.hermez_version,
            created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            filters=self._extract_filters(request),
            cards=self._normalize_rule_cards(rule_matches),
            actions_summary=actions_summary,
        )

        return bundle

    def _apply_request_filters(
        self, rules: list[RuleCard], request: PackRequest
    ) -> list[RuleCard]:
        """Apply filters from PackRequest to rule list."""
        filtered = rules

        # Filter by intent tags
        if request.intent_tags:
            filtered = self._filter_by_intent(filtered, request.intent_tags)

        # Filter by languages
        if request.languages:
            filtered = self._filter_by_languages(filtered, request.languages)

        # Filter deprecated rules unless explicitly allowed
        if not request.include_deprecated:
            filtered = [r for r in filtered if r.status != Status.DEPRECATED]

        return filtered

    def _filter_by_intent(
        self, rules: list[RuleCard], intent_tags: list[str] | None
    ) -> list[RuleCard]:
        """Filter rules by intent tags."""
        if not intent_tags:
            return rules

        filtered = []
        for rule in rules:
            # Debug: print what we're checking
            print(
                f"DEBUG: Checking rule {rule.id} with intent_tags "
                f"{rule.intent_tags} against filter {intent_tags}"
            )
            if any(tag in rule.intent_tags for tag in intent_tags):
                print(f"DEBUG: Rule {rule.id} matches!")
                filtered.append(rule)
            else:
                print(f"DEBUG: Rule {rule.id} does not match")

        return filtered

    def _filter_by_languages(
        self, rules: list[RuleCard], languages: list[str] | None
    ) -> list[RuleCard]:
        """Filter rules by programming languages."""
        if not languages:
            return rules

        filtered = []
        for rule in rules:
            if any(lang in rule.scope.languages for lang in languages):
                filtered.append(rule)

        return filtered

    def _sort_rules(self, rules: list[RuleCard]) -> list[RuleCard]:
        """Sort rules deterministically according to specification.

        Sort key: status (active>draft>deprecated), severity
        (error>warning>info), version desc, id asc
        """

        def sort_key(rule: RuleCard) -> tuple[int, int, int, str]:
            return (
                self._status_rank.get(rule.status, 999),  # status asc (active first)
                self._severity_rank.get(
                    rule.severity, 999
                ),  # severity asc (error first)
                -rule.version,  # version desc (higher versions first)
                rule.id,  # id asc (alphabetical)
            )

        return sorted(rules, key=sort_key)

    def _collect_target_paths(self, request: PackRequest) -> list[Path]:
        """Collect target file paths constrained by PackRequest.file_globs."""
        path = Path(request.path)

        if not path.exists():
            return []

        if path.is_file():
            return [path]

        if not path.is_dir():
            return []

        # Collect files recursively, respecting file_globs constraint
        target_paths = []
        file_globs = request.file_globs or [
            "*"
        ]  # Default to all files if no globs specified

        for root, dirs, files in os.walk(path):
            # Skip common directories to optimize
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {
                    "__pycache__",
                    "node_modules",
                    "build",
                    "dist",
                    ".git",
                    "target",
                }
            ]

            root_path = Path(root)
            for file in files:
                # Skip hidden files and common artifacts
                if file.startswith(".") or file.endswith(
                    (".pyc", ".pyo", ".tmp", ".log")
                ):
                    continue

                file_path = root_path / file

                # Check if file matches any of the specified globs
                if any(fnmatch.fnmatch(str(file_path), glob) for glob in file_globs):
                    target_paths.append(file_path)

        return target_paths

    def _evaluate_rules(
        self, rules: list[RuleCard], target_paths: list[Path]
    ) -> list[RuleMatch]:
        """Evaluate rules against target paths using scope → triggers
        → detectors order."""
        rule_matches = []

        for rule in rules:
            rule_matched = False
            triggered_by = []
            detected_in = []

            for target_path in target_paths:
                # Step 1: Evaluate scope
                if not self._matches_scope(rule, target_path):
                    continue

                # Step 2: Evaluate triggers (ALL must match)
                path_triggers = self._evaluate_triggers(rule, target_path)
                if rule.triggers and not path_triggers:
                    continue  # Triggers not satisfied

                # Step 3: Evaluate detectors (ANY can match)
                detectors_matched, detections = self._evaluate_detectors(
                    rule, target_path
                )
                if not detectors_matched:
                    continue  # Detectors not satisfied

                # Rule matched for this path
                rule_matched = True
                triggered_by.extend(path_triggers)
                detected_in.extend(detections)

            if rule_matched:
                # Remove duplicates and create RuleMatch
                rule_match = RuleMatch(
                    rule=rule,
                    fingerprint=rule.compute_fingerprint(),
                    triggered_by=list(set(triggered_by)),
                    detected_in=list(set(detected_in)),
                )
                rule_matches.append(rule_match)

        return rule_matches

    def _matches_scope(self, rule: RuleCard, target_path: Path) -> bool:
        """Check if rule matches the target path scope."""
        scope = rule.scope

        # Check repository patterns
        if scope.repo_patterns:
            repo_match = False
            for pattern in scope.repo_patterns:
                if fnmatch.fnmatch(str(target_path), pattern):
                    repo_match = True
                    break
            if not repo_match:
                return False

        # Check file globs
        if scope.file_globs:
            file_match = False
            for glob_pattern in scope.file_globs:
                if fnmatch.fnmatch(str(target_path), glob_pattern):
                    file_match = True
                    break
            if not file_match:
                return False

        # Check languages (basic extension matching)
        if scope.languages:
            lang_match = False
            file_ext = target_path.suffix.lower()
            for lang in scope.languages:
                lang_lower = lang.lower()
                if lang_lower == "kotlin" and file_ext in [".kt", ".kts"]:
                    lang_match = True
                elif lang_lower == "java" and file_ext == ".java":
                    lang_match = True
                elif lang_lower == "python" and file_ext in [".py", ".pyi"]:
                    lang_match = True
                elif lang_lower == "javascript" and file_ext in [".js", ".jsx"]:
                    lang_match = True
                elif lang_lower == "typescript" and file_ext in [".ts", ".tsx"]:
                    lang_match = True
                elif lang_lower == "groovy" and file_ext in [".gradle", ".groovy"]:
                    lang_match = True

                if lang_match:
                    break

            if not lang_match:
                return False

        return True

    def _evaluate_triggers(self, rule: RuleCard, target_path: Path) -> list[str]:
        """Evaluate triggers for a rule. Returns list of matched
        trigger descriptions."""
        matched_triggers = []

        for trigger in rule.triggers:
            if trigger.type == TriggerType.PATH_CONTAINS:
                if trigger.value in str(target_path):
                    matched_triggers.append(f"path contains '{trigger.value}'")
            elif trigger.type == TriggerType.FILE_EXISTS:
                if Path(trigger.value).exists():
                    matched_triggers.append(f"file exists '{trigger.value}'")

        return matched_triggers

    def _evaluate_detectors(
        self, rule: RuleCard, target_path: Path
    ) -> tuple[bool, list[str]]:
        """Evaluate detectors for a rule. Returns (matched, detection_descriptions)."""
        if not rule.detectors:
            return True, []  # No detectors means always match

        detection_matches = []

        for detector in rule.detectors:
            try:
                if detector.type == DetectorType.REGEX and detector.pattern:
                    # Check file glob constraint if specified
                    if detector.file_glob and not fnmatch.fnmatch(
                        str(target_path), detector.file_glob
                    ):
                        continue  # File doesn't match the glob

                    # Read file content and search for pattern
                    with open(target_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # Search line by line for better performance and context
                    lines = content.splitlines()
                    for line_num, line in enumerate(lines, 1):
                        if re.search(detector.pattern, line):
                            detection_matches.append(
                                f"regex '{detector.pattern}' found in "
                                f"{target_path.name}:{line_num}"
                            )
                            break  # Found match, no need to check other lines

                elif detector.type == DetectorType.FILE_EXISTS and detector.value:
                    if Path(detector.value).exists():
                        detection_matches.append(f"file exists '{detector.value}'")

                elif detector.type == DetectorType.PATH_CONTAINS and detector.value:
                    if detector.value in str(target_path):
                        detection_matches.append(f"path contains '{detector.value}'")

            except (FileNotFoundError, OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        # Return True if any detector matched (ANY logic)
        return len(detection_matches) > 0, detection_matches

    def _extract_filters(self, request: PackRequest) -> dict[str, Any]:
        """Extract filters from PackRequest for the bundle."""
        return {
            "intent_tags": request.intent_tags or [],
            "languages": request.languages or [],
            "file_globs": getattr(request, "file_globs", None) or [],
            "include_deprecated": request.include_deprecated,
            "limit": request.limit,
        }

    def _normalize_rule_cards(
        self, rule_matches: list[RuleMatch]
    ) -> list[dict[str, Any]]:
        """Normalize rule cards to JSON format with fingerprints."""
        normalized = []
        for match in rule_matches:
            rule_dict = match.rule.model_dump(exclude_unset=True)
            normalized.append(
                {
                    "rule": rule_dict,
                    "fingerprint": match.fingerprint,
                }
            )
        return normalized

    def _build_actions_summary(self, rule_matches: list[RuleMatch]) -> dict[str, Any]:
        """Build summary of actions from matched rules."""
        summary: dict[str, Any] = {
            "total_actions": len(rule_matches),
            "action_types": {},
            "severities": {},
            "domains": {},
        }

        for match in rule_matches:
            rule = match.rule

            # Count action types
            action_type = (
                rule.action.type.value
                if hasattr(rule.action.type, "value")
                else str(rule.action.type)
            )
            action_types: dict[str, int] = summary["action_types"]
            action_types[action_type] = action_types.get(action_type, 0) + 1

            # Count severities
            severity = (
                rule.severity.value
                if hasattr(rule.severity, "value")
                else str(rule.severity)
            )
            severities: dict[str, int] = summary["severities"]
            severities[severity] = severities.get(severity, 0) + 1

            # Count domains
            domains: dict[str, int] = summary["domains"]
            domains[rule.domain] = domains.get(rule.domain, 0) + 1

        return summary
