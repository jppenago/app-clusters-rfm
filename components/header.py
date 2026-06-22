"""
Componente de encabezado (hero).

Responsabilidad única: renderizar el bloque hero con el título de la aplicación
y, opcionalmente, el banner informativo de modo desarrollo.
"""

from __future__ import annotations

import streamlit as st


def render_header() -> None:
    st.markdown(
        """
        <div class="rfm-hero">
            <h1 class="">Segmentación RFM</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
