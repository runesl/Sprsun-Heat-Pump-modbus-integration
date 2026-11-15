import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import SprsunCoordinator

# Import definicji binary sensorów per model
from .models.CGK050V3L.binary_sensors import BINARY_SENSORS as BINARY_050

_LOGGER = logging.getLogger(__name__)

MODEL_BINARY_MAP = {
    "cgk_050v3l": BINARY_050,
}


def resolve_source_entity_id(hass, model, source_entity_id):
    """Find a shortnamed source even when HA retains its old entity ID."""
    for definition in MODEL_BINARY_MAP.get(model, []):
        shortname = definition.get("shortname")
        if shortname and source_entity_id == f"binary_sensor.sprsun_{model}_{shortname}":
            unique_id = f"{DOMAIN}_{model}_binary_{definition['address']}"
            return er.async_get(hass).async_get_entity_id(
                "binary_sensor", DOMAIN, unique_id
            ) or source_entity_id
    return source_entity_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Register binary sensors for the model."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SprsunCoordinator = data["coordinator"]
    model: str = data["model"]

    sensors_def = MODEL_BINARY_MAP.get(model, [])
    entities = [
        SprsunBinarySensor(coordinator, entry.entry_id, model, definition)
        for definition in sensors_def
    ]

    async_add_entities(entities)


class SprsunBinarySensor(BinarySensorEntity):
    """Binary sensor based on coordinator and discrete inputs."""

    _attr_should_poll = False

    def __init__(self, coordinator: SprsunCoordinator, entry_id, model, definition):
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._model = model
        self._def = definition

        self._address = definition["address"]
        self._index = definition.get("index", 0)

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{DOMAIN}_{model}_binary_{self._address}"

        shortname = definition.get("shortname", definition["name"])
        slug = slugify(f"sprsun_{model}_{shortname}")
        self.entity_id = f"binary_sensor.{slug}"

        self._attr_device_class = definition.get("device_class")

        self._icon_on = definition.get("icon_on", "mdi:check-circle")
        self._icon_off = definition.get("icon_off", "mdi:alert-circle")

        self._mapping = definition.get("mapping", {})

    async def async_added_to_hass(self):
        """Aktualizacja przy każdej zmianie koordynatora."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    # ---------------------------------------------------------
    # IKONA
    # ---------------------------------------------------------

    @property
    def icon(self):
        return self._icon_on if self.is_on else self._icon_off

    # ---------------------------------------------------------
    # ODCZYT STANU
    # ---------------------------------------------------------

    @property
    def available(self):
        return self.coordinator.last_update_success and self.is_on is not None

    @property
    def is_on(self):
        """Stan z discrete inputs."""
        bits = self.coordinator.data_discrete
        if bits is None:
            return None

        try:
            return bool(bits[self._address][self._index])
        except (IndexError, TypeError):
            return None

    # ---------------------------------------------------------
    # DODATKOWE ATRYBUTY
    # ---------------------------------------------------------

    @property
    def extra_state_attributes(self):
        if not self._mapping:
            return None

        value = 1 if self.is_on else 0
        return {        "description": self._mapping.get(value, "Unknown")}

    # ---------------------------------------------------------
    # DEVICE INFO
    # ---------------------------------------------------------

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Sprsun heat pump {self._model.upper().replace('_', '-')}",
            "manufacturer": "Sprsun",
            "model": self._model.upper().replace('_', '-'),
        }
