import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';
import { CardFooter } from '../components/CardFooter';

export interface TweetCard3DProps {
  cardSrc?: string;
  title?: string;
  subtitle?: string;
  badge?: string;
  source?: string;
  highlightWords?: string[];
}

export const TweetCard3D: React.FC<TweetCard3DProps> = ({
  cardSrc = '',
  title = 'COMMUNITY DISPATCH & TELEMETRY',
  subtitle = 'Official Verification & Primary Announcement',
  badge = 'OFFICIAL X DISPATCH',
  source = 'Source: Official X Post / Community Release',
  highlightWords,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Snappy 3D Entrance Spring
  const entrySpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.snappy,
  });

  // Perspective 3D rotation from 8° down to 0°
  const rotateX = interpolate(entrySpring, [0, 1], [8, 0]);
  const scale = interpolate(entrySpring, [0, 1], [0.94, 1.0]);

  // Organic floating hover oscillation
  const hoverY = Math.sin(frame / 18) * 4;
  const hoverRotateZ = Math.sin(frame / 36) * 0.4;

  return (
    <div
      style={{
        width: 1080,
        height: 1920,
        background: `radial-gradient(circle at 50% 25%, ${THEME.colors.bg} 0%, ${THEME.colors.bgDark} 100%)`,
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
      {/* Background Subtle Tech Grid */}
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
      <div style={{ width: '100%', zIndex: 2, marginBottom: 36 }}>
        <CardHeader badge={badge} title={title} subtitle={subtitle} />
      </div>

      {/* 3D Perspective Card Container */}
      <div
        style={{
          width: 960,
          zIndex: 2,
          marginBottom: 28,
          perspective: 1200,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%',
            transform: `perspective(1200px) rotateX(${rotateX}deg) rotateZ(${hoverRotateZ}deg) translateY(${hoverY}px) scale(${scale})`,
            transformStyle: 'preserve-3d',
            borderRadius: 24,
            border: '1px solid rgba(255, 255, 255, 0.12)',
            backgroundColor: 'rgba(17, 24, 39, 0.75)',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 25px 60px -15px rgba(0, 242, 254, 0.25), 0 0 40px rgba(0, 0, 0, 0.8)',
            position: 'relative',
            overflow: 'hidden',
            padding: 16,
            boxSizing: 'border-box',
          }}
        >
          {/* Card Media */}
          {cardSrc ? (
            <img
              src={cardSrc}
              alt="Tweet Card"
              style={{
                width: '100%',
                height: 'auto',
                borderRadius: 16,
                display: 'block',
              }}
            />
          ) : (
            <div
              style={{
                width: '100%',
                height: 480,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: THEME.colors.textMuted,
                fontSize: 24,
                fontFamily: THEME.fonts.mono,
              }}
            >
              [No Card Source Loaded]
            </div>
          )}
        </div>
      </div>

      {/* Bottom Footer */}
      <div style={{ width: '100%', zIndex: 2 }}>
        <CardFooter source={source} />
      </div>
    </div>
  );
};
