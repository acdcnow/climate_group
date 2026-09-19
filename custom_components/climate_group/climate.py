"""This platform allows several climate devices to be grouped into one climate device."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import logging
from statistics import mean
from typing import Any

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    ATTR_SWING_HORIZONTAL_MODE,
    ATTR_SWING_HORIZONTAL_MODES,
    ATTR_SWING_MODE,
    ATTR_SWING_MODES,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_STEP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.group.entity import GroupEntity
from homeassistant.components.group.util import (
    find_state_attributes,
    reduce_attribute,
    states_equal,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    CONF_ENTITIES,
    CONF_NAME,
    CONF_TEMPERATURE_UNIT,
    CONF_UNIQUE_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    CONF_DECIMAL_ACCURACY_TO_HALF,
    DEFAULT_NAME,
    SUPPORTED_FEATURES,
    normalize_temperature_unit,
    round_to_half,
)

_LOGGER = logging.getLogger(__name__)

# No limit on parallel updates to enable a group calling another group
PARALLEL_UPDATES = 0

#: Attributes that members expect to be converted from the group unit to the
#: unit system of Home Assistant.
CONVERTIBLE_ATTRIBUTES = (ATTR_TEMPERATURE, ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_TEMPERATURE_UNIT): cv.temperature_unit,
        vol.Optional(CONF_DECIMAL_ACCURACY_TO_HALF, default=False): cv.boolean,
        vol.Required(CONF_ENTITIES): cv.entities_domain(CLIMATE_DOMAIN),
    }
)


def _most_frequent(values: list[Any]) -> Any:
    """Return the most frequent value, the first seen value wins a tie."""
    return Counter(values).most_common(1)[0][0]


def _ordered_unique(values: Iterable[Any]) -> list[Any]:
    """Return the unique values, keeping the order they were seen in."""
    return list(dict.fromkeys(values))


def _to_hvac_modes(values: Iterable[Any]) -> list[HVACMode]:
    """Return the valid HVAC modes of an iterable, OFF first."""
    modes: list[HVACMode] = []
    for value in values:
        try:
            mode = HVACMode(value)
        except ValueError:
            _LOGGER.debug("Ignoring unsupported HVAC mode: %s", value)
            continue
        if mode not in modes:
            modes.append(mode)

    if HVACMode.OFF in modes:
        modes.remove(HVACMode.OFF)
        modes.insert(0, HVACMode.OFF)

    return modes


def _to_hvac_action(value: Any) -> HVACAction | None:
    """Return a valid HVAC action, or None for an unsupported one."""
    try:
        return HVACAction(value)
    except ValueError:
        _LOGGER.debug("Ignoring unsupported HVAC action: %s", value)
        return None


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up a climate group from the (legacy) YAML configuration."""
    async_add_entities(
        [
            ClimateGroup(
                config.get(CONF_UNIQUE_ID),
                config[CONF_NAME],
                config[CONF_ENTITIES],
                normalize_temperature_unit(config.get(CONF_TEMPERATURE_UNIT), hass),
                config.get(CONF_DECIMAL_ACCURACY_TO_HALF, False),
            )
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize climate group config entry."""
    options = config_entry.options
    data = config_entry.data

    async_add_entities(
        [
            ClimateGroup(
                config_entry.entry_id,
                options.get(CONF_NAME, data.get(CONF_NAME, config_entry.title)),
                options.get(CONF_ENTITIES, data.get(CONF_ENTITIES, [])),
                normalize_temperature_unit(
                    options.get(
                        CONF_TEMPERATURE_UNIT, data.get(CONF_TEMPERATURE_UNIT)
                    ),
                    hass,
                ),
                options.get(
                    CONF_DECIMAL_ACCURACY_TO_HALF,
                    data.get(CONF_DECIMAL_ACCURACY_TO_HALF, False),
                ),
            )
        ]
    )


class ClimateGroup(GroupEntity, ClimateEntity):
    """Representation of a climate group."""

    _attr_available: bool = False
    _attr_assumed_state: bool = True
    _attr_should_poll: bool = False

    def __init__(
        self,
        unique_id: str | None,
        name: str,
        entity_ids: list[str],
        temperature_unit: str,
        decimal_accuracy_to_half: bool = False,
    ) -> None:
        """Initialize a climate group."""
        self._entity_ids = list(entity_ids)
        self._member_features: dict[str, ClimateEntityFeature] = {}
        self._decimal_accuracy_to_half = bool(decimal_accuracy_to_half)

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_extra_state_attributes = {ATTR_ENTITY_ID: self._entity_ids}
        self._attr_temperature_unit = temperature_unit

        # Defaults, overwritten on every state update.
        self._attr_supported_features = ClimateEntityFeature(0)
        self._attr_hvac_modes = [HVACMode.OFF]
        self._attr_hvac_mode = None
        self._attr_hvac_action = None

        self._attr_swing_modes = None
        self._attr_swing_mode = None
        self._attr_swing_horizontal_modes = None
        self._attr_swing_horizontal_mode = None

        self._attr_fan_modes = None
        self._attr_fan_mode = None

        self._attr_preset_modes = None
        self._attr_preset_mode = None

    @callback
    def async_update_supported_features(
        self,
        entity_id: str,
        new_state: State | None,
    ) -> None:
        """Keep track of the features a member entity supports.

        Called by ``GroupEntity`` for every member on add and on every state
        change.
        """
        features = None
        if new_state is not None:
            features = new_state.attributes.get(ATTR_SUPPORTED_FEATURES)

        if not isinstance(features, int):
            self._member_features.pop(entity_id, None)
            return

        self._member_features[entity_id] = (
            ClimateEntityFeature(features) & SUPPORTED_FEATURES
        )

    @callback
    def async_update_group_state(self) -> None:
        """Query all members and determine the climate group state."""
        states: list[State] = [
            state
            for entity_id in self._entity_ids
            if (state := self.hass.states.get(entity_id)) is not None
        ]

        # The group is assumed to be changed when its members do not agree
        # or when a member does not know its real state.
        self._update_assumed_state_from_members()
        if not states_equal(states):
            self._attr_assumed_state = True

        # Set group as unavailable if all members are unavailable or missing
        self._attr_available = any(
            state.state != STATE_UNAVAILABLE for state in states
        )

        self._update_temperature(states)
        self._update_hvac(states)
        self._update_swing(states)
        self._update_fan(states)
        self._update_preset(states)
        self._aggregate_supported_features(states)

        _LOGGER.debug("State update complete for %s", self.name)

    @callback
    def _update_temperature(self, states: list[State]) -> None:
        """Determine the group temperature, the limits and the step."""
        self._attr_target_temperature = reduce_attribute(
            states, ATTR_TEMPERATURE, reduce=lambda *data: float(mean(data))
        )
        self._attr_target_temperature_step = reduce_attribute(
            states, ATTR_TARGET_TEMP_STEP, reduce=max
        )
        self._attr_target_temperature_low = reduce_attribute(
            states, ATTR_TARGET_TEMP_LOW, reduce=lambda *data: float(mean(data))
        )
        self._attr_target_temperature_high = reduce_attribute(
            states, ATTR_TARGET_TEMP_HIGH, reduce=lambda *data: float(mean(data))
        )
        self._attr_current_temperature = reduce_attribute(
            states, ATTR_CURRENT_TEMPERATURE, reduce=lambda *data: float(mean(data))
        )

        # The group can only offer the range every member supports, the
        # highest minimum and the lowest maximum.
        min_temp = reduce_attribute(states, ATTR_MIN_TEMP, reduce=max)
        max_temp = reduce_attribute(states, ATTR_MAX_TEMP, reduce=min)

        if min_temp is None or max_temp is None or min_temp >= max_temp:
            # No member reported limits, or the members have no common range.
            min_temp = TemperatureConverter.convert(
                DEFAULT_MIN_TEMP, UnitOfTemperature.CELSIUS, self.temperature_unit
            )
            max_temp = TemperatureConverter.convert(
                DEFAULT_MAX_TEMP, UnitOfTemperature.CELSIUS, self.temperature_unit
            )

        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        # Members that only accept half degrees would report a setpoint back
        # that differs from the one the group shows, so round it here.
        self._attr_target_temperature = self._round_setpoint(
            self._attr_target_temperature
        )
        self._attr_target_temperature_low = self._round_setpoint(
            self._attr_target_temperature_low
        )
        self._attr_target_temperature_high = self._round_setpoint(
            self._attr_target_temperature_high
        )

    def _round_setpoint(self, value: float | None) -> float | None:
        """Round a setpoint to half degrees when the option is enabled."""
        if value is None or not self._decimal_accuracy_to_half:
            return value
        return round_to_half(value)

    @callback
    def _update_hvac(self, states: list[State]) -> None:
        """Determine the group HVAC mode, action and available modes."""
        all_hvac_modes = list(find_state_attributes(states, ATTR_HVAC_MODES))
        if all_hvac_modes:
            self._attr_hvac_modes = _to_hvac_modes(
                mode for modes in all_hvac_modes for mode in modes
            )
        else:
            self._attr_hvac_modes = [HVACMode.OFF]

        # Return the most common HVAC mode (the mode the thermostats are set
        # to), ignoring OFF while at least one member is active. Members that
        # are unavailable or unknown do not report a mode at all.
        usable_states = [
            state
            for state in states
            if state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        ]
        member_modes: list[HVACMode] = []
        for state in usable_states:
            if state.state == HVACMode.OFF:
                continue
            if modes := _to_hvac_modes([state.state]):
                member_modes.append(modes[0])

        if member_modes:
            self._attr_hvac_mode = _most_frequent(member_modes)
        elif usable_states and all(
            state.state == HVACMode.OFF for state in usable_states
        ):
            # All members that know their state are off.
            self._attr_hvac_mode = HVACMode.OFF
        else:
            self._attr_hvac_mode = None

        # Return the most common action, ignoring OFF while a member is active.
        hvac_actions = [
            action
            for state in usable_states
            if (action := _to_hvac_action(state.attributes.get(ATTR_HVAC_ACTION)))
            is not None
        ]
        active_actions = [action for action in hvac_actions if action != HVACAction.OFF]

        if active_actions:
            self._attr_hvac_action = _most_frequent(active_actions)
        elif hvac_actions and all(
            action == HVACAction.OFF for action in hvac_actions
        ):
            self._attr_hvac_action = HVACAction.OFF
        else:
            self._attr_hvac_action = None

    @callback
    def _update_swing(self, states: list[State]) -> None:
        """Determine the available and the current swing modes."""
        all_swing_modes = list(find_state_attributes(states, ATTR_SWING_MODES))
        if all_swing_modes:
            self._attr_swing_modes = _ordered_unique(
                mode for modes in all_swing_modes for mode in modes
            )

        swing_modes = list(find_state_attributes(states, ATTR_SWING_MODE))
        self._attr_swing_mode = _most_frequent(swing_modes) if swing_modes else None

        all_swing_horizontal_modes = list(
            find_state_attributes(states, ATTR_SWING_HORIZONTAL_MODES)
        )
        if all_swing_horizontal_modes:
            self._attr_swing_horizontal_modes = _ordered_unique(
                mode for modes in all_swing_horizontal_modes for mode in modes
            )

        swing_horizontal_modes = list(
            find_state_attributes(states, ATTR_SWING_HORIZONTAL_MODE)
        )
        self._attr_swing_horizontal_mode = (
            _most_frequent(swing_horizontal_modes) if swing_horizontal_modes else None
        )

    @callback
    def _update_fan(self, states: list[State]) -> None:
        """Determine the available and the current fan modes."""
        all_fan_modes = list(find_state_attributes(states, ATTR_FAN_MODES))
        if all_fan_modes:
            self._attr_fan_modes = _ordered_unique(
                mode for modes in all_fan_modes for mode in modes
            )

        fan_modes = list(find_state_attributes(states, ATTR_FAN_MODE))
        self._attr_fan_mode = _most_frequent(fan_modes) if fan_modes else None

    @callback
    def _update_preset(self, states: list[State]) -> None:
        """Determine the available and the current preset modes."""
        all_preset_modes = list(find_state_attributes(states, ATTR_PRESET_MODES))
        if all_preset_modes:
            self._attr_preset_modes = _ordered_unique(
                mode for modes in all_preset_modes for mode in modes
            )

        preset_modes = list(find_state_attributes(states, ATTR_PRESET_MODE))
        self._attr_preset_mode = (
            _most_frequent(preset_modes) if preset_modes else None
        )

    @callback
    def _aggregate_supported_features(self, states: list[State]) -> None:
        """Merge the supported features of all members."""
        features = ClimateEntityFeature(0)
        for support in find_state_attributes(states, ATTR_SUPPORTED_FEATURES):
            if isinstance(support, int):
                features |= ClimateEntityFeature(support)

        # Mask the features with the ones the group can handle, so that we do
        # not break when new features are added to Home Assistant.
        self._attr_supported_features = features & SUPPORTED_FEATURES

    def _entities_supporting(self, feature: ClimateEntityFeature) -> list[str]:
        """Return the entity ids of all members supporting a feature."""
        return [
            entity_id
            for entity_id in self._entity_ids
            if self._member_features.get(entity_id, ClimateEntityFeature(0)) & feature
        ]

    async def _async_forward(
        self,
        service: str,
        data: dict[str, Any],
        feature: ClimateEntityFeature | None = None,
    ) -> None:
        """Forward a service call to the members of the group."""
        entity_ids = self._entity_ids

        if feature is not None:
            # Only call the members that announced support for the feature and
            # fall back to all members when nobody announced it (yet).
            entity_ids = self._entities_supporting(feature) or entity_ids

        _LOGGER.debug("Forwarding %s to %s: %s", service, entity_ids, data)

        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            service,
            {ATTR_ENTITY_ID: entity_ids, **data},
            blocking=True,
            context=self._context,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Forward the set_temperature command to all climate in the climate group."""
        data: dict[str, Any] = {}
        system_unit = self.hass.config.units.temperature_unit

        for key, value in kwargs.items():
            if key in CONVERTIBLE_ATTRIBUTES:
                if self._decimal_accuracy_to_half:
                    # Round in the unit of the group, the members would
                    # round the value on their own otherwise.
                    value = round_to_half(value)
                # Members are called with temperatures in the unit system of
                # Home Assistant, not in the unit of the group.
                data[key] = TemperatureConverter.convert(
                    value, self.temperature_unit, system_unit
                )
            else:
                data[key] = value

        await self._async_forward(SERVICE_SET_TEMPERATURE, data)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Forward the set_hvac_mode command to all climate in the climate group."""
        await self._async_forward(SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: hvac_mode})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Forward the fan_mode to all climate in the climate group."""
        await self._async_forward(
            SERVICE_SET_FAN_MODE,
            {ATTR_FAN_MODE: fan_mode},
            ClimateEntityFeature.FAN_MODE,
        )

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Forward the swing_mode to all climate in the climate group."""
        await self._async_forward(
            SERVICE_SET_SWING_MODE,
            {ATTR_SWING_MODE: swing_mode},
            ClimateEntityFeature.SWING_MODE,
        )

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        """Forward the swing_horizontal_mode to all climate in the climate group."""
        await self._async_forward(
            SERVICE_SET_SWING_HORIZONTAL_MODE,
            {ATTR_SWING_HORIZONTAL_MODE: swing_horizontal_mode},
            ClimateEntityFeature.SWING_HORIZONTAL_MODE,
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Forward the preset_mode to all climate in the climate group."""
        await self._async_forward(
            SERVICE_SET_PRESET_MODE,
            {ATTR_PRESET_MODE: preset_mode},
            ClimateEntityFeature.PRESET_MODE,
        )

    async def async_turn_on(self) -> None:
        """Turn all members on.

        Members that announce support for ``climate.turn_on`` are turned on
        through that service, otherwise the default implementation of
        ``ClimateEntity`` picks the HVAC mode to switch to.
        """
        if self._entities_supporting(ClimateEntityFeature.TURN_ON):
            await self._async_forward(
                SERVICE_TURN_ON, {}, ClimateEntityFeature.TURN_ON
            )
            return

        await super().async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn all members off.

        Members that announce support for ``climate.turn_off`` are turned off
        through that service, otherwise the default implementation of
        ``ClimateEntity`` switches to ``off``.
        """
        if self._entities_supporting(ClimateEntityFeature.TURN_OFF):
            await self._async_forward(
                SERVICE_TURN_OFF, {}, ClimateEntityFeature.TURN_OFF
            )
            return

        await super().async_turn_off()
