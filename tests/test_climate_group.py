"""Tests for the Climate Group integration.

The tests run against the Home Assistant stand-ins in ``tests/ha_stub.py``,
so they need no Home Assistant installation:

    python tests/test_climate_group.py
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ha_stub  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "climate_group"

hass = ha_stub.install()

# --------------------------------------------------------------------------
# load the integration
# --------------------------------------------------------------------------


def _load_integration() -> types.ModuleType:
    """Load custom_components.climate_group as a package."""
    parent = types.ModuleType("custom_components")
    parent.__path__ = [str(ROOT / "custom_components")]
    sys.modules["custom_components"] = parent

    spec = importlib.util.spec_from_file_location(
        "custom_components.climate_group",
        PKG_DIR / "__init__.py",
        submodule_search_locations=[str(PKG_DIR)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["custom_components.climate_group"] = module
    spec.loader.exec_module(module)
    return module


integration = _load_integration()
import custom_components.climate_group.climate as climate  # noqa: E402
import custom_components.climate_group.config_flow as config_flow  # noqa: E402
import custom_components.climate_group.const as const  # noqa: E402

ClimateEntityFeature = ha_stub.ClimateEntityFeature
HVACAction = ha_stub.HVACAction
HVACMode = ha_stub.HVACMode
UnitOfTemperature = ha_stub.UnitOfTemperature
ConfigEntry = ha_stub.ConfigEntry

CELSIUS = UnitOfTemperature.CELSIUS
FAHRENHEIT = UnitOfTemperature.FAHRENHEIT

BASE_FEATURES = int(
    ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
)

# --------------------------------------------------------------------------
# tiny test runner
# --------------------------------------------------------------------------

CHECKS = 0
FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    """Check a condition."""
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(message)


def equal(actual: Any, expected: Any, message: str) -> None:
    """Check that two values are equal."""
    check(actual == expected, f"{message}: expected {expected!r}, got {actual!r}")


def close(actual: Any, expected: float, message: str, tolerance: float = 0.001) -> None:
    """Check that two numbers are close."""
    check(
        actual is not None and abs(float(actual) - expected) < tolerance,
        f"{message}: expected ~{expected}, got {actual!r}",
    )


def run(coro: Any) -> Any:
    """Run a coroutine."""
    return asyncio.run(coro)


def schema_defaults(schema: Any) -> dict[str, Any]:
    """Return the values a form schema is prefilled with."""
    return schema({})


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def climate_state(
    entity_id: str,
    state: str,
    *,
    features: int = BASE_FEATURES,
    **attributes: Any,
) -> None:
    """Add a member climate entity to the state machine."""
    attributes["supported_features"] = features
    hass.states.set(entity_id, state, attributes)


def make_group(
    entity_ids: list[str],
    *,
    name: str = "Test Group",
    unit: str = CELSIUS,
    instance: ha_stub.HomeAssistant | None = None,
    with_features: bool = False,
) -> Any:
    """Create a climate group that uses the current Home Assistant stand-in."""
    entity = climate.ClimateGroup("uid", name, entity_ids, unit)
    entity.hass = instance or hass
    if with_features:
        # Home Assistant calls this when the entity is added.
        run(entity.async_added_to_hass())
    entity.async_update_group_state()
    return entity


def only_call(*, domain: str = "climate", service: str) -> dict[str, Any]:
    """Return the single recorded service call of a service."""
    calls = hass.services.called(domain, service)
    assert len(calls) == 1, f"expected 1 call of {domain}.{service}, got {len(calls)}"
    return calls[0]


# --------------------------------------------------------------------------
# state aggregation
# --------------------------------------------------------------------------


def test_majority_state_and_attributes() -> None:
    """The group reports the most common state and the mean temperatures."""
    global hass
    hass = ha_stub.reset_hass()
    for entity_id, mode in zip(
        ["climate.a", "climate.b", "climate.c"], ["heat", "heat", "cool"]
    ):
        climate_state(
            entity_id,
            mode,
            temperature=21.0,
            current_temperature=20.0,
            min_temp=7,
            max_temp=35,
            target_temp_step=0.5,
            hvac_modes=["off", "heat", "cool", "fan_only"],
            hvac_action="heating",
            fan_modes=["low", "high"],
            fan_mode="low",
            preset_modes=["eco", "comfort"],
            preset_mode="eco",
            swing_modes=["on", "off"],
            swing_mode="off",
            swing_horizontal_modes=["on", "off"],
            swing_horizontal_mode="on",
        )

    group = make_group(["climate.a", "climate.b", "climate.c"])

    equal(group.hvac_mode, HVACMode.HEAT, "most common hvac mode")
    equal(group.state, "heat", "state")
    equal(
        [str(mode) for mode in group.hvac_modes],
        ["off", "heat", "cool", "fan_only"],
        "hvac modes, off first",
    )
    equal(group.hvac_action, HVACAction.HEATING, "hvac action")
    equal(group.target_temperature, 21.0, "target temperature")
    equal(group.current_temperature, 20.0, "current temperature")
    equal(group.min_temp, 7, "min temp")
    equal(group.max_temp, 35, "max temp")
    equal(group.target_temperature_step, 0.5, "target temperature step")
    equal(group.fan_modes, ["low", "high"], "fan modes")
    equal(group.fan_mode, "low", "fan mode")
    equal(group.preset_modes, ["eco", "comfort"], "preset modes")
    equal(group.preset_mode, "eco", "preset mode")
    equal(group.swing_modes, ["on", "off"], "swing modes")
    equal(group.swing_mode, "off", "swing mode")
    equal(group.swing_horizontal_modes, ["on", "off"], "horizontal swing modes")
    equal(group.swing_horizontal_mode, "on", "horizontal swing mode")
    equal(group.available, True, "available")
    equal(group.assumed_state, True, "assumed while the members disagree")

    # Once all members agree, the state is no longer assumed.
    climate_state(
        "climate.c",
        "heat",
        temperature=21.0,
        current_temperature=20.0,
        min_temp=7,
        max_temp=35,
        hvac_modes=["off", "heat", "cool", "fan_only"],
        hvac_action="heating",
    )
    group.async_update_group_state()
    equal(group.assumed_state, False, "not assumed when the members agree")
    equal(group.hvac_mode, HVACMode.HEAT, "hvac mode")


def test_all_off() -> None:
    """All members off means the group is off."""
    global hass
    hass = ha_stub.reset_hass()
    for entity_id in ["climate.a", "climate.b"]:
        climate_state(
            entity_id, "off", hvac_modes=["off", "heat"], hvac_action="off"
        )

    group = make_group(["climate.a", "climate.b"])

    equal(group.hvac_mode, HVACMode.OFF, "hvac mode off")
    equal(group.hvac_action, HVACAction.OFF, "hvac action off")
    equal(group.state, "off", "state")


def test_unavailable_member_is_ignored() -> None:
    """An unavailable member does not break the group state."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "off", hvac_modes=["off", "heat"])
    hass.states.set("climate.b", "unavailable", {})
    hass.states.set("climate.missing", "unavailable", {})

    group = make_group(["climate.a", "climate.b"])

    equal(group.hvac_mode, HVACMode.OFF, "hvac mode from the members left")
    equal(group.state, "off", "state")
    equal(group.available, True, "still available")
    equal(group.assumed_state, True, "assumed, members disagree")

    group = make_group(["climate.b", "climate.missing"])
    equal(group.hvac_mode, None, "no hvac mode without usable members")
    equal(group.state, None, "no state without usable members")
    equal(group.available, False, "unavailable when all members are unavailable")

    group = make_group([])
    equal(group.hvac_mode, None, "no hvac mode without members")
    equal(group.available, False, "unavailable without members")


