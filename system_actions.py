import ctypes
import logging
import os
import subprocess


logger = logging.getLogger("lansoftlauncher")

_POWER_ACTIONS = {
    "shutdown": ["shutdown", "/s", "/t", "0"],
    "reboot": ["shutdown", "/r", "/t", "0"],
}


def execute_system_action(action: str, *, debug: bool = False) -> bool:
    if action == "mute_toggle":
        if os.name != "nt":
            logger.warning("Mute toggle is only supported on Windows")
            return False
        try:
            user32 = ctypes.windll.user32
            volume_mute_key = 0xAD
            user32.keybd_event(volume_mute_key, 0, 0, 0)
            user32.keybd_event(volume_mute_key, 0, 0x0002, 0)
            logger.info("System action executed: mute_toggle")
            return True
        except (AttributeError, OSError):
            logger.exception("Failed to execute system action: mute_toggle")
            return False

    command = _POWER_ACTIONS.get(action)
    if command is None:
        logger.warning("Unsupported system action ignored: %s", action)
        return False
    if debug:
        logger.info("System action recorded (debug mode, not executed): %s", action)
        return True

    try:
        result = subprocess.run(command, check=False)
        logger.info(
            "System action executed: %s returncode=%s",
            action,
            result.returncode,
        )
        return result.returncode == 0
    except OSError:
        logger.exception("Failed to execute system action: %s", action)
        return False
