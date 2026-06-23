"""
Componente del tab de estadísticas por cluster.

Responsabilidad única: renderizar las tarjetas de estadísticas descriptivas
de cada cluster (métricas medianas, frontera de decisión y desglose cuantitativo).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

_CLUSTER_PALETTE: list[str] = [
    "#6366F1",
    "#3B82F6",
    "#06B6D4",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F97316",
    "#84CC16",
]


def render_stats_tab(summary: pd.DataFrame, clust_df: pd.DataFrame) -> None:
    """
    Renderiza el contenido del tab de estadísticas por cluster.

    Parameters
    ----------
    summary:
        DataFrame de resumen por cluster generado por ``get_cluster_summary``.
    clust_df:
        DataFrame completo con columnas RFM + ``cluster``.
    """
    st.markdown(
        "<p style='font-size:1.1rem;font-weight:600;color:#0F172A;margin-bottom:1rem;display:flex;align-items:center;'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#6366F1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' style='margin-right:8px;flex-shrink:0;'><line x1='18' y1='20' x2='18' y2='10'/><line x1='12' y1='20' x2='12' y2='4'/><line x1='6' y1='20' x2='6' y2='14'/></svg>"
        "Estadísticas Descriptivas por Cluster</p>",
        unsafe_allow_html=True,
    )

    for _, row in summary.sort_values("cluster").iterrows():
        _render_cluster_card(row, clust_df)


# ── Sub-renderizadores privados ───────────────────────────────────────────────


def _render_cluster_card(row: pd.Series, clust_df: pd.DataFrame) -> None:
    """Renderiza la tarjeta de un único cluster."""
    cid = int(row["cluster"])
    n_c = int(row["n_clientes"])
    pct = row["porcentaje"]
    c_color = _CLUSTER_PALETTE[(cid - 1) % len(_CLUSTER_PALETTE)]

    with st.container(border=True):
        # Encabezado del clúster
        st.markdown(
            f"""
            <div style='display:flex;align-items:center;justify-content:space-between;
                        border-bottom:1px solid #E2E8F0;padding-bottom:0.8rem;margin-bottom:1rem;'>
                <div style='display:flex;align-items:center;gap:0.75rem;'>
                    <span style='width:14px;height:14px;border-radius:50%;
                                 background:{c_color};display:inline-block;'></span>
                    <div>
                        <h4 style='margin:0;color:{c_color};font-weight:700;display:inline-block;'>
                            Cluster {cid}
                        </h4>
                    </div>
                </div>
                <div style='text-align:right;'>
                    <span style='background:{c_color}22;color:{c_color};font-size:0.8rem;
                                 font-weight:700;padding:0.3rem 0.8rem;border-radius:999px;'>
                        {n_c:,} clientes ({pct:.2f}%)
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Frontera de decisión (Decision Tree)
        p_rules = row.get("reglas_automaticas", "Sujeto a distribución general")

        # Métricas medianas
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric(
            "Recencia Promedio",
            f"{row['recencia_median']:.1f} días",
            help="Calculado usando la mediana.",
        )
        sc2.metric(
            "Frecuencia Promedio",
            f"{row['frecuencia_median']:.1f} tx",
            help="Calculado usando la mediana.",
        )
        sc3.metric(
            "Monto Promedio (COP)",
            f"${row['valor_total_median']:,.0f}",
            help="Calculado usando la mediana.",
        )

        _render_quantitative_breakdown(cid, clust_df)


def _render_quantitative_breakdown(cid: int, clust_df: pd.DataFrame) -> None:
    """Renderiza el expander con estadísticas descriptivas completas de un cluster."""
    features_info = [
        ("recencia", "Recencia", "días"),
        ("frecuencia", "Frecuencia", "transacciones"),
        ("valor_total", "Valor Total", "COP"),
    ]
    stat_cols = st.columns(3)
    for col_widget, (feat, feat_label, unit) in zip(stat_cols, features_info):
        with col_widget:
            st.markdown(f"**{feat_label}** _{unit}_")
            feat_data = clust_df.loc[clust_df["cluster"] == cid, feat]
            desc = (
                feat_data.describe()
                .rename(
                    {
                        "count": "N",
                        "mean": "Media",
                        "std": "Desv. Est.",
                        "min": "Mínimo",
                        "25%": "P25",
                        "50%": "Mediana",
                        "75%": "P75",
                        "max": "Máximo",
                    }
                )
                .to_frame(name=unit)
                .round(2)
            )
            if feat == "valor_total":
                money_rows = [r for r in desc.index if r != "N"]
                desc[unit] = desc[unit].astype(object)
                desc.loc[money_rows, unit] = desc.loc[money_rows, unit].apply(
                    lambda x: f"$ {x:,.0f}"
                )
            st.dataframe(desc, use_container_width=True)
