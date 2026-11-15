import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import SprsunCoordinator

# Import definicji numberów per model
from .models.CGK050V3L.numbers import ENTITIES as NUMBERS_050

_LOGGER = logging.getLogger(__name__)

MODEL_NUMBERS_MAP = {
    "cgk_050v3l": NUMBERS_050,
}


# ---------------------------------------------------------
# SETUP ENTRY
# ---------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Register number entities for the model."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SprsunCoordinator = data["coordinator"]
    model: str = data["model"]

    numbers_def = MODEL_NUMBERS_MAP.get(model, [])
    entities = [
        SprsunNumberEntity(coordinator, entry.entry_id, model, definition)
        for definition in numbers_def
    ]

    async_add_entities(entities)


# ---------------------------------------------------------
# NUMBER MODBUS
# ---------------------------------------------------------


class SprsunNumberEntity(NumberEntity):
    """Number entity based on coordinator and Modbus registers."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: SprsunCoordinator,
        entry_id: str,
        model: str,
        definition: dict,
    ) -> None:
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._model = model
        self._def = definition

        self._register = definition["register"]

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{DOMAIN}_{model}_number_{self._register}"

        slug = slugify(f"sprsun_{model}_{definition['name']}")

        self.entity_id = f"number.{slug}"
        self._scale = definition.get("scale", 1.0)
        self._signed = definition.get("signed", False)
        self._attr_native_min_value = definition["min"] * self._scale
        self._attr_native_max_value = definition["max"] * self._scale
        self._attr_native_step = definition["step"] * self._scale
        self._attr_icon = definition.get("icon")
        self._attr_native_unit_of_measurement = definition.get("unit")

        mode = definition.get("mode", "slider")
        self._attr_mode = NumberMode.BOX if mode == "box" else NumberMode.SLIDER

        self._attr_available = True

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self):
        val = self.coordinator.data.get(self._register)
        if val is not None:
            if self._signed and val > 32767:
                val -= 65536
            return val * self._scale
        return None

    @property
    def extra_state_attributes(self):
        description = self._def.get("description")
        return {"description": description} if description else None

    async def async_set_native_value(self, value: float) -> None:
        try:
            raw_value = round(value / self._scale)
            if self._signed:
                raw_value &= 0xFFFF
            await self.coordinator.client.write_register(self._register, raw_value)
            await self.coordinator.async_request_refresh()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error writing number %s: %s", self._attr_name, err)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Pompa ciepła Sprsun {self._model.upper().replace('_', '-')}",
            "manufacturer": "Sprsun",
            "model": self._model.upper().replace("_", "-"),
        }
