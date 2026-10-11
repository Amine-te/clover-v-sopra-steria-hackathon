# Karis — Prompt Pack pour générer le mockup fonctionnel
## À utiliser avec OpenCode / Codex, prompt par prompt

> **But :** construire un mockup réellement fonctionnel, stable et présentable demain, à partir du dépôt existant.
>
> **Principe :** ne jamais demander à l’agent de “tout construire d’un coup”.  
> Utiliser les prompts ci-dessous dans l’ordre. À la fin de chaque prompt, faire tourner les tests et vérifier visuellement avant de continuer.

---

# 0. Contexte produit à garder pendant toute la génération

Karis est un **journal intelligent pour aidants**.

Flux principal :

```text
Aidant écrit / parle
        ↓
Transcription si audio
        ↓
Extraction structurée
        ↓
1 à 3 clarifications si utile
        ↓
JournalEntry finalisée
        ↓
Séparation privé / partageable
        ↓
Routage par rôle
        ↓
Messages personnalisés
        ↓
Validation humaine
        ↓
Timeline
        ↓
Rapport hebdomadaire
```

Extension multimodale :

```text
audio
├── transcription
└── SER simulé / provider

bracelet aidant
└── données privées par défaut

bracelet aidé
└── données autorisées pour la timeline

toutes les modalités
        ↓
MultimodalContext
```

Pour le mockup :
- le flux utilisateur doit être **réellement cliquable et cohérent** ;
- la logique métier doit être réelle ;
- PostgreSQL doit réellement persister les données ;
- les appels AWS doivent être encapsulés ;
- le mode démo doit fonctionner même sans AWS ;
- le SER et les bracelets peuvent être **simulés**, mais doivent passer par de vrais contrats/providers ;
- aucune donnée privée ne doit pouvoir apparaître dans un message destinataire ;
- aucun auto-envoi ;
- aucun diagnostic médical.

---

# PROMPT 1 — Audit du dépôt + plan d’implémentation

```text
Tu travailles dans le dépôt actuel du hackathon Karis.

Avant toute modification, inspecte attentivement :
- pyproject.toml
- pytest.ini
- README.md
- README_TESTS.md
- docs/IAM_SETUP.md
- samples/
- tests/
- src/clover_v_sopra_steria_hackathon/

Le dépôt contient déjà des exemples AWS pour Bedrock, S3, Transcribe et Textract, ainsi que des tests live AWS. Ne supprime ni ne casse ces éléments.

Produit final à construire :
Karis est un journal intelligent mobile-first pour aidants.

Flow P0 :
1. Thomas écrit ou enregistre une note sur Marie.
2. Si audio : transcription.
3. Analyse structurée de la note.
4. Séparation entre :
   - observations sur Marie,
   - actions,
   - personnes citées,
   - ressenti personnel de Thomas.
5. Au maximum 1 à 3 questions de clarification.
6. Validation de l'entrée.
7. Les informations privées de Thomas restent privées.
8. Le système prépare des messages différents pour Sophie, Nadia ou Marc selon leur rôle.
9. Thomas relit avant l'envoi.
10. L'entrée apparaît dans une timeline.
11. Une semaine de timeline permet de générer un rapport hebdomadaire factuel.

Extension de démo :
- SER aidant simulé via provider ;
- données bracelet aidant simulées et privées par défaut ;
- données bracelet Marie simulées ;
- MultimodalContext qui réunit transcript + SER + wearables.

Stack cible :
Frontend :
- Next.js
- TypeScript
- Tailwind
- mobile-first

Backend :
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic

Data :
- PostgreSQL
- Docker Compose local

AWS :
- S3
- Amazon Transcribe
- Amazon Bedrock
- providers mock équivalents

Règles :
- pas de Streamlit ;
- pas d'agent autonome ;
- pas de LangChain/LangGraph pour le P0 ;
- pas de vector DB ;
- pas de RAG dans le cœur du mockup ;
- ne pas intégrer WhatsApp réel ;
- mock messaging provider ;
- aucun diagnostic ;
- aucun auto-envoi ;
- private-by-default pour le ressenti, SER et wearable de l'aidant ;
- chaque output LLM structuré doit être validé par Pydantic ;
- PostgreSQL est la source de vérité.

Ta tâche dans ce prompt :
1. faire l'audit du dépôt ;
2. identifier ce qui peut être réutilisé ;
3. proposer l'arborescence finale exacte ;
4. proposer les dépendances à ajouter ;
5. proposer le plan de migration depuis la structure actuelle ;
6. identifier les risques pour une démo demain ;
7. NE PAS encore implémenter le produit.

À la fin, donne :
- les fichiers que tu comptes créer ;
- les fichiers existants que tu comptes modifier ;
- les commandes de lancement prévues ;
- les décisions techniques que tu as prises.

Ne fais aucun changement tant que le plan n'est pas clairement exposé.
```

