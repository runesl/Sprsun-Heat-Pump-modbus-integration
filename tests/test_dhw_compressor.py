"""Run with python3 -m unittest discover -s tests."""

import ast
from datetime import timedelta
import importlib.util
import logging
from pathlib import Path
import unittest
from unittest.mock import AsyncMock


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components/sprsun/dhw_compressor.py"
)
spec = importlib.util.spec_from_file_location("dhw_compressor", SOURCE)
dhw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dhw)


class DhwCompressorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original = {
            address: 300 + index * 10
            for index, address in enumerate(dhw.REGISTERS)
        }
        self.hardware = dict(self.original)
        self.disk = {}
        self.fail_write = None

        async def save(data):
            self.disk = dict(data)

        async def write(address, value):
            self.assertTrue(self.disk, "Originals must be durable before writing")
            if address == self.fail_write:
                return False
            self.hardware[address] = value
            return True

        async def read(address, count):
            return [self.hardware[address]]

        self.store = AsyncMock()
        self.store.async_load.side_effect = lambda: dict(self.disk)
        self.store.async_save.side_effect = save
        self.client = AsyncMock()
        self.client.write_register.side_effect = write
        self.client.read_holding_registers.side_effect = read
        self.controller = dhw.DhwCompressorOverride(self.client, self.store, True)
        await self.controller.async_load()

    async def update(self, active, controller=None, temperature=450):
        readings = {
            **self.hardware,
            dhw.DHW_TEMPERATURE_REGISTER: temperature,
        }
        await (controller or self.controller).async_update(readings, active)
        self.assertEqual(
            {address: readings[address] for address in self.hardware}, self.hardware
        )

    async def test_temperature_threshold_and_restoration_during_dhw(self):
        for temperature in (300, 379, 380):
            await self.update(True, temperature=temperature)
        self.client.write_register.assert_not_awaited()
        self.store.async_save.assert_not_awaited()

        await self.update(True, temperature=381)
        self.assertEqual(set(self.hardware.values()), {200})
        await self.update(True, temperature=380)
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(self.disk, {})

        self.hardware[dhw.REGISTERS[0]] = 420
        await self.update(True, temperature=390)
        await self.update(True, temperature=370)
        self.assertEqual(self.hardware[dhw.REGISTERS[0]], 420)
        self.assertEqual(self.disk, {})

    async def test_invalid_temperature_does_not_apply_or_restore_during_dhw(self):
        for temperature in (None, -1, 65535):
            await self.update(True, temperature=temperature)
        readings = dict(self.hardware)
        await self.controller.async_update(readings, True)
        self.client.write_register.assert_not_awaited()
        await self.update(True)
        self.client.write_register.reset_mock()
        for temperature in (None, -1, 65535):
            await self.update(True, temperature=temperature)
        self.client.write_register.assert_not_awaited()
        self.assertEqual(len(self.disk), 10)
        await self.update(False, temperature=None)
        self.assertEqual(self.hardware, self.original)

    async def test_restart_below_threshold_restores_saved_originals(self):
        await self.update(True)
        restarted = dhw.DhwCompressorOverride(self.client, self.store, True)
        await restarted.async_load()
        await self.update(True, restarted, temperature=380)
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(self.disk, {})

    async def test_complete_cycle_and_no_repeated_writes(self):
        await self.update(False)
        self.client.write_register.assert_not_awaited()
        await self.update(True)
        self.assertEqual(set(self.hardware.values()), {200})
        saved = dict(self.disk)
        await self.update(True)
        self.assertEqual(self.client.write_register.await_count, 10)
        self.assertEqual(self.disk, saved)
        await self.update(False)
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(self.disk, {})
        self.assertEqual(self.client.write_register.await_count, 20)

    async def test_restart_during_dhw_keeps_originals_until_dhw_ends(self):
        await self.update(True)
        restarted = dhw.DhwCompressorOverride(self.client, self.store, True)
        await restarted.async_load()
        await self.update(True, restarted)
        self.assertEqual(set(self.hardware.values()), {200})
        self.assertEqual(
            self.disk, {str(k): v for k, v in self.original.items()}
        )
        await self.update(False, restarted)
        self.assertEqual(self.hardware, self.original)

    async def test_startup_waits_for_valid_work_mode_before_restoring(self):
        await self.update(True)
        restarted = dhw.DhwCompressorOverride(self.client, self.store, True)
        await restarted.async_load()
        self.client.write_register.reset_mock()
        await self.update(None, restarted)
        self.client.write_register.assert_not_awaited()
        self.assertEqual(set(self.hardware.values()), {200})
        await self.update(False, restarted)
        self.assertEqual(self.hardware, self.original)

    async def test_restart_after_partial_override_restores_all(self):
        self.fail_write = dhw.REGISTERS[4]
        with self.assertRaises(RuntimeError):
            await self.update(True)
        self.assertEqual(len(self.disk), 10)
        self.fail_write = None
        restarted = dhw.DhwCompressorOverride(self.client, self.store, True)
        await restarted.async_load()
        await self.update(False, restarted)
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(self.disk, {})

    async def test_partial_restore_is_retried_after_restart(self):
        await self.update(True)
        self.fail_write = dhw.REGISTERS[4]
        with self.assertRaises(RuntimeError):
            await self.update(False)
        self.assertEqual(len(self.disk), 10)
        self.fail_write = None
        restarted = dhw.DhwCompressorOverride(self.client, self.store, True)
        await restarted.async_load()
        await self.update(False, restarted)
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(self.disk, {})

    async def test_no_writes_without_valid_work_mode(self):
        await self.update(None)
        self.client.write_register.assert_not_awaited()
        await self.update(True)
        self.client.write_register.reset_mock()
        await self.update(None)
        self.client.write_register.assert_not_awaited()
        self.assertEqual(len(self.disk), 10)

    async def test_disabling_restores_even_during_dhw(self):
        await self.update(True)
        disabled = dhw.DhwCompressorOverride(self.client, self.store, False)
        await disabled.async_load()
        await self.update(True, disabled)
        self.assertEqual(self.hardware, self.original)
        self.client.write_register.reset_mock()
        await self.update(True, disabled)
        self.client.write_register.assert_not_awaited()

    async def test_storage_failure_prevents_writes(self):
        self.store.async_save.side_effect = OSError("Disk full")
        with self.assertRaises(OSError):
            await self.update(True)
        self.client.write_register.assert_not_awaited()
        self.assertEqual(self.hardware, self.original)

    async def test_verification_failure_keeps_backup_for_retry(self):
        self.client.read_holding_registers.side_effect = None
        self.client.read_holding_registers.return_value = None
        with self.assertRaises(RuntimeError):
            await self.update(True)
        self.assertEqual(len(self.disk), 10)
        self.assertEqual(self.controller._original, self.original)

    async def test_invalid_or_incomplete_originals_prevent_writes(self):
        for invalid in ({}, {**self.original, dhw.REGISTERS[0]: 0}):
            with self.assertRaises((KeyError, ValueError)):
                await self.controller.async_update(
                    {**invalid, dhw.DHW_TEMPERATURE_REGISTER: 450}, True
                )
        self.client.write_register.assert_not_awaited()
        self.store.async_save.assert_not_awaited()

    async def test_corrupt_backup_prevents_loading_and_writes(self):
        self.disk = {str(dhw.REGISTERS[0]): 300}
        with self.assertRaises(ValueError):
            await self.controller.async_load()
        self.client.write_register.assert_not_awaited()

    async def test_failed_backup_clear_can_be_retried(self):
        await self.update(True)
        save = self.store.async_save.side_effect
        self.store.async_save.side_effect = OSError("Disk full")
        with self.assertRaises(OSError):
            await self.update(False)
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(len(self.disk), 10)
        self.store.async_save.side_effect = save
        await self.update(False)
        self.assertEqual(self.disk, {})

    def make_coordinator(self, work_mode, temperature=450):
        """Exercise the real polling cycle without requiring an HA installation."""
        class CoordinatorBase:
            def __init__(self, *args, **kwargs):
                pass

            def async_set_updated_data(self, data):
                self.data = data

        source = SOURCE.with_name("coordinator.py")
        classes = [
            node for node in ast.parse(source.read_text()).body
            if isinstance(node, ast.ClassDef)
        ]
        namespace = {
            "HomeAssistant": object,
            "DataUpdateCoordinator": CoordinatorBase,
            "UpdateFailed": RuntimeError,
            "timedelta": timedelta,
            "_LOGGER": logging.getLogger("test.coordinator"),
            "DOMAIN": "sprsun",
            "DEFAULT_SCAN_INTERVAL": 30,
            "WORK_MODE_REGISTER": dhw.WORK_MODE_REGISTER,
        }
        exec(
            compile(ast.Module(body=classes, type_ignores=[]), str(source), "exec"),
            namespace,
        )

        async def read(address, count):
            data = {
                **self.hardware,
                dhw.WORK_MODE_REGISTER: work_mode,
                dhw.DHW_TEMPERATURE_REGISTER: temperature,
            }
            return [
                data.get(i, 0)
                for i in range(address, address + count)
            ]

        self.client.read_holding_registers.side_effect = read
        self.client.read_coils.side_effect = lambda address, count: [False] * count
        self.client.read_discrete_inputs.side_effect = (
            lambda address, count: [False] * count
        )
        return namespace["SprsunCoordinator"](
            None, self.client, "entry", "cgk_050v3l", 30,
            dhw_compressor=self.controller,
        )

    async def test_polling_cycle_applies_and_publishes_verified_values(self):
        coordinator = self.make_coordinator(2)
        data = await coordinator._async_update_data()
        self.assertEqual(data[dhw.WORK_MODE_REGISTER], 2)
        self.assertFalse(coordinator.data_discrete[11][0])
        self.assertTrue(all(data[address] == 200 for address in dhw.REGISTERS))
        coordinator = self.make_coordinator(1)
        self.client.read_discrete_inputs.side_effect = (
            lambda address, count: [True] * count
        )
        data = await coordinator._async_update_data()
        self.assertEqual(
            {address: data[address] for address in dhw.REGISTERS}, self.original
        )

    async def test_polling_cycle_uses_raw_dhw_temperature(self):
        for temperature in (380, 381, 379):
            coordinator = self.make_coordinator(2, temperature)
            data = await coordinator._async_update_data()
            expected = (
                {address: 200 for address in dhw.REGISTERS}
                if temperature > 380 else self.original
            )
            self.assertEqual(
                {address: data[address] for address in dhw.REGISTERS}, expected
            )

    async def test_discrete_input_failure_does_not_prevent_work_mode_restore(self):
        for failed_address in (0, 120):
            await self.update(True)
            coordinator = self.make_coordinator(1)
            self.client.read_discrete_inputs.side_effect = (
                lambda address, count: None
                if address == failed_address else [False] * count
            )
            self.client.write_register.reset_mock()
            with self.assertLogs("test.coordinator", level="WARNING"):
                await coordinator._async_update_data()
            self.assertEqual(self.hardware, self.original)
            self.assertIsNone(coordinator.data_discrete)
            self.assertEqual(self.disk, {})

    async def test_incomplete_coil_blocks_are_discarded_and_recover(self):
        for failed_address in (0, 120):
            for failure in ("missing", "empty", "short"):
                with self.subTest(address=failed_address, failure=failure):
                    await self.update(True)
                    coordinator = self.make_coordinator(1)
                    coordinator.data_coils = {0: True, 120: True}

                    def read_coils(address, count):
                        if address != failed_address:
                            return [True] * count
                        if failure == "missing":
                            return None
                        return [True] * (count - 1 if failure == "short" else 0)

                    self.client.read_coils.side_effect = read_coils
                    with self.assertLogs("test.coordinator", level="WARNING"):
                        data = await coordinator._async_update_data()
                    self.assertEqual(coordinator.data_coils, {})
                    self.assertEqual(data[dhw.WORK_MODE_REGISTER], 1)
                    self.assertEqual(len(coordinator.data_discrete), 200)
                    self.assertEqual(self.hardware, self.original)
                    self.assertEqual(self.disk, {})

                    self.client.read_coils.side_effect = (
                        lambda address, count: [address == 120] * count
                    )
                    await coordinator._async_update_data()
                    self.assertEqual(coordinator.data_coils, {
                        address: address >= 120 for address in range(200)
                    })

    async def test_coil_block_padding_does_not_shift_addresses(self):
        coordinator = self.make_coordinator(1)
        self.client.read_coils.side_effect = lambda address, count: [
            (address + offset) % 3 == 0 for offset in range(count)
        ] + [True] * 8
        await coordinator._async_update_data()
        self.assertEqual(coordinator.data_coils, {
            address: address % 3 == 0 for address in range(200)
        })

    async def test_unknown_work_mode_neither_applies_nor_restores(self):
        for mode in (3, 65535):
            coordinator = self.make_coordinator(mode)
            self.client.write_register.reset_mock()
            await coordinator._async_update_data()
            self.client.write_register.assert_not_awaited()
            self.assertEqual(self.disk, {})
        await self.update(True)
        for mode in (3, 65535):
            coordinator = self.make_coordinator(mode)
            self.client.write_register.reset_mock()
            await coordinator._async_update_data()
            self.client.write_register.assert_not_awaited()
            self.assertEqual(len(self.disk), 10)

    async def test_cooling_mode_restores_originals(self):
        await self.update(True)
        coordinator = self.make_coordinator(0)
        await coordinator._async_update_data()
        self.assertEqual(self.hardware, self.original)
        self.assertEqual(self.disk, {})

    async def test_incomplete_holding_block_prevents_any_override(self):
        coordinator = self.make_coordinator(2)
        self.client.read_holding_registers.side_effect = None
        self.client.read_holding_registers.return_value = [300]
        with self.assertLogs("test.coordinator", level="ERROR"):
            with self.assertRaises(RuntimeError):
                await coordinator._async_update_data()
        self.client.write_register.assert_not_awaited()
