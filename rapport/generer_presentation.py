"""Génère la présentation PowerPoint du Rush 3 en suivant la charte (charte/CHARTE.md).

    pip install python-pptx
    python rapport/generer_presentation.py

Sortie : rapport/presentation_rush3.pptx
Les chiffres viennent des notebooks 01 (Léa), 02 et 03 (Jeanne) et de DECISIONS.md.
"""

import re
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

RACINE = Path(__file__).resolve().parent.parent
ICONES = RACINE / "charte" / "icones" / "png"
SORTIE = RACINE / "rapport" / "presentation_rush3.pptx"

NOIR, BLANC, FOND = "000000", "FFFFFF", "F4F4F4"
GRIS, GRIS_CLAIR, TEXTE_2 = "8A8A8A", "D9D9D9", "444444"
BLEU, VERT, ORANGE, JAUNE, ROSE, BRUN = "0055FF", "009925", "FF6B00", "FFDC00", "FFB3C9", "A88565"
POLICE = "Arial"  # repli de la charte (Inter si installée partout)

W, H, M = 13.333, 7.5, 0.556  # slide 16:9, marge de 80 px
NB_SLIDES = 21


def rgb(hexa):
    return RGBColor.from_string(hexa)


def fond(slide):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(FOND)


def forme(slide, kind, x, y, w, h, couleur, rayon=None, ligne=None):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(couleur)
    if ligne:
        s.line.color.rgb = rgb(ligne)
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if rayon is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, rayon / min(w, h))
    return s


def carte(slide, x, y, w, h, couleur=BLANC, rayon=0.22, ligne=None):
    return forme(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, couleur, rayon, ligne)


def insecables(txt):
    """Évite qu'un nombre soit coupé de son unité ou de ses milliers en fin de ligne."""
    txt = re.sub(r"(\d) (?=\d{3}\b)", "\\1\u00a0", txt)
    return re.sub(r" (€|%)", "\u00a0\\1", txt)


