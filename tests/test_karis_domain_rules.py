"""M2 — business-rule tests for the Karis domain model.

Pure-Python rules (no DB connection needed): privacy defaults are enforced at
construction time, and guard methods raise BusinessRuleViolation.
"""

import pytest

from clover_v_sopra_steria_hackathon.domain.rules import (
    BusinessRuleViolation,
    is_report_eligible,
)
from clover_v_sopra_steria_hackathon.models import (
    ActionItem,
    ActionStatus,
    CareCircleMember,
    CaregiverFeeling,
    DeliveryStatus,
    GeneratedMessage,
    InputType,
    JournalEntry,
    JournalStatus,
    Observation,
    Role,
    SubjectType,
    Visibility,
    VocalAffectSignal,
    WearableWindow,
)

# ---------------------------------------------------------------------------
# Privacy defaults
# ---------------------------------------------------------------------------


def test_caregiver_feeling_is_private_by_default():
    feeling = CaregiverFeeling(feeling="fatigue")
    assert feeling.visibility == Visibility.PRIVATE


def test_vocal_affect_signal_is_private_by_default():
    signal = VocalAffectSignal(valence="negative", arousal="high", confidence=0.61)
    assert signal.visibility == Visibility.PRIVATE


def test_observation_is_circle_visible_by_default():
    observation = Observation(category="nutrition", summary="Peu mangé")
    assert observation.visibility == Visibility.CIRCLE


def test_caregiver_wearable_window_is_private_by_default():
    window = WearableWindow(subject_type=SubjectType.CAREGIVER, subject_id=None)
    assert window.visibility == Visibility.PRIVATE


def test_recipient_wearable_window_is_circle_visible_by_default():
    window = WearableWindow(subject_type=SubjectType.CARE_RECIPIENT, subject_id=None)
    assert window.visibility == Visibility.CIRCLE


def test_caregiver_wearable_privacy_cannot_be_silently_overridden_by_default():
    # Explicit override is possible (deliberate choice), but never the default.
    window = WearableWindow(
        subject_type="caregiver",  # raw string also triggers the rule
        subject_id=None,
        visibility=Visibility.CIRCLE,
    )
    assert window.visibility == Visibility.CIRCLE  # explicit choice respected


# ---------------------------------------------------------------------------
# Role enum validity
# ---------------------------------------------------------------------------


def test_role_enum_contains_all_demo_roles():
    expected = {
        "primary_caregiver",
        "family_caregiver",
        "auxiliary",
        "administrative_helper",
        "family_informed",
        "medical_professional",
    }
    assert {r.value for r in Role} == expected


def test_valid_role_value_resolves():
    assert Role("family_caregiver") is Role.FAMILY_CAREGIVER
    member = CareCircleMember(role=Role.AUXILIARY)
    assert member.role is Role.AUXILIARY


def test_invalid_role_value_is_rejected():
    with pytest.raises(ValueError):
        Role("owner")


# ---------------------------------------------------------------------------
# Finalized-entry rule (weekly reports use finalized entries only)
# ---------------------------------------------------------------------------


def _entry() -> JournalEntry:
    return JournalEntry(input_type=InputType.TEXT, original_text="note")


def test_new_entry_is_draft_and_not_report_eligible():
    entry = _entry()
    assert entry.status == JournalStatus.DRAFT
    assert not entry.is_finalized
    assert not is_report_eligible(entry)


def test_finalize_makes_entry_report_eligible():
    entry = _entry()
    entry.finalize()
    assert entry.status == JournalStatus.FINALIZED
    assert entry.is_finalized
    assert is_report_eligible(entry)
    assert entry.finalized_at is not None


def test_double_finalize_is_rejected():
    entry = _entry()
    entry.finalize()
    with pytest.raises(BusinessRuleViolation):
        entry.finalize()


# ---------------------------------------------------------------------------
# Approved-before-send rule
# ---------------------------------------------------------------------------


def _message() -> GeneratedMessage:
    return GeneratedMessage(text="Bonjour Sophie, point sur Marie.")


def test_generated_message_starts_unapproved_draft():
    message = _message()
    assert message.approved is False
    assert message.delivery_status == DeliveryStatus.DRAFT
    assert not message.can_send


def test_cannot_send_without_approval():
    message = _message()
    with pytest.raises(BusinessRuleViolation, match="before approval"):
        message.mark_sent()
    assert message.delivery_status == DeliveryStatus.DRAFT
    assert message.sent_at is None


def test_approved_message_can_be_sent():
    message = _message()
    message.approve()
    assert message.can_send
    message.mark_sent()
    assert message.delivery_status == DeliveryStatus.SENT
    assert message.sent_at is not None


# ---------------------------------------------------------------------------
# Action item transitions (supporting rules)
# ---------------------------------------------------------------------------


def test_action_completes_and_cannot_be_cancelled_afterwards():
    action = ActionItem(title="Renouveler l'ordonnance")
    assert action.status == ActionStatus.PENDING
    action.complete()
    assert action.status == ActionStatus.DONE
    assert action.completed_at is not None
    with pytest.raises(BusinessRuleViolation):
        action.cancel()


def test_cancelled_action_cannot_be_completed():
    action = ActionItem(title="Séance de kiné")
    action.cancel()
    assert action.status == ActionStatus.CANCELLED
    with pytest.raises(BusinessRuleViolation):
        action.complete()
