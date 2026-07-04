"""Simple tests for Task completion and Pet task counting in pawpal_system.py."""

from pawpal_system import Pet, Priority, Task, TaskCategory


def test_mark_complete_updates_task_status():
    task = Task("Morning walk", 30, Priority.HIGH, TaskCategory.WALK)
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_adding_tasks_to_pet_increments_task_count():
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)

    pet.add_task(Task("Morning walk", 30, Priority.HIGH, TaskCategory.WALK))
    pet.add_task(Task("Feeding", 10, Priority.HIGH, TaskCategory.FEEDING))

    assert len(pet.tasks) == 2
