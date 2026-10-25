/**
 * rogalik-env-check вЂ” read-only diagnostics for the Rogalik game-dev environment.
 *
 * Registers one Host tool, `rogalik_env_check`, that reports the real Godot,
 * Pixelorama, Git and Python versions plus the state of the Rogalik checkout.
 * It never writes to the workspace, never reads tokens or dotfiles, and never
 * installs anything.
 *
 * Version probes run external binaries. Pixelorama needs a writable `user://`
 * directory, so the probe points `APPDATA` at a temporary folder instead of the
 * user's real Pixelorama profile, and the result is cached for the process.
 */

import { execFile } from 'node:child_process';
import { existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';

const runFile = promisify(execFile);

export const name = 'rogalik-env-check';
export const inject = ['tools'];

const DEFAULT_WORKSPACE = 'C:\\Users\\bow\\Desktop\\Rogalik';

const WINGET_GODOT_DIR =
  'C:\\Users\\bow\\AppData\\Local\\Microsoft\\WinGet\\Packages\\' +
  'GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe';

const GODOT_CANDIDATES = [
  join(WINGET_GODOT_DIR, 'Godot_v4.7.2-stable_win64_console.exe'),
  join(WINGET_GODOT_DIR, 'Godot_v4.7.2-stable_win64.exe'),
];

const PIXELORAMA_CANDIDATES = [
  'C:\\Users\\bow\\AppData\\Roaming\\Orama Interactive\\Pixelorama\\Pixelorama.exe',
  'C:\\Program Files\\Pixelorama\\Pixelorama.exe',
];

const PYTHON_CANDIDATES = [
  'C:\\Users\\bow\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe',
  'C:\\Users\\bow\\AppData\\Local\\Programs\\Python\\Python313\\python.exe',
];

const cache = new Map();

async function probe(file, args, options = {}) {
  try {
    const { stdout, stderr } = await runFile(file, args, {
      timeout: options.timeout ?? 20000,
      windowsHide: true,
      env: { ...process.env, ...(options.env ?? {}) },
      maxBuffer: 4 * 1024 * 1024,
    });
    return { ok: true, stdout: stdout ?? '', stderr: stderr ?? '', code: 0 };
  } catch (error) {
    return {
      ok: false,
      stdout: String(error?.stdout ?? ''),
      stderr: String(error?.stderr ?? error?.message ?? error),
      code: typeof error?.code === 'number' ? error.code : null,
    };
  }
}

async function cached(key, factory) {
  if (!cache.has(key)) cache.set(key, await factory());
  return cache.get(key);
}

function firstExisting(candidates) {
  for (const candidate of candidates) {
    if (candidate && existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }
  return null;
}

function parseVersion(text, pattern = /\d+\.\d+(?:\.\d+)?(?:[.\w-]*)?/) {
  const match = String(text).match(pattern);
  return match ? match[0] : null;
}

/**
 * Build a value the harness can serialise losslessly.
 *
 * External tools print Windows console bytes that are not valid UTF-8, which
 * JavaScript turns into lone surrogates; those break strict JSON round-trips.
 * `JSON.stringify` also drops `undefined` keys, so the result is a clean tree.
 */
export function toJsonValue(value) {
  return JSON.parse(
    JSON.stringify(value, (_key, current) =>
      typeof current === 'string' ? current.toWellFormed() : current,
    ),
  );
}

async function checkGodot(config) {
  const path =
    firstExisting([config.godotPath, ...GODOT_CANDIDATES]) ??
    (await cached('godot-which', async () => {
      const probeResult = await probe('godot', ['--version'], { timeout: 15000 });
      return probeResult.ok ? 'godot' : null;
    }));
  if (!path) return { found: false, reason: 'Godot executable not found' };

  const result = await cached(`godot-version:${path}`, () => probe(path, ['--headless', '--version']));
  const text = `${result.stdout}\n${result.stderr}`;
  return {
    found: true,
    path,
    version: parseVersion(text),
    raw: text.trim().split('\n').filter(Boolean).slice(-1)[0] ?? null,
    ok: result.ok,
    probeError: result.ok ? undefined : result.stderr.trim().split('\n')[0] || 'probe failed',
  };
}

async function checkPixelorama(config, deep) {
  const path = firstExisting([config.pixeloramaPath, ...PIXELORAMA_CANDIDATES]);
  if (!path) return { found: false, reason: 'Pixelorama executable not found' };
  if (!deep) return { found: true, path, version: null, note: 'version probe skipped (deep=false)' };

  return cached(`pixelorama-version:${path}`, async () => {
    const result = await probe(path, ['--headless', '--quit', '--', '--version'], {
      timeout: 45000,
      env: { APPDATA: join(tmpdir(), 'rogalik-env-check-pixelorama') },
    });
    const text = `${result.stdout}\n${result.stderr}`;
    const versionLine = text.match(/v?\d+\.\d+\.\d+-stable/i);
    return {
      found: true,
      path,
      version: versionLine ? versionLine[0] : parseVersion(text),
      ok: result.ok,
    };
  });
}

async function checkGit() {
  return cached('git-version', async () => {
    const result = await probe('git', ['--version'], { timeout: 15000 });
    return result.ok
      ? { found: true, version: parseVersion(result.stdout), raw: result.stdout.trim() }
      : { found: false, reason: result.stderr.trim() || 'git not available' };
  });
}

async function checkPython(config) {
  const path = firstExisting([config.pythonPath, ...PYTHON_CANDIDATES]);
  if (!path) {
    const result = await probe('python', ['--version'], { timeout: 15000 });
    return result.ok
      ? { found: true, path: 'python', version: parseVersion(result.stdout) }
      : { found: false, reason: 'python not found' };
  }
  const result = await probe(path, ['--version'], { timeout: 15000 });
  return {
    found: result.ok,
    path,
    version: parseVersion(`${result.stdout}${result.stderr}`),
  };
}

function checkWorkspace(workspace) {
  const checks = [
    ['directory', workspace, 'Rogalik checkout'],
    ['.git', join(workspace, '.git'), 'git repository'],
    ['task', join(workspace, 'docs', 'tasks', 'DSH_PLUGIN_BOOTSTRAP.md'), 'bootstrap task document'],
    ['godot_project', join(workspace, 'game', 'prototype', 'project.godot'), 'Godot test project'],
    ['pipeline', join(workspace, 'tools', 'pixel_pipeline', 'cli.py'), 'pixel pipeline CLI'],
    ['plugins', join(workspace, 'plugins'), 'local plugin bundles'],
  ];
  const entries = checks.map(([key, path, label]) => ({
    key,
    label,
    path,
    exists: existsSync(path),
  }));
  return {
    path: workspace,
    exists: existsSync(workspace),
    entries,
    ok: entries.every((entry) => entry.exists),
  };
}

export function apply(ctx, config = {}) {
  const settings = {
    workspace: config.workspace ?? process.env.ROGALIK_WORKSPACE ?? DEFAULT_WORKSPACE,
    godotPath: config.godotPath,
    pixeloramaPath: config.pixeloramaPath,
    pythonPath: config.pythonPath,
  };

  ctx.effect(() =>
    ctx.tools.register({
      name: 'rogalik_env_check',
      description:
        'Report the real Rogalik development environment: Godot and Pixelorama versions and paths, ' +
        'Git and Python, and whether the Rogalik checkout, Godot test project and pixel pipeline exist. ' +
        'Read-only; it never installs, edits or reads credentials.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          deep: {
            type: 'boolean',
            description:
              'Run the Pixelorama version probe (starts Pixelorama headless, ~3 s). Default true.',
          },
          workspace: {
            type: 'string',
            description: 'Rogalik checkout to inspect. Defaults to the configured workspace.',
          },
        },
      },
      output: {
        schema: {
          type: 'object',
          additionalProperties: true,
          properties: {
            status: { type: 'string', enum: ['PASS', 'FAIL'] },
            workspace: { type: 'string' },
            report: { type: 'object', additionalProperties: true },
          },
        },
        render: (_args, value) => {
          const lines = [`Rogalik environment: ${value.status}`];
          for (const [tool, info] of Object.entries(value.report?.tools ?? {})) {
            lines.push(
              info.found
                ? `  ${tool}: ${info.version ?? 'version unknown'}${info.path ? ` (${info.path})` : ''}`
                : `  ${tool}: MISSING - ${info.reason ?? 'not found'}`,
            );
          }
          const entries = value.report?.workspace?.entries ?? [];
          for (const entry of entries) {
            lines.push(`  ${entry.key}: ${entry.exists ? 'ok' : 'MISSING'} (${entry.path})`);
          }
          return [{ type: 'text', text: lines.join('\n') }];
        },
      },
      async execute(args) {
        const deep = args?.deep !== false;
        const workspace = args?.workspace ?? settings.workspace;
        const [godot, pixelorama, git, python] = await Promise.all([
          checkGodot(settings),
          checkPixelorama(settings, deep),
          checkGit(),
          checkPython(settings),
        ]);
        const workspaceReport = checkWorkspace(workspace);
        const required = [godot.found, pixelorama.found, git.found, workspaceReport.ok];
        const status = required.every(Boolean) ? 'PASS' : 'FAIL';
        return toJsonValue({
          status,
          workspace,
          generatedAt: new Date().toISOString(),
          report: {
            status,
            tools: { godot, pixelorama, git, python },
            workspace: workspaceReport,
            notes: [
              'Versions come from executing each binary, not from configuration files.',
              'Pixelorama runs with a temporary APPDATA so the real user profile is untouched.',
            ],
          },
        });
      },
      presentCall: () => ({ card: 'generic', title: 'Check Rogalik environment', kind: 'other' }),
    }),
  );
}

