# Product Coverage Outline

Use this during context collection and when checking charter coverage to make sure you're not only thinking about the obvious, visible parts of the product. Deliberately work through each dimension below.

Product Coverage Outline (PCO) is based on the SFDIPOT heuristic. Use this template to describe the product aspects in a table format. For every meaningful piece of information, create a new table row so the PCO can later be used for a test coverage report.

## PCO Template
Last reviewed: YYYY-MM-DD

|Product aspects|Content|
|-----------|-----------|
| Structure (what the product is physically built of) | |
| - Code | (Provide the executables, modules, and routines that make it up) |
| - Hardware | (Provide any hardware that's an integral part of the product itself) |
| - Services | (Provide independently running servers/processes that are part of the product) |
| - Non-executable files | (Mention text files, sample data, help files, and similar) |
| - Collateral | (Mention anything outside the software itself — paper docs, web pages, packaging, license agreements) |
| Function (everything the product does) |   |
| - Business rules | (Provide constraints, conditional behavior, boundaries that shape behavior) |
| - Multi-user/social | (Mention anything enabling interaction between people or concurrent access) |
| - Calculation | (List arithmetic operations, embedded or standalone) |
| - Security-related | (List user rights, data protection, encryption, front-end vs. back-end protections) |
| - Transformations | (List anything that modifies or converts something) |
| - State transitions | (List anything that changes view, configuration, or context) |
| - Multimedia | (Provide sounds, images, video, graphical display) |
| - Error handling | (Mention detection and recovery functions, including error messages) |
| - Interactions | (Describe how functions within the product affect each other) |
| - Testability hooks | (List diagnostics, logs, asserts, test menus built into the product) |
| Data (everything the product processes or produces) |   |
| - Input/output | (List data going in and data coming out) |
| - Preset | (List data shipped with the product — defaults, prefab databases) |
| - Persistent | (List data expected to survive across operations (settings, modes, view state)) |
| - Interdependent | (List data that influences or is influenced by other data) |
| - Sequences/combinations | (List ordering and permutations that matter) |
| - Cardinality | (List how many of something (zero, one, many, max) and uniqueness constraints) |
| - Big/little | (Provide size and aggregation variations) |
| - Invalid/noise | (Describe how the system should handle corrupted, out-of-bounds, or malformed data) |
| - Lifecycle | (Describe how a piece of data changes from creation through deletion) |
| Interfaces (every way the product is accessed or expressed) |   |
| - User interfaces | (List displays, buttons, fields — physical or virtual) |
| - System interfaces | (List logs, other programs, disk, network — anything non-human) |
| - API/SDK | (List programmatic interfaces for building on the product) |
| - Import/export | (List functions that package or interpret data for other products) |
| Platform (everything the product depends on, outside your own project) |   |
| - External hardware | (List required or optional hardware not shipped with the product) |
| - External software | (List OS, concurrently running apps, drivers, fonts) |
| - Embedded components | (List libraries built into the product but sourced elsewhere) |
| - Product footprint | (List memory, file handles, and other resources it consumes) |
| Operations (every real-world experience someone could have with the product) |   |
| - Users | (List the system’s different kinds of users and their attributes (end user, admin, API consumer)) |
| - Environment | (Describe the physical/situational context of use (noise, light, distraction)) |
| - Common use | (Describe typical, expected patterns of input) |
| - Uncommon use | (List periodic expected activity (backups, updates, scheduled maintenance)) |
| - Extreme use | (Describe intended but challenging usage patterns) |
| - Disfavored use | (Describe possible careless, mistaken, or malicious usage patterns) |
| Time (every relationship between the product and time) |   |
| - Time-related data | (List timeouts, time zones, holidays, warranty/term periods) |
| - Input/output timing | (List when things happen and the delays/intervals between them) |
| - Pacing | (List fast/slow input, bursts, hangs, bottlenecks, interruptions) |
| - Concurrency | (List multiple things happening at once — multi-user, threads, shared data, race conditions) |

## Rules
1. As the model makes mistakes while trying to build PCOs for different products, rules will be added here to help improve the final result.
