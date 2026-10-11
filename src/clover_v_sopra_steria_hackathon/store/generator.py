"""Deterministic generator of fictional demo data: 30 days of Observations and WearableSamples.

Given a seed, `generate` returns the same data every time (constitution rule 8: consistent demo
data). Every person and identifier is invented (constitution rule 6: fictional data only).
`seed_store` writes the generated Observations through a TimelineStore.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..models import Observation, WearableSample
from .service import TimelineStore

__all__ = ["SyntheticData", "generate", "seed_store"]

DEFAULT_SUBJECT_ID = "subject-demo-1"
DEFAULT_REPORTER_ID = "caregiver-demo-1"
DEFAULT_DAYS = 30
DEFAULT_SEED = 42

# Fictional caregiver-voice observations, grouped by category, with a severity hint.
_OBSERVATION_TEMPLATES: list[tuple[str, str, str]] = [
    ("sleep", "A bien dormi cette nuit", "info"),
    ("sleep", "Réveils fréquents pendant la nuit", "watch"),
    ("meals_hydration", "A pris un petit-déjeuner complet", "info"),
    ("meals_hydration", "A peu bu dans la journée", "watch"),
    ("medication", "A pris son traitement du matin", "info"),
    ("medication", "A refusé son traitement du soir", "watch"),
    ("mood_behavior", "Humeur calme et souriante", "info"),
    ("mood_behavior", "Agitation en fin de journée", "watch"),
    ("mobility_falls", "Marche aidée jusqu'au salon", "info"),
    ("mobility_falls", "Chute sans gravité près du lit", "urgent"),
    ("pain", "Aucune douleur signalée", "info"),
    ("pain", "Douleur au genou gauche signalée", "watch"),
    ("vitals", "Tension prise, valeurs habituelles", "info"),
    ("appointment", "Rendez-vous chez le médecin confirmé", "info"),
    ("logistics", "Courses livrées à domicile", "info"),
]

_SPAN_PREFIX = "note de l'aidant : "
_SLEEP_STATES = ["awake", "light", "deep"]


@dataclass
class SyntheticData:
    """The generated fictional data: Observations and matching WearableSamples."""

    observations: list[Observation]
    wearables: list[WearableSample]


def generate(
    subject_id: str = DEFAULT_SUBJECT_ID,
    reporter_id: str = DEFAULT_REPORTER_ID,
    days: int = DEFAULT_DAYS,
    end: Optional[datetime] = None,
    seed: int = DEFAULT_SEED,
) -> SyntheticData:
    """Return `days` days of fictional Observations and WearableSamples ending at `end` (UTC now)."""
    rng = random.Random(seed)
    end = (end or datetime.now(timezone.utc)).astimezone(timezone.utc)
    window_start = end - timedelta(days=days - 1)

    observations: list[Observation] = []
    wearables: list[WearableSample] = []

    for day_offset in range(days):
        day = (window_start + timedelta(days=day_offset)).date()
        observations.extend(_day_observations(rng, day, subject_id, reporter_id))
        wearables.extend(_day_wearables(rng, day, subject_id))

    return SyntheticData(observations=observations, wearables=wearables)


def seed_store(store: TimelineStore, data: SyntheticData) -> list[str]:
    """Write every Observation in `data` through the store; return the keys written."""
    return store.save_many(data.observations)


# Internals


def _day_observations(
    rng: random.Random, day, subject_id: str, reporter_id: str
) -> list[Observation]:
    """Three to five fictional observations spread across the day."""
    count = rng.randint(3, 5)
    templates = rng.sample(_OBSERVATION_TEMPLATES, count)
    observations: list[Observation] = []
    for index, (category, value, severity) in enumerate(templates):
        hour = 7 + rng.randint(0, 14)
        minute = rng.randint(0, 59)
        timestamp = datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)
        reported_at = datetime(day.year, day.month, day.day, 20, 5, tzinfo=timezone.utc)
        observations.append(
            Observation(
                id=f"obs-{day.isoformat()}-{index}",
                timestamp=timestamp,
                reported_at=reported_at,
                subject_id=subject_id,
                category=category,
                value=value,
                severity=severity,
                source="caregiver_voice",
                reported_by=reporter_id,
                confidence=round(rng.uniform(0.7, 0.98), 2),
                transcript_span=_SPAN_PREFIX + value.lower(),
            )
        )
    return observations


def _day_wearables(rng: random.Random, day, subject_id: str) -> list[WearableSample]:
    """Four fictional bracelet readings across the day (heart rate, sleep state, spo2, steps)."""
    samples: list[WearableSample] = []
    for hour in (2, 8, 14, 20):
        timestamp = datetime(day.year, day.month, day.day, hour, 0, tzinfo=timezone.utc)
        samples.append(
            WearableSample(
                timestamp=timestamp,
                subject_id=subject_id,
                heart_rate_bpm=rng.randint(55, 95),
                sleep_state=rng.choice(_SLEEP_STATES) if hour == 2 else None,
                spo2_pct=round(rng.uniform(94.0, 99.0), 1),
                steps=rng.randint(0, 600),
            )
        )
    return samples
