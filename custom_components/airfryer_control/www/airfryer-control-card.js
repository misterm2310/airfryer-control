/*
 * Airfryer Control – Karten für Home Assistant
 *   custom:airfryer-control-card    Zonen, Einstellungen im Fenster, Senden/Beenden
 *   custom:airfryer-control-ticker  Laufband mit den Fertig-Zeiten (optional mit Kochtimern)
 *
 * Für Doofe: Die Integration liefert diese Datei selbst aus. Du musst nichts
 * installieren – die Karten stehen im Karten-Dialog zur Auswahl.
 * Gemacht von Mister-M – mit Hilfe von Claude. Lizenz: MIT.
 */
const AC_BASE = new URL(".", import.meta.url).pathname.replace(/\/$/, "");
const AC_VERSION = new URL(import.meta.url).searchParams.get("v") || "";
const AC_REPO = "https://github.com/misterm2310/airfryer-control";

// ---------- Hilfen ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const isDe = (hass) => String(hass?.language || "de").toLowerCase().startsWith("de");
const tr = (hass, de, en) => (isDe(hass) ? de : en);

const COLORS = {
  gart: "#43A047", vorheizen: "#FB8C00", vorgeheizt: "#FB8C00", wartet_auf_start: "#FB8C00",
  fertig: "#E53935", warmhalten: "#8E24AA", pausiert: "#FDD835", schublade_offen: "#FDD835", offline: "#616161",
};
const RUNNING = ["gart", "vorheizen", "pausiert", "warmhalten"];
const STATE_TEXT = {
  aus: ["Aus", "Off"], bereit: ["Bereit", "Ready"], vorheizen: ["Heizt vor", "Preheating"],
  vorgeheizt: ["Vorgeheizt", "Preheated"], wartet_auf_start: ["Wartet auf Start", "Waiting for start"],
  gart: ["Gart", "Cooking"], pausiert: ["Pausiert", "Paused"], schublade_offen: ["Schublade offen", "Drawer open"],
  fertig: ["FERTIG!", "DONE!"], warmhalten: ["Hält warm", "Keeping warm"], offline: ["Offline", "Offline"],
  unbekannt: ["Unbekannt", "Unknown"],
};
const MODE_TEXT = {
  airfry: ["Heißluft", "Air fry", "mdi:fan"], roast: ["Braten", "Roast", "mdi:food-steak"],
  bake: ["Backen", "Bake", "mdi:muffin"], grill: ["Grillen", "Grill", "mdi:grill"],
  reheat: ["Aufwärmen", "Reheat", "mdi:microwave"], dry: ["Trocknen", "Dry", "mdi:water-off"],
};
const stateText = (hass, s) => { const t = STATE_TEXT[s]; return t ? tr(hass, t[0], t[1]) : s; };
const modeText = (hass, m) => { const t = MODE_TEXT[m]; return t ? tr(hass, t[0], t[1]) : m; };
const clock = (iso, hass) => {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleTimeString(isDe(hass) ? "de-DE" : "en-GB", { hour: "2-digit", minute: "2-digit" });
};
const valid = (s) => s && s.state !== "unknown" && s.state !== "unavailable";

/** Zonen der Integration finden (Zone 1, Zone 2, Grandzone …) */
function findZones(hass) {
  const zones = [];
  const ents = hass.entities || {};
  const re = /^sensor\.(.+_(?:zone_\d+|grandzone))_zustand$/;
  for (const id of Object.keys(hass.states)) {
    const m = re.exec(id);
    if (!m) continue;
    const reg = ents[id];
    if (reg && reg.platform && reg.platform !== "airfryer_control") continue;
    const key = m[1];
    const sw = [`switch.${key}_senden_beenden`, `switch.${key}_gart`].find((e) => hass.states[e]);
    zones.push({
      key,
      state: id,
      finish: `sensor.${key}_fertig_um`,
      mode: `select.${key}_programm`,
      temp: `number.${key}_temperatur_einstellen`,
      time: `number.${key}_garzeit_einstellen`,
      sw,
      name: zoneName(hass, key, hass.states[id]),
    });
  }
  const order = (z) => (/grandzone$/.test(z.key) ? 99 : Number((/zone_(\d+)$/.exec(z.key) || [0, 50])[1]));
  return zones.sort((a, b) => order(a) - order(b));
}
function zoneName(hass, key, st) {
  if (/grandzone$/.test(key)) return "Grandzone";
  const n = /zone_(\d+)$/.exec(key);
  return n ? tr(hass, `Zone ${n[1]}`, `Zone ${n[1]}`) : (st?.attributes?.friendly_name || key);
}

