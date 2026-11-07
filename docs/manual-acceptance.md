# Manual UI acceptance checklist

The tkinter UI is intentionally not covered by automated UI tests. Run these
checks with a disposable device database and copies of valid Stock sheet CSVs.

- [ ] With a configured device database, launch `start.pyw`; it opens directly
  on Sale, without showing Setup first.
- [ ] Resume an interrupted setup (catalog saved, no device name or float) and
  choose an invalid CSV. The error is shown, the previous filename returns, and
  **Start the day** still accepts the saved catalog.
- [ ] Sale shows `Stock sheet: <filename>` and **Change stock sheet…** without
  crowding or truncating the device identity. End-of-day shows the same active
  filename.
- [ ] On Sale, focus the item list and press `/`, then keypad `/`; each shortcut
  focuses the quick-entry Item ID field. Verify slash remains ordinary text in
  editable fields, including the quick-entry fields and the inline sale Qty
  editor, and does not activate quick entry in a dialog or on another screen.
- [ ] Press Enter with Item ID empty. Verify inline feedback appears and focus
  stays on Item ID. Enter a valid ID and press Enter; verify Qty is `1` and
  selected. Change Qty and add with Enter; verify the sale updates, fields reset
  to blank Item ID and Qty `1`, and focus returns to Item ID for repeated adds.
- [ ] Clear Qty and verify it defaults to `1`. Try non-integer, zero, and
  negative Qty; verify each error is inline, the entered values remain, and
  focus stays on Qty. Correct and retry. Try an unknown ID and a sold-out ID;
  verify inline feedback, retained values, and focus on Item ID. Correct the ID
  and verify the retained Qty can be used to retry.
- [ ] Press Escape from either quick-entry field. Verify Item ID clears, Qty
  returns to `1`, quick entry exits, and focus returns to the item list.
- [ ] With an item selected, use mouse **Add to sale** with a non-default Qty.
  Verify Qty resets to `1` after success and remains unchanged after a failed
  add.
- [ ] At the 800×600 minimum window size, verify the quick-entry strip remains
  visible beside **Items**, the item table has useful visible rows, and no
  horizontal scrollbar is introduced.
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
- [ ] Mark an item sold out, then switch to a sheet with the same Item ID and
  starting quantity; verify the mark remains. Switch to a sheet with a changed
  starting quantity and positive remaining; verify the mark clears. If remaining
  is zero, verify the mark stays set.
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
