# Safety-brief validation records (v2)

Historical regression version: `safety-brief-v2`. Real OpenAI calls with `gpt-4.1-mini` and `text-embedding-3-small`. The complete case results and execution fingerprint are in [reports/evaluation.json](../reports/evaluation.json).

The public service now uses Vertex AI for generation and embeddings. The OpenAI scores below are retained as historical results, not an evaluation of the new model. Current runtime checks are recorded separately in [vertex-smoke.json](../reports/vertex-smoke.json).

## What changed

The default workflow requests a drug-safety-team brief. It retrieves research, FDA communication and label sources separately; claims are categorized and checked against the appropriate source type. A cross-source interpretation needs research plus FDA or label evidence. The UI keeps retrieved-document counts separate from accepted-claim counts and shows gaps explicitly.

OpenAI calls now use structured output schemas. Personal risk/treatment requests also pass through a conservative English-language gate before model planning. Model-based scope checks remain in place for other requests. The gate can have false positives and is not a comprehensive medical intent classifier.

## Recorded results

| Measure | Result |
|---|---:|
| Completed cases | 34 / 36 |
| Drafted claims | 138 |
| Passing mechanical checks before model-support filtering | 116 |
| Published claims | 101 |
| Published claims passing citation/category/date checks | 101 / 101 |
| Withheld claims | 37 |
| Retrieved sources newer than cutoff | 0 |
| Out-of-scope questions publishing no claims | 6 / 6 |
| Cases retrieving the author-expected sources | 25 / 27 |
| Median runtime | 8.66 seconds |

These are 36 author-designed **regression** cases, not an untouched holdout benchmark. The case file retains its original development/held_out grouping for traceability, but this is not evidence of unseen-test performance. An earlier v2 run produced general research answers for three personal-treatment/risk prompts; that failure informed the scope gate. The earlier report is retained in `reports/archive/v2-before-scope-gate/`.

The first attempt with the final code completed 34/36 cases: `brief-04` and `brief-06` returned `RateLimitError`; a subsequent probe identified `credit_balance_exhausted` (insufficient quota). That report is retained in `reports/archive/v2-first-final-attempt/`. The two cases remained incomplete on retry. Only failed cases were retried; successful states were reused without rerunning or cherry-picking answers. Current incomplete cases: [('brief-04', 'RateLimitError'), ('brief-06', 'RateLimitError')].

Completed runs that drafted claims but published none: test-03, test-06, brief-03. Missing/partial verifier judgments or failed checks can leave an in-scope question without a usable answer. Such gaps remain visible. Passing the pipeline is not a guarantee of complete or correct scientific interpretation.

Mechanical checks are a gate invariant, not a clinical accuracy score. The paired mechanical-only versus final counts use the same drafted claims and passages; they measure filtering behavior, not an independently measured hallucination reduction. Source expectations check document retrieval, not complete passage coverage. A matching quote does not prove a whole claim, and the drafter/verifier use the same model family.

## Reproduction

- `uv run pytest -q`: 31 deterministic tests, including source-category separation, missing/ambiguous verification, quote/date checks, personal-request routing and a stubbed Bedrock request contract.
- `uv run python scripts/evaluate.py`: executes paid model calls. It resumes only from raw states whose fingerprint matches the case file, pipeline source, corpus and model configuration. Raw states are excluded from Git.
- `uv run python scripts/browser_smoke.py <URL>`: saved and real live runs, all three source sections, tool trace, preload labeling, mobile overflow, error recovery, and no raw corpus endpoint.

The current saved example comes from the Vertex `default_brief` smoke case, an actual recorded model run. The earlier OpenAI example is retained in the archived report history. It is explicitly labeled. Bedrock has not been live-verified. The data are still preloaded FDA/DailyMed/PubMed snapshots; this evaluation does not test live internet discovery.

## Vertex runtime verification

`scripts/vertex_smoke.py` makes three real model-path runs and checks a fourth personal-request case without invoking a model: a default safety brief, a historical cutoff, a question about whether a later study establishes an FDA warning withdrawal, and an individual risk/dose request. The checks cover source-category coverage, date filtering and the pre-model gate. Regulatory interpretation also requires manual source review. This is a small integration smoke suite, not the full 36-case regression benchmark or a clinical accuracy measure.

Vertex generation uses `google/gemini-3.8-flash` through Google’s OpenAI-compatible endpoint. Embeddings use `text-embedding-005`; all 63 passages were re-indexed in a separate Vertex collection. The embedding HTTP contract is also tested for batching, ordering and document/query task types.

The first Vertex trial exhausted the output limit during verification because the default reasoning consumed the budget; all seven draft claims were withheld. The failure summary is retained in `reports/archive/vertex-initial-verification-failure.json`. Setting explicit low reasoning effort resolved the truncation without relaxing verification checks; the completed suite uses that setting.