const BASE_CSS = `
  :host { display:block; }
  ha-card { overflow:hidden; }
  .ac-head { display:flex; align-items:center; gap:10px; padding:14px 16px 6px; }
  .ac-head ha-icon { color:var(--primary-color); --mdc-icon-size:26px; }
  .ac-head h2 { margin:0; font-size:1.1rem; font-weight:600; flex:1; }
  .ac-dot { width:10px; height:10px; border-radius:50%; background:#43A047; }
  .ac-dot.off { background:#9e9e9e; }
  .ac-ibtn { background:none; border:none; color:var(--secondary-text-color); cursor:pointer; padding:6px; border-radius:50%; display:flex; }
  .ac-ibtn:hover { background:rgba(127,127,127,.15); }
  .ac-ibtn ha-icon { --mdc-icon-size:22px; }
  .ac-zones { display:flex; flex-direction:column; padding:4px 0 8px; }
  .ac-row { display:flex; align-items:center; gap:12px; padding:10px 16px 10px 12px; border-left:4px solid var(--c, #9e9e9e); margin:2px 0; cursor:pointer; }
  .ac-row:hover { background:rgba(127,127,127,.08); }
  .ac-row > ha-icon { color:var(--c, #9e9e9e); --mdc-icon-size:30px; flex:none; }
  .ac-txt { flex:1; min-width:0; }
  .ac-name { font-weight:600; }
  .ac-state { color:var(--c, var(--secondary-text-color)); font-size:.95em; }
  .ac-sub { opacity:.75; font-size:.85em; }
  .ac-go { width:46px; height:46px; border-radius:50%; border:none; cursor:pointer; background:var(--b, #43A047); color:#fff; display:flex; align-items:center; justify-content:center; flex:none; }
  .ac-go:disabled { opacity:.4; cursor:default; }
  .ac-go ha-icon { --mdc-icon-size:22px; }
  .ac-empty { padding:16px; color:var(--secondary-text-color); }
  .ac-over { position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:9; display:flex; align-items:center; justify-content:center; padding:12px; }
  .ac-dlg { background:var(--card-background-color, #fff); color:var(--primary-text-color); border-radius:16px; width:min(420px,100%); max-height:92vh; overflow:auto; padding:16px; box-shadow:0 8px 30px rgba(0,0,0,.4); }
  .ac-dlg h3 { margin:0 0 4px; display:flex; align-items:center; gap:8px; }
  .ac-dlg h3 span { flex:1; }
  .ac-modes { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:12px 0; }
  .ac-mode { border:2px solid transparent; border-radius:12px; background:var(--secondary-background-color, rgba(127,127,127,.12)); color:inherit; padding:10px 4px; cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:4px; font:inherit; font-size:.85em; }
  .ac-mode.on { border-color:var(--primary-color); color:var(--primary-color); font-weight:600; }
  .ac-mode ha-icon { --mdc-icon-size:24px; }
  .ac-step { display:flex; align-items:center; justify-content:space-between; gap:8px; margin:10px 0; }
  .ac-step label { flex:1; opacity:.8; }
  .ac-step button { width:44px; height:44px; border-radius:50%; border:none; background:var(--secondary-background-color, rgba(127,127,127,.12)); color:inherit; font-size:1.4rem; cursor:pointer; }
  .ac-step b { min-width:84px; text-align:center; font-size:1.3rem; }
  .ac-big { width:100%; border:none; border-radius:12px; padding:14px; font-size:1.05rem; font-weight:700; color:#fff; background:var(--b, #43A047); cursor:pointer; margin-top:8px; }
  .ac-note { font-size:.85em; opacity:.7; margin:6px 0 0; text-align:center; }
  .elcredits { text-align:center; } .elcredits p { margin:8px 0; }
  .ellogo { background:#fff; border-radius:16px; padding:10px; display:inline-block; max-width:100%; box-shadow:0 1px 4px rgba(0,0,0,.12); }
  .ellogo img { display:block; max-width:100%; width:200px; height:auto; }
  .elcbtns { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin:12px 0; }
  .elcbtn { color:var(--primary-text-color); background:var(--secondary-background-color, rgba(127,127,127,.12)); border-radius:12px; padding:10px 14px; text-decoration:none; font-weight:500; }
  .elcbtn.pp { display:inline-flex; align-items:center; gap:8px; background:#0070BA; color:#fff; border:2px solid #003087; font-weight:700; }
  .elcbtn.pp svg { width:20px; height:20px; flex:none; }
  .elcsmall { opacity:.7; font-size:.9em; }
`;

