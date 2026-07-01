"""enrich.py — enrichissement avec recherche web réelle (DuckDuckGo)."""
from __future__ import annotations
from typing import Dict, Any, List, Tuple

from . import llm

ENRICH_SYSTEM = (
    "Tu es analyste en ENRICHISSEMENT de données pour un fonds de private equity. "
    "À partir du nom d'une société, de ses données registre et de RÉSULTATS DE RECHERCHE WEB, "
    "produis une fiche factuelle et concise. Appuie-toi PRIORITAIREMENT sur les résultats web "
    "(ce sont des faits). Si une information manque ou est incertaine, marque-la '[hypothèse]' "
    "et n'invente jamais de produit, client ou chiffre. "
    "Renvoie un JSON avec : what_they_do (str), summary (str), business_model (str), "
    "growth_signals (liste de str)."
)

EXCLUDE_DOMAINS = ("societe.com", "pappers.fr", "linkedin.com", "wikipedia.org",
                   "verif.com", "infogreffe.fr", "facebook.com", "youtube.com",
                   "bodacc", "score3", "manageo", "kompass", "indeed", "glassdoor")


def web_research(name: str, city: str = "", max_results: int = 5) -> Tuple[str, str]:
    """Recherche web gratuite (DuckDuckGo). Renvoie (contexte_texte, url_site_probable)."""
    query = f"{name} {city}".strip() + " entreprise activité"
    rows: List[dict] = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            rows = list(ddgs.text(query, region="fr-fr", max_results=max_results))
    except Exception as e:
        print(f"[web] recherche échouée ({name}) : {e}")
        return "", ""

    lines, site = [], ""
    for r in rows:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href") or r.get("url") or r.get("link") or ""
        lines.append(f"- {title} — {body} ({href})")
        if not site and href and not any(d in href.lower() for d in EXCLUDE_DOMAINS):
            site = href
    return "\n".join(lines), site


def fetch_website_text(url: str, max_chars: int = 4000) -> str:
    if not url:
        return ""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (sourcing-agent demo)"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return " ".join(soup.get_text(separator=" ").split())[:max_chars]
    except Exception as e:
        print(f"[enrich] site inaccessible ({url}) : {e}")
        return ""


def enrich_company(company: Dict[str, Any]) -> Dict[str, Any]:
    name = company.get("name", "")
    city = company.get("city", "")
    web_context, discovered_site = web_research(name, city)
    url = company.get("website") or discovered_site
    site_text = fetch_website_text(url) if url else ""

    user = (
        f"Société : {name}\n"
        f"Localisation : {city}\n"
        f"Secteur (NAF) : {company.get('sector')}\n"
        f"Chiffre d'affaires connu : {company.get('revenue_eur')}\n"
        f"Effectif : {company.get('headcount')}\n"
        f"Site probable : {url or '(inconnu)'}\n\n"
        f"RÉSULTATS DE RECHERCHE WEB :\n{web_context or '(aucun résultat)'}\n\n"
        f"EXTRAIT DU SITE :\n{site_text or '(non disponible)'}"
    )
    fiche = llm.complete_json(ENRICH_SYSTEM, user, max_tokens=1200)
    enriched = dict(company)
    enriched.update({
        "what_they_do": fiche.get("what_they_do", ""),
        "summary": fiche.get("summary", ""),
        "business_model": fiche.get("business_model", ""),
        "growth_signals": fiche.get("growth_signals", []),
        "website": url,
        "_web_found": bool(web_context),
        "_site_fetched": bool(site_text),
    })
    return enriched