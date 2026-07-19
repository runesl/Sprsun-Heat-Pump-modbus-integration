import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)


class HeatPumpModbusClient:

    def __init__(self, host: str, port: int, unit_id: int):
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    async def connect(self):
        if self._client is not None and getattr(self._client, "connected", False):
            return

        _LOGGER.info("Connecting to Modbus heat pump tcp://%s:%s (unit_id=%s)", self._host, self._port, self._unit_id)
        
        try:
            self._client = AsyncModbusTcpClient(
                host=self._host,
                port=self._port,
                timeout=5,
            )
            _LOGGER.debug("AsyncModbusTcpClient created successfully")

            # Try to set unit_id via available attributes
            if hasattr(self._client, "unit_id"):
                self._client.unit_id = self._unit_id
                _LOGGER.debug("Set unit_id via unit_id attribute: %s", self._unit_id)
            elif hasattr(self._client, "unit"):
                self._client.unit = self._unit_id
                _LOGGER.debug("Set unit_id via unit attribute: %s", self._unit_id)
            elif hasattr(self._client, "slave"):
                self._client.slave = self._unit_id
                _LOGGER.debug("Set unit_id via slave attribute: %s", self._unit_id)
            else:
                _LOGGER.warning("AsyncModbusTcpClient has no unit_id/unit/slave attribute - "
                               "unit_id may need to be passed per-call in pymodbus 3.x")

            _LOGGER.debug("Calling AsyncModbusTcpClient.connect() for %s:%s with 5s timeout", 
                         self._host, self._port)
            try:
                result = await self._client.connect()
                _LOGGER.debug("AsyncModbusTcpClient.connect() returned: %s (type: %s)", result, type(result).__name__)
            except Exception as connect_err:
                _LOGGER.error("Exception during AsyncModbusTcpClient.connect(): %s (type: %s)", 
                             connect_err, type(connect_err).__name__)
                raise
            
            connected = getattr(self._client, "connected", False)
            _LOGGER.debug("After connect(), client.connected = %s", connected)
            
            if not connected:
                _LOGGER.error("Connection failed: connected attribute is False after await connect(). "
                             "This may mean: (1) Device unreachable at tcp://%s:%s, "
                             "(2) Modbus timeout (configured: 5s), or (3) Protocol error", 
                             self._host, self._port)
                raise ConnectionError("Cannot connect to Modbus heat pump")
            
            _LOGGER.info("Successfully connected to Modbus heat pump tcp://%s:%s", self._host, self._port)
        except TypeError as err:
            _LOGGER.error("Invalid Modbus configuration: port=%s (type %s), unit_id=%s (type %s): %s", 
                         self._port, type(self._port).__name__, self._unit_id, type(self._unit_id).__name__, err)
            raise ConnectionError(f"Invalid Modbus configuration: {err}") from err
        except ConnectionError:
            raise
        except Exception as err:
            _LOGGER.error("Modbus connection error: %s (type: %s)", err, type(err).__name__)
            raise ConnectionError(f"Cannot connect to Modbus heat pump: {err}") from err

    async def close(self):
        """Graceful close of Modbus TCP connection."""
        if self._client is None:
            return

        try:
            # 1. Zamknij transport TCP (najważniejsze)
            if hasattr(self._client, "protocol") and hasattr(self._client.protocol, "transport"):
                transport = self._client.protocol.transport
                if transport is not None:
                    transport.close()

            # 2. Zamknij klienta (jeśli coś jeszcze robi)
            close_method = getattr(self._client, "close", None)
            if callable(close_method):
                result = close_method()
                if hasattr(result, "__await__"):
                    await result

        except Exception as err:
            _LOGGER.warning("Error closing Modbus TCP: %s", err)

        finally:
            self._client = None


    async def read_holding_registers(self, address: int, count: int = 1) -> list[int] | None:

        async with self._lock:
            try:
                if self._client is None or not getattr(self._client, "connected", False):
                    await self.connect()
            except ConnectionError as err:
                _LOGGER.error("Failed to connect to Modbus: %s", err)
                return None

            try:

                rr = await self._client.read_holding_registers(address=address, count=count)
            except ModbusException as err:
                _LOGGER.error("Modbus error reading address %s: %s", address, err)
                return None
            except Exception as err:  # na wypadek innych wyjątków
                _LOGGER.error("Unexpected error reading address %s: %s", address, err)
                return None

            if hasattr(rr, "isError") and rr.isError():
                _LOGGER.error("Modbus error response at address %s: %s", address, rr)
                return None

            if rr is None or not hasattr(rr, "registers"):
                _LOGGER.error("Invalid Modbus response at address %s: %s", address, rr)
                return None

            return rr.registers

    async def read_discrete_inputs(self, address: int, count: int = 1) -> list[int] | None:

        async with self._lock:
            try:
                if self._client is None or not getattr(self._client, "connected", False):
                    await self.connect()
            except ConnectionError as err:
                _LOGGER.error("Failed to connect to Modbus: %s", err)
                return None

            try:
                rr = await self._client.read_discrete_inputs(address=address, count=count)
            except ModbusException as err:
                _LOGGER.error("Modbus error reading DI %s: %s", address, err)
                return None
            except Exception as err:
                _LOGGER.error("Unexpected error reading DI %s: %s", address, err)
                return None

            if hasattr(rr, "isError") and rr.isError():
                _LOGGER.error("Modbus error response DI %s: %s", address, rr)
                return None

            if rr is None or not hasattr(rr, "bits"):
                _LOGGER.error("Invalid Modbus DI response at %s: %s", address, rr)
                return None

            return rr.bits

    async def write_register(self, address: int, value: int):
        """FC6 – write single holding register."""
        async with self._lock:
            try:
                if self._client is None or not getattr(self._client, "connected", False):
                    await self.connect()
            except ConnectionError as err:
                _LOGGER.error("Failed to connect to Modbus: %s", err)
                return False

            try:
                rr = await self._client.write_register(address=address, value=value )
            except Exception as err:
                _LOGGER.error("Modbus error writing register %s: %s", address, err)
                return False

            if hasattr(rr, "isError") and rr.isError():
                _LOGGER.error("Modbus error response writing register %s: %s", address, rr)
                return False

            return True


    async def write_registers(self, address: int, values: list[int]):
        """FC16 – zapis wielu rejestrów holding."""
        async with self._lock:
            try:
                if self._client is None or not getattr(self._client, "connected", False):
                    await self.connect()
            except ConnectionError as err:
                _LOGGER.error("Failed to connect to Modbus: %s", err)
                return False

            try:
                rr = await self._client.write_registers(address=address, values=values )
            except Exception as err:
                _LOGGER.error("Modbus error writing registers %s: %s", address, err)
                return False

            if hasattr(rr, "isError") and rr.isError():
                _LOGGER.error("Modbus error response writing registers %s: %s", address, rr)
                return False

            return True


    async def write_coil(self, address: int, value: bool):
        """FC5 – zapis pojedynczego bitu."""
        async with self._lock:
            try:
                if self._client is None or not getattr(self._client, "connected", False):
                    await self.connect()
            except ConnectionError as err:
                _LOGGER.error("Failed to connect to Modbus: %s", err)
                return False

            try:
                rr = await self._client.write_coil(address=address, value=value )
            except Exception as err:
                _LOGGER.error("Modbus error writing coil %s: %s", address, err)
                return False

            if hasattr(rr, "isError") and rr.isError():
                _LOGGER.error("Modbus error response writing coil %s: %s", address, rr)
                return False

            return True

    async def read_coils(self, address: int, count: int = 1) -> list[bool] | None:
        """FC1 – read coils."""
        async with self._lock:
            try:
                if self._client is None or not getattr(self._client, "connected", False):
                    await self.connect()
            except ConnectionError as err:
                _LOGGER.error("Failed to connect to Modbus: %s", err)
                return None

            try:
                rr = await self._client.read_coils(address=address, count=count)
            except Exception as err:
                _LOGGER.error("Modbus error reading coils %s: %s", address, err)
                return None

            if hasattr(rr, "isError") and rr.isError():
                _LOGGER.error("Modbus error response reading coils %s: %s", address, rr)
                return None

            if rr is None or not hasattr(rr, "bits"):
                _LOGGER.error("Invalid Modbus coils response at %s: %s", address, rr)
                return None

            return rr.bits[:count]   # return list of bools

