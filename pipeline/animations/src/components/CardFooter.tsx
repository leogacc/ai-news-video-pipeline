import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { THEME } from '../theme';

interface CardFooterProps {
  source?: string;
  watermark?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({
  source = 'Source: Research Paper & Benchmark Telemetry',
  watermark = '@leos.logos',
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [20, 35], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        width: '100%',
        padding: '0 64px',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
        opacity,
      }}
    >
      {/* Source Attribution - Regular weight per 2026-11-04 Source-Regular rule */}
      <div
        style={{
          color: THEME.colors.textMuted,
          fontFamily: THEME.fonts.title,
          fontSize: 24,
          fontWeight: 400,
          letterSpacing: '0.02em',
          textAlign: 'center',
        }}
      >
        {source}
      </div>

      {/* Watermark: @leos.logos, white 20% opaque (alpha 51), matching clip_frames.py */}
      <div
        style={{
          color: 'rgba(255, 255, 255, 0.20)',
          fontFamily: THEME.fonts.title,
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'lowercase',
        }}
      >
        {watermark}
      </div>
    </div>
  );
};
