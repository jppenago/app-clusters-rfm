"""
Módulo de cliente de Vertex AI para habilitar un chat inteligente interactivo
sobre los resultados del análisis RFM y clustering.
"""

from __future__ import annotations

import os

import pandas as pd
import vertexai
from vertexai.generative_models import Content, GenerativeModel, Part

_SA_KEY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "serviceaccount.json"
)

# Inicializamos Vertex AI usando el Service Account compartido
_VERTEX_INITIALIZED = False


def init_vertex() -> bool:
    """
    Inicializa la API de Vertex AI con las credenciales de Service Account.
    Retorna True si la inicialización es exitosa, False en caso contrario.
    """
    global _VERTEX_INITIALIZED
    if _VERTEX_INITIALIZED:
        return True

    if os.path.exists(_SA_KEY_PATH):
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _SA_KEY_PATH
            # Usamos el mismo Project ID definido en BigQuery
            vertexai.init(project="media-team-marketing", location="us-central1")
            _VERTEX_INITIALIZED = True
            return True
        except Exception as e:
            print(f"Error inicializando Vertex AI env: {e}")
            return False
    else:
        # En caso de que no exista el archivo de credenciales, intentamos inicialización por ADC
        try:
            vertexai.init(project="media-team-marketing", location="us-central1")
            _VERTEX_INITIALIZED = True
            return True
        except Exception as e:
            print(f"Error inicializando Vertex AI por ADC: {e}")
            return False


def get_chatbot_response(
    user_message: str,
    chat_history: list[dict[str, str]],
    summary_df: pd.DataFrame | None = None,
) -> str:
    """
    Usa el modelo Gemini 1.5 Flash en Vertex AI para responder preguntas en lenguaje natural
    sobre el comportamiento de la audiencia y los resultados de clustering.

    Parameters
    ----------
    user_message:
        El mensaje del usuario en el chat.
    chat_history:
        Historial de chat con formato [{"role": "user"|"assistant", "content": "..."}]
    summary_df:
        DataFrame consolidado con las estadísticas descriptivas por clúster.
    """
    if not init_vertex():
        return (
            "⚠️ No se pudo inicializar Vertex AI. Por favor, asegúrate de que el archivo "
            "`serviceaccount.json` sea válido y esté presente en la raíz del proyecto."
        )

    # Convertir el resumen de clústeres a una representación de texto clara
    if summary_df is not None and not summary_df.empty:
        # Formatear selectivamente columnas explicativas
        cols_to_show = [
            "cluster",
            "n_clientes",
            "porcentaje",
            "recencia_mean",
            "frecuencia_mean",
            "valor_total_mean",
            "reglas_automaticas",
        ]
        cols_present = [col for col in cols_to_show if col in summary_df.columns]
        summary_clean = summary_df[cols_present].copy()
        summary_clean = summary_clean.rename(
            columns={
                "recencia_mean": "recencia_promedio_dias",
                "frecuencia_mean": "frecuencia_promedio_compras",
                "valor_total_mean": "monto_promedio_cop",
                "n_clientes": "cantidad_clientes",
                "reglas_automaticas": "frontera_decision",
            }
        )
        summary_context = summary_clean.to_markdown(index=False)
    else:
        summary_context = "No hay datos de análisis calculados todavía o el usuario aún no ha subido el archivo."

    system_instruction = f"""
    Eres 'Gestor RFM Inteligente Bancolombia', un sofisticado asesor virtual para análisis de clientes y mercadeo inteligente en Bancolombia.
    Tu objetivo es ayudar a analistas de negocio, gerentes y equipos de mercadeo a interpretar la segmentación RFM realizada sobre su audiencia.
    
    El análisis utiliza tres variables fundamentales del comportamiento de compra:
    - Recencia: Días desde la última compra (menor es mejor ya que el cliente compró hace poco).
    - Frecuencia: Número total de compras en el período (mayor es mejor).
    - Monto/Valor Total: Dinero total facturado por el cliente en COP (mayor es mejor).
    
    Aquí tienes el resumen matemático real de los clústeres calculados para la audiencia analizada en esta sesión:
    
    ```markdown
    {summary_context}
    ```
    
    Instrucciones clave para tus respuestas:
    1. Mantén un tono formal, profesional, empático y orientado a negocios/marketing.
    2. Utiliza siempre los datos del resumen anterior para respaldar tus respuestas empíricamente. Sé específico con cifras si te preguntan detalles.
    3. Refiérete a los clústeres por su número (ej. "Cluster 1", "Cluster 2") y descríbelos a partir de sus métricas RFM (recencia, frecuencia y monto promedio) y su frontera de decisión. No inventes nombres ni arquetipos subjetivos.
    4. Propón estrategias de marketing accionables basadas exactamente en la situación de cada grupo (venta cruzada, fidelización, reactivación, etc.).
    5. Utiliza formato Markdown refinado con negritas, listas o tablas pequeñas si facilita la comprensión de la información.
    6. Responde siempre en español. No inventes datos que no estén descritos. Si te preguntan sobre datos individuales de clientes que no están incluidos, aclara con tacto que el modelo de IA responde sobre las estadísticas consolidadas de los segmentos.
    """

    try:
        # Cargamos el modelo Gemini 1.5 Flash adaptado para conversación veloz
        model = GenerativeModel(
            model_name="gemini-1.5-flash", system_instruction=[system_instruction]
        )

        # Mapeo del historial al formato esperado por el SDK de Vertex (user / model)
        contents: list[Content] = []
        for msg in chat_history:
            # Vertex AI usa "user" y "model"
            role = "user" if msg["role"] == "user" else "model"
            contents.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

        # Añadimos el último mensaje del usuario
        contents.append(Content(role="user", parts=[Part.from_text(user_message)]))

        response = model.generate_content(contents=contents)
        return response.text
    except Exception as e:
        return (
            f"❌ **Error al consultar Vertex AI (Gemini):** `{e}`\n\n"
            "Asegúrate de que la API de Vertex AI esté habilitada en tu proyecto de Google Cloud "
            "y que la cuenta de servicio tenga los roles correspondientes (como Administrador de Vertex AI o Usuario de Vertex AI)."
        )
