"""
Componente de estilos globales.

Responsabilidad única: inyectar el bloque <style> con la hoja de estilos CSS
de la aplicación. Debe llamarse una sola vez, al inicio del script principal.
"""

from __future__ import annotations

import streamlit as st


def render_styles() -> None:
    """Inyecta los estilos CSS globales de la aplicación."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

            html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

            /* ── Layout ── */
            .block-container { padding: 2rem 3rem 3rem 3rem !important; max-width: 1400px; }

            /* ── Hero ── */
            .rfm-hero { padding: 2rem 0 1.25rem 0; }
            .rfm-badge {
                display: inline-block;
                background: #EEF2FF; color: #4338CA;
                font-size: 0.7rem; font-weight: 700;
                letter-spacing: 0.1em; text-transform: uppercase;
                padding: 0.25rem 0.8rem; border-radius: 999px; margin-bottom: 0.9rem;
            }
            .rfm-title {
                font-size: 2.1rem; font-weight: 700; color: #0F172A;
                line-height: 1.2; margin: 0 0 0.45rem 0;
            }
            .rfm-sub { font-size: 0.97rem; color: #64748B; margin: 0; font-weight: 400; }

            /* ── Section labels ── */
            .section-label {
                font-size: 0.68rem; font-weight: 700; letter-spacing: 0.11em;
                text-transform: uppercase; color: #94A3B8; margin-bottom: 0.5rem;
            }

            /* ── Metric cards ── */
            [data-testid="stMetric"] {
                background: #F8FAFC; border: 1px solid #E2E8F0;
                border-radius: 14px; padding: 1.1rem 1.3rem !important;
            }
            [data-testid="stMetricLabel"] p {
                font-size: 0.72rem !important; font-weight: 700 !important;
                color: #64748B !important; text-transform: uppercase; letter-spacing: 0.07em;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.75rem !important; font-weight: 700 !important; color: #0F172A !important;
            }

            /* ── Sidebar ── */
            [data-testid="stSidebar"] {
                background: #F8FAFC !important; border-right: 1px solid #E2E8F0;
            }

            /* ── Tabs ── */
            button[data-baseweb="tab"] {
                font-size: 0.84rem !important; font-weight: 500 !important;
            }

            /* ── Cluster stat containers ── */
            [data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 14px !important; border: 1px solid #E2E8F0 !important;
            }

            /* ── Dividers ── */
            hr { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }

            /* ── Responsive ── */
            @media (max-width: 768px) {
                .block-container { padding: 1rem !important; }
                .rfm-title { font-size: 1.55rem; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
