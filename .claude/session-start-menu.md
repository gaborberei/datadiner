# Session start — pick a path

**Your FIRST action this session MUST be an `AskUserQuestion` call with the menu
below.** Not prose, not an inline "so which do you want?" — the tool. Emit it before
any other tool call, and before answering whatever the user typed.

## The call

Use exactly this shape. The tool appends its own free-text **"Other"** choice
automatically — never write a third option yourself, or it renders twice:

- `header`: `Path`
- `question`: `How do you want to use DataDiner this session?`
- `multiSelect`: `false`
- Option 1 — label **`Analyze my own data`**
  — dataset-onboarding (only if the CSV has no `dataset_brief.yaml`) →
  data-quality-gate → retention-analysis (Phase 1 overall → Phase 2 segments).
- Option 2 — label **`Take the course`**
  — retention-tutor (show → ask → probe → reveal), graded against the hidden answer
  key on course datasets, coaching mode on bring-your-own data.

The user therefore always sees three choices: the two paths, plus **Other** for
anything else.

## The only reasons to skip the menu

Skip it **only** when the first message does one of these. This is the complete
list — do not extend it by inference:

1. Invokes a skill by name (`/retention-analysis`, `/retention-tutor`,
   `/data-quality-gate`, `/dataset-onboarding`).
2. Says teach / quiz / walk me through / guide me → route to **retention-tutor**.
3. Names a specific CSV or dataset to analyze → route to the analyze path.

Everything else gets the menu, **including** messages that merely mention the repo or
a dataset in passing. "What is in this folder?", "what datasets are here?", "unzip
X", "how does this work?" **do not select a path**: answer the question, then ask the
menu in that same turn. When in doubt, ask the menu — a redundant menu costs one
keystroke; a skipped one silently drops the user into the wrong experience.

Route to the chosen skill; do not re-ask once they've picked.
