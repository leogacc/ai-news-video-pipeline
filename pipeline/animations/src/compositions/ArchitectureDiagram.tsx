import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';
import { CardFooter } from '../components/CardFooter';
import { GlowBorder } from '../components/GlowBorder';

export interface DiagramNode {
  id: string;
  step: string;
  title: string;
  subtitle?: string;
  badge?: string;
}

export interface ArchitectureDiagramProps {
  title?: string;
  subtitle?: string;
  category?: string;
  nodes?: DiagramNode[];
  source?: string;
  activeStepIndex?: number;
}

const DEFAULT_NODES: DiagramNode[] = [
  { id: '1', step: '01', title: 'User Intent & Goal', subtitle: 'Natural language complex task', badge: 'INPUT' },
  { id: '2', step: '02', title: 'Hierarchical Planner', subtitle: 'Decomposes task into sub-goals', badge: 'REASONING' },
  { id: '3', step: '03', title: 'Autonomous Tool Workers', subtitle: 'Executes parallel sandbox actions', badge: 'EXECUTION' },
  { id: '4', step: '04', title: 'Critic & Verifier', subtitle: 'Validates against ground truth tests', badge: 'VERIFICATION' },
];

export const ArchitectureDiagram: React.FC<ArchitectureDiagramProps> = ({
  title = 'MULTI-AGENT REASONING PIPELINE',
  subtitle = 'Autonomous Task Decomposition & Execution Architecture',
  category = 'SYSTEM ARCHITECTURE',
  nodes = DEFAULT_NODES,
  source = 'Source: Multi-Agent System Specification & Research',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Nodes reveal sequentially
  const startFrame = 15;
  const stepInterval = 18;

  // Signal packet travel along the spine
  // Loop packet through the steps every 50 frames
  const loopDuration = 50;
  const loopProgress = (frame % loopDuration) / loopDuration;

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
        <CardHeader badge={category} title={title} subtitle={subtitle} />
      </div>

      {/* Central Architecture Flow Pipeline */}
      <div style={{ width: 960, zIndex: 2, marginBottom: 28 }}>
        <GlowBorder active={true}>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
              gap: 20,
              padding: '10px 0',
            }}
          >
            {/* Connecting Vertical Trunk Spine (SVG) */}
            <div
              style={{
                position: 'absolute',
                top: 50,
                bottom: 50,
                left: 54,
                width: 4,
                zIndex: 1,
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  position: 'relative',
                }}
              >
                {/* Traveling glowing packet dot derived deterministically from frame */}
                <div
                  style={{
                    position: 'absolute',
                    top: `${loopProgress * 100}%`,
                    left: -4,
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: THEME.colors.primary,
                    boxShadow: `0 0 16px ${THEME.colors.primary}`,
                  }}
                />
              </div>
            </div>

            {/* Nodes */}
            {nodes.map((node, index) => {
              const nodeStart = startFrame + index * stepInterval;
              const nodeSpring = spring({
                frame: Math.max(0, frame - nodeStart),
                fps,
                config: SPRING_PRESETS.snappy,
              });

              // Active step highlighting calculation
              const activeStep = Math.floor((frame / 35) % nodes.length);
              const isActive = index === activeStep && frame > nodeStart;

              const borderColor = isActive
                ? THEME.colors.primary
                : nodeSpring > 0.5
                ? 'rgba(255, 255, 255, 0.10)'
                : 'transparent';

              const cardBg = isActive
                ? 'rgba(0, 242, 254, 0.12)'
                : 'rgba(17, 24, 39, 0.72)';

              return (
                <div
                  key={node.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 24,
                    transform: `translateX(${(1 - Math.min(1.0, nodeSpring)) * -40}px) scale(${Math.max(0.85, Math.min(1.02, nodeSpring))})`,
                    opacity: Math.min(1, Math.max(0, nodeSpring)),
                    zIndex: 2,
                  }}
                >
                  {/* Step Circle Marker */}
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: '50%',
                      backgroundColor: isActive ? THEME.colors.primary : 'rgba(17, 24, 39, 0.90)',
                      border: `2px solid ${isActive ? THEME.colors.primary : 'rgba(255,255,255,0.18)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: isActive ? '#000000' : THEME.colors.white,
                      fontFamily: THEME.fonts.mono,
                      fontSize: 20,
                      fontWeight: 800,
                      flexShrink: 0,
                      boxShadow: isActive ? `0 0 20px ${THEME.colors.primaryGlow}` : 'none',
                    }}
                  >
                    {node.step}
                  </div>

                  {/* Node Content Card */}
                  <div
                    style={{
                      flex: 1,
                      backgroundColor: cardBg,
                      backdropFilter: 'blur(12px)',
                      WebkitBackdropFilter: 'blur(12px)',
                      border: `1.5px solid ${borderColor}`,
                      borderRadius: 16,
                      padding: '20px 24px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      boxShadow: isActive ? `0 0 28px ${THEME.colors.primaryDim}` : '0 10px 25px rgba(0, 0, 0, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <span
                        style={{
                          color: isActive ? THEME.colors.primary : THEME.colors.white,
                          fontSize: 26,
                          fontWeight: 800,
                          letterSpacing: '-0.01em',
                        }}
                      >
                        {node.title}
                      </span>
                      {node.subtitle && (
                        <span
                          style={{
                            color: THEME.colors.textMuted,
                            fontSize: 20,
                            fontWeight: 500,
                          }}
                        >
                          {node.subtitle}
                        </span>
                      )}
                    </div>

                    {node.badge && (
                      <span
                        style={{
                          padding: '6px 14px',
                          borderRadius: 8,
                          backgroundColor: isActive ? THEME.colors.primary : 'rgba(255,255,255,0.06)',
                          color: isActive ? '#000000' : THEME.colors.textMuted,
                          fontSize: 16,
                          fontWeight: 700,
                          letterSpacing: '0.08em',
                          fontFamily: THEME.fonts.mono,
                        }}
                      >
                        {node.badge}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
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
