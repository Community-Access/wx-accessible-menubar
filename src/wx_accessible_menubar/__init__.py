"""wx-accessible-menubar — keyboard-accessible native menu bars for wxPython.

A native ``wx.MenuBar`` reads perfectly in NVDA and JAWS; the hard part is
reaching it from the keyboard when a child control (a focused ``wx.html2``
WebView2 above all) swallows Alt before Windows can route it to the menu bar.

:class:`AccessibleMenuBar` fixes that: plain Alt activates the bar, Alt+mnemonic
opens a menu, F10 works, Left/Right walk across the top-level menus, and focus
returns to your content afterward. It catches the keys with a frame-level key
hook for native apps and with an injected in-page listener for webview apps,
and drives the real native menu bar (no custom-drawn menu).

Built to pair with ``wx-accessible-webview``; extracted from VRP, the
accessible CHIRP radio programmer. A Community Access project.
"""

from __future__ import annotations

from wx_accessible_menubar.menubar import AccessibleMenuBar, DEFAULT_BRIDGE_NAME

__version__ = "0.1.1"
__all__ = [
    "AccessibleMenuBar",
    "DEFAULT_BRIDGE_NAME",
    "__version__",
]
