"""
Componente del tab de chat con el Asistente RFM Inteligente.

Responsabilidad única: renderizar la interfaz conversacional (tipo ChatGPT)
que permite al usuario hacer preguntas en lenguaje natural sobre los resultados
del clustering. Usa Gemini 1.5 Flash a través de Vertex AI como backend.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.vertex_client import get_chatbot_response

# Avatares para los mensajes del chat
_AVATAR_USER = "🧑‍💼"
_AVATAR_BOT = "🤖"

_SUGGESTIONS = [
    "¿Cuál es el cluster con mayor valor potencial para campañas de fidelización?",
    "¿Qué estrategia de reactivación recomendarías para el cluster con mayor recencia?",
    "¿Qué cluster tiene el perfil de cliente más activo y qué acciones tomar con él?",
    "Resume los hallazgos principales del análisis en un párrafo ejecutivo.",
]


def render_chat_tab(summary: pd.DataFrame) -> None:
    """
    Renderiza el tab del asistente conversacional RFM.

    Parameters
    ----------
    summary:
        DataFrame de resumen por cluster generado por ``get_cluster_summary``.
        Se inyecta como contexto en el system prompt del modelo.
    """
    st.markdown("##### 💬 Asistente RFM Inteligente")
    st.caption(
        "Haz preguntas en lenguaje natural sobre los segmentos identificados. "
        "El asistente tiene acceso a las estadísticas consolidadas de cada clúster."
    )

    # ── Sugerencias rápidas ───────────────────────────────────────────────────
    if not st.session_state["messages"]:
        st.markdown(
            "<p style='font-size:0.8rem; color:#64748B; margin-bottom:0.4rem;'>"
            "💡 <b>Preguntas sugeridas</b></p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, suggestion in enumerate(_SUGGESTIONS):
            with cols[i % 2]:
                if st.button(
                    suggestion,
                    key=f"suggestion_{i}",
                    use_container_width=True,
                ):
                    st.session_state["messages"].append(
                        {"role": "user", "content": suggestion}
                    )
                    with st.spinner("Consultando al asistente…"):
                        response = get_chatbot_response(
                            suggestion,
                            st.session_state["messages"][:-1],
                            summary_df=summary,
                        )
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": response}
                    )
                    st.rerun()

        st.markdown("---")

    # ── Historial de mensajes ─────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["messages"]:
            avatar = _AVATAR_USER if msg["role"] == "user" else _AVATAR_BOT
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # ── Botón para limpiar historial ──────────────────────────────────────────
    if st.session_state["messages"]:
        if st.button(
            "🗑️ Limpiar conversación",
            key="clear_chat",
            type="secondary",
        ):
            st.session_state["messages"] = []
            st.rerun()

    # ── Input del usuario ─────────────────────────────────────────────────────
    user_input = st.chat_input(
        "Pregunta sobre los clústeres, estrategias de marketing, interpretación de métricas…"
    )

    if user_input:
        # Mostrar mensaje del usuario inmediatamente
        with chat_container:
            with st.chat_message("user", avatar=_AVATAR_USER):
                st.markdown(user_input)

        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Obtener y mostrar respuesta del asistente
        with chat_container:
            with st.chat_message("assistant", avatar=_AVATAR_BOT):
                with st.spinner(""):
                    response = get_chatbot_response(
                        user_input,
                        st.session_state["messages"][:-1],
                        summary_df=summary,
                    )
                st.markdown(response)

        st.session_state["messages"].append({"role": "assistant", "content": response})
        st.rerun()
