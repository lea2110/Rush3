# Rush 3 — Satisfaction client d'une compagnie aérienne

Bootcamp Data, Epitech Paris MSc MBA, octobre 2026.

Consultants Data / BI pour la direction Expérience Client d'une compagnie aérienne européenne, nous devons :

1. **Expliquer** ce qui fait la satisfaction des passagers et sur quoi la compagnie peut agir.
2. **Prédire** quels passagers sont probablement insatisfaits **au moment de l'atterrissage**, pour que les équipes puissent les aborder avant qu'ils quittent l'aéroport.
3. **Encadrer** ce nouvel usage des données (protection des données, enfants, ce que voit l'agent) et formuler des recommandations.

## Qui a fait quoi

| Membre | Responsabilité | Branche | Fichiers principaux |
|---|---|---|---|
| **Léa** | Nettoyage des données ; volet 1 — **Expliquer** : exploration, facteurs de satisfaction, recommandations budget | `explication` | `clean_data.py`, `notebooks/01_exploration_facteurs.ipynb` |
| **Jeanne** | Volet 2 — **Prédire** : variables connues à l'atterrissage, règle simple sans modèle, modèles, gain net, évaluation finale | `modeles` | `src/features.py`, `src/economics.py`, `notebooks/02_modeles.ipynb`, `notebooks/03_evaluation_finale_test.ipynb` |
| **Côme** | Volet 3 — **Encadrer et livrer** : protection des données, synthèse pour la direction, rapport, présentation, relecture des Pull Requests | `rapport` | `rapport/`, `DECISIONS.md`, `README.md` |

Le code commun (`src/data.py`) a été mis en place en début de projet ; chaque décision de traitement est tracée dans [`DECISIONS.md`](DECISIONS.md).

## Structure du dépôt

```
Rush3/
├── README.md
├── DECISIONS.md                 ← journal des décisions (traitement, variables, planning)
├── requirements.txt
├── clean_data.py                ← nettoyage du fichier d'entraînement (Léa)
├── rush-3/data/
│   ├── raw/                     ← train.csv, test.csv (fichiers d'origine, non modifiés)
│   └── clean/                   ← train_clean.csv + rapport_nettoyage.csv (produits par clean_data.py)
├── src/                         ← code partagé, importé par les notebooks
│   ├── data.py                  ← load_train() / load_test() : mêmes traitements pour les deux fichiers
│   ├── features.py              ← variables connues à l'atterrissage
│   └── economics.py             ← gain net (40 €, 600 €, 1/3, 1/2, capacité 10 %)
├── notebooks/
│   ├── 01_exploration_facteurs.ipynb    ← volet 1 (Léa)
│   ├── 02_modeles.ipynb                 ← volet 2 (Jeanne), train uniquement
│   └── 03_evaluation_finale_test.ipynb  ← volet 2 (Jeanne), exécuté UNE seule fois
├── figures/                     ← graphiques exportés par les notebooks
└── rapport/                     ← rapport PDF et présentation (Côme)
```

## Reproduire les résultats

```bash
pip install -r requirements.txt
python clean_data.py
```

Puis ouvrir les notebooks depuis le dossier `notebooks/` et les exécuter dans l'ordre (*Redémarrer et tout exécuter*) :

1. `01_exploration_facteurs.ipynb`
2. `02_modeles.ipynb`
3. `03_evaluation_finale_test.ipynb` — évaluation finale sur `test.csv`

Toutes les graines aléatoires sont fixées (`RANDOM_STATE = 42` dans `src/data.py`) : deux exécutions donnent les mêmes chiffres.

## Règles de travail

- **`test.csv` n'est lu que dans le notebook 03**, une seule fois, après le choix définitif du modèle. Il ne sert ni à explorer, ni à choisir les variables, ni à régler les modèles. Les modèles sont comparés en **validation croisée sur train**.
- **Un notebook = une personne** : on ne modifie pas le notebook d'un autre (Git fusionne mal les notebooks). Le code utile à plusieurs va dans `src/`.
- Les données se chargent toujours avec `load_train()` / `load_test()`, jamais en relisant les CSV à la main.
- Avant de committer un notebook : *Redémarrer et tout exécuter*, il doit tourner de haut en bas.
- Chaque chiffre cité dans le rapport doit être visible dans un notebook.

## Travailler avec Git

Chacun travaille sur sa branche et passe par une Pull Request pour intégrer son travail dans `main`.

Première fois :

```bash
git clone https://github.com/lea2110/Rush3.git
cd Rush3
git checkout explication   # Léa  —  modeles : Jeanne  —  rapport : Côme
```

Si le dépôt est déjà cloné : `git fetch` puis `git checkout <ta-branche>`.

En cours de travail (petits commits, préfixés par le volet : `1:`, `2:`, `3:`) :

```bash
git add notebooks/02_modeles.ipynb
git commit -m "2: baseline au hasard et gain net"
git push
```

Récupérer ce que les autres ont fusionné dans `main` :

```bash
git checkout main
git pull
git checkout modeles
git merge main
```

Intégrer son travail : ouvrir une **Pull Request** de sa branche vers `main` sur GitHub. Une autre personne relit, puis fusionne.

## Livrables

- **Rapport PDF** (8 pages max hors annexes), ouvert par une synthèse d'une page pour la direction : exploration, facteurs, modèles, recommandations, protection des données.
- **Code** : ce dépôt, qui reproduit chaque chiffre du rapport.
- **Présentation orale** devant la direction, suivie de questions sur nos choix analytiques.
