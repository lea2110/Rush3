
from pathlib import Path
import pandas as pd

# Racine du projet Rush3
BASE_DIR = Path(__file__).resolve().parent

# Fichier source : on lit uniquement le train
TRAIN_PATH = BASE_DIR / "rush-3" / "data" / "raw" / "train.csv"

# Dossier de destination, à la racine du projet
OUTPUT_DIR = BASE_DIR / "rush-3" / "data" / "clean"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLEAN_FILE = OUTPUT_DIR / "train_clean.csv"
REPORT_FILE = OUTPUT_DIR / "rapport_nettoyage.csv"

# --------------------------------------------------
# 2. COLONNES À CONTRÔLER
# --------------------------------------------------

RATING_COLUMNS = [
    "Inflight wifi service",
    "Departure/Arrival time convenient",
    "Ease of Online booking",
    "Gate location",
    "Food and drink",
    "Online boarding",
    "Seat comfort",
    "Inflight entertainment",
    "On-board service",
    "Leg room service",
    "Baggage handling",
    "Checkin service",
    "Inflight service",
    "Cleanliness",
]

TEXT_COLUMNS = [
    "Gender",
    "Customer Type",
    "Type of Travel",
    "Class",
    "satisfaction",
]


# --------------------------------------------------
# 3. CHARGEMENT DU TRAIN UNIQUEMENT
# --------------------------------------------------


if not TRAIN_PATH.is_file():
    raise FileNotFoundError(
        f"Fichier train.csv introuvable : {TRAIN_PATH}"
    )

df = pd.read_csv(TRAIN_PATH)

print("Fichier d'entraînement chargé.")
print(f"Dimensions initiales : {df.shape}")



# --------------------------------------------------
# 4. CRÉATION DU RAPPORT DE CONTRÔLE
# --------------------------------------------------

report = []

def add_report(controle, valeur, detail=""):
    """Ajoute une information au rapport de nettoyage."""
    report.append({
        "controle": controle,
        "valeur": valeur,
        "detail": detail,
    })


rows_before = len(df)
columns_before = len(df.columns)

add_report("Lignes initiales", rows_before)
add_report("Colonnes initiales", columns_before)

missing_before = df.isna().sum()


# --------------------------------------------------
# 5. SUPPRESSION DE L'INDEX TECHNIQUE
# --------------------------------------------------

if "Unnamed: 0" in df.columns:
    index_column = df["Unnamed: 0"]

    expected_index = pd.Series(
        range(len(df)),
        index=df.index
    )

    if index_column.equals(expected_index):
        df = df.drop(columns=["Unnamed: 0"])
        add_report(
            "Colonne supprimée",
            "Unnamed: 0",
            "Index séquentiel sans valeur métier."
        )
    else:
        add_report(
            "Colonne conservée",
            "Unnamed: 0",
            "Index non séquentiel : vérification manuelle."
        )
else:
    add_report(
        "Colonne d'index",
        "Absente",
        "Aucune suppression nécessaire."
    )


# --------------------------------------------------
# 6. NETTOYAGE DES TEXTES
# --------------------------------------------------

for column in df.select_dtypes(include=["object"]).columns:
    # Supprime les espaces en début et en fin de texte.
    df[column] = df[column].str.strip()

    # Une chaîne vide est une valeur manquante.
    df[column] = df[column].replace("", pd.NA)

add_report(
    "Textes",
    "Contrôlés",
    "Espaces superflus supprimés ; chaînes vides converties en NA."
)


# --------------------------------------------------
# 7. RECHERCHE DES DOUBLONS
# --------------------------------------------------

duplicates = int(df.duplicated().sum())

add_report(
    "Doublons exacts avant suppression",
    duplicates
)

if duplicates > 0:
    df = df.drop_duplicates().copy()

add_report(
    "Lignes supprimées pour doublon",
    duplicates
)


# --------------------------------------------------
# 8. CONTRÔLE DES IDENTIFIANTS
# --------------------------------------------------

if "id" in df.columns:
    duplicate_ids = int(df["id"].duplicated().sum())

    add_report(
        "Identifiants id dupliqués",
        duplicate_ids,
        "Contrôle uniquement ; aucune ligne supprimée sur ce critère."
    )


# --------------------------------------------------
# 9. CONTRÔLE DES NOTES DE SERVICE
# --------------------------------------------------

for column in RATING_COLUMNS:
    if column not in df.columns:
        add_report(
            f"Colonne absente : {column}",
            "ERREUR"
        )
        continue

    invalid = int(
        ((df[column] < 0) | (df[column] > 5)).sum()
    )

    add_report(
        f"Notes hors intervalle : {column}",
        invalid,
        "Valeurs attendues entre 0 et 5. Le zéro est valide."
    )


# --------------------------------------------------
# 10. CONTRÔLE DES AUTRES VALEURS NUMÉRIQUES
# --------------------------------------------------

if "Age" in df.columns:
    invalid_age = int(
        ((df["Age"] < 0) | (df["Age"] > 120)).sum()
    )
    add_report(
        "Âges hors intervalle 0-120",
        invalid_age
    )

if "Flight Distance" in df.columns:
    invalid_distance = int(
        (df["Flight Distance"] <= 0).sum()
    )
    add_report(
        "Distances inférieures ou égales à zéro",
        invalid_distance
    )

for column in [
    "Departure Delay in Minutes",
    "Arrival Delay in Minutes",
]:
    if column in df.columns:
        negative_delays = int((df[column] < 0).sum())
        add_report(
            f"Retards négatifs : {column}",
            negative_delays
        )


# --------------------------------------------------
# 11. CONTRÔLE DES VALEURS MANQUANTES
# --------------------------------------------------

for column in df.columns:
    missing = int(df[column].isna().sum())

    add_report(
        f"Valeurs manquantes : {column}",
        missing,
        "Conservées si elles ne peuvent pas être corrigées "
        "sans inventer une information."
    )


# --------------------------------------------------
# 12. EXPORT DU CSV NETTOYÉ
# --------------------------------------------------

df.to_csv(
    CLEAN_FILE,
    index=False,
    encoding="utf-8-sig"
)

add_report("Lignes finales", len(df))
add_report("Colonnes finales", len(df.columns))
add_report(
    "Fichier produit",
    str(CLEAN_FILE.relative_to(BASE_DIR))
)


# --------------------------------------------------
# 13. EXPORT DU RAPPORT
# --------------------------------------------------

report_df = pd.DataFrame(report)

report_df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# --------------------------------------------------
# 14. RÉSUMÉ DANS LE TERMINAL
# --------------------------------------------------

print("\n--- BILAN DU NETTOYAGE ---")
print(f"Lignes avant : {rows_before}")
print(f"Lignes après : {len(df)}")
print(f"Colonnes avant : {columns_before}")
print(f"Colonnes après : {len(df.columns)}")
print(f"Doublons supprimés : {duplicates}")

print("\nValeurs manquantes après nettoyage :")
print(df.isna().sum()[df.isna().sum() > 0])

print(f"\nCSV nettoyé : {CLEAN_FILE}")
print(f"Rapport : {REPORT_FILE}")
print("\nNettoyage terminé.")
