"""
PES Editor 6 - Python Port
LZARI compression algorithm.
Port of Haruhiko Okumura's LZARI.C (1989).
"""
import io


class Lzari:
    N = 4096       # ring buffer size
    F = 60         # max match length
    THRESHOLD = 2  # min match length to encode as pair
    M = 15
    N_CHAR = 256 - 2 + 60  # = 314

    def __init__(self):
        self._reset()

    def _reset(self):
        NIL = self.N
        self.text_buf = [ord(' ')] * (self.N + self.F - 1)
        self.match_position = 0
        self.match_length = 0
        self.lson = [NIL] * (self.N + 1)
        self.rson = [NIL] * (self.N + 257)
        self.dad  = [NIL] * (self.N + 1)

        Q1 = 1 << self.M
        self.Q1 = Q1
        self.Q2 = 2 * Q1
        self.Q3 = 3 * Q1
        self.Q4 = 4 * Q1
        self.MAX_CUM = Q1 - 1

        self.char_to_sym = [0] * self.N_CHAR
        self.sym_to_char = [0] * (self.N_CHAR + 1)
        self.sym_freq    = [0] * (self.N_CHAR + 1)
        self.sym_cum     = [0] * (self.N_CHAR + 1)
        self.position_cum = [0] * (self.N + 1)

        self.low   = 0
        self.high  = self.Q4
        self.value = 0
        self.shifts = 0

        self.p_buffer = 0
        self.p_mask   = 128
        self.g_buffer = 0
        self.g_mask   = 0

        self.textsize = 0
        self.codesize = 0

    # ------------------------------------------------------------------
    # Bit I/O
    # ------------------------------------------------------------------

    def _put_bit(self, bit):
        if bit:
            self.p_buffer |= self.p_mask
        self.p_mask >>= 1
        if self.p_mask == 0:
            self._outfile.write(bytes([self.p_buffer]))
            self.p_buffer = 0
            self.p_mask = 128
            self.codesize += 1

    def _flush_bit_buffer(self):
        for _ in range(7):
            self._put_bit(0)

    def _get_bit(self):
        self.g_mask >>= 1
        if self.g_mask == 0:
            b = self._infile.read(1)
            self.g_buffer = b[0] if b else 0
            self.g_mask = 128
        return 1 if (self.g_buffer & self.g_mask) else 0

    # ------------------------------------------------------------------
    # Binary search trees
    # ------------------------------------------------------------------

    def _init_tree(self):
        NIL = self.N
        for i in range(self.N + 1, self.N + 257):
            self.rson[i] = NIL
        for i in range(self.N):
            self.dad[i] = NIL

    def _insert_node(self, r):
        NIL = self.N
        cmp = 1
        p = self.N + 1 + self.text_buf[r]
        self.rson[r] = self.lson[r] = NIL
        self.match_length = 0
        while True:
            if cmp >= 0:
                if self.rson[p] != NIL:
                    p = self.rson[p]
                else:
                    self.rson[p] = r
                    self.dad[r] = p
                    return
            else:
                if self.lson[p] != NIL:
                    p = self.lson[p]
                else:
                    self.lson[p] = r
                    self.dad[r] = p
                    return
            cmp = 0
            for i in range(1, self.F):
                cmp = self.text_buf[r + i] - self.text_buf[p + i]
                if cmp != 0:
                    break
            else:
                i = self.F - 1
            if i > self.THRESHOLD:
                if i > self.match_length:
                    self.match_position = (r - p) & (self.N - 1)
                    self.match_length = i
                    if self.match_length >= self.F:
                        break
                elif i == self.match_length:
                    temp = (r - p) & (self.N - 1)
                    if temp < self.match_position:
                        self.match_position = temp
        self.dad[r] = self.dad[p]
        self.lson[r] = self.lson[p]
        self.rson[r] = self.rson[p]
        self.dad[self.lson[p]] = r
        self.dad[self.rson[p]] = r
        if self.rson[self.dad[p]] == p:
            self.rson[self.dad[p]] = r
        else:
            self.lson[self.dad[p]] = r
        self.dad[p] = NIL

    def _delete_node(self, p):
        NIL = self.N
        if self.dad[p] == NIL:
            return
        if self.rson[p] == NIL:
            q = self.lson[p]
        elif self.lson[p] == NIL:
            q = self.rson[p]
        else:
            q = self.lson[p]
            if self.rson[q] != NIL:
                while self.rson[q] != NIL:
                    q = self.rson[q]
                self.rson[self.dad[q]] = self.lson[q]
                self.dad[self.lson[q]] = self.dad[q]
                self.lson[q] = self.lson[p]
                self.dad[self.lson[p]] = q
            self.rson[q] = self.rson[p]
            self.dad[self.rson[p]] = q
        self.dad[q] = self.dad[p]
        if self.rson[self.dad[p]] == p:
            self.rson[self.dad[p]] = q
        else:
            self.lson[self.dad[p]] = q
        self.dad[p] = NIL

    # ------------------------------------------------------------------
    # Arithmetic model
    # ------------------------------------------------------------------

    def _start_model(self):
        self.sym_cum[self.N_CHAR] = 0
        for sym in range(self.N_CHAR, 0, -1):
            ch = sym - 1
            self.char_to_sym[ch] = sym
            self.sym_to_char[sym] = ch
            self.sym_freq[sym] = 1
            self.sym_cum[sym - 1] = self.sym_cum[sym] + self.sym_freq[sym]
        self.sym_freq[0] = 0
        self.position_cum[self.N] = 0
        for i in range(self.N, 0, -1):
            self.position_cum[i - 1] = self.position_cum[i] + 10000 // (i + 200)

    def _update_model(self, sym):
        if self.sym_cum[0] >= self.MAX_CUM:
            c = 0
            for i in range(self.N_CHAR, 0, -1):
                self.sym_cum[i] = c
                self.sym_freq[i] = (self.sym_freq[i] + 1) >> 1
                c += self.sym_freq[i]
            self.sym_cum[0] = c
        i = sym
        while self.sym_freq[i] == self.sym_freq[i - 1]:
            i -= 1
        if i < sym:
            ch_i   = self.sym_to_char[i]
            ch_sym = self.sym_to_char[sym]
            self.sym_to_char[i]   = ch_sym
            self.sym_to_char[sym] = ch_i
            self.char_to_sym[ch_i]  = sym
            self.char_to_sym[ch_sym] = i
        self.sym_freq[i] += 1
        i -= 1
        while i >= 0:
            self.sym_cum[i] += 1
            i -= 1

    def _output(self, bit):
        self._put_bit(bit)
        while self.shifts > 0:
            self._put_bit(1 - bit)
            self.shifts -= 1

    def _encode_char(self, ch):
        sym = self.char_to_sym[ch]
        rng = self.high - self.low
        self.high = self.low + (rng * self.sym_cum[sym - 1]) // self.sym_cum[0]
        self.low  = self.low + (rng * self.sym_cum[sym])     // self.sym_cum[0]
        while True:
            if self.high <= self.Q2:
                self._output(0)
            elif self.low >= self.Q2:
                self._output(1)
                self.low  -= self.Q2
                self.high -= self.Q2
            elif self.low >= self.Q1 and self.high <= self.Q3:
                self.shifts += 1
                self.low  -= self.Q1
                self.high -= self.Q1
            else:
                break
            self.low  <<= 1
            self.high <<= 1
        self._update_model(sym)

    def _encode_position(self, position):
        rng = self.high - self.low
        self.high = self.low + (rng * self.position_cum[position])     // self.position_cum[0]
        self.low  = self.low + (rng * self.position_cum[position + 1]) // self.position_cum[0]
        while True:
            if self.high <= self.Q2:
                self._output(0)
            elif self.low >= self.Q2:
                self._output(1)
                self.low  -= self.Q2
                self.high -= self.Q2
            elif self.low >= self.Q1 and self.high <= self.Q3:
                self.shifts += 1
                self.low  -= self.Q1
                self.high -= self.Q1
            else:
                break
            self.low  <<= 1
            self.high <<= 1

    def _encode_end(self):
        self.shifts += 1
        if self.low < self.Q1:
            self._output(0)
        else:
            self._output(1)
        self._flush_bit_buffer()

    def _binary_search_sym(self, x):
        i, j = 1, self.N_CHAR
        while i < j:
            k = (i + j) // 2
            if self.sym_cum[k] > x:
                i = k + 1
            else:
                j = k
        return i

    def _binary_search_pos(self, x):
        i, j = 1, self.N
        while i < j:
            k = (i + j) // 2
            if self.position_cum[k] > x:
                i = k + 1
            else:
                j = k
        return i - 1

    def _start_decode(self):
        for _ in range(self.M + 2):
            self.value = 2 * self.value + self._get_bit()

    def _decode_char(self):
        rng = self.high - self.low
        sym = self._binary_search_sym(((self.value - self.low + 1) * self.sym_cum[0] - 1) // rng)
        self.high = self.low + (rng * self.sym_cum[sym - 1]) // self.sym_cum[0]
        self.low  = self.low + (rng * self.sym_cum[sym])     // self.sym_cum[0]
        while True:
            if self.low >= self.Q2:
                self.value -= self.Q2
                self.low   -= self.Q2
                self.high  -= self.Q2
            elif self.low >= self.Q1 and self.high <= self.Q3:
                self.value -= self.Q1
                self.low   -= self.Q1
                self.high  -= self.Q1
            elif self.high > self.Q2:
                break
            self.low   <<= 1
            self.high  <<= 1
            self.value = 2 * self.value + self._get_bit()
        ch = self.sym_to_char[sym]
        self._update_model(sym)
        return ch

    def _decode_position(self):
        rng = self.high - self.low
        position = self._binary_search_pos(((self.value - self.low + 1) * self.position_cum[0] - 1) // rng)
        self.high = self.low + (rng * self.position_cum[position])     // self.position_cum[0]
        self.low  = self.low + (rng * self.position_cum[position + 1]) // self.position_cum[0]
        while True:
            if self.low >= self.Q2:
                self.value -= self.Q2
                self.low   -= self.Q2
                self.high  -= self.Q2
            elif self.low >= self.Q1 and self.high <= self.Q3:
                self.value -= self.Q1
                self.low   -= self.Q1
                self.high  -= self.Q1
            elif self.high > self.Q2:
                break
            self.low   <<= 1
            self.high  <<= 1
            self.value = 2 * self.value + self._get_bit()
        return position

    # ------------------------------------------------------------------
    # Encode / Decode
    # ------------------------------------------------------------------

    def _encode(self):
        data_bytes = self._infile.read()
        total_size = len(data_bytes)
        # write textsize as little-endian uint32
        ts = total_size
        self._outfile.write(bytes([ts & 0xFF, (ts >> 8) & 0xFF, (ts >> 16) & 0xFF, (ts >> 24) & 0xFF]))
        self.codesize += 4
        if total_size == 0:
            return
        self.textsize = 0
        self._start_model()
        self._init_tree()
        src = data_bytes
        src_idx = 0
        s = 0
        r = self.N - self.F
        for i in range(s, r):
            self.text_buf[i] = ord(' ')
        length = 0
        while length < self.F and src_idx < len(src):
            self.text_buf[r + length] = src[src_idx]
            src_idx += 1
            length += 1
        self.textsize = length
        for i in range(1, self.F + 1):
            self._insert_node(r - i)
        self._insert_node(r)
        while length > 0:
            if self.match_length > length:
                self.match_length = length
            if self.match_length <= self.THRESHOLD:
                self.match_length = 1
                self._encode_char(self.text_buf[r])
            else:
                self._encode_char(255 - self.THRESHOLD + self.match_length)
                self._encode_position(self.match_position - 1)
            last_match_length = self.match_length
            consumed = 0
            while consumed < last_match_length and src_idx < len(src):
                self._delete_node(s)
                c = src[src_idx]; src_idx += 1
                self.text_buf[s] = c
                if s < self.F - 1:
                    self.text_buf[s + self.N] = c
                s = (s + 1) & (self.N - 1)
                r = (r + 1) & (self.N - 1)
                self._insert_node(r)
                consumed += 1
            self.textsize += consumed
            while consumed < last_match_length:
                self._delete_node(s)
                s = (s + 1) & (self.N - 1)
                r = (r + 1) & (self.N - 1)
                length -= 1
                if length:
                    self._insert_node(r)
                consumed += 1
            length -= last_match_length - consumed
        self._encode_end()

    def _decode(self):
        temp = self._infile.read(4)
        self.textsize = temp[0] | (temp[1] << 8) | (temp[2] << 16) | (temp[3] << 24)
        if self.textsize == 0:
            return
        self._start_decode()
        self._start_model()
        for i in range(self.N - self.F):
            self.text_buf[i] = ord(' ')
        r = self.N - self.F
        count = 0
        while count < self.textsize:
            c = self._decode_char()
            if c < 256:
                self._outfile.write(bytes([c]))
                self.text_buf[r] = c
                r = (r + 1) & (self.N - 1)
                count += 1
            else:
                i = (r - self._decode_position() - 1) & (self.N - 1)
                j = c - 255 + self.THRESHOLD
                for k in range(j):
                    c2 = self.text_buf[(i + k) & (self.N - 1)]
                    self._outfile.write(bytes([c2]))
                    self.text_buf[r] = c2
                    r = (r + 1) & (self.N - 1)
                    count += 1

    def encode(self, data: bytes) -> bytes:
        self._reset()
        self._infile = io.BytesIO(data)
        self._outfile = io.BytesIO()
        self._encode()
        return self._outfile.getvalue()

    def decode(self, data: bytes) -> bytes:
        self._reset()
        self._infile = io.BytesIO(data)
        self._outfile = io.BytesIO()
        self._decode()
        return self._outfile.getvalue()
