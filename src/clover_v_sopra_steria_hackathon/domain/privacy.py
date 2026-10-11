"""Deterministic privacy filtering for recipient-specific sharing."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import ActionItem, CareCircleMember, JournalEntry, Observation, Visibility


class AllowedObservation(BaseModel):
    id: UUID
    category: str
    description: str


class AllowedAction(BaseModel):
    id: UUID
    description: str
    status: str
    assignee_id: UUID | None = None


class RecipientContext(BaseModel):
    recipient_id: UUID
    recipient_name: str
    role: str
    journal_entry_id: UUID
    allowed_observations: list[AllowedObservation] = Field(default_factory=list)
    allowed_actions: list[AllowedAction] = Field(default_factory=list)
    relevant_context: list[str] = Field(default_factory=list)
    source_item_ids: list[UUID] = Field(default_factory=list)
    excluded_private_count: int = 0


@dataclass(frozen=True)
class PrivacyService:
    """Builds an allowlisted context without exposing original journal text."""

    def build_context(
        self,
        *,
        entry: JournalEntry,
        member: CareCircleMember,
        observations: list[Observation],
        actions: list[ActionItem],
    ) -> RecipientContext:
        allowed_observations = [
            item
            for item in observations
            if item.visibility != Visibility.PRIVATE
            and self._observation_allowed(member.role.value, item.category)
        ]
        allowed_actions = [
            item
            for item in actions
            if self._action_allowed(member, item)
        ]
        source_item_ids = [item.id for item in allowed_observations]
        source_item_ids.extend(item.id for item in allowed_actions)
        excluded_private_count = sum(
            1 for item in observations if item.visibility == Visibility.PRIVATE
        )
        excluded_private_count += sum(
            1 for item in entry.feelings if item.visibility == Visibility.PRIVATE
        )
        excluded_private_count += len(entry.vocal_signals)
        excluded_private_count += sum(
            1
            for item in entry.wearable_windows
            if item.visibility == Visibility.PRIVATE
        )
        return RecipientContext(
            recipient_id=member.user_id,
            recipient_name=member.user.full_name.split()[0],
            role=member.role.value,
            journal_entry_id=entry.id,
            allowed_observations=[
                AllowedObservation(
                    id=item.id,
                    category=item.category,
                    description=item.summary,
                )
                for item in allowed_observations
            ],
            allowed_actions=[
                AllowedAction(
                    id=item.id,
                    description=item.title,
                    status=item.status.value,
                    assignee_id=item.assignee_id,
                )
                for item in allowed_actions
            ],
            relevant_context=self._relevant_context(member, allowed_observations, allowed_actions),
            source_item_ids=source_item_ids,
            excluded_private_count=excluded_private_count,
        )

    @staticmethod
    def _observation_allowed(role: str, category: str) -> bool:
        if role == "family_caregiver":
            return category in {"fatigue", "nutrition", "general", "practical"}
        if role == "auxiliary":
            return category in {"nutrition", "practical", "general"}
        if role == "administrative_helper":
            return category in {"appointment", "administrative", "logistics"}
        if role == "family_informed":
            return category in {"general"}
        return False

    @staticmethod
    def _action_allowed(member: CareCircleMember, action: ActionItem) -> bool:
        role = member.role.value
        title = action.title.lower()
        if action.assignee_id == member.user_id:
            return True
        if role == "family_caregiver":
            return True
        if role == "auxiliary":
            return any(word in title for word in ("repas", "alimentation", "soin", "visite", "quotidien"))
        if role == "administrative_helper":
            return any(word in title for word in ("rendez-vous", "rendez vous", "kiné", "appointment", "administratif"))
        if role == "family_informed":
            return False
        return False

    @staticmethod
    def _relevant_context(
        member: CareCircleMember,
        observations: list[Observation],
        actions: list[ActionItem],
    ) -> list[str]:
        context = [item.summary for item in observations]
        context.extend(item.title for item in actions if item.assignee_id == member.user_id)
        return context


class RecipientContextBuilder:
    """Named façade for building the allowlisted recipient context."""

    def __init__(self, privacy: PrivacyService | None = None):
        self.privacy = privacy or PrivacyService()

    def build(
        self,
        *,
        entry: JournalEntry,
        member: CareCircleMember,
    ) -> RecipientContext:
        return self.privacy.build_context(
            entry=entry,
            member=member,
            observations=list(entry.observations),
            actions=list(entry.action_items),
        )
