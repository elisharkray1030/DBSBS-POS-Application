# Manual UI acceptance checklist

The tkinter UI is intentionally not covered by automated UI tests. Run these
checks with a disposable device database and copies of valid Stock sheet CSVs.

- [ ] With a configured device database, launch `start.pyw`; it opens directly
  on Sale, without showing Setup first.
- [ ] Sale shows `Stock sheet: <filename>` and **Change stock sheet…** without
  crowding or truncating the device identity. End-of-day shows the same active
  filename.
- [ ] Select an item, add an item to the current sale, then choose **Edit item…**.
  The app explains the current sale must be settled or emptied and does not open
  the edit dialog. Empty the current sale and verify the dialog allows editing
  only the name, price, and starting quantity, not the Item ID.
- [ ] Edit and save an item's name, price, and starting quantity. Verify future
  sales use the edited name/price, recorded sale snapshots and the selected CSV
  remain unchanged, and remaining quantity uses the edited baseline minus
  completed non-void sales (clamped at zero). Verify a name/price-only edit
  keeps an existing sold-out mark. A changed starting quantity with positive
  remaining clears that mark; when remaining is zero, it stays set.
- [ ] Export, edit an item, and attempt to wipe. Wipe is blocked until a fresh
  export is taken; verify the Stock sheet report uses the edited fields and
  preserves the original Item ID.
- [ ] Add an item to the current sale and choose **Change stock sheet…**. The
  app explains that the current sale must be settled or emptied, and does not
  open a file picker. Remove/settle the item and verify the action is available.
- [ ] Choose another valid CSV. The confirmation explains future prices,
  end-of-day source rows, retained recorded sales, and possible mixed prices.
  Cancel and confirm the active sheet and item list are unchanged.
- [ ] Confirm the change. The item list refreshes, the active filename updates,
  and a message reports the number of loaded items. New sales use the selected
  sheet's prices.
- [ ] Record a sale before switching and another after. Confirm the earlier
  sale remains at its original price and both screens show the selected active
  filename. Export and verify the Stock sheet rows/order come from the selected
  CSV while totals include both sales.
- [ ] Try an invalid CSV and verify an error is shown/logged without changing
  the active filename, items, current sale, or recorded sales.
- [ ] Export, switch sheets, and attempt to wipe. Wipe is blocked until a new
  export is taken; after exporting from the new sheet, the normal wipe flow
  succeeds.
- [ ] Relaunch and verify the saved catalog and filename remain active without
  rereading the source CSV. For a legacy database with catalog rows but no
  filename setting, verify the screens say **Source not recorded**.
