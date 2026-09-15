const DEFAULT_WEBHOOK = "http://127.0.0.1:8000/webhook/transcript";

const input = document.getElementById("webhookUrl");
const status = document.getElementById("status");

chrome.storage.sync.get({ webhookUrl: DEFAULT_WEBHOOK }, (cfg) => {
  input.value = cfg.webhookUrl || DEFAULT_WEBHOOK;
});

document.getElementById("save").addEventListener("click", () => {
  const webhookUrl = (input.value || "").trim() || DEFAULT_WEBHOOK;
  chrome.storage.sync.set({ webhookUrl }, () => {
    status.textContent = "Saved. Reload any open Meet tabs to pick this up.";
  });
});

document.getElementById("testPost").addEventListener("click", () => {
  status.textContent = "Posting a dummy transcript through the extension worker…";
  chrome.runtime.sendMessage({ type: "testPost" }, (resp) => {
    const err = chrome.runtime.lastError;
    if (err) {
      status.textContent = "Worker unreachable: " + err.message;
      return;
    }
    if (resp && resp.status === 404) {
      status.textContent =
        "POST path works — hub replied 404 for the dummy meeting URL. " +
        "Real captions will be accepted.";
      return;
    }
    if (resp && resp.ok) {
      status.textContent = "POST path works — hub accepted it: " + resp.body;
      return;
    }
    status.textContent =
      "POST failed: " +
      (resp && resp.status ? "HTTP " + resp.status + " " + resp.body : (resp && resp.error) || "unknown") +
      ". Is uvicorn running on that host/port?";
  });
});

document.getElementById("sendNow").addEventListener("click", () => {
  status.textContent = "Asking the extension worker to post buffered captions…";
  chrome.runtime.sendMessage({ type: "flushAll" }, (resp) => {
    const err = chrome.runtime.lastError;
    if (err) {
      status.textContent = "Worker unreachable: " + err.message;
      return;
    }
    if (!resp || !resp.ok) {
      status.textContent = "Send failed: " + ((resp && resp.error) || "unknown");
      return;
    }
    if (!resp.count) {
      status.textContent =
        "Nothing buffered. Open the Meet tab with Live Captions on first.";
      return;
    }
    status.textContent =
      "Posted " + resp.count + " transcript(s): " + JSON.stringify(resp.results);
  });
});

document.getElementById("testHub").addEventListener("click", async () => {
  const webhookUrl = (input.value || "").trim() || DEFAULT_WEBHOOK;
  let origin;
  try {
    origin = new URL(webhookUrl).origin;
  } catch {
    status.textContent = "Invalid webhook URL.";
    return;
  }
  status.textContent = "Checking " + origin + "/health …";
  try {
    const res = await fetch(origin + "/health", { cache: "no-store" });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      status.textContent = "Hub responded with HTTP " + res.status;
      return;
    }
    status.textContent =
      "Hub OK: " + JSON.stringify(body) + " — extension can reach the server.";
  } catch (err) {
    status.textContent =
      "Hub not reachable (" +
      (err && err.message ? err.message : "fetch failed") +
      "). Start uvicorn on that host/port.";
  }
});
