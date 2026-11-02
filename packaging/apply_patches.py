"""Apply our pinned text patches exactly; no Git installation required."""
from pathlib import Path, PurePosixPath
import re
import sys


def apply_patch(root, patch):
    root = Path(root).resolve()
    lines = Path(patch).read_text(encoding='utf-8').splitlines(keepends=True)
    changes = {}
    i = 0
    while i < len(lines):
        if not lines[i].startswith('--- a/'):
            i += 1
            continue
        old_name = lines[i][6:].strip()
        i += 1
        if i >= len(lines) or lines[i] != '+++ b/' + old_name + '\n':
            raise ValueError('Only same-path text changes are supported')
        relative = PurePosixPath(old_name)
        if relative.is_absolute() or '..' in relative.parts or ':' in old_name or '\\' in old_name:
            raise ValueError('Unsafe patch path')
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or target.is_symlink():
            raise ValueError('Patch path escapes receiver')
        original = target.read_text(encoding='utf-8').splitlines(keepends=True)
        output, cursor = [], 0
        i += 1
        while i < len(lines) and lines[i].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*\n', lines[i])
            if not match:
                raise ValueError('Invalid hunk header')
            start, old_count, new_start, new_count = [int(v) if v is not None else 1 for v in match.groups()]
            start = start - 1 if old_count else start
            if start < cursor or start > len(original):
                raise ValueError('Overlapping or out-of-bounds hunk')
            output.extend(original[cursor:start])
            if len(output) != (new_start - 1 if new_count else new_start):
                raise ValueError('New hunk offset mismatch')
            cursor = start
            removed = added = 0
            i += 1
            while i < len(lines) and lines[i][:1] in (' ', '+', '-') and not lines[i].startswith('--- a/'):
                line = lines[i]
                if line[0] in ' -':
                    if cursor >= len(original) or original[cursor] != line[1:]:
                        raise ValueError(f'Patch context mismatch in {old_name}:{cursor + 1}')
                    cursor += 1
                    removed += 1
                if line[0] in ' +':
                    output.append(line[1:])
                    added += 1
                i += 1
            if (removed, added) != (old_count, new_count):
                raise ValueError('Hunk line counts do not match')
        output.extend(original[cursor:])
        if target in changes:
            raise ValueError('Duplicate file section')
        changes[target] = ''.join(output)
    if not changes:
        raise ValueError('No changes found')
    for target, content in changes.items():
        target.write_text(content, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    for patch in sys.argv[2:]:
        apply_patch(sys.argv[1], patch)
