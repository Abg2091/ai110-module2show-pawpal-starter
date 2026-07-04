"""Core logic layer for PawPal+.

Class skeleton generated from diagrams/uml.mmd. Attributes and method
signatures are in place; behavior is implemented in a later step.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, IntEnum


# ── Enumerations ──────────────────────────────────────────────────────────


class Priority(IntEnum):
    """Ordered LOW < MEDIUM < HIGH — used for sorting."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TaskCategory(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDICATION = "medication"
    GROOMING = "grooming"
    ENRICHMENT = "enrichment"
    OTHER = "other"


# ── Core domain classes ───────────────────────────────────────────────────


class Owner:
    def __init__(self, name: str, available_minutes: int, preferences: str, pet: Pet):
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences
        self.pet = pet
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def get_tasks(self) -> list[Task]:
        pass


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age_years: int


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority
    category: TaskCategory
    is_recurring: bool = False
    frequency: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def is_high_priority(self) -> bool:
        pass

    def to_dict(self) -> dict:
        pass


# ── Scheduling classes ────────────────────────────────────────────────────


class Scheduler:
    def __init__(self, owner: Owner, start_time: str, plan_date: str):
        self.owner = owner
        self.pet = owner.pet
        self.start_time = start_time
        self.plan_date = plan_date

    def generate_plan(self) -> DailyPlan:
        pass

    def _sort_by_priority(self, tasks: list) -> list:
        pass

    def _filter_by_time(self, tasks: list, budget: int) -> list:
        pass

    def _resolve_conflicts(self, entries: list) -> list:
        pass

    def _explain(self, task: Task, slot: str) -> str:
        pass


@dataclass
class DailyPlan:
    pet: Pet
    date: str
    entries: list[ScheduledEntry] = field(default_factory=list)
    total_duration_minutes: int = 0

    def add_entry(self, entry: ScheduledEntry) -> None:
        pass

    def get_summary(self) -> str:
        pass

    def to_table(self) -> list:
        pass


@dataclass
class ScheduledEntry:
    task: Task
    start_time: str
    end_time: str
    reason: str

    def duration_minutes(self) -> int:
        pass
