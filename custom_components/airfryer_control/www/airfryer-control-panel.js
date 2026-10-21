// 📌 Seitenleisten-Ansicht: zeigt Laufband und Zonenkarte über die ganze Seite.
// Wird nur geladen, wenn die Option „In der Seitenleiste anzeigen“ eingeschaltet ist.
class AirfryerControlPanel extends HTMLElement {
  constructor() { super(); this._built = false; this._narrow = false; this._cards = []; }

  _de() {
    const l = String(this._hass?.locale?.language || this._hass?.language || "de").toLowerCase();
    return l.startsWith("de");
  }

  set hass(hass) {
    this._hass = hass;
    if (this._menu) { const t = this._de() ? "Menü" : "Menu"; this._menu.title = t; this._menu.setAttribute("aria-label", t); }
    for (const c of this._cards) c.hass = hass;
  }

  set narrow(v) { this._narrow = !!v; if (this._menu) this._menu.style.display = this._narrow ? "" : "none"; }
  set panel(p) { this._panel = p; this._load(); }
  connectedCallback() { this._build(); this._load(); }

  _build() {
    if (this._built) return;
    this._built = true;
    this.style.cssText = "display:block;height:100%;background:var(--primary-background-color);overflow:auto;";
    const bar = document.createElement("div");
    bar.style.cssText = "display:flex;align-items:center;gap:8px;padding:8px 12px 0;";
    const menu = document.createElement("button");
    menu.textContent = "☰";
    menu.title = this._de() ? "Menü" : "Menu";
    menu.setAttribute("aria-label", menu.title);
    menu.style.cssText = "font-size:24px;background:none;border:none;color:var(--primary-text-color);cursor:pointer;padding:4px 8px;";
    menu.style.display = this._narrow ? "" : "none";
    menu.addEventListener("click", () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    bar.appendChild(menu);
    this._menu = menu;
    const wrap = document.createElement("div");
    wrap.style.cssText = "max-width:700px;margin:0 auto;padding:8px 12px 24px;box-sizing:border-box;display:flex;flex-direction:column;gap:12px;";
    this.append(bar, wrap);
    this._wrap = wrap;
  }

  async _load() {
    if (this._cards.length || this._loading || !this._built) return;
    this._loading = true;
    try {
      if (!customElements.get("airfryer-control-card")) {
        await import(this._panel?.config?.card_url || "/airfryer_control_files/airfryer-control-card.js");
        await customElements.whenDefined("airfryer-control-card");
      }
      const ticker = document.createElement("airfryer-control-ticker");
      ticker.setConfig({ hide_when_idle: true });
      const card = document.createElement("airfryer-control-card");
      card.setConfig({ title: this._de() ? "Heißluftfritteuse" : "Air fryer" });
      this._cards = [ticker, card];
      this._wrap.append(ticker, card);
      if (this._hass) for (const c of this._cards) c.hass = this._hass;
    } catch (err) {
      this._wrap.textContent = (this._de() ? "Die Fritteuse konnte nicht geladen werden: " : "The air fryer could not be loaded: ") + (err && err.message ? err.message : err);
    } finally {
      this._loading = false;
    }
  }
}
if (!customElements.get("airfryer-control-panel")) customElements.define("airfryer-control-panel", AirfryerControlPanel);