def texte(slide, x, y, w, h, contenu, taille=16, gras=False, couleur=NOIR,
          align=PP_ALIGN.LEFT, ancre=MSO_ANCHOR.TOP, interligne=None):
    """contenu : str, ou liste de paragraphes ; un paragraphe = str ou liste de (texte, options)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = ancre
    paragraphes = contenu if isinstance(contenu, list) else [contenu]
    for i, para in enumerate(paragraphes):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if interligne:
            p.line_spacing = interligne
        morceaux = para if isinstance(para, list) else [(para, {})]
        for txt, opt in morceaux:
            r = p.add_run()
            r.text = insecables(txt)
            f = r.font
            f.name = POLICE
            f.size = Pt(opt.get("taille", taille))
            f.bold = opt.get("gras", gras)
            f.color.rgb = rgb(opt.get("couleur", couleur))
        if isinstance(para, list) and para and para[0][1].get("espace_avant"):
            p.space_before = Pt(para[0][1]["espace_avant"])
    return tb


def icone(slide, nom, x, y, taille=0.67, rond=False):
    chemin = ICONES / ("rond" if rond else "") / f"{nom}.png"
    return slide.shapes.add_picture(str(chemin), Inches(x), Inches(y), Inches(taille), Inches(taille))


def pastilles(slide, couleurs, x=M, y=0.5, d=0.18):
    for i, c in enumerate(couleurs):
        forme(slide, MSO_SHAPE.OVAL, x + i * (d + 0.07), y, d, d, c,
              ligne=GRIS_CLAIR if c in (BLANC, FOND) else None)


def titre(slide, txt, couleurs):
    pastilles(slide, couleurs)
    texte(slide, M, 0.85, W - 2 * M, 1.0, txt, taille=30, gras=True, ancre=MSO_ANCHOR.TOP, interligne=0.95)


def pied(slide, txt, numero=None):
    numero = len(prs.slides)  # numéro réel de la slide, même si on en insère
    texte(slide, M, 6.92, 9.0, 0.3, txt, taille=11, couleur=GRIS, ancre=MSO_ANCHOR.MIDDLE)
    # Points d'étape : noir = vu, pilule bleue = slide actuelle, gris clair = à venir
    d, g, long = 0.1, 0.07, 0.28
    largeur = (NB_SLIDES - 1) * (d + g) + long
    x = W - M - largeur
    for k in range(1, NB_SLIDES + 1):
        if k == numero:
            forme(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 7.02, long, d, BLEU, rayon=d / 2)
            x += long + g
        else:
            forme(slide, MSO_SHAPE.OVAL, x, 7.02, d, d, NOIR if k < numero else GRIS_CLAIR)
            x += d + g


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


def graphique_barres(slide, x, y, w, h, categories, valeurs, couleurs, format_nombre,
                     maximum=None, minimum=None):
    donnees = CategoryChartData()
    donnees.categories = categories
    donnees.add_series("valeurs", valeurs)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), donnees)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name = POLICE
    ch.font.size = Pt(13)
    plot = ch.plots[0]
    plot.gap_width = 55
    plot.vary_by_categories = False
    serie = plot.series[0]
    serie.invert_if_negative = False
    for i, c in enumerate(couleurs):
        pt = serie.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(c)
        pt.format.line.fill.background()
        # Sinon PowerPoint inverse (blanc) la couleur d'une barre négative
        from lxml import etree
        ns = "http://schemas.openxmlformats.org/drawingml/2006/chart"
        dpt = pt.format._element  # élément <c:dPt> du point
        if dpt is not None and dpt.find(f"{{{ns}}}invertIfNegative") is None:
            inv = etree.Element(f"{{{ns}}}invertIfNegative")
            inv.set("val", "0")
            dpt.find(f"{{{ns}}}idx").addnext(inv)
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = format_nombre
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(13)
    dl.font.bold = True
    dl.font.name = POLICE
    dl.font.color.rgb = rgb(NOIR)
    va = ch.value_axis
    va.visible = False
    va.has_major_gridlines = False
    va.has_minor_gridlines = False
    if maximum is not None:
        va.maximum_scale = maximum
    if minimum is not None:
        va.minimum_scale = minimum
    ca = ch.category_axis
    ca.reverse_order = True
    from pptx.enum.chart import XL_TICK_LABEL_POSITION
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    ca.has_major_gridlines = False
    ca.format.line.color.rgb = rgb(GRIS_CLAIR)
    ca.tick_labels.font.size = Pt(13)
    ca.tick_labels.font.name = POLICE
    ca.tick_labels.font.color.rgb = rgb(NOIR)
    return ch


def ligne_icone(slide, x, y, nom, titre_ligne, detail, w=5.2, taille=0.55, rond=False, gris=False):
    pic = icone(slide, nom, x, y, taille, rond)
    if gris:
        # Option écartée : icône pâlie (transparence via un voile gris clair)
        voile = forme(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, taille, taille, BLANC, rayon=taille * 0.25)
        voile.fill.fore_color.rgb = rgb(BLANC)
        _transparence(voile, 45)
    texte(slide, x + taille + 0.25, y - 0.02, w - taille - 0.25, taille + 0.1,
          [[(titre_ligne, {"gras": True, "taille": 17})], [(detail, {"taille": 13, "couleur": TEXTE_2})]],
          ancre=MSO_ANCHOR.MIDDLE)
    return pic


def _transparence(shape, pourcent):
    from lxml import etree
    srgb = shape.fill._xPr.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr")
    alpha = etree.SubElement(srgb, "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha")
    alpha.set("val", str(int((100 - pourcent) * 1000)))


def tableau(slide, x, y, largeurs, entetes, rangees, hauteur=0.55, taille=14, colonne_forte=None):
    """Tableau à la charte : en-tête sur fond gris, cellules blanches, colonne_forte en bleu."""
    tbl = slide.shapes.add_table(len(rangees) + 1, len(entetes), Inches(x), Inches(y),
                                 Inches(sum(largeurs)), Inches(hauteur * (len(rangees) + 1))).table
    for j, lw in enumerate(largeurs):
        tbl.columns[j].width = Inches(lw)
    for i in range(len(rangees) + 1):
        tbl.rows[i].height = Inches(hauteur)
        for j in range(len(entetes)):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            fort = colonne_forte is not None and j == colonne_forte
            cell.fill.fore_color.rgb = rgb(BLEU if (fort and i == 0) else (FOND if i == 0 else BLANC))
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            r = tf.paragraphs[0].add_run()
            r.text = insecables(entetes[j] if i == 0 else rangees[i - 1][j])
            r.font.name = POLICE
            r.font.size = Pt(taille)
            r.font.bold = i == 0 or j == 0 or fort
            couleur = BLANC if (fort and i == 0) else (NOIR if (i == 0 or j == 0 or fort) else TEXTE_2)
            r.font.color.rgb = rgb(couleur)
    tbl._tbl.tblPr.set("firstRow", "0")
    tbl._tbl.tblPr.set("bandRow", "0")
    return tbl


def barre_mini(slide, x, y, w, valeur, maximum, couleur, h=0.16):
    carte(slide, x, y, w, h, GRIS_CLAIR, rayon=h / 2)
    carte(slide, x, y, max(h, w * valeur / maximum), h, couleur, rayon=h / 2)


# ---------------------------------------------------------------------------
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
VIDE = prs.slide_layouts[6]


def nouvelle():
    s = prs.slides.add_slide(VIDE)
    fond(s)
    return s


# 1 — Couverture -------------------------------------------------------------
s = nouvelle()
carte(s, M, 0.75, W - 2 * M, 3.55, rayon=0.3)
pastilles(s, [VERT, BLEU, NOIR, GRIS_CLAIR, BLANC], x=M + 0.45, y=1.12)
texte(s, M + 0.45, 1.45, 8.6, 1.3, "Satisfaction", taille=84, gras=True, ancre=MSO_ANCHOR.MIDDLE)
icone(s, "satisfait", 9.35, 1.62, 0.98)
icone(s, "avion", 10.48, 1.62, 0.98)
icone(s, "passager", M + 0.45, 2.92, 0.98, rond=True)
texte(s, M + 1.65, 2.75, 8.0, 1.3, "passagers", taille=84, gras=True, ancre=MSO_ANCHOR.MIDDLE)
carte(s, M, 4.55, W - 2 * M, 1.65, rayon=0.3)
pastilles(s, [ROSE, BRUN, ORANGE, JAUNE, BLEU, NOIR], x=M + 0.45, y=4.88)
texte(s, M + 0.45, 5.2, 7.0, 0.7, "Où investir, et qui aborder à l'arrivée", taille=26, gras=True, ancre=MSO_ANCHOR.MIDDLE)
for i, (nom, rond) in enumerate([("valise", False), ("horloge", True), ("wifi", False), ("famille", True), ("repas", False)]):
    icone(s, nom, 7.95 + i * 0.92, 4.97, 0.78, rond)
pied(s, "Léa · Jeanne · Côme — Epitech Bootcamp Data, Rush 3 · octobre 2026", 1)
notes(s, "Côme — Introduction (20 s). Nous sommes consultants data pour la direction Expérience Client. "
         "Plus de la moitié des passagers jugent leur vol neutre ou décevant. Vous nous avez posé deux questions : "
         "où investir votre budget, et qui aborder à l'arrivée avant qu'il quitte l'aéroport. Léa répond à la première, "
         "Jeanne à la seconde, et je vous présenterai les conditions pour le faire dans le respect des données.")

# 2 — Synthèse ---------------------------------------------------------------
s = nouvelle()
titre(s, "En bref : trois réponses pour la direction", [BLEU, VERT, NOIR])
cols = [
    ("graphique", "43,3 %", "de passagers satisfaits",
     "58 % en voyage pro, 10 % en voyage perso. Leviers : parcours numérique, wi-fi, cabines."),
    ("euro", "5 375 €", "gagnés pour 1 000 passagers",
     "Le modèle désigne les 10 % à aborder : 94 sur 100 sont vraiment mécontents."),
    ("bouclier", "0 enfant", "signalé aux équipes",
     "Genre exclu ; ni score, ni âge, ni étiquette « mécontent » montrés aux agents."),
]
cw = (W - 2 * M - 2 * 0.35) / 3
for i, (ic, chiffre, legende, detail) in enumerate(cols):
    x = M + i * (cw + 0.35)
    carte(s, x, 2.0, cw, 4.55)
    icone(s, ic, x + 0.4, 2.4, 0.8)
    texte(s, x + 0.4, 3.4, cw - 0.8, 1.0, chiffre, taille=54, gras=True, couleur=BLEU if i == 1 else NOIR)
    texte(s, x + 0.4, 4.45, cw - 0.8, 0.75, legende, taille=18, gras=True)
    texte(s, x + 0.4, 5.3, cw - 0.8, 1.1, detail, taille=15, couleur=TEXTE_2)
pied(s, "Synthèse", 2)
notes(s, "Côme — Synthèse (40 s). Trois messages : 1) la satisfaction est de 43 %, et elle dépend surtout du motif du voyage "
         "et de la classe ; le budget doit cibler le parcours numérique, le wi-fi et les cabines. 2) Notre modèle permet "
         "d'aborder les bons passagers : sur 100 abordés, 94 sont vraiment mécontents, soit 5 375 € gagnés pour 1 000 passagers. "
         "3) Le dispositif respecte les données : aucun enfant signalé, le minimum d'information pour les agents.")

# 3 — Données et choix de traitement -----------------------------------------
s = nouvelle()
titre(s, "103 904 avis pour analyser, 25 976 pour le test final", [BLEU, GRIS_CLAIR])
carte(s, M, 2.0, 4.6, 4.55)
texte(s, M + 0.4, 2.35, 3.9, 0.9, "103 904", taille=48, gras=True)
texte(s, M + 0.4, 3.2, 3.9, 0.9, "passagers ayant répondu (train) : exploration, facteurs, choix du modèle",
      taille=15, couleur=TEXTE_2)
texte(s, M + 0.4, 4.3, 3.9, 0.9, "25 976", taille=48, gras=True, couleur=BLEU)
texte(s, M + 0.4, 5.15, 3.9, 0.9, "passagers « du mois prochain » (test) : lus une seule fois, à la toute fin",
      taille=15, couleur=TEXTE_2)
carte(s, M + 4.95, 2.0, W - 2 * M - 4.95, 4.55)
x0 = M + 5.35
lignes = [
    ("valide", "Une note de 0 = pas de réponse", "et non une mauvaise note, comme le précise le sujet"),
    ("horloge", "310 retards d'arrivée manquants", "remplacés par le retard au départ (corrélation 0,965)"),
    ("exclu", "Identifiant retiré, aucun doublon", "il ne dit rien du passager"),
    ("cible", "Modèles comparés en validation croisée", "sur train uniquement, en 5 parts"),
    ("graphique", "Résultats reproductibles", "graines fixées : mêmes chiffres à chaque exécution"),
]
for i, (ic, t1, t2) in enumerate(lignes):
    ligne_icone(s, x0, 2.3 + i * 0.83, ic, t1, t2, w=W - M - x0 - 0.3)
pied(s, "Données et méthode — Léa", 3)
notes(s, "Léa — Données (40 s). Nous avons travaillé sur 103 904 réponses. Le second fichier, 25 976 passagers, représente "
         "le mois prochain : nous ne l'avons ouvert qu'une fois, à la fin, pour mesurer le modèle retenu. Nos choix : "
         "un 0 veut dire « pas de réponse », pas une mauvaise note ; les 310 retards manquants sont remplacés par le retard "
         "au départ, presque identique ; l'identifiant est retiré. Tout est reproductible.")

# 4 — Satisfaction par profil (Léa) ------------------------------------------
s = nouvelle()
titre(s, "La satisfaction dépend surtout du motif et de la classe", [VERT, GRIS_CLAIR])
carte(s, M, 2.0, 8.3, 4.55)
cats = ["Voyage pro", "Voyage perso", "Classe Business", "Classe Eco Plus", "Classe Eco",
        "Clients fidèles", "Clients non fidèles"]
vals = [58.3, 10.2, 69.4, 24.6, 18.6, 47.7, 23.7]
graphique_barres(s, M + 0.3, 2.2, 7.7, 4.15, cats, vals, [VERT] * len(vals), '0.0" %"', maximum=85, minimum=0)
carte(s, M + 8.65, 2.0, W - 2 * M - 8.65, 4.55)
x0 = M + 9.0
texte(s, x0, 2.35, 3.0, 0.8, "43,3 %", taille=44, gras=True)
texte(s, x0, 3.15, 3.0, 0.5, "de satisfaits en moyenne", taille=15, couleur=TEXTE_2)
texte(s, x0, 3.85, 3.2, 0.4, "Force du lien (V de Cramér)", taille=15, gras=True)
for i, (lib, v) in enumerate([("Classe", 0.505), ("Motif du voyage", 0.449), ("Âge", 0.269), ("Genre", 0.012)]):
    yy = 4.35 + i * 0.52
    texte(s, x0, yy, 1.9, 0.3, lib, taille=13)
    texte(s, x0 + 2.3, yy, 0.8, 0.3, f"{v:.2f}".replace(".", ","), taille=13, gras=True, align=PP_ALIGN.RIGHT)
    barre_mini(s, x0, yy + 0.3, 3.1, v, 0.55, VERT if v > 0.1 else GRIS_CLAIR, h=0.1)
pied(s, "Volet 1 — Expliquer · Léa · taux de satisfaits par groupe, fichier d'entraînement", 4)
notes(s, "Léa — Profils (50 s). 58 % de satisfaits en voyage pro, seulement 10 % en voyage perso. En classe Business, 69 % ; "
         "en Eco, 19 %. Les clients fidèles sont deux fois plus satisfaits. Le genre ne joue presque pas (43 % chez les hommes "
         "comme chez les femmes). La classe et le motif du voyage sont de loin les liens les plus forts.")

# 5 — Services (Léa) ----------------------------------------------------------
s = nouvelle()
titre(s, "L'embarquement en ligne fait la plus grande différence", [BLEU, GRIS_CLAIR])
carte(s, M, 2.0, 8.3, 4.55)
services = ["Embarquement en ligne", "Divertissement à bord", "Wi-Fi en vol", "Confort du siège",
            "Service à bord", "Espace pour les jambes", "Propreté", "Réservation en ligne", "Enregistrement",
            "Bagages", "Service en vol", "Repas et boissons", "Porte d'embarquement", "Horaires pratiques"]
ecarts = [1.45, 1.07, 0.99, 0.93, 0.84, 0.83, 0.81, 0.63, 0.60, 0.59, 0.58, 0.56, 0.00, -0.14]
coul = [BLEU] * 3 + [GRIS_CLAIR] * 11
graphique_barres(s, M + 0.3, 2.1, 7.7, 4.35, services, ecarts, coul, '0.00', maximum=1.75, minimum=-0.3)
carte(s, M + 8.65, 2.0, W - 2 * M - 8.65, 4.55)
x0 = M + 9.0
icone(s, "wifi", x0, 2.35, 0.7)
texte(s, x0, 3.25, 3.2, 1.6,
      [[("Comment lire : ", {"gras": True, "taille": 15}),
        ("écart de note moyenne (sur 5) entre passagers satisfaits et mécontents.", {"taille": 15})]],
      couleur=TEXTE_2)
texte(s, x0, 4.6, 3.2, 1.7,
      [[("Porte d'embarquement et horaires : ", {"gras": True, "taille": 15}),
        ("aucun lien avec la satisfaction.", {"taille": 15})]], couleur=TEXTE_2)
pied(s, "Volet 1 — Expliquer · Léa · notes de 0 exclues (non-réponses)", 5)
notes(s, "Léa — Services (50 s). Pour chaque service, nous comparons la note moyenne des satisfaits et des mécontents. "
         "L'embarquement en ligne arrive en tête (1,45 point d'écart), puis le divertissement et le wi-fi. À l'inverse, "
         "l'emplacement de la porte et la commodité des horaires ne sont pas liés à la satisfaction.")

# 6 — Leviers par motif (Léa) ------------------------------------------------
s = nouvelle()
titre(s, "Les leviers changent selon le motif du voyage", [BLEU, BRUN])
cw = (W - 2 * M - 0.35) / 2
blocs = [
    ("valise", "Voyage pro", "71 655 passagers · 58 % satisfaits",
     [("Embarquement en ligne", 1.54), ("Divertissement à bord", 1.31), ("Confort du siège", 1.14)],
     "Priorité : gain de temps et confort"),
    ("famille", "Voyage perso", "32 249 passagers · 10 % satisfaits",
     [("Wi-Fi en vol", 2.10), ("Réservation en ligne", 1.88), ("Embarquement en ligne", 1.33)],
     "Priorité : le numérique"),
]
for i, (ic, nom, sous, items, prio) in enumerate(blocs):
    x = M + i * (cw + 0.35)
    carte(s, x, 2.0, cw, 4.55)
    icone(s, ic, x + 0.4, 2.35, 0.75, rond=True)
    texte(s, x + 1.4, 2.35, cw - 1.8, 0.45, nom, taille=24, gras=True)
    texte(s, x + 1.4, 2.8, cw - 1.8, 0.35, sous, taille=14, couleur=TEXTE_2)
    for k, (lib, v) in enumerate(items):
        yy = 3.55 + k * 0.78
        texte(s, x + 0.4, yy, cw - 2.0, 0.35, lib, taille=17, gras=True)
        texte(s, x + cw - 1.4, yy, 1.0, 0.35, f"{v:.2f}".replace(".", ","), taille=17, gras=True,
              couleur=BLEU, align=PP_ALIGN.RIGHT)
        barre_mini(s, x + 0.4, yy + 0.42, cw - 0.8, v, 2.2, BLEU)
    texte(s, x + 0.4, 5.95, cw - 0.8, 0.4, prio, taille=15, gras=True, couleur=TEXTE_2)
pied(s, "Volet 1 — Expliquer · Léa · écart de note moyenne entre satisfaits et mécontents, par segment", 6)
notes(s, "Léa — Segments (50 s). Chez les voyageurs pro, la satisfaction se joue sur l'embarquement en ligne, le divertissement "
         "et le siège. Chez les voyageurs perso, c'est presque uniquement le numérique : wi-fi (2,10 points d'écart) et "
         "réservation en ligne. Une même dépense n'aura donc pas le même effet partout.")

# 7 — Associé / actionnable / causal (Léa) -----------------------------------
s = nouvelle()
titre(s, "Lié à la satisfaction ne veut pas dire « cause »", [BLEU, JAUNE, GRIS_CLAIR])
carte(s, M, 2.0, W - 2 * M, 4.55)
entetes = ["Facteur", "Lien avec la satisfaction", "La compagnie peut agir ?", "Cause prouvée ?", "Action proposée"]
rangees = [
    ["Wi-Fi en vol", "Fort (2,10 en voyage perso)", "Oui : réseau", "Non démontré", "Fiabiliser la connexion"],
    ["Embarquement en ligne", "Fort (1,45)", "Oui : parcours numérique", "Non démontré", "Simplifier l'application"],
    ["Siège et divertissement", "Fort en voyage pro", "Oui, mais coûteux", "Non démontré", "Cibler les lignes affaires"],
    ["Classe et motif du voyage", "Très fort (0,51 et 0,45)", "Pas directement", "Non : profil du client", "Adapter l'offre par segment"],
    ["Porte et horaires", "Aucun", "—", "—", "Pas de budget"],
]
tbl = s.shapes.add_table(len(rangees) + 1, 5, Inches(M + 0.35), Inches(2.25), Inches(W - 2 * M - 0.7), Inches(3.3)).table
largeurs = [2.35, 2.45, 2.2, 1.95, 2.57]
for j, lw in enumerate(largeurs):
    tbl.columns[j].width = Inches(lw)
for i in range(len(rangees) + 1):
    tbl.rows[i].height = Inches(0.55)
    for j in range(5):
        cell = tbl.cell(i, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(FOND if i == 0 else BLANC)
        cell.margin_left = cell.margin_right = Inches(0.12)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = entetes[j] if i == 0 else rangees[i - 1][j]
        r.font.name = POLICE
        r.font.size = Pt(14)
        r.font.bold = i == 0 or j == 0
        r.font.color.rgb = rgb(NOIR if (i == 0 or j in (0, 4)) else TEXTE_2)
tbl_xml = tbl._tbl
tbl_xml.tblPr.set("firstRow", "0")
tbl_xml.tblPr.set("bandRow", "0")
icone(s, "alerte", M + 0.35, 5.8, 0.5)
texte(s, M + 1.05, 5.78, W - 2 * M - 1.4, 0.55,
      "Pour prouver un effet : améliorer un service sur une partie des vols seulement, et comparer la satisfaction.",
      taille=15, gras=True, ancre=MSO_ANCHOR.MIDDLE)
pied(s, "Volet 1 — Expliquer · Léa", 7)
notes(s, "Léa — Associé, actionnable, causal (50 s). Un lien statistique ne prouve pas une cause. La classe et le motif "
         "du voyage sont très liés à la satisfaction, mais ce sont des caractéristiques du client : on ne peut pas agir dessus "
         "directement. Le wi-fi et l'embarquement en ligne, eux, sont des leviers sur lesquels investir. Pour prouver l'effet, "
         "il faudra tester l'amélioration sur une partie des vols et comparer.")

# 8 — Variables à l'atterrissage (Jeanne) ------------------------------------
s = nouvelle()
titre(s, "Le modèle n'utilise que ce qui est connu à l'atterrissage", [BLEU, GRIS_CLAIR])
cw = (W - 2 * M - 0.35) / 2
for i, (ic, nom) in enumerate([("valide", "Utilisé"), ("exclu", "Écarté")]):
    x = M + i * (cw + 0.35)
    carte(s, x, 2.0, cw, 4.55)
    icone(s, ic, x + 0.4, 2.3, 0.55)
    texte(s, x + 1.2, 2.3, cw - 1.6, 0.55, nom, taille=24, gras=True, ancre=MSO_ANCHOR.MIDDLE)
x = M + 0.4
for k, (ic, t1, t2) in enumerate([
    ("siege", "Classe du billet", "billet"),
    ("passager", "Âge et statut de fidélité", "réservation ; l'âge n'est jamais montré aux agents"),
    ("avion", "Distance du vol", "plan de vol"),
    ("horloge", "Retards au départ et à l'arrivée", "opérations"),
]):
    ligne_icone(s, x, 3.15 + k * 0.82, ic, t1, t2, w=cw - 0.8)
x = M + cw + 0.35 + 0.4
for k, (ic, t1, t2, g) in enumerate([
    ("wifi", "Notes de service", "n'existent qu'après l'enquête", True),
    ("valise", "Motif du voyage", "déclaré dans l'enquête, inconnu pour les autres", True),
    ("confidentiel", "Genre", "aucun effet, risque de discrimination", False),
]):
    ligne_icone(s, x, 3.15 + k * 0.82, ic, t1, t2, w=cw - 0.8, gris=g)
pied(s, "Volet 2 — Prédire · Jeanne", 8)
notes(s, "Jeanne — Variables (40 s). Vos équipes agissent à l'atterrissage : l'enquête n'existe pas encore, et la plupart des "
         "passagers n'y répondront jamais. Nous n'utilisons donc que ce que la compagnie sait déjà : classe, âge, fidélité, "
         "distance et retards. Nous écartons les notes de service, le motif du voyage, déclaré dans l'enquête, et le genre, "
         "qui ne change rien et poserait un risque de discrimination.")

# 9 — Règle du jeu (Jeanne) -------------------------------------------------
s = nouvelle()
titre(s, "Comment nous avons jugé chaque approche", [BLEU, GRIS_CLAIR])
cw = (W - 2 * M - 0.35) / 2
# Gauche : le gain en euros
carte(s, M, 2.0, cw, 4.55)
icone(s, "euro", M + 0.4, 2.3, 0.6)
texte(s, M + 1.2, 2.3, cw - 1.6, 0.6, "1. On juge en euros", taille=19, gras=True,
      ancre=MSO_ANCHOR.MIDDLE)
texte(s, M + 0.4, 3.1, cw - 0.8, 0.7,
      "Chaque approche classe les passagers du plus au moins à risque. Les équipes abordent les 10 % en tête de liste.",
      taille=14, couleur=TEXTE_2)
for k, (signe, couleur_signe, t1, t2) in enumerate([
    ("+60 €", VERT, "un vrai mécontent abordé", "1/3 × 1/2 × 600 € de revenu gardé, moins 40 € d'approche"),
    ("−40 €", ORANGE, "un passager satisfait abordé", "l'approche est dépensée pour rien"),
]):
    yy = 4.0 + k * 0.9
    carte(s, M + 0.4, yy, 1.45, 0.62, couleur_signe, rayon=0.31)
    texte(s, M + 0.4, yy, 1.45, 0.62, signe, taille=20, gras=True, couleur=NOIR,
          align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
    texte(s, M + 2.1, yy - 0.04, cw - 2.5, 0.7, [[(t1, {"gras": True, "taille": 15})], [(t2, {"taille": 12, "couleur": TEXTE_2})]],
          ancre=MSO_ANCHOR.MIDDLE)
texte(s, M + 0.4, 5.85, cw - 0.8, 0.5,
      [[("Rentable dès que ", {}), ("40 %", {"gras": True}), (" des passagers abordés sont mécontents.", {})]],
      taille=14)
# Droite : la validation croisée
x = M + cw + 0.35
carte(s, x, 2.0, cw, 4.55)
icone(s, "cible", x + 0.4, 2.3, 0.6)
texte(s, x + 1.2, 2.3, cw - 1.6, 0.6, "2. Le même examen pour tous", taille=19, gras=True, ancre=MSO_ANCHOR.MIDDLE)
texte(s, x + 0.4, 3.1, cw - 0.8, 0.7,
      "Les 103 904 avis sont coupés en 5 parts. On apprend sur 4, on note la 5ᵉ, cinq fois de suite.",
      taille=14, couleur=TEXTE_2)
bw, bh, g = 0.62, 0.26, 0.08
for ligne in range(5):
    for col in range(5):
        forme(s, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.4 + col * (bw + g), 3.95 + ligne * (bh + g), bw, bh,
              BLEU if col == ligne else GRIS_CLAIR, rayon=0.06)
xl = x + 0.4 + 5 * (bw + g) + 0.2
for k, (c, lib) in enumerate([(GRIS_CLAIR, "apprend"), (BLEU, "est noté")]):
    forme(s, MSO_SHAPE.ROUNDED_RECTANGLE, xl, 4.05 + k * 0.45, 0.3, 0.2, c, rayon=0.05)
    texte(s, xl + 0.42, 3.98 + k * 0.45, 1.6, 0.34, lib, taille=13, ancre=MSO_ANCHOR.MIDDLE)
texte(s, x + 0.4, 5.75, cw - 0.8, 0.7,
      [[("Chaque passager est noté par un modèle qui ne l'a jamais vu. ", {}),
        ("Le fichier test reste fermé jusqu'à la fin.", {"gras": True})]],
      taille=14)
pied(s, "Volet 2 — Prédire · Jeanne · méthode", 9)
notes(s, "Jeanne — Règle du jeu (50 s). Pour comparer les approches, il faut la même règle du jeu. D'abord, on juge en euros "
         "avec vos propres chiffres : chaque approche classe les passagers et vos équipes abordent les 10 % en tête. Un vrai "
         "mécontent abordé rapporte 60 € en moyenne, un passager satisfait abordé coûte 40 €. Ensuite, on fait passer à tous "
         "le même examen : on coupe les 103 904 avis en 5 parts, on apprend sur 4 et on note la 5e, cinq fois. Chaque passager "
         "est ainsi noté par un modèle qui ne l'a jamais vu, comme vos passagers du mois prochain. Le fichier test, lui, est "
         "resté fermé jusqu'à la toute fin.")

# 10 — Cinq approches testées (Jeanne) ----------------------------------------
s = nouvelle()
titre(s, "Cinq approches testées, de la plus simple à la plus fine", [BLEU, GRIS_CLAIR])
carte(s, M, 2.0, W - 2 * M, 4.55)
approches = [
    ("Hasard", "on aborde 10 % des passagers sans choisir", 1655, GRIS_CLAIR, ""),
    ("Règle : plus gros retards", "on aborde les passagers les plus en retard", 2422, GRIS_CLAIR, ""),
    ("Règle : Eco puis retard", "la meilleure règle qu'un agent peut appliquer seul", 4744, GRIS, ""),
    ("Régression logistique", "additionne un poids par information", 4551, GRIS_CLAIR, "moins bien que la règle"),
    ("Gradient boosting", "combine les informations entre elles", 5512, BLEU, "retenu"),
]
xb, wb = M + 6.1, 4.6
for k, (nom, comment, v, c, etiquette) in enumerate(approches):
    yy = 2.3 + k * 0.78
    texte(s, M + 0.4, yy, 5.5, 0.7, [[(nom, {"gras": True, "taille": 17})], [(comment, {"taille": 13, "couleur": TEXTE_2})]],
          ancre=MSO_ANCHOR.MIDDLE)
    barre_mini(s, xb, yy + 0.24, wb, v, 6000, c, h=0.26)
    texte(s, xb + wb + 0.15, yy + 0.12, 1.3, 0.5, f"{v:,} €".replace(",", " "), taille=17, gras=True,
          couleur=BLEU if c == BLEU else NOIR, ancre=MSO_ANCHOR.MIDDLE)
    if etiquette:
        fc = NOIR if etiquette == "retenu" else BLANC
        pil = carte(s, xb + wb - 2.25 if etiquette != "retenu" else xb + wb - 1.15, yy - 0.12,
                    2.25 if etiquette != "retenu" else 1.15, 0.32, fc, rayon=0.16,
                    ligne=None if etiquette == "retenu" else GRIS_CLAIR)
        texte(s, xb + wb - (2.25 if etiquette != "retenu" else 1.15), yy - 0.12, 2.25 if etiquette != "retenu" else 1.15,
              0.32, etiquette, taille=11, gras=True, couleur=BLANC if etiquette == "retenu" else TEXTE_2,
              align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
icone(s, "exclu", M + 0.4, 6.18, 0.32)
texte(s, M + 0.85, 6.15, W - 2 * M - 1.2, 0.38,
      [[("Forêt aléatoire aussi testée, puis écartée : ", {"gras": True}),
        ("résultats différents à chaque exécution, alors que les chiffres doivent être reproductibles.", {})]],
      taille=13, ancre=MSO_ANCHOR.MIDDLE)
pied(s, "Volet 2 — Prédire · Jeanne · gain net pour 1 000 passagers, validation croisée sur train, sans motif du voyage", 10)
notes(s, "Jeanne — Les approches (60 s). Nous sommes partis du plus simple. Au hasard : 1 655 € pour 1 000 passagers. "
         "Aborder les plus retardés : 2 422 €. La meilleure règle qu'un agent peut appliquer seul, la classe Eco d'abord puis "
         "les plus retardés : 4 744 €. C'est le score à battre. La régression logistique, le modèle le plus classique, fait "
         "moins bien que cette règle : elle additionne un poids par information, sans voir les combinaisons. Le gradient "
         "boosting atteint 5 512 €, soit 768 € de plus que la règle. Nous avons aussi testé une forêt aléatoire, écartée car "
         "elle ne donnait pas les mêmes chiffres d'une exécution à l'autre.")

# 11 — D'où vient le gradient boosting (Jeanne) -------------------------------
s = nouvelle()
titre(s, "Gradient boosting : des petites règles qui se corrigent", [BLEU, GRIS_CLAIR])
carte(s, M, 2.0, 7.4, 4.55)
texte(s, M + 0.4, 2.3, 6.6, 0.45, "Comment il décide", taille=19, gras=True)
etapes = [
    ("1", "Une première petite règle", "« Classe Eco ? » : elle trie déjà grossièrement les passagers."),
    ("2", "Une deuxième corrige les erreurs", "« Client peu fidèle ? Retard de plus de 15 min ? »"),
    ("…", "Et ainsi de suite, une centaine de fois", "chaque règle s'attaque à ce que les précédentes ont raté."),
    ("=", "Le score de risque", "la somme de tous ces avis : on aborde les 10 % les plus élevés."),
]
for k, (num, t1, t2) in enumerate(etapes):
    yy = 2.95 + k * 0.86
    forme(s, MSO_SHAPE.OVAL, M + 0.4, yy + 0.06, 0.55, 0.55, BLEU if num == "=" else NOIR)
    texte(s, M + 0.4, yy + 0.06, 0.55, 0.55, num, taille=18, gras=True, couleur=BLANC,
          align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
    texte(s, M + 1.2, yy, 5.9, 0.7, [[(t1, {"gras": True, "taille": 16})], [(t2, {"taille": 13, "couleur": TEXTE_2})]],
          ancre=MSO_ANCHOR.MIDDLE)
x = M + 7.75
carte(s, x, 2.0, W - M - x, 4.55)
texte(s, x + 0.4, 2.3, 4.0, 0.45, "D'où ça vient", taille=19, gras=True)
histoire = [
    ("1990", "Robert Schapire : des règles faibles, combinées, donnent une règle forte (« boosting »)."),
    ("1995", "Yoav Freund et Robert Schapire : AdaBoost, premier algorithme largement utilisé."),
    ("2001", "Jerome Friedman (Stanford) : le gradient boosting, chaque règle corrige l'erreur restante."),
    ("Aujourd'hui", "méthode de référence sur les données en tableau ; nous utilisons la version de scikit-learn."),
]
for k, (date, txt) in enumerate(histoire):
    yy = 2.9 + k * 0.88
    texte(s, x + 0.4, yy, 4.0, 0.8, [[(date, {"gras": True, "taille": 15, "couleur": BLEU})], [(txt, {"taille": 12, "couleur": TEXTE_2})]])
pied(s, "Volet 2 — Prédire · Jeanne · HistGradientBoostingClassifier (scikit-learn), une centaine d'arbres de décision", 11)
notes(s, "Jeanne — Le gradient boosting (60 s). Le principe est simple. Une première petite règle trie grossièrement les "
         "passagers, par exemple : est-il en classe Eco ? Elle se trompe sur certains. Une deuxième règle se concentre sur ces "
         "erreurs : est-il peu fidèle, a-t-il eu du retard ? Et ainsi de suite, une centaine de fois. Le score final est la "
         "somme de tous ces avis. C'est pour ça qu'il fait mieux que la régression logistique : il voit les combinaisons, "
         "comme « Eco et peu fidèle et en retard ». L'idée vient de Robert Schapire en 1990 : des règles faibles, combinées, "
         "donnent une règle forte. Jerome Friedman, à Stanford, a formalisé le gradient boosting en 2001. C'est aujourd'hui "
         "la méthode de référence sur ce type de données.")

# 12 — Pourquoi celui-là (Jeanne) ----------------------------------------------
s = nouvelle()
titre(s, "Pourquoi le gradient boosting : quatre critères", [BLEU, NOIR, GRIS_CLAIR])
carte(s, M, 2.0, W - 2 * M, 4.55)
tableau(s, M + 0.35, 2.3, [2.6, 2.2, 2.2, 2.1, 2.42],
        ["Critère", "Règle : Eco puis retard", "Régression logistique", "Forêt aléatoire", "Gradient boosting"],
        [
            ["Gain pour 1 000 passagers", "4 744 €", "4 551 €", "moins bon*", "5 512 €"],
            ["Connu à l'atterrissage", "oui", "oui", "oui", "oui"],
            ["Mêmes chiffres à chaque fois", "oui", "oui", "non", "oui"],
            ["Explicable à la direction", "très facile", "oui", "moyen", "oui, par ce qui pèse"],
            ["Verdict", "référence à battre", "écartée", "écartée", "retenu"],
        ], hauteur=0.6, taille=14, colonne_forte=4)
texte(s, M + 0.35, 6.05, W - 2 * M - 0.7, 0.4,
      "* testée avec le motif du voyage : 5 609 € contre 5 672 € pour le gradient boosting.",
      taille=12, couleur=GRIS)
pied(s, "Volet 2 — Prédire · Jeanne · validation croisée sur train, sans motif du voyage", 12)
notes(s, "Jeanne — Le choix (50 s). Nous n'avons pas choisi seulement sur le score. Quatre critères : ce que ça rapporte, "
         "le fait de n'utiliser que des informations connues à l'atterrissage, la reproductibilité, et la possibilité de vous "
         "l'expliquer. La règle simple est la plus facile à expliquer, mais elle rapporte 768 € de moins pour 1 000 passagers. "
         "La régression logistique fait moins bien que la règle. La forêt aléatoire ne donne pas deux fois le même résultat. "
         "Le gradient boosting coche les quatre cases, et je vais vous montrer sur quoi il se base.")

# 13 — Avec ou sans motif (Jeanne) --------------------------------------------
s = nouvelle()
titre(s, "Sans le motif du voyage, un modèle devient utile", [BLEU, GRIS_CLAIR])
cw = (W - 2 * M - 0.35) / 2
blocs = [
    ("Si le motif du voyage était connu", [("Meilleure règle simple", 5565, GRIS), ("Modèle", 5672, NOIR)],
     "+107 €", "une règle simple suffirait", False),
    ("Sans le motif : notre cas", [("Meilleure règle simple (Eco puis retard)", 4744, GRIS),
                                             ("Modèle retenu", 5512, BLEU)],
     "+768 €", "le modèle fait la différence", True),
]
for i, (nom, barres, delta, legende, choix) in enumerate(blocs):
    x = M + i * (cw + 0.35)
    carte(s, x, 2.0, cw, 4.55)
    texte(s, x + 0.4, 2.3, cw - 0.8, 0.5, nom, taille=20, gras=True)
    if choix:
        pil = carte(s, x + cw - 2.15, 2.3, 1.75, 0.42, NOIR, rayon=0.21)
        texte(s, x + cw - 2.15, 2.3, 1.75, 0.42, "Notre choix", taille=14, gras=True, couleur=BLANC,
              align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
    for k, (lib, v, c) in enumerate(barres):
        yy = 3.1 + k * 0.95
        texte(s, x + 0.4, yy, cw - 2.0, 0.35, lib, taille=15, couleur=TEXTE_2)
        texte(s, x + cw - 1.9, yy, 1.5, 0.35, f"{v:,} €".replace(",", " "), taille=17, gras=True, align=PP_ALIGN.RIGHT)
        barre_mini(s, x + 0.4, yy + 0.42, cw - 0.8, v, 6000, c, h=0.26)
    texte(s, x + 0.4, 5.15, cw - 0.8, 0.8, delta, taille=44, gras=True, couleur=BLEU if choix else NOIR)
    texte(s, x + 0.4, 5.95, cw - 0.8, 0.4, legende, taille=15, gras=True, couleur=TEXTE_2)
pied(s, "Volet 2 — Prédire · Jeanne · gain net pour 1 000 passagers, validation croisée sur train", 9)
notes(s, "Jeanne — Pourquoi un modèle (50 s). Le motif du voyage prédit très bien l'insatisfaction : si on le connaissait, "
         "une règle simple, « voyage perso d'abord », rapporterait presque autant qu'un modèle. Mais la compagnie ne le "
         "connaît pas pour les passagers qui n'ont pas répondu. Sans lui, la meilleure règle tombe à 4 744 €, et notre modèle "
         "rapporte 768 € de plus pour 1 000 passagers. C'est là qu'il se justifie.")

# 14 — Ce qui guide le modèle (Jeanne) ----------------------------------------
s = nouvelle()
titre(s, "Ce qui guide le modèle, et qui il désigne", [BLEU, ORANGE, GRIS_CLAIR])
carte(s, M, 2.0, 6.0, 4.55)
texte(s, M + 0.4, 2.3, 5.2, 0.45, "Ce qui pèse dans sa décision", taille=19, gras=True)
poids = [("Classe du billet", 0.216), ("Âge", 0.064), ("Fidélité", 0.064),
         ("Retard à l'arrivée", 0.017), ("Distance du vol", 0.009), ("Retard au départ", 0.001)]
for k, (lib, v) in enumerate(poids):
    yy = 2.9 + k * 0.5
    texte(s, M + 0.4, yy, 2.2, 0.36, lib, taille=14, gras=k == 0, ancre=MSO_ANCHOR.MIDDLE)
    barre_mini(s, M + 2.65, yy + 0.1, 2.95, v, 0.22, BLEU if k == 0 else (NOIR if v > 0.05 else GRIS_CLAIR), h=0.16)
texte(s, M + 0.4, 5.95, 5.2, 0.5,
      "On brouille une information à la fois : plus le modèle se trompe ensuite, plus elle comptait.",
      taille=12, couleur=TEXTE_2)
x = M + 6.35
carte(s, x, 2.0, W - M - x, 4.55)
texte(s, x + 0.4, 2.3, 5.0, 0.45, "Le portrait des passagers signalés", taille=19, gras=True)
texte(s, x + 3.15, 2.85, 1.0, 0.3, "Signalés", taille=12, gras=True, align=PP_ALIGN.RIGHT)
texte(s, x + 4.25, 2.85, 1.0, 0.3, "Tous", taille=12, couleur=GRIS, align=PP_ALIGN.RIGHT)
portrait = [("En classe Eco", "80 %", "45 %"), ("Peu fidèles", "61 %", "18 %"), ("Âge médian", "33 ans", "40 ans"),
            ("Retard médian", "13 min", "0 min"), ("Vraiment mécontents", "95 %", "57 %")]
for k, (lib, a, b) in enumerate(portrait):
    yy = 3.25 + k * 0.55
    texte(s, x + 0.4, yy, 2.7, 0.4, lib, taille=15, ancre=MSO_ANCHOR.MIDDLE)
    texte(s, x + 3.05, yy, 1.1, 0.4, a, taille=17, gras=True, couleur=BLEU, align=PP_ALIGN.RIGHT, ancre=MSO_ANCHOR.MIDDLE)
    texte(s, x + 4.25, yy, 1.0, 0.4, b, taille=15, couleur=GRIS, align=PP_ALIGN.RIGHT, ancre=MSO_ANCHOR.MIDDLE)
texte(s, x + 0.4, 6.05, 5.0, 0.4, "En une phrase : des passagers en Eco, peu fidèles, plutôt jeunes, un peu retardés.",
      taille=12, gras=True)
pied(s, "Volet 2 — Prédire · Jeanne · importance par permutation et portrait des 10 % signalés, train", 14)
notes(s, "Jeanne — Ce qui guide le modèle (50 s). Pour savoir sur quoi il se base, on brouille une information à la fois "
         "et on regarde combien il se trompe ensuite. La classe du billet compte de loin le plus, puis l'âge et la fidélité ; "
         "les retards et la distance comptent peu. Résultat : il désigne surtout des passagers en Eco, 80 % contre 45 % en "
         "moyenne, peu fidèles, plutôt jeunes et un peu retardés. Et 95 % d'entre eux sont vraiment mécontents. "
         "Vous pouvez l'expliquer en une phrase à votre comité.")

# 15 — 94 sur 100 (Jeanne) ---------------------------------------------------
s = nouvelle()
titre(s, "Sur 100 passagers abordés, 94 sont vraiment mécontents", [BLEU, ORANGE])
carte(s, M, 2.0, 6.9, 4.55)
texte(s, M + 0.45, 2.3, 3.8, 2.4, "94", taille=180, gras=True, couleur=BLEU, ancre=MSO_ANCHOR.MIDDLE)
icone(s, "mecontent", M + 3.55, 3.75, 0.85, rond=True)
texte(s, M + 0.45, 4.9, 6.0, 1.3,
      "Le modèle choisit les 10 % de passagers les plus à risque : ce sont presque toujours les bons.",
      taille=20, gras=True)
x = M + 7.25
for k, (ic, chiffre, leg) in enumerate([("euro", "5 375 €", "gagnés pour 1 000 passagers arrivants"),
                                        ("graphique", "× 3,8", "par rapport à des passagers pris au hasard"),
                                        ("dialogue", "6 sur 100", "approches inutiles, environ 250 € pour 1 000 passagers")]):
    yy = 2.0 + k * 1.58
    carte(s, x, yy, W - M - x, 1.4)
    icone(s, ic, x + 0.35, yy + 0.35, 0.7)
    texte(s, x + 1.35, yy + 0.2, W - M - x - 1.6, 0.6, chiffre, taille=30, gras=True)
    texte(s, x + 1.35, yy + 0.82, W - M - x - 1.6, 0.45, leg, taille=13, couleur=TEXTE_2)
pied(s, "Volet 2 — Prédire · Jeanne · évaluation finale sur 25 976 passagers jamais vus, mineurs exclus", 10)
notes(s, "Jeanne — Résultat (50 s). Vos équipes peuvent aborder un passager sur dix. Le modèle donne un score de risque à chacun "
         "et désigne les 10 % les plus à risque. Testé sur 26 000 passagers qu'il n'avait jamais vus : 94 abordés sur 100 sont "
         "vraiment mécontents. Calcul : 94 mécontents, un sur trois serait parti, l'approche en ramène la moitié, soit environ "
         "16 clients gardés à 600 € ; moins 100 approches à 40 €. Environ 5 400 € pour 1 000 passagers.")

# 11 — Graphique test (Jeanne) -----------------------------------------------
s = nouvelle()
titre(s, "Sur des passagers jamais vus, le modèle bat les règles", [BLEU, GRIS_CLAIR])
carte(s, M, 2.0, 8.3, 4.55)
graphique_barres(s, M + 0.3, 2.3, 7.7, 3.95, ["Hasard", "Règle : Eco puis retard", "Modèle retenu"],
                 [1429, 4459, 5375], [GRIS_CLAIR, GRIS_CLAIR, BLEU], '#,##0" €"', maximum=6600, minimum=0)
carte(s, M + 8.65, 2.0, W - 2 * M - 8.65, 4.55)
x0 = M + 9.0
texte(s, x0, 2.35, 3.2, 0.7, "+916 €", taille=40, gras=True, couleur=BLEU)
texte(s, x0, 3.05, 3.2, 0.6, "par rapport à la meilleure règle simple", taille=14, couleur=TEXTE_2)
texte(s, x0, 3.95, 3.2, 0.4, "Un résultat stable", taille=17, gras=True)
texte(s, x0, 4.4, 3.2, 1.9,
      [[("Validation croisée : ", {"gras": True}), ("5 386 €, 93,9 %", {})],
       [("Test final : ", {"gras": True, "espace_avant": 6}), ("5 375 €, 93,8 %", {})],
       [("Le chiffre annoncé est fiable.", {"espace_avant": 6})]],
      taille=13, couleur=TEXTE_2)
pied(s, "Volet 2 — Prédire · Jeanne · gain net pour 1 000 passagers arrivants, test.csv utilisé une seule fois", 11)
notes(s, "Jeanne — Comparaison (40 s). Au hasard, on gagnerait 1 429 € ; avec la meilleure règle qu'un agent pourrait appliquer "
         "sans outil, 4 459 € ; avec le modèle, 5 375 €. Le résultat sur ces passagers jamais vus est presque identique à celui "
         "de notre validation croisée : 5 386 €. La performance annoncée n'est pas surestimée. Je passe la parole à Côme "
         "pour les conditions d'usage.")

# 12 — Mineurs (Côme) ---------------------------------------------------------
s = nouvelle()
titre(s, "Aucun enfant n'est jamais signalé aux équipes", [JAUNE, NOIR])
cw = (W - 2 * M - 2 * 0.35) / 3
blocs = [
    (JAUNE, "alerte", "23,7 %", "des passagers signalés seraient mineurs sans précaution, contre 7,6 % des passagers"),
    (BLANC, "famille", "0 %", "après exclusion des mineurs du signalement"),
    (BLANC, "bouclier", "−2 %", "de gain seulement : 5 386 € au lieu de 5 512 € pour 1 000 passagers"),
]
for i, (fc, ic, chiffre, txt) in enumerate(blocs):
    x = M + i * (cw + 0.35)
    carte(s, x, 2.0, cw, 3.55, fc)
    if fc == JAUNE:  # pas de tuile jaune sur une carte jaune : pastille noire
        forme(s, MSO_SHAPE.OVAL, x + 0.4, 2.35, 0.75, 0.75, NOIR)
        texte(s, x + 0.4, 2.35, 0.75, 0.75, "!", taille=30, gras=True, couleur=JAUNE,
              align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
    else:
        icone(s, ic, x + 0.4, 2.35, 0.75, rond=True)
    texte(s, x + 0.4, 3.25, cw - 0.8, 1.0, chiffre, taille=54, gras=True)
    texte(s, x + 0.4, 4.3, cw - 0.8, 1.1, txt, taille=15)
carte(s, M, 5.8, W - 2 * M, 0.75)
icone(s, "exclu", M + 0.3, 5.92, 0.5)
texte(s, M + 1.0, 5.8, W - 2 * M - 1.3, 0.75,
      [[("Retirer l'âge du modèle ne suffirait pas : ", {"gras": True}),
        ("−539 € et encore 11,6 % de mineurs signalés.", {})]],
      taille=15, ancre=MSO_ANCHOR.MIDDLE)
pied(s, "Volet 3 — Encadrer · Côme", 12)
notes(s, "Côme — Mineurs (50 s). Sans précaution, près d'un passager signalé sur quatre serait un enfant. Nous avons décidé "
         "qu'aucun mineur n'est jamais signalé : cela ne coûte que 2 % du gain. Retirer l'âge du modèle semblait plus "
         "respectueux, mais le modèle retrouverait quand même des enfants par d'autres indices, et perdrait plus : "
         "c'est justement l'âge qui permet de les exclure. L'âge n'est jamais montré aux agents.")

# 13 — Conditions RGPD (Côme) ------------------------------------------------
s = nouvelle()
titre(s, "Un nouvel usage des données, sous quatre conditions", [NOIR, BLEU, ROSE])
gw = (W - 2 * M - 0.35) / 2
gh = (4.55 - 0.35) / 2
blocs = [
    ("dialogue", "Informer et permettre de refuser",
     "Nouvelle finalité : mise à jour de la politique de confidentialité, intérêt légitime, droit d'opposition simple, analyse d'impact."),
    ("famille", "Protéger les enfants",
     "Aucun mineur signalé. Le profilage des enfants appelle une protection renforcée."),
    ("cible", "Limiter les informations utilisées",
     "Classe, fidélité, distance, retards et âge. Genre et motif du voyage exclus."),
    ("confidentiel", "Montrer le minimum aux agents",
     "Ni score, ni âge, ni étiquette « mécontent » ; signalements effacés après le vol."),
]
for i, (ic, t1, t2) in enumerate(blocs):
    x = M + (i % 2) * (gw + 0.35)
    y = 2.0 + (i // 2) * (gh + 0.35)
    carte(s, x, y, gw, gh)
    icone(s, ic, x + 0.4, y + 0.38, 0.75, rond=True)
    texte(s, x + 1.4, y + 0.35, gw - 1.8, 0.45, t1, taille=19, gras=True)
    texte(s, x + 1.4, y + 0.85, gw - 1.8, 1.1, t2, taille=14, couleur=TEXTE_2)
pied(s, "Volet 3 — Encadrer · Côme", 13)
notes(s, "Côme — Conditions (50 s). L'enquête servait à mesurer la satisfaction ; signaler des passagers qui n'ont jamais "
         "répondu est un nouvel usage. Il est acceptable à quatre conditions : informer les passagers et leur permettre de "
         "refuser, sur la base de l'intérêt légitime et après une analyse d'impact ; protéger les enfants ; limiter les "
         "informations utilisées ; montrer le minimum aux agents et ne pas conserver les signalements.")

# 14 — Ce que voit l'agent (Côme) --------------------------------------------
s = nouvelle()
titre(s, "Ce que l'agent voit, et ce qu'il ne voit jamais", [BLEU, NOIR])
# Tablette
carte(s, M, 2.0, 6.0, 4.55, GRIS_CLAIR, rayon=0.35)
carte(s, M + 0.25, 2.25, 5.5, 4.05, BLANC, rayon=0.22)
x0 = M + 0.6
texte(s, x0, 2.5, 4.8, 0.35, "Vol 1234 · arrivée 14:35 · porte 21", taille=13, couleur=GRIS)
icone(s, "dialogue", x0, 3.0, 0.7)
texte(s, x0 + 0.95, 2.98, 3.9, 0.75, [[("Siège 12B", {"gras": True, "taille": 24})],
                                      [("À accueillir en priorité", {"taille": 15, "couleur": TEXTE_2})]])
icone(s, "horloge", x0, 4.05, 0.5)
texte(s, x0 + 0.75, 4.05, 4.1, 0.5, "Motif : retard de 45 minutes", taille=16, gras=True, ancre=MSO_ANCHOR.MIDDLE)
texte(s, x0, 4.85, 4.8, 1.2,
      [[("Action suggérée : ", {"gras": True}),
        ("demander comment s'est passé le vol, proposer une collation ou une aide pour la correspondance.", {})]],
      taille=15, couleur=TEXTE_2)
# Jamais montré
x1 = M + 6.35
carte(s, x1, 2.0, W - M - x1, 4.55)
texte(s, x1 + 0.4, 2.3, 5.0, 0.5, "Jamais affiché", taille=22, gras=True)
for k, lib in enumerate(["Le score de risque", "L'âge ou le genre", "Une étiquette « mécontent »",
                         "Les réponses à l'enquête"]):
    yy = 3.0 + k * 0.8
    icone(s, "exclu", x1 + 0.4, yy, 0.5)
    texte(s, x1 + 1.15, yy, 4.5, 0.5, lib, taille=17, gras=True, ancre=MSO_ANCHOR.MIDDLE)
pied(s, "Volet 3 — Encadrer · Côme · exemple d'écran (vol fictif)", 14)
notes(s, "Côme — Écran agent (40 s). Concrètement, l'agent ne voit qu'un siège, un motif factuel comme un retard, et une "
         "action simple et positive. Il ne voit jamais le score, l'âge, le genre, ni une étiquette « mécontent ».")

# 15 — Où investir (Léa) -----------------------------------------------------
s = nouvelle()
titre(s, "Où investir : le service atteint ceux qu'on n'aborde pas", [VERT, BLEU, GRIS_CLAIR])
recos = [
    ("cible", "Parcours numérique", "embarquement en ligne (voyage pro), réservation en ligne (voyage perso)", BLEU),
    ("wifi", "Wi-Fi en vol", "le service le plus pénalisant pour les voyageurs perso (écart de 2,10)", BLEU),
    ("siege", "Cabines", "confort du siège et divertissement, d'abord sur les lignes affaires", BLEU),
    ("exclu", "Pas de budget", "pour l'emplacement des portes et les horaires, sans lien avec la satisfaction", GRIS_CLAIR),
]
for k, (ic, t1, t2, c) in enumerate(recos):
    yy = 2.0 + k * 1.18
    carte(s, M, yy, 8.3, 1.0)
    forme(s, MSO_SHAPE.OVAL, M + 0.3, yy + 0.27, 0.45, 0.45, c)
    texte(s, M + 0.3, yy + 0.27, 0.45, 0.45, str(k + 1) if k < 3 else "–", taille=16, gras=True,
          couleur=BLANC if c == BLEU else NOIR, align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
    icone(s, ic, M + 7.45, yy + 0.22, 0.55)
    texte(s, M + 1.0, yy + 0.15, 6.3, 0.7, [[(t1, {"gras": True, "taille": 17})], [(t2, {"taille": 13, "couleur": TEXTE_2})]],
          ancre=MSO_ANCHOR.MIDDLE)
x0 = M + 8.65
carte(s, x0, 2.0, W - M - x0, 4.54)
icone(s, "mecontent", x0 + 0.4, 2.35, 0.75, rond=True)
texte(s, x0 + 0.4, 3.3, 3.2, 0.9, "470", taille=54, gras=True)
texte(s, x0 + 0.4, 4.25, 3.2, 1.4,
      "mécontents sur 1 000 passagers ne pourront pas être abordés : seule l'amélioration du service les atteint.",
      taille=14, couleur=TEXTE_2)
pied(s, "Volet 1 — Expliquer · Léa", 15)
notes(s, "Léa — Budget (50 s). Même avec le meilleur modèle, les équipes ne peuvent aborder qu'un passager sur dix : environ "
         "470 mécontents sur 1 000 ne seront jamais abordés. Pour eux, le seul levier est le service. Nos priorités : le "
         "parcours numérique, le wi-fi en vol, puis les cabines sur les lignes affaires. Pas de budget pour les portes ou les "
         "horaires, qui ne sont pas liés à la satisfaction.")

# 16 — Décision (Côme) -------------------------------------------------------
s = nouvelle()
titre(s, "Ce que nous vous proposons", [BLEU, VERT, NOIR])
decisions = [
    ("satisfait", "Financer le parcours numérique, le wi-fi et les cabines",
     "priorités issues de l'analyse de satisfaction"),
    ("dialogue", "Lancer un pilote d'accueil à l'arrivée sur quelques aéroports",
     "avec un groupe témoin non abordé, pour mesurer combien de clients reviennent vraiment"),
    ("bouclier", "Encadrer l'usage des données avant tout déploiement",
     "analyse d'impact, information des passagers, aucun mineur signalé, écran agent minimal"),
]
for k, (ic, t1, t2) in enumerate(decisions):
    yy = 2.0 + k * 1.52
    carte(s, M, yy, W - 2 * M, 1.32)
    forme(s, MSO_SHAPE.OVAL, M + 0.4, yy + 0.33, 0.66, 0.66, BLEU)
    texte(s, M + 0.4, yy + 0.33, 0.66, 0.66, str(k + 1), taille=24, gras=True, couleur=BLANC,
          align=PP_ALIGN.CENTER, ancre=MSO_ANCHOR.MIDDLE)
    texte(s, M + 1.35, yy + 0.18, 9.6, 1.0, [[(t1, {"gras": True, "taille": 22})], [(t2, {"taille": 15, "couleur": TEXTE_2})]],
          ancre=MSO_ANCHOR.MIDDLE)
    icone(s, ic, W - M - 1.2, yy + 0.24, 0.85, rond=True)
pied(s, "Décisions demandées à la direction Expérience Client — Côme", 16)
notes(s, "Côme — Décision (40 s). Nous vous demandons trois décisions : financer les services prioritaires ; lancer un pilote "
         "d'accueil avec un groupe témoin, car c'est le seul moyen de prouver que l'approche fait revenir les clients ; et "
         "encadrer l'usage des données avant tout déploiement. Merci, nous sommes prêts pour vos questions.")

prs.save(SORTIE)
print("Présentation enregistrée :", SORTIE)
