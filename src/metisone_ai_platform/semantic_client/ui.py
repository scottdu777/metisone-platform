LOCAL_CHAT_UI_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MetisOne Semantic Client</title>
  <style>
    :root { color-scheme: light; font-family: Inter, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4f6f9; color: #172033; }
    .app { width: min(880px, calc(100vw - 28px)); margin: 28px auto; }
    header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
    h1 { margin: 0; font-size: 22px; }
    #status { color: #687386; font-size: 13px; }
    .panel { overflow: hidden; background: #fff; border: 1px solid #dfe4ec; border-radius: 14px; box-shadow: 0 8px 30px rgba(23, 32, 51, .06); }
    .modes { display: flex; gap: 8px; padding: 14px 16px; border-bottom: 1px solid #e7ebf1; }
    .mode { padding: 8px 14px; border: 0; border-radius: 8px; background: #eef2f7; color: #455166; cursor: pointer; }
    .mode.active { background: #1f6feb; color: #fff; }
    #messages { min-height: 430px; max-height: 60vh; overflow-y: auto; padding: 22px; display: flex; flex-direction: column; gap: 12px; }
    .message { max-width: 82%; padding: 11px 14px; border-radius: 12px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
    .user { align-self: flex-end; background: #1f6feb; color: #fff; }
    .assistant { align-self: flex-start; background: #f2f4f8; }
    .composer { display: grid; grid-template-columns: 1fr 92px; gap: 10px; padding: 16px; border-top: 1px solid #e7ebf1; }
    textarea { width: 100%; min-height: 72px; resize: vertical; padding: 11px 12px; border: 1px solid #ccd4df; border-radius: 9px; font: inherit; }
    #send { border: 0; border-radius: 9px; background: #1f6feb; color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
    #send:disabled { opacity: .55; cursor: wait; }
    @media (max-width: 640px) { .app { margin: 12px auto; } .message { max-width: 94%; } .composer { grid-template-columns: 1fr; } #send { min-height: 44px; } }
  </style>
</head>
<body>
  <main class="app">
    <header><h1>MetisOne Semantic Client</h1><span id="status">Loading config...</span></header>
    <section class="panel">
      <div class="modes">
        <button class="mode active" data-mode="query">Query Data</button>
        <button class="mode" data-mode="edit">Edit Model</button>
      </div>
      <div id="messages"></div>
      <div class="composer">
        <textarea id="message" placeholder="Example: How many Action films are there?"></textarea>
        <button id="send">Send</button>
      </div>
    </section>
  </main>
  <script>
    const messages = document.getElementById("messages");
    const input = document.getElementById("message");
    const send = document.getElementById("send");
    const status = document.getElementById("status");
    let mode = "query";

    function addMessage(role, text) {
      const node = document.createElement("div");
      node.className = `message ${role}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    async function postMessage() {
      const message = input.value.trim();
      if (!message) return;
      addMessage("user", message);
      input.value = "";
      send.disabled = true;
      try {
        const response = await fetch("/local-chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({message, mode})
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Request failed.");
        addMessage("assistant", payload.message || "Operation completed.");
      } catch (error) {
        addMessage("assistant", error.message || String(error));
      } finally {
        send.disabled = false;
        input.focus();
      }
    }

    document.querySelectorAll(".mode").forEach((button) => {
      button.addEventListener("click", () => {
        mode = button.dataset.mode;
        document.querySelectorAll(".mode").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        input.placeholder = mode === "query"
          ? "Example: How many Action films are there?"
          : "Example: Add a revenue sum measure to payment.";
        addMessage("assistant", mode === "query" ? "Switched to data query mode." : "Switched to semantic model edit mode.");
      });
    });

    send.addEventListener("click", postMessage);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) postMessage();
    });
    fetch("/local-config")
      .then((response) => response.json())
      .then(() => { status.textContent = "Config loaded"; })
      .catch(() => { status.textContent = "Failed to load config"; });
    addMessage("assistant", "Hello. You can query data or switch to Edit Model to update Semantic YAML.");
  </script>
</body>
</html>
"""
