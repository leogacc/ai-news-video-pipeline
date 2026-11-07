import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';

export interface PersistentHookBannerProps {
  text?: string;
  badge?: string;
  width?: number;
  height?: number;
  top?: number;
}

export const PersistentHookBanner: React.FC<PersistentHookBannerProps> = ({
  text = '⚡ AI BREAKTHROUGH DISPATCH',
  badge = '',
  width = 960,
  height = 110,
  top = 240,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring from top
  const entrySpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.snappy,
  });

  const translateY = interpolate(entrySpring, [0, 1], [-60, 0]);
  const opacity = interpolate(entrySpring, [0, 1], [0, 1]);

  const cleanText = badge && !text.startsWith(badge) ? `${badge} ${text}` : text;

  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: (1080 - width) / 2,
        width,
        height,
        transform: `translateY(${translateY}px)`,
        opacity,
        zIndex: 50,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(255, 255, 255, 0.98)',
          borderRadius: 24,
          border: '2px solid rgba(225, 230, 240, 1)',
          boxShadow: '0 12px 35px rgba(0, 0, 0, 0.45)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 32px',
          boxSizing: 'border-box',
        }}
      >
        <span
          style={{
            fontFamily: THEME.fonts.title,
            fontWeight: 800,
            fontSize: cleanText.length > 40 ? 28 : 34,
            color: '#0A0E16',
            letterSpacing: '-0.5px',
            textTransform: 'uppercase',
            textAlign: 'center',
            lineHeight: 1.2,
          }}
        >
          {cleanText}
        </span>
      </div>
    </div>
  );
};
