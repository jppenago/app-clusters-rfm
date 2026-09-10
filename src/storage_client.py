import pandas as pd
from google.cloud import storage
import google.auth
from datetime import datetime, timedelta
import pytz
import requests

def exportar_parquet_firmado(df_resultados, project_id, bucket_name="app-clusters-rfm"):
    zona_colombia = pytz.timezone('America/Bogota')
    ahora = datetime.now(zona_colombia)
    nombre_archivo = f"app_clustersrfm_{ahora.strftime('%Y%m%d_%H%M')}.parquet"
    
    # 1. Obtiene las credenciales del entorno (JSON local o Default en Cloud Run)
    credentials, _ = google.auth.default()
    client = storage.Client(project=project_id, credentials=credentials)
    
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(nombre_archivo)
    
    # 2. Convertir y subir
    buffer_parquet = df_resultados.to_parquet(index=False)
    blob.upload_from_string(buffer_parquet, content_type='application/octet-stream')
    
    # 3. Lógica híbrida para la firma de la URL (Local vs Producción)
    # Si detecta que hay una llave privada local (tu archivo serviceaccount.json)
    if hasattr(credentials, 'signer') and credentials.signer is not None:
        sa_email = None  # Se firma localmente sin problema
        
    # Si detecta que no hay llave privada (Estamos en Cloud Run)
    else:
        try:
            # Rescata el email de la cuenta de servicio de Cloud Run
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
            sa_email = requests.get(metadata_url, headers={"Metadata-Flavor": "Google"}, timeout=2).text
        except Exception:
            # Fallback de seguridad
            sa_email = getattr(credentials, 'service_account_email', None)

    # 4. Genera la URL
    url_temporal = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=1),
        method="GET",
        service_account_email=sa_email
    )
    
    return url_temporal
