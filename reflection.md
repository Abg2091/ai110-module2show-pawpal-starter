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
- If yes, describe at least one change and why you made it.

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