---

# PROMPT 2 — Scaffold complet frontend + backend + PostgreSQL

```text
Implémente maintenant uniquement la fondation du projet Karis selon le plan précédemment validé.

Contraintes :
- préserver les fichiers samples/ et tests AWS existants ;
- conserver le package Python actuel ;
- ajouter le backend Karis dans src/clover_v_sopra_steria_hackathon/ ;
- créer un frontend/ Next.js TypeScript ;
- créer docker-compose.yml pour PostgreSQL ;
- utiliser uv pour Python ;
- ne pas introduire de dépendances inutiles.

Backend attendu :

src/clover_v_sopra_steria_hackathon/
├── api/
├── core/
├── db/
├── domain/
├── models/
├── schemas/
├── services/
├── providers/
│   ├── transcription/
│   ├── llm/
│   ├── ser/
│   ├── wearables/
│   └── messaging/
└── main.py

Frontend attendu :

frontend/
├── app/
├── components/
├── hooks/
├── lib/
├── types/
└── public/

À implémenter :
1. FastAPI app ;
2. GET /api/health ;
3. settings via environment variables ;
4. SQLAlchemy async ou sync cohérent, simple et stable ;
5. Alembic ;
6. PostgreSQL Docker ;
7. CORS localhost:3000 ;
8. Next.js app fonctionnelle ;
9. page d'accueil minimale Karis ;
10. client API frontend ;
11. provider interfaces avec implémentations mock minimales :
    - MockTranscriptionProvider
    - MockLLMProvider
    - MockSERProvider
    - MockWearableProvider
    - MockMessagingProvider
12. .env.example ;
13. scripts/commandes simples de lancement.

Ne développe encore ni le workflow complet ni les écrans finaux.

Tests :
- test health ;
- test settings ;
- test DB connection/model bootstrap si raisonnable ;
- ne pas exiger AWS pour le test suite normal.

À la fin :
- lance les tests ;
- lance au moins un check de build frontend ;
- corrige toute erreur ;
- liste les commandes exactes pour lancer PostgreSQL, backend et frontend ;
- arrête-toi.
```

---

# PROMPT 3 — Modèle métier + migrations + seed de démonstration

