"""MCP Server implementation for HermezOS."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Config
from ..models import (
    Action,
    ActionType,
    PackRequest,
    Provenance,
    RuleCard,
    Scope,
    Severity,
    Status,
)
from ..packer import RulePacker
from ..storage.filesystem import FileSystemStorage

# Try to import native MCP, fallback to stdio shim
try:
    from mcp import Tool
    from mcp.server import Server

    # TextContent import kept for future use

    HAS_NATIVE_MCP = True
except ImportError:
    HAS_NATIVE_MCP = False

    # Define dummy classes for type hints when MCP is not available
    class Tool:
        pass

    class Server:
        pass


class MCPServer:
    """MCP Server for HermezOS tools."""

    def __init__(self, config_path: Path | None = None):
        """Initialize MCP server."""
        self.config = Config(config_path)
        self.storage = FileSystemStorage(self.config.registry_root)
        self.packer = RulePacker()

    def _send_response(self, response: dict[str, Any]) -> None:
        """Send response to stdout."""
        json_str = json.dumps(response, separators=(",", ":"))
        print(json_str, flush=True)

    def _send_error(self, error: str, id: str | None = None) -> None:
        """Send error response."""
        response = {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": error},
            "id": id,
        }
        self._send_response(response)

    def _handle_pack(self, params: dict[str, Any], request_id: str) -> None:
        """Handle pack tool call."""
        try:
            # Extract parameters
            path = params.get("path", ".")
            intent_tags = params.get("intent_tags")
            languages = params.get("languages")
            limit = params.get("limit")

            # Create pack request
            request = PackRequest(
                path=path, intent_tags=intent_tags, languages=languages, limit=limit
            )

            # Get all rules from storage
            rules = self.storage.list_rules()

            # Pack rules
            bundle = self.packer.pack(rules, request)

            # Send success response
            response = {
                "jsonrpc": "2.0",
                "result": bundle.model_dump(),
                "id": request_id,
            }
            self._send_response(response)

        except Exception as e:
            self._send_error(f"Pack failed: {str(e)}", request_id)

    def _handle_add_rule(self, params: dict[str, Any], request_id: str) -> None:
        """Handle add_rule tool call."""
        try:
            # Extract parameters
            domain = params.get("domain")
            name = params.get("name")

            if not domain or not name:
                self._send_error(
                    "Missing required parameters: domain and name", request_id
                )
                return

            # Generate rule ID
            slug = name.lower().replace(" ", "-").replace("_", "-")
            rule_id = f"RULE-{domain}-{slug}"

            # Check if rule already exists
            if self.storage.get_rule(rule_id):
                self._send_error(f"Rule '{rule_id}' already exists", request_id)
                return

            # Create basic rule structure
            rule = RuleCard(
                schema_version=self.config.get("registry.default_schema_version", 1),
                id=rule_id,
                name=name,
                version=1,
                status=Status.DRAFT,
                severity=Severity.INFO,
                domain=domain,
                intent_tags=[],
                scope=Scope(),
                triggers=[],
                detectors=[],
                action=Action(
                    type=ActionType.MANUAL,
                    steps=["Describe the manual steps to resolve this issue"],
                ),
                hint=f"Review {name.lower()}",
                references=[],
                provenance=Provenance(
                    author="MCP User",
                    created=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    last_updated=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
            )

            # Save the rule
            self.storage.save_card(rule)

            # Get the path where the rule was saved
            rule_path = self.storage._get_rule_path(rule_id)

            response = {
                "jsonrpc": "2.0",
                "result": {"path": str(rule_path)},
                "id": request_id,
            }
            self._send_response(response)

        except Exception as e:
            self._send_error(f"Add rule failed: {str(e)}", request_id)

    def _handle_initialize(self, params: dict[str, Any], request_id: str) -> None:
        """Handle initialize request."""
        response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "hermezos", "version": "0.1.0"},
            },
            "id": request_id,
        }
        self._send_response(response)

    def _handle_tools_list(self, params: dict[str, Any], request_id: str) -> None:
        """Handle tools/list request."""
        tools = [
            {
                "name": "hermez.pack",
                "description": "Pack HermezOS rules for a given path",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to analyze"},
                        "intent_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by intent tags",
                        },
                        "languages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by programming languages",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rules to return",
                        },
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "hermez.add_rule",
                "description": "Add a new HermezOS rule",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Rule domain"},
                        "name": {"type": "string", "description": "Rule name"},
                    },
                    "required": ["domain", "name"],
                },
            },
        ]

        response = {"jsonrpc": "2.0", "result": {"tools": tools}, "id": request_id}
        self._send_response(response)

    def _handle_tools_call(self, params: dict[str, Any], request_id: str) -> None:
        """Handle tools/call request."""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "hermez.pack":
            self._handle_pack(tool_args, request_id)
        elif tool_name == "hermez.add_rule":
            self._handle_add_rule(tool_args, request_id)
        else:
            self._send_error(f"Unknown tool: {tool_name}", request_id)

    def _process_message(self, message: dict[str, Any]) -> None:
        """Process incoming JSON-RPC message."""
        if not isinstance(message, dict):
            self._send_error("Invalid message format")
            return

        method = message.get("method")
        params = message.get("params", {})
        request_id = message.get("id")

        if method == "initialize":
            self._handle_initialize(params, request_id)
        elif method == "tools/list":
            self._handle_tools_list(params, request_id)
        elif method == "tools/call":
            self._handle_tools_call(params, request_id)
        else:
            self._send_error(f"Unknown method: {method}", request_id)

    def run(self) -> None:
        """Run the MCP server."""
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    self._process_message(message)
                except json.JSONDecodeError as e:
                    self._send_error(f"Invalid JSON: {str(e)}")

        except KeyboardInterrupt:
            pass
        except Exception as e:
            self._send_error(f"Server error: {str(e)}")


# Native MCP Server Implementation
if HAS_NATIVE_MCP:

    class NativeMCPServer:
        """Native MCP server using the official MCP library."""

        def __init__(self):
            self.config = Config()
            self.storage = FileSystemStorage(self.config.registry_root)
            self.packer = RulePacker()

            # Initialize MCP server
            self.server = Server("hermezos")

            @self.server.tool()
            async def hermez_pack(
                path: str,
                intent_tags: list | None = None,
                languages: list | None = None,
                limit: int | None = None,
            ) -> str:
                """Pack HermezOS rules for a given path."""
                try:
                    # Create pack request
                    request = PackRequest(
                        path=path,
                        intent_tags=intent_tags,
                        languages=languages,
                        limit=limit,
                    )

                    # Get all rules from storage
                    rules = self.storage.list_rules()

                    # Pack rules
                    bundle = self.packer.pack(rules, request)

                    # Return JSON response
                    return json.dumps(bundle.model_dump(), indent=2)

                except Exception as e:
                    raise Exception(f"Pack failed: {str(e)}") from e

            @self.server.tool()
            async def hermez_add_rule(domain: str, name: str) -> str:
                """Add a new HermezOS rule."""
                try:
                    # Generate rule ID
                    slug = name.lower().replace(" ", "-").replace("_", "-")
                    rule_id = f"RULE-{domain}-{slug}"

                    # Check if rule already exists
                    if self.storage.get_rule(rule_id):
                        raise Exception(f"Rule '{rule_id}' already exists")

                    # Create basic rule structure
                    rule = RuleCard(
                        schema_version=self.config.get(
                            "registry.default_schema_version", 1
                        ),
                        id=rule_id,
                        name=name,
                        version=1,
                        status=Status.DRAFT,
                        severity=Severity.INFO,
                        domain=domain,
                        intent_tags=[],
                        scope=Scope(),
                        triggers=[],
                        detectors=[],
                        action=Action(
                            type=ActionType.MANUAL,
                            steps=["Describe the manual steps to resolve this issue"],
                        ),
                        hint=f"Review {name.lower()}",
                        references=[],
                        provenance=Provenance(
                            author="MCP User",
                            created=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                            last_updated=datetime.utcnow().strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                        ),
                    )

                    # Save the rule
                    self.storage.save_card(rule)

                    # Get the path where the rule was saved
                    rule_path = self.storage._get_rule_path(rule_id)

                    return json.dumps({"path": str(rule_path)}, indent=2)

                except Exception as e:
                    raise Exception(f"Add rule failed: {str(e)}") from e

        async def run(self):
            """Run the native MCP server."""

            try:
                from mcp.server.stdio import stdio_server

                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(
                        read_stream,
                        write_stream,
                        self.server.create_initialization_options(),
                    )
            except ImportError as e:
                # Fallback if stdio_server is not available
                raise RuntimeError("Native MCP stdio server not available") from e


def main():
    """Main entry point for MCP server."""
    if HAS_NATIVE_MCP:
        # Use native MCP server
        import asyncio

        server = NativeMCPServer()
        asyncio.run(server.run())
    else:
        # Fallback to stdio shim
        server = MCPServer()
        server.run()


if __name__ == "__main__":
    main()
