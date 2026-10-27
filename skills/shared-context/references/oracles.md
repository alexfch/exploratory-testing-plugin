# Oracles — FEW HICCUPPS

An oracle is a principle for *recognizing* a problem — it answers "how would I know this is a bug?" Always name which oracle a finding violates; "this seems wrong" is weaker and harder for the user to act on than "this violates the Claims oracle: the docs say X, behavior shows Y."

## The categories

- **F – Familiarity**: Does the system have problems typical for the current industry, or a type of application, or problems that already exit or existed before?
- **E – Explainability**: Is there an easy way to explain the feature or the workflow? Something that is hard to explain, most probably is hard to implement, so it has a high risk of functional issues.
- **W – World**: Does the current behaviour conflict with how things work in the real world (dates, money, physics, names, addresses)?
- **H — History**: Does current behavior conflict with the product's own past behavior (a regression)?
- **I — Image**: Does it conflict with how the company/product presents itself (professionalism, brand, tone)?
- **C — Comparable Products**: Does it conflict with how similar products handle the same situation?
- **C — Claims**: Does it conflict with documentation, specs, help text, or marketing claims?
- **U — User expectations**: Does it conflict with what a reasonable user of this product would expect?
- **P — Product**: Does it conflict with other parts of the same product (internal consistency)?
- **P — Purpose**: Does it fail to serve the product's actual purpose?
- **S — Statutes**: Does it conflict with laws, regulations, or required standards?


## What you can and can't independently supply

Be explicit with the user about which of these you're drawing on real evidence for vs. approximating:

| Oracle | Your realistic access |
|---|---|
| Familiarity | As an expert in software testing, use your own built-in knowledge of typical problems. If the current buglist is provided, read it, figure out the patterns. | 
| Explainability | Can assess from what's shown to you (copy, UI, docs) — reasonable to judge directly. |
| World | Reason from your own knowledge related to what you test. |
| History | What's in this conversation/session/run. You don't have persistent memory of the product's past. Ask for it if relevant. |
| Image | Can assess from what's shown to you (copy, UI, docs) — reasonable to judge directly. |
| Comparable Products | Web search for how competitors/similar products behave; can't directly operate a competitor's product unless a tool lets you. Treat write-ups about a competitor as weaker evidence than direct interaction. |
| Claims | Strong if given docs/spec/marketing copy — compare directly. |
| User expectations | Use your bulit-in knowledge of typical expectations. If needed, you can search for stated expectations (reviews, forums, support threads) and apply general, well-established UX/domain conventions — but this is *not* equivalent to knowing this product's actual users. Say so if you're using the generic fallback. |
| Product (internal consistency) | Strong if you can observe multiple parts of the product (via a connected tool or provided material). |
| Purpose | Reason from stated product purpose/goals if given. |
| Statutes | General knowledge/search on relevant regulations (e.g., accessibility, privacy) — flag if this needs actual legal review, since you're not a lawyer. |

## How to apply during test execution

1. Apply to everything you observe, not only what looks wrong.
2. Treat the eleven FEW HICCUPPS oracles as lenses for *finding* problems, not labels for problems you have already noticed. Many important bugs look perfectly normal at first glance; they only show up when you compare what you see against a specific reference. If you wait for something to "look off" before applying the oracles, you will miss them.
3. Before testing, gather the references the oracles need (specs, docs, release notes, previous version, comparable products, relevant standards). If a reference is unavailable, note which oracles you can't fully apply and why. Never silently skip one.
4. For every step, screen, message, text, and behaviour you observe, run a quick sweep through all eleven, asking how it holds up from each oracle perspective.
5. Keep the sweep quick when everything holds up. When one or more oracles flag an inconsistency, even a partial one, stop and investigate deeper: reproduce, vary the conditions, and look for related problems. Then decide whether it's a bug, a question for the team, or expected
behaviour, and record your reasoning, naming every oracle involved.
6. State the oracle explicitly in the finding.
