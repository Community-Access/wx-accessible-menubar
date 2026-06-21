"""Keyboard-accessible native menu bars for wxPython.

A native ``wx.MenuBar`` is the most screen-reader-friendly menu there is: NVDA
and JAWS read real Win32 menus perfectly, with arrow navigation and mnemonics
handled by the OS. The problem is *reaching* it from the keyboard when a child
control swallows the keys before Windows can route Alt to the menu bar. A
focused ``wx.html2.WebView`` (Edge WebView2) is the classic offender: it runs
out of process and grabs the keyboard, so wx never sees Alt at all
(wxWidgets issue #24786).

:class:`AccessibleMenuBar` makes the native menu bar reliably keyboard-drivable:

* plain Alt activates the bar (then Left/Right walk across the top-level menus),
* Alt+<mnemonic> opens that menu, F10 activates the bar,
* focus returns to your content after a menu closes, after the window is
  maximized, and after it is reactivated.

It captures the keys two ways and uses whichever fits:

* a frame-level ``EVT_CHAR_HOOK`` for apps whose focus is a native control, and
* an in-page key listener injected into a ``wx.html2.WebView`` (the only place
  that still sees the keys when a webview holds focus), bridged back over the
  webview's own script-message channel.

On Windows it drives the real menu bar with ``WM_SYSCOMMAND`` / ``SC_KEYMENU``
(the exact signal Alt sends). On other platforms it falls back to native
handling and a popup, so it is safe to attach everywhere.

Extracted from VRP, the accessible CHIRP radio programmer, and built to pair
with ``wx-accessible-webview``.
"""

from __future__ import annotations

import json
import logging
from typing import Callable, Dict, Optional

import wx

LOG = logging.getLogger(__name__)

_IS_MSW = wx.Platform == "__WXMSW__"

# Windows: the menu-activation message Alt normally sends.
_WM_SYSCOMMAND = 0x0112
_SC_KEYMENU = 0xF100

#: Default script-message handler name used for the webview bridge.
DEFAULT_BRIDGE_NAME = "wxAccessibleMenuBar"


def _post_sc_keymenu(hwnd: int, lparam: int) -> bool:
    """Post ``WM_SYSCOMMAND`` / ``SC_KEYMENU`` to ``hwnd``.

    ``lparam`` is a menu's mnemonic character to open that menu, or 0 to just
    activate the bar (highlight the first item) so Left/Right walk across it.
    Either way Windows enters the real native menu-bar keyboard loop. Returns
    ``False`` (a no-op) off Windows.
    """
    if not _IS_MSW:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    # Set argtypes so a 64-bit HWND isn't truncated to a C int.
    user32.PostMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    ]
    user32.PostMessageW.restype = wintypes.BOOL
    return bool(user32.PostMessageW(hwnd, _WM_SYSCOMMAND, _SC_KEYMENU, lparam))


# Injected into a webview: catch Alt / Alt+letter / F10 (the menu keys WebView2
# hides from wx) and post them to the host. %(mnemonics)s is a JSON object
# mapping a lower-case mnemonic char to its top-level menu index; %(bridge)s is
# the script-message handler name.
_WEBVIEW_JS = r"""
(function(){
  if (window.__wxAmbInstalled) return;
  window.__wxAmbInstalled = true;
  var MN = %(mnemonics)s;
  var BRIDGE = %(bridge)s;
  function post(o){ try { window[BRIDGE].postMessage(JSON.stringify(o)); } catch(e){} }
  // Alt alone is confirmed on keyup, so it is never mistaken for the start of
  // Alt+letter, Alt+Tab or Alt+F4 (their second key clears the flag first).
  var altAlone = false;
  document.addEventListener('keyup', function(e){
    if(e.key==='Alt'){ if(altAlone){ e.preventDefault(); post({amb:'activate'}); } altAlone=false; }
  }, true);
  document.addEventListener('keydown', function(e){
    if(e.key==='Alt' && !e.ctrlKey && !e.shiftKey && !e.metaKey){ altAlone=true; return; }
    if(e.key==='F10' && !e.altKey && !e.ctrlKey && !e.shiftKey && !e.metaKey){
      altAlone=false; e.preventDefault(); post({amb:'activate'}); return; }
    if(e.altKey && !e.ctrlKey && !e.metaKey){
      var idx = MN[(e.key||'').toLowerCase()];
      altAlone=false;
      if(idx!==undefined){ e.preventDefault(); post({amb:'open', index:idx}); return; }
    } else if(e.key!=='Alt'){ altAlone=false; }
  }, true);
})();
"""


