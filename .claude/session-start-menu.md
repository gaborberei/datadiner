# Session start — pick a path

Before doing anything else this session, help the user choose how they want to use
DataDiner. **Unless their first message already clearly selects a path** (e.g. they
name a CSV to analyze, or ask to be taught/quizzed — then route directly and skip the
menu), open with an `AskUserQuestion` offering these two paths:

1. **Analyze my own data** — a direct retention analysis.
   - If the target CSV has **no** `dataset_brief.yaml` beside it, run
     **dataset-onboarding** first to build the brief.
   - Then run **data-quality-gate** to validate the CSV against the brief.
   - Then run **retention-analysis** (Phase 1 overall → Phase 2 segments).

2. **Take the course** — a guided Socratic lesson.
   - Hand off to **retention-tutor** (show → ask → probe → reveal), graded against
     the hidden answer key on course datasets, coaching mode on bring-your-own data.

Route to the chosen skill; do not re-ask once they've picked.
