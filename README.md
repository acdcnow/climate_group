# climate_group

thanks to @daenny for the initial version as he has no time any more I made some changes in order to get it working gain on HA core 2024.1.0

Home Assistant Climate Group

Groups multiple climate devices to a single entity. Useful if you have for instance multiple radiator thermostats in a room and want to control them all together.
Inspired/copied from light_group component [HA LIGHT](https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/group/light.py)

## How to install:

### HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=acdcnow&repository=climate_group&category=Integration)

Add this repo [HACS](https://github.com/acdcnow/climate_group) to the HACS store and install from there.

### local install
Put in "custom_components" folder located in hass.io inside the config folder.
(The 2 .py file must be config/custom_components/climate_group)



## Sample Configuration

Put this inside configuration.yaml in config folder of hass.io

```yaml
climate:
  - platform: climate_group
    name: 'Climate Friendly Name'
    temperature_unit: C  # default to celsius, 'C' or 'F'
    entities:
    - climate.clima1
    - climate.clima2
    - climate.clima3
    - climate.heater
    - climate.termostate
```

(use the entities you want to have in your climate_group)
