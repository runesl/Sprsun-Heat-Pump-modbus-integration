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
