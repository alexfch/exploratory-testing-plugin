# Bugs Writing

When you find a problem, add it to the current test session document ("TC-<Round>.md") under `Bugs` section.

## Table template
When you write the first problem to the section, you'll find and empty `Bugs` section without the bug table in it. Add the headers to the document before adding the current bug notes.

| Bug ID | Severity | Summary | Steps to reproduce | Expected behaviour | Actual behaviour | Violated Oracle |
| ------ | -------- | ------- | ------------------ | ------------------ | ---------------- | --------------- |

## Rules

- **Bug ID**: format `TC-<Round>-<YY>` where `Round` is number of the current test charter, `YY` sequence number of the bug found during this session.
- **Severity**: Blocker | Critical | Major | Minor | Trivial.
- **Summary**: Follow the format: "[User role].[Page/Screen name].[1 short sentence what happens but shouldn't OR what doesn't happen but should][under what conditions]". Example: "Admin. Add new user. Add button is not active even though all required fields are filled in."
- **Steps to reproduce**: Short specific steps to execute to get to the point with the problem. Example: "Login as Admin -> Fill in all required fields (FN-John, LN-Doe, Role-SalesRep, Department-Sales, Manager-Adam) -> Click Add button" (every step from the new line).
- **Expected behaviour**: Mention specific requirement (if exists) that describes expected behaviour. If the expected behavour is based on your assumtion or reasoning say it explicitly.
- **Actual behaviour**: Short 1-2 sentences that describes what exactly looks/behaves wrong
- **Violated Oracle**: What oracle did you use to understand that it's a problem?
