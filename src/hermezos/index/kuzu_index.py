"""Kùzu embedded graph database index implementation."""

from __future__ import annotations

import logging
from pathlib import Path

from ..models import PackRequest, RuleCard

logger = logging.getLogger(__name__)

# Lazy import for optional dependency
_kuzu = None


def _get_kuzu():
    """Lazy import kuzu with helpful error message."""
    global _kuzu
    if _kuzu is None:
        try:
            import kuzu

            _kuzu = kuzu
        except ImportError as err:
            raise ImportError(
                "The 'kuzu' library is required for Kùzu graph indexing. "
                "Install it with: pip install 'hermezos[indexing]' or run: "
                "hermez bootstrap"
            ) from err
    return _kuzu


class KuzuIndex:
    """Kùzu embedded graph database index adapter.

    Provides local graph database storage with efficient querying
    for rule prefiltering based on intent tags and domains.
    """

    def __init__(self, db_path: Path):
        """Initialize Kùzu index.

        Args:
            db_path: Path to Kùzu database directory
        """
        kuzu = _get_kuzu()  # This will raise ImportError if kuzu is not available

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)

        # Initialize schema
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        try:
            # Create node tables
            self.conn.execute(
                """
                CREATE NODE TABLE IF NOT EXISTS RuleCard(
                    rule_id STRING PRIMARY KEY,
                    fingerprint STRING,
                    domain STRING,
                    status STRING,
                    severity STRING,
                    version INT64,
                    name STRING
                )
            """
            )

            self.conn.execute(
                """
                CREATE NODE TABLE IF NOT EXISTS IntentTag(
                    tag STRING PRIMARY KEY
                )
            """
            )

            self.conn.execute(
                """
                CREATE NODE TABLE IF NOT EXISTS Domain(
                    domain STRING PRIMARY KEY
                )
            """
            )

            self.conn.execute(
                """
                CREATE NODE TABLE IF NOT EXISTS Doc(
                    path STRING PRIMARY KEY,
                    note STRING
                )
            """
            )

            # Create relationship tables
            self.conn.execute(
                """
                CREATE REL TABLE IF NOT EXISTS HAS_TAG(
                    FROM RuleCard TO IntentTag
                )
            """
            )

            self.conn.execute(
                """
                CREATE REL TABLE IF NOT EXISTS OF_DOMAIN(
                    FROM RuleCard TO Domain
                )
            """
            )

            self.conn.execute(
                """
                CREATE REL TABLE IF NOT EXISTS DOC(
                    FROM RuleCard TO Doc
                )
            """
            )

            logger.debug("Kùzu schema initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Kùzu schema: {e}")
            raise

    def candidate_ids(self, request: PackRequest) -> list[str]:
        """Get candidate rule IDs for the given pack request.

        Args:
            request: Pack request with filtering criteria

        Returns:
            List of rule IDs that match the request criteria
        """
        try:
            # Build query based on request filters
            conditions = []
            params = {}

            # Filter by intent tags
            if request.intent_tags:
                tag_conditions = []
                for i, tag in enumerate(request.intent_tags):
                    param_name = f"tag_{i}"
                    tag_conditions.append(f"t.tag = ${param_name}")
                    params[param_name] = tag

                conditions.append(f"({' OR '.join(tag_conditions)})")

            # Base query
            if conditions:
                query = f"""
                    MATCH (r:RuleCard)-[:HAS_TAG]->(t:IntentTag)
                    WHERE {" AND ".join(conditions)}
                    RETURN DISTINCT r.rule_id
                    ORDER BY r.rule_id
                """
            else:
                # No filters - return all rule IDs
                query = """
                    MATCH (r:RuleCard)
                    RETURN r.rule_id
                    ORDER BY r.rule_id
                """

            # Execute query
            result = self.conn.execute(query, params)
            rule_ids = [row[0] for row in result.get_as_df().values.tolist()]

            logger.debug(f"Kùzu query returned {len(rule_ids)} candidate rule IDs")
            return rule_ids

        except Exception as e:
            logger.warning(f"Failed to query Kùzu for candidates: {e}")
            return []  # Fall back to no filtering

    def upsert_card(self, card: RuleCard) -> None:
        """Insert or update a rule card in the index.

        Args:
            card: Rule card to upsert
        """
        try:
            # Delete existing data for this rule
            self._delete_card_data(card.id)

            # Insert rule card node
            self.conn.execute(
                """
                CREATE (r:RuleCard {
                    rule_id: $rule_id,
                    fingerprint: $fingerprint,
                    domain: $domain,
                    status: $status,
                    severity: $severity,
                    version: $version,
                    name: $name
                })
            """,
                {
                    "rule_id": card.id,
                    "fingerprint": card.compute_fingerprint(),
                    "domain": card.domain,
                    "status": card.status.value,
                    "severity": card.severity.value,
                    "version": card.version,
                    "name": card.name,
                },
            )

            # Insert domain node if not exists
            self.conn.execute(
                """
                MERGE (d:Domain {domain: $domain})
            """,
                {"domain": card.domain},
            )

            # Create domain relationship
            self.conn.execute(
                """
                MATCH (r:RuleCard {rule_id: $rule_id})
                MATCH (d:Domain {domain: $domain})
                CREATE (r)-[:OF_DOMAIN]->(d)
            """,
                {"rule_id": card.id, "domain": card.domain},
            )

            # Insert intent tags and relationships
            for tag in card.intent_tags:
                # Insert tag node if not exists
                self.conn.execute(
                    """
                    MERGE (t:IntentTag {tag: $tag})
                """,
                    {"tag": tag},
                )

                # Create tag relationship
                self.conn.execute(
                    """
                    MATCH (r:RuleCard {rule_id: $rule_id})
                    MATCH (t:IntentTag {tag: $tag})
                    CREATE (r)-[:HAS_TAG]->(t)
                """,
                    {"rule_id": card.id, "tag": tag},
                )

            # Insert document nodes and relationships
            for ref in card.references:
                if ref.doc_url.startswith(("./", "../")):
                    # Insert doc node if not exists
                    self.conn.execute(
                        """
                        MERGE (d:Doc {path: $path, note: $note})
                    """,
                        {"path": ref.doc_url, "note": ref.note or ""},
                    )

                    # Create doc relationship
                    self.conn.execute(
                        """
                        MATCH (r:RuleCard {rule_id: $rule_id})
                        MATCH (d:Doc {path: $path})
                        CREATE (r)-[:DOC]->(d)
                    """,
                        {"rule_id": card.id, "path": ref.doc_url},
                    )

            logger.debug(f"Upserted rule card {card.id} in Kùzu")

        except Exception as e:
            logger.error(f"Failed to upsert card {card.id} in Kùzu: {e}")

    def delete_card(self, card_id: str) -> None:
        """Delete a rule card from the index.

        Args:
            card_id: ID of the rule card to delete
        """
        try:
            self._delete_card_data(card_id)
            logger.debug(f"Deleted rule card {card_id} from Kùzu")

        except Exception as e:
            logger.error(f"Failed to delete card {card_id} from Kùzu: {e}")

    def _delete_card_data(self, card_id: str) -> None:
        """Delete all data for a rule card (internal helper)."""
        # Delete the rule card node and its relationships
        self.conn.execute(
            """
            MATCH (r:RuleCard {rule_id: $rule_id})
            DETACH DELETE r
        """,
            {"rule_id": card_id},
        )

    def close(self) -> None:
        """Close the index adapter and clean up resources."""
        try:
            if hasattr(self, "conn"):
                self.conn.close()
            if hasattr(self, "db"):
                self.db.close()
            logger.debug("Closed Kùzu database connection")
        except Exception as e:
            logger.error(f"Error closing Kùzu database: {e}")
