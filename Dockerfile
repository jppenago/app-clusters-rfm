# Usamos una imagen oficial y ligera de Python
FROM python:3.10-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Evitamos que Python escriba archivos .pyc y forzamos a que el output se vea en los logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copiamos primero el archivo de requerimientos (esto optimiza el tiempo de construcción)
COPY requirements.txt .

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la aplicación al contenedor
COPY . .

# Exponemos el puerto 8080 que es el requerido por Google Cloud Run
EXPOSE 8080

# Comando principal para arrancar Streamlit en el puerto 8080 y accesible desde fuera (0.0.0.0)
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.headless=true"]