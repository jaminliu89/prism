import test from 'node:test';
import { strict as assert } from 'node:assert';
import { greeting } from '../src/unrelated.mjs';
test('unrelated', () => assert.equal(greeting(), 'hello'));
