from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from metisone_ai_platform.semantic_layer.cube_yaml import (
    CubeCompiler,
    CubeSemanticLayerEditor,
    CubeYamlAutoCompleter,
    CubeYamlRepository,
    PostgresSchemaInspector,
)
from metisone_ai_platform.semantic_layer.cube_yaml.repository import CubeYamlDocument
from metisone_ai_platform.semantic_layer.edit_service.chat_agent import (
    RuleBasedSemanticEditAgent,
)
from metisone_ai_platform.semantic_layer.edit_service.config import (
    EditServiceConfig,
    load_config_from_env,
)
from metisone_ai_platform.semantic_layer.edit_service.schemas import (
    ChatRequest,
    ChatResponse,
    AutoCompleteRequest,
    CompileResponse,
    DimensionCreateRequest,
    EditResponse,
    JoinCreateRequest,
    MeasureCreateRequest,
    MemberUpdateRequest,
)
from metisone_ai_platform.semantic_layer.edit_service.ui import CHAT_UI_HTML


def create_app(config: EditServiceConfig | None = None) -> FastAPI:
    resolved_config = config or load_config_from_env()
    repository = CubeYamlRepository(resolved_config.cube_model_dir)
    editor = CubeSemanticLayerEditor(repository)
    chat_agent = RuleBasedSemanticEditAgent(editor)
    compiler = (
        CubeCompiler(
            resolved_config.compile_command,
            cwd=resolved_config.compile_cwd,
        )
        if resolved_config.compile_command
        else None
    )

    app = FastAPI(
        title="MetisOne Semantic Layer Edit Service",
        version="0.1.0",
    )

    @app.exception_handler(FileNotFoundError)
    def file_not_found_handler(
        request: Request,
        exc: FileNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "error_type": exc.__class__.__name__,
                "path": str(request.url.path),
            },
        )

    def require_token(
        authorization: str | None = Header(default=None),
    ) -> None:
        if not resolved_config.api_token:
            return
        expected = f"Bearer {resolved_config.api_token}"
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API token.",
            )

    auth_dependency = Depends(require_token)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "cube_model_dir": str(resolved_config.cube_model_dir),
        }

    @app.get("/ui", response_class=HTMLResponse)
    def chat_ui() -> str:
        return CHAT_UI_HTML

    @app.post(
        "/v1/chat",
        response_model=ChatResponse,
        dependencies=[auth_dependency],
    )
    def chat(request: ChatRequest) -> ChatResponse:
        command, result = chat_agent.handle(request.message)
        edit_response = EditResponse(**result.__dict__)
        return ChatResponse(
            success=result.success,
            message=result.message,
            command=command.__dict__,
            edit_result=edit_response,
        )

    @app.get("/v1/cubes", dependencies=[auth_dependency])
    def list_cubes() -> list[dict[str, Any]]:
        documents = repository.read_all()
        return [_document_summary(document) for document in documents]

    @app.get("/v1/cubes/{cube}", dependencies=[auth_dependency])
    def get_cube(cube: str) -> dict[str, Any]:
        document = repository.find_by_cube(cube)
        return {
            "file_path": str(document.path),
            "cube": cube,
            "data": _cube_data(document, cube),
        }

    @app.get("/v1/cubes/{cube}/measures", dependencies=[auth_dependency])
    def list_measures(cube: str) -> list[dict[str, Any]]:
        return _list_members(cube, "measures")

    @app.post(
        "/v1/cubes/{cube}/measures",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def create_measure(cube: str, request: MeasureCreateRequest) -> EditResponse:
        result = editor.create_measure(
            cube,
            name=request.name,
            sql=request.sql,
            measure_type=request.type,
            **request.extra_fields,
        )
        return EditResponse(**result.__dict__)

    @app.patch(
        "/v1/cubes/{cube}/measures/{name}",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def modify_measure(
        cube: str,
        name: str,
        request: MemberUpdateRequest,
    ) -> EditResponse:
        result = editor.modify_measure(cube, name, **request.fields)
        return EditResponse(**result.__dict__)

    @app.delete(
        "/v1/cubes/{cube}/measures/{name}",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def delete_measure(cube: str, name: str) -> EditResponse:
        result = editor.delete_measure(cube, name)
        return EditResponse(**result.__dict__)

    @app.get("/v1/cubes/{cube}/dimensions", dependencies=[auth_dependency])
    def list_dimensions(cube: str) -> list[dict[str, Any]]:
        return _list_members(cube, "dimensions")

    @app.post(
        "/v1/cubes/{cube}/dimensions",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def create_dimension(cube: str, request: DimensionCreateRequest) -> EditResponse:
        result = editor.create_dimension(
            cube,
            name=request.name,
            sql=request.sql,
            dimension_type=request.type,
            **request.extra_fields,
        )
        return EditResponse(**result.__dict__)

    @app.patch(
        "/v1/cubes/{cube}/dimensions/{name}",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def modify_dimension(
        cube: str,
        name: str,
        request: MemberUpdateRequest,
    ) -> EditResponse:
        result = editor.modify_dimension(cube, name, **request.fields)
        return EditResponse(**result.__dict__)

    @app.delete(
        "/v1/cubes/{cube}/dimensions/{name}",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def delete_dimension(cube: str, name: str) -> EditResponse:
        result = editor.delete_dimension(cube, name)
        return EditResponse(**result.__dict__)

    @app.get("/v1/cubes/{cube}/joins", dependencies=[auth_dependency])
    def list_joins(cube: str) -> list[dict[str, Any]]:
        return _list_members(cube, "joins")

    @app.post(
        "/v1/cubes/{cube}/joins",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def create_join(cube: str, request: JoinCreateRequest) -> EditResponse:
        result = editor.create_join(
            cube,
            name=request.name,
            sql=request.sql,
            relationship=request.relationship,
            **request.extra_fields,
        )
        return EditResponse(**result.__dict__)

    @app.patch(
        "/v1/cubes/{cube}/joins/{name}",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def modify_join(
        cube: str,
        name: str,
        request: MemberUpdateRequest,
    ) -> EditResponse:
        result = editor.modify_join(cube, name, **request.fields)
        return EditResponse(**result.__dict__)

    @app.delete(
        "/v1/cubes/{cube}/joins/{name}",
        response_model=EditResponse,
        dependencies=[auth_dependency],
    )
    def delete_join(cube: str, name: str) -> EditResponse:
        result = editor.delete_join(cube, name)
        return EditResponse(**result.__dict__)

    @app.post(
        "/v1/compile",
        response_model=CompileResponse,
        dependencies=[auth_dependency],
    )
    def compile_cube() -> CompileResponse:
        if compiler is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="METISONE_CUBE_COMPILE_COMMAND is not configured.",
            )

        result = compiler.compile()
        return CompileResponse(**result.__dict__)

    @app.post("/v1/auto-complete", dependencies=[auth_dependency])
    def auto_complete(request: AutoCompleteRequest) -> dict[str, Any]:
        if not resolved_config.postgres_dsn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="METISONE_POSTGRES_DSN is not configured.",
            )
        metadata = PostgresSchemaInspector(resolved_config.postgres_dsn).inspect(
            request.schemas
        )
        report = CubeYamlAutoCompleter(repository).complete(
            metadata,
            apply=request.apply,
            bidirectional_joins=request.bidirectional_joins,
        )
        return asdict(report)

    def _list_members(cube: str, key: str) -> list[dict[str, Any]]:
        document = repository.find_by_cube(cube)
        value = _cube_data(document, cube).get(key)
        if value is None:
            return []
        if not isinstance(value, list):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cube YAML field must be a list: {key}",
            )
        return value

    return app


def _document_summary(document: CubeYamlDocument) -> dict[str, Any]:
    cube_name = _cube_name(document)
    data = _cube_data(document, cube_name)
    return {
        "cube": cube_name,
        "file_path": str(document.path),
        "sql_table": data.get("sql_table"),
        "measures_count": len(data.get("measures") or []),
        "dimensions_count": len(data.get("dimensions") or []),
        "joins_count": len(data.get("joins") or []),
    }


def _cube_name(document: CubeYamlDocument) -> str:
    cubes = document.data.get("cubes")
    if isinstance(cubes, list):
        for cube in cubes:
            if isinstance(cube, dict) and cube.get("name"):
                return str(cube["name"])
    return str(document.data.get("cube") or document.data.get("name") or document.path.stem)


def _cube_data(document: CubeYamlDocument, cube_name: str) -> dict[str, Any]:
    cubes = document.data.get("cubes")
    if isinstance(cubes, list):
        for cube in cubes:
            if isinstance(cube, dict) and cube.get("name") == cube_name:
                return cube
        raise ValueError(f"Cube not found in YAML document: {cube_name}")
    return document.data
