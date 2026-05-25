FROM python:3.11-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel

# Install llm-sdk first (internal package)
COPY packages/llm-sdk /workspace/packages/llm-sdk
RUN pip install --no-cache-dir -e /workspace/packages/llm-sdk

# Install ingestion service
COPY services/ingestion/pyproject.toml /workspace/services/ingestion/pyproject.toml
RUN pip install --no-cache-dir -e /workspace/services/ingestion

COPY services/ingestion /workspace/services/ingestion

WORKDIR /workspace/services/ingestion

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

EXPOSE 8001
