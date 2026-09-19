"""Minimal stand-ins for Home Assistant.

Home Assistant 2026.9 requires Python 3.14, so it cannot be installed next to
the Python of this machine. These stand-ins mirror the parts of the Home
Assistant API that the Climate Group integration uses, with the same values and
semantics as Home Assistant core 2026.9.3 (see the notes in ``tests/README.md``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import IntFlag, StrEnum
import sys
import types
from typing import Any

# --------------------------------------------------------------------------
# homeassistant.const
# --------------------------------------------------------------------------


class HVACMode(StrEnum):
    """HVAC mode for climate devices."""

    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    HEAT_COOL = "heat_cool"
    AUTO = "auto"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class HVACAction(StrEnum):
    """HVAC action for climate devices."""

    COOLING = "cooling"
    DEFROSTING = "defrosting"
    DRYING = "drying"
    FAN = "fan"
    HEATING = "heating"
    IDLE = "idle"
    OFF = "off"
    PREHEATING = "preheating"


class ClimateEntityFeature(IntFlag):
    """Supported features of the climate entity."""

    TARGET_TEMPERATURE = 1
    TARGET_TEMPERATURE_RANGE = 2
    TARGET_HUMIDITY = 4
    FAN_MODE = 8
    PRESET_MODE = 16
    SWING_MODE = 32
    TURN_OFF = 128
    TURN_ON = 256
    SWING_HORIZONTAL_MODE = 512


class UnitOfTemperature(StrEnum):
    """Temperature units."""

    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


class Platform(StrEnum):
    """Platforms."""

    CLIMATE = "climate"


class EntityStateAttribute(StrEnum):
    """Entity state attributes."""

    ASSUMED_STATE = "assumed_state"


class EntityCapabilityAttribute(StrEnum):
    """Entity capability attributes."""

    GROUP_ENTITIES = "group_entities"


ATTR_ENTITY_ID = "entity_id"
ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_SUPPORTED_FEATURES = "supported_features"
ATTR_TEMPERATURE = "temperature"
CONF_ENTITIES = "entities"
CONF_NAME = "name"
CONF_TEMPERATURE_UNIT = "temperature_unit"
CONF_UNIQUE_ID = "unique_id"
STATE_UNAVAILABLE = "unavailable"
STATE_UNKNOWN = "unknown"
STATE_ON = "on"
STATE_OFF = "off"
SERVICE_TOGGLE = "toggle"
SERVICE_TURN_OFF = "turn_off"
SERVICE_TURN_ON = "turn_on"

# --------------------------------------------------------------------------
# homeassistant.components.climate.const
# --------------------------------------------------------------------------

ATTR_CURRENT_HUMIDITY = "current_humidity"
ATTR_CURRENT_TEMPERATURE = "current_temperature"
ATTR_FAN_MODES = "fan_modes"
ATTR_FAN_MODE = "fan_mode"
ATTR_PRESET_MODE = "preset_mode"
ATTR_PRESET_MODES = "preset_modes"
ATTR_HUMIDITY = "humidity"
ATTR_MAX_HUMIDITY = "max_humidity"
ATTR_MIN_HUMIDITY = "min_humidity"
ATTR_MAX_TEMP = "max_temp"
ATTR_MIN_TEMP = "min_temp"
ATTR_HVAC_ACTION = "hvac_action"
ATTR_HVAC_MODES = "hvac_modes"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_SWING_MODES = "swing_modes"
ATTR_SWING_MODE = "swing_mode"
ATTR_SWING_HORIZONTAL_MODE = "swing_horizontal_mode"
ATTR_SWING_HORIZONTAL_MODES = "swing_horizontal_modes"
ATTR_TARGET_HUMIDITY_STEP = "target_humidity_step"
ATTR_TARGET_TEMP_HIGH = "target_temp_high"
ATTR_TARGET_TEMP_LOW = "target_temp_low"
ATTR_TARGET_TEMP_STEP = "target_temp_step"

DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 35
DEFAULT_MIN_HUMIDITY = 30
DEFAULT_MAX_HUMIDITY = 99

CLIMATE_DOMAIN = "climate"

SERVICE_SET_FAN_MODE = "set_fan_mode"
SERVICE_SET_HVAC_MODE = "set_hvac_mode"
SERVICE_SET_HUMIDITY = "set_humidity"
SERVICE_SET_PRESET_MODE = "set_preset_mode"
SERVICE_SET_SWING_HORIZONTAL_MODE = "set_swing_horizontal_mode"
SERVICE_SET_SWING_MODE = "set_swing_mode"
SERVICE_SET_TEMPERATURE = "set_temperature"


# --------------------------------------------------------------------------
# homeassistant.util.unit_conversion
# --------------------------------------------------------------------------

_TO_KELVIN: dict[str, Callable[[float], float]] = {
    UnitOfTemperature.CELSIUS: lambda value: value + 273.15,
    UnitOfTemperature.FAHRENHEIT: lambda value: (value + 459.67) * 5 / 9,
    UnitOfTemperature.KELVIN: lambda value: value,
}
_FROM_KELVIN: dict[str, Callable[[float], float]] = {
    UnitOfTemperature.CELSIUS: lambda value: value - 273.15,
    UnitOfTemperature.FAHRENHEIT: lambda value: value * 9 / 5 - 459.67,
    UnitOfTemperature.KELVIN: lambda value: value,
}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature between two units."""
    if from_unit == to_unit:
        return value
    return round(
        _FROM_KELVIN[to_unit](_TO_KELVIN[from_unit](float(value))), 6
    )


