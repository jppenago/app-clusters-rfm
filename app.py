"""
Análisis RFM de Audiencias — Aplicación Streamlit

Flujo de uso:
  1. El usuario sube un CSV con la columna `llave_sistema`.
  2. La app extrae los datos RFM desde BigQuery (o datos simulados en dev).
  3. Se aplica K-Means Clustering sobre recencia, frecuencia y valor_total.
  4. Se muestran los resultados de forma visual y descriptiva.

Arquitectura
------------
Este script actúa como orquestador delgado. Toda la UI está encapsulada en
componentes reutilizables ubicados en ``components/``, siguiendo el principio
de responsabilidad única (SOLID-S) al estilo de componentes React.
"""

from __future__ import annotations

import warnings

import pandas as pd
import streamlit as st

# Las bibliotecas de Google emiten FutureWarning sobre Python 3.9 siendo EOL.
# No son accionables sin actualizar Python, por lo que se suprimen para evitar
# que ensucien la consola en entornos que no pueden migrar aún.
warnings.filterwarnings("ignore", category=FutureWarning, module=r"google\.")

from components.data_source import render_data_source
from components.empty_state import render_empty_state
from components.header import render_header
from components.metrics_bar import render_metrics_bar
from components.sidebar import render_sidebar
from components.styles import render_styles
from components.tab_data import render_data_tab
from components.tab_statistics import render_stats_tab
from components.tab_visualizations import render_viz_tab
from components.tab_ai import render_ai_tab  # Importamos el Asistente IA
from src.bigquery_client import filter_by_categories, get_categorical_options
from src.clustering import ClusteringResult, apply_kmeans, get_cluster_summary

from dotenv import load_dotenv

load_dotenv()

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Análisis RFM · Audiencias",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_styles()

# ── Session state ─────────────────────────────────────────────────────────────
_STATE_DEFAULTS: dict = {
    "result": None,
    "summary": None,
    "n_clusters_used": None,
    "selected_algo": None,
    "messages": [],
    "raw_rfm_df": None,
    "loaded_file_sig": None,
}
for key, val in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Sidebar ───────────────────────────────────────────────────────────────────
# Recibimos tanto la configuración como la señal del botón 'run_model'
sidebar_cfg, run_model = render_sidebar(st.session_state.get("raw_rfm_df"))
n_clusters: int = sidebar_cfg.n_clusters
winsorize: bool = sidebar_cfg.winsorize
winsor_pct: float = sidebar_cfg.winsor_pct

render_header()

# ── Fuente de datos ───────────────────────────────────────────────────────────
data_cfg = render_data_source(n_clusters)
_source_sig = data_cfg.source_sig
_loader = data_cfg.loader
_n_requested = data_cfg.n_requested

# ── Procesamiento ─────────────────────────────────────────────────────────────
if _source_sig is not None and _loader is not None:

    if st.session_state["loaded_file_sig"] != _source_sig:
        with st.spinner("📡 Cargando datos desde BigQuery…"):
            st.session_state["raw_rfm_df"] = _loader()
        st.session_state["loaded_file_sig"] = _source_sig
        st.session_state["result"] = None
        st.session_state["summary"] = None
        for _k in [k for k in st.session_state.keys() if k.startswith("filter_")]:
            del st.session_state[_k]
        st.rerun()

    _raw_df: pd.DataFrame = st.session_state["raw_rfm_df"]

    if _raw_df is None or _raw_df.empty:
        st.warning("⚠️ No se obtuvieron registros para la fuente seleccionada.")
        st.stop()

    n_clients = _n_requested if _n_requested is not None else len(_raw_df)

    _selections = {
        _col: st.session_state.get(f"filter_{_col}", _vals)
        for _col, _vals in get_categorical_options(_raw_df).items()
    }
    _filtered_preview = filter_by_categories(_raw_df, _selections)
    _n_filtered = len(_filtered_preview)

    if _n_filtered < n_clients:
        if _n_filtered < n_clusters:
            st.warning(
                f"⚠️ Tras aplicar los filtros solo quedan {_n_filtered:,} clientes, "
                f"que es menor que K={n_clusters}. Ajusta los filtros o reduce K."
            )
            st.stop()

    st.divider()

    # Reemplazamos el antiguo st.button por la señal `run_model` del Sidebar
    if run_model:
        with st.status("Procesando análisis…", expanded=True):

            rfm_df: pd.DataFrame = st.session_state["raw_rfm_df"].copy()
            _selections_btn = {
                _col: st.session_state.get(f"filter_{_col}", _vals)
                for _col, _vals in get_categorical_options(rfm_df).items()
            }
            rfm_df = filter_by_categories(rfm_df, _selections_btn)

            if rfm_df.empty or len(rfm_df) < n_clusters:
                st.error(
                    f"Tras aplicar los filtros solo quedan {len(rfm_df):,} registros, "
                    f"que es menor que K={n_clusters}. Ajusta los filtros o reduce K."
                )
                st.stop()

            try:
                result: ClusteringResult = apply_kmeans(
                    rfm_df,
                    n_clusters,
                    winsorize=winsorize,
                    winsor_pct=winsor_pct,
                )
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

            summary: pd.DataFrame = get_cluster_summary(result.df)

            st.session_state["result"] = result
            st.session_state["summary"] = summary
            st.session_state["n_clusters_used"] = len(result.df["cluster"].unique())
            st.session_state["selected_algo"] = "K-Means (Machine Learning)"
            st.session_state["messages"] = []

# ── Resultados ────────────────────────────────────────────────────────────────
if st.session_state["result"] is not None:

    result: ClusteringResult = st.session_state["result"]
    summary = st.session_state["summary"]
    n_used: int = st.session_state["n_clusters_used"]
    clust_df = result.df

    st.markdown(
        "<p class='section-label' style='margin-top:1.5rem;'>Resultados del análisis</p>",
        unsafe_allow_html=True,
    )

    render_metrics_bar(result, n_used)
    st.divider()

    # Añadimos la nueva pestaña del Asistente IA a la interfaz
    tab_viz, tab_stats, tab_data, tab_ai = st.tabs(
        [
            "Visualizaciones",
            "Estadísticas por Cluster",
            "Tabla de Datos",
            "🤖 Asistente IA",
        ]
    )

    with tab_viz:
        render_viz_tab(clust_df, summary)

    with tab_stats:
        render_stats_tab(summary, clust_df)

    with tab_data:
        render_data_tab(clust_df)

    with tab_ai:
        render_ai_tab(summary)

else:
    if st.session_state.get("raw_rfm_df") is None:
        render_empty_state()
