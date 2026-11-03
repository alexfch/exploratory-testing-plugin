# Charter Writing

A test charter is a short, focused mission statement that guides a time-boxed exploratory testing session.
Every test charter should be risk-driven: built around specific product risks, quality criteria or technical uncertainties rather than generic checklist items.
A test charter is expressed with a clear, formulaic structure: **Explore** [target / area / feature / risk] **with / using** [resources / tools / heuristics / personas] **to discover** [information / defects] **within** [a time box].
Examples:
- "Explore the checkout flow's coupon-code handling, with boundary and malformed inputs, to discover validation and error-handling problems"
- "Explore the CSV import's handling of malformed row data (missing fields, wrong types, encoding issues) to discover how gracefully it degrades and what it reports to the user"
- "Investigate what happens when import is interrupted mid-process (network drop, session timeout) to find partial-state or data-integrity risks"
- "Study concurrent imports by two admins to find race conditions in the underlying data"

## Key properties of a good charter:
- **Focused, not exhaustive** — it bounds the session's attention without dictating every action inside it. The tester still improvises within that scope.
- **Mission-driven, not procedural** — it says what to learn or what risk to investigate, not a scripted sequence of clicks.
- **Traceable to context and risk** — a good charter usually connects back to a specific area of risk, a coverage model (e.g., a piece of SFDIPOT), or a stakeholder concern, so you can explain later why that session mattered.

## Anti-patterns to avoid
- Charters that are really just disguised test cases ("verify field X accepts value Y") — that's checking, not a charter.
- Charters with no stated "to discover ___" — without a target question, there's no way to judge when the charter is exhausted.
- A charter per UI element instead of per risk/question — leads back to shallow, mechanical coverage.

## Rules

- **Don't front-load a complete charter list and execute it top-to-bottom.** Produce one charter; generate more as sessions complete and reveal what's actually worth investigating next.
- **Use SFDIPOT** (pco.md) as a check that charters aren't accidentally all about one dimension (e.g., all Function, no Data/Platform/Time).
- **Follow-on charters from findings**: when a session surfaces something interesting that wasn't fully chased down (defocused before exhausted, or a new risk appeared), the next charter should target that specifically, not just move to the next generic area.
- **Human-readable text formatting**: in the Test Charter, write content in the bullet point format – every new setup point, activity, heuristic, oracle, variation is a new point written from the new line.

## Template
*The template includes 4 secionts: Test Charter, Test Notes, Bugs, Problems. Take all of them to the charter document that you are going to create. Before pasting the template to the document, delete all the supporting notes (descriptions in Content column, Test Notes example, comments in Bugs and Problems section). However, use the supporting notes to understand what information to add into each section, table row or column.*

### Test Charter
| Headers | Content |
| ------- | ------- |
| Mission | *Put the charter mission here, in the format provided above* |
| Setup | *Describe the setup required for this charter: database, configurations, specific data or items added to the system ahead, etc. The Runner agent will have to do the setup before running the test session. When they matter for the charter, also name here the target(s) to test (type and which one, e.g. web at <url>, iOS app <app_id>, API <base_url>) and the account role to log in as (a role from the config, never a username or credential), or say that no login is needed* |
| Activities | *List all high-level scenarios/workflows/activities describing what to test as a part of this charter. List ideas only, do not get too detailed in particular steps. Let the Runner decide on the steps by itself.* | 
| Heuristics | *From the table with heiristics pick the ones that can help better execute the mission. Add the name of the heuristic and the description, so that the Runner better understand how to use it* 
| Oracles | *Out of all oracles you know, list the ones that most fit the charter mission. Add 1-2 sentence comments to each listed oracle explaining what exactly to pay attention to in the context of **this product** and **this test session**.* |
| Variations | *List variations in data, configs, flows, settings, system conditions that would uncover more issues as a part of this charter.* |

### Test Notes
| Time  | Action(s) | Observation | Oracle | Quality Criterion | Next step: Focus or Defocus |
| ----- | --------- | ----------- | ------ | ----------------- | --------- |
| *Examples:* | | | | |
| 09:00 | Log in -> Click 'Add New Product' -> Leave all fields empty -> Click 'Save' | Instead of getting error messages about empty fields the app navigated to the next screen as if all required data was provided | User expectations | Correctness | FOCUS |

### Bugs
*When creating a new charter document add the `Bugs` section title, but leave the section empty. The Runner agent will fill it in.*

### Problems
*When creating a new charter document add the `Problems` section title, but leave the section empty. The Runner agent will fill it in.*
