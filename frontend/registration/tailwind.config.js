/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eef4fc",
          100: "#d7e6f7",
          400: "#5c8fce",
          500: "#3569AC",
          600: "#2a5488",
          700: "#1f3f66",
        },
        accent: {
          400: "#3fd0d3",
          500: "#15B5B8",
          600: "#0f8f92",
        },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
