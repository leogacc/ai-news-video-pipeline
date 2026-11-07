import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { THEME, easeOutCubic } from '../theme';

interface CardHeaderProps {
  badge?: string;
  title: string;
  subtitle?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ badge, title, subtitle }) => {
  const frame = useCurrentFrame();

  const badgeOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const titleProgress = easeOutCubic(
    interpolate(frame, [5, 25], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  );
  const titleY = (1 - titleProgress) * 20;

  const subOpacity = interpolate(frame, [15, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        padding: '0 40px',
        boxSizing: 'border-box',
      }}
    >
      {badge && (
        <div
          style={{
            opacity: badgeOpacity,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 20px',
            borderRadius: 9999,
            backgroundColor: 'rgba(57, 255, 20, 0.08)',
            border: `1px solid ${THEME.colors.primary}`,
            color: THEME.colors.primary,
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            marginBottom: 20,
            boxShadow: `0 0 20px ${THEME.colors.primaryDim}`,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: THEME.colors.primary,
              boxShadow: `0 0 10px ${THEME.colors.primary}`,
            }}
          />
          {badge}
        </div>
      )}

      <h1
        style={{
          margin: 0,
          color: THEME.colors.white,
          fontFamily: THEME.fonts.title,
          fontSize: 54,
          fontWeight: 800,
          lineHeight: 1.15,
          letterSpacing: '-0.02em',
          transform: `translateY(${titleY}px)`,
          opacity: titleProgress,
          textTransform: 'uppercase',
        }}
      >
        {title}
      </h1>

      {subtitle && (
        <p
          style={{
            margin: '16px 0 0 0',
            color: THEME.colors.textMuted,
            fontFamily: THEME.fonts.title,
            fontSize: 28,
            fontWeight: 500,
            lineHeight: 1.4,
            maxWidth: 900,
            opacity: subOpacity,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
};
