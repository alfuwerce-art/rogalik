// Pre-install smoke test: exercise both local plugins with a stub Cordis context.
// Run inside the repository:  node plugins/_selftest.mjs
//
// External processes are spawned by the plugin. Inside a confined shell the DSH
// sandbox rejects spawn with piped stdio (EPERM), so this harness reports that
// condition instead of failing: the same code runs unsandboxed in the Host.
import assert from 'node:assert/strict';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

function stubCtx() {
  const registered = [];
  return {
    registered,
    effect(factory) {
      factory();
    },
    tools: {
      register(definition) {
        registered.push(definition);
        return () => {};
      },
    },
  };
}

const load = (relative) => import(pathToFileURL(join(here, relative)).href);

/** The harness rejects tool output that JSON cannot round-trip (lone surrogates). */
function assertLossless(value, label) {
  const text = JSON.stringify(value);
  assert.deepEqual(JSON.parse(text), value, `${label}: JSON round-trip changed the value`);
  assert.ok(
    !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(text),
    `${label}: output contains a lone surrogate`,
  );
}

// A real Windows console message with broken Cyrillic decoding.
const mojibake = 'РћС€РёР±РєР°: \uFFFD\uD800 path';
for (const [label, relative] of [
  ['env-check', 'rogalik-env-check/index.js'],
  ['pipeline', 'rogalik-pixel-pipeline/index.js'],
]) {
  const mod = await load(relative);
  assert.equal(typeof mod.toJsonValue, 'function', `${label}: toJsonValue exported`);
  const clean = mod.toJsonValue({ ok: true, note: mojibake, missing: undefined });
  assertLossless(clean, `${label} sanitised output`);
  assert.equal(clean.missing, undefined, `${label}: undefined keys dropped`);
  assert.ok(!clean.note.includes('\uD800'), `${label}: lone surrogate replaced`);
}

function sandboxBlocked(entry) {
  const text = String(entry?.probeError ?? entry?.problems?.join(' ') ?? '');
  return /EPERM|EACCES|spawn/i.test(text);
}

let exitCode = 0;

// --- rogalik-env-check ---------------------------------------------------
{
  const mod = await load('rogalik-env-check/index.js');
  const ctx = stubCtx();
  mod.apply(ctx, { workspace: process.env.ROGALIK_WORKSPACE ?? process.cwd() });
  assert.equal(ctx.registered.length, 1, 'env-check registers exactly one tool');
  const tool = ctx.registered[0];
  assert.equal(tool.name, 'rogalik_env_check');

  const result = await tool.execute({ deep: false });
  assertLossless(result, 'env-check result');
  console.log('[env-check] status:', result.status);
  for (const [key, value] of Object.entries(result.report.tools)) {
    console.log(
      `[env-check] ${key}:`,
      value.found ? `${value.version ?? 'version unknown'} ${value.path ?? ''}` : `MISSING ${value.reason ?? ''}`,
    );
  }
  for (const entry of result.report.workspace.entries) {
    console.log(`[env-check] ${entry.key}: ${entry.exists ? 'ok' : 'MISSING'} ${entry.path}`);
  }
  assert.ok(['PASS', 'FAIL'].includes(result.status));
  assert.ok(result.report.tools.godot, 'godot entry present');
  assert.ok(result.report.tools.pixelorama?.path, 'pixelorama path present');
  assert.match(tool.output.render({}, result)[0].text, /Rogalik environment/);

  if (result.status === 'FAIL') {
    const godot = result.report.tools.godot;
    if (sandboxBlocked(godot) || sandboxBlocked(result.report.tools.git)) {
      console.log('[env-check] external version probes blocked by the shell sandbox (expected).');
    } else {
      console.error('[env-check] unexpected FAIL outside the sandbox');
      exitCode = 1;
    }
  }
}

// --- rogalik-pixel-pipeline ---------------------------------------------
{
  const mod = await load('rogalik-pixel-pipeline/index.js');
  const ctx = stubCtx();
  mod.apply(ctx, {
    workspace: process.env.ROGALIK_WORKSPACE ?? process.cwd(),
    pythonPath: process.env.ROGALIK_PYTHON,
  });
  const tool = ctx.registered[0];
  assert.equal(tool.name, 'rogalik_pixel_pipeline');

  const check = await tool.execute({
    action: 'check',
    path: 'game/prototype/art/sprites/hero_walk.png',
    frame: 32,
    frames: 4,
  });
  assertLossless(check, 'pipeline result');
  console.log('[pipeline] status:', check.status, '| problems:', JSON.stringify(check.problems));
  if (check.status === 'PASS') {
    console.log(
      '[pipeline] frames:',
      check.report.metrics.frames,
      '| frame size:',
      `${check.report.metrics.frame_width}x${check.report.metrics.frame_height}`,
    );
    assert.equal(check.report.status, 'PASS');
  } else if (check.problems.some((problem) => /EPERM|spawn/i.test(problem))) {
    console.log('[pipeline] python spawn blocked by the shell sandbox (expected).');
  } else {
    exitCode = 1;
  }
}

process.exit(exitCode);

