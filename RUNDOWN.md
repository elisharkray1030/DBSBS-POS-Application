# Weekend POS rundown

This guide covers using the POS for Saturday-night presale prices followed by
Sunday marked prices. The POS keeps sales on each device; it does not sync tills
or automatically reset the day at end of day.

## Before the event

- Prepare valid Stock sheet CSVs for both price periods. Use the expected Stock
  sheet columns and make sure each physical item has the same, unique `ItemID`
  in both sheets.
- For items whose stock carries over, use the same **starting quantity**
  and `ItemID` in both sheets. If multiple tills sell from shared stock, use
  that same baseline on each till; each till counts only its own sales.
- Set up each till with its device name, starting cash float, and the Saturday
  presale Stock sheet. Keep each device's database for the whole weekend.

The app does not change the source CSV. It saves the active catalog on the
device, and switching sheets changes the catalog for future sales without
changing completed sales.

## Saturday night — presale

1. On each till, confirm the Sale screen shows the intended presale sheet
   filename before taking sales.
2. Ring sales as usual. Each completed sale keeps the item name and price that
   applied when it was settled. Voids do not count toward sold units or revenue.
3. At Saturday end of day, review the figures and export to a separate folder
   for that day and till (for example, `Saturday/Till A`). This is a snapshot
   through Saturday; it does not close or reset the device.
4. **Do not wipe the device after Saturday.** Wiping deletes its sales, catalog,
   adjustments, and settings needed for Sunday.

## Change to Sunday marked prices

1. On each till, finish or remove every item in the current sale. The POS will
   not change sheets while the current sale has items.
2. On the Sale screen choose **Change stock sheet…**, select the Sunday marked-
   price CSV, and read the confirmation before accepting.
3. Confirm the active filename and prices on the Sale screen after the change.
   New sales use Sunday prices; Saturday sales remain at their original prices.
4. If the CSV is invalid, the change fails and the previous sheet remains
   active. Check the filename and catalog before ringing the next sale.

When an incoming sheet has the same Item ID as a previously sold item, the POS
subtracts this device's completed, non-void sales for that Item ID from the
numeric starting quantity in the `Inventory` column. The Sunday Stock sheet's
Sales and Revenue for that Item ID combine Saturday and Sunday totals; Revenue
reflects the prices actually charged on both days. Sales are not transferred to
a different Item ID. Sales for an Item ID missing from the active sheet remain
in history and the End-of-day summary, but will not have a row in the active
Stock sheet report. For matching Item IDs, an existing manual Sold out mark
remains when the starting quantity is unchanged. It clears if the quantity
changes and the recalculated remaining quantity is positive; new Item IDs start
unmarked. A sheet change also means you must export again before the device can
be wiped.

## Sunday — marked prices and end of day

1. Confirm each till still shows the Sunday marked-price sheet and continue
   recording sales on the same device database.
2. At Sunday end of day, review and export each till again, this time into a
   separate folder for that day and till (for example, `Sunday/Till A`). The
   Sunday screen and exports are **cumulative**: they include Saturday and
   Sunday activity recorded on that device. End of day is a review and export,
   not a daily reset.
3. Check and save all required exports from all tills before wiping any device.
   The wipe safeguard requires an export after the latest sales, adjustments,
   or catalog change. Wiping is permanent.

## End-of-day figures and export files

The End-of-day screen is for one device. Expected cash is the starting float
plus that device's completed cash sales and cash adjustments. Octopus and
voucher totals are shown separately. The sold-item summary uses completed,
non-void sales; voids are listed separately. On Sunday these figures include
both days' activity on that device.

Each export creates:

- `sales.csv` — sale totals, tenders, status, and timestamps.
- `items.csv` — rows for each sale line, with item name, quantity, and price,
  associated with the sale by device and sequence number. It does **not** include
  `ItemID`.
- `stocks-<device>.csv` — the active Stock sheet's rows, with calculated Sales
  and Revenue for this device's retained history. The `Inventory` column is the
  starting-quantity baseline, not a remaining-stock column.

Keep separate folders for each **day and till** (for example, `Saturday/Till A`,
`Saturday/Till B`, `Sunday/Till A`, `Sunday/Till B`). The filenames `sales.csv`
and `items.csv` are the same on every till and a later export can replace files
with the same names in the destination folder.

The Sunday export already includes Saturday for that till. Do not add the
Saturday snapshot to the Sunday cumulative totals. To see sales by sale line
for each day, use the sale timestamps in `sales.csv`, then match device and sale
sequence to `items.csv`. These files retain each sale line's item name, quantity,
and price, but not its ItemID.

## Starting quantity: what the app can and cannot estimate

For each item on one device, the displayed remaining estimate is:

> max(0, active Stock sheet's starting quantity − this device's completed,
> non-void units sold for the same ItemID)

Thus, when both sheets use the same starting quantity from the `Inventory`
column, Saturday's sales remain deducted after the Sunday switch, and Sunday's
estimate includes sales from both days. The Stock sheet export reports the
`Inventory` baseline and cumulative `Sales`; derive remaining as `Inventory`
minus `Sales`, clamped at zero. A blank `Inventory` field means the app cannot estimate
remaining stock for that item.

This is **per device**, not a shared live count. If Till A and Till B sell from
the same physical stock, each till's on-screen estimate excludes the other
till's sales. For a combined estimate, if tills share the same starting
quantity, use the latest cumulative Sunday report from each till and calculate,
per `ItemID`:

> max(0, starting quantity − (Till A cumulative Sales + Till B cumulative Sales))

Count each till's Sunday cumulative report once; do not add its Saturday
snapshot as well. If tills have separate allocated stock, reconcile against
those allocations instead.

Physical restocks, losses, or other stock movements are not automatically
tracked. A physical count may therefore differ from the POS estimate. Do not
enter a Saturday closing count as Sunday's starting quantity: the app will
also deduct recorded Saturday sales. Ask the event organizer how to handle any
stock changes outside recorded sales.
