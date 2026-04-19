# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run from `skills/skill-toon-openapi/`:

```bash
# Install dependencies
pip install -r skills/skill-toon-openapi/requirements.txt

# Run full test suite
cd skills/skill-toon-openapi && pytest tests/ -v

# Run a single test file
cd skills/skill-toon-openapi && pytest tests/test_unit.py -v

# Run a single test by name
cd skills/skill-toon-openapi && pytest tests/test_unit.py -k "test_name" -v

# Run with coverage
cd skills/skill-toon-openapi && pytest tests/ --cov=scripts --cov-report=term-missing

# Ingest an API (two-step pipeline)
python skills/skill-toon-openapi/scripts/ingest/parse_spec.py <URL_or_file> > /tmp/spec.json
python skills/skill-toon-openapi/scripts/ingest/transform_toon.py /tmp/spec.json
```

## Architecture

This repo is a **Claude Code Marketplace Plugin** — an agent + skill bundle. The plugin manifest lives in `.claude-plugin/`, the agent definition in `agents/`, and all operational logic in `skills/skill-toon-openapi/`.

### How the agent and skill relate

`agents/toon-openapi-agent.md` is a thin identity layer: it sets the agent's language detection rules and delegates all logic to the skill. The skill (`skills/skill-toon-openapi/SKILL.md`) is the authority — it defines activation rules, sub-skill routing, global constraints, and storage paths.

### Ingest pipeline (critical path)

The core data flow is two sequential Python scripts:

1. **`scripts/ingest/parse_spec.py`** — fetches URL or reads file, handles JSON/YAML, resolves relative server URLs. Outputs raw spec JSON to stdout.
2. **`scripts/ingest/transform_toon.py`** — consumes the spec JSON, resolves all `$ref` references (circular-safe), and writes two artifacts per namespace under `.toon_apis/apis/<namespace>/`:
   - `toon.txt` — compact human+LLM-readable semantic overview (~500 tokens for a typical API)
   - `mapping.json` — full technical contract, always queried via `jq` (never `cat`)

The namespace slug is derived from the API title via `slugify()` in `transform_toon.py`.

### Sub-skill scripts

Each sub-skill has a `.md` instruction file (read by the LLM before execution) and a `.py` script (executed by the agent):

| Sub-skill | Script | Purpose |
|---|---|---|
| ingest | `parse_spec.py` + `transform_toon.py` | Parse and compile spec to TooN |
| consult | `log_metrics.py`, `resolve_multi.py` | Query API, track token usage, multi-namespace |
| diff | `diff_specs.py` | Compare two namespace mappings |
| validate | `validate_payload.py` | Validate JSON payload against mapping schema |
| testgen | `generate_tests.py` | Scaffold integration tests (multi-language) |
| clientgen | `extract_contract.py` | Extract structured contract for LLM code gen |
| exportgen | `export_context.py` | Export compact TooN blocks for cross-thread use |

### TooN grammar (for reading/writing toon.txt)

- Types: `s`=string, `i`=integer, `b`=boolean, `a`=array, `o`=object
- Markers: `!`=required, `?`=optional
- Param prefixes: `q:`=query, `h:`=header, `c:`=cookie, `f:`=form, `body.`=JSON body field, `rh:`=response header
- Special: `binary`=file upload, `stream`=SSE

### Test structure

Tests use `sys.path.insert` to import scripts directly — no package setup required. Fixtures are in `tests/fixtures/` (OAS3 full params, Swagger 2.0 Petstore, fake API). Integration tests hit real URLs and require network access.

### Storage layout

Runtime data is isolated to `.toon_apis/` at the consuming project root (gitignored). The plugin itself never writes to `.toon_apis/` — only the scripts do, when invoked by the agent in a consumer project.