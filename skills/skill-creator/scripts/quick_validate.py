#!/usr/bin/env python3
"""Quick validation script for skills.

This validator intentionally keeps dependencies light. It uses PyYAML when
available, but can also validate the simple frontmatter used by local skills
without requiring any third-party package.
"""

import sys
import os
import re
from pathlib import Path

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None


def parse_simple_frontmatter(frontmatter_text):
    """Parse a small subset of YAML used by local SKILL.md files.

    Supports `key: value` pairs and block strings like:

    description: >-
      line 1
      line 2
    """
    result = {}
    lines = frontmatter_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if ":" not in line:
            raise ValueError(f"Unsupported frontmatter line: {line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value in {">", ">-", "|", "|-"}:
            block_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if next_line.startswith(" ") or next_line.startswith("\t"):
                    block_lines.append(next_line.lstrip())
                    i += 1
                    continue
                break
            result[key] = "\n".join(block_lines).strip()
            continue

        if value.startswith(('"', "'")) and value.endswith(('"', "'")) and len(value) >= 2:
            value = value[1:-1]

        result[key] = value
        i += 1

    return result

def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter
    content = skill_md.read_text(encoding='utf-8')
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        if yaml is not None:
            frontmatter = yaml.safe_load(frontmatter_text)
        else:
            frontmatter = parse_simple_frontmatter(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except Exception as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Define allowed properties
    ALLOWED_PROPERTIES = {
        'name',
        'description',
        'license',
        'allowed-tools',
        'metadata',
        'compatibility',
        'argument-hint',
    }

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (kebab-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate compatibility field if present (optional)
    compatibility = frontmatter.get('compatibility', '')
    if compatibility:
        if not isinstance(compatibility, str):
            return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
        if len(compatibility) > 500:
            return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."

    argument_hint = frontmatter.get('argument-hint', '')
    if argument_hint and not isinstance(argument_hint, str):
        return False, f"argument-hint must be a string, got {type(argument_hint).__name__}"

    return True, "Skill is valid!"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)
    
    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
