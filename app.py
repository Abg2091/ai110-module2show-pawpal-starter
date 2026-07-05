from datetime import date, time

import streamlit as st  # type: ignore[import]

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

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to PawPal+! Set up your pet and owner details, add today's care
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


def render_entry(entry: ScheduledEntry) -> None:
    st.write(
        f"**{entry.start_time}-{entry.end_time}** {entry.task.title} "
        f"({entry.task.duration_minutes} min, {entry.task.priority.name.lower()} priority)"
    )
    st.caption(entry.reason)


def render_plan(plan: DailyPlan) -> None:
    st.markdown(f"**{plan.pet.name}'s plan — {plan.date}**")
    if not plan.entries:
        st.info("No tasks fit the available time today.")
        return
    for entry in plan.entries:
        render_entry(entry)
    st.caption(f"Total planned time: {plan.total_duration_minutes} minutes")


st.subheader("Pet & Owner")
col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    breed = st.text_input("Breed", value="Shiba Inu")
    age_years = st.number_input("Age (years)", min_value=0, value=3, step=1)
with col2:
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input("Available minutes today", min_value=0, value=60, step=5)
    preferences = st.text_input("Preferences", value="")

pet = Pet(name=pet_name, species=species, breed=breed, age_years=int(age_years))
owner = Owner(
    name=owner_name,
    available_minutes=int(available_minutes),
    preferences=preferences,
    pet=pet,
)

st.divider()

st.subheader("Tasks")
st.caption("Add today's care tasks. They feed directly into the scheduler below.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority_name = st.selectbox("Priority", [p.name for p in Priority], index=2)
with col4:
    category_name = st.selectbox("Category", [c.name for c in TaskCategory])

if st.button("Add task"):
    st.session_state.tasks.append(
        Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=Priority[priority_name],
            category=TaskCategory[category_name],
        )
    )

for task in st.session_state.tasks:
    owner.add_task(task)

if owner.get_tasks():
    st.write("Current tasks:")
    st.table([task.to_dict() for task in owner.get_tasks()])
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
col1, col2 = st.columns(2)
with col1:
    start_time_value = st.time_input("Start time", value=time(8, 0))
with col2:
    plan_date_value = st.date_input("Plan date", value=date.today())

if st.button("Generate schedule"):
    scheduler = Scheduler(
        owner=owner,
        start_time=start_time_value.strftime("%H:%M"),
        plan_date=plan_date_value.isoformat(),
    )
    plan = scheduler.generate_plan()
    render_plan(plan)
