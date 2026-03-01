/**
 * Theme Token System
 * Brand color palettes for StepByStep Direct
 */

export const themes = {
  flyers: {
    name: "Flyers",
    abbr: "PHI",
    bg: "#1A1A1A",
    bgAlt: "#242424",
    surface: "#2A2A2A",
    accent: "#F74902",
    accentHover: "#FF5A1A",
    text: "#FFFFFF",
    textSecondary: "#C4C4C4",
    textMuted: "#888888",
    textDim: "#666666",
    border: "rgba(247, 73, 2, 0.15)",
    borderSubtle: "rgba(255, 255, 255, 0.1)",
    inputBg: "#2A2A2A",
    gradient: "linear-gradient(135deg, rgba(247, 73, 2, 0.1) 0%, rgba(247, 73, 2, 0) 100%)",
    ratingGood: "#10B981",
    ratingMid: "#F59E0B",
    ratingBad: "#EF4444",
    pill: "rgba(247, 73, 2, 0.1)",
    pillBorder: "rgba(247, 73, 2, 0.3)",
    tag: "rgba(247, 73, 2, 0.2)"
  },
  
  claude: {
    name: "Claude",
    abbr: "ANTH",
    bg: "#2D2B28",
    bgAlt: "#3D3A35",
    surface: "#3D3A35",
    accent: "#DA7756",
    accentHover: "#E68A6A",
    text: "#F5F0EB",
    textSecondary: "#C7BFB6",
    textMuted: "#998F84",
    textDim: "#7A7067",
    border: "rgba(218, 119, 86, 0.18)",
    borderSubtle: "rgba(245, 240, 235, 0.1)",
    inputBg: "#3D3A35",
    gradient: "linear-gradient(135deg, rgba(218, 119, 86, 0.1) 0%, rgba(218, 119, 86, 0) 100%)",
    ratingGood: "#10B981",
    ratingMid: "#F59E0B",
    ratingBad: "#EF4444",
    pill: "rgba(218, 119, 86, 0.1)",
    pillBorder: "rgba(218, 119, 86, 0.3)",
    tag: "rgba(218, 119, 86, 0.2)"
  },
  
  amazon: {
    name: "Amazon",
    abbr: "AMZN",
    bg: "#0F1111",
    bgAlt: "#1A1F23",
    surface: "#1A1F23",
    accent: "#FF9900",
    accentHover: "#FFB84D",
    text: "#E8EAED",
    textSecondary: "#A8B1BA",
    textMuted: "#6B7785",
    textDim: "#4D5761",
    border: "rgba(255, 153, 0, 0.15)",
    borderSubtle: "rgba(232, 234, 237, 0.1)",
    inputBg: "#1A1F23",
    gradient: "linear-gradient(135deg, rgba(255, 153, 0, 0.1) 0%, rgba(255, 153, 0, 0) 100%)",
    ratingGood: "#10B981",
    ratingMid: "#F59E0B",
    ratingBad: "#EF4444",
    pill: "rgba(255, 153, 0, 0.1)",
    pillBorder: "rgba(255, 153, 0, 0.3)",
    tag: "rgba(255, 153, 0, 0.2)"
  }
};

/**
 * Get theme by key
 * @param {string} themeKey - Theme key (flyers, claude, amazon)
 * @returns {Object} Theme object
 */
export function getTheme(themeKey) {
  return themes[themeKey] || themes.claude; // Default to Claude theme
}

/**
 * Get all available theme keys
 * @returns {string[]} Array of theme keys
 */
export function getThemeKeys() {
  return Object.keys(themes);
}

/**
 * Apply theme to CSS custom properties
 * @param {Object} theme - Theme object
 */
export function applyThemeToDOM(theme) {
  if (typeof document === 'undefined') return; // Skip in non-browser environments

  const root = document.documentElement;
  
  root.style.setProperty('--bg', theme.bg);
  root.style.setProperty('--bg-alt', theme.bgAlt);
  root.style.setProperty('--surface', theme.surface);
  root.style.setProperty('--accent', theme.accent);
  root.style.setProperty('--accent-hover', theme.accentHover);
  root.style.setProperty('--text', theme.text);
  root.style.setProperty('--text-secondary', theme.textSecondary);
  root.style.setProperty('--text-muted', theme.textMuted);
  root.style.setProperty('--text-dim', theme.textDim);
  root.style.setProperty('--border', theme.border);
  root.style.setProperty('--border-subtle', theme.borderSubtle);
  root.style.setProperty('--input-bg', theme.inputBg);
  root.style.setProperty('--gradient', theme.gradient);
  root.style.setProperty('--rating-good', theme.ratingGood);
  root.style.setProperty('--rating-mid', theme.ratingMid);
  root.style.setProperty('--rating-bad', theme.ratingBad);
  root.style.setProperty('--pill', theme.pill);
  root.style.setProperty('--pill-border', theme.pillBorder);
  root.style.setProperty('--tag', theme.tag);
}

/**
 * Load theme from localStorage
 * @returns {string} Theme key from localStorage or default
 */
export function loadThemeFromStorage() {
  if (typeof localStorage === 'undefined') return 'claude';
  return localStorage.getItem('stepbystep-theme') || 'claude';
}

/**
 * Save theme to localStorage
 * @param {string} themeKey - Theme key to save
 */
export function saveThemeToStorage(themeKey) {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem('stepbystep-theme', themeKey);
}

export default {
  themes,
  getTheme,
  getThemeKeys,
  applyThemeToDOM,
  loadThemeFromStorage,
  saveThemeToStorage
};
