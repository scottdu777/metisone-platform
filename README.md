# MetisOne AI Platform

Early modular core for an AI knowledge / BI platform.

Start with [ARCHITECTURE.md](ARCHITECTURE.md) for human or AI-agent codebase
onboarding, system design, module boundaries, runtime flows, and extension
contracts.

Current modules:

- LLM Provider
- PostgreSQL Data Provider
- Native Semantic Provider
- Cube Core Provider
- Cube REST Data Query
- Cube YAML Semantic Layer Editor
- Local Semantic Chat Client
- Semantic Layer MCP boundary
- Query Orchestrator

The first implementation returns structured data only. UI, permissions, and policy filters are intentionally out of scope for this phase.

## Run Tests

```powershell
python -m pytest
```

## VS Code Debugging

The repo includes VS Code launch configurations in `.vscode/launch.json`.

Open the **Run and Debug** panel in VS Code, then choose one of:

- `Debug Semantic Edit Service`: starts the FastAPI edit service on port `8088`.
- `Debug Edit Service Client`: calls the service at `http://192.168.31.224:8088`.
- `Debug Local Chat Client UI`: starts a local browser UI on port `8090`.

Before using the debug button, install the project into your selected Python
environment:

```bash
pip install -e ".[service]"
```

Runtime configuration is centralized in `.env`. Start from `.env.example`,
then fill in your local values:

```bash
SEMANTIC_AGENT_MODE=openai
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com
OPENAI_CHAT_COMPLETIONS_URL=https://api.openai.com/v1/chat/completions

SEMANTIC_EDIT_SERVICE_URL=http://192.168.31.224:8088
SEMANTIC_EDIT_SERVICE_TOKEN=change-me

METISONE_CUBE_MODEL_DIR=/home/cody/metisone/model/cubes
METISONE_SEMANTIC_EDIT_TOKEN=change-me
METISONE_CUBE_COMPILE_COMMAND=
METISONE_CUBE_COMPILE_CWD=/home/cody/metisone

CUBE_API_BASE_URL=http://192.168.31.224:4000/cubejs-api/v1
CUBE_API_TOKEN=
```

`.env` and `sn.txt` are ignored by git. Do not commit API keys or tokens.

## Natural Language Data Query

MetisOne includes a first Cube REST data query layer in:

```txt
src/metisone_ai_platform/data_query/
```

It uses Cube REST `/v1/meta` to read semantic metadata, OpenAI to produce Cube
REST `/v1/load` query JSON, a validator to reject unknown members and unsafe
operators, and Cube REST `/v1/load` to return structured rows.

In the Local Chat UI:

```txt
Send       -> semantic layer edit flow
Query Data -> data query flow
```

Example question:

```txt
有没有一部叫 Academy Dinosaur 的电影？
```

Expected Cube query shape:

```json
{
  "dimensions": ["film.title"],
  "filters": [
    {
      "member": "film.title",
      "operator": "equals",
      "values": ["Academy Dinosaur"]
    }
  ],
  "limit": 1
}
```

If you are debugging the service on Ubuntu through VS Code Remote SSH, the
default launch config uses:

```txt
METISONE_CUBE_MODEL_DIR=/home/cody/metisone/model/cubes
METISONE_SEMANTIC_EDIT_TOKEN=change-me
```

If your Cube YAML directory or token is different, update `.vscode/launch.json`.

If you are debugging from Windows/local VS Code, use `Debug Local Chat Client UI`
or `Debug Edit Service Client` to call the Ubuntu service. The service itself
should still run on Ubuntu, because only Ubuntu can access
`/home/cody/metisone/model/cubes`.

## Chat UI

There are two UI options:

1. Local client UI on Windows

Run `Debug Local Chat Client UI` in VS Code, then open:

```txt
http://127.0.0.1:8090
```

This UI runs on your local machine. It contains the chat UI, LLM planner, MCP
client, and MCP-style semantic edit tools. The Ubuntu VM only runs the
deterministic edit service that can access Cube YAML files.

Default remote service:

```txt
http://192.168.31.224:8088
```

The local flow is:

```txt
Local Chat UI
  -> LLM Agent
  -> MCP Client
  -> Semantic Layer MCP Server
  -> Semantic Layer Edit Service
  -> Cube YAML files
```

Set these environment variables on your local machine if you want the agent to
use OpenAI:

```bash
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4.1-mini
SEMANTIC_AGENT_MODE=auto
```

`SEMANTIC_AGENT_MODE=auto` uses OpenAI when `OPENAI_API_KEY` exists. If the key
is not set, it falls back to the deterministic rule planner so you can still
debug the edit-service and MCP path.

For stricter OpenAI-only behavior:

```bash
SEMANTIC_AGENT_MODE=openai
```

For local deterministic parsing only:

```bash
SEMANTIC_AGENT_MODE=rule
```

2. Service-hosted UI on Ubuntu

When the Semantic Layer Edit Service is running, you can also open:

