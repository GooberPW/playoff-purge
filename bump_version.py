#!/usr/bin/env python3
"""
Version bumping utility for PlayoffPurge.

Usage:
    python bump_version.py patch   # 1.0.0 -> 1.0.1 (bug fixes)
    python bump_version.py minor   # 1.0.0 -> 1.1.0 (new features)
    python bump_version.py major   # 1.0.0 -> 2.0.0 (breaking changes)
"""
import sys
from pathlib import Path


def read_version():
    """Read current version from VERSION file."""
    version_file = Path(__file__).parent / "VERSION"
    return version_file.read_text().strip()


def write_version(version):
    """Write new version to VERSION file."""
    version_file = Path(__file__).parent / "VERSION"
    version_file.write_text(version + "\n")
    print(f"✅ Version updated to {version}")


def bump_version(bump_type):
    """
    Bump version based on type.
    
    Args:
        bump_type: 'major', 'minor', or 'patch'
    """
    current = read_version()
    
    try:
        major, minor, patch = map(int, current.split('.'))
    except ValueError:
        print(f"❌ Invalid version format in VERSION file: {current}")
        print("   Expected format: X.Y.Z (e.g., 1.0.0)")
        sys.exit(1)
    
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        print(f"❌ Invalid bump type: {bump_type}")
        print("   Use: major, minor, or patch")
        sys.exit(1)
    
    new_version = f"{major}.{minor}.{patch}"
    print(f"📦 Bumping version: {current} → {new_version}")
    write_version(new_version)
    return new_version


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py [major|minor|patch]")
        print("\nExamples:")
        print("  python bump_version.py patch   # Bug fixes (1.0.0 -> 1.0.1)")
        print("  python bump_version.py minor   # New features (1.0.0 -> 1.1.0)")
        print("  python bump_version.py major   # Breaking changes (1.0.0 -> 2.0.0)")
        sys.exit(1)
    
    bump_type = sys.argv[1].lower()
    bump_version(bump_type)
