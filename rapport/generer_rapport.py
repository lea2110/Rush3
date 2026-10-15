"""Génère le rapport PDF du Rush 3 (8 pages + annexes) en suivant la charte.

    python rapport/generer_rapport.py

- Recalcule tous les chiffres sur train avec le même code que les notebooks 01 et 02.
- Lit le résultat final sur test dans la sortie du notebook 03 (test.csv n'est pas relu).
- Produit rapport/rapport_rush3.html puis rapport/rapport_rush3.pdf (Chrome headless).
"""

import html
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RACINE = Path(__file__).resolve().parent.parent
sys.path.append(str(RACINE))

from src.data import RATING_COLUMNS, RANDOM_STATE, TARGET, load_train  # noqa: E402
from src.economics import CAPACITY, gain_net  # noqa: E402
from src.features import CATEGORICAL_FEATURES, LANDING_FEATURES, NUMERIC_FEATURES  # noqa: E402

SORTIE_HTML = RACINE / "rapport" / "rapport_rush3.html"
SORTIE_PDF = RACINE / "rapport" / "rapport_rush3.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

C = {"noir": "#000000", "blanc": "#FFFFFF", "fond": "#F4F4F4", "gris": "#8A8A8A", "gris_clair": "#D9D9D9",
     "texte2": "#444444", "bleu": "#0055FF", "vert": "#009925", "orange": "#FF6B00", "jaune": "#FFDC00",
     "rose": "#FFB3C9", "brun": "#A88565"}


# ---------------------------------------------------------------------------
# Formats français
def fr(x, d=0):
    if d < 0:  # arrondi à la dizaine, centaine…
        x, d = round(x, d), 0
    s = f"{x:,.{d}f}".replace(",", "\u00a0").replace(".", ",")
    return s


def pct(x, d=1):
    return f"{fr(x, d)} %"


def eur(x):
    return f"{fr(x)} €"


# ---------------------------------------------------------------------------
# 1. Volet 1 — Expliquer (même code que le notebook 01)
df = load_train()
satisfait = 1 - df[TARGET]
N = len(df)
TAUX = satisfait.mean() * 100


def taux_par(col):
    return (satisfait.groupby(df[col], observed=True).mean() * 100)


par_voyage = taux_par("Type of Travel")
par_classe = taux_par("Class")
par_fidelite = taux_par("Customer Type")
par_genre = taux_par("Gender")
effectifs_voyage = df["Type of Travel"].value_counts()

df["age_group"] = pd.cut(df["Age"], bins=[0, 18, 30, 45, 60, 120],
                         labels=["0-18", "19-30", "31-45", "46-60", "61+"], include_lowest=True)
df["delay_group"] = pd.cut(df["Arrival Delay in Minutes"], bins=[-0.01, 0, 15, 60, np.inf],
                           labels=["Aucun", "1-15 min", "16-60 min", "+60 min"])
par_age = taux_par("age_group")
par_retard = taux_par("delay_group")


def cramers_v(data, facteur):
    table = pd.crosstab(data[facteur], data[TARGET])
    chi2 = chi2_contingency(table)[0]
    n = table.to_numpy().sum()
    phi2 = chi2 / n
    r, k = table.shape
    phi2_corr = max(0, phi2 - ((k - 1) * (r - 1)) / (n - 1))
    r_corr = r - ((r - 1) ** 2) / (n - 1)
    k_corr = k - ((k - 1) ** 2) / (n - 1)
    return np.sqrt(phi2_corr / min(k_corr - 1, r_corr - 1))


V = {f: cramers_v(df[[f, TARGET]].dropna(), f)
     for f in ["Class", "Type of Travel", "age_group", "Customer Type", "delay_group", "Gender"]}

moyennes = df.groupby(TARGET)[RATING_COLUMNS].mean()
ecarts = (moyennes.loc[0] - moyennes.loc[1]).sort_values(ascending=False)
zeros = (load_train(zero_as_missing=False)[RATING_COLUMNS] == 0).mean() * 100

ecarts_segment = {}
for seg, groupe in df.groupby("Type of Travel"):
    m = groupe.groupby(TARGET)[RATING_COLUMNS].mean()
    ecarts_segment[seg] = (m.loc[0] - m.loc[1]).sort_values(ascending=False)

NOMS = {
    "Online boarding": "Embarquement en ligne", "Inflight entertainment": "Divertissement à bord",
    "Inflight wifi service": "Wi-Fi en vol", "Seat comfort": "Confort du siège",
    "On-board service": "Service à bord", "Leg room service": "Espace pour les jambes",
    "Cleanliness": "Propreté", "Ease of Online booking": "Réservation en ligne",
    "Checkin service": "Enregistrement", "Baggage handling": "Bagages", "Inflight service": "Service en vol",
    "Food and drink": "Repas et boissons", "Gate location": "Porte d'embarquement",
    "Departure/Arrival time convenient": "Horaires pratiques",
}

# ---------------------------------------------------------------------------
# 2. Volet 2 — Prédire (même code que le notebook 02, train uniquement)
X = df[LANDING_FEATURES]
y = df[TARGET]
retard = X["Arrival Delay in Minutes"].fillna(X["Departure Delay in Minutes"])
X_modele = X.copy()
X_modele["Arrival Delay in Minutes"] = retard
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
correlation_retards = df["Departure Delay in Minutes"].corr(df["Arrival Delay in Minutes"])
manquants_retard = int(df["Arrival Delay in Minutes"].isna().sum())

scores_hasard = np.random.default_rng(RANDOM_STATE).random(len(y))
perso = (X["Type of Travel"] == "Personal Travel").astype(int)
eco = (X["Class"] == "Eco").astype(int)


