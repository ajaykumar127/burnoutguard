# Deploying Burnout Guard to GitHub

How to publish this repo and open it to the world.

## 1. Publish

```bash
# from the repo root (git history is already initialised)
gh auth login                                  # once
gh repo create burnout-guard --public --source=. \
  --description "A Claude Skill that measures burnout and enforces graduated cool-off periods" \
  --push
```

Or without the GitHub CLI:
```bash
git remote add origin git@github.com:<you>/burnout-guard.git
git push -u origin main
```

## 2. Cut a release with the installable .skill file

```bash
# Package (zip the skill folder contents; the .skill extension is a zip)
zip -r burnout-guard.skill SKILL.md scripts references assets
gh release create v2.0.0 burnout-guard.skill \
  --title "Burnout Guard v2.0 — graduated levels" \
  --notes-file CHANGELOG.md
```

Claude.ai / Desktop users install by downloading the `.skill` asset from the release
and uploading it in Settings → Capabilities → Skills. Claude Code users just clone
into `~/.claude/skills/`.

## 3. Repo settings worth flipping

- **Issues:** on (templates ship in `.github/ISSUE_TEMPLATE/`).
- **Discussions:** on — threshold-tuning experiences make great community data.
- **Topics:** `claude`, `claude-skill`, `anthropic`, `wellbeing`, `burnout`,
  `developer-health`.
- **Social preview:** the levels table screenshots well.

## 4. Versioning

Semantic-ish: bump **major** for protocol changes (level semantics, exit conditions),
**minor** for new commands or references, **patch** for fixes and copy. Update
`CHANGELOG.md` with every release; the `version` field in `state.json` guards
migrations (see `load_state()` for the v1→v2 example).
