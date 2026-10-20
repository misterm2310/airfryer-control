<img src="docs/icon.png" width="96" align="right" alt="Icon">

# 🍟 Cosori Bedienung for Home Assistant

🇩🇪 **Deutsch?** → [README auf Deutsch](README.md)

**Your Cosori air fryer on your dashboard.** Time remaining, “done at”, temperature and program – for each zone. Plus an event when the food is ready (“🍟 Fries are done!” on your phone or as an announcement), a stop button and actions for automations.

Built for models the official VeSync integration does **not** know – first of all the **Dual Blaze TwinFry 10 L** (CAF-TF101S / CAF-TF102S).

> 🧪 **Beta!** This integration is new. Cosori does not publish how its air fryers talk. Much of it is derived from the open ioBroker adapter and pyvesync and **has not been checked on every real air fryer yet**. If something looks odd, tell us (see below) and we'll fix it.

---

## ✨ What can it do?

| Feature | How |
|---|---|
| 🔥 **Status** | Off, Ready, Preheating, Cooking, Paused, Drawer open, Done, Keeping warm, Offline. |
| ⏱️ **Time remaining & “done at”** | In minutes and as a time – overall and per zone. |
| 🧩 **Two zones** | On the TwinFry, separate sensors for zone 1 and zone 2. Whole drawer without divider = zone 1. |
| 🌡️ **Temperature & program** | Target temperature, measured temperature (if reported) and program (AirFry, Roast …). |
| 🔔 **“Done” event** | `cosori_bedienung_fertig` – for phone notifications, announcements or pausing the TV. |
| ⏹️ **Stop cooking** | Button for the whole fryer – and a **switch per zone** (“Zone 1 cooking”: turn off = stop that zone). |
| 🎛️ **Change temperature & time** | Number fields per zone. While the zone is cooking, new values go straight to the fryer – like in the app. |
| ▶️ **Start cooking** | Action with zone, temperature, minutes, program (see “Honestly”). |
| 🐢🐇 **Smart polling** | Idle: every 60 seconds (adjustable). Cooking: every 15 seconds. |
| 🛡️ **Privacy** | Your password is not stored, identifiers are redacted everywhere. Details below. |

---

## 📦 Installation

1. Open **HACS** → top right **⋮ → Custom repositories**.
2. Add `https://github.com/misterm2310/cosori-bedienung`, type **Integration**.
3. Search **Cosori Bedienung** → ⋮ → **Redownload** → enable **“Show beta versions”** → pick the newest → **Download**.
4. **Restart Home Assistant.**
5. **Settings → Devices & services → Add integration → Cosori Bedienung.**
6. Sign in with **the same account as in the VeSync app**, choose region **EU** or **US** – done. 🎉

<details><summary>Without HACS (manual)</summary>

Copy `custom_components/cosori_bedienung` to `/config/custom_components/cosori_bedienung` and restart Home Assistant.
</details>

---

## 👀 What you get

One device per air fryer. Entity IDs depend on the name in the app (here “Fritteuse”) and your Home Assistant language:

| Entity | Contents |
|---|---|
| `sensor.fritteuse_status` | Overall status (attribute `rohwert` = what the fryer actually reported) |
| `sensor.fritteuse_time_remaining` | Minutes until done (overall) |
| `sensor.fritteuse_done_at` | Time when everything is done |
| `sensor.fritteuse_zone_1_…` / `zone_2_…` | Status, time remaining, done at, program (only while cooking) |
| `switch.fritteuse_zone_1_cooking` / `zone_2_cooking` | On = zone is cooking. **Turn off = stop the zone.** Turning on is blocked (EU), you get a message. |
| `number.fritteuse_zone_1_set_temperature` / `…_set_cooking_time` | Change temperature (35–240 °C) / minutes while the zone is cooking |
| `binary_sensor.fritteuse_cooking` | On while preheating, cooking or briefly paused |
| `button.fritteuse_stop_cooking` | Stop |
| *Diagnostic:* `binary_sensor.fritteuse_online`, `button.fritteuse_refresh_now`, `sensor.fritteuse_raw_data` | Connection, poll now, last cloud response (without identifiers) |

---

## 🤖 Automations

The event `cosori_bedienung_fertig` carries `geraet` (name), `modell`, `zone` (`1`, `2`, `3` or `alle` = whole fryer), `zustand` and `programm`.

