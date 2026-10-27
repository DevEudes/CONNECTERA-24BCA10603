/* Connectera — progressive enhancements (every feature also works without JS). */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || ($("[name=csrfmiddlewaretoken]") || {}).value;

  async function post(url, data) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
      body: data instanceof FormData ? data : new URLSearchParams(data || {}),
      credentials: "same-origin",
    });
    let json = {};
    try { json = await res.json(); } catch (e) { /* not JSON */ }
    return { ok: res.ok, status: res.status, data: json };
  }
  async function getJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
    if (!res.ok) throw new Error(res.status);
    return res.json();
  }

  /* ---------- Toasts ---------- */
  const ICONS = { success: "bi-check-circle-fill", error: "bi-exclamation-circle-fill", info: "bi-info-circle-fill", warning: "bi-exclamation-triangle-fill" };
  function toast(text, type = "success") {
    let box = $(".toasts");
    if (!box) { box = document.createElement("div"); box.className = "toasts"; document.body.appendChild(box); }
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.setAttribute("role", "status");
    el.innerHTML = `<i class="bi ${ICONS[type] || ICONS.info}"></i><span></span><button class="close" aria-label="Close"><i class="bi bi-x-lg"></i></button>`;
    el.querySelector("span").textContent = text;
    box.appendChild(el);
    autoHide(el);
  }
  function autoHide(el) {
    const kill = () => { el.classList.add("hide"); setTimeout(() => el.remove(), 300); };
    el.querySelector(".close")?.addEventListener("click", kill);
    setTimeout(kill, el.classList.contains("info") ? 9000 : 4500);
  }
  $$(".toast").forEach(autoHide);
  window.ctoast = toast;

  /* ---------- Dropdowns: close when clicking outside ---------- */
  document.addEventListener("click", (e) => {
    $$("details.dropdown[open]").forEach((d) => { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });

  /* ---------- Modals ---------- */
  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open]");
    if (opener) { e.preventDefault(); $("#" + opener.dataset.open)?.showModal(); }
    const closer = e.target.closest("[data-close]");
    if (closer) { e.preventDefault(); closer.closest("dialog")?.close(); }
    if (e.target.tagName === "DIALOG") e.target.close();
  });

  /* ---------- Confirm before destructive actions ---------- */
  document.addEventListener("submit", (e) => {
    const msg = e.target.dataset.confirm;
    if (msg && !confirm(msg)) e.preventDefault();
  }, true);

  /* ---------- Password visibility ---------- */
  $$(".toggle-pwd").forEach((btn) => btn.addEventListener("click", () => {
    const input = btn.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.innerHTML = `<i class="bi ${show ? "bi-eye-slash" : "bi-eye"}"></i>`;
  }));

  /* ---------- Image previews ---------- */
  $$("input[type=file][data-preview]").forEach((input) => input.addEventListener("change", () => {
    const target = $(input.dataset.preview);
    const file = input.files[0];
    if (!target || !file) return;
    if (file.size > 5 * 1024 * 1024) { toast("Image too large (max 5 MB).", "error"); input.value = ""; return; }
    const url = URL.createObjectURL(file);
    target.innerHTML = `<img src="${url}" alt="Preview">`;
    target.classList.remove("hidden");
  }));

  /* ---------- Textarea auto-grow + counter ---------- */
  $$("textarea[data-autogrow]").forEach((t) => {
    const grow = () => { t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 240) + "px"; };
    t.addEventListener("input", grow); grow();
  });

  /* ---------- Likes ---------- */
  document.addEventListener("submit", async (e) => {
    const form = e.target.closest("form[data-like]");
    if (!form) return;
    e.preventDefault();
    const btn = form.querySelector("button");
    const r = await post(form.action);
    if (!r.ok) return toast("Something went wrong.", "error");
    btn.classList.toggle("liked", r.data.liked);
    btn.classList.remove("pop"); void btn.offsetWidth; btn.classList.add("pop");
    const card = form.closest(".post");
    const counter = card && card.querySelector("[data-like-count]");
    if (counter) counter.textContent = r.data.count;
  });

  /* ---------- Comments ---------- */
  document.addEventListener("submit", async (e) => {
    const form = e.target.closest("form[data-comment]");
    if (!form) return;
    e.preventDefault();
    const input = form.querySelector("input[name=text]");
    if (!input.value.trim()) return;
    const r = await post(form.action, new FormData(form));
    if (!r.ok) return toast(r.data.error || "Could not post the comment.", "error");
    const list = form.closest(".post").querySelector("[data-comments]");
    list.insertAdjacentHTML("beforeend", r.data.html);
    input.value = "";
    const counter = form.closest(".post").querySelector("[data-comment-count]");
    if (counter) counter.textContent = r.data.count;
  });

  /* ---------- Connection buttons (search cards, suggestions) ---------- */
  const STATE_HTML = {
    sent: '<i class="bi bi-hourglass-split"></i> Pending',
    connected: '<i class="bi bi-check2"></i> Connected',
    none: '<i class="bi bi-person-plus"></i> Connect',
  };
  document.addEventListener("submit", async (e) => {
    const form = e.target.closest("form[data-connect]");
    if (!form) return;
    e.preventDefault();
    const btn = form.querySelector("button");
    btn.disabled = true;
    const r = await post(form.action);
    toast(r.data.message || (r.ok ? "Done" : "Error"), r.ok && r.data.ok !== false ? "success" : "error");
    const state = r.data.state;
    if (state && STATE_HTML[state]) {
      btn.innerHTML = STATE_HTML[state];
      btn.className = "btn btn-sm " + (state === "none" ? "btn-primary" : "btn-soft");
      if (state === "none") btn.disabled = false;
    } else btn.disabled = false;
    const row = form.closest("[data-request-row]");
    if (row && r.ok) row.style.opacity = ".4";
  });

  /* ---------- Feed: progressive loading ---------- */
  const more = $("#load-more");
  if (more) {
    more.addEventListener("click", async (e) => {
      e.preventDefault();
      more.disabled = true;
      more.innerHTML = '<i class="bi bi-arrow-repeat"></i> Loading…';
      try {
        const data = await getJSON(more.dataset.url);
        $("#feed-list").insertAdjacentHTML("beforeend", data.html);
        if (data.has_next) {
          more.dataset.url = more.dataset.url.replace(/page=\d+/, "page=" + data.next);
          more.disabled = false;
          more.innerHTML = "Load more posts";
        } else more.parentElement.innerHTML = '<p class="subtle center">You\'re all caught up ✨</p>';
      } catch (err) { more.disabled = false; more.textContent = "Retry"; }
    });
  }

  /* ---------- Chat ---------- */
  const chat = $("#chat");
  if (chat) {
    const box = $("#chat-messages");
    const form = $("#chat-form");
    const textarea = form?.querySelector("textarea");
    const scrollDown = () => { box.scrollTop = box.scrollHeight; };
    scrollDown();
    let lastId = parseInt(chat.dataset.lastId || "0", 10);

    async function send() {
      const text = textarea.value.trim();
      if (!text) return;
      textarea.value = ""; textarea.style.height = "auto";
      const r = await post(form.action, { text });
      if (!r.ok) { toast(r.data.error || "Message not sent.", "error"); textarea.value = text; return; }
      $("#chat-empty")?.remove();
      box.insertAdjacentHTML("beforeend", r.data.html);
      lastId = Math.max(lastId, r.data.id);
      $("#seen-flag") && ($("#seen-flag").textContent = "Sent");
      scrollDown();
    }
    form?.addEventListener("submit", (e) => { e.preventDefault(); send(); });
    textarea?.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
    textarea?.focus();

    async function poll() {
      try {
        const data = await getJSON(`${chat.dataset.pollUrl}?after=${lastId}`);
        if (data.html) {
          $("#chat-empty")?.remove();
          const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
          box.insertAdjacentHTML("beforeend", data.html);
          if (nearBottom) scrollDown();
        }
        lastId = Math.max(lastId, data.last_id);
        const status = $("#chat-status");
        if (status) { status.textContent = data.online ? "Online" : "Offline"; status.classList.toggle("on", data.online); }
        const seen = $("#seen-flag");
        if (seen && data.seen) seen.innerHTML = '<i class="bi bi-check2-all"></i> Seen';
      } catch (e) { /* network hiccup: try again later */ }
    }
    setInterval(poll, 3000);
  }

  /* ---------- Navigation badges refresh ---------- */
  const counts = document.body.dataset.countsUrl;
  if (counts) {
    const setBadge = (key, n) => $$(`[data-badge="${key}"]`).forEach((b) => { b.textContent = n; b.classList.toggle("hidden", !n); });
    setInterval(async () => {
      try {
        const d = await getJSON(counts);
        setBadge("notifications", d.unread_notifications);
        setBadge("messages", d.unread_messages);
        setBadge("requests", d.pending_requests);
      } catch (e) { /* ignore */ }
    }, 20000);
  }

  /* ---------- Interests counter ---------- */
  const interestForm = $("#interest-form");
  if (interestForm) {
    const counter = $("#interest-count");
    const update = () => {
      const n = $$("input[type=checkbox]:checked", interestForm).length;
      counter.textContent = n;
      $("#interest-submit").disabled = n < 3;
    };
    interestForm.addEventListener("change", update); update();
  }

  /* ---------- Splash + onboarding slides ---------- */
  const splash = $(".splash");
  if (splash) setTimeout(() => splash.classList.add("gone"), 1600);
  const slides = $$(".slide");
  if (slides.length) {
    let i = 0;
    const dots = $$(".dots button");
    const next = $("#ob-next");
    const show = (n) => {
      i = (n + slides.length) % slides.length;
      slides.forEach((s, k) => s.classList.toggle("active", k === i));
      dots.forEach((d, k) => d.classList.toggle("active", k === i));
      const last = i === slides.length - 1;
      next.innerHTML = last ? 'Get started <i class="bi bi-arrow-right"></i>' : 'Next <i class="bi bi-arrow-right"></i>';
      next.dataset.last = last ? "1" : "";
    };
    dots.forEach((d, k) => d.addEventListener("click", () => show(k)));
    next.addEventListener("click", (e) => {
      if (next.dataset.last) return; // follow the link to sign up
      e.preventDefault(); show(i + 1);
    });
    let x0 = null;
    $(".slides").addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
    $(".slides").addEventListener("touchend", (e) => {
      if (x0 === null) return;
      const dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 50) show(i + (dx < 0 ? 1 : -1));
      x0 = null;
    });
    show(0);
  }

  /* ---------- Confetti (profile completed) ---------- */
  if ($("[data-confetti]")) {
    const colors = ["#7c3aed", "#a855f7", "#ec4899", "#f59e0b", "#10b981", "#0ea5e9"];
    for (let k = 0; k < 90; k++) {
      const c = document.createElement("span");
      c.className = "confetti";
      c.style.left = Math.random() * 100 + "vw";
      c.style.background = colors[k % colors.length];
      c.style.animationDuration = 2.5 + Math.random() * 2.5 + "s";
      c.style.animationDelay = Math.random() * .8 + "s";
      document.body.appendChild(c);
      setTimeout(() => c.remove(), 6000);
    }
  }
})();
