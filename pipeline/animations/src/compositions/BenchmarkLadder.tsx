import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';
import { CardFooter } from '../components/CardFooter';
import { GlowBorder } from '../components/GlowBorder';

export interface BenchmarkItem {
  label: string;
  value: number;
  baseline?: boolean;
  highlight?: boolean;
  badge?: string;
}

export interface BenchmarkLadderProps {
  title?: string;
  subtitle?: string;
  benchmarkName?: string;
  metricUnit?: string;
  items?: BenchmarkItem[];
  source?: string;
  deltaCallout?: string;
}

const DEFAULT_ITEMS: BenchmarkItem[] = [
  { label: 'o1-preview (High Reasoning)', value: 84.6, highlight: true, badge: 'NEW SOTA' },
  { label: 'Claude 3.5 Sonnet', value: 72.8, baseline: true },
  { label: 'GPT-4o (Omni)', value: 68.4, baseline: true },
  { label: 'Gemini 1.5 Pro', value: 65.2, baseline: true },
  { label: 'Llama 3 70B', value: 54.0, baseline: true },
];

export const BenchmarkLadder: React.FC<BenchmarkLadderProps> = ({
  title = 'BENCHMARK BREAKTHROUGH',
  subtitle = 'Coding & Complex Reasoning Evaluation',
  benchmarkName = 'SWE-bench Verified',
  metricUnit = '%',
  items = DEFAULT_ITEMS,
  source = 'Source: Research Paper Benchmarks & Telemetry',
  deltaCallout = '+16.2% OVER GPT-4o',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Find max value to calibrate horizontal scale (with 10% headroom)
  const maxRaw = Math.max(...items.map((i) => i.value), 100);
  const maxDomain = Math.ceil(maxRaw / 10) * 10;

  // Staggered bar entry configuration
  const startFrame = 15;
  const staggerFrames = 7;

  // Delta callout badge spring
  const calloutStart = startFrame + items.length * staggerFrames + 8;
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
        <CardHeader badge={benchmarkName} title={title} subtitle={subtitle} />
      </div>

      {/* Central Visual Card: Benchmark Ladder */}
      <div style={{ width: 960, zIndex: 2, marginBottom: 20 }}>
        <GlowBorder active={true}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {/* Isolated Chart Area: Bars and Guidelines */}
            <div
              style={{
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                gap: 24,
                paddingBottom: 24,
                marginBottom: deltaCallout ? 20 : 0,
                borderBottom: deltaCallout ? '1px solid rgba(255, 255, 255, 0.08)' : 'none',
              }}
            >
              {/* Axis Guidelines: Scoped ONLY to the chart area */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  bottom: 0,
                  left: 12,
                  right: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  pointerEvents: 'none',
                }}
              >
                {[0, 25, 50, 75, 100].map((tick) => (
                  <div
                    key={tick}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      height: '100%',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div
                      style={{
                        flex: 1,
                        width: 1,
                        backgroundColor: 'rgba(255, 255, 255, 0.06)',
                        borderStyle: 'dashed',
                      }}
                    />
                    <span
                      style={{
                        color: THEME.colors.textDim,
                        fontSize: 16,
                        fontFamily: THEME.fonts.mono,
                        marginTop: 8,
                      }}
                    >
                      {Math.round((tick / 100) * maxDomain)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Benchmark Bars */}
              {items.map((item, index) => {
                const itemStart = startFrame + index * staggerFrames;
                const barSpring = spring({
                  frame: Math.max(0, frame - itemStart),
                  fps,
                  config: SPRING_PRESETS.snappy,
                });
                const barProgress = Math.max(0, barSpring);

                const currentVal = Math.round(item.value * Math.min(1.0, barSpring) * 10) / 10;
                const isHighlight = item.highlight;
                const barColor = isHighlight ? THEME.colors.primary : '#475569';
                const labelColor = isHighlight ? THEME.colors.white : THEME.colors.textMuted;

                // Max bar width available in px (out of ~600px width allocated for bar track)
                const maxTrackWidth = 540;
                const barWidth = (item.value / maxDomain) * maxTrackWidth * barProgress;

                return (
                  <div
                    key={item.label}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                      zIndex: 3,
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        paddingRight: 20,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span
                          style={{
                            color: labelColor,
                            fontSize: isHighlight ? 28 : 24,
                            fontWeight: isHighlight ? 800 : 600,
                            letterSpacing: '-0.01em',
                          }}
                        >
                          {item.label}
                        </span>
                        {item.badge && barProgress > 0.8 && (
                          <span
                            style={{
                              padding: '4px 10px',
                              borderRadius: 6,
                              backgroundColor: THEME.colors.cyberYellow,
                              color: '#000000',
                              fontSize: 16,
                              fontWeight: 800,
                              letterSpacing: '0.05em',
                              boxShadow: `0 0 16px ${THEME.colors.cyberYellowGlow}`,
                            }}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>

                      {/* Numeric Value Label with Tabular Figures */}
                      <span
                        style={{
                          color: isHighlight ? THEME.colors.primary : THEME.colors.white,
                          fontSize: isHighlight ? 34 : 28,
                          fontWeight: 800,
                          fontVariantNumeric: 'tabular-nums',
                          fontFamily: THEME.fonts.mono,
                        }}
                      >
                        {currentVal.toFixed(1)}
                        <span style={{ fontSize: 20, opacity: 0.8, marginLeft: 2 }}>{metricUnit}</span>
                      </span>
                    </div>

                    {/* Horizontal Bar Track */}
                    <div
                      style={{
                        height: isHighlight ? 34 : 26,
                        width: '100%',
                        backgroundColor: 'rgba(255, 255, 255, 0.04)',
                        borderRadius: 8,
                        overflow: 'hidden',
                        position: 'relative',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${Math.max(2, (barWidth / maxTrackWidth) * 100)}%`,
                          backgroundColor: barColor,
                          borderRadius: 8,
                          boxShadow: isHighlight ? `0 0 24px ${THEME.colors.primaryGlow}` : 'none',
                          transition: 'none',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Delta Leap Callout Pill: Isolated in dedicated container BELOW chart & axis */}
            {deltaCallout && calloutSpring > 0.05 && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  marginTop: 4,
                  transform: `scale(${calloutSpring})`,
                  opacity: Math.min(1, calloutSpring),
                }}
              >
                <div
                  style={{
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
                      fontSize: 24,
                      fontWeight: 800,
                      letterSpacing: '0.05em',
                      textTransform: 'uppercase',
                    }}
                  >
                    ⚡ {deltaCallout}
                  </span>
                </div>
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
