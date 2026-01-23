# AURA-NOTES-MANAGER API Dockerfile
# Container image for the Notes Manager FastAPI backend.

# Installs service dependencies from the Notes Manager requirements
# and runs Uvicorn on port 8001 for the API service.
# Built from the AURA-NOTES-MANAGER root context.

# @see: AURA-NOTES-MANAGER/docker-compose.yml - Service build configuration
# @note: Uses Python 3.10 to match the local venv

FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY api /app

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
