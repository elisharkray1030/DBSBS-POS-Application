# Distribute a one-file Windows executable through GitHub Releases

The event laptops receive a single Windows x64 executable in a zip, built with
PyInstaller in one-file, windowed mode and published from a version tag by
GitHub Actions. The executable bundles Python, Tkinter, and the pinned
`customtkinter` dependency, so the organizer does not need to install Python or
connect to the internet on event day. The source-run workflow remains
available to developers.

The executable is unsigned. The README documents the first-run SmartScreen
warning rather than adding the cost and maintenance of code signing. The
organizer extracts it to a writable folder; the device database, failure log,
and end-of-day exports are stored beside the executable.

## Considered options

- **Keep distributing only the source folder** — rejected as the event-day
  installation path: each laptop would need Python and a successful online
  dependency bootstrap before it could run offline.
- **An installer or MSI** — rejected: the organizer needs only to extract the
  app into a writable folder, and an installer would add packaging and
  uninstall complexity without helping the two-laptop setup.
- **Code-sign the executable** — deferred: signing has an ongoing cost and is
  not needed for the two known laptops; the SmartScreen prompt is documented.

## Consequences

- A tagged GitHub Actions build gates release publication on tests, type
  checking, linting, and a startup smoke test of the packaged executable.
- The smoke test verifies that the executable remains running and creates
  `pos.db` beside itself; the event-laptop rehearsal remains a separate manual
  check of the actual downloaded artifact and its visual behavior.
- Users must extract the zip to a writable folder and keep the data files
  beside the executable.
- Releases target 64-bit Windows only. The unsigned executable may trigger
  SmartScreen on first launch.
- The Python source workflow remains the developer route; it is not the
  event-day installation path.
