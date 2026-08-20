// @lovable.dev/vite-tanstack-config already includes:
// - TanStack devtools
// - tanstackStart
// - viteReact
// - tailwindcss
// - tsConfigPaths
// - nitro
// - VITE_* env injection
// - @ path alias
// - React/TanStack dedupe
// - error logger plugins
// - sandbox detection

import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  vite: {
    server: {
      port: 8080,
      strictPort: true,
    },

    preview: {
      port: 8080,
      strictPort: true,
    },
  },

  tanstackStart: {
    server: {
      entry: "server",
    },
  },
});