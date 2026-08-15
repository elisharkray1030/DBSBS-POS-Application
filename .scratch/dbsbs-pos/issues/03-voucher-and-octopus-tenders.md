# 03 — Voucher & Octopus tenders + split settlement

**What to build:** The cashier can settle a sale by voucher or by Octopus in addition to cash, and can split a sale across cash and vouchers (e.g. $20 cash + $30 voucher). The app enforces that Octopus always settles the full sale amount on its own — partial Octopus or Octopus combined with another method is rejected. Voucher policy (denominations and change) is parked as TBC, so this ships with a placeholder voucher behavior (no change given) that the TBC resolution can refine.

**Blocked by:** 02 — Build & settle a cash sale

**Status:** ready-for-agent

- [ ] A sale can be settled by voucher, recorded as a voucher amount
- [ ] A sale can be settled by Octopus, recorded as an Octopus amount
- [ ] A sale can be split across cash and vouchers in any combination
- [ ] An Octopus tender that is not exactly the full sale total is rejected
- [ ] A settlement that combines Octopus with any other method is rejected
