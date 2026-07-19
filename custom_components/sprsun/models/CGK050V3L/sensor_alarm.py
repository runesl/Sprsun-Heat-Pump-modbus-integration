from homeassistant .components .sensor import SensorEntity 
from ...const import DOMAIN 

# Mapa alarmów: adres → (kod, opis)
ALARM_MAP ={
13 :("AL001","Pamięć alarm zapełniona"),
15 :("AL002","Fejl zapisu pamięci"),
16 :("AL003","Czujnik temperatur powrotu"),
17 :("AL004","Czujnik temperatur zasilania"),
18 :("AL005","Czujnik temperatur zewnętrznej"),
19 :("AL006","Temperatura skraplacza"),
20 :("AL007","Flowsensor wody"),
21 :("AL008","Alarm sensor faz"),
22 :("AL009","Advarsel godz. jednostki"),
23 :("AL010","Advarsel godz. pompy ob."),
24 :("AL011","Advarsel godz. sprężarki"),
25 :("AL012","Advarsel godz. wentylatora"),
26 :("AL013","Lav przegrz. - Zaw.A"),
27 :("AL014","Lav przegrz. - Zaw.B"),
28 :("AL015","LOP - Vlv.A"),
29 :("AL016","LOP - Vlv.B"),
30 :("AL017","MOP - Vlv.A"),
31 :("AL018","MOP - Vlv.B"),
32 :("AL019","Fejl napęd. Zaw.A"),
33 :("AL020","Fejl napęd. Zaw.B"),
34 :("AL021","Niska temperatur ssania Zaw.A"),
35 :("AL022","Niska temperatur ssania Zaw.B"),
36 :("AL023","Wysoka temperatur skraplacza"),
37 :("AL024","Fejl på sonde S1"),
38 :("AL025","Fejl på sonde S2"),
39 :("AL026","Fejl på sonde S3"),
40 :("AL027","Fejl på sonde S4"),
41 :("AL028","Afladet batteri"),
42 :("AL029","EEPROM"),
43 :("AL030","Ufuldstændig lukning af EVD"),
44 :("AL031","Nødstop lukning af EVD"),
45 :("AL032","FW not compatible EVD"),
46 :("AL033","Fejl konfiguracji EVD"),
47 :("AL034","EVD driver offline"),
48 :("AL035","BLDC za wysoka różnica ciśnień"),
48 :("AL036","BLDC wył sprężarka"),
49 :("AL037","BLCD Fejl transmisji"),
50 :("AL038","BLCD nieudane uruchomienie"),
51 :("AL039","BLCD Fejl uruchamiania"),
52 :("AL040","BLCD niska różnica ciśnień"),
53 :("AL041","BLCD za wysoka temperatur czynnika"),
54 :("AL042","Ramka: za wysoka wydajność sprężarki"),
55 :("AL043","Ramka: za wysokie ciśnienie sprężania"),
56 :("AL044","Ramka: za wysoki prąd"),
57 :("AL045","Ramka: za wysokie ciśnienie ssania"),
58 :("AL046","Ramka: za niska wydajność sprężarki"),
59 :("AL047","Ramka: za niska różnica ciśnień"),
60 :("AL048","Ramka: za niskie ciśnienie sprężania"),
61 :("AL049","Ramka: za niskie ciśnienie ssania"),
62 :("AL050","Ramka: za wysoka temperatur sprężania"),
63 :("AL051","Power+ Alarm: 01 - za duży prąd"),
64 :("AL052","Power+ Alarm: 02 - przeciążenie silnika"),
65 :("AL053","Power+ Alarm: 03 - DCbus za wysokie napięcie"),
66 :("AL054","Power+ Alarm: 04 - DCbus za niskie napięcie"),
67 :("AL055","Power+ Alarm: 05 - za wysoka temperatur napędu"),
68 :("AL056","Power+ Alarm: 06 - za niska temperatur napędu"),
69 :("AL057","Power+ Alarm: 07 - za duży prąd HW"),
70 :("AL058","Power+ Alarm: 08 - za wysoka temperatur silnika"),
71 :("AL059","Power+ Alarm: 09 - Fejl modułu IGBT"),
72 :("AL060","Power+ Alarm: 10 - Fejl płyty głównej"),
73 :("AL061","Power+ Alarm: 11 - domyślne parametry"),
74 :("AL062","Power+ Alarm: 12 - DCbus zakłócenia"),
75 :("AL063","Power+ Alarm: 13 - brak komunikacji"),
76 :("AL064","Power+ Alarm: 14 - Fejl termistora"),
77 :("AL065","Power+ Alarm: 15 - Fejl autoregulacji"),
78 :("AL066","Power+ Alarm: 16 - brak napędu"),
79 :("AL067","Power+ Alarm: 17 - Fejl fazy silnika"),
80 :("AL068","Power+ Alarm: 18 Fejl wentylatora"),
81 :("AL069","Power+ Alarm: 19 - Fejl prędkości"),
82 :("AL070","Power+ Alarm: 20 - Fejl modułu PFC"),
83 :("AL071","Power+ Alarm: 21 - za wysokie napięcie PFC"),
84 :("AL072","Power+ Alarm: 22 - za niskie napięcie PFC"),
85 :("AL073","Power+ Alarm: 23 - Fejl STO"),
86 :("AL074","Power+ Alarm: 24 - Fejl STO"),
87 :("AL075","Power+ Alarm: 25 - brak uziemienia"),
88 :("AL076","Power+ Alarm: 26 - Fejl wewnętrzny 1"),
89 :("AL077","Power+ Alarm: 27 - Fejl wewnętrzny 2"),
90 :("AL078","Power+ Alarm: 28 - przeciążenie napędu"),
91 :("AL079","Power+ Alarm: 29 - Fejl bezpieczeństwa uC"),
92 :("AL080","Power+ Alarm: 98 - nieoczekiwany restart"),
93 :("AL081","Power+ Alarm: 99 - nieoczekiwane zatrzymanie"),
94 :("AL082","Power+ alarm bezpiecz.01 pomiar prądu"),
95 :("AL083","Power+ alarm bezpiecz.02 prąd niezrown."),
96 :("AL084","Power+ alarm bezpiecz.03 przeciążenie"),
97 :("AL085","Power+ alarm bezpiecz.04 alarm STO"),
98 :("AL086","Power+ alarm bezpiecz.05 alarm płyty STO"),
99 :("AL087","Power+ alarm bezpiecz.06 brak zasilania"),
100 :("AL088","Power+ alarm bezpiecz.07 Fejl bufora polec HV"),
101 :("AL089","Power+ alarm bezpiecz.08 Fejl grzałki HV"),
102 :("AL090","Power+ alarm bezpiecz.09 Fejl komunikacji"),
103 :("AL091","Power+ alarm bezpiecz.10 zatrzymanie sprężarki"),
104 :("AL092","Power+ alarm bezpiecz.11 DCbus przeciążenie"),
105 :("AL093","Power+ alarm bezpiecz.12 prąd HWF DCbus"),
106 :("AL094","Power+ alarm bezpiecz.13 napięcie DCbus"),
107 :("AL095","Power+ alarm bezpiecz.14 napięcie HWF DCbus"),
108 :("AL096","Power+ alarm bezpiecz.15 napięcie wejściowe"),
109 :("AL097","Power+ alarm bezpiecz.16 napięcie wejściowe HWF"),
110 :("AL098","Power+ alarm bezpiecz.17 DCbus zasilania"),
111 :("AL099","Power+ alarm bezpiecz.18 HWF zasilanie"),
112 :("AL100","Power+ alarm bezpiecz.19 NTC przekr. temperatur"),
113 :("AL101","Power+ alarm bezpiecz.20 NTC za niska temperatur"),
114 :("AL102","Power+ alarm bezpiecz.21 Fejl NTC"),
115 :("AL103","Power+ alarm bezpiecz.22 Synchronizacja HWF"),
116 :("AL104","Power+ alarm bezpiecz.23 brak parametru"),
117 :("AL105","Power+ alarm bezpiecz.24 Fejl FW"),
118 :("AL106","Power+ alarm bezpiecz.25 Fejl HW"),
119 :("AL107","Power+ alarm bezpiecz.26 zarezerwowany"),
120 :("AL108","Power+ alarm bezpiecz.27 zarezerwowany"),
121 :("AL109","Power+ alarm bezpiecz.28 zarezerwowany"),
122 :("AL110","Power+ alarm bezpiecz.29 zarezerwowany"),
123 :("AL111","Power+ alarm bezpiecz.30 zarezerwowany"),
124 :("AL112","Power+ alarm bezpiecz.31 zarezerwowany"),
125 :("AL113","Power+ alarm bezpiecz.32 zarezerwowany"),
126 :("AL114","Power+ alarm: Power+ niepodłączony"),
127 :("AL115","EEV: niskie przegrzanie"),
128 :("AL116","EEV:LOP"),
129 :("AL117","EEV: MOP"),
130 :("AL118","EEV: wysoka temperatur skraplacza"),
131 :("AL119","EEV: niska temperatur skraplacza"),
132 :("AL120","EEV: Fejl silnika"),
133 :("AL121","EEV: samoregulacja"),
134 :("AL122","EEV: wyłączenie bezpieczeństwa"),
135 :("AL123","EEV: różnica temperatur"),
136 :("AL124","EEV: różnica ciśnień"),
137 :("AL125","EEV: zakres parametrów"),
138 :("AL126","EEV: pozycja serwisowa"),
139 :("AL127","EEV: Fejl ID zaworu"),
140 :("AL128","Lav ciśnienie"),
141 :("AL129","Høj ciśnienie"),
142 :("AL130","Fejl sensor temperatur sprężania"),
143 :("AL131","Fejl sensor temperatur ssania"),
144 :("AL132","Fejl sensor ciśnienia sprężania"),
145 :("AL133","Fejl sensor ciśnienia ssania"),
146 :("AL134","Fejl sensor temperatur zbiornika Varmtvand"),
147 :("AL135","Fejl sensor temperatur ssania EVI"),
148 :("AL136","Fejl sensor ciśnienia EVI"),
149 :("AL137","alarm sensor flow"),
150 :("AL138","alarm wysoka temperatur"),
151 :("AL139","alarm niska temperatur"),
152 :("AL140","alarm różnica temperatur"),
153 :("AL141","EVI alarm: Parameterområdeu"),
154 :("AL142","EVI alarm: Lav przegrzanie"),
155 :("AL143","EVI alarm: LOP"),
156 :("AL144","EVI alarm: MOP"),
157 :("AL145","EVI alarm: wysoka temperatur skraplacza"),
158 :("AL146","EVI alarm: niskie ciśnienie ssania"),
159 :("AL147","EVI alarm: Fejl silnika"),
160 :("AL148","EVI alarm: samoregulacja"),
161 :("AL149","EVI alarm: wyłączenie bezpieczeństwa"),
162 :("AL150","EVI alarm: Fejl pozycji serwisowej"),
163 :("AL151","EVI alarm: Fejl ID zaworu"),
164 :("AL152","Fejl zasilania"),
165 :("AL153","Fejl wentylatora 1"),
166 :("AL154","Fejl wentylatora 2"),
167 :("AL155","Rozłączenie wentylatorów"),
168 :("AL165","Rozłączenie slave 1"),
169 :("AL166","Rozłączenie master"),
170 :("AL167","Rozłączenie slave 2"),
171 :("AL168","Rozłączenie slave 3"),
172 :("AL169","Rozłączenie slave 4"),
173 :("AL170","Rozłączenie slave 5"),
174 :("AL171","Rozłączenie slave 6"),
175 :("AL172","Rozłączenie slave 7"),
176 :("AL173","Rozłączenie slave 8"),
177 :("AL174","Rozłączenie slave 9"),
}


