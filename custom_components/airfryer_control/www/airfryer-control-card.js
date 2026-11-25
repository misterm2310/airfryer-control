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

// 📢 Was ist neu – [Version, deutsch, englisch] im Stil von Kegelclub/Fixkosten: jeder Punkt beginnt mit <b>Stichwort:</b> + kurzer Erklärung.
// Mehrere Neuerungen in einem Eintrag mit „ · “ trennen – die normale Liste macht daraus eigene Punkte (nicht mitten im Fettgedruckten).
// Reihenfolge egal: angezeigt wird immer nach Version, Neueste oben. In einer Beta landen die Einträge dieser Beta-Reihe im orangen Kasten.
// ⚠️ Die Texte sind HTML (nur <b>) und werden NICHT maskiert – also nur eigene, feste Texte hier eintragen.
const AC_NEWS = [
  ["1.0.6-beta.4", "⏱️ <b>Laufband mit Restzeit:</b> statt nur „fertig um 18:05“ steht jetzt „noch 12 Min · fertig 18:05 Uhr“ – die Minuten zählen still runter, das Laufband läuft dabei weiter", "⏱️ <b>Ticker with time left:</b> instead of just “done at 18:05” it now says “12 min left · done 18:05” – the minutes count down quietly while the ticker keeps running"],
  ["1.0.6-beta.4", "🕒 <b>Fertig um …:</b> Zone antippen → Uhrzeit eintippen, wann das Essen fertig sein soll. Die Karte rechnet die Startzeit aus (Uhrzeit minus Garzeit) und zeigt sie in Zeile, Laufband und Küchen-Ticker der Einkaufsliste · Zur Startzeit blinkt „⏰ Jetzt starten!“ und mit Handys unter „Fertig melden an“ kommt eine Nachricht · Gestartet wird nie von allein – immer am Gerät", "🕒 <b>Done at …:</b> tap a zone → type the time the food should be done. The card works out the start time (time minus cooking time) and shows it in the row, the ticker and the shopping list's kitchen ticker · At start time “⏰ Start now!” blinks, and with phones under “Report done to” you get a message · It never starts by itself – always on the device"],
  ["1.0.6-beta.4", "😴 <b>Fritteuse hat das Programm verworfen:</b> drückt keiner Start, wirft die Fritteuse ein gesendetes Programm nach ca. 5 Minuten selbst weg. Jetzt steht dann „😴 Verworfen“ in der Zeile mit dem Knopf <b>📤 Nochmal senden</b> – deine Werte und „Was ist drin?“ bleiben stehen", "😴 <b>Fryer dropped the program:</b> if nobody presses Start, the fryer throws away a sent program after about 5 minutes. Now the row says “😴 Dropped” with the button <b>📤 Send again</b> – your values and “What's inside?” stay"],
  ["1.0.6-beta.4", "🔒 <b>Grandzone oder Zone 1/2:</b> Ist Zone 1 oder Zone 2 an (vorbereitet, heizt, gart …), ist die Grandzone grau und gesperrt – und andersherum. So landet nie ein Programm für die ganze Schublade neben schon belegten Zonen", "🔒 <b>Whole basket or zone 1/2:</b> while zone 1 or zone 2 is on (prepared, preheating, cooking …), the whole basket is grey and locked – and the other way round. So a program for the whole drawer never lands next to zones already in use"],
  ["1.0.6-beta.4", "🐞 <b>Schalter unter ⚙️ wieder normal:</b> Seitenleiste, Maskottchen & Co. waren seit beta.3 lange gestrichelte Kästen statt kleiner Schiebeschalter (der neue ↕️-Knopf im Lieblings-Formular hat sie verbogen)", "🐞 <b>Switches under ⚙️ back to normal:</b> sidebar, mascot & co. had been long dashed boxes instead of small sliders since beta.3 (the new ↕️ button in the favourite form bent them)"],
  ["1.0.6-beta.4", "🧹 <b>Aufgeräumt:</b> die Knöpfe „+1 / +3 Min“ und „Nachgaren“ sind raus – Zeit einfach mit − / + bei der Garzeit ändern", "🧹 <b>Tidied up:</b> the “+1 / +3 min” and “cook a bit more” buttons are gone – just change the time with − / + at the cooking time"],
  ["1.0.6-beta.3", "📺 <b>Laufband wie der Küchen-Ticker:</b> läuft nach der Uhrzeit nahtlos weiter, statt jede Minute vorne neu anzufangen (gut für den Fire TV). Beim ↕️ Schütteln und ⏰ Start vergessen blinkt der Rahmen orange und die Kochmützen werden zu pulsierenden ↕️ · Inhalt in Klammern: „Grandzone (Frikadellen)“ · „wartet seit 12 Min“ zählt still weiter", "📺 <b>Ticker like the kitchen ticker:</b> runs on seamlessly by the clock instead of starting over every minute (good for Fire TV). For ↕️ shaking and ⏰ forgot to start the frame blinks orange and the chef hats turn into pulsing ↕️ · Contents in brackets: “Grandzone (meatballs)” · “waiting 12 min” keeps counting quietly"],
  ["1.0.6-beta.3", "⭐ <b>Lieblinge neu:</b> ＋ Neu ist immer da und öffnet ein Formular mit Name, Programm, Temperatur, Zeit und ↕️ · ✏️ Bearbeiten → Liebling antippen = alles ändern, auch den Namen, 🗑️ = löschen · Nach dem letzten Löschen endet ✏️ von selbst (man steckte sonst fest)", "⭐ <b>Favourites reworked:</b> ＋ New is always there and opens a form with name, program, temperature, time and ↕️ · ✏️ Edit → tap a favourite = change everything, the name too, 🗑️ = delete · After deleting the last one ✏️ ends by itself (you used to get stuck)"],
  ["1.0.6-beta.3", "🐞 <b>Grandzone vergisst „Start vergessen?“:</b> nach Abbrechen oder „Bereit“ verschwinden „wartet seit“ und ⏰ wieder – vorher half nur Integration neu laden", "🐞 <b>Whole basket forgets “forgot to start?”:</b> after cancelling or “ready” the “waiting since” and ⏰ go away again – before only reloading the integration helped"],
  ["1.0.6-beta.2", "🍗 <b>Dual Blaze (CAF-P583S): Senden klappt!</b> Dank Markus' Test wissen wir: Die EU-Version will die Konto-Nummer mit kleinem „d“. Das ist jetzt Standard – „Senden“ klappt also auch nach einem Neustart von Home Assistant sofort (Issue #10)", "🍗 <b>Dual Blaze (CAF-P583S): sending works!</b> Thanks to Markus' test we know: the EU version wants the account number with a small “d”. That is now the default – so “Send” works right away, even after a Home Assistant restart (issue #10)"],
  ["1.0.6-beta.1", "🍗 <b>Dual Blaze (CAF-P583S) – Senden-Detektiv:</b> „Senden testen (für Bastler)“ probiert jetzt 9 zusätzliche Schreibweisen, bei denen je ein Feld anders ist. Keine startet die Fritteuse. Die angenommene merkt sich die Integration, „Senden“ nimmt sie dann zuerst (Issue #10)", "🍗 <b>Dual Blaze (CAF-P583S) – send detective:</b> “Test sending (for tinkerers)” now tries 9 extra spellings, each with one field changed. None of them starts the air fryer. The integration remembers the accepted one, and “Send” uses it first (issue #10)"],
  ["1.0.6-beta.1", "🛠️ <b>Befehl senden bei der Dual Blaze:</b> schickt jetzt die zwei Zusatzfelder mit, die die App bei jedem Befehl mitgibt", "🛠️ <b>Send command on the Dual Blaze:</b> now includes the two extra fields the app sends with every command"],
  ["1.0.5", "📲 <b>Fertig-Meldung aufs Handy – ohne Automation:</b> unter ⚙️ › Integration › „Fertig melden an“ dein Handy anhaken. Die Fritteuse schreibt selbst „🍟 Fritteuse fertig!“ (zwei Zonen = eine Nachricht), auf Wunsch auch „↕️ Jetzt schütteln!“. Standard: aus", "📲 <b>Done message to your phone – no automation:</b> under ⚙️ › Integration › “Report done to” tick your phone. The air fryer sends “🍟 Air fryer done!” itself (two zones = one message), optionally also “↕️ Shake now!”. Default: off"],
  ["1.0.5", "↕️ <b>Schütteln-Knopf pro Schublade:</b> beim Programm ein Knopf „↕️ Schütteln: Aus“ – antippen → Aus, Halbzeit oder alle 3, 5, 8 Min. Jede Schublade merkt sich ihre Wahl, ein ⭐ Liebling stellt ihn passend ein (Pommes ja, Kuchen nein). Die alte Schüttel-Erinnerung in ⚙️ ist dafür weg – wer sie an hatte, bekommt sie an allen Schubladen", "↕️ <b>Shake button per drawer:</b> at the program one button “↕️ Shake: Off” – tap it → Off, half time or every 3, 5, 8 min. Each drawer remembers its choice, a ⭐ favourite sets it to match (fries yes, cake no). The old shake reminder in ⚙️ is gone instead – if you had it on, all drawers get it"],
  ["1.0.5", "📺 <b>↕️ im Laufband:</b> zur Schüttel-Zeit blinkt in Karte und Laufband 3 Minuten lang ein ↕️ – fürs Küchen-Tablet und den Fire TV. Schublade auf = weg", "📺 <b>↕️ in the ticker:</b> at shake time a ↕️ blinks in the card and the ticker for 3 minutes – for the kitchen tablet and Fire TV. Drawer open = gone"],
  ["1.0.5", "⏰ <b>Vergessen zu starten?</b> Wartet eine Zone 10 Minuten auf Start am Gerät, zeigen Karte und Laufband einen Hinweis – mit Handys unter „Fertig melden an“ kommt auch eine Nachricht. Zeit unter ⚙️ › Integration, 0 = aus", "⏰ <b>Forgot to start?</b> If a zone waits 10 minutes for start on the device, the card and the ticker show a hint – with phones under “Report done to” you get a message too. Time under ⚙️ › Integration, 0 = off"],
  ["1.0.5", "🏷️ <b>Was ist drin?</b> Pro Zone eintippen, z. B. „Pommes“ – steht im Laufband und in der Fertig-Meldung. Ein ⭐ Liebling trägt seinen Namen selbst ein, nach dem Garen wird es vergessen", "🏷️ <b>What's inside?</b> Type it per zone, e.g. “Fries” – it shows in the ticker and in the done message. A ⭐ favourite fills in its name itself, after cooking it is forgotten"],
  ["1.0.5", "📶 <b>Wieder online = gleich aktuell:</b> ist die Verbindung wieder da (Funkloch, Handy in der Tasche, Fire TV im Standby), holt die Karte die Werte sofort im Hintergrund. Oben kurz „🔄 aktualisiere …“, ohne Verbindung „📴 keine Verbindung – letzter Stand“. Befehle werden bewusst nie nachgeschickt", "📶 <b>Back online = up to date right away:</b> when the connection is back (dead zone, phone in your pocket, Fire TV in standby), the card fetches the values in the background right away. The top briefly shows “🔄 updating …”, without a connection “📴 no connection – last known state”. Commands are deliberately never sent later"],
  ["1.0.5", "🔄 <b>Neue Version da:</b> hat Home Assistant schon eine neuere Version, steht oben ein Hinweis mit <b>„Neu laden“</b> – in Karte, Seitenleiste und Offline-App", "🔄 <b>New version available:</b> if Home Assistant already has a newer version, a hint with <b>“Reload”</b> appears at the top – in the card, the sidebar and the offline app"],
  ["1.0.5", "📱 <b>🔌 Integration auch in der Offline-App:</b> Admins stellen dort jetzt auch Abfrage-Takt, Seitenleiste, Fertig-Meldung und Co. ein · 🛠️ <b>Nicht mehr rausfliegen:</b> Speichern unter ⚙️ › Integration lässt dich auf der Seite", "📱 <b>🔌 Integration in the offline app too:</b> admins now set the polling interval, sidebar, done message and more there as well · 🛠️ <b>No more getting kicked out:</b> saving under ⚙️ › Integration keeps you on the page"],
  ["1.0.5", "📢 <b>Was ist neu</b> wie bei Kegelclub und Fixkosten: fettes Stichwort, eine Neuerung pro Punkt", "📢 <b>What's new</b> like Kegelclub and Fixkosten: bold keyword, one feature per point"],
  ["1.0.4", "⭐ <b>Lieblings-Programme:</b> einmal speichern, danach ein Tipp und es geht an die Zone · 🕘 <b>Zuletzt gesendet:</b> die letzten 5 Programme zum Wiederholen", "⭐ <b>Favourite programs:</b> save once, then one tap sends it to the zone · 🕘 <b>Recently sent:</b> the last 5 programs to repeat"],
  ["1.0.4", "⏱️ <b>Schnellknöpfe +1/+3 min:</b> Garen verlängern, nach „Fertig“ nachgaren, bei „Wartet auf Start“ mit neuer Zeit nochmal hinschicken", "⏱️ <b>Quick buttons +1/+3 min:</b> extend cooking, cook more after “Done”, resend with the new time while “Waiting for start”"],
  ["1.0.4", "↕️ <b>Schüttel-Erinnerung:</b> zur Halbzeit kommt ein Ereignis (für Handy oder Durchsage) – Standard aus", "↕️ <b>Shake reminder:</b> an event at half time (for phone or announcement) – off by default"],
  ["1.0.4", "⚙️ <b>Einstellungen in der Karte:</b> Zahnrad oben, 1:1 wie bei der Einkaufsliste – Suchfeld, Gruppen, Schalter in der Zeile", "⚙️ <b>Settings in the card:</b> cog at the top, 1:1 like the shopping list – search field, groups, switches in the row"],
  ["1.0.4", "📖 <b>Anleitung neu:</b> eigene Seite mit ←, Kapitel zum Aufklappen und Suchfeld · 💡 <b>Tipp beim ersten Start</b>", "📖 <b>New guide:</b> its own page with ←, chapters to unfold and a search field · 💡 <b>Tip on first start</b>"],
  ["1.0.4", "👁️ <b>Schriftgröße und Hell/Dunkel:</b> pro Gerät einstellbar", "👁️ <b>Font size and light/dark:</b> set per device"],
  ["1.0.4", "🔢 <b>TwinFry beim Garen:</b> Zeit und Temperatur lehnt das Gerät ab – die Karte sagt klar „bitte am Gerät ändern“ (#8)", "🔢 <b>TwinFry while cooking:</b> the device refuses time and temperature – the card clearly says “please change it on the device” (#8)"],
  ["1.0.4", "🚪 <b>Schublade offen:</b> bei der TwinFry zeigen alle Zonen „Schublade offen“ · ⏱️ <b>Grandzone:</b> Restzeit 0 Min statt „nicht verfügbar“, wird vor Zone 1/2 zurückgesetzt (#8)", "🚪 <b>Drawer open:</b> on the TwinFry every zone shows “Drawer open” · ⏱️ <b>Grandzone:</b> time remaining 0 min instead of “unavailable”, reset before Zone 1/2 (#8)"],
  ["1.0.4", "📶 <b>Funklöcher:</b> kurze Aussetzer bis 90 s zählen nicht mehr als offline · 🧩 <b>Zonen bleiben,</b> auch wenn die Fritteuse beim HA-Start schläft", "📶 <b>Signal drops:</b> short gaps up to 90 s no longer count as offline · 🧩 <b>Zones stay,</b> even if the fryer sleeps while HA starts"],
  ["1.0.4", "🍳 <b>Rezept-Nummern</b> wie in der VeSync-App · 🆕 <b>Dual Blaze CAF-P583S</b> zum Testen", "🍳 <b>Recipe numbers</b> like the VeSync app · 🆕 <b>Dual Blaze CAF-P583S</b> for testing"],
  ["1.0.4", "🌍 <b>Jede Sprache:</b> Kartentitel, Zonen und Online-Status passen sich Home Assistant an · 📱 <b>Offline-App</b> mit allen Symbolen", "🌍 <b>Every language:</b> card title, zones and online status follow Home Assistant · 📱 <b>Offline app</b> with all icons"],
  ["1.0.3", "🗼 <b>Turbo Tower Pro:</b> eigenes Modellprofil mit Gären · 🍟 <b>Maskottchen</b> Pommes-Tüte · 🎛️ <b>Programm-Kacheln</b> im Einkaufslisten-Stil", "🗼 <b>Turbo Tower Pro:</b> own model profile with proofing · 🍟 <b>Mascot:</b> bag of fries · 🎛️ <b>Program tiles</b> in shopping list style"],
  ["1.0.3", "🔗 <b>Match/Sync</b> bricht ab, wenn ein Fach arbeitet, und merkt sich eigene Werte pro Fach · ⓘ <b>Kurze Hilfe</b> neben den Feldern statt Textwand", "🔗 <b>Match/Sync</b> stops if a basket is busy and keeps own values per basket · ⓘ <b>Short help</b> next to the fields instead of a wall of text"],
  ["1.0.2", "🔌 <b>Schnittstelle</b> für andere Integrationen (z. B. Airfryer Recipes) · 💙 <b>Credits</b> wie bei der Einkaufsliste", "🔌 <b>Interface</b> for other integrations (e.g. Airfryer Recipes) · 💙 <b>Credits</b> like the shopping list"],
  ["1.0.1", "🛠️ <b>Fixes</b> aus den Betas (Issue #1 und #2)", "🛠️ <b>Fixes</b> from the betas (issues #1 and #2)"],
  ["1.0.0", "🎉 <b>Erste offizielle Version</b>", "🎉 <b>First official version</b>"],
];
const AC_NEWS_MAX = 15; // 🆕 höchstens 15 Neuerungen in der normalen Liste
// 🔢 Versionen vergleichen: 1.0.4-beta.10 > 1.0.4-beta.9 > 1.0.3 – und eine fertige Version zählt mehr als ihre Betas
function acVerCmp(a, b) {
  const p = (v) => { const m = /^(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?/.exec(String(v)) || []; return [+m[1] || 0, +m[2] || 0, +m[3] || 0, m[4] == null ? Infinity : +m[4]]; };
  const x = p(a), y = p(b);
  for (let i = 0; i < 4; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}
// 📢 Neueste Version immer oben – egal, in welcher Reihenfolge die Einträge oben stehen (Einträge einer Version bleiben in ihrer Reihenfolge)
const acNewsSorted = () => AC_NEWS.map((n, i) => [n, i]).sort((a, b) => acVerCmp(b[0][0], a[0][0]) || a[1] - b[1]).map((x) => x[0]);
// 🧪 Beta-Kasten: nur Einträge dieser Beta-Reihe (z. B. alle 1.0.4-beta.*), höchste Beta oben. Ohne Beta: leer.
function acBetaNews(ver = AC_VERSION) {
  if (!/-beta/i.test(ver)) return [];
  const base = ver.replace(/-beta.*$/i, "");
  return acNewsSorted().filter((n) => n[0].startsWith(base + "-beta") && acVerCmp(n[0], ver) <= 0);
}
// 📋 Normale Liste: alles bis zur aktuellen Version, OHNE die Einträge im Beta-Kasten – max. 15, Neuestes oben
function acMainNews(ver = AC_VERSION) {
  const beta = new Set(acBetaNews(ver));
  return acNewsSorted().filter((n) => !beta.has(n) && (!ver || acVerCmp(n[0], ver) <= 0));
}
// ✂️ „A · B · C“ → drei Punkte; steht „ · “ innerhalb von <b>…</b>, bleibt es zusammen (wie bei Kegelclub)
const acNewsSplit = (txt) => String(txt).split(" · ").reduce((a, x) => {
  const l = a[a.length - 1];
  if (l !== undefined && (l.match(/<b>/g) || []).length > (l.match(/<\/b>/g) || []).length) a[a.length - 1] = `${l} · ${x}`; else a.push(x);
  return a;
}, []);
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
const SPN = "\u0003"; // Platzhalter für den blinkenden ↕️ („Jetzt schütteln!“)
// 🔒 „An“ für die Sperre Grandzone ↔ Zone 1/2: vorbereitet, heizt, gart, Pause, warmhalten (bereit/fertig/aus = frei)
const ZONE_ON = ["wartet_auf_start", "wartet_auf_sync", "vorheizen", "vorgeheizt", "gart", "pausiert", "warmhalten"];
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
        progs: (mine.find((x) => x.device_id === dev && x.translation_key === "programme" && hass.states[x.entity_id]) || {}).entity_id, // ⭐ Lieblinge + 🕘 zuletzt
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
// 📶 Wieder online – im Hintergrund frisch holen (wie bei der Einkaufsliste)
// Für Doofe: War die Verbindung zu Home Assistant weg (Funkloch, Handy in der Tasche, Fire TV im Standby …)
// und ist sie wieder da, fragt die Karte die Fritteuse SOFORT neu (Knopf „Jetzt aktualisieren“ der Integration),
// statt bis zu einer Minute alte Werte zu zeigen. Nur EINE Abfrage für alle Karten und höchstens alle 30 s –
// das schont schwache Geräte wie den Fire TV. Befehle werden dabei NICHT nachgeschickt (wäre bei Hitze gefährlich).
const AC_BACK = { at: 0, busy: false, cards: new Set() };
function acRefreshIds(hass) {
  const ids = Object.values(hass.entities || {}).filter((e) => e && e.platform === AC && e.translation_key === "aktualisieren" && hass.states[e.entity_id]).map((e) => e.entity_id);
  return ids.length ? ids : Object.keys(hass.states).filter((id) => /^button\..+_((jetzt_)?aktualisieren|refresh_now)$/.test(id) && (!hass.entities || hass.entities[id]?.platform === AC));
}
function acBackOnline(card) {
  AC_BACK.cards.add(card);
  if (AC_BACK.busy || Date.now() - AC_BACK.at < 30000) return;
  AC_BACK.busy = true; AC_BACK.at = Date.now();
  const redraw = () => { for (const c of AC_BACK.cards) if (c.isConnected && c._hass) { c._sig = ""; c.hass = c._hass; } };
  redraw(); // 🔄 Leiste oben: „aktualisiere …“
  setTimeout(async () => { // kurz warten: Home Assistant meldet erst die Entitäten neu an
    const h = card._hass;
    try {
      const ids = h && h.connected !== false && !document.hidden ? acRefreshIds(h) : [];
      if (ids.length) await Promise.race([h.callService("button", "press", { entity_id: ids }), new Promise((ok) => setTimeout(ok, 15000))]);
    } catch (_) { /* egal – der normale Takt holt es sowieso */ }
    AC_BACK.busy = false;
    redraw();
    AC_BACK.cards.clear();
  }, 2000);
}
function zoneName(hass, key, st) {
  if (/grandzone$/.test(key)) return "Grandzone";
  const n = /zone_(\d+)$/.exec(key);
  return n ? tr(hass, `Zone ${n[1]}`, `Zone ${n[1]}`) : (st?.attributes?.friendly_name || key);
}

// 🏷️ Inhalt, ↕️ „Jetzt schütteln!“, ⏰ „Vergessen zu starten?“ – kommen von der Integration (Attribute der Zone)
const zoneExtra = (hass, z) => {
  const a = hass.states[z.state]?.attributes || {};
  const since = Date.parse(a.wartet_seit || "");
  return {
    inhalt: typeof a.inhalt === "string" && a.inhalt.trim() ? a.inhalt.trim() : "",
    shake: a.jetzt_schuetteln === true,
    every: Number.isInteger(a.schuetteln_alle) && a.schuetteln_alle >= 0 ? a.schuetteln_alle : null, // ↕️ Knopf: null = aus, 0 = Halbzeit, X = alle X Min
    forgot: a.start_vergessen === true,
    waitMin: Number.isFinite(since) ? Math.max(0, Math.floor((Date.now() - since) / 60000)) : null,
    // 🕒 „Fertig um …“: Wunsch-Zeit + Startzeit (rechnet die Integration aus) – „jetzt starten“ prüft die Karte selbst nach der Uhr
    goal: typeof a.fertig_wunsch === "string" && Number.isFinite(Date.parse(a.fertig_wunsch)) ? a.fertig_wunsch : "",
    start: typeof a.start_um === "string" && Number.isFinite(Date.parse(a.start_um)) ? a.start_um : "",
    startNow: a.jetzt_starten === true || (typeof a.start_um === "string" && Date.parse(a.start_um) <= Date.now() && !["gart", "vorheizen", "pausiert"].includes(hass.states[z.state]?.state)),
    dropped: a.verworfen === true, // 😴 Fritteuse hat das gesendete Programm selbst weggeworfen
  };
};
// 🔢 Nummer der Zone für die Dienste: Zone 1 = 1, Zone 2 = 2, Grandzone = 3
const zoneNum = (z) => (/grandzone$/.test(z.key) ? 3 : Number((/zone_(\d+)$/.exec(z.key) || [0, 1])[1]));
// „Heißluft · 200 °C · 18 Min“ – für Lieblinge und „Zuletzt gesendet“
const progLine = (hass, p) => `${modeText(hass, p.programm)} · ${p.temperatur} °C · ${p.minuten} ${tr(hass, "Min", "min")}`;

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
  .ac-row.ac-locked { opacity:.55; cursor:default; } .ac-row.ac-locked .ac-state { font-size:.9em; }
  .ac-row.open { background:color-mix(in srgb, var(--primary-color) 10%, transparent); }
  .ac-edit { margin:2px 0 8px; padding:12px; border:1px solid var(--divider-color, rgba(127,127,127,.3)); border-left:4px solid var(--c, #9e9e9e); border-radius:12px; }
  .ac-edit .ac-modes { margin-top:0; }
  .ac-close { display:block; margin:10px auto 0; font:inherit; font-size:.9em; color:var(--secondary-text-color); background:none; border:1px solid var(--divider-color, rgba(127,127,127,.3)); border-radius:12px; padding:6px 16px; cursor:pointer; }
  .ac-row > ha-icon { color:var(--c, #9e9e9e); --mdc-icon-size:30px; flex:none; }
  .ac-txt { flex:1; min-width:0; }
  .ac-name { font-weight:600; }
  .ac-state { color:var(--c, var(--secondary-text-color)); font-size:.95em; }
  .ac-sub { opacity:.75; font-size:.85em; }
  .ac-inh { font-weight:500; opacity:.8; } /* 🏷️ „· Pommes“ hinter dem Zonen-Namen */
  .ac-alert { display:inline-block; margin-top:4px; padding:2px 8px; border-radius:8px; font-size:.85em; font-weight:600; background:rgba(251,140,0,.16); color:#e65100; }
  .ac-drop { background:rgba(30,136,229,.14); color:#1565c0; } .ac-plan { color:#6a1b9a; opacity:1; font-weight:600; }
  .ac-resend { margin-left:6px; border:0; border-radius:999px; padding:2px 10px; font:inherit; font-weight:600; cursor:pointer; background:#43a047; color:#fff; }
  .ac-planbox { margin:6px 0 0; } .ac-planbox .ac-favform input { max-width:9em; }
  .ac-planline { margin-top:6px; font-size:.9em; font-weight:600; color:#6a1b9a; } .ac-planline.late { color:#e65100; }
  .ac-blink { display:inline-block; animation:ac_blink 1s steps(2, start) infinite; } /* ↕️ blinkt – nur an/aus, ganz wenig Arbeit für den Fire TV */
  @keyframes ac_blink { to { visibility:hidden; } }
  @media (prefers-reduced-motion: reduce) { .ac-blink { animation:none; } }
  .ac-tag { margin-left:6px; font-size:.85em; opacity:.8; }
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
  .ac-shk { flex:1; border:1.5px solid var(--divider-color, rgba(127,127,127,.35)); border-radius:12px; background:none; color:inherit; font:inherit; padding:10px 12px; text-align:left; cursor:pointer; margin:6px 0 2px; }
  .ac-shk.on { border-color:#f4511e; background:rgba(244,81,30,.08); }
  .ac-shkarr { float:right; opacity:.7; }
  .ac-shkseg { display:grid; grid-template-columns:repeat(5, 1fr); width:100%; margin:6px 0 4px; }
  .ac-shkseg button { padding:9px 2px; white-space:nowrap; }
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
  .ac-chk { cursor:pointer; } .ac-chk input { width:20px; height:20px; margin:0 0 0 12px; accent-color:var(--primary-color,#03a9f4); flex:none; }
  .ac-updbar { margin:0 4px 8px; padding:8px 10px; border-radius:12px; background:color-mix(in srgb, var(--primary-color,#03a9f4) 14%, transparent); font-size:.88em; display:flex; align-items:center; gap:8px; } /* 🔄 wie bei der Einkaufsliste */
  .ac-updbar b { flex:1; } .ac-updbar button { border:none; border-radius:10px; padding:6px 12px; background:var(--primary-color,#03a9f4); color:#fff; font:inherit; font-weight:600; cursor:pointer; }
  .ac-news { margin:4px 0; padding-left:20px; } .ac-news li { margin:3px 0; }
  .ac-betabox { border:1px solid #fb8c00; border-radius:12px; padding:10px 12px; margin:0 0 12px; background:rgba(251,140,0,.1); } /* 🧪 wie bei der Einkaufsliste */
  .ac-betabox ul { margin:0; padding-left:20px; } .ac-betabox li { margin:3px 0; } .ac-betabox .ac-pgsub { margin:4px 0 2px; }
  /* ⭐ Lieblinge / 🕘 zuletzt gesendet: Knöpfe im Stil der Programm-Kacheln */
  .ac-chips { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 0; }
  .ac-chip { position:relative; border:1.5px solid var(--divider-color, rgba(127,127,127,.35)); border-radius:12px; background:none; color:inherit; padding:8px 12px; cursor:pointer; font:inherit; font-size:.9em; display:flex; flex-direction:column; align-items:flex-start; gap:2px; text-align:left; }
  .ac-chip small { opacity:.7; font-size:.85em; }
  .ac-chip.add { border-style:dashed; color:var(--primary-color); align-items:center; justify-content:center; }
  .ac-chip.del { border-color:#e53935; }
  .ac-chip.del::after { content:"✕"; position:absolute; top:-8px; right:-8px; width:20px; height:20px; border-radius:50%; background:#e53935; color:#fff; font-size:12px; line-height:20px; text-align:center; }
  .ac-chip:disabled { opacity:.4; cursor:default; }
  .ac-flab .ac-edbtn { margin-left:auto; border:0; background:none; color:var(--primary-color); font:inherit; font-size:.95em; cursor:pointer; padding:2px 4px; }
  .ac-favform { display:flex; gap:8px; margin:8px 0 0; } .ac-favform input { flex:1; width:auto; min-width:0; }
  .ac-favform button { white-space:nowrap; flex:none; border:0; border-radius:10px; padding:0 14px; font:inherit; cursor:pointer; background:var(--secondary-background-color, rgba(127,127,127,.15)); color:inherit; }
  .ac-favform button.pri { background:#43a047; color:#fff; }
  .ac-chip.ed { border-style:dashed; } .ac-chip.sel { border-color:var(--primary-color); border-style:solid; box-shadow:0 0 0 1px var(--primary-color) inset; }
  .ac-favbox { margin:10px 0 0; padding:12px; border-radius:12px; border:1.5px solid var(--primary-color); background:var(--secondary-background-color, rgba(127,127,127,.08)); display:flex; flex-direction:column; gap:8px; }
  .ac-favtitle { font-weight:600; }
  .ac-frow { display:flex; align-items:center; gap:10px; } .ac-frow > span { flex:0 0 120px; font-size:.9em; opacity:.85; }
  .ac-frow .ac-num { flex:1; width:auto; min-width:0; }
  .ac-favbox button { white-space:nowrap; display:inline-flex !important; flex-direction:row !important; align-items:center; justify-content:center; gap:6px; height:auto; min-height:38px; line-height:1.2; width:auto; }
  /* ↕️ Schütteln-Knopf im Lieblings-Formular – eigener Name, sonst überschreibt er die Schalter unter ⚙️ (Seitenleiste & Co.) */
  .ac-ftgl { flex:1; justify-content:flex-start !important; border:1.5px dashed var(--divider-color, rgba(127,127,127,.4)); border-radius:10px; padding:7px 10px; font:inherit; background:none; color:inherit; cursor:pointer; text-align:left; }
  .ac-ftgl.on { border-style:solid; border-color:#f4511e; background:rgba(244,81,30,.12); }
  .ac-favbtns { display:flex; flex-wrap:wrap; gap:8px; margin-top:4px; } .ac-favbtns span { flex:1; }
  .ac-favbtns button { border:0; border-radius:10px; padding:9px 11px; font:inherit; cursor:pointer; background:var(--card-background-color, rgba(127,127,127,.15)); color:inherit; }
  .ac-favbtns .pri { background:#43a047; color:#fff; } .ac-favbtns .del { background:none; color:#e53935; border:1.5px solid #e53935; }
  /* ⏱️ +1 / +3 min */
  .ac-flash { margin:-2px 0 8px; padding:8px 12px; border-radius:10px; font-size:.88em; background:var(--secondary-background-color, rgba(127,127,127,.12)); }
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
    ${acSec("⭐", t("Lieblinge & zuletzt gesendet", "Favourites & recently sent"), `<p>${t("Zeile antippen → ganz oben stehen deine <b>⭐ Lieblinge</b>. Antippen = sofort an diese Zone senden. <b>＋ Neu</b> öffnet ein kleines Formular: Name (z. B. „Pommes“), Programm, Temperatur, Zeit und <b>↕️ Schütteln</b> (für Kuchen aus) – vorbelegt mit dem, was unten gerade eingestellt ist. <b>✏️ Bearbeiten</b> → Liebling antippen = alles ändern, auch den Namen, oder mit 🗑️ löschen.", "Tap a row → your <b>⭐ favourites</b> are at the top. Tap = send to this zone right away. <b>＋ New</b> opens a small form: name (e.g. “Fries”), program, temperature, time and <b>↕️ shake</b> (off for cake) – prefilled with what is set below. <b>✏️ Edit</b> → tap a favourite = change everything, the name too, or delete it with 🗑️.")}</p><p>${t("Darunter <b>🕘 Zuletzt gesendet</b>: die letzten 5 Programme. Lieblinge und Verlauf liegen in Home Assistant – Handy und Küchen-Tablet sehen dasselbe.", "Below that <b>🕘 Recently sent</b>: the last 5 programs. Favourites and history live in Home Assistant – phone and kitchen tablet see the same.")}</p>`, "#fdd835", t("Ein Tipp statt drei Felder", "One tap instead of three fields"))}
    ${acSec("📲", t("Fertig-Meldung aufs Handy", "Done message to your phone"), `<p>${t("Unter ⚙️ › Integration › <b>Fertig melden an</b> Häkchen bei deinem Handy setzen und speichern. Die Fritteuse schreibt dann selbst „🍟 Fritteuse fertig!“ – ohne eigene Automation. Auf Wunsch auch „↕️ Jetzt schütteln!“ (Haken „↕️ auch aufs Handy“ – wann, stellst du beim Programm ein). Kein Häkchen = aus (Standard). Wer selbst auf Stopp drückt, bekommt keine Meldung.", "Under ⚙️ › Integration › <b>Report done to</b> tick your phone and save. The air fryer then sends “🍟 Air fryer done!” itself – no automation needed. Optionally also “↕️ Shake now!” (tick “↕️ also to the phone” – when is set at the program). No tick = off (default). Pressing stop yourself sends no message.")}</p>`, "#8e24aa", t("ohne Automation", "no automation"))}
    ${acSec("🏷️", t("Was ist drin?", "What's inside?"), `<p>${t("Zeile antippen → <b>🏷️ Was ist drin?</b> eintippen, z. B. „Pommes“. Dann steht im Laufband „Zone 1 (Pommes): fertig um 18:30 Uhr“ und in der Fertig-Meldung aufs Handy „Zone 1 (Pommes): fertig“. Tippst du einen ⭐ Liebling an, steht sein Name von selbst da.", "Tap a row → type <b>🏷️ What's inside?</b>, e.g. “Fries”. Then the ticker says “Zone 1 (Fries): done at 18:30” and the done message on your phone “Zone 1 (Fries): done”. Tap a ⭐ favourite and its name lands there by itself.")}</p><p>${t("Nach dem Garen (Zone wieder „Bereit“ oder „Aus“) wird es von selbst vergessen.", "After cooking (zone back to “Ready” or “Off”) it is forgotten by itself.")}</p>`, "#6d4c41", t("Pommes oder Kuchen?", "Fries or cake?"))}
    ${acSec("↕️", t("Schütteln", "Shaking"), `<p>${t("Zone antippen → beim Programm steht <b>„↕️ Schütteln: Aus“</b>. Antippen klappt die Zeiten auf: <b>Aus · Halbzeit · alle 3 · 5 · 8 Min</b>. Eine antippen = gespeichert, die Zeile klappt wieder zu. Jede Schublade merkt sich ihre Wahl. Zur Schüttel-Zeit kommt das Ereignis <code>airfryer_control_schuetteln</code> für eine Handy-Nachricht oder Durchsage per Automation.", "Tap a zone → at the program you see <b>“↕️ Shake: Off”</b>. Tap it to open the times: <b>Off · half time · every 3 · 5 · 8 min</b>. Tap one = saved, the row closes again. Each drawer remembers its choice. At shake time the event <code>airfryer_control_schuetteln</code> fires for a phone message or announcement via an automation.")}</p><p>${t("Dazu blinkt 3 Minuten lang <b>↕️ in der Karte und im Laufband</b> – auch am Küchen-Tablet und Fire TV. Schublade auf = geschüttelt, dann ist es sofort weg. Ein ⭐ Liebling mit ↕️ aus (z. B. Kuchen) stellt den Knopf auf Aus, einer mit ↕️ an auf Halbzeit (wenn er aus war).", "Also <b>↕️ blinks in the card and the ticker</b> for 3 minutes – on the kitchen tablet and Fire TV too. Drawer open = shaken, then it is gone right away. A ⭐ favourite with ↕️ off (e.g. cake) sets the button to off, one with ↕️ on to half time (if it was off).")}</p>`, "#f4511e", t("pro Schublade", "per drawer"))}
    ${acSec("⏰", t("Vergessen zu starten?", "Forgot to start?"), `<p>${t("Nach „Senden“ muss man am Gerät auf Start drücken. Wartet eine Zone <b>10 Minuten</b> (einstellbar unter ⚙️ › Integration) auf Start, steht in der Karte und im Laufband „⏰ Start am Gerät vergessen?“ – mit Handys unter „Fertig melden an“ kommt auch eine Nachricht. Für Automationen: Ereignis <code>airfryer_control_start_vergessen</code>.", "After “Send” you have to press Start on the device. If a zone waits <b>10 minutes</b> (set under ⚙️ › Integration) for start, the card and the ticker show “⏰ Forgot to press Start?” – with phones under “Report done to” you also get a message. For automations: event <code>airfryer_control_start_vergessen</code>.")}</p>`, "#fb8c00", t("Der Klassiker", "The classic"))}
    ${acSec("🕒", t("Fertig um …", "Done at …"), `<p>${t("Zeile antippen → bei <b>🕒 Fertig um</b> die Uhrzeit eintippen, wann das Essen fertig sein soll, z. B. 18:30. Die Karte rechnet <b>Uhrzeit minus Garzeit = Startzeit</b> und zeigt in der Zeile und im Laufband „🕒 Start um 18:12 → fertig um 18:30“ (auch im Küchen-Ticker der Einkaufsliste). Zur Startzeit blinkt <b>„⏰ Jetzt starten!“</b>, und mit Handys unter ⚙️ › Integration › Fertig melden an kommt eine Nachricht.", "Tap a row → at <b>🕒 Done at</b> type the time the food should be done, e.g. 18:30. The card works out <b>time minus cooking time = start time</b> and shows “🕒 Start at 18:12 → done at 18:30” in the row and the ticker (also in the shopping list's kitchen ticker). At start time <b>“⏰ Start now!”</b> blinks, and with phones under ⚙️ › Integration › Report done to you get a message.")}</p><p>${t("<b>Gestartet wird nie von allein</b> – Senden und Start drückst du selbst. Am besten erst zur Startzeit senden: Die Fritteuse wirft ein gesendetes Programm nach ca. 5 Minuten ohne Start selbst weg. Dann steht „😴 Verworfen“ in der Zeile mit <b>📤 Nochmal senden</b> – deine Werte bleiben stehen. Fängt die Zone an zu garen, ist die Uhrzeit erledigt und verschwindet.", "<b>It never starts by itself</b> – you press Send and Start. Best send only at start time: the fryer throws away a sent program after about 5 minutes without Start. Then the row says “😴 Dropped” with <b>📤 Send again</b> – your values stay. Once the zone starts cooking, the time is done and disappears.")}</p>`, "#6a1b9a", t("Startzeit ausrechnen lassen", "Let it work out the start time"))}
    ${acSec("⏹️", t("Knopf rechts", "Button on the right"), `<p>${t("<b>Grün</b> = senden, <b>Orange</b> = abbrechen (noch nicht gestartet), <b>Rot</b> = Garen beenden.", "<b>Green</b> = send, <b>orange</b> = cancel (not started yet), <b>red</b> = stop cooking.")}</p>`, "#e53935", t("Senden, Abbrechen, Beenden", "Send, cancel, stop"))}
    ${acSec("🔗", "Match & Sync", `<p>${t("Bei zwei Zonen: „Einstellungen übernehmen“ kopiert die andere Zone. <b>Match senden</b> = beide Zonen bekommen dieselben Werte. <b>Sync senden</b> = beide werden zur selben Zeit fertig.", "With two zones: “Copy settings” copies the other zone. <b>Send Match</b> = both zones get the same values. <b>Send Sync</b> = both finish at the same time.")}</p><p>${t("Der Sync-Hinweis sagt dir außerdem, wann du die zweite Zone startest.", "The sync hint also tells you when to start the second zone.")}</p>`, "#1e88e5", t("Zwei Körbe, ein Abendessen", "Two baskets, one dinner"))}
    ${acSec("🔢", t("Oben in der Karte", "At the top of the card"), `<p>${t("Die blaue Zahl = so viele Zonen garen gerade. 🟢/🔴 = Fritteuse online oder offline. 📴 = gerade keine Verbindung zu Home Assistant (die Karte zeigt den letzten Stand). Ist die Verbindung wieder da, holt die Karte die Werte sofort im Hintergrund (🔄). <b>ⓘ</b> = Infos & Credits. <b>⚙️</b> = Einstellungen.", "The blue number = zones cooking right now. 🟢/🔴 = fryer online or offline. 📴 = no connection to Home Assistant right now (the card shows the last known state). Once it is back, the card fetches the values in the background right away (🔄). <b>ⓘ</b> = info & credits. <b>⚙️</b> = settings.")}</p>`, "#8e24aa", t("Zahl, Punkt, Knöpfe", "Number, dot, buttons"))}
    ${acSec("⚙️", t("Einstellungen", "Settings"), `<p>${t("Das Zahnrad oben in der Karte öffnet die Einstellungen:", "The cog at the top of the card opens the settings:")}</p><ul class="ac-ol"><li>${t("<b>👁️ Ansicht</b>: Schriftgröße und Hell/Dunkel – gilt nur auf diesem Gerät.", "<b>👁️ View</b>: font size and light/dark – only on this device.")}</li><li>${t("<b>🍟 Karte</b>: Maskottchen, Leiste oben, Anleitung-Knopf – nur auf diesem Gerät.", "<b>🍟 Card</b>: mascot, top bar, guide button – only on this device.")}</li><li>${t("<b>🔌 Integration</b> (nur Admins): Abfrage-Takt, Seitenleiste, „Vergessen zu starten?“ und Fertig-Meldung aufs Handy – gilt für alle, auch in der Offline-App.", "<b>🔌 Integration</b> (admins only): polling interval, sidebar, “Forgot to start?” and done message to your phone – for everyone, in the offline app too.")}</li></ul>`, "#607d8b", t("Ansicht, Karte, Integration", "View, card, integration"))}
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
    this._backCheck(hass);
    this._verCheck();
    // 📄 Auf einer Seite nicht neu zeichnen – sonst gehen Suchtext und aufgeklappte Kapitel verloren
    if (this._page && this._pageDrawn && lang === hass.language) return;
    const zones = findZones(hass);
    const sig = zones.map((z) => [z.state, z.finish, z.mode, z.temp, z.time, z.sw]
      .map((e) => { const s = hass.states[e]; return s ? s.state + "|" + (s.attributes?.min ?? "") + (s.attributes?.max ?? "") : "-"; }).join(",")).join(";")
      + "#" + (findOnline(hass, zones)?.state || "") + (hass.connected === false ? "x" : "") + (AC_BACK.busy ? "b" : "") + this._open + (hass.language || "") + new Date().getHours()
      + "#" + JSON.stringify(zones.map((z) => { const a = hass.states[z.progs]?.attributes || {}; return [a.lieblinge, a.zuletzt]; }))
      + "#" + JSON.stringify(zones.map((z) => { const x = zoneExtra(hass, z); return [x.inhalt, x.shake, x.every, x.forgot, x.forgot ? x.waitMin : 0, x.goal, x.start, x.startNow, x.dropped]; }))
      + (zones.some((z) => zoneExtra(hass, z).goal) ? "#" + Math.floor(Date.now() / 60000) : ""); // 🕒 „in 42 Min“ jede Minute neu
    if (sig === this._sig) return;
    // ⌨️ Tippt gerade jemand den Namen eines Lieblings? Dann nicht dazwischenfunken (kommt gleich danach)
    if (this._favForm && this.shadowRoot.activeElement?.matches?.("[data-favf]")) return;
    if (this.shadowRoot.activeElement?.matches?.("[data-inhalt], [data-plan]")) return; // 🏷️/🕒 tippt gerade „Was ist drin?“ oder die Uhrzeit
    this._sig = sig;
    this._zones = zones;
    this._render();
  }

  // 📶 Verbindung zu Home Assistant war weg und ist wieder da? Dann im Hintergrund frisch holen (siehe AC_BACK)
  _backCheck(hass) {
    const up = hass.connected !== false, was = this._up;
    this._up = up;
    if (was === false && up) { this._verAt = 0; acBackOnline(this); } // 🔄 auch gleich nach einer neuen Version schauen
  }

  // 🔄 Neue Version da? Home Assistant fragen, welche Version dort läuft (höchstens jede Minute, nur wenn die Seite sichtbar ist)
  async _verCheck() {
    const h = this._hass;
    if (!h || typeof h.callWS !== "function" || !AC_VERSION || document.hidden) return;
    const now = Date.now();
    if (this._verAt && now - this._verAt < 60000) return;
    this._verAt = now;
    try {
      const r = await h.callWS({ type: "airfryer_control/info" });
      const v = String(r?.version || "");
      if (v !== (this._srvVer || "")) { this._srvVer = v; this._render(); }
    } catch (_) { /* ältere Version in HA oder offline – dann eben kein Hinweis */ }
  }
  // 🔄 Hinweis-Leiste wie bei der Einkaufsliste: HA hat schon eine neuere Version als die geladene Karte
  _updHtml() {
    const server = this._srvVer, hass = this._hass;
    if (!server || !AC_VERSION || server === AC_VERSION) return "";
    return acVerCmp(server, AC_VERSION) > 0
      ? `<div class="ac-updbar" role="status">🔄 <b>${esc(tr(hass, `Neue Version ${server} ist da (hier läuft noch ${AC_VERSION}).`, `New version ${server} is available (this still runs ${AC_VERSION}).`))}</b><button type="button" data-reload>${esc(tr(hass, "Neu laden", "Reload"))}</button></div>`
      : `<div class="ac-updbar" role="status">🔄 <b>${esc(tr(hass, `Die Karte ist schon ${AC_VERSION}, Home Assistant noch ${server} – bitte Home Assistant neu starten.`, `The card is already ${AC_VERSION}, Home Assistant still ${server} – please restart Home Assistant.`))}</b></div>`;
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
    if (page === "settings" && !this._integ && this._canInteg()) this._integLoad();
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
    const lost = hass.connected === false; // 📶 keine Verbindung zu Home Assistant (nicht die Fritteuse)
    const pill = lost ? ["off", `📴 ${tr(hass, "keine Verbindung – letzter Stand", "no connection – last known state")}`]
      : AC_BACK.busy ? ["", `🔄 ${tr(hass, "aktualisiere …", "updating …")}`]
      : on ? ["", `🟢 ${tr(hass, "verbunden", "connected")}`] : ["off", `🔴 ${tr(hass, "offline", "offline")}`];
    const top = !eff.top ? "" : `<div class="ac-top">
        <span class="ac-pill ${pill[0]}">${esc(pill[1])}</span>
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
        const x = zoneExtra(hass, z);
        const lock = this._lockedBy(z, zones); // 🔒 Grandzone ↔ Zone 1/2
        if (lock.length) {
          if (this._open === z.key) this._open = null;
          const who = lock.map((o) => o.name).join(tr(hass, " und ", " and "));
          return `<div class="ac-row ac-locked" data-z="${esc(z.key)}" data-locked="1" style="--c:#bdbdbd" title="${esc(tr(hass, `Gesperrt, solange ${who} an ist`, `Locked while ${who} is on`))}">
          <ha-icon icon="mdi:toaster-oven"></ha-icon>
          <div class="ac-txt"><div class="ac-name">${esc(z.name)}</div>
            <div class="ac-state">🔒 ${esc(tr(hass, `Gesperrt – ${who} ist an`, `Locked – ${who} is on`))}</div></div>
          <button class="ac-go" style="--b:#9e9e9e" disabled aria-label="${esc(tr(hass, "Gesperrt", "Locked"))}"><ha-icon icon="mdi:lock-outline"></ha-icon></button>
        </div>`;
        }
        // ↕️ blinkt zur Schüttel-Zeit, ⏰ wenn der Start am Gerät vergessen wurde
        const alert = x.shake ? `<div class="ac-alert ac-shake" role="status"><span class="ac-blink">↕️</span> ${esc(tr(hass, "Jetzt schütteln!", "Shake now!"))}</div>`
          : x.forgot ? `<div class="ac-alert" role="status">⏰ ${esc(tr(hass, `Wartet seit ${x.waitMin ?? "?"} Min – Start am Gerät vergessen?`, `Waiting ${x.waitMin ?? "?"} min – forgot to press Start?`))}</div>`
          : x.startNow && x.goal ? `<div class="ac-alert ac-shake" role="status"><span class="ac-blink">⏰</span> ${esc(st?.state === "wartet_auf_start"
            ? tr(hass, `Jetzt am Gerät starten – fertig um ${clock(x.goal, hass)} Uhr`, `Press Start now – done at ${clock(x.goal, hass)}`)
            : tr(hass, `Jetzt senden und starten – fertig um ${clock(x.goal, hass)} Uhr`, `Send and start now – done at ${clock(x.goal, hass)}`))}</div>`
          : x.dropped ? `<div class="ac-alert ac-drop" role="status">😴 ${esc(tr(hass, "Fritteuse hat das Programm verworfen (kein Start)", "Fryer dropped the program (no start)"))} <button type="button" class="ac-resend" data-go="${esc(z.key)}">📤 ${esc(tr(hass, "Nochmal senden", "Send again"))}</button></div>`
          : x.start && x.goal ? `<div class="ac-sub ac-plan">🕒 ${esc(tr(hass, `Start um ${clock(x.start, hass)} Uhr → fertig um ${clock(x.goal, hass)} Uhr`, `Start at ${clock(x.start, hass)} → done at ${clock(x.goal, hass)}`))}</div>` : "";
        return `<div class="ac-row ${this._open === z.key ? "open" : ""}" data-z="${esc(z.key)}" style="--c:${this._color(z)}" title="${esc(tr(hass, "Antippen = Programm, Temperatur und Zeit", "Tap = program, temperature and time"))}">
          <ha-icon icon="mdi:toaster-oven"></ha-icon>
          <div class="ac-txt"><div class="ac-name">${esc(z.name)}${x.inhalt ? ` <span class="ac-inh">· ${esc(x.inhalt)}</span>` : ""}</div>
            <div class="ac-state">${esc(stateText(hass, st?.state))}</div>
            ${sub ? `<div class="ac-sub">${esc(sub)}</div>` : ""}${alert}
            </div>
          <button class="ac-go" data-go="${esc(z.key)}" style="--b:${b.color}" title="${esc(b.text)}" ${z.sw ? "" : "disabled"}><ha-icon icon="${b.icon}"></ha-icon></button>
        </div>${this._msg?.key === z.key ? `<div class="ac-flash" role="status">${esc(this._msg.text)}</div>` : ""}${this._open === z.key ? this._zoneHtml(z, zones) : ""}`;
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
    this.shadowRoot.innerHTML = `<style>${BASE_CSS}</style><div class="ac-wrap ${sz}">${top}${this._updHtml()}
      <ha-card class="${th}">${body}</ha-card>
      ${!eff.guide || this._page ? "" : `<div class="ac-foot"><button type="button" data-guide><ha-icon icon="mdi:book-open-page-variant-outline"></ha-icon><span>${esc(tr(hass, "Anleitung", "Guide"))}</span></button></div>`}</div>`;
    this._pageDrawn = !!this._page;
    this._wire();
  }

  // 💡 Tipp beim ersten Start (einmal pro Gerät, wegklickbar). Neuerungen stehen unter ⚙️ › Über › Was ist neu.
  _boxHtml(eff) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    if (eff.guide && !lsGet("tip", false)) {
      return `<div class="ac-box" style="--bc:#f9a825" data-box="tip"><b>💡 ${t("Neu hier?", "New here?")}</b><p>${t("Unten auf 📖 Anleitung tippen – da steht alles drin. Und oben unter ⚙️ stellst du Schriftgröße, Hell/Dunkel und mehr ein.", "Tap 📖 Guide at the bottom – it's all in there. And under ⚙️ at the top you set font size, light/dark and more.")}</p>
        <div class="ac-bbtns"><button type="button" class="pri" data-tip="guide">📖 ${t("Zeig mir", "Show me")}</button><button type="button" data-tip="ok">${t("Okay", "Okay")}</button></div></div>`;
    }
    return "";
  }

  // 📄 Seite: Kopf mit ← + Inhalt
  _pageHtml() {
    const hass = this._hass, t = (d, e) => tr(hass, d, e);
    const P = {
      guide: ["📖", t("Anleitung", "Guide"), "#3949ab"],
      settings: ["⚙️", t("Einstellungen", "Settings"), "#607d8b"],
      credits: ["ℹ️", t("Über Airfryer Control", "About Airfryer Control"), "#0288d1"],
      news: ["📢", t("Was ist neu", "What's new"), "#fb8c00"],
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

  // 📢 Was ist neu – 1:1 wie bei der Einkaufsliste: oranger Beta-Kasten oben (nur in einer Beta), darunter max. 15 Neuerungen
  _newsHtml() {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    const beta = acBetaNews(), main = acMainNews();
    const upTo = main.length ? main[0][0].replace(/-beta.*$/i, "") : AC_VERSION;
    const box = beta.length ? `<div class="ac-betabox"><b>🧪 ${t("Du bist in der Beta", "You are in the beta")} <span translate="no">${esc(AC_VERSION)}</span></b>
        <p class="ac-pgsub">${t("Neu in dieser Beta:", "New in this beta:")}</p>
        <ul>${beta.map((n) => `<li><b translate="no">${esc(n[0].replace(/^.*-(beta\.\d+)$/i, "$1"))}</b> · ${tr(hass, n[1], n[2])}</li>`).join("")}</ul></div>` : "";
    // ✂️ wie bei Kegelclub/Fixkosten: an „ · “ in eigene Punkte trennen – aber nicht mitten im Fettgedruckten; höchstens 15 Punkte
    const items = main.flatMap((n) => acNewsSplit(tr(hass, n[1], n[2]))).slice(0, AC_NEWS_MAX);
    return `${box}<p class="ac-pgsub">${t("Die letzten Neuerungen bis Version", "The latest new features up to version")} <b translate="no">${esc(upTo || "?")}</b> – ${t("das Neueste steht oben", "the newest is at the top")}</p>
      <ul class="ac-news">${items.map((x) => `<li>${x}</li>`).join("")}</ul>
      <p class="elcsmall"><a href="${AC_REPO}/releases" target="_blank" rel="noopener">${t("Alle Versionen auf GitHub", "All versions on GitHub")}</a></p>`;
  }

  // ⚙️ Einstellungen – 1:1 wie bei der Einkaufsliste: Suchfeld, Gruppen zum Aufklappen, Zeilen mit buntem Symbol,
  // Schalter direkt in der Zeile, Antippen der Zeile = eigene Seite mit Erklärung
  _setGroups() {
    const hass = this._hass, t = (d, e) => tr(hass, d, e), v = this._view(), eff = this._eff();
    const admin = this._canInteg() && (this._integ || hass.user?.is_admin || (inApp() && !this._integDenied)); // 🔌 in der App gibt es kein hass.user – der Server sagt, ob Admin
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
        { key: "forgot", icon: "mdi:timer-alert-outline", color: "#fb8c00", title: t("Vergessen zu starten?", "Forgot to start?"), info: wait || (+io.start_vergessen ? t(`Hinweis nach ${+io.start_vergessen} Min ohne Start · gilt für alle`, `Hint after ${+io.start_vergessen} min without start · for everyone`) : t("Aus", "Off")), kw: "vergessen start starten wartet hinweis erinnerung forgot start waiting hint reminder" },
        { key: "notify", icon: "mdi:cellphone-message", color: "#8e24aa", title: t("Fertig melden an", "Report done to"), info: wait || ((io.melden_an || []).length ? `📲 ${(io.melden_an || []).join(", ")}${io.melden_schuetteln ? t(" · auch ↕️", " · also ↕️") : ""}${io.melden_vergessen !== false ? t(" · auch ⏰", " · also ⏰") : ""}` : t("Aus · Handy-Nachricht ohne Automation", "Off · phone message without automation")), kw: "handy melden nachricht fertig benachrichtigung notify mobile app phone notification push" },
        { key: "smasc", icon: "mdi:emoticon-happy-outline", color: "#fb8c00", title: t("Maskottchen in der Seitenleiste", "Mascot in the sidebar"), info: wait || t("Nur die Seite in der Seitenleiste · gilt für alle", "Only the sidebar page · for everyone"), kw: "maskottchen seitenleiste mascot sidebar", on: io ? !!io.maskottchen : null },
        inApp() ? null : { key: "haopts", icon: "mdi:cog-outline", color: "#607d8b", title: t("Alle Optionen in Home Assistant", "All options in Home Assistant"), info: t("Öffnet die Integration (auch Zeiteinheit)", "Opens the integration (also time unit)"), kw: "optionen integration zeiteinheit options time unit", act: "haopts" },
      ];
      for (let i = rows.length - 1; i >= 0; i--) if (!rows[i]) rows.splice(i, 1); // App: ohne „Alle Optionen in Home Assistant“
      if ((this._integ?.entries || []).length > 1) rows.unshift({ key: "entry", icon: "mdi:toaster-oven", color: "#6d4c41", title: t("Fritteuse", "Air fryer"), info: (this._integ.entries.find((e) => e.entry_id === this._integ.entry) || {}).title || "", kw: "fritteuse geraet auswahl fryer device" });
      groups.push({ key: "integ", title: t("🔌 Integration (nur Admins)", "🔌 Integration (admins only)"), rows });
    }
    const about = [
      { key: "aguide", icon: "mdi:book-open-page-variant-outline", color: "#3949ab", title: t("Anleitung", "Guide"), info: t("Alles Schritt für Schritt, mit Suche", "Everything step by step, with search"), kw: "anleitung hilfe guide help", page: "guide" },
    ];
    about.push({ key: "anews", icon: "mdi:new-box", color: "#fb8c00", title: t("Was ist neu", "What's new"), info: `Version ${AC_VERSION || "?"}`, kw: "neu beta neuigkeiten version news was ist neu whats new", page: "news" });
    about.push(
      { key: "acredits", icon: "mdi:information-outline", color: "#0288d1", title: t("Credits, Spenden, Datenschutz", "Credits, donations, privacy"), info: "Mister-M · MIT", kw: "credits spenden paypal datenschutz github fehler idee donate privacy bug", page: "credits" },
      { key: "atip", icon: "mdi:lightbulb-on-outline", color: "#f9a825", title: t("Tipp wieder zeigen", "Show tip again"), info: t("Zeigt den 💡 Tipp über den Zonen noch einmal", "Shows the 💡 tip above the zones once more"), kw: "tipp kasten wieder zeigen tip box again", act: "tipagain" },
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
    // 🔌 Auswahl für einen Wert der Integration (wird sofort gespeichert)
    const segIo = (k, cur, opts) => `<div class="ac-seg" role="group">${opts.map(([val, label]) => `<button type="button" data-ioval="${k}" data-val="${val}" class="${cur === val ? "on" : ""}" aria-pressed="${cur === val}">${esc(label)}</button>`).join("")}</div>`;
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
      case "forgot": {
        const min = io.start_vergessen == null ? 10 : +io.start_vergessen;
        return `<p>${esc(t("Nach „Senden“ muss man am Gerät noch auf Start drücken – das vergisst man gern. Wartet eine Zone zu lange auf Start, steht in der Karte und im Laufband „⏰ Start am Gerät vergessen?“. Dazu kommt einmal das Ereignis „airfryer_control_start_vergessen“, und mit Handys unter „Fertig melden an“ auch eine Nachricht.", "After “Send” you still have to press Start on the device – easy to forget. If a zone waits too long for start, the card and the ticker show “⏰ Forgot to press Start?”. Plus the event “airfryer_control_start_vergessen” fires once, and with phones under “Report done to” you get a message too."))}</p>
          <div class="ac-flab"><span>${esc(t("Hinweis nach", "Hint after"))}</span></div>${segIo("start_vergessen", min, [[0, t("Aus", "Off")], [5, "5 Min"], [10, "10 Min"], [15, "15 Min"], [20, "20 Min"]])}
          <p class="ac-pgsub">${esc(t("Standard: 10 Minuten · gilt für alle", "Default: 10 minutes · for everyone"))}</p>${reload}`;
      }
      case "notify": {
        const chosen = new Set(io.melden_an || []);
        const all = (this._integ?.notify || Object.keys(hass.services?.notify || {})).filter((x) => x !== "send_message"); // 📲 Liste kommt vom Server (die App kennt hass.services nicht)
        for (const c of chosen) if (!all.includes(c)) all.push(c); // gewählt, aber gerade nicht da → trotzdem zeigen
        all.sort((a, b) => (b.startsWith("mobile_app_") - a.startsWith("mobile_app_")) || a.localeCompare(b));
        const list = all.length ? all.map((x) => `<label class="ac-lrow ac-swline ac-chk"><input type="checkbox" data-nsvc="${esc(x)}" ${chosen.has(x) ? "checked" : ""}><span class="ac-grow" style="padding:10px 12px"><b translate="no">${esc(x.startsWith("mobile_app_") ? "📱 " + x.slice(11) : x)}</b><small translate="no">notify.${esc(x)}</small></span></label>`).join("")
          : `<p class="ac-pgsub">${esc(t("Kein notify-Dienst gefunden. Installiere die Home-Assistant-App auf dem Handy und melde dich an – dann taucht hier „📱 dein_handy“ auf.", "No notify service found. Install the Home Assistant app on your phone and sign in – then “📱 your_phone” shows up here."))}</p>`;
        return `<p>${esc(t("Die Fritteuse schreibt dir selbst aufs Handy, wenn sie fertig ist – ganz ohne eigene Automation. Häkchen bei einem oder mehreren Handys setzen und speichern. Kein Häkchen = aus (Standard). Hat jemand selbst auf Stopp gedrückt, kommt keine Meldung.", "The air fryer messages your phone itself when it is done – no automation needed. Tick one or more phones and save. No tick = off (default). If someone pressed stop themselves, no message is sent."))}</p>
          ${list}
          ${sw("nshake", !!io.melden_schuetteln, t("↕️ auch aufs Handy", "↕️ also to the phone"), t("„↕️ Jetzt schütteln!“ · wann, stellst du pro Schublade beim Programm ein · Standard: aus", "“↕️ Shake now!” · when is set per drawer at the program · default: off"))}
          ${sw("nforgot", io.melden_vergessen !== false, t("Auch „⏰ Vergessen zu starten?“", "Also “⏰ Forgot to start?”"), t("Standard: an · nur an die Handys oben", "Default: on · only to the phones above"))}
          <button type="button" class="ac-big" data-nsave style="--b:#43a047">💾 ${esc(t("Speichern", "Save"))}</button>${reload}`;
      }
      case "interval": return `<p>${esc(t("So oft fragt Home Assistant die Cosori-Cloud, wenn nichts gart (30–600 Sekunden). Beim Garen wird immer alle 15 Sekunden gefragt.", "How often Home Assistant asks the Cosori cloud while nothing is cooking (30–600 seconds). While cooking it always asks every 15 seconds."))}</p>
        <div class="ac-lrow ac-swline"><span class="ac-grow" style="padding:10px 0 10px 12px"><b>${esc(t("Sekunden", "Seconds"))}</b><small>30–600</small></span><input type="number" class="ac-num" data-io="intervall" min="30" max="600" step="10" value="${esc(io.intervall ?? 60)}" style="margin-right:12px"></div>
        <button type="button" class="ac-big" data-iosave style="--b:#43a047">💾 ${esc(t("Speichern", "Save"))}</button>${reload}`;
      case "entry": return `<p>${esc(t("Du hast mehrere Fritteusen. Wähle, für welche die Integrations-Einstellungen gelten sollen.", "You have several air fryers. Choose which one the integration settings are for."))}</p><select class="ac-num" style="width:100%" data-integentry>${(this._integ?.entries || []).map((e) => `<option value="${esc(e.entry_id)}" ${e.entry_id === this._integ.entry ? "selected" : ""}>${esc(e.title)}</option>`).join("")}</select>`;
      default: return "";
    }
  }

  // 🔌 Optionen der Integration – eigene WebSocket-Befehle (nur Admins), klappt auch in der Offline-App
  _canInteg() { const h = this._hass; return typeof h?.callWS === "function" && (!h.user || !!h.user.is_admin); }
  async _integLoad(entryId) {
    const hass = this._hass;
    this._integErr = false;
    try {
      const res = await hass.callWS({ type: "airfryer_control/optionen", ...(entryId ? { entry_id: entryId } : {}) });
      this._integ = { entry: res.entry, entries: res.entries || [], data: res.data || {}, notify: res.notify || null };
    } catch (err) {
      if (err?.code === "unauthorized") this._integDenied = true; else this._integErr = true; // kein Admin → Gruppe einfach weg
    }
    if (this._page === "settings") this._render();
  }
  async _integSave(patch) {
    if (!this._integ) return false;
    try {
      const res = await this._hass.callWS({ type: "airfryer_control/optionen_speichern", entry_id: this._integ.entry, daten: patch });
      this._integ.data = res?.data || { ...this._integ.data, ...patch };
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
        lsSet("tip", null); lsSet("news", null); // „news“ = alter Merker vom früheren Beta-Kasten, wird nur aufgeräumt
        const s = el.querySelector("small"); if (s) s.textContent = "✅ " + t("Wird wieder gezeigt", "Will show again");
      }
    }));
    scope.querySelectorAll("[data-tgl]").forEach((el) => el.addEventListener("click", async () => {
      const k = el.dataset.tgl, on = el.getAttribute("aria-pressed") !== "true";
      if (k === "nshake" || k === "nforgot") { el.setAttribute("aria-pressed", String(on)); return; } // 📲 wird mit „Speichern“ zusammen mit den Handys gespeichert
      if (k === "sidebar" || k === "smasc") { // 🔌 gilt für alle → Integration speichern
        el.disabled = true; el.setAttribute("aria-pressed", String(on));
        const ok = await this._integSave(k === "sidebar" ? { sidebar: on } : { maskottchen: on });
        el.disabled = false;
        if (!ok) el.setAttribute("aria-pressed", String(!on));
        const msg = this.shadowRoot.querySelector("[data-iomsg]");
        if (msg) msg.textContent = ok ? "✅ " + t("Gespeichert! Die Integration lädt kurz neu.", "Saved! The integration reloads briefly.") : "😕 " + t("Speichern ging nicht. Bitte nochmal versuchen.", "Saving failed. Please try again.");
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
    // 📲 Handys für die Fertig-Meldung speichern (gilt für alle)
    scope.querySelector("[data-nsave]")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget, msg = this.shadowRoot.querySelector("[data-iomsg]");
      const svcs = [...this.shadowRoot.querySelectorAll("[data-nsvc]")].filter((x) => x.checked).map((x) => x.dataset.nsvc).slice(0, 10);
      const shake = this.shadowRoot.querySelector('[data-tgl="nshake"]')?.getAttribute("aria-pressed") === "true";
      const forgot = this.shadowRoot.querySelector('[data-tgl="nforgot"]')?.getAttribute("aria-pressed") !== "false";
      btn.disabled = true;
      const ok = await this._integSave({ melden_an: svcs, melden_schuetteln: shake, melden_vergessen: forgot });
      btn.disabled = false;
      if (msg) msg.textContent = ok ? "✅ " + (svcs.length ? t("Gespeichert! Ab jetzt meldet sich die Fritteuse auf dem Handy.", "Saved! From now on the air fryer messages your phone.") : t("Gespeichert – Handy-Meldung ist aus.", "Saved – phone message is off.")) : "😕 " + t("Speichern ging nicht. Bitte nochmal versuchen.", "Saving failed. Please try again.");
    });
    // ⏰ Start vergessen: Knopf antippen = sofort speichern (gilt für alle)
    scope.querySelectorAll("[data-ioval]").forEach((el) => el.addEventListener("click", async () => {
      const k = el.dataset.ioval, val = Number(el.dataset.val), msg = this.shadowRoot.querySelector("[data-iomsg]");
      const btns = [...scope.querySelectorAll(`[data-ioval="${k}"]`)];
      btns.forEach((b) => { b.disabled = true; b.classList.toggle("on", b === el); b.setAttribute("aria-pressed", String(b === el)); });
      const ok = await this._integSave({ [k]: val });
      btns.forEach((b) => { b.disabled = false; });
      if (msg) msg.textContent = ok ? "✅ " + t("Gespeichert! Die Integration lädt kurz neu.", "Saved! The integration reloads briefly.") : "😕 " + t("Speichern ging nicht. Bitte nochmal versuchen.", "Saving failed. Please try again.");
    }));
    scope.querySelector("[data-iosave]")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget, msg = this.shadowRoot.querySelector("[data-iomsg]");
      const n = Math.round(Number(this.shadowRoot.querySelector('[data-io="intervall"]').value) / 10) * 10;
      btn.disabled = true;
      const ok = await this._integSave({ intervall: Math.min(600, Math.max(30, Number.isFinite(n) ? n : 60)) });
      btn.disabled = false;
      if (msg) msg.textContent = ok ? "✅ " + t("Gespeichert! Die Integration lädt kurz neu.", "Saved! The integration reloads briefly.") : "😕 " + t("Speichern ging nicht. Bitte nochmal versuchen.", "Saving failed. Please try again.");
    });
  }

  // Die andere Zone (ohne Grandzone), für „Match“ und „Sync“
  // 🔒 Grandzone ODER Zone 1/2 – nie beides: Ist Zone 1 oder 2 „an“, ist die Grandzone gesperrt, und andersherum.
  // Für Doofe: Die Grandzone ist die ganze Schublade ohne Trennwand. Liegt in Zone 1 schon was, passt da keine Grandzone rein.
  // Eine Zone, die selbst gerade an ist, wird nie gesperrt (sonst käme man nicht mehr an „Abbrechen“/„Beenden“).
  _lockedBy(z, zones) {
    const hass = this._hass, on = (x) => ZONE_ON.includes(hass.states[x.state]?.state);
    if (on(z)) return [];
    const grand = /grandzone$/.test(z.key);
    return zones.filter((x) => x.key !== z.key && /grandzone$/.test(x.key) !== grand && on(x));
  }
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
      ${this._favHtml(z, opts)}
      ${this._inhaltHtml(z)}
      ${opts.length ? `<div class="ac-flab"><span>${t("Programm", "Program")}</span>${this._info(modeKey, tr(hass, "Programm", "Program"))}</div>${this._hint(modeKey, t("Tippe ein Programm an. Temperatur und Zeit springen dann auf den Vorschlag der Fritteuse für dieses Programm.", "Tap a program. Temperature and time then jump to the fryer's suggestion for that program."))}<div class="ac-modes">${modes}</div>` : ""}
      ${this._shakeHtml(z)}
      ${step("temp", tr(hass, "Temperatur", "Temperature"), temp, "°C", tHelp)}
      ${step("time", tr(hass, "Garzeit", "Cooking time"), time, "Min", mHelp)}
      ${this._planHtml(z)}
      ${this._syncHtml(z, zones)}
      ${other ? `<div class="ac-withinfo"><button class="ac-match" data-match="${esc(z.key)}" ${RUNNING.includes(hass.states[other.state]?.state) ? "disabled" : ""}>📋 ${t(`Einstellungen auf ${other.name} übernehmen`, `Copy settings to ${other.name}`)}</button>${this._info(copyKey, tr(hass, "Einstellungen übernehmen", "Copy settings"))}</div>${this._hint(copyKey, t(`Kopiert Programm, Temperatur und Zeit nur in die Felder von ${other.name}. An die Fritteuse geht dabei noch nichts.`, `Copies program, temperature and time into the fields of ${other.name} only. Nothing is sent to the fryer yet.`))}` : ""}
      ${this._syncSendHtml(z, zones)}
      <div class="ac-withinfo"><button class="ac-big" data-go="${esc(z.key)}" style="--b:${b.color}" ${z.sw ? "" : "disabled"}>${esc(b.text)}</button>${this._info(goKey, b.text)}</div>
      ${this._hint(goKey, t("Senden bereitet die Fritteuse nur vor – gestartet wird immer am Gerät. Abbrechen nimmt ein vorbereitetes Programm wieder weg, Beenden stoppt das Garen.", "Send only prepares the fryer – you always start it on the device. Cancel removes a prepared program, Stop ends cooking."))}
      <button class="ac-close" data-close>${esc(tr(hass, "Zuklappen", "Close"))}</button>
    </div>`;
  }

  // ⭐ Lieblinge + 🕘 zuletzt gesendet (liegen in Home Assistant, für alle Geräte gleich)
  _progs(z) { const a = this._hass.states[z.progs]?.attributes || {}; return { favs: Array.isArray(a.lieblinge) ? a.lieblinge : [], recent: Array.isArray(a.zuletzt) ? a.zuletzt : [] }; }
  // ⭐ Formular für neuen / geänderten Liebling (wie bei der Einkaufsliste: alles an einem Ort)
  _favFormHtml(z, opts) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e)), f = this._favForm, d = f.draft;
    const progs = (opts.length ? opts : [d.programm]).map((o) => `<option value="${esc(o)}" ${o === d.programm ? "selected" : ""}>${esc(modeText(hass, o))}</option>`).join("");
    const row = (label, html) => `<label class="ac-frow"><span>${label}</span>${html}</label>`;
    return `<div class="ac-favbox">
      <div class="ac-favtitle">${f.idx == null ? `＋ ${t("Neuer Liebling", "New favourite")}` : `✏️ ${t("Liebling bearbeiten", "Edit favourite")}`}</div>
      ${row(t("Name", "Name"), `<input class="ac-num" data-favf="name" maxlength="40" value="${esc(d.name)}" placeholder="${t("z. B. Pommes", "e.g. Fries")}" enterkeyhint="done">`)}
      ${row(t("Programm", "Program"), `<select class="ac-num" data-favf="programm">${progs}</select>`)}
      ${row(t("Temperatur (°C)", "Temperature (°C)"), `<input class="ac-num" data-favf="temperatur" type="number" inputmode="numeric" min="35" max="240" step="5" value="${esc(d.temperatur)}">`)}
      ${row(t("Zeit (Min)", "Time (min)"), `<input class="ac-num" data-favf="minuten" type="number" inputmode="numeric" min="1" max="600" step="1" value="${esc(d.minuten)}">`)}
      ${row(t("↕️ Schütteln", "↕️ Shake"), `<button type="button" class="ac-ftgl ${d.schuetteln ? "on" : ""}" data-favf="schuetteln" aria-pressed="${d.schuetteln}">${d.schuetteln ? t("an", "on") : t("aus (z. B. Kuchen)", "off (e.g. cake)")}</button>`)}
      <div class="ac-favbtns">${f.idx != null ? `<button type="button" class="del" data-favdel>🗑️ ${t("Löschen", "Delete")}</button>` : ""}<span></span><button type="button" data-favcancel>${t("Abbrechen", "Cancel")}</button><button type="button" class="pri" data-favsave>💾 ${t("Speichern", "Save")}</button></div>
    </div>`;
  }
  _favHtml(z, opts) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    if (!z.progs || !hass.entities?.[z.state]?.device_id) return "";
    const fits = (p) => !opts.length || opts.includes(p.programm); // nur Programme, die diese Zone kann
    const { favs, recent } = this._progs(z);
    const busy = RUNNING.includes(hass.states[z.state]?.state) ? "disabled" : "";
    const edit = this._favEdit === z.key, favKey = `${z.key}:fav`, recKey = `${z.key}:recent`;
    const noShake = (p) => p.schuetteln === false; // ↕️ bei diesem Liebling nicht ans Schütteln erinnern
    const favChips = favs.map((p, i) => [p, i]).filter(([p]) => fits(p)).map(([p, i]) => edit
      ? `<button type="button" class="ac-chip ed ${this._favForm?.idx === i ? "sel" : ""}" data-favpick="${i}" aria-label="${t(`${p.name} bearbeiten`, `Edit ${p.name}`)}"><b>✏️ ${esc(p.name)}</b><small>${esc(progLine(hass, p))}${noShake(p) ? " · ↕️✕" : ""}</small></button>`
      : `<button type="button" class="ac-chip" data-fav="${i}" ${busy}><b>⭐ ${esc(p.name)}</b><small>${esc(progLine(hass, p))}${noShake(p) ? " · ↕️✕" : ""}</small></button>`).join("");
    const form = this._favForm?.key === z.key ? this._favFormHtml(z, opts) : "";
    const recChips = recent.filter(fits).slice(0, 5).map((p) => `<button type="button" class="ac-chip" data-recent="${esc(JSON.stringify([p.programm, p.temperatur, p.minuten]))}" ${busy}><b>🕘 ${esc(modeText(hass, p.programm))}</b><small>${esc(`${p.temperatur} °C · ${p.minuten} ${tr(hass, "Min", "min")}`)}</small></button>`).join("");
    return `<div class="ac-flab"><span>⭐ ${t("Lieblinge", "Favourites")}</span>${this._info(favKey, tr(hass, "Lieblinge", "Favourites"))}${favChips || edit ? `<button type="button" class="ac-edbtn" data-favedit>${edit ? t("✓ Fertig", "✓ Done") : t("✏️ Bearbeiten", "✏️ Edit")}</button>` : ""}</div>
      ${this._hint(favKey, t("Antippen = sofort an diese Zone senden (nur bereitstellen, Start am Gerät). ＋ Neu öffnet ein Formular: Name, Programm, Temperatur, Zeit und ↕️ Schütteln (vorbelegt mit der Einstellung unten). ✏️ Bearbeiten: Liebling antippen = alles ändern, auch den Namen, 🗑️ = löschen. Lieblinge gelten auf allen Geräten.", "Tap = send to this zone right away (prepare only, start on the device). ＋ New opens a form: name, program, temperature, time and ↕️ shaking (prefilled with the setting below). ✏️ Edit: tap a favourite = change everything, the name too, 🗑️ = delete. Favourites apply on all devices."))}
      <div class="ac-chips">${favChips}<button type="button" class="ac-chip add ${this._favForm?.key === z.key && this._favForm.idx == null ? "sel" : ""}" data-favadd title="${t("Neuen Liebling anlegen", "Create a new favourite")}">＋ ${t("Neu", "New")}</button></div>${form}
      ${recChips ? `<div class="ac-flab"><span>🕘 ${t("Zuletzt gesendet", "Recently sent")}</span>${this._info(recKey, tr(hass, "Zuletzt gesendet", "Recently sent"))}</div>${this._hint(recKey, t("Die letzten 5 Programme, die an die Fritteuse gingen. Antippen = nochmal an diese Zone senden.", "The last 5 programs sent to the fryer. Tap = send to this zone again."))}<div class="ac-chips">${recChips}</div>` : ""}`;
  }
  // 🕒 „Fertig um …“ – Uhrzeit eintippen, die Integration rechnet die Startzeit aus. Gestartet wird NIE von allein.
  _planHtml(z) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    if (!hass.entities?.[z.state]?.device_id) return "";
    const s = hass.states[z.state]?.state;
    if (["gart", "vorheizen", "pausiert", "warmhalten"].includes(s)) return ""; // gart schon → „fertig um“ zeigt die Fritteuse selbst
    const x = zoneExtra(hass, z), key = `${z.key}:plan`;
    const val = x.goal ? new Date(x.goal).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }) : "";
    const mins = Math.max(1, Math.round(Number(hass.states[z.time]?.state) || 0));
    let line = "";
    if (x.goal && x.start) {
      const left = Math.round((Date.parse(x.start) - Date.now()) / 60000);
      const inTxt = left >= 60 ? tr(hass, `in ${Math.floor(left / 60)} Std ${left % 60} Min`, `in ${Math.floor(left / 60)} h ${left % 60} min`) : tr(hass, `in ${left} Min`, `in ${left} min`);
      line = left > 0
        ? `<div class="ac-planline">▶️ ${t(`Um ${clock(x.start, hass)} Uhr am Gerät starten (${inTxt}) · Garzeit ${mins} Min`, `Start on the device at ${clock(x.start, hass)} (${inTxt}) · cooking time ${mins} min`)}</div>`
        : `<div class="ac-planline late">⏰ ${t(`Jetzt starten! Dann ist es um ${clock(x.goal, hass)} Uhr fertig`, `Start now! Then it is done at ${clock(x.goal, hass)}`)}${left < -1 ? t(` (eigentlich schon seit ${-left} Min – jetzt gestartet = fertig um ${clock(new Date(Date.now() + mins * 60000).toISOString(), hass)} Uhr)`, ` (actually ${-left} min ago – started now = done at ${clock(new Date(Date.now() + mins * 60000).toISOString(), hass)})`) : ""}</div>`;
    }
    return `<div class="ac-planbox"><div class="ac-flab"><span>🕒 ${t("Fertig um", "Done at")}</span>${this._info(key, tr(hass, "Fertig um", "Done at"))}</div>
      ${this._hint(key, t("Uhrzeit eintippen, wann das Essen fertig sein soll, z. B. 18:30. Die Karte rechnet: Uhrzeit minus Garzeit = Startzeit, und zeigt sie in der Zeile und im Laufband. Zur Startzeit blinkt „⏰ Jetzt starten!“ (mit Handys unter ⚙️ › Fertig melden an kommt auch eine Nachricht). Gestartet wird NIE von allein – Senden und Start drückst du selbst. Tipp: Erst zur Startzeit senden – die Fritteuse wirft ein gesendetes Programm nach ca. 5 Minuten ohne Start wieder weg. Heizt dein Programm vor, rechne ein paar Minuten dazu. Ist die Uhrzeit heute schon vorbei, gilt morgen.", "Type the time the food should be done, e.g. 18:30. The card works out: time minus cooking time = start time, and shows it in the row and the ticker. At start time “⏰ Start now!” blinks (with phones under ⚙️ › Report done to you also get a message). It NEVER starts by itself – you press Send and Start. Tip: only send at start time – the fryer throws away a sent program after about 5 minutes without Start. If your program preheats, add a few minutes. If the time has already passed today, tomorrow counts."))}
      <div class="ac-favform"><input class="ac-num" type="time" data-plan="${esc(z.key)}" value="${esc(val)}" aria-label="${t("Fertig um", "Done at")}" enterkeyhint="done">${x.goal ? `<button type="button" data-plandel="${esc(z.key)}" aria-label="${t("Uhrzeit löschen", "Delete time")}">✕</button>` : ""}</div>${line}</div>`;
  }
  async _setPlan(z, value) {
    const hass = this._hass, dev = hass.entities?.[z.state]?.device_id;
    if (!dev) return;
    const v = String(value || "").trim().slice(0, 5);
    try { await this._svc("fertig_um_setzen", { geraet: dev, zone: zoneNum(z), uhrzeit: v }); }
    catch (e) { this._flash(z, tr(hass, `😕 Ging nicht: ${e?.message || e}`, `😕 Did not work: ${e?.message || e}`)); }
  }
  // 🏷️ „Was ist drin?“ – steht im Laufband und in der Fertig-Meldung, wird nach dem Garen von selbst vergessen
  _inhaltHtml(z) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    if (!hass.entities?.[z.state]?.device_id) return "";
    const x = zoneExtra(hass, z), key = `${z.key}:inhalt`;
    return `<div class="ac-flab"><span>🏷️ ${t("Was ist drin?", "What's inside?")}</span>${this._info(key, tr(hass, "Was ist drin?", "What's inside?"))}</div>
      ${this._hint(key, t("Z. B. „Pommes“. Steht dann im Laufband („Zone 1 (Pommes)“) und in der Fertig-Meldung aufs Handy. Tippst du einen ⭐ Liebling an, steht sein Name von selbst hier. Nach dem Garen wird es wieder vergessen.", "E.g. “Fries”. Then it shows in the ticker (“Zone 1 (Fries)”) and in the done message on your phone. Tap a ⭐ favourite and its name lands here by itself. After cooking it is forgotten again."))}
      <div class="ac-favform"><input class="ac-num" data-inhalt="${esc(z.key)}" maxlength="40" value="${esc(x.inhalt)}" placeholder="${t("z. B. Pommes", "e.g. Fries")}" aria-label="${t("Was ist drin?", "What's inside?")}" enterkeyhint="done">${x.inhalt ? `<button type="button" data-inhaltdel="${esc(z.key)}" aria-label="${t("Inhalt löschen", "Delete contents")}">✕</button>` : ""}</div>`;
  }
  // ↕️ Schütteln pro Schublade: nur EIN Knopf mit der aktuellen Wahl – erst beim Antippen klappen die Zeiten auf
  _shakeHtml(z) {
    const hass = this._hass, t = (d, e) => esc(tr(hass, d, e));
    if (!hass.entities?.[z.state]?.device_id) return "";
    const every = zoneExtra(hass, z).every, key = `${z.key}:shake`, open = this._shkOpen === z.key;
    const label = (v) => v == null ? tr(hass, "Aus", "Off") : v === 0 ? tr(hass, "Halbzeit", "Half time") : tr(hass, `alle ${v} Min`, `every ${v} min`);
    const short = (v) => v == null || v === 0 ? label(v) : tr(hass, `alle ${v}`, `every ${v}`); // aufgeklappt kurz: „alle 3“
    const opts = [null, 0, 3, 5, 8];
    if (every != null && !opts.includes(every)) opts.push(every); // z. B. per Dienst „alle 4 Min“ gesetzt → trotzdem zeigen
    const val = (v) => v == null ? "aus" : v === 0 ? "halbzeit" : String(v);
    return `<div class="ac-withinfo"><button type="button" class="ac-shk ${every == null ? "" : "on"}" data-shk="${esc(z.key)}" aria-expanded="${open}">↕️ ${t("Schütteln", "Shake")}: <b>${esc(label(every))}</b> <span class="ac-shkarr">${open ? "▴" : "▾"}</span></button>${this._info(key, tr(hass, "Schütteln", "Shake"))}</div>
      ${this._hint(key, t("Erinnert ans Schütteln: zur Halbzeit oder alle 3, 5 oder 8 Minuten blinkt in Karte und Laufband „↕️ Jetzt schütteln!“ (3 Minuten, Schublade auf = weg). Gilt nur für diese Schublade und bleibt gemerkt. Ein ⭐ Liebling mit ↕️ aus (z. B. Kuchen) stellt hier auf Aus.", "Reminds you to shake: at half time or every 3, 5 or 8 minutes “↕️ Shake now!” blinks in the card and the ticker (3 minutes, drawer open = gone). Only for this drawer and it is remembered. A ⭐ favourite with ↕️ off (e.g. cake) switches it off here."))}
      ${open ? `<div class="ac-seg ac-shkseg" role="group" style="grid-template-columns:repeat(${opts.length}, 1fr)">${opts.map((v) => `<button type="button" data-shkval="${val(v)}" data-zk="${esc(z.key)}" class="${v === every ? "on" : ""}" aria-pressed="${v === every}" aria-label="${esc(label(v))}">${esc(short(v))}</button>`).join("")}</div>` : ""}`;
  }
  async _setShake(z, howOften) {
    const hass = this._hass, dev = hass.entities?.[z.state]?.device_id;
    if (!dev) return;
    try { await this._svc("schuetteln_setzen", { geraet: dev, zone: zoneNum(z), wie_oft: /^\d+$/.test(howOften) ? Number(howOften) : howOften }); }
    catch (e) { this._flash(z, tr(hass, `😕 Ging nicht: ${e?.message || e}`, `😕 Did not work: ${e?.message || e}`)); }
  }
  async _setInhalt(z, text) {
    const hass = this._hass, dev = hass.entities?.[z.state]?.device_id;
    if (!dev) return;
    const val = String(text || "").trim().slice(0, 40);
    if (val === zoneExtra(hass, z).inhalt) return;
    try { await this._svc("inhalt_setzen", { geraet: dev, zone: zoneNum(z), inhalt: val }); }
    catch (e) { this._flash(z, tr(hass, `😕 Ging nicht: ${e?.message || e}`, `😕 Did not work: ${e?.message || e}`)); }
  }
  _flash(z, text) { // kurze Meldung unter der Zeile (verschwindet nach 6 s)
    this._msg = { key: z.key, text }; this._sig = ""; this.hass = this._hass;
    clearTimeout(this._msgT);
    this._msgT = setTimeout(() => { if (this._msg?.key === z.key) { this._msg = null; this._sig = ""; this.hass = this._hass; } }, 6000);
  }
  async _svc(service, data, withAnswer = false) { // Dienst der Integration (mit Antwort, wenn gewünscht)
    const hass = this._hass;
    if (withAnswer && typeof hass.callWS === "function") {
      const r = await hass.callWS({ type: "call_service", domain: AC, service, service_data: data, return_response: true });
      return r?.response;
    }
    await hass.callService(AC, service, data);
    return null;
  }
  async _sendProg(z, p, fav = false) { // ⭐/🕘 an die Zone schicken – nur bereitstellen, nie starten
    const hass = this._hass, dev = hass.entities?.[z.state]?.device_id;
    if (!dev || this._busySend) return;
    this._busySend = true;
    try {
      const data = { geraet: dev, zone: zoneNum(z), programm: p.programm, temperatur: p.temperatur, minuten: p.minuten };
      if (fav) { // ⭐ Liebling: ↕️ ja/nein mitschicken – und sein Name wird zum Inhalt, wenn noch nichts eingetippt ist
        data.schuetteln = p.schuetteln !== false;
        if (!zoneExtra(hass, z).inhalt && p.name) data.inhalt = String(p.name).slice(0, 40);
      }
      const r = await this._svc("programm_senden", data, true);
      this._flash(z, r && r.ok === false
        ? tr(hass, `😕 Hat nicht geklappt (${r.fehler || r.ergebnis}). Ist die Fritteuse an?`, `😕 Did not work (${r.fehler || r.ergebnis}). Is the fryer on?`)
        : tr(hass, `✅ ${progLine(hass, p)} ist bereit – jetzt am Gerät auf Start drücken.`, `✅ ${progLine(hass, p)} is ready – now press Start on the device.`));
    } catch (e) {
      this._flash(z, tr(hass, `😕 Senden ging nicht: ${e?.message || e}`, `😕 Sending failed: ${e?.message || e}`));
    } finally { this._busySend = false; }
  }
  _wire() {
    const root = this.shadowRoot;
    // 🔄 Neu laden: nur die eigenen Zwischenspeicher der App leeren, den Offline-Helfer aktualisieren – wie bei der Einkaufsliste
    root.querySelector("[data-reload]")?.addEventListener("click", () => {
      try { caches?.keys?.().then((ks) => ks.filter((k) => k.startsWith("airfryer-control-app-")).forEach((k) => caches.delete(k))); } catch (_) { /* egal */ }
      try { navigator.serviceWorker?.getRegistrations?.().then((rs) => rs.forEach((r) => { if (/\/airfryer_control\/app\//.test(r.scope)) r.update().catch(() => {}); })); } catch (_) { /* egal */ }
      setTimeout(() => location.reload(), 300);
    });
    const zoneOf = (k) => (this._zones || []).find((x) => x.key === k);
    // ↕️ Schütteln: Knopf klappt die Zeiten auf/zu, Zeit antippen = speichern und wieder zu
    root.querySelectorAll("[data-shk]").forEach((el) => el.addEventListener("click", () => {
      this._shkOpen = this._shkOpen === el.dataset.shk ? null : el.dataset.shk; this._sig = ""; this.hass = this._hass;
    }));
    root.querySelectorAll("[data-shkval]").forEach((el) => el.addEventListener("click", async () => {
      const z = zoneOf(el.dataset.zk);
      el.parentElement.querySelectorAll("button").forEach((b) => { b.disabled = true; b.classList.toggle("on", b === el); });
      if (z) await this._setShake(z, el.dataset.shkval);
      this._shkOpen = null; this._sig = ""; this.hass = this._hass;
    }));
    // ⭐ Lieblinge: senden, speichern, löschen
    const openZ = () => zoneOf(this._open);
    root.querySelectorAll("[data-fav]").forEach((el) => el.addEventListener("click", () => {
      const z = openZ(), p = z && this._progs(z).favs[Number(el.dataset.fav)];
      if (p) this._sendProg(z, p, true);
    }));
    root.querySelectorAll("[data-recent]").forEach((el) => el.addEventListener("click", () => {
      const z = openZ();
      try { const [programm, temperatur, minuten] = JSON.parse(el.dataset.recent); if (z) this._sendProg(z, { programm, temperatur, minuten }); } catch (_) { /* egal */ }
    }));
    // ⭐ Lieblinge: ✏️-Modus, ＋ Neu, antippen = bearbeiten, 💾 speichern, 🗑️ löschen
    const redraw = () => { this._sig = ""; this.hass = this._hass; };
    root.querySelector("[data-favedit]")?.addEventListener("click", () => { this._favEdit = this._favEdit === this._open ? null : this._open; this._favForm = null; redraw(); });
    const openForm = (idx) => {
      const z = openZ(), hass = this._hass;
      if (!z) return;
      const p = idx == null ? null : this._progs(z).favs[idx];
      const mode = hass.states[z.mode]?.state, temp = Number(hass.states[z.temp]?.state), min = Number(hass.states[z.time]?.state);
      const draft = p ? { name: p.name, programm: p.programm, temperatur: p.temperatur, minuten: p.minuten, schuetteln: p.schuetteln !== false }
        : { name: "", programm: mode, temperatur: Number.isFinite(temp) ? temp : 180, minuten: Number.isFinite(min) ? min : 15, schuetteln: true }; // vorbelegt mit der Einstellung unten
      const same = this._favForm?.key === z.key && this._favForm.idx === (p ? idx : null);
      this._favForm = same ? null : { key: z.key, idx: p ? idx : null, old: p?.name || null, draft };
      redraw();
      root.querySelector('[data-favf="name"]')?.focus();
    };
    root.querySelector("[data-favadd]")?.addEventListener("click", () => openForm(null));
    root.querySelectorAll("[data-favpick]").forEach((el) => el.addEventListener("click", () => openForm(Number(el.dataset.favpick))));
    root.querySelector("[data-favcancel]")?.addEventListener("click", () => { this._favForm = null; redraw(); });
    root.querySelectorAll("[data-favf]").forEach((el) => {
      const k = el.dataset.favf, d = this._favForm?.draft;
      if (!d) return;
      if (k === "schuetteln") {
        el.addEventListener("click", () => { // ↕️ umschalten ohne neu zu zeichnen
          d.schuetteln = !d.schuetteln;
          el.classList.toggle("on", d.schuetteln); el.setAttribute("aria-pressed", String(d.schuetteln));
          el.textContent = d.schuetteln ? tr(this._hass, "an", "on") : tr(this._hass, "aus (z. B. Kuchen)", "off (e.g. cake)");
        });
        return;
      }
      el.addEventListener(el.tagName === "SELECT" ? "change" : "input", () => { d[k] = k === "name" || k === "programm" ? el.value : Number(el.value); });
      if (k === "name") el.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); saveFav(); } });
    });
    // 🏷️ Was ist drin? – speichern beim Verlassen des Feldes oder mit Enter
    root.querySelectorAll("[data-inhalt]").forEach((el) => {
      const z = zoneOf(el.dataset.inhalt);
      el.addEventListener("change", () => { if (z) this._setInhalt(z, el.value); });
      el.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); el.blur(); } });
    });
    // 🕒 Fertig um – speichern beim Verlassen des Feldes / Enter, ✕ = löschen
    root.querySelectorAll("[data-plan]").forEach((el) => {
      const z = zoneOf(el.dataset.plan);
      el.addEventListener("change", () => { if (z && /^\d{1,2}:\d{2}/.test(el.value)) this._setPlan(z, el.value); });
      el.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); el.blur(); } });
    });
    root.querySelectorAll("[data-plandel]").forEach((el) => el.addEventListener("click", () => { const z = zoneOf(el.dataset.plandel); if (z) this._setPlan(z, ""); }));
    root.querySelectorAll("[data-inhaltdel]").forEach((el) => el.addEventListener("click", () => { const z = zoneOf(el.dataset.inhaltdel); if (z) this._setInhalt(z, ""); }));
    const saveFav = async () => {
      const z = openZ(), hass = this._hass, f = this._favForm;
      if (!z || !f) return;
      const d = f.draft, name = String(d.name || "").trim();
      if (!name) { root.querySelector('[data-favf="name"]')?.focus(); return; }
      if (!d.programm || !Number.isFinite(d.temperatur) || !Number.isFinite(d.minuten) || d.minuten < 1) return;
      const data = { geraet: hass.entities?.[z.state]?.device_id, name, programm: d.programm, temperatur: d.temperatur, minuten: d.minuten, schuetteln: d.schuetteln !== false };
      if (f.old) data.alter_name = f.old; // ✏️ umbenennen: bleibt an seinem Platz
      this._favForm = null;
      try {
        await this._svc("liebling_speichern", data);
        this._flash(z, tr(hass, `⭐ „${name}“ gespeichert.`, `⭐ “${name}” saved.`));
      } catch (e) { this._flash(z, tr(hass, `😕 Speichern ging nicht: ${e?.message || e}`, `😕 Saving failed: ${e?.message || e}`)); }
    };
    root.querySelector("[data-favsave]")?.addEventListener("click", saveFav);
    root.querySelector("[data-favdel]")?.addEventListener("click", async () => {
      const z = openZ(), f = this._favForm;
      if (!z || !f?.old) return;
      const left = this._progs(z).favs.filter((p) => p.name !== f.old).length;
      this._favForm = null;
      if (!left) this._favEdit = null; // 🧹 letzter Liebling weg → ✏️-Modus endet von selbst (sonst steckt man fest)
      try { await this._svc("liebling_loeschen", { geraet: this._hass.entities?.[z.state]?.device_id, name: f.old }); } catch (_) { /* Fehler zeigt Home Assistant selbst */ }
      redraw();
    });
    root.querySelectorAll("[data-help]").forEach((el) => el.addEventListener("click", (e) => {
      e.stopPropagation(); // ⓘ: nur die Hilfe auf-/zuklappen, ohne neu zu zeichnen
      const k = el.dataset.help;
      const open = !this._helpOpen.has(k);
      if (open) this._helpOpen.add(k); else this._helpOpen.delete(k);
      el.setAttribute("aria-expanded", String(open));
      root.querySelectorAll("[data-hint]").forEach((h) => { if (h.dataset.hint === k) h.hidden = !open; });
    }));
    root.querySelectorAll(".ac-row").forEach((el) => el.addEventListener("click", (e) => {
      if (e.target.closest("[data-go]") || el.dataset.locked) return; // 🔒 gesperrte Zone klappt nicht auf
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
    // 💡 Tipp wegklicken
    root.querySelectorAll("[data-tip]").forEach((el) => el.addEventListener("click", () => {
      lsSet("tip", true);
      if (el.dataset.tip === "guide") this._go("guide"); else { this._sig = ""; this._render(); }
    }));
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
    this._update();
  }
  // 🔁 Für Doofe: Neu gebaut wird nur, wenn sich wirklich etwas ändert (andere Zone, anderer Zustand,
  // andere Farbe). Zählt nur „wartet seit 12 Min“ weiter, wird bloß die Zahl im Text getauscht –
  // das Laufband läuft dabei einfach weiter und springt nicht an den Anfang.
  _update() {
    const parts = this._parts();
    const sig = parts.items.map((i) => i.replace(/\d+/g, "#")).join("|") + parts.done + parts.shake + (this._config?.language || "") + (this._config?.speed || "");
    if (sig !== this._sig) { this._sig = sig; this._render(parts); return; }
    const txt = parts.items.join("|");
    if (txt !== this._txt) { this._txt = txt; this._fill(parts); }
    this._measure();
  }
  connectedCallback() {
    // „wartet seit X Min“ still weiterzählen (alle 30 s nachsehen, neu gebaut wird dabei nichts)
    this._timer = setInterval(() => { if (this._hass) this._update(); }, 30000);
  }
  disconnectedCallback() { clearInterval(this._timer); }

  _lh() { const l = this._config?.language; return l && l !== "auto" ? { ...this._hass, language: l } : this._hass; }

  // 📺 Texte 1:1 wie der Küchen-Ticker im Dashboard – nur Kochtimer hinten und „wartet auf Sync-Start“ dazu
  _parts() {
    const hass = this._lh();
    const items = [];
    let done = false, shake = false;
    const fr = tr(hass, "Fritteuse", "Air fryer");
    for (const z of findZones(hass)) {
      const s = hass.states[z.state]?.state;
      const fin = hass.states[z.finish];
      const x = zoneExtra(hass, z);
      const name = x.inhalt ? `${z.name} (${x.inhalt})` : z.name; // 🏷️ „Grandzone (Frikadellen)“
      if (x.shake && (s === "gart" || s === "pausiert")) { // ↕️ Schüttel-Zeit: Rahmen blinkt orange
        shake = true;
        items.push(`${SPN} ${fr} ${name}: ${tr(hass, "JETZT SCHÜTTELN!", "SHAKE NOW!")}`);
      } else if (s === "wartet_auf_start" && x.forgot) { // ⏰ Start am Gerät vergessen?
        shake = true;
        items.push(`⏰ ${fr} ${name}: ${x.waitMin != null
          ? tr(hass, `wartet seit ${x.waitMin} Min – Start am Gerät vergessen?`, `waiting ${x.waitMin} min – forgot to press Start?`)
          : tr(hass, "Start am Gerät vergessen?", "forgot to press Start?")}`);
      } else if (x.goal && x.startNow && s !== "gart" && s !== "vorheizen" && s !== "pausiert") { // 🕒 Startzeit ist da
        shake = true;
        items.push(`⏰ ${fr} ${name}: ${tr(hass, `JETZT STARTEN – fertig um ${clock(x.goal, hass)} Uhr`, `START NOW – done at ${clock(x.goal, hass)}`)}`);
      } else if (x.goal && x.start && s !== "gart" && s !== "vorheizen" && s !== "pausiert") { // 🕒 geplant
        items.push(`${FRY} ${fr} ${name}: ${tr(hass, `Start um ${clock(x.start, hass)} Uhr → fertig um ${clock(x.goal, hass)} Uhr`, `start at ${clock(x.start, hass)} → done at ${clock(x.goal, hass)}`)}`);
      } else if (x.dropped && s === "bereit") { // 😴 Fritteuse hat das Programm weggeworfen
        items.push(`😴 ${fr} ${name}: ${tr(hass, "Programm verworfen – nochmal senden", "program dropped – send again")}`);
      } else if (s === "gart" || s === "vorheizen") {
        const when = s === "vorheizen" ? tr(hass, "heizt vor", "preheating")
          : valid(fin) ? (() => { // ⏱️ Restzeit vorne, Uhrzeit dahinter – jede Minute wird nur die Zahl getauscht
            const left = Math.max(0, Math.ceil((Date.parse(fin.state) - Date.now()) / 60000));
            return Number.isFinite(left) ? tr(hass, `noch ${left} Min · fertig ${clock(fin.state, hass)} Uhr`, `${left} min left · done ${clock(fin.state, hass)}`)
              : tr(hass, `fertig um ${clock(fin.state, hass)} Uhr`, `done at ${clock(fin.state, hass)}`);
          })() : tr(hass, "gart", "cooking");
        items.push(`${FRY} ${fr} ${name}: ${when}`);
      } else if (s === "wartet_auf_sync") {
        items.push(`${FRY} ${fr} ${name}: ${tr(hass, "wartet auf Sync-Start", "waiting for sync start")}`);
      } else if (s === "wartet_auf_start") {
        items.push(`${FRY} ${fr} ${name}: ${tr(hass, "wartet auf Start", "waiting for start")}`);
      } else if (s === "fertig") {
        done = true;
        items.push(`${FRY} ${fr} ${name}: ${tr(hass, "FERTIG!", "DONE!")}`);
      }
    }
    for (const id of this._config?.extra_entities || []) { // ⏲️ Kochtimer (z. B. Einkaufsliste) – hinter der Fritteuse
      const timers = hass.states[id]?.attributes?.timer;
      if (!Array.isArray(timers)) continue;
      timers.filter((x) => x.fertig).forEach((x) => { done = true; items.push(`${TMR}${x.name}: ${tr(hass, "FERTIG!", "DONE!")}`); });
      timers.filter((x) => !x.fertig).sort((a, b) => Date.parse(a.ende) - Date.parse(b.ende))
        .forEach((x) => { const left = Math.max(0, Math.ceil((Date.parse(x.ende) - Date.now()) / 60000)); // ⏱️ Restzeit wie bei der Fritteuse
          items.push(`${TMR}${x.name}: ${Number.isFinite(left) ? tr(hass, `noch ${left} Min · fertig ${clock(x.ende, hass)} Uhr`, `${left} min left · done ${clock(x.ende, hass)}`) : tr(hass, `fertig um ${clock(x.ende, hass)} Uhr`, `done at ${clock(x.ende, hass)}`)}`); });
    }
    return { items, done, shake };
  }

  _html(items) {
    const hass = this._lh();
    const base = items.length ? items.join(" +++ ") : tr(hass, "👨‍🍳 Kein Kochtimer aktiv", "👨‍🍳 No cooking timer active");
    const piece = `+++ ${base} `;
    const text = piece.repeat(Math.max(5, Math.ceil(320 / piece.length)));
    const img = `<img class="fry" src="${AC_BASE}/icon.png?v=${esc(AC_VERSION)}" alt="" width="20" height="20">`;
    const timg = `<img class="fry" src="${AC_BASE}/timer-icon.png?v=${esc(AC_VERSION)}" alt="" width="24" height="24" style="width:24px;height:24px;margin:-4px 6px 0 0">`;
    return esc(text).split(FRY).join(img).split(TMR).join(timg).split(SPN).join('<span class="spoon">↕️</span>');
  }

  // Nur den Text tauschen (gleiche Länge bis auf eine Ziffer) – Laufband läuft weiter
  _fill(parts) {
    const html = this._html(parts.items);
    this.shadowRoot.querySelectorAll(".txt").forEach((el) => { el.innerHTML = html; });
  }

  _render(parts = this._parts()) {
    const hass = this._lh();
    if (!hass || !this._config) return;
    const { items, done, shake } = parts;
    this._txt = items.join("|");
    const hide = this._config.hide_when_idle && !items.length;
    this.hidden = hide;
    this.style.display = hide ? "none" : "";
    this.dispatchEvent(new CustomEvent("card-visibility-changed", { detail: { value: !hide }, bubbles: true, composed: true }));
    const html = this._html(items);
    // 🚦 Rot = fertig, Orange blinkend = ↕️ schütteln / ⏰ Start vergessen, sonst Türkis (wie im Dashboard)
    const warn = !done && shake;
    const color = done ? "#E53935" : shake ? "#FB8C00" : "#26A69A";
    const icon = warn ? "mdi:arrow-up-down-bold" : "mdi:chef-hat";
    const pulse = done ? "ac_pulse 1s ease-in-out infinite" : warn ? "ac_pulse .8s ease-in-out infinite" : "none";
    this.shadowRoot.innerHTML = `<style>
      :host { display:block; }
      .fry { width:20px; height:20px; vertical-align:middle; margin:-3px 4px 0 0; border-radius:4px; }
      .spoon { display:inline-block; animation:ac_blink 1s steps(2, start) infinite; }
      @keyframes ac_blink { to { visibility:hidden; } }
      ha-card { display:block; height:40px; padding:0; background:var(--card-background-color); border-radius:8px; border:none; box-shadow:0 5px 3px rgba(0,0,0,.1); overflow:hidden; }
      .box { display:flex; align-items:center; width:100%; height:100%; border:2px solid ${color}; border-radius:8px; box-sizing:border-box; ${warn ? "animation:ac_rahmen .8s ease-in-out infinite;" : ""} }
      .box ha-icon { flex:none; --mdc-icon-size:22px; margin:0 10px; color:${color}; animation:${pulse}; }
      .box ha-icon + .win + ha-icon { animation-delay:.5s; }
      .win { flex:1; min-width:0; overflow:hidden; display:flex; align-items:center; }
      .wrap { white-space:nowrap; display:flex; animation:ac_tick 60s linear infinite; will-change:transform; }
      .txt { font-family:Roboto,sans-serif; font-size:16px; font-weight:500; line-height:20px; padding-right:20px; color:var(--primary-text-color); }
      @keyframes ac_pulse { 0% { opacity:1 } 50% { opacity:.3 } 100% { opacity:1 } }
      @keyframes ac_rahmen { 0% { border-color:#FB8C00 } 50% { border-color:#FFE0B2 } 100% { border-color:#FB8C00 } }
      @keyframes ac_tick { from { transform:translate3d(0,0,0) } to { transform:translate3d(-50%,0,0) } }
      @media (prefers-reduced-motion: reduce) { .wrap, .box, .box ha-icon, .spoon { animation:none; } }
    </style>
    <ha-card><div class="box"><ha-icon icon="${icon}"></ha-icon><div class="win"><div class="wrap"><span class="txt">${html}</span><span class="txt">${html}</span></div></div><ha-icon icon="${icon}"></ha-icon></div></ha-card>`;
    this._measured = false;
    this._tries = 0;
    this._measure();
  }

  // Dauer aus der echten Textbreite: Breite ÷ Tempo (Pixel pro Sekunde). So läuft jeder Text gleich schnell.
  // ⏱️ Startpunkt aus der Uhrzeit (Date.now): Neu bauen oder Seite neu laden → das Laufband steht da,
  // wo es nach der Uhr gerade sein muss, statt vorne neu anzufangen (wie der Küchen-Ticker).
  _measure() {
    if (this._measured || !this.shadowRoot) return;
    const wrap = this.shadowRoot.querySelector(".wrap");
    const one = wrap?.firstElementChild;
    const w = one ? one.getBoundingClientRect().width : 0;
    if (w > 0) {
      const speed = Math.min(200, Math.max(20, Number(this._config?.speed) || 60));
      const dur = Math.max(8, Math.round(w / speed));
      wrap.style.animationDuration = `${dur}s`;
      wrap.style.animationDelay = `${(-((Date.now() / 1000) % dur)).toFixed(2)}s`;
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
