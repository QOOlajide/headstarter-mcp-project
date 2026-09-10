/**
 * Google Meet Live Caption content script.
 * Buffers captions while Live Captions are on; on leave, beacons to the hub.
 */
(function () {
  const DEFAULT_WEBHOOK = "http://127.0.0.1:8000/webhook/transcript";
  let transcriptBuffer = [];
  let lastSpokenText = "";
  let webhookUrl = DEFAULT_WEBHOOK;
  let reminded = false;

  chrome.storage.sync.get({ webhookUrl: DEFAULT_WEBHOOK }, (cfg) => {
    if (cfg && cfg.webhookUrl) webhookUrl = cfg.webhookUrl;
  });

  function showCaptionHint() {
    if (reminded) return;
    reminded = true;
    const el = document.createElement("div");
    el.textContent =
      "Meeting Hub: turn on Live Captions so this extension can capture the transcript.";
    el.style.cssText =
      "position:fixed;z-index:999999;bottom:16px;left:16px;max-width:360px;" +
      "padding:10px 12px;background:#111;color:#fff;font:13px/1.4 sans-serif;" +
      "border-radius:8px;opacity:0.92;";
    document.documentElement.appendChild(el);
    setTimeout(() => el.remove(), 12000);
  }

  const observer = new MutationObserver(() => {
    const captionContainer =
      document.querySelector('div[jscontroller="D1tHje"]') ||
      document.querySelector(".a4cQT");
    if (!captionContainer) {
      if (transcriptBuffer.length === 0) showCaptionHint();
      return;
    }

    const speakerEl =
      captionContainer.querySelector(".zs7s8d") ||
      captionContainer.querySelector(".jxFHg");
    const textEl =
      captionContainer.querySelector(".iTTPOb") ||
      captionContainer.querySelector(".CNhiyc");

    const speaker = speakerEl ? speakerEl.innerText.trim() : "Unknown";
    const text = textEl ? textEl.innerText.trim() : "";

    if (text && text !== lastSpokenText) {
      lastSpokenText = text;
      transcriptBuffer.push({
        speaker,
        text,
        timestamp: new Date().toISOString(),
      });
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  window.addEventListener("beforeunload", () => {
    if (transcriptBuffer.length === 0) return;

    const payload = JSON.stringify({
      meet_url: window.location.origin + window.location.pathname,
      transcript: transcriptBuffer
        .map((e) => `[${e.timestamp}] ${e.speaker}: ${e.text}`)
        .join("\n"),
    });

    navigator.sendBeacon(webhookUrl, payload);
  });
})();
