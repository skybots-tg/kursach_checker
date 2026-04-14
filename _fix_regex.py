"""One-time script: restore ALLOWED_CHARS_RE using \\u escapes in raw strings."""
import pathlib, re as _re

p = pathlib.Path("app/rules_engine/checks_content.py")
data = p.read_bytes()

# Find the block: ALLOWED_CHARS_RE = re.compile( ... )
# Use a regex to match it regardless of line endings and content
pattern = _re.compile(
    rb'ALLOWED_CHARS_RE\s*=\s*re\.compile\(.*?\)\s*\)',
    _re.DOTALL,
)
m = pattern.search(data)
if not m:
    print("ERROR: Could not find ALLOWED_CHARS_RE block")
    exit(1)

print(f"Found block at [{m.start()}:{m.end()}]")
print(f"Content preview: {data[m.start():m.start()+40]!r}")

new_block = (
    b'ALLOWED_CHARS_RE = re.compile(\r\n'
    b'    r"[\\u0000-\\u007F"\r\n'
    b'    r"\\u0400-\\u04FF"\r\n'
    b'    r"\\u00A0-\\u00FF"\r\n'
    b'    r"\\u0370-\\u03FF"\r\n'
    b'    r"\\u2010-\\u2015"\r\n'
    b'    r"\\u2018\\u2019\\u201C\\u201D\\u00AB\\u00BB\\u2026"\r\n'
    b'    r"\\u2116\\u0301"\r\n'
    b'    r"\\u2022\\u25CF\\u25CB\\u25A0\\u25AA\\u2023"\r\n'
    b'    r"\\u2070-\\u209F"\r\n'
    b'    r"\\u2200-\\u22FF"\r\n'
    b'    r"\\u2150-\\u218F"\r\n'
    b'    r"]"\r\n'
    b')'
)

data = data[:m.start()] + new_block + data[m.end():]

# Verify no null bytes remain
nulls = [i for i, b in enumerate(data) if b == 0]
if nulls:
    print(f"WARNING: {len(nulls)} null bytes remain")
else:
    print("OK: no null bytes")

p.write_bytes(data)
print("Done: ALLOWED_CHARS_RE restored")
