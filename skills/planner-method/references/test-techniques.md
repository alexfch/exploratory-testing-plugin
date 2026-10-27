# General Test Techniques

Nine families of general-purpose techniques for designing tests. Use them to generate test ideas and to vary *how* you're testing, not just *what* you're testing (pair with the current product Product Coverage Outline (PCO)).

Each technique below has: **what it is**, **how to apply it**, and an **execution note** — an honest statement of what's needed for you to actually run it (not just describe it), since idea-generation and execution are different capabilities for you and shouldn't be conflated in a report.

Ignore techniques with the #IGNORE tag. Do not collect information for them, do not generate test ideas based on them. Do not use them.

---

## Function Testing — test what it can do
**Apply**: identify the product's functions/subfunctions → decide how you'd know each one works → test one at a time → confirm it does what it should and doesn't do what it shouldn't.
**Execution note**: strong fit for you either way. Idea generation needs no tool. Actual execution needs a connected tool (browser/API/terminal) to invoke functions and observe real results — without one, say explicitly that you're reasoning from the spec, not from observed behavior.

## Claims Testing — challenge every claim
**Apply**: pull claims from any reference material (specs, help text, SLAs, EULAs, marketing) → clarify vague claims → test the product against each → if testing from a spec, expect spec and product to need reconciling, not just the product to be "wrong."
**Execution note**: strong fit. Parsing and comparing claims to behavior is close to a core strength. Feed it the actual claim source — don't invent claims from memory of "similar products."

## Domain Testing — partition the data
**Apply**: find all data the product processes (inputs and outputs) → choose values worth testing (boundaries, typical, invalid, best representatives) → consider meaningful combinations → pick inputs that force the full range of outputs.
**Execution note**: strong fit for generating systematic partitions — this is close to an algorithmic reasoning task. Execution (feeding the values in) needs a tool; without one, present the partition as a proposed test matrix rather than as results.

## User Testing — involve the users
**Apply**: identify user categories/roles → work out what each does, how, and what they value → get real user data/logs, or work with what you can obtain given your mode.
**Execution note**: your weakest fit, and you have no path to literally "bring in real users" — that option in the source material assumes a human tester, not you. What you can do depends on involvement mode: in `human-in-the-loop`, ask the user running the skill for real user data, logs, or personas rather than guessing. In `agent-only`, simulate a user based on whatever product/domain information you have (provided materials or search) — but always label this explicitly as your own assumption/understanding of the user in the session notes and final report, never as observed or verified user behavior. A simulated persona is a starting hypothesis to test against, not a substitute for real user truth.

## [#IGNORE] Stress Testing — overwhelm the product
**Apply**: find subsystems vulnerable to overload → identify the data/resources involved → select or generate challenging conditions (large/complex data, high load, long runs, many cases, low memory).
**Execution note**: partial fit. You can generate strong ideas about what would stress a system, and can script small-scale stress (loops, large payloads, repeated calls) if a terminal/API tool is available. Real infrastructure-scale load (thousands of concurrent users, distributed load) is beyond what you can generate — flag that as needing a dedicated load-testing tool rather than attempting to simulate it narratively.

## Risk Testing — imagine a problem, then look for it
**Apply**: brainstorm what could realistically go wrong → prioritize which matters most → work out how you'd detect it → design tests specifically to reveal it → draw on experts, docs, past bugs, or risk heuristics where available.
**Execution note**: strong fit, and mostly tool-independent — Use past-bug history and domain knowledge (searched or provided) to sharpen this rather than guessing generically.

## [#IGNORE] Flow Testing — do one thing after another
**Apply**: chain multiple activities end-to-end (e.g. a tour through a state model) → don't reset state between actions → vary timing/sequencing → try parallel threads.
**Execution note**: partial fit. Sequential flows are a strong fit with a connected tool. Genuine concurrency (parallel threads, precise timing/races) is a real limitation — you act close to one step at a time, so true concurrent execution depends on whether the tool itself can issue simultaneous actions. Say explicitly when a "concurrency test" is actually sequential-with-narration rather than real parallelism.

## [#IGNORE] Tool-Supported Testing — use tools to be more powerful
**Apply**: find or build tools that perform/check many things → consider tools for coverage, oracles, change detection, or test-data generation.
**Execution note**: unusual fit — you can be the tool-builder (e.g. write a script in the sandbox to automate a check or generate data), not just a tool user. Be explicit in reporting about which parts of a session were automated by something you built versus manually reasoned, so the distinction doesn't get lost.

## Scenario Testing — test to a compelling story
**Apply**: think about everything happening around the product → design tests with meaningful, complex interactions → aim for a believable story of someone who matters doing something that matters.
**Execution note**: partial fit. You can construct plausible, complex narrative scenarios well. The gap: "compelling and meaningful" is defined by real stakeholder priorities you likely don't know — ask for domain/user context before assuming a scenario is the one that actually matters, rather than presenting a plausible-sounding guess as if it were validated.

---

## How to use this file

- **Choose the technique(s) that fit the target, don't default to Function Testing out of habit.** Techniques and targets aren't independent — a target (a product factor, a risk, a claim) calls for whatever technique(s) actually reveal problems in it. E.g. a data-heavy target calls for Domain Testing; a documented behavior calls for Claims Testing; a risk you've identified calls for Risk Testing. When generating charters or executing sessions, pick technique(s) by asking "what would actually surface a problem here," not by reaching for whichever technique is most familiar.
- **State idea-vs-execution honestly.** For every technique used, be clear whether you generated ideas only (no tool) or actually executed them (tool-observed results) — never blur the two in session notes or the final report.
- **Weakest-fit techniques need explicit input, not silent guessing.** User Testing and Scenario Testing both depend on real stakeholder/user knowledge you don't have by default — ask for it (per the mode rules in 1.2) rather than substituting a generic assumption without flagging it.
