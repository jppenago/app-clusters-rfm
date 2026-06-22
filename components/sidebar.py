"""
Componente de barra lateral (sidebar).

Responsabilidad única: renderizar todos los controles del panel lateral y
retornar sus valores encapsulados en ``SidebarConfig``.

El componente no ejecuta lógica de negocio; solo expone los controles al
usuario y devuelve una configuración tipada que el script principal consume.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.bigquery_client import get_categorical_options


@dataclass
class SidebarConfig:
    """Valores de configuración seleccionados en el panel lateral."""

    n_clusters: int
    winsorize: bool | None
    winsor_pct: float | None


def render_sidebar(raw_rfm_df: pd.DataFrame | None = None) -> SidebarConfig:
    """
    Renderiza el panel lateral completo y retorna la configuración seleccionada.

    Parameters
    ----------
    raw_rfm_df:
        DataFrame sin filtrar cargado desde BigQuery. Se usa para generar los
        filtros categóricos dinámicos. Si es ``None``, ese bloque se omite.

    Returns
    -------
    SidebarConfig
        Valores actuales de K, winsorizing y percentil de corte.
    """
    with st.sidebar:
        # ── Número de clusters ────────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;color:#64748B;"
            "text-transform:uppercase;letter-spacing:0.08em;margin-top:1.1rem;margin-bottom:0.3rem;'>"
            "Número de Clusters (K)</p>",
            unsafe_allow_html=True,
        )
        n_clusters: int = st.slider(
            "K",
            min_value=2,
            max_value=10,
            value=4,
            step=1,
            label_visibility="collapsed",
            help=(
                "Define en cuántos grupos se dividirá la audiencia. "
                "Un valor de K más alto produce segmentos más específicos."
            ),
        )

        # ── Tratamiento de outliers (winsorizing) ─────────────────────────────
        # st.markdown(
        #     "<p style='font-size:0.72rem;font-weight:700;color:#64748B;"
        #     "text-transform:uppercase;letter-spacing:0.08em;margin-top:1.1rem;margin-bottom:0.3rem;'>"
        #     "Tratamiento de Outliers</p>",
        #     unsafe_allow_html=True,
        # )
        # winsorize: bool = st.toggle(
        #     "Recortar valores extremos (winsorizing)",
        #     value=False,
        #     help=(
        #         "Capa los valores extremos de recencia, frecuencia y monto a un "
        #         "percentil, SIN eliminar clientes. Reduce la influencia de los "
        #         "outliers sobre los centroides y suele mejorar la separación de los "
        #         "clusters."
        #     ),
        # )
        # winsor_pct: float = 99.0
        # if winsorize:
        #     winsor_pct = st.slider(
        #         "Percentil de corte",
        #         min_value=90.0,
        #         max_value=99.9,
        #         value=99.0,
        #         step=0.1,
        #         help=(
        #             "Percentil superior de recorte (y su simétrico inferior). "
        #             "Ej. 99.0 recorta por encima del p99 y por debajo del p1. "
        #             "Un valor más bajo recorta más agresivamente."
        #         ),
        #     )

        # ── Filtros de columnas categóricas ───────────────────────────────────
        if raw_rfm_df is not None:
            _cat_opts = get_categorical_options(raw_rfm_df)
            if _cat_opts:
                st.divider()
                st.markdown(
                    "<p style='font-size:0.72rem;font-weight:700;color:#64748B;"
                    "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;'>"
                    "Filtrar Audiencia</p>",
                    unsafe_allow_html=True,
                )
                for _col, _values in _cat_opts.items():
                    _label = _col.replace("_", " ").title()
                    st.multiselect(
                        _label,
                        options=_values,
                        default=_values,
                        key=f"filter_{_col}",
                        help=f"Selecciona los valores de **{_label}** que deseas incluir en el análisis.",
                    )

    return SidebarConfig(
        n_clusters=n_clusters,
        winsorize=None,
        winsor_pct=None,
    )
