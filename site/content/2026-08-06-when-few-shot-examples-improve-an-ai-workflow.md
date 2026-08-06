## What the source establishes

Google AI for Developers documents few-shot prompting as one of several strategies for structuring prompts to the Gemini API. The guidance frames few-shot examples as a way to show a model what you want, rather than only telling it. The core idea is straightforward: when you include a small number of input-output pairs in a prompt, the model can infer the pattern, format, or reasoning style you expect for new inputs.

The source positions few-shot prompting alongside other strategies such as zero-shot prompting, chain-of-thought prompting, and role-based prompting. It does not present few-shot as universally superior. Instead, it treats it as a tool that fits specific situations—particularly when the task has a clear structure, when the output format matters, or when the model needs to learn a non-obvious pattern from the prompt itself.

The OECD AI Principles are cited as a broader reference point for responsible AI use. They emphasize transparency, accountability, and human oversight. In the context of few-shot prompting, these principles surface as a reminder that examples shape model behavior, and poorly chosen examples can introduce bias, narrow the model's range of valid responses, or encode assumptions that should be questioned.

What the source does not do: it does not provide benchmarks comparing few-shot to zero-shot performance. It does not quantify how many examples are "enough." It does not test specific prompts or report measured outcomes. The guidance is descriptive and strategic, not empirical.

## What this means

Few-shot examples work because they give the model a concrete reference. Language models are pattern-matching systems trained on vast text. When you show it a few examples of the kind of output you want, you are essentially narrowing the space of plausible responses. This can improve accuracy on structured tasks, enforce a consistent format, or teach the model a reasoning style it might not otherwise adopt.

But the mechanism also carries trade-offs. Examples are a form of instruction, and like any instruction, they can be too narrow. If your examples all follow one pattern, the model may struggle when a new input falls outside that pattern. This is the overfitting risk the source alludes to: a prompt that works well for the cases you showed it may fail on cases you did not anticipate.

The OECD principles add a layer of caution. If your examples come from a single domain, demographic, or style, the model may learn to replicate that narrowness. This is not a technical limitation alone—it is a design choice with real consequences. A prompt that only shows examples of formal business writing will produce formal business writing, even when a casual tone is more appropriate. A prompt that only shows examples from one cultural context may struggle with inputs from another.

The practical takeaway is that few-shot prompting is a decision about what you want the model to learn—and what you are willing to let it overlook.

## A practical next step

If you are considering adding few-shot examples to a prompt, follow this workflow:

1. **Define the decision you need the model to make.** Write it as a single sentence. For example: "Classify customer messages by urgency and recommended response type."

2. **Write three to five examples that cover the range of inputs you expect.** Do not write examples that all look the same. Include edge cases. Include inputs that are ambiguous. Include inputs that might tempt the model to choose the wrong category.

3. **Label your examples clearly.** Use a consistent format. For instance:

   **Input:** "My order hasn't arrived and it's been two weeks."
   **Output:** Urgency: High | Response type: Escalation + tracking check

   **Input:** "Can you tell me what materials this product is made from?"
   **Output:** Urgency: Low | Response type: Informational

   These are non-official examples created for illustration. They are not drawn from any Google or OECD publication.

4. **Test the prompt on inputs you did not include in your examples.** Look for patterns in where the model succeeds and where it fails. If it consistently misclassifies a certain type of input, add an example that covers that case.

5. **Review your examples against the OECD principles.** Ask: Do these examples represent a diverse set of inputs? Do they encode assumptions that could exclude valid responses? Are they transparent about what the model is being asked to do?

6. **Document your prompt.** Keep a record of the examples you included, why you included them, and what you observed during testing. This makes it easier to revise the prompt later and to explain your choices to others.

## Limits and uncertainty

Few-shot prompting has real limits that the source acknowledges implicitly and that responsible use requires you to make explicit.

**The number of examples is unknown.** The source does not specify an optimal count. Three examples may be enough for a simple classification task. Ten may be needed for a complex reasoning task. More is not always better. Excessively long prompts increase token cost and can dilute the signal from your best examples.

**Example quality matters more than quantity.** A single clear, well-chosen example can outperform five mediocre ones. An example that contains errors, ambiguity, or bias will teach the model to repeat those problems.

**The model can overfit to your examples.** If your examples all follow one format, the model may produce outputs that match that format even when a different format would be more appropriate. This is not a bug in the model—it is a feature of how few-shot prompting works. The model is doing what you showed it. The question is whether what you showed it is sufficient.

**Bias is a real risk.** Examples are a form of training data, even when they are embedded in a prompt. If your examples come from a narrow source, the model may replicate that narrowness. The OECD principles remind us that this is not a theoretical concern. It is a design responsibility.

**The source does not provide benchmarks.** There is no published data from Google or the OECD that quantifies how much few-shot prompting improves performance on specific tasks. Any claim about effectiveness should be treated as a hypothesis to test, not a fact to assume.

## When to use or skip it

Use few-shot prompting when:

- The task has a clear structure that is easier to show than to describe.
- The output format matters and the model tends to ignore formatting instructions.
- The reasoning pattern is non-obvious and benefits from concrete illustration.
- You have a small but representative set of examples that cover the range of inputs you expect.
- You are willing to test and revise the prompt based on observed performance.

Skip few-shot prompting when:

- The task is simple enough that a clear instruction works reliably.
- You do not have representative examples and risk teaching the model a narrow pattern.
- The input space is too diverse to cover with a small set of examples.
- You need the model to adapt flexibly to unfamiliar inputs rather than follow a learned pattern.
- Adding examples would significantly increase token cost without a clear benefit.

The decision is not whether few-shot prompting is good or bad. It is whether your task, your examples, and your constraints make it the right tool for the job. The source gives you the framework. Your judgment determines the outcome.

## Sources

- https://ai.google.dev/gemini-api/docs/prompting-strategies
- https://oecd.ai/en/ai-principles
