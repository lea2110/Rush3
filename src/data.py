"""Chargement commun des données pour les trois notebooks.

clean_data.py (Léa) produit rush-3/data/clean/train_clean.csv.
Ce module ajoute les traitements décidés en synchro 1 et applique
exactement les mêmes étapes au fichier de test.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "rush-3" / "data" / "raw"
CLEAN_TRAIN = ROOT / "rush-3" / "data" / "clean" / "train_clean.csv"

RANDOM_STATE = 42
TARGET = "insatisfait"  # 1 = "neutral or dissatisfied", 0 = "satisfied"

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


def prepare(df, zero_as_missing=True):
    """Traitements communs à train et test (voir DECISIONS.md)."""
    df = df.drop(columns=["Unnamed: 0", "id"], errors="ignore").copy()

    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].str.strip()

    # Une note de 0 = pas de réponse ou service non applicable.
    if zero_as_missing:
        df[RATING_COLUMNS] = df[RATING_COLUMNS].replace(0, np.nan)

    df[TARGET] = (df["satisfaction"] != "satisfied").astype(int)
    return df.drop(columns=["satisfaction"])


def load_train(zero_as_missing=True):
    """Fichier d'entraînement nettoyé : le seul à utiliser pour explorer et modéliser."""
    return prepare(pd.read_csv(CLEAN_TRAIN, encoding="utf-8-sig"), zero_as_missing)


def load_test(zero_as_missing=True):
    """À appeler UNIQUEMENT dans notebooks/03_evaluation_finale_test.ipynb."""
    return prepare(pd.read_csv(RAW_DIR / "test.csv"), zero_as_missing)
