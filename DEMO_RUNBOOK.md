# Karis — démonstration jury (2 minutes)

## Démarrer

Depuis la racine du dépôt, utiliser Python/uv, Node/npm et Docker. PostgreSQL est exposé sur **5433** (le conteneur utilise 5432).

Le mode démo fonctionne sans identifiants AWS. Les valeurs par défaut sont :

```dotenv
APP_ENV=development
DEMO_RESET_ENABLED=true
LLM_PROVIDER=mock
LLM_FALLBACK_TO_MOCK=true
STT_PROVIDER=mock
SER_PROVIDER=mock
WEARABLE_PROVIDER=mock
OBJECT_STORAGE_PROVIDER=mock
MESSAGING_PROVIDER=mock
```

Si un `.env` existe, vérifier qu'il ne sélectionne pas de fournisseurs live pour cette présentation. Ne pas écraser les réglages d'un autre projet.

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run python scripts/reset_demo.py
uv run uvicorn clover_v_sopra_steria_hackathon.main:app --reload
```

Dans un autre terminal :

```bash
cd frontend && npm run dev
```

Préflight, dans un troisième terminal, depuis la racine :

```bash
uv run python scripts/demo_smoke.py
```

Résultat attendu : tous les contrôles `[PASS]`, puis **DEMO READY**, code de sortie 0. Le script vérifie l'API et la base, crée une note temporaire, exerce le parcours voix/clarification/confidentialité et génère le bilan de la semaine de seed. Il supprime ensuite sa note et ses brouillons ; il n'envoie aucun message. Le bilan généré reste disponible (une nouvelle génération remplace le bilan de cette période).

**URL exacte : http://localhost:3000/demo?technical=1**

Pour une autre adresse d'API : `uv run python scripts/demo_smoke.py --api-url http://localhost:8001`. Le script doit utiliser la même configuration de base que le serveur.

## Parcours chronométré

| Temps | Action | Phrase / point à montrer |
|---|---|---|
| 0:00 | Entrer comme Thomas, puis Accueil | « Thomas ouvre son journal. Marie a 82 ans. » |
| 0:10 | **Raconter ma journée** → **Utiliser l'audio de démonstration** | Une note vocale, sans formulaire médical. |
| 0:30 | Relire la transcription et la carte Pipeline | Audio stocké, transcription, SER et contexte multimodal ; les fournisseurs sont identifiés comme mocks. |
| 0:40 | Continuer ; répondre **Oui**, Continuer, **Oui**, Continuer | Deux précisions utiles, une question à la fois. |
| 0:55 | Relecture | Fatigue de Marie, alimentation, **traitement déclaré comme pris**, ressenti de Thomas **Privé**. Ouvrir brièvement le panneau multimodal, puis le refermer. |
| 1:15 | **Valider et préparer le partage**, carte Sophie | Montrer les faits autorisés et **Données privées transmises : 0**. Les données privées sont filtrées **avant** la génération, pas masquées après. |
| 1:35 | **Voir la timeline** | Notes regroupées par jour, actions à suivre. L'envoi est facultatif et nécessite une approbation explicite. |
| 1:45 | **Bilan de la semaine** → ouvrir le bilan préparé par le préflight | « Une faible alimentation a été rapportée à trois reprises entre mardi et jeudi. » Montrer l'agrégation déterministe et les 6 notes validées de la semaine passée. |
| 2:00 | Conclusion | « Karis organise les mots, respecte l'intimité et aide le cercle à se coordonner. » |

Note de démonstration :

> Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé.

Le bouton **Utiliser la note de démonstration** offre le même parcours en mode texte. Le micro réel fonctionne sur localhost ou en HTTPS avec l'autorisation du navigateur ; l'audio de démo ne requiert pas cette autorisation. Aucun délai artificiel n'est ajouté.

## Mode technique

- Activé par `?technical=1` ou **Menu → Mode technique** ; désactivé par `?technical=0` ou le même bouton.
- Le choix reste actif dans l'onglet lors des transitions. Aucune règle métier ne dépend de ce choix.
- Cartes : transcription, génération/validation, filtrage par destinataire, construction du rapport.
- Les compteurs affichés proviennent du backend. Les informations techniques excluent les textes privés, les prompts, les clés d'objets, les URL signées et les identifiants AWS.
- Les métadonnées des appels LLM sont éphémères, conservées dans l'onglet pour la présentation. Une note ancienne peut indiquer que les métadonnées ne sont pas disponibles, sans inventer de fournisseur ni de latence.
- Le nombre d'objets structurés du partage inclut les mesures ; le sous-ensemble partageable est celui des observations/actions utilisé par le filtrage existant. Les mesures de bracelet de Marie ne sont pas transmises dans ces messages.

## Réinitialiser entre deux passages

**Menu → Réinitialiser la démo → Confirmer**, ou :

```bash
uv run python scripts/reset_demo.py
```

La réinitialisation est atomique et limitée à la famille de démo : notes/messages/bilans de Marie, cercle et fenêtres de mesure de démo. Les identifiants des personnes restent déterministes ; les autres familles sont préservées. L'historique couvre la dernière semaine complète lundi–dimanche **strictement passée** : 7 notes, dont 6 validées. L'API `POST /api/demo/reset` exige `{"confirmed": true}` et est indisponible si `APP_ENV=production` ou `DEMO_RESET_ENABLED=false`. Ce mode local n'est pas un mécanisme d'authentification de production.

Après un reset, relancer le smoke pour préparer le bilan et revenir à l'URL de démo. Les fichiers audio mocks sont locaux sous `.data/audio` ; le reset de base ne supprime pas ces fichiers.

## Si quelque chose échoue

- **Backend inaccessible** : relancer uvicorn, vérifier `/api/health` et le port 8000. La page affiche un message de connexion lisible.
- **PostgreSQL** : vérifier `docker compose ps`, la base sur localhost:5433, puis `uv run alembic upgrade head` et le reset.
- **Bedrock** : conserver `LLM_FALLBACK_TO_MOCK=true` ; l'interface indique le repli **Mode démo**. Avec le repli désactivé, l'erreur reste contrôlée et la note enregistrée est conservée.
- **Transcription** : réessayer sur la même note ou **Continuer avec la note de démonstration**. Cette substitution est un choix explicite ; une transcription live réussie n'est jamais simulée.
- **SER / bracelets indisponibles** : la note continue ; l'interface affiche les modalités réellement disponibles. Aucun diagnostic n'est dérivé des mesures.
- **Envoi** : les brouillons approuvés restent disponibles ; réessayer. Les éventuels messages déjà livrés conservent leur statut. Seule la boîte mock est prévue pour cette démo.
- **Note/bilan introuvable après reset** : revenir à l'Accueil ou à `/demo?technical=1`.

## Vérifications de code

```bash
uv run pytest
uv run python scripts/demo_smoke.py
cd frontend && npm run build
```

Les tests AWS live restent opt-in avec le marqueur existant. La préparation du jury utilise uniquement les mocks. Le navigateur doit pouvoir joindre le backend ; sur un téléphone physique, `localhost` désigne le téléphone (utiliser l'adresse réseau appropriée et ajuster CORS/API_URL, ou présenter avec l'émulation mobile locale).
