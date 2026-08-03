from metisone_ai_platform.semantic_client.llm_agent import (
    LocalLLMSemanticEditAgent,
)
from metisone_ai_platform.semantic_edit.llm.contracts import LLMPlan, SemanticEditPlanner
from metisone_ai_platform.semantic_edit.mcp.contracts import (
    MCPClient,
    ToolCall,
    ToolResult,
)
from metisone_ai_platform.semantic_edit.mcp.semantic_edit_server import (
    SemanticLayerEditMCPServer,
)


class FakeEditClient:
    def __init__(self) -> None:
        self.calls = []

    def list_cubes(self):
        self.calls.append(("list_cubes",))
        return [{"name": "payment"}]

    def create_measure(self, cube, name, sql, measure_type, extra_fields=None):
        self.calls.append(("create_measure", cube, name, sql, measure_type, extra_fields))
        return {"success": True, "message": "created"}

    def create_pre_aggregation(
        self,
        cube,
        name,
        pre_aggregation_type="rollup",
        measures=None,
        dimensions=None,
        segments=None,
        time_dimension=None,
        granularity=None,
        extra_fields=None,
    ):
        self.calls.append(
            (
                "create_pre_aggregation",
                cube,
                name,
                pre_aggregation_type,
                measures,
                dimensions,
                segments,
                time_dimension,
                granularity,
                extra_fields,
            )
        )
        return {"success": True, "message": "created"}

    def auto_complete(self, schemas, apply, bidirectional_joins):
        self.calls.append(("auto_complete", schemas, apply, bidirectional_joins))
        return {"changed": True}

    def normalize_models(self, apply):
        self.calls.append(("normalize_models", apply))
        return {"changed": True}


class FakePlanner(SemanticEditPlanner):
    def __init__(self) -> None:
        self.context = None

    def plan(self, message, tools, context=None):
        self.context = context
        return LLMPlan(
            tool_calls=[
                ToolCall(
                    name="create_measure",
                    arguments={
                        "cube": "payment",
                        "name": "revenue",
                        "sql": "amount",
                        "type": "sum",
                        "title": "Revenue",
                    },
                )
            ],
            response_hint="Measure planned.",
        )


class MultiRoundPlanner(SemanticEditPlanner):
    def __init__(self) -> None:
        self.contexts = []

    def plan(self, message, tools, context=None):
        self.contexts.append(context)
        if not context.get("observations"):
            return LLMPlan(
                tool_calls=[
                    ToolCall(name="list_dimensions", arguments={"cube": "actor"})
                ],
                response_hint="Checking dimensions.",
            )
        return LLMPlan(
            tool_calls=[
                ToolCall(
                    name="create_dimension",
                    arguments={
                        "cube": "actor",
                        "name": "full_name",
                        "sql": "first_name || ' ' || last_name",
                        "type": "string",
                    },
                )
            ],
            response_hint="Dimension planned.",
        )


class FakeMCPClient(MCPClient):
    def __init__(self) -> None:
        self.calls = []

    def list_tools(self):
        return [{"name": "list_cubes"}, {"name": "create_measure"}]

    def call_tool(self, call):
        self.calls.append(call)
        if call.name == "list_cubes":
            return ToolResult(name=call.name, success=True, data=[{"name": "payment"}])
        if call.name == "list_dimensions":
            return ToolResult(
                name=call.name,
                success=True,
                data=[
                    {"name": "first_name", "sql": "first_name", "type": "string"},
                    {"name": "last_name", "sql": "last_name", "type": "string"},
                ],
            )
        return ToolResult(name=call.name, success=True, data={"success": True})


def test_semantic_edit_mcp_server_maps_create_measure() -> None:
    edit_client = FakeEditClient()
    server = SemanticLayerEditMCPServer(edit_client)

    result = server.call_tool(
        ToolCall(
            name="create_measure",
            arguments={
                "cube": "payment",
                "name": "revenue",
                "sql": "amount",
                "type": "sum",
                "title": "Revenue",
            },
        )
    )

    assert result.success is True
    assert edit_client.calls == [
        (
            "create_measure",
            "payment",
            "revenue",
            "amount",
            "sum",
            {"title": "Revenue"},
        )
    ]


def test_semantic_edit_mcp_server_maps_auto_complete() -> None:
    edit_client = FakeEditClient()
    server = SemanticLayerEditMCPServer(edit_client)

    result = server.call_tool(
        ToolCall(
            name="auto_complete",
            arguments={
                "schemas": ["public"],
                "apply": True,
                "bidirectional_joins": True,
            },
        )
    )

    assert result.success is True
    assert result.data == {"changed": True}
    assert edit_client.calls == [("auto_complete", ["public"], True, True)]


def test_semantic_edit_mcp_server_maps_normalize_models() -> None:
    edit_client = FakeEditClient()
    server = SemanticLayerEditMCPServer(edit_client)

    result = server.call_tool(
        ToolCall(
            name="normalize_models",
            arguments={"apply": True},
        )
    )

    assert result.success is True
    assert result.data == {"changed": True}
    assert edit_client.calls == [("normalize_models", True)]


def test_semantic_edit_mcp_server_maps_create_pre_aggregation() -> None:
    edit_client = FakeEditClient()
    server = SemanticLayerEditMCPServer(edit_client)

    result = server.call_tool(
        ToolCall(
            name="create_pre_aggregation",
            arguments={
                "cube": "payment",
                "name": "pay_by_month",
                "measures": ["payment.count"],
                "time_dimension": "payment.payment_date",
                "granularity": "month",
                "scheduled_refresh": True,
            },
        )
    )

    assert result.success is True
    assert edit_client.calls == [
        (
            "create_pre_aggregation",
            "payment",
            "pay_by_month",
            "rollup",
            ["payment.count"],
            None,
            None,
            "payment.payment_date",
            "month",
            {"scheduled_refresh": True},
        )
    ]


def test_local_llm_agent_plans_then_calls_mcp() -> None:
    planner = FakePlanner()
    mcp_client = FakeMCPClient()
    agent = LocalLLMSemanticEditAgent(planner=planner, mcp_client=mcp_client)

    result = agent.handle("add revenue")

    assert result["success"] is True
    assert planner.context == {"cubes": [{"name": "payment"}]}
    assert [call.name for call in mcp_client.calls] == ["list_cubes", "create_measure"]
    assert result["tool_calls"][0]["name"] == "create_measure"


def test_local_llm_agent_replans_after_read_only_tool() -> None:
    planner = MultiRoundPlanner()
    mcp_client = FakeMCPClient()
    agent = LocalLLMSemanticEditAgent(planner=planner, mcp_client=mcp_client)

    result = agent.handle("add full name to actor")

    assert result["success"] is True
    assert [call.name for call in mcp_client.calls] == [
        "list_cubes",
        "list_dimensions",
        "create_dimension",
    ]
    assert result["tool_calls"][0]["name"] == "list_dimensions"
    assert result["tool_calls"][1]["name"] == "create_dimension"
    assert planner.contexts[1]["observations"][0]["data"][0]["name"] == "first_name"
