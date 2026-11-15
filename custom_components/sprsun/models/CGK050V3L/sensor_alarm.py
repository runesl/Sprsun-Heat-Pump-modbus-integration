from homeassistant .components .sensor import SensorEntity
from ...const import DOMAIN
import logging
_LOGGER = logging.getLogger(__name__)

# Mapa alarmów: adres → (kod, opis)
ALARM_MAP = {
    13: ("AL001", "Alarmhukommelse fuld"),
    15: ("AL002", "Fejl ved skrivning til hukommelse"),
    16: ("AL003", "Fejl: returtemperaturføler"),
    17: ("AL004", "Fejl: fremløbstemperaturføler"),
    18: ("AL005", "Fejl: udetemperaturføler"),
    19: ("AL006", "Høj kondensatortemperatur"),
    20: ("AL007", "Fejl: vandflowføler"),
    21: ("AL008", "Faseføleralarm"),
    22: ("AL009", "Advarsel: driftstimer enhed"),
    23: ("AL010", "Advarsel: driftstimer cirkulationspumpe"),
    24: ("AL011", "Advarsel: driftstimer kompressor"),
    25: ("AL012", "Advarsel: driftstimer ventilator"),
    26: ("AL013", "Lav overhedning – ventil A"),
    27: ("AL014", "Lav overhedning – ventil B"),
    28: ("AL015", "LOP – ventil A"),
    29: ("AL016", "LOP – ventil B"),
    30: ("AL017", "MOP – ventil A"),
    31: ("AL018", "MOP – ventil B"),
    32: ("AL019", "Fejl: ventil A motor"),
    33: ("AL020", "Fejl: ventil B motor"),
    34: ("AL021", "Lav sugegastemperatur – ventil A"),
    35: ("AL022", "Lav sugegastemperatur – ventil B"),
    36: ("AL023", "Høj kondensatortemperatur"),
    37: ("AL024", "Fejl: føler S1"),
    38: ("AL025", "Fejl: føler S2"),
    39: ("AL026", "Fejl: føler S3"),
    40: ("AL027", "Fejl: føler S4"),
    41: ("AL028", "Lavt batteriniveau"),
    42: ("AL029", "EEPROM‑fejl"),
    43: ("AL030", "EVD ikke fuldt lukket"),
    44: ("AL031", "EVD nød‑lukning"),
    45: ("AL032", "EVD firmware inkompatibel"),
    46: ("AL033", "EVD konfigurationsfejl"),
    47: ("AL034", "EVD driver offline"),
    48: ("AL036", "BLDC: kompressor slukket"),
    49: ("AL037", "BLDC: kommunikationsfejl"),
    50: ("AL038", "BLDC: mislykket start"),
    51: ("AL039", "BLDC: startfejl"),
    52: ("AL040", "BLDC: lav trykforskel"),
    53: ("AL041", "BLDC: høj kølemiddeltemperatur"),
    54: ("AL042", "Ramke: for høj kompressorydelse"),
    55: ("AL043", "Ramke: for højt kompressionstryk"),
    56: ("AL044", "Ramke: for høj strøm"),
    57: ("AL045", "Ramke: for højt sugetryk"),
    58: ("AL046", "Ramke: for lav kompressorydelse"),
    59: ("AL047", "Ramke: for lav trykforskel"),
    60: ("AL048", "Ramke: for lavt kompressionstryk"),
    61: ("AL049", "Ramke: for lavt sugetryk"),
    62: ("AL050", "Ramke: for høj kompressionstemperatur"),
    63: ("AL051", "Power+: for høj strøm"),
    64: ("AL052", "Power+: motoroverbelastning"),
    65: ("AL053", "Power+: DC‑bus for højt spænding"),
    66: ("AL054", "Power+: DC‑bus for lavt spænding"),
    67: ("AL055", "Power+: høj drivtemperatur"),
    68: ("AL056", "Power+: lav drivtemperatur"),
    69: ("AL057", "Power+: for høj HW‑strøm"),
    70: ("AL058", "Power+: høj motortemperatur"),
    71: ("AL059", "Power+: IGBT‑modulfejl"),
    72: ("AL060", "Power+: hovedkortfejl"),
    73: ("AL061", "Power+: standardparametre"),
    74: ("AL062", "Power+: DC‑bus støj"),
    75: ("AL063", "Power+: ingen kommunikation"),
    76: ("AL064", "Power+: termistorfejl"),
    77: ("AL065", "Power+: autoreguleringsfejl"),
    78: ("AL066", "Power+: ingen drift"),
    79: ("AL067", "Power+: fasefejl motor"),
    80: ("AL068", "Power+: ventilatorfejl"),
    81: ("AL069", "Power+: hastighedsfejl"),
    82: ("AL070", "Power+: PFC modulfejl"),
    83: ("AL071", "Power+: PFC for højt spænding"),
    84: ("AL072", "Power+: PFC for lavt spænding"),
    85: ("AL073", "Power+: STO‑fejl"),
    86: ("AL074", "Power+: STO‑fejl"),
    87: ("AL075", "Power+: manglende jord"),
    88: ("AL076", "Power+: intern fejl 1"),
    89: ("AL077", "Power+: intern fejl 2"),
    90: ("AL078", "Power+: drivoverbelastning"),
    91: ("AL079", "Power+: sikkerhedsfejl uC"),
    92: ("AL080", "Power+: uventet genstart"),
    93: ("AL081", "Power+: uventet stop"),
    94: ("AL082", "Power+: strømfølerfejl"),
    95: ("AL083", "Power+: ubalanceret strøm"),
    96: ("AL084", "Power+: overbelastning"),
    97: ("AL085", "Power+: STO‑alarm"),
    98: ("AL086", "Power+: STO‑kortfejl"),
    99: ("AL087", "Power+: ingen forsyning"),
    100: ("AL088", "Power+: HV bufferfejl"),
    101: ("AL089", "Power+: HV varmelegeme fejl"),
    102: ("AL090", "Power+: kommunikationsfejl"),
    103: ("AL091", "Power+: kompressorstop"),
    104: ("AL092", "Power+: DC‑bus overbelastning"),
    105: ("AL093", "Power+: DC‑bus HWF‑strøm"),
    106: ("AL094", "Power+: DC‑bus spænding"),
    107: ("AL095", "Power+: DC‑bus HWF‑spænding"),
    108: ("AL096", "Power+: indgangsspænding"),
    109: ("AL097", "Power+: HWF indgangsspænding"),
    110: ("AL098", "Power+: DC‑bus forsyning"),
    111: ("AL099", "Power+: HWF forsyning"),
    112: ("AL100", "Power+: NTC høj temperatur"),
    113: ("AL101", "Power+: NTC lav temperatur"),
    114: ("AL102", "Power+: NTC fejl"),
    115: ("AL103", "Power+: HWF synkronisering"),
    116: ("AL104", "Power+: manglende parameter"),
    117: ("AL105", "Power+: firmwarefejl"),
    118: ("AL106", "Power+: hardwarefejl"),
    119: ("AL107", "Power+: reserveret"),
    120: ("AL108", "Power+: reserveret"),
    121: ("AL109", "Power+: reserveret"),
    122: ("AL110", "Power+: reserveret"),
    123: ("AL111", "Power+: reserveret"),
    124: ("AL112", "Power+: reserveret"),
    125: ("AL113", "Power+: reserveret"),
    126: ("AL114", "Power+: ikke tilsluttet"),
    127: ("AL115", "EEV: lav overhedning"),
    128: ("AL116", "EEV: LOP"),
    129: ("AL117", "EEV: MOP"),
    130: ("AL118", "EEV: høj kondensatortemperatur"),
    131: ("AL119", "EEV: lav kondensatortemperatur"),
    132: ("AL120", "EEV: motorfejl"),
    133: ("AL121", "EEV: autoregulering"),
    134: ("AL122", "EEV: sikkerhedsstop"),
    135: ("AL123", "EEV: temperaturforskel"),
    136: ("AL124", "EEV: trykforskel"),
    137: ("AL125", "EEV: parameterområde"),
    138: ("AL126", "EEV: serviceposition"),
    139: ("AL127", "EEV: ventil‑ID fejl"),
    140: ("AL128", "Lavt tryk"),
    141: ("AL129", "Højt tryk"),
    142: ("AL130", "Fejl: kompressionstemperaturføler"),
    143: ("AL131", "Fejl: sugegastemperaturføler"),
    144: ("AL132", "Fejl: kompressionstrykføler"),
    145: ("AL133", "Fejl: sugetrykføler"),
    146: ("AL134", "Fejl: varmtvandsføler"),
    147: ("AL135", "Fejl: EVI sugegastemperaturføler"),
    148: ("AL136", "Fejl: EVI trykføler"),
    149: ("AL137", "Flowføleralarm"),
    150: ("AL138", "Høj temperaturalarm"),
    151: ("AL139", "Lav temperaturalarm"),
    152: ("AL140", "Temperaturforskel alarm"),
    153: ("AL141", "EVI: parameterområde"),
    154: ("AL142", "EVI: lav overhedning"),
    155: ("AL143", "EVI: LOP"),
    156: ("AL144", "EVI: MOP"),
    157: ("AL145", "EVI: høj kondensatortemperatur"),
    158: ("AL146", "EVI: lavt sugetryk"),
    159: ("AL147", "EVI: motorfejl"),
    160: ("AL148", "EVI: autoregulering"),
    161: ("AL149", "EVI: sikkerhedsstop"),
    162: ("AL150", "EVI: servicepositionsfejl"),
    163: ("AL151", "EVI: ventil‑ID fejl"),
    164: ("AL152", "Strømforsyningsfejl"),
    165: ("AL153", "Ventilator 1 fejl"),
    166: ("AL154", "Ventilator 2 fejl"),
    167: ("AL155", "Ventilatorer frakoblet"),
    168: ("AL165", "Slave 1 frakoblet"),
    169: ("AL166", "Master frakoblet"),
    170: ("AL167", "Slave 2 frakoblet"),
    171: ("AL168", "Slave 3 frakoblet"),
    172: ("AL169", "Slave 4 frakoblet"),
    173: ("AL170", "Slave 5 frakoblet"),
    174: ("AL171", "Slave 6 frakoblet"),
    175: ("AL172", "Slave 7 frakoblet"),
    176: ("AL173", "Slave 8 frakoblet"),
    177: ("AL174", "Slave 9 frakoblet"),
}


