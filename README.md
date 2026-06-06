# SnippetTray

Your personal command launcher, one click away.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

SnippetTray sits quietly in your system tray and puts your most-used shell commands a single click away. No terminal hunting, no command history spelunking — just open the window, hit **Run**, and it executes with `sudo` in a fresh terminal.

---

## Features

- System tray icon that works on KDE Plasma, GNOME, XFCE, and any desktop supporting StatusNotifierItem
- Scrollable snippet list with description, command, and per-row action buttons
- One-click execution with automatic `sudo` in a new terminal window
- Copy any command to the clipboard instantly
- Add, edit, and delete snippets through a clean dialog — no config file editing required
- Snippets persist in a plain JSON file you can version-control or back up
- Hides to tray on close; never clutters your taskbar
- Single Python file, no framework dependencies beyond `pystray` and `Pillow`

---

## Screenshot

<img width="861" height="550" alt="Schermata_20260606_142527" src="https://github.com/user-attachments/assets/6ff813e6-4820-4108-bef7-26c98368df01" />

## Requirements

- Python 3.8 or later (system Python — see Wayland note below)
- A desktop environment with a system tray (KDE Plasma, GNOME + AppIndicator extension, XFCE, etc.)
- One of: `konsole`, `gnome-terminal`, `xfce4-terminal`, or `xterm`

**Python dependencies** — installed automatically by `install.sh`:

- [pystray](https://github.com/moses-palmer/pystray)
- [Pillow](https://python-pillow.org/)

**Wayland note:** On KDE Plasma and other Wayland compositors, SnippetTray must run under the system Python (`/usr/bin/python3`) rather than a virtualenv, because it needs the `gi` (PyGObject) package to register via the AppIndicator/StatusNotifierItem protocol. `install.sh` detects and handles this automatically.

---

## Installation

```bash
git clone git clone https://github.com/drakmanga/SnippetTray.git
cd snippettray
bash install.sh
```

The script will:

1. Install `pystray` and `Pillow` via `pip --user` using the correct Python interpreter
2. Copy `snippettray.py` to `~/.local/bin/`
3. Create `~/.config/autostart/snippettray.desktop` so the app starts automatically at login

To start immediately without logging out:

```bash
/usr/bin/python3 ~/.local/bin/snippettray.py &
```

---

## Usage

Once running, SnippetTray lives in the system tray. Left-click or right-click the icon to open the main window. The tray menu also provides **Open** and **Quit** entries.

### Main window

Each row in the snippet list has four buttons:

| Button | Action |
|--------|--------|
| Run | Opens a terminal and runs `sudo <command>` |
| Copy | Copies the command to the clipboard |
| Edit | Opens a pre-filled dialog to modify the snippet |
| Del | Deletes the snippet after confirmation |

Closing the window hides it back to the tray. Use **Quit** from the tray menu to exit completely.

### Adding a snippet

Click **+ Add Snippet** and fill in two fields:

- **Description** — a short label shown in the list (e.g. `Restart nginx`)
- **Command** — the shell command, without `sudo` (it is prepended automatically at runtime)

There are also two checkboxes:

- **Run with sudo (as root)** — enabled by default. Uncheck it for commands that must run as your normal user (e.g. user-space installers that explicitly reject root).
- **Keep terminal open after command finishes** — disabled by default. Enable it for interactive commands that prompt for input during execution (e.g. an installer that asks questions). Leave it unchecked for commands that run and exit on their own.

Press **Save** or Enter to confirm, Escape to cancel.

### Running a command

SnippetTray detects the first available terminal emulator in this order — `konsole`, `gnome-terminal`, `xfce4-terminal`, `xterm` — and runs the command inside it. The terminal closes automatically when the command exits.

---

## Data storage

Snippets are stored at:

```
~/.config/snippettray/snippets.json
```

The file is created on first run with three example snippets. You can edit it directly; changes take effect the next time the app starts.

---

## Uninstalling

```bash
pkill -f snippettray.py
rm ~/.local/bin/snippettray.py
rm ~/.config/autostart/snippettray.desktop
rm -rf ~/.config/snippettray    # also deletes all saved snippets
```

---

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please [open an issue](https://github.com/drakmanga/SnippetTray/issues).

To submit code changes:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your feature"`)
4. Push to your branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please keep PRs focused — one feature or fix per PR.

---

## License

MIT
