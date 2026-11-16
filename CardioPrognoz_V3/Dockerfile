# Educational ephemeral staging container (NOT intended for clinical use).
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0
COPY . .
RUN useradd -r -u 10001 -m cardio && mkdir -p /app/instance && chown cardio:cardio /app/instance
USER cardio
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "90", "app:app"]
