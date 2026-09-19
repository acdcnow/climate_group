# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.0-beta.2] - 2026-09-19

Compatibility with the configuration of the other `climate_group` forks and a
setpoint rounding that is consistent between the group and its members.

### Added

- The YAML key `decimal_accuracy_to_half` of the other `climate_group` forks
  (for example [bjrnptrsn/climate_group](https://github.com/bjrnptrsn/climate_group))
  is accepted, so an existing configuration loads again instead of failing with
  "is an invalid option for climate_group.climate".
- The same option is available in the UI as *Round setpoints to 0.5*, in the
  setup form and in the options flow.
- With the option enabled the group rounds the target temperature and the target
  temperature range to the nearest half degree, both in the state it reports and
  in the calls it forwards to the members. Room temperature measurements are not
  rounded.

### Fixed

- The rounding is applied before the setpoint is converted into the unit system
  of Home Assistant and forwarded, so a group in Fahrenheit sends a value the
  members accept instead of the unrounded average.

## [2.0.0-beta.1] - 2026-09-19

Modernized for Home Assistant 2026.9, configured in the UI, with brand images
and a set of fixes for the aggregation of the member states.

### Added

- Config flow: climate groups are created through *Settings → Devices &
  services → Add integration → Climate Group* with an entity picker for the
  members.
- Options flow to change the name, the members and the temperature unit of an
  existing group, with an automatic reload of the group.
- English and German translations, `strings.json` and an icon in the config
  flow.
- Brand images in `custom_components/climate_group/brand/` – `icon`, `logo` and
  their `dark`/`@2x` variants, so no CDN lookup is needed.
- Support for `climate.set_swing_horizontal_mode`, `climate.turn_on`,
  `climate.turn_off` and `climate.toggle`; the group forwards them to the
  members.
- Members are now tracked per entity: a mode service is only forwarded to the
  members that announce support for that feature, with a fallback to all
  members when no member announced its features (yet).
- Diagnostics for the repository: `tests/test_climate_group.py` (behaviour
  against Home Assistant stand-ins) and `tests/static_check.py` (manifest,
  HACS metadata, translations and brand images).
- `CHANGELOG.md`, rewritten `README.md` and `info.md`, HACS and hassfest
  validation workflow.

### Changed

- Requires Home Assistant **2026.9.0** or newer (the previous release required
  2024.1.0, the fork itself was based on 2024.1).
- `GroupEntity` is imported from `homeassistant.components.group.entity`, where
  it lives since 2026.9; the old import from
  `homeassistant.components.group` no longer exists.
- The integration is set up from a config entry
  (`async_setup_entry`/`async_unload_entry` + `async_forward_entry_setups`), and
  the entity is created from the entry data instead of reading `entry.options`
  only. Options override the entry data.
- The manifest no longer contains a `homeassistant` key (hassfest rejects it);
  the minimum Home Assistant version is declared in `hacs.json`.
- Aggregation is deterministic: the available modes keep the order the members
  report them in with `off` first, and ties of the most common mode are resolved
  in favour of the first member instead of the random order of a `set()`.
- Temperatures are converted from the unit of the group into the unit system of
  Home Assistant before they are forwarded to the members.
- The `entity_id` attribute is marked as unrecorded, so it no longer fills the
  recorder database.
- Replaced the duplicated state listener of the group base class with the
  `async_update_supported_features` hook of Home Assistant 2026.9.

### Fixed

- An unavailable member no longer leaks `unavailable` into the HVAC mode of the
  group, which could crash the entity with a `ValueError`.
- A group whose members are off but partly unavailable now reports `off`
  instead of `unknown`.
- The group no longer writes `off` into `preset_mode` when all members are off
  (the old code assigned the HVAC mode to the preset attribute).
- A member that reports an unknown HVAC mode or action is ignored instead of
  raising.
- `min_temp`/`max_temp` no longer become `None` (which broke the service
  validation) when the members have no common temperature range.
- Member states that are missing from the state machine are handled instead of
  being counted as a state.

### Deprecated

- Nothing. The YAML configuration (`platform: climate_group`) keeps working
  unchanged, the UI is simply the recommended way to configure a group.

## [1.0.1] - 2024-01-07

### Fixed

- Adapted the component to Home Assistant 2024.1.0 (`GroupEntity`,
  `ClimateEntityFeature`, entity services).

## [1.0.0] - 2019

- Initial release by [@daenny](https://github.com/daenny) as
  `custom_components/climate_group`.

[2.0.0-beta.2]: https://github.com/acdcnow/climate_group/releases/tag/v2.0.0-beta.2
[2.0.0-beta.1]: https://github.com/acdcnow/climate_group/releases/tag/v2.0.0-beta.1
[1.0.1]: https://github.com/acdcnow/climate_group/releases/tag/V1.0.1
