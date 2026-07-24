---
title: "Build a Five-Case Test Set for an AI Prompt"
slug: "2026-07-10-build-a-five-case-test-set-for-an-ai-prompt"
date: "2026-07-10"
domain: "ai"
category: "AI"
primary_keyword: "Build a Five-Case Test Set for an AI Prompt"
word_count: 1004
---
When refining prompts for Large Language Models (LLMs), relying on a single "happy path" example is insufficient. A robust evaluation strategy requires a structured test set that probes the boundaries of your instruction. This article outlines a method to build a five-case test set, covering an ordinary case, ambiguity, missing information, distracting input, and a known edge case.

This approach transforms prompt engineering from guesswork into a repeatable quality assurance workflow. By systematically stress-testing these five dimensions, you can identify where your model fails to follow instructions or hallucinates content before deployment.

## The Five-Case Framework

A balanced test set should not only verify that the prompt works but also demonstrate how it behaves under pressure. The following five cases provide comprehensive coverage of common failure modes.

### 1. The Ordinary Case
**Purpose:** Establish a baseline.
This case uses a standard, well-formed input that clearly aligns with the prompt’s intent. It verifies that the core functionality works as expected when conditions are ideal. If the model fails here, the fundamental logic of the prompt is likely flawed.

*   **Input Characteristic:** Clear, concise, and directly relevant to the task.
*   **Expected Outcome:** Accurate, compliant response matching the desired format and tone.

### 2. The Ambiguity Case
**Purpose:** Test interpretation resilience.
Real-world inputs often lack precision. This case introduces vague language or multiple possible interpretations. It reveals whether your prompt includes sufficient constraints to guide the model toward a single correct interpretation or if it allows the model to guess incorrectly.

*   **Input Characteristic:** Uses terms like "soon," "large," or "improve" without defining metrics or deadlines.
*   **Expected Outcome:** The model either asks for clarification (if instructed) or makes a reasonable, documented assumption. Failure indicates the prompt needs stricter definitions.

### 3. The Missing Information Case
**Purpose:** Evaluate handling of incomplete data.
Users frequently omit critical details. This case tests whether the prompt instructs the model to proceed with assumptions, request more data, or flag the error. It prevents the model from silently generating incorrect or hallucinated content due to gaps in context.

*   **Input Characteristic:** Lacks a key variable required by the prompt (e.g., asking for a summary of a document that isn’t provided).
*   **Expected Outcome:** The model identifies the missing element and responds appropriately based on its instructions (e.g., "I cannot summarize because the text is missing").

### 4. The Distracting Input Case
**Purpose:** Assess signal-to-noise ratio.
Inputs often contain irrelevant information, formatting errors, or conversational filler. This case checks if the model can filter out noise and focus solely on the actionable parts of the query. It is crucial for preventing "context leakage," where the model gets confused by unrelated data.

*   **Input Characteristic:** Contains large blocks of irrelevant text, markdown errors, or off-topic questions mixed with the primary request.
*   **Expected Outcome:** The model ignores the noise and processes only the relevant instruction. Failure suggests the need for clearer delimiters or negative constraints in the prompt.

### 5. The Known Edge Case
**Purpose:** Stress-test specific boundaries.
This case targets a known limitation or unusual scenario relevant to your domain. Examples include extreme length limits, special characters, contradictory instructions, or culturally sensitive topics. It ensures the model handles outliers gracefully rather than crashing or producing unsafe content.

*   **Input Characteristic:** Pushes technical limits (e.g., 10,000 words) or contains logical paradoxes.
*   **Expected Outcome:** The model adheres to safety guidelines or truncates output cleanly, rather than entering an infinite loop or generating harmful content.

## Workflow: Constructing and Running the Test Set

To implement this framework effectively, follow this structured workflow.

### Step 1: Define Success Criteria
Before testing, write down what a "good" response looks like for each of the five cases. For the ordinary case, success might be a JSON output. For the ambiguity case, success might be a polite request for clarification.

### Step 2: Draft the Test Inputs
Create five distinct input strings. Ensure they are reproducible. Store them in a simple CSV or JSON file for easy iteration.

```json
[
  {
    "case": "ordinary",
    "input": "Summarize the following paragraph in one sentence: [Clear text]"
  },
  {
    "case": "ambiguous",
    "input": "Make this better: [Vague text]"
  },
  ...
]
```

### Step 3: Execute and Compare
Run each input through your prompt template. Compare the outputs against your success criteria. Use a consistent temperature setting (e.g., 0.2) to ensure deterministic results during testing.

### Step 4: Iterate
If a case fails, refine the prompt. Add explicit instructions for handling ambiguity or missing data. Re-run the entire five-case set after each change to ensure you haven’t broken the ordinary case while fixing the edge case.

## Limits and Uncertainty

This framework provides a structured method for evaluating prompt behavior, but it has inherent limitations.

*   **Static Nature:** A five-case test set captures specific scenarios but cannot guarantee performance across all possible real-world variations. It is a sampling method, not a complete audit.
*   **Model Variability:** Different models (or even different versions of the same model) may interpret ambiguity differently. Results from one model do not automatically transfer to another.
*   **Subjectivity:** Judging "ambiguity" or "distraction" can be subjective. What seems clear to one engineer may seem vague to another. Define your criteria explicitly to reduce bias.
*   **No Performance Metrics:** This guide focuses on qualitative correctness. It does not measure latency, cost, or throughput. A prompt may pass these tests but still be too slow or expensive for production use.

## When to Use It

Use this five-case test set during the initial development phase of any new prompt or when making significant changes to an existing one. It is particularly valuable when:

*   Deploying prompts for critical business tasks where accuracy is paramount.
*   Onboarding new team members to your prompt engineering standards.
*   Debugging unexpected model behaviors in production.

## When to Skip It

You may skip this rigorous testing if:

*   The prompt is for low-stakes, creative brainstorming where exact compliance is not required.
*   You are using a pre-built, vendor-managed system where prompt customization is limited or discouraged.
*   Time constraints are extreme, and a quick heuristic check is sufficient for immediate needs (though this increases risk).

## Sources

- https://ai.google.dev/gemini-api/docs/prompting-strategies