```text
Implémente le modèle métier P0 de Karis.

Le JournalEntry est l'aggregate root.

Créer les entités suivantes :

User
- id
- email
- display_name
- created_at

CareRecipient
- id
- first_name
- last_name optional
- birth_year optional
- short_context optional
- created_by
- created_at

CareCircleMember
- id
- care_recipient_id
- name
- relationship
- role
- preferred_channel
- sharing_preferences JSON
- contact_value optional
- active
- created_at

JournalEntry
- id
- care_recipient_id
- author_user_id
- input_type: text | voice
- original_text optional
- transcript optional
- audio_object_key optional
- entry_date
- status
- created_at
- updated_at

Observation
- id
- journal_entry_id
- category
- description
- source_confidence: reported | clarified
- importance: low | medium | high
- visibility JSON/list
- include_in_weekly_report
- transcript_span optional
- created_at

CaregiverFeeling
- id
- journal_entry_id
- description
- visibility default private
- transcript_span optional

ActionItem
- id
- journal_entry_id
- description
- status: done | todo | verify
- assigned_member_id optional
- due_at optional
- visibility

Clarification
- id
- journal_entry_id
- question
- reason
- answer optional
- created_at

GeneratedMessage
- id
- journal_entry_id
- recipient_member_id
- channel
- generated_text
- edited_text optional
- approved
- delivery_status
- sent_at optional

VocalAffectSignal
- id
- journal_entry_id
- valence optional
- arousal optional
- top_label optional
- confidence
- quality
- model_version
- visibility default private

WearableWindow
- id
- journal_entry_id
- subject_type: caregiver | care_recipient
- subject_id
- from_ts
- to_ts
- summary JSON
- quality
- visibility

WeeklyReport
- id
- care_recipient_id
- period_start
- period_end
- generated_payload JSON
- edited_markdown optional
- approved_at optional
- created_at

Créer les enums nécessaires.

Règles métier :
- caregiver feelings PRIVATE par défaut ;
- SER aidant PRIVATE par défaut ;
- wearable aidant PRIVATE par défaut ;
- un message ne peut cibler qu'un membre actif du care circle ;
- une WeeklyReport n'utilise que les entrées finalized ;
- aucune donnée private ne peut être routée vers un destinataire.

Créer une migration Alembic complète.

Créer un seed de démo :
- Thomas : aidant principal
- Marie : aidée, 82 ans
- Sophie : fille / family_caregiver
- Nadia : auxiliary
- Marc : administrative_helper
- Paul : family_informed

Créer 7 jours d'historique réaliste :
- 3 mentions de faible alimentation entre mardi et jeudi ;
- 2 nuits perturbées ;
- 1 rendez-vous kiné annulé ;
- 1 action terminée ;
- 1 action en attente ;
- 1 ressenti privé de Thomas ;
- quelques wearable windows Marie ;
- quelques wearable windows Thomas marqués private.

Créer un script :
scripts/reset_demo.py
ou équivalent

qui remet la base dans cet état déterministe.

Créer les tests de contraintes métier.

Lance migrations + seed + tests.
Corrige les erreurs.
Arrête-toi après validation.
```

---

# PROMPT 4 — API journal texte + timeline sans IA réelle

```text
Construis maintenant un premier vertical slice totalement fonctionnel SANS dépendre de Bedrock.

Objectif :
un utilisateur en mode démo peut saisir une note texte, l'enregistrer, la voir structurée via MockLLMProvider, la finaliser, puis la retrouver dans la timeline.

API :
POST /api/auth/demo
GET  /api/me

GET  /api/care-recipients
GET  /api/care-recipients/{id}

GET  /api/care-recipients/{id}/members

POST /api/journal
GET  /api/journal/{id}
POST /api/journal/{id}/analyze
POST /api/journal/{id}/finalize

GET /api/care-recipients/{id}/timeline

MockLLMProvider :
pour le scénario principal exact :

“Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé.”

doit produire :
- observation fatigue Marie ;
- observation alimentation faible Marie ;
- traitement déclaré comme pris ;
- personne citée Sophie ;
- caregiver feeling Thomas = très fatigué, private ;
- clarification_needed = true ;
- question fatigue inhabituelle ;
- question Sophie doit-elle vérifier l'alimentation.

Pour d'autres textes, fournir une extraction de mock simple mais cohérente.

Frontend :
- /demo ou bouton “Entrer en mode démo”
- /dashboard
- /journal/new
- /journal/[id]/review
- /timeline

UX :
- français ;
- mobile-first ;
- esthétique Karis : fond blanc chaud, bleu marine, teal/vert doux, accent corail ;
- cartes arrondies ;
- interface rassurante ;
- pas d'apparence médicale froide.

Dashboard :
- Marie
- “Comment s’est passée la journée avec Marie ?”
- CTA “Raconter ma journée”
- CTA “Écrire”
- timeline récente
- carte “Bilan de la semaine”

Journal texte :
- textarea naturelle ;
- pas de formulaire médical ;
- bouton “Analyser”.

Review :
- observations Marie ;
- actions ;
- ressenti Thomas privé ;
- provenance/source si utile.

Timeline :
- entrées seed + nouvelle entrée ;
- lisible sur mobile.

Ne fais pas encore la clarification interactive ni les messages.

Tests :
- API create/analyze/finalize/timeline ;
- privacy default du caregiver feeling.

Faire un build frontend.
Tester le parcours complet.
Arrête-toi.
```

---

# PROMPT 5 — Clarification interactive

