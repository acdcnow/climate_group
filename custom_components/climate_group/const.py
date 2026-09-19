"""Constants for the Climate Group integration."""

from __future__ import annotations

from typing import Any, Final

from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant

DOMAIN: Final = "climate_group"

DEFAULT_NAME: Final = "Climate Group"

#: Round the setpoints of the group to half degrees. The key is the same as in
#: the other climate_group forks, so their configuration keeps working.
CONF_DECIMAL_ACCURACY_TO_HALF: Final = "decimal_accuracy_to_half"

#: Features the group is able to aggregate and forward to its members.
#: Features reported by members that are not listed here (e.g. humidity) are
#: masked out, because the group has no meaningful way to handle them.
SUPPORTED_FEATURES: Final = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.SWING_MODE
    | ClimateEntityFeature.SWING_HORIZONTAL_MODE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)

#: Temperature units that can be selected for a group.
TEMPERATURE_UNITS: Final = (UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT)


def normalize_temperature_unit(value: Any, hass: HomeAssistant) -> str:
    """Return a valid temperature unit for a group.

    Accepts the short form used by the legacy YAML configuration ("C"/"F"),
    the values of ``UnitOfTemperature`` ("°C"/"°F") and ``None``.
    """
    if value is None:
        return hass.config.units.temperature_unit

    normalized = str(value).upper()
    if normalized == "C":
        return UnitOfTemperature.CELSIUS
    if normalized == "F":
        return UnitOfTemperature.FAHRENHEIT
    if normalized in TEMPERATURE_UNITS:
        return normalized

    # The config flow and the YAML schema both validate the unit, so this is
    # only a safety net.
    return hass.config.units.temperature_unit


def round_to_half(value: float) -> float:
    """Round a temperature to the nearest half degree.

    Thermostats that only accept setpoints in 0.5 steps cannot be set to e.g.
    21.3 degrees, so the group rounds the value instead of showing a setpoint
    the devices never report back.
    """
    return round(round(value * 2) / 2, 1)
