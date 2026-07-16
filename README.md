# MetisOne AI Platform

MetisOne provides one Semantic Client and two independently callable backend
APIs:

- Semantic Client: one UI for querying data and editing semantic models.
- Semantic Edit API: Cube YAML editing, PostgreSQL schema discovery, and model compilation.
- Semantic Query API: natural-language planning, Cube query validation, and Cube REST execution.

## Current Source Layout

```text
src/metisone_ai_platform/
|-- semantic_client/
|   |-- app.py                    # user-facing FastAPI/UI on :8090
|   |-- llm_agent.py              # semantic edit agent
|   |-- ui.py
|   `-- api_clients/
|       |-- edit_api.py           # outbound HTTP client for :8088
|       `-- query_api.py          # outbound HTTP client for :8091
|-- semantic_edit/
|   |-- service/                  # public Edit API on :8088
|   |-- cube_yaml/                # YAML repository, editor, completion, compiler
|   |-- llm/                      # edit planner contracts and implementations
|   `-- mcp/                      # edit tool contracts and adapters
|-- semantic_query/
|   |-- app.py                    # public Query API on :8091
|   |-- orchestrator.py           # query use case
|   |-- planner.py                # OpenAI Cube-query planner
|   |-- validator.py              # semantic member/query validation
|   |-- cube_client.py            # Cube REST adapter
|   `-- models.py                 # query request, plan, and result models
|-- observability/                # rotating JSONL request/response logs
`-- core/
    `-- env.py                    # shared dotenv loader
```

New code uses these package paths directly.

## Runtime Topology

```text
User -> Semantic Client :8090
          |-- HTTP -> Semantic Edit API :8088 -> Cube YAML / PostgreSQL
          `-- HTTP -> Semantic Query API :8091 -> OpenAI / Cube REST

Third-party clients
          |-- HTTP -> Semantic Edit API :8088
          `-- HTTP -> Semantic Query API :8091
```

Semantic Client is the official UI, not the owner of Edit or Query business
logic. Third-party web, mobile, BI, agent, or automation clients may call the
two APIs directly.

## Install

Python `>=3.11` is required.

```bash
pip install -e ".[service,postgres]"
```

For a production wheel:

```bash
pip install build
python -m build
```

## Configuration

Each deployment owns an independent `.env`. Copy only the templates needed on
that machine:

```text
deployments/semantic_client/.env.example
deployments/semantic_edit_yaml_service/.env.example
deployments/semantic_data_query_service/.env.example
```

Real `.env` files are ignored by Git. Never put real API keys, DSNs, or tokens
in `.env.example`.

Service-to-service tokens must match:

- Client `SEMANTIC_EDIT_SERVICE_TOKEN` = Edit API `METISONE_SEMANTIC_EDIT_TOKEN`
- Client `SEMANTIC_DATA_QUERY_SERVICE_TOKEN` = Query API `SEMANTIC_DATA_QUERY_SERVICE_TOKEN`

## Start The Applications

### Semantic Edit API — port 8088

```bash
cd deployments/semantic_edit_yaml_service
uvicorn main:app --host 0.0.0.0 --port 8088
```

### Semantic Query API — port 8091

```bash
cd deployments/semantic_data_query_service
uvicorn main:app --host 127.0.0.1 --port 8091
```

Bind to an internal network interface or place the API behind HTTPS when it
must be called from another machine.

### Semantic Client — port 8090

```bash
cd deployments/semantic_client
uvicorn main:app --host 127.0.0.1 --port 8090
```

Open `http://127.0.0.1:8090`.

VS Code launch configurations provide equivalent `Debug ...` entries for all
three processes.

## Public Query API

```http
POST /v1/query
Authorization: Bearer <query-service-token>
Content-Type: application/json

{
  "question": "Action category has how many films?",
  "limit": 100
}
```

The response contains a concise answer, generated Cube query, rows, row count,
and Cube annotation.

## Public Edit API

Core endpoints include:

```text
GET    /v1/cubes
GET    /v1/cubes/{cube}
POST   /v1/cubes/{cube}/measures
PATCH  /v1/cubes/{cube}/measures/{name}
DELETE /v1/cubes/{cube}/measures/{name}
POST   /v1/cubes/{cube}/dimensions
POST   /v1/cubes/{cube}/joins
POST   /v1/auto-complete
POST   /v1/compile
```

Except for `/health`, Edit API endpoints require the configured bearer token.
The compile command is fixed in the service environment and cannot be supplied
by an API request.

## JSON Request/Response Logs

All three processes write JSONL logs when `METISONE_REQUEST_LOG_FILE` is set.
Each record contains:

- UTC timestamp and service name
- request ID, method, path, status, and duration
- request JSON and response JSON

Files rotate by size. Token, password, secret, API-key, and authorization
fields are redacted. The templates default to separate files under `logs/`.
Use absolute log paths in production.

## Tests

```bash
python -m pytest
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for dependency rules and detailed call
flows.
