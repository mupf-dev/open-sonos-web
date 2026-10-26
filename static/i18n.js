"use strict";
/* Übersetzungen
 *
 * Jede Sprache ist eine Datei static/i18n/<code>.json (z. B. fr.json). Eine neue Datei wird automatisch
 * erkannt und in der Sprachauswahl angeboten – kein Code nötig. Fehlende Schlüssel fallen auf Englisch zurück.
 *
 *   _("queue.title")                      → "Queue"
 *   _("common.tracks", { count: 3 })      → "3 tracks"   (Mehrzahl über { "one": …, "other": … })
 *   _("stage.read_more", { source: "x" }) → Platzhalter {source} wird ersetzt
 *
 * Statisches HTML: data-i18n="key" (Text), data-i18n-title="key" (Tooltip).
 */
const I18N = { lang: "en", dict: {}, fallback: {}, languages: [], missing: new Set(), untranslated: new Set() };

function i18nLookup(dict, key) {
  return key.split(".").reduce((o, k) => (o && typeof o === "object" ? o[k] : undefined), dict);
}

function _(key, params = {}, fallback) {
  let s = i18nLookup(I18N.dict, key);
  if (s === undefined) {
    s = i18nLookup(I18N.fallback, key);
    // für Übersetzer: fehlende Einträge sammeln (I18N.untranslated / I18N.missing in der Browser-Konsole)
    if (s !== undefined && I18N.lang !== "en" && !I18N.untranslated.has(key)) { I18N.untranslated.add(key); console.info(`[i18n] ${I18N.lang}: “${key}” fehlt, Englisch verwendet`); }
  }
  if (s === undefined) {
    if (fallback === undefined && !I18N.missing.has(key)) { I18N.missing.add(key); console.warn(`[i18n] unbekannter Schlüssel “${key}”`); }
    return fallback !== undefined ? fallback : key;
  }
  if (s && typeof s === "object" && !Array.isArray(s) && "other" in s) {
    let rule = "other";
    try { rule = new Intl.PluralRules(I18N.lang).select(Number(params.count ?? 0)); } catch {}
    s = s[rule] ?? s.other;
  }
  return typeof s === "string" ? s.replace(/\{(\w+)\}/g, (m, k) => (params[k] ?? m)) : s;
}

function i18nApply(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = _(el.dataset.i18n); });
  root.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = _(el.dataset.i18nTitle); });
}

function i18nStored() { try { return localStorage.getItem("lang") || ""; } catch { return ""; } }

async function i18nInit() {
  const load = async (code) => { try { const r = await fetch(`/static/i18n/${code}.json`); return r.ok ? await r.json() : {}; } catch { return {}; } };
  try { I18N.languages = await (await fetch("/api/i18n")).json(); } catch { I18N.languages = [{ code: "en", name: "English" }]; }
  const codes = I18N.languages.map((l) => l.code);
  let lang = i18nStored();
  if (!codes.includes(lang)) {
    const wanted = (navigator.languages?.length ? navigator.languages : [navigator.language || "en"]).map((l) => l.toLowerCase().split("-")[0]);
    lang = wanted.find((c) => codes.includes(c)) || "en";
  }
  I18N.lang = lang;
  I18N.fallback = await load("en");
  I18N.dict = lang === "en" ? I18N.fallback : await load(lang);
  document.documentElement.lang = lang;
  i18nApply();
}

/* Sprache wechseln: merken (pro Gerät) und Seite neu aufbauen */
function i18nSet(code) {
  try { localStorage.setItem("lang", code); } catch {}
  location.reload();
}
