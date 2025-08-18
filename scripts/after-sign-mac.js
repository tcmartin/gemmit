// scripts/after-sign-mac.js
const { signAsync } = require('electron-osx-sign');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: 'pipe', ...opts });
  if (r.status !== 0) {
    const out = (r.stdout || '').toString();
    const err = (r.stderr || '').toString();
    throw new Error(`${cmd} ${args.join(' ')} failed (${r.status})\n${out}${err}`);
  }
  return (r.stdout || '').toString();
}

function listFiles(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir)) {
    const p = path.join(dir, e);
    const st = fs.lstatSync(p);
    if (st.isSymbolicLink()) continue;
    if (st.isDirectory()) out.push(...listFiles(p));
    else out.push(p);
  }
  return out;
}

function isMachO(p) {
  try { return run('file', ['-b', p]).includes('Mach-O'); }
  catch { return false; }
}

module.exports = async function afterSign(context) {
  const appOutDir = context.appOutDir;
  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);
  const contents = path.join(appPath, 'Contents');

  // Folders where Mach-O files often live:
  const candidates = [
    path.join(contents, 'MacOS'),
    path.join(contents, 'Frameworks'),
    path.join(contents, 'Resources'),
    path.join(contents, 'Resources', 'app.asar.unpacked'),
  ];

  // Collect all files
  let files = [];
  for (const c of candidates) files.push(...listFiles(c));
  files = files.filter(isMachO);

  // Remove quarantine attributes if they slipped in
  try { run('xattr', ['-r', '-d', 'com.apple.quarantine', appPath]); } catch {}

  const identity = process.env.CSC_NAME || 'Developer ID Application';

  // Sign each Mach-O individually
  for (const f of files) {
    try { fs.chmodSync(f, 0o755); } catch {}
    run('codesign', [
      '--force',
      '--options', 'runtime',
      '--timestamp',
      '--sign', identity,
      f
    ]);
  }

  // Re-sign the .app bundle to include everything
  await signAsync({
    app: appPath,
    identity,
    'hardened-runtime': true,
    entitlements: path.join(process.cwd(), 'build', 'entitlements.mac.plist'),
    'entitlements-inherit': path.join(process.cwd(), 'build', 'entitlements.mac.plist'),
    'signature-flags': 'library',
  });
};
