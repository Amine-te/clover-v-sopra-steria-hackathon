# M9 — Bedrock optionnel

## Configuration

Le mode démo reste entièrement local, déterministe et sans identifiants AWS :

```dotenv
LLM_PROVIDER=mock
LLM_FALLBACK_TO_MOCK=true
```

Pour activer Bedrock, renseigner `.env`, puis redémarrer l’API :

```dotenv
LLM_PROVIDER=bedrock
LLM_FALLBACK_TO_MOCK=true
AWS_DEFAULT_REGION=<région du modèle>
AWS_BEDROCK_MODEL_ID=<identifiant du modèle ou du profil d’inférence compatible Converse>
```

Les identifiants sont résolus par la chaîne standard boto3 (profil, environnement
ou rôle). Le démarrage ne crée aucun client AWS. Le client `bedrock-runtime` est
créé et réutilisé seulement lors d’un appel LLM.

## JSON, validation et erreurs

Chaque appel utilise Converse, avec `maxTokens=3000`. Le fournisseur demande
`outputConfig.textFormat` de type `json_schema` lorsqu’il est disponible dans le
SDK. Si le modèle refuse explicitement ce format, l’appel est renouvelé sans
`outputConfig`, avec une instruction JSON stricte et le même schéma.

Les deux chemins suivent exactement la même validation locale :

1. JSON strict : pas de texte Markdown, de clés dupliquées ni de nombres non finis.
2. Schéma Pydantic : champs/types attendus et rejet des champs supplémentaires.
3. Règles métier de l’analyse : ressentis privés, observations concernant la
   personne accompagnée, statuts valides, au maximum trois questions avec raisons,
   formulation du traitement déclaré pris et absence d’observance inférée.
4. Persistance seulement après validation.

Les contraintes non prises en charge par le sous-ensemble JSON Schema de Bedrock
sont retirées du schéma de génération, mais restent appliquées localement par
Pydantic. Une réponse invalide entraîne **une seule réparation**. Aucun contenu
invalide n’est enregistré. Les règles sémantiques (pas de diagnostic, invention,
prescription ou recalcul des totaux) sont explicitement imposées par les prompts ;
la validation structurelle n’est pas une vérification médicale du texte généré.

Avec `LLM_FALLBACK_TO_MOCK=true`, une erreur contrôlée de configuration, AWS ou
validation utilise le fournisseur mock existant. Avec `false`, l’API retourne une
erreur HTTP 502 lisible en français. L’analyse existante est préservée ; les
réponses de clarification sont enregistrées avant l’appel optionnel.

## Confidentialité et métadonnées

- Messages : uniquement `RecipientContext`, déjà filtré et autorisé par le backend.
  Le fournisseur revalide ce contrat et refuse tout champ supplémentaire, même
  imbriqué. Il ne reçoit jamais l’entrée complète, le texte original, les ressentis,
  le SER ou le wearable de l’aidant.
- Rapports : uniquement `WeeklyReportContext`, avec comptes et preuves déterministes.
- Analyse propriétaire : texte/transcription, réponses de clarification, prénoms
  et signaux multimodaux séparés. Ces mesures restent contextuelles et les signaux
  de l’aidant privés. L’analyse précédente n’est pas utilisée comme preuve.
- L’autorisation des destinataires, l’approbation et l’envoi restent déterministes.

Les réponses aux appels de génération exposent `provider_metadata` :
`provider_used`, `model_id`, `latency_ms`, `validation_retry_count`, `fallback_used`.
Un repli est explicitement marqué `provider_used="mock-fallback"` et
`fallback_used=true`. `model_id` désigne le modèle Bedrock tenté en cas de repli.
Ces métadonnées concernent l’appel en cours ; elles ne sont pas persistées et sont
absentes (`null`) lors d’une lecture ultérieure ou si aucun nouveau brouillon n’a
été généré. Les logs incluent opération, fournisseur, modèle, latence, validation
et repli, sans texte du journal, prompt privé, réponse brute ou secret AWS.

## Vérification

```bash
uv run pytest
```

Le test live utilise uniquement un journal synthétique, désactive le repli et
nécessite une configuration valide ainsi que des identifiants avec accès au modèle :

```bash
uv run pytest tests/test_karis_bedrock_live.py --aws-live
```

Depuis `frontend/`, vérifier également `npm run build`.
