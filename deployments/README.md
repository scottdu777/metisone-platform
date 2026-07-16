# Independent deployment units

The three applications are deployed independently while sharing the reusable
Python code under `src/metisone_ai_platform`:

- `semantic_edit_yaml_service`: owns Cube YAML files, PostgreSQL schema
  inspection, compilation, and the authenticated edit API.
- `semantic_client`: the single user-facing UI. It calls both backend APIs but
  never needs database, Cube API, or YAML filesystem credentials.
- `semantic_data_query_service`: authenticated semantic data-query API for
  Semantic Client and third-party clients.
  It owns OpenAI and Cube REST credentials, but cannot edit YAML.

Copy each `.env.example` to `.env` only for the application being deployed.
Run commands from the selected deployment directory after installing the root
package in editable mode.

## Request/response logs

Each process can write JSONL request/response records through
`METISONE_REQUEST_LOG_FILE`. One line represents one HTTP request and includes
the service, request ID, duration, status, request JSON, and response JSON.
Files rotate at `METISONE_REQUEST_LOG_MAX_BYTES` and retain
`METISONE_REQUEST_LOG_BACKUP_COUNT` backups. Token, password, secret, API-key,
and authorization fields are redacted. Use an absolute log path for production
deployments; the relative paths in `.env.example` are intended for local use.
