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
    scheduler = Scheduler(owner=owner, start_time=start_time, plan_date=PLAN_DATE)
    return scheduler.generate_plan()


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
        Task("Morning walk", 30, Priority.HIGH, TaskCategory.WALK),
        Task("Feeding", 10, Priority.HIGH, TaskCategory.FEEDING),
    ]
    luna_tasks = [
        Task("Litter box cleaning", 15, Priority.MEDIUM, TaskCategory.OTHER),
    ]

    mochi_plan = build_plan_for_pet(owner, mochi, mochi_tasks, start_time="07:30")
    luna_plan = build_plan_for_pet(owner, luna, luna_tasks, start_time="09:00")

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


if __name__ == "__main__":
    main()
