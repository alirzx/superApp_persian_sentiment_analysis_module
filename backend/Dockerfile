FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
ARG PIP_PRIMARY_INDEX_URL=https://package-mirror.liara.ir/repository/pypi/simple
ARG PIP_FALLBACK_INDEX_URL=https://mirror2.chabokan.net/pypi/simple/
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN (pip install --index-url "$PIP_PRIMARY_INDEX_URL" -r /tmp/requirements.txt || \
     pip install --index-url "$PIP_FALLBACK_INDEX_URL" -r /tmp/requirements.txt) \
    && groupadd -r app && useradd -r -g app -d /app app
COPY backend/app /app/app
COPY models.json /app/models.json
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
