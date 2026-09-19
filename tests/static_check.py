"""Static checks for the repository layout and the metadata files.

    python tests/static_check.py
"""

from __future__ import annotations

import json
from pathlib import Path
import py_compile
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "climate_group"

# The version of the integration and of the release that is published for it.
VERSION = "2.0.0-beta.2"
MIN_HOME_ASSISTANT = "2026.9.0"

# Home Assistant 2026.9 ships the group entity in this module.
GROUP_ENTITY_MODULE = "homeassistant.components.group.entity"

# Keys that hassfest accepts in the manifest of an integration.
MANIFEST_KEYS = {
    "after_dependencies",
    "codeowners",
    "config_flow",
    "dependencies",
    "dhcp",
    "documentation",
    "domain",
    "bluetooth",
    "integration_type",
    "iot_class",
    "issue_tracker",
    "loggers",
    "mqtt",
    "name",
    "requirements",
    "single_config_entry",
    "ssdp",
    "usb",
    "zeroconf",
    "version",
}

# Keys that HACS accepts in hacs.json.
HACS_KEYS = {
    "content_in_root",
    "country",
    "filename",
    "hacs",
    "hide_default_branch",
    "homeassistant",
    "name",
    "persistent_directory",
    "render_readme",
    "zip_release",
}

# Brand images: name -> (width, height)
BRAND_IMAGES = {
    "icon.png": (256, 256),
    "icon@2x.png": (512, 512),
    "dark_icon.png": (256, 256),
    "dark_icon@2x.png": (512, 512),
    "logo.png": (512, 256),
    "logo@2x.png": (1024, 512),
    "dark_logo.png": (512, 256),
    "dark_logo@2x.png": (1024, 512),
}

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, message: str) -> None:
    """Check a condition."""
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(message)


def read_json(path: Path) -> dict:
    """Read a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def keys_of(data: dict, prefix: str = "") -> set[str]:
    """Return all nested keys of a translation file."""
    result: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        result.add(path)
        if isinstance(value, dict):
            result |= keys_of(value, path)
    return result


def png_size(path: Path) -> tuple[int, int]:
    """Return the size of a PNG file."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG file"
    return struct.unpack(">II", data[16:24])


