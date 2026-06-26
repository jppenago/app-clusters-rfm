"""
Componente del tab de Asistente de IA (Vertex AI).

Responsabilidad única: Inicializar una sesión de chat con Gemini, inyectar
los resultados del clustering desde la memoria RAM (st.session_state)
como contexto, y gestionar la interfaz del chat.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession


def init_ai_agent(summary: pd.DataFrame) -> tuple[ChatSession, str]:
    """
    Inicializa la sesión de chat con Gemini y le inyecta el contexto de los clusters.
    Toma el DataFrame directamente de la memoria RAM y lo convierte a texto.
    """
    # Inicializamos Vertex AI usando las credenciales del entorno
    vertexai.init()

    # Usamos Gemini 2.5 Flash, que es el último modelo estable y veloz en Vertex AI
    # A partir de la versión 2.5, se recomienda usar el nombre base sin sufijo para la versión estable
    model = GenerativeModel("gemini-2.5-flash")
    chat = model.start_chat()

    # ¡AQUÍ ESTÁ LA MAGIA EN MEMORIA!
    # Tomamos el DataFrame que viene de la RAM y lo convertimos a formato Markdown
    # para que el LLM lo pueda leer como si fuera una tabla de texto.
    contexto_clusters = summary.to_markdown(index=False)

    system_prompt = f"""
    Eres un experto en Marketing Estratégico, Ciencia de Datos y Negocios. Acabamos de 
    ejecutar un modelo de clustering K-Means (Análisis RFM - Recencia, Frecuencia, Monto) 
    sobre nuestra base de clientes, la cual contiene información detallada sobre su 
    comportamiento de compra en los ultimos 6 meses del año actual.
    
    Aquí tienes el resumen estadístico en memoria y las reglas lógicas de cada cluster:
    {contexto_clusters}
    
    Tu tarea es:
    1. Analizar estos datos y darle un nombre comercial e intuitivo a cada cluster (ej. "Campeones", "En Riesgo", "Leales").
    2. Explicar en palabras sencillas (sin jerga matemática compleja) qué tipo de cliente es cada uno.
    3. Sugerir campañas de marketing accionables para maximizar el valor de cada grupo.
    
    REGLA DE FORMATO OBLIGATORIA: 
    Tu respuesta debe estar formateada de manera impecable utilizando Markdown. 
    Usa títulos (###), texto en negrita (**texto**), listas con viñetas (-) y emojis para organizar visualmente la información. NO devuelvas un solo bloque de texto plano. Queremos un reporte muy profesional, estructurado y fácil de leer.
    
    Por favor, preséntate brevemente de forma profesional pero amigable, y entrega tu análisis inicial 
    de los clusters. Luego, quédate atento para responder las preguntas del usuario sobre estos segmentos.
    """

    # Enviamos el contexto inicial de forma silenciosa para obtener la primera respuesta
    response = chat.send_message(system_prompt)
    return chat, response.text


def render_ai_tab(summary: pd.DataFrame) -> None:
    """Renderiza la interfaz del Asistente de IA en Streamlit."""

    st.markdown(
        "<p style='font-size:1.1rem;font-weight:600;color:#0F172A;margin-bottom:1rem;display:flex;align-items:center;'>"
        "🤖 Asistente Estratégico de IA (Gemini)</p>",
        unsafe_allow_html=True,
    )
    st.info(
        "Pregúntale al agente sobre los resultados del clustering, ideas de campañas o cómo interpretar los datos. Todo ocurre en memoria."
    )

    # Guardamos la sesión de chat en la memoria de Streamlit (session_state)
    # para que la IA recuerde la conversación mientras el usuario navega
    if "ai_chat_session" not in st.session_state:
        with st.spinner(
            "Despertando al Agente de IA y analizando clusters en memoria..."
        ):
            try:
                chat_session, initial_analysis = init_ai_agent(summary)
                st.session_state["ai_chat_session"] = chat_session
                st.session_state["ai_chat_history"] = [
                    {"role": "assistant", "content": initial_analysis}
                ]
            except Exception as e:
                st.error(f"Error al conectar con Vertex AI: {e}")
                return

    # Mostrar historial de mensajes iterando sobre la RAM
    for msg in st.session_state["ai_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Caja de texto para el usuario
    if prompt := st.chat_input(
        "Ej: ¿Qué campaña me recomiendas para el Cluster 2 con bajo presupuesto?"
    ):

        # Guardar y mostrar el mensaje del usuario
        st.session_state["ai_chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Obtener respuesta del agente
        chat = st.session_state["ai_chat_session"]
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    response = chat.send_message(prompt)
                    st.markdown(response.text)
                    # Guardar respuesta en historial
                    st.session_state["ai_chat_history"].append(
                        {"role": "assistant", "content": response.text}
                    )
                except Exception as e:
                    st.error(f"Hubo un problema al procesar tu solicitud: {e}")
