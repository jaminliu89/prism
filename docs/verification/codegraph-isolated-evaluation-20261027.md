# CodeGraph × Prism — isolated provider evaluation (2026-10-27)

## Experiment contract

Goal: determine whether a semantic dependency provider finds indirectly affected tests beyond a deliberately narrow direct-import text-search baseline. This is a controlled proof-of-mechanism, not a product-wide comparison or production adoption.

- Provider: colbymchenry/codegraph, fixed npm version 1.6.2.
- Environment: GitHub Actions Ubuntu + Node 22; temporary-prefix npm installation using --ignore-scripts; CI runner only.
- Restrictions: DO_NOT_TRACK=1, CODEGRAPH_TELEMETRY=0, CODEGRAPH_NO_UPDATE_CHECK=1. No `codegraph install`, no global Agent configuration, no user/private runtime projects indexed.
- Corpus: synthetic JavaScript ESM and Python subgraphs in `experiments/codegraph/fixture`, deliberately small and auditable.
- Query: source core module change. Expected ground truth: directly attached core unit test AND handler end-to-end test; unrelated test excluded.
- Baseline: search only test files that directly import core (simple and deliberately insufficient); this is **not** a comparison against LSP/compiler or a competent full-repository grep approach.

## Observed results

| Code family | Direct-import baseline | CodeGraph `affected --quiet` | Ground truth |
| --- | --- | --- | --- |
| JavaScript ESM | `test/core.test.mjs` | `test/core.test.mjs`, `test/handler.test.mjs` | Both tests |
| Python | `tests_py/test_core.py` | `tests_py/test_core.py`, `tests_py/test_handler.py` | Both tests |

Both runs exclude the deliberately unrelated test. GitHub Actions run
https://github.com/jaminliu89/prism/actions/runs/40461375011
finished successfully at tested SHA `327e80328ca97cd286e558cdb5ec21313fddb538`.
Python fixture: 3 tests pass. Existing Prism: 63 tests pass, `prism.py doctor` passes.
The earlier JavaScript-only run is available at https://github.com/jaminliu89/prism/actions/runs/40460878985.

## Verdict and production gate

**ACCEPTED FOR REPRODUCIBLE SANDBOXED EXPERIMENT ONLY**.
CodeGraph has demonstrated *specific* indirect dependency/test mapping in both JavaScript and Python. No benchmark proves global precision, completeness, security, or production integration.

Do not route Product Foundry/Prism by default until:

1. Pin dependency artifacts and complete supply-chain/telemetry behavior review.
2. Run benchmark against **authorized** representative private-code revisions in a controlled egress-restricted environment; evaluate misses, false positives, cost, index freshness and time.
3. Inspect dynamic workflow dispatch, event routing, implicit dependencies and prompt/config-only changes; these might evade static graphs.
4. Confirm read-only indexing, no secret or private orchestration export, safe MCP tool visibility, and full opt-in.
5. Compare CodeGraph against the actual existing group code indexing tools, not only simplistic grep.

The optional code intelligence output is evidence for a human/QA review, never a release approval or proof that proprietary orchestration resists reverse engineering.
