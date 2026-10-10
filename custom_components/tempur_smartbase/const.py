"""Constants for the Tempur Smartbase (Sleeptracker) integration."""

from __future__ import annotations

from datetime import timedelta
from enum import IntEnum
from typing import Final

DOMAIN: Final = "tempur_smartbase"
MANUFACTURER: Final = "Tempur"

CONF_BRAND: Final = "brand"

BRAND_TEMPUR: Final = "tempur"
BRAND_BEAUTYREST: Final = "beautyrest"
BRAND_SERTA: Final = "serta"

# Cloud host and app client identity per brand. The Tempur app ("Sleeptracker AI")
# talks to tsi.sleeptracker.com; Beautyrest and Serta share motionxlive.com.
BRAND_CONFIG: Final[dict[str, dict[str, str]]] = {
    BRAND_TEMPUR: {
        "base_host": "tsi.sleeptracker.com",
        "client_id": "sleeptracker-android-tsi",
        "client_version": "1.9.47",
    },
    BRAND_BEAUTYREST: {
        "base_host": "motionxlive.com",
        "client_id": "sleeptracker-android",
        "client_version": "6.5.15",
    },
    BRAND_SERTA: {
        "base_host": "motionxlive.com",
        "client_id": "sleeptracker-android",
        "client_version": "6.5.15",
    },
}

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

FEATURE_MOTORS: Final = "motors"
FEATURE_ENV_SENSORS: Final = "env_sensors"


class Command(IntEnum):
    """Values for `bedControlCommand` on the adjustableBaseControls endpoint."""

    PRESET_ZERO_G = 0
    STATUS = 1
    PRESET_FLAT = 2
    PRESET_TV = 3
    PRESET_ANTI_SNORE = 4
    PRESET_USER_FAVORITE = 6

    MOTOR_HEAD_UP = 100
    MOTOR_HEAD_DOWN = 101
    MOTOR_FEET_UP = 102
    MOTOR_FEET_DOWN = 103
    MOTOR_LUMBAR_UP = 104
    MOTOR_LUMBAR_DOWN = 105
    MOTOR_LUMBAR_STOP = 106
    MOTOR_HEAD_STOP = 107
    MOTOR_FEET_STOP = 108
    MOTOR_TILT_UP = 120
    MOTOR_TILT_DOWN = 121
    MOTOR_TILT_STOP = 122

    MASSAGE_HEAD_STEP = 210
    MASSAGE_FOOT_STEP = 211
    MASSAGE_STEP = 225
    MASSAGE_PATTERN_STEP = 226
    TOGGLE_SAFETY_LIGHTS = 230
    MASSAGE_TIMER_STEP = 231

    PROGRAM_TV = 300
    PROGRAM_ANTI_SNORE = 302
    PROGRAM_ZERO_G = 303
    PROGRAM_USER_FAVORITE = 304


MASSAGE_PATTERNS: Final = {0: "none", 1: "pulse", 2: "constant", 3: "ripple"}