class SprsunActiveAlarmsSensor (SensorEntity ):
    """Sensor zbiorczy pokazujący aktywne alarmy."""

    _attr_should_poll =False 
    _attr_name ="Aktywne alarmy"

    def __init__ (self ,client ,entry_id ,model ):
        self ._client =client 
        self ._entry_id =entry_id 
        self ._model =model 
        self ._active =[]
        self ._attr_available =True 

        self ._attr_unique_id =f"sprsun_{model }_active_alarms"
        self .entity_id =f"sensor.sprsun_{model }_active_alarms"

    @property 
    def device_info (self ):
        return {
        "identifiers":{(DOMAIN ,self ._entry_id )},
        "name":f"Pompa ciepła Sprsun {self ._model .upper ().replace ('_','-')}",
        "manufacturer":"Sprsun",
        "model":self ._model .upper ().replace ('_','-'),
        }

    @property 
    def icon (self ):
        return "mdi:check-circle"if not self ._active else "mdi:alert-circle"

    @property 
    def state (self ):
        if not self ._active :
            return "Brak"
        return "\n".join (self ._active )

    @property 
    def extra_state_attributes (self ):
        if not self ._active :
            return {"opisy":"Brak"}

        return {
        "opisy":{
        code :desc 
        for code ,desc in (
        alarm .split (" – ",1 )for alarm in self ._active 
        )
        }
        }

    async def async_update (self ):
        values =await self ._client .read_discrete_inputs (13 ,165 )

        if not values :
            self ._active =[]
            self ._attr_available =False 
            return 

        active =[]

        for offset ,bit_value in enumerate (values ):
            if bit_value ==1 :
                address =13 +offset 
                alarm =ALARM_MAP .get (address )
                if alarm :
                    code ,desc =alarm 
                    active .append (f"{code } – {desc }")

        self ._active =active 
        self ._attr_available =True 
        self .async_write_ha_state ()
