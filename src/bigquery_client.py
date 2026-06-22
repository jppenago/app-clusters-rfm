from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _inject_windows_certs() -> None:
    """Combina el almacén de certificados de Windows con el bundle de certifi.

    En redes corporativas con inspección SSL (proxy con CA autofirmada), la CA
    corporativa ya está registrada en el almacén del SO pero no en el bundle de
    certifi que usan ``requests`` y ``google-auth``.  Esta función:

    1. Lee las CAs de los almacenes "CA" y "ROOT" del SO Windows.
    2. Las combina con el bundle de certifi en un fichero temporal.
    3. Establece ``REQUESTS_CA_BUNDLE`` y ``SSL_CERT_FILE`` apuntando a ese
       fichero, de modo que todas las peticiones HTTP del proceso confían en
       la CA corporativa sin deshabilitar la verificación SSL.

    Es un no-op en sistemas no-Windows o si ya se ejecutó en este proceso.
    """
    import os
    import sys

    if sys.platform != "win32":
        return
    if os.environ.get("_RFM_CERTS_INJECTED"):
        return

    import base64
    import ssl
    import tempfile

    import certifi

    pem_lines: list[str] = []
    for store_name in ("CA", "ROOT"):
        try:
            for cert_der, encoding, _ in ssl.enum_certificates(store_name):
                if encoding == "x509_asn" and isinstance(cert_der, bytes):
                    b64 = base64.b64encode(cert_der).decode("ascii")
                    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
                    pem_lines.append("-----BEGIN CERTIFICATE-----")
                    pem_lines.extend(lines)
                    pem_lines.append("-----END CERTIFICATE-----")
        except Exception:
            pass

    if not pem_lines:
        return

    with open(certifi.where(), encoding="utf-8") as fh:
        certifi_bundle = fh.read()

    combined = certifi_bundle + "\n" + "\n".join(pem_lines) + "\n"

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".pem", delete=False, encoding="utf-8"
    )
    tmp.write(combined)
    tmp.close()

    os.environ["REQUESTS_CA_BUNDLE"] = tmp.name
    os.environ["SSL_CERT_FILE"] = tmp.name
    os.environ["_RFM_CERTS_INJECTED"] = "1"


_BQ_PROJECT = "media-team-marketing"
_BQ_DATASET = "clusters_rfm"
_BQ_TABLE = "jzp_global_compras_rfm_v2_partitioned"

# ── Esquema de salida ─────────────────────────────────────────────────────────
# Variables que alimentan el clustering (NO tocar: las consume src/clustering.py)
RFM_COLUMNS: list[str] = ["recencia", "frecuencia", "valor_total"]

# Columnas categóricas de enriquecimiento expuestas como filtros en la app.
# Se eligen de baja/media cardinalidad para que el panel de filtros sea usable.
CATEGORICAL_COLUMNS: list[str] = [
    "segmento",
    "subsegmento",
    "genero",
    "producto",
]

# Columnas de enriquecimiento que se retornan para perfilar y mostrar en la
# tabla de datos, pero NO se exponen como filtros categóricos.
_EXTRA_ENRICHMENT_COLUMNS: list[str] = [
    # "nivel_renta",
    # "nivel_lealtad",
    # "principalidad",
    # "nivel_digital",
    # "perfil_transaccional",
    # "ocupacion",
    # "edad",
    # "valor_ingreso_estimado",
]

# Orden final de columnas que retorna ``fetch_audience_data``.
OUTPUT_COLUMNS: list[str] = ["llave_sistema"] + CATEGORICAL_COLUMNS + RFM_COLUMNS

# Mapeo columna_origen (BigQuery) -> alias de salida usado por la app.
_BQ_COLUMN_ALIASES: dict[str, str] = {
    "llave_sistema": "llave_sistema",
    "desc_segmento": "segmento",
    "desc_subsegmento": "subsegmento",
    "desc_genero": "genero",
    # "rango_edad": "rango_edad",
    # "nivel_renta": "nivel_renta",
    # "nivel_lealtad": "nivel_lealtad",
    # "cat_principalidad": "principalidad",
    # "nivel_dig_trx": "nivel_digital",
    # "perfil_trx": "perfil_transaccional",
    # "desc_ocupacion": "ocupacion",
    # "edad": "edad",
    # "valor_ingreso_estimado": "valor_ingreso_estimado",
    "recency_dias": "recencia",
    "frecuencia": "frecuencia",
    "valor_total": "valor_total",
    "producto": "producto",
}


def fetch_audience_data(llave_sistemas: list[str]) -> pd.DataFrame:
    """
    Extrae datos RFM enriquecidos de la tabla maestra para los IDs indicados.

    Parameters
    ----------
    llave_sistemas:
        Lista de identificadores de clientes (llave_sistema).

    Returns
    -------
    pd.DataFrame con las columnas definidas en ``OUTPUT_COLUMNS``:
        llave_sistema | <categóricas de enriquecimiento> |
        ocupacion | edad | valor_ingreso_estimado |
        recencia | frecuencia | valor_total
    """
    return _bigquery_fetch(llave_sistemas)


