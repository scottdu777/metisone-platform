# MetisOne AI Platform

MetisOne is an experimental BI platform built on top of
[Cube Core](https://cube.dev/).

The project explores a simpler way to build BI software. Instead of asking
users to work through many configuration screens, MetisOne lets users manage
the semantic layer and query data through natural language.

With AI agents, the system can understand a user's request, work with Cube
semantic metadata, generate the right Cube query, and return a business answer.
The long-term goal is to reduce product complexity, avoid unnecessary manual
configuration, and lower the cost of BI for small and mid-sized teams.

This project is still an early proof of concept.

## What MetisOne Does Today

- Edits Cube YAML semantic models through an API and chat-style agent tools.
- Adds, updates, and deletes dimensions, measures, joins, and pre-aggregations.
- Auto-completes Cube YAML models from PostgreSQL schema metadata.
- Normalizes common Cube YAML issues, including `pre_aggregations: null` and
  JavaScript-like pre-aggregation snippets.
- Converts natural-language questions into Cube REST `/load` queries.
- Validates generated query members against Cube `/meta` before calling Cube.
- Writes request/response logs and optional LLM planning traces as JSONL.
- Provides one local Semantic Client UI for both model editing and data query.

## Architecture

MetisOne is split into three independently runnable services:

```text
Semantic Client UI (:8090)
  |-- calls Semantic Edit API (:8088)
  `-- calls Semantic Data Query API (:8091)

Semantic Edit API (:8088)
  |-- reads/writes Cube YAML model files
  |-- discovers PostgreSQL schema metadata
  `-- optionally runs a configured Cube compile/restart command

Semantic Data Query API (:8091)
  |-- reads Cube /meta
  |-- asks OpenAI to plan a Cube REST query
  |-- validates and normalizes the query
  `-- calls Cube REST /load

Cube Core
  |-- owns semantic model runtime
  `-- executes generated Cube REST queries
```

For the current development setup, the client and data-query services usually
run on the local machine, while Cube Core and the Edit API can run on an Ubuntu
server close to the Cube YAML model files.

See [ARCHITECTURE.md](ARCHITECTURE.md) for deeper design notes and dependency
boundaries.

## Source Layout

```text
src/metisone_ai_platform/
|-- core/
|   `-- env.py
|-- observability/
|   `-- request_logging.py
|-- semantic_client/
|   |-- app.py
|   |-- llm_agent.py
|   |-- ui.py
|   `-- api_clients/
|       |-- edit_api.py
|       `-- query_api.py
|-- semantic_edit/
|   |-- service/
|   |-- cube_yaml/
|   |-- llm/
|   `-- mcp/
`-- semantic_query/
    |-- app.py
    |-- cube_client.py
    |-- planner.py
    |-- presentation.py
    |-- validator.py
    `-- models.py
```

Deployment entry points live under:

```text
deployments/
|-- semantic_client/
|-- semantic_data_query_service/
`-- semantic_edit_yaml_service/
```

## Installation

Python `>=3.11` is required.

For normal service development:

```bash
pip install -e ".[service,postgres]"
```

For tests:

```bash
pip install -e ".[service,postgres,dev]"
```

On Windows, you can explicitly use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Or activate it first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

## Configuration

Each service has its own `.env.example`:

```text
deployments/semantic_client/.env.example
deployments/semantic_data_query_service/.env.example
deployments/semantic_edit_yaml_service/.env.example
```

Copy the needed template to `.env` in the same deployment folder:

```bash
cp .env.example .env
```

Real `.env` files are ignored by Git. Do not commit API keys, DSNs, bearer
tokens, or other secrets.

Important token relationships:

- Client `SEMANTIC_EDIT_SERVICE_TOKEN` must match Edit API
  `METISONE_SEMANTIC_EDIT_TOKEN`.
- Client `SEMANTIC_DATA_QUERY_SERVICE_TOKEN` must match Query API
  `SEMANTIC_DATA_QUERY_SERVICE_TOKEN`.

Optional query planner alias configuration:

```env
METISONE_CUBE_ALIASES_JSON={"film":["movie","movies"]}
```

This helps the query planner map business words to Cube names without hardcoding
customer-specific database logic into the code.

## Start Services

Install dependencies from the repository root before starting each deployment:

```bash
pip install -e ".[service,postgres]"
```

### Semantic Edit API

```bash
cd deployments/semantic_edit_yaml_service
uvicorn main:app --host 0.0.0.0 --port 8088
```

This service owns write access to Cube YAML model files. It also owns the
PostgreSQL DSN used for schema discovery.

### Semantic Data Query API

```bash
cd deployments/semantic_data_query_service
uvicorn main:app --host 127.0.0.1 --port 8091
```

This service owns OpenAI configuration and Cube REST API configuration.

### Semantic Client UI

```bash
cd deployments/semantic_client
uvicorn main:app --host 127.0.0.1 --port 8090
```

Open:

```text
http://127.0.0.1:8090
```

VS Code launch configurations are available for debugging the services.

## Semantic Data Query API

Request:

```http
POST /v1/query
Authorization: Bearer <query-service-token>
Content-Type: application/json

{
  "question": "How many sports movies were rented in Woodridge?",
  "limit": 100
}
```

Response includes:

- `answer`: concise user-facing answer
- `plan`: final normalized Cube query plan
- `cube_request`: request sent to Cube REST `/load`
- `cube_response`: raw Cube response

The query planner uses Cube `/meta` as the source of truth. It asks the LLM to
generate a Cube query, then validates and normalizes the output before Cube is
called. The normalization layer handles issues such as duplicate cube prefixes,
exact-label filters, location filters, and choosing the most relevant count
measure from metadata.

## Semantic Edit API

Core endpoints:

```text
GET    /health
GET    /v1/cubes
GET    /v1/cubes/{cube}

GET    /v1/cubes/{cube}/measures
POST   /v1/cubes/{cube}/measures
PATCH  /v1/cubes/{cube}/measures/{name}
DELETE /v1/cubes/{cube}/measures/{name}

GET    /v1/cubes/{cube}/dimensions
POST   /v1/cubes/{cube}/dimensions
PATCH  /v1/cubes/{cube}/dimensions/{name}
DELETE /v1/cubes/{cube}/dimensions/{name}

GET    /v1/cubes/{cube}/joins
POST   /v1/cubes/{cube}/joins
PATCH  /v1/cubes/{cube}/joins/{name}
DELETE /v1/cubes/{cube}/joins/{name}

GET    /v1/cubes/{cube}/pre-aggregations
POST   /v1/cubes/{cube}/pre-aggregations
PATCH  /v1/cubes/{cube}/pre-aggregations/{name}
DELETE /v1/cubes/{cube}/pre-aggregations/{name}

POST   /v1/auto-complete
POST   /v1/normalize-models
POST   /v1/compile
```

Except for `/health`, endpoints require the configured bearer token.

### Auto-complete And Normalize

`POST /v1/auto-complete` can compare PostgreSQL schema metadata with Cube YAML
models and add missing model details, including:

- primary key dimensions
- missing identifier dimensions such as `customer_id` or `inventory_id`
- joins inferred from foreign keys
- normalized `pre_aggregations`

`POST /v1/normalize-models` fixes YAML structure issues without requiring a
PostgreSQL DSN. It is useful for repairing Cube UI generated model snippets,
especially JavaScript-like pre-aggregation blocks.

## Chat-Based Editing

The Semantic Client can run in OpenAI agent mode. In this flow:

```text
User message
  -> OpenAI edit planner
  -> MCP-style semantic edit tools
  -> Semantic Edit API
  -> Cube YAML files
```

The edit tool layer is intentionally loose-coupled. It exposes actions such as
listing cubes, creating dimensions, creating joins, creating pre-aggregations,
auto-completing models, and normalizing models.

## Logging

All services can write JSONL request/response logs when
`METISONE_REQUEST_LOG_FILE` is set.

The Semantic Data Query API also supports an LLM trace log:

```env
METISONE_LLM_TRACE_LOG_FILE=logs/semantic_query_llm.jsonl
```

The LLM trace log contains:

- OpenAI request payload
- raw OpenAI response content
- parsed LLM payload
- final normalized query plan

Sensitive fields such as tokens, passwords, API keys, and authorization headers
are redacted.

## Tests

Run all tests:

```bash
python -m pytest -q
```

Current local validation:

```text
52 passed
```

## Generated Artifacts

The repository may contain local demo artifacts such as YouTube scripts or PPTX
files under `outputs/`. Runtime logs and local `.env` files should not be
committed.

## License

MetisOne AI Platform is open source under the [Apache License 2.0](LICENSE).
