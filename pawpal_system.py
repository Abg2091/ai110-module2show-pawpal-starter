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


# ── Time helpers ──────────────────────────────────────────────────────────

_TIME_FORMAT = "%H:%M"


def _parse_time(value: str) -> datetime:
    return datetime.strptime(value, _TIME_FORMAT)


def _format_time(moment: datetime) -> str:
    return moment.strftime(_TIME_FORMAT)


def _add_minutes(value: str, minutes: int) -> str:
    return _format_time(_parse_time(value) + timedelta(minutes=minutes))


# ── Core domain classes ───────────────────────────────────────────────────


class Owner:
    def __init__(self, name: str, available_minutes: int, preferences: str, pet: Pet):
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences
        self.pet = pet
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        self.tasks = [t for t in self.tasks if t.id != task.id]

    def get_tasks(self) -> list[Task]:
        return list(self.tasks)


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
        return self.priority == Priority.HIGH

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.name,
            "category": self.category.value,
            "is_recurring": self.is_recurring,
            "frequency": self.frequency,
        }


# ── Scheduling classes ────────────────────────────────────────────────────


class Scheduler:
    def __init__(self, owner: Owner, start_time: str, plan_date: str):
        self.owner = owner
        self.pet = owner.pet
        self.start_time = start_time
        self.plan_date = plan_date

    def generate_plan(self) -> DailyPlan:
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

    def _sort_by_priority(self, tasks: list) -> list:
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def _filter_by_time(self, tasks: list, budget: int) -> list:
        fitted = []
        remaining = budget
        for task in tasks:
            if task.duration_minutes <= remaining:
                fitted.append(task)
                remaining -= task.duration_minutes
        return fitted

    def _resolve_conflicts(self, entries: list) -> list:
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
        return (
            f"scheduled at {slot} because it is {task.priority.name.lower()} priority "
            f"({task.category.value}) and fits within the remaining time budget"
        )


@dataclass
class DailyPlan:
    pet: Pet
    date: str
    entries: list[ScheduledEntry] = field(default_factory=list)
    total_duration_minutes: int = 0

    def add_entry(self, entry: ScheduledEntry) -> None:
        self.entries.append(entry)
        self.total_duration_minutes += entry.duration_minutes()

    def get_summary(self) -> str:
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
        delta = _parse_time(self.end_time) - _parse_time(self.start_time)
        return int(delta.total_seconds() // 60)


# ── Command-line interface ───────────────────────────────────────────────


def _prompt_nonempty(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("  This field is required.")


def _prompt_int(label: str, default: int | None = None, minimum: int = 0) -> int:
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
    hint = "Y/n" if default else "y/N"
    raw = input(f"{label} ({hint}): ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def _setup_owner_and_pet() -> Owner:
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
    print("\n== Generate today's plan ==")
    start_time = _prompt_nonempty("Plan start time (HH:MM)", default="08:00")
    plan_date = _prompt_nonempty("Plan date (YYYY-MM-DD)", default=date.today().isoformat())
    scheduler = Scheduler(owner=owner, start_time=start_time, plan_date=plan_date)
    plan = scheduler.generate_plan()
    print()
    print(plan.get_summary())
    return plan


def _run_demo() -> None:
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
