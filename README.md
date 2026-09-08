# LAN Kiosk Launcher

This launcher works in two roles:

- `instructor`: shows the app buttons and broadcasts the selected command to listeners.
- `listener`: shows `Waiting for instructions...` and launches whatever command the instructor sends.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Edit `apps.json`.

Instructor example:

```json
{
  "role": "instructor",
  "server_host": "",
  "port": 8765,
  "apps": [
    {"name": "Notepad", "cmd": "notepad.exe"},
    {"name": "Calculator", "cmd": "calc.exe"},
    {"name": "Paint", "cmd": "mspaint.exe"}
  ]
}
```

Listener example:

```json
{
  "role": "listener",
  "server_host": "10.0.0.15",
  "port": 8765,
  "apps": []
}
```

Use the instructor machine IP address in `server_host` for each listener.

3. Run the launcher on each device:

```bash
python main.py
```

On the instructor machine, clicking a button launches the app on the instructor and sends the same command to all connected listeners.
On listener machines, a black screen shows `Waiting for instructions...` until the command arrives.
