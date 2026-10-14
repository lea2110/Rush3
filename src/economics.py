"""Valeur économique d'une liste de passagers à aborder (hypothèses de la direction)."""

import numpy as np

COST_APPROACH = 40       # € par passager abordé
LOST_REVENUE = 600       # € de revenu futur perdu si le passager ne revole pas
CHURN_RATE = 1 / 3       # part des neutres/insatisfaits qui ne revolent pas
RECOVERY_RATE = 1 / 2    # part des partants ramenés par une approche
CAPACITY = 0.10          # part maximale des passagers arrivants abordables

# Gain espéré en abordant un vrai insatisfait, avant le coût de l'approche : 100 €.
VALUE_TRUE_POSITIVE = LOST_REVENUE * CHURN_RATE * RECOVERY_RATE


def gain_net(y_true, scores, capacity=CAPACITY):
    """Aborde la part `capacity` des passagers aux scores les plus élevés.

    y_true : 1 = neutre ou insatisfait ; scores : plus haut = plus à risque.
    """
    y_true = np.asarray(y_true)
    scores = np.asarray(scores, dtype=float)
    n = len(y_true)
    k = int(np.floor(capacity * n))
    top = np.argsort(-scores, kind="stable")[:k]
    true_positives = int(y_true[top].sum())
    gain = true_positives * VALUE_TRUE_POSITIVE - k * COST_APPROACH
    return {
        "passagers_abordes": k,
        "insatisfaits_abordes": true_positives,
        "precision": true_positives / k if k else 0.0,
        "rappel": float(true_positives / y_true.sum()) if y_true.sum() else 0.0,
        "gain_net": gain,
        "gain_net_pour_1000": gain / n * 1000,
    }


# Seuil de rentabilité : précision minimale pour que l'approche rapporte.
BREAK_EVEN_PRECISION = COST_APPROACH / VALUE_TRUE_POSITIVE  # 0,40
