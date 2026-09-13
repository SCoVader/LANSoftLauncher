# Changelog

## Version 0.6

- Added administrator password protection using a salted PBKDF2-HMAC-SHA256 password digest stored in `admin_password.bin`.
- Added persistent operating-time tracking in `operating_time.bin`, with periodic and graceful-shutdown saves.
- Added the `--reset-clock PASSWORD` command-line option for resetting accumulated operating time.
- Added atomic operating-time file writes and validation for password and operating-time records.
- Added PyInstaller-safe resource resolution through `resource_path`, including bundled system-button icons.
- Added `Launcher.spec` for building a one-file Windows executable named `Launcher.exe`.
- Expanded launcher feature tests for password storage, password verification, and operating-time persistence.

## Version 0.5

- Added a compact system action toolbar with icon-based shutdown, reboot, and mute/unmute controls.
- Shutdown and reboot actions now trigger locally and broadcast to listeners when used from the instructor UI.
- Volume toggle now updates locally and sends the mute/unmute command to remote listener machines.
- The launcher no longer exits immediately after launching an app; it minimizes instead, keeping the kiosk interface available.
- Added a running operating-time clock in HHHH:MM format to track approximate uptime for deployed systems.
- Updated network message handling so both command launches and system actions are received correctly from instructor broadcasts.
