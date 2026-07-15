"""Generic marker-delimited section extraction. Not specific to the
"Board:" section, so it's reused for "Commands:" too without
duplicating this logic.
"""
from typing import List, Optional


def read_lines(stream) -> List[str]:
    return [line.strip() for line in stream.read().splitlines()]


def read_section(lines: List[str], start_marker: str, end_marker: Optional[str] = None) -> List[str]:
    start = lines.index(start_marker) + 1
    section = []
    i = start
    while i < len(lines) and lines[i] != end_marker:
        if lines[i]:
            section.append(lines[i])
        i += 1
    return section