def test_assumed_state() -> None:
    """The group is assumed when members disagree or assume their own state."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", hvac_modes=["off", "heat"])
    climate_state("climate.b", "cool", hvac_modes=["off", "cool"])

    group = make_group(["climate.a", "climate.b"])
    equal(group.assumed_state, True, "assumed when members disagree")

    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", hvac_modes=["off", "heat"], assumed_state=True)
    climate_state("climate.b", "heat", hvac_modes=["off", "heat"])

    group = make_group(["climate.a", "climate.b"])
    equal(group.assumed_state, True, "assumed when a member assumes its state")


def test_temperature_limits() -> None:
    """The group offers the range every member supports."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", temperature=20.0, min_temp=7, max_temp=35)
    climate_state("climate.b", "heat", temperature=24.0, min_temp=16, max_temp=30)

    group = make_group(["climate.a", "climate.b"])
    equal(group.min_temp, 16, "highest minimum")
    equal(group.max_temp, 30, "lowest maximum")
    equal(group.target_temperature, 22.0, "mean target temperature")

    # Members without a common range fall back to the defaults of the unit.
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", min_temp=10, max_temp=20)
    climate_state("climate.b", "heat", min_temp=25, max_temp=30)

    group = make_group(["climate.a", "climate.b"])
    equal(group.min_temp, 7, "default minimum")
    equal(group.max_temp, 35, "default maximum")

    # Members in Fahrenheit get the defaults of their unit.
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", min_temp=60, max_temp=70)
    climate_state("climate.b", "heat", min_temp=100, max_temp=110)

    group = make_group(["climate.a", "climate.b"], unit=FAHRENHEIT)
    close(group.min_temp, 44.6, "default minimum in Fahrenheit", 0.1)
    close(group.max_temp, 95.0, "default maximum in Fahrenheit", 0.1)