```txt
http://192.168.31.224:8088/ui
```

For your preferred setup, use the **local client UI**. Enter the API token from
`METISONE_SEMANTIC_EDIT_TOKEN`, then ask for a semantic layer change. With
OpenAI enabled, you can use more natural requests. Without OpenAI, the fallback
planner supports controlled natural language like:

```txt
create measure revenue on payment sql amount type sum title "Revenue"
modify measure revenue on payment title "Total Revenue"
delete measure revenue on payment
create dimension payment_date on payment sql payment_date type time title "Payment Date"
```

The local UI sends the message to a local agent. The agent plans tool calls,
executes them through an MCP-style boundary, and the MCP tool server calls the
remote service's structured CRUD APIs. This keeps the agent and chat UI on your
development machine while the Ubuntu service only edits Cube YAML.

The current MCP implementation is in-process:

```txt
src/metisone_ai_platform/semantic_layer/mcp/
```

It is intentionally isolated behind `MCPClient` and `MCPServer` contracts so a
real stdio/HTTP MCP transport can replace it later without changing the local
chat UI or LLM planner.

## Optional PostgreSQL Dependency

```powershell
pip install ".[postgres]"
```

## Semantic Layer

Semantic layer code lives in its own package:

```txt
src/metisone_ai_platform/semantic_layer/
```

It contains:

- `models.py`: semantic models, metrics, dimensions, joins
- `contracts.py`: semantic provider interface
- `native_provider.py`: native SQL compiler
- `cube_core/`: Cube Core API providers
- `cube_yaml/`: Cube YAML repository, editor, and compile command runner

Legacy imports under `metisone_ai_platform.providers.semantic` and
`metisone_ai_platform.providers.cube_core` are kept as thin compatibility
wrappers.

## Cube Core Provider

Cube API integration lives in:

```txt
src/metisone_ai_platform/semantic_layer/cube_core/
```

Example:

```python
from metisone_ai_platform.orchestrator.query_orchestrator import QueryOrchestrator
from metisone_ai_platform.semantic_layer.cube_core import (
    CubeClient,
    CubeDataProvider,
    CubeSemanticProvider,
)
from metisone_ai_platform.providers.llm import OpenAIChatLLMProvider

client = CubeClient(
    base_url="http://localhost:4000",
    api_token="Bearer your_cube_token",
)

orchestrator = QueryOrchestrator(
    llm_provider=OpenAIChatLLMProvider(),
    semantic_provider=CubeSemanticProvider(client),
    data_provider=CubeDataProvider(client),
)
```

## Cube YAML Editor

The MVP semantic layer assistant can update Cube YAML files through structured
operations:

```python
from metisone_ai_platform.semantic_layer.cube_yaml import (
    CubeSemanticLayerEditor,
    CubeYamlRepository,
)

repository = CubeYamlRepository("cube")
editor = CubeSemanticLayerEditor(repository)

editor.create_measure(
    cube="payment",
    name="revenue",
    sql="amount",
    measure_type="sum",
)
```

Cube recompilation is intentionally configurable:

```python
from metisone_ai_platform.semantic_layer.cube_yaml import CubeCompiler

compiler = CubeCompiler(["docker", "compose", "restart", "cube"], cwd=".")
result = compiler.compile()
```

## Semantic Layer Edit Service

The edit service is designed to run next to Cube on the Ubuntu server. Your
local MetisOne app can call it over HTTP while keeping direct YAML file access
on the Cube host.

### 1. Prepare The Ubuntu Host

Current development layout:

```txt
/home/cody/metisone-platform/
  pyproject.toml
  src/

/home/cody/metisone/
  docker-compose.yml
  model/
    cubes/
      payment.yml
      rental.yml
      customer.yml
```

Cube should mount the same model directory into the Cube container. For
example:

```yaml
services:
  cube:
    volumes:
      - ./model:/cube/conf/model
```

The edit service must run as a user that can read and write the Cube YAML
files under `/home/cody/metisone/model/cubes`.

### 2. Install Dependencies

From the project root on Ubuntu:

```bash
cd /home/cody/metisone-platform
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ".[service,postgres]"
```

### 3. Configure Environment Variables

sudo nano /etc/metisone-semantic-edit.env

```bash
METISONE_CUBE_MODEL_DIR=/home/cody/metisone/model/cubes
METISONE_SEMANTIC_EDIT_TOKEN=change-me-to-a-long-random-token
METISONE_CUBE_COMPILE_COMMAND=docker compose restart cube
METISONE_CUBE_COMPILE_CWD=/home/cody/metisone
```

If your Cube YAML files are directly under `/home/cody/metisone`, use:

```bash
METISONE_CUBE_MODEL_DIR=/home/cody/metisone
```

`METISONE_CUBE_COMPILE_CWD` should point to the directory that contains
`docker-compose.yml` or `compose.yaml`.

Configuration:

