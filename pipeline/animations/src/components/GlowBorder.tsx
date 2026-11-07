import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { THEME } from '../theme';

interface GlowBorderProps {
  children: React.ReactNode;
  active?: boolean;
}

export const GlowBorder: React.FC<GlowBorderProps> = ({ children, active = true }) => {
  const frame = useCurrentFrame();

  const glowPulse = active
    ? interpolate(Math.sin((frame / 30) * Math.PI * 2), [-1, 1], [0.35, 0.65])
    : 0;

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        backgroundColor: THEME.colors.cardBg,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: `1px solid ${THEME.colors.cardBorder}`,
        borderRadius: 24,
        padding: 40,
        boxSizing: 'border-box',
        boxShadow: active
          ? `0 20px 50px rgba(0, 0, 0, 0.6), 0 0 35px rgba(0, 242, 254, ${glowPulse * 0.25}), inset 0 0 20px rgba(0, 242, 254, 0.04)`
          : '0 20px 50px rgba(0, 0, 0, 0.5)',
      }}
    >
      {/* Corner crosshairs */}
      <div
        style={{
          position: 'absolute',
          top: -1,
          left: -1,
          width: 24,
          height: 24,
          borderTop: `3px solid ${THEME.colors.primary}`,
          borderLeft: `3px solid ${THEME.colors.primary}`,
          borderTopLeftRadius: 24,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: -1,
          right: -1,
          width: 24,
          height: 24,
          borderTop: `3px solid ${THEME.colors.primary}`,
          borderRight: `3px solid ${THEME.colors.primary}`,
          borderTopRightRadius: 24,
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -1,
          left: -1,
          width: 24,
          height: 24,
          borderBottom: `3px solid ${THEME.colors.primary}`,
          borderLeft: `3px solid ${THEME.colors.primary}`,
          borderBottomLeftRadius: 24,
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -1,
          right: -1,
          width: 24,
          height: 24,
          borderBottom: `3px solid ${THEME.colors.primary}`,
          borderRight: `3px solid ${THEME.colors.primary}`,
          borderBottomRightRadius: 24,
        }}
      />

      {children}
    </div>
  );
};
