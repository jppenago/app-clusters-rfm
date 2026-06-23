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

            /* ── Tab SVG icons ── */
            [data-baseweb="tab-list"] button[data-baseweb="tab"]::before {
                content: '';
                display: inline-block;
                width: 14px; height: 14px;
                background-repeat: no-repeat;
                background-position: center;
                background-size: contain;
                margin-right: 5px;
                vertical-align: -2px;
            }
            [data-baseweb="tab-list"] button[data-baseweb="tab"]:nth-of-type(1)::before {
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234338CA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='23 6 13.5 15.5 8.5 10.5 1 18'/%3E%3Cpolyline points='17 6 23 6 23 12'/%3E%3C/svg%3E");
            }
            [data-baseweb="tab-list"] button[data-baseweb="tab"]:nth-of-type(2)::before {
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234338CA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='20' x2='18' y2='10'/%3E%3Cline x1='12' y1='20' x2='12' y2='4'/%3E%3Cline x1='6' y1='20' x2='6' y2='14'/%3E%3C/svg%3E");
            }
            [data-baseweb="tab-list"] button[data-baseweb="tab"]:nth-of-type(3)::before {
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234338CA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2'/%3E%3Cline x1='3' y1='9' x2='21' y2='9'/%3E%3Cline x1='3' y1='15' x2='21' y2='15'/%3E%3Cline x1='9' y1='9' x2='9' y2='21'/%3E%3Cline x1='15' y1='9' x2='15' y2='21'/%3E%3C/svg%3E");
            }

            /* ── Section headings with SVG icons ── */
            .section-heading {
                font-size: 1rem; font-weight: 600; color: #0F172A;
                margin: 0.5rem 0 0.5rem 0; display: flex; align-items: center;
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
