import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("flitz-theme")||"dark";if(t==="dark")document.documentElement.classList.add("dark");}catch(e){document.documentElement.classList.add("dark");}})();`;

export function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("flitz-theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      className="glass relative inline-flex h-9 w-9 items-center justify-center rounded-full text-foreground transition-all duration-300 hover:shadow-glow"
    >
      <Sun
        className={`absolute h-4 w-4 transition-all duration-500 ${dark ? "scale-0 rotate-90 opacity-0" : "scale-100 rotate-0 opacity-100"}`}
      />
      <Moon
        className={`absolute h-4 w-4 transition-all duration-500 ${dark ? "scale-100 rotate-0 opacity-100" : "scale-0 -rotate-90 opacity-0"}`}
      />
    </button>
  );
}
