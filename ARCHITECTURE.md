# MetisOne Current Architecture

This document describes the active Semantic Client, Edit API, and Query API
architecture.

## 1. Application Boundaries

MetisOne has three peer application modules:

```text
semantic_client/   official UI and outbound HTTP clients
semantic_edit/     independently callable semantic model Edit API
semantic_query/    independently callable semantic data Query API
```

Semantic Client consumes the two APIs. It does not own their business logic.
Edit and Query can be called directly by third-party clients.

```text
                         +-----------------------------+
User/Browser ----------> | Semantic Client :8090       |
                         +-------------+---------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v                                       v
       +--------------------------+          +---------------------------+
       | Semantic Edit API :8088  |          | Semantic Query API :8091  |
       +------------+-------------+          +-------------+-------------+
                    |                                      |
                    v                                      v
          Cube YAML / PostgreSQL                     OpenAI / Cube REST

Third-party clients may call :8088 or :8091 directly.
```

## 2. Source Layout

```text
src/metisone_ai_platform/
|-- semantic_client/
|   |-- app.py
|   |-- main.py
|   |-- ui.py
|   |-- agent.py
|   |-- llm_agent.py
|   `-- api_clients/
|       |-- edit_api.py
|       `-- query_api.py
|-- semantic_edit/
|   |-- service/
|   |   |-- app.py
|   |   |-- config.py
|   |   |-- schemas.py
|   |   `-- chat_agent.py
|   |-- cube_yaml/
|   |   |-- repository.py
|   |   |-- editor.py
|   |   |-- auto_complete.py
|   |   |-- compiler.py
|   |   `-- yaml_codec.py
|   |-- llm/
|   `-- mcp/
|-- semantic_query/
|   |-- app.py
|   |-- config.py
|   |-- contracts.py
|   |-- models.py
|   |-- orchestrator.py
|   |-- planner.py
|   |-- validator.py
|   |-- cube_client.py
|   `-- presentation.py
|-- observability/
|   `-- request_logging.py
`-- core/
    `-- env.py
```

## 3. Semantic Client

Semantic Client is the only bundled UI and runs on port `8090`.

Responsibilities:

- display Query Data and Edit Model modes;
- plan edit operations with the configured LLM planner;
- call Edit tools through `MCPClient`;
- call the two backend APIs through outbound HTTP clients;
- return concise text to the browser;
- record the original request and concise response.

It must not:

- read or write Cube YAML;
- connect to PostgreSQL;
- hold Cube REST credentials;
- implement Query or Edit API business use cases.

Outbound adapters live in `semantic_client/api_clients/` so their purpose is
not confused with the backend services.

## 4. Semantic Edit API

Semantic Edit API runs on port `8088` and owns all model-editing behavior.

```text
HTTP request
  -> semantic_edit.service.app
  -> Pydantic schema and bearer authentication
  -> CubeSemanticLayerEditor / CubeYamlAutoCompleter / CubeCompiler
  -> CubeYamlRepository
  -> Cube YAML files
```

PostgreSQL access is used for schema discovery and YAML auto-completion. Only
this process receives the PostgreSQL DSN and Cube model filesystem path.

The edit planner produces structured `ToolCall` objects. It does not generate
or overwrite an entire YAML document. Repository path checks ensure edits stay
inside the configured model root.

## 5. Semantic Query API

Semantic Query API runs on port `8091` and owns the full query use case.

```text
POST /v1/query
  -> semantic_query.app
  -> DataQueryOrchestrator.ask()
  -> Cube REST /v1/meta
  -> OpenAIDataQueryPlanner.plan()
  -> CubeQueryValidator.validate()
  -> Cube REST /v1/load
  -> rows, annotation, generated query, and concise answer
```

Only this process receives Cube REST credentials. The planner output is
validated against Cube metadata before execution.

## 6. API Clients Versus API Services

Files under `semantic_client/api_clients/` are outbound HTTP adapters:

```text
edit_api.py   -> calls Semantic Edit API
query_api.py  -> calls Semantic Query API
```

They handle URLs, bearer tokens, JSON serialization, timeouts, and HTTP error
mapping. They contain no YAML, PostgreSQL, OpenAI query-planning, or Cube query
business logic.

The API implementations live under `semantic_edit/service/` and
`semantic_query/app.py`.

## 7. Dependency Rules

These rules are mandatory:

1. `semantic_client` may depend on `semantic_edit` contracts and its own HTTP
   adapters.
2. `semantic_edit` and `semantic_query` must not import `semantic_client`.
3. `semantic_edit` and `semantic_query` must not depend on each other.
4. Concrete HTTP clients are injected behind contracts such as
   `SemanticEditGateway`.
5. `semantic_client` must not contain backend business logic or backend
   credentials.
6. YAML edits belong in `semantic_edit/cube_yaml`, not FastAPI routes or UI.
7. Query planning and validation belong in `semantic_query`, not the Client.
8. Cross-boundary data remains structured: Pydantic HTTP schemas, query
   dataclasses, and `ToolCall` / `ToolResult`.
9. Secrets must come from deployment environments and must never be committed.

## 8. Deployment Units

| Deployment | ASGI entry point | Port |
| --- | --- | --- |
| Semantic Client | `metisone_ai_platform.semantic_client.main:app` | 8090 |
| Semantic Edit API | `metisone_ai_platform.semantic_edit.service.main:app` | 8088 |
| Semantic Query API | `metisone_ai_platform.semantic_query.main:app` | 8091 |

Deployment wrappers and isolated environments live under:

```text
deployments/semantic_client/
deployments/semantic_edit_yaml_service/
deployments/semantic_data_query_service/
```

The wrappers load the adjacent `.env` before importing the application
factory.

## 9. Trust And Credentials

| Process | Credentials it owns |
| --- | --- |
| Semantic Client | OpenAI edit-planner key, Edit API token, Query API token |
| Semantic Edit API | Edit bearer token, PostgreSQL DSN, YAML path |
| Semantic Query API | Query bearer token, OpenAI key, Cube REST URL/token |

Client and server token values must match, but use role-specific variable
names. Production deployments should use HTTPS, individual client identities,
rate limits, and fine-grained Edit permissions.

## 10. Observability

`observability/request_logging.py` provides rotating JSONL request/response
logging for all three processes. Records include request ID, duration, status,
request JSON, and response JSON. Sensitive key names are recursively redacted.

The Client log captures the user request and concise response. Edit and Query
logs capture their detailed API payloads for analysis.

## 11. Code Navigation

| Task | Start here |
| --- | --- |
| Client UI/API aggregation | `semantic_client/app.py` |
| Edit outbound HTTP calls | `semantic_client/api_clients/edit_api.py` |
| Query outbound HTTP calls | `semantic_client/api_clients/query_api.py` |
| Edit API routes | `semantic_edit/service/app.py` |
| YAML CRUD | `semantic_edit/cube_yaml/editor.py` |
| YAML auto-completion | `semantic_edit/cube_yaml/auto_complete.py` |
| Edit planner | `semantic_edit/llm/` |
| Edit MCP boundary | `semantic_edit/mcp/` |
| Query API routes | `semantic_query/app.py` |
| Query orchestration | `semantic_query/orchestrator.py` |
| Query planner | `semantic_query/planner.py` |
| Cube query validation | `semantic_query/validator.py` |
| Cube REST adapter | `semantic_query/cube_client.py` |
| JSON request logs | `observability/request_logging.py` |

## 12. Verification

Run the complete suite after boundary or API changes:

```bash
python -m pytest
```

Tests cover Query planning/validation, Edit CRUD and completion, Client API
aggregation, authentication, logging, redaction, and log rotation.