def fetch_full_population(limit: int | None = None) -> pd.DataFrame:
    """
    Extrae la población completa de la tabla maestra (todos los clientes).

    Parameters
    ----------
    limit:
        Número máximo de clientes a traer.  ``None`` trae toda la población
        (puede ser costoso/lento según el tamaño de la tabla).

    Returns
    -------
    pd.DataFrame con las mismas columnas que ``fetch_audience_data``.
    """
    return _bigquery_fetch_all(limit)


def get_categorical_options(df: pd.DataFrame) -> dict[str, list]:
    """
    Retorna los valores únicos de cada columna categórica presente en *df*.

    Returns
    -------
    dict ``{nombre_columna: [valor1, valor2, …]}`` en orden alfabético.
    Solo incluye columnas que existan en *df* y tengan al menos un valor no nulo.
    """
    result: dict[str, list] = {}
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            unique_vals = sorted(df[col].dropna().unique().tolist())
            if unique_vals:
                result[col] = unique_vals
    return result


def filter_by_categories(df: pd.DataFrame, selections: dict[str, list]) -> pd.DataFrame:
    """
    Filtra *df* según selecciones categóricas de forma segura ante nulos.

    Reglas por columna:
      * Si la selección está vacía o incluye **todos** los valores disponibles,
        no se filtra esa columna (se conservan incluso las filas con valor nulo).
      * En caso contrario, se conservan solo las filas cuyo valor esté en la
        selección (las filas con nulo en esa columna se excluyen, igual que
        cualquier otro valor no seleccionado).

    Esto evita que añadir múltiples filtros de enriquecimiento elimine clientes
    de forma silenciosa solo por tener atributos demográficos faltantes.
    """
    out = df
    for col, selected in selections.items():
        if col not in out.columns or not selected:
            continue
        available = set(out[col].dropna().unique().tolist())
        # Todos los valores disponibles seleccionados -> no se filtra (no-op).
        if available and set(selected) >= available:
            continue
        out = out[out[col].isin(selected)]
    return out


def _get_bq_client():
    """Crea un cliente de BigQuery autenticado con el Service Account."""
    import os  # noqa: PLC0415

    from google.cloud import bigquery  # noqa: PLC0415
    from google.oauth2 import service_account  # noqa: PLC0415

    # Inyectar CAs del SO de Windows para entornos con proxy de inspección SSL.
    _inject_windows_certs()

    sa_key_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "serviceaccount.json"
    )
    credentials = service_account.Credentials.from_service_account_file(
        sa_key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=_BQ_PROJECT, credentials=credentials)


def _build_select_clause() -> str:
    """Construye el SELECT con alias a partir del mapeo declarado."""
    return ",\n            ".join(
        f"{source} AS {alias}" if source != alias else source
        for source, alias in _BQ_COLUMN_ALIASES.items()
    )


def _ensure_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Garantiza orden y presencia de las columnas esperadas por la app."""
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[OUTPUT_COLUMNS]


def _bigquery_fetch(llave_sistemas: list[str]) -> pd.DataFrame:
    """
    Extrae datos desde BigQuery usando consulta parametrizada (sin riesgo de
    inyección SQL).  Requiere credenciales GCP configuradas.

    Nota: ``create_bqstorage_client=False`` deshabilita la BigQuery Storage API
    (gRPC) y fuerza la descarga por REST, evitando un cuelgue conocido en
    Python 3.9 con ciertos entornos de threading/gRPC.
    """
    from google.cloud import bigquery  # noqa: PLC0415

    safe_ids = [lid for lid in llave_sistemas if re.match(r"^[\w\-]+$", str(lid))]

    if not safe_ids:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    client = _get_bq_client()

    query = f"""
        SELECT
            {_build_select_clause()}
        FROM `{_BQ_PROJECT}.{_BQ_DATASET}.{_BQ_TABLE}`
        WHERE llave_sistema IN UNNEST(@llave_sistemas)
    """
    print(query)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("llave_sistemas", "STRING", safe_ids)
        ]
    )

    job = client.query(query, job_config=job_config)
    df = job.result(timeout=300).to_dataframe(create_bqstorage_client=False)
    return _ensure_output_columns(df)


def _bigquery_fetch_all(limit: int | None = None) -> pd.DataFrame:
    """
    Extrae TODA la población de la tabla (opcionalmente acotada con ``limit``).
    """
    client = _get_bq_client()

    query = f"""
        SELECT
            {_build_select_clause()}
        FROM `{_BQ_PROJECT}.{_BQ_DATASET}.{_BQ_TABLE}`
        WHERE llave_sistema IS NOT NULL
    """
    if limit is not None:
        query += f"\n        LIMIT {int(limit)}"

    print(query)

    job = client.query(query)
    df = job.result(timeout=300).to_dataframe(create_bqstorage_client=False)
    return _ensure_output_columns(df)
