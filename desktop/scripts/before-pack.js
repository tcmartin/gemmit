// scripts/before-pack.js
const { spawnSync } = require('child_process');

module.exports = async function beforePack(context) {
  // Best-effort arch detection; default to arm64 (your current target)
  const arch = process.env.PRUNE_ARCH || 'arm64';
  const appDir = context.appDir;

  console.log(`[before-pack] pruning for macOS ${arch} in ${appDir}`);
  const r = spawnSync(process.execPath, [
    'scripts/prune-macos.js',
    `--appDir=${appDir}`,
    `--arch=${arch}`,
    ...(process.env.PRUNE_AGGRESSIVE ? ['--aggressive'] : [])
  ], { stdio: 'inherit' });

  if (r.status !== 0) {
    throw new Error(`prune-macos failed (exit ${r.status})`);
  }
};
