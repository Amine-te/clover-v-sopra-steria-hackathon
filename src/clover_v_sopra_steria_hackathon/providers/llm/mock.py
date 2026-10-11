"""Deterministic mock LLM provider for the M3 text journal slice."""

from typing import Any

from ..base import JournalAnalysisResult, RecipientMessageDraft, WeeklyReportDraft
from .contracts import JournalAnalysisContext


class MockLLMProvider:
    def analyze_journal(
        self, *, text: str, context: JournalAnalysisContext | None = None
    ) -> JournalAnalysisResult:
        demo_sentence = (
            "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement "
            "mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis "
            "vraiment crevé."
        )
        clarified = "Clarification answers:" in text
        if text.strip().startswith(demo_sentence) and clarified:
            fatigue_clarified = (
                "Cette fatigue était-elle plus importante que d’habitude ?\nA: Oui"
                in text
            )
            coordination_requested = (
                "Souhaitez-vous que Sophie vérifie l’alimentation lors de sa visite ce soir ?\nA: Oui"
                in text
            )
            return JournalAnalysisResult(
                short_summary=(
                    "Marie semble plus fatiguée aujourd’hui, a peu mangé et son "
                    "traitement a été déclaré comme pris. Sophie doit passer ce soir."
                ),
                observations=[
                    {
                        "category": "fatigue",
                        "description": (
                            "Marie était plus fatiguée que d’habitude aujourd’hui"
                            if fatigue_clarified
                            else "Marie était plus fatiguée aujourd’hui"
                        ),
                        "source_confidence": "clarified" if fatigue_clarified else "reported",
                        "importance": "medium",
                        "include_in_weekly_report": True,
                    },
                    {
                        "category": "nutrition",
                        "description": "Marie a très peu mangé aujourd’hui",
                        "source_confidence": "reported",
                        "importance": "medium",
                        "include_in_weekly_report": True,
                    },
                    {
                        "category": "medication",
                        "description": "Traitement déclaré comme pris",
                        "source_confidence": "reported",
                        "importance": "low",
                        "include_in_weekly_report": True,
                    },
                ],
                caregiver_feelings=[
                    {
                        "description": "Thomas se dit vraiment fatigué",
                        "visibility": "private",
                    }
                ],
                actions=(
                    [{
                        "description": "Sophie vérifie l’alimentation lors de sa visite ce soir",
                        "status": "todo",
                        "assignee_name": "Sophie",
                    }]
                    if coordination_requested
                    else []
                ),
                people_mentioned=["Sophie"],
            )
        if text.strip() == demo_sentence:
            return JournalAnalysisResult(
                short_summary=(
                    "Marie semble plus fatiguée aujourd’hui, a peu mangé et son "
                    "traitement a été déclaré comme pris. Sophie doit passer ce soir."
                ),
                observations=[
                    {"category": "fatigue", "description": "Marie était plus fatiguée aujourd’hui", "source_confidence": "reported", "importance": "medium", "include_in_weekly_report": True},
                    {"category": "nutrition", "description": "Marie a très peu mangé aujourd’hui", "source_confidence": "reported", "importance": "medium", "include_in_weekly_report": True},
                    {"category": "medication", "description": "Traitement déclaré comme pris", "source_confidence": "reported", "importance": "low", "include_in_weekly_report": True},
                ],
                caregiver_feelings=[{"description": "Thomas se dit vraiment fatigué", "visibility": "private"}],
                actions=[{"description": "Sophie passe ce soir", "status": "pending"}],
                people_mentioned=["Sophie"],
                clarification_needed=True,
                questions=[
                    "Cette fatigue était-elle plus importante que d’habitude ?",
                    "Souhaitez-vous que Sophie vérifie l’alimentation lors de sa visite ce soir ?",
                ],
                clarification_reasons=[
                    "Préciser si la fatigue est inhabituelle.",
                    "Transformer une observation en action de coordination si souhaité.",
                ],
            )
        if text.strip() == "Maman n’était vraiment pas bien aujourd’hui.":
            return JournalAnalysisResult(
                short_summary="Une précision est utile pour comprendre la journée de Marie.",
                clarification_needed=True,
                questions=["Qu’avez-vous remarqué exactement ?"],
                clarification_reasons=["Éviter d’inventer des symptômes et recueillir un fait précis."],
            )
        lowered = text.lower()
        if "kiné" in lowered and ("annulé" in lowered or "annule" in lowered):
            return JournalAnalysisResult(
                short_summary="Le rendez-vous de kinésithérapie a été annulé.",
                observations=[
                    {
                        "category": "appointment",
                        "description": "Rendez-vous de kinésithérapie annulé",
                        "source_confidence": "reported",
                        "importance": "medium",
                        "include_in_weekly_report": True,
                    }
                ],
                actions=[
                    {
                        "description": "Marc doit reprendre rendez-vous",
                        "status": "pending",
                        "assignee_name": "Marc",
                    }
                ],
                people_mentioned=["Marc"],
            )
        return JournalAnalysisResult(
            short_summary=f"Note de la journée ({len(text)} caractères).",
            observations=[
                {
                    "category": "general",
                    "description": text.strip(),
                    "source_confidence": "reported",
                    "importance": "low",
                    "include_in_weekly_report": True,
                }
            ],
        )

    def generate_recipient_message(
        self, *, recipient_name: str, context: dict[str, Any]
    ) -> RecipientMessageDraft:
        observations = context.get("allowed_observations", [])
        actions = context.get("allowed_actions", [])
        descriptions = [item["description"] for item in observations]
        action_descriptions = [item["description"] for item in actions]
        if recipient_name == "Sophie" and descriptions:
            fatigue = next((item for item in descriptions if "fatiguée" in item), None)
            nutrition = next((item for item in descriptions if "mangé" in item), None)
            action = next((item for item in action_descriptions if "alimentation" in item), None)
            parts = ["Bonjour Sophie,"]
            if fatigue:
                parts.append(fatigue.rstrip("."))
            if nutrition:
                parts.append(
                    f"et {nutrition.removeprefix('Marie ').lower().rstrip('.')}."
                    if nutrition.startswith("Marie a ")
                    else nutrition
                )
            if action:
                parts.append("Comme tu passes ce soir, peux-tu vérifier comment se passe son repas ?")
            return RecipientMessageDraft(recipient=recipient_name, text=" ".join(parts))
        if recipient_name == "Marc":
            return RecipientMessageDraft(
                recipient=recipient_name,
                text="Bonjour Marc, le rendez-vous de kinésithérapie a été annulé. Peux-tu reprendre rendez-vous ?",
            )
        if descriptions or action_descriptions:
            facts = descriptions + action_descriptions
            return RecipientMessageDraft(
                recipient=recipient_name,
                text=f"Bonjour {recipient_name}, " + " ".join(facts) + ".",
            )
        return RecipientMessageDraft(
            recipient=recipient_name,
            text=f"[mock] Message de suivi pour {recipient_name}.",
        )

    def generate_weekly_report(
        self, *, context: dict[str, Any]
    ) -> WeeklyReportDraft:
        recurring = context.get("recurring_observations", {})
        nutrition = recurring.get("nutrition", {})
        sleep = recurring.get("sleep", {})
        nutrition_count = nutrition.get("count", 0)
        sleep_count = sleep.get("count", 0)
        nutrition_text = (
            f"Une faible alimentation a été rapportée à {self._french_count(nutrition_count)} reprises"
            + (
                f" entre {self._weekday(nutrition.get('dates', [])[0])} et "
                f"{self._weekday(nutrition.get('dates', [])[-1])}."
                if len(nutrition.get("dates", [])) > 1
                else "."
            )
            if nutrition_count
            else "Aucune observation de faible alimentation n'a été rapportée."
        )
        sleep_text = (
            f"{self._french_count(sleep_count).capitalize()} nuits perturbées ont été rapportées."
            if sleep_count
            else "Aucune nuit perturbée n'a été rapportée."
        )
        appointments = [
            item["description"]
            for item in context.get("observations_by_category", {}).get("appointment", [])
        ]
        completed = context.get("completed_actions", [])
        pending = context.get("pending_actions", [])
        sections = [
            f"## Alimentation\n\n{nutrition_text}",
            f"## Sommeil\n\n{sleep_text}",
        ]
        if appointments:
            sections.append("## Organisation\n\n" + " ".join(appointments) + ".")
        if completed or pending:
            sections.append(
                "## Actions\n\n"
                + (f"Terminée : {completed[0]['description']}.\n" if completed else "")
                + (f"À suivre : {pending[0]['description']}." if pending else "")
            )
        medication = context.get("medication_reported", [])
        if medication:
            sections.append(
                "## Traitement\n\n"
                + " ".join(
                    f"Le traitement a été déclaré comme pris le {item['date']}."
                    for item in medication
                )
            )
        return WeeklyReportDraft(
            title=f"Semaine de {context.get('care_recipient_name', 'Marie')}",
            markdown="\n\n".join(sections),
        )

    @staticmethod
    def _french_count(count: int) -> str:
        return {1: "une", 2: "deux", 3: "trois", 4: "quatre"}.get(count, str(count))

    @staticmethod
    def _weekday(value: str) -> str:
        from datetime import date

        names = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        return names[date.fromisoformat(value).weekday()]
