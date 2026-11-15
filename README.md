<b>Integration: Sprsun CGK_V3L – Home Assistant (Modbus / LAN)</b>

This integration enables direct connection of Sprsun CGK_V3L series heat pumps to Home Assistant via Modbus (for example using a Modbus TCP gateway or another converter). The goal is full local control and reading of operating parameters without using cloud services.

Supported models:

CGK025V3L, CGK030V3L, CGK040V3L, CGK050V3L, CGK060V3L

The integration creates the following entity types in Home Assistant:

1. Climate (climate.*)

Features include (among others):

- Setpoint temperatures for:
  - heating
  - cooling
  - domestic hot water (DHW)
- Advanced settings:
  - hysteresis (start/stop) for heating / cooling / DHW
  - heating/cooling curves (X1–X4, Y1–Y4)
  - schedule-based temperature setpoints
  - heater activation temperature
  - Delta T parameter

2. Sensors (sensor.*)

Logical sensors and measurements such as:

- Compressor run time: daily / monthly / yearly / total
- Fan run time: daily / monthly / yearly / total
- Pump ownership days (OwnershipDays)

Counting is based on binary states of existing HA entities (e.g., compressor ON/OFF, fan ON/OFF).

3. Binary sensors (binary_sensor.*)

Examples:

- Power status
- Flow sensor
- Control inputs (external, AC, heating, cooling)

Outputs and states exposed as entities include:

- circulation pump
- circulation pump 2
- compressor
- fan
- 3-/4-way valves
- heaters (cabinet, compressor, main)
- fan speed signals

Additional features:

- dynamic icons depending on state (icon_on / icon_off)
- optional state description mapping (extra_state_attributes["description"])
- active alarms sensor

4. Switches (switch.*)

5. Buttons (button.*)

Examples:

- restore heat pump factory settings
- restore compressor factory parameters

6. Numbers (number.*)

There are two kinds of number entities:

a) Register-backed numbers
b) Logical counters that count transitions such as:
   - (OFF → ON) for a single sensor
   - complex defrost sequences (compressor ON, fan OFF for at least 60 s)

Device grouping and naming in HA:

- Entities are grouped as a single device in HA.
- device_info.identifiers: (DOMAIN, entry_id)
- device name: Sprsun heat pump <MODEL>
- unique_id is built from: DOMAIN, model, entity type and address/register or a key
- entity_id is generated using the pattern sprsun_<model>_<name>
  - names are normalized by removing Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż → a, c, e, l, n, o, s, z, z)
  - spaces are replaced with underscores (_)

This ensures stable, predictable entity identifiers.

Requirements:

- Working Modbus access to the Sprsun heat pump (for example via an RS485–TCP converter or LAN gateway)
- Home Assistant with ability to install custom components (HACS or manual copy to custom_components/sprsun)

Installation (short):

- Copy the sprsun folder into: <config>/custom_components/sprsun
- Restart Home Assistant

In Home Assistant UI:

- Settings → Integrations → Add Integration → choose "Sprsun" (or install via HACS if available)
- Provide Modbus connection parameters according to your pump/gateway configuration
- After successful connection and register read, entities (climate, sensor, binary_sensor, switch, select, number, button) will appear automatically in HA

Logging and debugging:

### Optional DHW compressor limit (CGK050V3L)

Enable the compressor limit during setup or through **Reconfigure** (disabled by
default). While `work_mode` (holding register 215) is 2 (DHW) and the DHW
temperature (register 195, tenths of a degree Celsius) is above 38 C, the
temperature-dependent compressor setpoints in registers 116, 121, 126, 131, 136,
141, 146, 151, 156 and 161 are set to raw value 200 (20 rps, not 20 rpm).
This changes the setpoint curve, not the measured compressor speed.

All ten original values are saved in Home Assistant storage before any write.
They are restored when DHW temperature falls to 38 C or below, when `work_mode`
changes to 0 (cooling) or 1 (heating), or when the option is disabled and the
integration reloads. If the temperature rises above 38 C again during DHW,
the limit is applied again, saving the then-current setpoints.
Writes are read back for verification;
failed operations are retried on subsequent successful polling cycles.
Missing or unknown work mode never triggers restoration. Invalid or missing DHW
temperature leaves the current settings unchanged during DHW. The three-way valve
is not used to control this feature. Do not manually adjust these
setpoints while the override is active: restoration uses the saved originals.

On startup or integration reload, any saved originals are restored at the first
successful polling cycle if DHW is no longer active or the temperature is at or
below 38 C. If DHW is still active above 38 C,
the limit continues. Unknown work mode
does not trigger restoration. Failed restoration is retried without discarding
the backup.
Restoration requires Home Assistant to be running with a working Modbus connection;
while it is offline, the pump keeps the last written settings. Keep the
integration's storage and configuration until restoration has completed.

The integration uses the logger name homeassistant.components.sprsun (the integration domain).

You can increase logging level in configuration.yaml:

```yaml
logger:
  default: warning
  logs:
    custom_components.sprsun: debug
```

Notes:

- Additional pump models that support Modbus may be added over time.