```text
Ajoute le workflow de clarification à Karis.

Backend :
- persister les Clarification ;
- endpoint :
  POST /api/journal/{id}/clarifications
- permettre de soumettre les réponses ;
- après réponse, relancer l'analyse via provider ;
- finaliser une analyse enrichie ;
- au maximum 3 questions.

Pour le scénario démo :
Question 1 :
“Cette fatigue était-elle plus importante que d’habitude ?”

Réponse démo :
“Oui.”

Question 2 :
“Souhaitez-vous que Sophie vérifie l’alimentation lors de sa visite ce soir ?”

Réponse démo :
“Oui.”

Après clarification :
- fatigue = plus importante que d'habitude ;
- ajouter action :
  “Sophie vérifie l’alimentation ce soir”
- action liée à Sophie si possible.

Frontend :
- /journal/[id]/clarify
- afficher une question à la fois ;
- réponses rapides Oui / Non + texte libre ;
- transition fluide ;
- résumé live discret ;
- après la dernière question → écran review.

Important :
- ne pas inventer de question si MockLLMProvider indique que la note est déjà suffisante ;
- jamais plus de 3 ;
- stocker questions et réponses ;
- le backend reconstruit le contexte, pas le navigateur.

Tests :
- scénario ambigu ;
- scénario sans clarification ;
- limite max 3 ;
- re-analyse après réponse.

Faire le parcours complet jusqu'à review.
```

---

# PROMPT 6 — SER + wearables simulés + Multimodal Context

```text
Ajoute maintenant l'enrichissement multimodal de démonstration.

Important :
pour le hackathon, SER et bracelets sont simulés mais doivent être intégrés proprement derrière des providers réels.

Créer :

SpeechEmotionProvider
- analyze(audio_object_key) -> VocalAffectSignal

MockSERProvider :
pour le scénario démo :
- valence = negative
- arousal = high
- confidence = 0.61
- quality = good
- model_version = demo-ser-v1
- visibility = private

WearableProvider
- summarize(subject_type, subject_id, around) -> WearableWindowSummary

MockWearableProvider :

Thomas :
- heart_rate_avg_bpm = 91
- quality = good
- coverage_pct = 92
- visibility = private

Marie :
- heart_rate_avg_bpm = 74
- steps_total = 1320
- quality = good
- coverage_pct = 88

Créer :
MultimodalContextBuilder

Il doit produire :
- transcript/original text ;
- semantic analysis ;
- caregiver vocal affect ;
- caregiver wearable summary ;
- care recipient wearable summary.

Règles :
- SER Thomas reste private ;
- wearable Thomas reste private ;
- ces données ne doivent jamais apparaître dans les prompts/messages de Sophie/Nadia/Marc ;
- les données Marie peuvent être visibles dans timeline selon config ;
- jamais de causalité inventée entre SER et FC ;
- jamais de diagnostic.

Frontend :
dans l'écran de review, ajouter une section repliable :
“Contexte multimodal”

Afficher :
- Transcript ✓
- SER aidant ✓
- Bracelet aidant ✓
- Bracelet Marie ✓

Détails :
- SER : valence / arousal / confiance, badge “privé”
- bracelet Thomas : FC moyenne, couverture, badge “privé”
- bracelet Marie : FC moyenne, activité, qualité

Ne surcharge pas l'écran principal.

Tests :
- construction contexte multimodal ;
- privacy SER/wearable aidant ;
- graceful degradation si provider retourne None.
```

---

# PROMPT 7 — Voice recording + AWS Transcribe / fallback demo

```text
Ajoute la saisie vocale de bout en bout.

Frontend :
- MediaRecorder API ;
- gros bouton microphone ;
- timer ;
- stop ;
- playback local ;
- upload ;
- état de transcription ;
- fallback saisie texte.

Backend :
- endpoint upload audio ;
- ObjectStorageProvider ;
- S3ObjectStorageProvider ;
- MockObjectStorageProvider ;
- TranscriptionProvider ;
- AWSTranscribeProvider ;
- MockTranscriptionProvider.

Réutilise autant que possible la logique / configuration déjà présente dans samples/transcribe_sample.py et samples/s3_sample.py sans casser les samples.

Configuration :
STT_PROVIDER=mock|aws_transcribe
OBJECT_STORAGE_PROVIDER=mock|s3

En mock :
si un audio est envoyé, retourner le transcript du scénario démo.

En live :
- stocker l'audio dans S3 privé ;
- démarrer Transcribe ;
- langue fr-FR ;
- polling/backoff raisonnable ;
- récupérer le transcript ;
- persister transcript ;
- gérer timeout/erreur proprement.

Le même audio doit ensuite être transmis au SERProvider, mais le mock SER peut être utilisé même quand Transcribe est live.

UX :
si Transcribe échoue :
“Nous n’avons pas réussi à transcrire l’enregistrement. Vous pouvez réessayer ou écrire la note.”

Le journal ne doit jamais être perdu.

Ajouter option pratique de démo :
“Utiliser l’audio de démonstration”
qui peut utiliser samples/audio/Enregistrement.mp3 si accessible côté backend ou un fixture dédié.

Tests normaux : mock uniquement.
Tests live AWS : marqués/skippés derrière flag existant --aws-live si cohérent avec le repo.

Tester sur navigateur mobile/local HTTPS si possible.
```

