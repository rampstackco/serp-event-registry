#!/usr/bin/env python3
"""Validate data/events.jsonl against schema/event.schema.json and the registry rules.

Every check fails loudly with the offending line, the event_id where one is
available, and the reason. The validator never rewrites the data file. If the
file is out of order it says so and exits non zero rather than sorting it
silently, because the file is the canon and a silent fix would hide a bad edit.

Requires: Python 3.9 or newer, jsonschema.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.stderr.write(
        "error: jsonschema is not installed. Run: python -m pip install jsonschema\n"
    )
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "events.jsonl"
SCHEMA_PATH = REPO_ROOT / "schema" / "event.schema.json"

# Registry window floor. Nothing before the first public conversational answer
# surface belongs in this file.
EARLIEST_EVENT_DATE = date(2022, 11, 1)

# The only event_type permitted to omit source_urls.
UNSOURCED_TYPE = "sensor_spike"


class Report:
    """Collects failures so one run reports every problem, not just the first."""

    def __init__(self, data_path: Path) -> None:
        self.rel_path = data_path.name
        self.errors: list[str] = []

    def fail(self, line_no: int, event_id: str | None, reason: str) -> None:
        tag = f" [{event_id}]" if event_id else ""
        self.errors.append(f"{self.rel_path}:{line_no}:{tag} {reason}")

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        sys.stderr.write(f"error: schema not found at {SCHEMA_PATH}\n")
        raise SystemExit(2)
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_rows(report: Report) -> list[tuple[int, dict]]:
    """Parse every non empty line. Blank lines inside the file are an error."""
    if not DATA_PATH.exists():
        sys.stderr.write(f"error: data file not found at {DATA_PATH}\n")
        raise SystemExit(2)

    rows: list[tuple[int, dict]] = []
    raw = DATA_PATH.read_text(encoding="utf-8")

    if raw and not raw.endswith("\n"):
        report.fail(0, None, "file does not end with a newline")

    for line_no, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            report.fail(line_no, None, "blank line; every line must hold one event object")
            continue
        if line != line.rstrip():
            report.fail(line_no, None, "line has trailing whitespace")
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            report.fail(line_no, None, f"line is not valid JSON: {exc.msg} at column {exc.colno}")
            continue
        if not isinstance(parsed, dict):
            report.fail(line_no, None, "line is valid JSON but is not an object")
            continue
        rows.append((line_no, parsed))
    return rows


def check_schema(rows: list[tuple[int, dict]], schema: dict, report: Report) -> None:
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    for line_no, row in rows:
        event_id = row.get("event_id") if isinstance(row.get("event_id"), str) else None
        for error in sorted(validator.iter_errors(row), key=lambda e: list(e.path)):
            location = "/".join(str(part) for part in error.path) or "(root)"
            report.fail(line_no, event_id, f"schema violation at {location}: {error.message}")


def check_ids(rows: list[tuple[int, dict]], report: Report) -> None:
    seen: dict[str, int] = {}
    for line_no, row in rows:
        event_id = row.get("event_id")
        event_date = row.get("event_date")
        if not isinstance(event_id, str):
            continue
        if event_id in seen:
            report.fail(
                line_no,
                event_id,
                f"duplicate event_id; already used on line {seen[event_id]}",
            )
        else:
            seen[event_id] = line_no

        if isinstance(event_date, str) and not event_id.startswith(f"{event_date}-"):
            report.fail(
                line_no,
                event_id,
                f"slug date prefix does not match event_date {event_date}",
            )


def check_dates(rows: list[tuple[int, dict]], report: Report, today: date) -> None:
    for line_no, row in rows:
        event_id = row.get("event_id") if isinstance(row.get("event_id"), str) else None

        event_date = parse_iso_date(row.get("event_date", ""))
        if event_date is None:
            report.fail(line_no, event_id, f"event_date is not a valid ISO date: {row.get('event_date')!r}")
        else:
            if event_date > today:
                report.fail(line_no, event_id, f"event_date {event_date} is in the future (today is {today})")
            if event_date < EARLIEST_EVENT_DATE:
                report.fail(
                    line_no,
                    event_id,
                    f"event_date {event_date} is before the registry floor {EARLIEST_EVENT_DATE}",
                )

        added = parse_iso_date(row.get("added", ""))
        last_updated = parse_iso_date(row.get("last_updated", ""))
        if added is None:
            report.fail(line_no, event_id, f"added is not a valid ISO date: {row.get('added')!r}")
        elif added > today:
            report.fail(line_no, event_id, f"added {added} is in the future (today is {today})")
        if last_updated is None:
            report.fail(line_no, event_id, f"last_updated is not a valid ISO date: {row.get('last_updated')!r}")
        elif last_updated > today:
            report.fail(line_no, event_id, f"last_updated {last_updated} is in the future (today is {today})")
        if added and last_updated and last_updated < added:
            report.fail(line_no, event_id, f"last_updated {last_updated} is earlier than added {added}")


def check_sources(rows: list[tuple[int, dict]], report: Report) -> None:
    for line_no, row in rows:
        event_id = row.get("event_id") if isinstance(row.get("event_id"), str) else None
        event_type = row.get("event_type")
        sources = row.get("source_urls")

        if event_type == UNSOURCED_TYPE:
            if sources is not None and not isinstance(sources, list):
                report.fail(line_no, event_id, "source_urls must be a list when present")
            continue

        if not isinstance(sources, list) or not sources:
            report.fail(
                line_no,
                event_id,
                f"event_type {event_type!r} requires at least one source_url; only {UNSOURCED_TYPE} may omit it",
            )
            continue

        for url in sources:
            if not isinstance(url, str) or not url.startswith("https://"):
                report.fail(line_no, event_id, f"source_url is not https: {url!r}")


def check_related(rows: list[tuple[int, dict]], report: Report) -> None:
    known = {row.get("event_id") for _, row in rows if isinstance(row.get("event_id"), str)}
    for line_no, row in rows:
        event_id = row.get("event_id") if isinstance(row.get("event_id"), str) else None
        related = row.get("related_events")
        if related is None:
            continue
        if not isinstance(related, list):
            report.fail(line_no, event_id, "related_events must be a list")
            continue
        for pointer in related:
            if pointer == event_id:
                report.fail(line_no, event_id, "related_events points at its own event_id")
            elif pointer not in known:
                report.fail(line_no, event_id, f"related_events pointer does not resolve: {pointer!r}")


def check_order(rows: list[tuple[int, dict]], report: Report) -> None:
    """The file must read in ascending event_date, tie broken by event_id."""
    previous: tuple[str, str] | None = None
    previous_line = 0
    for line_no, row in rows:
        event_date = row.get("event_date")
        event_id = row.get("event_id")
        if not isinstance(event_date, str) or not isinstance(event_id, str):
            continue
        current = (event_date, event_id)
        if previous is not None and current <= previous:
            report.fail(
                line_no,
                event_id,
                (
                    f"file is out of order: ({event_date}, {event_id}) does not sort after "
                    f"({previous[0]}, {previous[1]}) on line {previous_line}. "
                    "Sort by event_date ascending, then event_id ascending. "
                    "The validator will not reorder the file for you."
                ),
            )
        previous = current
        previous_line = line_no


def summarize(rows: list[tuple[int, dict]]) -> str:
    types = Counter(row.get("event_type") for _, row in rows)
    attributions = Counter(row.get("attribution") for _, row in rows)
    surfaces: Counter = Counter()
    for _, row in rows:
        for surface in row.get("surface", []) or []:
            surfaces[surface] += 1

    def render(counter: Counter) -> str:
        return ", ".join(f"{key}={value}" for key, value in sorted(counter.items()))

    return "\n".join(
        [
            f"rows: {len(rows)}",
            f"event_type: {render(types)}",
            f"attribution: {render(attributions)}",
            f"surface: {render(surfaces)}",
        ]
    )


def main() -> int:
    today = datetime.now(timezone.utc).date()
    report = Report(DATA_PATH)
    schema = load_schema()
    rows = read_rows(report)

    check_schema(rows, schema, report)
    check_ids(rows, report)
    check_dates(rows, report, today)
    check_sources(rows, report)
    check_related(rows, report)
    check_order(rows, report)

    if not report.ok:
        sys.stderr.write(f"FAIL: {len(report.errors)} problem(s) in {DATA_PATH}\n\n")
        for error in report.errors:
            sys.stderr.write(f"  {error}\n")
        sys.stderr.write("\n")
        return 1

    sys.stdout.write(f"OK: {DATA_PATH.name} passed every check\n")
    sys.stdout.write(summarize(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
