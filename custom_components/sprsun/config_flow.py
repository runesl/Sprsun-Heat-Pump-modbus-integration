# config_flow.py
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    CONF_SCAN_INTERVAL,
    CONF_MODEL,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DEFAULT_SCAN_INTERVAL,
    MODELS,
)


class SprsunConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        return await self._async_step_settings(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        return await self._async_step_settings(user_input, self._get_reconfigure_entry())

    async def _async_step_settings(self, user_input, entry=None):
        """Share connection settings between setup and reconfiguration."""
        step_id = "reconfigure" if entry is not None else "user"
        data = dict(entry.data) if entry is not None else {}
        options = dict(entry.options) if entry is not None else {}
        scan_interval = options.get(
            CONF_SCAN_INTERVAL, data.pop(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        errors = {}

        if user_input is not None:
            for other in self._async_current_entries():
                if (
                    (entry is None or other.entry_id != entry.entry_id)
                    and other.data.get(CONF_HOST) == user_input[CONF_HOST]
                ):
                    errors[CONF_HOST] = "already_configured"

            if not user_input[CONF_HOST]:
                errors[CONF_HOST] = "host_required"

            if user_input[CONF_PORT] < 1 or user_input[CONF_PORT] > 65535:
                errors[CONF_PORT] = "invalid_port"

            if user_input[CONF_UNIT_ID] < 1 or user_input[CONF_UNIT_ID] > 255:
                errors[CONF_UNIT_ID] = "invalid_unit_id"

            if user_input[CONF_SCAN_INTERVAL] < 5:
                errors[CONF_SCAN_INTERVAL] = "min_5"

            if not errors:
                data.update(
                    {
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                    }
                )
                options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
                if entry is not None:
                    return self.async_update_reload_and_abort(
                        entry, data=data, options=options
                    )

                selected_label = user_input[CONF_MODEL]
                data[CONF_MODEL] = MODELS[selected_label]
                return self.async_create_entry(
                    title=f"Sprsun {selected_label}",
                    data=data,
                    options=options,
                )

        defaults = {**data, CONF_SCAN_INTERVAL: scan_interval, **(user_input or {})}
        fields = {
            vol.Required(
                CONF_HOST, default=defaults.get(CONF_HOST, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=65535, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=255, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL, default=defaults[CONF_SCAN_INTERVAL]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
        }
        if entry is None:
            fields[vol.Required(CONF_MODEL)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(MODELS.keys()),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(fields),
            errors=errors,
        )
