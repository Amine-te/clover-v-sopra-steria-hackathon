# Karis — Technical Architecture

## 1. Daily Flow: Voice → Timeline + Notifications

```mermaid
flowchart TD
    A([🎙️ Caregiver<br/>records voice<br/>report]) -->|WAV / MP3| B

    subgraph AWS ["☁️ AWS — us-east-1"]
        B[("S3<br/>audio/<br/>{job_id}.mp3")] -->|s3://bucket/audio/...| C
        C["AWS Transcribe<br/>lang: fr-FR<br/>async job"] -->|signed URL → JSON| D
        D["transcript text<br/>(plain French)"]
    end

    D --> E

    subgraph AGENT ["🤖 Strands Agent  ·  Claude Haiku 4.5"]
        E["📥 tool: transcribe<br/>returns transcript + S3 key"]
        E --> F["🔬 tool: extract_observations<br/>Bedrock Converse API<br/>strict JSON prompt<br/>→ list of Observations"]
        F --> G["🔍 tool: find_gaps<br/>daily checklist check<br/>(sleep / meals / meds / mood)<br/>→ missing categories"]
        G -->|≤ 3 questions| H["💬 Caregiver answers<br/>in Streamlit UI"]
        H -->|answers text| F2["🔬 tool: extract_observations<br/>(follow-up answers)"]
        F2 --> I
        F --> I["🛡️ tool: guardrail_check<br/>Bedrock Guardrails<br/>blocks: diagnosis / treatment<br/>/ prescription"]
        I -->|clean observations| J["📤 tool: route_and_notify<br/>routing matrix in code<br/>Haiku writes wording only"]
        I -->|clean observations| K["💾 tool: store_observations<br/>S3 JSON store"]
    end

    K --> L[("S3<br/>observations/<br/>{date}/{id}.json")]
    L --> M["📅 Timeline<br/>local index<br/>query by date · category · severity"]
    M --> N["🖥️ Streamlit UI<br/>Timeline view"]

    J --> NOTIFY

    subgraph NOTIFY ["📨 Notifications  ·  mock by default"]
        P1["👩‍⚕️ Auxiliary<br/>immediate: falls, meds<br/>daily: sleep, meals"]
        P2["👨‍👩‍👧 Family<br/>immediate: falls, meds<br/>daily summary: sleep, meals<br/>filtered: mood"]
        P4["🧑 Caregiver<br/>all categories<br/>confirmation"]
    end

    style AGENT fill:#1e1b4b,color:#e0e7ff,stroke:#6366f1
    style AWS fill:#0f172a,color:#e2e8f0,stroke:#38bdf8
    style NOTIFY fill:#14532d,color:#dcfce7,stroke:#4ade80
```

---

## 2. Strands Agent — Tools Catalogue

```mermaid
flowchart LR
    AG(["🤖 Strands Agent<br/>Claude Haiku 4.5<br/>ordinary tool-calling loop"])

    AG --> T1
    AG --> T2
    AG --> T3
    AG --> T4
    AG --> T5
    AG --> T6
    AG --> T7

    T1["📤 transcribe<br/>─────────────<br/>IN  audio path + S3 key<br/>OUT transcript text<br/>FALL cached fixture if<br/>    USE_CACHED_TRANSCRIPTS=true"]

    T2["🔬 extract_observations<br/>─────────────<br/>IN  transcript + context<br/>OUT list[Observation]<br/>MOD Bedrock Converse<br/>    strict JSON schema<br/>    no diagnosis allowed"]

    T3["🔍 find_gaps<br/>─────────────<br/>IN  list[Observation]<br/>OUT list[question] ≤ 3<br/>MOD checklist diff<br/>    priority-ordered"]

    T4["🛡️ guardrail_check<br/>─────────────<br/>IN  any LLM text<br/>OUT text OR redacted+flag<br/>MOD Bedrock Guardrails<br/>    GUARDRAIL_ID from config"]

    T5["💾 store_observations<br/>─────────────<br/>IN  list[Observation]<br/>OUT S3 keys written<br/>MOD boto3 put_object<br/>    one JSON per fact"]

    T6["📤 route_and_notify<br/>─────────────<br/>IN  list[Observation]<br/>OUT list[SentMessage]<br/>MOD routing matrix (code)<br/>    Haiku writes wording<br/>    mock/SNS/SES/Telegram"]

    T7["📄 generate_report<br/>─────────────<br/>IN  period, subject_id<br/>OUT HTML + PDF paths<br/>MOD query timeline<br/>    + wearable data<br/>    Bedrock Sonnet 4<br/>    guardrail applied"]

    style AG fill:#312e81,color:#e0e7ff,stroke:#818cf8
```

---

## 3. Data Contracts — What Flows Between Tools

```mermaid
erDiagram
    Observation {
        string id PK
        datetime timestamp
        datetime reported_at
        string subject_id
        enum category "sleep · meals_hydration · medication · mood_behavior · mobility_falls · pain · vitals · incident · appointment · logistics"
        string value "factual plain text only"
        enum severity "info · watch · urgent"
        enum source "caregiver_voice · wearable · auxiliary_report"
        string reported_by
        float confidence "0 to 1"
        string transcript_span "exact words from transcript"
    }

    WearableSample {
        datetime timestamp
        string subject_id FK
        int heart_rate_bpm
        enum sleep_state "awake · light · deep"
        float spo2_pct
        int steps
    }

    SentMessage {
        string id PK
        string recipient "auxiliary · family · caregiver"
        string channel "mock · sns · ses · telegram"
        string body
        list observation_ids FK
        datetime sent_at
    }

    Observation ||--o{ SentMessage : "routed to"
    WearableSample }o--|| Observation : "becomes (source=wearable)"
```

