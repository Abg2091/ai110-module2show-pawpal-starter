"""Temporary execution environment for verifying pawpal_system.py logic.

The Owner/Pet relationship in pawpal_system.py is deliberately one owner to
one pet at a time (see diagrams/uml.mmd and reflection.md). To exercise the
real Scheduler/DailyPlan logic for two pets under the same owner, this script
reuses a single Owner instance and retargets its `pet` and task list before
generating each pet's plan, then combines both plans into one printed
schedule.

Run with:
    python main.py
"""

from datetime import date

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TaskCategory

PLAN_DATE = date.today().isoformat()


def build_plan_for_pet(owner: Owner, pet: Pet, tasks: list[Task], start_time: str):
    owner.pet = pet
    owner.tasks = []
    for task in tasks:
        owner.add_task(task)
        pet.add_task(task)
    scheduler = Scheduler(owner=owner, start_time=start_time, plan_date=PLAN_DATE)
    return scheduler.generate_plan()


def filter_tasks(pets: list[Pet], *, completed: bool | None = None, pet_name: str | None = None) -> list[Task]:
    """Return tasks across pets matching the completion status and/or pet name."""
    matches = []
    for pet in pets:
        if pet_name is not None and pet.name != pet_name:
            continue
        for task in pet.tasks:
            if completed is not None and task.completed != completed:
                continue
            matches.append(task)
    return matches


def main() -> None:
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)
    luna = Pet(name="Luna", species="cat", breed="Domestic Shorthair", age_years=2)

    owner = Owner(
        name="Jordan Alvarez",
        available_minutes=90,
        preferences="mornings for Mochi, mid-morning for Luna",
        pet=mochi,
    )

    mochi_tasks = [
        Task("Evening brushing", 20, Priority.LOW, TaskCategory.GROOMING),
        Task("Puzzle toy", 15, Priority.MEDIUM, TaskCategory.ENRICHMENT),
        Task("Morning walk", 30, Priority.HIGH, TaskCategory.WALK),
        Task("Feeding", 10, Priority.HIGH, TaskCategory.FEEDING),
    ]
    mochi_tasks[0].mark_complete()  # brushing was already done this morning

    luna_tasks = [
        Task("Vet checkup", 30, Priority.HIGH, TaskCategory.OTHER),
        Task("Litter box cleaning", 15, Priority.MEDIUM, TaskCategory.OTHER),
        Task("Feeding", 10, Priority.HIGH, TaskCategory.FEEDING),
    ]
    luna_tasks[0].mark_complete()  # vet checkup already happened

    mochi_plan = build_plan_for_pet(owner, mochi, mochi_tasks, start_time="07:30")
    # Same start time as Mochi's plan on purpose, to demonstrate cross-pet conflict detection below.
    luna_plan = build_plan_for_pet(owner, luna, luna_tasks, start_time="07:30")

    banner = "=" * 42
    print(banner)
    print("           Today's Schedule")
    print(banner)
    print(f"Owner: {owner.name}")
    print(f"Date:  {PLAN_DATE}")

    for pet, plan in ((mochi, mochi_plan), (luna, luna_plan)):
        print()
        print(f"-- {pet.name} ({pet.species}, {pet.breed}) --")
        # Skip the summary's own "Daily plan for ..." header line; the
        # per-pet header above already identifies the pet.
        print("\n".join(plan.get_summary().splitlines()[1:]))

    print(banner)

    print()
    print("== Conflict detection ==")
    conflicts = Scheduler.detect_conflicts([mochi_plan, luna_plan])
    if conflicts:
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("  No conflicts found.")

    pets = [mochi, luna]

    print()
    print("== Filtering demo ==")
    completed_tasks = filter_tasks(pets, completed=True)
    print(f"Completed tasks ({len(completed_tasks)}):")
    for task in completed_tasks:
        print(f"  - {task.title} ({task.category.value})")

    pending_tasks = filter_tasks(pets, completed=False)
    print(f"\nPending tasks ({len(pending_tasks)}):")
    for task in pending_tasks:
        print(f"  - {task.title} ({task.category.value})")

    for pet in pets:
        pet_tasks = filter_tasks(pets, pet_name=pet.name)
        print(f"\nTasks for {pet.name} ({len(pet_tasks)}):")
        for task in pet_tasks:
            status = "done" if task.completed else "pending"
            print(f"  - {task.title} [{status}]")

    print()
    print("== Sorting demo (by priority, high first) ==")
    all_tasks = [task for pet in pets for task in pet.tasks]
    for task in sorted(all_tasks, key=lambda t: t.priority, reverse=True):
        print(f"  - {task.title}: {task.priority.name}")


if __name__ == "__main__":
    main()
