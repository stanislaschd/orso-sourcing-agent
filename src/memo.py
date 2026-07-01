"""
memo.py
───────
Couche "RESTITUTION" : pour les meilleures cibles, on génère une mini-note
d'investissement d'une page (markdown). C'est le livrable "lisible par un
associé" — celui qui montre que l'agent ne crache pas qu'un score, mais une
analyse.
"""
from __future__ import annotations
from typing import Dict, Any

from . import llm
from .config import Thesis

MEMO_SYSTEM = (
    "Tu es analyste senior en private equity. Rédige une NOTE D'INVESTISSEMENT — PHASE 1 "
    "(screening), en markdown, d'une à deux pages, en respectant EXACTEMENT cette structure "
    "et ces formats (ne change JAMAIS l'ordre ni le type de chaque section) :\n\n"
    "## {Nom} — {recommandation} (score {score}/100)\n\n"
    "**1. Résumé exécutif** — 2-3 phrases.\n\n"
    "**2. Activité & business model** — 3-4 puces courtes.\n\n"
    "**3. Marché & positionnement** — 3-4 puces courtes.\n\n"
    "**4. Éléments financiers** — TOUJOURS un tableau markdown avec EXACTEMENT ces colonnes et ces lignes :\n"
    "| Indicateur | Valeur | Statut |\n| --- | --- | --- |\n"
    "| Chiffre d'affaires | … | … |\n| Croissance du CA | … | … |\n"
    "| Marge EBITDA | … | … |\n| Récurrence des revenus | … | … |\n"
    "| Valeur d'entreprise | … | … |\n"
    "(Statut = 'Fait' si la donnée est fournie, sinon 'Donnée non disponible'. "
    "Ne donne JAMAIS la VE comme un fait : la VE n'est pas le CA.)\n\n"
    "**5. Adéquation à la thèse** — TOUJOURS un tableau markdown avec EXACTEMENT ces colonnes :\n"
    "| Critère Orso | Statut |\n| --- | --- |\n"
    "une ligne par critère de la thèse fournie ; Statut = ✅ aligné / ⚠️ à confirmer / ❌ non aligné.\n\n"
    "**6. Risques & points de vigilance** — puces.\n\n"
    "**7. Recommandation & prochaines étapes** — décision + to-do de due diligence (puces).\n\n"
    "RÈGLES : distingue les faits des hypothèses (préfixe '[hypothèse]') ; n'invente rien. "
    "Renvoie un JSON avec une seule clé : memo_markdown (str)."
)


def make_memo(company: Dict[str, Any], thesis: Thesis) -> str:
    user = (
        f"Thèse :\n{thesis.to_prompt_block()}\n\n"
        f"Cible : {company.get('name')} — score {company.get('fit_score')}/100, "
        f"reco {company.get('recommended_action')}\n"
        f"Activité : {company.get('what_they_do')}\n"
        f"Business model : {company.get('business_model')}\n"
        f"Justification du score : {company.get('rationale')}\n"
        f"Risques identifiés : {', '.join(company.get('risks', []) or [])}\n"
        f"Signaux de croissance : {', '.join(company.get('growth_signals', []) or [])}"
    )
    result = llm.complete_json(MEMO_SYSTEM, user, max_tokens=3000)
    return result.get("memo_markdown", f"## {company.get('name')}\n(note indisponible)")
