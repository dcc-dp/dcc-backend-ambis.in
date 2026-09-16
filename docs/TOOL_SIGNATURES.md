# Hermes Tool Interfaces

For Dayat's orchestration loop (`app/api/v1/services/hermes_agent.py`). These four tools live in
`app/tools/` and are what Hermes calls at each step of a student attempt — the chassis (agent loop,
SSE streaming, session/turn management) is Dayat's; everything below the tool-call boundary is Ooka's.

All four are implemented, unit-tested, and pushed to `main` as of `e0d560d`. None of them are wired
into `ask.py`/`hermes_agent.py` yet — both are still full mocks. That wiring is the next step, and can
start directly from the signatures below.

## Expected call order per student attempt

```
Evaluator.evaluate()
    -> Diagnostician.diagnose()   (only if the attempt was wrong)
    -> PolicyEngine.next_intervention()
    -> StateManager.update()
```

`Evaluator` and `Diagnostician` never see each other's output — both take the same
`(exercise, student_answer)` pair independently. `PolicyEngine` is pure (no DB/LLM) and only needs the
attempt history for the *current problem*. `StateManager` is the only one that writes anything.

## 1. `Evaluator` — grading (`app/tools/evaluator.py`)

```python
Evaluator(llm_client: LLMClient)

await evaluator.evaluate(exercise: Exercise, student_answer: str) -> EvaluationResult
# EvaluationResult(is_correct: bool, error_type: str | None)
# error_type is None iff is_correct is True; otherwise one of:
#   "calculation" | "procedural" | "conceptual" | "prerequisite"
```

- MCQ exercises: deterministic key match, no LLM call, `error_type` always `"conceptual"` when wrong
  (an MCQ distractor is always a tagged wrong rule, never a slip).
- Free-form/short-answer exercises: one LLM call via the grading-rubric prompt. That prompt only ever
  sees `{question, correct_answer, solution_steps, student_answer}` — never ladder/session/intervention
  context, so grading stays unbiased regardless of what the policy engine does next.
- Raises `ValueError` if `student_answer` is over 2000 chars, `LLMResponseError` if the LLM response
  doesn't parse into a valid result.

## 2. `Diagnostician` — misconception matching (`app/tools/diagnostician.py`)

```python
Diagnostician(db: AsyncSession, llm_client: LLMClient)

await diagnostician.diagnose(exercise: Exercise, student_answer: str) -> str | None
# returns a misconceptions.code, or None if no misconception was detected
```

- MCQ: looks up the selected option's tagged `misconception_id`, resolves it to a `code` — no LLM.
- Free-form: LLM proposes a hypothesis against the *closed set* of misconceptions tagged to that
  exercise's concept; accepted only on an exact code match, otherwise `None`. Never open-label.
- Same 2000-char guard and `LLMResponseError` behavior as `Evaluator`.

## 3. `PolicyEngine` — intervention ladder (`app/tools/policy_engine.py`)

```python
next_intervention(
    attempts_for_problem: list[AttemptRecord],   # AttemptRecord(error_type, misconception_code, is_correct)
    misconception_seen_before: bool,
) -> PolicyDecision
# PolicyDecision(kind: str, rule_code: str, reason: str)
# kind is one of: "guiding_question" | "hint" | "explanation" | "worked_example"
```

- Pure function — no DB, no LLM, no I/O. Safe to call directly, synchronously.
- `attempts_for_problem` must be scoped to the **current problem_id only** — the ladder resets per
  problem, it does not look across a whole session.
- `rule_code`/`reason` are for logging into `interventions`, not for display to the student.

## 4. `StateManager` — mastery/state update (`app/tools/state_manager.py`)

```python
StateManager(db: AsyncSession)

await state_manager.update(
    student_id: UUID,
    concept_id: UUID,
    score: float,                    # 1.0 if correct, 0.0 if incorrect
    misconception_code: str | None,  # None if none detected this attempt
) -> StudentConceptState
```

- One atomic `INSERT ... ON CONFLICT DO UPDATE` — never read-then-write from Python. Safe to call
  concurrently for different students/concepts.
- Updates EWMA mastery, confidence, correct streak, and bumps `misconception_counts` in one statement.
- Commits internally — call this last, after grading/diagnosis/policy are all resolved for the attempt.

## Not covered here (still open)

- Intervention *content* prompts (hint/guiding_question/explanation/worked_example text generation) —
  build-order item 4, not started.
- Wiring these four into `ask.py`/`hermes_agent.py` end-to-end — the actual next task once this doc is
  read.
