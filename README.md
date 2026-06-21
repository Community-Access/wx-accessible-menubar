# wx-accessible-menubar

Keyboard-accessible native menu bars for wxPython. Plain Alt activates the bar,
Alt plus a mnemonic opens a menu, F10 works, Left and Right walk across the
top-level menus, and focus returns to your content afterward. It works in plain
native apps and, crucially, in apps where a focused `wx.html2.WebView`
(Edge WebView2) would otherwise eat every keystroke before the menu bar sees it.

It drives the real native menu bar. It does not draw its own menu, because a
native Win32 menu is the thing NVDA and JAWS already read perfectly.

## The problem

A native `wx.MenuBar` is the most screen-reader-friendly menu you can ship: the
OS handles Alt, mnemonics, arrow navigation, and announces everything to NVDA
and JAWS for free. The trouble is reaching it from the keyboard when something
swallows Alt first.

The worst offender is `wx.html2.WebView`. On Windows it is Edge WebView2, which
runs out of process and captures the keyboard at the OS level. wx never sees Alt
at all (wxWidgets issue #24786), so the menu bar simply never opens. Even a
frame-level `EVT_CHAR_HOOK` fires zero times, because the keys never reach wx.

## The idea

Catch the keys where they actually are, then hand them to the real menu bar.

- In a native-control app the frame still sees the keys, so a frame-level key
  hook catches Alt, Alt plus a mnemonic, and F10.
- In a webview app the one place that still sees the keys is the page itself, so
  a tiny key listener is injected into the webview and bridged back over the
  webview's own script-message channel.

Either way, on Windows the menu bar is opened by posting the exact message Alt
normally sends (`WM_SYSCOMMAND` with `SC_KEYMENU`). That puts the genuine menu
bar into its keyboard loop, so Left and Right move across the top-level menus and
Up, Down, and Enter work natively, read correctly by the screen reader. On other
platforms it falls back to native handling and a popup, so it is safe to attach
everywhere.

## Install

```bash
pip install wx-accessible-menubar
```

It depends only on wxPython.

## Usage

Build your menu bar as usual, with `&` mnemonics in the top-level labels, then
wrap it. For a plain native app:

```python
from wx_accessible_menubar import AccessibleMenuBar

bar = wx.MenuBar()
file_menu = wx.Menu()
file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
bar.Append(file_menu, "&File")
# ... more menus ...

AccessibleMenuBar(self, bar, focus_target=self.text_ctrl)
```

For an app whose content is a webview, pass the underlying
`wx.html2.WebView` so the page-side listener gets installed too. If you use
`wx-accessible-webview`, that control is `AccessibleWebView.view`:

```python
AccessibleMenuBar(
    self,
    bar,
    webview=self.web.view,        # the wx.html2.WebView
    focus_target=self.web.view,   # return focus here after a menu closes
)
```

That is it. Tap Alt and use the arrow keys.

## API

### `AccessibleMenuBar(frame, menubar, *, focus_target=None, webview=None, restore_focus=None, bridge_name=..., bare_alt_ms=200)`

- `frame` — the `wx.Frame` that owns the menu bar.
- `menubar` — your `wx.MenuBar`. It is set on the frame if it is not already.
- `focus_target` — a `wx.Window` to focus after a menu closes, after the window
  is maximized, and after it is reactivated. For a webview app this is the
  webview, so the in-page key handling keeps working.
- `webview` — an optional `wx.html2.WebView`. When given, the menu keys are also
  caught inside the page and bridged back automatically.
- `restore_focus` — an optional callable used instead of `focus_target.SetFocus`.
- `bridge_name` — the script-message handler name for the webview bridge. Change
  it only if it collides with one you already use.
- `bare_alt_ms` — how long the native path waits before treating a lone Alt as a
  tap. Any other key cancels it.
- `capture_native_keys` — off by default. On a normal Windows app the OS already
  routes Alt to the menu bar, so we don't hook it. Turn this on only if you have
  a native control that eats Alt itself and you want the library to drive the
  menu bar for it.

## Platforms

- Windows is where the work happens: the synthetic Alt signal (`SC_KEYMENU`) and
  the webview key bridge.
- macOS uses the global Apple menu bar, which is already accessible: VoiceOver
  reaches it with VO+M, Full Keyboard Access with Ctrl+F2. Option is a typing
  key on Mac, so the library does not hijack it. `activate()` and `open()` are
  no-ops there by design; focus restoration still runs.
- Linux desktops route Alt to the menu bar themselves for native-focus apps.

Wherever the synthetic driving doesn't apply, the library stays out of the way
and the native, screen-reader-aware mechanism takes over.

Methods you can call yourself:

- `activate()` — highlight the menu bar (what plain Alt and F10 do).
- `open(index)` — open a top-level menu by position.
- `handle_bridge_message(raw)` — if your app already owns the webview's
  script-message channel, route messages here instead of passing `webview=`.

## Where it helps most

Be honest with yourself about your app. In a plain native app, Windows already
routes Alt to the menu bar on its own, so here the value is consistency and the
focus-restoration guarantees (the parts wx sometimes flubs after a menu closes or
the window is maximized). The big, can't-live-without-it value is the webview and
hybrid case, where without this the menu bar is unreachable by keyboard.

## Pairs with wx-accessible-webview

[`wx-accessible-webview`](https://github.com/Community-Access/wx-accessible-webview)
makes the content accessible. This makes the menu bar accessible when that content
holds focus. Together they cover the whole window.

## Born out of VRP

This is a generalized extraction of the menu-bar keyboard handling built for VRP,
the accessible CHIRP radio programmer, which hosts its UI in a webview and needed
a menu bar a blind user could actually drive.

## Created by

Taylor Arndt, a Community Access project.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports, screen-reader testing, and
pull requests are all welcome.

## License

MIT. See [LICENSE](LICENSE).
