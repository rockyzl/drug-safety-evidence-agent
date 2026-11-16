# Evaluation record

Executed with real OpenAI API calls, gpt-4.1-mini and text-embedding-3-small, on November 15–16, 2026. The case file was written before the evaluation batch; no prompts were changed in response to held-out results. The initial exploratory run informed the quoting prompt before this frozen batch.

## Cases and results

30 author-designed questions: 6 development and 24 held out. Expectations specify sources, cutoff behavior or abstention, not independently annotated clinical gold answers. This is a small engineering evaluation, not a validated medical benchmark.

| Measure | Result |
|---|---:|
| Completed live runs | 30 / 30 |
| Development / held-out cases | 6 / 24 |
| Drafted claims | 116 |
| Claims passing mechanical checks before semantic verification | 103 / 116 |
| Claims published after both checks | 100 / 116 |
| Published claims passing ID, exact-quote and date checks | 100 / 100 |
| Retrieved sources exceeding cutoff | 0 |
| Out-of-scope cases producing no published claim | 5 / 5 |
| Cases retrieving all author-expected sources | 23 / 23 |
| Median runtime | 9.73 seconds |

Development: 24 drafted, 20 passed mechanical checks, 20 published. Held out: 92 drafted, 83 passed mechanical checks, 80 published. No-source cutoff cases also abstained.

The paired comparison uses the **same draft and retrieved passages**: mechanical checks alone admitted 103 claims; adding the model support assessment admitted 100. Three further claims were withheld by the semantic layer. Thirteen failed mechanical checks, chiefly nonmatching quoted text. This measures filter behavior, **not a reduction in independently measured hallucinations**. A correct claim can be withheld because its quote is malformed; an incorrect claim can still pass a model verifier.

The 100/100 published-citation result is an expected gate invariant, not independent accuracy evidence. Source retrieval expectations only check that a source was found, not that the best passages were ranked first or that a complete answer was produced. The verifier uses the same model family as the drafter, and thus may share its errors.

## Reproduction

1. Install dependencies and prepare the corpus/index as in the README.
2. Run `uv run pytest -q` for deterministic fail-closed checks and the stubbed Bedrock request contract.
3. Run `uv run python scripts/evaluate.py`. This makes paid API calls and resumes from local `reports/raw/evaluation/` results. To produce a fresh run, move that directory aside first.
4. Inspect `reports/evaluation.json` for case-level results and corpus/case hashes. Raw model states are kept locally and excluded from Git.
5. Run `uv run python scripts/browser_smoke.py <URL>` to exercise saved and live results, citations, tool traces, mobile overflow and error recovery. It makes one additional live model request.

The retained saved example comes from `dev-01`, the comparison question. It is an actual recorded model run and includes one withheld claim; it is not hand-written to appear flawless.

Unit tests cover invented IDs, mismatched/empty quotes, absent citations, future source dates, ambiguous/missing/partial verifier judgments, a verifier outage, out-of-scope graph routing, public excerpt limits, and Bedrock request/response structure. Bedrock tests use a stub; AWS execution has not been verified.