class SprsunActiveAlarmsSensor(SensorEntity):
    """Sensor zbiorczy pokazujący aktywne alarmy."""

    _attr_should_poll = False
    _attr_name = "Aktive alarmer"

    def __init__(self, coordinator, entry_id, model):
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._model = model
        self._attr_unique_id = f"sprsun_{model}_active_alarms"
        self.entity_id = f"sensor.sprsun_{model}_active_alarms"

    async def async_added_to_hass(self):
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Sprsun varmepumpe {self._model.upper().replace('_', '-')}",
            "manufacturer": "Sprsun",
            "model": self._model.upper().replace('_', '-'),
        }

    @property
    def available(self):
        return self._coordinator.last_update_success and self._coordinator.data_discrete is not None

    @property
    def _active_alarms(self):
        active = []
        if not self._coordinator.data_discrete:
            return active
        
        for address, info in ALARM_MAP.items():
            if address < len(self._coordinator.data_discrete):
                # data_discrete er en liste af lister med bools: [[False], [True], ...]
                if self._coordinator.data_discrete[address][0]:
                    code, desc = info
                    active.append(f"{code} – {desc}")
        return active

    @property
    def icon(self):
        return "mdi:alert-circle" if self._active_alarms else "mdi:check-circle"

    @property
    def state(self):
        alarms = self._active_alarms
        if not alarms:
            return "Ingen"
        return "\n".join(alarms)

    @property
    def extra_state_attributes(self):
        alarms = self._active_alarms
        if not alarms:
            return {"beskrivelser": "Ingen"}

        return {
            "beskrivelser": {
                code: desc
                for code, desc in (
                    alarm.split(" – ", 1) for alarm in alarms
                )
            }
        }