---

## 4. Routing Matrix — Who Gets What

```mermaid
flowchart TD
    OBS["Observation<br/>+ severity"] --> RM

    subgraph RM ["Routing Matrix  ·  hard-coded, not LLM"]
        direction TB
        R1["category: sleep · meals_hydration<br/>→ Auxiliary ✅  Family: daily summary<br/>   Caregiver ✅"]
        R2["category: medication issue<br/>→ Auxiliary ⚡IMMEDIATE  Family ⚡IMMEDIATE<br/>   Caregiver ✅"]
        R3["category: mobility_falls · incident<br/>→ Auxiliary ⚡IMMEDIATE  Family ⚡IMMEDIATE<br/>   Caregiver ✅"]
        R4["category: mood_behavior<br/>→ Auxiliary ✅  Family: filtered summary<br/>   Caregiver ✅"]
        R5["category: pain · vitals<br/>→ Auxiliary ✅  Family: summary<br/>   Caregiver ✅"]
        R6["category: logistics<br/>→ Auxiliary ✅  Family ❌  Caregiver ✅"]
        OVERRIDE["severity = urgent<br/>→ overrides table:<br/>   everyone marked ✅ gets it IMMEDIATELY"]
    end

    OBS --> OVERRIDE
    RM --> LLM["Haiku 4.5<br/>writes the wording<br/>per recipient role"]
    LLM --> CH

    subgraph CH ["Notification Channel  ·  NOTIFY_CHANNEL env var"]
        MOCK["mock<br/>shown in Streamlit UI<br/>+ written to log"]
        SNS["sns<br/>AWS SNS SMS<br/>(sandbox required)"]
        SES["ses<br/>AWS SES email"]
        TEL["telegram<br/>Bot API"]
    end
```

---

## 5. Report Flow — Timeline → PDF Export (Doctolib / Hospital)

```mermaid
flowchart TD
    REQ(["⚙️ App requests<br/>report for last N days<br/>(for export)"]) --> QT

    subgraph STORE ["💾 S3 + Local Index"]
        QT["query_timeline<br/>(period, subject_id)<br/>→ list[Observation]"]
        QW["query_wearable<br/>(period, subject_id)<br/>→ list[WearableSample]"]
    end

    QT --> MERGE
    QW --> MERGE

    MERGE["merge_by_date<br/>(pure Python, no LLM)<br/>sorted chronologically"] --> SUM

    SUM["Bedrock Converse<br/>Claude Sonnet 4<br/>prompt: write factual chronology<br/>no diagnosis / interpretation"] --> GC

    GC["guardrail_check<br/>Bedrock Guardrails<br/>same guardrail as daily flow"] --> RENDER

    RENDER["render<br/>HTML template (Jinja2)<br/>+ WeasyPrint → PDF"] --> OUT

    subgraph OUT ["📁 Export Formats"]
        HTML["report_{date}.html<br/>(Hospital integration)"]
        PDF["report_{date}.pdf<br/>(Doctolib / Dossier)"]
    end

    OUT --> UI(["🖥️ Streamlit<br/>Download button"])

    style STORE fill:#0f172a,color:#e2e8f0,stroke:#38bdf8
```

---

## 6. Mock Notification API — How Recipients "Receive" Messages

During the demo all messages go through a **mock channel**. The mock is a thin in-process bus — no real network call — so the demo works without SNS/SES setup.

```mermaid
sequenceDiagram
    participant Agent as 🤖 Strands Agent
    participant Notifier as 📤 notifier.py<br/>(NOTIFY_CHANNEL=mock)
    participant Log as 📋 mock_messages.jsonl<br/>(local file / S3)
    participant UI as 🖥️ Streamlit UI

    Agent->>Notifier: send(recipient, body, observation_ids)
    Notifier->>Log: append SentMessage JSON
    Notifier-->>Agent: SentMessage(id, channel="mock", sent_at=…)

    UI->>Log: poll / read on page load
    Log-->>UI: list[SentMessage]
    UI-->>UI: render "Inbox" per recipient tab
```

**When a real channel is configured (`sns`, `ses`, `telegram`):**

```mermaid
sequenceDiagram
    participant Notifier as 📤 notifier.py
    participant CH as ☁️ AWS SNS / SES<br/>or Telegram Bot API
    participant Phone as 📱 Recipient device

    Notifier->>CH: boto3.publish() or requests.post()
    CH-->>Notifier: MessageId
    Notifier->>Log: append SentMessage (channel="sns"|"ses"|"telegram")
    CH->>Phone: SMS / email / Telegram message
```

---

## 7. Engagement Signal (Optional) — Caregiver Burnout Detection

```mermaid
flowchart LR
    AUDIO["🎙️ Same audio<br/>from daily report"] --> FEAT

    subgraph SIGNAL ["signals/ module  ·  built last"]
        FEAT["extract_prosody<br/>(librosa / pydub)<br/>· speech rate<br/>· pause duration<br/>· energy / amplitude<br/>· answer length in words"]
        FEAT --> COMPARE["compare_to_baseline<br/>caregiver's own<br/>rolling 30-day baseline"]
        COMPARE --> LEVEL["engagement_level<br/>normal | low"]
    end

    LEVEL -->|low| MODE["Streamlit switches<br/>to Minimal Mode<br/>· tap only<br/>· ≤ 2 questions<br/>· no guilt messaging"]
    LEVEL -->|normal| FULL["Normal daily flow"]
```

---

> **Key rule:** The LLM touches **wording only**. Every routing decision, every guardrail check, every tool invocation order is controlled by code. The agent can re-order tool calls but cannot invent new recipients or bypass the matrix.
