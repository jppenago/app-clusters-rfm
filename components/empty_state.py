"""
Componente de estado vacío.

Responsabilidad única: renderizar el placeholder central que se muestra cuando
no hay datos cargados todavía.
"""

from __future__ import annotations

import streamlit as st


def render_empty_state() -> None:
    """Muestra el placeholder de bienvenida cuando no hay datos cargados."""
    st.markdown(
        """
        <div style='text-align:center;padding:3.5rem 1rem;'>
            <p style='font-size:2.8rem;margin:0 0 0.6rem 0;'>📂</p>
            <p style='font-size:1.05rem;font-weight:600;color:#1E293B;margin:0 0 0.35rem 0;'>
                Sin datos cargados
            </p>
            <p style='font-size:0.88rem;color:#64748B;margin:0;'>
                Sube un CSV con la columna <code>llave_sistema</code>, o elige
                <strong>"Usar toda la población"</strong> para iniciar el análisis.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
