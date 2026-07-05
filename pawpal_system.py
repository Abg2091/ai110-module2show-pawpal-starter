"""Core logic layer for PawPal+.

Implements the classes from diagrams/uml.mmd and exposes them through an
interactive command-line interface so every feature (owner/pet setup, task
management, plan generation) is operable from the terminal.

Run directly to use the CLI:
    python pawpal_system.py            # interactive menu
    python pawpal_system.py --demo     # seeded, non-interactive walkthrough
"""

from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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


# Categories that must never be dropped by the scheduler's time filter, no
# matter how little budget remains — missing a pet's meds or feeding isn't
# an acceptable tradeoff the way skipping a grooming session is.
MANDATORY_CATEGORIES = frozenset({TaskCategory.MEDICATION, TaskCategory.FEEDING})


# ── Time helpers ──────────────────────────────────────────────────────────

_TIME_FORMAT = "%H:%M"


def _parse_time(value: str) -> datetime:
    """Parse an "HH:MM" string into a datetime."""
    return datetime.strptime(value, _TIME_FORMAT)


def _format_time(moment: datetime) -> str:
    """Format a datetime back into an "HH:MM" string."""
    return moment.strftime(_TIME_FORMAT)


def _add_minutes(value: str, minutes: int) -> str:
    """Return the "HH:MM" time that is `minutes` after `value`."""
    return _format_time(_parse_time(value) + timedelta(minutes=minutes))


# New: date-string helpers, added so recurring tasks can compute a future due
# date (e.g. "daily" = +1 day) the same way the time helpers above already do.
_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str) -> date:
    """Parse a "YYYY-MM-DD" string into a date."""
    return datetime.strptime(value, _DATE_FORMAT).date()


def _add_days(value: str, days: int) -> str:
    """Return the "YYYY-MM-DD" date that is `days` after `value`."""
    return (_parse_date(value) + timedelta(days=days)).isoformat()


# New: frequency -> number of days until a completed recurring task's next
# occurrence, used by Task.next_occurrence() to compute its due date.
_RECURRENCE_INTERVAL_DAYS = {"daily": 1, "weekly": 7}


# ── Core domain classes ───────────────────────────────────────────────────


class Owner:
    def __init__(self, name: str, available_minutes: int, preferences: str, pet: Pet):
        """Create an owner with their available time, preferences, and pet."""
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences
        self.pet = pet
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the owner's task list."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove the task matching the given task's id."""
        self.tasks = [t for t in self.tasks if t.id != task.id]

    def get_tasks(self) -> list[Task]:
        """Return a copy of the owner's current task list."""
        return list(self.tasks)


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age_years: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to the pet's own task list."""
        self.tasks.append(task)


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority
    category: TaskCategory
    is_recurring: bool = False
    frequency: str = ""
    completed: bool = False
    # Repurposed: used to hold the plan_date a recurring task was last reset for;
    # now holds the "YYYY-MM-DD" date this occurrence is due for, since renewal
    # is driven by completion + next_occurrence() rather than a date comparison.
    last_scheduled_date: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def is_high_priority(self) -> bool:
        """Return True if the task's priority is HIGH."""
        return self.priority == Priority.HIGH

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        self.completed = True

    def next_occurrence(self, reference_date: str) -> "Task | None":
        """Return a new Task for the next occurrence, due `frequency` after `reference_date`.

        New: replaces the old approach of resetting this same instance's
        `completed` flag, so a finished occurrence stays as a historical record
        instead of being silently reused for the next cycle.
        """
        interval = _RECURRENCE_INTERVAL_DAYS.get(self.frequency.lower())
        if not self.is_recurring or interval is None:
            return None
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            category=self.category,
            is_recurring=True,
            frequency=self.frequency,
            last_scheduled_date=_add_days(reference_date, interval),
        )

    def to_dict(self) -> dict:
        """Return a plain-dict representation of the task."""
        return {
            "id": self.id,
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.name,
            "category": self.category.value,
            "is_recurring": self.is_recurring,
            "frequency": self.frequency,
            "completed": self.completed,
            "last_scheduled_date": self.last_scheduled_date,
        }


# ── Scheduling classes ────────────────────────────────────────────────────


