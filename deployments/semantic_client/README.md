# Semantic Client

```bash
cp .env.example .env
cd ../..
pip install -e ".[service]"
cd deployments/semantic_client
uvicorn main:app --host 127.0.0.1 --port 8090
```

This is the official user-facing UI. It calls the Semantic Edit YAML Service
and Semantic Data Query Service APIs, but has no database, Cube REST, or
YAML filesystem credentials.

User edit/query requests and concise responses are written as JSONL to the
file configured by `METISONE_REQUEST_LOG_FILE`.
