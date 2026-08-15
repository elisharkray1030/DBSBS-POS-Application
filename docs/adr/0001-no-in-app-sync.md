# Two devices, no in-app sync — reconciled by hand via CSV export

The stall runs two Windows laptops on event day with no network between them. We deliberately do **not** sync or merge their records in-app: each device keeps its own database, and at the end of the day each exports its sales as CSV for the organizer to combine by hand.

The instinct is to sync the two laptops. We rejected that because adding sync introduces a second fragile distributed-system component for a one-day annual event — a failure mode that's hard to debug mid-fete. A spreadsheet pivot over two CSV files is trivial, robust, and keeps each device's logic trustable to itself. The cost is manual end-of-day reconciliation, which the organizer already has to do anyway (counting cash, matching the Octopus machine, counting leftover stock).

## Considered options

- **Ad-hoc Wi-Fi / Bluetooth sync between the two laptops** — rejected: unreliable on the day, and sync conflict resolution is disproportionate effort.
- **In-app combined view** — import the other device's CSV on one laptop to compute combined totals/remaining stock inside the app. Rejected: the organizer does this arithmetic deliberately; keeping the app single-device avoids any cross-device coupling.

## Consequences

- Each device issues its own independent sequence numbers, so both laptops will have a "sale #1". A device name set at setup stamps every exported sale to keep them distinguishable.
- The end-of-day stock check (`remaining = starting − sold on A − sold on B`) and the combined-Octopus-vs-machine check are performed by the organizer, not the app.