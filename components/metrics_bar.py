"""
Componente de barra de métricas resumen.

Responsabilidad única: renderizar la fila de cinco KPI-cards que resume los
resultados generales del clustering (total clientes, K, Silhouette, etc.).
"""

from __future__ import annotations

import streamlit as st

from src.clustering import ClusteringResult


def render_metrics_bar(result: ClusteringResult, n_used: int) -> None:
    """
    Renderiza la fila de métricas resumen del clustering.

    Parameters
    ----------
    result:
        Resultado del proceso de K-Means con métricas de calidad incluidas.
    n_used:
        Número efectivo de clusters generados (puede diferir de K pedido si
        hay menos puntos únicos que K).
    """
    m1, m2 = st.columns(2)

    m1.metric("Total Clientes", f"{len(result.df):,}")
    m2.metric("Clusters (K)", n_used)

    if getattr(result, "winsorized", False):
        st.caption(
            f"Outliers tratados con winsorizing al percentil {result.winsor_pct:.1f} "
            "(valores extremos recortados, sin eliminar clientes)."
        )
