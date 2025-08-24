#!/usr/bin/env node
/**
 * Prunes node_modules and extra resources to macOS-only content.
 * - Keeps darwin/* (arm64 + universal by default)
 * - Removes 
 * - Drops .exe/.dll/.pdb and other obviously non-mac artifacts
 * - Optionally trims tests/docs/maps to shrink size further
 *
 * Usage:
 *   node scripts/prune-macos.js --appDir=. --arch=arm64 --aggressive
 */

const fs = require('fs');
const fsp = fs.promises;
const path = require('path');

const args = Object.fromEntries(
  process.argv.slice(2).map(a => {
    const m = a.match(/^--([^=]+)(=(.*))?$/);
    return m ? [m[1], m[3] ?? true] : [a, true];
  })
);

const APP_DIR = path.resolve(args.appDir || '.');
const ARCH = (args.arch || 'arm64').toLowerCase();
const AGGRESSIVE = Boolean(args.aggressive); // also remove docs/tests/maps

const NM = path.join(APP_DIR, 'node_modules');
const RES_BIN = path.join(APP_DIR, 'resources', 'bin');

// Platforms we *never* need inside a mac app
const NON_MAC_PLAT_DIRS = [
  'win', 'win32', 'windows',
  'linux', 'freebsd', 'openbsd', 'netbsd',
  'android', 'aix', 'sunos'
];

// Keep these darwin subdirs; drop others (e.g., darwin-x64 if you ship arm64-only)
const KEEP_DARWIN = new Set([
  `darwin-${ARCH}`,
  'darwin-universal',
  'darwin', // some packages just use "darwin"
]);

// File extensions that are definitely not needed on macOS
const EXT_REMOVE_ALWAYS = new Set(['.exe', '.dll', '.pdb']);

// Aggressive trimming (optional; safe for runtime but removes dev assets)
const AGGRESSIVE_PATTERNS = [
  'test', 'tests', '__tests__', '__mocks__',
  'example', 'examples', 'docs', 'doc'
];

async function exists(p) {
  try { await fsp.access(p); return true; } catch { return false; }
}

async function walk(dir, onEntry) {
  const st = await fsp.lstat(dir);
  if (!st.isDirectory()) return;
  const entries = await fsp.readdir(dir);
  for (const e of entries) {
    const p = path.join(dir, e);
    let s;
    try { s = await fsp.lstat(p); } catch { continue; }
    await onEntry(p, s);
    if (s.isDirectory() && !s.isSymbolicLink()) {
      await walk(p, onEntry);
    }
  }
}

async function rmrf(p) {
  try { await fsp.rm(p, { recursive: true, force: true }); }
  catch { /* ignore */ }
}

function shouldRemoveByPlatform(p) {
  const parts = p.split(path.sep).map(s => s.toLowerCase());

  // remove explicit non-mac platform dirs
  if (parts.some(seg => NON_MAC_PLAT_DIRS.includes(seg))) return true;

  // inside prebuilds/build/bin/vendor/... keep only darwin allowed variants
  // e.g., prebuilds/darwin-arm64, prebuilds/win32-x64, prebuilds/linux-x64
  const maybePlatformish = ['prebuilds', 'build', 'bin', 'vendor', 'binaries', 'native', 'dist'];
  const idx = parts.findIndex(seg => maybePlatformish.includes(seg));
  if (idx >= 0) {
    const rest = parts.slice(idx + 1).join('/');
    // If rest mentions darwin-*, keep only if in KEEP_DARWIN
    const m = rest.match(/darwin(?:-universal|-x64|-arm64)?/);
    if (m) {
      const tag = m[0].toLowerCase();
      if (!KEEP_DARWIN.has(tag)) return true; // e.g., darwin-x64 when arch=arm64
      return false;
    }
    // If rest mentions another OS/arch, drop it
    if (/(linux|win|windows|freebsd|openbsd|netbsd|android|aix|sunos)/.test(rest)) return true;
  }
  return false;
}

function shouldRemoveByExt(p) {
  const ext = path.extname(p).toLowerCase();
  if (EXT_REMOVE_ALWAYS.has(ext)) return true;
  // Remove .so files that are clearly in a linux/ non-darwin subtree
  if (ext === '.so' && /(^|\/)(linux|freebsd|openbsd|netbsd|android)\b/i.test(p)) return true;
  return false;
}

function isAggressiveTrash(p) {
  const name = path.basename(p).toLowerCase();
  if (AGGRESSIVE_PATTERNS.includes(name)) return true;
  // Remove .map files
  if (name.endsWith('.map')) return true;
  // Keep license/notice to stay compliant
  if (name === 'license' || name === 'license.md' || name === 'notice' || name === 'notice.md') return false;
  // Most README/CHANGELOG can go
  if (/^(readme|changelog)(\..*)?$/.test(name)) return true;
  // Drop markdown in node_modules (safe)
  if (name.endsWith('.md')) return true;
  return false;
}

async function pruneTree(root) {
  if (!(await exists(root))) return { removed: 0, scanned: 0 };
  let removed = 0, scanned = 0;

  await walk(root, async (p, stat) => {
    scanned++;
    const rel = p.slice(root.length + 1);
    if (!rel) return;

    // Directories: decide early
    if (stat.isDirectory()) {
      if (shouldRemoveByPlatform(rel)) {
        await rmrf(p); removed++; return;
      }
      if (AGGRESSIVE && isAggressiveTrash(p)) {
        await rmrf(p); removed++; return;
      }
      return;
    }

    // Files:
    if (shouldRemoveByExt(rel)) {
      await rmrf(p); removed++; return;
    }
    if (AGGRESSIVE && isAggressiveTrash(rel)) {
      await rmrf(p); removed++; return;
    }
  });

  return { removed, scanned };
}

(async () => {
  console.log(`[prune-macos] appDir=${APP_DIR} arch=${ARCH} aggressive=${AGGRESSIVE}`);
  let totalRemoved = 0, totalScanned = 0;

  // 1) node_modules
  if (await exists(NM)) {
    const { removed, scanned } = await pruneTree(NM);
    totalRemoved += removed; totalScanned += scanned;
  }

  // 2) resources/bin — keep only mac-arm64 subtree
  if (await exists(RES_BIN)) {
    // delete sibling platform dirs
    const entries = await fsp.readdir(RES_BIN).catch(() => []);
    for (const e of entries) {
      const p = path.join(RES_BIN, e);
      const name = e.toLowerCase();
      const st = await fsp.lstat(p);
      if (!st.isDirectory()) continue;

      const keep = (name === `mac-${ARCH}`) || (name === 'darwin') || (name === 'darwin-universal') || (name === 'macos') || (name === 'universal');
      if (!keep) {
        await rmrf(p); totalRemoved++;
      }
    }
    // also nuke obvious non-mac binaries in bin root
    const files = await fsp.readdir(RES_BIN).catch(() => []);
    for (const f of files) {
      const p = path.join(RES_BIN, f);
      if ((/\.(exe|dll|pdb)$/i).test(f)) { await rmrf(p); totalRemoved++; }
    }
  }

  console.log(`[prune-macos] scanned=${totalScanned} removed=${totalRemoved}`);
})().catch(err => {
  console.error(`[prune-macos] ERROR`, err);
  process.exit(1);
});
