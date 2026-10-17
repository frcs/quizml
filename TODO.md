# Backlog

This is an informal list of ideas, not a release plan. The active code review
findings and their status are tracked in [CODE_REVIEW.md](CODE_REVIEW.md).

## User experience

- Improve LaTeX installation guidance and make external tool requirements
  easier to diagnose.

## Rendering and errors

- Audit error handling and clarify diagnostics for compilation failures.
- Re-evaluate the MathML, SVG, and PNG math rendering backends.
- Consider whether LaTeX image conversion can avoid redundant tool invocations.

## Quiz authoring

- Consider a `shortname` field for a one-line question summary.
- Evaluate a `part` keyword for grouping questions.
- Review matching and ordering support across the LaTeX and HTML templates.
