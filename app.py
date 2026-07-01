"""app.py — interface de démo Streamlit, brandée Orso."""
import os
import glob
import base64
import streamlit as st
import pandas as pd

from src import config
from src.config import Thesis, get_thesis
from src.pipeline import run_pipeline, ranked_to_rows
from src.export import memo_to_docx_bytes

st.set_page_config(page_title="Orso Partners — Agent de sourcing", page_icon="🦊", layout="wide")

NAVY = "#1B2F6B"

_logos = glob.glob("data/orso_logo.*")
LOGO_PATH = _logos[0] if _logos else ""


def logo_data_uri(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    ext = "jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{ext};base64,{b64}"


st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 1120px;}
div[data-testid="stMetric"] {
    background: #F4F7FC; border: 1px solid #E1E8F2;
    border-radius: 14px; padding: 16px 20px;
}
div[data-testid="stMetricValue"] {color: #1B2F6B;}
details {border-radius: 12px !important;}
</style>
""", unsafe_allow_html=True)

logo_uri = logo_data_uri(LOGO_PATH)
logo_html = (
    f'<div style="background:#fff;border-radius:12px;padding:10px 16px;display:flex;align-items:center">'
    f'<img src="{logo_uri}" style="height:52px"/></div>' if logo_uri else ""
)
st.markdown(
    f"""
    <div style="background:linear-gradient(135deg,{NAVY},#33508F);border-radius:18px;
                padding:26px 34px;display:flex;align-items:center;gap:26px;margin-bottom:22px">
      {logo_html}
      <div>
        <div style="color:#fff;font-size:1.95rem;font-weight:700;line-height:1.15">
            Agent de sourcing &amp; screening</div>
        <div style="color:#C7D3EC;font-size:1.02rem;margin-top:6px">
            Private Equity mid-cap européen &nbsp;·&nbsp; sourcing dans le registre public
            &nbsp;·&nbsp; enrichissement &amp; scoring par IA</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    if LOGO_PATH:
        st.image(LOGO_PATH, width=150)
    st.header("⚙️ Configuration")
    provider_options = ["anthropic", "openai", "mock"]
    default_idx = provider_options.index(config.LLM_PROVIDER) if config.LLM_PROVIDER in provider_options else 0
    provider = st.selectbox("Moteur LLM", provider_options, index=default_idx)
    config.LLM_PROVIDER = provider
    if provider == "mock":
        st.info("Mode démo hors-ligne (données simulées).")
    limit = st.slider("Taille de l'univers", 3, 24, 8)
    top_n = st.slider("Nombre de mémos", 1, 5, 3)

st.subheader("1 · Thèse d'investissement")
preset = get_thesis("default")
c1, c2 = st.columns(2)
with c1:
    name = st.text_input("Nom de la thèse", preset.name)
    sectors = st.text_input("Secteurs (séparés par des virgules)", ", ".join(preset.sectors))
    geos = st.text_input("Géographies", ", ".join(preset.geographies))
with c2:
    ca_min = st.number_input("CA min (M€)", value=float(preset.ca_min_m))
    ca_max = st.number_input("CA max (M€)", value=float(preset.ca_max_m))
criteria = st.text_area("Critères qualitatifs", preset.criteria, height=90)

thesis = Thesis(
    name=name,
    sectors=[s.strip() for s in sectors.split(",") if s.strip()],
    geographies=[g.strip() for g in geos.split(",") if g.strip()],
    ca_min_m=ca_min, ca_max_m=ca_max, criteria=criteria,
)

st.subheader("2 · Lancer l'agent")
if st.button("🚀 Lancer le sourcing", type="primary"):
    status = st.empty()
    with st.spinner("L'agent source, enrichit et score les cibles…"):
        result = run_pipeline(thesis, limit=limit, top_n=top_n,
                              use_pappers=False,
                              progress=lambda m: status.write(m))
    status.empty()
    rows = ranked_to_rows(result["ranked"])
    df = pd.DataFrame(rows)

    n_total = len(df)
    n_priority = int((df["Reco"].isin(["Prioritaire", "À étudier"])).sum()) if n_total else 0
    avg = int(df["Score"].mean()) if n_total else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Cibles analysées", n_total)
    m2.metric("À étudier / prioritaires", n_priority)
    m3.metric("Score moyen", avg)

    st.subheader("3 · Shortlist classée")
    st.dataframe(
        df, width="stretch", hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "Site": st.column_config.LinkColumn("Site"),
        },
    )
    st.download_button("⬇️ Télécharger le CSV", df.to_csv(index=False).encode("utf-8"),
                       "shortlist.csv", "text/csv")

    st.subheader("4 · Notes de synthèse (top cibles)")
    for company_name, md in result["memos"].items():
        with st.expander(f"📄 {company_name}"):
            st.markdown(md)
            safe = "".join(ch if ch.isalnum() else "_" for ch in company_name)
            docx_bytes = memo_to_docx_bytes(md)
            if docx_bytes:
                st.download_button(
                    "⬇️ Télécharger en Word", docx_bytes,
                    file_name=f"note_{safe}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_{safe}",
                )
else:
    st.info("Configurez la thèse, puis cliquez sur \"Lancer le sourcing\".")