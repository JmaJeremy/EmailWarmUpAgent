/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#080B14',
          surface: '#0F1221',
          card: '#161929',
          elevated: '#1C2035',
        },
        border: {
          DEFAULT: '#1E2436',
          subtle: '#252B3E',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#8892A0',
          muted: '#4A5568',
        },
        orange: {
          DEFAULT: '#FF6B35',
          light: '#FF8C5A',
          dark: '#E55520',
          glow: 'rgba(255,107,53,0.15)',
        },
        green: {
          DEFAULT: '#00D68F',
          light: '#33DEAD',
          dark: '#00A870',
          glow: 'rgba(0,214,143,0.15)',
        },
        blue: {
          accent: '#4D9CFF',
          glow: 'rgba(77,156,255,0.15)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-card': 'linear-gradient(135deg, #161929 0%, #0F1221 100%)',
        'gradient-orange': 'linear-gradient(135deg, #FF6B35 0%, #E55520 100%)',
        'gradient-green': 'linear-gradient(135deg, #00D68F 0%, #00A870 100%)',
        'gradient-hero': 'radial-gradient(ellipse at 50% 0%, rgba(255,107,53,0.12) 0%, transparent 60%)',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'card-hover': '0 8px 30px rgba(0,0,0,0.5)',
        'orange-glow': '0 0 20px rgba(255,107,53,0.25)',
        'green-glow': '0 0 20px rgba(0,214,143,0.25)',
        'inner-border': 'inset 0 1px 0 rgba(255,255,255,0.05)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { transform: 'translateY(8px)', opacity: 0 }, '100%': { transform: 'translateY(0)', opacity: 1 } },
        glow: { '0%': { boxShadow: '0 0 5px rgba(255,107,53,0.2)' }, '100%': { boxShadow: '0 0 20px rgba(255,107,53,0.4)' } },
      },
    },
  },
  plugins: [],
}
