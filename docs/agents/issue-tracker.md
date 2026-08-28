# Issue tracker: GitHub Issues

Tickets and issues for this repo live as GitHub issues in the
`elisharkray1030/DBSBS-POS-Application` repository (use the `gh` CLI).
Feature specs stay as markdown files under `.scratch/<feature-slug>/spec.md`;
the tickets that break them out live on GitHub.

## Conventions

- One feature per label: `dbsbs-pos`, `stock-sheet`, `customtkinter-ui`, ... —
  create a label when a feature starts and apply it to every ticket of that
  feature.
- A feature's spec stays local at `.scratch/<feature-slug>/spec.md`; the
  tickets derived from it are GitHub issues titled `[<feature>] NN — <slug>`.
- Ticket state is the GitHub issue's open/closed state; triage roles are
  labels (see `triage-labels.md`).
- Blocking edges are references to the blocking issue numbers in the body
  (`Blocked by: #12, #13`). A ticket is unblocked when every referenced issue
  is closed. Create blockers before their dependents so the references exist.

## When a skill says "publish to the issue tracker"

Create a GitHub issue via the `gh` CLI (`gh issue create ...`), apply the
feature label and the relevant triage label, and link the spec in the body.
For a feature spec, keep the spec itself at
`.scratch/<feature-slug>/spec.md` and publish tickets as GitHub issues.

## When a skill says "fetch the relevant ticket"

Read the issue at the given number: `gh issue view <number> --repo
elisharkray1030/DBSBS-POS-Application`.