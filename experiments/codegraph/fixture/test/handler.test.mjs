import test from 'node:test';
import { strict as assert } from 'node:assert';
import { handleIdea } from '../src/handler.mjs';
test('handler', () => assert.equal(handleIdea(' A ').intent, 'a'));
