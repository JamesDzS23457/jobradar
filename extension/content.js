/*
 * JobRadar Assistant — page assistant.
 *
 * Safe behavior:
 *  - fills fields with data prepared by JobRadar;
 *  - uploads the selected CV;
 *  - asks JobRadar for drafted answers to custom questions;
 *  - never stores passwords, bypasses CAPTCHA/2FA or hides automation.
 *  - assisted mode leaves the final submit click to the user.
 */

(() => {
  if (window.__jobradarAssistantLoaded) return;
  window.__jobradarAssistantLoaded = true;

  const APP_HINT = "Abre la vacante desde JobRadar y pulsa «Preparar postulación».";
  const SUBMIT_TEXTS = [
    "submit application",
    "submit my application",
    "enviar postulación",
    "enviar postulacion",
    "enviar solicitud",
    "enviar candidatura",
    "submit",
    "enviar",
    "finalizar postulación",
    "finalizar postulacion",
  ];
  const NEXT_TEXTS = ["next", "continue", "continuar", "siguiente", "save and continue", "guardar y continuar"];
  const QUESTION_HINT = /(why|cover|motiv|tell us|describe|explain|salary|pretensi|authoriz|sponsor|visa|disponib|availability|experiencia|experience|proyecto|project|logro|achievement|pregunta|question)/i;

  const state = {
    root: null,
    shadow: null,
    session: null,
    portal: null,
    auto: false,
    busy: false,
    reported: false,
    message: "",
    filled: 0,
    missing: 0,
    answers: {},
    initializedSessionId: null,
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function normalize(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function send(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!response?.ok) {
          reject(new Error(response?.error || "No se pudo contactar a JobRadar."));
          return;
        }
        resolve(response);
      });
    });
  }

  function ensureRoot() {
    if (state.root && document.documentElement.contains(state.root)) return;
    const host = document.createElement("div");
    host.id = "jobradar-assistant-root";
    host.style.all = "initial";
    host.style.position = "fixed";
    host.style.zIndex = "2147483647";
    host.style.right = "18px";
    host.style.bottom = "18px";
    const shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = `
      :host { all: initial; }
      * { box-sizing: border-box; }
      .panel {
        width: 360px; max-width: calc(100vw - 24px); border-radius: 18px;
        background: #0b1220; color: #e6eefb; border: 1px solid #223047;
        box-shadow: 0 24px 60px rgba(0,0,0,.45); overflow: hidden;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      }
      header { display:flex; align-items:center; justify-content:space-between; padding:12px 14px; background:linear-gradient(135deg,#10251d,#0b1220); border-bottom:1px solid #1d2a3c; }
      .brand { display:flex; align-items:center; gap:8px; font-weight:700; font-size:13px; }
      .dot { width:8px; height:8px; border-radius:999px; background:#34d399; box-shadow:0 0 10px #34d399; }
      .close { background:transparent; border:0; color:#94a3b8; font-size:18px; cursor:pointer; line-height:1; }
      .body { padding:14px; display:grid; gap:10px; }
      .job { font-size:12px; font-weight:700; color:#fff; line-height:1.35; }
      .meta { font-size:10px; color:#94a3b8; line-height:1.5; }
      .message { font-size:11px; line-height:1.5; color:#cbd5e1; background:#0f172a; border:1px solid #1d2a3c; border-radius:10px; padding:9px 10px; }
      .warn { color:#fcd34d; border-color:rgba(251,191,36,.25); background:rgba(251,191,36,.07); }
      .ok { color:#86efac; border-color:rgba(52,211,153,.25); background:rgba(52,211,153,.07); }
      .row { display:flex; gap:8px; }
      button.action { flex:1; border:1px solid #2b3b53; border-radius:10px; background:#162235; color:#e2e8f0; padding:9px 10px; font-size:11px; font-weight:650; cursor:pointer; }
      button.action.primary { background:#34d399; border-color:#34d399; color:#04140f; }
      button.action:disabled { opacity:.5; cursor:not-allowed; }
      footer { padding:9px 14px 12px; border-top:1px solid #1d2a3c; font-size:9px; line-height:1.45; color:#64748b; }
      a { color:#6ee7b7; }
    `;
    shadow.appendChild(style);
    const container = document.createElement("div");
    container.className = "panel";
    shadow.appendChild(container);
    document.documentElement.appendChild(host);
    state.root = host;
    state.shadow = shadow;
  }

  function statusClass() {
    if (state.reported) return "message ok";
    if (state.missing > 0 || /manual|captcha|login|t[eé]rminos/i.test(state.message)) return "message warn";
    return "message";
  }

  function render() {
    if (!state.shadow) return;
    const panel = state.shadow.querySelector(".panel");
    if (!panel) return;
    const session = state.session;
    const job = session?.job;
    const portal = state.portal || session?.portal;
    const title = job ? `${job.title} — ${job.company}` : "Asistente JobRadar";
    const meta = portal
      ? `${portal.label} · ${portal.mode === "auto_submit" ? "auto-envío permitido" : portal.mode === "assisted" ? "asistido" : "solo manual"}`
      : "";
    panel.innerHTML = `
      <header>
        <div class="brand"><span class="dot"></span> JobRadar Assistant</div>
        <button class="close" data-close aria-label="Cerrar">×</button>
      </header>
      <div class="body">
        <div>
          <div class="job">${escapeHtml(title)}</div>
          <div class="meta">${escapeHtml(meta)}</div>
        </div>
        <div class="${statusClass()}">${escapeHtml(state.message || (session ? "Listo para rellenar el formulario." : APP_HINT))}</div>
        ${state.filled || state.missing ? `<div class="meta">${state.filled} campos rellenados${state.missing ? ` · ${state.missing} requieren tu revisión` : ""}</div>` : ""}
        <div class="row">
          ${session && !state.auto ? `<button class="action" data-fill ${state.busy ? "disabled" : ""}>${state.busy ? "Rellenando..." : "Rellenar de nuevo"}</button>` : ""}
          ${session && !state.auto ? `<button class="action primary" data-submit ${state.busy || state.reported ? "disabled" : ""}>Enviar postulación</button>` : ""}
          ${!session ? `<button class="action" data-close>Cerrar</button>` : ""}
        </div>
      </div>
      <footer>
        Usa tu sesión real del navegador. No se guardan contraseñas ni se evaden CAPTCHA/2FA.
        ${state.auto ? " El auto-envío está activo para esta sesión." : " Revisa cada campo antes de enviar."}
      </footer>
    `;
    panel.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", closePanel));
    panel.querySelector("[data-fill]")?.addEventListener("click", () => runFill(false));
    panel.querySelector("[data-submit]")?.addEventListener("click", submitFromPanel);
  }

  function closePanel() {
    if (state.root) state.root.remove();
    state.root = null;
    state.shadow = null;
  }

  function showPanel() {
    ensureRoot();
    render();
  }

  function hashParams() {
    return new URLSearchParams(window.location.hash.replace(/^#/, ""));
  }

  async function initFromHash() {
    const params = hashParams();
    const sessionId = params.get("jobradar-session");
    if (!sessionId) return;
    await initSession(Number(sessionId), params.get("jobradar-auto") === "1");
  }

  async function initSession(sessionId, auto, force = false) {
    if (!force && Number(state.initializedSessionId) === Number(sessionId)) return;
    state.initializedSessionId = Number(sessionId);
    ensureRoot();
    state.session = null;
    state.auto = Boolean(auto);
    state.reported = false;
    state.busy = true;
    state.message = "Cargando tus datos...";
    state.filled = 0;
    state.missing = 0;
    render();
    try {
      const classification = await send({ type: "JOBRADAR_CLASSIFY", url: window.location.href });
      state.portal = classification.portal;
      if (classification.portal?.mode === "manual_only") {
        state.busy = false;
        state.message = classification.portal.reason;
        render();
        return;
      }
      const response = await send({ type: "JOBRADAR_GET_SESSION", sessionId });
      state.session = response.session;
      state.portal = response.session.portal;
      state.busy = false;
      state.message = state.auto
        ? "Auto-envío autorizado. Rellenando y enviando..."
        : "Datos cargados. Vamos a rellenar el formulario.";
      render();
      await runFill(state.auto);
    } catch (error) {
      state.busy = false;
      state.initializedSessionId = null;
      state.message = `No se pudo cargar la sesión: ${error.message}`;
      render();
    }
  }

  function textFor(element) {
    const values = [
      element.getAttribute("aria-label"),
      element.getAttribute("placeholder"),
      element.getAttribute("name"),
      element.getAttribute("id"),
      element.getAttribute("autocomplete"),
    ];
    if (element.labels) {
      for (const label of element.labels) values.push(label.innerText || label.textContent);
    }
    const wrappingLabel = element.closest("label");
    if (wrappingLabel) values.push(wrappingLabel.innerText || wrappingLabel.textContent);
    const fieldset = element.closest("fieldset");
    if (fieldset) {
      const legend = fieldset.querySelector("legend");
      if (legend) values.push(legend.innerText || legend.textContent);
    }
    return values.filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }

  function mapKey(element) {
    const text = normalize(textFor(element));
    const type = normalize(element.getAttribute("type"));
    if (!text && !type) return "";
    if (type === "email" || /e-?mail|correo electronico|correo/.test(text)) return "email";
    if (type === "tel" || /phone|telefono|celular|mobile|whatsapp/.test(text)) return "phone";
    if (/linkedin/.test(text)) return "linkedin";
    if (/github/.test(text)) return "github";
    if (/portfolio|portafolio|website|sitio web|pagina web/.test(text)) return "portfolio";
    if (/first name|nombre(s)?(?! completo)|given name|primer nombre/.test(text)) return "first_name";
    if (/last name|apellido|family name|surname/.test(text)) return "last_name";
    if (/full name|nombre completo|your name|nombre y apellido/.test(text)) return "full_name";
    if (/salary|salario|pretension|pretensión|compensation|remuneracion/.test(text)) return "salary_expectation";
    if (/years.*experience|anos.*experiencia|años.*experiencia/.test(text)) return "years_experience";
    if (/current.*company|empresa.*actual|company name|empresa/.test(text)) return "current_company";
    if (/current.*title|job title|cargo actual|cargo/.test(text)) return "current_title";
    if (/cover letter|carta de presentacion|carta de presentación|message|mensaje/.test(text)) return "cover_letter";
    if (/city|ciudad|location|ubicacion|ubicación|country|pais|país/.test(text)) return "location";
    if (/^name$|nombre/.test(text)) return "full_name";
    return "";
  }

  function setNativeValue(element, value) {
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    if (setter) setter.call(element, value);
    else element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    element.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function setSelect(element, value) {
    const target = normalize(value);
    const options = Array.from(element.options || []);
    const match =
      options.find((option) => normalize(option.value) === target) ||
      options.find((option) => normalize(option.textContent) === target) ||
      options.find((option) => normalize(option.textContent).includes(target) || target.includes(normalize(option.textContent)));
    if (!match) return false;
    element.value = match.value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function visible(element) {
    if (!element || element.disabled || element.type === "hidden") return false;
    const style = window.getComputedStyle(element);
    return style.display !== "none" && style.visibility !== "hidden" && element.getClientRects().length > 0;
  }

  async function uploadCv() {
    const inputs = Array.from(document.querySelectorAll('input[type="file"]')).filter((input) => !input.disabled);
    if (!inputs.length || !state.session?.cv_url) return false;
    const input = inputs.find((item) => /cv|resume|hoja de vida|curriculum/i.test(textFor(item))) || inputs[0];
    if (!input) return false;
    try {
      const response = await send({
        type: "JOBRADAR_FETCH_CV",
        url: state.session.cv_url,
        name: state.session.cv_file_name,
      });
      const binary = atob(response.base64);
      const bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
      const file = new File([bytes], response.name || "cv.pdf", { type: response.mime || "application/pdf" });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      if (/pdf/i.test(input.accept || "") && !/\.pdf$/i.test(file.name)) {
        state.message = "El portal pide PDF y el CV seleccionado no es PDF. Revisa la elección del CV.";
      }
      return true;
    } catch (error) {
      state.missing += 1;
      state.message = `No se pudo adjuntar el CV: ${error.message}`;
      return false;
    }
  }

  function collectQuestions() {
    const elements = Array.from(document.querySelectorAll('textarea, input[type="text"]'));
    const result = [];
    for (const element of elements) {
      if (!visible(element) || mapKey(element)) continue;
      const label = textFor(element);
      if (label.length < 12 || label.length > 350) continue;
      if (!label.includes("?") && !QUESTION_HINT.test(label)) continue;
      if (!result.some((item) => normalize(item.label) === normalize(label))) {
        result.push({ element, label });
      }
      if (result.length >= 12) break;
    }
    return result;
  }

  async function fillCustomAnswers() {
    const questions = collectQuestions();
    if (!questions.length || !state.session?.job_id) return;
    try {
      const response = await send({
        type: "JOBRADAR_DRAFT_ANSWERS",
        jobId: state.session.job_id,
        questions: questions.map((item) => item.label),
      });
      const byQuestion = new Map();
      for (const answer of response.answers || []) {
        byQuestion.set(normalize(answer.question), answer);
      }
      for (const question of questions) {
        const answer =
          byQuestion.get(normalize(question.label)) ||
          [...byQuestion.entries()].find(([key]) => key.includes(normalize(question.label).slice(0, 50)))?.[1];
        if (answer?.answer && !answer.needs_user_input) {
          setNativeValue(question.element, answer.answer);
          state.answers[question.label] = answer.answer;
          state.filled += 1;
        } else {
          state.missing += 1;
          question.element.setAttribute("data-jobradar-review", "true");
        }
      }
    } catch (error) {
      state.message = `No se pudieron redactar las respuestas: ${error.message}`;
    }
  }

  async function fillCurrentPage() {
    let filled = 0;
    let missing = 0;
    const fields = state.session?.fields || {};
    const controls = Array.from(document.querySelectorAll("input, textarea, select"));
    for (const element of controls) {
      if (!visible(element)) continue;
      const type = normalize(element.getAttribute("type"));
      if (["file", "hidden", "submit", "button", "reset", "checkbox", "radio"].includes(type)) continue;
      const key = mapKey(element);
      if (!key) continue;
      const value = fields[key];
      if (!value) {
        missing += 1;
        continue;
      }
      if (element instanceof HTMLSelectElement) {
        if (setSelect(element, value)) filled += 1;
        else missing += 1;
      } else {
        setNativeValue(element, value);
        filled += 1;
      }
    }
    const customFilledStart = state.filled;
    const customMissingStart = state.missing;
    await fillCustomAnswers();
    await uploadCv();
    filled += state.filled - customFilledStart;
    missing += state.missing - customMissingStart;
    state.filled = filled;
    state.missing = missing;
    return { filled, missing };
  }

  function detectBlocker() {
    const passwordVisible = Array.from(document.querySelectorAll('input[type="password"]')).some(visible);
    if (passwordVisible) {
      return "El portal pide iniciar sesión. Inicia sesión manualmente y vuelve a abrir el asistente.";
    }
    const captcha = Array.from(
      document.querySelectorAll(
        'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], textarea[name*="captcha"], [class*="captcha"], [id*="captcha"]',
      ),
    ).some(visible);
    if (captcha) {
      return "El portal pide CAPTCHA. Completa la verificación manualmente; el asistente no la evade.";
    }
    const twoFactor = Array.from(
      document.querySelectorAll(
        'input[autocomplete="one-time-code"], input[name*="otp"], input[name*="2fa"], input[id*="2fa"]',
      ),
    ).some(visible);
    if (twoFactor) {
      return "El portal pide verificación en dos pasos. Completa el código manualmente; el asistente no la evita.";
    }
    return "";
  }

  function detectRequiredConsent() {
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"][required]'));
    const blocking = checkboxes.find((element) =>
      /acepto|agree|terms|terminos|términos|privacidad|privacy|consentimiento/i.test(textFor(element)),
    );
    if (blocking) {
      blocking.setAttribute("data-jobradar-review", "true");
      return "Hay una casilla de términos/privacidad obligatoria. Márcala manualmente y revisa el envío.";
    }
    return "";
  }

  function findActionButton(texts) {
    const candidates = Array.from(
      document.querySelectorAll('button, input[type="submit"], input[type="button"], a[role="button"], a.button'),
    ).filter((element) => visible(element) && !element.disabled);
    let best = null;
    let bestScore = 0;
    for (const element of candidates) {
      const text = normalize(element.innerText || element.value || element.textContent || "");
      if (!text) continue;
      for (const candidate of texts) {
        const target = normalize(candidate);
        let score = 0;
        if (text === target) score = 3;
        else if (text.includes(target)) score = 2;
        else if (target.includes(text) && text.length > 4) score = 1;
        if (score > bestScore) {
          best = element;
          bestScore = score;
        }
      }
    }
    return best;
  }

  async function report(status, message) {
    if (!state.session) return;
    state.reported = true;
    state.busy = false;
    state.message = message;
    render();
    try {
      await send({
        type: "JOBRADAR_REPORT",
        sessionId: state.session.id,
        status,
        message,
      });
    } catch (error) {
      state.message = `${message} (No se pudo reportar: ${error.message})`;
      render();
    }
  }

  async function runFill(auto) {
    if (!state.session || state.busy) return;
    ensureRoot();
    state.auto = Boolean(auto);
    state.busy = true;
    state.reported = false;
    state.message = "Rellenando formulario...";
    render();
    try {
      const blocker = detectBlocker();
      if (blocker) {
        await report("manual", blocker);
        return;
      }
      const result = await fillCurrentPage();
      state.filled = result.filled;
      state.missing = result.missing;
      state.busy = false;
      if (state.auto) {
        const consent = detectRequiredConsent();
        if (consent) {
          await report("manual", consent);
          return;
        }
        await autoAdvanceAndSubmit();
      } else {
        state.message = `Formulario rellenado (${result.filled} campos). Revisa los campos marcados y envía tú mismo.`;
        render();
      }
    } catch (error) {
      state.busy = false;
      state.message = `No se pudo rellenar el formulario: ${error.message}`;
      render();
    }
  }

  async function clickSubmitAndObserve(submit) {
    if (!state.session) return;
    const beforeUrl = window.location.href;
    try {
      await send({
        type: "JOBRADAR_SUBMIT_INTENT",
        sessionId: state.session.id,
        url: beforeUrl,
      });
    } catch {
      // The content script may still survive and report the result itself.
    }
    submit.click();
    await sleep(1900);
    const success =
      window.location.href !== beforeUrl ||
      /thank you|thanks for applying|application (was )?submitted|application received|successfully submitted|postulaci[oó]n (enviada|recibida)|solicitud (enviada|recibida)|hemos recibido|gracias por postular/i.test(
        document.body.innerText,
      );
    if (success) {
      await report("submitted", "Postulación enviada por el asistente. Revisa el correo de confirmación del portal.");
    } else {
      await report(
        "manual",
        "El botón de envío se pulsó, pero no pudimos confirmar el envío. Revisa la pestaña y completa el último paso.",
      );
    }
  }

  async function autoAdvanceAndSubmit() {
    for (let step = 0; step < 4; step += 1) {
      const blocker = detectBlocker();
      if (blocker) {
        await report("manual", blocker);
        return;
      }
      const submit = findActionButton(SUBMIT_TEXTS);
      if (submit) {
        state.message = "Enviando postulación...";
        render();
        await clickSubmitAndObserve(submit);
        return;
      }
      const next = findActionButton(NEXT_TEXTS);
      if (next) {
        state.message = "Avanzando al siguiente paso...";
        render();
        next.click();
        await sleep(2600);
        await fillCurrentPage();
        continue;
      }
      break;
    }
    await report("manual", "No encontré un botón de envío. Completa el último paso manualmente en el portal.");
  }

  async function submitFromPanel() {
    if (!state.session || state.reported) return;
    state.busy = true;
    state.message = "Buscando el botón de envío...";
    render();
    const blocker = detectBlocker();
    if (blocker) {
      await report("manual", blocker);
      return;
    }
    const consent = detectRequiredConsent();
    if (consent) {
      await report("manual", consent);
      return;
    }
    if (!window.confirm("¿Enviar la postulación ahora? Revisa que todos los campos sean correctos.")) {
      state.busy = false;
      state.message = "Envío cancelado. Puedes revisar y enviar desde el portal.";
      render();
      return;
    }
    const submit = findActionButton(SUBMIT_TEXTS);
    if (!submit) {
      await report("manual", "No encontré el botón de envío. Envía desde el portal y márcalo en JobRadar.");
      return;
    }
    state.message = "Enviando postulación...";
    render();
    await clickSubmitAndObserve(submit);
  }

  document.addEventListener(
    "submit",
    () => {
      if (!state.session || state.reported || state.auto) return;
      setTimeout(() => {
        if (!state.reported) {
          report("submitted", "Formulario enviado desde el portal. JobRadar lo registró en tu tracker.");
        }
      }, 1800);
    },
    true,
  );

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "JOBRADAR_OPEN_PANEL") {
      showPanel();
      if (!state.session) {
        state.portal = null;
        state.message = "Clasificando portal...";
        render();
        send({ type: "JOBRADAR_CLASSIFY", url: window.location.href })
          .then((response) => {
            state.portal = response.portal;
            state.message =
              response.portal?.mode === "manual_only"
                ? response.portal.reason
                : "Portal compatible con el asistente. Abre la vacante desde JobRadar y pulsa «Preparar postulación».";
            render();
          })
          .catch((error) => {
            state.message = error.message;
            render();
          });
      }
    }
    if (message?.type === "JOBRADAR_RESUME" && message.sessionId) {
      if (state.session?.id === message.sessionId && (state.busy || state.reported || state.auto)) return;
      initSession(Number(message.sessionId), true, true);
    }
  });

  initFromHash();
  window.addEventListener("hashchange", initFromHash);
  if (window.location.hash.includes("jobradar-session=")) {
    setTimeout(initFromHash, 500);
  }
})();