function creditsHtml(hass) {
  const t = (de, en) => tr(hass, de, en);
  return `<div class="elcredits" translate="no">
    <div class="ellogo"><img src="${AC_BASE}/mister-m.webp?v=${esc(AC_VERSION)}" alt="Mister-M" loading="lazy"></div>
    <p><b>Airfryer Control</b> v${esc(AC_VERSION)}</p>
    <p>${t("Gemacht von <b>Mister-M</b> – mit Hilfe von Claude 🤖", "Made by <b>Mister-M</b> – with help from Claude 🤖")}</p>
    <p>${t("Ich versuche, Updates und Fehler-Korrekturen zeitnah zu erledigen.", "I try to ship updates and fixes promptly.")}</p>
    <div class="elcbtns">
      <a class="elcbtn" href="${AC_REPO}" target="_blank" rel="noopener">🐙 GitHub</a>
      <a class="elcbtn" href="${AC_REPO}/discussions" target="_blank" rel="noopener">💡 ${t("Idee oder Wunsch", "Idea or request")}</a>
      <a class="elcbtn" href="${AC_REPO}/issues" target="_blank" rel="noopener">🐞 ${t("Fehler melden", "Report a bug")}</a>
      <a class="elcbtn pp" href="https://paypal.me/MarcoStrickmann" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C1 8.6 2.7 5 6.2 5c2 0 3.5 1.1 5.8 3.4C14.3 6.1 15.8 5 17.8 5c3.5 0 5.2 3.6 3.8 6.8C19.5 16.4 12 21 12 21z" fill="#fff"/></svg><span>${t("Spenden mit PayPal", "Donate with PayPal")}</span></a>
    </div>
    <p class="elcsmall">${t("Airfryer Control ist und bleibt kostenlos. Wenn es dir gefällt, freue ich mich über eine kleine Spende – ganz freiwillig. Beim Antippen öffnet sich PayPal im Browser; vorher geht nichts ins Internet.", "Airfryer Control is and stays free. If you like it, I would be happy about a small donation – completely voluntary. Tapping opens PayPal in your browser; nothing goes to the internet before that.")}</p>
    <p>🔒 ${t("Datenschutz: Diese Karte spricht nur mit deinem Home Assistant und schickt selbst nichts ins Internet. Die Integration meldet sich mit deinem VeSync-Konto bei der Cosori-Cloud an – Kennungen werden in der Diagnose geschwärzt.", "Privacy: this card only talks to your Home Assistant and sends nothing to the internet itself. The integration signs in to the Cosori cloud with your VeSync account – identifiers are redacted in the diagnostics.")}</p>
    <p class="elcsmall">${t("Kein offizielles Produkt von Cosori, VeSync oder Arovast.", "Not an official product of Cosori, VeSync or Arovast.")} · ${t("Lizenz", "License")}: MIT</p>
  </div>`;
}

