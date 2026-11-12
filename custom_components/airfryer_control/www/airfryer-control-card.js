/*
 * Airfryer Control – Karten für Home Assistant
 *   custom:airfryer-control-card    Zonen, Einstellungen klappen unter der Zeile auf, Senden/Beenden
 *   custom:airfryer-control-ticker  Laufband mit den Fertig-Zeiten (optional mit Kochtimern)
 *
 * Für Doofe: Die Integration liefert diese Datei selbst aus. Du musst nichts
 * installieren – die Karten stehen im Karten-Dialog zur Auswahl.
 * Gemacht von Mister-M – mit Hilfe von Claude. Lizenz: MIT.
 */
const AC_BASE = new URL(".", import.meta.url).pathname.replace(/\/$/, "");
const AC_VERSION = new URL(import.meta.url).searchParams.get("v") || "";
const AC_REPO = "https://github.com/misterm2310/airfryer-control";

// 📢 Neu in dieser Beta – Neueste oben (wie bei der Einkaufsliste). [Version, deutsch, englisch]
const AC_NEWS = [
  ["1.0.4-beta.5", "🚪 TwinFry: Schublade auf = alle Zonen zeigen „Schublade offen“, auch die Grandzone (#8)", "🚪 TwinFry: drawer open = every zone shows “Drawer open”, the Grandzone too (#8)"],
  ["1.0.4-beta.4", "⚙️ Einstellungen sehen jetzt 1:1 aus wie bei der Einkaufsliste: Suchfeld, Gruppen, Schalter in der Zeile, eigene Seite pro Einstellung", "⚙️ Settings now look 1:1 like the shopping list: search field, groups, switches in the row, its own page per setting"],
  ["1.0.4-beta.4", "📢 Neuigkeiten immer nach Version sortiert – die neueste steht oben", "📢 News always sorted by version – the newest is on top"],
  ["1.0.4-beta.4", "⏱️ Grandzone-Restzeit zeigt „0 Min“ statt „nicht verfügbar“, wenn nichts gart (#8)", "⏱️ Grandzone time remaining shows “0 min” instead of “unavailable” when idle (#8)"],
  ["1.0.4-beta.3", "⚙️ Einstellungen direkt in der Karte (Zahnrad oben): Ansicht, Karte und – für Admins – die Integration", "⚙️ Settings right in the card (cog at the top): view, card and – for admins – the integration"],
  ["1.0.4-beta.3", "📖 Anleitung neu: eigene Seite mit ←, Kapitel zum Aufklappen und Suchfeld", "📖 New guide: its own page with ←, chapters to unfold and a search field"],
  ["1.0.4-beta.3", "👁️ Schriftgröße und Hell/Dunkel – pro Gerät einstellbar", "👁️ Font size and light/dark – per device"],
  ["1.0.4-beta.3", "📢 Dieser Kasten + 💡 Tipp beim ersten Start", "📢 This box + 💡 tip on first start"],
  ["1.0.4-beta.3", "📱 Offline-App: alle Symbole da (Anleitung, Zahnrad, Programme)", "📱 Offline app: all icons are there (guide, cog, programs)"],
  ["1.0.4-beta.2", "📶 Kurze Funklöcher (bis 90 s) zählen nicht mehr als offline", "📶 Short signal drops (up to 90 s) no longer count as offline"],
  ["1.0.4-beta.2", "🔀 TwinFry: Grandzone wird vor Zone 1/2 automatisch zurückgesetzt", "🔀 TwinFry: the Grandzone is reset automatically before Zone 1/2"],
  ["1.0.4-beta.2", "🧩 Zonen bleiben, auch wenn die Fritteuse beim HA-Start schläft", "🧩 Zones stay even if the fryer sleeps while HA starts"],
  ["1.0.4-beta.2", "🍳 Rezept-Nummern wie in der VeSync-App · 🆕 Dual Blaze CAF-P583S zum Testen", "🍳 Recipe numbers like the VeSync app · 🆕 Dual Blaze CAF-P583S for testing"],
  ["1.0.4-beta.2", "🌍 Kartentitel in der Sprache von Home Assistant", "🌍 Card title in the language of Home Assistant"],
  ["1.0.4-beta.1", "🔎 Karte findet Zonen und Online-Status in jeder Sprache", "🔎 Card finds zones and online status in every language"],
];
// 🔢 Versionen vergleichen: 1.0.4-beta.10 > 1.0.4-beta.9 > 1.0.3 – und eine fertige Version zählt mehr als ihre Betas
function acVerCmp(a, b) {
  const p = (v) => { const m = /^(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?/.exec(String(v)) || []; return [+m[1] || 0, +m[2] || 0, +m[3] || 0, m[4] == null ? Infinity : +m[4]]; };
  const x = p(a), y = p(b);
  for (let i = 0; i < 4; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}
// 📢 Neueste Version immer oben – egal, in welcher Reihenfolge die Einträge oben stehen (Einträge einer Version bleiben in ihrer Reihenfolge)
const acNewsSorted = () => AC_NEWS.map((n, i) => [n, i]).sort((a, b) => acVerCmp(b[0][0], a[0][0]) || a[1] - b[1]).map((x) => x[0]);
// 💾 Merkzettel pro Gerät (Ansicht, Tipp gesehen …). Geht der Speicher nicht (privates Fenster), klappt alles trotzdem.
const AC_LS = "airfryer_control.";
const lsGet = (k, d) => { try { const v = localStorage.getItem(AC_LS + k); return v == null ? d : JSON.parse(v); } catch (_) { return d; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(AC_LS + k); else localStorage.setItem(AC_LS + k, JSON.stringify(v)); } catch (_) { /* egal */ } };
const inApp = () => { try { return location.pathname.startsWith("/airfryer_control/app/"); } catch (_) { return false; } };

// ---------- Hilfen ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const isDe = (hass) => String(hass?.language || "de").toLowerCase().startsWith("de");
const tr = (hass, de, en) => (isDe(hass) ? de : en);

const COLORS = {
  gart: "#43A047", vorheizen: "#FB8C00", vorgeheizt: "#FB8C00", wartet_auf_start: "#FB8C00", wartet_auf_sync: "#FB8C00",
  fertig: "#E53935", warmhalten: "#8E24AA", pausiert: "#FDD835", schublade_offen: "#FDD835", offline: "#616161",
};
// Platzhalter im Laufband-Text: wird beim Zeichnen durch das Fritteusen-Icon ersetzt
const FRY = "\u0001";
const TMR = "\u0002"; // Platzhalter für das Timer-Symbol (Kochmütze mit Wecker, wie in der Einkaufsliste)
const RUNNING = ["gart", "vorheizen", "pausiert", "warmhalten", "wartet_auf_sync"];
const STATE_TEXT = {
  aus: ["Aus", "Off"], bereit: ["Bereit", "Ready"], vorheizen: ["Heizt vor", "Preheating"],
  vorgeheizt: ["Vorgeheizt", "Preheated"], wartet_auf_start: ["Wartet auf Start", "Waiting for start"],
  wartet_auf_sync: ["Wartet auf Sync-Start", "Waiting for sync start"],
  gart: ["Gart", "Cooking"], pausiert: ["Pausiert", "Paused"], schublade_offen: ["Schublade offen", "Drawer open"],
  fertig: ["FERTIG!", "DONE!"], warmhalten: ["Hält warm", "Keeping warm"], offline: ["Offline", "Offline"],
  unbekannt: ["Unbekannt", "Unknown"],
};
const MODE_TEXT = {
  airfry: ["Heißluft", "Air fry", "mdi:fan"], roast: ["Braten", "Roast", "mdi:food-steak"],
  bake: ["Backen", "Bake", "mdi:muffin"], grill: ["Grillen", "Grill", "mdi:grill"],
  reheat: ["Aufwärmen", "Reheat", "mdi:microwave"], dry: ["Trocknen", "Dry", "mdi:water-off"],
  proof: ["Gären", "Proof", "mdi:baguette"], // 🗼 nur Turbo Tower Pro (CAF-DC111S)
  // 🍗 Dual Blaze CAF-P583S (ein Korb)
  broil: ["Überbacken", "Broil", "mdi:fire"], chicken: ["Hähnchen", "Chicken", "mdi:food-drumstick"],
  steak: ["Steak", "Steak", "mdi:food-steak"], seafood: ["Fisch", "Seafood", "mdi:fish"],
  veggies: ["Gemüse", "Veggies", "mdi:carrot"], fries: ["Pommes", "Fries", "mdi:french-fries"],
  frozen: ["Tiefkühl", "Frozen", "mdi:snowflake"],
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
// 🔎 Entitäten finden – über die Integration selbst (Plattform + translation_key), damit es in jeder
// Sprache und mit jedem Gerätenamen klappt (Issue #8). Nur wenn das nicht geht: alte Namenssuche.
const AC = "airfryer_control";
const ZONE_RE = /(?:^|_)(zone_\d+|grandzone)(?=_|$)/;
const zoneToken = (id) => (ZONE_RE.exec(String(id).split(".")[1] || "") || [])[1];
function findZones(hass) {
  const ents = hass.entities || {};
  const mine = Object.values(ents).filter((e) => e && e.platform === AC && e.translation_key && e.entity_id);
  const zones = [];
  if (mine.some((e) => e.translation_key === "zone_status")) {
    const sib = (dev, domain, tk, token) => {
      const e = mine.find((x) => x.device_id === dev && x.translation_key === tk && x.entity_id.startsWith(domain + ".") && zoneToken(x.entity_id) === token);
      return e && hass.states[e.entity_id] ? e.entity_id : undefined;
    };
    for (const e of mine) {
      if (e.translation_key !== "zone_status" || !e.entity_id.startsWith("sensor.") || !hass.states[e.entity_id]) continue;
      const obj = e.entity_id.split(".")[1];
      const m = ZONE_RE.exec(obj);
      if (!m) continue;
      const token = m[1];
      const key = obj.slice(0, obj.indexOf(token, m.index) + token.length);
      const dev = e.device_id;
      zones.push({
        key,
        state: e.entity_id,
        finish: sib(dev, "sensor", "zone_fertig_um", token) || `sensor.${key}_fertig_um`,
        mode: sib(dev, "select", "zone_programm_waehlen", token) || `select.${key}_programm`,
        temp: sib(dev, "number", "zone_temperatur", token) || `number.${key}_temperatur_einstellen`,
        time: sib(dev, "number", "zone_garzeit", token) || `number.${key}_garzeit_einstellen`,
        sw: sib(dev, "switch", "zone_senden", token),
        name: zoneName(hass, key, hass.states[e.entity_id]),
      });
    }
  } else {
    // Alte Namenssuche (z. B. ohne Geräte-Zuordnung): deutsch „…_zustand“ und englisch „…_status“
    const re = /^sensor\.(.+_(?:zone_\d+|grandzone))_(?:zustand|status)$/;
    for (const id of Object.keys(hass.states)) {
      const m = re.exec(id);
      if (!m) continue;
      const reg = ents[id];
      if (reg && reg.platform && reg.platform !== AC) continue;
      const key = m[1];
      const sw = [`switch.${key}_senden_beenden`, `switch.${key}_send_stop`, `switch.${key}_gart`].find((x) => hass.states[x]);
      const pick = (...ids) => ids.find((x) => hass.states[x]) || ids[0];
      zones.push({
        key,
        state: id,
        finish: pick(`sensor.${key}_fertig_um`, `sensor.${key}_done_at`),
        mode: pick(`select.${key}_programm`, `select.${key}_program`),
        temp: pick(`number.${key}_temperatur_einstellen`, `number.${key}_set_temperature`),
        time: pick(`number.${key}_garzeit_einstellen`, `number.${key}_set_cooking_time`),
        sw,
        name: zoneName(hass, key, hass.states[id]),
      });
    }
  }
  const order = (z) => (/grandzone$/.test(z.key) ? 99 : Number((/zone_(\d+)$/.exec(z.key) || [0, 50])[1]));
  return zones.sort((a, b) => order(a) - order(b));
}
// 🟢 Online-Sensor der Fritteuse (gleiches Gerät wie die Zonen), sonst der alte Name
function findOnline(hass, zones) {
  const mine = Object.values(hass.entities || {}).filter((e) => e && e.platform === AC && e.translation_key === "online" && hass.states[e.entity_id]);
  const dev = zones && zones[0] ? hass.entities?.[zones[0].state]?.device_id : undefined;
  const e = mine.find((x) => dev && x.device_id === dev) || mine[0];
  if (e) return hass.states[e.entity_id];
  const byName = Object.keys(hass.states).find((id) => /^binary_sensor\..+_online$/.test(id) && hass.entities?.[id]?.platform === AC);
  return hass.states[byName] || hass.states["binary_sensor.cosori_online"];
}
function zoneName(hass, key, st) {
  if (/grandzone$/.test(key)) return "Grandzone";
  const n = /zone_(\d+)$/.exec(key);
  return n ? tr(hass, `Zone ${n[1]}`, `Zone ${n[1]}`) : (st?.attributes?.friendly_name || key);
}

// ---------- 🍟 Maskottchen Airfryer (wie Sparschwein, Einkaufswagen und Kegelfigur) ----------
function acMood(hass, zones, now = new Date()) {
  const st = zones.map((z) => hass.states[z.state]?.state);
  if (st.includes("fertig")) return "done";                  // 🔔 Fertig!
  if (st.some((s) => RUNNING.includes(s))) return "happy";   // 😄 gart gerade
  if (findOnline(hass, zones)?.state === "off" || st.includes("offline")) return "sleep";
  const hr = now.getHours();
  if (hr >= 22 || hr < 6) return "sleep";                    // 😴 nachts
  return "calm";
}
function acEaster(y) { // 🐣 Gauß'sche Osterformel (wie bei der Einkaufsliste)
  const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
  return new Date(y, Math.floor((h + l - 7 * m + 114) / 31) - 1, ((h + l - 7 * m + 114) % 31) + 1);
}
function acDeco(now = new Date()) { // 👗 gleiche Kostüm-Tage wie bei den anderen Maskottchen
  const m = now.getMonth() + 1, day = now.getDate();
  if ((m === 12 && day === 31) || (m === 1 && day === 1)) return "party";
  if (m === 12 && day <= 26) return "santa";
  const today = new Date(now.getFullYear(), now.getMonth(), day), diff = Math.round((today - acEaster(now.getFullYear())) / 86400000);
  if (diff >= -3 && diff <= 1) return "bunny";
  if ((m === 10 && day >= 17) || (m === 11 && day <= 7)) return "pumpkin";
  return m >= 3 && m <= 5 ? "spring" : m >= 6 && m <= 8 ? "summer" : m >= 9 && m <= 11 ? "autumn" : "winter";
}
function acMascotSvg(mood, deco = "") {
  const k = "currentColor";
  const eyes = mood === "sleep" ? `<path d="M11.6 13.6q1.2 1 2.4 0M18 13.6q1.2 1 2.4 0" fill="none" stroke="${k}" stroke-width="1.1" stroke-linecap="round"/>`
    : mood === "done" ? `<path d="M11.6 14l1.2-1.6 1.2 1.6M18 14l1.2-1.6 1.2 1.6" fill="none" stroke="${k}" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/>`
    : `<circle cx="12.8" cy="13.4" r="1.05" fill="${k}"/><circle cx="19.2" cy="13.4" r="1.05" fill="${k}"/>`;
  const mouth = { happy: `<path d="M14 16.4q2 2 4 0" fill="none" stroke="${k}" stroke-width="1.1" stroke-linecap="round"/>`,
    done: `<ellipse cx="16" cy="17" rx="1.6" ry="1.3" fill="${k}"/>`,
    calm: `<path d="M14.6 16.6q1.4.9 2.8 0" fill="none" stroke="${k}" stroke-width="1.1" stroke-linecap="round"/>`,
    sleep: `<path d="M15 16.8q1 .6 2 0" fill="none" stroke="${k}" stroke-width="1" stroke-linecap="round"/>` }[mood] || "";
  const extra = mood === "happy" ? `<path d="M11 2.6q-1.2-1.4 0-2.8M16 2q-1.2-1.4 0-2.8M21 2.6q-1.2-1.4 0-2.8" fill="none" stroke="#90a4ae" stroke-width="1" stroke-linecap="round" opacity=".8"/>`
    : mood === "done" ? `<path d="M27 3.5l.7 1.6 1.6.7-1.6.7-.7 1.6-.7-1.6-1.6-.7 1.6-.7z" fill="#fdd835"/><text x="26" y="12" font-size="5" font-weight="700" fill="#e53935">!</text>`
    : mood === "sleep" ? `<text x="24" y="5" font-size="5" font-weight="700" fill="${k}" opacity=".7">z</text><text x="27.4" y="2" font-size="3.6" font-weight="700" fill="${k}" opacity=".5">z</text>` : "";
  const hat = { santa: `<path d="M9.6 4.6q6-8 12.8-.6l-1.8 1.2z" fill="#e53935"/><rect x="8.8" y="3.6" width="14.4" height="2.2" rx="1.1" fill="#fff"/><circle cx="23" cy="2.6" r="1.5" fill="#fff"/>`,
    party: `<path d="M13.4 4l2.6-6.4 2.6 6.4z" fill="#ab47bc" stroke="#6a1b9a" stroke-width=".5"/><circle cx="16" cy="-2.6" r="1.1" fill="#fdd835"/>`,
    pumpkin: `<g transform="translate(3.4 25.4)"><ellipse cx="0" cy="0" rx="3.8" ry="3.1" fill="#fb8c00" stroke="#e65100" stroke-width=".6"/><path d="M0-3.1q-1.6 3.1 0 6.2M-2-2.6q-1.7 2.6 0 5.2M2-2.6q1.7 2.6 0 5.2" fill="none" stroke="#e65100" stroke-width=".5"/><path d="M0-3.1v-1.4q.8-.7 1.8-.5" fill="none" stroke="#43a047" stroke-width="1.1" stroke-linecap="round"/></g>`,
    bunny: `<ellipse cx="12.6" cy="0" rx="1.5" ry="4.2" transform="rotate(-12 12.6 4)" fill="#f8bbd0" stroke="${k}" stroke-width=".8"/><ellipse cx="19.4" cy="0" rx="1.5" ry="4.2" transform="rotate(12 19.4 4)" fill="#f8bbd0" stroke="${k}" stroke-width=".8"/>`,
    spring: `<g transform="translate(22.4 4) scale(1.15)"><circle cx="0" cy="-1.5" r="1.2" fill="#f48fb1"/><circle cx="1.5" cy="0" r="1.2" fill="#f48fb1"/><circle cx="0" cy="1.5" r="1.2" fill="#f48fb1"/><circle cx="-1.5" cy="0" r="1.2" fill="#f48fb1"/><circle cx="0" cy="0" r="1" fill="#fdd835"/></g>`,
    summer: `<rect x="10.6" y="12" width="4.2" height="2.8" rx="1.1" fill="#263238"/><rect x="17.2" y="12" width="4.2" height="2.8" rx="1.1" fill="#263238"/><path d="M14.8 12.8h2.4" stroke="#263238" stroke-width=".8" stroke-linecap="round"/>`,
    autumn: `<g transform="translate(9.4 4.2) rotate(-22) scale(1.15)"><path d="M0 0q3.2-4.2 6.4.2q-3.2 3.4-6.4-.2z" fill="#ef6c00"/><path d="M.2-.2l4.2-.6" stroke="#8d4a00" stroke-width=".5"/></g>`,
    winter: `<path d="M7.6 20.4q8.4 2.6 16.8 0" fill="none" stroke="#e53935" stroke-width="2.4" stroke-linecap="round"/><path d="M21.6 21q1.4 2.8.6 5.6" fill="none" stroke="#c62828" stroke-width="2" stroke-linecap="round"/><path d="M11 21.2l.5.4M15.6 21.8v.5M20 21.2l-.5.4" stroke="#fff" stroke-width=".8" stroke-linecap="round"/>` }[deco] || "";
  return `<svg class="ac-mascot ${mood}" viewBox="0 0 32 30" width="34" height="32" style="overflow:visible" aria-hidden="true">
    <rect x="6" y="4.6" width="20" height="23.4" rx="6" fill="#eceff1" stroke="${k}" stroke-width="1.3"/>
    <rect x="9.4" y="7" width="13.2" height="2.4" rx="1.2" fill="#263238"/><circle cx="20.4" cy="8.2" r=".7" fill="#ff7043"/>
    <rect x="8.6" y="10.8" width="14.8" height="9.6" rx="3.4" fill="#fff" stroke="${k}" stroke-width=".9"/>
    <rect x="13" y="22.6" width="6" height="2.4" rx="1.2" fill="#90a4ae" stroke="${k}" stroke-width=".7"/>
    ${mood === "happy" || mood === "done" ? `<circle cx="10.6" cy="16.4" r=".9" fill="#ec407a" opacity=".45"/><circle cx="21.4" cy="16.4" r=".9" fill="#ec407a" opacity=".45"/>` : ""}
    ${eyes}${mouth}${extra}${hat}</svg>`;
}

const BASE_CSS = `
  :host { display:block; }
  ha-card { overflow:hidden; }
  .ac-head { display:flex; align-items:center; gap:10px; padding:14px 16px 6px; }
  .ac-head ha-icon { color:var(--primary-color); --mdc-icon-size:26px; }
  .ac-logo { width:30px; height:30px; border-radius:8px; flex:none; }
  .ac-masc { flex:none; display:flex; color:var(--primary-text-color); }
  .ac-mascot.happy { animation:acwob 2.6s ease-in-out infinite; transform-origin:50% 90%; }
  .ac-mascot.done { animation:achop .7s ease-out infinite; }
  @keyframes acwob { 0%,100% { transform:rotate(-3deg); } 50% { transform:rotate(3deg); } }
  @keyframes achop { 0%,100% { transform:translateY(0); } 40% { transform:translateY(-3px); } }
  @media (prefers-reduced-motion: reduce) { .ac-mascot { animation:none !important; } }
  .ac-head h2 { margin:0; font-size:1.1rem; font-weight:600; flex:1; }
  /* 🟢 Leiste über der Karte – genau wie bei der Einkaufsliste */
  .ac-top { display:flex; align-items:center; gap:8px; margin:0 4px 8px; font-size:13px; color:var(--secondary-text-color); }
  .ac-pill { border-radius:999px; padding:2px 10px; background:color-mix(in srgb, var(--success-color,#43a047) 18%, transparent); color:var(--primary-text-color); white-space:nowrap; }
  .ac-pill.off { background:color-mix(in srgb, var(--error-color,#db4437) 20%, transparent); }
  .ac-greet { flex:1; min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; text-align:center; color:var(--primary-text-color); }
  .ac-top .ac-ibtn { padding:2px; } .ac-top .ac-ibtn ha-icon { --mdc-icon-size:20px; }
  .ac-ver { opacity:.8; }
  .ac-badge { background:var(--primary-color,#03a9f4); color:var(--text-primary-color,#fff); border-radius:999px; padding:1px 9px; font-size:.75em; font-weight:600; }
  /* 📖 Knopfreihe unter der Karte – wie bei der Einkaufsliste */
  .ac-foot { display:flex; justify-content:center; gap:10px; margin:14px 6px 8px; font-size:13px; color:var(--secondary-text-color); }
  .ac-foot button { font:inherit; color:inherit; background:none; border:1px solid var(--divider-color, rgba(127,127,127,.3)); border-radius:12px; padding:8px 18px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; }
  .ac-foot button span { text-decoration:underline; }
  .ac-foot button ha-icon { --mdc-icon-size:18px; }
  .ac-guide h4 { margin:14px 0 4px; } .ac-guide p { margin:4px 0; line-height:1.45; }
  .ac-dot { width:10px; height:10px; border-radius:50%; background:#43A047; }
  .ac-dot.off { background:#9e9e9e; }
  .ac-ibtn { background:none; border:none; color:var(--secondary-text-color); cursor:pointer; padding:6px; border-radius:50%; display:flex; }
  .ac-ibtn:hover { background:rgba(127,127,127,.15); }
  .ac-ibtn ha-icon { --mdc-icon-size:22px; }
  .ac-zones { display:flex; flex-direction:column; gap:4px; padding:4px 10px 8px; }
  /* 🧺 Zeilen wie die Artikel der Einkaufsliste: abgerundet, Farbstreifen links */
  .ac-row { display:flex; align-items:center; gap:12px; padding:8px 10px 8px 10px; border-left:4px solid var(--c, #9e9e9e); border-radius:12px; margin:0; cursor:pointer; transition:background .2s; }
  .ac-row:hover { background:color-mix(in srgb, var(--primary-color) 6%, transparent); }
  .ac-row.open { background:color-mix(in srgb, var(--primary-color) 10%, transparent); }
  .ac-edit { margin:2px 0 8px; padding:12px; border:1px solid var(--divider-color, rgba(127,127,127,.3)); border-left:4px solid var(--c, #9e9e9e); border-radius:12px; }
  .ac-edit .ac-modes { margin-top:0; }
  .ac-close { display:block; margin:10px auto 0; font:inherit; font-size:.9em; color:var(--secondary-text-color); background:none; border:1px solid var(--divider-color, rgba(127,127,127,.3)); border-radius:12px; padding:6px 16px; cursor:pointer; }
  .ac-row > ha-icon { color:var(--c, #9e9e9e); --mdc-icon-size:30px; flex:none; }
  .ac-txt { flex:1; min-width:0; }
  .ac-name { font-weight:600; }
  .ac-state { color:var(--c, var(--secondary-text-color)); font-size:.95em; }
  .ac-sub { opacity:.75; font-size:.85em; }
  .ac-go { width:46px; height:46px; border-radius:12px; border:none; cursor:pointer; background:var(--b, #43A047); color:#fff; display:flex; align-items:center; justify-content:center; flex:none; }
  .ac-go:disabled { opacity:.4; cursor:default; }
  .ac-go ha-icon { --mdc-icon-size:22px; }
  .ac-empty { padding:16px; color:var(--secondary-text-color); }
  .ac-over { position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:9; display:flex; align-items:center; justify-content:center; padding:12px; }
  .ac-dlg { background:var(--card-background-color, #fff); color:var(--primary-text-color); border-radius:16px; width:min(420px,100%); max-height:92vh; overflow:auto; padding:16px; box-shadow:0 8px 30px rgba(0,0,0,.4); }
  .ac-dlg h3 { margin:0 0 4px; display:flex; align-items:center; gap:8px; }
  .ac-dlg h3 span { flex:1; }
  .ac-modes { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:12px 0; }
  .ac-mode { border:1.5px solid var(--divider-color, rgba(127,127,127,.35)); border-radius:12px; background:none; color:inherit; padding:10px 4px; cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:4px; font:inherit; font-size:.85em; }
  .ac-mode.on { border-color:var(--primary-color); background:color-mix(in srgb, var(--primary-color) 15%, transparent); color:var(--primary-color); font-weight:600; } /* wie die Symbol-Auswahl der Einkaufsliste */
  .ac-mode ha-icon { --mdc-icon-size:24px; }
  .ac-step { display:flex; align-items:center; justify-content:space-between; gap:8px; margin:10px 0; }
  .ac-step label { flex:1; opacity:.8; }
  .ac-step button { width:44px; height:44px; border-radius:12px; border:1px solid var(--divider-color, rgba(127,127,127,.3)); background:none; color:inherit; font-size:1.4rem; cursor:pointer; }
  .ac-step b { min-width:84px; text-align:center; font-size:1.3rem; }
  .ac-big { width:100%; border:none; border-radius:12px; padding:14px; font-size:1.05rem; font-weight:700; color:#fff; background:var(--b, #43A047); cursor:pointer; margin-top:8px; }
  .ac-sync { margin:10px 0 0; padding:10px 12px; border-radius:12px; background:var(--secondary-background-color, rgba(127,127,127,.12)); font-size:.92em; }
  .ac-sync b { color:var(--primary-color); }
  .ac-match { width:100%; border:2px solid var(--primary-color); background:none; color:var(--primary-color); border-radius:12px; padding:10px; font:inherit; font-weight:600; cursor:pointer; margin-top:10px; }
  .ac-pair { display:flex; gap:8px; }
  .ac-pair .ac-match { flex:1; }
  .ac-match:disabled { opacity:.4; cursor:default; }
  .ac-note { font-size:.85em; opacity:.7; margin:6px 0 0; text-align:center; }
  /* ⓘ Hilfe zum Antippen (wie in der Einkaufsliste): kleines i neben dem Feld statt Textwand */
  .finfo { flex:none; width:20px; height:20px; padding:0; border-radius:50%; border:1.5px solid var(--primary-color, #03a9f4); background:none; color:var(--primary-color, #03a9f4); font:700 11px/1 serif; font-style:italic; cursor:pointer; }
  .finfo[aria-expanded="true"] { background:var(--primary-color, #03a9f4); color:#fff; }
  .ac-flab { display:flex; align-items:center; gap:6px; margin:12px 0 0; font-size:.9em; opacity:.85; }
  .ac-hint { font-size:.85em; margin:6px 0 0; padding:8px 10px; border-radius:10px; background:var(--secondary-background-color, rgba(127,127,127,.12)); }
  .ac-hint[hidden] { display:none; }
  .ac-step label { display:flex; align-items:center; gap:6px; }
  .ac-step button.finfo { width:20px; height:20px; border-radius:50%; border:1.5px solid var(--primary-color, #03a9f4); font:700 11px/1 serif; font-style:italic; color:var(--primary-color, #03a9f4); } /* nicht so groß wie die −/+ Knöpfe */
  .ac-step button.finfo[aria-expanded="true"] { background:var(--primary-color, #03a9f4); color:#fff; }
  .ac-withinfo { display:flex; align-items:center; gap:8px; }
  .ac-ol { margin:4px 0 8px; padding-left:22px; } .ac-ol li { margin:2px 0; }
  .ac-url { display:flex; gap:8px; margin:6px 0; } .ac-url input { flex:1; min-width:0; padding:8px 10px; border-radius:10px; border:1px solid var(--divider-color, #ccc); background:var(--card-background-color, #fff); color:var(--primary-text-color); font:inherit; }
  .ac-url button { border:0; border-radius:10px; padding:8px 12px; background:var(--primary-color, #03a9f4); color:#fff; font:inherit; font-weight:600; cursor:pointer; }
  .ac-withinfo > :first-child { flex:1; }
  .elcredits { text-align:center; } .elcredits p { margin:8px 0; }
  .ellogo { background:#fff; border-radius:16px; padding:10px; display:inline-block; max-width:100%; box-shadow:0 1px 4px rgba(0,0,0,.12); }
  .ellogo img { display:block; max-width:100%; width:200px; height:auto; }
  .elcbtns { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin:12px 0; }
  .elcbtn { color:var(--primary-text-color); background:var(--secondary-background-color, rgba(127,127,127,.12)); border-radius:12px; padding:10px 14px; text-decoration:none; font-weight:500; }
  .elcbtn.pp { display:inline-flex; align-items:center; gap:8px; background:#0070BA; color:#fff; border:2px solid #003087; font-weight:700; }
  .elcbtn.pp svg { width:20px; height:20px; flex:none; }
  .elcsmall { opacity:.7; font-size:.9em; }
  /* 👁️ Ansicht pro Gerät: Schriftgröße (zoom) und Hell/Dunkel (eigene Farben nur für die Karte) */
  ha-card { display:block; }
  .ac-sz-s { zoom:.9; } .ac-sz-l { zoom:1.15; }
  ha-card.ac-th-light { --ha-card-background:#fff; --card-background-color:#fff; --primary-text-color:#212121; --secondary-text-color:#6b6b6b; --divider-color:rgba(0,0,0,.14); --secondary-background-color:#eceff1; background:#fff; color:#212121; color-scheme:light; }
  ha-card.ac-th-dark { --ha-card-background:#1c1c1c; --card-background-color:#1c1c1c; --primary-text-color:#e6e6e6; --secondary-text-color:#a0a0a0; --divider-color:rgba(255,255,255,.14); --secondary-background-color:#2a2a2a; background:#1c1c1c; color:#e6e6e6; color-scheme:dark; }
  /* 📄 Seiten mit ← (Anleitung, Einstellungen, Credits, Neuigkeiten) – wie bei der Einkaufsliste */
  .ac-pghead { display:flex; align-items:center; gap:10px; padding:10px 12px; border-bottom:3px solid var(--pc, var(--primary-color)); }
  .ac-pghead h2 { margin:0; font-size:1.15rem; flex:1; }
  .ac-pgic { width:36px; height:36px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:20px; background:color-mix(in srgb, var(--pc, var(--primary-color)) 18%, transparent); flex:none; }
  .ac-back { background:none; border:0; color:var(--primary-text-color); cursor:pointer; padding:6px; border-radius:50%; display:flex; }
  .ac-back:hover { background:rgba(127,127,127,.15); }
  .ac-back ha-icon { --mdc-icon-size:26px; }
  .ac-pgbody { padding:10px 14px 16px; line-height:1.45; }
  .ac-pgsub { color:var(--secondary-text-color); margin:0 0 10px; font-size:.92em; }
  /* 🗂️ Kapitel/Gruppen zum Aufklappen: ein Kasten, buntes Symbol, Pfeil rechts */
  .ac-sec { border:1px solid var(--divider-color, rgba(127,127,127,.3)); border-radius:12px; margin:10px 0 0; overflow:hidden; }
  .ac-sec summary { cursor:pointer; padding:10px 12px; font-weight:600; list-style:none; display:flex; align-items:center; gap:12px; background:color-mix(in srgb, var(--primary-text-color, #000) 3%, transparent); }
  .ac-sec summary::-webkit-details-marker { display:none; }
  .ac-sec summary::after { content:""; flex:none; width:8px; height:8px; margin:0 6px 4px auto; border-right:2px solid var(--secondary-text-color); border-bottom:2px solid var(--secondary-text-color); transform:rotate(45deg); transition:transform .2s; }
  .ac-sec[open] summary::after { transform:rotate(225deg); margin-bottom:-4px; }
  .ac-sec[open] summary { border-bottom:1px solid var(--divider-color, rgba(127,127,127,.3)); }
  .ac-sec[hidden] { display:none; }
  .ac-sic { flex:none; width:36px; height:36px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:18px; background:color-mix(in srgb, var(--gc, #607d8b) 22%, transparent); }
  .ac-stt { flex:1; min-width:0; } .ac-stt b { display:block; } .ac-stt small { display:block; font-weight:400; font-size:.82em; color:var(--secondary-text-color); }
  .ac-sec > div { padding:8px 12px 12px; }
  .ac-sec p { margin:6px 0; }
  .ac-search { display:flex; align-items:center; gap:4px; flex-wrap:wrap; }
  .ac-q { flex:1; min-width:0; font:inherit; padding:10px 12px; border-radius:12px; border:1px solid var(--divider-color, rgba(127,127,127,.4)); background:var(--card-background-color, #fff); color:var(--primary-text-color); }
  .ac-none { flex-basis:100%; color:var(--secondary-text-color); margin:8px 2px 0; }
  .ac-none[hidden] { display:none; }
  /* ⚙️ Einstellungen: Zeilen mit Schalter oder Auswahl */
  .ac-set { display:flex; align-items:center; gap:10px; padding:8px 0; border-bottom:1px solid var(--divider-color, rgba(127,127,127,.2)); flex-wrap:wrap; }
  .ac-set:last-child { border-bottom:0; }
  .ac-set > span { flex:1; min-width:140px; } .ac-set small { display:block; color:var(--secondary-text-color); font-size:.82em; }
  .ac-seg { display:inline-flex; border:1px solid var(--divider-color, rgba(127,127,127,.35)); border-radius:12px; overflow:hidden; }
  .ac-seg button { font:inherit; font-size:.9em; border:0; background:none; color:inherit; padding:7px 11px; cursor:pointer; }
  .ac-seg button + button { border-left:1px solid var(--divider-color, rgba(127,127,127,.35)); }
  .ac-seg button.on { background:var(--primary-color, #03a9f4); color:#fff; font-weight:600; }
  .ac-sw { width:22px; height:22px; accent-color:var(--primary-color, #03a9f4); cursor:pointer; }
  /* ⚙️ Einstellungen 1:1 wie bei der Einkaufsliste (lgbox / lgroup / lrow / ic / tgl) */
  .ac-srch { display:flex; align-items:center; gap:6px; margin:0 0 4px; }
  .ac-srch ha-icon { color:var(--secondary-text-color); flex:none; }
  .ac-srch input { flex:1; min-width:0; font:inherit; padding:9px 14px; border-radius:21px; border:1px solid var(--divider-color, rgba(127,127,127,.4)); background:var(--card-background-color, #fff); color:var(--primary-text-color); }
  .ac-lgbox { margin:10px 0 0; border:1px solid var(--divider-color, rgba(127,127,127,.25)); border-radius:12px; overflow:hidden; }
  .ac-lgroup { display:flex; align-items:center; gap:12px; width:100%; margin:0; padding:10px 12px; box-sizing:border-box; font:inherit; font-size:1em; color:var(--primary-text-color); background:color-mix(in srgb, var(--primary-text-color, #000) 3%, transparent); border:0; cursor:pointer; text-align:left; }
  .ac-lgroup[aria-expanded="true"] { border-bottom:1px solid var(--divider-color, rgba(127,127,127,.25)); }
  .ac-lgroup b { display:block; font-weight:600; }
  .ac-lgroup small, .ac-lrow small { display:block; color:var(--secondary-text-color); font-size:.8em; font-weight:400; }
  .ac-gem { width:36px; height:36px; flex:none; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:18px; background:color-mix(in srgb, var(--primary-text-color, #000) 7%, transparent); }
  .ac-grow { flex:1 1 auto; min-width:0; }
  .ac-chev { flex:none; color:var(--secondary-text-color); }
  .ac-lrow { display:flex; align-items:center; gap:12px; width:100%; box-sizing:border-box; text-align:left; padding:10px 12px; margin:3px 0; border-radius:12px; cursor:pointer; border:1px solid var(--divider-color, rgba(127,127,127,.25)); background:var(--secondary-background-color, rgba(127,127,127,.06)); color:var(--primary-text-color); font:inherit; }
  .ac-lrow:hover { border-color:var(--primary-color, #03a9f4); }
  .ac-lrow b { display:block; font-weight:500; }
  .ac-lrow .ac-chev { opacity:.5; }
  .ac-lgbox .ac-lrow { margin:0 0 0 4px; width:calc(100% - 4px); border:0; border-radius:0; border-top:1px solid var(--divider-color, rgba(127,127,127,.25)); background:none; }
  .ac-lgbox .ac-lgroup + .ac-lrow { border-top:0; }
  .ac-lgbox .ac-lrow:hover { background:color-mix(in srgb, var(--primary-color, #03a9f4) 6%, transparent); }
  .ac-lgbox div.ac-lrow, div.ac-lrow { padding:0 12px 0 0; cursor:default; }
  .ac-lmain { display:flex; align-items:center; gap:12px; flex:1 1 auto; min-width:0; padding:10px 0 10px 12px; border:0; background:none; color:inherit; font:inherit; text-align:left; cursor:pointer; }
  .ac-ic { --ic:#607d8b; width:36px; height:36px; flex:none; border-radius:12px; display:flex; align-items:center; justify-content:center; background:var(--ic); color:#fff; }
  .ac-ic ha-icon { --mdc-icon-size:20px; color:#fff; }
  .ac-tgl { flex:none; width:40px; height:22px; padding:0; border:0; border-radius:12px; background:#bdbdbd; position:relative; cursor:pointer; transition:background .15s; }
  .ac-tgl > span { position:absolute; top:2px; left:2px; width:18px; height:18px; border-radius:50%; background:#fff; box-shadow:0 1px 2px rgba(0,0,0,.3); transition:left .15s; }
  .ac-tgl[aria-pressed="true"] { background:var(--primary-color, #03a9f4); }
  .ac-tgl[aria-pressed="true"] > span { left:20px; }
  .ac-tgl:disabled { opacity:.5; cursor:default; }
  .ac-swline { margin:10px 0; }
  .ac-pghead .ac-ic { width:36px; height:36px; }
  .ac-num { width:90px; font:inherit; padding:7px 10px; border-radius:10px; border:1px solid var(--divider-color, rgba(127,127,127,.4)); background:var(--card-background-color, #fff); color:var(--primary-text-color); }
  .ac-lbtn { display:flex; align-items:center; gap:10px; width:100%; margin:8px 0 0; font:inherit; text-align:left; color:var(--primary-text-color); background:var(--secondary-background-color, rgba(127,127,127,.12)); border:0; border-radius:12px; padding:10px 12px; cursor:pointer; }
  .ac-msg { margin:8px 0 0; font-size:.9em; }
  /* 📢 / 💡 Kästen über den Zonen */
  .ac-box { margin:4px 12px 6px; padding:10px 12px; border-radius:12px; border:1px solid var(--bc, #fb8c00); background:color-mix(in srgb, var(--bc, #fb8c00) 10%, transparent); font-size:.92em; }
  .ac-box ul { margin:4px 0 0; padding-left:20px; } .ac-box li { margin:2px 0; }
  .ac-box p { margin:4px 0 0; }
  .ac-bbtns { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
  .ac-bbtns button { font:inherit; font-size:.92em; border:1px solid var(--divider-color, rgba(127,127,127,.35)); background:var(--card-background-color, #fff); color:var(--primary-text-color); border-radius:12px; padding:6px 12px; cursor:pointer; }
  .ac-bbtns button.pri { background:var(--bc, #fb8c00); border-color:var(--bc, #fb8c00); color:#fff; font-weight:600; }
  .ac-news h4 { margin:12px 0 2px; } .ac-news ul { margin:2px 0; padding-left:20px; }
`;

function creditsHtml(hass) {
  const t = (de, en) => tr(hass, de, en);
  return `<div class="elcredits" translate="no">
    <div class="ellogo"><img src="${AC_BASE}/mister-m.webp?v=${esc(AC_VERSION)}" alt="Mister-M" loading="lazy"></div>
    <p><img src="${AC_BASE}/icon.png?v=${esc(AC_VERSION)}" alt="" width="56" height="56" style="border-radius:14px;vertical-align:middle;margin-right:8px"><b>Airfryer Control</b> v${esc(AC_VERSION)}</p>
    <p>${t("Gemacht von <b>Mister-M</b> – mit Hilfe von Claude 🤖", "Made by <b>Mister-M</b> – with help from Claude 🤖")}</p>
    <p>${t("Ich versuche, Updates und Fehler-Korrekturen zeitnah zu erledigen.", "I try to ship updates and fixes promptly.")}</p>
    <p class="elcsmall">📅 ${t("Neue offizielle Versionen kommen immer sonntags. An den anderen Tagen gibt es nur Test-Versionen (Beta) – die siehst du in HACS (ab Home Assistant 2026.11: Einstellungen › Marketplace) unter „Beta-Versionen anzeigen“.", "New official versions always come out on Sundays. On the other days there are only test versions (beta) – you see them in HACS (from Home Assistant 2026.11: Settings › Marketplace) under “Show beta versions”.")}</p>
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

// 👋 Gruß in der Leiste oben – dieselben Zeiten wie bei der Einkaufsliste
function acGreeting(hass, now = new Date()) {
  const hr = now.getHours();
  const de = hr >= 22 || hr < 5 ? "🌙 Gute Nacht" : hr < 10 ? "☀️ Guten Morgen" : hr < 12 ? "🍽️ Mahlzeit" : hr < 18 ? "👋 Grüß dich" : "🌆 Guten Abend";
  const en = hr >= 22 || hr < 5 ? "🌙 Good night" : hr < 12 ? "☀️ Good morning" : hr < 18 ? "👋 Hi" : "🌆 Good evening";
  const first = String(hass?.user?.name || "").trim().split(/\s+/)[0];
  const base = tr(hass, de, en);
  return first ? `${base}, ${first}` : base;
}
// 📱 So kommt die Handy-App auf den Startbildschirm (wie bei der Einkaufsliste)
function acAppUrl() {
  try { return `${location.origin}/airfryer_control/app/`; } catch (_) { return "/airfryer_control/app/"; }
}
function acAppGuideHtml(hass) {
  const t = (d, e) => tr(hass, d, e);
  if (inApp()) return ""; // wir sind schon in der App 😉
  const url = acAppUrl();
  return `<p>${t("Laufband und Zonen gibt es auch als <b>eigene kleine App</b> auf dem Startbildschirm – ohne App-Store.", "Ticker and zones also come as a <b>small app of their own</b> on your home screen – no app store needed.")}</p>
    <ol class="ac-ol"><li>${t("Adresse kopieren", "Copy the address")}</li>
      <li>${t("Im Handy-<b>Browser</b> öffnen (Chrome/Safari, nicht in der HA-App)", "Open it in your phone's <b>browser</b> (Chrome/Safari, not the HA app)")}</li>
      <li>${t("Mit deinem Home-Assistant-Benutzer anmelden", "Log in with your Home Assistant user")}</li>
      <li>${t("Browser-Menü → <b>„Zum Startbildschirm hinzufügen“</b>", "Browser menu → <b>“Add to Home screen”</b>")}</li></ol>
    <div class="ac-url"><input readonly value="${esc(url)}" translate="no" aria-label="${esc(t("Adresse der App", "App address"))}"><button type="button" data-copyapp>📋 ${t("Kopieren", "Copy")}</button></div>
    <p class="elcsmall">⚠️ ${t("Nicht das Dashboard als Verknüpfung speichern! Richtig ist es, wenn die Adresse auf <b>/airfryer_control/app/</b> endet. Von unterwegs: deine externe Adresse (z. B. Nabu Casa) + <b>/airfryer_control/app/</b>. Für „Zum Startbildschirm“ braucht der Browser meist eine https-Adresse.", "Don't save the dashboard as a shortcut! It's right when the address ends in <b>/airfryer_control/app/</b>. From outside: your external address (e.g. Nabu Casa) + <b>/airfryer_control/app/</b>. For “Add to Home screen” the browser usually needs an https address.")}</p>`;
}
// 🗂️ Ein Kapitel / eine Gruppe zum Aufklappen (wie Anleitung und Einstellungen der Einkaufsliste)
const acSec = (icon, title, body, color = "#607d8b", sub = "", key = "") =>
  `<details class="ac-sec" style="--gc:${color}"${key ? ` data-sec="${esc(key)}"` : ""}><summary><span class="ac-sic">${icon}</span><span class="ac-stt"><b>${title}</b>${sub ? `<small>${sub}</small>` : ""}</span></summary><div>${body}</div></details>`;
// 📖 Anleitung: Kapitel zum Aufklappen + Suchfeld (eigene Seite mit ←)
function acGuideHtml(hass) {
  const t = (d, e) => tr(hass, d, e);
  const app = acAppGuideHtml(hass);
  return `<p class="ac-pgsub">${t("Tippe ein Kapitel an – oder such einfach nach einem Wort.", "Tap a chapter – or just search for a word.")}</p>
    <div class="ac-search"><input type="search" class="ac-q" data-q placeholder="${esc(t("🔎 In dieser Anleitung suchen, z. B. Sync", "🔎 Search this guide, e.g. sync"))}" aria-label="${esc(t("In dieser Anleitung suchen", "Search this guide"))}" autocomplete="off" enterkeyhint="search"><p class="ac-none" data-none hidden>${t("Nichts gefunden 🤷 – versuch ein anderes Wort.", "Nothing found 🤷 – try another word.")}</p></div>
    ${acSec("🍟", t("Zonen", "Zones"), `<p>${t("Jede Zeile ist eine Zone deiner Fritteuse. Farbe und Text zeigen, was sie gerade macht: <b>grün</b> = gart, <b>orange</b> = wartet auf Start, <b>rot</b> = fertig, <b>grau</b> = bereit oder aus.", "Each row is one zone of your air fryer. Colour and text show what it is doing: <b>green</b> = cooking, <b>orange</b> = waiting for start, <b>red</b> = done, <b>grey</b> = ready or off.")}</p>`, "#43a047", t("Was die Farben bedeuten", "What the colours mean"))}
    ${acSec("🎛️", t("Programm einstellen", "Set a program"), `<p>${t("Zeile antippen → darunter klappen Programm, Temperatur und Zeit auf (nochmal antippen = zu) → <b>Senden</b>. Das kleine <b>ⓘ</b> neben einem Feld erklärt es kurz.", "Tap a row → program, temperature and time unfold below it (tap again to close) → <b>Send</b>. The small <b>ⓘ</b> next to a field explains it briefly.")}</p><p>${t("Die Fritteuse ist dann vorbereitet – <b>gestartet wird immer am Gerät</b>. Sicher ist sicher. 🔥", "The fryer is then prepared – <b>you always start it on the device</b>. Better safe than sorry. 🔥")}</p>`, "#fb8c00", t("Programm, Temperatur, Zeit", "Program, temperature, time"))}
    ${acSec("⏹️", t("Knopf rechts", "Button on the right"), `<p>${t("<b>Grün</b> = senden, <b>Orange</b> = abbrechen (noch nicht gestartet), <b>Rot</b> = Garen beenden.", "<b>Green</b> = send, <b>orange</b> = cancel (not started yet), <b>red</b> = stop cooking.")}</p>`, "#e53935", t("Senden, Abbrechen, Beenden", "Send, cancel, stop"))}
    ${acSec("🔗", "Match & Sync", `<p>${t("Bei zwei Zonen: „Einstellungen übernehmen“ kopiert die andere Zone. <b>Match senden</b> = beide Zonen bekommen dieselben Werte. <b>Sync senden</b> = beide werden zur selben Zeit fertig.", "With two zones: “Copy settings” copies the other zone. <b>Send Match</b> = both zones get the same values. <b>Send Sync</b> = both finish at the same time.")}</p><p>${t("Der Sync-Hinweis sagt dir außerdem, wann du die zweite Zone startest.", "The sync hint also tells you when to start the second zone.")}</p>`, "#1e88e5", t("Zwei Körbe, ein Abendessen", "Two baskets, one dinner"))}
    ${acSec("🔢", t("Oben in der Karte", "At the top of the card"), `<p>${t("Die blaue Zahl = so viele Zonen garen gerade. 🟢/🔴 = Fritteuse online oder offline. <b>ⓘ</b> = Infos & Credits. <b>⚙️</b> = Einstellungen.", "The blue number = zones cooking right now. 🟢/🔴 = fryer online or offline. <b>ⓘ</b> = info & credits. <b>⚙️</b> = settings.")}</p>`, "#8e24aa", t("Zahl, Punkt, Knöpfe", "Number, dot, buttons"))}
    ${acSec("⚙️", t("Einstellungen", "Settings"), `<p>${t("Das Zahnrad oben in der Karte öffnet die Einstellungen:", "The cog at the top of the card opens the settings:")}</p><ul class="ac-ol"><li>${t("<b>👁️ Ansicht</b>: Schriftgröße und Hell/Dunkel – gilt nur auf diesem Gerät.", "<b>👁️ View</b>: font size and light/dark – only on this device.")}</li><li>${t("<b>🍟 Karte</b>: Maskottchen, Leiste oben, Anleitung-Knopf – nur auf diesem Gerät.", "<b>🍟 Card</b>: mascot, top bar, guide button – only on this device.")}</li><li>${t("<b>🔌 Integration</b> (nur Admins): Abfrage-Takt und Seitenleiste – gilt für alle.", "<b>🔌 Integration</b> (admins only): polling interval and sidebar – for everyone.")}</li></ul>`, "#607d8b", t("Ansicht, Karte, Integration", "View, card, integration"))}
    ${app ? acSec("📱", t("Als App aufs Handy", "As an app on your phone"), app, "#0288d1", t("Ohne App-Store", "No app store")) : ""}
    ${acSec("📦", t("Installieren & Updates", "Install & updates"), `<p>${t("Installation über HACS (ab Home Assistant 2026.11: Einstellungen › Marketplace). Dort kommen auch die Updates an. Betas siehst du nur mit „Beta-Versionen anzeigen“.", "Install via HACS (from Home Assistant 2026.11: Settings › Marketplace). Updates arrive there too. You only see betas with “Show beta versions”.")}</p>`, "#6d4c41", "HACS / Marketplace")}
    ${acSec("🎃", t("Maskottchen", "Mascot"), `<p>${t("Im Karten-Editor oder unter ⚙️ › Karte einschalten (für die Seitenleiste: ⚙️ › Integration). Es zieht sich je nach Jahreszeit um. 🎅🐰🎃", "Switch it on in the card editor or under ⚙️ › Card (for the sidebar: ⚙️ › Integration). It changes costumes with the seasons. 🎅🐰🎃")}</p>`, "#f9a825", t("Zieht sich je nach Jahreszeit um", "Dresses up for the seasons"))}`;
}

// ---------- Hauptkarte ----------
class AirfryerControlCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._open = null; // Schlüssel der Zone, die aufgeklappt ist
    this._page = null; // 📄 offene Seite: "guide" | "settings" | "credits" | "news" (null = Zonen)
    this._helpOpen = new Set(); // ⓘ-Hilfen, die gerade offen sind (bleiben beim Neuzeichnen offen)
    this._sig = "";
  }
  setConfig(config) {
    this._config = { compact: false, ...config };
    this._sig = "";
    if (this._hass) this._render();
  }
  static getStubConfig() { return {}; } // 🌐 ohne festen Titel: die Karte nimmt den Titel in der Sprache von Home Assistant
  static getConfigElement() { return document.createElement("airfryer-control-card-editor"); }
  getCardSize() { return 4; }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6 }; }

  set hass(hass) {
    const lang = this._hass?.language;
    this._hass = hass;
    // 📄 Auf einer Seite nicht neu zeichnen – sonst gehen Suchtext und aufgeklappte Kapitel verloren
    if (this._page && this._pageDrawn && lang === hass.language) return;
    const zones = findZones(hass);
    const sig = zones.map((z) => [z.state, z.finish, z.mode, z.temp, z.time, z.sw]
      .map((e) => { const s = hass.states[e]; return s ? s.state + "|" + (s.attributes?.min ?? "") + (s.attributes?.max ?? "") : "-"; }).join(",")).join(";")
      + "#" + (findOnline(hass, zones)?.state || "") + this._open + (hass.language || "") + new Date().getHours();
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

  // 👁️ Einstellungen nur für dieses Gerät (aus dem Speicher des Browsers) + was davon wirklich gilt
  _view() { const v = lsGet("view", {}); return v && typeof v === "object" ? v : {}; }
  _eff() {
    const v = this._view(), c = this._config || {};
    return {
      masc: typeof v.masc === "boolean" ? v.masc : !!c.maskottchen,
      top: typeof v.top === "boolean" ? v.top : c.statuszeile !== false,
      guide: typeof v.guide === "boolean" ? v.guide : c.anleitung !== false,
    };
  }
  _go(page) { // 📄 Seite öffnen (null = zurück zu den Zonen)
    this._from = page && page !== "settings" && this._page === "settings" ? "settings" : null;
    this._page = page || null; this._pageDrawn = false; this._secOpen = null; this._sub = null; this._sig = "";
    const h = this._hass;
    if (page === "settings" && !this._integ && h?.user?.is_admin && typeof h.callApi === "function" && typeof h.callWS === "function" && !inApp()) this._integLoad();
    if (!page) { this.hass = this._hass; } else this._render();
    try { this.scrollIntoView?.({ block: "nearest" }); } catch (_) { /* egal */ }
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;
    const zones = this._zones || findZones(hass);
    const v = this._view(), eff = this._eff();
    // 🌐 Standard-Titel in der Sprache von Home Assistant (alter deutscher Standard zählt auch als „kein Titel“)
    const title = !this._config.title || (this._config.title === "Heißluftfritteuse" && !isDe(hass)) ? tr(hass, "Heißluftfritteuse", "Air fryer") : this._config.title;
    const online = findOnline(hass, zones);
    const on = online?.state === "on";
    const top = !eff.top ? "" : `<div class="ac-top">
        <span class="ac-pill ${on ? "" : "off"}">${on ? `🟢 ${esc(tr(hass, "verbunden", "connected"))}` : `🔴 ${esc(tr(hass, "offline", "offline"))}`}</span>
        <span class="ac-greet">${esc(acGreeting(hass))}</span>
        ${AC_VERSION ? `<span class="ac-ver" translate="no">v${esc(AC_VERSION)}</span>` : ""}</div>`;
    let body;
    if (this._page) body = this._pageHtml();
    else {
      const rows = zones.map((z) => {
        const st = hass.states[z.state];
        const fin = hass.states[z.finish];
        const b = this._btn(z);
        const sub = valid(fin) ? tr(hass, `fertig um ${clock(fin.state, hass)} Uhr`, `done at ${clock(fin.state, hass)}`) : "";
        return `<div class="ac-row ${this._open === z.key ? "open" : ""}" data-z="${esc(z.key)}" style="--c:${this._color(z)}" title="${esc(tr(hass, "Antippen = Programm, Temperatur und Zeit", "Tap = program, temperature and time"))}">
          <ha-icon icon="mdi:toaster-oven"></ha-icon>
          <div class="ac-txt"><div class="ac-name">${esc(z.name)}</div>
            <div class="ac-state">${esc(stateText(hass, st?.state))}</div>
            ${sub ? `<div class="ac-sub">${esc(sub)}</div>` : ""}</div>
          <button class="ac-go" data-go="${esc(z.key)}" style="--b:${b.color}" title="${esc(b.text)}" ${z.sw ? "" : "disabled"}><ha-icon icon="${b.icon}"></ha-icon></button>
        </div>${this._open === z.key ? this._zoneHtml(z, zones) : ""}`;
      }).join("");
      const running = zones.filter((z) => RUNNING.includes(hass.states[z.state]?.state)).length; // 🔢 Zahl-Blase = wie viele Zonen gerade garen
      body = `<div class="ac-head">${eff.masc ? `<span class="ac-masc" title="${esc(tr(hass, "Maskottchen (unter ⚙️ abschaltbar)", "Mascot (switch off under ⚙️)"))}">${acMascotSvg(acMood(hass, zones), acDeco())}</span>` : `<img class="ac-logo" src="${AC_BASE}/icon.png?v=${esc(AC_VERSION)}" alt="" width="30" height="30">`}${running ? `<span class="ac-badge" title="${esc(tr(hass, "Zonen, die gerade garen", "Zones cooking right now"))}">${running}</span>` : ""}<h2>${esc(title)}</h2>
          <span class="ac-dot ${on ? "" : "off"}" title="${on ? "Online" : "Offline"}"></span>
          <button class="ac-ibtn" data-page="settings" title="${esc(tr(hass, "Einstellungen", "Settings"))}"><ha-icon icon="mdi:cog-outline"></ha-icon></button>
          <button class="ac-ibtn" data-page="credits" data-info title="Info"><ha-icon icon="mdi:information-outline"></ha-icon></button></div>
        ${this._boxHtml(eff)}
        <div class="ac-zones">${rows || `<div class="ac-empty">${esc(tr(hass, "Keine Zonen gefunden. Ist die Integration „Airfryer Control“ eingerichtet und die Fritteuse online?", "No zones found. Is the “Airfryer Control” integration set up and the fryer online?"))}</div>`}</div>`;
    }
    const sz = v.size === "s" ? "ac-sz-s" : v.size === "l" ? "ac-sz-l" : "";
    const th = v.theme === "light" ? "ac-th-light" : v.theme === "dark" ? "ac-th-dark" : "";
    this.shadowRoot.innerHTML = `<style>${BASE_CSS}</style><div class="ac-wrap ${sz}">${top}
      <ha-card class="${th}">${body}</ha-card>
      ${!eff.guide || this._page ? "" : `<div class="ac-foot"><button type="button" data-guide><ha-icon icon="mdi:book-open-page-variant-outline"></ha-icon><span>${esc(tr(hass, "Anleitung", "Guide"))}</span></button></div>`}</div>`;
    this._pageDrawn = !!this._page;
    this._wire();
  }

  // 💡 Tipp beim ersten Start, danach 📢 „Neu in dieser Beta“ (je einmal pro Gerät, wegklickbar)
  _boxHtml(eff) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    if (eff.guide && !lsGet("tip", false)) {
      return `<div class="ac-box" style="--bc:#f9a825" data-box="tip"><b>💡 ${t("Neu hier?", "New here?")}</b><p>${t("Unten auf 📖 Anleitung tippen – da steht alles drin. Und oben unter ⚙️ stellst du Schriftgröße, Hell/Dunkel und mehr ein.", "Tap 📖 Guide at the bottom – it's all in there. And under ⚙️ at the top you set font size, light/dark and more.")}</p>
        <div class="ac-bbtns"><button type="button" class="pri" data-tip="guide">📖 ${t("Zeig mir", "Show me")}</button><button type="button" data-tip="ok">${t("Okay", "Okay")}</button></div></div>`;
    }
    const news = this._news();
    if (news.length && lsGet("news", "") !== AC_VERSION) {
      return `<div class="ac-box" style="--bc:#fb8c00" data-box="news"><b>📢 ${t("Neu in dieser Beta", "New in this beta")}</b> <span class="elcsmall" translate="no">v${esc(AC_VERSION)}</span>
        <ul>${(news.filter((n) => n[0] === AC_VERSION).length ? news.filter((n) => n[0] === AC_VERSION) : news.slice(0, 4)).map((n) => `<li>${esc(tr(hass, n[1], n[2]))}</li>`).join("")}</ul>
        <div class="ac-bbtns"><button type="button" class="pri" data-page="news">${t("Alle Neuerungen", "All news")}</button><button type="button" data-newsok>${t("Gelesen", "Got it")}</button></div></div>`;
    }
    return "";
  }
  // Neuerungen dieser Beta: nur in einer Beta-Version, Einträge der aktuellen Beta zuerst
  _news() {
    if (!/beta/i.test(AC_VERSION)) return [];
    const base = AC_VERSION.replace(/-beta.*$/i, "");
    return acNewsSorted().filter((n) => n[0].startsWith(base + "-beta") && acVerCmp(n[0], AC_VERSION) <= 0);
  }

  // 📄 Seite: Kopf mit ← + Inhalt
  _pageHtml() {
    const hass = this._hass, t = (d, e) => tr(hass, d, e);
    const P = {
      guide: ["📖", t("Anleitung", "Guide"), "#3949ab"],
      settings: ["⚙️", t("Einstellungen", "Settings"), "#607d8b"],
      credits: ["ℹ️", t("Über Airfryer Control", "About Airfryer Control"), "#0288d1"],
      news: ["📢", t("Neu in dieser Beta", "New in this beta"), "#fb8c00"],
    }[this._page] || ["📄", "", "#607d8b"];
    const sub = this._page === "settings" && this._sub ? this._subRow(this._sub) : null;
    if (sub) return `<div class="ac-pghead" style="--pc:${sub.color}"><button class="ac-back" data-back title="${esc(t("Zurück", "Back"))}" aria-label="${esc(t("Zurück", "Back"))}"><ha-icon icon="mdi:arrow-left"></ha-icon></button><span class="ac-ic" style="--ic:${sub.color}"><ha-icon icon="${sub.icon}"></ha-icon></span><h2>${esc(sub.title)}</h2></div>
      <div class="ac-pgbody">${this._subHtml(this._sub)}</div>`;
    const body = this._page === "guide" ? acGuideHtml(hass)
      : this._page === "settings" ? this._settingsHtml()
      : this._page === "news" ? this._newsHtml()
      : creditsHtml(hass);
    return `<div class="ac-pghead" style="--pc:${P[2]}"><button class="ac-back" data-back title="${esc(t("Zurück", "Back"))}" aria-label="${esc(t("Zurück", "Back"))}"><ha-icon icon="mdi:arrow-left"></ha-icon></button><span class="ac-pgic">${P[0]}</span><h2>${esc(P[1])}</h2></div>
      <div class="ac-pgbody ${this._page === "guide" ? "ac-guide" : ""}">${body}</div>`;
  }

  _newsHtml() {
    const hass = this._hass;
    const list = /beta/i.test(AC_VERSION) ? this._news() : acNewsSorted();
    const vers = [...new Set(list.map((n) => n[0]))];
    return `<p class="ac-pgsub">${esc(tr(hass, `Du nutzt v${AC_VERSION || "?"}. Neueste oben.`, `You are on v${AC_VERSION || "?"}. Newest first.`))}</p>
      <div class="ac-news">${vers.map((ver) => `<h4 translate="no">${esc(ver)}</h4><ul>${list.filter((n) => n[0] === ver).map((n) => `<li>${esc(tr(hass, n[1], n[2]))}</li>`).join("")}</ul>`).join("")}</div>
      <p class="elcsmall"><a href="${AC_REPO}/releases" target="_blank" rel="noopener">${esc(tr(hass, "Alle Versionen auf GitHub", "All versions on GitHub"))}</a></p>`;
  }

  // ⚙️ Einstellungen – 1:1 wie bei der Einkaufsliste: Suchfeld, Gruppen zum Aufklappen, Zeilen mit buntem Symbol,
  // Schalter direkt in der Zeile, Antippen der Zeile = eigene Seite mit Erklärung
  _setGroups() {
    const hass = this._hass, t = (d, e) => tr(hass, d, e), v = this._view(), eff = this._eff();
    const admin = hass.user?.is_admin && typeof hass.callApi === "function" && typeof hass.callWS === "function" && !inApp();
    const io = this._integ?.data;
    const sizeTxt = { s: t("Kleiner", "Smaller"), l: t("Größer", "Larger") }[v.size] || "Standard";
    const themeTxt = { light: t("Hell", "Light"), dark: t("Dunkel", "Dark") }[v.theme] || t("Auto (wie Home Assistant)", "Auto (like Home Assistant)");
    const groups = [
      { key: "view", title: t("👁️ Ansicht", "👁️ View"), rows: [
        { key: "size", icon: "mdi:format-size", color: "#3949ab", title: t("Schriftgröße", "Font size"), info: `${sizeTxt} · ${t("nur dieses Gerät", "this device only")}`, kw: "schrift text gross klein zoom font size bigger smaller" },
        { key: "theme", icon: "mdi:theme-light-dark", color: "#455a64", title: t("Hell / Dunkel", "Light / dark"), info: `${themeTxt} · ${t("nur dieses Gerät", "this device only")}`, kw: "farben hell dunkel design theme dark light colours" },
      ] },
      { key: "card", title: t("🍟 Karte", "🍟 Card"), rows: [
        { key: "masc", icon: "mdi:emoticon-happy-outline", color: "#fb8c00", title: t("Maskottchen", "Mascot"), info: t("Statt Logo, zieht sich je nach Jahreszeit um", "Instead of the logo, dresses up for the seasons"), kw: "maskottchen gesicht logo mascot face", on: eff.masc },
        { key: "top", icon: "mdi:dock-top", color: "#43a047", title: t("Leiste oben", "Top bar"), info: t("Verbunden/offline, Gruß und Version", "Connected/offline, greeting and version"), kw: "leiste status gruss version online bar greeting", on: eff.top },
        { key: "guide", icon: "mdi:book-open-page-variant-outline", color: "#3949ab", title: t("Anleitung-Knopf", "Guide button"), info: t("Der 📖-Knopf unter der Karte", "The 📖 button below the card"), kw: "anleitung knopf hilfe guide help button", on: eff.guide },
      ] },
    ];
    if (admin) {
      const wait = !io ? (this._integErr ? t("Konnte nicht geladen werden", "Could not be loaded") : t("Lädt …", "Loading …")) : "";
      const rows = [
        { key: "interval", icon: "mdi:update", color: "#26a69a", title: t("Abfrage-Takt", "Polling interval"), info: wait || t(`Alle ${io.intervall ?? 60} s, wenn nichts gart`, `Every ${io.intervall ?? 60} s while idle`), kw: "abfrage takt intervall sekunden cloud polling interval seconds" },
        { key: "sidebar", icon: "mdi:dock-left", color: "#1e88e5", title: t("In der Seitenleiste", "In the sidebar"), info: wait || t("Eintrag „Fritteuse“ links im Menü · gilt für alle", "“Fritteuse” entry in the left menu · for everyone"), kw: "seitenleiste menu sidebar panel", on: io ? !!io.sidebar : null },
        { key: "smasc", icon: "mdi:emoticon-happy-outline", color: "#fb8c00", title: t("Maskottchen in der Seitenleiste", "Mascot in the sidebar"), info: wait || t("Nur die Seite in der Seitenleiste · gilt für alle", "Only the sidebar page · for everyone"), kw: "maskottchen seitenleiste mascot sidebar", on: io ? !!io.maskottchen : null },
        { key: "haopts", icon: "mdi:cog-outline", color: "#607d8b", title: t("Alle Optionen in Home Assistant", "All options in Home Assistant"), info: t("Öffnet die Integration (auch Zeiteinheit)", "Opens the integration (also time unit)"), kw: "optionen integration zeiteinheit options time unit", act: "haopts" },
      ];
      if ((this._integ?.entries || []).length > 1) rows.unshift({ key: "entry", icon: "mdi:toaster-oven", color: "#6d4c41", title: t("Fritteuse", "Air fryer"), info: (this._integ.entries.find((e) => e.entry_id === this._integ.entry) || {}).title || "", kw: "fritteuse geraet auswahl fryer device" });
      groups.push({ key: "integ", title: t("🔌 Integration (nur Admins)", "🔌 Integration (admins only)"), rows });
    }
    const about = [
      { key: "aguide", icon: "mdi:book-open-page-variant-outline", color: "#3949ab", title: t("Anleitung", "Guide"), info: t("Alles Schritt für Schritt, mit Suche", "Everything step by step, with search"), kw: "anleitung hilfe guide help", page: "guide" },
    ];
    if (this._news().length) about.push({ key: "anews", icon: "mdi:bullhorn-outline", color: "#fb8c00", title: t("Neu in dieser Beta", "New in this beta"), info: `v${AC_VERSION}`, kw: "neu beta neuigkeiten version news", page: "news" });
    about.push(
      { key: "acredits", icon: "mdi:information-outline", color: "#0288d1", title: t("Credits, Spenden, Datenschutz", "Credits, donations, privacy"), info: "Mister-M · MIT", kw: "credits spenden paypal datenschutz github fehler idee donate privacy bug", page: "credits" },
      { key: "atip", icon: "mdi:lightbulb-on-outline", color: "#f9a825", title: t("Tipp und Beta-Kasten wieder zeigen", "Show tip and beta box again"), info: t("Zeigt 💡 und 📢 über den Zonen noch einmal", "Shows 💡 and 📢 above the zones once more"), kw: "tipp kasten wieder zeigen tip box again", act: "tipagain" },
    );
    groups.push({ key: "about", title: t("ℹ️ Über", "ℹ️ About"), rows: about });
    return groups;
  }
  _settingsHtml() {
    const hass = this._hass, t = (d, e) => tr(hass, d, e);
    if (this._sub) return this._subHtml(this._sub);
    return `<div class="ac-srch"><ha-icon icon="mdi:magnify"></ha-icon><input type="search" data-setq placeholder="${esc(t("In den Einstellungen suchen, z. B. Schrift", "Search the settings, e.g. font"))}" value="${esc(this._setQ || "")}" aria-label="${esc(t("In den Einstellungen suchen", "Search the settings"))}" autocomplete="off" enterkeyhint="search"></div>
      <div data-setlist>${this._setListHtml()}</div>
      <p class="ac-pgsub" style="margin-top:12px">${esc(t("👁️ Ansicht und 🍟 Karte gelten nur auf diesem Gerät, 🔌 Integration für alle.", "👁️ View and 🍟 Card apply to this device only, 🔌 Integration to everyone."))}</p>`;
  }
  _setListHtml() {
    const hass = this._hass, t = (d, e) => tr(hass, d, e);
    const q = (this._setQ || "").trim().toLowerCase();
    const out = this._setGroups().map((g) => {
      const rows = g.rows.filter((r) => !q || `${r.title} ${r.info} ${r.kw}`.toLowerCase().includes(q)).map((r) => {
        const main = `<span class="ac-ic" style="--ic:${r.color}"><ha-icon icon="${r.icon}"></ha-icon></span><span class="ac-grow"><b>${esc(r.title)}</b><small>${esc(r.info)}</small></span>`;
        if (r.on !== undefined) {
          return `<div class="ac-lrow"><button type="button" class="ac-lmain" data-sub="${r.key}">${main}</button><button type="button" class="ac-tgl" data-tgl="${r.key}" aria-pressed="${!!r.on}" ${r.on === null ? "disabled" : ""} title="${esc(t("An / aus", "On / off"))}" aria-label="${esc(r.title)} ${esc(t("an / aus", "on / off"))}"><span></span></button></div>`;
        }
        const attr = r.page ? `data-page="${r.page}"` : r.act ? `data-sact="${r.act}"` : `data-sub="${r.key}"`;
        return `<button type="button" class="ac-lrow" ${attr}>${main}${r.act === "tipagain" ? "" : `<ha-icon class="ac-chev" icon="mdi:chevron-right"></ha-icon>`}</button>`;
      }).join("");
      if (!rows) return "";
      const open = !!q || this._setOpen === g.key; // 🗂️ zugeklappt; bei der Suche klappen passende Gruppen von selbst auf
      const [emo, ...name] = g.title.split(" ");
      const tg = g.rows.filter((r) => typeof r.on === "boolean");
      const sum = tg.length ? t(`${g.rows.length} Einstellungen · ${tg.filter((r) => r.on).length} an`, `${g.rows.length} settings · ${tg.filter((r) => r.on).length} on`) : g.rows.map((r) => r.title).join(", ");
      return `<div class="ac-lgbox"><button type="button" class="ac-lgroup" data-grp="${g.key}" aria-expanded="${open}"><span class="ac-gem">${emo}</span><span class="ac-grow"><b>${esc(name.join(" "))}</b><small>${esc(sum)}</small></span><ha-icon class="ac-chev" icon="${open ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon></button>${open ? rows : ""}</div>`;
    }).join("");
    return out || `<p class="ac-pgsub">${esc(t(`Nichts gefunden zu „${this._setQ}“ 🤷`, `Nothing found for “${this._setQ}” 🤷`))}</p>`;
  }
  _subRow(key) { for (const g of this._setGroups()) { const r = g.rows.find((x) => x.key === key); if (r) return r; } return null; }
  // 📄 Eigene Seite einer Einstellung: Erklärung + Bedienung (wie die Unterseiten der Einkaufsliste)
  _subHtml(key) {
    const hass = this._hass, t = (d, e) => tr(hass, d, e), v = this._view(), eff = this._eff(), io = this._integ?.data || {};
    const seg = (k, cur, opts) => `<div class="ac-seg" role="group">${opts.map(([val, label]) => `<button type="button" data-view="${k}" data-val="${val}" class="${cur === val ? "on" : ""}" aria-pressed="${cur === val}">${esc(label)}</button>`).join("")}</div>`;
    const sw = (k, on, label, sub) => `<div class="ac-lrow ac-swline"><span class="ac-grow" style="padding:10px 0 10px 12px"><b>${esc(label)}</b><small>${esc(sub)}</small></span><button type="button" class="ac-tgl" data-tgl="${k}" aria-pressed="${!!on}" aria-label="${esc(label)}"><span></span></button></div>`;
    const local = t("Gilt nur auf diesem Gerät (gespeichert im Browser).", "Only applies to this device (saved in the browser).");
    const reset = `<button type="button" class="ac-lbtn" data-vreset="${key}">↩️ ${esc(t("Wie im Karten-Editor", "Like in the card editor"))}</button>`;
    const reload = `<p class="ac-msg" data-iomsg>ℹ️ ${esc(t("Gilt für alle. Beim Speichern lädt die Integration kurz neu (ein paar Sekunden).", "Applies to everyone. Saving reloads the integration briefly (a few seconds)."))}</p>`;
    switch (key) {
      case "size": return `<p>${esc(t("Macht alles in der Karte größer oder kleiner – praktisch fürs Küchen-Tablet oder den Fire TV.", "Makes everything in the card larger or smaller – handy for a kitchen tablet or Fire TV."))}</p>${seg("size", v.size || "m", [["s", t("Kleiner", "Smaller")], ["m", "Standard"], ["l", t("Größer", "Larger")]])}<p class="ac-pgsub">${esc(local)}</p>`;
      case "theme": return `<p>${esc(t("Auto nimmt die Farben von Home Assistant. Hell oder Dunkel stellt die Karte fest ein, egal was Home Assistant macht.", "Auto uses the colours of Home Assistant. Light or dark fixes the card, whatever Home Assistant does."))}</p>${seg("theme", v.theme || "auto", [["auto", "Auto"], ["light", t("Hell", "Light")], ["dark", t("Dunkel", "Dark")]])}<p class="ac-pgsub">${esc(local)}</p>`;
      case "masc": return `<p>${esc(t("Die kleine Fritteuse mit Gesicht oben links statt dem Logo. Sie freut sich beim Garen, hüpft bei „Fertig“ und zieht sich je nach Jahreszeit um (Weihnachtsmütze, Hasenohren, Kürbis …).", "The little air fryer with a face at the top left instead of the logo. It smiles while cooking, hops when done and dresses up for the seasons (Santa hat, bunny ears, pumpkin …)."))}</p>${sw("masc", eff.masc, t("Maskottchen zeigen", "Show mascot"), local)}${reset}`;
      case "top": return `<p>${esc(t("Die Leiste über der Karte: 🟢 verbunden / 🔴 offline, ein Gruß mit deinem Namen und die Version.", "The bar above the card: 🟢 connected / 🔴 offline, a greeting with your name and the version."))}</p>${sw("top", eff.top, t("Leiste oben zeigen", "Show top bar"), local)}${reset}`;
      case "guide": return `<p>${esc(t("Der Knopf „📖 Anleitung“ unter der Karte. Die Anleitung findest du auch ohne ihn: ⚙️ › Über › Anleitung.", "The “📖 Guide” button below the card. You also find the guide without it: ⚙️ › About › Guide."))}</p>${sw("guide", eff.guide, t("Anleitung-Knopf zeigen", "Show guide button"), local)}${reset}`;
      case "sidebar": return `<p>${esc(t("Fügt links im Menü den Eintrag „Fritteuse“ hinzu: eine ganze Seite mit Laufband und Zonen.", "Adds a “Fritteuse” entry to the left menu: a full page with the ticker and the zones."))}</p>${sw("sidebar", !!io.sidebar, t("In der Seitenleiste zeigen", "Show in the sidebar"), t("gilt für alle", "for everyone"))}${reload}`;
      case "smasc": return `<p>${esc(t("Das Maskottchen auf der Seite in der Seitenleiste. Auf Dashboard-Karten schaltest du es unter 🍟 Karte.", "The mascot on the sidebar page. On dashboard cards you switch it under 🍟 Card."))}</p>${sw("smasc", !!io.maskottchen, t("Maskottchen in der Seitenleiste", "Mascot in the sidebar"), t("gilt für alle", "for everyone"))}${reload}`;
      case "interval": return `<p>${esc(t("So oft fragt Home Assistant die Cosori-Cloud, wenn nichts gart (30–600 Sekunden). Beim Garen wird immer alle 15 Sekunden gefragt.", "How often Home Assistant asks the Cosori cloud while nothing is cooking (30–600 seconds). While cooking it always asks every 15 seconds."))}</p>
        <div class="ac-lrow ac-swline"><span class="ac-grow" style="padding:10px 0 10px 12px"><b>${esc(t("Sekunden", "Seconds"))}</b><small>30–600</small></span><input type="number" class="ac-num" data-io="intervall" min="30" max="600" step="10" value="${esc(io.intervall ?? 60)}" style="margin-right:12px"></div>
        <button type="button" class="ac-big" data-iosave style="--b:#43a047">💾 ${esc(t("Speichern", "Save"))}</button>${reload}`;
      case "entry": return `<p>${esc(t("Du hast mehrere Fritteusen. Wähle, für welche die Integrations-Einstellungen gelten sollen.", "You have several air fryers. Choose which one the integration settings are for."))}</p><select class="ac-num" style="width:100%" data-integentry>${(this._integ?.entries || []).map((e) => `<option value="${esc(e.entry_id)}" ${e.entry_id === this._integ.entry ? "selected" : ""}>${esc(e.title)}</option>`).join("")}</select>`;
      default: return "";
    }
  }

  // 🔌 Optionen der Integration (Optionen-Dialog von Home Assistant im Hintergrund – lesen, wieder zu, speichern)
  async _optFlow(entryId) {
    return this._hass.callApi("POST", "config/config_entries/options/flow", { handler: entryId, show_advanced_options: false });
  }
  async _integLoad(entryId) {
    const hass = this._hass;
    this._integErr = false;
    try {
      const entries = (await hass.callWS({ type: "config_entries/get", domain: AC })) || [];
      if (!entries.length) throw new Error("none");
      const entry = entries.find((e) => e.entry_id === entryId) || entries[0];
      const flow = await this._optFlow(entry.entry_id);
      const d = {};
      for (const f of flow.data_schema || []) d[f.name] = f.default ?? f.description?.suggested_value;
      hass.callApi("DELETE", `config/config_entries/options/flow/${flow.flow_id}`).catch(() => {}); // nur gelesen – wieder zu
      this._integ = { entry: entry.entry_id, entries: entries.map((e) => ({ entry_id: e.entry_id, title: e.title })), data: d };
    } catch (_) { this._integErr = true; }
    if (this._page === "settings") this._render();
  }
  async _integSave(patch) {
    const hass = this._hass;
    if (!this._integ) return false;
    const data = { ...this._integ.data, ...patch };
    for (const k of Object.keys(data)) if (data[k] === undefined) delete data[k];
    try {
      const flow = await this._optFlow(this._integ.entry);
      const res = await hass.callApi("POST", `config/config_entries/options/flow/${flow.flow_id}`, data);
      if (res?.type !== "create_entry") { hass.callApi("DELETE", `config/config_entries/options/flow/${flow.flow_id}`).catch(() => {}); return false; }
      this._integ.data = data;
      return true;
    } catch (_) { return false; }
  }
  // Handgriffe der Einstellungen (nach jedem Neuzeichnen der Liste wieder anklemmen)
  _wireSet(scope, isRoot = false) {
    const hass = this._hass, t = (d, e) => tr(hass, d, e);
    const relist = () => { const box = this.shadowRoot.querySelector("[data-setlist]"); if (box) { box.innerHTML = this._setListHtml(); this._wireSet(box); } };
    scope.querySelectorAll("[data-grp]").forEach((el) => el.addEventListener("click", () => {
      this._setOpen = this._setOpen === el.dataset.grp ? null : el.dataset.grp; relist(); // 🗂️ eine Gruppe auf = die vorherige zu
    }));
    scope.querySelectorAll("[data-sub]").forEach((el) => el.addEventListener("click", () => { this._sub = el.dataset.sub; this._render(); }));
    if (!isRoot) scope.querySelectorAll("[data-page]").forEach((el) => el.addEventListener("click", () => this._go(el.dataset.page)));
    scope.querySelectorAll("[data-sact]").forEach((el) => el.addEventListener("click", () => {
      if (el.dataset.sact === "haopts") {
        history.pushState(null, "", "/config/integrations/integration/airfryer_control");
        window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      } else if (el.dataset.sact === "tipagain") {
        lsSet("tip", null); lsSet("news", null);
        const s = el.querySelector("small"); if (s) s.textContent = "✅ " + t("Wird wieder gezeigt", "Will show again");
      }
    }));
    scope.querySelectorAll("[data-tgl]").forEach((el) => el.addEventListener("click", async () => {
      const k = el.dataset.tgl, on = el.getAttribute("aria-pressed") !== "true";
      if (k === "sidebar" || k === "smasc") { // 🔌 gilt für alle → Integration speichern
        el.disabled = true; el.setAttribute("aria-pressed", String(on));
        const ok = await this._integSave(k === "sidebar" ? { sidebar: on } : { maskottchen: on });
        el.disabled = false;
        if (!ok) el.setAttribute("aria-pressed", String(!on));
        const msg = this.shadowRoot.querySelector("[data-iomsg]");
        if (msg) msg.textContent = ok ? "✅ " + t("Gespeichert! Die Integration lädt kurz neu.", "Saved! The integration reloads briefly.") : "😕 " + t("Speichern ging nicht. Versuch es über „Alle Optionen in Home Assistant“.", "Saving failed. Try “All options in Home Assistant”.");
        if (!this._sub) relist();
        return;
      }
      const v = this._view(); v[k] = on; lsSet("view", v); this._render(); // 🍟 nur dieses Gerät
    }));
    scope.querySelectorAll("[data-view]").forEach((el) => el.addEventListener("click", () => {
      const v = this._view(), val = el.dataset.val;
      if (val === "m" || val === "auto") delete v[el.dataset.view]; else v[el.dataset.view] = val;
      lsSet("view", v); this._render();
    }));
    scope.querySelectorAll("[data-vreset]").forEach((el) => el.addEventListener("click", () => { const v = this._view(); delete v[el.dataset.vreset]; lsSet("view", v); this._render(); }));
    scope.querySelector("[data-integentry]")?.addEventListener("change", (e) => { this._integ = null; this._integLoad(e.target.value); });
    scope.querySelector("[data-iosave]")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget, msg = this.shadowRoot.querySelector("[data-iomsg]");
      const n = Math.round(Number(this.shadowRoot.querySelector('[data-io="intervall"]').value) / 10) * 10;
      btn.disabled = true;
      const ok = await this._integSave({ intervall: Math.min(600, Math.max(30, Number.isFinite(n) ? n : 60)) });
      btn.disabled = false;
      if (msg) msg.textContent = ok ? "✅ " + t("Gespeichert! Die Integration lädt kurz neu.", "Saved! The integration reloads briefly.") : "😕 " + t("Speichern ging nicht. Versuch es über „Alle Optionen in Home Assistant“.", "Saving failed. Try “All options in Home Assistant”.");
    });
  }

  // Die andere Zone (ohne Grandzone), für „Match“ und „Sync“
  _other(z, zones) {
    if (/grandzone$/.test(z.key)) return null;
    return zones.find((x) => x.key !== z.key && !/grandzone$/.test(x.key)) || null;
  }

  // 🔗 Sync: Hinweis, wann die Zone gestartet werden soll, damit beide gleichzeitig fertig werden
  // ⓘ Knopf + versteckter Hilfetext (antippen = auf, nochmal antippen = zu)
  _info(key, label) {
    const open = this._helpOpen.has(key);
    return `<button type="button" class="finfo" data-help="${esc(key)}" aria-expanded="${open}" title="${esc(tr(this._hass, "Was ist das?", "What is this?"))}" aria-label="${esc(tr(this._hass, `Erklärung: ${label}`, `Explanation: ${label}`))}">i</button>`;
  }
  _hint(key, html) {
    return `<p class="ac-hint" data-hint="${esc(key)}" ${this._helpOpen.has(key) ? "" : "hidden"}>${html}</p>`;
  }

  _syncHtml(z, zones) {
    const hass = this._hass;
    const o = this._other(z, zones);
    if (!o) return "";
    const st = (id) => hass.states[id]?.state;
    const mine = Number(st(z.time));
    if (!Number.isFinite(mine) || mine <= 0) return "";
    const oState = st(o.state), zState = st(z.state);
    if (RUNNING.includes(zState)) return "";
    let msg = "";
    if (RUNNING.includes(oState) && valid(hass.states[o.finish])) {
      const left = Math.round((Date.parse(hass.states[o.finish].state) - Date.now()) / 60000);
      if (!Number.isFinite(left)) return "";
      const wait = left - mine;
      msg = wait > 0
        ? tr(hass, `<b>Sync:</b> ${z.name} in <b>${wait} Min</b> starten – dann werden beide gleichzeitig fertig (${clock(hass.states[o.finish].state, hass)} Uhr).`,
                   `<b>Sync:</b> start ${z.name} in <b>${wait} min</b> – then both finish together (${clock(hass.states[o.finish].state, hass)}).`)
        : wait === 0
          ? tr(hass, `<b>Sync:</b> ${z.name} <b>jetzt</b> starten – dann werden beide gleichzeitig fertig.`, `<b>Sync:</b> start ${z.name} <b>now</b> – then both finish together.`)
          : tr(hass, `<b>Sync:</b> ${z.name} ist ${-wait} Min zu lang – gleichzeitig fertig geht nicht mehr.`, `<b>Sync:</b> ${z.name} is ${-wait} min too long – finishing together is no longer possible.`);
    } else if (!RUNNING.includes(oState)) {
      const other = Number(st(o.time));
      if (!Number.isFinite(other) || other <= 0) return "";
      const diff = Math.abs(mine - other);
      msg = diff === 0
        ? tr(hass, "<b>Sync:</b> beide Zonen gleich lang – gleichzeitig starten, dann sind sie gleichzeitig fertig.", "<b>Sync:</b> both zones take the same time – start together and they finish together.")
        : mine < other
          ? tr(hass, `<b>Sync:</b> ${z.name} <b>${diff} Min</b> nach ${o.name} starten – dann werden beide gleichzeitig fertig.`, `<b>Sync:</b> start ${z.name} <b>${diff} min</b> after ${o.name} – then both finish together.`)
          : tr(hass, `<b>Sync:</b> ${o.name} <b>${diff} Min</b> nach ${z.name} starten – dann werden beide gleichzeitig fertig.`, `<b>Sync:</b> start ${o.name} <b>${diff} min</b> after ${z.name} – then both finish together.`);
    }
    return msg ? `<div class="ac-sync">🔗 ${msg}</div>` : "";
  }

  // 📋 Match: Programm, Temperatur und Zeit dieser Zone auf die andere Zone übernehmen
  // 🔗 Match/Sync an die Fritteuse schicken (nur bereitstellen – gestartet wird am Gerät)
  async _sendSync(z, kind) {
    const hass = this._hass;
    const dev = hass.entities?.[z.state]?.device_id;
    if (!dev || this._syncing) return;
    this._syncing = true;
    try {
      const num = Number((/zone_(\d+)$/.exec(z.key) || [])[1]);
      const data = { geraet: dev, ...(kind === "match" && (num === 1 || num === 2) ? { quelle: num } : {}) }; // Match: Werte DIESER Zone für beide
      await hass.callService("airfryer_control", kind === "match" ? "match_senden" : "sync_senden", data);
    } catch (_) { /* Fehler zeigt Home Assistant selbst */ } finally { this._syncing = false; }
  }

  _syncSendHtml(z, zones) {
    const hass = this._hass;
    const o = this._other(z, zones);
    if (!o || !hass.entities?.[z.state]?.device_id) return "";
    const dis = [z, o].some((x) => RUNNING.includes(hass.states[x.state]?.state)) ? "disabled" : "";
    const lab = (de, en) => esc(tr(hass, de, en));
    const key = `${z.key}:sync`;
    return `<div class="ac-withinfo"><div class="ac-pair">
      <button class="ac-match" data-sendsync="match" data-z="${esc(z.key)}" ${dis}>🟰 ${lab("Match senden", "Send Match")}</button>
      <button class="ac-match" data-sendsync="sync" data-z="${esc(z.key)}" ${dis}>🔗 ${lab("Sync senden", "Send Sync")}</button>
    </div>${this._info(key, "Match & Sync")}</div>
    ${this._hint(key, lab("Match: beide Zonen bekommen die Werte dieser Zone. Sync: beide werden zur selben Zeit fertig. Es wird nur bereitgestellt – gestartet wird am Gerät. Gart eine Zone gerade, geht beides nicht. An einer Turbo Tower Pro getestet, an der TwinFry noch nicht.", "Match: both zones get this zone's values. Sync: both finish at the same time. Only prepares – you start on the device. Not possible while a zone is cooking. Tested on a Turbo Tower Pro, not yet on the TwinFry."))}`;
  }

  async _match(z) {
    const hass = this._hass;
    const o = this._other(z, this._zones || []);
    if (!o || this._matching) return;
    this._matching = true;
    try {
      const prog = hass.states[z.mode]?.state;
      if (prog && hass.states[o.mode]?.state !== prog) {
        await hass.callService("select", "select_option", { entity_id: o.mode, option: prog });
        await new Promise((r) => setTimeout(r, 800)); // die Grenzen der Zone ändern sich mit dem Programm
      }
      const lim = (id, v) => { const a = this._hass.states[id]?.attributes || {}; let x = Number(v); if (a.min != null) x = Math.max(Number(a.min), x); if (a.max != null) x = Math.min(Number(a.max), x); return x; };
      await hass.callService("number", "set_value", { entity_id: o.temp, value: lim(o.temp, hass.states[z.temp]?.state) });
      await hass.callService("number", "set_value", { entity_id: o.time, value: lim(o.time, hass.states[z.time]?.state) });
    } catch (_) { /* Fehler zeigt Home Assistant selbst */ } finally { this._matching = false; }
  }

  // ✏️ Zone einstellen – klappt UNTER der Zeile auf, die Zeile bleibt stehen (wie in der Einkaufsliste)
  _zoneHtml(z, zones) {
    const hass = this._hass;
    const mode = hass.states[z.mode];
    const temp = hass.states[z.temp];
    const time = hass.states[z.time];
    const b = this._btn(z);
    const opts = mode?.attributes?.options || [];
    const modes = opts.map((o) => `<button class="ac-mode ${mode.state === o ? "on" : ""}" data-mode="${esc(o)}"><ha-icon icon="${(MODE_TEXT[o] || [])[2] || "mdi:chef-hat"}"></ha-icon>${esc(modeText(hass, o))}</button>`).join("");
    const t = (de, en) => esc(tr(hass, de, en));
    // Zahl mit −/+ und ⓘ am Namen; die Hilfe klappt direkt darunter auf
    const step = (what, label, st, unit, help) => st ? `<div class="ac-step"><label>${esc(label)}${help ? this._info(`${z.key}:${what}`, label) : ""}</label><button data-step="${what}" data-d="-1">−</button><b>${esc(st.state)} ${unit}</b><button data-step="${what}" data-d="1">+</button></div>${help ? this._hint(`${z.key}:${what}`, help) : ""}` : "";
    const ta = temp?.attributes || {}, ma = time?.attributes || {};
    const tHelp = ta.min != null ? t(`Für dieses Programm: ${ta.min}–${ta.max} °C${ta.step ? `, in ${ta.step}-°C-Schritten` : ""}.`, `For this program: ${ta.min}–${ta.max} °C${ta.step ? `, in ${ta.step} °C steps` : ""}.`) : "";
    const mHelp = ma.min != null ? t(`Für dieses Programm: ${ma.min}–${ma.max} Min.`, `For this program: ${ma.min}–${ma.max} min.`) : "";
    const other = this._other(z, zones);
    const copyKey = `${z.key}:copy`, goKey = `${z.key}:go`, modeKey = `${z.key}:mode`;
    return `<div class="ac-edit" style="--c:${this._color(z)}">
      ${opts.length ? `<div class="ac-flab"><span>${t("Programm", "Program")}</span>${this._info(modeKey, tr(hass, "Programm", "Program"))}</div>${this._hint(modeKey, t("Tippe ein Programm an. Temperatur und Zeit springen dann auf den Vorschlag der Fritteuse für dieses Programm.", "Tap a program. Temperature and time then jump to the fryer's suggestion for that program."))}<div class="ac-modes">${modes}</div>` : ""}
      ${step("temp", tr(hass, "Temperatur", "Temperature"), temp, "°C", tHelp)}
      ${step("time", tr(hass, "Garzeit", "Cooking time"), time, "Min", mHelp)}
      ${this._syncHtml(z, zones)}
      ${other ? `<div class="ac-withinfo"><button class="ac-match" data-match="${esc(z.key)}" ${RUNNING.includes(hass.states[other.state]?.state) ? "disabled" : ""}>📋 ${t(`Einstellungen auf ${other.name} übernehmen`, `Copy settings to ${other.name}`)}</button>${this._info(copyKey, tr(hass, "Einstellungen übernehmen", "Copy settings"))}</div>${this._hint(copyKey, t(`Kopiert Programm, Temperatur und Zeit nur in die Felder von ${other.name}. An die Fritteuse geht dabei noch nichts.`, `Copies program, temperature and time into the fields of ${other.name} only. Nothing is sent to the fryer yet.`))}` : ""}
      ${this._syncSendHtml(z, zones)}
      <div class="ac-withinfo"><button class="ac-big" data-go="${esc(z.key)}" style="--b:${b.color}" ${z.sw ? "" : "disabled"}>${esc(b.text)}</button>${this._info(goKey, b.text)}</div>
      ${this._hint(goKey, t("Senden bereitet die Fritteuse nur vor – gestartet wird immer am Gerät. Abbrechen nimmt ein vorbereitetes Programm wieder weg, Beenden stoppt das Garen.", "Send only prepares the fryer – you always start it on the device. Cancel removes a prepared program, Stop ends cooking."))}
      <button class="ac-close" data-close>${esc(tr(hass, "Zuklappen", "Close"))}</button>
    </div>`;
  }

  _wire() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-help]").forEach((el) => el.addEventListener("click", (e) => {
      e.stopPropagation(); // ⓘ: nur die Hilfe auf-/zuklappen, ohne neu zu zeichnen
      const k = el.dataset.help;
      const open = !this._helpOpen.has(k);
      if (open) this._helpOpen.add(k); else this._helpOpen.delete(k);
      el.setAttribute("aria-expanded", String(open));
      root.querySelectorAll("[data-hint]").forEach((h) => { if (h.dataset.hint === k) h.hidden = !open; });
    }));
    root.querySelectorAll(".ac-row").forEach((el) => el.addEventListener("click", (e) => {
      if (e.target.closest("[data-go]")) return;
      this._open = this._open === el.dataset.z ? null : el.dataset.z; this._sig = ""; this.hass = this._hass; // nochmal antippen = zuklappen
    }));
    root.querySelectorAll("[data-go]").forEach((el) => el.addEventListener("click", (e) => {
      e.stopPropagation();
      const z = (this._zones || []).find((x) => x.key === el.dataset.go);
      if (z) this._toggle(z);
    }));
    // 📄 Seiten öffnen / zurück
    root.querySelectorAll("[data-page]").forEach((el) => el.addEventListener("click", () => this._go(el.dataset.page)));
    root.querySelector("[data-guide]")?.addEventListener("click", () => this._go("guide"));
    root.querySelector("[data-back]")?.addEventListener("click", () => { // aus ⚙️ geöffnet = zurück zu ⚙️
      if (this._sub) { this._sub = null; this._render(); } else this._go(this._from || null);
    });
    root.querySelector("[data-copyapp]")?.addEventListener("click", async (e) => { // 📋 App-Adresse kopieren
      e.stopPropagation();
      const btn = e.currentTarget, inp = btn.previousElementSibling;
      try { await navigator.clipboard.writeText(inp.value); } catch (_) { inp.select(); try { document.execCommand("copy"); } catch (__) { /* egal */ } }
      btn.textContent = "✅ " + tr(this._hass, "Kopiert", "Copied");
    });
    // 💡 / 📢 Kästen wegklicken
    root.querySelectorAll("[data-tip]").forEach((el) => el.addEventListener("click", () => {
      lsSet("tip", true);
      if (el.dataset.tip === "guide") this._go("guide"); else { this._sig = ""; this._render(); }
    }));
    root.querySelector("[data-newsok]")?.addEventListener("click", () => { lsSet("news", AC_VERSION); this._render(); });
    // ⚙️ Einstellungen (Liste, Schalter, Unterseiten) + 🔎 Suche in den Einstellungen
    this._wireSet(root, true);
    const sq = root.querySelector("[data-setq]");
    sq?.addEventListener("input", () => {
      this._setQ = sq.value;
      const box = root.querySelector("[data-setlist]");
      if (box) { box.innerHTML = this._setListHtml(); this._wireSet(box); }
    });
    // 🗂️ Gruppen/Kapitel: eins auf = die anderen zu (bei der Suche bleiben alle Treffer offen)
    let searching = false;
    const secs = [...root.querySelectorAll("details.ac-sec")];
    secs.forEach((d) => {
      if (d.dataset.sec && d.dataset.sec === this._secOpen) d.open = true;
      d.addEventListener("toggle", () => {
        if (d.open && !searching) secs.forEach((o) => { if (o !== d) o.open = false; });
        if (d.dataset.sec) { if (d.open) this._secOpen = d.dataset.sec; else if (this._secOpen === d.dataset.sec) this._secOpen = null; }
      });
    });
    // 🔎 Suche in der Anleitung: nur Kapitel mit allen Wörtern zeigen und aufklappen
    const q = root.querySelector("[data-q]");
    if (q) {
      const none = root.querySelector("[data-none]");
      const norm = (x) => String(x || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ß/g, "ss");
      const texts = secs.map((d) => norm(d.textContent));
      q.addEventListener("input", () => {
        const words = norm(q.value).split(/\s+/).filter(Boolean);
        searching = words.length > 0;
        let hits = 0;
        secs.forEach((d, i) => {
          const hit = !words.length || words.every((w) => texts[i].includes(w));
          d.hidden = !hit; d.open = words.length > 0 && hit;
          if (hit && words.length) hits++;
        });
        none.hidden = !words.length || hits > 0;
      });
    }
    root.querySelectorAll("[data-close]").forEach((el) => el.addEventListener("click", () => {
      this._open = null; this._sig = ""; this.hass = this._hass;
    }));
    root.querySelectorAll("[data-match]").forEach((el) => el.addEventListener("click", () => {
      const z = (this._zones || []).find((x) => x.key === el.dataset.match);
      if (z) this._match(z);
    }));
    root.querySelectorAll("[data-sendsync]").forEach((el) => el.addEventListener("click", () => {
      const z = (this._zones || []).find((x) => x.key === el.dataset.z);
      if (z) this._sendSync(z, el.dataset.sendsync);
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
      const stepBy = Number(st.attributes?.step) || (el.dataset.step === "temp" ? 5 : 1); // Gären: 1 °C
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
        items.push(`${FRY} ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${when}`);
      } else if (s === "wartet_auf_sync") {
        items.push(`${FRY} ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${tr(hass, "wartet auf Sync-Start", "waiting for sync start")}`);
      } else if (s === "wartet_auf_start") {
        items.push(`${FRY} ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${tr(hass, "wartet auf Start", "waiting for start")}`);
      } else if (s === "fertig") {
        done = true;
        items.push(`${FRY} ${tr(hass, "Fritteuse", "Air fryer")} ${name}: ${tr(hass, "FERTIG!", "DONE!")}`);
      }
    }
    for (const id of this._config?.extra_entities || []) {
      const timers = hass.states[id]?.attributes?.timer;
      if (!Array.isArray(timers)) continue;
      timers.filter((x) => x.fertig).forEach((x) => { done = true; items.push(`${TMR}${x.name}: ${tr(hass, "FERTIG!", "DONE!")}`); });
      timers.filter((x) => !x.fertig).sort((a, b) => Date.parse(a.ende) - Date.parse(b.ende))
        .forEach((x) => items.push(`${TMR}${x.name}: ${tr(hass, `fertig um ${clock(x.ende, hass)} Uhr`, `done at ${clock(x.ende, hass)}`)}`));
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
    const img = `<img class="fry" src="${AC_BASE}/icon.png?v=${esc(AC_VERSION)}" alt="" width="20" height="20">`;
    const timg = `<img class="fry" src="${AC_BASE}/timer-icon.png?v=${esc(AC_VERSION)}" alt="" width="24" height="24" style="width:24px;height:24px;margin:-4px 6px 0 0">`;
    const html = esc(text).split(FRY).join(img).split(TMR).join(timg);
    this.shadowRoot.innerHTML = `<style>
      :host { display:block; }
      .fry { width:20px; height:20px; vertical-align:middle; margin:-3px 4px 0 0; border-radius:4px; }
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
    <ha-card><div class="box"><ha-icon icon="mdi:chef-hat"></ha-icon><div class="win"><div class="wrap"><span class="txt">${html}</span><span class="txt">${html}</span></div></div><ha-icon icon="mdi:chef-hat"></ha-icon></div></ha-card>`;
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
function makeEditor(schemaFn, labelFn, defaults) {
  return class extends HTMLElement {
    get _defaults() { return defaults; }
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
      this._form.data = { ...(this._defaults || {}), ...this._config }; // 🟢 Schalter, die standardmäßig AN sind, auch so anzeigen
      this._form.schema = schemaFn(this._hass);
      this._form.computeLabel = (s) => labelFn(this._hass, s.name);
    }
  };
}
const cardLabels = { title: ["Titel", "Title"], maskottchen: ["🍟 Maskottchen Airfryer oben links zeigen", "🍟 Show air fryer mascot top left"], statuszeile: ["🟢 Leiste über der Karte (verbunden, Gruß, Version)", "🟢 Bar above the card (connected, greeting, version)"], anleitung: ["📖 Knopf „Anleitung“ unter der Karte", "📖 “Guide” button below the card"] };
customElements.define("airfryer-control-card-editor", makeEditor(
  () => [{ name: "title", selector: { text: {} } }, { name: "maskottchen", selector: { boolean: {} } }, { name: "statuszeile", selector: { boolean: {} } }, { name: "anleitung", selector: { boolean: {} } }],
  (h, n) => { const l = cardLabels[n]; return l ? tr(h, l[0], l[1]) : n; }, { statuszeile: true, anleitung: true }));
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

AirfryerControlCard.mascotSvg = acMascotSvg; AirfryerControlCard.mascotDeco = acDeco; // 🧪 für Tests und Vorschau
customElements.define("airfryer-control-card", AirfryerControlCard);
customElements.define("airfryer-control-ticker", AirfryerControlTicker);
window.customCards = window.customCards || [];
window.customCards.push(
  { type: "airfryer-control-card", name: "Airfryer Control", description: "Zonen der Heißluftfritteuse: Status, Programm, Temperatur, Zeit, Senden/Beenden.", preview: false },
  { type: "airfryer-control-ticker", name: "Airfryer Control – Laufband", description: "Laufband mit den Fertig-Zeiten der Fritteuse (optional mit Kochtimern).", preview: false },
);
console.info(`%c AIRFRYER-CONTROL %c ${AC_VERSION} `, "background:#26A69A;color:#fff;font-weight:700", "background:#333;color:#fff");
