![AI README](https://img.shields.io/badge/AI-README-blue)
# PawchiveHooker

CLI/Daemon for "webhooking" [pawchive.pw](https://pawchive.pw) - polling-based webhook emulation.

## Requirements

- Python 3.10+
- pipx (recommended) or pip

## Installing

### pipx

```bash
pipx install git+https://github.com/MetyV/PawchiveHooker.git
```

### pip

```bash
pip install --user git+https://github.com/MetyV/PawchiveHooker.git
```

## Uninstalling

If the daemon is running, stop it first:

```bash
hooker stop
```

Then remove the package:

```bash
pipx uninstall pawchive-hooker
```

If installed via pip:

```bash
pip uninstall pawchive-hooker
```

Configuration and state files are stored in the platform-specific user config directory and are **not** removed automatically:

| Platform | Path |
|---|---|
| Linux   | `~/.config/Pawchive/` |
| macOS   | `~/Library/Application Support/Pawchive/` |
| Windows | `%LOCALAPPDATA%\Pawchive\` |

To remove them:

```bash
# Linux
rm -rf ~/.config/Pawchive

# macOS
rm -rf ~/Library/Application\ Support/Pawchive

# Windows (PowerShell)
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Pawchive"

# Windows (CMD)
rmdir /s /q "%LOCALAPPDATA%\Pawchive"
```

## Usage

### Add an author to track

```bash
hooker --add-author 'service|id'
```

Example:

```bash
hooker --add-author 'patreon|12345'
```

### Start the daemon

```bash
hooker --check-profiles start
```

The daemon checks for updates once an hour, at `:00`.

### Stop the daemon

```bash
hooker stop
```

### Options

| Flag | Description |
|---|---|
| `--add-author 'service\|id'` | Add an author to the tracking list |
| `--check-profiles` | Check author profile updates |
| `--check-posts` | Check author post updates (not implemented for now) |
| `--semaphore N` | Max concurrent requests (default: 4) |
| `--auto-update` | Update `endpoints.py` before starting |
| `--no-auto-update` | Do not update `endpoints.py` |

### Configuration

Settings are stored in `settings.json` in the user config directory (see [Uninstalling](#uninstalling) for paths):

```json
{
  "semaphore": 4,
  "auto_update": false
}
```

Changes to `settings.json` are picked up on the next hourly iteration, without restarting the daemon.