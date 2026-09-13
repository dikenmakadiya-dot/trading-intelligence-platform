/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        oled: {
          canvas: '#020617',
          surface: '#0F172A',
          subsurface: '#1E293B',
          border: '#1E293B',
          muted: '#64748B',
          text: '#F8FAFC',
        },
        trade: {
          bullish: '#22C55E',
          bearish: '#EF4444',
          accent: '#38BDF8',
          amber: '#F59E0B',
          purple: '#A855F7',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Fira Code', 'JetBrains Mono', 'Menlo', 'Consolas', 'monospace']
      },
      boxShadow: {
        'bull-glow': '0 0 15px rgba(34, 197, 94, 0.2)',
        'bear-glow': '0 0 15px rgba(239, 68, 68, 0.2)',
        'accent-glow': '0 0 15px rgba(56, 189, 248, 0.2)',
        'card-glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)'
      }
    },
  },
  plugins: [],
}
