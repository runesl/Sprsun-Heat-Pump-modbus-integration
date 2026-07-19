from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)

from .modbus_client import HeatPumpModbusClient
from .coordinator import SprsunCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """General setup (unused for config entries)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host: str = entry.data[CONF_HOST]
    port: int = int(entry.data[CONF_PORT])
    unit_id: int = int(entry.data[CONF_UNIT_ID])
    model: str = entry.data[CONF_MODEL]
    scan_interval: int = int(entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    _LOGGER.debug(
        "Initializing Sprsun Modbus: host=%s port=%s unit_id=%s model=%s scan=%s",
        host,
        port,
        unit_id,
        model,
        scan_interval,
    )

    # Create Modbus client
    client = HeatPumpModbusClient(host, port, unit_id)

    # Create coordinator
    coordinator = SprsunCoordinator(
        hass,
        client,
        entry.entry_id,
        model,
        scan_interval,
    )

    # First bulk read
    await coordinator.async_config_entry_first_refresh()

    # Save integration data
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "model": model,
        "coordinator": coordinator,
    }

    # Load platforms (sensor, climate, select, switch, button)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data: dict[str, Any] = hass.data[DOMAIN].pop(entry.entry_id, {})
        client: HeatPumpModbusClient | None = data.get("client")

        if client is not None:
            try:
                close_method = getattr(client, "close", None)
                if callable(close_method):
                    result = close_method()
                    if hasattr(result, "__await__"):
                        await result
            except Exception as exc:
                _LOGGER.warning("Error closing Modbus client: %s", exc)

    return unload_ok
