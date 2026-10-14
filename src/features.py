"""Variables connues par la compagnie au moment de l'atterrissage.

Seules ces variables peuvent servir au modèle de détection.
Liste provisoire : à valider en synchro 1 (voir DECISIONS.md).
"""

NUMERIC_FEATURES = [
    "Age",
    "Flight Distance",
    "Departure Delay in Minutes",
    "Arrival Delay in Minutes",
]

CATEGORICAL_FEATURES = [
    "Customer Type",   # hypothèse : statut du programme de fidélité
    "Type of Travel",  # à tester avec et sans : motif pas forcément connu
    "Class",
]

# Exclues du modèle de détection, avec la raison (à reprendre dans le rapport).
EXCLUDED = {
    "Gender": "écart d'insatisfaction quasi nul, risque de discrimination",
    "notes de service": "connues seulement après l'enquête, pas à l'atterrissage",
    "id": "identifiant technique",
}

LANDING_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# --- Modèle retenu (à confirmer en synchro 2) ---
# Gradient boosting sans le type de voyage : motif du voyage pas connu
# de façon fiable à l'atterrissage pour des passagers non répondants.
MODEL_CATEGORICAL_FEATURES = [c for c in CATEGORICAL_FEATURES if c != "Type of Travel"]
MODEL_FEATURES = NUMERIC_FEATURES + MODEL_CATEGORICAL_FEATURES

# Les mineurs ne sont jamais signalés aux équipes (protection des données).
AGE_MINIMUM_SIGNALEMENT = 18