def test_supported_features_are_masked() -> None:
    """Features the group cannot handle are not announced."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state(
        "climate.a",
        "heat",
        features=int(
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TARGET_HUMIDITY
            | ClimateEntityFeature.FAN_MODE
        ),
    )
    climate_state(
        "climate.b",
        "heat",
        features=int(
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.SWING_MODE
            | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
    )

    group = make_group(["climate.a", "climate.b"])

    equal(
        group.supported_features,
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.SWING_HORIZONTAL_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF,
        "merged and masked features",
    )
    check(
        not group.supported_features & ClimateEntityFeature.TARGET_HUMIDITY,
        "humidity must not be announced",
    )

    # A member without features only removes them again.
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", features=int(ClimateEntityFeature.FAN_MODE))
    climate_state("climate.b", "heat", features=int(ClimateEntityFeature.TARGET_TEMPERATURE))
    group = make_group(["climate.a", "climate.b"])
    equal(
        group.supported_features,
        ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.TARGET_TEMPERATURE,
        "features of both members",
    )


def test_member_features_are_tracked() -> None:
    """The features of every member are tracked individually."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat", features=int(ClimateEntityFeature.FAN_MODE))
    group = make_group(["climate.a", "climate.b"], with_features=True)

    check(
        "climate.a" in group._member_features
        and "climate.b" not in group._member_features,
        "only members with a state are tracked",
    )
    equal(
        group._member_features["climate.a"],
        ClimateEntityFeature.FAN_MODE,
        "tracked features of a member",
    )
    equal(
        group._member_features["climate.a"] & ClimateEntityFeature.TARGET_HUMIDITY,
        ClimateEntityFeature(0),
        "unknown features are not tracked",
    )

    group.async_update_supported_features("climate.a", None)
    check(
        "climate.a" not in group._member_features,
        "features are dropped when the state is gone",
    )

    group.async_update_supported_features(
        "climate.a", ha_stub.State("climate.a", "heat", {})
    )
    check(
        "climate.a" not in group._member_features,
        "members without supported_features are not tracked",
    )


