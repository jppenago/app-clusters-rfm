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
    st.markdown("##### 📊 Promedio de metricas por cluster")
    st.caption(
        "Medianas de Recencia, Frecuencia y Valor Total para cada segmento identificado."
    )
    st.plotly_chart(plot_cluster_comparison_bars(summary), use_container_width=True)

    st.markdown("---")

    # ── Bloque 2: Vista 3D y distribución de tamaños ────────────────────────
    st.markdown("##### 🌐 Distribución por Cluster")
    _, col_donut, _ = st.columns([1, 3, 1])
    with col_donut:
        st.plotly_chart(plot_cluster_sizes(clust_df), use_container_width=True)

    with st.expander("🌐 Vista tridimensional", expanded=False):
        st.plotly_chart(plot_3d_scatter(clust_df), use_container_width=True)

    st.markdown("---")

    # ── Bloque 3: Distribuciones estadísticas (ancho completo) ──────────────
    st.markdown("##### 📦 Distribución de Variables RFM por Cluster")
    st.caption(
        "Boxplots de Recencia, Frecuencia y Valor Total por cluster. "
        "Permite comparar la dispersión y medianas entre segmentos."
    )
    st.plotly_chart(plot_feature_boxplots(clust_df), use_container_width=True)

    st.markdown("---")

    # ── Bloque 4: Perfil normalizado (radar) ────────────────────────────────
    st.markdown("##### 🕸️ Perfil normalizado")
    st.caption(
        "Comparación relativa de cada segmento en las tres dimensiones RFM. "
        "Mayor área = mejor perfil de cliente."
    )
    _, col_radar, _ = st.columns([1, 3, 1])
    with col_radar:
        st.plotly_chart(plot_radar_chart(summary), use_container_width=True)
