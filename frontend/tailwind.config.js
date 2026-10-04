/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        agro: {
          50: '#f2f9f3',
          100: '#e1f2e5',
          200: '#c5e5cd',
          300: '#99d1a6',
          400: '#67b579',
          500: '#439956',
          600: '#327c44',
          700: '#2a6338',
          800: '#254f30',
          900: '#204129',
        },
      },
    },
  },
  plugins: [],
}
