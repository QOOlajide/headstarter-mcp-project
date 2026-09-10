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
