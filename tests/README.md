# Tests

The integration is tested without a Home Assistant installation. Home Assistant
2026.9 needs Python 3.14, which is not available next to the Python used here,
so `tests/ha_stub.py` registers stand-ins for the Home Assistant modules the
integration imports.

The stand-ins are written after the sources of Home Assistant 2026.9.3, with the
same enum values and the same behaviour of the parts that are used
(`GroupEntity`, `group.util`, the climate entity services, the config entry
flow helpers, the unit conversion). Everything that was verified this way is
listed in `../CHANGELOG.md`.

## Behaviour tests

```powershell
python tests/test_climate_group.py
```

Runs the aggregation, the service forwarding, the config and options flow, the
YAML platform setup and the config entry setup. Needs `voluptuous`:

```powershell
pip install voluptuous
```

## Static checks

```powershell
python tests/static_check.py
```

Checks everything that does not need Home Assistant at runtime:

* all Python files compile
* `manifest.json` has sorted keys, only keys hassfest accepts, no
  `homeassistant` key and the version of the release
* `hacs.json` only uses keys HACS supports and declares the minimum Home
  Assistant version
* `strings.json` is identical to `translations/en.json` and the other languages
  have the same keys
* the error and abort keys of the flows exist in the translations (and the other
  way round)
* every brand image exists in the size Home Assistant expects
* the imports and APIs that changed in Home Assistant 2026.9 are used correctly
* the changelog and the readme mention the released version

## Brand images

The images in `custom_components/climate_group/brand/` are drawn with Pillow at
four times the size they are needed in and downscaled with LANCZOS. A browser
cannot render those sizes reliably (it snaps fractional CSS sizes), so the exact
sizes are checked in `tests/static_check.py`.