def test_state_change_listener_updates_the_group() -> None:
    """A member state change updates the group state."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "off", hvac_modes=["off", "heat"])
    climate_state("climate.b", "off", hvac_modes=["off", "heat"])

    group = make_group(["climate.a", "climate.b"], instance=hass)
    run(group.async_added_to_hass())
    equal(group.state, "off", "initial state")

    climate_state("climate.a", "heat", hvac_modes=["off", "heat"])
    climate_state("climate.b", "heat", hvac_modes=["off", "heat"])
    ha_stub.fire_state_change("climate.a")

    equal(group.state, "heat", "state after the member changed")
    check(group.state_writes > 0, "the state was written")


# --------------------------------------------------------------------------
# service forwarding
# --------------------------------------------------------------------------


def test_set_temperature_converts_the_unit() -> None:
    """Temperatures are forwarded in the unit system of Home Assistant."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat")
    climate_state("climate.b", "heat")
    group = make_group(["climate.a", "climate.b"], unit=FAHRENHEIT)

    run(group.async_set_temperature(temperature=70.0))

    call = only_call(service="set_temperature")
    equal(call["data"]["entity_id"], ["climate.a", "climate.b"], "members")
    close(call["data"]["temperature"], 21.111, "converted temperature", 0.01)
    equal(call["blocking"], True, "blocking call")
    equal(call["context"], None, "context of the entity")


