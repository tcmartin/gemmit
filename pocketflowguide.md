# Agentic Coding: Humans Design, Agents Code!

> If you are an AI agent involved in building LLM systems, read this guide VERY, VERY carefully! This is the most important chapter in the entire document.
>
> **Throughout development:**
>
> 1. Start with a small, simple solution.
> 2. Design at a high level (`docs/design.md`) before implementation.
> 3. Frequently ask humans for feedback and clarification.

---

## Agentic Coding Steps

Agentic Coding is a collaboration between **Human System Design** and **Agent Implementation**:

| Step              | Human Effort | AI Effort  | Description                                                         |
| ----------------- | ------------ | ---------- | ------------------------------------------------------------------- |
| 1. Requirements   | ★★★ High     | ★☆☆ Low    | Humans understand requirements & context.                           |
| 2. Flow Design    | ★★☆ Medium   | ★★☆ Medium | Humans outline high-level flow; AI fills in details.                |
| 3. Utilities      | ★★☆ Medium   | ★★☆ Medium | Humans provide APIs/integrations; AI implements utility functions.  |
| 4. Data Design    | ★☆☆ Low      | ★★★ High   | AI designs data schema; humans verify.                              |
| 5. Node Design    | ★☆☆ Low      | ★★★ High   | AI plans node I/O based on flow; humans review.                     |
| 6. Implementation | ★☆☆ Low      | ★★★ High   | AI writes code for nodes and flow.                                  |
| 7. Optimization   | ★★☆ Medium   | ★★☆ Medium | Humans evaluate; AI optimizes prompts, flow, and parameters.        |
| 8. Reliability    | ★☆☆ Low      | ★★★ High   | AI writes tests, retries, and self-evaluation nodes for robustness. |

---

### 1. Requirements

* **Clarify requirements** and assess AI suitability:

  * Good for routine tasks (forms, emails).
  * Good for creative tasks with defined inputs (slides, SQL).
  * Not good for ambiguous strategy problems.
* **Keep it user-centric**: frame problems from the user’s perspective.
* **Balance complexity vs. impact**: deliver high-value features quickly.

### 2. Flow Design

* Outline how your system orchestrates **nodes**.
* Identify design patterns: Map-Reduce, Agent, RAG, Workflow.
* For each node:

  * One-line description of function.
  * Inputs, outputs, and actions.
* Draw your flow (e.g., a Mermaid diagram):

  ```mermaid
  flowchart LR
    start[Start] --> batch[Batch]
    batch --> check[Check]
    check -->|OK| process
    check -->|Error| fix[Fix]
    fix --> check

    subgraph process[Process]
      step1[Step 1] --> step2[Step 2]
    end

    process --> endNode[End]
  ```
* If humans can’t specify the flow, AI agents can’t automate it.

### 3. Utilities

* Identify external **utility functions** (body of the AI):

  * Reading inputs (emails, Slack).
  * Writing outputs (reports, messages).
  * External tools (LLMs, web search).
* Document I/O and purpose for each utility.
* Example:

  ```python
  def call_llm(prompt):
      client = OpenAI(api_key="YOUR_KEY")
      r = client.chat.completions.create(...)
      return r.choices[0].message.content
  ```

### 4. Data Design

* Design a **shared store** (in-memory dict or database):

  ```python
  shared = {
      "user": {"id": "user123", "context": {...}},
      "results": {}
  }
  ```
* Nodes read/write to this contract.

### 5. Node Design

* For each node:

  * **Type**: Regular / Batch / Async.
  * **Prep**: What data to read from `shared`.
  * **Exec**: Which utility functions to call.
  * **Post**: Where to write outputs in `shared`.
* Avoid catching exceptions here; leverage built-in retries.

### 6. Implementation

* AI implements nodes and flow based on design.
* **Keep it simple**; fail fast using Node retry mechanisms.
* Add logging for easier debugging.

### 7. Optimization

* Use human intuition for quick evaluations.
* **Redesign flow** (back to Step 2) as needed.
* **Prompt engineering** and **in-context learning** for fine-tuning.

### 8. Reliability

* **Node Retries**: Ensure outputs meet requirements; configure retry settings.
* **Logging & Visualization**: Track and visualize node performance.
* **Self-Evaluation**: Add LLM-powered review nodes for uncertain outputs.

---

### Example Project Structure

```
my_project/
├── main.py        # Entry point
├── nodes.py       # Node definitions
├── flow.py        # Flow orchestration
├── utils/         # Utility functions
│   ├── call_llm.py
│   └── search_web.py
├── requirements.txt
└── docs/
    └── design.md  # High-level design docs
```

> **Note**: Keep your `docs/requirements.md`, `docs/design.md`, and `docs/tasks.md` in sync throughout development.

