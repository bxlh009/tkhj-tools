---
title: "GPT-5.6 Sol Is Here: Cheaper Per Token, Faster Than GPT-4o, and the Codex Question"
slug: "gpt-56-sol-release-and-chatgpt-work"
date: "2026-07-10"
category: "ai-news"
primary_keyword: "GPT-5.6 release"
long_tail_keywords: ["GPT-5.6 pricing", "GPT-5.6 vs GPT-4o", "ChatGPT Work agent", "Codex merged"]
word_count: 820
estimated_read_min: 9
structure_template: "B"
---

OpenAI launched GPT-5.6 on July 9, 2026, and the story is not just that they shipped a new model. It is that they shipped three of them at once, folded Codex into the main ChatGPT app, and quietly admitted something they have been dancing around for a year: enterprises are price-sensitive, even for the best model on the leaderboard.

The GPT-5.6 family comes in three tiers. Sol is the flagship, priced at $5 per million input tokens and $30 per million output. Terra sits in the middle at $2.50 / $15. Luna is the budget tier at $1 / $6. For context, Sol's output price is roughly half of what GPT-4o charged at its peak, and OpenAI is betting that cheaper-per-token plus faster inference will win over the enterprise buyers who have been quietly testing Claude and Gemini side by side.

The early numbers back that up on the performance side. Sol hit 53.6% on the AgentsLastExam benchmark, clearing the previous highest score of 44.4%. On coding tasks, Sol reportedly lands around 80% on a private internal battery. What caught my eye, though, is the efficiency claim: Sol produces 54% fewer output tokens than its predecessor and runs 57% faster. If that holds up in real workloads, the cost-per-task story is not just "cheaper token" but "fewer tokens needed to finish the same job." That is a different pitch than the one OpenAI made a year ago, when raw benchmark dominance was enough.

Then there is Codex. If you have been following the developer tools space, you know Codex has lived as a standalone coding agent for the past year. OpenAI announced it is merging Codex into ChatGPT on desktop, and the user response was, to put it mildly, mixed. Sam Altman took to Twitter to clarify that Codex is "not going away," but the decision to fold it into the main app has left some developers wondering whether the specialized tooling will survive the consolidation. I have seen this before: a powerful standalone feature gets absorbed into the parent product, gets a worse UX six months later, and the original power users quietly migrate. I hope that is not the pattern here, but the skepticism is warranted given how these product absorptions typically play out.

The third announcement, ChatGPT Work, is OpenAI's answer to a question every knowledge worker has been asking: can an agent actually run a project end to end, not just answer prompts? Work is pitched as a mode inside ChatGPT that lets an agent work for hours on a task, generate documents and spreadsheets, and operate on a schedule. OpenAI says enterprise customers are already using it to coordinate multi-step workflows across teams. The idea is compelling. But if you have tested agents for any length of time, you know the gap between "demo video" and "does not corrupt my spreadsheet at 2 AM" is where most of these tools die. I have not tested Work myself yet, so I am not going to pretend I have a verdict. I will say the concept is what the space needs. The execution is what separates a useful feature from an expensive beta.

And the competition did not sit still. While OpenAI was launching GPT-5.6, Claude briefly overtook it on the lmsys leaderboard. The lead did not last by all accounts, but the fact that it happened at all during an OpenAI launch week tells you something about how tight the top of this market has become. Anthropic's Fable 5 also appears to be cheaper than expected. The days when OpenAI could ship a model and dominate the conversation for three months are over. The gap is weeks now, not months.

Where does this leave the rest of us? If you are a solo practitioner or small team watching the GPT-5.6 release, here is what I would focus on. First, Sol's per-token pricing makes it worth retesting if you evaluated GPT-4o and decided the cost was too high for routine tasks. Second, hold off on the panic migration. If your current model setup works, GPT-5.6 is an incremental step for most workloads, not a revolution. Watch the community benchmarks over the next two weeks before you restructure your pipeline. Third, if you are a developer who relies on Codex, start asking OpenAI hard questions about the roadmap for standalone tooling before your workflow gets caught in the consolidation.

The GPT-5.6 launch is a solid engineering release wrapped in a pricing story. OpenAI admitted, in their own way, that raw performance is table stakes. The thing they are actually selling now is efficiency. Whether that efficiency survives contact with real enterprise budgets is the story I will be watching for the next quarter.

## References

- https://www.ithome.com/0/891/213.htm
- https://www.ithome.com/0/891/201.htm
