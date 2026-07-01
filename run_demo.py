#!/usr/bin/env python3
"""
run_demo.py — lance le pipeline en ligne de commande.

Exemples :
    python run_demo.py --mock                 # tourne sans clé API (données simulées)
    python run_demo.py --thesis default --limit 12 --top 3
    LLM_PROVIDER=anthropic python run_demo.py  # vrai LLM (clé dans .env)

Sorties : outputs/shortlist.csv  +  outputs/memos/*.md
"""
import argparse
import csv
import os

from src import config
from src.config import get_thesis
from src.pipeline import run_pipeline, ranked_to_rows


def main():
    ap = argparse.ArgumentParser(description="Agent de sourcing PE mid-cap")
    ap.add_argument("--thesis", default="default", help="clé de thèse (default | industrial_services)")
    ap.add_argument("--limit", type=int, default=12, help="taille de l'univers à analyser")
    ap.add_argument("--top", type=int, default=3, help="nombre de mémos à générer")
    ap.add_argument("--mock", action="store_true", help="force le mode mock (aucune clé requise)")
    ap.add_argument("--no-pappers", action="store_true", help="ignore Pappers, force le CSV seed")
    args = ap.parse_args()

    if args.mock:
        config.LLM_PROVIDER = "mock"

    print(f"Provider LLM : {config.LLM_PROVIDER}  |  Thèse : {args.thesis}\n")
    thesis = get_thesis(args.thesis)

    result = run_pipeline(
        thesis,
        limit=args.limit,
        top_n=args.top,
        use_pappers=not args.no_pappers,
        progress=print,
    )

    rows = ranked_to_rows(result["ranked"])

    # Tableau résumé en console
    print("\n=== SHORTLIST ===")
    for r in rows:
        print(f"  {r['Score']:>3}  {r['Société']:<22}  {r['Reco']:<12}  {r['Activité'][:60]}")

    # Écriture des fichiers
    os.makedirs("outputs/memos", exist_ok=True)
    with open("outputs/shortlist.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    for name, md in result["memos"].items():
        safe = "".join(ch if ch.isalnum() else "_" for ch in name)
        with open(f"outputs/memos/{safe}.md", "w", encoding="utf-8") as f:
            f.write(md)

    print(f"\n✓ outputs/shortlist.csv  +  {len(result['memos'])} mémo(s) dans outputs/memos/")


if __name__ == "__main__":
    main()