def main() -> int:
    """Run all checks."""
    global CHECKS

    py_files = sorted(ROOT.rglob("*.py"))
    py_files = [path for path in py_files if ".git" not in path.parts]

    # ---------------------------------------------------------------- python
    for path in py_files:
        CHECKS += 1
        try:
            py_compile.compile(str(path), doraise=True, cfile=str(path) + "c")
        except py_compile.PyCompileError as err:
            FAILURES.append(f"{path.name} does not compile: {err}")
        else:
            Path(str(path) + "c").unlink(missing_ok=True)

    source = "\n".join(
        (PKG / name).read_text(encoding="utf-8")
        for name in ("__init__.py", "climate.py", "config_flow.py", "const.py")
    )

    # -------------------------------------------------------------- manifest
    manifest = read_json(PKG / "manifest.json")
    # hassfest requires "domain, name, then alphabetical order".
    expected_order = ["domain", "name"] + sorted(
        key for key in manifest if key not in ("domain", "name")
    )
    check(
        list(manifest) == expected_order,
        "manifest.json keys must be domain, name, then alphabetical (hassfest): "
        f"{list(manifest)}",
    )
    check(
        set(manifest) <= MANIFEST_KEYS,
        f"manifest.json has unsupported keys: {sorted(set(manifest) - MANIFEST_KEYS)}",
    )
    check(manifest["domain"] == PKG.name, "the manifest domain matches the folder")
    check(manifest["version"] == VERSION, "the manifest version matches the release")
    check(manifest["config_flow"] is True, "the manifest enables the config flow")
    check(
        manifest["dependencies"] == ["climate"],
        "the manifest depends on the climate integration",
    )
    check(
        manifest["integration_type"] == "helper",
        "the integration type is helper",
    )
    check(manifest["iot_class"] == "calculated", "the IoT class is calculated")
    check(
        "homeassistant" not in manifest,
        "the minimum Home Assistant version belongs into hacs.json",
    )
    check(
        manifest["codeowners"] == ["@acdcnow"], "the code owner is set"
    )

    # ------------------------------------------------------------- hacs.json
    hacs = read_json(ROOT / "hacs.json")
    check(
        set(hacs) <= HACS_KEYS,
        f"hacs.json has unsupported keys: {sorted(set(hacs) - HACS_KEYS)}",
    )
    check(bool(hacs.get("name")), "hacs.json needs a name")
    check(
        hacs.get("homeassistant") == MIN_HOME_ASSISTANT,
        "hacs.json needs the minimum Home Assistant version",
    )
    check(
        hacs.get("content_in_root") is not True,
        "the integration is not in the root of the repository",
    )
    check(
        (ROOT / "info.md").is_file(),
        "HACS shows info.md when render_readme is not set",
    )

    # --------------------------------------------------------- translations
    strings = read_json(PKG / "strings.json")
    english = read_json(PKG / "translations" / "en.json")
    check(strings == english, "strings.json must match translations/en.json")

    for language in ("de",):
        translated = read_json(PKG / "translations" / f"{language}.json")
        check(
            keys_of(translated) == keys_of(english),
            f"translations/{language}.json must have the same keys as English",
        )

    # The error keys of the flows must be documented and used.
    error_keys = {
        match
        for match in re.findall(
            r'errors\[\w+\] = "(\w+)"', source
        )
    }
    error_keys.add("already_configured")  # raised by _async_abort_entries_match
    documented = set(english["config"]["error"]) | set(english["config"]["abort"])
    check(
        error_keys == documented,
        "the flow error keys and the translations differ: "
        f"used={sorted(error_keys)} documented={sorted(documented)}",
    )
    check(
        set(english["options"]["error"]) == set(english["config"]["error"]),
        "the options flow documents the same errors as the config flow",
    )

    # ----------------------------------------------------------------- brand
    for name, size in BRAND_IMAGES.items():
        path = PKG / "brand" / name
        check(path.is_file(), f"brand/{name} is missing")
        if path.is_file():
            check(
                png_size(path) == size,
                f"brand/{name} must be {size[0]}x{size[1]}, got {png_size(path)}",
            )

    # -------------------------------------------------------------- 2026.9 API
    check(
        f"from {GROUP_ENTITY_MODULE} import GroupEntity" in source,
        "GroupEntity must be imported from the module it lives in since 2026.9",
    )
    check(
        "from homeassistant.components.group import GroupEntity" not in source,
        "GroupEntity is not available in the group package anymore",
    )
    check(
        "async_forward_entry_setups" in source,
        "__init__.py must forward the config entry to the climate platform",
    )
    check(
        "async_unload_platforms" in source,
        "__init__.py must unload the climate platform",
    )
    check(
        "OptionsFlowWithReload" in source,
        "the options flow must reload the config entry",
    )
    check(
        "hass.data[DOMAIN]" not in source,
        "hass.data must not be used to store the runtime data",
    )
    check("async_timeout" not in source, "async_timeout was removed from Home Assistant")

    # --------------------------------------------------------------- versioning
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    check(VERSION in changelog, "the changelog mentions the released version")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check(VERSION in readme, "the readme mentions the released version")
    check(
        MIN_HOME_ASSISTANT in readme,
        "the readme mentions the minimum Home Assistant version",
    )
    check(
        "decimal_accuracy_to_half" in readme and "decimal_accuracy_to_half" in source,
        "the option that the other climate_group forks use is documented and accepted",
    )

    if FAILURES:
        print(f"FAILED ({CHECKS} checks, {len(FAILURES)} failures)")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1

    print(f"static checks passed ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
