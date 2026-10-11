"""Deterministic mock wearable provider for M5."""

from datetime import datetime, timedelta

from ..base import WearableSummary


class MockWearableProvider:
    def summarize(
        self, *, subject_type: str, subject_id: str, around: datetime
    ) -> WearableSummary | None:
        caregiver = subject_type == "caregiver"
        return WearableSummary(
            subject_type=subject_type,
            subject_id=subject_id,
            window_start=around - timedelta(hours=1),
            window_end=around,
            metrics=(
                {
                    "heart_rate_avg_bpm": 91,
                    "coverage_pct": 92,
                }
                if caregiver
                else {
                    "heart_rate_avg_bpm": 74,
                    "steps_total": 1320,
                    "coverage_pct": 88,
                }
            ),
            quality="good",
            visibility="private" if caregiver else "circle",
            provider="mock-wearables",
        )
