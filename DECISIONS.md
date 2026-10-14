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

## Traitements ajoutés dans `src/data.py` (2026-10-14)

- `id` retiré : identifiant technique.
- Notes de service à **0 → valeur manquante** (0 = pas de réponse ou service non applicable, d'après le sujet). Paramètre `zero_as_missing` pour comparer si besoin.
- Cible `insatisfait` : 1 = « neutral or dissatisfied », 0 = « satisfied ».
- `load_test()` applique exactement les mêmes traitements à test.csv.

## Décisions de modélisation — volet 2 (Jeanne, 2026-10-14)

Tous les chiffres viennent de `notebooks/02_modeles.ipynb` (validation croisée à 5 plis sur train, `random_state=42`), exprimés en gain net pour 1 000 passagers arrivants. Gain maximal possible (n'aborder que des insatisfaits) : 6 000 €.

Validation par le groupe : Léa <à confirmer>, Côme <à confirmer>.

### Traitement des données pour le modèle
- **Retard d'arrivée manquant (310 lignes, 0,3 %)** : remplacé par le retard au départ — les deux sont quasi identiques (corrélation 0,965) ; calcul ligne par ligne, sans fuite d'information.
- **Retards extrêmes** : conservés — ce sont de vrais retards, et précisément les passagers les plus à risque.
- **Notes à 0** : traitées comme valeurs manquantes (sans effet sur le modèle de détection, qui n'utilise pas les notes).

### Méthode de comparaison
- `test.csv` n'est utilisé pour aucun choix : comparaison en **validation croisée à 5 plis sur train**, même découpage pour toutes les règles et tous les modèles.
- Critère : **gain net** avec les hypothèses de la direction (+60 € par insatisfait abordé, −40 € par satisfait abordé, capacité 10 %). Seuil de rentabilité : 40 % de précision.

### Variables du modèle de détection (connues à l'atterrissage)
- **Gardées** : Class, Age, Customer Type, Flight Distance, Departure Delay, Arrival Delay.
- **Exclues** :
  - 14 notes de service — n'existent qu'après l'enquête, inconnues à l'atterrissage ;
  - Gender — quasi aucun écart d'insatisfaction (57,3 % femmes / 56,1 % hommes), risque de discrimination ;
  - **Type of Travel** — motif du voyage déclaré dans l'enquête, pas connu de façon fiable pour des passagers non répondants ;
  - id — identifiant technique.
- **Hypothèse** : Customer Type correspond au statut du programme de fidélité, donc connu à l'atterrissage.
- Codé dans `src/features.py` (`MODEL_FEATURES`).

### Choix du modèle
| Sans le type de voyage | Gain / 1 000 passagers | Précision |
|---|---|---|
| Hasard | 1 655 € | 0,566 |
| Règle : plus gros retards | 2 422 € | 0,642 |
| Règle : Eco puis retard (meilleure règle simple) | 4 744 € | 0,874 |
| Régression logistique | 4 551 € | 0,855 |
| **Gradient boosting** | **5 512 €** | **0,951** |

- **Retenu : gradient boosting** — +768 € par rapport à la meilleure règle simple ; la régression logistique fait moins bien que la règle.
- Pour mémoire, avec le type de voyage : règle « voyage perso puis retard » 5 565 €, gradient boosting 5 672 € (+107 € seulement : une règle simple suffirait si le motif était connu).
- Forêt aléatoire écartée : résultats non identiques d'une exécution à l'autre (exigence de reproductibilité).
- **Capacité** : on utilise les 10 % — la précision reste au-dessus de 95 % jusqu'à 10 %, chaque approche supplémentaire rapporte.

### Mineurs (protection des données — décision de Côme)
- Sans précaution, 23,7 % des passagers signalés seraient mineurs (contre 7,6 % des passagers).
- **Retenu : garder l'âge dans le modèle, ne jamais signaler un mineur** (`AGE_MINIMUM_SIGNALEMENT = 18`) → **5 386 €**, précision 0,939, 0 % de mineurs signalés (coût : −126 €, soit 2 %).
- Écarté : retirer l'âge du modèle → 4 973 € et encore 11,6 % de mineurs signalés (le modèle les repère par d'autres variables).
- Piste pour le rapport : aborder l'adulte accompagnant (non chiffrable avec nos données).

### Résultat attendu du dispositif (validation croisée)
Pour 1 000 passagers arrivants : 100 abordés, ≈ 94 réellement insatisfaits, ≈ 5 386 € de gain net, ≈ 5 approches inutiles (≈ 195 €).

## Volet 1 — leviers recommandés (Léa)

- <à compléter par Léa>

## Planning

- Rendu : <heure> — Gel des chiffres : <heure>
- Envoi du rendu : <qui>, <où>

## Évaluation finale sur test.csv

- Exécutée une seule fois le <date, heure> par Jeanne, après validation du modèle par le groupe (`notebooks/03_evaluation_finale_test.ipynb`).
- Résultat : <précision, gain net pour 1 000 passagers>
