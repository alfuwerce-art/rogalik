/**
 * rogalik-pixel-pipeline вЂ” one Host tool over the `tools/pixel_pipeline` CLI.
 *
 * Actions:
 *   check  - validate a PNG, a sprite sheet or a tileset (PASS/FAIL + metrics)
 *   build  - build a Pixelorama .pxo project from an RGBA sprite sheet
 *   export - export a .pxo to PNG frames or one sprite sheet via Pixelorama's CLI
 *   atlas  - pack a sheet into an atlas plus Godot-friendly JSON metadata
 *   demo   - run the whole chain on the generated placeholder sprite
 *
 * The heavy lifting lives in Python (Pillow) and in the real Pixelorama binary;
 * this plugin only validates arguments, runs the CLI and surfaces its report.
 */

import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { promisify } from 'node:util';

const runFile = promisify(execFile);

export const name = 'rogalik-pixel-pipeline';
export const inject = ['tools'];

const DEFAULT_WORKSPACE = 'C:\\Users\\bow\\Desktop\\Rogalik';
const DEFAULT_PYTHON =
  'C:\\Users\\bow\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe';

const ACTIONS = ['check', 'build', 'export', 'atlas', 'demo'];

function buildArgs(args) {
  const action = args?.action;
  const argv = [];

  if (action === 'check') {
    if (!args.path) throw new Error('check requires `path`');
    argv.push('check', args.path);
    if (args.tile) argv.push('--tile', String(args.tile));
    else if (args.frame) {
      argv.push('--frame', String(args.frame));
      if (args.frameHeight) argv.push('--frame-height', String(args.frameHeight));
      if (args.frames) argv.push('--frames', String(args.frames));
    }
    argv.push('--as-json');
    if (args.json) argv.push('--json', args.json);
    return argv;
  }

  if (action === 'build') {
    if (!args.sheet || !args.out || !args.frame) {
      throw new Error('build requires `sheet`, `out` and `frame`');
    }
    argv.push('build', args.out, '--sheet', args.sheet, '--frame', String(args.frame));
    if (args.fps) argv.push('--fps', String(args.fps));
    if (args.tag) argv.push('--tag', args.tag);
    return argv;
  }

  if (action === 'export') {
    if (!args.project || !args.out) throw new Error('export requires `project` and `out`');
    argv.push('export', args.project, '--out', args.out);
    if (args.spritesheet) argv.push('--sheet');
    if (args.scale) argv.push('--scale', String(args.scale));
    if (args.name) argv.push('--name', args.name);
    return argv;
  }

  if (action === 'atlas') {
    if (!args.sheet || !args.out || !args.frame) {
      throw new Error('atlas requires `sheet`, `out` and `frame`');
    }
    argv.push('atlas', args.sheet, '--frame', String(args.frame), '--out', args.out);
    if (args.frameHeight) argv.push('--frame-height', String(args.frameHeight));
    if (args.columns) argv.push('--columns', String(args.columns));
    return argv;
  }

  if (action === 'demo') {
    argv.push('demo');
    if (args.out) argv.push('--out', args.out);
    return argv;
  }

  throw new Error(`unknown action ${JSON.stringify(action)}; expected one of ${ACTIONS.join(', ')}`);
}

