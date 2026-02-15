"""Pre-commit helper: ensure any .py file defining VERBOSE uses VERBOSE = 1.

Usage:
  python -m exdrf_util.check_verbose [--fix] <file.py> ...
  With --fix, rewrites VERBOSE = n to VERBOSE = 1 in place (autofix).
"""

import re
import sys

# Match VERBOSE = <integer> at line start (optional leading/trailing
# space/comments).
VERBOSE_PATTERN = re.compile(
    r"^\s*VERBOSE\s*=\s*(\d+)(?:\s*#.*)?\s*$", re.MULTILINE
)
# Capture up to the number for substitution (fix mode).
VERBOSE_FIX_PATTERN = re.compile(r"^(\s*VERBOSE\s*=\s*)\d+", re.MULTILINE)


def check_file(path: str) -> list[tuple[int, int]]:
    """Find lines where VERBOSE is set to a value other than 1.

    Args:
        path: Path to a Python source file.

    Returns:
        List of (line_number, value) for each VERBOSE = x with x != 1.
        Empty if file is ok or not readable.
    """
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except OSError as e:
        print("%s: could not read file: %s" % (path, e), file=sys.stderr)
        return []

    violations = []
    for match in VERBOSE_PATTERN.finditer(text):
        value = int(match.group(1))
        if value != 1:
            line_no = text[: match.start()].count("\n") + 1
            violations.append((line_no, value))
    return violations


def fix_file(path: str) -> bool:
    """Rewrite VERBOSE = n to VERBOSE = 1 in place. Return True if changed."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except OSError as e:
        print("%s: could not read file: %s" % (path, e), file=sys.stderr)
        return False

    new_text = VERBOSE_FIX_PATTERN.sub(r"\g<1>1", text)
    if new_text == text:
        return False
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    return True


def main() -> int:
    """Run the check on files passed as arguments. Exit 1 if any violation."""
    argv = sys.argv[1:]
    fix_mode = bool(argv and argv[0] == "--fix")
    if fix_mode:
        argv = argv[1:]
    paths = [p for p in argv if p.endswith(".py")]

    if fix_mode:
        for path in paths:
            if fix_file(path):
                print("%s: VERBOSE set to 1" % path)
        return 0

    failed = False
    for path in paths:
        for line_no, value in check_file(path):
            print(
                "%s:%d: VERBOSE = %d (must be VERBOSE = 1)"
                % (path, line_no, value)
            )
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