class Scheduler:
    def __init__(self, owner: Owner, start_time: str, plan_date: str):
        """Create a scheduler for an owner's pet, start time, and plan date."""
        self.owner = owner
        self.pet = owner.pet
        self.start_time = start_time
        self.plan_date = plan_date

    def generate_plan(self) -> DailyPlan:
        """Build a DailyPlan by sorting, filtering, and slotting the owner's tasks."""
        self._carry_forward_tasks()
        tasks = self._sort_by_priority(self.owner.get_tasks())
        tasks = self._filter_by_time(tasks, self.owner.available_minutes)

        entries: list[ScheduledEntry] = []
        current_time = self.start_time
        for task in tasks:
            end_time = _add_minutes(current_time, task.duration_minutes)
            entries.append(
                ScheduledEntry(
                    task=task,
                    start_time=current_time,
                    end_time=end_time,
                    reason=self._explain(task, current_time),
                )
            )
            current_time = end_time

        entries = self._resolve_conflicts(entries)

        plan = DailyPlan(pet=self.pet, date=self.plan_date)
        for entry in entries:
            plan.add_entry(entry)
        return plan

    def _carry_forward_tasks(self) -> None:
        """Spawn the next occurrence for completed recurring tasks; drop other completed tasks.

        Changed from resetting `completed`/`last_scheduled_date` in place on a
        new day to spawning a fresh Task per occurrence, since date-gated
        in-place resets couldn't represent "the next due date" a caller needs.
        """
        for task in self.owner.get_tasks():
            if not task.completed:
                continue
            if task.is_recurring:
                next_task = task.next_occurrence(self.plan_date)
                if next_task is not None:
                    self.owner.add_task(next_task)
            self.owner.remove_task(task)

    def _sort_by_priority(self, tasks: list) -> list:
        """Return tasks sorted from highest to lowest priority."""
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def _filter_by_time(self, tasks: list, budget: int) -> list:
        """Return tasks that fit the budget, always keeping mandatory categories."""
        fitted = []
        remaining = budget
        for task in tasks:
            is_mandatory = task.category in MANDATORY_CATEGORIES
            if is_mandatory or task.duration_minutes <= remaining:
                fitted.append(task)
                remaining -= task.duration_minutes
        return fitted

    def _resolve_conflicts(self, entries: list) -> list:
        """Shift overlapping entries so none start before the previous one ends."""
        if not entries:
            return entries
        resolved = sorted(entries, key=lambda e: _parse_time(e.start_time))
        for previous, current in zip(resolved, resolved[1:]):
            if _parse_time(current.start_time) < _parse_time(previous.end_time):
                duration = current.duration_minutes()
                current.start_time = previous.end_time
                current.end_time = _add_minutes(current.start_time, duration)
        return resolved

    def _explain(self, task: Task, slot: str) -> str:
        """Return a human-readable reason the task was scheduled at the given slot."""
        return (
            f"scheduled at {slot} because it is {task.priority.name.lower()} priority "
            f"({task.category.value}) and fits within the remaining time budget"
        )

    @staticmethod
    def detect_conflicts(plans: list["DailyPlan"]) -> list[str]:
        """Return warning strings for any entries that overlap in time, across one or more pets.

        New: a lightweight pairwise time-overlap check that reports conflicts
        as plain strings instead of raising, since plans built by separate
        Scheduler runs (e.g. one per pet) can't be auto-resolved the way
        `_resolve_conflicts` shifts entries within a single run.
        """
        warnings = []
        dated_entries = [(plan.pet, entry) for plan in plans for entry in plan.entries]
        for index, (pet_a, entry_a) in enumerate(dated_entries):
            for pet_b, entry_b in dated_entries[index + 1 :]:
                a_starts_first = _parse_time(entry_a.start_time) < _parse_time(entry_b.end_time)
                b_starts_first = _parse_time(entry_b.start_time) < _parse_time(entry_a.end_time)
                if a_starts_first and b_starts_first:
                    warnings.append(
                        f"Warning: '{entry_a.task.title}' for {pet_a.name} "
                        f"({entry_a.start_time}-{entry_a.end_time}) overlaps with "
                        f"'{entry_b.task.title}' for {pet_b.name} "
                        f"({entry_b.start_time}-{entry_b.end_time})"
                    )
        return warnings


