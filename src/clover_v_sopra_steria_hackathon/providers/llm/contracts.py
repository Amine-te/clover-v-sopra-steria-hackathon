"""Strict live-LLM extraction contracts and deterministic domain validation."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...domain.multimodal import VocalAffectContext, WearableContext


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ClarificationInput(StrictModel):
    question: str
    answer: str


class JournalAnalysisContext(StrictModel):
    care_recipient_first_name: str
    caregiver_first_name: str
    clarification_answers: list[ClarificationInput] = Field(default_factory=list)
    caregiver_vocal_affect: VocalAffectContext | None = None
    caregiver_wearable: WearableContext | None = None
    care_recipient_wearable: WearableContext | None = None


class AnalysisObservation(StrictModel):
    category: Literal[
        "fatigue", "nutrition", "medication", "sleep", "appointment", "general",
        "practical", "administrative", "logistics", "mood",
    ]
    description: str = Field(min_length=1)
    subject: Literal["care_recipient"] = "care_recipient"
    source_confidence: Literal["reported", "clarified", "uncertain"] = "reported"
    importance: Literal["low", "medium", "high"] = "low"
    include_in_weekly_report: bool = True


class AnalysisFeeling(StrictModel):
    description: str = Field(min_length=1)
    visibility: Literal["private"] = "private"


class AnalysisAction(StrictModel):
    description: str = Field(min_length=1)
    status: Literal["pending", "todo", "done", "cancelled"] = "pending"
    assignee_name: str | None = None


class JournalEntryAnalysis(StrictModel):
    short_summary: str = Field(min_length=1)
    observations: list[AnalysisObservation]
    caregiver_feelings: list[AnalysisFeeling]
    actions: list[AnalysisAction]
    people_mentioned: list[str]
    clarification_needed: bool
    questions: list[str] = Field(max_length=3)
    clarification_reasons: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def domain_rules(self) -> Self:
        if self.clarification_needed != bool(self.questions):
            raise ValueError("Clarification flag must match questions")
        if len(self.questions) != len(self.clarification_reasons):
            raise ValueError("Each question requires a reason")
        if any(not value.strip() for value in self.questions + self.clarification_reasons):
            raise ValueError("Questions and reasons cannot be empty")
        for observation in self.observations:
            if observation.category == "medication":
                if "traitement déclaré comme pris" not in observation.description.casefold():
                    raise ValueError("Medication must remain reported, not inferred adherence")
                if observation.source_confidence != "reported":
                    raise ValueError("Medication remains reported")
        return self


class MessageOutput(StrictModel):
    text: str = Field(min_length=1, max_length=2000)


class ReportOutput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    markdown: str = Field(min_length=1, max_length=20000)
