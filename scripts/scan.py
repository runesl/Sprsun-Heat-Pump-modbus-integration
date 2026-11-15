from pymodbus.client import ModbusTcpClient

IP = "192.168.0.19"
client = ModbusTcpClient(IP, port=502, timeout=3)
client.connect()

print("Forbundet – scanner efter 65 / 650 ...\n")

# Scan flere områder
ranges = [
    (0, 100),
    (100, 100),
    (200, 100),
    (300, 100),
    (400, 100),
]

for start, count in ranges:
    result = client.read_holding_registers(start, count=count)
    if not result.isError():
        for i, val in enumerate(result.registers):
            print(f"*** Mulig match: Offset {start + i} = {val}")
    else:
        print(f"Fejl ved {start}: {result}")

client.close()
