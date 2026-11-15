import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.util import dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import SprsunCoordinator
from .binary_sensor import resolve_source_entity_id

# Importy sensorów rejestrowych
from .models.CGK050V3L.sensors import SENSORS as SENSORS_050
from .models.CGK050V3L.sensors import COUNTERS as COUNTERS_050

# Importy logic sensors
from .models.CGK050V3L.logic_sensors import *

_LOGGER = logging.getLogger(__name__)

MODEL_SENSORS_MAP = {
    "cgk_050v3l": SENSORS_050,
}

MODEL_COUNTERS_MAP = {
    "cgk_050v3l": COUNTERS_050,
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

    entities.extend(
        SprsunCounterSensor(hass, entry.entry_id, model, definition)
        for definition in MODEL_COUNTERS_MAP.get(model, [])
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


class SprsunCounterSensor(RestoreEntity, SensorEntity):
    """Read-only counter based on the integration's binary signals."""

    _attr_should_poll = False

    def __init__(self, hass, entry_id, model, definition):
        self.hass = hass
        self._entry_id = entry_id
        self._model = model
        self._reset = definition.get("reset")
        self._source_sensor = definition.get("source_sensor")
        self._source_compressor = definition.get("source_compressor")
        self._source_fan = definition.get("source_fan")
        for attribute in ("_source_sensor", "_source_compressor", "_source_fan"):
            source = getattr(self, attribute)
            if source:
                setattr(self, attribute, source.replace("<model>", model))

        self._value = 0
        self._period = None
        self._defrost_active = False
        self._defrost_start = None
        self._unsub_state = None
        self._unsub_defrost = None
        self._unsub_reset = None

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{DOMAIN}_{model}_counter_{definition['unique_id']}"
        self.entity_id = f"sensor.sprsun_{model}_{definition['unique_id']}"
        self._attr_icon = definition.get("icon")
        self._attr_state_class = "total_increasing" if self._reset is None else None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        for attribute in ("_source_sensor", "_source_compressor", "_source_fan"):
            setattr(
                self, attribute,
                resolve_source_entity_id(self.hass, self._model, getattr(self, attribute)),
            )

        last_state = await self.async_get_last_state()
        self._period = self._period_for(dt_util.now())
        if last_state is not None:
            try:
                self._value = int(float(last_state.state))
            except (TypeError, ValueError, OverflowError):
                self._value = 0
            if self._period is not None:
                restored_period = last_state.attributes.get("counter_period")
                if restored_period is None:
                    restored_period = self._period_for(last_state.last_updated)
                if restored_period != self._period:
                    self._value = 0
        self.async_write_ha_state()

        if self._source_sensor:
            self._unsub_state = async_track_state_change_event(
                self.hass, [self._source_sensor], self._handle_state_change
            )
        if self._source_compressor and self._source_fan:
            self._unsub_defrost = async_track_state_change_event(
                self.hass,
                [self._source_compressor, self._source_fan],
                self._handle_defrost_state_change,
            )
        if self._reset in ("daily", "monthly", "yearly"):
            self._unsub_reset = async_track_time_change(
                self.hass, self._handle_reset_time_event,
                hour=0, minute=0, second=0,
            )

    async def async_will_remove_from_hass(self):
        for attribute in ("_unsub_state", "_unsub_defrost", "_unsub_reset"):
            unsubscribe = getattr(self, attribute)
            if unsubscribe:
                unsubscribe()
                setattr(self, attribute, None)
        await super().async_will_remove_from_hass()

    @property
    def native_value(self):
        return self._value

    @property
    def extra_state_attributes(self):
        return {"counter_period": self._period} if self._period is not None else {}

    def _period_for(self, now):
        date_format = {
            "daily": "%Y-%m-%d",
            "monthly": "%Y-%m",
            "yearly": "%Y",
        }.get(self._reset)
        return dt_util.as_local(now).strftime(date_format) if date_format else None

    async def _handle_reset_time_event(self, now):
        period = self._period_for(now)
        if period is not None and period != self._period:
            self._value = 0
            self._period = period
            self.async_write_ha_state()

    async def _handle_state_change(self, event):
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if old and new and old.state == "off" and new.state == "on":
            await self._handle_reset_time_event(dt_util.now())
            self._value += 1
            self.async_write_ha_state()

    async def _handle_defrost_state_change(self, event):
        """Count a completed compressor-ON/fan-OFF period of at least 60 seconds."""
        now = datetime.now()
        compressor = self.hass.states.get(self._source_compressor)
        fan = self.hass.states.get(self._source_fan)
        if (
            not compressor
            or not fan
            or compressor.state not in ("on", "off")
            or fan.state not in ("on", "off")
        ):
            self._defrost_active = False
            self._defrost_start = None
            return
        if compressor.state == "on" and fan.state == "off":
            if not self._defrost_active:
                self._defrost_active = True
                self._defrost_start = now
            return
        if (
            self._defrost_active
            and self._defrost_start
            and (now - self._defrost_start).total_seconds() >= 60
        ):
            await self._handle_reset_time_event(dt_util.now())
            self._value += 1
            self.async_write_ha_state()
        self._defrost_active = False
        self._defrost_start = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Sprsun varmepumpe {self._model.upper().replace('_', '-')}",
            "manufacturer": "Sprsun",
            "model": self._model.upper().replace("_", "-"),
        }
