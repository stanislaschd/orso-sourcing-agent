"""
score.py
────────
Couche "SCORING" : le cœur de l'intelligence. On donne au LLM (a) la thèse
d'investissement et (b) la fiche enrichie de la société, et on lui demande de
noter l'alignement sur plusieurs dimensions PE, avec justification et risques.

Les dimensions de scoring sont celles d'un investisseur (fit thèse, 
croissance, qualité du business, défendabilité), et non des métriques génériques.
"""
from __future__ import annotations
from typing import Dict, Any

from . import llm
from .config import Thesis

SCORE_SYSTEM = (
    "Tu es analyste d'investissement (SCORING) dans un fonds de private equity mid-cap. "
    "Évalue l'adéquation d'une société à une thèse d'investissement donnée. "
    "Sois exigeant et honnête : un mauvais fit doit avoir un score bas.\n"
    "RÈGLES STRICTES :\n"
    "1. Ne confonds JAMAIS le chiffre d'affaires (CA) et la valeur d'entreprise (VE). "
    "Le CA n'est PAS la VE : la VE dépend de la marge, de la croissance et d'un multiple. "
    "N'estime une VE que si les données le permettent ; sinon écris que la VE est inconnue.\n"
    "2. Distingue les FAITS fournis (nom, NAF, CA, effectif) des HYPOTHÈSES. "
    "N'affirme rien que les données ne contiennent pas ; préfixe toute supposition par '[hypothèse]'. "
    "N'invente aucun produit, client ni chiffre.\n"
    "Renvoie un JSON avec : fit_score (entier 0-100), "
    "subscores (objet : thesis_fit, growth, business_quality, defensibility, chacun 0-100), "
    "rationale (str, 2-3 phrases), risks (liste de str), "
    "recommended_action (str : 'Prioritaire' | 'À étudier' | 'À surveiller' | 'Écarter')."
)


def score_company(company: Dict[str, Any], thesis: Thesis) -> Dict[str, Any]:
    """Note une société enrichie par rapport à la thèse."""
    user = (
        f"=== THÈSE D'INVESTISSEMENT ===\n{thesis.to_prompt_block()}\n\n"
        f"=== SOCIÉTÉ À ÉVALUER ===\n"
        f"Nom : {company.get('name')}\n"
        f"Secteur : {company.get('sector')}\n"
        f"Activité : {company.get('what_they_do')}\n"
        f"Business model : {company.get('business_model')}\n"
        f"Signaux de croissance : {', '.join(company.get('growth_signals', []) or []) or 'n/a'}\n"
        f"CA (si connu) : {company.get('revenue_eur', 'inconnu')}\n"
        f"Effectif (si connu) : {company.get('headcount', 'inconnu')}\n"
        f"Résumé : {company.get('summary')}"
    )
    result = llm.complete_json(SCORE_SYSTEM, user, max_tokens=2000)
    scored = dict(company)
    scored.update({
        "fit_score": int(result.get("fit_score", 0) or 0),
        "subscores": result.get("subscores", {}),
        "rationale": result.get("rationale", ""),
        "risks": result.get("risks", []),
        "recommended_action": result.get("recommended_action", ""),
    })
    return scored
