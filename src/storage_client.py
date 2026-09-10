import pandas as pd
from google.cloud import storage
from datetime import datetime, timedelta
import pytz

def exportar_parquet_firmado(df_resultados, project_id, bucket_name="app-clusters-rfm"):
    # 1. Obtener la hora actual en Colombia (UTC-5)
    zona_colombia = pytz.timezone('America/Bogota')
    ahora = datetime.now(zona_colombia)
    nombre_archivo = f"app_clustersrfm_{ahora.strftime('%Y%m%d_%H%M')}.parquet"
    
    # 2. Inicializar el cliente de Cloud Storage
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(nombre_archivo)
    
    # 3. Convertir el DataFrame a Parquet en memoria (retorna bytes)
    buffer_parquet = df_resultados.to_parquet(index=False)
    blob.upload_from_string(buffer_parquet, content_type='application/octet-stream')
    
    # 4. Generar la Signed URL (válida por 1 hora)
    url_temporal = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=1),
        method="GET"
    )
    return url_temporal