---

# PROMPT 8 — Bedrock réel + Structured Output + Pydantic

```text
Remplace maintenant progressivement MockLLMProvider par un BedrockLLMProvider, sans supprimer le mock.

Configuration :
LLM_PROVIDER=mock|bedrock
AWS_BEDROCK_MODEL_ID=...

Réutilise la configuration AWS existante et le sample bedrock_sample.py si utile.

Le provider doit exposer des méthodes séparées :

analyze_journal(...)
generate_recipient_message(...)
generate_weekly_report(...)

Pour analyze_journal :
- prompt système strict ;
- sortie JSON structurée ;
- utiliser Structured Outputs / JSON Schema si le modèle Bedrock disponible le permet ;
- sinon demander JSON strict et valider avec Pydantic ;
- retry contrôlé une fois si validation échoue ;
- jamais de parsing fragile par regex.

Schéma JournalEntryAnalysis :
- short_summary
- observations
- caregiver_feelings
- actions
- people_mentioned
- clarification_needed
- questions

Règles prompt :
- utiliser uniquement les faits fournis ;
- ne jamais diagnostiquer ;
- ne jamais prescrire ;
- ne pas inventer ;
- distinguer aidant et aidé ;
- caregiver feelings private by default ;
- max 3 questions ;
- préserver l'incertitude ;
- “traitement déclaré comme pris”, pas “observance confirmée”.

Important :
le modèle n'a PAS l'autorité sur :
- permissions ;
- destinataires finaux ;
- envoi ;
- visibilité effective.

Tout cela reste backend.

Créer fixtures pour que tests normaux n'appellent pas AWS.

Ajouter tests live Bedrock optionnels.

À la fin, montrer un exemple de résultat live si credentials disponibles, mais le projet doit rester 100% utilisable en mock.
```

---

# PROMPT 9 — Confidentialité + routage + messages personnalisés

```text
Implémente la fonctionnalité la plus importante pour le pitch :
confidentialité + routage sélectif + génération de messages.

Principe :
une JournalEntry n'est jamais envoyée entière au LLM pour rédiger un message.

Créer :
PrivacyService
RoutingService
RecipientContextBuilder
MessageGenerationService

Flow :
structured items
→ filtre private
→ vérification rôle / sharing_preferences
→ allowlist d'items autorisés
→ RecipientContext minimal
→ LLM wording
→ review humaine
→ mock send.

Règles :
- caregiver feelings private : jamais dans recipient context ;
- SER aidant private : jamais dans recipient context ;
- wearable aidant private : jamais dans recipient context ;
- recipient doit être membre actif du care circle ;
- si une catégorie n'est pas pertinente pour le rôle, elle n'est pas transmise ;
- partir d'une liste vide et ajouter seulement les items autorisés ;
- ne jamais faire “full journal minus secrets”.

Routage démo :
Sophie, family_caregiver :
- fatigue Marie
- alimentation Marie
- action de visite

Nadia, auxiliary :
- informations pratiques pertinentes sur Marie
- alimentation si autorisé

Marc, administrative_helper :
- rendez-vous / administratif uniquement

Paul, family_informed :
- résumé général non sensible si pertinent

Endpoints :
POST /api/journal/{id}/messages/generate
PATCH /api/messages/{id}
POST /api/journal/{id}/messages/send
GET /api/messages/mock-inbox

MockMessagingProvider :
- stocke “sent” en DB ;
- mock inbox visible dans UI.

Frontend :
/journal/[id]/share

Afficher une carte par destinataire :
- pourquoi il est concerné ;
- message généré ;
- modifier ;
- toggle envoyer ;
- canal ;
- bouton final “Envoyer X messages”.

Avant envoi :
relecture obligatoire.

Ajouter dans l'UI une phrase discrète :
“Les informations privées ont été exclues avant la génération de ces messages.”

Tests OBLIGATOIRES :
1. “Thomas est épuisé” absent du prompt/context de Sophie.
2. SER Thomas absent.
3. wearable Thomas absent.
4. Marc ne reçoit pas une observation repas si non autorisé.
5. destinataire externe/inactif refusé.
6. aucun message ne part sans approved=true.

Ce prompt est critique : ne continue pas tant que tous ces tests passent.
```