def pipeline(num, cat, lineaire):
    prep = ColumnTransformer([("num", StandardScaler() if lineaire else "passthrough", num),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    modele = LogisticRegression(max_iter=1000) if lineaire else HistGradientBoostingClassifier(random_state=RANDOM_STATE)
    return make_pipeline(prep, modele)


def scores_cv(num, cat, lineaire):
    return cross_val_predict(pipeline(num, cat, lineaire), X_modele[num + cat], y, cv=cv, method="predict_proba")[:, 1]


print("Validation croisée…")
cat_sans = [c for c in CATEGORICAL_FEATURES if c != "Type of Travel"]
num_sans_age = [c for c in NUMERIC_FEATURES if c != "Age"]
R = {
    "hasard": gain_net(y, scores_hasard),
    "retard": gain_net(y, retard),
    "perso": gain_net(y, perso * 10_000 + retard),
    "eco": gain_net(y, eco * 10_000 + retard),
    "log_avec": gain_net(y, scores_cv(NUMERIC_FEATURES, CATEGORICAL_FEATURES, True)),
}
s_boost_avec = scores_cv(NUMERIC_FEATURES, CATEGORICAL_FEATURES, False)
R["boost_avec"] = gain_net(y, s_boost_avec)
R["log_sans"] = gain_net(y, scores_cv(NUMERIC_FEATURES, cat_sans, True))
s_boost = scores_cv(NUMERIC_FEATURES, cat_sans, False)
R["boost_sans"] = gain_net(y, s_boost)
mineur = (X["Age"] < 18).values
R["retenu"] = gain_net(y, np.where(mineur, -np.inf, s_boost))
s_sans_age = scores_cv(num_sans_age, cat_sans, False)
R["sans_age"] = gain_net(y, s_sans_age)
MAX_GAIN = gain_net(y, y.values)["gain_net_pour_1000"]
nb_abordes = int(np.floor(CAPACITY * len(y)))


def top(scores):
    return np.argsort(-scores, kind="stable")[:nb_abordes]


part_mineurs = mineur[top(s_boost)].mean() * 100
part_mineurs_sans_age = mineur[top(s_sans_age)].mean() * 100
capacite = {c: gain_net(y, s_boost, capacity=c) for c in [0.02, 0.05, 0.08, 0.10]}

signale = np.zeros(len(y), dtype=bool)
signale[top(s_boost)] = True
portrait = {
    "Classe Eco": (X["Class"].eq("Eco").mean() * 100, X.loc[signale, "Class"].eq("Eco").mean() * 100, "%"),
    "Clients non fidèles": (X["Customer Type"].eq("disloyal Customer").mean() * 100,
                            X.loc[signale, "Customer Type"].eq("disloyal Customer").mean() * 100, "%"),
    "Âge médian": (X["Age"].median(), X.loc[signale, "Age"].median(), " ans"),
    "Retard médian à l'arrivée": (retard.median(), retard[signale].median(), " min"),
}

X_app, X_val, y_app, y_val = train_test_split(X_modele[NUMERIC_FEATURES + cat_sans], y, test_size=0.2,
                                              stratify=y, random_state=RANDOM_STATE)
mod_imp = pipeline(NUMERIC_FEATURES, cat_sans, False).fit(X_app, y_app)
imp = permutation_importance(mod_imp, X_val, y_val, scoring="roc_auc", n_repeats=5, random_state=RANDOM_STATE)
importance = pd.Series(imp.importances_mean, index=X_val.columns).sort_values(ascending=False)
NOMS_VAR = {"Class": "Classe", "Age": "Âge", "Customer Type": "Fidélité", "Arrival Delay in Minutes": "Retard à l'arrivée",
            "Flight Distance": "Distance", "Departure Delay in Minutes": "Retard au départ"}

pour_1000 = 1000 / len(y)
fp_cv = (R["retenu"]["passagers_abordes"] - R["retenu"]["insatisfaits_abordes"]) * pour_1000
non_abordes = (int(y.sum()) - R["retenu"]["insatisfaits_abordes"]) * pour_1000
mecontents_1000 = y.mean() * 1000

# ---------------------------------------------------------------------------
# 3. Résultat final sur test : lu dans la sortie du notebook 03 (exécution unique)
nb03 = json.loads((RACINE / "notebooks" / "03_evaluation_finale_test.ipynb").read_text(encoding="utf-8"))
T, date_test = {}, ""
for cell in nb03["cells"]:
    for out in cell.get("outputs", []):
        texte = "".join(out.get("text", ""))
        if "Exécution" in texte:
            date_test = texte.split(":", 1)[1].strip()
        h = "".join(out.get("data", {}).get("text/html", ""))
        for nom, a, b, p, g in re.findall(
                r"<th>([^<]+)</th>\s*<td>(\d+)</td>\s*<td>(\d+)</td>\s*<td>([\d.]+)</td>\s*<td>([\d.]+)</td>", h):
            T[html.unescape(nom)] = {"abordes": int(a), "insatisfaits": int(b), "precision": float(p), "gain": float(g)}
T_MOD, T_REG, T_HAS = T["Modèle retenu"], T["Règle : Eco puis retard"], T["Hasard"]
fp_test = (T_MOD["abordes"] - T_MOD["insatisfaits"]) / T_MOD["abordes"] * 100
with open(RACINE / "rush-3" / "data" / "raw" / "test.csv", encoding="utf-8") as f:  # taille seulement
    n_test = sum(1 for _ in f) - 1
cout_max = T_MOD["precision"] * 100

print("Contrôles : retenu CV", round(R["retenu"]["gain_net_pour_1000"]), "| test", round(T_MOD["gain"]),
      "| mineurs", round(part_mineurs, 1), "| V classe", round(V["Class"], 3), "| écart embarquement",
      round(ecarts["Online boarding"], 2))


# ---------------------------------------------------------------------------
# 4. Briques graphiques (SVG inline, charte + règles de visualisation)
def barre_path(x0, y0, x1, h, r=4):
    """Barre horizontale : coins arrondis côté valeur, carrée côté ligne de base."""
    if abs(x1 - x0) < 0.5:
        return ""
    r = min(r, h / 2, abs(x1 - x0))
    if x1 >= x0:
        return (f"M{x0:.1f},{y0:.1f}H{x1 - r:.1f}Q{x1:.1f},{y0:.1f} {x1:.1f},{y0 + r:.1f}"
                f"V{y0 + h - r:.1f}Q{x1:.1f},{y0 + h:.1f} {x1 - r:.1f},{y0 + h:.1f}H{x0:.1f}Z")
    return (f"M{x0:.1f},{y0:.1f}H{x1 + r:.1f}Q{x1:.1f},{y0:.1f} {x1:.1f},{y0 + r:.1f}"
            f"V{y0 + h - r:.1f}Q{x1:.1f},{y0 + h:.1f} {x1 + r:.1f},{y0 + h:.1f}H{x0:.1f}Z")


def esc(t):
    return html.escape(str(t))


def barres(items, largeur=330, etiquette=120, vmax=None, vmin=0.0, h=12, pas=21, fmt=None,
           repere=None, repere_txt="", titre_svg=""):
    """items = [(libellé, valeur, couleur)] — barres horizontales, valeur au bout."""
    fmt = fmt or (lambda v: fr(v, 1))
    vmax = vmax or max(v for _, v, _ in items) * 1.15
    zone = largeur - etiquette - 46
    x_zero = etiquette + zone * (0 - vmin) / (vmax - vmin)
    haut = len(items) * pas + (14 if repere is not None else 4)
    dy0 = 14 if repere is not None else 2
    out = [f'<svg viewBox="0 0 {largeur} {haut}" width="100%" role="img" aria-label="{esc(titre_svg)}">']
    out.append(f'<line x1="{x_zero:.1f}" y1="{dy0 - 2}" x2="{x_zero:.1f}" y2="{haut}" stroke="#D9D9D9" stroke-width="1"/>')
    if repere is not None:
        xr = etiquette + zone * (repere - vmin) / (vmax - vmin)
        out.append(f'<line x1="{xr:.1f}" y1="10" x2="{xr:.1f}" y2="{haut}" stroke="#8A8A8A" stroke-width="1"/>')
        out.append(f'<text x="{xr:.1f}" y="7" font-size="7.5" fill="#444" text-anchor="middle">{esc(repere_txt)}</text>')
    for i, (lib, v, coul) in enumerate(items):
        yb = dy0 + i * pas + (pas - h) / 2
        x1 = etiquette + zone * (v - vmin) / (vmax - vmin)
        out.append(f'<text x="{etiquette - 6}" y="{yb + h - 2.5:.1f}" font-size="8.5" fill="#000" text-anchor="end">{esc(lib)}</text>')
        out.append(f'<path d="{barre_path(x_zero, yb, x1, h)}" fill="{coul}"><title>{esc(lib)} : {esc(fmt(v))}</title></path>')
        if v >= 0:
            out.append(f'<text x="{max(x1, x_zero) + 4:.1f}" y="{yb + h - 2.5:.1f}" font-size="8.5" font-weight="700" fill="#000">{esc(fmt(v))}</text>')
        else:
            out.append(f'<text x="{x_zero + 4:.1f}" y="{yb + h - 2.5:.1f}" font-size="8.5" font-weight="700" fill="#000">{esc(fmt(v))}</text>')
    out.append("</svg>")
    return "".join(out)


def colonnes(items, largeur=250, hauteur=110, vmax=100, fmt=None, couleur=C["vert"], titre_svg=""):
    fmt = fmt or (lambda v: pct(v, 0))
    n = len(items)
    zone_h = hauteur - 30
    pas = largeur / n
    w = min(24, pas * 0.5)
    out = [f'<svg viewBox="0 0 {largeur} {hauteur}" width="100%" role="img" aria-label="{esc(titre_svg)}">',
           f'<line x1="0" y1="{zone_h + 12}" x2="{largeur}" y2="{zone_h + 12}" stroke="#D9D9D9" stroke-width="1"/>']
    for i, (lib, v) in enumerate(items):
        cx = pas * i + pas / 2
        hb = zone_h * v / vmax
        y0 = zone_h + 12 - hb
        r = min(4, w / 2, hb)
        d = (f"M{cx - w / 2:.1f},{zone_h + 12}V{y0 + r:.1f}Q{cx - w / 2:.1f},{y0:.1f} {cx - w / 2 + r:.1f},{y0:.1f}"
             f"H{cx + w / 2 - r:.1f}Q{cx + w / 2:.1f},{y0:.1f} {cx + w / 2:.1f},{y0 + r:.1f}V{zone_h + 12}Z")
        out.append(f'<path d="{d}" fill="{couleur}"><title>{esc(lib)} : {esc(fmt(v))}</title></path>')
        out.append(f'<text x="{cx:.1f}" y="{y0 - 4:.1f}" font-size="8.5" font-weight="700" text-anchor="middle">{esc(fmt(v))}</text>')
        out.append(f'<text x="{cx:.1f}" y="{hauteur - 4}" font-size="8" fill="#444" text-anchor="middle">{esc(lib)}</text>')
    out.append("</svg>")
    return "".join(out)


def anneau(valeur, couleur, taille=92, epaisseur=10, libelle=""):
    r = (taille - epaisseur) / 2
    circ = 2 * np.pi * r
    plein = circ * valeur / 100
    return (f'<svg viewBox="0 0 {taille} {taille}" width="{taille}" height="{taille}" role="img" aria-label="{esc(libelle)}">'
            f'<circle cx="{taille / 2}" cy="{taille / 2}" r="{r}" fill="none" stroke="#EDEDED" stroke-width="{epaisseur}"/>'
            f'<circle cx="{taille / 2}" cy="{taille / 2}" r="{r}" fill="none" stroke="{couleur}" stroke-width="{epaisseur}" '
            f'stroke-linecap="round" stroke-dasharray="{plein:.1f} {circ:.1f}" transform="rotate(-90 {taille / 2} {taille / 2})"/>'
            f'<text x="50%" y="54%" text-anchor="middle" font-size="16" font-weight="800">{esc(pct(valeur))}</text></svg>')


PERSONNE = ('<circle cx="12" cy="6.3" r="3.1"/><path d="M6.3 20.5v-4.8a5.7 5.7 0 0 1 11.4 0v4.8z"/>')


def personnes(n, actifs, couleur_actif=C["bleu"], couleur=C["gris_clair"], taille=22):
    s = ""
    for i in range(n):
        coul = couleur_actif if i < actifs else couleur
        s += f'<svg viewBox="0 0 24 24" width="{taille}" height="{taille}" fill="{coul}" aria-hidden="true">{PERSONNE}</svg>'
    return f'<span class="personnes">{s}</span>'


def grille_100(actifs, couleur=C["orange"], taille=10, ecart=3, echelle=1.45):
    cote = 10 * taille + 9 * ecart
    s = f'<svg viewBox="0 0 {cote} {cote}" width="{cote * echelle:.0f}" height="{cote * echelle:.0f}" role="img" aria-label="{actifs} sur 100">'
    for k in range(100):
        i, j = divmod(k, 10)
        coul = couleur if k < actifs else C["gris_clair"]
        s += f'<rect x="{j * (taille + ecart)}" y="{i * (taille + ecart)}" width="{taille}" height="{taille}" rx="2.5" fill="{coul}"/>'
    return s + "</svg>"


def chevrons(n=4, couleur=C["bleu"]):
    s = "".join(f'<path d="M{i * 7},0 L{i * 7 + 5},5 L{i * 7},10" fill="none" stroke="{couleur}" stroke-width="2" '
                f'stroke-linecap="round" stroke-linejoin="round"/>' for i in range(n))
    return f'<svg class="chev" viewBox="-1 -1 {n * 7 + 2} 12" width="{n * 7 + 2}" height="12" aria-hidden="true">{s}</svg>'


def ico(nom, taille=26, rond=False):
    dossier = "rond/" if rond else ""
    return f'<img class="ico" src="../charte/icones/{dossier}{nom}.svg" width="{taille}" height="{taille}" alt="">'


def mini(valeur, vmax, couleur=C["bleu"]):
    return (f'<span class="mini"><span style="width:{min(100, valeur / vmax * 100):.1f}%;background:{couleur}"></span></span>')


# ---------------------------------------------------------------------------
# 5. Mise en page
ETAPES = ["Synthèse", "Données et méthode", "Qui est satisfait", "Ce qui fait la différence",
          "Prédire à l'atterrissage", "Résultats", "Protection des données", "Recommandations"]


def fil(etape):
    morceaux = []
    for i, e in enumerate(ETAPES, 1):
        cls = "ici" if i == etape else ("fait" if i < etape else "")
        morceaux.append(f'<span class="etape {cls}"><b>{i}</b>{esc(e) if i == etape else ""}</span>')
    return '<nav class="fil">' + chevrons(1, C["gris_clair"]).join(morceaux) + "</nav>"


def page(etape, pastilles, titre, chapeau, corps, annexe=None, numero=None):
    pts = "".join(f'<i style="background:{p}"></i>' for p in pastilles)
    tete = fil(etape) if etape else f'<nav class="fil"><span class="etape ici"><b>{annexe}</b>Annexe</span></nav>'
    points = "".join(
        f'<i class="{"ici" if k == numero else ("fait" if k < numero else "")}"></i>' for k in range(1, 11))
    return f"""
<section class="page">
  {tete}
  <div class="pastilles">{pts}</div>
  <h1>{titre}</h1>
  <p class="chapeau">{chapeau}</p>
  <div class="corps">{corps}</div>
  <footer><span>Rush 3 · Satisfaction passagers — Léa · Jeanne · Côme</span><span class="points">{points}</span></footer>
</section>"""


def carte(contenu, classe="", style=""):
    return f'<div class="carte {classe}" style="{style}">{contenu}</div>'


def ligne(icone, titre, detail, rond=False, taille=24):
    return (f'<div class="ligne">{ico(icone, taille, rond)}<div><b>{titre}</b><span>{detail}</span></div></div>')


pages = []

# --- Page 1 : synthèse --------------------------------------------------------
g_ret = R["retenu"]["gain_net_pour_1000"]
p1 = f"""
<div class="g3">
  {carte(f'<div class="hero-ligne">{anneau(TAUX, C["vert"], 96, 10, "taux de satisfaction")}<div><div class="k">des passagers sont satisfaits</div><div class="s">{pct(par_voyage["Business travel"], 0)} en voyage pro, {pct(par_voyage["Personal Travel"], 0)} en voyage perso</div></div></div>')}
  {carte(f'{ico("euro", 30)}<div class="hero bleu">{eur(T_MOD["gain"])}</div><div class="k">gagnés pour 1&nbsp;000 passagers arrivants</div><div class="s">{fr(T_MOD["gain"] / T_HAS["gain"], 1)} fois plus qu’au hasard</div>')}
  {carte(f'{ico("bouclier", 30)}<div class="hero">0 enfant</div><div class="k">signalé aux équipes</div><div class="s">genre exclu, écran agent minimal</div>')}
</div>
<div class="carte">
  <h2>Ce que nous avons trouvé</h2>
  <div class="recit">
    <div class="pas">{ico("graphique", 30)}<div><b>La satisfaction dépend d’abord du motif du voyage et de la classe.</b>
      <span>{pct(par_classe["Business"], 0)} de satisfaits en Business contre {pct(par_classe["Eco"], 0)} en Eco ; les clients fidèles le sont deux fois plus.</span></div></div>
    <div class="pas">{ico("wifi", 30)}<div><b>Les leviers sont numériques et changent selon le motif.</b>
      <span>Voyage pro : embarquement en ligne, divertissement, siège. Voyage perso : Wi-Fi et réservation en ligne. Portes et horaires : aucun lien.</span></div></div>
    <div class="pas">{ico("cible", 30)}<div><b>Un modèle repère les mécontents dès l’atterrissage.</b>
      <span>Les équipes abordent 100 passagers sur 1&nbsp;000 : {round(T_MOD["precision"] * 100)} sont réellement mécontents. +{eur(T_MOD["gain"] - T_REG["gain"])} par rapport à la meilleure règle simple.</span></div></div>
    <div class="pas">{ico("bouclier", 30)}<div><b>Un nouvel usage des données, sous conditions.</b>
      <span>Aucun mineur signalé (coût : {pct((R["boost_sans"]["gain_net_pour_1000"] - g_ret) / R["boost_sans"]["gain_net_pour_1000"] * 100, 0)} du gain), information et droit d’opposition, ni score ni âge montrés aux agents.</span></div></div>
  </div>
</div>
<div class="carte">
  <h2>Ce que nous vous proposons</h2>
  <div class="decisions">
    <div><em>1</em><b>Financer le parcours numérique, le Wi-Fi et les cabines</b><span>en testant chaque amélioration sur une partie des vols</span></div>
    <div><em>2</em><b>Lancer un pilote d’accueil à l’arrivée</b><span>avec un groupe témoin pour mesurer le retour réel des clients</span></div>
    <div><em>3</em><b>Encadrer les données avant tout déploiement</b><span>analyse d’impact, information des passagers, aucun mineur signalé</span></div>
  </div>
</div>"""
pages.append(page(1, [C["bleu"], C["vert"], C["noir"]], "Où investir, qui aborder à l’arrivée, et à quelles conditions",
                  f"Plus de la moitié des passagers jugent leur vol neutre ou décevant. À partir de {fr(N)} réponses à l’enquête post-vol, "
                  "nous répondons aux deux questions de la direction Expérience Client.", p1, numero=1))

# --- Page 2 : données et méthode ---------------------------------------------
p2 = f"""
<div class="carte">
  <h2>Deux fichiers, une règle : le test ne sert qu’une fois</h2>
  <div class="flux">
    <div class="boite">{ico("dialogue", 26)}<div><div class="k2">{fr(N + n_test)}</div><span>réponses à l’enquête post-vol</span></div></div>
    {chevrons()}
    <div class="boite"><div><div class="k2">{fr(N)}</div><span><b>train</b> : explorer, expliquer, comparer les modèles (validation croisée en 5 parts)</span></div></div>
    {chevrons()}
    <div class="boite bleu-b"><div><div class="k2 bleu">{fr(n_test)}</div><span><b>test</b> : les passagers « du mois prochain », lus une seule fois, à la fin</span></div></div>
  </div>
</div>
<div class="g2">
  <div class="carte">
    <h2>Nos choix de traitement</h2>
    {ligne("valide", "Une note de 0 = pas de réponse", f"et non une mauvaise note ; {pct((load_train(zero_as_missing=False)[RATING_COLUMNS] == 0).any(axis=1).mean() * 100)} des passagers ont au moins un 0")}
    {ligne("horloge", f"{manquants_retard} retards d’arrivée manquants", f"remplacés par le retard au départ (corrélation {fr(correlation_retards, 3)})")}
    {ligne("exclu", "Identifiant retiré, aucun doublon", "il ne dit rien du passager")}
    {ligne("alerte", "Retards extrêmes conservés", "ce sont de vrais retards, et les passagers les plus à risque")}
    {ligne("famille", "Enfants gardés dans l’analyse", "leur avis compte ; leur signalement est encadré (partie 7)")}
    {ligne("graphique", "Résultats reproductibles", "graines fixées : deux exécutions donnent les mêmes chiffres")}
  </div>
  <div class="carte">
    <h2>La règle du jeu économique</h2>
    <p class="s">Estimations de la direction, utilisées pour choisir le modèle.</p>
    <div class="capa">{personnes(10, 1, taille=26)}<span><b>1 passager sur 10</b> peut être abordé par les équipes</span></div>
    <div class="equation">
      <span><b class="eq">1/3</b>des mécontents<br>ne revolent pas</span><b>×</b><span><b class="eq">1/2</b>ramenés par<br>une approche</span><b>×</b><span><b class="eq">600&nbsp;€</b>de revenu<br>futur</span><b>−</b><span><b class="eq">40&nbsp;€</b>par<br>approche</span>
    </div>
    <div class="g2 serre">
      <div class="tuile-chiffre"><div class="k2 bleu">+60&nbsp;€</div><span>par mécontent abordé</span></div>
      <div class="tuile-chiffre"><div class="k2">−40&nbsp;€</div><span>par satisfait abordé pour rien</span></div>
    </div>
    <p class="note">{ico("cible", 18)} Aborder est rentable dès que <b>40&nbsp;%</b> des passagers abordés sont mécontents. On juge donc les modèles au <b>gain net</b>, pas à l’exactitude.</p>
  </div>
</div>"""
p2 += '<div class="carte"><h2>Le déroulé du rapport</h2><div class="deroule">' + "".join(
    f'<span class="d-etape"><b>{i}</b>{esc(e)}<i>p.&nbsp;{i}</i></span>' + (chevrons(2, C["gris_clair"]) if i < len(ETAPES) else "")
    for i, e in enumerate(ETAPES, 1)) + '</div></div>'
pages.append(page(2, [C["bleu"], C["gris_clair"]], "Deux fichiers, trois volets, une méthode",
                  "Le premier fichier sert à comprendre et à choisir ; le second mesure, une seule fois, ce que vaudra le dispositif le mois prochain.",
                  p2, numero=2))

# --- Page 3 : qui est satisfait ------------------------------------------------
profils = [("Voyage pro", par_voyage["Business travel"]), ("Voyage perso", par_voyage["Personal Travel"]),
           ("Classe Business", par_classe["Business"]), ("Classe Eco Plus", par_classe["Eco Plus"]),
           ("Classe Eco", par_classe["Eco"]), ("Clients fidèles", par_fidelite["Loyal Customer"]),
           ("Clients non fidèles", par_fidelite["disloyal Customer"]), ("Femmes", par_genre["Female"]),
           ("Hommes", par_genre["Male"])]
v_items = [("Classe", V["Class"]), ("Motif du voyage", V["Type of Travel"]), ("Tranche d’âge", V["age_group"]),
           ("Fidélité", V["Customer Type"]), ("Retard à l’arrivée", V["delay_group"]), ("Genre", V["Gender"])]
p3 = f"""
<div class="g-2-1">
  <div class="carte">
    <h2>Taux de satisfaits par profil</h2>
    {barres([(l, v, C["vert"]) for l, v in profils], largeur=380, etiquette=110, vmax=82, fmt=lambda v: pct(v), repere=TAUX, repere_txt=f"moyenne {pct(TAUX)}", titre_svg="Taux de satisfaits par profil")}
  </div>
  <div class="carte">
    <h2>Force du lien avec la satisfaction</h2>
    <p class="s">V de Cramér : 0 = aucun lien, 1 = lien parfait</p>
    {"".join(f'<div class="v"><span>{esc(l)}</span><b>{fr(v, 3)}</b>{mini(v, 0.55, C["vert"] if v > 0.1 else C["gris_clair"])}</div>' for l, v in v_items)}
    <p class="note">La <b>classe</b> et le <b>motif du voyage</b> pèsent le plus ; le genre ne joue presque pas.</p>
  </div>
</div>
<div class="g2">
  <div class="carte">
    <h2>Les plus jeunes et les plus âgés sont les plus critiques</h2>
    {colonnes([(k, v) for k, v in par_age.items()], largeur=300, hauteur=120, vmax=70, titre_svg="Satisfaits par âge")}
    <p class="s">Taux de satisfaits par tranche d’âge (ans)</p>
  </div>
  <div class="carte">
    <h2>Le retard pèse, mais moins que le profil</h2>
    {colonnes([(k, v) for k, v in par_retard.items()], largeur=300, hauteur=120, vmax=70, titre_svg="Satisfaits par retard")}
    <p class="s">Taux de satisfaits selon le retard à l’arrivée ; {manquants_retard} retards inconnus exclus</p>
  </div>
</div>
<div class="carte">
  <h2>Sur 10 passagers, combien sont satisfaits ?</h2>
  <div class="duo">
    <div class="duo-g">{ico("valise", 30, True)}<div><b>Voyage pro</b>{personnes(10, round(par_voyage["Business travel"] / 10), C["vert"], taille=24)}<span><b class="k3">{pct(par_voyage["Business travel"])}</b> de satisfaits · {fr(effectifs_voyage["Business travel"])} passagers</span></div></div>
    {chevrons(3, C["gris_clair"])}
    <div class="duo-g">{ico("famille", 30, True)}<div><b>Voyage perso</b>{personnes(10, round(par_voyage["Personal Travel"] / 10), C["vert"], taille=24)}<span><b class="k3">{pct(par_voyage["Personal Travel"])}</b> de satisfaits · {fr(effectifs_voyage["Personal Travel"])} passagers : presque 9 sur 10 sont mécontents</span></div></div>
  </div>
</div>"""
pages.append(page(3, [C["vert"], C["gris_clair"]], "La satisfaction dépend surtout du motif du voyage et de la classe",
                  f"En moyenne, {pct(TAUX)} des passagers sont satisfaits. Mais derrière cette moyenne, les profils s’opposent : un voyageur pro en Business et un voyageur perso en Eco ne vivent pas le même vol.",
                  p3, numero=3))

# --- Page 4 : ce qui fait la différence ---------------------------------------
top3 = list(ecarts.index[:3])
serv = [(NOMS[s], ecarts[s], C["bleu"] if s in top3 else C["gris_clair"]) for s in ecarts.index]
seg_html = ""
for seg, titre_seg, icone in [("Business travel", "Voyage pro", "valise"), ("Personal Travel", "Voyage perso", "famille")]:
    lignes_seg = "".join(f'<div class="v"><span>{NOMS[s]}</span><b>{fr(v, 2)}</b>{mini(v, 2.2)}</div>'
                         for s, v in ecarts_segment[seg].head(3).items())
    seg_html += f'<div class="seg">{ico(icone, 26, True)}<div class="seg-c"><b>{titre_seg}</b>{lignes_seg}</div></div>'
matrice = [
    ("wifi", "Wi-Fi en vol", "Fort (2,10 en voyage perso)", "Oui : réseau", "Fiabiliser la connexion"),
    ("cible", "Embarquement en ligne", f"Fort ({fr(ecarts['Online boarding'], 2)})", "Oui : parcours numérique", "Simplifier l’application"),
    ("siege", "Siège et divertissement", "Fort en voyage pro", "Oui, mais coûteux", "Cibler les lignes affaires"),
    ("valise", "Classe et motif du voyage", f"Très fort ({fr(V['Class'], 3)} et {fr(V['Type of Travel'], 3)})", "Pas directement", "Adapter l’offre par segment"),
    ("exclu", "Porte et horaires", "Aucun", "—", "Pas de budget"),
]
p4 = f"""
<div class="g-2-1">
  <div class="carte">
    <h2>Écart de note entre satisfaits et mécontents</h2>
    {barres(serv, largeur=380, etiquette=118, vmax=1.75, vmin=-0.3, h=10, pas=17, fmt=lambda v: fr(v, 2), titre_svg="Écart de note par service")}
    <p class="s">Note moyenne sur 5 des satisfaits moins celle des mécontents ; notes à 0 exclues</p>
  </div>
  <div class="carte">
    <h2>Les leviers selon le motif</h2>
    {seg_html}
    <p class="note">Une même dépense n’aura pas le même effet partout : le voyageur perso attend surtout du <b>numérique</b>.</p>
  </div>
</div>
<div class="carte">
  <h2>Lié à la satisfaction ne veut pas dire « cause » : sur quoi agir</h2>
  <table class="matrice">
    <thead><tr><th>Facteur</th><th>Lien avec la satisfaction</th><th>La compagnie peut agir ?</th><th>Cause prouvée ?</th><th>Action proposée</th></tr></thead>
    <tbody>{"".join(f'<tr><td>{ico(i, 18)}<b>{f}</b></td><td>{a}</td><td>{b}</td><td>Non démontré</td><td><b>{act}</b></td></tr>' for i, f, a, b, act in matrice)}</tbody>
  </table>
  <p class="note">{ico("alerte", 18)} Pour prouver un effet avant un gros investissement : améliorer un service sur une partie des vols seulement, et comparer la satisfaction.</p>
</div>"""
pages.append(page(4, [C["bleu"], C["gris_clair"]], "Ce qui fait la différence : le parcours numérique et le confort",
                  "Les 14 notes de service montrent où se joue la satisfaction. Elles servent à expliquer et à orienter le budget, pas à prédire : elles n’existent qu’après l’enquête.",
                  p4, numero=4))

# --- Page 5 : prédire à l'atterrissage ----------------------------------------
avec = [("Hasard", R["hasard"]["gain_net_pour_1000"], C["gris_clair"]),
        ("Règle : perso puis retard", R["perso"]["gain_net_pour_1000"], C["gris"]),
        ("Régression logistique", R["log_avec"]["gain_net_pour_1000"], C["gris_clair"]),
        ("Gradient boosting", R["boost_avec"]["gain_net_pour_1000"], C["gris"])]
sans = [("Hasard", R["hasard"]["gain_net_pour_1000"], C["gris_clair"]),
        ("Règle : Eco puis retard", R["eco"]["gain_net_pour_1000"], C["gris"]),
        ("Régression logistique", R["log_sans"]["gain_net_pour_1000"], C["gris_clair"]),
        ("Gradient boosting", R["boost_sans"]["gain_net_pour_1000"], C["bleu"])]
imp_items = [(NOMS_VAR[k], v, C["bleu"] if i == 0 else C["gris"]) for i, (k, v) in enumerate(importance.items())]
d_avec = R["boost_avec"]["gain_net_pour_1000"] - R["perso"]["gain_net_pour_1000"]
d_sans = R["boost_sans"]["gain_net_pour_1000"] - R["eco"]["gain_net_pour_1000"]
p5 = f"""
<div class="g2">
  <div class="carte">
    <h2>{ico("valide", 20)} Utilisé : connu à l’atterrissage</h2>
    {ligne("siege", "Classe du billet", "billet")}
    {ligne("passager", "Âge et statut de fidélité", "réservation et programme de fidélité (hypothèse) ; l’âge n’est jamais montré aux agents")}
    {ligne("avion", "Distance du vol", "plan de vol")}
    {ligne("horloge", "Retards au départ et à l’arrivée", "opérations")}
  </div>
  <div class="carte">
    <h2>{ico("exclu", 20)} Écarté</h2>
    {ligne("wifi", "Notes de service", "n’existent qu’après l’enquête")}
    {ligne("valise", "Motif du voyage", "déclaré dans l’enquête, inconnu pour les non-répondants")}
    {ligne("confidentiel", "Genre", f"aucun effet ({pct(100 - par_genre['Female'])} contre {pct(100 - par_genre['Male'])} de mécontents), risque de discrimination")}
  </div>
</div>
<div class="carte">
  <h2>Pourquoi un modèle ? Parce que le motif du voyage est inconnu</h2>
  <p class="s">Gain net pour 1&nbsp;000 passagers arrivants, validation croisée sur train ; maximum possible : {eur(MAX_GAIN)}</p>
  <div class="g2">
    <div><h3>Si le motif était connu</h3>{barres(avec, largeur=300, etiquette=128, vmax=6600, fmt=eur, titre_svg="Avec le motif")}
      <div class="delta">{chevrons(3, C["gris"])}<span><b>+{eur(d_avec)}</b> seulement pour le modèle : une règle simple suffirait</span></div></div>
    <div><h3>Sans le motif : notre cas</h3>{barres(sans, largeur=300, etiquette=128, vmax=6600, fmt=eur, titre_svg="Sans le motif")}
      <div class="delta">{chevrons(3)}<span><b class="bleu">+{eur(d_sans)}</b> pour le modèle : c’est là qu’il se justifie</span></div></div>
  </div>
  <p class="note">{ico("graphique", 18)} La régression logistique fait moins bien que la règle simple. Une forêt aléatoire a aussi été testée et écartée : ses résultats changeaient d’une exécution à l’autre.</p>
</div>
<div class="g2">
  <div class="carte">
    <h2>Ce qui pèse dans ses décisions</h2>
    {barres(imp_items, largeur=300, etiquette=100, vmax=importance.max() * 1.25, fmt=lambda v: fr(v, 3), h=10, pas=16, titre_svg="Importance des variables")}
    <p class="s">Importance par permutation : perte de qualité quand on mélange la variable</p>
  </div>
  <div class="carte">
    <h2>Qui il signale</h2>
    <table class="portrait"><thead><tr><th></th><th>Tous</th><th>Signalés</th></tr></thead><tbody>
    {"".join(f'<tr><td>{k}</td><td>{fr(a, 0)}{u.replace("%", "&nbsp;%")}</td><td><b>{fr(b, 0)}{u.replace("%", "&nbsp;%")}</b></td></tr>' for k, (a, b, u) in portrait.items())}
    </tbody></table>
    <p class="note">Surtout des passagers en Eco, peu fidèles, plus jeunes et un peu retardés.</p>
  </div>
</div>"""
pages.append(page(5, [C["bleu"], C["gris_clair"]], "À l’atterrissage, le modèle n’utilise que ce que la compagnie sait déjà",
                  "Le modèle est entraîné sur les répondants mais appliqué à tous les passagers arrivants, qui pour la plupart ne répondront jamais à l’enquête.",
                  p5, numero=5))

# --- Page 6 : résultats ---------------------------------------------------------
test_items = [("Hasard", T_HAS["gain"], C["gris_clair"]), ("Règle : Eco puis retard", T_REG["gain"], C["gris"]),
              ("Modèle retenu", T_MOD["gain"], C["bleu"])]
imp_items = [(NOMS_VAR[k], v, C["bleu"] if i == 0 else C["gris"]) for i, (k, v) in enumerate(importance.items())]
p6 = f"""
<div class="g-1-2">
  <div class="carte centre">
    <h2>Sur 100 passagers abordés</h2>
    {grille_100(round(T_MOD["precision"] * 100))}
    <div class="legende"><span><i style="background:{C["orange"]}"></i><b>{round(T_MOD["precision"] * 100)}</b> vraiment mécontents</span><span><i style="background:{C["gris_clair"]}"></i><b>{100 - round(T_MOD["precision"] * 100)}</b> satisfaits abordés pour rien</span></div>
  </div>
  <div class="carte">
    <h2>Sur {fr(n_test)} passagers jamais vus, le modèle bat toute règle</h2>
    {barres(test_items, largeur=400, etiquette=118, vmax=6400, fmt=eur, h=14, pas=26, titre_svg="Gain sur test")}
    <div class="g3 serre">
      <div class="tuile-chiffre"><div class="k2 bleu">+{eur(T_MOD["gain"] - T_REG["gain"])}</div><span>par rapport à la meilleure règle</span></div>
      <div class="tuile-chiffre"><div class="k2">× {fr(T_MOD["gain"] / T_HAS["gain"], 1)}</div><span>par rapport au hasard</span></div>
      <div class="tuile-chiffre"><div class="k2">≈ {eur(round((T_MOD["abordes"] - T_MOD["insatisfaits"]) * 40 / n_test * 1000, -1))}</div><span>d’approches inutiles pour 1&nbsp;000 passagers</span></div>
    </div>
  </div>
</div>
<div class="carte stable">
  {ico("valide", 30, True)}
  <div><b>Validation croisée</b><span>{pct(R["retenu"]["precision"] * 100)} · {eur(g_ret)}</span></div>
  {chevrons(5)}
  <div><b>Test final, exécuté une fois ({esc(date_test)})</b><span>{pct(T_MOD["precision"] * 100)} · {eur(T_MOD["gain"])}</span></div>
  {chevrons(5)}
  <div><b class="bleu">Le chiffre annoncé est fiable</b><span>les deux mesures sont quasi identiques</span></div>
</div>
<div class="g2">
  <div class="carte">
    <h2>Faut-il aborder 10&nbsp;% des passagers ?</h2>
    {colonnes([(pct(c * 100, 0), r["gain_net_pour_1000"]) for c, r in capacite.items()], largeur=300, hauteur=118, vmax=6400, fmt=eur, couleur=C["bleu"], titre_svg="Gain selon la part abordée")}
    <p class="s">Gain pour 1&nbsp;000 passagers selon la part abordée (validation croisée). La précision reste au-dessus de {pct(min(r["precision"] for r in capacite.values()) * 100, 0)} : chaque approche supplémentaire rapporte, on utilise toute la capacité.</p>
  </div>
  <div class="carte limites">
    <h2>{ico("alerte", 20)} Limites à garder en tête</h2>
    <div class="lim"><b>Capacité</b><span>environ {fr(non_abordes, -1)} mécontents sur 1&nbsp;000 ne seront jamais abordés, quel que soit le modèle.</span></div>
    <div class="lim"><b>Répondants</b><span>le modèle apprend sur ceux qui ont répondu ; il faudra suivre sa performance sur tous les passagers.</span></div>
    <div class="lim"><b>Hypothèses</b><span>rentable jusqu’à environ {eur(cout_max)} par approche ; l’effet réel d’une approche reste à mesurer (pilote avec groupe témoin).</span></div>
  </div>
</div>"""
pages.append(page(6, [C["bleu"], C["orange"]], f"Sur 100 passagers abordés, {round(T_MOD['precision'] * 100)} sont vraiment mécontents",
                  f"Modèle retenu : gradient boosting sans le motif du voyage, mineurs exclus. Il a été mesuré une seule fois sur les passagers du mois prochain : {eur(T_MOD['gain'])} gagnés pour 1&nbsp;000 passagers arrivants.",
                  p6, numero=6))

# --- Page 7 : protection des données --------------------------------------------
p7 = f"""
<div class="carte">
  <h2>Aucun enfant n’est jamais signalé</h2>
  <div class="flux">
    <div class="boite jaune">{ico("alerte", 26)}<div><div class="k2">{pct(part_mineurs)}</div><span>des signalés seraient mineurs sans précaution (contre {pct((X["Age"] < 18).mean() * 100)} des passagers)</span></div></div>
    {chevrons()}
    <div class="boite">{ico("famille", 26, True)}<div><div class="k2">0&nbsp;%</div><span>après exclusion des mineurs du signalement</span></div></div>
    {chevrons()}
    <div class="boite">{ico("bouclier", 26, True)}<div><div class="k2">−{eur(R["boost_sans"]["gain_net_pour_1000"] - g_ret)}</div><span>seulement pour 1&nbsp;000 passagers ({pct((R["boost_sans"]["gain_net_pour_1000"] - g_ret) / R["boost_sans"]["gain_net_pour_1000"] * 100, 0)} du gain)</span></div></div>
  </div>
  <p class="note">{ico("exclu", 18)} Retirer l’âge du modèle ne suffirait pas : −{eur(R["boost_sans"]["gain_net_pour_1000"] - R["sans_age"]["gain_net_pour_1000"])} et encore {pct(part_mineurs_sans_age)} de mineurs signalés, repérés par d’autres indices. C’est l’âge qui permet de les exclure.</p>
</div>
<div class="g2">
  {carte(f'<div class="cond">{ico("dialogue", 30, True)}<div><b>Informer et permettre de refuser</b><span>Nouvelle finalité : politique de confidentialité mise à jour, intérêt légitime, droit d’opposition simple, analyse d’impact (AIPD) avant déploiement.</span></div></div>')}
  {carte(f'<div class="cond">{ico("famille", 30, True)}<div><b>Protéger les enfants</b><span>Le profilage des enfants appelle une protection renforcée : aucun mineur n’est signalé ; piste : s’adresser à l’adulte accompagnant.</span></div></div>')}
  {carte(f'<div class="cond">{ico("cible", 30, True)}<div><b>Limiter les informations</b><span>Classe, fidélité, distance, retards et âge. Genre et motif du voyage exclus.</span></div></div>')}
  {carte(f'<div class="cond">{ico("confidentiel", 30, True)}<div><b>Montrer le minimum</b><span>Ni score, ni âge, ni genre, ni réponses à l’enquête ; signalements effacés après le vol.</span></div></div>')}
</div>
<div class="g2">
  <div class="tablette">
    <div class="ecran">
      <span class="meta">Vol 1234 · arrivée 14:35 · porte 21 (exemple fictif)</span>
      <div class="ligne">{ico("dialogue", 30)}<div><b class="grand">Siège 12B</b><span>À accueillir en priorité</span></div></div>
      <div class="ligne">{ico("horloge", 24)}<div><b>Motif : retard de 45 minutes</b></div></div>
      <p class="s"><b>Action suggérée :</b> demander comment s’est passé le vol, proposer une collation ou une aide pour la correspondance.</p>
    </div>
  </div>
  <div class="carte">
    <h2>Ce que l’agent ne voit jamais</h2>
    {"".join(ligne("exclu", t, "", taille=22) for t in ["Le score de risque", "L’âge ou le genre", "Une étiquette « mécontent »", "Les réponses à l’enquête"])}
  </div>
</div>"""
pages.append(page(7, [C["jaune"], C["noir"], C["rose"]], "Un nouvel usage des données, acceptable sous quatre conditions",
                  "L’enquête servait à mesurer la satisfaction. Signaler au personnel des passagers qui, pour la plupart, n’y ont jamais répondu est un nouvel usage de leurs données : il doit être encadré.",
                  p7, numero=7))

# --- Page 8 : recommandations ---------------------------------------------------
abordes_1000 = 100
p8 = f"""
<div class="carte">
  <h2>Sur 1&nbsp;000 passagers arrivants</h2>
  <div class="flux">
    <div class="boite">{ico("mecontent", 26, True)}<div><div class="k2">≈ {fr(mecontents_1000, -1)}</div><span>sont neutres ou mécontents</span></div></div>
    {chevrons()}
    <div class="boite bleu-b">{ico("dialogue", 26, True)}<div><div class="k2 bleu">{abordes_1000}</div><span>sont abordés, dont {round(T_MOD["precision"] * 100)} vraiment mécontents</span></div></div>
    {chevrons()}
    <div class="boite">{ico("wifi", 26, True)}<div><div class="k2">≈ {fr(non_abordes, -1)}</div><span>restent hors de portée : seul le service les atteint</span></div></div>
  </div>
</div>
<div class="g-2-1">
  <div class="carte">
    <h2>Où investir le budget</h2>
    <div class="prio"><em>1</em>{ico("cible", 24)}<div><b>Parcours numérique</b><span>embarquement en ligne (voyage pro), réservation en ligne (voyage perso) : application et site</span></div></div>
    <div class="prio"><em>2</em>{ico("wifi", 24)}<div><b>Wi-Fi en vol</b><span>le service le plus pénalisant pour les voyageurs perso (écart de {fr(ecarts_segment["Personal Travel"]["Inflight wifi service"], 2)}) : stabiliser, offrir la messagerie</span></div></div>
    <div class="prio"><em>3</em>{ico("siege", 24)}<div><b>Cabines</b><span>confort du siège et divertissement, d’abord sur les lignes affaires</span></div></div>
    <div class="prio gris"><em>–</em>{ico("exclu", 24)}<div><b>Pas de budget</b><span>emplacement des portes et horaires, sans lien avec la satisfaction</span></div></div>
  </div>
  <div class="carte">
    <h2>Déployer pas à pas</h2>
    <ol class="etapes">
      <li><b>Pilote</b><span>quelques aéroports, avec un groupe témoin de passagers signalés mais non abordés</span></li>
      <li><b>Mesurer</b><span>taux de retour réel, satisfaction, performance du modèle sur tous les passagers</span></li>
      <li><b>Décider</b><span>étendre si le gain se confirme, après l’analyse d’impact</span></li>
    </ol>
  </div>
</div>
<div class="carte decision-finale">
  <h2>Les trois décisions que nous vous demandons</h2>
  <div class="decisions">
    <div><em>1</em>{ico("satisfait", 26, True)}<b>Financer le parcours numérique, le Wi-Fi et les cabines</b></div>
    <div><em>2</em>{ico("dialogue", 26, True)}<b>Lancer le pilote d’accueil avec groupe témoin</b></div>
    <div><em>3</em>{ico("bouclier", 26, True)}<b>Encadrer l’usage des données avant tout déploiement</b></div>
  </div>
</div>"""
pages.append(page(8, [C["bleu"], C["vert"], C["noir"]], "Investir dans le service, et aborder les bons passagers",
                  "Les deux leviers se complètent : le modèle permet d’aborder les bons passagers à l’arrivée, mais seule l’amélioration du service atteint tous les autres.",
                  p8, numero=8))


# --- Annexes (tableaux : tous les chiffres des graphiques) ---------------------
def tableau(entetes, lignes_t, classe="annexe"):
    th = "".join(f"<th>{e}</th>" for e in entetes)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in lignes_t)
    return f'<table class="{classe}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def ligne_r(nom, r):
    return [nom, pct(r["precision"] * 100), pct(r["rappel"] * 100), eur(r["gain_net_pour_1000"])]


a1 = f"""
<div class="g2">
  <div class="carte"><h2>A.1 Comparaison en validation croisée (train)</h2>
  <h3>Avec le motif du voyage</h3>
  {tableau(["Approche", "Précision", "Rappel", "Gain pour 1\u00a0000"], [ligne_r("Hasard", R["hasard"]), ligne_r("Règle : plus gros retards", R["retard"]), ligne_r("Règle : voyage perso puis retard", R["perso"]), ligne_r("Régression logistique", R["log_avec"]), ligne_r("Gradient boosting", R["boost_avec"])])}
  <h3>Sans le motif du voyage</h3>
  {tableau(["Approche", "Précision", "Rappel", "Gain pour 1\u00a0000"], [ligne_r("Règle : Eco puis retard", R["eco"]), ligne_r("Régression logistique", R["log_sans"]), ligne_r("Gradient boosting", R["boost_sans"]), ligne_r("Gradient boosting, mineurs exclus (retenu)", R["retenu"]), ligne_r("Gradient boosting sans l’âge", R["sans_age"])])}
  <p class="s">Gain maximal possible : {eur(MAX_GAIN)} pour 1 000 passagers. Rappel : part de tous les mécontents qui sont abordés (limitée par la capacité de 10 %).</p>
  </div>
  <div class="carte"><h2>A.2 Évaluation finale (test, exécution unique)</h2>
  {tableau(["Approche", "Abordés", "Mécontents abordés", "Précision", "Gain pour 1\u00a0000"], [[k, fr(v["abordes"]), fr(v["insatisfaits"]), pct(v["precision"] * 100), eur(v["gain"])] for k, v in T.items()])}
  <p class="s">Exécuté le {esc(date_test)} ; notebook 03.</p>
  <h2>A.3 Capacité utilisée (modèle sans motif)</h2>
  {tableau(["Part abordée", "Précision", "Gain pour 1\u00a0000"], [[pct(c * 100, 0), pct(r["precision"] * 100), eur(r["gain_net_pour_1000"])] for c, r in capacite.items()])}
  <h2>A.4 Importance des variables</h2>
  {tableau(["Variable", "Importance"], [[NOMS_VAR[k], fr(v, 3)] for k, v in importance.items()])}
  </div>
</div>"""
pages.append(page(None, [C["gris_clair"], C["bleu"]], "Annexe A — Tous les chiffres du modèle",
                  "Valeurs exactes des graphiques des parties 5 et 6.", a1, annexe="A", numero=9))

a2 = f"""
<div class="g2">
  <div class="carte"><h2>B.1 Taux de satisfaits</h2>
  {tableau(["Groupe", "Satisfaits"], [[l, pct(v)] for l, v in profils] + [[f"Âge {k}", pct(v)] for k, v in par_age.items()] + [[f"Retard {k}", pct(v)] for k, v in par_retard.items()])}
  <h2>B.2 Force du lien (V de Cramér)</h2>
  {tableau(["Facteur", "V"], [[l, fr(v, 3)] for l, v in v_items])}
  </div>
  <div class="carte"><h2>B.3 Notes de service</h2>
  {tableau(["Service", "Satisfaits", "Mécontents", "Écart", "Part de 0"], [[NOMS[s], fr(moyennes.loc[0, s], 2), fr(moyennes.loc[1, s], 2), fr(ecarts[s], 2), pct(zeros[s], 2)] for s in ecarts.index])}
  <h2>B.4 Qui a fait quoi</h2>
  <p class="s"><b>Léa</b> — nettoyage, facteurs de satisfaction, leviers budgétaires (notebook 01). <b>Jeanne</b> — variables à l’atterrissage, modèles, gain, évaluation finale (notebooks 02 et 03). <b>Côme</b> — protection des données, rapport, présentation.</p>
  <h2>B.5 Reproduire ce rapport</h2>
  <p class="s">Dépôt Git du groupe (README : qui a fait quoi ; DECISIONS.md : journal des choix). Commandes : <code>pip install -r requirements.txt</code>, <code>python clean_data.py</code>, exécuter les notebooks 01 → 02 → 03, puis <code>python rapport/generer_rapport.py</code>. Tous les chiffres de ce rapport sont recalculés par ce script, sauf le test final, lu dans le notebook 03.</p>
  </div>
</div>"""
pages.append(page(None, [C["gris_clair"], C["vert"]], "Annexe B — Tous les chiffres de l’analyse",
                  "Valeurs exactes des graphiques des parties 2 à 4.", a2, annexe="B", numero=10))

# ---------------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { --noir:#000; --fond:#F4F4F4; --gris:#8A8A8A; --gris-clair:#D9D9D9; --t2:#444; --bleu:#0055FF; --jaune:#FFDC00; }
body { font-family: Inter, "Helvetica Neue", Helvetica, Arial, sans-serif; color: var(--noir); background: var(--fond);
       -webkit-print-color-adjust: exact; print-color-adjust: exact; font-size: 9.4pt; line-height: 1.34; }
.page { width: 210mm; height: 297mm; padding: 11mm 13mm 9mm; background: var(--fond); display: flex; flex-direction: column;
        page-break-after: always; overflow: hidden; position: relative; }
.fil { display: flex; align-items: center; gap: 4px; margin-bottom: 5mm; flex-wrap: nowrap; }
.etape { display: inline-flex; align-items: center; gap: 5px; font-size: 7.5pt; color: var(--gris); font-weight: 600; }
.etape b { width: 15px; height: 15px; border-radius: 50%; background: var(--gris-clair); color: #fff; display: inline-grid; place-items: center; font-size: 7pt; }
.etape.fait b { background: var(--noir); }
.etape.ici { color: var(--noir); background: #fff; border-radius: 999px; padding: 2px 9px 2px 2px; }
.etape.ici b { background: var(--bleu); }
.chev { flex: none; }
.pastilles { display: flex; gap: 5px; margin-bottom: 3mm; }
.pastilles i { width: 10px; height: 10px; border-radius: 50%; display: block; }
h1 { font-size: 21pt; line-height: 1.08; font-weight: 800; letter-spacing: -0.02em; max-width: 175mm; }
.chapeau { font-size: 10.4pt; color: var(--t2); margin: 2.5mm 0 5mm; max-width: 172mm; }
.corps { flex: 1; display: flex; flex-direction: column; gap: 4.5mm; min-height: 0; }
footer { display: flex; justify-content: space-between; align-items: center; font-size: 7pt; color: var(--gris); margin-top: 3mm; }
.points { display: flex; gap: 4px; align-items: center; }
.points i { width: 6px; height: 6px; border-radius: 3px; background: var(--gris-clair); display: block; }
.points i.fait { background: var(--noir); }
.points i.ici { width: 18px; background: var(--bleu); }
.carte { background: #fff; border-radius: 12px; padding: 5mm 5.5mm; }
.carte h2 { font-size: 11.6pt; font-weight: 800; letter-spacing: -0.01em; margin-bottom: 2.2mm; display: flex; align-items: center; gap: 6px; }
h3 { font-size: 8.8pt; font-weight: 700; margin: 1mm 0 1.5mm; }
.g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
.g3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4mm; }
.g-2-1 { display: grid; grid-template-columns: 1.55fr 1fr; gap: 4mm; }
.g-1-2 { display: grid; grid-template-columns: 1fr 1.7fr; gap: 4mm; }
.serre { gap: 2.5mm; }
.s { color: var(--t2); font-size: 8.5pt; margin-top: 1mm; }
.note { color: var(--t2); font-size: 8.5pt; margin-top: 3mm; }
.note .ico { display: inline-block; vertical-align: -4px; margin-right: 5px; }
.bleu { color: var(--bleu); }
.hero { font-size: 30pt; font-weight: 800; letter-spacing: -0.03em; line-height: 1; margin: 2.5mm 0 1.5mm; }
.k { font-weight: 700; font-size: 10.4pt; }
.k2 { font-size: 18pt; font-weight: 800; letter-spacing: -0.02em; line-height: 1.05; }
.hero-ligne { display: flex; align-items: center; gap: 4mm; }
.ico { display: block; flex: none; }
.recit { display: grid; gap: 3mm; }
.pas { display: flex; gap: 3.5mm; align-items: flex-start; padding-bottom: 3mm; border-bottom: 2px dotted var(--gris-clair); }
.pas:last-child { border-bottom: 0; padding-bottom: 0; }
.pas b { display: block; font-size: 10.2pt; }
.pas span, .ligne span, .volet span, .cond span, .prio span, .decisions span, .boite span, .tuile-chiffre span, .etapes span, .duo-g span { display: block; color: var(--t2); font-size: 8.6pt; }
.decisions { display: grid; gap: 2.5mm; }
.decisions > div { display: flex; align-items: center; gap: 3mm; background: var(--fond); border-radius: 10px; padding: 2.5mm 3mm; }
.decisions > div > b { font-size: 9.8pt; }
.decisions em, .prio em { font-style: normal; flex: none; width: 20px; height: 20px; border-radius: 50%; background: var(--bleu); color: #fff; display: grid; place-items: center; font-weight: 800; font-size: 9pt; }
.decisions span { margin-left: auto; text-align: right; max-width: 60mm; }
.flux { display: flex; align-items: center; gap: 3mm; }
.boite { flex: 1; display: flex; align-items: center; gap: 3mm; background: var(--fond); border-radius: 10px; padding: 3mm; min-height: 17mm; }
.boite.bleu-b { background: #E8EFFF; }
.boite.jaune { background: var(--jaune); }
.boite.jaune span { color: #000; }
.ligne { display: flex; align-items: center; gap: 3mm; padding: 1.4mm 0; }
.ligne b { display: block; font-size: 9.6pt; }
.ligne b.grand { font-size: 14pt; }
.capa { display: flex; flex-direction: column; gap: 1.5mm; margin: 2mm 0 3mm; }
.personnes { display: inline-flex; gap: 1px; flex: none; }
.equation { display: flex; align-items: center; justify-content: space-between; gap: 2mm; background: var(--fond); border-radius: 10px; padding: 2.5mm 3mm; font-size: 7.6pt; color: var(--t2); text-align: center; }
.equation b { font-size: 12pt; color: var(--noir); }
.equation b.eq { display: block; font-size: 13pt; font-weight: 800; }
.tuile-chiffre { background: var(--fond); border-radius: 10px; padding: 2.5mm 3mm; margin-top: 2.5mm; }
.volet { display: flex; gap: 3mm; align-items: flex-start; }
.volet b { display: block; font-size: 8.8pt; }
.v { display: grid; grid-template-columns: 1fr auto; align-items: center; column-gap: 3mm; margin: 2mm 0; font-size: 9pt; }
.v .mini { grid-column: 1 / -1; margin-top: 1mm; }
.mini { display: block; height: 6px; border-radius: 3px; background: #EDEDED; overflow: hidden; }
.mini span { display: block; height: 100%; border-radius: 3px; }
.duo { display: flex; align-items: center; gap: 5mm; }
.duo-g { flex: 1; display: flex; align-items: flex-start; gap: 3.5mm; }
.duo-g > div > b { display: block; font-size: 10.2pt; margin-bottom: 1.5mm; }
.duo-g .personnes { margin-bottom: 1.5mm; }
.k3 { display: inline !important; font-size: 13pt; color: #000; }
.carte h2:not(:first-child) { margin-top: 4mm; }
.seg { display: flex; gap: 3mm; margin-bottom: 3mm; }
.seg-c { flex: 1; }
.seg-c > b { font-size: 9.3pt; }
table { width: 100%; border-collapse: collapse; }
.matrice th, .annexe th, .portrait th { text-align: left; font-size: 7.6pt; color: var(--t2); font-weight: 700; background: var(--fond); padding: 1.6mm 2mm; }
.matrice td { padding: 2.2mm 2mm; border-bottom: 1px solid #EDEDED; font-size: 8.8pt; vertical-align: middle; }
.matrice td:first-child { display: flex; align-items: center; gap: 2mm; }
.portrait td { padding: 1.5mm 2mm; border-bottom: 1px solid #EDEDED; font-size: 9pt; }
.portrait td:not(:first-child), .portrait th:not(:first-child) { text-align: right; font-variant-numeric: tabular-nums; }
.annexe td { padding: 1.3mm 2mm; border-bottom: 1px solid #EDEDED; font-size: 8.4pt; font-variant-numeric: tabular-nums; }
.annexe td:not(:first-child), .annexe th:not(:first-child) { text-align: right; }
.centre { display: flex; flex-direction: column; align-items: center; }
.centre h2 { align-self: flex-start; }
.legende { display: grid; gap: 1.5mm; margin-top: 3mm; font-size: 8pt; align-self: stretch; }
.legende i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.stable { display: flex; align-items: center; gap: 3.5mm; padding: 3.2mm 4.8mm; }
.stable b, .stable span { display: block; }
.stable > div { flex: 1; }
.stable span { color: var(--t2); font-size: 8.6pt; }
.limites span { font-size: 8.6pt; color: var(--t2); }
.limites b { color: var(--noir); }
.lim { padding: 1.8mm 0; border-bottom: 2px dotted var(--gris-clair); }
.lim:last-child { border-bottom: 0; }
.lim b { display: block; font-size: 9.6pt; }
.delta { display: flex; align-items: center; gap: 2.5mm; margin-top: 2mm; font-size: 8.8pt; color: var(--t2); }
.cond { display: flex; gap: 3.5mm; align-items: flex-start; }
.cond b { display: block; font-size: 10.2pt; margin-bottom: 0.8mm; }
.tablette { background: var(--gris-clair); border-radius: 16px; padding: 3mm; }
.ecran { background: #fff; border-radius: 11px; padding: 3.5mm 4mm; height: 100%; }
.meta { font-size: 7.2pt; color: var(--gris); }
.prio { display: flex; align-items: center; gap: 3mm; padding: 2.2mm 0; border-bottom: 2px dotted var(--gris-clair); }
.prio:last-child { border-bottom: 0; }
.prio b { display: block; font-size: 10pt; }
.prio.gris em { background: var(--gris-clair); color: #000; }
.etapes { list-style: none; counter-reset: e; display: grid; gap: 2.5mm; }
.etapes li { counter-increment: e; position: relative; padding-left: 9mm; }
.etapes li::before { content: counter(e); position: absolute; left: 0; top: 0; width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--bleu); color: var(--bleu); display: grid; place-items: center; font-weight: 800; font-size: 8.5pt; }
.etapes b { display: block; font-size: 10pt; }
.decision-finale .decisions > div { padding: 2mm 3mm; }
.deroule { display: flex; flex-wrap: wrap; align-items: center; gap: 2.5mm 2mm; }
.d-etape { display: inline-flex; align-items: center; gap: 2mm; background: var(--fond); border-radius: 999px; padding: 1.4mm 3.5mm 1.4mm 1.4mm; font-weight: 700; font-size: 8.8pt; }
.d-etape b { width: 18px; height: 18px; border-radius: 50%; background: var(--bleu); color: #fff; display: grid; place-items: center; font-size: 8pt; }
.d-etape i { font-style: normal; font-weight: 400; color: var(--gris); font-size: 7.8pt; }
code { font-family: Menlo, monospace; font-size: 7.3pt; background: var(--fond); padding: 0 3px; border-radius: 3px; }
svg text { font-family: Inter, "Helvetica Neue", Helvetica, Arial, sans-serif; }
"""

doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Rapport Rush 3 — Satisfaction passagers</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>{''.join(pages)}</body></html>"""
SORTIE_HTML.write_text(doc, encoding="utf-8")
print("HTML :", SORTIE_HTML)

subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                f"--print-to-pdf={SORTIE_PDF}", SORTIE_HTML.as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("PDF :", SORTIE_PDF)
