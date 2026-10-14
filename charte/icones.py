"""Génère le jeu d'icônes de la charte (SVG) dans charte/icones/.

    python charte/icones.py

Chaque pictogramme est dessiné sur une grille de 24 × 24, puis posé dans une tuile
de couleur (carrée arrondie ou ronde), dans l'esprit de la signalétique d'aéroport.
- charte/icones/<nom>.svg          tuile carrée arrondie, couleur par défaut
- charte/icones/rond/<nom>.svg     tuile ronde
- charte/icones/noir/<nom>.svg     pictogramme seul, noir, fond transparent
- charte/icones/blanc/<nom>.svg    pictogramme seul, blanc, fond transparent
"""

from pathlib import Path

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "icones"

COULEURS = {
    "bleu": "#0055FF", "vert": "#009925", "orange": "#FF6B00", "jaune": "#FFDC00",
    "rose": "#FFB3C9", "brun": "#A88565", "noir": "#000000", "gris_clair": "#D9D9D9",
}
# Couleur du pictogramme sur chaque tuile (contraste suffisant pour un élément graphique).
ENCRE = {
    "bleu": "#FFFFFF", "vert": "#FFFFFF", "brun": "#FFFFFF", "noir": "#FFFFFF",
    "orange": "#000000", "jaune": "#000000", "rose": "#000000", "gris_clair": "#000000",
}

# {i} = couleur du pictogramme, {f} = couleur du fond (pour les découpes).
T = 'stroke="{i}" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" fill="none"'

PICTOS = {
    "avion": ("bleu", """
<path fill="{i}" d="M12 2.5c1 0 1.6 1 1.6 2.2v4.8l7.4 4.3v2l-7.4-2.2v4.3l2.2 1.7v1.6L12 20.3l-3.8.9v-1.6l2.2-1.7v-4.3L3 15.8v-2l7.4-4.3V4.7c0-1.2.6-2.2 1.6-2.2z"/>"""),
    "atterrissage": ("bleu", """
<g transform="translate(12 10.5) rotate(125) scale(0.78) translate(-12 -12)">
<path fill="{i}" d="M12 2.5c1 0 1.6 1 1.6 2.2v4.8l7.4 4.3v2l-7.4-2.2v4.3l2.2 1.7v1.6L12 20.3l-3.8.9v-1.6l2.2-1.7v-4.3L3 15.8v-2l7.4-4.3V4.7c0-1.2.6-2.2 1.6-2.2z"/></g>
<path {T} d="M3 21h18"/>"""),
    "passager": ("noir", """
<circle fill="{i}" cx="12" cy="6.3" r="3.1"/>
<path fill="{i}" d="M6.3 20.5v-4.8a5.7 5.7 0 0 1 11.4 0v4.8z"/>"""),
    "famille": ("rose", """
<circle fill="{i}" cx="8.8" cy="5.4" r="2.7"/>
<path fill="{i}" d="M4.2 20.5v-5.6a4.6 4.6 0 0 1 9.2 0v5.6z"/>
<circle fill="{i}" cx="17.4" cy="10.3" r="2.1"/>
<path fill="{i}" d="M14.3 20.5v-3.4a3.1 3.1 0 0 1 6.2 0v3.4z"/>"""),
    "valise": ("brun", """
<path {T} d="M9 7.5V5.6c0-.9.7-1.6 1.6-1.6h2.8c.9 0 1.6.7 1.6 1.6v1.9"/>
<rect fill="{i}" x="3.5" y="7.5" width="17" height="12.5" rx="2.6"/>
<path stroke="{f}" stroke-width="1.8" stroke-linecap="round" d="M8.5 10.5v6.5M15.5 10.5v6.5"/>"""),
    "siege": ("bleu", """
<path fill="{i}" d="M7.2 3h2.6c.7 0 1.2.5 1.2 1.2V13h6.2c1.2 0 2.2 1 2.2 2.2V17H8.7A2.7 2.7 0 0 1 6 14.3V4.2C6 3.5 6.5 3 7.2 3z"/>
<path {T} d="M9.5 17v3.8M16.5 17v3.8"/>"""),
    "horloge": ("orange", """
<circle {T} cx="12" cy="12" r="8.6"/>
<path {T} d="M12 7.4V12l3.3 2.2"/>"""),
    "wifi": ("bleu", """
<path {T} d="M3.6 9.4a12 12 0 0 1 16.8 0M6.8 12.8a7.4 7.4 0 0 1 10.4 0M9.8 16.1a3.1 3.1 0 0 1 4.4 0"/>
<circle fill="{i}" cx="12" cy="19.2" r="1.6"/>"""),
    "repas": ("jaune", """
<path {T} d="M7 3v6.2a2 2 0 0 0 4 0V3M9 9.5V21M16.5 21V3c-2.2 1.4-3.3 3.8-3.3 7.2v3.3h3.3"/>"""),
    "euro": ("vert", """
<path {T} d="M17.5 6.6A7.4 7.4 0 1 0 17.5 17.4M4.6 10.2h9.2M4.6 13.8h9.2"/>"""),
    "satisfait": ("vert", """
<circle fill="{i}" cx="12" cy="12" r="9.2"/>
<circle fill="{f}" cx="8.9" cy="10" r="1.35"/><circle fill="{f}" cx="15.1" cy="10" r="1.35"/>
<path stroke="{f}" stroke-width="2.1" stroke-linecap="round" fill="none" d="M8.2 13.9c2.1 2.7 5.5 2.7 7.6 0"/>"""),
    "mecontent": ("orange", """
<circle fill="{i}" cx="12" cy="12" r="9.2"/>
<circle fill="{f}" cx="8.9" cy="10" r="1.35"/><circle fill="{f}" cx="15.1" cy="10" r="1.35"/>
<path stroke="{f}" stroke-width="2.1" stroke-linecap="round" fill="none" d="M8.2 16.4c2.1-2.5 5.5-2.5 7.6 0"/>"""),
    "dialogue": ("bleu", """
<path fill="{i}" d="M6.5 3.5h11A2.5 2.5 0 0 1 20 6v7.5a2.5 2.5 0 0 1-2.5 2.5h-6.2L6.8 20v-4h-.3A2.5 2.5 0 0 1 4 13.5V6a2.5 2.5 0 0 1 2.5-2.5z"/>
<circle fill="{f}" cx="8.4" cy="9.8" r="1.25"/><circle fill="{f}" cx="12" cy="9.8" r="1.25"/><circle fill="{f}" cx="15.6" cy="9.8" r="1.25"/>"""),
    "cible": ("orange", """
<circle {T} cx="12" cy="12" r="8.6"/><circle {T} cx="12" cy="12" r="4.6"/>
<circle fill="{i}" cx="12" cy="12" r="1.7"/>"""),
    "graphique": ("bleu", """
<rect fill="{i}" x="3.5" y="12.5" width="4.4" height="8" rx="1.2"/>
<rect fill="{i}" x="9.8" y="7.5" width="4.4" height="13" rx="1.2"/>
<rect fill="{i}" x="16.1" y="3.5" width="4.4" height="17" rx="1.2"/>"""),
    "bouclier": ("noir", """
<path fill="{i}" d="M12 2.6l7.6 3v5.8c0 4.7-3.2 8.4-7.6 9.9-4.4-1.5-7.6-5.2-7.6-9.9V5.6z"/>
<path stroke="{f}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none" d="M8.5 12.1l2.4 2.4 4.6-4.8"/>"""),
    "confidentiel": ("noir", """
<path fill="{i}" d="M2.6 12C4.9 7.7 8.2 5.6 12 5.6s7.1 2.1 9.4 6.4c-2.3 4.3-5.6 6.4-9.4 6.4S4.9 16.3 2.6 12z"/>
<circle fill="{f}" cx="12" cy="12" r="3.3"/><circle fill="{i}" cx="12" cy="12" r="1.5"/>
<path stroke="{f}" stroke-width="5" stroke-linecap="round" d="M4.5 19.5l15-15"/>
<path stroke="{i}" stroke-width="2.3" stroke-linecap="round" d="M4.5 19.5l15-15"/>"""),
    "alerte": ("jaune", """
<path fill="{i}" stroke="{i}" stroke-width="2" stroke-linejoin="round" d="M12 3.4l9 15.9H3z"/>
<rect fill="{f}" x="10.9" y="8.6" width="2.2" height="6" rx="1.1"/>
<circle fill="{f}" cx="12" cy="17.1" r="1.25"/>"""),
    "valide": ("vert", """
<path stroke="{i}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" fill="none" d="M4.8 12.6l4.6 4.6 9.8-10.2"/>"""),
    "exclu": ("gris_clair", """
<path stroke="{i}" stroke-width="2.8" stroke-linecap="round" fill="none" d="M6.2 6.2l11.6 11.6M17.8 6.2L6.2 17.8"/>"""),
}


