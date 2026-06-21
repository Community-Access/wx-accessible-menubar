# Contributing

**Contributions are welcome — anyone can contribute, and we want them.** This is
a Community Access open-source project, created by Taylor Arndt.

## Ways to help
- **Report bugs** — open an issue with what you expected, what happened, your OS,
  wxPython version, whether you use a webview, and your screen reader (if relevant).
- **Test with screen readers** — NVDA, JAWS, Narrator (Windows), VoiceOver
  (macOS), Orca (Linux). Real-world a11y reports are the most valuable thing here.
- **Send pull requests** — features, fixes, docs, examples.

## Ground rules
- **Accessibility first.** The whole point is that the native menu bar is fully
  keyboard-operable and reads correctly in NVDA/JAWS. Changes shouldn't regress
  that; note how you tested (which screen reader / OS, native or webview app).
- **Native menus, never custom-drawn.** We drive the real `wx.MenuBar`; we do not
  build our own menu widget. A hand-rolled menu reads worse than the OS one.
- Keep it **dependency-light** — wxPython only.
- Match the existing style; format with `ruff format` (line length 100).

## Dev setup
```bash
pip install -e .                  # installs wxPython
python examples/native_demo.py    # native-control app (try with a screen reader)
python examples/webview_demo.py   # webview app (Windows: tap Alt, then Right)
```

## Pull requests
- Describe the change and how you verified it (which screen reader / OS, native
  or webview).
- One focused change per PR is easiest to review.

Thanks for helping make keyboard-accessible menu bars in wxPython the default,
not the exception.
