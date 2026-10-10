# Open questions

Decisions the team still has to make. Move each answer into the relevant spec when settled.

| # | Question | Affects | Default until decided |
| --- | --- | --- | --- |
| 1 | Do follow-up questions appear in the app or by SMS? | 003, 008, 010 | In the app |
| 2 | Which notification channel is real: SMS (SNS), email (SES) or Telegram? | 005, 008 | Mock channel shown in the UI |
| 3 | Whose wearable data goes in the report: the cared-for person's only? | 007, 011 | Cared-for person's, simulated |
| 4 | Do the Claude models need inference profile IDs to be invoked? | 000 | Test one call per model in foundations |
| 5 | Are EventBridge, Lambda and AgentCore permissions available? | 008, 012 | APScheduler and a demo button; AgentCore shown as target |
| 6 | Who owns each feature? | all | Fill in `README.md` index |
| 7 | Hackathon dates and demo slot | all | Unknown; build order only |
| 8 | SNS SMS sandbox and origination: available or not? | 005 | Mock channel; fall back to SES email or Telegram |
| 9 | Transcribe quality on emotional or informal French speech | 001, 002 | Test with real audio early; keep cached transcripts for the demo |
| 10 | Which categories are on the daily completeness checklist? | 003 | sleep, meals\_hydration, medication, mood\_behavior (confirm with team) |
| 11 | Follow-up answers: voice, tap, or both? | 003, 010 | In-app text or tap; voice re-transcription optional |
| 12 | Charts for wearable data (sleep, heart rate) in the report? | 007 | Text only for first version; charts added if time allows |
| 13 | Notify a relief contact after repeated low-engagement signals? | 011 | No automatic notification in first version |
