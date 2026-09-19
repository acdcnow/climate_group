# Climate Group

Groups multiple climate entities into a single thermostat entity – for example
all radiator thermostats of one room, or several zones of a heat pump.

**Version 2.0.0-beta.1 · requires Home Assistant 2026.9.0 or newer**

## What it does

* Adds a climate entity that controls all of its members at once.
* Averages the current and the target temperature of the members.
* Reports the most common mode of the members and merges the available modes.
* Announces only the features its members announce, and only forwards a mode to
  the members that support it.
* Ignores members that are unavailable, and only becomes unavailable itself when
  every member is gone.
* Can contain another group, so groups can be nested.

## Installation

1. Add `https://github.com/acdcnow/climate_group` to HACS as a **custom
   repository** with the category *Integration* (or copy the folder
   `custom_components/climate_group` into your `config` directory).
2. Install **Climate Group** and restart Home Assistant.
3. *Settings → Devices & services → Add integration → Climate Group*, then pick a
   name and the climate entities that should be grouped.

Beta versions are only offered when *Show beta versions* is enabled in HACS.

## Options

| Option | Description |
| --- | --- |
| Name | Name of the group, also used for the entity ID (`Living Room` → `climate.living_room`). |
| Climate entities | The members of the group. |
| Temperature unit | Unit the group reports temperatures in. Keep the Home Assistant unit system unless your devices report another unit. |

The options can be changed any time with *Configure* on the integration entry,
which reloads the group automatically.

YAML configuration is still supported:

```yaml
climate:
  - platform: climate_group
    name: Living Room
    entities:
      - climate.clima1
      - climate.clima2
```

## Aggregation

| Attribute | Calculation |
| --- | --- |
| Current / target temperature | Mean of the members |
| Min / max temperature | Highest minimum and lowest maximum of the members |
| HVAC mode and action | Most common value, `off` only when all members are off |
| Available modes | Union of the members |
| Supported features | Union of the members, limited to what a group can forward |

## Links

* [README](https://github.com/acdcnow/climate_group/blob/master/README.md) –
  full documentation, services, troubleshooting
* [Changelog](https://github.com/acdcnow/climate_group/blob/master/CHANGELOG.md)
* [Issues](https://github.com/acdcnow/climate_group/issues)

Licensed under the MIT License. Originally created by
[@daenny](https://github.com/daenny).
