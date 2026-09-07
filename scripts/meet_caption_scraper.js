/**
 * Google Meet Live Caption scraper (requirements §4.3 / ADR 003).
 * Inject via userscript/extension on meet.google.com with Live Captions enabled.
 * On leave, beacons transcript to local webhook hub.
 */
(function () {
  let transcriptBuffer = [];
  let lastSpokenText = "";

  const observer = new MutationObserver(() => {
    const captionContainer =
      document.querySelector('div[jscontroller="D1tHje"]') ||
      document.querySelector(".a4cQT");
    if (!captionContainer) return;

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

    navigator.sendBeacon(
      "http://127.0.0.1:8000/webhook/transcript",
      payload
    );
  });
})();
