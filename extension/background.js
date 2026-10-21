/*
 * JobRadar Assistant — background service worker.
 *
 * This extension is intentionally user-assisted. It uses the browser's real
 * session, never stores portal passwords and never implements CAPTCHA, 2FA or
 * anti-detection bypasses.
 */

const DEFAULT_API_BASE = "http://127.0.0.1:8000";
let queueActive = false;
let processing = false;
let activeTabId = null;
let activeSessionId = null;
let activeTimer = null;
let pendingSubmit = null;

async function apiBase() {
  const stored = await chrome.storage.local.get({ apiBase: DEFAULT_API_BASE });
  return String(stored.apiBase || DEFAULT_API_BASE).replace(/\/+$/, "");
}

async function api(path, options = {}) {
  const response = await fetch(`${await apiBase()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `JobRadar API ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch {
      // Keep the HTTP status.
    }
    throw new Error(message);
  }
  return response.json();
}

function addSessionHash(url, sessionId, auto) {
  if (!url) return url;
  try {
    const parsed = new URL(url);
    parsed.hash = `jobradar-session=${sessionId}${auto ? "&jobradar-auto=1" : ""}`;
    return parsed.toString();
  } catch {
    return `${url}${url.includes("#") ? "" : "#"}jobradar-session=${sessionId}${auto ? "&jobradar-auto=1" : ""}`;
  }
}

