"""
Componente del tab de tabla de datos.

Responsabilidad única: renderizar la tabla interactiva de clientes etiquetados
por cluster, con filtro de cluster y botón de descarga CSV.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_data_tab(clust_df: pd.DataFrame) -> None:
    """
    Renderiza el contenido del tab de tabla de datos.

    Parameters
    ----------
    clust_df:
        DataFrame completo con columnas RFM + ``cluster``.
    """
    st.markdown(
        "<p class='section-label'>Datos etiquetados por Cluster</p>",
        unsafe_allow_html=True,
    )

    cluster_options = ["Todos"] + [
        f"Cluster {c}" for c in sorted(clust_df["cluster"].unique())
    ]
    selected = st.selectbox("Filtrar por cluster:", cluster_options)

    if selected == "Todos":
        display_df = clust_df
    else:
        cid_filter = int(selected.split()[1])
        display_df = clust_df[clust_df["cluster"] == cid_filter]

    display_fmt = display_df.sort_values("cluster").reset_index(drop=True).copy()
    display_fmt["valor_total"] = display_fmt["valor_total"].apply(
        lambda x: f"$ {x:,.0f}"
    )
    st.dataframe(display_fmt, use_container_width=True)

    csv_out = clust_df.to_csv(index=False)
    st.download_button(
        "↓ Descargar resultados completos (CSV)",
        data=csv_out,
        file_name="audiencia_clusterizada.csv",
        mime="text/csv",
        use_container_width=True,
    )
