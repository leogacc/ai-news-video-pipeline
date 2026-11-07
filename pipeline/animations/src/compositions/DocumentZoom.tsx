import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';

export interface DocumentZoomProps {
  imageSrc?: string;
  sourceName?: string;
  headline?: string;
  quoteText?: string;
  badge?: string;
  source?: string;
}

export const DocumentZoom: React.FC<DocumentZoomProps> = ({
  imageSrc = '',
  sourceName = 'PRIMARY SOURCE INVESTIGATION',
  headline = 'AUTONOMOUS SYSTEM DELETES PRODUCTION DATABASE',
  quoteText = 'The autonomous agent dropped both live production tables and all replica backups in under nine seconds.',
  badge = 'VERIFIED DISPATCH',
  source = 'Source: Official Investigation / Community Dispatch',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring for document container
  const entrySpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.snappy,
  });

  // Targeted camera zoom-in starting after 15 frames (0.5s)
  const zoomSpring = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: SPRING_PRESETS.smooth,
  });

  const scale = interpolate(zoomSpring, [0, 1], [1.0, 1.32]);
  const translateY = interpolate(zoomSpring, [0, 1], [0, -60]);

  // Synchronous yellow highlighter sweep (frame 25 to 70)
  const highlightProgress = interpolate(frame, [25, 65], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

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
      <div style={{ width: '100%', zIndex: 2, marginBottom: 32 }}>
        <CardHeader badge={badge} title={sourceName} subtitle={headline} />
      </div>

      {/* Document Zoom Container */}
      <div
        style={{
          width: 960,
          zIndex: 2,
          marginBottom: 28,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%',
            transform: `scale(${scale}) translateY(${translateY}px)`,
            transformOrigin: 'center 45%',
            borderRadius: 24,
            border: '1px solid rgba(255, 255, 255, 0.14)',
            backgroundColor: 'rgba(15, 20, 32, 0.85)',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 35px rgba(0, 242, 254, 0.2)',
            overflow: 'hidden',
            padding: '36px 40px',
            boxSizing: 'border-box',
          }}
        >
          {/* Document Header Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              paddingBottom: 20,
              marginBottom: 28,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  backgroundColor: THEME.colors.red,
                }}
              />
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  backgroundColor: THEME.colors.yellow,
                }}
              />
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  backgroundColor: THEME.colors.neonGreen,
                }}
              />
              <span
                style={{
                  fontFamily: THEME.fonts.mono,
                  fontSize: 18,
                  color: THEME.colors.textMuted,
                  marginLeft: 12,
                }}
              >
                archive.org / verified_dispatch.pdf
              </span>
            </div>
            <div
              style={{
                padding: '4px 12px',
                borderRadius: 6,
                backgroundColor: 'rgba(0, 242, 254, 0.12)',
                border: '1px solid rgba(0, 242, 254, 0.3)',
                color: THEME.colors.cyan,
                fontFamily: THEME.fonts.mono,
                fontSize: 14,
                fontWeight: 700,
              }}
            >
              PRIMARY PROOF
            </div>
          </div>

          {/* Headline Snippet */}
          <div
            style={{
              fontFamily: THEME.fonts.title,
              fontSize: 26,
              fontWeight: 800,
              color: '#FFFFFF',
              lineHeight: 1.3,
              marginBottom: 24,
            }}
          >
            {headline}
          </div>

          {/* Smoking Gun Quote with Cyber Yellow Highlighter */}
          <div
            style={{
              position: 'relative',
              padding: '20px 24px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: 12,
              borderLeft: `4px solid ${THEME.colors.cyan}`,
              marginBottom: 24,
            }}
          >
            {/* Animated Highlighter Overlay */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                bottom: 0,
                width: `${highlightProgress}%`,
                backgroundColor: 'rgba(255, 235, 59, 0.32)',
                borderRadius: 8,
                transition: 'width 0.1s linear',
                pointerEvents: 'none',
              }}
            />
            <span
              style={{
                position: 'relative',
                fontFamily: THEME.fonts.body,
                fontSize: 28,
                fontWeight: 700,
                color: '#FFFFFF',
                lineHeight: 1.45,
                zIndex: 1,
              }}
            >
              "{quoteText}"
            </span>
          </div>

          {/* Byline / Source footer */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontFamily: THEME.fonts.mono,
              fontSize: 16,
              color: THEME.colors.textMuted,
            }}
          >
            <span>Verified: Zero unauthorized hallucinations</span>
            <span style={{ color: THEME.colors.neonGreen }}>100% AUDIT REPRODUCIBLE</span>
          </div>
        </div>
      </div>
    </div>
  );
};
