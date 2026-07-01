"""sources.py — couche SOURCING (registre public gratuit → Pappers → CSV)."""
from __future__ import annotations
import csv
import os
import time
import random
from typing import List, Dict, Any

from . import config

SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "data", "seed_companies.csv")

# Codes NAF par secteur (mandat Orso). À affiner librement.
NAF_DEFAULT = [
    # Technology / logiciel
    "62.01Z", "62.02A", "58.29C", "63.11Z",
    # Business Services
    "70.22Z", "78.20Z", "80.10Z", "81.21Z", "82.20Z",
    # Healthcare / santé
    "86.10Z", "21.20Z", "32.50A", "86.90A",
    # Niche Industrials
    "28.99B", "26.51B", "25.62B",
]

# Tranches d'effectif INSEE : 50 à 999 salariés (mid-market).
EFFECTIF_DEFAULT = ["21", "22", "31", "32", "41"]

# Fourchette de chiffre d'affaires cible (en euros). Ajuster selon la thèse.
CA_MIN_EUR = 20_000_000
CA_MAX_EUR = 500_000_000

EFFECTIF_LABELS = {
    "NN": "n/c", "00": "0", "01": "1-2", "02": "3-5", "03": "6-9",
    "11": "10-19", "12": "20-49", "21": "50-99", "22": "100-199",
    "31": "200-249", "32": "250-499", "41": "500-999", "42": "1000-1999",
    "51": "2000-4999", "52": "5000-9999", "53": "10000+",
}


def from_csv(path: str = SEED_PATH, limit: int | None = None) -> List[Dict[str, Any]]:
    companies: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            companies.append({
                "name": row.get("company_name", "").strip(),
                "website": row.get("website", "").strip(),
                "sector": row.get("sector_guess", "").strip(),
                "source": "seed_csv",
            })
    return companies[:limit] if limit else companies


def _latest_ca(finances: Dict[str, Any] | None) -> int | None:
    if not finances:
        return None
    try:
        year = max(finances.keys())
        return finances[year].get("ca")
    except Exception:
        return None


def from_recherche_entreprises(naf_codes: List[str] | None = None,
                               effectif_codes: List[str] | None = None,
                               ca_min: int = CA_MIN_EUR,
                               ca_max: int = CA_MAX_EUR,
                               query: str = "",
                               departments: List[str] | None = None,
                               limit: int = 20) -> List[Dict[str, Any]]:
    """API publique gratuite. Priorise les sociétés dont le CA est connu et dans la cible."""
    import requests
    naf_codes = naf_codes or NAF_DEFAULT
    naf_codes = random.sample(naf_codes, len(naf_codes))  # ordre des secteurs varié
    effectif_codes = effectif_codes or EFFECTIF_DEFAULT
    seen: set = set()
    in_band: List[Dict[str, Any]] = []
    others: List[Dict[str, Any]] = []

    for naf in naf_codes:
        if len(in_band) >= limit:
            break
        params: Dict[str, Any] = {
            "activite_principale": naf,
            "tranche_effectif_salarie": ",".join(effectif_codes),
            "etat_administratif": "A",
            "per_page": 15,
            "page": random.randint(1, 3),
        }
        if query:
            params["q"] = query
        if departments:
            params["departement"] = ",".join(departments)
        try:
            r = requests.get("https://recherche-entreprises.api.gouv.fr/search",
                             params=params, timeout=20)
            r.raise_for_status()
            results = r.json().get("results", [])
        except Exception as e:
            print(f"[gouv] NAF {naf} échec : {e}")
            continue

        for ent in results:
            siren = ent.get("siren")
            if not siren or siren in seen:
                continue
            seen.add(siren)
            siege = ent.get("siege") or {}
            eff = ent.get("tranche_effectif_salarie") or "NN"
            ca = _latest_ca(ent.get("finances"))
            company = {
                "name": ent.get("nom_complet") or ent.get("nom_raison_sociale", ""),
                "website": "",
                "sector": f"NAF {ent.get('activite_principale', '?')}",
                "siren": siren,
                "city": siege.get("libelle_commune", ""),
                "departement": siege.get("departement", ""),
                "headcount": f"{EFFECTIF_LABELS.get(eff, eff)} salariés",
                "revenue_eur": ca,
                "categorie": ent.get("categorie_entreprise", ""),
                "source": "recherche-entreprises.gouv",
            }
            if ca is not None and ca_min <= ca <= ca_max:
                in_band.append(company)
            elif ca is None:
                others.append(company)
        time.sleep(0.2)

    universe = in_band[:limit]
    if len(universe) < limit:
        universe += others[: limit - len(universe)]
    return universe


def _prioritize_by_ca(companies: List[Dict[str, Any]],
                      ca_min: int,
                      ca_max: int,
                      limit: int) -> List[Dict[str, Any]]:
    """Priorise les sociétés dont le CA est connu et dans la fourchette utilisateur."""
    in_band = [
        c for c in companies
        if (ca := c.get("revenue_eur")) is not None and ca_min <= ca <= ca_max
    ]
    unknown = [c for c in companies if c.get("revenue_eur") is None]
    universe = in_band[:limit]
    if len(universe) < limit:
        universe += unknown[: limit - len(universe)]
    return universe


def from_pappers(naf_codes: List[str] | None = None,
                 department: str | None = None,
                 ca_min: int = CA_MIN_EUR,
                 ca_max: int = CA_MAX_EUR,
                 limit: int = 20) -> List[Dict[str, Any]]:
    if not config.PAPPERS_API_KEY:
        return []
    import requests
    params: Dict[str, Any] = {
        "api_token": config.PAPPERS_API_KEY,
        "par_page": limit,
        "entreprise_cessee": "false",
    }
    if naf_codes:
        params["code_naf"] = ",".join(naf_codes)
    if department:
        params["departement"] = department
    try:
        r = requests.get("https://api.pappers.fr/v2/recherche", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[pappers] échec : {e}")
        return []
    out: List[Dict[str, Any]] = []
    for ent in data.get("resultats", []):
        out.append({
            "name": ent.get("nom_entreprise") or ent.get("denomination", ""),
            "website": ent.get("site_web", ""),
            "sector": ent.get("libelle_code_naf", ""),
            "siren": ent.get("siren", ""),
            "city": (ent.get("siege") or {}).get("ville", ""),
            "revenue_eur": ent.get("chiffre_affaires"),
            "headcount": ent.get("effectif"),
            "source": "pappers",
        })
    return _prioritize_by_ca(out, ca_min, ca_max, limit)


def get_universe(use_pappers: bool = True, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
    ca_min = kwargs.get("ca_min", CA_MIN_EUR)
    ca_max = kwargs.get("ca_max", CA_MAX_EUR)
    universe = from_recherche_entreprises(limit=limit, **kwargs)
    if universe:
        return universe
    print("[sources] API publique indisponible.")
    if use_pappers and config.PAPPERS_API_KEY:
        pappers_kwargs: Dict[str, Any] = {"limit": limit, "ca_min": ca_min, "ca_max": ca_max}
        if kwargs.get("naf_codes"):
            pappers_kwargs["naf_codes"] = kwargs["naf_codes"]
        dept = kwargs.get("department") or (
            kwargs["departments"][0] if kwargs.get("departments") else None
        )
        if dept:
            pappers_kwargs["department"] = dept
        universe = from_pappers(**pappers_kwargs)
        if universe:
            return universe
    print("[sources] → CSV seed (CA non filtré : pas de donnée financière dans le seed).")
    return from_csv(limit=limit)