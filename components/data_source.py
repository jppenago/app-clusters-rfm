"""
Componente de selección de fuente de datos.

Responsabilidad única: renderizar el bloque de carga de datos (CSV o población
completa) y retornar la configuración de la fuente en ``DataSourceConfig``.

El componente nunca ejecuta la carga real ni toca el session_state; solo
expone los controles y construye el callable que el script principal invocará.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from src.bigquery_client import fetch_audience_data, fetch_full_population


@dataclass
class DataSourceConfig:
    """
    Configuración de la fuente de datos seleccionada por el usuario.

    Attributes
    ----------
    source_sig:
        Cadena que identifica de forma única la fuente + parámetros actuales.
        ``None`` si el usuario no ha seleccionado ni confirmado ninguna fuente.
    loader:
        Callable sin argumentos que, al invocarse, retorna el DataFrame crudo
        de BigQuery (o datos simulados). ``None`` si no hay fuente activa.
    n_requested:
        Número de clientes solicitados en el CSV. ``None`` si la fuente es la
        población completa.
    """

    source_sig: str | None
    loader: Callable[[], pd.DataFrame] | None
    n_requested: int | None


def render_data_source(n_clusters: int) -> DataSourceConfig:
    """
    Renderiza el selector de fuente de datos y retorna la configuración activa.

    Parameters
    ----------
    n_clusters:
        Valor de K seleccionado en el sidebar. Se usa para validar que la
        fuente tenga suficientes clientes antes de continuar.

    Returns
    -------
    DataSourceConfig
        Firma de la fuente, callable de carga y número de clientes solicitados.
    """
    st.markdown("<p class='section-label'>Fuente de datos</p>", unsafe_allow_html=True)
    data_source = st.radio(
        "Fuente de datos",
        options=["Cargar audiencia (CSV)", "Usar toda la población"],
        horizontal=True,
        label_visibility="collapsed",
        help="Analiza una audiencia específica (CSV) o toda la población de la tabla.",
    )

    _source_sig: str | None = None
    _loader: Callable[[], pd.DataFrame] | None = None
    _n_requested: int | None = None

    if data_source == "Cargar audiencia (CSV)":
        _source_sig, _loader, _n_requested = _render_csv_uploader(n_clusters)
    else:
        _source_sig, _loader = _render_full_population(n_clusters)

    return DataSourceConfig(
        source_sig=_source_sig,
        loader=_loader,
        n_requested=_n_requested,
    )


# ── Sub-renderizadores privados ───────────────────────────────────────────────


def _render_csv_uploader(
    n_clusters: int,
) -> tuple[str | None, Callable[[], pd.DataFrame] | None, int | None]:
    """Renderiza el bloque de carga de CSV y retorna (sig, loader, n_requested)."""
    upload_col, format_col = st.columns([2, 1], gap="large")

    with upload_col:
        st.markdown(
            "<p class='section-label'>Cargar Audiencia</p>", unsafe_allow_html=True
        )
        uploaded_file = st.file_uploader(
            "Archivo CSV con los identificadores de tu audiencia",
            type=["csv"],
            label_visibility="collapsed",
            help="El archivo debe contener la columna `llave_sistema`.",
        )

    if uploaded_file is None:
        return None, None, None

    try:
        audience_df = pd.read_csv(uploaded_file, dtype=str)
    except Exception as exc:
        st.error(f"No se pudo leer el archivo: {exc}")
        st.stop()

    if "llave_sistema" not in audience_df.columns:
        st.error(
            "El archivo debe contener la columna **`llave_sistema`**. "
            f"Columnas encontradas: `{list(audience_df.columns)}`."
        )
        st.stop()

    llave_sistemas: list[str] = (
        audience_df["llave_sistema"].dropna().astype(str).unique().tolist()
    )
    n_requested = len(llave_sistemas)

    # st.success(f"✅ Archivo válido — **{n_requested:,} clientes** únicos encontrados.")

    if n_requested < n_clusters:
        st.warning(
            f"⚠️ El número de clientes ({n_requested:,}) es menor que K={n_clusters}. "
            "Reduce el número de clusters en la barra lateral."
        )
        st.stop()

    source_sig = f"CSV:{uploaded_file.name}:{n_requested}"
    loader: Callable[[], pd.DataFrame] = lambda ids=llave_sistemas: fetch_audience_data(
        ids
    )
    return source_sig, loader, n_requested


def _render_full_population(
    n_clusters: int,
) -> tuple[str | None, Callable[[], pd.DataFrame] | None]:
    """Renderiza el bloque de carga de población completa y retorna (sig, loader)."""
    st.markdown(
        "<p style='font-size:0.88rem;color:#64748B;'>Se analizará la población completa "
        "de la tabla. Puedes limitar el tamaño a una muestra para pruebas rápidas.</p>",
        unsafe_allow_html=True,
    )
    lim_col, btn_col = st.columns([2, 1], gap="large")

    with lim_col:
        _use_limit = st.checkbox(
            "Limitar a una muestra de clientes",
            value=True,
            help=(
                "Recomendado para pruebas. Desactívalo para traer TODA la población "
                "(puede ser lento y consumir mucha memoria según el tamaño de la tabla)."
            ),
        )
        _limit_val: int | None = None
        if _use_limit:
            _limit_val = int(
                st.number_input(
                    "Máximo de clientes a traer",
                    min_value=int(n_clusters),
                    max_value=2_000_000,
                    value=50_000,
                    step=10_000,
                )
            )

    with btn_col:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        _load_clicked = st.button(
            "📥 Cargar población", type="primary", use_container_width=True
        )

    _target_sig = f"FULL:{'all' if _limit_val is None else _limit_val}"

    # Se activa si el usuario hace clic, o si esa misma configuración ya está cargada.
    if _load_clicked or st.session_state.get("loaded_file_sig") == _target_sig:
        loader: Callable[[], pd.DataFrame] = (
            lambda lim=_limit_val: fetch_full_population(lim)
        )
        return _target_sig, loader

    return None, None
