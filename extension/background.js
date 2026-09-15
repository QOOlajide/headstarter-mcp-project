/**
 * Service worker: owns every network call to the hub.
 * Content scripts run on the https://meet.google.com origin, so their own
 * requests to http://127.0.0.1 are subject to CORS / private-network checks
 * and are cut short when the Meet tab unloads. The worker holds the latest
 * transcript per tab and posts it from the extension origin instead.
 * https://developer.chrome.com/docs/extensions/develop/concepts/network-requests
 */
const DEFAULT_WEBHOOK = "http://127.0.0.1:8000/webhook/transcript";
const PENDING_KEY = "pendingTranscripts";

async function getWebhookUrl() {
  const cfg = await chrome.storage.sync.get({ webhookUrl: DEFAULT_WEBHOOK });
  return cfg.webhookUrl || DEFAULT_WEBHOOK;
}

async function hubUrl(path) {
  const webhookUrl = await getWebhookUrl();
  return new URL(webhookUrl).origin + path;
}

/** Does the hub recognise the Meet URL of each open Meet tab? Read-only. */
async function checkOpenMeetTabs() {
  const tabs = await chrome.tabs.query({ url: "https://meet.google.com/*" });
  if (!tabs.length) return { ok: true, tabs: [] };

  const url = await hubUrl("/debug/resolve");
  const results = [];
  for (const tab of tabs) {
    let meetUrl;
    try {
      const parsed = new URL(tab.url);
      meetUrl = parsed.origin + parsed.pathname;
    } catch {
      continue;
    }
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meet_url: meetUrl }),
      });
      results.push({ meetUrl, status: res.status, ...(await res.json()) });
    } catch (err) {
      results.push({
        meetUrl,
        error: String(err && err.message ? err.message : err),
      });
    }
  }
  return { ok: true, tabs: results };
}

async function getPending() {
  const stored = await chrome.storage.session.get({ [PENDING_KEY]: {} });
  return stored[PENDING_KEY] || {};
}

async function setPending(pending) {
  await chrome.storage.session.set({ [PENDING_KEY]: pending });
}

async function rememberBuffer(tabId, meetUrl, transcript) {
  if (tabId == null) return;
  const pending = await getPending();
  pending[String(tabId)] = { meetUrl, transcript, updatedAt: Date.now() };
  await setPending(pending);
}

async function forgetBuffer(tabId) {
  if (tabId == null) return;
  const pending = await getPending();
  delete pending[String(tabId)];
  await setPending(pending);
}

async function postTranscript(meetUrl, transcript) {
  const webhookUrl = await getWebhookUrl();
  const body = JSON.stringify({ meet_url: meetUrl, transcript });
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const res = await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      const text = await res.text();
      const result = {
        ok: res.ok,
        status: res.status,
        body: text.slice(0, 300),
        attempt,
      };
      if (res.ok) return result;
      lastError = result;
      if (res.status >= 400 && res.status < 500) return result;
    } catch (err) {
      lastError = {
        ok: false,
        error: String(err && err.message ? err.message : err),
        attempt,
      };
    }
    await new Promise((r) => setTimeout(r, 1000 * attempt));
  }
  return lastError || { ok: false, error: "post failed" };
}

async function flushTab(tabId) {
  const pending = await getPending();
  const entry = pending[String(tabId)];
  if (!entry || !entry.transcript) return { ok: false, error: "nothing buffered" };
  await forgetBuffer(tabId);
  return postTranscript(entry.meetUrl, entry.transcript);
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const tabId = sender && sender.tab ? sender.tab.id : null;

  if (msg?.type === "bufferUpdate") {
    rememberBuffer(tabId, msg.meetUrl, msg.transcript).then(() =>
      sendResponse({ ok: true })
    );
    return true;
  }

  if (msg?.type === "flushNow") {
    forgetBuffer(tabId)
      .then(() => postTranscript(msg.meetUrl, msg.transcript))
      .then((result) => sendResponse(result))
      .catch((err) =>
        sendResponse({ ok: false, error: String(err && err.message ? err.message : err) })
      );
    return true;
  }

  if (msg?.type === "flushAll") {
    getPending()
      .then(async (pending) => {
        const results = [];
        for (const key of Object.keys(pending)) {
          const entry = pending[key];
          if (!entry || !entry.transcript) continue;
          results.push({
            meetUrl: entry.meetUrl,
            result: await postTranscript(entry.meetUrl, entry.transcript),
          });
        }
        await setPending({});
        sendResponse({ ok: true, count: results.length, results });
      })
      .catch((err) =>
        sendResponse({ ok: false, error: String(err && err.message ? err.message : err) })
      );
    return true;
  }

  if (msg?.type === "testPost") {
    // /debug/echo answers 200 without touching Notion, so a pass here means
    // "the POST reached uvicorn" and nothing else.
    hubUrl("/debug/echo")
      .then((url) =>
        fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ probe: true }),
        })
      )
      .then(async (res) => ({
        ok: res.ok,
        status: res.status,
        body: (await res.text()).slice(0, 200),
      }))
      .then(sendResponse)
      .catch((err) =>
        sendResponse({ ok: false, error: String(err && err.message ? err.message : err) })
      );
    return true;
  }

  if (msg?.type === "checkMeetUrl") {
    checkOpenMeetTabs().then(sendResponse);
    return true;
  }

  if (msg?.type === "pendingStatus") {
    getPending().then((pending) => {
      const entries = Object.values(pending).map((e) => ({
        meetUrl: e.meetUrl,
        chars: (e.transcript || "").length,
        updatedAt: e.updatedAt,
      }));
      sendResponse({ ok: true, entries });
    });
    return true;
  }

  return false;
});

// Closing the Meet tab kills the content script mid-send; the worker still has
// the buffer, so it does the POST here.
chrome.tabs.onRemoved.addListener((tabId) => {
  flushTab(tabId);
});
