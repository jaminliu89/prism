import test from 'node:test';
import { strict as assert } from 'node:assert';
import { normalizeIntent } from '../src/core.mjs';
test('normalize', () => assert.equal(normalizeIntent(' A '), 'a'));
