"""
Componente de la barra lateral (Sidebar).

Responsabilidad única: Renderizar los controles de configuración del modelo K-Means,
los filtros de la audiencia y capturar la señal de ejecución mediante un formulario.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.bigquery_client import get_categorical_options


@dataclass
class SidebarConfig:
    n_clusters: int
    winsorize: bool
    winsor_pct: float


def render_sidebar(raw_df: pd.DataFrame | None = None) -> tuple[SidebarConfig, bool]:
    """
    Renderiza la barra lateral con los parámetros del modelo K-Means y los filtros categóricos.
    Agrupa todo en un formulario para evitar ejecuciones en cada cambio de input.

    Parameters
    ----------
    raw_df : pd.DataFrame | None
        DataFrame original para extraer las opciones de filtrado.

    Returns
    -------
    tuple[SidebarConfig, bool]
        Configuración del modelo y el estado del botón de ejecución (True si fue presionado).
    """
    with st.sidebar:
        # --- INYECCIÓN DE CSS PARA CORREGIR TEXTOS BLANCOS ---
        # Forzamos a que los títulos (h2, h3), párrafos (p) y etiquetas de sliders/botones (label)
        # dentro del sidebar tengan un color oscuro (#0F172A) para garantizar su lectura.
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label {
                color: #0F172A !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # -----------------------------------------------------

        st.markdown("## ⚙️ Configuración del Modelo")
        st.info(
            "Ajusta los parámetros y presiona 'Ejecutar Modelo' para actualizar los resultados."
        )

        # Agrupamos los inputs en un formulario para evitar recargas automáticas (reruns)
        with st.form("modelo_config_form"):

            n_clusters = st.slider(
                "Número de Clusters (K)",
                min_value=2,
                max_value=10,
                value=4,
                help="Cantidad de segmentos en los que se agrupará la audiencia.",
            )

            st.markdown("### 🛠️ Preprocesamiento")
            winsorize = st.toggle(
                "Aplicar Winsorizing",
                value=True,
                help="Limita los valores extremos (outliers) a un percentil específico para evitar que distorsionen los centroides.",
            )

            winsor_pct = 99.0
            if winsorize:
                winsor_pct = st.slider(
                    "Percentil de Corte",
                    min_value=90.0,
                    max_value=99.9,
                    value=99.0,
                    step=0.1,
                    help="Percentil superior para el recorte de outliers.",
                )

            # Si hay datos cargados en memoria, mostramos los filtros categóricos dinámicos
            if raw_df is not None and not raw_df.empty:
                st.markdown("### 🎯 Filtros de Audiencia")
                categorical_opts = get_categorical_options(raw_df)

                for col, options in categorical_opts.items():
                    st.multiselect(
                        label=f"Filtrar por {col.replace('_', ' ').title()}",
                        options=options,
                        default=options,
                        key=f"filter_{col}",  # Se guarda directamente en st.session_state al hacer submit
                        help=f"Selecciona las categorías permitidas para {col}.",
                    )

            st.divider()

            # Botón de ejecución dentro del formulario
            run_model = st.form_submit_button(
                "🚀 Ejecutar Modelo", type="primary", use_container_width=True
            )

    return SidebarConfig(n_clusters, winsorize, winsor_pct), run_model
