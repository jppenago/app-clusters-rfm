"""
Componente del tab de tabla de datos.

Responsabilidad única: renderizar la tabla interactiva de clientes etiquetados
por cluster, con filtro de cluster y botón de descarga CSV.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from src.storage_client import exportar_parquet_firmado


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
    
    # Renderizamos la tabla usando el formato nativo para evitar el error de PyArrow
    # y usamos width="stretch" en lugar del obsoleto use_container_width
    st.dataframe(
        display_fmt.head(50), 
        width="stretch",
        column_config={
            "valor_total": st.column_config.NumberColumn(
                "valor_total",
                format="$ %d"
            )
        }
    )

    st.divider()
    
    # Actualizamos también el botón con width="stretch"
    if st.button("Guardar en Cloud Storage y Generar Link (.parquet)", width="stretch"):
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
