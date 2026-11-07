import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';

export interface StopwatchTickerProps {
  targetSeconds?: number;
  label?: string;
  badge?: string;
  title?: string;
  subtitle?: string;
  source?: string;
  warningText?: string;
}

export const StopwatchTicker: React.FC<StopwatchTickerProps> = ({
  targetSeconds = 9.0,
  label = 'TIME UNTIL FULL DATABASE PURGE',
  badge = 'TEMPORAL VELOCITY',
  title = 'CATASTROPHIC ESCALATION SPEED',
  subtitle = 'Measured Time-To-Failure Across Agent Swarm',
  source = 'Source: Production Incident Telemetry',
  warningText = 'CRITICAL AUTOMATION FAILURE ENCOUNTERED',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring for container
  const entrySpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.snappy,
  });

  // Calculate elapsed time from 0.00s to targetSeconds over 60 frames (~2 seconds)
  const elapsed = interpolate(frame, [10, 70], [0, targetSeconds], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const formattedSeconds = elapsed.toFixed(2);
  const isTargetReached = frame >= 70;

  // Pulse effect when target is reached
  const pulse = Math.sin(frame * 0.25) * 0.05 + 1.0;

  // Warning banner entrance spring
  const warningSpring = spring({
    frame: Math.max(0, frame - 55),
    fps,
    config: SPRING_PRESETS.bouncy,
  });

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
      {/* Subtle background tech grid */}
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

      {/* Main Chronometer HUD Card */}
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
            border: isTargetReached
              ? `2px solid ${THEME.colors.accentDanger}`
              : '1px solid rgba(0, 242, 254, 0.35)',
            boxShadow: isTargetReached
              ? '0 25px 60px -10px rgba(244, 63, 94, 0.4), 0 0 35px rgba(244, 63, 94, 0.25)'
              : '0 25px 60px -10px rgba(0, 0, 0, 0.8), 0 0 35px rgba(0, 242, 254, 0.2)',
            padding: '44px 36px',
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            transition: 'border 0.3s ease, box-shadow 0.3s ease',
          }}
        >
          {/* Status Chip */}
          <div
            style={{
              padding: '6px 16px',
              borderRadius: 20,
              backgroundColor: isTargetReached
                ? 'rgba(244, 63, 94, 0.15)'
                : 'rgba(0, 242, 254, 0.12)',
              border: `1px solid ${isTargetReached ? THEME.colors.accentDanger : THEME.colors.primary}`,
              color: isTargetReached ? THEME.colors.accentDanger : THEME.colors.primary,
              fontFamily: THEME.fonts.mono,
              fontSize: 14,
              fontWeight: 800,
              letterSpacing: '1px',
              marginBottom: 20,
            }}
          >
            {isTargetReached ? 'STOPPED — CRITICAL POINT' : 'LIVE STOPWATCH TICKER'}
          </div>

          {/* Label */}
          <div
            style={{
              fontFamily: THEME.fonts.title,
              fontSize: 22,
              fontWeight: 800,
              color: THEME.colors.textMuted,
              letterSpacing: '1px',
              textTransform: 'uppercase',
              marginBottom: 16,
              textAlign: 'center',
            }}
          >
            {label}
          </div>

          {/* Digital Timer Readout */}
          <div
            style={{
              fontFamily: THEME.fonts.mono,
              fontSize: 96,
              fontWeight: 900,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-2px',
              color: isTargetReached ? '#FFFFFF' : THEME.colors.primary,
              textShadow: isTargetReached
                ? '0 0 40px rgba(244, 63, 94, 0.8)'
                : '0 0 30px rgba(0, 242, 254, 0.6)',
              transform: isTargetReached ? `scale(${pulse})` : 'scale(1)',
              display: 'flex',
              alignItems: 'baseline',
              gap: 8,
              marginBottom: 24,
            }}
          >
            <span>{formattedSeconds}</span>
            <span style={{ fontSize: 36, color: THEME.colors.textDim, fontWeight: 700 }}>s</span>
          </div>

          {/* Progress Bar Track */}
          <div
            style={{
              width: '85%',
              height: 12,
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: 6,
              overflow: 'hidden',
              marginBottom: 32,
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <div
              style={{
                width: `${Math.min(100, (elapsed / targetSeconds) * 100)}%`,
                height: '100%',
                background: isTargetReached
                  ? `linear-gradient(90deg, ${THEME.colors.accentWarning}, ${THEME.colors.accentDanger})`
                  : `linear-gradient(90deg, ${THEME.colors.primary}, ${THEME.colors.neonGreen})`,
                boxShadow: isTargetReached
                  ? '0 0 15px rgba(244, 63, 94, 0.8)'
                  : '0 0 15px rgba(0, 242, 254, 0.8)',
              }}
            />
          </div>

          {/* Critical Warning Alert Pill */}
          {frame >= 55 && (
            <div
              style={{
                width: '100%',
                transform: `scale(${warningSpring})`,
                backgroundColor: 'rgba(244, 63, 94, 0.16)',
                border: `2px solid ${THEME.colors.accentDanger}`,
                borderRadius: 16,
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxSizing: 'border-box',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 28 }}>⚠️</span>
                <span
                  style={{
                    fontFamily: THEME.fonts.title,
                    fontWeight: 800,
                    fontSize: 18,
                    color: '#FFFFFF',
                    letterSpacing: '0.4px',
                  }}
                >
                  {warningText}
                </span>
              </div>
              <div
                style={{
                  backgroundColor: THEME.colors.accentDanger,
                  color: '#FFFFFF',
                  fontFamily: THEME.fonts.mono,
                  fontWeight: 800,
                  fontSize: 13,
                  padding: '6px 12px',
                  borderRadius: 6,
                }}
              >
                BREACH
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
