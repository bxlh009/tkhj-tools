## Treat the prompt as a working component

Prompt debugging becomes unreliable when the only test is “Did I like this
answer?” A useful prompt has a job, an expected output, and examples that expose
different ways it can fail. The goal is not to discover one magical wording. It
is to produce acceptable behavior across a small, representative set of inputs.

Google’s prompt design guidance emphasizes clear instructions, context,
consistent examples, and iteration based on observed responses. A compact test
set turns those ideas into a repeatable workflow.

## Define the contract

Write four lines before editing the prompt:

1. **Task:** what transformation or decision should happen?
2. **Input boundary:** what information may the model use?
3. **Output contract:** which fields, length, tone, or format are required?
4. **Failure rule:** when should the model abstain or flag uncertainty?

Avoid goals such as “make it better” or “sound intelligent.” Replace them with
checks another person can apply. For example: “Return a JSON object containing
`claim`, `source_sentence`, and `confidence_note`; do not add a claim when the
source sentence is absent.”

## Build five varied cases

Start with five inputs, not fifty. Include one ordinary case, one ambiguous case,
one case with missing information, one case with distracting text, and one edge
case that previously failed. Keep the expected property beside each input.

The cases should vary in content while preserving the same task. Repeating five
near-identical examples can make a prompt look stable while leaving the actual
boundary untested.

## Change one thing at a time

Run the baseline prompt against all five cases and record failures. Then make one
change: clarify an instruction, add a delimiter, supply a varied example, or
tighten the output contract. Run all cases again.

Changing persona, structure, examples, tone, and output format together hides
which change helped. It can also fix one example while silently breaking another.
A one-change loop makes regressions visible.

## Original practice example

This example is original.

Task: extract a deadline from a supplied paragraph.

Weak instruction: “Find the deadline and explain it.”

Test cases reveal three failures: the model invents a deadline when none appears,
confuses an issue date with a response date, and returns prose that downstream
code cannot parse.

A stronger contract is: “Use only the text inside `<source>`. Return
`{"deadline": null, "evidence": null}` when no response deadline is stated.
Otherwise copy the shortest sentence fragment that states the deadline. Return
JSON only.”

The answer is better not because it sounds more authoritative, but because the
input boundary, missing-data behavior, evidence requirement, and output shape can
all be checked.

## Original practice example

This example is original.

Task: classify support messages as billing, access, or product feedback.

The first three examples are clean and direct, so the prompt passes. A fourth
message says, “I cannot log in to download the invoice.” It contains both access
and billing language. Add an expected rule instead of another vague instruction:
classify by the action required first; if access must be restored before billing
can be handled, return `access` and preserve `billing` as a secondary tag.

The reasoning is explicit and reusable. The new case tests priority, not merely
keyword recognition.

## Keep a failure log

Record the date, input label, observed failure, prompt change, and result. Group
failures by type: missing context, instruction conflict, unsupported claim,
format violation, or edge-case ambiguity. When several failures share a type,
repair the contract rather than adding a separate exception for every sentence.

## Limits and uncertainty

A five-case set is a starting point, not evidence that a prompt is production
ready. Model updates, new input distributions, and adversarial text can change
behavior. Expand the set with real failures, keep consequential actions behind
human review, and rerun tests when the model or prompt changes.

## When to use or skip it

Use this method when a prompt supports a repeated workflow and its outputs can be
checked. Skip elaborate prompt optimization for one-off, low-risk brainstorming.
If the task requires current facts, private system access, or deterministic
calculation, prompt wording alone is insufficient; add retrieval, permissions,
code, or another appropriate control.
