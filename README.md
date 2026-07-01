# Orso Sourcing Agent

Agent de **sourcing & screening** pour le private equity mid-cap. À partir d'une
thèse d'investissement, il source des sociétés réelles dans le registre public
français, les enrichit, les score contre la thèse, et génère des notes
d'investissement de phase 1.

## Pipeline

`thèse → sourcing → enrichissement → scoring → notes`

| Étape | Fichier | Rôle |
|-------|---------|------|
| Sourcing | `src/sources.py` | Univers de sociétés (API Recherche d'entreprises, filtré par secteur, taille, CA) |
| Enrichissement | `src/enrich.py` | Fiche société à partir des données disponibles |
| Scoring | `src/score.py` | Note d'adéquation à la thèse (0-100), justification, risques |
| Notes | `src/memo.py` | Note d'investissement phase 1 par cible top |
| Orchestration | `src/pipeline.py` | Enchaîne les étapes |
| Interface | `app.py` | Application Streamlit |

## Stack

Python · Streamlit · [API Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr) (data.gouv, gratuite) · LLM (Claude ou OpenAI)

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # renseigner LLM_PROVIDER + clé API
streamlit run app.py
```

## Données

Sourcing depuis le **registre public officiel** des entreprises françaises,
filtré par code NAF (secteur), tranche d'effectif et chiffre d'affaires. La
valeur d'entreprise n'étant pas publique, le raisonnement se fait sur le CA.

## Limites & feuille de route

- Couverture France ; extension prévue à l'Italie (Registro Imprese) et au DACH/Benelux.
- Enrichissement web société par société (en cours) pour ancrer l'analyse sur des faits réels.
- RAG sur la doctrine d'investissement et les rapports sectoriels.
- Serveur MCP pour connecter l'agent aux outils internes (CRM deal, data room).
- Architecture multi-agents (scout → analyste → rédacteur).

---