# AI Scoping and Project Initialization Guide

This file defines the default instructions for the AI assistant when a new project is created under the `~/Gemmit_Projects` directory. It combines the Diamond Paradigm (requirements, design, tasks) with the [PocketFlow Guide](https://the-pocket.github.io/PocketFlow/guide.html).

---

## 1. Project Intake

* **Objective**: Clarify the user’s goal in a single, concise statement.
* **Context**: Identify existing assets, preferences, and environment.
* **Stakeholders**: List the end-user roles and technical constraints.

***PocketFlow Step 1: Ideation***

> Prompt the user to describe their problem, desired outcome, and any initial constraints.

---

## 2. Requirements Exploration

* Generate a **Requirements Summary**.
* Distinguish **Must-Have** vs **Nice-to-Have** features.
* Seek clarifications if any requirement is ambiguous.

***PocketFlow Step 2: Requirement Analysis***

> Create a formalized requirements.md with clear acceptance criteria for each item.

---

## 3. High-Level Design

* Propose architectural components and data flow.
* Sketch UI/UX wireframes or component hierarchy.
* Assess technology stack choices.

***PocketFlow Step 3: Design***

> Draft design.md outlining modules, interfaces, and chosen libraries/tools.

---

## 4. Task Breakdown

* Break designs into **Atomic Tasks** with status markers:

  * `[]` not started
  * `[-]` in progress
  * `[x]` completed
* Prioritize tasks by dependencies and user impact.

***PocketFlow Step 4: Planning***

> Populate tasks.md with individual steps, estimated effort, and dependencies.

---

## 5. Iteration and Review

* After each sprint (2–4 tasks), review progress and update docs.
* Incorporate user feedback into requirements and design.

***PocketFlow Step 5: Iteration***

> At task completion, summarize outcomes, blockers, and next actions.

---

> **Note**: The AI should always maintain the three core project docs—`requirements.md`, `design.md`, `tasks.md`—and update them continuously as the project evolves, following the Diamond Paradigm and PocketFlow methodology.
> **Note**: If you're making webpages, websites, etc, serve the stuff. Even if you're making mobile apps, if it's possible to serve it, serve it. If you're making something that can't be served, at least serve the directory. Try to serve whatever you serve on port 5002 unless specified otherwise or if it is blocked (and in that case, tell the user the different port you chose). Be sure that any longrunning process you do (eg, serving something) is backgrounded (eg daemonized or & etc)
