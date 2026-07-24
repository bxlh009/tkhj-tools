## Start with the consequence, not the confidence

An AI answer can sound certain without being reliable. The useful first question is
not “Does this read well?” It is “What happens if this is wrong?” A harmless
brainstorming suggestion needs a lighter check than a claim placed in a report, a
decision sent to a customer, or an instruction that changes code or data.

Use three risk levels. Low-risk output is reversible and private: alternative
headlines, questions to investigate, or a rough outline. Medium-risk output may
shape someone else’s work but can still be reviewed before use. High-risk output
affects money, safety, legal obligations, access, production systems, or a person’s
opportunities. The higher the consequence, the less weight fluency should carry.

## Separate four kinds of content

Copy the answer into a working note and label each important sentence as one of
four types:

1. **Supplied fact:** directly present in material you gave the model.
2. **External claim:** a fact about the world that needs a source.
3. **Inference:** a conclusion drawn from facts, assumptions, or patterns.
4. **Recommendation:** a proposed action that depends on goals and tradeoffs.

This separation prevents a common mistake: treating an inference as if it came
from a source. It also makes review efficient. Supplied facts can be checked
against the input. External claims need independent evidence. Inferences need
their assumptions exposed. Recommendations need an owner who accepts the
tradeoff.

## Run the source check

For every external claim, ask for a primary source or locate one independently.
Do not treat a model-generated citation as proof that the source exists or
supports the sentence. Open the source, find the relevant passage, confirm its
date and scope, and record the link beside the claim.

If a product vendor supplies the source, preserve the attribution: “The vendor
states…” is different from “Independent testing shows…”. A release note can
establish what a company announced. It cannot establish that the feature works
equally well for every user or workflow.

## Test the fragile parts

Some claims are easier to verify by running a small test than by discussing them.
Calculations can be recomputed. Code can run against a focused test. A summary can
be compared with the source paragraph. A structured extraction can be checked
against several records, including awkward edge cases.

Make the test small and reversible. Record the input, expected result, actual
result, and failure. One successful example is not enough when the task has
different formats or edge cases.

## Original practice scenario

This scenario is original and is not a report of a real organization.

An AI assistant summarizes a policy document and says a request “must be answered
within ten days.” The sentence is clear and plausible. Label it as an external
claim because the time limit is not visible in the prompt excerpt. The next step
is to find the controlling section in the policy, confirm whether the document
means calendar or business days, and record any exceptions.

The answer is not ready for operational use until those points are verified.
Fluent wording does not reduce the consequence of an incorrect deadline.

## Original practice scenario

This scenario is also original.

An AI tool recommends replacing a manual review with automatic approval because
“accuracy is high.” Label that sentence as both an external claim and a
recommendation. Ask what dataset produced the accuracy figure, which error types
were counted, and what a false approval costs. Then run a shadow test where the
automation makes recommendations but cannot execute them.

The reasoning is simple: aggregate accuracy does not describe the costliest
failure, and a reversible pilot reveals errors without transferring authority.

## Decide what can leave the draft

An answer is ready to use only when the remaining uncertainty matches the
consequence. Low-risk brainstorming may retain openly labeled uncertainty.
Medium-risk work should have claims linked and key outputs sampled. High-risk
work needs an accountable human reviewer, an appropriate domain process, and a
record of what was checked.

The NIST AI Resource Center describes testing, evaluation, verification, and
validation as practical parts of managing AI systems. This checklist is a compact
editorial adaptation, not a substitute for a formal risk-management program.

## Limits and uncertainty

No checklist can prove that every claim is correct. Sources may be outdated,
tests may omit edge cases, and reviewers may share the model’s assumptions.
Increase review depth when consequences rise, and preserve a way to correct or
reverse the result.
