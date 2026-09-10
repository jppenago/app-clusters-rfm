"""
Componente del tab de tabla de datos.

Responsabilidad única: renderizar la tabla interactiva de clientes etiquetados
por cluster, con filtro de cluster y botón de descarga CSV.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from src.storage_client import exportar_parquet_firmado  # Importamos la función de Storage


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
    
    # 1. Limitamos la previsualización a las primeras 50 filas para evitar bloqueos
    st.dataframe(display_fmt.head(50), use_container_width=True)

    # 2. Reemplazamos la descarga directa en memoria por la exportación a Cloud Storage
    st.divider()
    
    # Nota: Exportamos el dataframe original completo (clust_df), no el limitado a 50 filas
    if st.button("Guardar en Cloud Storage y Generar Link (.parquet)", use_container_width=True):
        with st.spinner("Procesando y subiendo archivo a Cloud Storage..."):
            try:
                url_descarga = exportar_parquet_firmado(
                    df_resultados=clust_df, 
                    project_id="media-team-marketing",
                    bucket_name="app-clusters-rfm"
                )
                
                st.success("¡Archivo guardado exitosamente!")
                st.markdown(f"[**⬇️ Descargar archivo Parquet (Válido por 1 hora)**]({url_descarga})")
                
            except Exception as e:
                st.error(f"Ocurrió un error al intentar guardar el archivo: {e}")