@dataclass
class DailyPlan:
    pet: Pet
    date: str
    entries: list[ScheduledEntry] = field(default_factory=list)
    total_duration_minutes: int = 0

    def add_entry(self, entry: ScheduledEntry) -> None:
        """Append an entry to the plan and update the total duration."""
        self.entries.append(entry)
        self.total_duration_minutes += entry.duration_minutes()

    def get_summary(self) -> str:
        """Return a formatted, human-readable summary of the plan."""
        lines = [f"Daily plan for {self.pet.name} ({self.pet.breed}) - {self.date}"]
        if not self.entries:
            lines.append("  No tasks fit the available time today.")
        for entry in self.entries:
            lines.append(
                f"  {entry.start_time}-{entry.end_time}  {entry.task.title} "
                f"({entry.task.duration_minutes} min) [priority: {entry.task.priority.name.lower()}]"
            )
            lines.append(f"      reason: {entry.reason}")
        lines.append(f"Total planned time: {self.total_duration_minutes} minutes")
        return "\n".join(lines)

    def to_table(self) -> list:
        """Return the plan's entries as a list of plain dicts."""
        return [
            {
                "start": entry.start_time,
                "end": entry.end_time,
                "task": entry.task.title,
                "duration_minutes": entry.duration_minutes(),
                "priority": entry.task.priority.name,
                "category": entry.task.category.value,
                "reason": entry.reason,
            }
            for entry in self.entries
        ]


