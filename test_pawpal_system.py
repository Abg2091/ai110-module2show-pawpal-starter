"""Tests for the PawPal+ scheduling behavior in pawpal_system.py."""

import pytest

from pawpal_system import (
    DailyPlan,
    Owner,
    Pet,
    Priority,
    Scheduler,
    ScheduledEntry,
    Task,
    TaskCategory,
)


@pytest.fixture
def pet():
    return Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)


@pytest.fixture
def owner(pet):
    return Owner(name="Jordan", available_minutes=60, preferences="mornings only", pet=pet)


# ── Priority ──────────────────────────────────────────────────────────────


def test_priority_is_orderable():
    assert Priority.HIGH > Priority.MEDIUM > Priority.LOW


# ── Task ──────────────────────────────────────────────────────────────────


def test_task_is_high_priority():
    high = Task("Walk", 20, Priority.HIGH, TaskCategory.WALK)
    medium = Task("Walk", 20, Priority.MEDIUM, TaskCategory.WALK)
    assert high.is_high_priority()
    assert not medium.is_high_priority()


def test_task_to_dict_uses_readable_enum_values():
    task = Task("Walk", 20, Priority.HIGH, TaskCategory.WALK)
    as_dict = task.to_dict()
    assert as_dict["priority"] == "HIGH"
    assert as_dict["category"] == "walk"
    assert as_dict["id"] == task.id


def test_tasks_get_unique_ids_even_with_identical_fields():
    a = Task("Feed Mochi", 10, Priority.HIGH, TaskCategory.FEEDING)
    b = Task("Feed Mochi", 10, Priority.HIGH, TaskCategory.FEEDING)
    assert a.id != b.id


# ── Owner ─────────────────────────────────────────────────────────────────


def test_owner_add_and_get_tasks(owner):
    task = Task("Walk", 10, Priority.LOW, TaskCategory.WALK)
    owner.add_task(task)
    assert owner.get_tasks() == [task]


def test_owner_remove_task_only_removes_the_matching_identity(owner):
    a = Task("Feed Mochi", 10, Priority.HIGH, TaskCategory.FEEDING)
    b = Task("Feed Mochi", 10, Priority.HIGH, TaskCategory.FEEDING)
    owner.add_task(a)
    owner.add_task(b)

    owner.remove_task(a)

    assert owner.get_tasks() == [b]


def test_owner_owns_its_pet(owner, pet):
    assert owner.pet is pet


# ── Scheduler ─────────────────────────────────────────────────────────────


def test_scheduler_derives_pet_from_owner(owner, pet):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")
    assert scheduler.pet is pet


def test_sort_by_priority_orders_high_first_and_is_stable(owner):
    low = Task("Brush", 10, Priority.LOW, TaskCategory.GROOMING)
    high1 = Task("Walk", 10, Priority.HIGH, TaskCategory.WALK)
    medium = Task("Play", 10, Priority.MEDIUM, TaskCategory.ENRICHMENT)
    high2 = Task("Meds", 10, Priority.HIGH, TaskCategory.MEDICATION)
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")

    ordered = scheduler._sort_by_priority([low, high1, medium, high2])

    assert ordered == [high1, high2, medium, low]


def test_filter_by_time_skips_tasks_that_do_not_fit_but_keeps_checking(owner):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")
    fits = Task("A", 30, Priority.HIGH, TaskCategory.WALK)
    too_big = Task("B", 40, Priority.HIGH, TaskCategory.GROOMING)
    also_fits = Task("C", 20, Priority.MEDIUM, TaskCategory.ENRICHMENT)

    fitted = scheduler._filter_by_time([fits, too_big, also_fits], budget=60)

    assert fitted == [fits, also_fits]


def test_filter_by_time_never_drops_mandatory_categories(owner):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")
    oversized_meds = Task("Meds", 40, Priority.LOW, TaskCategory.MEDICATION)
    optional = Task("Play", 20, Priority.HIGH, TaskCategory.ENRICHMENT)

    fitted = scheduler._filter_by_time([oversized_meds, optional], budget=30)

    assert oversized_meds in fitted


def test_filter_by_time_mandatory_overflow_blocks_later_optional_tasks(owner):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")
    oversized_meds = Task("Meds", 40, Priority.HIGH, TaskCategory.MEDICATION)
    optional = Task("Play", 10, Priority.HIGH, TaskCategory.ENRICHMENT)

    fitted = scheduler._filter_by_time([oversized_meds, optional], budget=30)

    assert fitted == [oversized_meds]


