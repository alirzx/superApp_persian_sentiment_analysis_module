FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
ARG PIP_PRIMARY_INDEX_URL=https://package-mirror.liara.ir/repository/pypi/simple
ARG PIP_FALLBACK_INDEX_URL=https://mirror2.chabokan.net/pypi/simple/
ARG PIP_TIMEOUT_SECONDS=90
ARG PIP_RETRIES=4
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
# --isolated ignores user/site pip config and prevents an implicit PyPI index.
# Retry mirror failures with longer timeouts, switching to Chabokan only if needed.
RUN set -eu; \
    (python -m pip --isolated install --disable-pip-version-check --no-cache-dir \
       --timeout "$PIP_TIMEOUT_SECONDS" --retries "$PIP_RETRIES" \
       --index-url "$PIP_PRIMARY_INDEX_URL" -r /tmp/requirements.txt || \
     python -m pip --isolated install --disable-pip-version-check --no-cache-dir \
       --timeout "$PIP_TIMEOUT_SECONDS" --retries "$PIP_RETRIES" \
       --index-url "$PIP_FALLBACK_INDEX_URL" -r /tmp/requirements.txt); \
    groupadd -r app; useradd -r -g app -d /app app
COPY backend/app /app/app
COPY models.json /app/models.json
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