---

# PROMPT 10 — Rapport hebdomadaire + timeline enrichie

```text
Implémente le rapport hebdomadaire.

Objectif :
le code collecte et agrège d'abord les faits ; le LLM rédige ensuite.

Backend :
ReportAggregationService

Pour une période :
1. charger uniquement JournalEntry status=finalized ;
2. exclure private ;
3. inclure uniquement include_in_weekly_report / professional_report selon règles ;
4. trier chronologiquement ;
5. grouper les observations ;
6. calculer en code les occurrences et dates ;
7. construire un WeeklyReportContext ;
8. appeler LLMProvider.generate_weekly_report ;
9. valider WeeklyReportPayload avec Pydantic.

Ne jamais demander au LLM de compter lui-même à partir des transcripts bruts.

WeeklyReportPayload :
- period_start
- period_end
- general_summary
- nutrition
- sleep
- mood_behavior
- mobility
- medication_reported
- notable_events
- appointments_logistics
- completed_actions
- pending_items
- recurring_reported_observations
- suggested_questions_for_professional
- source_entry_count
- missing_information_notes

Scénario seed attendu :
“Une faible alimentation a été rapportée à trois reprises entre mardi et jeudi.”

Interdit :
“Marie souffre de malnutrition.”

SER Thomas et wearable Thomas :
EXCLUS par défaut du rapport Marie.

Wearables Marie :
peuvent apparaître comme :
“Le bracelet a mesuré...”
jamais comme diagnostic.

Endpoints :
POST /api/care-recipients/{id}/reports/weekly/generate
GET  /api/reports/{id}
PATCH /api/reports/{id}
POST /api/reports/{id}/approve

Frontend :
/reports/weekly
ou /reports/[id]

UI :
- “Votre semaine avec Marie”
- période
- nombre d'entrées
- sections lisibles
- modifier
- approuver
- bouton export simulé/HTML
- disclaimer :
“Ce document résume les informations consignées dans Karis. Il ne constitue pas un avis médical.”

Tests :
- count low appetite = 3 ;
- private data excluded ;
- medication missing days not invented ;
- report only finalized entries.
```

---

# PROMPT 11 — Polish UI complet pour la démo

```text
Polis maintenant l'interface pour qu'elle soit présentable devant le jury.

Ne change pas la logique métier sauf bug.

Direction visuelle :
- fond ivoire / blanc chaud ;
- bleu marine pour titres ;
- teal / vert doux pour actions ;
- accent corail ;
- cartes très légèrement teintées ;
- radius généreux ;
- ombres très légères ;
- icônes Lucide ;
- look humain, calme, premium, non médical.

Mobile-first :
- largeur 360–430 px prioritaire ;
- desktop propre mais secondaire ;
- gros touch targets ;
- bottom nav.

Navigation :
- Accueil
- Journal
- Timeline
- Cercle
- Menu

Dashboard :
- Bonjour Thomas
- Marie
- “Comment s’est passée la journée avec Marie ?”
- gros CTA micro
- CTA texte
- dernières entrées
- carte bilan hebdomadaire

Ajouter :
- loading states ;
- skeletons ;
- empty states ;
- erreurs user-friendly ;
- transitions légères ;
- badges privé / partagé ;
- indicateurs source :
  transcript / clarification / SER / wearable ;
- panneau “Contexte multimodal” repliable.

Créer une UX démo très fluide :
- bouton “Réinitialiser la démo”
- bouton “Utiliser la note de démonstration”
- aucune étape ne doit nécessiter plus d'un ou deux clics inutiles.

Ne mets pas de jargon technique visible dans l'interface utilisateur principale.

Les noms techniques peuvent apparaître uniquement dans un petit “mode présentation technique” facultatif.

Faire :
- npm run build
- lint si configuré
- test backend
- vérifier responsive.
```