```yaml
alias: Air fryer – food is ready
description: "Sends a phone notification as soon as the Cosori air fryer is completely done."
mode: single
triggers:
  - trigger: event
    event_type: cosori_bedienung_fertig
    event_data:
      zone: alle
conditions:
  # Maintenance switch: if it is on, stay quiet. Don't have one? Delete this condition.
  - condition: state
    entity_id: input_boolean.schalter_wartung
    state: "off"
actions:
  - action: notify.mobile_app_your_phone
    continue_on_error: true
    data:
      title: "🍟 Food is ready!"
      message: "{{ trigger.event.data.geraet }} is done. Enjoy!"
      data:
        ttl: 0
        priority: high
        sticky: true
        car_ui: true
        notification_icon: mdi:french-fries
        tag: fritteuse_fertig_01
```

| Action | What it does |
|---|---|
| `cosori_bedienung.garen_starten` | Start: `zone` (`1`, `2`, `beide` = both, `ganz` = whole drawer), `temperatur` (°C), `minuten`, `programm` (`airfry`, `roast`, `bake`, `broil`, `reheat`, `dehydrate`, `preheat`); for `beide` optional own values for zone 2. |
| `cosori_bedienung.garen_beenden` | Stop. |
| `cosori_bedienung.befehl_senden` | **Tinkerers, admins only:** sends an app command and returns the response (without account data). |

---

## 🛡️ Privacy

Only Home Assistant talks to the VeSync server – exactly like your app. Nobody else.

- **Stored** (in Home Assistant, so also in your backups): your account **email**, **not** your password but only its **MD5 value** (VeSync needs it to log in; ⚠️ it can be used to log in, so treat backups like a key), a **random device ID**, your options.
- **Sent** only to **VeSync** (`smartapi.vesync.eu` / `smartapi.vesync.com`): login, device list, fryer status (every 15–60 s), your commands. **Nothing** goes to the developer or anyone else. No telemetry.
- **Redacted** everywhere (raw-data sensor, diagnostics, “send command” responses): token, account ID, device IDs (cid/uuid/MAC), email, image links. Password and token are never logged.
- **Removing** the integration deletes everything above from Home Assistant.

---

## 🙈 Honestly: what doesn't work (yet)

- **Unofficial.** If Cosori/VeSync change their server, it may break until updated.
- **Remote start** is partly blocked by Cosori in the EU. You get a clear error if the fryer refuses.
- **Pause/resume:** command not known for sure yet – no button.
- **Stopping a single zone and changing temperature/time** are sent as the app is believed to do (`endCook` with zone, `setTimeOrTemp`) – **not yet tried on a real TwinFry**.
- **Field names** on the TwinFry are partly guessed. If a sensor shows nonsense, check `sensor.…_raw_data`.
- **Older 3.7/5.8 qt models** (CS…): display only, no start.

**Time remaining 60× too large/small?** Devices & services → Cosori Bedienung → **Configure** → “Time values of the air fryer” → seconds or minutes.

**When are new versions released?** Official releases on **Sundays**, beta versions on other days (HACS → ⋮ → Redownload → “Show beta versions”).

---

## 💙 Like it?

It is and stays **free**. If you like, you can send a small voluntary donation via PayPal: [paypal.me/MarcoStrickmann](https://paypal.me/MarcoStrickmann). Thank you! 🙏

[![PayPal](https://img.shields.io/badge/PayPal-Donate-0070BA?logo=paypal&logoColor=white)](https://paypal.me/MarcoStrickmann)

Ideas → [Discussions](https://github.com/misterm2310/cosori-bedienung/discussions) · Bugs → [Issues](https://github.com/misterm2310/cosori-bedienung/issues) (please attach **Download diagnostics**, identifiers are already redacted).

## 🙌 Credits & legal

Made by **Mister-M** – with help from **Claude**. Login flow and commands are based on the open [ioBroker adapter “vesync”](https://github.com/TA2k/ioBroker.vesync) (MIT) and [pyvesync](https://github.com/webdjoe/pyvesync) (MIT) – thanks! 🙏

Not an official product of Cosori, VeSync or Arovast. All trademarks belong to their owners. License: [MIT](LICENSE).
