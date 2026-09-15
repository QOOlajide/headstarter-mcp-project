/**
 * Google Meet Live Caption content script.
 * Buffers captions while Live Captions are on and mirrors the buffer to the
 * service worker, which owns the POST to the hub (see background.js).
 */
(function () {
  const DEFAULT_WEBHOOK = "http://127.0.0.1:8000/webhook/transcript";
  let transcriptBuffer = [];
  let lastSpokenText = "";
  let webhookUrl = DEFAULT_WEBHOOK;
  let reminded = false;
  let statusEl = null;
  let sent = false;
  let mirroredLen = 0;

  chrome.storage.sync.get({ webhookUrl: DEFAULT_WEBHOOK }, (cfg) => {
    if (cfg && cfg.webhookUrl) webhookUrl = cfg.webhookUrl;
    pingHub();
  });

  function ensureStatusPill() {
    if (statusEl && document.documentElement.contains(statusEl)) return statusEl;
    statusEl = document.createElement("div");
    statusEl.id = "meeting-hub-status";
    statusEl.style.cssText =
      "position:fixed;z-index:999999;top:12px;right:12px;" +
      "padding:8px 10px;background:#111;color:#fff;font:12px/1.35 sans-serif;" +
      "border-radius:8px;opacity:0.9;max-width:280px;pointer-events:none;";
    document.documentElement.appendChild(statusEl);
    return statusEl;
  }

  function setStatus(text, ok) {
    const el = ensureStatusPill();
    el.textContent = text;
    el.style.background = ok ? "#0b3d2e" : "#4a1c1c";
  }

  function hubOrigin() {
    try {
      return new URL(webhookUrl).origin;
    } catch {
      return "http://127.0.0.1:8000";
    }
  }

  function pingHub() {
    setStatus("Meeting Hub: extension active — checking hub…", true);
    fetch(hubOrigin() + "/health", { method: "GET", cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("bad status");
        setStatus("Meeting Hub: extension + hub OK", true);
      })
      .catch(() => {
        setStatus(
          "Meeting Hub: extension active, but hub not reachable at " +
            hubOrigin(),
          false
        );
      });
  }

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

  function findCaptionRegion() {
    return (
      document.querySelector(
        '[role="region"][aria-label*="aption" i], [role="region"][aria-label*="ubtitle" i]'
      ) ||
      document.querySelector('[jsname="tgaKEf"]') ||
      document.querySelector('div[jscontroller="D1tHje"]') ||
      document.querySelector(".a4cQT") ||
      null
    );
  }

  function extractSpeaker(root) {
    const el =
      root.querySelector("span.NWpY1d") ||
      root.querySelector(".NWpY1d") ||
      root.querySelector(".KcIKyf") ||
      root.querySelector(".jxFHg") ||
      root.querySelector(".zs7s8d");
    return el ? el.innerText.trim() : "Unknown";
  }

  function pushCaption(speaker, text) {
    if (!text || text === lastSpokenText) return;
    lastSpokenText = text;
    transcriptBuffer.push({
      speaker: speaker || "Unknown",
      text,
      timestamp: new Date().toISOString(),
    });
    setStatus(
      "Meeting Hub: capturing captions (" + transcriptBuffer.length + ")",
      true
    );
  }

  function scanCaptions() {
    const region = findCaptionRegion() || document.body;

    const textNodes = region.querySelectorAll(".ygicle.VbkSUe, .ygicle");
    if (textNodes.length) {
      textNodes.forEach((textEl) => {
        const unit = textEl.parentElement || textEl;
        const speaker = extractSpeaker(unit) || extractSpeaker(region);
        pushCaption(speaker, (textEl.innerText || "").trim());
      });
      return;
    }

    if (region === document.body && transcriptBuffer.length === 0) {
      showCaptionHint();
    }
  }

  function meetUrl() {
    return window.location.origin + window.location.pathname;
  }

  function serializeTranscript() {
    return transcriptBuffer
      .map((e) => `[${e.timestamp}] ${e.speaker}: ${e.text}`)
      .join("\n");
  }

  function mirrorBuffer() {
    if (sent || transcriptBuffer.length === 0) return;
    if (transcriptBuffer.length === mirroredLen) return;
    mirroredLen = transcriptBuffer.length;
    try {
      chrome.runtime.sendMessage(
        {
          type: "bufferUpdate",
          meetUrl: meetUrl(),
          transcript: serializeTranscript(),
        },
        () => void chrome.runtime.lastError
      );
    } catch (_) {}
  }

  // Only the post-call screen — never the bare word "rejoin" (Meet shows that
  // during active calls and used to spam flush/debug requests).
  function looksLikeLeftMeeting() {
    const t = (document.body && document.body.innerText) || "";
    return /you('ve| have)? left the (meeting|call)|return to home screen/i.test(
      t
    );
  }

  function flushTranscript() {
    if (sent || transcriptBuffer.length === 0) return;
    sent = true;

    const transcript = serializeTranscript();
    try {
      chrome.runtime.sendMessage(
        { type: "flushNow", meetUrl: meetUrl(), transcript },
        (resp) => {
          if (chrome.runtime.lastError || !(resp && resp.ok)) {
            setStatus("Meeting Hub: send failed — is the hub running?", false);
            return;
          }
          setStatus(
            "Meeting Hub: transcript sent (" + transcriptBuffer.length + ")",
            true
          );
        }
      );
    } catch (_) {
      sent = false;
    }
  }

  function isLeaveControl(el) {
    if (!el || !el.closest) return false;
    const btn = el.closest("button, [role='button'], div[data-tooltip]");
    if (!btn) return false;
    const label = (
      (btn.getAttribute("aria-label") || "") +
      " " +
      (btn.getAttribute("data-tooltip") || "") +
      " " +
      (btn.innerText || "")
    ).toLowerCase();
    return /leave call|leave meeting|end call|end meeting|hang up|just leave/.test(
      label
    );
  }

  const observer = new MutationObserver(() => {
    scanCaptions();
    if (looksLikeLeftMeeting()) flushTranscript();
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  });
  setInterval(scanCaptions, 1500);
  setInterval(mirrorBuffer, 3000);
  setInterval(() => {
    if (looksLikeLeftMeeting()) flushTranscript();
  }, 2000);

  document.addEventListener(
    "click",
    (ev) => {
      if (isLeaveControl(ev.target)) flushTranscript();
    },
    true
  );

  window.addEventListener("pagehide", () => flushTranscript());
  window.addEventListener("beforeunload", () => flushTranscript());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") mirrorBuffer();
  });

  setStatus("Meeting Hub: extension active", true);
})();
