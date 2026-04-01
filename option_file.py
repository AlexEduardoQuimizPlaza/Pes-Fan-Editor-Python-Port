"""
PES Editor 6 - Python Port
OptionFile: handles reading/writing PES6 binary save files.
Supports XPS (SharkPort), PSU (PowerSave), MAX (MaxSave) and BIN (PC) formats.
"""
import os
import zlib
from typing import Optional

from lzari import Lzari


LENGTH = 1191936

BLOCK = [12, 5144, 9544, 14288, 37116, 657956, 751472, 763804, 911144, 1170520]
BLOCK_SIZE = [4844, 1268, 4730, 22816, 620000, 93501, 12320, 147328, 259364, 21032]

_SHARKPORT = bytes([13, 0, 0, 0, 83, 104, 97, 114, 107, 80, 111, 114, 116, 83, 97, 118, 101, 0, 0, 0, 0])
_MAGIC_MAX = b"Ps2PowerSave"

# 446-entry encryption key (PS2 format)
_KEY = [
    2058578050, 2058578078, 2058578109, 2058578079, 2058578084, 2058578115,
    2058578073, 2058578105, 2058578068, 2058578101, 2058578095, 2058578045,
    2058578100, 2058578111, 2058578096, 2058578068, 2058578101, 2058578117,
    2058578115, 2058578071, 2058578064, 2058578045, 2058578078, 2058578085,
    2058578062, 2058578116, 2058578109, 2058578045, 2058578115, 2058578076,
    2058578049, 2058578093, 2058578066, 2058578051, 2058578082, 2058578114,
    2058578045, 2058578093, 2058578052, 2058578112, 2058578073, 2058578063,
    2058578100, 2058578102, 2058578103, 2058578053, 2058578085, 2058578078,
    2058578077, 2058578115, 2058578076, 2058578086, 2058578116, 2058578111,
    2058578083, 2058578109, 2058578072, 2058578047, 2058578081, 2058578049,
    2058578074, 2058578048, 2058578086, 2058578110, 2058578098, 2058578102,
    2058578105, 2058578050, 2058578046, 2058578086, 2058578095, 2058578083,
    2058578065, 2058578062, 2058578047, 2058578116, 2058578109, 2058578100,
    2058578068, 2058578100, 2058578109, 2058578104, 2058578079, 2058578084,
    2058578084, 2058578083, 2058578084, 2058578098, 2058578096, 2058578070,
    2058578068, 2058578110, 2058578094, 2058578045, 2058578114, 2058578082,
    2058578116, 2058578068, 2058578114, 2058578097, 2058578085, 2058578115,
    2058578072, 2058578068, 2058578047, 2058578099, 2058578076, 2058578101,
    2058578086, 2058578117, 2058578052, 2058578109, 2058578070, 2058578050,
    2058578118, 2058578046, 2058578109, 2058578098, 2058578099, 2058578064,
    2058578048, 2058578103, 2058578069, 2058578075, 2058578068, 2058578085,
    2058578110, 2058578111, 2058578114, 2058578110, 2058578081, 2058578084,
    2058578077, 2058578073, 2058578084, 2058578100, 2058578104, 2058578063,
    2058578083, 2058578049, 2058578065, 2058578109, 2058578105, 2058578099,
    2058578105, 2058578062, 2058578069, 2058578070, 2058578065, 2058578066,
    2058578047, 2058578100, 2058578107, 2058578077, 2058578062, 2058578050,
    2058578113, 2058578080, 2058578065, 2058578083, 2058578095, 2058578111,
    2058578096, 2058578044, 2058578116, 2058578053, 2058578084, 2058578077,
    2058578118, 2058578100, 2058578072, 2058578044, 2058578073, 2058578104,
    2058578117, 2058578074, 2058578069, 2058578110, 2058578050, 2058578045,
    2058578045, 2058578047, 2058578047, 2058578106, 2058578064, 2058578099,
    2058578095, 2058578063, 2058578067, 2058578068, 2058578049, 2058578108,
    2058578098, 2058578115, 2058578099, 2058578097, 2058578106, 2058578097,
    2058578116, 2058578116, 2058578110, 2058578118, 2058578099, 2058578111,
    2058578106, 2058578109, 2058578101, 2058578093, 2058578077, 2058578053,
    2058578061, 2058578098, 2058578050, 2058578086, 2058578104, 2058578098,
    2058578113, 2058578102, 2058578065, 2058578077, 2058578082, 2058578044,
    2058578050, 2058578085, 2058578117, 2058578045, 2058578117, 2058578113,
    2058578082, 2058578051, 2058578110, 2058578103, 2058578096, 2058578069,
    2058578052, 2058578114, 2058578046, 2058578044, 2058578047, 2058578108,
    2058578083, 2058578075, 2058578077, 2058578069, 2058578050, 2058578101,
    2058578063, 2058578082, 2058578052, 2058578108, 2058578106, 2058578109,
    2058578112, 2058578062, 2058578071, 2058578051, 2058578047, 2058578097,
    2058578062, 2058578100, 2058578048, 2058578080, 2058578080, 2058578077,
    2058578047, 2058578048, 2058578096, 2058578100, 2058578118, 2058578105,
    2058578096, 2058578072, 2058578085, 2058578084, 2058578061, 2058578114,
    2058578044, 2058578049, 2058578053, 2058578093, 2058578064, 2058578049,
    2058578083, 2058578069, 2058578073, 2058578104, 2058578080, 2058578098,
    2058578103, 2058578093, 2058578049, 2058578044, 2058578099, 2058578094,
    2058578070, 2058578103, 2058578070, 2058578062, 2058578078, 2058578102,
    2058578104, 2058578109, 2058578068, 2058578067, 2058578108, 2058578108,
    2058578076, 2058578086, 2058578053, 2058578104, 2058578093, 2058578070,
    2058578105, 2058578110, 2058578094, 2058578112, 2058578086, 2058578049,
    2058578101, 2058578086, 2058578108, 2058578071, 2058578095, 2058578079,
    2058578097, 2058578116, 2058578111, 2058578046, 2058578103, 2058578071,
    2058578067, 2058578063, 2058578096, 2058578048, 2058578079, 2058578103,
    2058578068, 2058578114, 2058578079, 2058578072, 2058578102, 2058578115,
    2058578053, 2058578047, 2058578084, 2058578046, 2058578110, 2058578044,
    2058578108, 2058578101, 2058578078, 2058578073, 2058578086, 2058578049,
    2058578107, 2058578069, 2058578077, 2058578086, 2058578079, 2058578110,
    2058578048, 2058578116, 2058578101, 2058578108, 2058578081, 2058578093,
    2058578113, 2058578065, 2058578045, 2058578080, 2058578109, 2058578075,
    2058578097, 2058578071, 2058578049, 2058578053, 2058578078, 2058578050,
    2058578075, 2058578067, 2058578083, 2058578061, 2058578116, 2058578116,
    2058578075, 2058578093, 2058578116, 2058578100, 2058578093, 2058578052,
    2058578085, 2058578047, 2058578095, 2058578081, 2058578045, 2058578044,
    2058578101, 2058578097, 2058578110, 2058578115, 2058578096, 2058578069,
    2058578053, 2058578050, 2058578112, 2058578085, 2058578104, 2058578082,
    2058578073, 2058578099, 2058578081, 2058578045, 2058578079, 2058578071,
    2058578080, 2058578047, 2058578113, 2058578076, 2058578082, 2058578117,
    2058578086, 2058578046, 2058578099, 2058578068, 2058578074, 2058578108,
    2058578064, 2058578077, 2058578115, 2058578066, 2058578074, 2058578104,
    2058578082, 2058578115, 2058578117, 2058578082, 2058578117, 2058578048,
    2058578053, 2058578107, 2058578079, 2058578116, 2058578081, 2058578086,
    2058578064, 2058577996,
]

