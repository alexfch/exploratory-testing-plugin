# Mind-Map Coverage Format

A visual/structural summary of coverage, complementary to the SBTM notes (which are chronological/per-session; the mind map is organized by product area).

## Structure (text/markdown tree — render as an actual diagram via the visualizer tool if the surface supports inline visuals and the user would benefit from seeing it)

```
[Product/Feature under test]
├── [Area 1 — e.g. an SFDPOT dimension or major sub-feature]
│   ├── Covered: [what was tested] — [pass/issue-found]
│   ├── Not covered: [what wasn't reached] — [why]
│   └── Findings: [bug refs, linking back to SBTM notes]
├── [Area 2]
│   └── ...
└── [Area N]
```

## Guidance

- Organize top-level branches by product area or SFDPOT dimension — whichever maps more naturally onto how this specific product was actually explored.
- Mark each leaf clearly as covered/not-covered/issue-found — the point is to make gaps visually obvious at a glance, not just to list what was done.
- Link findings back to the SBTM session notes rather than duplicating full finding detail here — this is a map, not the report body.
- If rendering inline (not just as a text tree), use the diagram capability available in the current environment rather than building an image from scratch by hand.