// ---------- Hauptkarte ----------
class AirfryerControlCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._open = null; // Schlüssel der Zone, deren Fenster offen ist ("__credits" = Credits)
    this._sig = "";
  }
  setConfig(config) {
    this._config = { compact: false, ...config };
    this._sig = "";
    if (this._hass) this._render();
  }
  static getStubConfig() { return { title: "Heißluftfritteuse" }; }
  static getConfigElement() { return document.createElement("airfryer-control-card-editor"); }
  getCardSize() { return 4; }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6 }; }

  set hass(hass) {
    this._hass = hass;
    const zones = findZones(hass);
    const sig = zones.map((z) => [z.state, z.finish, z.mode, z.temp, z.time, z.sw]
      .map((e) => { const s = hass.states[e]; return s ? s.state + "|" + (s.attributes?.min ?? "") + (s.attributes?.max ?? "") : "-"; }).join(",")).join(";")
      + "#" + (hass.states["binary_sensor.cosori_online"]?.state || "") + this._open + (hass.language || "");
    if (sig === this._sig) return;
    this._sig = sig;
    this._zones = zones;
    this._render();
  }

  _color(z) { return COLORS[this._hass.states[z.state]?.state] || "var(--secondary-text-color)"; }
  _btn(z) {
    const s = this._hass.states[z.state]?.state;
    if (s === "wartet_auf_start") return { color: "#FB8C00", icon: "mdi:close", text: tr(this._hass, "Abbrechen", "Cancel") };
    if (RUNNING.includes(s)) return { color: "#E53935", icon: "mdi:stop", text: tr(this._hass, "Beenden", "Stop") };
    return { color: "#43A047", icon: "mdi:send", text: tr(this._hass, "Senden", "Send") };
  }
  _toggle(z) { if (z.sw) this._hass.callService("switch", "toggle", { entity_id: z.sw }); }

  _render() {
    const hass = this._hass;
    if (!hass) return;
    const zones = this._zones || findZones(hass);
    const title = this._config.title ?? "Heißluftfritteuse";
    const online = hass.states["binary_sensor.cosori_online"];
    const rows = zones.map((z) => {
      const st = hass.states[z.state];
      const fin = hass.states[z.finish];
      const b = this._btn(z);
      const sub = valid(fin) ? tr(hass, `fertig um ${clock(fin.state, hass)} Uhr`, `done at ${clock(fin.state, hass)}`) : "";
      return `<div class="ac-row" data-z="${esc(z.key)}" style="--c:${this._color(z)}">
        <ha-icon icon="mdi:toaster-oven"></ha-icon>
        <div class="ac-txt"><div class="ac-name">${esc(z.name)}</div>
          <div class="ac-state">${esc(stateText(hass, st?.state))}</div>
          ${sub ? `<div class="ac-sub">${esc(sub)}</div>` : ""}</div>
        <button class="ac-go" data-go="${esc(z.key)}" style="--b:${b.color}" title="${esc(b.text)}" ${z.sw ? "" : "disabled"}><ha-icon icon="${b.icon}"></ha-icon></button>
      </div>`;
    }).join("");
    this.shadowRoot.innerHTML = `<style>${BASE_CSS}</style>
      <ha-card>
        <div class="ac-head"><ha-icon icon="mdi:toaster-oven"></ha-icon><h2>${esc(title)}</h2>
          <span class="ac-dot ${online && online.state === "on" ? "" : "off"}" title="${online?.state === "on" ? "Online" : "Offline"}"></span>
          <button class="ac-ibtn" data-info title="Info"><ha-icon icon="mdi:information-outline"></ha-icon></button></div>
        <div class="ac-zones">${rows || `<div class="ac-empty">${esc(tr(hass, "Keine Zonen gefunden. Ist die Integration „Airfryer Control“ eingerichtet und die Fritteuse online?", "No zones found. Is the “Airfryer Control” integration set up and the fryer online?"))}</div>`}</div>
        ${this._dialogHtml(zones)}
      </ha-card>`;
    this._wire();
  }

  _dialogHtml(zones) {
    const hass = this._hass;
    if (!this._open) return "";
    if (this._open === "__credits") {
      return `<div class="ac-over" data-close><div class="ac-dlg">${creditsHtml(hass)}<button class="ac-big" data-close style="--b:var(--primary-color)">${esc(tr(hass, "Schließen", "Close"))}</button></div></div>`;
    }
    const z = zones.find((x) => x.key === this._open);
    if (!z) return "";
    const mode = hass.states[z.mode];
    const temp = hass.states[z.temp];
    const time = hass.states[z.time];
    const b = this._btn(z);
    const opts = mode?.attributes?.options || [];
    const modes = opts.map((o) => `<button class="ac-mode ${mode.state === o ? "on" : ""}" data-mode="${esc(o)}"><ha-icon icon="${(MODE_TEXT[o] || [])[2] || "mdi:chef-hat"}"></ha-icon>${esc(modeText(hass, o))}</button>`).join("");
    const step = (what, label, st, unit) => st ? `<div class="ac-step"><label>${esc(label)}</label><button data-step="${what}" data-d="-1">−</button><b>${esc(st.state)} ${unit}</b><button data-step="${what}" data-d="1">+</button></div>` : "";
    const min = temp?.attributes?.min, max = temp?.attributes?.max;
    return `<div class="ac-over" data-close><div class="ac-dlg" style="--c:${this._color(z)}">
      <h3><ha-icon icon="mdi:toaster-oven" style="color:${this._color(z)}"></ha-icon><span>${esc(z.name)}</span><button class="ac-ibtn" data-close><ha-icon icon="mdi:close"></ha-icon></button></h3>
      <div class="ac-state" style="color:${this._color(z)}">${esc(stateText(hass, hass.states[z.state]?.state))}</div>
      ${opts.length ? `<div class="ac-modes">${modes}</div>` : ""}
      ${step("temp", tr(hass, "Temperatur", "Temperature"), temp, "°C")}
      ${step("time", tr(hass, "Garzeit", "Cooking time"), time, "Min")}
      ${min != null ? `<p class="ac-note">${esc(tr(hass, `Für dieses Programm: ${min}–${max} °C`, `For this program: ${min}–${max} °C`))}</p>` : ""}
      <button class="ac-big" data-go="${esc(z.key)}" style="--b:${b.color}" ${z.sw ? "" : "disabled"}>${esc(b.text)}</button>
      <p class="ac-note">${esc(tr(hass, "Senden bereitet die Fritteuse vor – gestartet wird am Gerät.", "Send prepares the fryer – you start it on the device."))}</p>
    </div></div>`;
  }

  _wire() {
    const root = this.shadowRoot;
    root.querySelectorAll(".ac-row").forEach((el) => el.addEventListener("click", (e) => {
      if (e.target.closest("[data-go]")) return;
      this._open = el.dataset.z; this._sig = ""; this.hass = this._hass;
    }));
    root.querySelectorAll("[data-go]").forEach((el) => el.addEventListener("click", (e) => {
      e.stopPropagation();
      const z = (this._zones || []).find((x) => x.key === el.dataset.go);
      if (z) this._toggle(z);
    }));
    const info = root.querySelector("[data-info]");
    if (info) info.addEventListener("click", () => { this._open = "__credits"; this._sig = ""; this.hass = this._hass; });
    root.querySelectorAll("[data-close]").forEach((el) => el.addEventListener("click", (e) => {
      if (el.classList.contains("ac-over") && e.target !== el) return;
      this._open = null; this._sig = ""; this.hass = this._hass;
    }));
    root.querySelectorAll("[data-mode]").forEach((el) => el.addEventListener("click", () => {
      const z = (this._zones || []).find((x) => x.key === this._open);
      if (z) this._hass.callService("select", "select_option", { entity_id: z.mode, option: el.dataset.mode });
    }));
    root.querySelectorAll("[data-step]").forEach((el) => el.addEventListener("click", () => {
      const z = (this._zones || []).find((x) => x.key === this._open);
      if (!z) return;
      const id = el.dataset.step === "temp" ? z.temp : z.time;
      const st = this._hass.states[id];
      if (!st) return;
      const stepBy = el.dataset.step === "temp" ? 5 : 1;
      let v = Number(st.state) + Number(el.dataset.d) * stepBy;
      const min = st.attributes?.min, max = st.attributes?.max;
      if (min != null) v = Math.max(Number(min), v);
      if (max != null) v = Math.min(Number(max), v);
      this._hass.callService("number", "set_value", { entity_id: id, value: v });
    }));
  }
}