- `METISONE_CUBE_MODEL_DIR`: directory containing Cube YAML files.
- `METISONE_POSTGRES_DSN`: optional PostgreSQL DSN used to enrich Cube-generated
  YAML with database primary keys, unique constraints, and foreign-key joins.

### Auto-complete Cube-generated YAML

Install the service and PostgreSQL extras, point `METISONE_CUBE_MODEL_DIR` at
the Cube-generated YAML directory, and configure `METISONE_POSTGRES_DSN`.
Preview deterministic changes first:

```http
POST /v1/auto-complete
Authorization: Bearer <token>
Content-Type: application/json

{
  "schemas": ["public"],
  "apply": false,
  "bidirectional_joins": true
}
```

Using curl against a service running on port 8088:

```bash
curl -X POST http://127.0.0.1:8088/v1/auto-complete \
  -H "Authorization: Bearer $METISONE_SEMANTIC_EDIT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"schemas":["public"],"apply":false,"bidirectional_joins":true}'
```

Using PowerShell:

```powershell
$headers = @{ Authorization = "Bearer $env:METISONE_SEMANTIC_EDIT_TOKEN" }
$body = @{
  schemas = @("public")
  apply = $false
  bidirectional_joins = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8088/v1/auto-complete" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

Repeat with `"apply": true` after reviewing `changes` and `warnings`. The
auto-completer only uses database constraint evidence. It marks existing
primary-key dimensions or creates missing ones from PostgreSQL column types,
adds a `count` measure when missing, creates FK-side
`many_to_one`/`one_to_one` joins, and optionally creates reverse
`one_to_many` joins. Conflicting joins, missing Cube models, tables without
primary keys, and multiple foreign keys between the same pair of tables are
reported without being overwritten or guessed.
- `METISONE_SEMANTIC_EDIT_TOKEN`: bearer token required by the API.
- `METISONE_CUBE_COMPILE_COMMAND`: fixed command run by `POST /v1/compile`.
- `METISONE_CUBE_COMPILE_CWD`: working directory for the compile command.

The compile command is configured on the server and is not accepted from API
requests. This prevents remote callers from executing arbitrary shell commands.

### 4. Run Manually

For a quick manual run:

```bash
cd /home/cody/metisone-platform
source .venv/bin/activate
set -a
source /etc/metisone-semantic-edit.env
set +a
uvicorn metisone_ai_platform.semantic_layer.edit_service.main:app \
  --host 0.0.0.0 \
  --port 8088
```

### 5. Run With systemd

Create `/etc/systemd/system/metisone-semantic-edit.service`:

```ini
[Unit]
Description=MetisOne Semantic Layer Edit Service
After=network.target docker.service

[Service]
User=cody
Group=cody
WorkingDirectory=/home/cody/metisone-platform
EnvironmentFile=/etc/metisone-semantic-edit.env
ExecStart=/home/cody/metisone-platform/.venv/bin/uvicorn metisone_ai_platform.semantic_layer.edit_service.main:app --host 0.0.0.0 --port 8088
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable metisone-semantic-edit
sudo systemctl start metisone-semantic-edit
sudo systemctl status metisone-semantic-edit
```

View logs:

```bash
sudo journalctl -u metisone-semantic-edit -f
```

### 6. Verify From The Ubuntu Host

Health check:

```bash
curl http://127.0.0.1:8088/health
```

List cubes:

```bash
curl http://127.0.0.1:8088/v1/cubes \
  -H "Authorization: Bearer change-me-to-a-long-random-token"
```

Create a measure:

```bash
curl -X POST http://192.168.31.224:8088/v1/cubes/payment/measures \
  -H "Authorization: Bearer change-me-to-a-long-random-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "revenue",
    "sql": "amount",
    "type": "sum",
    "extra_fields": {
      "title": "Revenue"
    }
  }'
```

Trigger Cube restart/recompile:

```bash
curl -X POST http://127.0.0.1:8088/v1/compile \
  -H "Authorization: Bearer change-me-to-a-long-random-token"
```

### 7. Call From Local MetisOne

From your local machine, call the Ubuntu server IP:

```txt
SEMANTIC_EDIT_SERVICE_URL=http://192.168.31.224:8088
SEMANTIC_EDIT_SERVICE_TOKEN=change-me-to-a-long-random-token
```

Local MetisOne should send structured requests to this service after the LLM
has converted the user message into an operation such as `create_measure` or
`modify_dimension`.

Python client example:

```python
from metisone_ai_platform.semantic_layer.edit_service import (
    SemanticEditServiceClient,
)

client = SemanticEditServiceClient(
    base_url="http://192.168.31.224:8088",
    api_token="change-me",
)

print(client.health())
print(client.list_cubes())

client.create_measure(
    cube="payment",
    name="revenue",
    sql="amount",
    measure_type="sum",
    extra_fields={"title": "Revenue"},
)
```

### 8. Useful Endpoints

```txt
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
POST   /v1/compile
```
