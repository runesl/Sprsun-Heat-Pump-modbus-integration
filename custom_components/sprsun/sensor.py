import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import SprsunCoordinator

# Importy sensorów rejestrowych
from .models.CGK050V3L.sensors import SENSORS as SENSORS_050

# Importy logic sensors
from .models.CGK050V3L.logic_sensors import *

_LOGGER = logging.getLogger(__name__)

MODEL_SENSORS_MAP = {
    "cgk_050v3l": SENSORS_050,
}

MODEL_LOGIC_MAP = {
    "cgk_050v3l": {
        "CompressorRuntime": SprsunCompressorRuntimeSensor,
        "FanRuntime": SprsunFanRuntimeSensor,
        "OwnershipDays": SprsunOwnershipDaysSensor,
    },
}


# ---------------------------------------------------------
# SETUP ENTRY
# ---------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SprsunCoordinator = data["coordinator"]
    model: str = data["model"]

    sensors_def = MODEL_SENSORS_MAP.get(model)
    if sensors_def is None:
        _LOGGER.error("No sensors for model %s", model)
        return

    entities: list[SensorEntity] = []

    # Sensory rejestrowe (z Modbus)
    for definition in sensors_def:
        entities.append(
            SprsunGenericSensor(
                coordinator,
                entry.entry_id,
                model,
                definition
            )
        )

    # LOGIC SENSORS
    logic = MODEL_LOGIC_MAP[model]

    entities.extend([
        logic["CompressorRuntime"]("Compressor run time daily",
                                   f"{DOMAIN}_{model}_compressor_run_time_daily",
                                   "daily", entry.entry_id, model),
        logic["CompressorRuntime"]("Compressor run time monthly",
                                   f"{DOMAIN}_{model}_compressor_run_time_monthly",
                                   "monthly", entry.entry_id, model),
        logic["CompressorRuntime"]("Compressor run time yearly",
                                   f"{DOMAIN}_{model}_compressor_run_time_yearly",
                                   "yearly", entry.entry_id, model),
        logic["CompressorRuntime"]("Compressor run time total",
                                   f"{DOMAIN}_{model}_compressor_run_time_total",
                                   "total", entry.entry_id, model),

        logic["FanRuntime"]("Fan run time daily",
                            f"{DOMAIN}_{model}_fan_run_time_daily",
                            "daily", entry.entry_id, model),
        logic["FanRuntime"]("Fan run time monthly",
                            f"{DOMAIN}_{model}_fan_run_time_monthly",
                            "monthly", entry.entry_id, model),
        logic["FanRuntime"]("Fan run time yearly",
                            f"{DOMAIN}_{model}_fan_run_time_yearly",
                            "yearly", entry.entry_id, model),
        logic["FanRuntime"]("Fan run time total",
                            f"{DOMAIN}_{model}_fan_run_time_total",
                            "total", entry.entry_id, model),

        logic["OwnershipDays"]("Pump ownership days",
                               f"{DOMAIN}_{model}_pump_ownership_days",
                               entry.entry_id, model),
    ])

    # Active alarms summary sensor (SensorEntity, belongs in sensor domain)
    try:
        model_folder = model.replace("_", "").upper()
        module = __import__(
            f"custom_components.sprsun.models.{model_folder}.sensor_alarm",
            fromlist=["SprsunActiveAlarmsSensor"],
        )
        alarm_class = getattr(module, "SprsunActiveAlarmsSensor")
        entities.append(alarm_class(coordinator, entry.entry_id, model))
    except Exception as err:
        _LOGGER.error("Failed to load alarm sensor: %s", err)

    async_add_entities(entities)


# ---------------------------------------------------------
# SENSOR REJESTROWY (Modbus → koordynator)
# ---------------------------------------------------------

class SprsunGenericSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator: SprsunCoordinator, entry_id, model, definition):
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._model = model
        self._def = definition

        self._register = definition["register"]
        self._scale = definition.get("scale", 1)
        self._signed = definition.get("signed", False)

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{DOMAIN}_{model}_sensor_{self._register}"

        slug = slugify(f"sprsun_{model}_{definition['name']}")

        self.entity_id = f"sensor.{slug}"

        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self._attr_icon = definition.get("icon")
        self._icon_map = definition.get("icon_map")

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self):
        raw = self.coordinator.data.get(self._register)

        if raw is None:
            return None

        if self._signed and raw > 32767:
            raw -= 65536

        raw = raw * self._scale

        mapping = self._def.get("mapping")
        if mapping:
            return mapping.get(raw, raw)

        return raw

    @property
    def icon(self):
        if self._icon_map:
            raw = self.coordinator.data.get(self._register)
            return self._icon_map.get(raw, self._attr_icon)
        return self._attr_icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Pompa ciepła Sprsun {self._model.upper().replace('_', '-')}",
            "manufacturer": "Sprsun",
            "model": self._model.upper().replace('_', '-'),
        }