// ---------- Laufband ----------
class AirfryerControlTicker extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._sig = ""; }
  setConfig(config) {
    this._config = { hide_when_idle: true, speed: 60, extra_entities: [], language: "auto", ...config };
    this._sig = "";
    if (this._hass) this._render();
  }
  static getStubConfig() { return { hide_when_idle: true }; }
  static getConfigElement() { return document.createElement("airfryer-control-ticker-editor"); }
  getCardSize() { return 1; }
  getGridOptions() { return { columns: "full", rows: 1 }; }

  set hass(hass) {
    this._hass = hass;
    const parts = this._parts();
    const sig = parts.items.join("|") + parts.done + (this._config?.language || "") + (this._config?.speed || "");
    if (sig === this._sig) { this._measure(); return; }
    this._sig = sig;
    this._render();
  }
  connectedCallback() {
    // Minutenanzeige bei Kochtimern aktuell halten
    this._timer = setInterval(() => { if (this._hass) { this._sig = ""; this.hass = this._hass; } }, 60000);
  }
  disconnectedCallback() { clearInterval(this._timer); }

  _lh() { const l = this._config?.language; return l && l !== "auto" ? { ...this._hass, language: l } : this._hass; }

  _parts() {
    const hass = this._lh();
    const items = [];
    let done = false;
    for (const z of findZones(hass)) {
      const s = hass.states[z.state]?.state;
      const fin = hass.states[z.finish];
      const name = z.name;
      if (s === "gart" || s === "vorheizen") {
        const when = s === "gart" && valid(fin) ? tr(hass, `fertig um ${clock(fin.state, hass)} Uhr`, `done at ${clock(fin.state, hass)}`)
          : (s === "vorheizen" ? tr(hass, "heizt vor", "preheating") : tr(hass, "gart", "cooking"));
        items.push(`🍟 ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${when}`);
      } else if (s === "wartet_auf_start") {
        items.push(`🍟 ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${tr(hass, "wartet auf Start", "waiting for start")}`);
      } else if (s === "fertig") {
        done = true;
        items.push(`🍟 ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${tr(hass, "FERTIG!", "DONE!")}`);
      }
    }
    for (const id of this._config?.extra_entities || []) {
      const timers = hass.states[id]?.attributes?.timer;
      if (!Array.isArray(timers)) continue;
      timers.filter((x) => x.fertig).forEach((x) => { done = true; items.push(`⏰ ${x.name}: ${tr(hass, "FERTIG!", "DONE!")}`); });
      timers.filter((x) => !x.fertig).sort((a, b) => Date.parse(a.ende) - Date.parse(b.ende))
        .forEach((x) => items.push(`⏲️ ${x.name}: ${tr(hass, `fertig um ${clock(x.ende, hass)} Uhr`, `done at ${clock(x.ende, hass)}`)}`));
    }
    return { items, done };
  }

  _render() {
    const hass = this._lh();
    if (!hass || !this._config) return;
    const { items, done } = this._parts();
    const hide = this._config.hide_when_idle && !items.length;
    this.hidden = hide;
    this.style.display = hide ? "none" : "";
    this.dispatchEvent(new CustomEvent("card-visibility-changed", { detail: { value: !hide }, bubbles: true, composed: true }));
    const base = items.length ? items.join(" +++ ") : tr(hass, "👨‍🍳 Kein Kochtimer aktiv", "👨‍🍳 No cooking timer active");
    const piece = `+++ ${base} `;
    const plain = piece.length;
    const n = Math.max(5, Math.ceil(320 / plain));
    const text = piece.repeat(n);
    const dur = Math.max(8, Math.round(((plain * n * 11) / 100) * (60 / (Number(this._config.speed) || 60))));
    const color = done ? "#E53935" : "#26A69A";
    this.shadowRoot.innerHTML = `<style>
      :host { display:block; }
      ha-card { display:block; height:40px; padding:0; background:var(--card-background-color); border-radius:8px; border:none; box-shadow:0 5px 3px rgba(0,0,0,.1); overflow:hidden; }
      .box { display:flex; align-items:center; width:100%; height:100%; border:2px solid ${color}; border-radius:8px; box-sizing:border-box; }
      .box ha-icon { flex:none; --mdc-icon-size:22px; margin:0 10px; color:${color}; ${done ? "animation:ac_pulse 1s ease-in-out infinite;" : ""} }
      .box ha-icon + .win + ha-icon { animation-delay:.5s; }
      .win { flex:1; min-width:0; overflow:hidden; display:flex; align-items:center; }
      .wrap { white-space:nowrap; display:flex; animation:ac_tick ${dur}s linear infinite; }
      .txt { font-family:Roboto,sans-serif; font-size:16px; font-weight:500; line-height:20px; padding-right:20px; color:var(--primary-text-color); }
      @keyframes ac_pulse { 0% { opacity:1 } 50% { opacity:.3 } 100% { opacity:1 } }
      @keyframes ac_tick { from { transform:translateX(0) } to { transform:translateX(-50%) } }
      @media (prefers-reduced-motion: reduce) { .wrap { animation:none; } .box ha-icon { animation:none; } }
    </style>
    <ha-card><div class="box"><ha-icon icon="mdi:chef-hat"></ha-icon><div class="win"><div class="wrap"><span class="txt">${esc(text)}</span><span class="txt">${esc(text)}</span></div></div><ha-icon icon="mdi:chef-hat"></ha-icon></div></ha-card>`;
    this._measured = false;
    this._tries = 0;
    this._measure();
  }

  // Dauer aus der echten Textbreite: Breite ÷ Tempo (Pixel pro Sekunde). So läuft jeder Text gleich schnell.
  _measure() {
    if (this._measured || !this.shadowRoot) return;
    const wrap = this.shadowRoot.querySelector(".wrap");
    const one = wrap?.firstElementChild;
    const w = one ? one.getBoundingClientRect().width : 0;
    if (w > 0) {
      const speed = Math.min(200, Math.max(20, Number(this._config?.speed) || 60));
      wrap.style.animationDuration = `${Math.max(8, Math.round(w / speed))}s`;
      this._measured = true;
    } else if (!this._retry && (this._tries = (this._tries || 0) + 1) <= 5) { // nur kurz erneut versuchen (versteckte Karte hat Breite 0) – danach beim nächsten Update
      this._retry = requestAnimationFrame(() => { this._retry = 0; this._measure(); });
    }
  }
}