class TemperatureConverter:
    """Conversions between temperature units."""

    @staticmethod
    def convert(value: float, from_unit: str | None, to_unit: str) -> float:
        """Convert a temperature between two units."""
        return convert_temperature(value, str(from_unit), str(to_unit))


# --------------------------------------------------------------------------
# homeassistant.core
# --------------------------------------------------------------------------


def callback(func: Callable) -> Callable:
    """Mark a function as a callback."""
    return func


@dataclass
class State:
    """Representation of a state."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        """Return the domain of the entity."""
        return self.entity_id.partition(".")[0]


class _States:
    """State machine stand-in."""

    def __init__(self) -> None:
        self._states: dict[str, State] = {}

    def get(self, entity_id: str) -> State | None:
        """Return a state."""
        return self._states.get(entity_id)

    def set(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> None:
        """Set a state."""
        self._states[entity_id] = State(entity_id, state, attributes or {})

    def remove(self, entity_id: str) -> None:
        """Remove a state."""
        self._states.pop(entity_id, None)

    def async_entity_ids(self, domain: str | None = None) -> list[str]:
        """Return all entity ids, optionally of one domain."""
        if domain is None:
            return list(self._states)
        return [
            entity_id
            for entity_id in self._states
            if entity_id.partition(".")[0] == domain
        ]


class _Services:
    """Service registry stand-in that records the calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def async_call(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        blocking: bool = False,
        context: Any = None,
        target: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> None:
        """Record a service call."""
        self.calls.append(
            {
                "domain": domain,
                "service": service,
                "data": dict(service_data or {}),
                "blocking": blocking,
                "context": context,
            }
        )

    def last(self) -> dict[str, Any]:
        """Return the last recorded call."""
        return self.calls[-1]

    def called(self, domain: str, service: str) -> list[dict[str, Any]]:
        """Return all calls of a service."""
        return [
            call
            for call in self.calls
            if call["domain"] == domain and call["service"] == service
        ]


class _UnitSystem:
    """Unit system stand-in."""

    def __init__(self, temperature_unit: str = UnitOfTemperature.CELSIUS) -> None:
        self.temperature_unit = temperature_unit


class _Config:
    """Config stand-in."""

    def __init__(self, temperature_unit: str = UnitOfTemperature.CELSIUS) -> None:
        self.units = _UnitSystem(temperature_unit)


class _ConfigEntries:
    """Config entries manager stand-in."""

    def __init__(self) -> None:
        self.forwarded: list[tuple[str, list[str]]] = []
        self.unloaded: list[tuple[str, list[str]]] = []

    async def async_forward_entry_setups(self, entry: Any, platforms: list) -> None:
        """Record the forwarded platforms."""
        self.forwarded.append((entry.entry_id, [str(platform) for platform in platforms]))

    async def async_unload_platforms(self, entry: Any, platforms: list) -> bool:
        """Record the unloaded platforms."""
        self.unloaded.append((entry.entry_id, [str(platform) for platform in platforms]))
        return True


_STATE_LISTENERS: list[tuple[list[str], Callable]] = []


def async_track_state_change_event(
    hass: Any, entity_ids: list[str], action: Callable
) -> Callable[[], None]:
    """Track state change events of the given entities."""
    listener = (list(entity_ids), action)
    _STATE_LISTENERS.append(listener)

    def remove() -> None:
        if listener in _STATE_LISTENERS:
            _STATE_LISTENERS.remove(listener)

    return remove


def fire_state_change(entity_id: str) -> None:
    """Notify all registered listeners about a state change."""
    for entity_ids, action in list(_STATE_LISTENERS):
        if entity_id in entity_ids:
            action(
                types.SimpleNamespace(
                    data={
                        "entity_id": entity_id,
                        "new_state": _HASS.states.get(entity_id),
                    },
                    context=types.SimpleNamespace(id="test"),
                )
            )


class HomeAssistant:
    """Home Assistant stand-in."""

    def __init__(self, temperature_unit: str = UnitOfTemperature.CELSIUS) -> None:
        self.states = _States()
        self.services = _Services()
        self.config = _Config(temperature_unit)
        self.config_entries = _ConfigEntries()
        self.data: dict[str, Any] = {}
        self.is_running = True

    async def async_add_executor_job(self, func: Callable, *args: Any) -> Any:
        """Run a job in the executor (synchronously here)."""
        return func(*args)


_HASS: HomeAssistant | None = None


def get_hass() -> HomeAssistant:
    """Return the managed Home Assistant stand-in."""
    global _HASS
    if _HASS is None:
        _HASS = HomeAssistant()
    return _HASS


def reset_hass(temperature_unit: str = UnitOfTemperature.CELSIUS) -> HomeAssistant:
    """Return a fresh Home Assistant stand-in."""
    global _HASS
    _STATE_LISTENERS.clear()
    _HASS = HomeAssistant(temperature_unit)
    return _HASS


# --------------------------------------------------------------------------
# homeassistant.helpers.group.util
# --------------------------------------------------------------------------


def find_state_attributes(states: list[State], key: str) -> Iterator[Any]:
    """Find attributes with matching key from states."""
    for state in states:
        if (value := state.attributes.get(key)) is not None:
            yield value


def find_state(states: list[State]) -> Iterator[Any]:
    """Find state from states."""
    for state in states:
        yield state.state


def mean_int(*args: Any) -> int:
    """Return the mean of the supplied values."""
    return int(sum(args) / len(args))


def states_equal(states: list[State]) -> bool:
    """Return True if all states are equal."""
    return _values_equal(find_state(states))


def _values_equal(values: Iterator[Any]) -> bool:
    """Return True if all values are equal."""
    from itertools import groupby

    grp = groupby(values)
    return bool(next(grp, True) and not next(grp, False))


def reduce_attribute(
    states: list[State],
    key: str,
    default: Any | None = None,
    reduce: Callable[..., Any] = mean_int,
) -> Any:
    """Find the reduced value of an attribute of all states."""
    attrs = list(find_state_attributes(states, key))

    if not attrs:
        return default

    if len(attrs) == 1:
        return attrs[0]

    return reduce(*attrs)


# --------------------------------------------------------------------------
# homeassistant.components.group.entity
# --------------------------------------------------------------------------


class GroupEntity:
    """Representation of a group of entities."""

    _attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        for entity_id in self._entity_ids:
            if (state := self.hass.states.get(entity_id)) is None:
                continue
            self.async_update_supported_features(entity_id, state)

        def async_state_changed_listener(event: Any) -> None:
            """Handle child updates."""
            self.async_update_supported_features(
                event.data["entity_id"], event.data["new_state"]
            )
            self.async_defer_or_update_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._entity_ids, async_state_changed_listener
            )
        )

    def async_on_remove(self, func: Callable[[], None]) -> None:
        """Register a cleanup function."""
        self._cleanups.append(func)

    @callback
    def async_defer_or_update_ha_state(self) -> None:
        """Only update once at start."""
        if not self.hass.is_running:
            return

        self.async_update_group_state()
        self.async_write_ha_state()

    @callback
    def async_write_ha_state(self) -> None:
        """Write the state (recorded here)."""
        self.state_writes += 1

    @callback
    def async_set_context(self, context: Any) -> None:
        """Set the context."""

    @callback
    def _update_assumed_state_from_members(self) -> None:
        """Update assumed_state based on member entities."""
        self._attr_assumed_state = False
        for entity_id in self._entity_ids:
            if (state := self.hass.states.get(entity_id)) is None:
                continue
            if state.attributes.get(EntityStateAttribute.ASSUMED_STATE):
                self._attr_assumed_state = True
                return

    @callback
    def async_update_supported_features(self, entity_id: str, new_state: State | None) -> None:
        """Update dictionaries with supported features."""

    @callback
    def async_update_group_state(self) -> None:
        """Abstract method to update the entity."""
        raise NotImplementedError


