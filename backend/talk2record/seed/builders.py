"""Bookkeeping helpers shared by the seeding pipeline.

The seeding pipeline only provisions platform/admin reference data — see
``reference_data.py`` for what is actually written. This module just exposes
the lightweight types the orchestrator and the management command share.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(slots=True)
class SeedOptions:
    """Runtime options for the ``seed_data`` command.

    Currently a no-op placeholder — the seed only writes platform/admin
    reference data and does not need any tenant-related arguments. The class
    is kept so that future toggles (e.g. ``--reset``) can be added without
    plumbing every call site.
    """


@dataclass(slots=True)
class SeedSummary:
    counters: dict[str, dict[str, int]] = field(default_factory=dict)

    def bump(
        self,
        bucket: str,
        *,
        created: bool | int = False,
        updated: bool | int = False,
    ) -> None:
        counter = self.counters.setdefault(bucket, {"created": 0, "updated": 0})
        if created:
            counter["created"] += int(created)
        if updated:
            counter["updated"] += int(updated)

    def rows(self) -> list[tuple[str, int, int]]:
        return [
            (bucket, values["created"], values["updated"])
            for bucket, values in sorted(self.counters.items())
            if values["created"] or values["updated"]
        ]