# 256-byte XOR key for PC (BIN) format
_KEY_PC = bytes([
    115, 96, 225, 198, 31, 60, 173, 66, 11, 88, 185, 254, 55, 180, 5, 250,
    163, 80, 145, 54, 79, 44, 93, 178, 59, 72, 105, 110, 103, 164, 181, 106,
    211, 64, 65, 166, 127, 28, 13, 34, 107, 56, 25, 222, 151, 148, 101, 218,
    3, 48, 241, 22, 175, 12, 189, 110, 155, 40, 201, 78, 199, 132, 21, 74,
    51, 32, 161, 134, 223, 252, 109, 2, 203, 24, 121, 190, 247, 116, 197, 186,
    99, 16, 81, 246, 15, 236, 29, 114, 251, 8, 41, 46, 39, 100, 117, 42,
    147, 0, 1, 102, 63, 220, 205, 226, 43, 248, 217, 158, 87, 84, 37, 154,
    195, 240, 177, 214, 111, 204, 125, 82, 91, 232, 137, 14, 135, 68, 213, 10,
    243, 224, 97, 70, 159, 188, 45, 194, 139, 216, 57, 126, 183, 52, 133, 122,
    35, 208, 17, 182, 207, 172, 221, 50, 187, 200, 233, 238, 231, 36, 53, 234,
    83, 192, 193, 38, 255, 156, 141, 162, 235, 184, 153, 94, 23, 20, 229, 90,
    131, 176, 113, 150, 47, 140, 61, 18, 27, 168, 73, 206, 71, 4, 149, 202,
    179, 160, 33, 6, 95, 124, 237, 130, 75, 152, 249, 62, 119, 244, 69, 58,
    227, 144, 209, 118, 143, 108, 157, 242, 123, 136, 169, 174, 167, 228, 245,
    170, 19, 128, 129, 230, 191, 92, 77, 98, 171, 120, 89, 30, 215, 212, 165,
    26, 67, 112, 49, 86, 239, 76, 253, 210, 219, 104, 9, 142, 7, 196, 85, 138,
])


