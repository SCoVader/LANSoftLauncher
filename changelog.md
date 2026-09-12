# Changelog

## Version 0.5

- Added a compact system action toolbar with icon-based shutdown, reboot, and mute/unmute controls.
- Shutdown and reboot actions now trigger locally and broadcast to listeners when used from the instructor UI.
- Volume toggle now updates locally and sends the mute/unmute command to remote listener machines.
- The launcher no longer exits immediately after launching an app; it minimizes instead, keeping the kiosk interface available.
- Added a running operating-time clock in HHHH:MM format to track approximate uptime for deployed systems.
- Updated network message handling so both command launches and system actions are received correctly from instructor broadcasts.
