import { useCallback, useEffect, useState } from "react";
const STORAGE_KEY = "dvein-theme";
function currentTheme() {
  return document.documentElement.dataset.theme ?? "light";
}
/**
 * Reads the theme stamped onto <html> by the inline script in index.html and
 * keeps it in sync with localStorage. The initial value is never computed here,
 * so there is no flash of the wrong theme on first paint.
 */
export function useTheme() {
  const [theme, setTheme] = useState(currentTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);
  const toggle = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);
  return { theme, setTheme, toggle };
}
