"""Temporary compressor setpoints with durable recovery after a restart."""

REGISTERS = (116, 121, 126, 131, 136, 141, 146, 151, 156, 161)
WORK_MODE_REGISTER = 215
DHW_TEMPERATURE_REGISTER = 195
DHW_TEMPERATURE_THRESHOLD = 380  # Tenths of a degree Celsius.
DHW_SPEED = 200


class DhwCompressorOverride:
    """Keep the original temperature curve until every register is restored."""

    def __init__(self, client, store, enabled: bool) -> None:
        self.client = client
        self.store = store
        self.enabled = enabled
        self._original: dict[int, int] | None = None

    async def async_load(self) -> None:
        saved = await self.store.async_load()
        if saved:
            original = {int(address): value for address, value in saved.items()}
            if set(original) != set(REGISTERS) or any(
                type(value) is not int or not 200 <= value <= 700
                for value in original.values()
            ):
                raise ValueError("Invalid saved DHW compressor setpoints")
            self._original = original

    async def async_update(self, registers: dict[int, int], dhw_active: bool | None):
        """Use only fresh register values and a known current work mode."""
        if dhw_active is None:
            return

        override = False
        if self.enabled and dhw_active:
            temperature = registers.get(DHW_TEMPERATURE_REGISTER)
            if type(temperature) is not int or not 0 <= temperature <= 1000:
                return
            override = temperature > DHW_TEMPERATURE_THRESHOLD
        if self._original is None:
            if not override:
                return
            original = {address: registers[address] for address in REGISTERS}
            if any(
                type(value) is not int or not 200 <= value <= 700
                for value in original.values()
            ):
                raise ValueError("Invalid compressor setpoints; DHW override not applied")
            # Persist all originals before the first write, including partial failures.
            await self.store.async_save(
                {str(address): value for address, value in original.items()}
            )
            self._original = original

        targets = (
            {address: DHW_SPEED for address in REGISTERS}
            if override
            else self._original
        )
        for address, value in targets.items():
            if registers.get(address) == value:
                continue
            if not await self.client.write_register(address, value):
                raise RuntimeError(f"Failed to write compressor register {address}")
            result = await self.client.read_holding_registers(address, 1)
            if result != [value]:
                raise RuntimeError(f"Failed to verify compressor register {address}")
            registers[address] = value

        if not override:
            await self.store.async_save({})
            self._original = None
