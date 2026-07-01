"""config.py — variables d'env + thèses (raisonnement sur le CA)."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default) or default


LLM_PROVIDER = get_env("LLM_PROVIDER", "mock").lower()
LLM_MODEL = get_env("LLM_MODEL", "")
ANTHROPIC_API_KEY = get_env("ANTHROPIC_API_KEY")
OPENAI_API_KEY = get_env("OPENAI_API_KEY")
PAPPERS_API_KEY = get_env("PAPPERS_API_KEY")


@dataclass
class Thesis:
    name: str
    sectors: List[str] = field(default_factory=list)
    geographies: List[str] = field(default_factory=list)
    ca_min_m: float = 20          # chiffre d'affaires mini (M€)
    ca_max_m: float = 300         # chiffre d'affaires maxi (M€)
    criteria: str = ""

    def to_prompt_block(self) -> str:
        return (
            f"Nom de la thèse : {self.name}\n"
            f"Secteurs visés : {', '.join(self.sectors) or 'tous'}\n"
            f"Géographies : {', '.join(self.geographies) or 'Europe'}\n"
            f"Fourchette de chiffre d'affaires : {self.ca_min_m}–{self.ca_max_m} M€ "
            f"(la valeur d'entreprise n'étant pas publique, on raisonne sur le CA)\n"
            f"Critères qualitatifs : {self.criteria or 'non précisés'}"
        )


THESES = {
    "default": Thesis(
        name="Orso — champions français & italiens du mid-market, à potentiel international",
        sectors=["Business Services", "Santé / Healthcare", "Technology / logiciel",
                 "Industrie de niche"],
        geographies=["France", "Italie"],
        ca_min_m=20,
        ca_max_m=300,
        criteria=("Champion national doté d'une équipe de management de talent, à transformer "
                  "en leader international. Position de leader sur une niche défendable, "
                  "croissance soutenue, revenus récurrents ou récurrents-like, potentiel "
                  "d'expansion internationale et de build-up par acquisitions complémentaires."),
    ),
    "industrial_services": Thesis(
        name="Services industriels & B2B — consolidation de niche",
        sectors=["services industriels", "maintenance", "distribution B2B spécialisée"],
        geographies=["France", "DACH", "Benelux"],
        ca_min_m=30,
        ca_max_m=250,
        criteria=("Récurrence des contrats, fragmentation du marché propice au build-up, "
                  "marges solides, faible cyclicité, management prêt à réinvestir."),
    ),
}


def get_thesis(key: str = "default") -> Thesis:
    return THESES.get(key, THESES["default"])