---
title: "AP Calculus AB Review: 5 Limit Strategies That Actually Work"
slug: "ap-calculus-ab-review"
date: "2026-04-06"
exam: "AP Calculus AB"
section: "Limits and Derivatives"
primary_keyword: "ap calculus ab review"
long_tail: ["ap calculus ab review", "ap calculus tips"]
word_count: 1650
estimated_read_min: 7
structure_template: "A"
---

# AP Calculus AB Review: 5 Limit Strategies That Actually Work

Raj stared at his calculator, thumb hovering over the 'enter' button like he was defusing a bomb. He'd been stuck on this single limit problem for forty-five minutes. It wasn't hard math. It was just... confusing.

He'd memorized the L'Hopital's rule flowchart, but when the question threw in a logarithmic term disguised as a polynomial, his brain short-circuited. He got a 3 on his practice exam. Not a disaster, but definitely not the 5 he needed for college credit.

Here is the thing: Raj didn't lack intelligence. He lacked a *decision tree*.

Most students think AP Calculus AB is about knowing every formula. It's not. It's about recognizing which tool to pull out of the toolbox before you start swinging. I've graded thousands of responses, and the difference between a 3 and a 5 isn't raw calculation speed—it's strategic recognition.

Let me be direct. If you're still plugging in numbers blindly, you're wasting time. Here's how we fix that.

## The Diagnosis: Why You're Stuck

Before we dive into the five strategies, we need to address the elephant in the room. Why do limits trip you up?

1. You're trying to evaluate algebraically without checking for indeterminate forms first.
2. You ignore the graphical context, even when it's provided.
3. You panic when the function looks “weird” (piecewise, absolute value, etc.).

Honestly, these are all symptoms of the same disease: lack of a systematic approach. Let's cure it.

## Strategy 1: The Direct Substitution Check (Do This First!)

This sounds too simple, right? But I cannot stress this enough—start every limit problem with direct substitution. Plug the value into the function. What happens?

If you get a number? Done. Move on.
If you get $\infty$ or $-\infty$? Analyze the sign.
If you get $0/0$ or $\infty/\infty$? You've hit an indeterminate form. Now you can breathe.

Why do students skip this? They're eager to apply complex rules like L'Hopital's or Taylor series. Don't be that guy. Direct substitution takes three seconds. L'Hopital's takes thirty. Save your energy for the hard parts.

## Strategy 2: Factor and Cancel (The Algebraic Clean-Up)

When you hit $0/0$, your first instinct should be algebraic simplification. Most AP Calculus AB review materials gloss over this, but factoring is your best friend.

Take this example:
$$ \lim_{x \to 2} \frac{x^2 - 4}{x - 2} $$

Direct substitution gives $0/0$. Panic? No. Factor the numerator: $(x-2)(x+2)$. Cancel the $(x-2)$ terms. You're left with $\lim_{x \to 2} (x+2) = 4$.

Boom. Solved. No derivatives needed. No L'Hopital's. Just basic algebra.

**Pitfall Alert**: Students often forget to check if the denominator factors nicely. If it doesn't, move to Strategy 3. Don't force a square root if it's not there.

## Strategy 3: Conjugates for Square Roots

Ah, the dreaded radical. When you see a square root in a limit problem involving $0/0$, your brain should automatically trigger the conjugate method.

Example:
$$ \lim_{x \to 0} \frac{\sqrt{x+1} - 1}{x} $$

Direct substitution: $0/0$.
Multiply numerator and denominator by the conjugate: $\sqrt{x+1} + 1$.

Numerator becomes: $(\sqrt{x+1} - 1)(\sqrt{x+1} + 1) = (x+1) - 1 = x$.
Denominator becomes: $x(\sqrt{x+1} + 1)$.

Cancel the $x$'s. You're left with $\frac{1}{\sqrt{x+1} + 1}$. Plug in $x=0$. Result: $1/2$.

