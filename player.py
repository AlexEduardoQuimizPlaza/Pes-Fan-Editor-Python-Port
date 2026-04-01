"""
PES Editor 6 - Python Port
Player class.
"""

START_ADR   = 37116
START_ADR_E = 14288
FIRST_ML    = 4414
FIRST_SHOP  = 4437
FIRST_YOUNG = 4597
FIRST_OLD   = 4774
FIRST_UNUSED = 4784
FIRST_EDIT  = 32768
TOTAL       = 5000
TOTAL_EDIT  = 184
FIRST_CLASSIC = 1312
FIRST_CLUB  = 1473
FIRST_PES_UNITED = 3954


class Player:
    def __init__(self, option_file, index: int, adr: int):
        from stats import get_value, age as age_stat, set_value, call_name, name_edited, call_edited, shirt_edited
        self._of = option_file
        self.index = index
        self.adr   = adr

        if index == 0:
            self.name = "<empty>"
            return

        if index < 0 or (index >= TOTAL and index < FIRST_EDIT) or index > 32951:
            self.name = "<ERROR>"
            self.index = 0
            return

        if index >= FIRST_EDIT:
            a = START_ADR_E
            offset = (index - FIRST_EDIT) * 124
        else:
            a = START_ADR
            offset = index * 124

        name_bytes = bytes(option_file.data[a + offset: a + offset + 32])
        length = 0
        for j in range(0, len(name_bytes) - 1, 2):
            if name_bytes[j] == 0 and name_bytes[j + 1] == 0:
                length = j
                break
        try:
            self.name = name_bytes[:length].decode("utf-16-le")
        except Exception:
            self.name = f"<Error {index}>"

        if not self.name:
            if index >= FIRST_EDIT:
                self.name = f"<Edited {index - FIRST_EDIT}>"
            elif index >= FIRST_UNUSED:
                self.name = f"<Unused {index}>"
            else:
                self.name = f"<L {index}>"

    def __str__(self):
        return self.name

    def __lt__(self, other):
        import stats as s
        if self.name != other.name:
            return self.name < other.name
        return s.get_value(self._of, self.index, s.age) < s.get_value(self._of, other.index, s.age)

    def set_name(self, new_name: str):
        import stats as s
        if self.index == 0 or len(new_name) > 15:
            return
        try:
            encoded = new_name.encode("utf-16-le")
        except Exception:
            encoded = b"\x00" * 30
        name_bytes = bytearray(32)
        copy_len = min(len(encoded), 30)
        name_bytes[:copy_len] = encoded[:copy_len]
        if self.index >= FIRST_EDIT:
            a = START_ADR_E + (self.index - FIRST_EDIT) * 124
        else:
            a = START_ADR + self.index * 124
        self._of.data[a:a+32] = name_bytes
        s.set_value(self._of, self.index, s.call_name, 0xCDCD)
        s.set_value(self._of, self.index, s.name_edited, 1)
        s.set_value(self._of, self.index, s.call_edited, 1)
        self.name = new_name

    def get_shirt_name(self) -> str:
        if self.index >= FIRST_EDIT:
            a = START_ADR_E + 32 + (self.index - FIRST_EDIT) * 124
        else:
            a = START_ADR + 32 + self.index * 124
        if self._of.data[a] == 0:
            return ""
        sb = bytearray(self._of.data[a:a+16])
        for i in range(16):
            if sb[i] == 0:
                sb[i] = ord('!')
        return bytes(sb).decode("latin-1").replace("!", "")

    def set_shirt_name(self, n: str):
        import stats as s
        if len(n) >= 16 or self.index == 0:
            return
        if self.index >= FIRST_EDIT:
            a = START_ADR_E + 32 + (self.index - FIRST_EDIT) * 124
        else:
            a = START_ADR + 32 + self.index * 124
        n = n.upper()
        nb = bytearray(n.encode("latin-1"))
        for i in range(len(nb)):
            if not (65 <= nb[i] <= 90) and nb[i] not in (46, 32, 95):
                nb[i] = 32
        t = bytearray(16)
        t[:len(nb)] = nb
        self._of.data[a:a+16] = t
        s.set_value(self._of, self.index, s.shirt_edited, 1)

    def make_shirt(self, n: str):
        length = len(n)
        if 5 < length < 9:
            spaces = " "
        elif 3 < length <= 5:
            spaces = "  "
        elif length == 3:
            spaces = "    "
        elif length == 2:
            spaces = "        "
        else:
            spaces = ""
        n = n.upper()
        nb = bytearray(n.encode("latin-1"))
        for i in range(len(nb)):
            if not (65 <= nb[i] <= 90) and nb[i] not in (46, 32, 95):
                nb[i] = 32
        n = nb.decode("latin-1")
        result = ""
        for i in range(len(n) - 1):
            result += n[i] + spaces
        result += n[-1] if n else ""
        self.set_shirt_name(result)
