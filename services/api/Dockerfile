FROM python:3.11-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel

# Install llm-sdk first (internal package)
COPY packages/llm-sdk /workspace/packages/llm-sdk
RUN pip install --no-cache-dir -e /workspace/packages/llm-sdk

# Install api service
COPY services/api/pyproject.toml /workspace/services/api/pyproject.toml
RUN pip install --no-cache-dir -e /workspace/services/api

# Install ingestion package too, so the api can optionally run the consumer
# in-process (ENABLE_INLINE_INGESTION=true) without a separate worker.
COPY services/ingestion/pyproject.toml /workspace/services/ingestion/pyproject.toml
RUN pip install --no-cache-dir -e /workspace/services/ingestion

COPY services/ingestion /workspace/services/ingestion
COPY services/api /workspace/services/api

WORKDIR /workspace/services/api

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