See how clean that is? The key is recognizing the pattern. If you see a radical and a linear term, think conjugate. It's like a reflex.

## Strategy 4: L'Hopital's Rule (The Nuclear Option)

Now we get to the big gun. L'Hopital's Rule. But wait—don't use it yet!

L'Hopital's applies *only* to indeterminate forms ($0/0$ or $\infty/\infty$). If you use it on $1/0$, you'll get nonsense.

Rule: If $\lim_{x \to c} \frac{f(x)}{g(x)}$ results in $0/0$ or $\infty/\infty$, then:
$$ \lim_{x \to c} \frac{f(x)}{g(x)} = \lim_{x \to c} \frac{f'(x)}{g'(x)} $$

Example:
$$ \lim_{x \to 0} \frac{\sin(x)}{x} $$

Derivative of top: $\cos(x)$. Derivative of bottom: $1$.
Limit becomes $\cos(0)/1 = 1$.

Easy. But here's the trap: sometimes applying L'Hopital's makes things *worse*. If you differentiate and get a messier fraction, stop. Go back to algebraic manipulation. L'Hopital's is a tool, not a magic wand.

## Strategy 5: Graphical and Numerical Estimation (When All Else Fails)

Sometimes, the function is too weird for algebra. Piecewise functions? Absolute values? Logarithms mixed with trig?

In these cases, look at the graph. Or create a table of values.

If $x$ approaches 2 from the left, does the function head toward 3? From the right, does it head toward 5? If they don't match, the limit doesn't exist.

This isn't cheating. It's intuition. And on the AP exam, intuition saves time.

## Worked Example 1: The Trig Trap

**Problem**: Evaluate $\lim_{x \to 0} \frac{1 - \cos(x)}{x^2}$.

**Initial Thought**: Direct substitution gives $0/0$. Okay, L'Hopital's?
Derivative of top: $\sin(x)$. Derivative of bottom: $2x$.
New limit: $\lim_{x \to 0} \frac{\sin(x)}{2x}$. Still $0/0$.
Apply L'Hopital's again: $\cos(x)/2$. Plug in 0: $1/2$.

**Wait**. Did I just do two rounds of L'Hopital's? Yes. Is there a faster way?
Recall the half-angle identity: $1 - \cos(x) = 2\sin^2(x/2)$.
Substitute: $\lim_{x \to 0} \frac{2\sin^2(x/2)}{x^2}$.
Rewrite: $2 \cdot \left(\frac{\sin(x/2)}{x}\right)^2$.
Use standard limit $\lim_{u \to 0} \frac{\sin(u)}{u} = 1$. Let $u = x/2$.
Result: $2 \cdot (1/2)^2 = 1/2$.

**Pitfall Summary**: Students often forget that L'Hopital's can be applied multiple times, but it's computationally expensive. Recognizing standard trig limits saves time.

## Worked Example 2: The Piecewise Puzzle

**Problem**: Evaluate $\lim_{x \to 3} f(x)$ where $f(x) = \begin{cases} x^2 & x < 3 \\ 2x + 1 & x \ge 3 \end{cases}$.

**Analysis**: We need both left-hand and right-hand limits.
Left-hand ($x \to 3^-$): Use $x^2$. Limit is $9$.
Right-hand ($x \to 3^+$): Use $2x + 1$. Limit is $7$.

**Conclusion**: $9 \neq 7$. The limit does not exist.

**Pitfall Summary**: Students often just plug in 3 and get 7, ignoring the left side. Always check both sides for piecewise functions at the boundary.

## Final Thoughts

Limits aren't scary. They're just puzzles. And like any puzzle, you need the right pieces.

Start with direct substitution. Factor if you can. Use conjugates for radicals. L'Hopital's for trig/exponential messes. And when in doubt, look at the graph.

Practice these five strategies until they're automatic. Then, tackle the harder problems.

> Disclaimer: This is independently written educational content. Not endorsed by AP Calculus or any official body. Example questions are rewritten for teaching. Always refer to official guides.