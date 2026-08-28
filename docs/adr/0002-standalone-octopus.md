# Standalone Octopus — the app never touches the machine

Octopus payments are taken on a single shared external Octopus machine that is **not** connected to the app. The cashier taps the card on the machine, then records the amount in the app as part of the sale. At the end of the day, the combined Octopus from both devices is manually checked against that one machine's own report.

The instinct is to integrate (drive the card reader from the app via an SDK). We stayed standalone because the machine is shared hardware handed to another stall at the end of the event, integration would lock the app to a specific machine's SDK/protocol, and the machine already keeps its own authoritative record of every tap. The app therefore only needs an audit trail — per-sale Octopus amounts plus the sale's sequence number — that a human can reconcile against the machine's report.

## Considered options

- **Integrate via the Octopus SDK / a reader under app control** — rejected: hardware lock-in, the machine moves between hands, and the effort isn't justified for a one-day annual event.

## Consequences

- Octopus amounts in the app are cashier-entered and therefore error-prone; the sequence number per sale is the cross-check against the machine's report.
- Octopus must always settle the full sale total on its own — it can't be split against cash or vouchers, since the app has no way to drive a partial tap.