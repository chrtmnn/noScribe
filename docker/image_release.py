"""Decide which moving tags the current GitHub Actions ref may publish.

- latest: only the highest stable version and image revision
- <version>: for a revision tag v<version>-r<N>, only the highest revision
  of that version (a plain v<version> tag already gets it from the tag itself)
"""

import os
import re
import subprocess


RELEASE_TAG = re.compile(r"v([0-9]+(?:\.[0-9]+)*)(?:-r([0-9]+))?")


def stable_release_key(tag):
    """Compare numeric release versions and optional Docker image revisions."""
    match = RELEASE_TAG.fullmatch(tag)
    if match is None:
        return None
    version = list(map(int, match[1].split(".")))
    while len(version) > 1 and version[-1] == 0:
        version.pop()
    return tuple(version), int(match[2] or 0)


def _release_tag(ref):
    if not ref.startswith("refs/tags/"):
        return None
    return ref.removeprefix("refs/tags/")


def is_latest_release(ref, tags):
    tag = _release_tag(ref)
    current = stable_release_key(tag) if tag else None
    if current is None or tag not in tags:
        return False
    stable = [key for name in tags if (key := stable_release_key(name)) is not None]
    return current == max(stable)


def version_tag(ref, tags):
    """Return the moving <version> tag a revision tag may publish, or ""."""
    tag = _release_tag(ref)
    match = RELEASE_TAG.fullmatch(tag) if tag else None
    if match is None or match[2] is None or tag not in tags:
        return ""
    current = stable_release_key(tag)
    same_version = [key for name in tags
                    if (key := stable_release_key(name)) is not None and key[0] == current[0]]
    return match[1] if current == max(same_version) else ""


def main():
    ref = os.environ["GITHUB_REF"]
    latest = False
    version = ""
    tag = _release_tag(ref)
    if tag and stable_release_key(tag) is not None:
        # Read remote tags so shallow checkouts and long builds use current data.
        refs = subprocess.check_output(
            ["git", "ls-remote", "--tags", "--refs", "origin", "refs/tags/v*"],
            text=True,
        )
        tags = [line.split("\t", 1)[1].removeprefix("refs/tags/")
                for line in refs.splitlines()]
        latest = is_latest_release(ref, tags)
        version = version_tag(ref, tags)
    print(f"latest={str(latest).lower()}")
    print(f"version={version}")


if __name__ == "__main__":
    main()
