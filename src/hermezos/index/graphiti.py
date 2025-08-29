"""Graphiti index implementation with export and live modes."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from ..models import PackRequest, RuleCard
from . import IndexAdapter

logger = logging.getLogger(__name__)

# Lazy import for optional dependency
_requests = None

def _get_requests():
    """Lazy import requests with helpful error message."""
    global _requests
    if _requests is None:
        try:
            import requests
            _requests = requests
        except ImportError:
            raise ImportError(
                "The 'requests' library is required for Graphiti live mode. "
                "Install it with: pip install 'hermezos[indexing]' or run: hermez bootstrap"
            )
    return _requests


class GraphitiIndex:
    """Graphiti index adapter with export_only and live modes.
    
    In export_only mode (default), writes deterministic JSONL files to disk.
    In live mode, sends data to Graphiti server via HTTP API.
    """

    def __init__(
        self,
        mode: str = "export_only",
        url: str = "http://localhost:8800",
        api_key: str = "",
        export_path: Path = Path("graph"),
    ):
        """Initialize Graphiti index.
        
        Args:
            mode: "export_only" or "live"
            url: Graphiti server URL (for live mode)
            api_key: Graphiti API key (for live mode)
            export_path: Directory for JSONL exports (for export_only mode)
        """
        self.mode = mode.lower()
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.export_path = export_path
        
        # In-memory storage for export_only mode
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        
        if self.mode == "export_only":
            # Ensure export directory exists
            self.export_path.mkdir(parents=True, exist_ok=True)

    def candidate_ids(self, request: PackRequest) -> list[str]:
        """Get candidate rule IDs for the given pack request.
        
        In export_only mode, returns empty list (no filtering).
        In live mode, could query Graphiti server but returns empty for now.
        
        Args:
            request: Pack request with filtering criteria
            
        Returns:
            Empty list (no prefiltering in current implementation)
        """
        # For now, Graphiti doesn't provide prefiltering
        # This could be enhanced to query the live server for candidates
        return []

    def upsert_card(self, card: RuleCard) -> None:
        """Insert or update a rule card in the index.
        
        Args:
            card: Rule card to upsert
        """
        if self.mode == "export_only":
            self._upsert_card_export(card)
        elif self.mode == "live":
            self._upsert_card_live(card)

    def delete_card(self, card_id: str) -> None:
        """Delete a rule card from the index.
        
        Args:
            card_id: ID of the rule card to delete
        """
        if self.mode == "export_only":
            self._delete_card_export(card_id)
        elif self.mode == "live":
            self._delete_card_live(card_id)

    def close(self) -> None:
        """Close the index adapter and clean up resources."""
        if self.mode == "export_only":
            self._write_export_files()

    def _upsert_card_export(self, card: RuleCard) -> None:
        """Upsert card in export mode - store in memory for later write."""
        # Create nodes
        rule_node = {
            "id": card.id,
            "type": "RuleCard",
            "fingerprint": card.compute_fingerprint(),
            "domain": card.domain,
            "status": card.status.value,
            "severity": card.severity.value,
            "version": card.version,
            "name": card.name,
        }
        self._nodes[card.id] = rule_node
        
        # Create domain node
        domain_id = f"domain:{card.domain}"
        domain_node = {
            "id": domain_id,
            "type": "Domain",
            "name": card.domain,
        }
        self._nodes[domain_id] = domain_node
        
        # Create intent tag nodes
        for tag in card.intent_tags:
            tag_id = f"tag:{tag}"
            tag_node = {
                "id": tag_id,
                "type": "IntentTag",
                "name": tag,
            }
            self._nodes[tag_id] = tag_node
        
        # Create document nodes for references
        for ref in card.references:
            if ref.doc_url.startswith(("./", "../")):
                doc_id = f"doc:{ref.doc_url}"
                doc_node = {
                    "id": doc_id,
                    "type": "Doc",
                    "path": ref.doc_url,
                    "note": ref.note,
                }
                self._nodes[doc_id] = doc_node
        
        # Remove old edges for this card
        self._edges = [e for e in self._edges if e.get("source") != card.id]
        
        # Create edges
        # RuleCard -> Domain
        self._edges.append({
            "source": card.id,
            "target": domain_id,
            "type": "OF_DOMAIN",
        })
        
        # RuleCard -> IntentTag
        for tag in card.intent_tags:
            self._edges.append({
                "source": card.id,
                "target": f"tag:{tag}",
                "type": "HAS_TAG",
            })
        
        # RuleCard -> Doc
        for ref in card.references:
            if ref.doc_url.startswith(("./", "../")):
                self._edges.append({
                    "source": card.id,
                    "target": f"doc:{ref.doc_url}",
                    "type": "DOC",
                })

    def _delete_card_export(self, card_id: str) -> None:
        """Delete card from export mode - remove from memory."""
        # Remove node
        self._nodes.pop(card_id, None)
        
        # Remove edges
        self._edges = [e for e in self._edges if e.get("source") != card_id and e.get("target") != card_id]

    def _write_export_files(self) -> None:
        """Write nodes and edges to JSONL files atomically."""
        try:
            # Write nodes.jsonl
            nodes_path = self.export_path / "nodes.jsonl"
            self._write_jsonl_atomic(nodes_path, sorted(self._nodes.values(), key=lambda x: x["id"]))
            
            # Write edges.jsonl
            edges_path = self.export_path / "edges.jsonl"
            sorted_edges = sorted(self._edges, key=lambda x: (x["source"], x["target"], x["type"]))
            self._write_jsonl_atomic(edges_path, sorted_edges)
            
            logger.info(f"Exported {len(self._nodes)} nodes and {len(self._edges)} edges to {self.export_path}")
            
        except Exception as e:
            logger.error(f"Failed to write export files: {e}")

    def _write_jsonl_atomic(self, path: Path, data: list[dict[str, Any]]) -> None:
        """Write JSONL data to file atomically."""
        # Create temporary file in same directory
        temp_fd = None
        temp_path = None
        
        try:
            # Create temporary file
            temp_fd, temp_path_str = tempfile.mkstemp(
                dir=path.parent, prefix=f"{path.name}.tmp.", suffix=".tmp"
            )
            temp_path = Path(temp_path_str)
            
            # Write JSONL content to temporary file
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                for item in data:
                    json.dump(item, f, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
                    f.write("\n")
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            temp_fd = None  # Don't close again in finally
            
            # Atomic rename
            temp_path.replace(path)
            
        finally:
            if temp_fd is not None:
                os.close(temp_fd)
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _upsert_card_live(self, card: RuleCard) -> None:
        """Upsert card in live mode - send to Graphiti server."""
        try:
            # Prepare data for Graphiti API
            data = {
                "rule_card": card.model_dump(),
                "fingerprint": card.compute_fingerprint(),
            }
            
            headers = {
                "Content-Type": "application/json",
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Send to Graphiti server
            requests = _get_requests()
            response = requests.post(
                f"{self.url}/api/rules",
                json=data,
                headers=headers,
                timeout=30,
            )
            
            if response.status_code not in (200, 201):
                logger.warning(f"Failed to upsert card {card.id} to Graphiti: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Failed to upsert card {card.id} to Graphiti: {e}")

    def _delete_card_live(self, card_id: str) -> None:
        """Delete card from live mode - send delete to Graphiti server."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Send delete to Graphiti server
            requests = _get_requests()
            response = requests.delete(
                f"{self.url}/api/rules/{card_id}",
                headers=headers,
                timeout=30,
            )
            
            if response.status_code not in (200, 204, 404):
                logger.warning(f"Failed to delete card {card_id} from Graphiti: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Failed to delete card {card_id} from Graphiti: {e}")