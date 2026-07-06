from datetime import date, time

import streamlit as st  # type: ignore[import]

from pawpal_system import (
    MANDATORY_CATEGORIES,
    DailyPlan,
    Owner,
    Pet,
    Priority,
    Scheduler,
    Task,
    TaskCategory,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to PawPal+! Set up your household, add each pet's today's care
tasks, and generate a scheduled daily plan below.
"""
)

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

st.divider()

if "pets" not in st.session_state:
    st.session_state.pets = [
        {
            "pet": Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3),
            "tasks": [],
            "start_time": time(8, 0),
        }
    ]


def plan_to_rows(plan: DailyPlan) -> list[dict]:
    """Turn a DailyPlan's entries into table rows for st.table.

    Reuses Scheduler's own output (plan.to_table()) rather than re-deriving
    order or filtering in the display layer -- entries already reflect the
    scheduler's priority sort, time-budget filter, and conflict resolution.
    Only a display-only "mandatory" flag is added here, from the domain
    constant the scheduler itself enforces.
    """
    rows = []
    for entry, row in zip(plan.entries, plan.to_table()):
        row = dict(row)
        row["mandatory"] = entry.task.category in MANDATORY_CATEGORIES
        rows.append(row)
    return rows


def render_plan(plan: DailyPlan) -> None:
    if not plan.entries:
        st.info("No tasks fit the available time today.")
        return
    st.table(plan_to_rows(plan))
    st.caption(f"Total planned time: {plan.total_duration_minutes} minutes")


st.subheader("Owner")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input("Available minutes per pet, today", min_value=0, value=60, step=5)
with col2:
    preferences = st.text_input("Preferences", value="")

st.divider()

st.subheader("Pets & Tasks")
st.caption(
    "Add one or more pets. Each pet gets its own tasks and start time, so "
    "PawPal+ can check for care times that overlap across pets."
)

with st.expander("Add a pet", expanded=True, key="add_pet_expander"):
    col1, col2 = st.columns(2)
    with col1:
        new_pet_name = st.text_input("Pet name", key="new_pet_name")
        new_species = st.selectbox("Species", ["dog", "cat", "other"], key="new_species")
    with col2:
        new_breed = st.text_input("Breed", key="new_breed")
        new_age = st.number_input("Age (years)", min_value=0, value=1, step=1, key="new_age")
    if st.button("Add pet"):
        if new_pet_name.strip():
            st.session_state.pets.append(
                {
                    "pet": Pet(name=new_pet_name.strip(), species=new_species, breed=new_breed, age_years=int(new_age)),
                    "tasks": [],
                    "start_time": time(8, 0),
                }
            )
            st.success(f"Added {new_pet_name.strip()}. Select them below under \"Manage tasks for\" to add tasks.")
        else:
            st.warning("Pet name is required.")

if not st.session_state.pets:
    st.info("Add a pet above to start planning tasks.")
    st.stop()

pet_names = [entry["pet"].name for entry in st.session_state.pets]
selected_index = st.selectbox(
    "Manage tasks for",
    range(len(st.session_state.pets)),
    format_func=lambda i: pet_names[i],
)
selected = st.session_state.pets[selected_index]
selected_name = selected["pet"].name

col1, col2 = st.columns(2)
with col1:
    selected["start_time"] = st.time_input(f"{selected_name}'s start time", value=selected["start_time"])
with col2:
    st.write(f"**Species / breed:** {selected['pet'].species} / {selected['pet'].breed or '—'}")

st.markdown(f"**Add a task for {selected_name}**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk", key=f"title_{selected_index}")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20, key=f"dur_{selected_index}")
with col3:
    priority_name = st.selectbox("Priority", [p.name for p in Priority], index=2, key=f"prio_{selected_index}")
with col4:
    category_name = st.selectbox("Category", [c.name for c in TaskCategory], key=f"cat_{selected_index}")

if st.button("Add task", key=f"add_{selected_index}"):
    selected["tasks"].append(
        Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=Priority[priority_name],
            category=TaskCategory[category_name],
        )
    )

if selected["tasks"]:
    st.table([{k: v for k, v in task.to_dict().items() if k != "id"} for task in selected["tasks"]])
else:
    st.info(f"No tasks yet for {selected_name}.")

st.divider()

st.subheader("Generate Household Schedule")
# One shared plan date for every pet: Scheduler.detect_conflicts() compares
# entries by clock time only, not by plan.date, so plans generated for
# different dates could be falsely flagged as overlapping. Keeping a single
# date for the whole household sidesteps that.
plan_date_value = st.date_input("Plan date", value=date.today())

if st.button("Generate schedule"):
    owner = Owner(
        name=owner_name,
        available_minutes=int(available_minutes),
        preferences=preferences,
        pet=st.session_state.pets[0]["pet"],
    )

    results = []
    for entry in st.session_state.pets:
        owner.pet = entry["pet"]
        owner.tasks = []
        for task in entry["tasks"]:
            owner.add_task(task)
        scheduler = Scheduler(
            owner=owner,
            start_time=entry["start_time"].strftime("%H:%M"),
            plan_date=plan_date_value.isoformat(),
        )
        results.append((entry, scheduler.generate_plan()))

    st.divider()
    conflicts = Scheduler.detect_conflicts([plan for _, plan in results])
    if conflicts:
        st.warning(f"⚠️ {len(conflicts)} scheduling conflict(s) found across pets:")
        for message in conflicts:
            st.warning(message)
    else:
        st.success("✅ No conflicts — every pet's care tasks are scheduled at non-overlapping times.")

    for entry, plan in results:
        st.markdown(f"### {plan.pet.name}'s plan — {plan.date}")
        render_plan(plan)
        scheduled_ids = {scheduled.task.id for scheduled in plan.entries}
        unscheduled = [task for task in entry["tasks"] if task.id not in scheduled_ids]
        if unscheduled:
            titles = ", ".join(task.title for task in unscheduled)
            st.warning(f"Didn't fit in today's {available_minutes}-minute budget: {titles}")
