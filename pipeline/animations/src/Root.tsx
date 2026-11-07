import React from 'react';
import { Composition } from 'remotion';
import { BenchmarkLadder, BenchmarkLadderProps } from './compositions/BenchmarkLadder';
import { ArchitectureDiagram, ArchitectureDiagramProps } from './compositions/ArchitectureDiagram';
import { KineticMetricCounter, KineticMetricCounterProps } from './compositions/KineticMetricCounter';
import { TweetCard3D, TweetCard3DProps } from './compositions/TweetCard3D';
import { PersistentHookBanner, PersistentHookBannerProps } from './compositions/PersistentHookBanner';
import { DocumentZoom, DocumentZoomProps } from './compositions/DocumentZoom';
import { TerminalRunner, TerminalRunnerProps } from './compositions/TerminalRunner';
import { StopwatchTicker, StopwatchTickerProps } from './compositions/StopwatchTicker';
import { GrowthPill, GrowthPillProps } from './compositions/GrowthPill';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition<BenchmarkLadderProps>
        id="BenchmarkLadder"
        component={BenchmarkLadder}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<ArchitectureDiagramProps>
        id="ArchitectureDiagram"
        component={ArchitectureDiagram}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<KineticMetricCounterProps>
        id="KineticMetricCounter"
        component={KineticMetricCounter}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<TweetCard3DProps>
        id="TweetCard3D"
        component={TweetCard3D}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<PersistentHookBannerProps>
        id="PersistentHookBanner"
        component={PersistentHookBanner}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<DocumentZoomProps>
        id="DocumentZoom"
        component={DocumentZoom}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<TerminalRunnerProps>
        id="TerminalRunner"
        component={TerminalRunner}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<StopwatchTickerProps>
        id="StopwatchTicker"
        component={StopwatchTicker}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
      <Composition<GrowthPillProps>
        id="GrowthPill"
        component={GrowthPill}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
    </>
  );
};
