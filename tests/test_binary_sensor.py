"""Tests for stable IDs of the binary signals used by counters."""

import ast
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "custom_components/sprsun"
MODEL = "cgk_050v3l"
NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)

spec = importlib.util.spec_from_file_location("sprsun_counter", ROOT / "counter.py")
counter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(counter_module)


def definitions(filename, variable):
    tree = ast.parse((ROOT / "models/CGK050V3L" / filename).read_text())
    return ast.literal_eval(next(
        node.value for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == variable
            for target in node.targets
        )
    ))


class FakeRestoreEntity:
    async def async_added_to_hass(self):
        pass

    async def async_get_last_state(self):
        return None

    async def async_will_remove_from_hass(self):
        pass


class FakeSensorEntity:
    def async_write_ha_state(self):
        pass


class BinarySourceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / "binary_sensor.py"
        nodes = [
            node for node in ast.parse(source.read_text()).body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in ("SprsunBinarySensor", "resolve_source_entity_id")
        ]
        namespace = {
            "BinarySensorEntity": object,
            "SprsunCoordinator": object,
            "DOMAIN": "sprsun",
            "slugify": lambda value: value.lower().replace(" ", "_"),
            "MODEL_BINARY_MAP": {
                MODEL: definitions("binary_sensors.py", "BINARY_SENSORS")
            },
        }
        exec(
            compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"),
            namespace,
        )
        sensor_source = ROOT / "sensor.py"
        counter_nodes = [
            node for node in ast.parse(sensor_source.read_text()).body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name == "SprsunCounterSensor"
        ]
        namespace.update({
            "SensorEntity": FakeSensorEntity,
            "RestoreEntity": FakeRestoreEntity,
            "HomeAssistant": object,
            "Counter": counter_module.Counter,
            "dt_util": SimpleNamespace(
                now=lambda: NOW,
                as_local=lambda value: value.astimezone(timezone.utc),
            ),
            "async_track_state_change_event": Mock(return_value=lambda: None),
            "async_track_time_change": Mock(return_value=lambda: None),
        })
        exec(
            compile(
                ast.Module(body=counter_nodes, type_ignores=[]),
                str(sensor_source), "exec",
            ),
            namespace,
        )
        cls.namespace = namespace
        cls.entity_class = namespace["SprsunBinarySensor"]
        cls.counter_class = namespace["SprsunCounterSensor"]
        cls.resolve_source = staticmethod(namespace["resolve_source_entity_id"])
        cls.binary_definitions = definitions("binary_sensors.py", "BINARY_SENSORS")

    def make_entity(self, definition):
        return self.entity_class(
            SimpleNamespace(
                data_discrete=[[False] for _ in range(200)],
                last_update_success=True,
            ),
            "test-entry", MODEL, definition,
        )

    def test_shortnames_and_identity_do_not_depend_on_display_names(self):
        for definition in self.binary_definitions:
            if "shortname" not in definition:
                continue
            with self.subTest(shortname=definition["shortname"]):
                original = self.make_entity(definition)
                renamed = self.make_entity({**definition, "name": "Renamed signal"})
                self.assertEqual(original.entity_id, renamed.entity_id)
                self.assertEqual(original._attr_unique_id, renamed._attr_unique_id)

    def test_counter_sources_resolve_to_defined_binary_signals(self):
        entity_ids = {
            self.make_entity(definition).entity_id
            for definition in self.binary_definitions
        }
        for definition in definitions("sensors.py", "COUNTERS"):
            for key in (
                "source_sensor", "source_compressor", "source_fan"
            ):
                if key in definition:
                    with self.subTest(counter=definition["name"], source=key):
                        source = definition[key].replace("<model>", MODEL)
                        self.assertIn(source, entity_ids)

    def test_restored_status_signals_read_documented_discrete_inputs(self):
        for address, shortname in (
            (179, "compressor_running"), (180, "fan_running"),
            (11, "dhw_valve_active"),
        ):
            with self.subTest(address=address):
                definition = next(
                    item for item in self.binary_definitions
                    if item.get("shortname") == shortname
                )
                entity = self.make_entity(definition)
                self.assertFalse(entity.is_on)
                entity.coordinator.data_discrete[address][0] = True
                self.assertTrue(entity.is_on)

    def test_missing_binary_data_is_unavailable_not_off(self):
        definition = next(
            item for item in self.binary_definitions if item["address"] == 179
        )
        entity = self.make_entity(definition)
        entity.coordinator.data_discrete[179][0] = True
        self.assertTrue(entity.available)
        entity.coordinator.last_update_success = False
        self.assertFalse(entity.available)
        entity.coordinator.last_update_success = True
        for bits in (None, [], [[False]], [[False]] * 179 + [[]]):
            with self.subTest(bits=bits):
                entity.coordinator.data_discrete = bits
                self.assertIsNone(entity.is_on)
                self.assertFalse(entity.available)
        entity.coordinator.data_discrete = [[True] for _ in range(200)]
        self.assertTrue(entity.available)
        self.assertTrue(entity.is_on)

    async def test_counter_does_not_count_connection_recovery_as_a_start(self):
        definition = next(
            item for item in self.binary_definitions if item["address"] == 179
        )
        signal = self.make_entity(definition)
        signal.coordinator.data_discrete[179][0] = True
        counter = self.counter_class(
            object(), "entry", MODEL,
            next(
                item for item in definitions("sensors.py", "COUNTERS")
                if item["unique_id"] == "compressor_starts_total"
            ),
        )

        def state():
            return SimpleNamespace(
                state=("on" if signal.is_on else "off")
                if signal.available else "unavailable"
            )

        old = state()
        for bits in (None, [[True]] * 200, [[False]] * 200, [[True]] * 200):
            signal.coordinator.data_discrete = bits
            new = state()
            await counter._handle_state_change(SimpleNamespace(data={
                "old_state": old, "new_state": new,
            }))
            expected = 1 if old.state == "off" and new.state == "on" else 0
            self.assertEqual(counter.native_value, expected)
            old = new

    def test_unrelated_entities_keep_name_based_ids(self):
        definition = next(
            item for item in self.binary_definitions if item["address"] == 8
        )
        entity = self.make_entity(definition)
        self.assertEqual(
            entity.entity_id, f"binary_sensor.sprsun_{MODEL}_cirkulationspumpe"
        )

    def test_existing_sources_are_found_after_entity_id_changes(self):
        registry = Mock()
        with patch.dict(
            self.namespace, {"er": SimpleNamespace(async_get=lambda hass: registry)}
        ):
            for definition in self.binary_definitions:
                shortname = definition.get("shortname")
                if not shortname:
                    continue
                source = f"binary_sensor.sprsun_{MODEL}_{shortname}"
                for actual_id in ("binary_sensor.old_polish_id", "binary_sensor.new_id"):
                    registry.async_get_entity_id.return_value = actual_id
                    self.assertEqual(
                        self.resolve_source(object(), MODEL, source), actual_id
                    )
                    registry.async_get_entity_id.assert_called_with(
                        "binary_sensor", "sprsun",
                        f"sprsun_{MODEL}_binary_{definition['address']}",
                    )

    def test_new_install_uses_default_source_id(self):
        registry = Mock()
        registry.async_get_entity_id.return_value = None
        source = f"binary_sensor.sprsun_{MODEL}_compressor_running"
        with patch.dict(
            self.namespace, {"er": SimpleNamespace(async_get=lambda hass: registry)}
        ):
            self.assertEqual(self.resolve_source(object(), MODEL, source), source)
            self.assertIsNone(self.resolve_source(object(), MODEL, None))

    def test_counter_ids_are_english_and_independent_of_display_names(self):
        for definition in definitions("sensors.py", "COUNTERS"):
            with self.subTest(counter=definition["name"]):
                original = self.counter_class(object(), "entry", MODEL, definition)
                renamed = self.counter_class(
                    object(), "entry", MODEL,
                    {**definition, "name": "Renamed counter"},
                )
                self.assertEqual(original.entity_id, renamed.entity_id)
                self.assertIsInstance(original, FakeSensorEntity)
                self.assertTrue(original.entity_id.startswith("sensor."))
                self.assertFalse(hasattr(original, "async_set_native_value"))
                self.assertNotIn("ilosc", original.entity_id)
                self.assertNotIn("ilosc", original._attr_unique_id)

    async def test_counter_uses_existing_source_id_and_counts_a_start(self):
        definition = next(
            item for item in definitions("sensors.py", "COUNTERS")
            if item.get("unique_id") == "compressor_starts_total"
        )
        registry = Mock()
        registry.async_get_entity_id.return_value = "binary_sensor.actual_compressor"
        listener = Mock(return_value=lambda: None)
        with patch.dict(self.namespace, {
            "er": SimpleNamespace(async_get=lambda hass: registry),
            "async_track_state_change_event": listener,
        }):
            counter = self.counter_class(object(), "entry", MODEL, definition)
            await counter.async_added_to_hass()
            self.assertEqual(listener.call_args.args[1], ["binary_sensor.actual_compressor"])
            await listener.call_args.args[2](SimpleNamespace(data={
                "old_state": SimpleNamespace(state="off"),
                "new_state": SimpleNamespace(state="on"),
            }))
            self.assertEqual(counter.native_value, 1)

    async def test_defrost_counter_uses_existing_sources(self):
        definition = next(
            item for item in definitions("sensors.py", "COUNTERS")
            if item.get("unique_id") == "defrosts_total"
        )
        actual_ids = {
            f"sprsun_{MODEL}_binary_179": "binary_sensor.actual_compressor",
            f"sprsun_{MODEL}_binary_180": "binary_sensor.actual_fan",
        }
        registry = Mock()
        registry.async_get_entity_id.side_effect = (
            lambda domain, platform, unique_id: actual_ids[unique_id]
        )
        states = {
            "binary_sensor.actual_compressor": SimpleNamespace(state="on"),
            "binary_sensor.actual_fan": SimpleNamespace(state="off"),
        }
        hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
        with patch.dict(
            self.namespace, {"er": SimpleNamespace(async_get=lambda hass: registry)}
        ), patch.object(self.namespace["dt_util"], "now", return_value=NOW) as clock:
            counter = self.counter_class(hass, "entry", MODEL, definition)
            await counter.async_added_to_hass()
            await counter._handle_defrost_state_change(None)
            clock.return_value = NOW + timedelta(seconds=61)
            states["binary_sensor.actual_fan"].state = "on"
            await counter._handle_defrost_state_change(None)
            self.assertEqual(counter.native_value, 1)

    async def test_defrost_counter_discards_ha_unknown_states(self):
        definition = next(
            item for item in definitions("sensors.py", "COUNTERS")
            if item["unique_id"] == "defrosts_total"
        )
        for source in ("_source_compressor", "_source_fan"):
            for invalid_state in ("unknown", "unavailable", None):
                with self.subTest(source=source, invalid_state=invalid_state):
                    states = {}
                    hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
                    counter = self.counter_class(hass, "entry", MODEL, definition)
                    states[counter._source_compressor] = SimpleNamespace(state="on")
                    states[counter._source_fan] = SimpleNamespace(state="off")
                    with patch.object(
                        self.namespace["dt_util"], "now", return_value=NOW
                    ) as clock:
                        await counter._handle_defrost_state_change(None)
                        clock.return_value = NOW + timedelta(seconds=61)
                        states[getattr(counter, source)] = (
                            SimpleNamespace(state=invalid_state)
                            if invalid_state is not None else None
                        )
                        await counter._handle_defrost_state_change(None)
                        self.assertEqual(counter.native_value, 0)
                        states[counter._source_compressor] = SimpleNamespace(state="on")
                        states[counter._source_fan] = SimpleNamespace(state="on")
                        await counter._handle_defrost_state_change(None)
                        self.assertEqual(counter.native_value, 0)

    async def test_daily_sensor_restores_resets_and_unsubscribes_on_unload(self):
        definition = next(
            item for item in definitions("sensors.py", "COUNTERS")
            if item["unique_id"] == "compressor_starts_daily"
        )
        registry = Mock()
        registry.async_get_entity_id.return_value = "binary_sensor.actual_compressor"
        unsubscribe_state = Mock()
        unsubscribe_reset = Mock()
        with patch.dict(self.namespace, {
            "er": SimpleNamespace(async_get=lambda hass: registry),
            "async_track_state_change_event": Mock(return_value=unsubscribe_state),
            "async_track_time_change": Mock(return_value=unsubscribe_reset),
        }):
            counter = self.counter_class(object(), "entry", MODEL, definition)
            counter.async_get_last_state = AsyncMock(
                return_value=SimpleNamespace(
                    state="4", attributes={}, last_updated=NOW
                )
            )
            await counter.async_added_to_hass()
            self.assertEqual(counter.native_value, 4)
            await counter._handle_reset_time_event(
                datetime(2026, 11, 16, tzinfo=timezone.utc)
            )
            self.assertEqual(counter.native_value, 0)
            await counter.async_will_remove_from_hass()
            unsubscribe_state.assert_called_once_with()
            unsubscribe_reset.assert_called_once_with()

    async def test_legacy_restore_uses_home_assistants_local_date(self):
        local_tz = timezone(timedelta(hours=1))
        local_now = datetime(2026, 11, 16, 0, 30, tzinfo=local_tz)
        with patch.dict(self.namespace, {"dt_util": SimpleNamespace(
            now=lambda: local_now,
            as_local=lambda value: value.astimezone(local_tz),
        )}):
            for hour, expected in ((22, 0), (23, 7)):
                with self.subTest(utc_hour=hour):
                    counter = self.counter_class(object(), "entry", MODEL, {
                        "name": "Counter", "unique_id": "test", "reset": "daily",
                    })
                    counter.async_get_last_state = AsyncMock(
                        return_value=SimpleNamespace(
                            state="7", attributes={},
                            last_updated=datetime(
                                2026, 11, 15, hour, 10, tzinfo=timezone.utc
                            ),
                        )
                    )
                    await counter.async_added_to_hass()
                    self.assertEqual(counter.native_value, expected)

    async def test_counter_period_metadata_survives_reload_after_midnight(self):
        next_day = datetime(2026, 11, 16, tzinfo=timezone.utc)
        counter = self.counter_class(object(), "entry", MODEL, {
            "name": "Counter", "unique_id": "test", "reset": "daily",
        })
        counter.async_get_last_state = AsyncMock(return_value=SimpleNamespace(
            state="7", attributes={"counter_period": "2026-11-15"},
            last_updated=NOW,
        ))
        await counter.async_added_to_hass()
        with patch.object(self.namespace["dt_util"], "now", return_value=next_day):
            await counter._handle_state_change(SimpleNamespace(data={
                "old_state": SimpleNamespace(state="off"),
                "new_state": SimpleNamespace(state="on"),
            }))
            self.assertEqual(counter.native_value, 1)
            await counter._handle_reset_time_event(next_day)
            self.assertEqual(counter.native_value, 1)
            restored = self.counter_class(object(), "entry", MODEL, {
                "name": "Counter", "unique_id": "test", "reset": "daily",
            })
            restored.async_get_last_state = AsyncMock(
                return_value=SimpleNamespace(
                    state=str(counter.native_value),
                    attributes=counter.extra_state_attributes,
                    last_updated=NOW,
                )
            )
            await restored.async_added_to_hass()
            self.assertEqual(restored.native_value, 1)

    async def test_platform_setup_places_counters_only_in_sensor_domain(self):
        entry = SimpleNamespace(entry_id="entry")
        coordinator = SimpleNamespace(data={})
        hass = SimpleNamespace(data={
            "sprsun": {"entry": {"coordinator": coordinator, "model": MODEL}}
        })
        sensor_namespace = {
            **self.namespace,
            "ConfigEntry": object,
            "AddEntitiesCallback": object,
            "SprsunCoordinator": object,
            "MODEL_SENSORS_MAP": {MODEL: []},
            "MODEL_COUNTERS_MAP": {MODEL: definitions("sensors.py", "COUNTERS")},
            "MODEL_LOGIC_MAP": {MODEL: {
                key: lambda *args: object()
                for key in ("CompressorRuntime", "FanRuntime", "OwnershipDays")
            }},
            "__import__": lambda *args, **kwargs: SimpleNamespace(
                SprsunActiveAlarmsSensor=lambda *args: object()
            ),
            "_LOGGER": Mock(),
        }
        source = ROOT / "sensor.py"
        setup = next(
            node for node in ast.parse(source.read_text()).body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_setup_entry"
        )
        exec(
            compile(ast.Module(body=[setup], type_ignores=[]), str(source), "exec"),
            sensor_namespace,
        )
        add_sensors = Mock()
        await sensor_namespace["async_setup_entry"](hass, entry, add_sensors)
        counters = [
            entity for entity in add_sensors.call_args.args[0]
            if isinstance(entity, self.counter_class)
        ]
        self.assertEqual(len(counters), 13)
        self.assertEqual(len({entity.entity_id for entity in counters}), 13)

        number_definitions = definitions("numbers.py", "ENTITIES")
        source = ROOT / "number.py"
        setup = next(
            node for node in ast.parse(source.read_text()).body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_setup_entry"
        )
        number_factory = Mock(return_value=object())
        number_namespace = {
            "HomeAssistant": object, "ConfigEntry": object,
            "AddEntitiesCallback": object, "DOMAIN": "sprsun",
            "MODEL_NUMBERS_MAP": {MODEL: number_definitions},
            "SprsunNumberEntity": number_factory,
        }
        exec(
            compile(ast.Module(body=[setup], type_ignores=[]), str(source), "exec"),
            number_namespace,
        )
        add_numbers = Mock()
        await number_namespace["async_setup_entry"](hass, entry, add_numbers)
        self.assertEqual(len(add_numbers.call_args.args[0]), len(number_definitions))
        for factory_call in number_factory.call_args_list:
            self.assertIn("register", factory_call.args[3])
