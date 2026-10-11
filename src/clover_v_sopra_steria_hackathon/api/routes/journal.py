"""M3 text journal and care-circle endpoints."""

import uuid
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pathlib import Path
import time
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ...api.deps import (
    get_db,
    get_llm_provider,
    get_messaging_provider, get_object_storage_provider, get_transcription_provider,
    get_ser_provider,
    get_wearable_provider,
)
from ...domain.multimodal import MultimodalJournalContext, build_multimodal_context
from ...domain.privacy import PrivacyService, RecipientContext, RecipientContextBuilder
from ...domain.routing import RoutingService
from ...domain.report import WeeklyReportContext
from ...models import (
    ActionItem,
    CareCircleMember,
    CareRecipient,
    CaregiverFeeling,
    Clarification,
    DeliveryStatus,
    GeneratedMessage,
    InputType,
    JournalEntry,
    JournalStatus,
    Observation,
    User,
    Visibility,
    VocalAffectSignal,
    WearableWindow,
    WeeklyReport,
)
from ...models.enums import ActionStatus, SubjectType
from ...providers.base import (
    JournalAnalysisResult,
    ProviderMetadata,
    LLMProvider,
    MessagingProvider,
    ObjectStorageProvider, TranscriptionProvider,
    SpeechEmotionProvider,
    WearableProvider,
)
from ..schemas import (
    ActionResponse,
    CareRecipientResponse,
    FeelingResponse,
    JournalCreate,
    JournalResponse,
    ClarificationResponse,
    ClarificationSubmission,
    MessageGenerationResponse,
    MessagePatch,
    MessageResponse,
    PrivacyPipeline,
    MockInboxItem,
    MockInboxResponse,
    WeeklyReportGenerate,
    WeeklyReportPatch,
    WeeklyReportResponse,
    MemberResponse,
    ObservationResponse,
    TimelineItem,
    TimelineResponse,
    UserResponse,
    MultimodalContextResponse,
    AudioUploadResponse, TranscriptPatch, TranscriptResponse,
)
from ...services.message_service import MessageGenerationService
from ...services.report_service import ReportAggregationService, WeeklyReportService
from ...providers.llm.contracts import ClarificationInput, JournalAnalysisContext

router = APIRouter()
logger = logging.getLogger(__name__)
THOMAS_EMAIL = "thomas@karis.demo"


def _get_thomas(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == THOMAS_EMAIL))
    if user is None:
        raise HTTPException(status_code=404, detail="Demo user Thomas is not seeded.")
    return user


def _entry_query():
    return select(JournalEntry).options(
        selectinload(JournalEntry.observations),
        selectinload(JournalEntry.feelings),
        selectinload(JournalEntry.action_items),
        selectinload(JournalEntry.clarifications),
        selectinload(JournalEntry.vocal_signals),
        selectinload(JournalEntry.wearable_windows),
    )


def _journal_response(entry: JournalEntry) -> JournalResponse:
    observations = [
        ObservationResponse(
            id=item.id,
            category=item.category,
            description=item.summary,
            visibility=item.visibility,
            include_in_weekly_report=item.include_in_weekly_report,
        )
        for item in entry.observations
    ]
    feelings = [
        FeelingResponse(
            id=item.id,
            description=item.feeling,
            visibility=item.visibility,
        )
        for item in entry.feelings
    ]
    actions = [
        ActionResponse(
            id=item.id,
            description=item.title,
            status=item.status.value,
            assigned_member_id=item.assignee_id,
        )
        for item in entry.action_items
    ]
    clarifications = [
        ClarificationResponse(
            id=item.id,
            question=item.question,
            reason=item.reason,
            answer=item.answer,
            answered_at=item.answered_at,
        )
        for item in entry.clarifications
    ]
    return JournalResponse(
        id=entry.id,
        care_recipient_id=entry.recipient_id,
        author_user_id=entry.author_id,
        input_type=entry.input_type,
        status=entry.status,
        original_text=entry.original_text,
        transcript=entry.transcript,
        occurred_at=entry.occurred_at,
        finalized_at=entry.finalized_at,
        short_summary=entry.analysis_summary,
        observations=observations,
        caregiver_feelings=feelings,
        actions=actions,
        people_mentioned=entry.people_mentioned or [],
        has_private_data=bool(feelings),
        clarifications=clarifications,
        clarification_needed=any(item.answer is None for item in entry.clarifications),
        audio_object_key=entry.audio_object_key,
        audio_mime_type=entry.audio_mime_type,
        transcription_status=entry.transcription_status,
    )


