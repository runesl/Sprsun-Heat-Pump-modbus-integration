import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import SprsunCoordinator

# Importy buttonów dla wszystkich modeli
from .models.CGK050V3L.buttons import ENTITIES as BUTTONS_050

_LOGGER = logging.getLogger(__name__)

MODEL_BUTTONS_MAP = {
    "cgk_050v3l": BUTTONS_050,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Register buttons for the model."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SprsunCoordinator = data["coordinator"]
    model: str = data["model"]

    buttons_def = MODEL_BUTTONS_MAP.get(model, [])
    entities = [
        SprsunGenericButton(coordinator, entry.entry_id, model, definition)
        for definition in buttons_def
    ]

    async_add_entities(entities)


class SprsunGenericButton(ButtonEntity):
    """Button: write value 1 to Modbus register."""

    _attr_should_poll = False

    def __init__(self, coordinator: SprsunCoordinator, entry_id, model, definition):
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._model = model
        self._def = definition

        self._register = definition["register"]

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{DOMAIN}_{model}_button_{self._register}"
        self._attr_icon = definition.get("icon", "mdi:gesture-tap-button")

        slug = slugify(f"sprsun_{model}_{definition['name']}")
        self.entity_id = f"button.{slug}"

        self._attr_available = True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Sprsun heat pump {self._model.upper().replace('_', '-')}",
            "manufacturer": "Sprsun",
            "model": self._model.upper().replace('_', '-'),
        }

    async def async_press(self) -> None:
        """Pressing the button = write 1 to the register."""
        try:
            await self.coordinator.client.write_register(self._register, 1)
            _LOGGER.info(
                "BUTTON %s: wrote 1 to register %s",
                self._attr_name,
                self._register,
            )
        except Exception as err:
            _LOGGER.error(
                "Error writing button %s (reg %s): %s",
                self._attr_name,
                self._register,
                err,
            )
            self._attr_available = False
