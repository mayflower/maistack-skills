---
name: contract-redline
description: Generate lawyer-facing deliverables from approved contract redlines. Use this skill when the user already has redline JSON or wants tracked-changes .docx files, redline PDFs, summary PDFs, internal negotiation memos, markdown output, document diffs, placeholder scans, or redline remapping between contract versions.
license: MIT. See LICENSE.txt for attribution and full terms.
---

# Contract Redline

Adapted from `evolsb/legal-redline-tools` at commit `f81f6763bef10e6b1357e557d1cd1602f9ef47fb`, then packaged as a local `maistack-skills` execution skill.

This skill takes structured redline JSON and a source `.docx` file, then generates counterparty-facing and internal deliverables. It works well after `contract-review`, but it can also run standalone if the user already has valid JSON redlines.

## Use This Skill When

- The user wants a tracked-changes `.docx` from approved redlines.
- The user wants a redline PDF, summary PDF, internal memo PDF, or markdown generated from contract edits.
- The user wants to diff two `.docx` versions into redline JSON.
- The user wants to scan a `.docx` for blank fields, placeholders, or missing references.
- The user wants to remap existing redlines onto a newer contract draft.

## Inputs

Minimum required inputs:

- source `.docx`
- redline JSON array using the schema below

Optional inputs:

- author name
- document title
- party names for headers
- output mode (`external` or `internal`)

## JSON Schema

Required operation types:

- `replace`: `old`, `new`
- `delete`: `text`
- `insert_after`: `anchor`, `text`
- `add_section`: `text`, `after_section`, optional `new_section_number`

Optional metadata:

- `section`
- `title`
- `tier`
- `rationale`
- `walkaway`
- `precedent`

Treat `rationale`, `walkaway`, and `precedent` as internal-only unless the user explicitly asks for internal analysis.

## Main Commands

Use the local wrapper, not a remote `pip install`:

```bash
python scripts/legal_redline_cli.py apply input.docx output.docx \
  --from-json assets/sample-redlines.json \
  --pdf full-redline.pdf \
  --summary-pdf summary.pdf \
  --memo-pdf internal-memo.pdf \
  --markdown redlines.md \
  --doc-title "Agreement Title" \
  --doc-parties "Party A / Party B"
```

Other supported commands:

```bash
python scripts/legal_redline_cli.py diff old.docx new.docx -o changes.json
python scripts/legal_redline_cli.py scan contract.docx -o scan.json
python scripts/legal_redline_cli.py remap old.docx new.docx --redlines redlines.json -o remapped.json
python scripts/legal_redline_cli.py compare --agreements msa=msa.json sow=sow.json -o comparison.md
```

## Output Policy

- `output.docx`: tracked-changes Word file for negotiation
- `--pdf`: full-document redline PDF
- `--summary-pdf`: clean schedule of proposed changes
- `--memo-pdf`: internal memo with tiers, rationale, walkaway positions, and precedent
- `--markdown`: structured markdown output for docs or follow-on workflows

Never send internal memo content to the counterparty unless the user explicitly asks for internal analysis to be shared.

## Text Matching Rules

- `old`, `text`, and `anchor` must match document text closely. Copy directly from the contract where possible.
- If text does not match safely, inspect the CLI output for `[NOT FOUND]` entries and the final `Applied: X/Y redlines` summary. Treat any partial application as a failure that must be explained before the deliverable is treated as final.
- Use `scan` before `apply` if the document likely contains placeholders, missing exhibits, or inconsistent references.
- Use `diff` when the user has two contract versions and wants machine-generated redlines rather than hand-authored JSON.
- Use `remap` when the user has valid redlines written for an earlier draft.

## Workflow

1. Validate the source `.docx` and redline JSON.
2. Decide whether outputs are external, internal, or both.
3. Run `scan` first if placeholders or exhibit issues are likely.
4. Run `apply` to generate tracked changes and deliverables.
5. If an anchor fails or only some redlines apply, report the exact failing fragment and request corrected source text instead of presenting the output as complete.

## Relationship to `contract-review`

Use `contract-review` to analyze the business and legal risk, prioritize asks, and produce redline JSON.

Use `contract-redline` to turn that JSON into:

- tracked-changes `.docx`
- redline PDF
- summary PDF
- internal memo PDF
- markdown deliverables
