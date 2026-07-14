LOCAL_CHAT_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MetisOne Local Semantic Chat Client</title>
  <style>
    body { margin: 0; font-family: Inter, system-ui, sans-serif; background: #f6f7f9; color: #18202f; }
    header { padding: 18px 28px; background: #fff; border-bottom: 1px solid #dfe3ea; }
    h1 { margin: 0; font-size: 20px; letter-spacing: 0; }
    main { width: min(980px, calc(100vw - 32px)); margin: 0 auto; padding: 24px 0; }
    .toolbar, .querybar, .composer { display: grid; grid-template-columns: 1fr 180px; gap: 12px; margin-bottom: 16px; }
    .toolbar, .querybar { grid-template-columns: 1fr 220px 160px; }
    input, textarea, button { font: inherit; }
    input, textarea { box-sizing: border-box; width: 100%; border: 1px solid #cdd4df; border-radius: 6px; padding: 10px 12px; background: #fff; }
    button { border: 0; border-radius: 6px; background: #1f6feb; color: #fff; font-weight: 600; cursor: pointer; min-height: 42px; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    .messages { min-height: 420px; display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
    .message { max-width: 82%; padding: 12px 14px; border-radius: 8px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
    .user { align-self: flex-end; background: #1f6feb; color: #fff; }
    .assistant { align-self: flex-start; background: #fff; border: 1px solid #dfe3ea; }
    textarea { resize: vertical; min-height: 72px; }
    @media (max-width: 760px) { .toolbar, .querybar, .composer { grid-template-columns: 1fr; } .message { max-width: 100%; } }
  </style>
</head>
<body>
  <header><h1>MetisOne Local Semantic Chat Client</h1></header>
  <main>
    <div class="toolbar">
      <input id="serviceUrl" />
      <input id="token" type="password" placeholder="API token from SEMANTIC_EDIT_SERVICE_TOKEN" />
      <button id="loadCubes">Load Cubes</button>
    </div>
    <div class="querybar">
      <input id="cubeApiUrl" />
      <input id="cubeToken" type="password" placeholder="Cube API token from CUBE_API_TOKEN" />
      <button id="queryData">Query Data</button>
    </div>
    <section id="messages" class="messages"></section>
    <div class="composer">
      <textarea id="message" placeholder='Try: create measure revenue on payment sql amount type sum title "Revenue"'></textarea>
      <button id="send">Send</button>
    </div>
  </main>
  <script>
    const serviceUrl = document.getElementById("serviceUrl");
    const tokenInput = document.getElementById("token");
    const cubeApiUrl = document.getElementById("cubeApiUrl");
    const cubeTokenInput = document.getElementById("cubeToken");
    const messages = document.getElementById("messages");
    const messageInput = document.getElementById("message");
    const sendButton = document.getElementById("send");
    const loadCubesButton = document.getElementById("loadCubes");
    const queryDataButton = document.getElementById("queryData");

    function addMessage(role, text) {
      const node = document.createElement("div");
      node.className = `message ${role}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    async function postJson(path, body) {
      const response = await fetch(path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
      });
      const text = await response.text();
      let payload;
      try {
        payload = text ? JSON.parse(text) : {};
      } catch (error) {
        payload = { detail: text || String(error) };
      }
      if (!response.ok) throw new Error(payload.detail || JSON.stringify(payload));
      return payload;
    }

    async function loadLocalConfig() {
      try {
        const response = await fetch("/local-config");
        if (!response.ok) return;
        const payload = await response.json();
        serviceUrl.value = payload.service_url || "";
        cubeApiUrl.value = payload.cube_api_url || "";
        addMessage("assistant", `Config loaded from .env. Agent mode: ${payload.agent_mode}. OpenAI key: ${payload.has_openai_api_key ? "set" : "not set"}.`);
      } catch (error) {
        addMessage("assistant", `Could not load local config: ${String(error)}`);
      }
    }

    async function sendChat() {
      const text = messageInput.value.trim();
      if (!text) return;
      addMessage("user", text);
      messageInput.value = "";
      sendButton.disabled = true;
      try {
        const payload = await postJson("/local-chat", {
          service_url: serviceUrl.value,
          api_token: tokenInput.value,
          message: text
        });
        const details = payload.tool_calls
          ? {
              tool_calls: payload.tool_calls,
              tool_results: payload.tool_results,
              context: payload.context
            }
          : payload;
        addMessage("assistant", `${payload.message}\\n\\n${JSON.stringify(details, null, 2)}`);
      } catch (error) {
        addMessage("assistant", String(error));
      } finally {
        sendButton.disabled = false;
      }
    }

    async function loadCubes() {
      try {
        const payload = await postJson("/local-cubes", {
          service_url: serviceUrl.value,
          api_token: tokenInput.value
        });
        addMessage("assistant", `Available cubes:\\n${JSON.stringify(payload.cubes, null, 2)}`);
      } catch (error) {
        addMessage("assistant", String(error));
      }
    }

    async function queryData() {
      const text = messageInput.value.trim();
      if (!text) return;
      addMessage("user", text);
      messageInput.value = "";
      queryDataButton.disabled = true;
      try {
        const payload = await postJson("/local-query", {
          cube_api_url: cubeApiUrl.value,
          cube_api_token: cubeTokenInput.value || null,
          message: text,
          limit: 100
        });
        addMessage("assistant", `${payload.message}\\n\\n${JSON.stringify({
          cube_query: payload.plan.cube_query,
          rows: payload.result.rows,
          row_count: payload.result.row_count,
          annotation: payload.result.annotation
        }, null, 2)}`);
      } catch (error) {
        addMessage("assistant", String(error));
      } finally {
        queryDataButton.disabled = false;
      }
    }

    sendButton.addEventListener("click", sendChat);
    loadCubesButton.addEventListener("click", loadCubes);
    queryDataButton.addEventListener("click", queryData);
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) sendChat();
    });
    loadLocalConfig();
    addMessage("assistant", "This UI runs locally. Runtime configuration is loaded from .env. The local agent plans with OpenAI when OPENAI_API_KEY is set, calls MCP tools, then updates Cube YAML through the remote Ubuntu edit service.");
  </script>
</body>
</html>
"""
