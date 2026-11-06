#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


def bump_semver(old_name: str, bump_type: str, explicit_name: str | None = None) -> str:
    if explicit_name:
        return explicit_name
    semver = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", old_name)
    if not semver:
        return old_name
    major = int(semver.group(1))
    minor = int(semver.group(2))
    patch = int(semver.group(3))
    rest = semver.group(4)
    if bump_type == "major":
        return f"{major + 1}.0.0{rest}"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0{rest}"
    else:  # patch (default)
        return f"{major}.{minor}.{patch + 1}{rest}"


def bump_gradle_properties(prop_path: Path, args) -> bool:
    content = prop_path.read_text(encoding="utf-8")
    code_match = re.search(r"((?:APP_)?VERSION_CODE)=(\d+)", content)
    if not code_match:
        return False

    code_key = code_match.group(1)
    old_code = int(code_match.group(2))
    new_code = old_code + 1
    content = re.sub(rf"{code_key}=\d+", f"{code_key}={new_code}", content)

    old_name = None
    new_name = None
    name_match = re.search(r"((?:APP_)?VERSION_NAME)=(\S+)", content)
    if name_match:
        name_key = name_match.group(1)
        old_name = name_match.group(2)
        if not args.code_only:
            bump_type = "major" if args.major else ("minor" if args.minor else "patch")
            new_name = bump_semver(old_name, bump_type, args.name)
            if new_name != old_name:
                content = re.sub(rf"{name_key}=\S+", f"{name_key}={new_name}", content)

    prop_path.write_text(content, encoding="utf-8")
    print(f"Updated {prop_path.name}:")
    print(f"  {code_key}: {old_code} -> {new_code}")
    if old_name:
        if new_name and new_name != old_name:
            print(f"  {name_key}: {old_name} -> {new_name}")
        else:
            print(f"  {name_key}: {old_name} (unchanged)")
    return True


def bump_build_gradle_kts(build_path: Path, args) -> bool:
    content = build_path.read_text(encoding="utf-8")
    code_match = re.search(r"(versionCode\s*=\s*)(\d+)", content)
    name_match = re.search(r'(versionName\s*=\s*")([^"]+)(")', content)
    if not code_match and not name_match:
        return False

    old_code = None
    new_code = None
    if code_match:
        old_code = int(code_match.group(2))
        new_code = old_code + 1
        content = content[:code_match.start(2)] + str(new_code) + content[code_match.end(2):]

    old_name = None
    new_name = None
    if name_match and not args.code_only:
        old_name = name_match.group(2)
        bump_type = "major" if args.major else ("minor" if args.minor else "patch")
        new_name = bump_semver(old_name, bump_type, args.name)
        if new_name != old_name:
            # Re-search after code modification in case indices changed
            content = re.sub(r'(versionName\s*=\s*")[^"]+(")', rf"\g<1>{new_name}\g<2>", content)

    build_path.write_text(content, encoding="utf-8")
    print(f"Updated {build_path.name}:")
    if old_code is not None:
        print(f"  versionCode: {old_code} -> {new_code}")
    if old_name:
        if new_name and new_name != old_name:
            print(f"  versionName: {old_name} -> {new_name}")
        else:
            print(f"  versionName: {old_name} (unchanged)")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Bump versionCode and versionName in gradle.properties or build.gradle.kts"
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Explicit version name to set (e.g. 0.5.0)",
    )
    parser.add_argument(
        "--major",
        action="store_true",
        help="Bump major version (e.g. 0.4.0 -> 1.0.0)",
    )
    parser.add_argument(
        "--minor",
        action="store_true",
        help="Bump minor version (e.g. 0.4.0 -> 0.5.0)",
    )
    parser.add_argument(
        "--patch",
        action="store_true",
        help="Bump patch version (e.g. 0.4.0 -> 0.4.1)",
    )
    parser.add_argument(
        "--code-only",
        action="store_true",
        help="Only increment versionCode without changing versionName",
    )
    args = parser.parse_args()

    cwd = Path.cwd()

    # 1. Check gradle.properties in current directory
    prop_path = cwd / "gradle.properties"
    if prop_path.exists() and bump_gradle_properties(prop_path, args):
        return

    # 2. Check build.gradle.kts in standard locations
    for candidate in [
        cwd / "app" / "build.gradle.kts",
        cwd / "automotive" / "build.gradle.kts",
        cwd / "build.gradle.kts",
    ]:
        if candidate.exists() and bump_build_gradle_kts(candidate, args):
            return

    # 3. Check local.properties as a fallback for VERSION_CODE
    local_prop = cwd / "local.properties"
    if local_prop.exists() and bump_gradle_properties(local_prop, args):
        return

    print(
        f"Error: No version fields found to bump in {cwd}. "
        f"Expected APP_VERSION_CODE / VERSION_CODE in gradle.properties or versionCode in build.gradle.kts.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
