/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#fdf4f1',
          100: '#fbe5dc',
          200: '#f6c9b8',
          300: '#efa48a',
          400: '#e67a57',
          500: '#c85a3d',
          600: '#b04530',
          700: '#923628',
          800: '#762d24',
          900: '#612822',
        },
        gold: {
          400: '#e8c56a',
          500: '#d4a853',
          600: '#b8882f',
        },
        charcoal: {
          900: '#1c1c1c',
          800: '#2c2c2c',
          700: '#3c3c3c',
          600: '#555555',
          400: '#888888',
          200: '#cccccc',
          100: '#eeeeee',
          50:  '#faf8f5',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
