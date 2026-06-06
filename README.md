# SnippetTray

A lightweight Linux desktop application that lives in the system tray and gives you one-click access to frequently used shell commands. Each snippet stores a command and a description; you can run it as root in a new terminal, copy it to the clipboard, or manage it through a simple GUI.

## Requirements

- Python 3.8 or later (system Python, not a virtualenv — see note below)
- A desktop environment with a system tray (KDE Plasma, GNOME with AppIndicator extension, XFCE, etc.)
- One of the following terminal emulators: `konsole`, `gnome-terminal`, `xfce4-terminal`, or `xterm`

**Python dependencies** (installed automatically by `install.sh`):

- [pystray](https://github.com/moses-palmer/pystray)
- [Pillow](https://python-pillow.org/)

**Note on Wayland:** On KDE Plasma and other Wayland compositors, SnippetTray requires the system Python (`/usr/bin/python3`) rather than a virtualenv Python, because it needs access to the `gi` (PyGObject) package to use the AppIndicator/StatusNotifierItem protocol. The `install.sh` script handles this automatically.

## Installation

Clone or download the repository, then run the install script:

```bash
bash install.sh
```

The script will:

1. Install `pystray` and `Pillow` via `pip --user` using the appropriate Python interpreter
2. Copy `snippettray.py` to `~/.local/bin/`
3. Create `~/.config/autostart/snippettray.desktop` so the app starts automatically at login

To start SnippetTray immediately without logging out:

```bash
/usr/bin/python3 ~/.local/bin/snippettray.py &
```

## Usage

After launching, SnippetTray runs silently in the background. Its icon appears in the system tray.

- **Left-click or right-click** the tray icon to open the main window
- The tray menu also provides an **Open** entry and a **Quit** entry

### Main window

The main window displays all saved snippets in a scrollable list. Each row shows the description and the command, with four action buttons on the right:

| Button | Action |
|--------|--------|
| Run | Executes the command in a new terminal window with `sudo` |
| Copy | Copies the raw command to the clipboard |
| Edit | Opens a dialog to modify the command or description |
| Del | Deletes the snippet after a confirmation prompt |

Closing the main window hides it back to the tray. To quit the application entirely, use **Quit** from the tray menu.

### Adding a snippet

Click **+ Add Snippet** in the toolbar. Fill in:

- **Description** — a short label shown in the list (e.g. "Restart nginx")
- **Command** — the shell command to run (without `sudo`; it is added automatically at runtime)

Press **Save** or hit Enter to confirm. Press Escape to cancel.

### Running a command

Clicking **Run** on a snippet opens a new terminal window and executes `sudo <command>`. The terminal closes automatically when the command finishes. SnippetTray tries the following terminal emulators in order and uses the first one found:

1. `konsole`
2. `gnome-terminal`
3. `xfce4-terminal`
4. `xterm`

## Data storage

Snippets are saved in plain JSON format at:

```
~/.config/snippettray/snippets.json
```

The file and its parent directory are created automatically on first run. Three example snippets are pre-loaded to demonstrate the format. You can edit the file directly if needed; changes take effect the next time the app loads.

## Uninstalling

```bash
pkill -f snippettray.py
rm ~/.local/bin/snippettray.py
rm ~/.config/autostart/snippettray.desktop
rm -rf ~/.config/snippettray   # also removes saved snippets
```
