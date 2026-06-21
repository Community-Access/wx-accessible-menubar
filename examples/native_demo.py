"""Native-control demo: a text editor with an accessible menu bar.

Run it (ideally with a screen reader on), tap Alt, and use Left/Right to move
across File / Edit / Help, Up/Down inside a menu, Enter to choose, Escape to
return to the text box.

    python examples/native_demo.py
"""

import wx

from wx_accessible_menubar import AccessibleMenuBar


class Demo(wx.Frame):
    def __init__(self):
        super().__init__(None, title="wx-accessible-menubar — native demo", size=(700, 480))

        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.text.SetValue(
            "Tap Alt, then use Left/Right to move across the menus.\n"
            "Up/Down inside a menu, Enter to choose, Escape to come back here."
        )

        bar = wx.MenuBar()

        file_menu = wx.Menu()
        m_new = file_menu.Append(wx.ID_NEW, "&New\tCtrl+N")
        m_open = file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
        file_menu.AppendSeparator()
        m_exit = file_menu.Append(wx.ID_EXIT, "E&xit")
        bar.Append(file_menu, "&File")

        edit_menu = wx.Menu()
        m_copy = edit_menu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
        m_paste = edit_menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V")
        bar.Append(edit_menu, "&Edit")

        help_menu = wx.Menu()
        m_about = help_menu.Append(wx.ID_ABOUT, "&About")
        bar.Append(help_menu, "&Help")

        # One line: make the whole menu bar keyboard-accessible, and send focus
        # back to the text box after a menu closes.
        AccessibleMenuBar(self, bar, focus_target=self.text)

        self.Bind(wx.EVT_MENU, lambda e: self.Close(), m_exit)
        self.Bind(wx.EVT_MENU, self._on_about, m_about)
        for item in (m_new, m_open, m_copy, m_paste):
            self.Bind(wx.EVT_MENU, self._on_stub, item)

        self.CreateStatusBar()
        self.SetStatusText("Tap Alt to reach the menus.")
        self.text.SetFocus()

    def _on_about(self, _event):
        wx.MessageBox(
            "wx-accessible-menubar native demo.\nTap Alt to reach the menus.",
            "About",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _on_stub(self, event):
        item = self.GetMenuBar().FindItemById(event.GetId())
        self.SetStatusText(f"Chose: {item.GetItemLabelText() if item else event.GetId()}")


def main():
    app = wx.App(False)
    Demo().Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
