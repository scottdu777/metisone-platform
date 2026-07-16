CHAT_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MetisOne Semantic Layer Assistant</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #18202f;
    }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
    }
    header {
      padding: 18px 28px;
      border-bottom: 1px solid #dfe3ea;
      background: #ffffff;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 650;
      letter-spacing: 0;
    }
    main {
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0;
    }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr 180px;
      gap: 12px;
      margin-bottom: 16px;
    }
    input, textarea, button {
      font: inherit;
    }
    input, textarea {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #cdd4df;
      border-radius: 6px;
      padding: 10px 12px;
      background: #ffffff;
      color: #18202f;
    }
    button {
      border: 0;
      border-radius: 6px;
      background: #1f6feb;
      color: #ffffff;
      font-weight: 600;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .messages {
      min-height: 420px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 16px;
    }
    .message {
      max-width: 82%;
      padding: 12px 14px;
      border-radius: 8px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .user {
      align-self: flex-end;
      background: #1f6feb;
      color: #ffffff;
    }
    .assistant {
      align-self: flex-start;
      background: #ffffff;
      border: 1px solid #dfe3ea;
    }
    .composer {
      display: grid;
      grid-template-columns: 1fr 120px;
      gap: 12px;
    }
    textarea {
      resize: vertical;
      min-height: 72px;
    }
    code {
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 0.92em;
    }
    @media (max-width: 700px) {
      .toolbar, .composer {
        grid-template-columns: 1fr;
      }
      .message {
        max-width: 100%;
      }
      button {
        min-height: 42px;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>MetisOne Semantic Layer Assistant</h1>
  </header>
  <main>
    <div class="toolbar">
      <input id="token" type="password" placeholder="API token from METISONE_SEMANTIC_EDIT_TOKEN" />
      <button id="loadCubes">Load Cubes</button>
    </div>
    <section id="messages" class="messages"></section>
    <div class="composer">
      <textarea id="message" placeholder='Try: create measure revenue on payment sql amount type sum title "Revenue"'></textarea>
      <button id="send">Send</button>
    </div>
  </main>
  <script>
    const tokenInput = document.getElementById("token");
    const messages = document.getElementById("messages");
    const messageInput = document.getElementById("message");
    const sendButton = document.getElementById("send");
    const loadCubesButton = document.getElementById("loadCubes");

    function addMessage(role, text) {
      const node = document.createElement("div");
      node.className = `message ${role}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    function authHeaders() {
      return {
        "Authorization": `Bearer ${tokenInput.value}`,
        "Content-Type": "application/json"
      };
    }

    async function sendChat() {
      const text = messageInput.value.trim();
      if (!text) return;
      addMessage("user", text);
      messageInput.value = "";
      sendButton.disabled = true;
      try {
        const response = await fetch("/v1/chat", {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ message: text })
        });
        const payload = await response.json();
        if (!response.ok) {
          addMessage("assistant", payload.detail || "Request failed");
          return;
        }
        addMessage("assistant", `${payload.message}\\n\\n${JSON.stringify(payload.command, null, 2)}`);
      } catch (error) {
        addMessage("assistant", String(error));
      } finally {
        sendButton.disabled = false;
      }
    }

    async function loadCubes() {
      try {
        const response = await fetch("/v1/cubes", { headers: authHeaders() });
        const payload = await response.json();
        if (!response.ok) {
          addMessage("assistant", payload.detail || "Could not load cubes");
          return;
        }
        addMessage("assistant", `Available cubes:\\n${JSON.stringify(payload, null, 2)}`);
      } catch (error) {
        addMessage("assistant", String(error));
      }
    }

    sendButton.addEventListener("click", sendChat);
    loadCubesButton.addEventListener("click", loadCubes);
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        sendChat();
      }
    });

    addMessage("assistant", "Hi. I can update Cube YAML using structured natural language. Start by entering your API token and loading cubes.");
  </script>
</body>
</html>
"""
