"""Charte graphique du projet (voir charte/CHARTE.md).

Dans un notebook :
    from src.charte import appliquer, COULEURS
    appliquer()
"""

from pathlib import Path

import matplotlib.pyplot as plt

STYLE = Path(__file__).resolve().parent.parent / "charte" / "charte.mplstyle"

COULEURS = {
    "noir": "#000000",
    "blanc": "#FFFFFF",
    "fond": "#F4F4F4",
    "gris": "#8A8A8A",
    "gris_clair": "#D9D9D9",
    "bleu": "#0055FF",
    "vert": "#009925",
    "orange": "#FF6B00",
    "jaune": "#FFDC00",
    "rose": "#FFB3C9",
    "brun": "#A88565",
}

# Rôles : toujours la même couleur pour la même idée, sur tous les graphiques.
ROLES = {
    "recommande": COULEURS["bleu"],      # notre modèle, notre recommandation
    "reference": COULEURS["gris_clair"], # hasard, règles simples, autres options
    "satisfait": COULEURS["vert"],
    "insatisfait": COULEURS["orange"],
    "attention": COULEURS["jaune"],      # point de vigilance (ex. mineurs)
}

# Ordre des couleurs quand plusieurs catégories sans rôle sont comparées.
CATEGORIES = [
    COULEURS["bleu"],
    COULEURS["orange"],
    COULEURS["vert"],
    COULEURS["brun"],
    COULEURS["rose"],
    COULEURS["jaune"],
]


def appliquer():
    """Applique la charte à tous les graphiques matplotlib/seaborn qui suivent."""
    plt.style.use(STYLE)


def couleurs_barres(etiquettes, recommande):
    """Bleu pour l'élément recommandé, gris clair pour les références."""
    return [ROLES["recommande"] if e == recommande else ROLES["reference"] for e in etiquettes]
