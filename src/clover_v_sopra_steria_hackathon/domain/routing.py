"""Deterministic care-circle routing; no model decides recipients."""

from dataclasses import dataclass

from ..models import CareCircleMember, JournalEntry
from .privacy import PrivacyService, RecipientContext


@dataclass(frozen=True)
class RoutingService:
    privacy: PrivacyService

    def contexts_for_entry(
        self, *, entry: JournalEntry, members: list[CareCircleMember]
    ) -> list[RecipientContext]:
        contexts: list[RecipientContext] = []
        for member in members:
            if not member.active or member.recipient_id != entry.recipient_id:
                continue
            context = self.privacy.build_context(
                entry=entry,
                member=member,
                observations=list(entry.observations),
                actions=list(entry.action_items),
            )
            if context.allowed_observations or context.allowed_actions:
                contexts.append(context)
        return contexts
