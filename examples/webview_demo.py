"""Webview demo: a menu bar that works even though a WebView2 holds focus.

This is the case that motivated the library. The window's content is a
``wx.html2.WebView``; on Windows that webview eats Alt before wx can see it, so
without help the menu bar is unreachable by keyboard. With ``AccessibleMenuBar``
you tap Alt and the native menu bar opens anyway.

    python examples/webview_demo.py

Tap Alt, then Left/Right across File / View / Help. (Windows is the case that
matters here; on macOS/Linux it falls back to native handling.)
"""

import wx
import wx.html2

from wx_accessible_menubar import AccessibleMenuBar

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Webview demo</title></head>
<body>
  <h1>Webview content</h1>
  <p>This text lives inside a WebView2. Click here, then tap Alt: the native
     menu bar still opens, and Left/Right move across the menus.</p>
  <p><button onclick="document.getElementById('out').textContent='button works too'">A button</button></p>
  <p id="out" role="status" aria-live="polite"></p>
</body></html>"""


class Demo(wx.Frame):
    def __init__(self):
        super().__init__(None, title="wx-accessible-menubar — webview demo", size=(760, 520))

        self.web = wx.html2.WebView.New(self)

        bar = wx.MenuBar()
        file_menu = wx.Menu()
        m_open = file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
        file_menu.AppendSeparator()
        m_exit = file_menu.Append(wx.ID_EXIT, "E&xit")
        bar.Append(file_menu, "&File")

        view_menu = wx.Menu()
        m_reload = view_menu.Append(wx.ID_REFRESH, "&Reload")
        bar.Append(view_menu, "&View")

        help_menu = wx.Menu()
        m_about = help_menu.Append(wx.ID_ABOUT, "&About")
        bar.Append(help_menu, "&Help")

        # Pass the webview so the in-page key listener is installed and focus is
        # returned to the page after a menu closes.
        AccessibleMenuBar(self, bar, webview=self.web, focus_target=self.web)

        self.Bind(wx.EVT_MENU, lambda e: self.Close(), m_exit)
        self.Bind(wx.EVT_MENU, lambda e: self.web.Reload(), m_reload)
        self.Bind(wx.EVT_MENU, self._on_about, m_about)
        self.Bind(wx.EVT_MENU, lambda e: self.SetStatusText("Open chosen"), m_open)

        self.CreateStatusBar()
        self.SetStatusText("Tap Alt to reach the menus (even though a webview has focus).")
        self.web.SetPage(PAGE, "")
        self.web.SetFocus()

    def _on_about(self, _event):
        wx.MessageBox(
            "wx-accessible-menubar webview demo.\n"
            "The menu bar works even though a WebView2 holds focus.",
            "About",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )


def main():
    app = wx.App(False)
    Demo().Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
