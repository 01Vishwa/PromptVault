import type { Config } from 'tailwindcss';

const config: Config = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Axiom Dark Theme
                background: 'hsl(240 10% 3.9%)',
                foreground: 'hsl(0 0% 98%)',

                // Card/Surface colors
                card: {
                    DEFAULT: 'hsl(240 10% 6%)',
                    foreground: 'hsl(0 0% 98%)',
                },

                // Muted colors
                muted: {
                    DEFAULT: 'hsl(240 10% 12%)',
                    foreground: 'hsl(240 5% 64.9%)',
                },

                // Electric Violet Accent
                accent: {
                    DEFAULT: 'hsl(263.4 70% 50.4%)',
                    foreground: 'hsl(0 0% 98%)',
                    light: 'hsl(263.4 70% 60%)',
                    dark: 'hsl(263.4 70% 40%)',
                },

                // Border colors
                border: 'hsl(240 10% 15%)',
                'border-hover': 'hsl(240 10% 25%)',

                // Input colors
                input: 'hsl(240 10% 8%)',
                ring: 'hsl(263.4 70% 50.4%)',

                // Status colors
                success: 'hsl(142 76% 36%)',
                warning: 'hsl(38 92% 50%)',
                error: 'hsl(0 84% 60%)',
                info: 'hsl(199 89% 48%)',
            },

            fontFamily: {
                sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
                mono: ['Fira Code', 'SF Mono', 'Consolas', 'monospace'],
            },

            borderRadius: {
                'xl': '1rem',
                '2xl': '1.5rem',
            },

            boxShadow: {
                'glow': '0 0 20px rgba(139, 92, 246, 0.3)',
                'glow-sm': '0 0 10px rgba(139, 92, 246, 0.2)',
                'card': '0 4px 20px rgba(0, 0, 0, 0.4)',
            },

            backdropBlur: {
                'glass': '12px',
            },

            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'slide-in': 'slideIn 0.2s ease-out',
                'pulse-dot': 'pulseDot 1.4s ease-in-out infinite',
            },

            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideIn: {
                    '0%': { opacity: '0', transform: 'translateX(-10px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                pulseDot: {
                    '0%, 80%, 100%': { opacity: '0.4', transform: 'scale(0.8)' },
                    '40%': { opacity: '1', transform: 'scale(1)' },
                },
            },
        },
    },
    plugins: [],
};

export default config;
