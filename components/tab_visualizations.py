"""
Componente del tab de visualizaciones.

Responsabilidad única: renderizar todos los gráficos Plotly del tab
"Visualizaciones" (comparativa, scatter 3D, donut, boxplots y radar).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.visualization import (
    plot_3d_scatter,
    plot_cluster_comparison_bars,
    plot_cluster_sizes,
    plot_feature_boxplots,
    plot_radar_chart,
)


def render_viz_tab(clust_df: pd.DataFrame, summary: pd.DataFrame) -> None:
    """
    Renderiza el contenido del tab de visualizaciones.

    Parameters
    ----------
    clust_df:
        DataFrame con columnas RFM + ``cluster`` (y ``*_scaled`` si aplica).
    summary:
        DataFrame de resumen por cluster generado por ``get_cluster_summary``.
    """
    # ── Bloque 1: Comparativa directa ──────────────────────────────────────
    st.markdown(
        "<p class='section-heading'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='#6366F1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' style='vertical-align:-3px;margin-right:6px;flex-shrink:0;'><line x1='18' y1='20' x2='18' y2='10'/><line x1='12' y1='20' x2='12' y2='4'/><line x1='6' y1='20' x2='6' y2='14'/></svg>"
        "Promedio de métricas por cluster</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Medianas de Recencia, Frecuencia y Valor Total para cada segmento identificado."
    )
    st.plotly_chart(plot_cluster_comparison_bars(summary), use_container_width=True)

    st.markdown("---")

    # ── Bloque 2: Vista 3D y distribución de tamaños ────────────────────────
    st.markdown(
        "<p class='section-heading'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='#6366F1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' style='vertical-align:-3px;margin-right:6px;flex-shrink:0;'><polygon points='12 2 2 7 12 12 22 7 12 2'/><polyline points='2 17 12 22 22 17'/><polyline points='2 12 12 17 22 12'/></svg>"
        "Distribución por Cluster</p>",
        unsafe_allow_html=True,
    )
    _, col_donut, _ = st.columns([1, 3, 1])
    with col_donut:
        st.plotly_chart(plot_cluster_sizes(clust_df), use_container_width=True)

    with st.expander("Vista tridimensional", expanded=False):
        st.plotly_chart(plot_3d_scatter(clust_df), use_container_width=True)

    st.markdown("---")

    # ── Bloque 3: Distribuciones estadísticas (ancho completo) ──────────────
    st.markdown(
        "<p class='section-heading'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='#6366F1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' style='vertical-align:-3px;margin-right:6px;flex-shrink:0;'><rect x='4' y='8' width='16' height='8'/><line x1='12' y1='2' x2='12' y2='8'/><line x1='12' y1='16' x2='12' y2='22'/><line x1='8' y1='2' x2='16' y2='2'/><line x1='8' y1='22' x2='16' y2='22'/></svg>"
        "Distribución de Variables RFM por Cluster</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Boxplots de Recencia, Frecuencia y Valor Total por cluster. "
        "Permite comparar la dispersión y medianas entre segmentos."
    )
    st.plotly_chart(plot_feature_boxplots(clust_df), use_container_width=True)

    st.markdown("---")

    # ── Bloque 4: Perfil normalizado (radar) ────────────────────────────────
    st.markdown(
        "<p class='section-heading'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='#6366F1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' style='vertical-align:-3px;margin-right:6px;flex-shrink:0;'><polygon points='12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5'/><line x1='12' y1='2' x2='12' y2='22'/><line x1='22' y1='8.5' x2='2' y2='15.5'/><line x1='2' y1='8.5' x2='22' y2='15.5'/></svg>"
        "Perfil normalizado</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Comparación relativa de cada segmento en las tres dimensiones RFM. "
        "Mayor área = mejor perfil de cliente."
    )
    _, col_radar, _ = st.columns([1, 3, 1])
    with col_radar:
        st.plotly_chart(plot_radar_chart(summary), use_container_width=True)