def _message_response(
    message: GeneratedMessage,
    member: CareCircleMember,
    context: RecipientContext | None,
) -> MessageResponse:
    allowed_count = (
        len(context.allowed_observations) + len(context.allowed_actions)
        if context
        else 0
    )
    structured_count = allowed_count + (context.excluded_private_count if context else 0)
    return MessageResponse(
        id=message.id,
        recipient_member_id=message.recipient_member_id,
        recipient_name=member.user.full_name.split()[0],
        recipient_role=member.role,
        source_entry_id=message.source_entry_id,
        channel=message.channel,
        text=message.text,
        approved=message.approved,
        delivery_status=message.delivery_status.value,
        sent_at=message.sent_at,
        structured_item_count=structured_count,
        allowed_item_count=allowed_count,
        excluded_private_count=context.excluded_private_count if context else 0,
    )


def _context_for_member(entry: JournalEntry, member: CareCircleMember) -> RecipientContext:
    return RecipientContextBuilder().build(entry=entry, member=member)


def _report_response(report: WeeklyReport) -> WeeklyReportResponse:
    return WeeklyReportResponse.model_validate(report, from_attributes=True)


def _analysis_context(entry: JournalEntry) -> str:
    answers = [
        f"Q: {item.question}\nA: {item.answer}"
        for item in entry.clarifications
        if item.answer is not None
    ]
    if not answers:
        return entry.transcript or entry.original_text
    return f"{entry.transcript or entry.original_text}\n\nClarification answers:\n" + "\n".join(answers)


def _owner_analysis_context(entry: JournalEntry, db: Session) -> JournalAnalysisContext:
    multimodal = build_multimodal_context(entry)
    recipient = db.get(CareRecipient, entry.recipient_id)
    author = db.get(User, entry.author_id)
    assert recipient is not None and author is not None
    return JournalAnalysisContext(
        care_recipient_first_name=recipient.first_name,
        caregiver_first_name=author.full_name.split()[0],
        clarification_answers=[
            ClarificationInput(question=item.question, answer=item.answer)
            for item in entry.clarifications if item.answer is not None
        ],
        caregiver_vocal_affect=multimodal.caregiver_vocal_affect,
        caregiver_wearable=multimodal.caregiver_wearable,
        care_recipient_wearable=multimodal.care_recipient_wearable,
    )


def _llm_metadata(result) -> ProviderMetadata:
    return result.provider_metadata or ProviderMetadata(provider_used=result.provider)


