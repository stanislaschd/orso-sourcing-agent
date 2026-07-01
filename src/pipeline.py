"""
pipeline.py
───────────
Orchestrateur : enchaîne les 4 étapes pour produire un shortlist classé.

    thèse ──► [sourcing] ──► [enrichissement] ──► [scoring] ──► tri ──► [mémos]

C'est la fonction qu'appellent à la fois le script CLI (run_demo.py) et l'UI
Streamlit (app.py).
"""
from __future__ import annotations
from typing import Dict, Any, List, Callable, Optional

from . import sources, enrich, score, memo
from .config import Thesis


def _ca_bounds_eur(
    thesis: Thesis,
    ca_min_eur: Optional[int] = None,
    ca_max_eur: Optional[int] = None,
) -> tuple[int, int]:
    """Dérive la fourchette CA (€) depuis la thèse, sauf override explicite."""
    ca_min = ca_min_eur if ca_min_eur is not None else int(thesis.ca_min_m * 1_000_000)
    ca_max = ca_max_eur if ca_max_eur is not None else int(thesis.ca_max_m * 1_000_000)
    return ca_min, ca_max


def run_pipeline(
    thesis: Thesis,
    limit: int = 12,
    top_n: int = 3,
    use_pappers: bool = True,
    ca_min_eur: Optional[int] = None,
    ca_max_eur: Optional[int] = None,
    progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Exécute le pipeline. La fourchette CA vient de la thèse (M€ → €)."""
    log = progress or (lambda msg: None)

    ca_min, ca_max = _ca_bounds_eur(thesis, ca_min_eur, ca_max_eur)
    src_kwargs: Dict[str, Any] = {"ca_min": ca_min, "ca_max": ca_max}

    log(f"① Sourcing de l'univers (limite {limit}, CA {ca_min // 1_000_000}–{ca_max // 1_000_000} M€)…")
    universe = sources.get_universe(use_pappers=use_pappers, limit=limit, **src_kwargs)
    log(f"   {len(universe)} sociétés trouvées.")

    scored: List[Dict[str, Any]] = []
    for i, company in enumerate(universe, 1):
        name = company.get("name", "?")
        log(f"② Enrichissement {i}/{len(universe)} : {name}…")
        enriched = enrich.enrich_company(company)
        log(f"③ Scoring : {name}…")
        scored.append(score.score_company(enriched, thesis))

    # Tri décroissant par score d'adéquation
    ranked = sorted(scored, key=lambda c: c.get("fit_score", 0), reverse=True)

    log(f"④ Rédaction des mémos (top {top_n})…")
    memos: Dict[str, str] = {}
    for company in ranked[:top_n]:
        memos[company["name"]] = memo.make_memo(company, thesis)

    log("✓ Terminé.")
    return {"ranked": ranked, "memos": memos}


def ranked_to_rows(ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aplatit le résultat pour un tableau (CSV / DataFrame)."""
    rows = []
    for c in ranked:
        rows.append({
            "Société": c.get("name"),
            "Score": c.get("fit_score"),
            "Reco": c.get("recommended_action"),
            "Activité": c.get("what_they_do"),
            "Justification": c.get("rationale"),
            "Risques": "; ".join(c.get("risks", []) or []),
            "Site": c.get("website"),
        })
    return rows
