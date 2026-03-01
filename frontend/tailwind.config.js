/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Deep space palette
        space: {
          950: '#050810',
          900: '#0a0e1a',
          850: '#0d1224',
          800: '#111730',
          700: '#1a2040',
          600: '#232b50',
          500: '#2e3760',
        },
        // Electric cyan accent
        cyan: {
          50: '#e0fcff',
          100: '#b8f5ff',
          200: '#85edff',
          300: '#52e5ff',
          400: '#00e5ff',
          500: '#00c8e0',
          600: '#00a3b8',
          700: '#007d8f',
          800: '#005a66',
          900: '#00363d',
        },
        // Warm amber accent
        amber: {
          50: '#fff8e0',
          100: '#ffecb3',
          200: '#ffe082',
          300: '#ffd54f',
          400: '#ffca28',
          500: '#ffab00',
          600: '#ff8f00',
          700: '#ff6f00',
          800: '#e65100',
          900: '#bf3600',
        },
        // Status colors
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#3b82f6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0, 229, 255, 0.15)',
        'glow-cyan-lg': '0 0 40px rgba(0, 229, 255, 0.25)',
        'glow-amber': '0 0 20px rgba(255, 171, 0, 0.15)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3)',
        'card': '0 2px 8px rgba(0, 0, 0, 0.2), 0 0 1px rgba(255,255,255,0.05)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.3), 0 0 1px rgba(0, 229, 255, 0.2)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(circle, var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-down': 'slide-down 0.3s ease-out',
        'fade-in': 'fade-in 0.4s ease-out',
        'count-up': 'count-up 1s ease-out',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 10px rgba(0, 229, 255, 0.1)' },
          to: { boxShadow: '0 0 25px rgba(0, 229, 255, 0.3)' },
        },
        'slide-up': {
          from: { transform: 'translateY(10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          from: { transform: 'translateY(-10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};