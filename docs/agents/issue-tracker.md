# Issue tracker: GitHub Issues

Tickets and issues for this repo live as GitHub issues in the
`elisharkray1030/DBSBS-POS-Application` repository (use the `gh` CLI).
Feature specs are published to the issue tracker as GitHub issues too —
there is no local `.scratch/` directory anymore (fully migrated to the
remote). The canonical spec lives at issue #32; see the tracker for the
feature specs listed below.

## Feature specs (on the tracker)

| Feature | Spec issue | Feature label |
| ------- | ---------- | ------------- |
| DBS Garden Fete POS (canonical) | #32 | `dbsbs-pos` |
| Stock sheet round-trip | #33 | `stock-sheet` |
| Stock sheet round-trip deepening (U1) | #34 | `stock-sheet` |
| CustomTkinter UI migration | #35 | `customtkinter-ui` |
| Table header contrast fix | #36 | `table-header-contrast-fix` |
| End-of-event reporting deepening (U2) | #29 | `end-of-event-reporting` |

## Conventions

- One feature per label: `dbsbs-pos`, `stock-sheet`, `customtkinter-ui`, ... —
  create a label when a feature starts and apply it to every ticket of that
  feature.
- A feature's spec is a GitHub issue (see the table above); the tickets
  derived from it are GitHub issues titled `[<feature>] NN — <slug>`.
- Ticket state is the GitHub issue's open/closed state; triage roles are
  labels (see `triage-labels.md`).
- Blocking edges are references to the blocking issue numbers in the body
  (`Blocked by: #12, #13`). A ticket is unblocked when every referenced issue
  is closed. Create blockers before their dependents so the references exist.

## When a skill says "publish to the issue tracker"

Create a GitHub issue via the `gh` CLI (`gh issue create ...`), apply the
feature label and the relevant triage label, and link the spec in the body.
For a feature spec, publish the spec itself as a GitHub issue (as the
canonical home) and the tickets derived from it as further GitHub issues.

## When a skill says "fetch the relevant ticket"

Read the issue at the given number: `gh issue view <number> --repo
elisharkray1030/DBSBS-POS-Application`.