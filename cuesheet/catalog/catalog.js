// #
// catalog — 토큰·컴포넌트 목록을 실제 스타일시트에서 읽는다. 손으로 적으면 드리프트한다


// #
// collect

function eachRule(sheets, visit) {
  for (const sheet of sheets) {
    let rules;
    try {
      rules = sheet.cssRules;
    } catch {
      continue; // cross-origin
    }
    for (const rule of rules) {
      if (rule.styleSheet) eachRule([rule.styleSheet], visit);
      else visit(rule);
    }
  }
}

function collect() {
  const tokens = new Map();
  const classes = new Set();

  eachRule(document.styleSheets, (rule) => {
    if (!rule.style || !rule.selectorText) return;

    if (rule.selectorText.includes(":root")) {
      for (const name of rule.style) {
        if (name.startsWith("--")) {
          tokens.set(name, rule.style.getPropertyValue(name).trim());
        }
      }
    }

    for (const match of rule.selectorText.matchAll(/\.((?:e|b|s|v)-[a-z0-9-]+)/g)) {
      classes.add(match[1]);
    }
  });

  return { tokens, classes };
}


// #
// render token

// 정규식으로 값 모양을 맞히지 않는다 — 브라우저에게 물어본다.
// oklch·color-mix 처럼 표기가 늘어도 여기가 따라갈 필요가 없다
function kindOf(resolved) {
  if (CSS.supports("color", resolved)) return "color";
  if (/^[\d.]+(px|rem)$/.test(resolved) && CSS.supports("width", resolved)) return "length";
  if (CSS.supports("transition-duration", resolved)) return "time";
  return "text";
}

function preview(kind, resolved) {
  if (kind === "color") {
    const box = document.createElement("span");
    box.className = "e-swatch";
    box.style.background = resolved;
    return box;
  }
  if (kind === "length") {
    const box = document.createElement("span");
    box.className = "e-swatch";
    box.style.background = "var(--accent)";
    box.style.width = resolved;
    box.style.height = "var(--x-space-3)";
    return box;
  }

  const text = document.createElement("span");
  text.className = "e-code";
  text.textContent = kind === "time" ? resolved : "";
  return text;
}


function specs(list, tokens) {
  const root = getComputedStyle(document.documentElement);

  return list.map(([name, source]) => {
    const resolved = root.getPropertyValue(name).trim();
    const item = document.createElement("li");
    item.className = "b-spec";

    item.append(preview(kindOf(resolved), resolved));

    const label = document.createElement("span");
    label.className = "e-code";
    label.textContent = name;
    item.append(label);

    const value = document.createElement("span");
    value.className = "e-code";
    value.textContent = source.startsWith("var(") ? `${source} → ${resolved}` : resolved;
    item.append(value);

    return item;
  });
}

function group(id, list, tokens) {
  const target = document.getElementById(id);
  if (!target) return;
  target.replaceChildren(...specs(list, tokens));
}


// #
// coverage — 정의됐지만 카탈로그에 데모가 없는 컴포넌트

function coverage(classes) {
  const demoed = new Set(
    [...document.querySelectorAll("[data-demo]")].map((node) => node.dataset.demo)
  );
  const missing = [...classes]
    .filter((name) => !demoed.has(name))
    .sort();

  const target = document.getElementById("coverage");
  target.textContent = missing.length
    ? `데모 없는 컴포넌트 ${missing.length}개 — ${missing.join(", ")}`
    : `컴포넌트 ${classes.size}개 전부 데모 있음`;
}


// #
// run

window.addEventListener("load", () => {
  const { tokens, classes } = collect();
  const entries = [...tokens.entries()];

  group("token-x", entries.filter(([name]) => name.startsWith("--x-")), tokens);
  group("token-semantic", entries.filter(([name]) => !name.startsWith("--x-")), tokens);

  document.getElementById("count-x").textContent =
    entries.filter(([name]) => name.startsWith("--x-")).length;
  document.getElementById("count-semantic").textContent =
    entries.filter(([name]) => !name.startsWith("--x-")).length;

  coverage(classes);
});


// #
// theme — 시스템 / 라이트 / 다크 셋을 돌린다. 컴포넌트는 어느 테마인지 모른다

const THEMES = [null, "light", "dark"];
const LABEL = { null: "시스템", light: "라이트", dark: "다크" };
const THEME_KEY = "cuesheet.theme";

function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;

  document.getElementById("theme-label").textContent = LABEL[theme];
  try {
    if (theme) localStorage.setItem(THEME_KEY, theme);
    else localStorage.removeItem(THEME_KEY);
  } catch {
    // 저장 불가여도 이번 세션은 동작한다
  }
}

window.addEventListener("load", () => {
  let current = null;
  try {
    current = localStorage.getItem(THEME_KEY);
  } catch {
    // 위와 같다
  }
  applyTheme(THEMES.includes(current) ? current : null);

  document.getElementById("theme").addEventListener("click", () => {
    const next = THEMES[(THEMES.indexOf(document.documentElement.dataset.theme || null) + 1) % THEMES.length];
    applyTheme(next);
  });
});
