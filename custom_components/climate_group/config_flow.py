"""Config flow for the Climate Group integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_ENTITIES, CONF_NAME, CONF_TEMPERATURE_UNIT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_DECIMAL_ACCURACY_TO_HALF,
    DEFAULT_NAME,
    DOMAIN,
    TEMPERATURE_UNITS,
    normalize_temperature_unit,
)


def _entity_selector() -> selector.EntitySelector:
    """Return a selector for selecting one or more climate entities."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            filter=[{"domain": CLIMATE_DOMAIN}],
            multiple=True,
            reorder=True,
        )
    )


def _temperature_unit_selector() -> selector.SelectSelector:
    """Return a selector for the temperature unit of the group."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(TEMPERATURE_UNITS),
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _decimal_accuracy_selector() -> selector.BooleanSelector:
    """Return a selector for the half degree rounding of the group."""
    return selector.BooleanSelector()


def _selected_entities(user_input: dict[str, Any]) -> list[str]:
    """Return the submitted entity ids without duplicates."""
    entities = user_input.get(CONF_ENTITIES) or []
    if isinstance(entities, str):
        entities = [entities]
    return list(dict.fromkeys(entities))


def _available_entities(hass: HomeAssistant, entities: list[str]) -> list[str]:
    """Return the entity ids that still exist.

    Used to build the default of the form, so that entities that were removed
    in the meantime are not offered for selection again.
    """
    known = set(hass.states.async_entity_ids(CLIMATE_DOMAIN))
    registry = er.async_get(hass)

    available: list[str] = []
    for entity_id in entities:
        if entity_id in known:
            available.append(entity_id)
            continue
        if (
            entity_entry := registry.async_get(entity_id)
        ) is not None and not entity_entry.disabled_by:
            available.append(entity_id)

    return available


def _entities_of_entry(hass: HomeAssistant, entry: ConfigEntry) -> list[str]:
    """Return the entity ids that belong to a config entry."""
    registry = er.async_get(hass)
    return [
        entity.entity_id
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    ]


def _validate(
    hass: HomeAssistant,
    user_input: dict[str, Any],
    entities: list[str],
    own_entities: list[str] | None = None,
) -> dict[str, str]:
    """Validate the submitted form, returning a field to error key mapping."""
    errors: dict[str, str] = {}

    if not str(user_input.get(CONF_NAME, "")).strip():
        errors[CONF_NAME] = "no_name"

    if not entities:
        errors[CONF_ENTITIES] = "no_entities"
    elif own_entities and any(entity_id in own_entities for entity_id in entities):
        # A group that contains itself would never settle on a state.
        errors[CONF_ENTITIES] = "no_self_reference"
    else:
        registry = er.async_get(hass)
        for entity_id in entities:
            entity_entry = registry.async_get(entity_id)
            domain = (
                entity_entry.domain
                if entity_entry is not None
                else entity_id.partition(".")[0]
            )
            if domain != CLIMATE_DOMAIN:
                errors[CONF_ENTITIES] = "invalid_entities"
                break

    return errors


def _entry_data(hass: HomeAssistant, user_input: dict[str, Any]) -> dict[str, Any]:
    """Return the config entry data for a submitted form."""
    return {
        CONF_NAME: str(user_input[CONF_NAME]).strip(),
        CONF_ENTITIES: _selected_entities(user_input),
        CONF_TEMPERATURE_UNIT: normalize_temperature_unit(
            user_input.get(CONF_TEMPERATURE_UNIT), hass
        ),
        CONF_DECIMAL_ACCURACY_TO_HALF: bool(
            user_input.get(CONF_DECIMAL_ACCURACY_TO_HALF, False)
        ),
    }


def _schema(hass: HomeAssistant, defaults: dict[str, Any]) -> vol.Schema:
    """Return the schema of the climate group form."""
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME, default=defaults.get(CONF_NAME) or DEFAULT_NAME
            ): cv.string,
            vol.Required(
                CONF_ENTITIES,
                default=_available_entities(hass, defaults.get(CONF_ENTITIES) or []),
            ): _entity_selector(),
            vol.Required(
                CONF_TEMPERATURE_UNIT,
                default=defaults.get(CONF_TEMPERATURE_UNIT)
                or hass.config.units.temperature_unit,
            ): _temperature_unit_selector(),
            vol.Required(
                CONF_DECIMAL_ACCURACY_TO_HALF,
                default=bool(defaults.get(CONF_DECIMAL_ACCURACY_TO_HALF, False)),
            ): _decimal_accuracy_selector(),
        }
    )


class ClimateGroupConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow of the Climate Group integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a new climate group."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entities = _selected_entities(user_input)
            errors = _validate(self.hass, user_input, entities)

            if not errors:
                name = str(user_input[CONF_NAME]).strip()
                # The name of a group is used to build its entity id.
                self._async_abort_entries_match({CONF_NAME: name})

                return self.async_create_entry(
                    title=name, data=_entry_data(self.hass, user_input)
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, user_input or {}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        """Return the options flow that edits an existing group."""
        return ClimateGroupOptionsFlow()


class ClimateGroupOptionsFlow(OptionsFlowWithReload):
    """Edit the name, the members or the unit of an existing climate group."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options of a climate group."""
        entry = self.config_entry
        own_entities = _entities_of_entry(self.hass, entry)

        defaults: dict[str, Any] = {
            CONF_NAME: entry.options.get(
                CONF_NAME, entry.data.get(CONF_NAME, entry.title)
            ),
            CONF_ENTITIES: entry.options.get(
                CONF_ENTITIES, entry.data.get(CONF_ENTITIES, [])
            ),
            CONF_TEMPERATURE_UNIT: entry.options.get(
                CONF_TEMPERATURE_UNIT, entry.data.get(CONF_TEMPERATURE_UNIT)
            ),
            CONF_DECIMAL_ACCURACY_TO_HALF: entry.options.get(
                CONF_DECIMAL_ACCURACY_TO_HALF,
                entry.data.get(CONF_DECIMAL_ACCURACY_TO_HALF, False),
            ),
        }

        errors: dict[str, str] = {}

        if user_input is not None:
            entities = _selected_entities(user_input)
            errors = _validate(self.hass, user_input, entities, own_entities)

            if not errors:
                name = str(user_input[CONF_NAME]).strip()
                self._async_abort_entries_match({CONF_NAME: name})

                return self.async_create_entry(
                    data=_entry_data(self.hass, user_input)
                )

            defaults = user_input

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, defaults),
            errors=errors,
        )
