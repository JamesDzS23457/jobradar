/* Bridge between the local JobRadar web app and the extension service worker. */
(() => {
  if (window.__jobradarWebBridgeLoaded) return;
  window.__jobradarWebBridgeLoaded = true;

  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    const data = event.data;
    if (!data || data.source !== "jobradar-web") return;

    if (data.type === "START_AUTO_RUN") {
      chrome.runtime.sendMessage({ type: "JOBRADAR_START_QUEUE", runId: data.runId }, () => {
        void chrome.runtime.lastError;
      });
    }
    if (data.type === "SESSION_READY") {
      chrome.runtime.sendMessage({ type: "JOBRADAR_SESSION_READY", sessionId: data.sessionId }, () => {
        void chrome.runtime.lastError;
      });
    }
  });
})();
