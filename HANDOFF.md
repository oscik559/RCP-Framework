# Handoff Notes — RCP-Framework Submission Prep

_Last updated: 2026-03-19_

## What was done
- `.env` purged from all git history (git filter-repo)
- `Paper/` untracked from git (added to .gitignore) — keep locally, never commit
- `hydroscand_produktbok.egg-info/` untracked
- New private repo created: https://github.com/oscik559/RCP-Framework
- History pushed clean (no .env)

## Still to do

### Repo structure
- [ ] Rename `Layer_Experiments/` → `Layer_Experiments_Case_I/`
- [ ] Move `compute_mcnemar.py` (root) → `Layer_Experiments_Case_I/`
- [ ] Fix `.gitignore` — add `Paper/`, `.env`, `egg-info/`, `__pycache__/`
- [ ] Decide on `check_encoding.py` and `fix_example_encoding.py` at root — likely delete or move
- [ ] Review `presentation.yaml` at root — include or remove?

### Files to update
- [ ] `README.md` — update repo name references from Hydroscand_Produktbok → RCP-Framework, add proper usage instructions
- [ ] `requirements.txt` — verify it is complete and clean
- [ ] `LICENSE` — verify author name and year are correct
- [ ] `Paper/case_ii_results.txt` — update with final results from both case studies (not committed, local only)

### Before going public
- [ ] Add co-authors as GitHub collaborators (need their GitHub usernames or emails):
  - Mehdi Tarkian
  - Sanjay Nambiar
  - Marie Jonsson
  - Christoffer Brax
- [ ] Update data availability statement in paper.tex with repo URL:
  `https://github.com/oscik559/RCP-Framework`
- [ ] Flip repo visibility to **public** at submission

### database/backups/data.zip
- 62 MB — over GitHub's 50 MB soft limit. Pushed fine for now.
  If it causes issues later, use Git LFS or host the DB elsewhere and link in README.

## Repo name rationale
`RCP-Framework` — Relational Control Plane, the core contribution of the paper.
Old name `Hydroscand_Produktbok` was company/project specific, not paper-facing.
