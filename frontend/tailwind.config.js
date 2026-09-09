/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#effef3', 100: '#d9ffe2', 200: '#b5fdc7', 300: '#7df79b',
          400: '#42e76d', 500: '#1fce50', 600: '#13a93d', 700: '#118533',
          800: '#12682c', 900: '#115626', 950: '#052f12',
        },
        surface: {
          0: '#070908', 50: '#0d100e', 100: '#141816', 200: '#1c211e',
          300: '#29302b', 400: '#3e4841', 500: '#68736c',
        },
        cricket: {
          green: '#42e76d', red: '#ff5c68', amber: '#f5ba45', blue: '#55a7ff', purple: '#a889ff',
        },
      },
      fontFamily: {
        sans: ['Source Sans 3', 'Helvetica Neue', 'Arial', 'system-ui', 'sans-serif'],
        display: ['Source Sans 3', 'Helvetica Neue', 'Arial', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        panel: '0 24px 80px rgba(0,0,0,.36)',
        glow: '0 0 28px rgba(66,231,109,.14)',
      },
      animation: {
        'pulse-live': 'pulse-live 2s ease-in-out infinite',
        'rise-in': 'rise-in .45s cubic-bezier(.2,.8,.2,1) both',
      },
      keyframes: {
        'pulse-live': { '0%, 100%': { opacity: '1' }, '50%': { opacity: '.35' } },
        'rise-in': { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
