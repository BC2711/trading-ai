/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        status: {
          success: "#10b981",
          warning: "#f59e0b",
          error: "#ef4444",
          info: "#06b6d4"
        }
      },
      boxShadow: {
        glass: "0 24px 80px rgba(15, 23, 42, 0.18)"
      }
    }
  },
  plugins: []
};
