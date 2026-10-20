export const LANGUAGES = {
  en: "English", "zh-TW": "繁體中文", "zh-CN": "简体中文", ja: "日本語", ko: "한국어",
  es: "Español", fr: "Français", de: "Deutsch", "pt-BR": "Português (Brasil)",
};

let dict = {};
let fallback = {};
let current = "en";

export function pickLanguage() {
  const saved = localStorage.getItem("cleartake.lang");
  if (saved in LANGUAGES) return saved;
  for (const tag of navigator.languages || [navigator.language || "en"]) {
    if (tag in LANGUAGES) return tag;
    const lower = tag.toLowerCase();
    if (lower.startsWith("zh")) return /tw|hk|hant/.test(lower) ? "zh-TW" : "zh-CN";
    if (lower === "pt" || lower.startsWith("pt-")) return "pt-BR";
    const base = lower.split("-")[0];
    if (base in LANGUAGES) return base;
  }
  return "en";
}

async function load(lang) {
  const response = await fetch(`locales/${lang}.json`);
  if (!response.ok) throw new Error(`locale ${lang}`);
  return response.json();
}

export async function setLanguage(lang) {
  fallback = Object.keys(fallback).length ? fallback : await load("en");
  dict = lang === "en" ? fallback : await load(lang).catch(() => fallback);
  current = lang;
  localStorage.setItem("cleartake.lang", lang);
  document.documentElement.lang = lang;
  apply();
  return lang;
}

export function t(key, vars = {}) {
  const one = vars.n !== undefined && new Intl.PluralRules(current).select(Number(vars.n)) === "one" ? `${key}.one` : null;
  const text = (one && (dict[one] ?? fallback[one])) || (dict[key] ?? fallback[key] ?? key);
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

export function apply(root = document) {
  for (const node of root.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const node of root.querySelectorAll("[data-i18n-aria]")) node.setAttribute("aria-label", t(node.dataset.i18nAria));
  document.dispatchEvent(new CustomEvent("languagechange", { detail: current }));
}
