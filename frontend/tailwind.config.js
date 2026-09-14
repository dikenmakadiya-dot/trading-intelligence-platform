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
          canvas: '#030712',
          surface: '#070C1A',
          subsurface: '#0E172F',
          border: '#172445',
          muted: '#64748B',
          text: '#F8FAFC',
        },
        obsidian: {
          950: '#030712',
          900: '#060B18',
          850: '#0A1024',
          800: '#0F172E',
          750: '#15203E',
          700: '#1E294B',
        },
        trade: {
          bullish: '#10B981',
          bullishGlow: '#00FF9D',
          bearish: '#FF3366',
          accent: '#00E5FF',
          amber: '#F59E0B',
          purple: '#8B5CF6',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace']
      },
      boxShadow: {
        'bull-glow': '0 0 20px rgba(0, 255, 157, 0.25)',
        'bear-glow': '0 0 20px rgba(255, 51, 102, 0.25)',
        'accent-glow': '0 0 20px rgba(0, 229, 255, 0.25)',
        'card-glass': '0 10px 30px -5px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08)'
      }
    },
  },
  plugins: [],
}
