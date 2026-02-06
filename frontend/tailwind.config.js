/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'oregon-green': '#005A2B',
        'oregon-gold': '#FFC72C',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