@dataclass
class ScheduledEntry:
    task: Task
    start_time: str
    end_time: str
    reason: str

    def duration_minutes(self) -> int:
        """Return the entry's duration in minutes."""
        delta = _parse_time(self.end_time) - _parse_time(self.start_time)
        return int(delta.total_seconds() // 60)


# ── Command-line interface ───────────────────────────────────────────────


def _prompt_nonempty(label: str, default: str | None = None) -> str:
    """Prompt until the user enters a non-empty value or accepts the default."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("  This field is required.")


def _prompt_int(label: str, default: int | None = None, minimum: int = 0) -> int:
    """Prompt until the user enters a valid integer >= minimum."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if value < minimum:
            print(f"  Please enter a number >= {minimum}.")
            continue
        return value


def _prompt_choice(label: str, options) -> object:
    """Prompt the user to pick one option from a numbered list."""
    options = list(options)
    print(f"{label}:")
    for index, option in enumerate(options, start=1):
        name = getattr(option, "name", option)
        print(f"  {index}) {name}")
    while True:
        raw = input(f"Choose 1-{len(options)}: ").strip()
        try:
            index = int(raw)
        except ValueError:
            print("  Please enter a number from the list.")
            continue
        if 1 <= index <= len(options):
            return options[index - 1]
        print(f"  Please enter a number between 1 and {len(options)}.")


def _prompt_yes_no(label: str, default: bool = False) -> bool:
    """Prompt for a yes/no answer, defaulting if left blank."""
    hint = "Y/n" if default else "y/N"
    raw = input(f"{label} ({hint}): ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def _setup_owner_and_pet() -> Owner:
    """Interactively collect pet and owner details and return the new Owner."""
    print("\n== Set up your pet ==")
    pet = Pet(
        name=_prompt_nonempty("Pet name"),
        species=_prompt_nonempty("Species"),
        breed=_prompt_nonempty("Breed"),
        age_years=_prompt_int("Age (years)", minimum=0),
    )
    print("\n== Set up owner ==")
    owner = Owner(
        name=_prompt_nonempty("Owner name"),
        available_minutes=_prompt_int("Available minutes today", default=60, minimum=0),
        preferences=_prompt_nonempty("Preferences (free text)", default=""),
        pet=pet,
    )
    return owner


def _add_task(owner: Owner) -> None:
    """Interactively collect task details and add it to the owner."""
    print("\n== Add a task ==")
    title = _prompt_nonempty("Task title")
    duration = _prompt_int("Duration (minutes)", minimum=1)
    priority = _prompt_choice("Priority", Priority)
    category = _prompt_choice("Category", TaskCategory)
    is_recurring = _prompt_yes_no("Is this recurring?")
    frequency = _prompt_nonempty("Frequency (e.g. daily, weekly)", default="") if is_recurring else ""
    owner.add_task(
        Task(
            title=title,
            duration_minutes=duration,
            priority=priority,
            category=category,
            is_recurring=is_recurring,
            frequency=frequency,
        )
    )
    print(f"Added '{title}'.")


def _list_tasks(owner: Owner) -> None:
    """Print a numbered list of the owner's current tasks."""
    tasks = owner.get_tasks()
    print("\n== Tasks ==")
    if not tasks:
        print("  No tasks yet.")
        return
    for index, task in enumerate(tasks, start=1):
        flag = " (recurring)" if task.is_recurring else ""
        print(
            f"  {index}) {task.title} - {task.duration_minutes} min, "
            f"{task.priority.name.lower()} priority, {task.category.value}{flag}"
        )


def _remove_task(owner: Owner) -> None:
    """Interactively remove a task chosen from the owner's task list."""
    tasks = owner.get_tasks()
    _list_tasks(owner)
    if not tasks:
        return
    index = _prompt_int("Task number to remove", minimum=1)
    if index > len(tasks):
        print("  No task with that number.")
        return
    task = tasks[index - 1]
    owner.remove_task(task)
    print(f"Removed '{task.title}'.")


def _generate_plan(owner: Owner) -> DailyPlan:
    """Interactively generate and print today's plan for the owner."""
    print("\n== Generate today's plan ==")
    start_time = _prompt_nonempty("Plan start time (HH:MM)", default="08:00")
    plan_date = _prompt_nonempty("Plan date (YYYY-MM-DD)", default=date.today().isoformat())
    scheduler = Scheduler(owner=owner, start_time=start_time, plan_date=plan_date)
    plan = scheduler.generate_plan()
    print()
    print(plan.get_summary())
    return plan


def _run_demo() -> None:
    """Run a non-interactive, seeded demo of the scheduling pipeline."""
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)
    owner = Owner(name="Jordan", available_minutes=60, preferences="mornings only", pet=pet)
    owner.add_task(Task("Morning walk", 30, Priority.HIGH, TaskCategory.WALK))
    owner.add_task(Task("Feeding", 10, Priority.HIGH, TaskCategory.FEEDING))
    owner.add_task(Task("Medication", 5, Priority.HIGH, TaskCategory.MEDICATION))
    owner.add_task(Task("Brushing", 20, Priority.LOW, TaskCategory.GROOMING))
    owner.add_task(Task("Puzzle toy", 15, Priority.MEDIUM, TaskCategory.ENRICHMENT))

    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date=date.today().isoformat())
    plan = scheduler.generate_plan()

    print(plan.get_summary())
    print("\nTable view:")
    for row in plan.to_table():
        print(f"  {row}")


def run_cli() -> None:
    """Run the interactive PawPal+ menu loop."""
    owner = _setup_owner_and_pet()
    last_plan: DailyPlan | None = None

    menu = """
== PawPal+ ==
1) Add task
2) Remove task
3) List tasks
4) Generate today's plan
5) Show last plan again
6) Exit
"""
    while True:
        print(menu)
        choice = input("Choose 1-6: ").strip()
        if choice == "1":
            _add_task(owner)
        elif choice == "2":
            _remove_task(owner)
        elif choice == "3":
            _list_tasks(owner)
        elif choice == "4":
            last_plan = _generate_plan(owner)
        elif choice == "5":
            if last_plan is None:
                print("No plan generated yet.")
            else:
                print()
                print(last_plan.get_summary())
        elif choice == "6":
            print("Goodbye!")
            return
        else:
            print("Please choose a number from 1-6.")


def main() -> None:
    """Parse CLI arguments and dispatch to the demo or interactive menu."""
    parser = argparse.ArgumentParser(description="PawPal+ command-line interface")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a non-interactive demo with seeded owner/pet/tasks and print the plan.",
    )
    args = parser.parse_args()

    if args.demo:
        _run_demo()
    else:
        try:
            run_cli()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")


if __name__ == "__main__":
    main()
