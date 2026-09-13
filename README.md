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
- The system action buttons also trigger the action locally and send the command to all connected listeners.
- On listener machines, a black screen displays `Waiting for instructions...` until data is received.
- The clock indicates accumulated operating time across launcher sessions and is saved every ten minutes and during graceful shutdown.

## Notes

- The launcher is intended for supervised kiosk or managed workstation environments.
- The icons used for the system buttons are stored in the `icons` directory.
- The project includes a changelog in [changelog.md](changelog.md).
