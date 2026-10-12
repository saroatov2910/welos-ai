from stats import load_events


def test_load_events_reads_every_line(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text('{"event": "decision_created"}\n{"event": "card_blocked"}\n')

    events = load_events(str(log))

    assert len(events) == 2
    assert events[0]["event"] == "decision_created"


def test_load_events_skips_empty_lines(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text('{"event": "decision_created"}\n\n\n{"event": "card_blocked"}\n')

    assert len(load_events(str(log))) == 2
