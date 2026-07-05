`# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

==========================================
           Today's Schedule
==========================================
Owner: Jordan Alvarez
Date:  2026-07-04

-- Mochi (dog, Shiba Inu) --
  07:30-08:00  Morning walk (30 min) [priority: high]
      reason: scheduled at 07:30 because it is high priority (walk) and fits within the remaining time budget
  08:00-08:10  Feeding (10 min) [priority: high]
      reason: scheduled at 08:00 because it is high priority (feeding) and fits within the remaining time budget
Total planned time: 40 minutes

-- Luna (cat, Domestic Shorthair) --
  09:00-09:15  Litter box cleaning (15 min) [priority: medium]
      reason: scheduled at 09:00 because it is medium priority (other) and fits within the remaining time budget
Total planned time: 15 minutes
==========================================

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | sort by priority: _sort_by_priority(self, tasks:list) -> list:
 """Return tasks sorted from highest to lowest priority."""

| Filtering | filter by time: _filter_by_time(self, tasks: list, budget: int) -> list:
"""Return tasks that fit the budget, always keeping mandatory categories."""

|Conflict detection| detect_conflicts(plans: list["DailyPlan"]) -> list[str]:
"""Return warning strings for any entries that overlap in time, across one or more pets.

    Changed: pairs now come from itertools.combinations instead of manual
    `enumerate` + `entries[index + 1:]` slicing, which allocated a new list
    on every outer iteration -- wasted O(n) copying on top of the pairwise
    comparisons. The overlap test and message formatting were also pulled
    out into named helpers (_entries_overlap, _conflict_message) so the
    loop body reads as "for each pair, warn if it overlaps" instead of a
    block of inline, confusingly-named booleans."""

| Conflict handling | _resolve_conflicts(self, entries: list) -> list:
 """Shift overlapping entries so none start before the previous one ends."""
 
| Recurring tasks | next_occurrence(self, reference_date: str) -> "Task | None":
"""Return a new Task for the next occurrence, due `frequency` after `reference_date`.

    New: replaces the old approach of resetting this same instance's
    `completed` flag, so a finished occurrence stays as a historical record
    instead of being silently reused for the next cycle."""

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
