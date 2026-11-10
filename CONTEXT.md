# DBS Garden Fete POS

The point-of-sale application for a single stall at the annual DBS Garden Fete. It runs fully offline — no network connection is available or needed on event day.

## Language

**Event**:
The annual DBS Garden Fete — a single-day event held once per year. The app is set up for each year's event.
_Avoid_: Fete, fair

**Stall**:
The selling point this app serves. Each stall at the fete runs its own register; this app belongs to exactly one stall.
_Avoid_: Register, booth

**Item**:
A physical DBS boarding-school-themed object sold over the counter at a fixed price.
_Avoid_: Product, merchandise

**Item ID**:
The stable identifier an item carries from the organizer's Stock sheet (`ItemID` column). The app's canonical identity for an item — unique within the sheet, never assigned in-app, and written back unchanged on the Stock sheet report. Shown alongside the item name in the item list.
_Avoid_: SKU, code

**Sale**:
A single customer's purchase at the stall, made up of one or more items.
_Avoid_: Transaction, purchase

**Current sale**:
The sale being built on a device right now, before it is settled. Distinct from a recorded **Sale**: the cashier edits the current sale freely, and only a settled sale becomes a record.
_Avoid_: Open sale, live sale, basket

**Sale line**:
One row of a sale: an item, its quantity, and that row's total. A sale is made up of one or more sale lines; an item appears in at most one line per sale.
_Avoid_: Line item, line, row

**Cash**:
Notes and coins handed over the counter in payment.
_Avoid_: Money, change

**Octopus**:
A contactless stored-value card tapped on the stall's single shared Octopus machine. The app is not connected to the machine — it records the amount paid by Octopus. The combined Octopus from both devices is checked against this one machine's report at the end of the day.
_Avoid_: Card, contactless

**Voucher**:
A fixed-value token bought with cash before the event or on the day. The stall only ever receives vouchers as payment — it never sells them. Redeemed at the stall in payment for items. (Denomination and change policy: to be confirmed.)
_Avoid_: Coupon, ticket, token

**Receipt**:
The hand-written order sheet given to the customer at the point of sale. Written by the cashier by hand; the app never prints one.
_Avoid_: Order sheet, slip

**Catalog**:
The full list of items and their prices, loaded from the organizer's active Stock sheet CSV. During the event, the operator may select a different Stock sheet and edit an existing item's name, price, or starting quantity on the device. The app does not add or remove Item IDs, and local edits never change the source CSV.
_Avoid_: Menu, product list

**Stock sheet**:
The organizer's master CSV listing every item, with columns `ItemID, ItemName, Price, Inventory, Sales, Revenue`. The active sheet supplies the catalog and source cells; the operator may change it during the event. At the end of the day each device writes out a new report file with the same columns, filling Sales and Revenue from retained completed sales (the source file is left untouched), and the organizer combines the two devices' reports by hand.
_Avoid_: Stocks file, stock list

**Source cells**:
The four cells `ItemID, ItemName, Price, Inventory` associated with a Stock sheet row. They start as delivered by the organizer's file; the report preserves the ItemID cell exactly, while ItemName, Price, and Inventory reflect any in-app edits. The source CSV itself is never changed.
_Avoid_: Raw cells, original cells

**Device**:
One of the two Windows laptops the stall operates on event day. Each device is used by a single cashier at a time and has its own copy of the catalog. The devices have no network between them.
_Avoid_: Machine, register, terminal

**Device database**:
The on-disk per-device store of the device's durable records — setup, catalog, sales, and cash adjustments. It survives crashes and is wiped at the end of the day once the export is taken. One per device; never shared between them.
_Avoid_: Database, DB, local store

**Float**:
The starting change money in the till at the start of the event, excluded from the day's takings when reconciling cash.
_Avoid_: Change, float money

**Correction**:
A change made to a recorded sale so that it shows the right items and amount. Corrections count toward the day's totals.
_Avoid_: Edit, fix, adjustment

**Void**:
Removing a sale from the record entirely, as though it never happened. Voids do not count toward the day's totals, but stay visible in a separate section of the sales export for audit.
_Avoid_: Cancel, delete, refund

**Starting quantity**:
The baseline count used to estimate how many units of an item remain. It is initially taken from the Stock sheet's `Inventory` column, but the operator may reset it during the event; the estimate subtracts completed, non-void units sold for that item.
_Avoid_: Stock level, inventory

**Sold out**:
An item the stall has stopped selling, marked manually by the cashier during the event. The app never infers sold-out from the remaining quantity; only the cashier's explicit marking sets it.
_Avoid_: Out of stock, unavailable

**Items sold**:
The per-item count of units sold on a device, in final state and excluding voids. Shown on the end-of-day screen and written into the Stock sheet report's Sales column.
_Avoid_: Sold count, units moved

**Expected cash**:
The amount the till should hold at a given moment: the float plus all cash sales on that device, plus any cash added mid-day, minus any cash removed mid-day. Compared against the physically counted cash.
_Avoid_: Cash count, till total

**Cash adjustment**:
Cash added to or removed from the till during the event (e.g. topping up change). Recorded so expected cash stays accurate.
_Avoid_: Cash in/out, float top-up

**Sales export**:
CSV file(s) produced from each device containing that device's sales, given to the organizer to combine both devices' records. The app never merges devices itself.
_Avoid_: Report, sync, sales file

**Device name**:
A short label given to a device at setup (e.g. "Till A"). Stamped on every sale that device records and carried into its sales export, so the two devices' exports can be told apart. A Device name must be safe to embed in a file name — the register rejects names that would break the export — because it names the export's Stock sheet report file.
_Avoid_: Till label, register id

**End-of-day**:
The per-device reconciliation figures produced at the close of the event: expected cash, Octopus and voucher totals, per-item sold counts, the voids list, and the cash adjustments. Shown on the end-of-day screen and written to the sales export. Computed per device, never merged in-app.
_Avoid_: End of event, closing figures

**Split settlement**:
A sale paid by more than one payment method. Any non-empty combination of Cash, Octopus, and Voucher may be used; each method covers a positive portion, and the portions add up to the sale total. Cash tendered is recorded separately from the Cash portion so change is computed only against Cash.
_Avoid_: Split payment, part payment

**Sequence number**:
The running number assigned to a sale as it is made, shown on the sale record and used to cross-check against the Octopus machine's own report.
_Avoid_: Sale ID, order number, receipt number
