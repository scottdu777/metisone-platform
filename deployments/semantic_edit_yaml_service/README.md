# Semantic Edit YAML Service

```bash
cp .env.example .env
cd ../..
pip install -e ".[service,postgres]"
cd deployments/semantic_edit_yaml_service
uvicorn main:app --host 0.0.0.0 --port 8088
```

This deployment owns database credentials and write access to Cube YAML.
Structured `/v1/*` request/response records are written to
`METISONE_REQUEST_LOG_FILE` when configured.
c