def test_set_temperature_passes_the_hvac_mode() -> None:
    """The HVAC mode is part of the set_temperature call."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state("climate.a", "heat")
    group = make_group(["climate.a"])

    run(
        group.async_set_temperature(
            temperature=21.0, hvac_mode=HVACMode.HEAT, target_temp_low=18.0
        )
    )

    call = only_call(service="set_temperature")
    equal(call["data"]["temperature"], 21.0, "temperature")
    equal(call["data"]["target_temp_low"], 18.0, "target temperature low")
    equal(call["data"]["hvac_mode"], HVACMode.HEAT, "hvac mode")
    equal(len(hass.services.calls), 1, "a single call is forwarded")


def test_mode_services_are_forwarded_to_capable_members() -> None:
    """Mode services only reach the members that support them."""
    global hass
    hass = ha_stub.reset_hass()
    with_fan = int(ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.PRESET_MODE)
    without_fan = int(ClimateEntityFeature.TARGET_TEMPERATURE)
    climate_state("climate.a", "heat", features=with_fan, fan_modes=["low"],
                  preset_modes=["eco"])
    climate_state("climate.b", "heat", features=without_fan, min_temp=7, max_temp=35,
                  temperature=20.0)
    group = make_group(["climate.a", "climate.b"], with_features=True)

    run(group.async_set_fan_mode("low"))
    equal(only_call(service="set_fan_mode")["data"]["entity_id"], ["climate.a"], "fan")

    hass.services.calls.clear()
    run(group.async_set_preset_mode("eco"))
    equal(
        only_call(service="set_preset_mode")["data"]["entity_id"],
        ["climate.a"],
        "preset",
    )

    hass.services.calls.clear()
    run(group.async_set_swing_mode("on"))
    # Nobody announced swing support, so every member is called.
    equal(
        only_call(service="set_swing_mode")["data"]["entity_id"],
        ["climate.a", "climate.b"],
        "fall back to all members",
    )

    hass.services.calls.clear()
    run(group.async_set_swing_horizontal_mode("on"))
    equal(
        only_call(service="set_swing_horizontal_mode")["data"]["entity_id"],
        ["climate.a", "climate.b"],
        "horizontal swing",
    )

    hass.services.calls.clear()
    run(group.async_set_hvac_mode(HVACMode.HEAT))
    call = only_call(service="set_hvac_mode")
    equal(call["data"]["entity_id"], ["climate.a", "climate.b"], "all members")
    equal(call["data"]["hvac_mode"], HVACMode.HEAT, "hvac mode")


def test_turn_on_and_turn_off() -> None:
    """Turning the group on and off reaches the members."""
    global hass
    hass = ha_stub.reset_hass()
    features = int(ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF)
    climate_state("climate.a", "off", features=features, hvac_modes=["off", "heat"])
    climate_state("climate.b", "off", features=features, hvac_modes=["off", "heat"])
    group = make_group(["climate.a", "climate.b"], with_features=True)

    run(group.async_turn_on())
    call = only_call(service="turn_on")
    equal(call["data"]["entity_id"], ["climate.a", "climate.b"], "members")
    equal(call["data"].get("hvac_mode"), None, "no mode is forced")

    hass.services.calls.clear()
    run(group.async_turn_off())
    equal(
        only_call(service="turn_off")["data"]["entity_id"],
        ["climate.a", "climate.b"],
        "members",
    )


def test_turn_on_falls_back_to_a_hvac_mode() -> None:
    """Members without turn_on support get a HVAC mode instead."""
    global hass
    hass = ha_stub.reset_hass()
    climate_state(
        "climate.a",
        "off",
        features=int(ClimateEntityFeature.TARGET_TEMPERATURE),
        hvac_modes=["off", "heat"],
    )
    group = make_group(["climate.a"], with_features=True)

    run(group.async_turn_on())
    call = only_call(service="set_hvac_mode")
    equal(call["data"]["hvac_mode"], HVACMode.HEAT, "fallback mode")

    hass.services.calls.clear()
    run(group.async_turn_off())
    equal(
        only_call(service="set_hvac_mode")["data"]["hvac_mode"],
        HVACMode.OFF,
        "fallback off",
    )


# --------------------------------------------------------------------------
# setup
# --------------------------------------------------------------------------


def test_yaml_setup() -> None:
    """The legacy YAML configuration still works."""
    global hass
    hass = ha_stub.reset_hass()
    import voluptuous as vol

    schema = climate.PLATFORM_SCHEMA
    config = schema(
        {
            "platform": "climate_group",
            "name": "Living Room",
            "temperature_unit": "C",
            "entities": ["climate.a", "climate.b"],
        }
    )
    equal(config["temperature_unit"], CELSIUS, "short unit is normalized")
    equal(config["entities"], ["climate.a", "climate.b"], "entities")

    try:
        schema(
            {
                "platform": "climate_group",
                "entities": ["sensor.not_a_climate"],
            }
        )
    except vol.Invalid:
        check(True, "a non climate entity is rejected")
    else:
        check(False, "the YAML schema accepted a non climate entity")

    default = schema({"platform": "climate_group", "entities": ["climate.a"]})
    equal(default["name"], const.DEFAULT_NAME, "default name")

    added: list[Any] = []
    run(
        climate.async_setup_platform(
            hass,
            {
                "name": "Living Room",
                "unique_id": "living-room",
                "entities": ["climate.a"],
            },
            added.extend,
        )
    )
    equal(len(added), 1, "one entity is added")
    entity = added[0]
    equal(entity.name, "Living Room", "name")
    equal(entity.unique_id, "living-room", "unique id")
    equal(entity._entity_ids, ["climate.a"], "entities")
    equal(entity.temperature_unit, CELSIUS, "unit from the unit system")


def test_config_entry_setup() -> None:
    """A config entry creates the group and options win over data."""
    global hass
    hass = ha_stub.reset_hass()
    entry = ConfigEntry(
        entry_id="entry-1",
        data={
            "name": "From data",
            "entities": ["climate.a"],
            "temperature_unit": CELSIUS,
        },
    )
    added: list[Any] = []
    run(climate.async_setup_entry(hass, entry, added.extend))

    equal(len(added), 1, "one entity is added")
    entity = added[0]
    equal(entity.unique_id, "entry-1", "the entry id is the unique id")
    equal(entity.name, "From data", "name from data")

    entry.options = {
        "name": "From options",
        "entities": ["climate.b", "climate.c"],
        "temperature_unit": FAHRENHEIT,
    }
    added = []
    run(climate.async_setup_entry(hass, entry, added.extend))
    entity = added[0]
    equal(entity.name, "From options", "name from options")
    equal(entity._entity_ids, ["climate.b", "climate.c"], "entities from options")
    equal(entity.temperature_unit, FAHRENHEIT, "unit from options")


def test_forwarding_and_unloading() -> None:
    """The integration forwards to the climate platform."""
    global hass
    hass = ha_stub.reset_hass()
    entry = ConfigEntry(entry_id="entry-2")

    check(run(integration.async_setup_entry(hass, entry)), "setup returns True")
    equal(hass.config_entries.forwarded, [("entry-2", ["climate"])], "forwarded")

    check(run(integration.async_unload_entry(hass, entry)), "unload returns True")
    equal(hass.config_entries.unloaded, [("entry-2", ["climate"])], "unloaded")


# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------


def test_normalize_temperature_unit() -> None:
    """Every accepted form of a temperature unit is normalized."""
    global hass
    hass = ha_stub.reset_hass(FAHRENHEIT)

    equal(const.normalize_temperature_unit(None, hass), FAHRENHEIT, "None")
    equal(const.normalize_temperature_unit("C", hass), CELSIUS, "C")
    equal(const.normalize_temperature_unit("c", hass), CELSIUS, "c")
    equal(const.normalize_temperature_unit("F", hass), FAHRENHEIT, "F")
    equal(const.normalize_temperature_unit("°C", hass), CELSIUS, "degree C")
    equal(const.normalize_temperature_unit(CELSIUS, hass), CELSIUS, "enum")
    equal(const.normalize_temperature_unit("kelvin", hass), FAHRENHEIT, "fallback")


# --------------------------------------------------------------------------
# config flow
# --------------------------------------------------------------------------


def _prepare_flow(instance: Any, entry: ConfigEntry | None = None) -> Any:
    """Attach the stand-in Home Assistant to a flow."""
    instance.hass = hass
    if entry is not None:
        instance._config_entry = entry
    return instance


def test_config_flow_creates_a_group() -> None:
    """The user flow creates a config entry."""
    global hass
    hass = ha_stub.reset_hass()
    ha_stub.reset_entries()
    climate_state("climate.a", "heat")
    climate_state("climate.b", "heat")

    flow = _prepare_flow(config_flow.ClimateGroupConfigFlow())
    form = run(flow.async_step_user())
    equal(form["type"], "form", "the form is shown first")
    equal(form["errors"], {}, "no errors")
    defaults = schema_defaults(form["data_schema"])
    equal(defaults["name"], const.DEFAULT_NAME, "default name")
    equal(defaults["entities"], [], "no entity is preselected")
    equal(defaults["temperature_unit"], CELSIUS, "default unit is the unit system")

    result = run(
        flow.async_step_user(
            {
                "name": "  Living Room  ",
                "entities": ["climate.a", "climate.b", "climate.a"],
                "temperature_unit": CELSIUS,
            }
        )
    )
    equal(result["type"], "create_entry", "entry is created")
    equal(result["title"], "Living Room", "title is trimmed")
    equal(
        result["data"],
        {
            "name": "Living Room",
            "entities": ["climate.a", "climate.b"],
            "temperature_unit": CELSIUS,
        },
        "entry data",
    )


def test_config_flow_validation() -> None:
    """The user flow rejects invalid input."""
    global hass
    hass = ha_stub.reset_hass()
    ha_stub.reset_entries()

    flow = _prepare_flow(config_flow.ClimateGroupConfigFlow())
    form = run(
        flow.async_step_user(
            {"name": "Group", "entities": [], "temperature_unit": CELSIUS}
        )
    )
    equal(form["type"], "form", "the form is shown again")
    equal(form["errors"], {"entities": "no_entities"}, "empty selection")

    form = run(
        flow.async_step_user(
            {
                "name": "",
                "entities": ["climate.a"],
                "temperature_unit": CELSIUS,
            }
        )
    )
    equal(form["errors"], {"name": "no_name"}, "missing name")

    # An entity of another domain in the registry is rejected.
    ha_stub._REGISTRY.entries["sensor.temperature"] = ha_stub.RegistryEntry(
        "sensor.temperature", "sensor"
    )
    form = run(
        flow.async_step_user(
            {
                "name": "Group",
                "entities": ["sensor.temperature"],
                "temperature_unit": CELSIUS,
            }
        )
    )
    equal(form["errors"], {"entities": "invalid_entities"}, "wrong domain")
    equal(
        schema_defaults(form["data_schema"])["name"], "Group", "input is kept"
    )

    # A duplicate name aborts the flow.
    ha_stub.add_entry(
        ConfigEntry(data={"name": "Group", "entities": ["climate.a"]})
    )
    try:
        run(
            flow.async_step_user(
                {
                    "name": "Group",
                    "entities": ["climate.a"],
                    "temperature_unit": CELSIUS,
                }
            )
        )
    except ha_stub.AbortFlow as err:
        equal(err.reason, "already_configured", "abort reason")
    else:
        FAILURES.append("a duplicate name did not abort the flow")


def test_form_defaults_hide_vanished_entities() -> None:
    """Entities that no longer exist are not preselected."""
    global hass
    hass = ha_stub.reset_hass()
    ha_stub.reset_entries()
    climate_state("climate.here", "heat")
    ha_stub._REGISTRY.entries["climate.registry_only"] = ha_stub.RegistryEntry(
        "climate.registry_only", "climate"
    )
    ha_stub._REGISTRY.entries["climate.disabled"] = ha_stub.RegistryEntry(
        "climate.disabled", "climate", disabled_by="user"
    )

    flow = _prepare_flow(config_flow.ClimateGroupConfigFlow())
    form = run(
        flow.async_step_user(
            {
                "name": "",
                "entities": [
                    "climate.here",
                    "climate.registry_only",
                    "climate.disabled",
                    "climate.gone",
                ],
                "temperature_unit": CELSIUS,
            }
        )
    )
    equal(form["errors"], {"name": "no_name"}, "the name is required")
    equal(
        schema_defaults(form["data_schema"])["entities"],
        ["climate.here", "climate.registry_only"],
        "only usable entities are preselected",
    )


def test_options_flow() -> None:
    """The options flow edits an existing group."""
    global hass
    hass = ha_stub.reset_hass()
    ha_stub.reset_entries()
    climate_state("climate.a", "heat")
    climate_state("climate.b", "heat")

    entry = ha_stub.add_entry(
        ConfigEntry(
            entry_id="entry-3",
            title="Group",
            data={
                "name": "Group",
                "entities": ["climate.a"],
                "temperature_unit": CELSIUS,
            },
        )
    )
    ha_stub._REGISTRY.entries["climate.group"] = ha_stub.RegistryEntry(
        "climate.group", "climate", config_entry_id="entry-3"
    )

    flow = _prepare_flow(config_flow.ClimateGroupOptionsFlow(), entry)
    form = run(flow.async_step_init())
    defaults = schema_defaults(form["data_schema"])
    equal(defaults["name"], "Group", "name default")
    equal(defaults["entities"], ["climate.a"], "entity default")

    # The group may not contain itself.
    form = run(
        flow.async_step_init(
            {
                "name": "Group",
                "entities": ["climate.group", "climate.b"],
                "temperature_unit": CELSIUS,
            }
        )
    )
    equal(
        form["errors"],
        {"entities": "no_self_reference"},
        "self reference is rejected",
    )

    result = run(
        flow.async_step_init(
            {
                "name": "New name",
                "entities": ["climate.a", "climate.b"],
                "temperature_unit": FAHRENHEIT,
            }
        )
    )
    equal(result["type"], "create_entry", "options are stored")
    equal(
        result["data"],
        {
            "name": "New name",
            "entities": ["climate.a", "climate.b"],
            "temperature_unit": FAHRENHEIT,
        },
        "option data",
    )
    equal(config_flow.ClimateGroupOptionsFlow.automatic_reload, True, "reloads")

    # Options win over data when the entry is set up again.
    entry.options = result["data"]
    added: list[Any] = []
    run(climate.async_setup_entry(hass, entry, added.extend))
    equal(added[0].name, "New name", "options win over data")
    equal(added[0].temperature_unit, FAHRENHEIT, "unit from options")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> int:
    """Run all tests."""
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        try:
            test()
        except Exception as err:  # noqa: BLE001
            FAILURES.append(f"{test.__name__} raised {type(err).__name__}: {err}")

    if FAILURES:
        print(f"FAILED ({CHECKS} checks, {len(FAILURES)} failures)")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1

    print(f"ALL PASS ({CHECKS} checks, {len(tests)} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
