import json
import sys
from collections import Counter
from pathlib import Path


def load_events(path: str) -> list[dict]:
    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events
