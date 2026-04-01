"""
PES Editor 6 - Python Port
Emblem / badge graphics access — constants and layout ported directly from
the Java editor's Emblems.java.

Layout (all at absolute byte offsets in of.data):
  startAdr = 911308

  Counters (just before data block):
    of.data[911148]  count128  – number of 128-colour emblems stored
    of.data[911149]  count16   – number of 16-colour emblems stored

  128-colour slot n  (n = 0 .. count128-1):
    base      = startAdr + n * SIZE_128
    palette   = base + 64          (128 RGBA entries × 4 bytes = 512 bytes;
                                    stored as 256 × 4 = 1024 bytes, upper half unused)
    raster    = base + 1088        (4096 bytes, 64×64 at 8-bit/pixel)

  16-colour slot m  (m = 0 .. count16-1):
    Two 16-colour slots fit inside each 128-colour slot position, packed from
    the BACK of the 50-slot area (slots 49, 48, …).
    base      = startAdr + (49 - m//2) * SIZE_128 + (m%2) * SIZE_16
    palette   = base + 64          (16 RGBA entries × 4 bytes = 64 bytes)
    raster    = base + 128         (2048 bytes, 64×64 at 4-bit/pixel, MSB-first nibbles)

  Free-slot totals (mirrors Java getFree16/getFree128):
    free16  = 100 - count128*2 - count16
    free128 = (100 - count128*2 - count16) // 2
"""

START_ADR   = 911308   # Java: startAdr

# 128-colour emblem
SIZE_128    = 5184
PAL_128     = 128      # colours read from palette
PAL_OFF_128 = 64       # byte offset of palette within slot
RAS_OFF_128 = 1088     # byte offset of raster within slot
RASTER_128  = 4096     # raster bytes (64×64 × 8-bit)

# 16-colour emblem
SIZE_16     = 2176
PAL_16      = 16
PAL_OFF_16  = 64
RAS_OFF_16  = 128
RASTER_16   = 2048     # raster bytes (64×64 × 4-bit)

# Image dimensions
IMG_SIZE    = 64       # both types are 64×64 before any scaling

# Legacy constants kept for backwards-compatibility with clubs.py
TOTAL       = 116
FLAG_FIRST  = 292      # == clubs.FIRST_FLAG – first user emblem index in clubs data


# ── counters ──────────────────────────────────────────────────────────────────
def count128(of) -> int:
    return of.data[START_ADR - 160] & 0xFF


def count16(of) -> int:
    return of.data[START_ADR - 159] & 0xFF


def get_free16(of) -> int:
    return max(0, 100 - count128(of) * 2 - count16(of))