---

# PROMPT 12 — Mode “Technical Demo” pour le jury

```text
Ajoute un mode de présentation technique activable par query param ou toggle discret :

?technical=1

Ce mode ne change pas la logique du produit.

Il affiche seulement des informations pédagogiques supplémentaires pendant la démo :

Après transcription :
- “Source : Amazon Transcribe” ou “Mock Transcribe”

Contexte multimodal :
- Transcript ✓
- SER aidant ✓
- Bracelet aidant ✓
- Bracelet Marie ✓

Après analyse :
- Structured Output
- Pydantic validated
- status

Dans l'écran share :
- nombre d'items structurés
- nombre d'items filtrés private
- recipient context count

Exemple :
“7 éléments structurés → 3 autorisés pour Sophie → 3 envoyés au générateur”

Dans le rapport :
- “12 événements DB → 9 reportables → agrégation déterministe → Bedrock”

Important :
- rester élégant ;
- ne jamais montrer des API keys ;
- ne pas afficher les prompts complets ;
- ne pas afficher de données privées dans un debug panel destiné à un autre rôle ;
- technical mode est pour notre présentation, pas un dashboard d'observabilité complet.

Ce mode doit rendre le pitch technique beaucoup plus facile à démontrer.
```

---

# PROMPT 13 — Hardening de la démo de 2 minutes

```text
Prépare le projet spécifiquement pour une démo de 2 minutes qui ne peut pas échouer.

Scénario exact :

1. Dashboard Thomas / Marie.
2. “Raconter ma journée”.
3. Utiliser audio démo ou saisie :
   “Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé.”
4. Transcription.
5. Clarification fatigue inhabituelle → Oui.
6. Clarification Sophie vérifie alimentation → Oui.
7. Review :
   Marie :
   - fatigue plus importante
   - faible alimentation
   - traitement déclaré comme pris
   Thomas :
   - fatigue personnelle, privé
   Multimodal :
   - SER privé
   - wearable Thomas privé
   - wearable Marie visible selon règles
8. Share :
   Sophie reçoit le message pertinent.
   Montrer explicitement que private data count > 0 mais private passed_to_prompt = 0.
9. Timeline.
10. Rapport :
    “faible alimentation rapportée à trois reprises...”

Implémenter :
- reset démo ;
- fixtures stables ;
- aucun timeout long ;
- si provider live échoue, fallback automatique contrôlé vers mock avec badge “mode démo” ;
- pas de stacktrace dans UI ;
- cache des résultats du scénario si utile ;
- mock inbox stable.

Créer un script :
scripts/demo_smoke.py

qui vérifie automatiquement :
- DB accessible ;
- seed présent ;
- providers configurés ;
- scénario mock complet possible.

Créer aussi :
DEMO_RUNBOOK.md

avec :
- commande de lancement ;
- URL ;
- étapes de clic ;
- phrase à dire à chaque étape ;
- plan B si audio échoue ;
- plan B si AWS échoue.

À la fin, exécute :
- backend tests ;
- frontend build ;
- demo smoke ;
- corrige tout ;
- fournis le statut final de readiness.
```

---

# PROMPT 14 — Audit final avant présentation

```text
Fais un audit final du mockup Karis comme si tu étais responsable de la démo demain.

Ne rajoute aucune feature.

Vérifie :

BACKEND
- migrations
- seed
- health
- journal
- clarification
- multimodal context
- privacy
- routing
- message generation
- mock sending
- timeline
- weekly report

SECURITY
- private caregiver feeling jamais dans recipient context
- SER aidant jamais dans recipient context
- wearable aidant jamais dans recipient context
- aucun auto-send
- aucun diagnostic généré
- aucun secret frontend

FRONTEND
- mobile 360 px
- dashboard
- voice/text
- clarification
- review
- share
- timeline
- report
- technical demo mode

ROBUSTESSE
- mock mode complet sans AWS
- live Transcribe optionnel
- live Bedrock optionnel
- fallback contrôlé
- reset demo
- smoke test

PERFORMANCE DEMO
- aucun écran ne doit bloquer plus de quelques secondes en mock
- aucun appel live obligatoire
- aucune dépendance au hardware bracelet réel

Lance tous les tests et build.
Corrige uniquement les bugs / incohérences.
Ne refactorise pas inutilement.

À la fin, produire un rapport :
1. PASS / FAIL par fonctionnalité ;
2. commandes exactes de lancement ;
3. variables d'environnement nécessaires ;
4. scénario de démo final ;
5. risques restants ;
6. plan B pour chaque risque.
```

