"""Parses .kfc script files into command tuples.

Supported commands (case-insensitive keywords):
  Board
    <row0>
    <row1>
    ...
  click <x> <y>
  wait <seconds>
  print board
"""


def parse_script(lines):
    """Returns a list of command tuples:
      ('board', [row_string, ...])
      ('click', x: int, y: int)
      ('wait', seconds: float)
      ('print_board',)
    """
    commands = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue

        lower = line.lower()

        if lower == "board":
            i += 1
            rows = []
            while i < len(lines) and lines[i].strip() and not _is_command(lines[i].strip()):
                rows.append(lines[i].strip())
                i += 1
            commands.append(("board", rows))

        elif lower.startswith("click "):
            parts = line.split()
            commands.append(("click", int(parts[1]), int(parts[2])))
            i += 1

        elif lower.startswith("wait "):
            parts = line.split()
            commands.append(("wait", float(parts[1])))
            i += 1

        elif lower == "print board":
            commands.append(("print_board",))
            i += 1

        else:
            raise ValueError(f"Unknown DSL command: {line!r}")

    return commands


def _is_command(line):
    low = line.lower()
    return (
        low == "board"
        or low.startswith("click ")
        or low.startswith("wait ")
        or low == "print board"
    )