def picto(nom, encre, fond):
    corps = PICTOS[nom][1].replace("{T}", T)
    return corps.replace("{i}", encre).replace("{f}", fond)


def tuile(nom, couleur=None, forme="carre"):
    couleur = couleur or PICTOS[nom][0]
    fond, encre = COULEURS[couleur], ENCRE[couleur]
    if forme == "rond":
        base = f'<circle cx="24" cy="24" r="24" fill="{fond}"/>'
    else:
        base = f'<rect width="48" height="48" rx="12" fill="{fond}"/>'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="480" height="480">'
        f'{base}<g transform="translate(10 10) scale(1.1667)">{picto(nom, encre, fond)}</g></svg>\n'
    )


def seul(nom, encre):
    # Les découpes (yeux, coche…) prennent la couleur du fond prévu :
    # version noire sur le fond gris des slides, version blanche sur une slide bleue.
    fond = "#F4F4F4" if encre == "#000000" else "#0055FF"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="240" height="240">'
        f'{picto(nom, encre, fond)}</svg>\n'
    )


if __name__ == "__main__":
    for dossier in ["", "rond", "noir", "blanc"]:
        (SORTIE / dossier).mkdir(parents=True, exist_ok=True)
    for nom in PICTOS:
        (SORTIE / f"{nom}.svg").write_text(tuile(nom), encoding="utf-8")
        (SORTIE / "rond" / f"{nom}.svg").write_text(tuile(nom, forme="rond"), encoding="utf-8")
        (SORTIE / "noir" / f"{nom}.svg").write_text(seul(nom, "#000000"), encoding="utf-8")
        (SORTIE / "blanc" / f"{nom}.svg").write_text(seul(nom, "#FFFFFF"), encoding="utf-8")
    print(f"{len(PICTOS)} icônes générées dans {SORTIE}")
