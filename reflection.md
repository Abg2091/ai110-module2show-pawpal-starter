# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The initial UML uses 8 classes organized into two layers: a domain layer and a scheduling layer.

The domain layer has three core classes. `Owner` stores the owner's name, daily time budget (in minutes), and preferences, and is responsible for holding the task list. `Pet` holds basic info (name, species, breed, age) and is associated with one owner. `Task` is the atomic unit of care — it has a title, duration, priority, category, and an optional recurrence flag. Two enumerations (`Priority`: LOW/MEDIUM/HIGH and `TaskCategory`: WALK, FEEDING, MEDICATION, GROOMING, ENRICHMENT, OTHER) back the `Task` so there are no magic strings.

The scheduling layer has three classes. `Scheduler` takes an owner, a pet, and their task list and exposes a `generate_plan()` method; private helpers handle sorting by priority, filtering tasks that fit the remaining time budget, and resolving time conflicts. It produces a `DailyPlan` (modeled as a dependency, not ownership, to keep concerns separate). `DailyPlan` holds an ordered list of `ScheduledEntry` objects and knows the total duration; it can render a summary table. `ScheduledEntry` pairs a `Task` with a concrete start/end time and a human-readable `reason` string that explains why the task was placed at that slot — satisfying the "explain the plan" requirement from the scenario.

``````````````````````````````````````````
3 Core actions a user should be able to perform:

1.User should be able to provide pet related inputs. (e.g. name, breed, age, ongoing medications if any etc.)

2. User should be able to provide personal time availability.

3. User should be able to see the today's task, and update/modify if needed.


**b. Design changes**

- Did your design change during implementation?

Yes

- If yes, describe at least one change and why you made it.
Changes Made:

1. Give Scheduler/DailyPlan an actual date — this is a guaranteed crash today
The problem: DailyPlan requires a date to exist (it's a mandatory field, no default), but nothing anywhere in Scheduler ever captures what that date is. The moment generate_plan() tries to build a DailyPlan, it will hit a dead end — either the program throws an error because no date was provided, or someone patches around it by quietly grabbing "today's date" from the computer's clock.

Why that patch is worse than the crash: if the code silently fills in "today" on its own, then every time you re-run a test, or generate a plan for a different day than today, you get a different, unpredictable result. That makes bugs almost impossible to reproduce — "it worked yesterday" becomes a real, recurring complaint.

UML change (diagrams/uml.mmd):


class Scheduler {
    +Owner owner
    +Pet pet
    +list~Task~ tasks
    +str start_time
    +str plan_date        %% NEW
    ...
}
Code change (pawpal_system.py):


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet, tasks: list[Task], start_time: str, plan_date: str):
        ...
        self.plan_date = plan_date
So generate_plan() has a real value to hand to DailyPlan(date=self.plan_date, ...) instead of guessing.

Plain-language why: think of DailyPlan as a form that legally requires today's date written on it. Right now, nobody ever hands the date to the person filling out the form — they either can't finish it, or they just scribble in whatever date happens to be on their watch. Making the date something you hand in on purpose means the form is always filled out correctly and the same way, every time.

2. Make Priority actually orderable — sorting will crash otherwise
The problem: Priority is defined as a plain label (LOW, MEDIUM, HIGH) with no built-in sense of "bigger" or "smaller." The scheduler's whole job is to sort tasks by priority — but Python has no way to know that HIGH outranks MEDIUM unless we tell it. Trying to sort by priority as-is will raise an error the first time it's attempted.

UML change: no visual change needed — the diagram already shows Priority as an enumeration; just add a one-line note documenting the intended rank order so future readers (and graders) know it's meaningful:


class Priority {
    <<enumeration>>
    LOW
    MEDIUM
    HIGH
}
note for Priority "Ordered LOW < MEDIUM < HIGH — used for sorting"
Code change:


from enum import IntEnum

