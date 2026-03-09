---
name: contract-review
description: Review commercial contracts, NDAs, SaaS/MSA terms, DPAs, consulting or employment agreements, and M&A transaction documents. Use for first-pass legal risk review, negotiation prep, clause analysis, extracting key terms, and producing structured redline JSON for follow-on tracked-changes deliverables. Pair with contract-redline when the user wants lawyer-facing .docx or PDF outputs.
license: MIT. See LICENSE.txt for attribution and full terms.
---

# Contract Review

Adapted from `evolsb/claude-legal-skill` at commit `e6c63c630ce63024fdbff6a1c7e4276b43bfe07b`, then rewritten for `maistack-skills`.

Review legal agreements for business risk, negotiation leverage, missing protections, and concrete redline proposals. This skill is for analysis and negotiation prep. It can produce structured redline JSON, but it does not itself generate tracked-changes documents. Use `contract-redline` for lawyer-facing `.docx` and PDF outputs.

## Use This Skill When

- The user asks to review or analyze a contract, agreement, NDA, MSA, DPA, SOW, consulting agreement, employment agreement, reseller agreement, merchant agreement, or acquisition document.
- The user wants a clause-by-clause risk review, negotiation priorities, fallback positions, or suggested markup.
- The user wants machine-readable redline JSON that can be handed to `contract-redline`.

## Core Workflow

1. Determine the document type, the user's position, and whether the draft is signed or still negotiable.
2. Run a pre-review completeness pass before substantive analysis:
   - blank fields, placeholders, missing exhibits, broken cross-references, signature status, governing law and venue.
3. Apply the correct review lens:
   - NDA: `references/nda.md`
   - SaaS/MSA/DPA/commercial services: `references/saas-msa.md`
   - M&A and transaction documents: `references/ma.md`
   - EU/DACH cautions: `references/eu-dach-caveats.md`
4. Classify issues by severity and commercial leverage:
   - Tier 1: unacceptable risk / likely walkaway issue
   - Tier 2: important negotiated ask
   - Tier 3: desirable improvement
5. Produce a business-readable markdown review.
6. If the user wants markup, produce structured redline JSON using the schema below.

If the user's position is unclear, ask or state the assumption explicitly before final recommendations. Do not silently review from the wrong side.

## Output Requirements

Use markdown. Do not use XML tags.

Default review structure:

1. Contract title and document type
2. User position and counterparty
3. Draft/executed status
4. Pre-signing alerts
5. Executive summary
6. Key terms table
7. Risk analysis grouped by severity
8. Missing provisions
9. Negotiation priorities
10. Short disclaimer

Always include a disclaimer equivalent to: "This review is for informational and negotiation-preparation purposes only and is not legal advice. Material terms should be reviewed by qualified counsel."

## Redline JSON Schema

When the user wants proposed edits, output a JSON array that `contract-redline` can consume directly.

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

Rules:

- Copy `old`, `text`, and `anchor` from the document exactly. Do not paraphrase.
- Keep `rationale`, `walkaway`, and `precedent` internal-facing. They are useful for internal memos, not counterparty-facing documents.
- If a passage is too ambiguous to target safely, say so instead of fabricating a brittle redline.

Example skeleton:

```json
[
  {
    "type": "replace",
    "old": "three (3) months",
    "new": "twelve (12) months",
    "section": "10.2",
    "title": "Liability Cap",
    "tier": 1,
    "rationale": "3 months is below normal B2B commercial range.",
    "walkaway": "Accept 6 months if needed."
  }
]
```

## Review Guidance

- Prefer specific replacement language over vague advice like "negotiate this."
- Distinguish between missing protections and merely unfavorable protections.
- Note commercial context that affects negotiability: deal size, standard-form paper, regulated industry, renewal pressure, or transaction timing.
- Use the existing always-on `docx` skill for `.docx` extraction or document inspection; do not duplicate generic Word-processing guidance here.

## EU/DACH Caveats

- This skill is not a Germany- or EU-exclusive legal workflow. It starts from general commercial contracting norms and adds explicit EU/DACH cautions.
- Flag governing law, venue, employee non-compete enforceability, mandatory labor protections, and privacy annexes when they materially affect the recommendation.
- If the agreement is mainly a DPA, SCC annex, privacy addendum, or personal-data processing package, combine this review with `gdpr-dsgvo-expert`.
- Avoid asserting definitive jurisdiction-specific legal conclusions unless the document and user context support them. Escalate to qualified counsel when the issue turns on local enforceability.

## Relationship to `contract-redline`

Use `contract-review` on its own for:

- first-pass legal review,
- negotiation strategy,
- red-flag identification,
- clause extraction,
- redline JSON creation.

Use `contract-redline` after this skill when the user wants:

- tracked-changes `.docx`,
- redline PDF,
- summary PDF,
- internal negotiation memo,
- markdown deliverables generated from approved redlines.