def _replace_analysis(
    entry: JournalEntry,
    result: JournalAnalysisResult,
    db: Session,
) -> None:
    db.execute(delete(Observation).where(Observation.entry_id == entry.id))
    db.execute(delete(CaregiverFeeling).where(CaregiverFeeling.entry_id == entry.id))
    db.execute(delete(ActionItem).where(ActionItem.entry_id == entry.id))
    entry.observations.clear()
    entry.feelings.clear()
    entry.action_items.clear()
    entry.analysis_summary = result.short_summary
    entry.people_mentioned = result.people_mentioned
    for item in result.observations:
        entry.observations.append(
            Observation(
                recipient_id=entry.recipient_id,
                category=item.get("category", "general"),
                summary=item.get("description", ""),
                visibility=Visibility.CIRCLE,
                include_in_weekly_report=bool(item.get("include_in_weekly_report", True)),
            )
        )
    for item in result.caregiver_feelings:
        entry.feelings.append(
            CaregiverFeeling(
                caregiver_id=entry.author_id,
                feeling=item.get("description", ""),
                visibility=Visibility.PRIVATE,
            )
        )
    for item in result.actions:
        assignee_id = None
        assignee_name = item.get("assignee_name")
        if assignee_name:
            assignee_id = db.scalar(
                select(User.id)
                .join(CareCircleMember.user)
                .where(
                    CareCircleMember.recipient_id == entry.recipient_id,
                    CareCircleMember.active.is_(True),
                    User.full_name.ilike(f"{assignee_name}%"),
                )
            )
        action_status = item.get("status", "pending")
        if action_status == "todo":
            action_status = "pending"
        entry.action_items.append(
            ActionItem(
                recipient_id=entry.recipient_id,
                title=item.get("description", ""),
                status=ActionStatus(action_status),
                assignee_id=assignee_id,
            )
        )


@router.post("/auth/demo", response_model=UserResponse)
def demo_auth(db: Session = Depends(get_db)) -> UserResponse:
    return UserResponse.model_validate(_get_thomas(db))


@router.get("/me", response_model=UserResponse)
def get_me(db: Session = Depends(get_db)) -> UserResponse:
    return UserResponse.model_validate(_get_thomas(db))


@router.get("/care-recipients", response_model=list[CareRecipientResponse])
def list_recipients(db: Session = Depends(get_db)):
    return list(db.scalars(select(CareRecipient).order_by(CareRecipient.first_name)))


@router.get("/care-recipients/{recipient_id}", response_model=CareRecipientResponse)
def get_recipient(recipient_id: uuid.UUID, db: Session = Depends(get_db)):
    recipient = db.get(CareRecipient, recipient_id)
    if recipient is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")
    return recipient


@router.get("/care-recipients/{recipient_id}/members", response_model=list[MemberResponse])
def list_members(recipient_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(CareRecipient, recipient_id) is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")
    members = db.scalars(
        select(CareCircleMember)
        .where(CareCircleMember.recipient_id == recipient_id)
        .options(selectinload(CareCircleMember.user))
        .order_by(CareCircleMember.created_at)
    )
    return [
        MemberResponse(id=m.id, user_id=m.user_id, name=m.user.full_name, role=m.role, active=m.active)
        for m in members
    ]


@router.post("/journal", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db)) -> JournalResponse:
    _get_thomas(db)
    if db.get(CareRecipient, payload.care_recipient_id) is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")
    entry = JournalEntry(
        recipient_id=payload.care_recipient_id,
        author_id=_get_thomas(db).id,
        input_type=payload.input_type,
        original_text=payload.original_text,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _journal_response(entry)


ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/mp3",
    "audio/wav", "audio/x-wav", "audio/wave",
}