async function reportStatus(sessionId, status, message) {
  return api(`/api/extension/sessions/${sessionId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, message: String(message || "").slice(0, 1800) }),
  });
}

async function injectContent(tabId) {
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  } catch (error) {
    console.warn("JobRadar could not inject content script", error);
  }
}

function clearPendingSubmit() {
  if (pendingSubmit?.timer) clearTimeout(pendingSubmit.timer);
  pendingSubmit = null;
}

function finishActiveSession() {
  if (activeTimer) clearTimeout(activeTimer);
  activeTimer = null;
  clearPendingSubmit();
  activeTabId = null;
  activeSessionId = null;
  processing = false;
  if (queueActive) {
    setTimeout(() => processNext(), 1800);
  }
}

function watchPendingSubmit(sessionId, tabId, beforeUrl) {
  clearPendingSubmit();
  pendingSubmit = {
    sessionId,
    tabId,
    beforeUrl,
    timer: setTimeout(async () => {
      if (!pendingSubmit || pendingSubmit.sessionId !== sessionId) return;
      const current = await chrome.tabs.get(tabId).catch(() => null);
      const changed = Boolean(current?.url && current.url !== beforeUrl);
      try {
        if (changed) {
          await reportStatus(
            sessionId,
            "submitted",
            "El portal navegó a una página de confirmación. Revisa el correo del portal.",
          );
        } else {
          await reportStatus(
            sessionId,
            "manual",
            "No pudimos confirmar el envío automático. Revisa la pestaña y completa el envío manualmente.",
          );
        }
      } catch (error) {
        console.warn("JobRadar submit confirmation failed", error);
      }
      if (Number(sessionId) === Number(activeSessionId)) {
        finishActiveSession();
      } else {
        clearPendingSubmit();
      }
    }, 9000),
  };
}

function watchdog(sessionId) {
  if (activeTimer) clearTimeout(activeTimer);
  activeTimer = setTimeout(async () => {
    if (activeSessionId !== sessionId) return;
    try {
      await reportStatus(
        sessionId,
        "manual",
        "El portal no respondió al asistente. Revisa la pestaña y completa los pasos humanos.",
      );
    } catch (error) {
      console.warn("JobRadar watchdog report failed", error);
    }
    finishActiveSession();
  }, 180000);
}

async function openQueuedSession(session) {
  const url = addSessionHash(session.job?.url || "", session.id, true);
  if (!url) {
    await reportStatus(session.id, "manual", "La vacante no tiene enlace de postulación.");
    processing = false;
    setTimeout(() => processNext(), 1000);
    return;
  }
  activeSessionId = session.id;
  const tab = await chrome.tabs.create({ url, active: true });
  activeTabId = tab.id;
  watchdog(session.id);
  setTimeout(() => injectContent(tab.id), 1800);
}

async function processNext() {
  if (processing) return;
  processing = true;
  try {
    const data = await api("/api/extension/next");
    if (!data.session) {
      processing = false;
      queueActive = false;
      return;
    }
    await openQueuedSession(data.session);
  } catch (error) {
    console.warn("JobRadar queue error", error);
    processing = false;
    queueActive = false;
  }
}

async function startQueue() {
  queueActive = true;
  if (!processing) await processNext();
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(index, index + chunk));
  }
  return btoa(binary);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      switch (message?.type) {
        case "JOBRADAR_PING":
          sendResponse({ ok: true, version: chrome.runtime.getManifest().version });
          return;
        case "JOBRADAR_START_QUEUE":
          await startQueue();
          sendResponse({ ok: true });
          return;
        case "JOBRADAR_SESSION_READY":
          sendResponse({ ok: true });
          return;
        case "JOBRADAR_GET_SESSION": {
          const data = await api(`/api/application-sessions/${message.sessionId}`);
          sendResponse({ ok: true, session: data.session });
          return;
        }
        case "JOBRADAR_DRAFT_ANSWERS": {
          const data = await api("/api/applications/draft-answers", {
            method: "POST",
            body: JSON.stringify({ job_id: message.jobId, questions: message.questions || [] }),
          });
          sendResponse({ ok: true, answers: data.answers || [] });
          return;
        }
        case "JOBRADAR_CLASSIFY": {
          const data = await api(`/api/portals/classify?url=${encodeURIComponent(message.url || "")}`);
          sendResponse({ ok: true, portal: data.portal });
          return;
        }
        case "JOBRADAR_FETCH_CV": {
          const response = await fetch(`${await apiBase()}${message.url}`);
          if (!response.ok) throw new Error("No se pudo descargar el CV.");
          const buffer = await response.arrayBuffer();
          sendResponse({
            ok: true,
            base64: arrayBufferToBase64(buffer),
            mime: response.headers.get("content-type") || "application/pdf",
            name: message.name || "cv.pdf",
          });
          return;
        }
        case "JOBRADAR_SUBMIT_INTENT": {
          if (sender.tab?.id) {
            watchPendingSubmit(Number(message.sessionId), sender.tab.id, String(message.url || ""));
          }
          sendResponse({ ok: true });
          return;
        }
        case "JOBRADAR_REPORT": {
          await reportStatus(message.sessionId, message.status, message.message);
          if (Number(message.sessionId) === Number(activeSessionId)) {
            finishActiveSession();
          } else if (pendingSubmit?.sessionId === Number(message.sessionId)) {
            clearPendingSubmit();
          }
          sendResponse({ ok: true });
          return;
        }
        default:
          sendResponse({ ok: false, error: "Mensaje desconocido." });
      }
    } catch (error) {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
    }
  })();
  return true;
});

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;
  await injectContent(tab.id);
  try {
    await chrome.tabs.sendMessage(tab.id, { type: "JOBRADAR_OPEN_PANEL" });
  } catch {
    // The page may not allow content scripts.
  }
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
  if (pendingSubmit && tabId === pendingSubmit.tabId) {
    if (changeInfo.status !== "complete") return;
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    if (tab?.url && tab.url !== pendingSubmit.beforeUrl) {
      const sessionId = pendingSubmit.sessionId;
      try {
        await reportStatus(
          sessionId,
          "submitted",
          "El portal navegó a una página de confirmación después del envío. Revisa el correo de confirmación.",
        );
      } catch (error) {
        console.warn("JobRadar submit confirmation failed", error);
      }
      if (Number(sessionId) === Number(activeSessionId)) {
        finishActiveSession();
      } else {
        clearPendingSubmit();
      }
      return;
    }
    return;
  }
  if (changeInfo.status !== "complete" || tabId !== activeTabId || !activeSessionId) return;
  await injectContent(tabId);
  setTimeout(async () => {
    try {
      await chrome.tabs.sendMessage(tabId, {
        type: "JOBRADAR_RESUME",
        sessionId: activeSessionId,
      });
    } catch {
      // Content script may still be loading.
    }
  }, 900);
});

chrome.runtime.onInstalled.addListener(async () => {
  const stored = await chrome.storage.local.get({ apiBase: DEFAULT_API_BASE });
  if (!stored.apiBase) {
    await chrome.storage.local.set({ apiBase: DEFAULT_API_BASE });
  }
});