def _to_int32(value: int) -> int:
    """Convert to signed 32-bit integer."""
    value = value & 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return value


def _to_uint32(value: int) -> int:
    return value & 0xFFFFFFFF


def _byte_to_int_le(data: bytearray, a: int) -> int:
    """Read 4 bytes as little-endian signed int."""
    v = data[a] | (data[a+1] << 8) | (data[a+2] << 16) | (data[a+3] << 24)
    return _to_int32(v)


def _int_to_bytes_le(v: int) -> bytes:
    v = _to_uint32(v)
    return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF])


def _swab_int(v: int) -> int:
    """Byte-swap a 32-bit integer (big-endian <-> little-endian)."""
    b0 = (v >> 24) & 0xFF
    b1 = (v >> 16) & 0xFF
    b2 = (v >> 8) & 0xFF
    b3 = v & 0xFF
    return b3 | (b2 << 8) | (b1 << 16) | (b0 << 24)


class OptionFile:
    FORMAT_XPS = 0
    FORMAT_BIN = 1
    FORMAT_PSU = 2
    FORMAT_MAX = 3

    def __init__(self):
        self.data = bytearray(LENGTH)
        self._header_data: Optional[bytes] = None
        self.file_name: Optional[str] = None
        self.game_id: Optional[str] = None
        self.game_name: str = ""
        self.save_name: str = ""
        self.notes: str = ""
        self.format: int = -1
        self.file_count: int = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def to_byte(self, i: int) -> int:
        """Clip integer to signed byte range, return as unsigned 0-255."""
        i &= 0xFF
        return i

    def to_int(self, b: int) -> int:
        """Convert a raw byte (possibly negative) to 0-255."""
        return b & 0xFF

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def read(self, path: str) -> bool:
        self.format = -1
        done = True
        ext = _get_extension(path).lower() if _get_extension(path) else ""
        fname = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                raw = f.read()

            if ext == "xps":
                done = self._parse_xps(raw)
            elif ext == "psu":
                done = self._parse_psu(raw)
            elif ext == "max":
                done = self._parse_max(raw)
            else:
                # BIN / PC format
                if fname == "KONAMI-WIN32WEXUOPT":
                    self.game_id = "PC_WE"
                else:
                    self.game_id = "PC_PES"
                self.format = self.FORMAT_BIN
                self.data = bytearray(raw[:LENGTH])
                self._convert_data()  # XOR decrypt PC format

            if done and self.format != -1:
                if self.format != self.FORMAT_MAX:
                    pass  # data already set inside parse methods
                if self.format == self.FORMAT_BIN:
                    pass  # already decrypted via _convert_data above
                self._decrypt()

        except Exception as e:
            print(f"Error reading file: {e}")
            done = False

        self.file_name = os.path.basename(path) if done else None
        return done

    def _parse_xps(self, raw: bytes) -> bool:
        offset = len(raw) - LENGTH - 4
        pos = 21
        size = _swab_int(int.from_bytes(raw[pos:pos+4], "big"))
        pos += 4
        self.game_name = raw[pos:pos+size].decode("iso-8859-1")
        pos += size
        size = _swab_int(int.from_bytes(raw[pos:pos+4], "big"))
        pos += 4
        self.save_name = raw[pos:pos+size].decode("iso-8859-1")
        pos += size
        size = _swab_int(int.from_bytes(raw[pos:pos+4], "big"))
        pos += 4
        self.notes = raw[pos:pos+size].decode("iso-8859-1")
        pos += size
        self._header_data = raw[pos:offset]
        self.game_id = raw[pos+6:pos+25].decode("iso-8859-1")
        self.data = bytearray(raw[offset:offset+LENGTH])
        self.format = self.FORMAT_XPS
        return True

    def _parse_psu(self, raw: bytes) -> bool:
        header_len = len(raw) - LENGTH
        self._header_data = raw[:header_len]
        self.game_id = raw[64:83].decode("iso-8859-1")
        self.data = bytearray(raw[header_len:header_len+LENGTH])
        self.format = self.FORMAT_PSU
        return True

    def _parse_max(self, raw: bytes) -> bool:
        magic = raw[:12]
        if magic != _MAGIC_MAX:
            return False
        stored_crc = int.from_bytes(raw[12:16], "little")
        patched = bytearray(raw)
        patched[12] = patched[13] = patched[14] = patched[15] = 0
        computed = zlib.crc32(bytes(patched)) & 0xFFFFFFFF
        if _to_int32(computed) != _to_int32(stored_crc):
            return False

        self.game_id = raw[16:48].decode("iso-8859-1").rstrip("\x00")
        self.game_name = raw[48:80].decode("iso-8859-1").rstrip("\x00")
        code_size = _swab_int(int.from_bytes(raw[80:84], "big"))
        self.file_count = _swab_int(int.from_bytes(raw[84:88], "big"))
        compressed = raw[88:88+code_size]
        lz = Lzari()
        decompressed = lz.decode(compressed)
        p = 0
        for _ in range(self.file_count):
            size = int.from_bytes(decompressed[p:p+4], "little")
            title = decompressed[p+4:p+23].decode("iso-8859-1")
            if size == LENGTH and title == self.game_id:
                self._header_data = bytes(decompressed[:p+36])
                self.data = bytearray(decompressed[p+36:p+36+LENGTH])
                self.format = self.FORMAT_MAX
                return True
            p = p + 36 + size
            p = ((p + 23) // 16 * 16) - 8
        return False

    # ------------------------------------------------------------------
    # File saving
    # ------------------------------------------------------------------

    def save(self, path: str) -> bool:
        self.data[45] = 1
        self.data[46] = 1
        self.data[5938] = 1
        self.data[5939] = 1
        done = True
        self._encrypt()
        self._check_sums()
        if self.format == self.FORMAT_BIN:
            self._convert_data()
        try:
            with open(path, "wb") as f:
                if self.format == self.FORMAT_XPS:
                    save_name = os.path.splitext(os.path.basename(path))[0]
                    f.write(_SHARKPORT)
                    gn = self.game_name.encode("iso-8859-1")
                    sn = save_name.encode("iso-8859-1")
                    nt = self.notes.encode("iso-8859-1")
                    f.write(_swab_int(len(gn)).to_bytes(4, "big"))
                    f.write(gn)
                    f.write(_swab_int(len(sn)).to_bytes(4, "big"))
                    f.write(sn)
                    f.write(_swab_int(len(nt)).to_bytes(4, "big"))
                    f.write(nt)
                    f.write(self._header_data)
                    f.write(self.data)
                    f.write(b"\x00\x00\x00\x00")
                elif self.format == self.FORMAT_PSU:
                    f.write(self._header_data)
                    f.write(self.data)
                elif self.format == self.FORMAT_MAX:
                    text_size = len(self._header_data) + LENGTH
                    text_size = ((text_size + 23) // 16 * 16) - 8
                    temp = bytearray(text_size)
                    temp[:len(self._header_data)] = self._header_data
                    temp[len(self._header_data):len(self._header_data)+LENGTH] = self.data
                    lz = Lzari()
                    compressed = lz.encode(bytes(temp))
                    code_size = len(compressed)
                    header2 = bytearray(88)
                    header2[:12] = _MAGIC_MAX
                    gi = self.game_id.encode("iso-8859-1")
                    header2[16:16+len(gi)] = gi
                    gn = self.game_name.encode("iso-8859-1")
                    header2[48:48+len(gn)] = gn
                    header2[80:84] = _int_to_bytes_le(code_size)
                    header2[84:88] = _int_to_bytes_le(self.file_count)
                    crc_val = zlib.crc32(bytes(header2)) & 0xFFFFFFFF
                    crc_val = (zlib.crc32(compressed, crc_val)) & 0xFFFFFFFF
                    header2[12:16] = crc_val.to_bytes(4, "little")
                    f.write(header2)
                    f.write(compressed)
                else:
                    f.write(self.data)
        except Exception as e:
            print(f"Error saving file: {e}")
            done = False

        if self.format == self.FORMAT_BIN:
            self._convert_data()
        self._decrypt()
        return done

    # ------------------------------------------------------------------
    # Encryption / Decryption
    # ------------------------------------------------------------------

    def _decrypt(self):
        for i in range(1, 10):
            k = 0
            a = BLOCK[i]
            end = BLOCK[i] + BLOCK_SIZE[i]
            while a + 4 <= end:
                c = _byte_to_int_le(self.data, a)
                # Keep arithmetic in unsigned 32-bit to match Java int overflow behaviour.
                # If we used _to_int32 before the XOR, Python sign-extends the negative
                # value infinitely and the XOR result would differ from Java's 32-bit result.
                p = (_to_uint32(c - _KEY[k]) + 0x7AB3684C) & 0xFFFFFFFF
                p ^= 0x7AB3684C
                self.data[a] = p & 0xFF
                self.data[a+1] = (p >> 8) & 0xFF
                self.data[a+2] = (p >> 16) & 0xFF
                self.data[a+3] = (p >> 24) & 0xFF
                k += 1
                if k == 446:
                    k = 0
                a += 4

    def _encrypt(self):
        for i in range(1, 10):
            k = 0
            a = BLOCK[i]
            end = BLOCK[i] + BLOCK_SIZE[i]
            while a + 4 <= end:
                p = _to_uint32(_byte_to_int_le(self.data, a))
                c = _to_uint32(_KEY[k] + _to_uint32((p ^ 0x7AB3684C) - 0x7AB3684C))
                self.data[a] = c & 0xFF
                self.data[a+1] = (c >> 8) & 0xFF
                self.data[a+2] = (c >> 16) & 0xFF
                self.data[a+3] = (c >> 24) & 0xFF
                k += 1
                if k == 446:
                    k = 0
                a += 4

    def _convert_data(self):
        """XOR cipher for PC (BIN) format."""
        k = 0
        for a in range(LENGTH):
            self.data[a] ^= _KEY_PC[k]
            k = (k + 1) & 0xFF

    def _check_sums(self):
        for i in range(10):
            chk = 0
            a = BLOCK[i]
            end = BLOCK[i] + BLOCK_SIZE[i]
            while a + 4 <= end:
                chk = _to_int32(chk + _byte_to_int_le(self.data, a))
                a += 4
            b = BLOCK[i] - 8
            self.data[b] = chk & 0xFF
            self.data[b+1] = (chk >> 8) & 0xFF
            self.data[b+2] = (chk >> 16) & 0xFF
            self.data[b+3] = (chk >> 24) & 0xFF

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_bytes(self, i: int) -> bytes:
        return bytes([i & 0xFF, (i >> 8) & 0xFF])

    def get_bytes_int(self, i: int) -> bytes:
        return _int_to_bytes_le(i)

    def is_we(self) -> bool:
        return self.game_id in ("BASLUS-21464W2K7OPT", "PC_WE")

    @staticmethod
    def is_ps2_pes(s: str) -> bool:
        return (s.startswith("BESLES-") and s.endswith("PES6OPT")) or s == "BASLUS-21464W2K7OPT"


def _get_extension(path: str) -> Optional[str]:
    _, ext = os.path.splitext(path)
    if ext:
        return ext.lstrip(".")
    return None