def test_generate_plan_builds_sequential_schedule_and_drops_what_does_not_fit(owner):
    owner.available_minutes = 60
    owner.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK))
    owner.add_task(Task("Feed", 10, Priority.HIGH, TaskCategory.FEEDING))
    owner.add_task(Task("Brush", 30, Priority.LOW, TaskCategory.GROOMING))  # only 20 min left
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")

    plan = scheduler.generate_plan()

    assert [entry.task.title for entry in plan.entries] == ["Walk", "Feed"]
    assert (plan.entries[0].start_time, plan.entries[0].end_time) == ("08:00", "08:30")
    assert (plan.entries[1].start_time, plan.entries[1].end_time) == ("08:30", "08:40")
    assert plan.total_duration_minutes == 40


def test_generate_plan_reads_tasks_live_from_owner(owner):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")

    assert scheduler.generate_plan().entries == []

    owner.add_task(Task("Walk", 10, Priority.HIGH, TaskCategory.WALK))

    assert len(scheduler.generate_plan().entries) == 1


def test_generate_plan_renews_recurring_task_completion_on_a_new_day(owner):
    meds = Task("Meds", 5, Priority.HIGH, TaskCategory.MEDICATION, is_recurring=True)
    owner.add_task(meds)

    Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04").generate_plan()
    meds.mark_complete()
    assert meds.completed is True

    Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04").generate_plan()
    assert meds.completed is True  # same-day regeneration leaves it alone

    Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-05").generate_plan()
    assert meds.completed is False  # new day renews it


def test_generate_plan_does_not_reset_recurring_completion_within_the_same_day(owner):
    walk = Task("Walk", 10, Priority.HIGH, TaskCategory.WALK, is_recurring=True)
    owner.add_task(walk)
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")

    scheduler.generate_plan()
    walk.mark_complete()
    scheduler.generate_plan()

    assert walk.completed is True


def test_generate_plan_removes_completed_one_off_tasks(owner):
    vet_visit = Task("Vet visit", 30, Priority.HIGH, TaskCategory.OTHER)
    vet_visit.mark_complete()
    owner.add_task(vet_visit)

    Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04").generate_plan()

    assert vet_visit not in owner.get_tasks()


def test_generate_plan_keeps_pending_one_off_tasks(owner):
    vet_visit = Task("Vet visit", 30, Priority.HIGH, TaskCategory.OTHER)
    owner.add_task(vet_visit)

    Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04").generate_plan()

    assert vet_visit in owner.get_tasks()


def test_resolve_conflicts_shifts_overlapping_entries_and_preserves_duration(owner):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")
    task_a = Task("A", 30, Priority.HIGH, TaskCategory.WALK)
    task_b = Task("B", 20, Priority.HIGH, TaskCategory.FEEDING)
    entries = [
        ScheduledEntry(task_a, "08:00", "08:30", "reason a"),
        ScheduledEntry(task_b, "08:15", "08:35", "reason b"),  # overlaps with A
    ]

    resolved = scheduler._resolve_conflicts(entries)

    assert (resolved[0].start_time, resolved[0].end_time) == ("08:00", "08:30")
    assert (resolved[1].start_time, resolved[1].end_time) == ("08:30", "08:50")


# ── DailyPlan / ScheduledEntry ────────────────────────────────────────────


def test_scheduled_entry_duration_minutes_from_start_and_end():
    task = Task("Walk", 45, Priority.HIGH, TaskCategory.WALK)
    entry = ScheduledEntry(task, "08:00", "08:45", "because")
    assert entry.duration_minutes() == 45


def test_daily_plan_summary_handles_no_tasks(owner):
    scheduler = Scheduler(owner=owner, start_time="08:00", plan_date="2026-07-04")
    plan = scheduler.generate_plan()
    assert "No tasks fit" in plan.get_summary()


def test_daily_plan_summary_includes_task_and_total(owner):
    owner.add_task(Task("Walk", 15, Priority.HIGH, TaskCategory.WALK))
    scheduler = Scheduler(owner=owner, start_time="09:00", plan_date="2026-07-04")

    summary = scheduler.generate_plan().get_summary()

    assert "Walk" in summary
    assert "Total planned time: 15 minutes" in summary


def test_daily_plan_to_table_shape(owner):
    owner.add_task(Task("Walk", 15, Priority.HIGH, TaskCategory.WALK))
    scheduler = Scheduler(owner=owner, start_time="09:00", plan_date="2026-07-04")

    table = scheduler.generate_plan().to_table()

    assert table[0]["task"] == "Walk"
    assert table[0]["duration_minutes"] == 15
    assert table[0]["priority"] == "HIGH"


def test_daily_plan_add_entry_accumulates_total_duration():
    pet_obj = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)
    plan = DailyPlan(pet=pet_obj, date="2026-07-04")
    task = Task("Walk", 20, Priority.HIGH, TaskCategory.WALK)

    plan.add_entry(ScheduledEntry(task, "08:00", "08:20", "because"))

    assert plan.total_duration_minutes == 20
    assert len(plan.entries) == 1
