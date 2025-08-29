"""Null index implementation - no-op for backward compatibility."""

from __future__ import annotations

from ..models import PackRequest, RuleCard


class NullIndex:
    """No-op index adapter that provides backward compatibility.

    This adapter does nothing and returns empty results, ensuring
    that existing behavior is preserved when indexing is disabled.
    """

    def candidate_ids(self, request: PackRequest) -> list[str]:
        """Return empty list - no filtering applied.

        Args:
            request: Pack request (ignored)

        Returns:
            Empty list, meaning all rules should be evaluated
        """
        return []

    def upsert_card(self, card: RuleCard) -> None:
        """No-op upsert operation.

        Args:
            card: Rule card (ignored)
        """
        pass

    def delete_card(self, card_id: str) -> None:
        """No-op delete operation.

        Args:
            card_id: Rule card ID (ignored)
        """
        pass

    def close(self) -> None:
        """No-op close operation."""
        pass
