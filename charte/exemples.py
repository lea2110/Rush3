"""Génère les visuels d'exemple de la charte : planche des couleurs et graphique type.

    python charte/exemples.py

Les chiffres du graphique sont recopiés de DECISIONS.md (évaluation finale sur test) :
ce fichier sert à montrer le style. Les graphiques du rapport sont produits par les notebooks.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ICI = Path(__file__).resolve().parent
sys.path.append(str(ICI.parent))

from src.charte import COULEURS, appliquer, couleurs_barres  # noqa: E402

appliquer()


def planche_couleurs():
    nuancier = [
        ("Bleu", "bleu", "Recommandé,\nnotre modèle", "blanc"),
        ("Orange", "orange", "Insatisfaits,\nalerte", "noir"),
        ("Vert", "vert", "Satisfaits,\ngain", "noir"),
        ("Jaune", "jaune", "Point\nd'attention", "noir"),
        ("Rose", "rose", "Catégorie\nsecondaire", "noir"),
        ("Brun", "brun", "Catégorie\nsecondaire", "noir"),
        ("Noir", "noir", "Textes\net titres", "blanc"),
        ("Gris clair", "gris_clair", "Références,\ncomparaisons", "noir"),
        ("Fond", "fond", "Fond\ndes slides", "noir"),
    ]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    fig.patch.set_facecolor(COULEURS["fond"])
    ax.set_facecolor(COULEURS["fond"])
    ax.set_xlim(0, 9)
    ax.set_ylim(0.3, 2.9)
    ax.axis("off")
    for i, (nom, cle, role, texte) in enumerate(nuancier):
        ax.add_patch(FancyBboxPatch(
            (i + 0.08, 0.5), 0.84, 2.25,
            boxstyle="round,pad=0,rounding_size=0.2",
            facecolor=COULEURS[cle], edgecolor=COULEURS["gris_clair"], linewidth=1,
        ))
        ax.text(i + 0.2, 2.6, nom, color=COULEURS[texte], fontsize=12, fontweight="bold", va="top")
        ax.text(i + 0.2, 0.68, COULEURS[cle].upper(), color=COULEURS[texte], fontsize=10)
        ax.text(i + 0.2, 2.15, role, color=COULEURS[texte], fontsize=9.5, va="top", linespacing=1.3)
    ax.set_title("Charte Rush 3 — couleurs et rôles", loc="left", pad=8)
    fig.savefig(ICI / "palette.png", facecolor=COULEURS["fond"])
    plt.close(fig)


def graphique_type():
    options = ["Hasard", "Règle : Eco puis retard", "Modèle retenu"]
    gains = [1429, 4459, 5375]

    fig, ax = plt.subplots()
    barres = ax.barh(options, gains, color=couleurs_barres(options, "Modèle retenu"), height=0.6)
    ax.invert_yaxis()
    ax.bar_label(barres, labels=[f"{g:,} €".replace(",", " ") for g in gains],
                 padding=8, fontsize=14, fontweight="bold")
    ax.set_xlim(0, 6400)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xlabel("Gain net pour 1 000 passagers arrivants", color=COULEURS["gris"], fontweight="normal")
    ax.set_title("Le modèle rapporte 3,8 fois plus que le hasard")
    ax.text(0, -0.16, "Évaluation finale sur 25 976 passagers jamais vus · mineurs jamais signalés",
            transform=ax.transAxes, fontsize=11, color=COULEURS["gris"])
    fig.savefig(ICI / "exemple_graphique.png")
    plt.close(fig)


if __name__ == "__main__":
    planche_couleurs()
    graphique_type()
    print("Visuels générés dans", ICI)
