from utils import int16_to_hex, extract_float

class Trame:
    def __init__(self, dest, source, f, param, value_hex):
        self.da0 = dest[:2]
        self.da1 = dest[2:]
        self.sa0 = source[:2]
        self.sa1 = source[2:]
        self.f = f
        self.data = f"55 53 45 52 2d 30 30 30 00 34 30 39 35 00 {param} {value_hex}"

        self.l0, self.l1 = self.calculate_length()

    def extract_data(self, dataStruct):
        values = {}
        data_bytes = bytes.fromhex(self.data)

        for key in dataStruct:
            if dataStruct[key]["type"] == int :
                values[key] = data_bytes[dataStruct[key]["index"]]
            else:
                values[key] = extract_float(data_bytes, data_bytes[dataStruct[key]["index"]])

        print(values)

        return values

    def calculate_length(self):
        """Calcule la taille de la trame en fonction des champs DA, SA, F et DATA."""
        size_DA = 2
        size_SA = 2
        size_F = 1
        size_DATA = len(bytes.fromhex(self.data))

        total_size = size_DA + size_SA + size_F + size_DATA
        length_hex = int16_to_hex(total_size)

        return length_hex[:2], length_hex[2:]

    def build(self):
        """Construit la trame complète avec le CRC."""
        trame_crc_hex = f"{self.l0} {self.l1} {self.sa0} {self.sa1} {self.da0} {self.da1} {self.f} {self.data}"
        trame_crc_bytes = bytes.fromhex(trame_crc_hex)

        crc_bytes = self.calculate_crc(trame_crc_bytes)
        trame_hex = f"68 {trame_crc_hex} {crc_bytes.hex()} 16"

        print(trame_hex)

        return bytes.fromhex(trame_hex)

    def calculate_crc(self, data: bytes):
        """Calcule le CRC-CCITT (XModem)."""
        crc = 0x0000
        poly = 0x1021

        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
                crc &= 0xFFFF

        return crc.to_bytes(2, 'big')
