# /update-recursive-kg

Automate the full release loop for the Recursive Mono KG custom font.

## Trigger

User says something like:
- "update recursive kg"
- "build and release recursive font"
- "bump recursive font version"
- "/update-recursive-kg"

## Workflow

### 1. Check repo state

- `cd /Users/kg/dev/oss/recursive-code-config`
- Check `git status`
- **If uncommitted changes exist:** warn the user but continue anyway
- **If working tree is clean:** warn the user that there are no changes to release and ask if they want to proceed anyway (they might want to bump version without config changes)

### 2. Auto-increment version

- Read `Version:` from `premade-configs/config.kg.yaml`
- Increment by 1 (e.g., "37" → "38")
- Update the file

### 3. Commit changes

- `git add -A`
- `git commit -m "bump version to <new_version> for new release"`
- If nothing to commit (no changes at all), still proceed — the version bump itself is the change

### 4. Build fonts

- `cd /Users/kg/dev/oss/recursive-code-config/fonts`
- Delete old font files in `RecursiveKG/` first to avoid stale files
- Build: `../venv/bin/python3 ../scripts/instantiate-code-fonts.py ../premade-configs/config.kg.yaml`
- Verify all 8 font files exist:
  - Regular, Italic, Semibold, SemiboldItalic, Bold, BoldItalic, Black, BlackItalic

### 5. Create release zip

- `cd /Users/kg/dev/oss/recursive-code-config/fonts`
- `zip -r -X /tmp/recursive-<version>.zip RecursiveKG`
- Calculate SHA256: `shasum -a 256 /tmp/recursive-<version>.zip`

### 6. Create GitHub release

- `gh release create v<version> -R kaushikgopal/recursive-code-config --title "Recursive Mono KG v<version>" --notes "Updated Recursive Mono KG font build" /tmp/recursive-<version>.zip`
- **If release already exists:** warn user, then force-update by deleting the existing release first:
  - `gh release delete v<version> -R kaushikgopal/recursive-code-config --yes`
  - Then recreate it

### 7. Update homebrew-tools cask

- Edit `/Users/kg/dev/oss/homebrew-tools/Casks/font-recursive-kg.rb`:
  - Update `version`
  - Update `sha256`
  - Update `url` to point to new release zip
- Commit: `git add Casks/font-recursive-kg.rb && git commit -m "update: recursive kg <version>"`
- Push: `git push origin master`

### 8. Update .brewfile

- Check if `cask "kaushikgopal/tools/font-recursive-kg"` exists in both:
  - `/Users/kg/.Brewfile`
  - `/Users/kg/.brewfile`
- If missing, add it under the `######## Fonts` section
- If already present, no change needed

### 9. Push recursive-code-config

- `cd /Users/kg/dev/oss/recursive-code-config`
- `git push origin main`

### 10. Verify

- Confirm GitHub release URL is accessible
- Confirm homebrew-tools cask has correct version/sha
- Report success to user with install command:
  ```
  brew install --cask kaushikgopal/tools/font-recursive-kg
  ```

## Error Handling

- **Build fails:** Stop and report error output
- **GitHub release fails (not "already exists"):** Stop and report
- **Homebrew push fails:** Stop and report
- **Missing font files after build:** Stop and report which files are missing

## Paths (hardcoded)

- Config repo: `/Users/kg/dev/oss/recursive-code-config`
- Homebrew tools: `/Users/kg/dev/oss/homebrew-tools`
- Brewfiles: `/Users/kg/.Brewfile`, `/Users/kg/.brewfile`
- GitHub repo: `kaushikgopal/recursive-code-config`
- Homebrew tap repo: `kaushikgopal/homebrew-tools`
- Python venv: `/Users/kg/dev/oss/recursive-code-config/venv/bin/python3`

## Notes

- The skill assumes `gh` CLI is authenticated and has `workflow` scope
- The skill assumes the user has push access to both repos
- The skill does NOT check ghostty config — the user is responsible for updating `config.kg.yaml` before triggering this skill
- The skill always bumps version even if no other config changes exist