# --------------------------------------------------------------------------
# homeassistant.helpers.entity_platform
# --------------------------------------------------------------------------

AddEntitiesCallback = Callable[..., None]
AddConfigEntryEntitiesCallback = Callable[..., None]


# --------------------------------------------------------------------------
# homeassistant.helpers.config_validation
# --------------------------------------------------------------------------

import voluptuous as vol  # noqa: E402

PLATFORM_SCHEMA = vol.Schema(
    {vol.Optional("platform"): str}, extra=vol.ALLOW_EXTRA
)
PLATFORM_SCHEMA_BASE = PLATFORM_SCHEMA


def string(value: Any) -> str:
    """Validate a string."""
    return str(value)


def boolean(value: Any) -> bool:
    """Validate a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "yes", "on", "1"):
            return True
        if value.lower() in ("false", "no", "off", "0"):
            return False
    raise vol.Invalid(f"Expected a boolean, got {value!r}")


def entity_id(value: Any) -> str:
    """Validate an entity id."""
    value = string(value).lower()
    if "." not in value:
        raise vol.Invalid(f"Entity ID {value} is not valid")
    return value


def entities_domain(domain: str | list[str]) -> Callable[[Any], list[str]]:
    """Validate a list of entity ids of one or more domains."""
    domains = [domain] if isinstance(domain, str) else domain

    def validator(value: Any) -> list[str]:
        value = ensure_list_of_entity_ids(value)
        for entity in value:
            if entity.partition(".")[0] not in domains:
                raise vol.Invalid(
                    f"Entity {entity} is not valid for domain {domain}"
                )
        return value

    return validator


def ensure_list_of_entity_ids(value: Any) -> list[str]:
    """Validate one or more entity ids."""
    if isinstance(value, str):
        value = [value]
    return [entity_id(item) for item in value]


def temperature_unit(value: Any) -> str:
    """Validate and transform temperature unit."""
    value = str(value).upper()
    if value == "C":
        return UnitOfTemperature.CELSIUS
    if value == "F":
        return UnitOfTemperature.FAHRENHEIT
    raise vol.Invalid("invalid temperature unit (expected C or F)")


# --------------------------------------------------------------------------
# homeassistant.helpers.selector
# --------------------------------------------------------------------------


class SelectSelectorMode(StrEnum):
    """Possible modes for a select selector."""

    LIST = "list"
    DROPDOWN = "dropdown"


class EntitySelectorConfig(dict):
    """Config of an entity selector."""


class SelectSelectorConfig(dict):
    """Config of a select selector."""


class BooleanSelectorConfig(dict):
    """Config of a boolean selector."""


class _Selector:
    """Base selector."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = dict(config or {})

    def __call__(self, value: Any) -> Any:
        """Validate the selected value (Home Assistant validates it against the entity registry)."""
        return value

    def serialize(self) -> dict[str, Any]:
        """Serialize the selector."""
        return {"type": self.selector_type, "config": self.config}


