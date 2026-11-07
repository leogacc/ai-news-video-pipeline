import React from 'react';
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';

export interface GrowthPillProps {
  value?: string;
  label?: string;
  subLabel?: string;
  trend?: 'up' | 'down';
  deltaBadge?: string;
  badge?: string;
  title?: string;
  subtitle?: string;
  source?: string;
  stats?: Array<{ label: string; value: string }>;
}

export const GrowthPill: React.FC<GrowthPillProps> = ({
  value = '$159B',
  label = 'TOTAL MARKET CAP WIPEOUT',
  subLabel = 'Enterprise valuation loss across 14 enterprise providers',
  trend = 'down',
  deltaBadge = '-100%',
  badge = 'FINANCIAL SHOCKWAVE',
  title = 'MARKET VALUATION CRASH',
  subtitle = 'Immediate Capital Disruption Post-Deployment',
  source = 'Source: Bloomberg Terminal / Nasdaq Data',
  stats = [
    { label: 'PEAK PE RATIO', value: '78.4x' },
    { label: 'IMPACT DURATION', value: '< 24 HRS' },
    { label: 'RECOVERY OUTLOOK', value: 'UNVERIFIED' },
  ],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring for main container
  const entrySpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.snappy,
  });

  // Entrance spring for the central big value pill
  const pillSpring = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: SPRING_PRESETS.bouncy,
  });

  const isDown = trend === 'down';
  const accentColor = isDown ? THEME.colors.accentDanger : THEME.colors.emerald;
  const glowColor = isDown ? 'rgba(244, 63, 94, 0.45)' : 'rgba(16, 185, 129, 0.45)';

  return (
    <div
      style={{
        width: 1080,
        height: 1920,
        background: `radial-gradient(circle at 50% 30%, ${THEME.colors.bg} 0%, ${THEME.colors.bgDark} 100%)`,
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: 190,
        boxSizing: 'border-box',
        overflow: 'hidden',
        fontFamily: THEME.fonts.title,
      }}
    >
      {/* Background Tech Grid */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)`,
          backgroundSize: '80px 80px',
          opacity: 0.7,
          pointerEvents: 'none',
        }}
      />

      {/* Top Header */}
      <div style={{ width: '100%', zIndex: 2, marginBottom: 32 }}>
        <CardHeader badge={badge} title={title} subtitle={subtitle} />
      </div>

      {/* Main Metric HUD Container */}
      <div
        style={{
          width: 960,
          transform: `scale(${entrySpring})`,
          opacity: entrySpring,
          zIndex: 2,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%',
            borderRadius: 28,
            backgroundColor: 'rgba(11, 15, 25, 0.94)',
            border: `2px solid ${accentColor}`,
            boxShadow: `0 25px 60px -10px rgba(0, 0, 0, 0.8), 0 0 40px ${glowColor}`,
            padding: '44px 36px',
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          {/* Label Header */}
          <div
            style={{
              fontFamily: THEME.fonts.title,
              fontSize: 22,
              fontWeight: 800,
              color: THEME.colors.textMuted,
              letterSpacing: '1px',
              textTransform: 'uppercase',
              marginBottom: 20,
              textAlign: 'center',
            }}
          >
            {label}
          </div>

          {/* Central Massive Value Pill */}
          <div
            style={{
              transform: `scale(${pillSpring})`,
              display: 'flex',
              alignItems: 'center',
              gap: 20,
              padding: '16px 36px',
              borderRadius: 36,
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              border: `2px solid ${accentColor}`,
              boxShadow: `0 0 30px ${glowColor}`,
              marginBottom: 24,
            }}
          >
            <span
              style={{
                fontFamily: THEME.fonts.mono,
                fontSize: 84,
                fontWeight: 900,
                color: '#FFFFFF',
                letterSpacing: '-1px',
              }}
            >
              {value}
            </span>
            <div
              style={{
                backgroundColor: accentColor,
                color: '#FFFFFF',
                fontFamily: THEME.fonts.title,
                fontWeight: 900,
                fontSize: 24,
                padding: '8px 16px',
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span>{isDown ? '▼' : '▲'}</span>
              <span>{deltaBadge}</span>
            </div>
          </div>

          {/* SubLabel */}
          <div
            style={{
              fontFamily: THEME.fonts.body,
              fontSize: 18,
              color: THEME.colors.textMuted,
              textAlign: 'center',
              maxWidth: 720,
              lineHeight: 1.4,
              marginBottom: 32,
            }}
          >
            {subLabel}
          </div>

          {/* Micro-Stats Bottom Bar */}
          <div
            style={{
              width: '100%',
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 16,
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              paddingTop: 24,
            }}
          >
            {stats.map((s, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  padding: '12px 8px',
                  borderRadius: 12,
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <div
                  style={{
                    fontFamily: THEME.fonts.mono,
                    fontSize: 12,
                    fontWeight: 700,
                    color: THEME.colors.textDim,
                    letterSpacing: '0.5px',
                    marginBottom: 4,
                  }}
                >
                  {s.label}
                </div>
                <div
                  style={{
                    fontFamily: THEME.fonts.mono,
                    fontSize: 20,
                    fontWeight: 800,
                    color: '#FFFFFF',
                  }}
                >
                  {s.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
