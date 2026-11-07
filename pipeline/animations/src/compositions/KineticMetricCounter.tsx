import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';
import { CardFooter } from '../components/CardFooter';
import { GlowBorder } from '../components/GlowBorder';

export interface SubMetricItem {
  label: string;
  value: string;
  change?: string;
  accent?: 'green' | 'blue' | 'yellow';
}

export interface KineticMetricCounterProps {
  title?: string;
  subtitle?: string;
  badge?: string;
  metricLabel?: string;
  targetValue?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  deltaCallout?: string;
  subMetrics?: SubMetricItem[];
  source?: string;
}

const DEFAULT_SUB_METRICS: SubMetricItem[] = [
  { label: 'Token Throughput', value: '184 tok/s', change: '+3.2x', accent: 'green' },
  { label: 'Memory Footprint', value: '14.2 GB', change: '-45%', accent: 'blue' },
  { label: 'Inference Latency', value: '18 ms', change: '-60%', accent: 'green' },
];

export const KineticMetricCounter: React.FC<KineticMetricCounterProps> = ({
  title = 'BREAKTHROUGH INFERENCE SPEEDUP',
  subtitle = 'Speculative Decoding & Quantization Optimization',
  badge = 'PERFORMANCE BENCHMARK',
  metricLabel = 'EFFECTIVE TOKEN GENERATION',
  targetValue = 184.5,
  prefix = '',
  suffix = ' tok/s',
  decimals = 1,
  deltaCallout = '3.2X FASTER THAN BASELINE',
  subMetrics = DEFAULT_SUB_METRICS,
  source = 'Source: Research Paper Benchmarks & Hardware Profiler',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Primary count-up spring animation
  const countStart = 15;
  const countSpring = spring({
    frame: Math.max(0, frame - countStart),
    fps,
    config: SPRING_PRESETS.snappy,
  });
  const countProgress = Math.min(1.05, Math.max(0, countSpring));

  const displayedVal = targetValue * countProgress;
  const formattedVal =
    decimals > 0
      ? displayedVal.toFixed(decimals)
      : Math.round(displayedVal).toLocaleString('en-US');

  // Delta badge spring
  const calloutStart = countStart + 35;
  const calloutSpring = spring({
    frame: Math.max(0, frame - calloutStart),
    fps,
    config: SPRING_PRESETS.snappy,
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
      <div style={{ width: '100%', zIndex: 2, marginBottom: 36 }}>
        <CardHeader badge={badge} title={title} subtitle={subtitle} />
      </div>

      {/* Central Visual Card */}
      <div style={{ width: 960, zIndex: 2, marginBottom: 28 }}>
        <GlowBorder active={true}>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              gap: 28,
            }}
          >
            {/* Metric Category Label */}
            <div
              style={{
                color: THEME.colors.textMuted,
                fontSize: 24,
                fontWeight: 700,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
              }}
            >
              {metricLabel}
            </div>

            {/* Massive Kinetic Number Ticker with Tabular Figures */}
            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                justifyContent: 'center',
                gap: 12,
              }}
            >
              {prefix && (
                <span
                  style={{
                    color: THEME.colors.primary,
                    fontSize: 72,
                    fontWeight: 800,
                  }}
                >
                  {prefix}
                </span>
              )}
              <span
                style={{
                  color: THEME.colors.primary,
                  fontSize: 130,
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  fontVariantNumeric: 'tabular-nums',
                  lineHeight: 1,
                  textShadow: `0 0 40px ${THEME.colors.primaryGlow}`,
                }}
              >
                {formattedVal}
              </span>
              {suffix && (
                <span
                  style={{
                    color: THEME.colors.white,
                    fontSize: 48,
                    fontWeight: 800,
                    letterSpacing: '-0.02em',
                  }}
                >
                  {suffix}
                </span>
              )}
            </div>

            {/* Glowing Linear Progress Gauge Bar */}
            <div
              style={{
                width: '100%',
                height: 12,
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                borderRadius: 9999,
                overflow: 'hidden',
                position: 'relative',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${countProgress * 100}%`,
                  backgroundColor: THEME.colors.primary,
                  boxShadow: `0 0 20px ${THEME.colors.primary}`,
                  borderRadius: 9999,
                }}
              />
            </div>

            {/* Delta Leap Callout Pill */}
            {deltaCallout && calloutSpring > 0.05 && (
              <div
                style={{
                  transform: `scale(${calloutSpring})`,
                  opacity: Math.min(1, calloutSpring),
                  backgroundColor: 'rgba(0, 242, 254, 0.12)',
                  border: `2px solid ${THEME.colors.primary}`,
                  borderRadius: 16,
                  padding: '12px 32px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  boxShadow: `0 0 30px ${THEME.colors.primaryDim}`,
                }}
              >
                <span
                  style={{
                    color: THEME.colors.primary,
                    fontSize: 26,
                    fontWeight: 800,
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                  }}
                >
                  ⚡ {deltaCallout}
                </span>
              </div>
            )}

            {/* Supporting Metric Tiles */}
            {subMetrics && subMetrics.length > 0 && (
              <div
                style={{
                  width: '100%',
                  display: 'grid',
                  gridTemplateColumns: `repeat(${subMetrics.length}, 1fr)`,
                  gap: 16,
                  marginTop: 10,
                }}
              >
                {subMetrics.map((sm, idx) => {
                  const smStart = countStart + 22 + idx * 6;
                  const smSpring = spring({
                    frame: Math.max(0, frame - smStart),
                    fps,
                    config: SPRING_PRESETS.snappy,
                  });

                  return (
                    <div
                      key={sm.label}
                      style={{
                        backgroundColor: 'rgba(17, 24, 39, 0.72)',
                        backdropFilter: 'blur(12px)',
                        border: '1px solid rgba(255, 255, 255, 0.10)',
                        borderRadius: 16,
                        padding: '18px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 6,
                        opacity: Math.min(1, smSpring),
                        transform: `scale(${Math.max(0, smSpring)})`,
                        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.36)',
                      }}
                    >
                      <span
                        style={{
                          color: THEME.colors.textMuted,
                          fontSize: 18,
                          fontWeight: 600,
                          textAlign: 'center',
                        }}
                      >
                        {sm.label}
                      </span>
                      <span
                        style={{
                          color: THEME.colors.white,
                          fontSize: 28,
                          fontWeight: 800,
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {sm.value}
                      </span>
                      {sm.change && (
                        <span
                          style={{
                            color: THEME.colors.primary,
                            fontSize: 18,
                            fontWeight: 700,
                          }}
                        >
                          {sm.change}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </GlowBorder>
      </div>

      {/* Bottom Footer */}
      <div style={{ width: '100%', zIndex: 2 }}>
        <CardFooter source={source} />
      </div>
    </div>
  );
};