class EntitySelector(_Selector):
    """Selector of one or more entities."""

    selector_type = "entity"

    def __init__(self, config: EntitySelectorConfig | None = None) -> None:
        super().__init__(config)


class SelectSelector(_Selector):
    """Selector of a value from a list."""

    selector_type = "select"


class BooleanSelector(_Selector):
    """Selector of a boolean."""

    selector_type = "boolean"


# --------------------------------------------------------------------------
# homeassistant.helpers.entity_registry / entity platform modules
# --------------------------------------------------------------------------


@dataclass
class RegistryEntry:
    """Entity registry entry."""

    entity_id: str
    domain: str
    config_entry_id: str | None = None
    disabled_by: str | None = None
    unique_id: str | None = None


class _EntityRegistry:
    """Entity registry stand-in."""

    def __init__(self) -> None:
        self.entries: dict[str, RegistryEntry] = {}

    def async_get(self, entity_id: str) -> RegistryEntry | None:
        """Return an entry."""
        return self.entries.get(entity_id)

    def async_entries_for_config_entry(self, entry_id: str) -> list[RegistryEntry]:
        """Return the entries of a config entry."""
        return [
            entry
            for entry in self.entries.values()
            if entry.config_entry_id == entry_id
        ]


_REGISTRY = _EntityRegistry()