export function apply(ctx, config = {}) {
  const workspace = config.workspace ?? process.env.ROGALIK_WORKSPACE ?? DEFAULT_WORKSPACE;
  const python = config.pythonPath ?? DEFAULT_PYTHON;
  const pipelineDir = join(workspace, 'tools');

  ctx.effect(() =>
    ctx.tools.register({
      name: 'rogalik_pixel_pipeline',
      description:
        'Prepare and verify Rogalik pixel art. Actions: check (validate PNG/sheet/tileset, PASS/FAIL), ' +
        'build (RGBA sheet -> Pixelorama .pxo), export (.pxo -> PNG frames or sprite sheet through the ' +
        'real Pixelorama CLI), atlas (pack frames into an atlas + JSON), demo (end-to-end smoke test). ' +
        'Every action returns structured artifacts and concrete problems.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        required: ['action'],
        properties: {
          action: {
            type: 'string',
            enum: ACTIONS,
            description: 'Pipeline step to run.',
          },
          path: { type: 'string', description: 'PNG to inspect (check).' },
          sheet: { type: 'string', description: 'Sprite sheet PNG (check/build/atlas).' },
          project: { type: 'string', description: 'Pixelorama .pxo project (export).' },
          out: { type: 'string', description: 'Output file or directory.' },
          frame: { type: 'integer', description: 'Frame width in pixels.' },
          frameHeight: { type: 'integer', description: 'Frame height; defaults to frame width.' },
          frames: { type: 'integer', description: 'Expected frame count (check).' },
          tile: { type: 'integer', description: 'Tile size for a tileset (check).' },
          columns: { type: 'integer', description: 'Atlas columns.' },
          fps: { type: 'number', description: 'Animation FPS recorded in the .pxo (build).' },
          tag: { type: 'string', description: 'Animation tag name spanning all frames (build).' },
          spritesheet: { type: 'boolean', description: 'Export one sprite sheet instead of frames.' },
          scale: { type: 'integer', description: 'Integer export scale.' },
          name: { type: 'string', description: 'Output file stem override.' },
        },
      },
      output: {
        schema: {
          type: 'object',
          additionalProperties: true,
          properties: {
            status: { type: 'string', enum: ['PASS', 'FAIL'] },
            action: { type: 'string' },
            args: { type: 'array', items: { type: 'string' } },
            report: { type: 'object', additionalProperties: true },
            problems: { type: 'array', items: { type: 'string' } },
          },
        },
        render: (_args, value) => {
          const head = `Pixel pipeline ${value.action}: ${value.status}`;
          const details = [];
          if (value.report?.artifacts) {
            const artifacts = Array.isArray(value.report.artifacts)
              ? value.report.artifacts
              : [value.report.artifacts];
            details.push(...artifacts.map((artifact) => `  artifact: ${artifact}`));
          }
          if (value.report?.checks) {
            for (const check of value.report.checks) {
              details.push(`  [${check.status}] ${check.name}: ${check.detail}`);
            }
          }
          for (const problem of value.problems ?? []) details.push(`  problem: ${problem}`);
          return [{ type: 'text', text: [head, ...details].join('\n') }];
        },
      },
      async execute(args) {
        const argv = buildArgs(args);
        const env = { ...process.env, PYTHONPATH: pipelineDir, PYTHONIOENCODING: 'utf-8' };
        try {
          const { stdout: out } = await runFile(python, ['-m', 'pixel_pipeline.cli', ...argv], {
            cwd: workspace,
            env,
            timeout: 240000,
            windowsHide: true,
            maxBuffer: 16 * 1024 * 1024,
          });
          return toJsonValue({
            status: 'PASS',
            action: args.action,
            args: argv,
            report: parseReport(out),
            problems: [],
          });
        } catch (error) {
          const stdout = String(error?.stdout ?? '');
          const stderr = String(error?.stderr ?? error?.message ?? error);
          const report = parseReport(stdout);
          const failed = report?.status === 'FAIL';
          return toJsonValue({
            status: 'FAIL',
            action: args.action,
            args: argv,
            report,
            problems: [
              ...(failed ? [] : ['pipeline exited with an error']),
              ...(stderr ? [stderr.trim().split('\n').slice(-6).join('\n')] : []),
            ],
          });
        }
      },
      presentCall: (args) => ({
        card: 'generic',
        title: `Pixel pipeline: ${args?.action ?? 'unknown'}`,
        kind: 'execute',
        rawInput: args,
      }),
    }),
  );
}

function parseReport(stdout) {
  const text = String(stdout ?? '').trim();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(text.slice(start, end + 1));
      } catch {
        /* fall through to the raw text */
      }
    }
    return { raw: text.slice(-4000) };
  }
}

/**
 * Make the value safe for the harness's lossless-JSON check: tool output on
 * Windows can contain console bytes that JSON cannot round-trip as UTF-8.
 */
export function toJsonValue(value) {
  return JSON.parse(
    JSON.stringify(value, (_key, current) =>
      typeof current === 'string' ? current.toWellFormed() : current,
    ),
  );
}

