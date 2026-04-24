import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        yale: '#00356b',
        'yale-light': '#63aaff',
        surface: '#fafafa',
        card: '#ffffff',
        muted: '#6b7280',
        border: '#e5e7eb',
        accent: '#2E4A7A',
        red: '#C0392B',
        orange: '#E67E22',
        green: '#27AE60',
        gray: '#7F8C8D',
        dark: '#2C3E50',
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', '"Times New Roman"', 'serif'],
        sans: ['"Helvetica Neue"', 'Helvetica', 'Arial', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
