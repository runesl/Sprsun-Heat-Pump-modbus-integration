"""Tests for number entities without a Home Assistant runtime."""

import ast
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock


class NumberEntityTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        source = (
            Path(__file__).resolve().parents[1]
            / "custom_components/sprsun/number.py"
        )
        tree = ast.parse(source.read_text())
        entity_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "SprsunNumberEntity"
        )
        namespace = {
            "NumberEntity": object,
            "SprsunCoordinator": object,
            "DOMAIN": "sprsun",
            "slugify": lambda value: value,
            "NumberMode": SimpleNamespace(BOX="box", SLIDER="slider"),
            "_LOGGER": logging.getLogger(__name__),
        }
        exec(
            compile(
                ast.Module(body=[entity_class], type_ignores=[]), str(source), "exec"
            ),
            namespace,
        )
        cls.entity_class = namespace["SprsunNumberEntity"]
        model = source.parent / "models/CGK050V3L/numbers.py"
        definitions = next(
            node.value for node in ast.parse(model.read_text()).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "ENTITIES"
                for target in node.targets
            )
        )
        cls.definitions = {
            definition["register"]: definition
            for definition in ast.literal_eval(definitions)
            if "register" in definition
        }

    def make_entity(self, register, raw):
        coordinator = SimpleNamespace(
            data={register: raw},
            client=SimpleNamespace(write_register=AsyncMock(return_value=True)),
            async_request_refresh=AsyncMock(),
        )
        return self.entity_class(
            coordinator, "test-entry", "cgk_050v3l", self.definitions[register]
        )

    def test_description_is_exposed_as_state_attribute(self):
        entity = self.entity_class.__new__(self.entity_class)
        description = "Explanation.\n\nSource: manual, p. 5."
        entity._def = {"description": description}
        self.assertEqual(entity.extra_state_attributes, {"description": description})

    def test_numbers_without_descriptions_have_no_extra_attributes(self):
        entity = self.entity_class.__new__(self.entity_class)
        entity._def = {"register": 81}
        self.assertIsNone(entity.extra_state_attributes)

    def test_defrost_temperatures_decode_sign_and_scale(self):
        for register, raw, expected in (
            (83, 65526, -1.0),
            (83, 65336, -20.0),
            (84, 150, 15.0),
            (85, 65236, -30.0),
            (85, 150, 15.0),
            (86, 70, 7.0),
        ):
            with self.subTest(register=register, raw=raw):
                entity = self.make_entity(register, raw)
                self.assertAlmostEqual(entity.native_value, expected)

    def test_scaled_temperature_input_ranges(self):
        for register, minimum, maximum in (
            (83, -20, 30),
            (84, 0, 30),
            (85, -30, 30),
            (86, 1, 30),
        ):
            with self.subTest(register=register):
                entity = self.make_entity(register, 0)
                self.assertEqual(entity._attr_native_min_value, minimum)
                self.assertEqual(entity._attr_native_max_value, maximum)
                self.assertEqual(entity._attr_native_step, 0.1)

    async def test_temperature_writes_encode_sign_and_round_decimals(self):
        for register, value, expected_raw in (
            (83, -1.0, 65526),
            (83, -0.3, 65533),
            (84, 0.3, 3),
            (85, -30.0, 65236),
            (85, 15.0, 150),
            (86, 7.3, 73),
        ):
            with self.subTest(register=register, value=value):
                entity = self.make_entity(register, 0)
                await entity.async_set_native_value(value)
                entity.coordinator.client.write_register.assert_awaited_once_with(
                    register, expected_raw
                )
                entity.coordinator.async_request_refresh.assert_awaited_once()

    async def test_other_register_conversions_are_preserved(self):
        for register, raw, value in ((13, 50, 50), (81, 650, 65)):
            with self.subTest(register=register):
                entity = self.make_entity(register, raw)
                self.assertEqual(entity.native_value, value)
                await entity.async_set_native_value(value)
                entity.coordinator.client.write_register.assert_awaited_once_with(
                    register, raw
                )
