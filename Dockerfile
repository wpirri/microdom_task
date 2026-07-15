FROM python:3.11-slim

# Crear usuario no-root
RUN useradd -m appuser

# Crear directorio de logs dentro del contenedor
RUN mkdir -p /app/logs
RUN mkdir -p /app/etc

# Crear directorio de la app
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . .

# Dar permisos al usuario
RUN chown -R appuser:appuser /app

# Cambiar al usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8082

# Ejecutar la app
#CMD ["python", "run.py"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