@router.post("/journal/{entry_id}/audio", response_model=AudioUploadResponse)
def upload_audio(
    entry_id: uuid.UUID,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_object_storage_provider),
) -> AudioUploadResponse:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    content_type = (audio.content_type or "").lower().split(";")[0]
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio format.")
    data = audio.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty.")
    try:
        key = storage.put_audio(data=data, content_type=content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Audio storage failed.") from exc
    entry.audio_object_key = key
    entry.audio_mime_type = content_type
    entry.input_type = InputType.VOICE
    entry.transcription_status = "uploaded"
    db.commit()
    return AudioUploadResponse(
        storage_provider=getattr(storage, "provider_name", type(storage).__name__),
        journal_entry_id=entry.id, input_type=entry.input_type,
        audio_mime_type=content_type, audio_object_key=key,
        transcription_status=entry.transcription_status,
    )


@router.post("/journal/{entry_id}/audio/demo", response_model=AudioUploadResponse)
def upload_demo_audio(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_object_storage_provider),
) -> AudioUploadResponse:
    path = Path(__file__).resolve().parents[4] / "samples" / "audio" / "Enregistrement.mp3"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Demo audio not found.")
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    try:
        key = storage.put_audio(data=path.read_bytes(), content_type="audio/mpeg")
    except Exception as exc:
        logger.warning("operation=demo_audio provider=storage status=failed error_type=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="L’audio n’a pas pu être stocké. Votre journal est conservé ; vous pouvez continuer par écrit.") from exc
    entry.audio_object_key = key
    entry.audio_mime_type = "audio/mpeg"
    entry.input_type = InputType.VOICE
    entry.transcription_status = "uploaded"
    db.commit()
    return AudioUploadResponse(
        storage_provider=getattr(storage, "provider_name", type(storage).__name__),
        journal_entry_id=entry.id, input_type=entry.input_type,
        audio_mime_type="audio/mpeg", audio_object_key=key,
        transcription_status="uploaded",
    )


@router.post("/journal/{entry_id}/transcribe", response_model=TranscriptResponse)
def transcribe_journal(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    transcription: TranscriptionProvider = Depends(get_transcription_provider),
) -> TranscriptResponse:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if not entry.audio_object_key:
        raise HTTPException(status_code=409, detail="No audio is attached to this entry.")
    entry.transcription_status = "processing"
    db.commit()
    started = time.monotonic()
    try:
        result = transcription.transcribe(audio_object_key=entry.audio_object_key)
    except Exception as exc:
        entry.transcription_status = "failed"
        db.commit()
        logger.warning("operation=transcription status=failed error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="La transcription n’a pas abouti. Votre journal est conservé ; vous pouvez réessayer ou continuer avec la note de démonstration.",
        ) from exc
    entry.transcript = result.text
    entry.transcription_status = "completed"
    entry.transcription_duration_ms = int((time.monotonic() - started) * 1000)
    db.commit()
    return TranscriptResponse(
        journal_entry_id=entry.id, transcript=result.text, language=result.language,
        provider=result.provider, transcription_status=entry.transcription_status,
    )


@router.patch("/journal/{entry_id}", response_model=JournalResponse)
def patch_journal(
    entry_id: uuid.UUID,
    payload: TranscriptPatch,
    db: Session = Depends(get_db),
) -> JournalResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if entry.input_type != InputType.VOICE or entry.status == JournalStatus.FINALIZED:
        raise HTTPException(status_code=409, detail="Only an editable voice transcript can be changed.")
    entry.transcript = payload.transcript
    db.commit()
    refreshed = db.scalar(_entry_query().where(JournalEntry.id == entry.id))
    assert refreshed is not None
    return _journal_response(refreshed)


@router.get("/journal/{entry_id}", response_model=JournalResponse)
def get_journal(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> JournalResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    return _journal_response(entry)


@router.post("/journal/{entry_id}/analyze", response_model=JournalResponse)
def analyze_journal(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> JournalResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if entry.status == JournalStatus.FINALIZED:
        raise HTTPException(status_code=409, detail="Finalized entries cannot be re-analyzed.")

    result: JournalAnalysisResult = llm.analyze_journal(
        text=_analysis_context(entry), context=_owner_analysis_context(entry, db),
    )
    db.execute(delete(Clarification).where(Clarification.entry_id == entry.id))
    entry.clarifications.clear()
    _replace_analysis(entry, result, db)
    for question, reason in zip(result.questions[:3], result.clarification_reasons[:3]):
        entry.clarifications.append(
            Clarification(question=question, reason=reason)
        )
    entry.status = JournalStatus.ANALYZED
    db.commit()
    refreshed = db.scalar(_entry_query().where(JournalEntry.id == entry.id))
    assert refreshed is not None
    response = _journal_response(refreshed)
    response.provider_metadata = _llm_metadata(result)
    return response


@router.post("/journal/{entry_id}/clarifications", response_model=JournalResponse)
def submit_clarifications(
    entry_id: uuid.UUID,
    payload: ClarificationSubmission,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> JournalResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if entry.status != JournalStatus.ANALYZED or not entry.clarifications:
        raise HTTPException(status_code=409, detail="Entry is not awaiting clarification.")
    by_id = {item.id: item for item in entry.clarifications}
    for answer in payload.answers:
        clarification = by_id.get(answer.clarification_id)
        if clarification is None:
            raise HTTPException(status_code=400, detail="Clarification does not belong to this entry.")
        clarification.answer = answer.answer
        clarification.answered_at = datetime.now(timezone.utc)
    if any(item.answer is None for item in entry.clarifications):
        db.commit()
        refreshed = db.scalar(_entry_query().where(JournalEntry.id == entry.id))
        assert refreshed is not None
        return _journal_response(refreshed)
    # Persist the user's answers before an optional live call can fail.
    db.commit()
    result = llm.analyze_journal(
        text=_analysis_context(entry), context=_owner_analysis_context(entry, db),
    )
    _replace_analysis(entry, result, db)
    db.commit()
    refreshed = db.scalar(_entry_query().where(JournalEntry.id == entry.id))
    assert refreshed is not None
    response = _journal_response(refreshed)
    response.provider_metadata = _llm_metadata(result)
    return response


@router.post("/journal/{entry_id}/finalize", response_model=JournalResponse)
def finalize_journal(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> JournalResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if entry.status != JournalStatus.ANALYZED:
        raise HTTPException(status_code=409, detail="Journal entry must be analyzed before finalization.")
    entry.finalize()
    db.commit()
    refreshed = db.scalar(_entry_query().where(JournalEntry.id == entry.id))
    assert refreshed is not None
    return _journal_response(refreshed)


@router.post(
    "/journal/{entry_id}/multimodal/enrich",
    response_model=MultimodalContextResponse,
)
def enrich_multimodal(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    ser: SpeechEmotionProvider = Depends(get_ser_provider),
    wearable: WearableProvider = Depends(get_wearable_provider),
) -> MultimodalContextResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    thomas = _get_thomas(db)
    try:
        ser_result = ser.analyze(audio_object_key=entry.audio_object_key or str(entry.id))
    except Exception as exc:
        logger.warning("operation=ser status=unavailable error_type=%s", type(exc).__name__)
        ser_result = None
    if ser_result is not None:
        entry.vocal_signals.clear()
        db.flush()
        entry.vocal_signals.append(
            VocalAffectSignal(
                caregiver_id=thomas.id,
                valence=ser_result.valence,
                arousal=ser_result.arousal,
                top_label=ser_result.top_label,
                confidence=ser_result.confidence,
                quality=ser_result.quality,
                model_version=ser_result.model_version,
                provider=ser_result.provider,
                visibility=Visibility.PRIVATE,
            )
        )
    results = []
    for subject, subject_id in ((SubjectType.CAREGIVER, thomas.id), (SubjectType.CARE_RECIPIENT, entry.recipient_id)):
        try:
            results.append(wearable.summarize(subject_type=subject.value, subject_id=str(subject_id), around=entry.occurred_at))
        except Exception as exc:
            logger.warning("operation=wearable subject=%s status=unavailable error_type=%s", subject.value, type(exc).__name__)
    for result in results:
        if result is None:
            continue
        subject_type = SubjectType(result.subject_type)
        for previous in list(entry.wearable_windows):
            if previous.subject_type == subject_type:
                entry.wearable_windows.remove(previous)
        db.flush()
        visibility = (
            Visibility.PRIVATE
            if subject_type == SubjectType.CAREGIVER
            else Visibility.CIRCLE
        )
        metrics = {
            **result.metrics,
            "quality": result.quality,
            "provider": result.provider,
        }
        entry.wearable_windows.append(
            WearableWindow(
                subject_type=subject_type,
                subject_id=uuid.UUID(result.subject_id),
                window_start=result.window_start,
                window_end=result.window_end,
                metrics=metrics,
                visibility=visibility,
            )
        )
    db.commit()
    refreshed = db.scalar(_entry_query().where(JournalEntry.id == entry.id))
    assert refreshed is not None
    return MultimodalContextResponse.model_validate(
        build_multimodal_context(refreshed).model_dump()
    )


@router.get(
    "/journal/{entry_id}/multimodal-context",
    response_model=MultimodalContextResponse,
)
def get_multimodal_context(
    entry_id: uuid.UUID, db: Session = Depends(get_db)
) -> MultimodalContextResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    return MultimodalContextResponse.model_validate(
        build_multimodal_context(entry).model_dump()
    )


@router.post(
    "/journal/{entry_id}/messages/generate",
    response_model=MessageGenerationResponse,
)
def generate_messages(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> MessageGenerationResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if entry.status not in {JournalStatus.ANALYZED, JournalStatus.FINALIZED}:
        raise HTTPException(
            status_code=409,
            detail="Entry must be analyzed or finalized before sharing.",
        )
    members = list(
        db.scalars(
            select(CareCircleMember)
            .where(CareCircleMember.recipient_id == entry.recipient_id)
            .options(selectinload(CareCircleMember.user))
            .order_by(CareCircleMember.created_at)
        )
    )
    contexts = RoutingService(privacy=PrivacyService()).contexts_for_entry(
        entry=entry, members=members
    )
    members_by_user = {member.user_id: member for member in members}
    service = MessageGenerationService(llm)
    drafts: list[MessageResponse] = []
    for context in contexts:
        metadata = None
        member = members_by_user[context.recipient_id]
        message = db.scalar(
            select(GeneratedMessage).where(
                GeneratedMessage.source_entry_id == entry.id,
                GeneratedMessage.recipient_member_id == member.id,
            )
        )
        if message is None:
            draft = service.generate(context)
            metadata = _llm_metadata(draft)
            message = GeneratedMessage(
                recipient_member_id=member.id,
                source_entry_id=entry.id,
                channel=draft.channel,
                text=draft.text,
            )
            db.add(message)
            db.flush()
        elif message.delivery_status != DeliveryStatus.SENT:
            draft = service.generate(context)
            metadata = _llm_metadata(draft)
            message.channel = draft.channel
            message.text = draft.text
            message.approved = False
            message.delivery_status = DeliveryStatus.DRAFT
        response = _message_response(message, member, context)
        response.provider_metadata = metadata
        shareable = sum(item.visibility != Visibility.PRIVATE for item in entry.observations) + len(entry.action_items)
        response.privacy_pipeline = PrivacyPipeline(
            structured_count=len(entry.observations) + len(entry.action_items) + len(entry.feelings) + len(entry.vocal_signals) + len(entry.wearable_windows),
            shareable_count=shareable,
            authorized_count=len(context.source_item_ids),
            transmitted_count=len(context.source_item_ids),
        )
        drafts.append(response)
    db.commit()
    return MessageGenerationResponse(drafts=drafts)


@router.get("/journal/{entry_id}/messages", response_model=MessageGenerationResponse)
def get_messages(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> MessageGenerationResponse:
    """Read saved drafts without regenerating or resetting user approvals."""
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    rows = db.execute(select(GeneratedMessage, CareCircleMember).join(
        CareCircleMember, CareCircleMember.id == GeneratedMessage.recipient_member_id,
    ).where(GeneratedMessage.source_entry_id == entry.id).options(selectinload(CareCircleMember.user))).all()
    drafts = []
    for message, member in rows:
        if not member.active:
            continue
        context = _context_for_member(entry, member)
        response = _message_response(message, member, context)
        response.privacy_pipeline = PrivacyPipeline(
            structured_count=len(entry.observations) + len(entry.action_items) + len(entry.feelings) + len(entry.vocal_signals) + len(entry.wearable_windows),
            shareable_count=sum(item.visibility != Visibility.PRIVATE for item in entry.observations) + len(entry.action_items),
            authorized_count=len(context.source_item_ids), transmitted_count=len(context.source_item_ids),
        )
        drafts.append(response)
    return MessageGenerationResponse(drafts=drafts)


@router.patch("/messages/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: uuid.UUID,
    payload: MessagePatch,
    db: Session = Depends(get_db),
) -> MessageResponse:
    message = db.get(GeneratedMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    member = db.scalar(
        select(CareCircleMember)
        .where(CareCircleMember.id == message.recipient_member_id)
        .options(selectinload(CareCircleMember.user))
    )
    if member is None or not member.active:
        raise HTTPException(status_code=409, detail="Recipient is not an active care-circle member.")
    if message.delivery_status == DeliveryStatus.SENT:
        raise HTTPException(status_code=409, detail="A sent message cannot be edited.")
    if payload.edited_text is not None:
        message.text = payload.edited_text
        message.approved = False
        message.delivery_status = DeliveryStatus.DRAFT
    if payload.enabled is False or payload.approved is False:
        message.approved = False
        message.delivery_status = DeliveryStatus.DRAFT
    if payload.approved is True:
        message.approve()
    entry = (
        db.scalar(_entry_query().where(JournalEntry.id == message.source_entry_id))
        if message.source_entry_id
        else None
    )
    context = _context_for_member(entry, member) if entry else None
    db.commit()
    return _message_response(message, member, context)


@router.post(
    "/journal/{entry_id}/messages/send",
    response_model=MessageGenerationResponse,
)
def send_messages(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    messaging: MessagingProvider = Depends(get_messaging_provider),
) -> MessageGenerationResponse:
    entry = db.scalar(_entry_query().where(JournalEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    messages = list(
        db.scalars(
            select(GeneratedMessage)
            .where(GeneratedMessage.source_entry_id == entry.id)
        )
    )
    members = {
        member.id: member
        for member in db.scalars(
            select(CareCircleMember)
            .where(CareCircleMember.recipient_id == entry.recipient_id)
            .options(selectinload(CareCircleMember.user))
        )
    }
    result: list[MessageResponse] = []
    for message in messages:
        member = members.get(message.recipient_member_id)
        if member is None or not member.active:
            continue
        if message.approved and message.delivery_status == DeliveryStatus.APPROVED:
            try:
                messaging.send(channel=message.channel, recipient=member.user.full_name, text=message.text)
            except Exception as exc:
                db.commit()  # completed deliveries remain sent; failed draft stays approved
                logger.warning("operation=messaging status=failed error_type=%s", type(exc).__name__)
                raise HTTPException(status_code=502, detail="L’envoi n’a pas abouti. Vos messages restent disponibles pour réessayer.") from exc
            message.mark_sent()
        context = _context_for_member(entry, member)
        result.append(_message_response(message, member, context))
    db.commit()
    return MessageGenerationResponse(drafts=result)


@router.get("/messages/mock-inbox", response_model=MockInboxResponse)
def mock_inbox(db: Session = Depends(get_db)) -> MockInboxResponse:
    rows = db.execute(
        select(GeneratedMessage, CareCircleMember)
        .join(CareCircleMember, CareCircleMember.id == GeneratedMessage.recipient_member_id)
        .where(GeneratedMessage.delivery_status == DeliveryStatus.SENT)
        .options(selectinload(CareCircleMember.user))
        .order_by(GeneratedMessage.sent_at.desc())
    ).all()
    return MockInboxResponse(
        messages=[
            MockInboxItem(
                id=message.id,
                recipient_name=member.user.full_name,
                recipient_role=member.role,
                channel=message.channel,
                text=message.text,
                delivery_status=message.delivery_status.value,
                sent_at=message.sent_at,
            )
            for message, member in rows
            if message.sent_at is not None
        ]
    )


@router.post(
    "/care-recipients/{recipient_id}/reports/weekly/generate",
    response_model=WeeklyReportResponse,
)
def generate_weekly_report(
    recipient_id: uuid.UUID,
    payload: WeeklyReportGenerate,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> WeeklyReportResponse:
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=422, detail="Period end must be after period start.")
    if db.get(CareRecipient, recipient_id) is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")
    aggregator = ReportAggregationService(db)
    context = aggregator.build(
        recipient_id=recipient_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    report = db.scalar(
        select(WeeklyReport).where(
            WeeklyReport.recipient_id == recipient_id,
            WeeklyReport.period_start == payload.period_start,
            WeeklyReport.period_end == payload.period_end,
        )
    )
    draft = WeeklyReportService(llm).generate(context)
    if report is None:
        report = WeeklyReport(
            recipient_id=recipient_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
        db.add(report)
    report.title = draft.title
    report.content = draft.markdown
    report.approved = False
    report.approved_at = None
    report.source_entry_count = context.source_entry_count
    report.structured_item_count = context.structured_item_count
    report.reportable_item_count = context.reportable_item_count
    report.excluded_private_count = context.excluded_private_count
    db.commit()
    db.refresh(report)
    response = _report_response(report)
    response.provider_metadata = _llm_metadata(draft)
    return response


@router.get(
    "/care-recipients/{recipient_id}/reports",
    response_model=list[WeeklyReportResponse],
)
def list_reports(recipient_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(CareRecipient, recipient_id) is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")
    return list(
        db.scalars(
            select(WeeklyReport)
            .where(WeeklyReport.recipient_id == recipient_id)
            .order_by(WeeklyReport.period_end.desc())
        )
    )


@router.get("/reports/{report_id}", response_model=WeeklyReportResponse)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Weekly report not found.")
    return _report_response(report)


@router.patch("/reports/{report_id}", response_model=WeeklyReportResponse)
def edit_report(
    report_id: uuid.UUID,
    payload: WeeklyReportPatch,
    db: Session = Depends(get_db),
):
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Weekly report not found.")
    if report.approved:
        raise HTTPException(status_code=409, detail="Approved reports cannot be edited.")
    report.content = payload.edited_markdown
    db.commit()
    db.refresh(report)
    return _report_response(report)


@router.post("/reports/{report_id}/approve", response_model=WeeklyReportResponse)
def approve_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Weekly report not found.")
    report.approved = True
    report.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return _report_response(report)


@router.get("/care-recipients/{recipient_id}/timeline", response_model=TimelineResponse)
def timeline(recipient_id: uuid.UUID, db: Session = Depends(get_db)) -> TimelineResponse:
    if db.get(CareRecipient, recipient_id) is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")
    entries = db.scalars(
        _entry_query()
        .where(
            JournalEntry.recipient_id == recipient_id,
            JournalEntry.status == JournalStatus.FINALIZED,
        )
        .order_by(JournalEntry.occurred_at.desc())
    )
    items = [
        TimelineItem(
            id=entry.id,
            date=entry.occurred_at,
            short_summary=entry.analysis_summary or entry.original_text,
            observations=[
                ObservationResponse(
                    id=item.id,
                    category=item.category,
                    description=item.summary,
                    visibility=item.visibility,
                    include_in_weekly_report=item.include_in_weekly_report,
                )
                for item in entry.observations
            ],
            actions=[
                ActionResponse(id=item.id, description=item.title, status=item.status.value)
                for item in entry.action_items
            ],
            source_type=entry.input_type,
            has_private_data=bool(entry.feelings),
        )
        for entry in entries
    ]
    return TimelineResponse(care_recipient_id=recipient_id, items=items)
