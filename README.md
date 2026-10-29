# LAN Kiosk Launcher

This project is a kiosk-style launcher for Windows machines. It supports two roles:

- `instructor`: displays the app launcher and broadcasts commands to connected listeners.
- `listener`: waits for instructions and launches the received app or system action.

## Current capabilities

- Launches configured desktop apps from a full-screen kiosk UI.
- Sends remote commands from the instructor to all connected listeners.
- Minimizes the instructor launcher after executing a command instead of closing it.
- Includes a bottom control bar with icon buttons for:
  - shutdown
  - reboot
  - local and remote volume mute toggle
  - operating time display in `HHHH:MM` format
- Runs in full-screen, borderless kiosk mode with the window always on top.

## Setup

1. Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

2. Configure the launcher using `config.json`, `instructor.json`, or `listener.json`.

Example instructor config:

```json
{
  "role": "instructor",
  "system_name": "complex1",
  "server_host": "",
  "port": 8765,
  "apps": [
    {"name": "Notepad", "cmd": "notepad.exe"},
    {"name": "Calculator", "cmd": "calc.exe"},
    {"name": "Paint", "cmd": "mspaint.exe"}
  ]
}
```

Example listener config:

```json
{
  "role": "listener",
  "system_name": "complex1",
  "server_host": "",
  "port": 8765,
  "apps": []
}
```

Give each complex a unique `system_name`, shared by its instructor and listeners. Listeners with an empty
`server_host` discover a matching instructor over the LAN; a configured `server_host`
continues to use a fixed IP. The instructor only accepts TCP clients with a matching
`system_name`. Allow UDP discovery and TCP connections on the configured `port` through
the local firewall.

3. Run the launcher on each device:

```bash
python main.py
```

For safe testing, add `-d` or `--debug` to log shutdown/reboot requests without executing or broadcasting them:

```bash
python main.py --debug
python main.py --config instructor.json -d
```

For a text menu without the kiosk UI, use `-t` or `--terminal`. The menu reserves `0` for system actions, and numbers config actions starting at `1`. Use `-e N` or `--execute N` to launch a config action directly by that number; system actions are not available through `-e`.

```bash
python main.py --terminal
python main.py --config instructor.json -t
python main.py --config instructor.json --execute 1
```

```bash
# You can specify a config file name
python main.py --config instructor.json
python main.py --config listener.json
```

On first launch, the launcher asks for an administrator password. It stores the password hash in the binary `admin_password.bin` file and accumulated operating time in the binary `operating_time.bin` file beside the selected configuration file. To reset the operating-time counter, run:

```bash
python main.py --config instructor.json --reset-clock YOUR_PASSWORD
```

## Build With PyInstaller

The repository includes `Launcher.spec`, which configures a one-file Windows build and bundles the `icons` directory. Install the dependencies, including PyInstaller, and run the build from the project directory:

```powershell
pip install -r requirements.txt
pyinstaller.exe .\Launcher.spec --clean
```

The generated executable is `dist\Launcher.exe`. Copy the required configuration file beside the executable, then select it when starting the launcher:

```powershell
.\dist\Launcher.exe --config instructor.json
.\dist\Launcher.exe --config listener.json
```

The first run creates `admin_password.bin` and `operating_time.bin` beside the selected configuration file. To reset the operating-time counter in the packaged application, run:

```powershell
.\dist\Launcher.exe --config instructor.json --reset-clock YOUR_PASSWORD
```

## Behavior

- On the instructor machine, clicking an app button launches the app locally and broadcasts it to the listeners.
- Shutdown and reboot buttons execute the action locally and broadcast it to connected listeners by default.
- In debug mode (`-d` or `--debug`), shutdown and reboot actions are logged locally but neither executed nor broadcast.
- Terminal mode displays configured app commands and a submenu for shutdown, reboot, and mute toggle without opening the kiosk UI.
- Launcher startup, application launches, system actions, mute state, listener connection state, and operating-time saves are recorded in `launcher.log` beside the selected configuration file.
- On listener machines, a black screen displays `Waiting for instructions...` until data is received.
- The clock indicates accumulated operating time across launcher sessions and is saved every ten minutes and during graceful shutdown.

## Notes

- The launcher is intended for supervised kiosk or managed workstation environments.
- The icons used for the system buttons are stored in the `icons` directory.
- The project includes a changelog in [changelog.md](changelog.md).