def get_free128(of) -> int:
    return max(0, (100 - count128(of) * 2 - count16(of)) // 2)


# ── address helpers ───────────────────────────────────────────────────────────
def _addr128(slot: int) -> int:
    """Base address for 128-colour emblem slot `slot`."""
    return START_ADR + slot * SIZE_128


def _addr16(slot: int) -> int:
    """Base address for 16-colour emblem slot `slot`."""
    return START_ADR + (49 - slot // 2) * SIZE_128 + (slot % 2) * SIZE_16


# ── palette / raster readers ──────────────────────────────────────────────────
def get_palette_128(of, slot: int) -> list:
    """Return list of PAL_128 (r,g,b,a) tuples for a 128-colour slot."""
    base = _addr128(slot) + PAL_OFF_128
    return [(of.data[base + i*4],
             of.data[base + i*4 + 1],
             of.data[base + i*4 + 2],
             of.data[base + i*4 + 3]) for i in range(PAL_128)]


def get_raster_128(of, slot: int) -> bytes:
    """Return RASTER_128 bytes of 8-bit raster for a 128-colour slot."""
    base = _addr128(slot) + RAS_OFF_128
    return bytes(of.data[base: base + RASTER_128])


def get_palette_16(of, slot: int) -> list:
    """Return list of PAL_16 (r,g,b,a) tuples for a 16-colour slot."""
    base = _addr16(slot) + PAL_OFF_16
    return [(of.data[base + i*4],
             of.data[base + i*4 + 1],
             of.data[base + i*4 + 2],
             of.data[base + i*4 + 3]) for i in range(PAL_16)]


def get_raster_16(of, slot: int) -> bytes:
    """Return RASTER_16 bytes of 4-bit raster for a 16-colour slot."""
    base = _addr16(slot) + RAS_OFF_16
    return bytes(of.data[base: base + RASTER_16])


# ── decode to pixel list ───────────────────────────────────────────────────────
def decode_128(of, slot: int, opaque: bool = False):
    """
    Decode a 128-colour emblem to a list of 64*64 (r,g,b,a) tuples.
    If opaque=True all alpha values are 255.
    """
    palette = get_palette_128(of, slot)
    raster  = get_raster_128(of, slot)
    pixels  = []
    for i in range(IMG_SIZE * IMG_SIZE):
        ci = raster[i] if i < len(raster) else 0
        if ci < len(palette):
            r, g, b, a = palette[ci]
        else:
            r, g, b, a = 0, 0, 0, 0
        pixels.append((r, g, b, 255 if opaque else a))
    return pixels


def decode_16(of, slot: int, opaque: bool = False):
    """
    Decode a 16-colour emblem to a list of 64*64 (r,g,b,a) tuples.
    Nibble order: high nibble = first pixel (MSB-first, matches Java
    MultiPixelPackedSampleModel with bitsPerPixel=4).
    If opaque=True all alpha values are 255.
    """
    palette = get_palette_16(of, slot)
    raster  = get_raster_16(of, slot)
    pixels  = []
    for i in range(IMG_SIZE * IMG_SIZE):
        byte_idx = i // 2
        if byte_idx < len(raster):
            byte_val = raster[byte_idx]
            # MSB-first: even pixel → high nibble, odd pixel → low nibble
            ci = (byte_val >> 4) & 0xF if (i % 2 == 0) else byte_val & 0xF
        else:
            ci = 0
        if ci < len(palette):
            r, g, b, a = palette[ci]
        else:
            r, g, b, a = 0, 0, 0, 0
        pixels.append((r, g, b, 255 if opaque else a))
    return pixels


# ── clubs value ↔ emblem type/slot ────────────────────────────────────────────
def clubs_value_to_slot(adj: int):
    """
    Given adj = clubs_emblem - FLAG_FIRST (0..149), return (type, slot) where
    type is '128' or '16' and slot is the emblem slot index.
    Returns (None, None) if adj is out of range.
    """
    if 0 <= adj < 50:
        return ('128', adj)
    if 50 <= adj < 150:
        return ('16', adj - 50)
    return (None, None)


def decode_by_adj(of, adj: int, opaque: bool = False):
    """
    Decode emblem by its adj value (clubs_emblem - FLAG_FIRST).
    Uses the Java-compatible indirection tables at START_ADR-158 (128-colour)
    and START_ADR-108 (16-colour) to map logical index → physical slot.
    Falls back to direct mapping when a table entry is 0 (uninitialized by
    older Python saves that predate this fix).
    """
    INDIR_128   = START_ADR - 158   # 911150 — 50-byte table for 128-colour
    INDIR_16    = START_ADR - 108   # 911200 — 100-byte table for 16-colour
    FREE_MARKER = 0x99              # Java's -103 (signed) = free slot

    if 0 <= adj < 50:
        val = of.data[INDIR_128 + adj] & 0xFF
        if val == FREE_MARKER:
            return None
        phys = val if val != 0 else adj   # 0 = uninitialized → direct map
        return decode_128(of, phys, opaque)

    if 50 <= adj < 150:
        i   = adj - 50
        val = of.data[INDIR_16 + i] & 0xFF
        if val == FREE_MARKER:
            return None
        phys = (val - 50) if val != 0 else i  # 0 = uninitialized → direct map
        return decode_16(of, phys, opaque)

    return None


# ── write helpers ─────────────────────────────────────────────────────────────
def set_palette_128(of, slot: int, palette: list):
    base = _addr128(slot) + PAL_OFF_128
    for i, (r, g, b, a) in enumerate(palette[:PAL_128]):
        of.data[base + i*4]     = r & 0xFF
        of.data[base + i*4 + 1] = g & 0xFF
        of.data[base + i*4 + 2] = b & 0xFF
        of.data[base + i*4 + 3] = a & 0xFF


def set_raster_128(of, slot: int, raster: bytes):
    """Write RASTER_128 bytes of 8-bit-per-pixel raster."""
    base = _addr128(slot) + RAS_OFF_128
    of.data[base: base + RASTER_128] = raster[:RASTER_128]


def set_palette_16(of, slot: int, palette: list):
    base = _addr16(slot) + PAL_OFF_16
    for i, (r, g, b, a) in enumerate(palette[:PAL_16]):
        of.data[base + i*4]     = r & 0xFF
        of.data[base + i*4 + 1] = g & 0xFF
        of.data[base + i*4 + 2] = b & 0xFF
        of.data[base + i*4 + 3] = a & 0xFF


def set_raster_16(of, slot: int, raster: bytes):
    base = _addr16(slot) + RAS_OFF_16
    of.data[base: base + RASTER_16] = raster[:RASTER_16]


def set_count16(of, v: int):
    of.data[START_ADR - 159] = v & 0xFF


def set_count128(of, v: int):
    of.data[START_ADR - 160] = v & 0xFF


def _fit_pad(img, size: int):
    """Resize image to fit inside size×size preserving aspect ratio, pad with transparency."""
    from PIL import Image
    w, h   = img.size
    scale  = min(size / w, size / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(resized, ((size - nw) // 2, (size - nh) // 2))
    return out


def _quantise16(img):
    """
    Quantise a 64×64 RGBA PIL Image to 16 colours.
    Returns (palette, indices) where:
      palette  — list of 16 (r,g,b,a) tuples, index 0 is transparent
      indices  — list of 64*64 palette indices (0 = transparent)
    Mirrors the approach used in ImageConverterDialog:
      • MEDIANCUT on RGB (avoids RGBA restriction)
      • Index 0 reserved for transparent pixels
    """
    from PIL import Image
    orig_alpha = [p[3] for p in img.getdata()]

    # Quantise on RGB — PAL_16-1 opaque colours, slot 0 kept for transparency
    quant   = img.convert("RGB").quantize(
                  colors=PAL_16 - 1, method=Image.Quantize.MEDIANCUT, dither=0)
    raw_pal = quant.getpalette()
    quant_idx = list(quant.getdata())

    # Build palette: index 0 = transparent, 1..15 = opaque colours
    palette = [(0, 0, 0, 0)]
    for i in range(PAL_16 - 1):
        palette.append((raw_pal[i*3], raw_pal[i*3+1], raw_pal[i*3+2], 255))

    # Map quantised indices: transparent pixels → 0, opaque → qi + 1
    indices = [0 if alpha < 128 else qi + 1
               for qi, alpha in zip(quant_idx, orig_alpha)]
    return palette, indices


def _write16(of, slot: int, palette: list, indices: list) -> int:
    """
    Write palette + MSB-first nibble raster to a 16-colour emblem slot.
    Also writes the Java-compatible metadata:
      • used-flag byte at slot base
      • indirection-table entry at START_ADR-108
      • emblem-id (little-endian) at slot base + 4
    Returns the emblem id (clubs value) that was assigned.
    """
    INDIR_16    = START_ADR - 108   # 911200
    FREE_MARKER = 0x99

    raster = bytearray(RASTER_16)
    for i in range(0, IMG_SIZE * IMG_SIZE, 2):
        hi = indices[i]     & 0xF
        lo = indices[i + 1] & 0xF if i + 1 < len(indices) else 0
        raster[i // 2] = (hi << 4) | lo
    set_palette_16(of, slot, palette)
    set_raster_16(of, slot, bytes(raster))
    if slot >= count16(of):
        set_count16(of, slot + 1)

    # Mark slot as used (Java: of.data[startPos] = 1)
    base = _addr16(slot)
    of.data[base] = 1

    # Find the first free logical index in the 16-colour indirection table
    logical_idx = None
    for i in range(100):
        v = of.data[INDIR_16 + i] & 0xFF
        if v == FREE_MARKER or v == 0:
            logical_idx = i
            break
    if logical_idx is None:
        logical_idx = slot   # fallback: all 100 logical slots claimed

    # Write indirection entry: physical slot stored as 50+slot
    of.data[INDIR_16 + logical_idx] = (50 + slot) & 0xFF

    # Compute and store emblem id in slot header (little-endian at base+4..5)
    emb_id = FLAG_FIRST + 50 + logical_idx
    of.data[base + 4] = emb_id & 0xFF
    of.data[base + 5] = (emb_id >> 8) & 0xFF

    return emb_id


def load_from_image(of, slot_type: str, slot: int, path: str):
    """
    Load a PNG/GIF and store as a 16-colour emblem at the given slot.
    slot_type must be '16' (128-colour import not yet implemented).
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow (PIL) required: pip install Pillow")
    img = _fit_pad(Image.open(path).convert("RGBA"), IMG_SIZE)
    palette, indices = _quantise16(img)
    return _write16(of, slot, palette, indices)


def load_from_pil_image(of, slot_type: str, slot: int, img):
    """
    Same as load_from_image but accepts an already-open PIL Image object.
    Useful when the image comes from a URL (BytesIO) instead of a file path.
    slot_type must be '16'.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow (PIL) required: pip install Pillow")
    img = _fit_pad(img.convert("RGBA"), IMG_SIZE)
    palette, indices = _quantise16(img)
    return _write16(of, slot, palette, indices)


# ── delete helpers ───────────────────────────────────────────────────────────
def delete16(of, slot: int):
    """
    Delete 16-colour emblem at physical slot.
    Mirrors Java Emblems.delete16: frees indirection entry, unassigns from clubs,
    shifts last slot into the gap, clears the vacated last slot, decrements count.
    """
    import clubs as Clubs
    INDIR_16    = START_ADR - 108   # 911200
    FREE_MARKER = 0x99

    base   = _addr16(slot)
    emb_id = of.data[base + 4] | (of.data[base + 5] << 8)
    si     = emb_id - (FLAG_FIRST + 50)   # logical index in 16-colour table

    if 0 <= si < 100:
        of.data[INDIR_16 + si] = FREE_MARKER

    Clubs.un_ass_emblem(of, si + 50)

    n = count16(of)
    if slot != n - 1:
        src = _addr16(n - 1)
        dst = _addr16(slot)
        of.data[dst:dst + SIZE_16] = of.data[src:src + SIZE_16]
        moved_id = of.data[dst + 4] | (of.data[dst + 5] << 8)
        moved_si = moved_id - (FLAG_FIRST + 50)
        if 0 <= moved_si < 100:
            of.data[INDIR_16 + moved_si] = (50 + slot) & 0xFF

    src = _addr16(n - 1)
    of.data[src:src + SIZE_16] = bytes(SIZE_16)
    set_count16(of, n - 1)


def delete128(of, slot: int):
    """
    Delete 128-colour emblem at physical slot.
    Mirrors Java Emblems.delete128.
    """
    import clubs as Clubs
    INDIR_128   = START_ADR - 158   # 911150
    FREE_MARKER = 0x99

    base   = _addr128(slot)
    emb_id = of.data[base + 4] | (of.data[base + 5] << 8)
    si     = emb_id - FLAG_FIRST   # logical index in 128-colour table

    if 0 <= si < 50:
        of.data[INDIR_128 + si] = FREE_MARKER

    Clubs.un_ass_emblem(of, si)

    n = count128(of)
    if slot != n - 1:
        src = _addr128(n - 1)
        dst = _addr128(slot)
        of.data[dst:dst + SIZE_128] = of.data[src:src + SIZE_128]
        moved_id = of.data[dst + 4] | (of.data[dst + 5] << 8)
        moved_si = moved_id - FLAG_FIRST
        if 0 <= moved_si < 50:
            of.data[INDIR_128 + moved_si] = slot & 0xFF

    src = _addr128(n - 1)
    of.data[src:src + SIZE_128] = bytes(SIZE_128)
    set_count128(of, n - 1)


def export_png(of, phys_slot: int, is128: bool, path: str):
    """Export emblem at physical slot to a PNG file (requires Pillow)."""
    try:
        from PIL import Image as PILImage
    except ImportError:
        raise RuntimeError("Pillow (PIL) required: pip install Pillow")
    pixels = decode_128(of, phys_slot, opaque=False) if is128 \
             else decode_16(of, phys_slot, opaque=False)
    img = PILImage.new("RGBA", (IMG_SIZE, IMG_SIZE))
    img.putdata(pixels)
    img.save(path, "PNG")


# ── legacy shim (kept for any existing callers) ────────────────────────────────
def get_palette(of, emblem_idx: int) -> list:
    """Deprecated shim – use decode_16 / decode_128 directly."""
    kind, slot = clubs_value_to_slot(emblem_idx)
    if kind == '128':
        return get_palette_128(of, slot)
    if kind == '16':
        return get_palette_16(of, slot)
    return [(0, 0, 0, 0)] * 16


def get_raster(of, emblem_idx: int) -> bytes:
    """Deprecated shim."""
    kind, slot = clubs_value_to_slot(emblem_idx)
    if kind == '128':
        return get_raster_128(of, slot)
    if kind == '16':
        return get_raster_16(of, slot)
    return bytes(512)
