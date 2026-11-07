export const THEME = {
  colors: {
    bg: '#0B0F19',                    // Deep Midnight Slate
    bgDark: '#030712',                // Vignette edge
    primary: '#00F2FE',               // Tech Cyan (primary winner / focus)
    primaryGlow: 'rgba(0, 242, 254, 0.40)',
    primaryDim: 'rgba(0, 242, 254, 0.12)',
    cyberYellow: '#FFE600',           // Electric Cyber Yellow
    cyberYellowGlow: 'rgba(255, 230, 0, 0.40)',
    emerald: '#10B981',               // Positive delta emerald
    emeraldGlow: 'rgba(16, 185, 129, 0.35)',
    neonGreen: '#39FF14',             // Channel terminal green
    white: '#FFFFFF',
    textMuted: '#94A3B8',             // Slate 400
    textDim: '#64748B',               // Slate 500
    cardBg: 'rgba(17, 24, 39, 0.78)', // Glassmorphic slate-900
    cardBorder: 'rgba(255, 255, 255, 0.10)',
    cardBorderActive: '#00F2FE',
    accentBlue: '#38BDF8',
    accentWarning: '#FBBF24',
    accentDanger: '#F43F5E',
  },
  glass: {
    card: {
      backgroundColor: 'rgba(17, 24, 39, 0.78)',
      backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255, 255, 255, 0.10)',
      boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 242, 254, 0.08)',
    },
  },
  fonts: {
    title: 'Montserrat, Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    body: 'Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    mono: '"JetBrains Mono", "DejaVu Sans Mono", monospace',
  },
  layout: {
    width: 1080,
    height: 1920,
    paddingX: 64,
    headerTop: 260,
    footerBottom: 120,
    contentTop: 440,
    contentHeight: 1100,
  },
} as const;

export const SPRING_PRESETS = {
  snappy: { damping: 12, mass: 0.5, stiffness: 110, overshootClamping: false },
  gentle: { damping: 16, mass: 0.8, stiffness: 90, overshootClamping: false },
  bouncy: { damping: 10, mass: 0.4, stiffness: 140, overshootClamping: false },
  subtle: { damping: 14, mass: 0.6, stiffness: 100, overshootClamping: false },
} as const;

export const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);
export const easeOutExpo = (t: number): number => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));
export const easeInOutQuad = (t: number): number =>
  t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
