from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _inject_system_certs() -> None:
    """Combina el almacén de certificados del SO con el bundle de certifi.

    En redes corporativas con inspección SSL (proxy con CA autofirmada), la CA
    corporativa está registrada en el almacén del SO pero no en el bundle de
    certifi que usan ``requests`` y ``google-auth``.  Esta función:

    - **Windows**: lee los almacenes "CA" y "ROOT" via ``ssl.enum_certificates``.
    - **macOS**: lee los keychains del sistema via el comando ``security``.
    - **Linux/otros**: no-op (los certificados del sistema suelen estar en
      rutas estándar que el SO ya expone; si se necesita, ajustar manualmente).

    En todos los casos combina los certificados encontrados con el bundle de
    certifi en un fichero temporal y establece ``REQUESTS_CA_BUNDLE`` y
    ``SSL_CERT_FILE`` apuntando a él, de modo que todas las peticiones HTTP del
    proceso confían en la CA corporativa sin deshabilitar la verificación SSL.

    Es un no-op si ya se ejecutó en este proceso (``_RFM_CERTS_INJECTED``).
    """
    import os
    import sys

    if os.environ.get("_RFM_CERTS_INJECTED"):
        return

    import tempfile

    import certifi

    extra_pem: str = ""

    if sys.platform == "win32":
        import base64
        import ssl

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
        extra_pem = "\n".join(pem_lines)

    elif sys.platform == "darwin":
        import subprocess

        # SystemRootCertificates = root CAs embebidas en macOS.
        # System.keychain = certificados adicionales instalados por el SO / MDM corporativo.
        keychains = [
            "/System/Library/Keychains/SystemRootCertificates.keychain",
            "/Library/Keychains/System.keychain",
        ]
        parts: list[str] = []
        for keychain in keychains:
            try:
                proc = subprocess.run(
                    ["security", "find-certificate", "-a", "-p", keychain],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    parts.append(proc.stdout.strip())
            except Exception:
                pass
        extra_pem = "\n".join(parts)

    if not extra_pem.strip():
        return

    with open(certifi.where(), encoding="utf-8") as fh:
        certifi_bundle = fh.read()

    combined = certifi_bundle + "\n" + extra_pem + "\n"

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

# Orden final de columnas que retorna ``fetch_audience_data``.
OUTPUT_COLUMNS: list[str] = ["llave_sistema"] + CATEGORICAL_COLUMNS + RFM_COLUMNS

# Mapeo columna_origen (BigQuery) -> alias de salida usado por la app.
_BQ_COLUMN_ALIASES: dict[str, str] = {
    "llave_sistema": "llave_sistema",
    "desc_segmento": "segmento",
    "desc_subsegmento": "subsegmento",
    "desc_genero": "genero",
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


'''
def _get_bq_client():
    """Crea un cliente de BigQuery autenticado con el Service Account."""
    import os  # noqa: PLC0415

    from google.cloud import bigquery  # noqa: PLC0415
    from google.oauth2 import service_account  # noqa: PLC0415

    # Inyectar CAs del SO (Windows y macOS) para entornos con proxy de inspección SSL.
    _inject_system_certs()

    sa_key_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "serviceaccount.json"
    )
    credentials = service_account.Credentials.from_service_account_file(
        sa_key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=_BQ_PROJECT, credentials=credentials)
'''


# ... existing code ...
def _get_bq_client():
    import os
    import google.auth
    from google.cloud import bigquery
    from google.oauth2 import service_account

    print("\n[DEBUG] Iniciando _get_bq_client()...")

    # 1. Detectamos de forma infalible si estamos en Cloud Run
    # Google Cloud Run inyecta automáticamente la variable de entorno 'K_SERVICE'
    is_cloud_run = "K_SERVICE" in os.environ
    print(f"[DEBUG] ¿Está en Cloud Run (K_SERVICE existe)? : {is_cloud_run}")

    if is_cloud_run:
        print(
            "[DEBUG] Entorno de PRODUCCIÓN detectado. Obteniendo credenciales (ADC)..."
        )
        # En PRODUCCIÓN (Cloud Run): usamos ADC de forma segura
        credentials, project_id = google.auth.default()
        print(f"[DEBUG] ADC obtenidas exitosamente. Project ID: {project_id}")
        client = bigquery.Client(credentials=credentials, project=project_id)
        print("[DEBUG] Cliente BigQuery inicializado (Producción).")
    else:
        # En LOCAL (tu máquina): Obligamos a usar el archivo JSON
        local_key_path = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS", "serviceaccount.json"
        )
        print(
            f"[DEBUG] Entorno LOCAL detectado. Buscando credenciales en: {os.path.abspath(local_key_path)}"
        )

        # Si no encuentra el archivo, lanzamos un error claro para EVITAR el loop infinito
        if not os.path.exists(local_key_path):
            print("[DEBUG] ❌ ERROR: Archivo JSON no encontrado. Deteniendo ejecución.")
            raise FileNotFoundError(
                f"¡ALERTA LOCAL! No se encontró el archivo de credenciales en la ruta: '{os.path.abspath(local_key_path)}'. "
                "El proceso se detuvo para evitar un loop infinito. Por favor verifica que el archivo exista "
                "en esa ubicación exacta."
            )

        print("[DEBUG] ✅ Archivo JSON encontrado. Cargando credenciales...")
        credentials = service_account.Credentials.from_service_account_file(
            local_key_path
        )
        print(
            f"[DEBUG] Credenciales cargadas. Project ID: {credentials.project_id}. Inicializando cliente..."
        )
        client = bigquery.Client(
            credentials=credentials, project=credentials.project_id
        )
        print("[DEBUG] Cliente BigQuery inicializado (Local).")

    return client


# ... existing code ...


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
        WHERE llave_sistema IN UNNEST(@llave_sistemas) AND valor_total >= 10000
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
        WHERE llave_sistema IS NOT NULL AND valor_total >= 10000
    """
    if limit is not None:
        query += f"\n        LIMIT {int(limit)}"

    print(query)

    job = client.query(query)
    df = job.result(timeout=300).to_dataframe(create_bqstorage_client=False)
    return _ensure_output_columns(df)
