// Local registration check: every tool our bundles register must expose a
// model-valid JSON Schema. The harness rejects a tool whose root parameters
// schema is not `type: "object"`, so this script fails before installation.
//
// Run: node plugins/_schema-check.mjs
import assert from 'node:assert/strict';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const ALLOWED = new Set(['object', 'array', 'string', 'number', 'integer', 'boolean', 'null']);

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

function checkNode(node, path, problems) {
  if (node === null || typeof node !== 'object') {
    problems.push(`${path}: schema node must be an object`);
    return;
  }
  if (Array.isArray(node)) {
    problems.push(`${path}: schema node must not be an array`);
    return;
  }
  const hasType = node.type !== undefined;
  const hasComposition = node.oneOf !== undefined;
  if (!hasType && !hasComposition && node.properties === undefined) {
    problems.push(`${path}: node has neither type, oneOf nor properties`);
  }
  if (hasType) {
    const types = Array.isArray(node.type) ? node.type : [node.type];
    for (const type of types) {
      if (!ALLOWED.has(type)) problems.push(`${path}: unsupported type ${JSON.stringify(type)}`);
    }
  }
  if (node.enum !== undefined) {
    assert.ok(Array.isArray(node.enum), `${path}: enum must be an array`);
  }
  if (node.properties !== undefined) {
    assert.equal(typeof node.properties, 'object', `${path}.properties must be an object`);
    for (const [key, child] of Object.entries(node.properties)) {
      checkNode(child, `${path}.properties.${key}`, problems);
    }
  }
  if (node.required !== undefined) {
    assert.ok(Array.isArray(node.required), `${path}.required must be an array of names`);
    for (const name of node.required) {
      assert.equal(typeof name, 'string', `${path}.required entries must be strings`);
      if (node.properties && !(name in node.properties)) {
        problems.push(`${path}.required names unknown property ${JSON.stringify(name)}`);
      }
    }
  }
  if (node.items !== undefined) checkNode(node.items, `${path}.items`, problems);
  if (node.oneOf !== undefined) {
    node.oneOf.forEach((child, index) => checkNode(child, `${path}.oneOf[${index}]`, problems));
  }
  if (node.additionalProperties !== undefined) {
    assert.equal(
      typeof node.additionalProperties,
      'boolean',
      `${path}.additionalProperties must be a boolean in this harness`,
    );
  }
}

let failed = false;

for (const relative of [
  'rogalik-env-check/index.js',
  'rogalik-pixel-pipeline/index.js',
]) {
  const mod = await import(pathToFileURL(join(here, relative)).href);
  const ctx = stubCtx();
  mod.apply(ctx, { workspace: process.cwd() });
  assert.ok(ctx.registered.length > 0, `${relative} registered no tools`);

  for (const tool of ctx.registered) {
    const problems = [];
    assert.equal(typeof tool.name, 'string', `${relative}: tool name`);
    assert.ok(tool.description.length > 10, `${relative}: tool description`);

    if (tool.parameters?.type !== 'object') {
      problems.push(
        `parameters root type is ${JSON.stringify(tool.parameters?.type)}; expected "object"`,
      );
    }
    checkNode(tool.parameters, `${tool.name}.parameters`, problems);

    if (tool.output?.schema === undefined) {
      problems.push('output.schema is missing');
    } else {
      checkNode(tool.output.schema, `${tool.name}.output.schema`, problems);
    }
    if (typeof tool.output?.render !== 'function') problems.push('output.render is missing');
    if (tool.parameters?.type === 'object' && tool.parameters.properties === undefined) {
      problems.push('object schema has no properties');
    }

    if (problems.length > 0) {
      failed = true;
      console.error(`FAIL ${tool.name}`);
      for (const problem of problems) console.error('  -', problem);
    } else {
      const propertyCount = Object.keys(tool.parameters.properties ?? {}).length;
      console.log(`PASS ${tool.name}: root object, ${propertyCount} properties, output schema ok`);
    }
  }
}

process.exit(failed ? 1 : 0);
