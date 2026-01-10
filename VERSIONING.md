# Versioning System

PlayoffPurge uses semantic versioning (MAJOR.MINOR.PATCH) displayed in the footer of all pages.

## Version Format

**Format:** `X.Y.Z`
- **X (MAJOR)**: Breaking changes, major rewrites
- **Y (MINOR)**: New features, enhancements
- **Z (PATCH)**: Bug fixes, small improvements

**Example:** `1.2.3` = version 1, with 2 feature releases and 3 patches

---

## Manual Version Bumping

Use the `bump_version.py` script to manually increment versions:

```bash
# Patch version (bug fixes)
python bump_version.py patch
# 1.0.0 → 1.0.1

# Minor version (new features)
python bump_version.py minor
# 1.0.0 → 1.1.0

# Major version (breaking changes)
python bump_version.py major
# 1.0.0 → 2.0.0
```

---

## Git Hooks (Optional Auto-Increment)

To automatically increment patch version on every commit:

### 1. Create Git Hook

Create `.git/hooks/pre-commit` (no extension):

```bash
#!/bin/bash
# Auto-increment patch version on commit

python bump_version.py patch

# Stage the VERSION file
git add VERSION

exit 0
```

### 2. Make Executable

```bash
# Linux/Mac
chmod +x .git/hooks/pre-commit

# Windows (Git Bash)
chmod +x .git/hooks/pre-commit
```

### 3. How It Works

Every time you commit:
- Version automatically increments (1.0.0 → 1.0.1 → 1.0.2...)
- VERSION file is updated and staged
- Commit proceeds with new version

### 4. When to Bump Minor/Major

When you want to release a **new feature** or **breaking change**:

```bash
# BEFORE committing, bump manually
python bump_version.py minor  # or major

# Then commit as usual
git add .
git commit -m "feat: add new draft feature"
# Auto-increments to next patch (e.g., 1.1.0 → 1.1.1)
```

---

## Disabling Auto-Increment

To skip auto-increment for a specific commit:

```bash
git commit -m "docs: update README" --no-verify
```

---

## Version Display

Version appears in footer:
```
PlayoffPurge Dashboard v1.2.3 • Powered by Google Sheets
```

The version is read from `VERSION` file at runtime, so no server restart needed after version bumps.

---

## Best Practices

### When to Bump PATCH (1.0.0 → 1.0.1)
- Bug fixes
- Small CSS tweaks
- Performance improvements
- Documentation updates

**With auto-increment**: Happens automatically on every commit

### When to Bump MINOR (1.0.0 → 1.1.0)
- New features
- API additions
- UI enhancements
- New pages/functionality

**Manual**: `python bump_version.py minor` before committing

### When to Bump MAJOR (1.0.0 → 2.0.0)
- Breaking changes
- Complete rewrites
- API changes that break compatibility
- Major architectural changes

**Manual**: `python bump_version.py major` before committing

---

## Examples

```bash
# Workflow without auto-increment
git add .
python bump_version.py patch
git add VERSION
git commit -m "fix: resolve draft button issue"
git push

# Workflow with auto-increment (hook installed)
git add .
git commit -m "fix: resolve draft button issue"
# Version auto-increments from 1.0.0 → 1.0.1
git push

# New feature workflow (with auto-increment)
python bump_version.py minor  # 1.0.5 → 1.1.0
git add .
git commit -m "feat: add snake draft board"
# Auto-increments to 1.1.1
git push
```

---

## File Locations

- **Version file**: `VERSION` (single line with version number)
- **Bump script**: `bump_version.py`
- **Config reader**: `config.py` (property `app_version`)
- **Display**: All page footers (via `base.html` template)
