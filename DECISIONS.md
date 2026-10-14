# Journal des décisions — Rush 3

Chaque choix de traitement des données ou de modélisation est noté ici avec sa justification. Ce fichier sert à rédiger la partie « choix de traitement » du rapport et à répondre aux questions de l'oral.

## Nettoyage initial (Léa, 2026-10-13) — `clean_data.py`

- Fichier traité : **train.csv uniquement** (test.csv non utilisé).
- `Unnamed: 0` supprimée : index séquentiel sans valeur métier.
- Textes : espaces superflus supprimés, chaînes vides converties en valeurs manquantes.
- Doublons exacts : 0 ; identifiants `id` dupliqués : 0.
- Notes de service : toutes entre 0 et 5.
- Valeurs manquantes conservées (pas d'information inventée) : 310 sur `Arrival Delay in Minutes`.
- Résultat : `rush-3/data/clean/train_clean.csv` + `rapport_nettoyage.csv`.

## Traitements ajoutés dans `src/data.py` (provisoire, à valider en synchro 1)

- `id` retiré : identifiant technique.
- Notes de service à **0 → valeur manquante** (0 = pas de réponse ou service non applicable, d'après le sujet). Paramètre `zero_as_missing` pour comparer si besoin.
- Cible `insatisfait` : 1 = « neutral or dissatisfied », 0 = « satisfied ».
- `load_test()` applique exactement les mêmes traitements à test.csv.

## Synchro 1 — <date, heure> (Léa, Jeanne, Côme)

### Traitement des données
- Notes à 0 : <décision> — <justification>
- Retard d'arrivée manquant (310 lignes) : <décision : = retard au départ / médiane / suppression> — <justification> (traitement fait dans le pipeline du modèle)
- Retards extrêmes : <décision>

### Variables du modèle de détection (connues à l'atterrissage)
- Gardées : <liste>
- Exclues : 14 notes de service (inconnues à l'atterrissage), id, Gender (<raison>)
- À tester avec et sans : Type of Travel
- Hypothèses : Customer Type = <…> ; Type of Travel = <…>

### Planning
- Rendu : <heure> — Synchro 2 : <heure> — Gel des chiffres : <heure>
- Envoi du rendu : <qui>, <où>

## Synchro 2 — <heure>

- Leviers recommandés : <…>
- Modèle retenu : <…> — pourquoi : <…>

## Synchro 3 — gel des chiffres — <heure>

- Évaluation finale sur test exécutée le <date, heure> par <qui>.
