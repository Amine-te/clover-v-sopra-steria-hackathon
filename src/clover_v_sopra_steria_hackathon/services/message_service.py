"""Recipient message generation from already-authorized contexts."""

from ..domain.privacy import RecipientContext
from ..providers.base import LLMProvider, RecipientMessageDraft


class MessageGenerationService:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate(self, context: RecipientContext) -> RecipientMessageDraft:
        # Only this allowlisted Pydantic object crosses the LLM boundary.
        return self.llm.generate_recipient_message(
            recipient_name=context.recipient_name,
            context=context.model_dump(mode="json"),
        )