// ---------- Editoren ----------
function makeEditor(schemaFn, labelFn) {
  return class extends HTMLElement {
    setConfig(config) { this._config = config; this._draw(); }
    set hass(hass) { this._hass = hass; this._draw(); }
    _draw() {
      if (!this._hass || !this._config) return;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.addEventListener("value-changed", (e) => {
          this._config = e.detail.value;
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      this._form.hass = this._hass;
      this._form.data = this._config;
      this._form.schema = schemaFn(this._hass);
      this._form.computeLabel = (s) => labelFn(this._hass, s.name);
    }
  };
}
const cardLabels = { title: ["Titel", "Title"] };
customElements.define("airfryer-control-card-editor", makeEditor(
  () => [{ name: "title", selector: { text: {} } }],
  (h, n) => { const l = cardLabels[n]; return l ? tr(h, l[0], l[1]) : n; }));
const tickLabels = {
  extra_entities: ["Zusätzliche Kochtimer (z. B. sensor.einkaufsliste_kochtimer)", "Extra timers (e.g. sensor.einkaufsliste_kochtimer)"],
  hide_when_idle: ["Ausblenden, wenn nichts läuft", "Hide when idle"],
  speed: ["Tempo (Pixel pro Sekunde)", "Speed (pixels per second)"],
  language: ["Sprache", "Language"],
};
customElements.define("airfryer-control-ticker-editor", makeEditor(
  () => [
    { name: "extra_entities", selector: { entity: { multiple: true, domain: "sensor" } } },
    { name: "hide_when_idle", selector: { boolean: {} } },
    { name: "speed", selector: { number: { min: 20, max: 200, step: 5, mode: "box" } } },
    { name: "language", selector: { select: { mode: "dropdown", options: [{ value: "auto", label: "Auto (Home Assistant)" }, { value: "de", label: "Deutsch" }, { value: "en", label: "English" }] } } },
  ],
  (h, n) => { const l = tickLabels[n]; return l ? tr(h, l[0], l[1]) : n; }));

customElements.define("airfryer-control-card", AirfryerControlCard);
customElements.define("airfryer-control-ticker", AirfryerControlTicker);
window.customCards = window.customCards || [];
window.customCards.push(
  { type: "airfryer-control-card", name: "Airfryer Control", description: "Zonen der Heißluftfritteuse: Status, Programm, Temperatur, Zeit, Senden/Beenden.", preview: false },
  { type: "airfryer-control-ticker", name: "Airfryer Control – Laufband", description: "Laufband mit den Fertig-Zeiten der Fritteuse (optional mit Kochtimern).", preview: false },
);
console.info(`%c AIRFRYER-CONTROL %c ${AC_VERSION} `, "background:#26A69A;color:#fff;font-weight:700", "background:#333;color:#fff");
