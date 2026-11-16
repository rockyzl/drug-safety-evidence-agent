# Evidence Desk

A working, source-linked drug-safety research demo built as an independent learning project. Ask about the apparent difference between ORAL Surveillance and STAR-RA, then inspect the model's search decisions, claim checks and original sources.

**Live demo:** deployment URL is recorded below after verification.  
**Design:** [Paper canvas](https://app.paper.design/file/01M7GZ4X3RT3H1KPN7BEJK659S)

## Try it

1. Open the live demo and select **Try a saved example** for an immediate, clearly labeled recorded model run.
2. Select **Run agent** for a new real model call. The page shows actual server progress.
3. Expand a source under a claim. Open the original document to inspect its context.
4. Inspect any withheld claims and the agent's tool calls.

The live model is **OpenAI gpt-4.1-mini**, with **text-embedding-3-small** embeddings. A real LangGraph workflow selects bounded search-tool calls, retrieves evidence from Chroma, drafts cited claims, and checks each claim before including it. This is a research prototype, not clinical decision support.

## Stack and real integrations

| Component | Implementation |
|---|---|
| Agent workflow | LangGraph, validated model-generated search plan, bounded read-only tool dispatch |
| Generation and verification | OpenAI API, separate drafting and support-assessment calls |
| Retrieval | Chroma vectors + lexical token overlap, reciprocal rank fusion |
| Evidence | FDA communication, selected DailyMed label sections, two PubMed abstracts |
| Provenance | Source URLs, publication/version dates, SHA-256 hashes, stable passage IDs |
| Checks | Reference membership, exact quote, date cutoff, model-assessed support |
| Web | FastAPI, server-sent events, responsive HTML/CSS/JS designed in Paper |
| Hosting | Google Cloud Run, dedicated service account, Secret Manager |
| AWS Bedrock | Converse adapter implemented and contract-tested; **not live-verified** |

No full source corpus or API key is committed. The ingestion script fetches the public source snapshots. Public manifests record what was used. Research papers are abstract-only; this is not a systematic review or comprehensive search service.

## Run locally

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), an OpenAI API key in your local environment.

```bash
uv sync --frozen
# Set OPENAI_API_KEY securely in your environment; never commit it.
uv run python scripts/ingest.py
uv run python scripts/index.py
uv run uvicorn app.main:app --host 127.0.0.1 --port 8186
```

Open http://127.0.0.1:8186. Ingestion uses cached documents unless called with `--refresh`. Indexing and live queries incur model/embedding API charges. When refreshing the corpus, also re-run indexing, evaluation and regenerate the saved example so their provenance remains aligned. The existing report describes the checked-in manifest hashes, not future snapshots.

```bash
uv run pytest -q
uv run python scripts/evaluate.py
uv run playwright install chromium
uv run python scripts/browser_smoke.py
```

The public result and evaluation files are included so a clone can display the recorded example immediately after index preparation. Live requests remain actual API calls.

## Optional Bedrock generation

Configure AWS credentials using your normal local login/profile; do not paste keys into code. Set `EVIDENCE_PROVIDER=bedrock`, `BEDROCK_MODEL_ID` to an enabled model/inference profile, and `AWS_REGION`. The adapter uses [Bedrock Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html). The role needs permission to invoke the selected model. OpenAI embeddings are still required. This adapter has a stubbed contract test, not a verified AWS deployment.

## Deployment

`scripts/deploy.sh` builds a private image and deploys Cloud Run. Set `CLOUD_PROJECT`; create an Artifact Registry repository `evidence-desk`, runtime service account `evidence-desk`, and Secret Manager secret `evidence-desk-openai-key`. Grant that account secret accessor **on that one secret**. The script uses one worker, at most one instance, and scales to zero.

Anonymous usage is limited to two active runs, 20 runs/hour and 80/day per process. Counters reset after restart; these are not guaranteed spending limits. Change `DAILY_RUN_LIMIT` for a smaller daily allowance. Public access is intentional for the portfolio demo.

## Validation and limits

30/30 live evaluation cases completed. The pipeline withheld 16 of 116 drafted claims; 100 published claims passed mechanical citation checks. Five out-of-scope prompts abstained. These are engineering checks, **not clinical accuracy scores**. The same model family generates and verifies, which limits independence. [Full evaluation](docs/evaluation.md).

No patient information, internal pharmaceutical data, safety submissions or production pharmacovigilance integrations are used. Do not submit patient or confidential information. Date filtering excludes newer indexed versions; it does not reconstruct historical pages. Review original sources before using a result.

- [Architecture and interview explanation](docs/architecture.md)
- [Design tool research and Paper implementation](docs/design.md)
- [Source manifest](app/data/source-manifest.json)
- [Case-level evaluation results](reports/evaluation.json)

Code is MIT licensed. IBM Plex fonts use the bundled SIL Open Font License. Third-party source documents retain their original terms and are fetched separately; the code license does not cover them.
