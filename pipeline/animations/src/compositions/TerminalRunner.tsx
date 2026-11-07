import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { THEME, SPRING_PRESETS } from '../theme';
import { CardHeader } from '../components/CardHeader';

export interface StdoutLine {
  text: string;
  type?: 'info' | 'success' | 'warning' | 'error';
}

export interface TerminalRunnerProps {
  command?: string;
  typingDurationFrames?: number;
  stdoutLines?: StdoutLine[];
  refusalBadge?: string;
  isRefusal?: boolean;
  badge?: string;
  title?: string;
  subtitle?: string;
  source?: string;
}

export const TerminalRunner: React.FC<TerminalRunnerProps> = ({
  command = '$ noorm db:drop --prod',
  typingDurationFrames = 30,
  stdoutLines = [
    { text: '[INIT] Inspecting target database connection string...', type: 'info' },
    { text: '[AST] Parsing command syntax tree for destructive mutations...', type: 'warning' },
    { text: '[BLOCK] Destructive mutation detected on production branch', type: 'error' },
    { text: '+ Security rule enforced inside the tool boundary', type: 'success' },
  ],
  refusalBadge = 'REFUSED: DROP TABLE BLOCKED',
  isRefusal = true,
  badge = 'LIVE CLI SIMULATION',
  title = 'TERMINAL EXECUTION & RULE REFUSAL',
  subtitle = 'Deterministic Tool-Level Safety Guardrails',
  source = 'Source: Live Tool Execution Trace',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring for main container
  const entrySpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.snappy,
  });

  // Calculate typed command characters
  const rawCommand = command.startsWith('$ ') ? command.slice(2) : command;
  const charsCount = Math.floor(
    interpolate(frame, [10, 10 + typingDurationFrames], [0, rawCommand.length], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    })
  );
  const visibleCommand = rawCommand.slice(0, charsCount);
  const isTypingDone = frame >= 10 + typingDurationFrames;

  // Blinking cursor (toggles every 8 frames)
  const showCursor = Math.floor(frame / 8) % 2 === 0;

  // Refusal banner spring pop (triggers after stdout lines stream)
  const refusalSpring = spring({
    frame: Math.max(0, frame - (10 + typingDurationFrames + 20)),
    fps,
    config: SPRING_PRESETS.bouncy,
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
        <CardHeader badge={badge} title={title} subtitle={subtitle} />
      </div>

      {/* Terminal Window Container */}
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
            borderRadius: 24,
            border: isRefusal && frame > 45
              ? `2px solid ${THEME.colors.red}`
              : '1px solid rgba(0, 242, 254, 0.35)',
            backgroundColor: 'rgba(11, 15, 25, 0.94)',
            backdropFilter: 'blur(20px)',
            boxShadow: isRefusal && frame > 45
              ? '0 25px 60px -15px rgba(255, 0, 85, 0.4), 0 0 35px rgba(255, 0, 85, 0.3)'
              : '0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 35px rgba(0, 242, 254, 0.25)',
            overflow: 'hidden',
            padding: '32px 36px',
            boxSizing: 'border-box',
            transition: 'border 0.2s ease, box-shadow 0.2s ease',
          }}
        >
          {/* Terminal Title Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(0, 242, 254, 0.15)',
              paddingBottom: 18,
              marginBottom: 24,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: '#FF5F56' }} />
              <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: '#FFBD2E' }} />
              <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: '#27C93F' }} />
              <span
                style={{
                  fontFamily: THEME.fonts.mono,
                  fontSize: 16,
                  color: 'rgba(180, 195, 215, 0.8)',
                  marginLeft: 12,
                }}
              >
                bash — sandbox_cli@production
              </span>
            </div>
            <div
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                backgroundColor: 'rgba(57, 255, 20, 0.12)',
                border: '1px solid rgba(57, 255, 20, 0.3)',
                color: THEME.colors.neonGreen,
                fontFamily: THEME.fonts.mono,
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              ACTIVE TTY
            </div>
          </div>

          {/* Prompt & Command Typing */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              fontFamily: THEME.fonts.mono,
              fontSize: 24,
              fontWeight: 700,
              color: '#FFFFFF',
              marginBottom: 24,
            }}
          >
            <span style={{ color: THEME.colors.cyan, marginRight: 12 }}>$&nbsp;</span>
            <span>{visibleCommand}</span>
            {showCursor && (
              <span style={{ color: THEME.colors.neonGreen, marginLeft: 4 }}>▋</span>
            )}
          </div>

          {/* Stdout Logs Stream */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
              fontFamily: THEME.fonts.mono,
              fontSize: 19,
              lineHeight: 1.4,
              marginBottom: 20,
            }}
          >
            {stdoutLines.map((line, idx) => {
              const lineDelay = 10 + typingDurationFrames + idx * 7;
              if (frame < lineDelay) return null;

              let color = '#DCE1EB';
              if (line.type === 'error' || line.text.includes('BLOCK') || line.text.includes('FAIL')) {
                color = THEME.colors.red;
              } else if (line.type === 'success' || line.text.startsWith('+')) {
                color = THEME.colors.neonGreen;
              } else if (line.type === 'warning' || line.text.includes('AST')) {
                color = THEME.colors.yellow;
              } else if (line.type === 'info' || line.text.includes('INIT')) {
                color = THEME.colors.cyan;
              }

              return (
                <div key={idx} style={{ color }}>
                  {line.text}
                </div>
              );
            })}
          </div>

          {/* Refusal Alert Banner */}
          {isRefusal && frame >= 10 + typingDurationFrames + 20 && (
            <div
              style={{
                marginTop: 20,
                transform: `scale(${refusalSpring})`,
                backgroundColor: 'rgba(255, 0, 85, 0.16)',
                border: `2px solid ${THEME.colors.red}`,
                borderRadius: 14,
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <span style={{ fontSize: 28 }}>🚨</span>
                <div>
                  <div
                    style={{
                      fontFamily: THEME.fonts.title,
                      fontWeight: 800,
                      fontSize: 19,
                      color: '#FFFFFF',
                      letterSpacing: '0.3px',
                    }}
                  >
                    {refusalBadge}
                  </div>
                  <div
                    style={{
                      fontFamily: THEME.fonts.mono,
                      fontSize: 14,
                      color: 'rgba(255, 255, 255, 0.75)',
                      marginTop: 2,
                    }}
                  >
                    Rule enforced inside the tool boundary
                  </div>
                </div>
              </div>
              <div
                style={{
                  backgroundColor: THEME.colors.red,
                  color: '#FFFFFF',
                  fontFamily: THEME.fonts.mono,
                  fontWeight: 800,
                  fontSize: 13,
                  padding: '6px 12px',
                  borderRadius: 6,
                }}
              >
                BLOCKED
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
