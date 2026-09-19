# Climate Group

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=acdcnow&repository=climate_group&category=Integration)
[![GitHub release](https://img.shields.io/github/v/release/acdcnow/climate_group?include_prereleases)](https://github.com/acdcnow/climate_group/releases)
[![Minimum Home Assistant version](https://img.shields.io/badge/Home%20Assistant-2026.9.0%2B-blue)](https://www.home-assistant.io/)

Groups multiple climate entities into a single climate entity. Useful if you
have several radiator thermostats in one room, a heat pump with more than one
zone, or an AC and a floor heating that should always be controlled together.

The group entity behaves like any other thermostat: it shows the average room
temperature, the average setpoint and the mode your devices are in, and every
service call is forwarded to all members.

**This version (2.0.0-beta.1) requires Home Assistant 2026.9.0 or newer.**

## Features

- **Configured in the UI** – add a group from *Settings → Devices & services →
  Add integration → Climate Group*, pick the members with the entity picker and
  change them later through *Configure*.
- **YAML still works** – existing `climate:` platform configurations keep
  working, they are not deprecated.
- **Real aggregation** – setpoint and room temperature are averaged, the mode
  is the most common mode of your devices, and the available fan, preset and
  swing modes are merged.
- **Only what your devices can do** – the group announces exactly those
  features that its members announce, and a mode is only forwarded to the
  members that support it. A group of two TRVs without fan support does not
  offer `set_fan_mode`, and a group with one AC does not spam errors for the
  TRVs.
- **Group of groups** – a group can contain another group, which is handy for
  building a floor or a whole-house group.
- **Unavailable members are ignored** – as long as one member knows its state,
  the group shows a state; only when all members are gone the group becomes
  unavailable.
- **Brand images included** – the icon and logo ship with the integration
  (`custom_components/climate_group/brand/`), no CDN lookup needed.

## Installation

### HACS

1. Open HACS → **Integrations** → the three dot menu → **Custom repositories**.
2. Add `https://github.com/acdcnow/climate_group` with the category
   **Integration**.
3. Install **Climate Group** and restart Home Assistant.

Beta releases are only offered when *Show beta versions* is enabled in the
HACS settings.

### Manual

Copy the folder `custom_components/climate_group` into the `config` directory
of your Home Assistant installation, so that it ends up in
`config/custom_components/climate_group`, and restart Home Assistant.

## Configuration

### User interface (recommended)

1. *Settings → Devices & services → Add integration*.
2. Search for **Climate Group**.
3. Give the group a name and select the climate entities it should contain.

The name is used to build the entity ID, e.g. the name *Living Room* creates
`climate.living_room`. The options flow (*Configure* on the integration entry)
changes the name, the members and the temperature unit afterwards; changing the
options reloads the group automatically.

| Option | Description |
| --- | --- |
| Name | Name of the group, also used for its entity ID. |
| Climate entities | The members of the group. Only `climate.*` entities can be selected. |
| Temperature unit | Unit in which the group reports temperatures. Keep the unit system of Home Assistant unless your thermostats report a different unit. |

### YAML (still supported)

```yaml
# configuration.yaml
climate:
  - platform: climate_group
    name: Climate Friendly Name
    temperature_unit: C   # optional, 'C' or 'F', defaults to the unit system
    unique_id: living_room_climate_group   # optional
    entities:
      - climate.clima1
      - climate.clima2
      - climate.heater
```

| Key | Required | Description |
| --- | --- | --- |
| `name` | no | Name of the group, defaults to `Climate Group`. |
| `entities` | yes | List of `climate.*` entities, validated by the schema. |
| `temperature_unit` | no | `C` or `F`, defaults to the unit system of Home Assistant. |
| `unique_id` | no | Sets a fixed unique ID, useful for the entity registry. |

> Tip: a YAML group and a UI group can coexist, but the UI is the way forward –
> deleting the YAML block and adding the group in the UI gives the same entity
> name and therefore keeps the same entity ID.

## How the group behaves

| Group attribute | How it is calculated |
| --- | --- |
| Current temperature | Mean of all members that report one. |
| Target temperature | Mean of all members that report one. |
| Target temperature range | Mean of `target_temp_low` / `target_temp_high` of all members that report them. |
| Min / max temperature | The highest `min_temp` and the lowest `max_temp`, so the group only offers a range every member accepts. If the members have no common range, the defaults (7–35 °C) are used. |
| Target temperature step | The coarsest step reported by the members. |
| HVAC mode | The most common mode of the members, ignoring `off` while at least one member is active. `off` if all members are off. |
| HVAC action | The most common action, ignoring `off` while at least one member is active. |
| Available HVAC modes | Union of the modes of all members, with `off` first. |
| Fan / preset / swing / horizontal swing mode | The most common value of the members. |
| Available fan / preset / swing modes | Union of the modes of all members. |
| Supported features | Union of the features of all members, limited to the features a group can handle (temperature, temperature range, preset, fan, swing, swing horizontal, turn on, turn off). |
| `assumed_state` | Off while all members agree, otherwise on, so Home Assistant knows that the state is not certain. |
| `available` | Off only when every member is missing or unavailable. |
| Extra attribute `entity_id` | The members of the group. |

The group is updated by the state changes of its members, it does not poll.

## Services

Every climate service is forwarded to the members of the group with the same
entity IDs that Home Assistant uses for a single entity:

| Service | Behaviour |
| --- | --- |
| `climate.set_temperature` | Forwarded to all members, including `hvac_mode`, `target_temp_low` and `target_temp_high`. Values are converted from the unit of the group into the unit system of Home Assistant. |
| `climate.set_hvac_mode` | Forwarded to all members. |
| `climate.set_fan_mode` | Forwarded to the members that announce fan mode support. |
| `climate.set_preset_mode` | Forwarded to the members that announce preset mode support. |
| `climate.set_swing_mode` | Forwarded to the members that announce swing mode support. |
| `climate.set_swing_horizontal_mode` | Forwarded to the members that announce horizontal swing support. |
| `climate.turn_on` / `climate.turn_off` | Forwarded to the members that announce turn on/off support. Members that do not announce it get a HVAC mode instead (`heat`/`cool`/`heat_cool` when turning on, `off` when turning off). |
| `climate.toggle` | Turns the group on or off, depending on its current mode. |

## Breaking changes in 2.0

- **Home Assistant 2026.9.0 or newer** is required. `GroupEntity` moved to
  `homeassistant.components.group.entity`, the entity services and the
  `ClimateEntityFeature` flags changed, and the integration was modernized for
  the config entry and entity APIs of 2026.9.
- **Behaviour fixes** that change reported values: an unavailable member no
  longer leaks the string `unavailable` into the HVAC mode, the HVAC mode of a
  group whose members are off but partly unavailable is now `off` (it was
  `unknown` before), and the group no longer reports `off` as its preset mode.
- **YAML users** do not have to change anything, `platform: climate_group` keeps
  working.

## Troubleshooting

- **The group does not offer fan, preset or swing modes.** None of the members
  announces the matching feature. Check the `supported_features` attribute of
  the members.
- **Temperatures are off by a factor.** The members do not report temperatures
  in the same unit as the group. Set the temperature unit of the group to the
  unit of the members.
- **The mode jumps between two values.** The members disagree, which is shown by
  `assumed_state: true`. The group reports the most common mode.
- **A mode service reports an error for a single member.** The member does not
  support that mode; that is what the entity does on its own, the group cannot
  change it.

## Credits

- Created by [@daenny](https://github.com/daenny) as
  [climate_group](https://github.com/daenny/climate_group) (MIT).
- 1.0.1 by [@acdcnow](https://github.com/acdcnow), fixing the 2024.1 incompatibility.
- 2.x by [@acdcnow](https://github.com/acdcnow): config flow, UI configuration,
  aggregation fixes, brand images and support for Home Assistant 2026.9.

Licensed under the [MIT License](LICENSE).
