/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Waveriders Primary Green Gradient
        primary: {
          light: '#A8E6CF',
          DEFAULT: '#4CAF50',
          deep: '#2E7D32',
        },
        // Neutral Grays
        gray: {
          medium: '#9E9E9E',
          dark: '#616161',
          charcoal: '#424242',
          black: '#212121',
        },
        // Accent Colors
        accent: {
          charcoal: '#1A1A1A',
          yellow: '#FFD600',
        },
      },
      fontFamily: {
        sans: ['Instrument Sans', 'system-ui', 'sans-serif'],
        body: ['Instrument Sans Medium', 'system-ui', 'sans-serif'],
        heading: ['Instrument Sans Bold', 'system-ui', 'sans-serif'],
      },
      fontWeight: {
        body: '500',
        heading: '700',
      },
    },
  },
  plugins: [],
}
