# Semantic Data Query Service

```bash
cp .env.example .env
cd ../..
pip install -e ".[service]"
cd deployments/semantic_data_query_service
uvicorn main:app --host 127.0.0.1 --port 8091
```

This API can be called by Semantic Client or a third-party client. Call
`POST /v1/query` with a bearer token and JSON body:

```json
{"question": "Action category has how many films?", "limit": 100}
```

The full question, generated Cube query, rows, and response are written as
JSONL to `METISONE_REQUEST_LOG_FILE` when configured.

To inspect the LLM planner input and output, configure:

```env
METISONE_LLM_TRACE_LOG_FILE=logs/semantic_query_llm.jsonl
```

This writes one JSON object per LLM planning call. It includes the OpenAI
request payload, raw model content, parsed payload, and final Cube query plan.
The OpenAI API key is never logged because it is only sent in the HTTP
authorization header, and sensitive fields are redacted as a second guard.