def async_get_registry(hass: Any = None) -> _EntityRegistry:
    """Return the registry."""
    return _REGISTRY


def async_entries_for_config_entry(registry: _EntityRegistry, entry_id: str) -> list[RegistryEntry]:
    """Return the entries of a config entry."""
    return registry.async_entries_for_config_entry(entry_id)


# --------------------------------------------------------------------------
# homeassistant.config_entries
# --------------------------------------------------------------------------


@dataclass
class ConfigEntry:
    """Config entry stand-in."""

    entry_id: str = "entry-id"
    domain: str = "climate_group"
    title: str = "Climate Group"
    data: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


class AbortFlow(Exception):
    """Abort a flow."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ConfigFlowResult(dict):
    """Result of a flow step."""


class _FlowBase:
    """Shared behaviour of config and options flows."""

    def __init__(self, config_entry: ConfigEntry | None = None) -> None:
        self.hass = get_hass()
        self._config_entry = config_entry

    @property
    def config_entry(self) -> ConfigEntry | None:
        """Return the config entry of an options flow."""
        return self._config_entry

    def _async_current_entries(self, include_ignore: bool = False) -> list[ConfigEntry]:
        """Return the existing entries."""
        return list(entries())

    def _async_abort_entries_match(self, match_dict: dict[str, Any] | None = None) -> None:
        """Abort if another entry matches all data."""
        current = [
            entry
            for entry in self._async_current_entries()
            if entry.entry_id != (
                self._config_entry.entry_id if self._config_entry else None
            )
        ]
        for entry in current:
            for key, value in (match_dict or {}).items():
                if (key, value) not in entry.options.items() and (
                    key,
                    value,
                ) not in entry.data.items():
                    break
            else:
                raise AbortFlow("already_configured")

    def async_create_entry(
        self, *, title: str | None = None, data: dict[str, Any], **kwargs: Any
    ) -> ConfigFlowResult:
        """Finish the flow."""
        return ConfigFlowResult(
            type="create_entry", title=title, data=data, options=data
        )

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any = None,
        errors: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> ConfigFlowResult:
        """Show a form."""
        return ConfigFlowResult(
            type="form",
            step_id=step_id,
            data_schema=data_schema,
            errors=errors or {},
        )


class ConfigFlow(_FlowBase):
    """Config flow stand-in."""

    def __init_subclass__(cls, domain: str | None = None, **kwargs: Any) -> None:
        """Register the domain of the flow."""
        super().__init_subclass__(**kwargs)
        cls.domain = domain


class OptionsFlow(_FlowBase):
    """Options flow stand-in."""


class OptionsFlowWithReload(OptionsFlow):
    """Options flow that reloads the entry."""

    automatic_reload = True


_ENTRIES: list[ConfigEntry] = []


def entries() -> list[ConfigEntry]:
    """Return all known config entries."""
    return _ENTRIES


def add_entry(entry: ConfigEntry) -> ConfigEntry:
    """Register a config entry."""
    _ENTRIES.append(entry)
    return entry


def reset_entries() -> None:
    """Forget all config entries."""
    _ENTRIES.clear()


# --------------------------------------------------------------------------
# module registration
# --------------------------------------------------------------------------


def _register(name: str, package: bool, **attrs: Any) -> types.ModuleType:
    """Register a module in sys.modules and on its parent."""
    module = types.ModuleType(name)
    if package:
        module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module

    parent_name, _, child_name = name.rpartition(".")
    if parent_name and parent_name in sys.modules:
        setattr(sys.modules[parent_name], child_name, module)
    return module


def install() -> HomeAssistant:
    """Install all stand-in modules and return a Home Assistant instance."""
    _register("homeassistant", package=True)
    _register("homeassistant.components", package=True)
    _register("homeassistant.helpers", package=True)
    _register("homeassistant.util", package=True)

    core = _register(
        "homeassistant.core",
        package=False,
        HomeAssistant=HomeAssistant,
        State=State,
        callback=callback,
        Event=types.SimpleNamespace,
        EventStateChangedData=dict,
        Context=types.SimpleNamespace,
    )
    core.__dict__["State"] = State

    _register(
        "homeassistant.const",
        package=False,
        ATTR_ENTITY_ID=ATTR_ENTITY_ID,
        ATTR_FRIENDLY_NAME=ATTR_FRIENDLY_NAME,
        ATTR_SUPPORTED_FEATURES=ATTR_SUPPORTED_FEATURES,
        ATTR_TEMPERATURE=ATTR_TEMPERATURE,
        CONF_ENTITIES=CONF_ENTITIES,
        CONF_NAME=CONF_NAME,
        CONF_TEMPERATURE_UNIT=CONF_TEMPERATURE_UNIT,
        CONF_UNIQUE_ID=CONF_UNIQUE_ID,
        STATE_OFF=STATE_OFF,
        STATE_ON=STATE_ON,
        STATE_UNAVAILABLE=STATE_UNAVAILABLE,
        STATE_UNKNOWN=STATE_UNKNOWN,
        SERVICE_TOGGLE=SERVICE_TOGGLE,
        SERVICE_TURN_OFF=SERVICE_TURN_OFF,
        SERVICE_TURN_ON=SERVICE_TURN_ON,
        EntityCapabilityAttribute=EntityCapabilityAttribute,
        EntityStateAttribute=EntityStateAttribute,
        Platform=Platform,
        UnitOfTemperature=UnitOfTemperature,
    )

    _register(
        "homeassistant.helpers.typing",
        package=False,
        ConfigType=dict,
        DiscoveryInfoType=dict,
    )

    _register(
        "homeassistant.util.unit_conversion",
        package=False,
        TemperatureConverter=TemperatureConverter,
    )

    config_validation = _register(
        "homeassistant.helpers.config_validation",
        package=False,
        PLATFORM_SCHEMA=PLATFORM_SCHEMA,
        PLATFORM_SCHEMA_BASE=PLATFORM_SCHEMA_BASE,
        boolean=boolean,
        string=string,
        entity_id=entity_id,
        entities_domain=entities_domain,
        temperature_unit=temperature_unit,
    )

    _register(
        "homeassistant.helpers.event",
        package=False,
        async_track_state_change_event=async_track_state_change_event,
    )

    _register(
        "homeassistant.helpers.entity_platform",
        package=False,
        AddEntitiesCallback=AddEntitiesCallback,
        AddConfigEntryEntitiesCallback=AddConfigEntryEntitiesCallback,
    )

    _register(
        "homeassistant.helpers.selector",
        package=False,
        BooleanSelector=BooleanSelector,
        BooleanSelectorConfig=BooleanSelectorConfig,
        EntitySelector=EntitySelector,
        EntitySelectorConfig=EntitySelectorConfig,
        SelectSelector=SelectSelector,
        SelectSelectorConfig=SelectSelectorConfig,
        SelectSelectorMode=SelectSelectorMode,
    )

    entity_registry = _register(
        "homeassistant.helpers.entity_registry",
        package=False,
        async_get=async_get_registry,
        async_entries_for_config_entry=async_entries_for_config_entry,
    )
    entity_registry.__dict__["EntityRegistryEntry"] = RegistryEntry

    config_entries = _register(
        "homeassistant.config_entries",
        package=False,
        AbortFlow=AbortFlow,
        ConfigEntry=ConfigEntry,
        ConfigFlow=ConfigFlow,
        ConfigFlowResult=ConfigFlowResult,
        OptionsFlow=OptionsFlow,
        OptionsFlowWithReload=OptionsFlowWithReload,
    )
    config_entries.__dict__["add_entry"] = add_entry

    group_util = _register(
        "homeassistant.components.group.util",
        package=False,
        find_state=find_state,
        find_state_attributes=find_state_attributes,
        mean_int=mean_int,
        reduce_attribute=reduce_attribute,
        states_equal=states_equal,
    )
    del group_util

    _register(
        "homeassistant.components.group.entity",
        package=False,
        GroupEntity=GroupEntity,
    )
    _register("homeassistant.components.group", package=True, util=sys.modules["homeassistant.components.group.util"])

    climate_const = _register(
        "homeassistant.components.climate.const",
        package=False,
        ATTR_CURRENT_HUMIDITY=ATTR_CURRENT_HUMIDITY,
        ATTR_CURRENT_TEMPERATURE=ATTR_CURRENT_TEMPERATURE,
        ATTR_FAN_MODE=ATTR_FAN_MODE,
        ATTR_FAN_MODES=ATTR_FAN_MODES,
        ATTR_HUMIDITY=ATTR_HUMIDITY,
        ATTR_HVAC_ACTION=ATTR_HVAC_ACTION,
        ATTR_HVAC_MODE=ATTR_HVAC_MODE,
        ATTR_HVAC_MODES=ATTR_HVAC_MODES,
        ATTR_MAX_HUMIDITY=ATTR_MAX_HUMIDITY,
        ATTR_MAX_TEMP=ATTR_MAX_TEMP,
        ATTR_MIN_HUMIDITY=ATTR_MIN_HUMIDITY,
        ATTR_MIN_TEMP=ATTR_MIN_TEMP,
        ATTR_PRESET_MODE=ATTR_PRESET_MODE,
        ATTR_PRESET_MODES=ATTR_PRESET_MODES,
        ATTR_SWING_HORIZONTAL_MODE=ATTR_SWING_HORIZONTAL_MODE,
        ATTR_SWING_HORIZONTAL_MODES=ATTR_SWING_HORIZONTAL_MODES,
        ATTR_SWING_MODE=ATTR_SWING_MODE,
        ATTR_SWING_MODES=ATTR_SWING_MODES,
        ATTR_TARGET_HUMIDITY_STEP=ATTR_TARGET_HUMIDITY_STEP,
        ATTR_TARGET_TEMP_HIGH=ATTR_TARGET_TEMP_HIGH,
        ATTR_TARGET_TEMP_LOW=ATTR_TARGET_TEMP_LOW,
        ATTR_TARGET_TEMP_STEP=ATTR_TARGET_TEMP_STEP,
        DEFAULT_MAX_HUMIDITY=DEFAULT_MAX_HUMIDITY,
        DEFAULT_MAX_TEMP=DEFAULT_MAX_TEMP,
        DEFAULT_MIN_HUMIDITY=DEFAULT_MIN_HUMIDITY,
        DEFAULT_MIN_TEMP=DEFAULT_MIN_TEMP,
        DOMAIN=CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE=SERVICE_SET_FAN_MODE,
        SERVICE_SET_HVAC_MODE=SERVICE_SET_HVAC_MODE,
        SERVICE_SET_HUMIDITY=SERVICE_SET_HUMIDITY,
        SERVICE_SET_PRESET_MODE=SERVICE_SET_PRESET_MODE,
        SERVICE_SET_SWING_HORIZONTAL_MODE=SERVICE_SET_SWING_HORIZONTAL_MODE,
        SERVICE_SET_SWING_MODE=SERVICE_SET_SWING_MODE,
        SERVICE_SET_TEMPERATURE=SERVICE_SET_TEMPERATURE,
        ClimateEntityFeature=ClimateEntityFeature,
        HVACAction=HVACAction,
        HVACMode=HVACMode,
    )
    del climate_const

    _register(
        "homeassistant.components.climate",
        package=True,
        PLATFORM_SCHEMA=PLATFORM_SCHEMA,
        ClimateEntity=ClimateEntity,
        ClimateEntityFeature=ClimateEntityFeature,
        HVACAction=HVACAction,
        HVACMode=HVACMode,
        const=sys.modules["homeassistant.components.climate.const"],
    )

    sys.modules["homeassistant.components.climate"].__dict__["DOMAIN"] = CLIMATE_DOMAIN

    return get_hass()


class ClimateEntity:
    """Climate entity stand-in with the API the group uses."""

    _attr_available = True
    _attr_assumed_state = False
    _attr_should_poll = True
    _attr_current_temperature = None
    _attr_fan_mode = None
    _attr_fan_modes = None
    _attr_hvac_action = None
    _attr_hvac_mode = None
    _attr_hvac_modes = []
    _attr_max_temp = None
    _attr_min_temp = None
    _attr_preset_mode = None
    _attr_preset_modes = None
    _attr_supported_features = ClimateEntityFeature(0)
    _attr_swing_horizontal_mode = None
    _attr_swing_horizontal_modes = None
    _attr_swing_mode = None
    _attr_swing_modes = None
    _attr_target_temperature = None
    _attr_target_temperature_high = None
    _attr_target_temperature_low = None
    _attr_target_temperature_step = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    state_writes = 0
    _cleanups: list[Callable] = []
    _context = None

    @property
    def state(self) -> str | None:
        """Return the current state."""
        return self._attr_hvac_mode.value if self._attr_hvac_mode else None

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._attr_available

    @property
    def assumed_state(self) -> bool:
        """Return True if the state is assumed."""
        return self._attr_assumed_state

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return self._attr_name

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the entity."""
        return self._attr_unique_id

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return self._attr_temperature_unit

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the supported features."""
        return self._attr_supported_features

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        return self._attr_hvac_mode

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the available HVAC modes."""
        return self._attr_hvac_modes

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        return self._attr_hvac_action

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._attr_current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._attr_target_temperature

    @property
    def target_temperature_step(self) -> float | None:
        """Return the target temperature step."""
        return self._attr_target_temperature_step

    @property
    def target_temperature_high(self) -> float | None:
        """Return the upper target temperature."""
        return self._attr_target_temperature_high

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lower target temperature."""
        return self._attr_target_temperature_low

    @property
    def fan_mode(self) -> str | None:
        """Return the fan mode."""
        return self._attr_fan_mode

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the available fan modes."""
        return self._attr_fan_modes

    @property
    def preset_mode(self) -> str | None:
        """Return the preset mode."""
        return self._attr_preset_mode

    @property
    def preset_modes(self) -> list[str] | None:
        """Return the available preset modes."""
        return self._attr_preset_modes

    @property
    def swing_mode(self) -> str | None:
        """Return the swing mode."""
        return self._attr_swing_mode

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the available swing modes."""
        return self._attr_swing_modes

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Return the horizontal swing mode."""
        return self._attr_swing_horizontal_mode

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return the available horizontal swing modes."""
        return self._attr_swing_horizontal_modes

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if not hasattr(self, "_attr_min_temp") or self._attr_min_temp is None:
            return convert_temperature(
                DEFAULT_MIN_TEMP, UnitOfTemperature.CELSIUS, self.temperature_unit
            )
        return self._attr_min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if not hasattr(self, "_attr_max_temp") or self._attr_max_temp is None:
            return convert_temperature(
                DEFAULT_MAX_TEMP, UnitOfTemperature.CELSIUS, self.temperature_unit
            )
        return self._attr_max_temp

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if len(self.hvac_modes) == 2 and HVACMode.OFF in self.hvac_modes:
            for mode in self.hvac_modes:
                if mode != HVACMode.OFF:
                    await self.async_set_hvac_mode(mode)
                    return

        for mode in (HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL):
            if mode not in self.hvac_modes:
                continue
            await self.async_set_hvac_mode(mode)
            return

        raise NotImplementedError

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if HVACMode.OFF in self.hvac_modes:
            await self.async_set_hvac_mode(HVACMode.OFF)
            return

        raise NotImplementedError

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        raise NotImplementedError

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a temperature."""
        raise NotImplementedError


def climate_entity_class() -> type:
    """Return the ClimateEntity class."""
    return ClimateEntity