---

# Prompt unique si tu es très pressé

> Utilise-le seulement si tu ne peux vraiment pas procéder étape par étape.

```text
Construis un mockup complet et présentable de Karis dans ce dépôt, en préservant tous les samples et tests AWS existants.

Karis est un journal intelligent pour aidants.

Architecture :
- Next.js + TypeScript mobile-first dans frontend/
- FastAPI + Python dans le package src existant
- Pydantic
- SQLAlchemy + Alembic
- PostgreSQL via Docker Compose
- S3 pour audio
- Amazon Transcribe pour STT
- Bedrock pour extraction, clarification, messages et rapport
- provider mocks obligatoires
- SER et wearables simulés via providers
- mock messaging

Flow :
voice/text
→ transcription
→ SER + wearable context
→ structured extraction
→ max 3 clarifications
→ Pydantic + domain validation
→ privacy/visibility
→ timeline
→ selective recipient context
→ personalized messages
→ human approval
→ mock send
→ weekly report.

Demo family:
- Thomas caregiver
- Marie, 82
- Sophie family caregiver
- Nadia auxiliary
- Marc admin helper
- Paul informed family.

Demo note:
“Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé.”

Expected:
- Marie fatigue
- Marie low food intake
- medication reported taken
- Sophie mentioned
- Thomas tired = private
- clarification fatigue unusual
- clarification Sophie checks food
- SER Thomas private
- wearable Thomas private
- wearable Marie contextual
- Sophie message excludes every private item
- timeline persists
- report says low food intake reported 3 times in seeded week.

Non-negotiable:
- no diagnosis
- no autonomous agent
- no LangChain/LangGraph
- no vector DB/RAG for MVP
- no auto-send
- private data filtered BEFORE recipient LLM prompt
- PostgreSQL is memory
- every LLM structured output Pydantic validated
- mock mode must run without AWS credentials
- build must be demo-ready on mobile
- add reset-demo and technical-demo mode
- tests must prove privacy rules.

Work systematically:
1. inspect repo
2. scaffold
3. domain + DB
4. seed
5. APIs
6. text flow
7. clarification
8. SER/wearables
9. voice
10. Bedrock
11. privacy/routing
12. messages
13. timeline/report
14. UI polish
15. demo hardening
16. run all tests + frontend build.

Do not stop at static screens: the mockup must have real state transitions and real persistence.
Do not claim a feature is implemented if it is only visually mocked.
External services may have mock implementations, but they must share the same interfaces as live providers.
```

---

# Ordre recommandé

```text
Prompt 1  → audit
Prompt 2  → scaffold
Prompt 3  → DB/domain/seed
Prompt 4  → vertical slice texte
Prompt 5  → clarification
Prompt 6  → SER/wearables
Prompt 7  → voice
Prompt 8  → Bedrock
Prompt 9  → privacy/routing/messages
Prompt 10 → report
Prompt 11 → UI polish
Prompt 12 → technical demo mode
Prompt 13 → demo hardening
Prompt 14 → final audit
```

---

# Conseil important

Pour demain, **le mock mode doit être la voie principale de démonstration**.

Les intégrations AWS live doivent être disponibles et démontrables si elles marchent, mais elles ne doivent pas devenir un point de défaillance unique.

Le jury doit voir un produit complet.

La meilleure architecture de hackathon est donc :

```text
UI réelle
+ API réelle
+ DB réelle
+ règles métier réelles
+ privacy réelle
+ state transitions réelles

AWS live quand disponible
↕ même interface
providers mock déterministes pour sécuriser la démo
```

C’est beaucoup plus crédible qu’un prototype où toute la démo dépend d’un seul appel externe.
