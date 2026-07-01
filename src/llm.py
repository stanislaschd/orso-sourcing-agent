"""
llm.py
──────
Couche d'abstraction au-dessus des LLM. Tout le reste du code appelle
`complete_json(...)` SANS savoir si derrière c'est Claude, GPT, ou un faux
LLM ("mock") qui renvoie des données simulées.

Concept clé — la "sortie structurée" :
On ne veut pas que le LLM réponde en prose ; on veut un objet JSON exploitable
par du code (un score, des champs précis). La technique : on lui DEMANDE
explicitement de répondre en JSON, puis on parse la réponse. C'est la base de
tout pipeline "LLM-as-a-component".
"""
from __future__ import annotations
import json
import re
import hashlib
from typing import Any, Dict

from . import config


# ── Point d'entrée unique ───────────────────────────────────────────────────
def complete_json(system: str, user: str, *, max_tokens: int = 1200) -> Dict[str, Any]:
    """
    Envoie (system, user) au LLM configuré et renvoie un dict Python.
    Bascule automatiquement sur le provider défini dans .env (LLM_PROVIDER).
    """
    provider = config.LLM_PROVIDER
    if provider == "anthropic":
        raw = _call_anthropic(system, user, max_tokens)
    elif provider == "openai":
        raw = _call_openai(system, user, max_tokens)
    else:  # "mock" ou inconnu → données simulées, aucune clé requise
        return _mock_json(system, user)
    try:
        return _extract_json(raw)
    except Exception as e:
        print(f"[llm] JSON illisible, on continue avec une fiche vide : {e}")
        return {}


# ── Implémentations par provider (importées paresseusement) ─────────────────
def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    import anthropic  # importé seulement si on utilise vraiment Anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    model = config.LLM_MODEL or "claude-sonnet-4-5"
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system + "\n\nRéponds UNIQUEMENT avec un objet JSON valide, sans texte autour.",
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _call_openai(system: str, user: str, max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    model = config.LLM_MODEL or "gpt-4o"
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system + "\n\nRéponds uniquement en JSON valide."},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


# ── Parsing robuste ─────────────────────────────────────────────────────────
def _extract_json(raw: str) -> Dict[str, Any]:
    """Extrait le premier bloc JSON d'une réponse, même si le LLM bavarde."""
    raw = raw.strip()
    # retire d'éventuelles balises ```json ... ```
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


# ── Mode mock : pipeline complet sans aucune clé API ────────────────────────
def _mock_json(system: str, user: str) -> Dict[str, Any]:
    """
    Renvoie des données plausibles et DÉTERMINISTES (basées sur un hash) selon
    le type d'appel détecté. Permet de faire tourner toute la démo hors-ligne.
    """
    seed = int(hashlib.md5(user.encode("utf-8")).hexdigest(), 16)

    if "ENRICHISSEMENT" in system:
        return {
            "what_they_do": "Éditeur de logiciel B2B en mode SaaS pour [fonction métier].",
            "summary": "Société de croissance positionnée sur une niche, modèle d'abonnement.",
            "growth_signals": ["recrutements en cours", "expansion internationale", "levée récente"],
            "business_model": "Abonnement récurrent (SaaS)",
        }
    if "SCORING" in system:
        base = 55 + (seed % 40)  # score entre 55 et 94
        return {
            "fit_score": base,
            "subscores": {
                "thesis_fit": 50 + (seed % 50),
                "growth": 40 + (seed // 7 % 60),
                "business_quality": 45 + (seed // 13 % 55),
                "defensibility": 40 + (seed // 17 % 60),
            },
            "rationale": "Bon alignement secteur/géographie ; signaux de croissance présents ; "
                         "modèle récurrent. À valider : taille réelle vs fourchette de VE.",
            "risks": ["taille possiblement hors fourchette", "concurrence sur la niche"],
            "recommended_action": "À étudier" if base >= 70 else "À surveiller",
        }
    if "MEMO" in system:
        return {
            "memo_markdown": "## Note de synthèse (simulée)\n\n*Mode mock — branche une clé API "
                             "pour une vraie analyse.*\n\n- **Thèse** : alignement à confirmer\n"
                             "- **Forces** : modèle récurrent, niche\n- **Risques** : taille, concurrence"
        }
    return {"note": "mock"}
