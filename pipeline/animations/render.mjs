#!/usr/bin/env node
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import { fileURLToPath } from 'url';
import { bundle } from '@remotion/bundler';
import { selectComposition, renderMedia } from '@remotion/renderer';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getFilesRecursively(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getFilesRecursively(fullPath));
    } else {
      results.push(fullPath);
    }
  }
  return results;
}

function computeSrcHash() {
  const hash = crypto.createHash('md5');
  const srcDir = path.join(__dirname, 'src');
  if (fs.existsSync(srcDir)) {
    const files = getFilesRecursively(srcDir).sort();
    for (const f of files) {
      hash.update(path.relative(srcDir, f));
      hash.update(fs.readFileSync(f));
    }
  }
  const pkgFile = path.join(__dirname, 'package.json');
  if (fs.existsSync(pkgFile)) {
    hash.update(fs.readFileSync(pkgFile));
  }
  return hash.digest('hex');
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    composition: null,
    props: {},
    out: null,
    durationInFrames: null,
    fps: 30,
    crf: 18,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--composition' && i + 1 < args.length) {
      options.composition = args[++i];
    } else if (arg === '--props' && i + 1 < args.length) {
      const val = args[++i];
      if (fs.existsSync(val)) {
        options.props = JSON.parse(fs.readFileSync(val, 'utf8'));
      } else {
        options.props = JSON.parse(val);
      }
    } else if (arg === '--out' && i + 1 < args.length) {
      options.out = args[++i];
    } else if (arg === '--durationInFrames' && i + 1 < args.length) {
      options.durationInFrames = parseInt(args[++i], 10);
    } else if (arg === '--fps' && i + 1 < args.length) {
      options.fps = parseInt(args[++i], 10);
    } else if (arg === '--crf' && i + 1 < args.length) {
      options.crf = parseInt(args[++i], 10);
    }
  }

  if (!options.composition) {
    console.error('Error: --composition is required');
    process.exit(1);
  }
  if (!options.out) {
    console.error('Error: --out is required');
    process.exit(1);
  }

  return options;
}

async function main() {
  const opts = parseArgs();
  const entryPoint = path.join(__dirname, 'src', 'index.ts');

  if (!fs.existsSync(entryPoint)) {
    console.error(`Error: Entry point not found: ${entryPoint}`);
    process.exit(1);
  }

  // Ensure output directory exists
  const outDir = path.dirname(path.resolve(opts.out));
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  // Webpack Bundle Caching (Phase 7):
  // Eliminates 4-8s of redundant compilation per animation shot
  const srcHash = computeSrcHash();
  const cacheBaseDir = path.join(__dirname, '.remotion_bundle_cache');
  const cachedBundleDir = path.join(cacheBaseDir, srcHash);

  let bundleLocation;
  if (fs.existsSync(path.join(cachedBundleDir, 'index.html'))) {
    console.log(`[Remotion] Using pre-bundled Webpack cache (${srcHash.slice(0, 8)})...`);
    bundleLocation = cachedBundleDir;
  } else {
    console.log(`[Remotion] Bundling composition entry point (fresh cache ${srcHash.slice(0, 8)})...`);
    fs.mkdirSync(cachedBundleDir, { recursive: true });
    bundleLocation = await bundle({
      entryPoint,
      outDir: cachedBundleDir,
    });
  }

  console.log(`[Remotion] Selecting composition '${opts.composition}'...`);
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: opts.composition,
    inputProps: opts.props,
  });

  if (!composition) {
    console.error(`Error: Composition '${opts.composition}' not found`);
    process.exit(1);
  }

  // Override duration if specified
  if (opts.durationInFrames) {
    composition.durationInFrames = opts.durationInFrames;
  }
  if (opts.fps) {
    composition.fps = opts.fps;
  }

  console.log(
    `[Remotion] Rendering ${opts.composition} (${composition.width}x${composition.height} @ ${composition.fps}fps, ${composition.durationInFrames} frames) -> ${opts.out}`
  );

  const chromiumArgs = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];

  // Check if downloaded chrome-headless-shell exists
  const localHeadlessShell = path.join(
    __dirname,
    'node_modules',
    '.remotion',
    'chrome-headless-shell',
    'linux64',
    'chrome-headless-shell-linux64',
    'chrome-headless-shell'
  );

  const chromiumOptions = {
    args: chromiumArgs,
  };

  if (fs.existsSync(localHeadlessShell)) {
    chromiumOptions.executablePath = localHeadlessShell;
  } else if (fs.existsSync('/usr/bin/chromium')) {
    chromiumOptions.executablePath = '/usr/bin/chromium';
  }

  let lastReportedPercent = -1;

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: 'h264',
    crf: opts.crf,
    outputLocation: path.resolve(opts.out),
    inputProps: opts.props,
    chromiumOptions,
    onProgress: ({ renderedFrames, totalFrames }) => {
      const percent = Math.floor((renderedFrames / totalFrames) * 100);
      if (percent % 25 === 0 && percent !== lastReportedPercent) {
        lastReportedPercent = percent;
        console.log(`[Remotion Progress] ${percent}% (${renderedFrames}/${totalFrames} frames)`);
      }
    },
  });

  console.log(`[Remotion Complete] Rendered -> ${opts.out}`);
}

main().catch((err) => {
  console.error('[Remotion Error]', err);
  process.exit(1);
});
