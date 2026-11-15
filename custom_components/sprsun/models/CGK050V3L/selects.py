ENTITIES = [
    {
        "name": "Driftstilstand",
        "register": 0,
        "options": {
            0: "Køling",
            1: "Opvarmning",
            2: "Varmtvand",
            3: "Køling + Varmtvand",
            4: "Opvarmning + Varmtvand",
        },
        "icon": "mdi:heat-pump",
    },
    {
        "name": "Cirkulationspumpens tilstand",
        "register": 11,
        "options": {
            0: "Kontinuerlig",
            1: "Behovsstyret (PWM)",
            2: "Interval",
        },
        "icon": "mdi:pump",
    },
    {
        "name": "Ventilatorens driftstilstand",
        "register": 12,
        "options": {
            0: "Dag",
            1: "Nat",
            2: "Varmekurve",
            3: "Service",
        },
        "icon": "mdi:fan",
    },
    {
        "name": "Varmelegeme",
        "register": 323,
        "options": {
            0: "Deaktiveret",
            1: "Kun Varmtvand",
            2: "Kun opvarmning",
            3: "Varmtvand + opvarmning",
            4: "Uafhængig",
        },
        "icons": {
            0: "mdi:radiator-off",
            1: "mdi:water-boiler",
            2: "mdi:radiator",
            3: "mdi:heat-wave",
            4: "mdi:radiator",
        },
    },
    {
        "name": "Ugedag",
        "register": 187,
        "options": {
            1: "Mandag",
            2: "Tirsdag",
            3: "Onsdag",
            4: "Torsdag",
            5: "Fredag",
            6: "Lørdag",
            7: "Søndag",
        },
        "icon": "mdi:timer-edit",
    },
]