class AccessibleMenuBar:
    """Make a frame's native ``wx.MenuBar`` keyboard-accessible.

    Build your ``wx.MenuBar`` as normal (top-level menus with ``&`` mnemonics in
    their labels, e.g. ``"&File"``), then wrap it::

        bar = wx.MenuBar()
        ...
        AccessibleMenuBar(frame, bar, focus_target=my_webview, webview=my_webview)

    Parameters
    ----------
    frame:
        The ``wx.Frame`` (or ``wx.MDIParentFrame``) that owns the menu bar.
    menubar:
        The ``wx.MenuBar``. If it is not already the frame's menu bar, it is set.
    focus_target:
        A ``wx.Window`` to focus after a menu closes / the window is maximized or
        reactivated. For a webview app this is usually the webview control, so
        the in-page key handling keeps working. Ignored if ``restore_focus`` is
        given.
    webview:
        Optional ``wx.html2.WebView``. When given, the menu keys are also caught
        inside the page (the only place they survive a focused WebView2) and
        bridged back automatically. Pass the underlying ``wx.html2.WebView``; if
        you use ``wx-accessible-webview`` that is ``AccessibleWebView.view``.
    restore_focus:
        Optional zero-argument callable used instead of ``focus_target.SetFocus``
        when returning focus.
    bridge_name:
        Script-message handler name for the webview bridge. Defaults to
        :data:`DEFAULT_BRIDGE_NAME`; change it only if it collides with one you
        already use.
    bare_alt_ms:
        How long (ms) the native ``EVT_CHAR_HOOK`` path waits before treating a
        lone Alt as a tap. Any other key cancels it. Tunable; 200 ms reads as
        instant.
    """

    def __init__(
        self,
        frame: "wx.Frame",
        menubar: "wx.MenuBar",
        *,
        focus_target: Optional["wx.Window"] = None,
        webview: Optional["object"] = None,
        restore_focus: Optional[Callable[[], None]] = None,
        bridge_name: str = DEFAULT_BRIDGE_NAME,
        bare_alt_ms: int = 200,
        capture_native_keys: bool = False,
    ) -> None:
        self._frame = frame
        self._menubar = menubar
        self._focus_target = focus_target
        self._restore_focus_cb = restore_focus
        self._webview = webview
        self._bridge_name = bridge_name
        self._bare_alt_ms = int(bare_alt_ms)
        self._capture_native_keys = bool(capture_native_keys)
        self._bare_alt_timer: Optional["wx.CallLater"] = None

        if frame.GetMenuBar() is not menubar:
            frame.SetMenuBar(menubar)

        # mnemonic char -> top-level index, parsed from the menu labels, and the
        # reverse index -> mnemonic char code for SC_KEYMENU.
        self._mnemonics: Dict[str, int] = self._compute_mnemonics(menubar)
        self._index_to_char: Dict[int, int] = {i: ord(c) for c, i in self._mnemonics.items()}

        # Focus restoration runs on every platform.
        frame.Bind(wx.EVT_MENU_CLOSE, self._on_menu_close)
        frame.Bind(wx.EVT_MAXIMIZE, self._on_maximize)
        frame.Bind(wx.EVT_ACTIVATE, self._on_activate)

        # The synthetic key handling is Windows-only: that is where Alt has to be
        # reconstructed. macOS uses the global menu bar (VoiceOver VO+M /
        # Ctrl+F2) and Linux desktops route Alt themselves, so we don't interfere.
        if _IS_MSW:
            # Webview path: the in-page listener is the only thing that sees keys
            # a focused WebView2 swallows.
            if webview is not None:
                self._wire_webview(webview)
            # Native control path is opt-in: on a normal Windows app the OS
            # already routes Alt to the menu bar, so hooking it would double up.
            # Enable only when a native control eats Alt itself.
            if capture_native_keys:
                frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    # -- public API ----------------------------------------------------------

    def activate(self) -> None:
        """Highlight the menu bar with no menu dropped, so Right/Left walk across
        the top-level menus. This is what plain Alt and F10 do on Windows.

        Windows only: it posts the Alt signal to the real menu bar. On macOS the
        menu bar is the global Apple menu bar, reached with VoiceOver (VO+M) or
        Full Keyboard Access (Ctrl+F2); on Linux the desktop routes Alt itself.
        On those platforms this is a deliberate no-op so we never fight the
        native, screen-reader-aware mechanism.
        """
        self._cancel_bare_alt()
        if not _post_sc_keymenu(self._frame.GetHandle(), 0):
            LOG.debug("activate(): native menu-bar keyboard access is handled by "
                      "the OS on this platform (macOS VO+M / Ctrl+F2).")

    def open(self, index: int) -> None:
        """Open the top-level menu at ``index`` in the native keyboard loop
        (Windows). A no-op on other platforms (see :meth:`activate`)."""
        self._cancel_bare_alt()
        if not _post_sc_keymenu(self._frame.GetHandle(), self._index_to_char.get(index, 0)):
            LOG.debug("open(%r): handled natively by the OS on this platform.", index)

    def handle_bridge_message(self, raw) -> bool:
        """Handle a webview message yourself.

        Use this if your app already owns the webview's script-message channel
        and routes messages itself: pass the raw JSON string or decoded dict.
        Returns ``True`` if it was one of ours.
        """
        data = raw
        if isinstance(raw, (str, bytes)):
            try:
                data = json.loads(raw)
            except Exception:
                return False
        if not isinstance(data, dict):
            return False
        kind = data.get("amb")
        if kind == "activate":
            self.activate()
            return True
        if kind == "open":
            try:
                self.open(int(data.get("index", 0)))
            except (TypeError, ValueError):
                self.open(0)
            return True
        return False

    @property
    def mnemonics(self) -> Dict[str, int]:
        """Mapping of mnemonic char -> top-level menu index, parsed from labels."""
        return dict(self._mnemonics)

    # -- mnemonics -----------------------------------------------------------

    @staticmethod
    def _compute_mnemonics(menubar: "wx.MenuBar") -> Dict[str, int]:
        result: Dict[str, int] = {}
        for i in range(menubar.GetMenuCount()):
            label = menubar.GetMenuLabel(i)  # includes the '&' mnemonic marker
            pos = label.find("&")
            if pos != -1 and pos + 1 < len(label):
                ch = label[pos + 1].lower()
                result.setdefault(ch, i)
        return result

    # -- native key hook -----------------------------------------------------

    def _on_char_hook(self, event: "wx.KeyEvent") -> None:
        key = event.GetKeyCode()
        # Plain Alt by itself: arm activation (cancelled below if a second key
        # turns it into a combo).
        if key == wx.WXK_ALT and not event.ControlDown() and not event.ShiftDown():
            self._schedule_bare_alt()
            event.Skip()
            return
        self._cancel_bare_alt()
        if event.AltDown() and not event.ControlDown() and not event.ShiftDown():
            letter = chr(key).lower() if 32 <= key < 128 else ""
            idx = self._mnemonics.get(letter)
            if idx is not None:
                self.open(idx)
                return  # consumed
        if key == wx.WXK_F10 and not event.HasAnyModifiers():
            self.activate()
            return  # consumed
        event.Skip()

    def _schedule_bare_alt(self) -> None:
        self._cancel_bare_alt()
        self._bare_alt_timer = wx.CallLater(self._bare_alt_ms, self.activate)

    def _cancel_bare_alt(self) -> None:
        timer = self._bare_alt_timer
        if timer is not None and timer.IsRunning():
            timer.Stop()
        self._bare_alt_timer = None

    # -- focus restoration ---------------------------------------------------

    def _restore_focus(self) -> None:
        if self._restore_focus_cb is not None:
            try:
                self._restore_focus_cb()
            except Exception:  # noqa: BLE001 - never let focus restore crash the app
                LOG.debug("restore_focus callback raised", exc_info=True)
            return
        target = self._focus_target
        if target is not None:
            try:
                target.SetFocus()
            except Exception:  # noqa: BLE001
                LOG.debug("focus_target.SetFocus() raised", exc_info=True)

    def _on_menu_close(self, event: "wx.MenuEvent") -> None:
        event.Skip()
        wx.CallAfter(self._restore_focus)

    def _on_maximize(self, event: "wx.MaximizeEvent") -> None:
        event.Skip()
        wx.CallAfter(self._restore_focus)

    def _on_activate(self, event: "wx.ActivateEvent") -> None:
        event.Skip()
        # Skip while a modal dialog is up (the frame is disabled then), so we
        # don't yank focus away from the dialog.
        if event.GetActive() and self._frame.IsEnabled():
            wx.CallAfter(self._restore_focus)

    # -- webview bridge ------------------------------------------------------

    def _wire_webview(self, webview) -> None:
        import wx.html2  # local import: only needed for the webview path

        try:
            webview.AddScriptMessageHandler(self._bridge_name)
        except Exception:  # noqa: BLE001
            LOG.warning(
                "AddScriptMessageHandler(%r) failed; webview menu keys disabled",
                self._bridge_name,
            )
            return
        webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._on_script_message)
        webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self._on_webview_loaded)
        # If the page is already loaded, inject straight away.
        self._inject_js(webview)

    def _on_webview_loaded(self, event) -> None:
        event.Skip()
        self._inject_js(self._webview)

    def _inject_js(self, webview) -> None:
        js = _WEBVIEW_JS % {
            "mnemonics": json.dumps(self._mnemonics),
            "bridge": json.dumps(self._bridge_name),
        }
        try:
            webview.RunScript(js)
        except Exception:  # noqa: BLE001
            LOG.debug("RunScript(menu key listener) raised", exc_info=True)

    def _on_script_message(self, event) -> None:
        # The event fires for every handler on this webview; only take ours.
        try:
            if event.GetMessageHandler() != self._bridge_name:
                event.Skip()
                return
        except Exception:  # noqa: BLE001 - older wx may not expose the name
            pass
        self.handle_bridge_message(event.GetString())
