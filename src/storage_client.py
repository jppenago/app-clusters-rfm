import pandas as pd
from google.cloud import storage
import google.auth
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import pytz
import requests

def exportar_parquet_firmado(df_resultados, project_id, bucket_name="app-clusters-rfm"):
    zona_colombia = pytz.timezone('America/Bogota')
    ahora = datetime.now(zona_colombia)
    nombre_archivo = f"app_clustersrfm_{ahora.strftime('%Y%m%d_%H%M')}.parquet"
    
    # 1. Obtiene las credenciales y las refresca para asegurar que el token esté activo
    credentials, _ = google.auth.default()
    if not credentials.valid:
        credentials.refresh(Request())
        
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(nombre_archivo)
    
    # 2. Convertir y subir (Esto ya sabemos que funciona perfecto)
    buffer_parquet = df_resultados.to_parquet(index=False)
    blob.upload_from_string(buffer_parquet, content_type='application/octet-stream')
    
    # 3. Preparar los parámetros básicos para la firma
    sign_kwargs = {
        "version": "v4",
        "expiration": timedelta(hours=1),
        "method": "GET"
    }
    
    # 4. Lógica de firma híbrida (Cloud Run vs Local)
    # Si detecta que no hay llave privada local (es decir, estamos en Cloud Run)
    if not (hasattr(credentials, 'signer') and credentials.signer is not None):
        
        # Rescata el email de la cuenta de servicio de Cloud Run
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
        sa_email = requests.get(metadata_url, headers={"Metadata-Flavor": "Google"}, timeout=2).text
        
        # Inyecta el email y el token activo para que IAM autorice la firma
        sign_kwargs["service_account_email"] = sa_email
        sign_kwargs["access_token"] = credentials.token

    # 5. Genera la URL con los parámetros correspondientes
    url_temporal = blob.generate_signed_url(**sign_kwargs)
    
    return url_temporal
