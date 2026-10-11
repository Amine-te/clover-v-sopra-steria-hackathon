"""Deterministic mock messaging provider — never sends anything externally."""

from ..base import DeliveryReceipt


class MockMessagingProvider:
    def send(self, *, channel: str, recipient: str, text: str) -> DeliveryReceipt:
        return DeliveryReceipt(
            channel=channel,
            recipient=recipient,
            status="sent",
        )