class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
Everything else about Priority stays the same — you still write Priority.HIGH — but now Priority.HIGH > Priority.LOW is True instead of an error, and _sort_by_priority just works.

Plain-language why: imagine three folders labeled Low, Medium, and High, but nobody told the filing clerk which one to deal with first. "Sort these by importance" is an instruction the clerk can't follow without knowing the ranking. Numbering them 1, 2, 3 behind the scenes gives the clerk (the computer) a rule to follow, while everyone still reads and writes the friendly names.

3. Connect Owner to their Pet — the diagram promises this relationship but the code never delivers it
The problem: the UML explicitly says "an Owner owns one Pet," but the Owner class has no pet field at all. As a workaround, Scheduler is handed owner and pet as two completely separate, unconnected pieces of information — nothing stops someone from accidentally pairing the wrong owner with the wrong pet.

UML change: the relationship is already drawn correctly (Owner "1" --> "1" Pet : owns) — the diagram isn't wrong, the code just doesn't implement what it promises. No diagram change needed; this is purely a code fix to bring it in line with the diagram.

Code change:


class Owner:
    def __init__(self, name: str, available_minutes: int, preferences: str, pet: Pet):
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences
        self.pet = pet
        self.tasks: list[Task] = []
Then Scheduler can be simplified to pull the pet from the owner instead of asking for it separately:


class Scheduler:
    def __init__(self, owner: Owner, tasks: list[Task], start_time: str, plan_date: str):
        self.owner = owner
        self.pet = owner.pet   # derived, not separately supplied
        ...
Plain-language why: right now, filling out a "start a schedule" request means separately telling the system "here's the owner" and "here's the pet," as if they might not belong together — like ordering a leash and a dog from two different counters and hoping someone remembers to match them up. Storing the pet directly on the owner means you only ever say "here's the owner," and their pet comes along automatically, correctly, every time.

4. Stop keeping two separate task lists — Owner and Scheduler currently disagree with each other
The problem: Owner keeps its own list of tasks (add_task/remove_task/get_tasks), but Scheduler is also given its own independent task list when it's created. These two lists have no ongoing connection. If you add or remove a task on the Owner after the Scheduler was set up, the Scheduler never finds out — it keeps planning against the old, outdated list.

Code change:


class Scheduler:
    def __init__(self, owner: Owner, start_time: str, plan_date: str):
        self.owner = owner
        self.pet = owner.pet
        self.start_time = start_time
        self.plan_date = plan_date
        # no separate self.tasks — always read live from the owner:

    def generate_plan(self) -> DailyPlan:
        tasks = self.owner.get_tasks()
        ...
Plain-language why: picture two grocery lists for the same household — one stuck on the fridge, one carried in someone's pocket. If you cross an item off the fridge list, the pocket list still says to buy it. Having exactly one list that everyone reads from directly (the Owner's) means there's only ever one "truth" about what tasks exist, and the scheduler can never accidentally work from stale information.

5. Give Task a stable identity, so "remove this task" removes the right one
The problem: Task is a dataclass, which means Python considers two tasks "equal" if all their fields match — same title, same duration, same priority — even if they're meant to be two separate entries (e.g., the owner logged "Feed Mochi, 10 min" twice for two different times of day). When remove_task is implemented, a natural approach (self.tasks.remove(task)) will remove the first matching task it finds — which might not be the one the user actually meant to delete.

Code change: give each Task a unique, invisible ID at creation time so removal is based on "this exact task," not "a task that looks like this one":


import uuid

@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority
    category: TaskCategory
    is_recurring: bool = False
    frequency: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
Plain-language why: imagine identical twins wearing name tags that just say "Sam." If someone says "send Sam home," you can't tell which twin they mean — you'd just grab whichever one you saw first. Giving each task its own invisible serial number is like giving each twin a different ID badge underneath the name tag: they can still both be called "Sam" to a person, but the system never confuses one for the other.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
