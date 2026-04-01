"""
PES Editor 6 - Python Port
Logo graphics access — constants ported from Java Logos.java.

Layout (per slot, size=608 bytes):
  startAdr + slot * 608 + 0   : isUsed byte  (1 = occupied)
  startAdr + slot * 608 + 32  : palette      (16 RGBA entries × 4 bytes = 64 bytes)
  startAdr + slot * 608 + 96  : raster       (512 bytes, 32×32 at 4-bit MSB-first nibbles)
"""

TOTAL      = 80       # Java: total = 80
START_ADR  = 862492   # Java: startAdr = 862492
SIZE       = 608      # Java: size = 608
PAL_OFF    = 32       # palette offset within slot
RAS_OFF    = 96       # raster offset within slot
PAL_SIZE   = 16       # colours
RAS_BYTES  = 512      # raster bytes (32×32 × 4-bit)
IMG_SIZE   = 32       # 32×32 pixels


def _addr(slot: int) -> int:
    return START_ADR + slot * SIZE


def is_used(of, slot: int) -> bool:
    return of.data[_addr(slot)] == 1


def get_palette(of, slot: int) -> list:
    """Return list of 16 (r,g,b,a) tuples."""
    base = _addr(slot) + PAL_OFF
    return [(of.data[base + i*4],
             of.data[base + i*4 + 1],
             of.data[base + i*4 + 2],
             of.data[base + i*4 + 3]) for i in range(PAL_SIZE)]


def set_palette(of, slot: int, palette: list):
    base = _addr(slot) + PAL_OFF
    for i, (r, g, b, a) in enumerate(palette[:PAL_SIZE]):
        of.data[base + i*4]     = r & 0xFF
        of.data[base + i*4 + 1] = g & 0xFF
        of.data[base + i*4 + 2] = b & 0xFF
        of.data[base + i*4 + 3] = a & 0xFF


def get_raster(of, slot: int) -> bytes:
    """Return 512 bytes of 4-bit MSB-first raster."""
    base = _addr(slot) + RAS_OFF
    return bytes(of.data[base: base + RAS_BYTES])


def set_raster(of, slot: int, raster: bytes):
    base = _addr(slot) + RAS_OFF
    of.data[base: base + RAS_BYTES] = raster[:RAS_BYTES]


def decode(of, slot: int, opaque: bool = False):
    """
    Decode logo to a list of IMG_SIZE*IMG_SIZE (r,g,b,a) tuples.
    Returns None if slot is not used.
    If opaque=True all alpha values are set to 255.
    """
    if not is_used(of, slot):
        return None
    palette = get_palette(of, slot)
    raster  = get_raster(of, slot)
    pixels  = []
    for i in range(IMG_SIZE * IMG_SIZE):
        byte_idx = i // 2
        if byte_idx < len(raster):
            bv = raster[byte_idx]
            # MSB-first: even pixel → high nibble, odd pixel → low nibble
            ci = (bv >> 4) & 0xF if (i % 2 == 0) else bv & 0xF
        else:
            ci = 0
        if ci < len(palette):
            r, g, b, a = palette[ci]
        else:
            r, g, b, a = 0, 0, 0, 0
        pixels.append((r, g, b, 255 if opaque else a))
    return pixels


def delete(of, slot: int):
    """Erase a logo slot (zero all bytes)."""
    a = _addr(slot)
    of.data[a: a + SIZE] = bytes(SIZE)


def import_logo(of_src, slot_src: int, of_dst, slot_dst: int):
    a_s = _addr(slot_src)
    a_d = _addr(slot_dst)
    of_dst.data[a_d: a_d + SIZE] = of_src.data[a_s: a_s + SIZE]


def load_from_image(of, slot: int, path: str):
    """
    Load a PNG/GIF, quantise to 16 colours, and store as a logo at slot.
    Transparency: palette index 0 is used as the transparent colour.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow (PIL) required: pip install Pillow")

    _raw   = Image.open(path).convert("RGBA")
    scale  = min(IMG_SIZE / _raw.width, IMG_SIZE / _raw.height)
    nw, nh = max(1, int(_raw.width * scale)), max(1, int(_raw.height * scale))
    _fit   = _raw.resize((nw, nh), Image.LANCZOS)
    img    = Image.new("RGBA", (IMG_SIZE, IMG_SIZE), (0, 0, 0, 0))
    img.paste(_fit, ((IMG_SIZE - nw) // 2, (IMG_SIZE - nh) // 2))
    quant = img.quantize(colors=PAL_SIZE, method=Image.Quantize.FASTOCTREE)
    raw_pal  = quant.getpalette()          # R,G,B triples, 256 entries
    orig_pix = list(img.getdata())         # original RGBA for alpha detection

    palette = []
    for i in range(PAL_SIZE):
        r = raw_pal[i * 3]
        g = raw_pal[i * 3 + 1]
        b = raw_pal[i * 3 + 2]
        # Determine alpha from the original image pixels mapped to this colour
        a = 255
        palette.append((r, g, b, a))

    # Ensure index 0 is the transparent entry (alpha=0)
    # Look for any palette entry whose original pixels are mostly transparent
    indices = list(quant.getdata())
    # Count alpha per palette index from original image
    alpha_sum  = [0] * PAL_SIZE
    alpha_cnt  = [0] * PAL_SIZE
    for pi, idx in enumerate(indices):
        _, _, _, oa = orig_pix[pi]
        alpha_sum[idx] += oa
        alpha_cnt[idx] += 1
    # Mark fully-transparent entries (avg alpha < 32)
    for i in range(PAL_SIZE):
        cnt = alpha_cnt[i]
        if cnt > 0 and (alpha_sum[i] // cnt) < 32:
            r, g, b, _ = palette[i]
            palette[i] = (r, g, b, 0)

    # Swap transparent entry to index 0 (Java convention)
    trans_idx = next((i for i in range(PAL_SIZE) if palette[i][3] == 0), None)
    if trans_idx is not None and trans_idx != 0:
        palette[0], palette[trans_idx] = palette[trans_idx], palette[0]
        indices = [trans_idx if v == 0 else (0 if v == trans_idx else v)
                   for v in indices]
    elif trans_idx is None:
        # Force index 0 to transparent if no transparent entry exists
        r, g, b, _ = palette[0]
        palette[0] = (r, g, b, 0)

    # Build raster: MSB-first nibbles (high nibble = even pixel)
    raster = bytearray(RAS_BYTES)
    for i in range(0, IMG_SIZE * IMG_SIZE, 2):
        hi = indices[i]     & 0xF
        lo = indices[i + 1] & 0xF if i + 1 < len(indices) else 0
        raster[i // 2] = (hi << 4) | lo

    set_palette(of, slot, palette)
    set_raster(of, slot, bytes(raster))
    of.data[_addr(slot)] = 1   # mark as used


def load_from_pil_image(of, slot: int, img):
    """
    Same as load_from_image but accepts an already-open PIL Image object.
    Useful when the image comes from a URL (BytesIO) instead of a file path.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow (PIL) required: pip install Pillow")

    _raw   = img.convert("RGBA")
    scale  = min(IMG_SIZE / _raw.width, IMG_SIZE / _raw.height)
    nw, nh = max(1, int(_raw.width * scale)), max(1, int(_raw.height * scale))
    _fit   = _raw.resize((nw, nh), Image.LANCZOS)
    img    = Image.new("RGBA", (IMG_SIZE, IMG_SIZE), (0, 0, 0, 0))
    img.paste(_fit, ((IMG_SIZE - nw) // 2, (IMG_SIZE - nh) // 2))
    quant     = img.quantize(colors=PAL_SIZE, method=Image.Quantize.FASTOCTREE)
    raw_pal   = quant.getpalette()
    orig_pix  = list(img.getdata())
    indices   = list(quant.getdata())

    palette = []
    for i in range(PAL_SIZE):
        r = raw_pal[i * 3]
        g = raw_pal[i * 3 + 1]
        b = raw_pal[i * 3 + 2]
        palette.append((r, g, b, 255))

    alpha_sum = [0] * PAL_SIZE
    alpha_cnt = [0] * PAL_SIZE
    for pi, idx in enumerate(indices):
        _, _, _, oa = orig_pix[pi]
        alpha_sum[idx] += oa
        alpha_cnt[idx] += 1
    for i in range(PAL_SIZE):
        cnt = alpha_cnt[i]
        if cnt > 0 and (alpha_sum[i] // cnt) < 32:
            r, g, b, _ = palette[i]
            palette[i] = (r, g, b, 0)

    trans_idx = next((i for i in range(PAL_SIZE) if palette[i][3] == 0), None)
    if trans_idx is not None and trans_idx != 0:
        palette[0], palette[trans_idx] = palette[trans_idx], palette[0]
        indices = [trans_idx if v == 0 else (0 if v == trans_idx else v)
                   for v in indices]
    elif trans_idx is None:
        r, g, b, _ = palette[0]
        palette[0] = (r, g, b, 0)

    raster = bytearray(RAS_BYTES)
    for i in range(0, IMG_SIZE * IMG_SIZE, 2):
        hi = indices[i]     & 0xF
        lo = indices[i + 1] & 0xF if i + 1 < len(indices) else 0
        raster[i // 2] = (hi << 4) | lo

    set_palette(of, slot, palette)
    set_raster(of, slot, bytes(raster))
    of.data[_addr(slot)] = 1


def find_free_slot(of) -> int:
    """Return the first unused logo slot, or -1 if all are occupied."""
    for slot in range(TOTAL):
        if not is_used(of, slot):
            return slot
    return -1


def export_to_png(of, slot: int, path: str):
    """Export a logo slot as a PNG file (requires Pillow)."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow (PIL) required: pip install Pillow")

    if not is_used(of, slot):
        raise ValueError(f"Logo slot {slot} is empty")

    palette = get_palette(of, slot)
    raster  = get_raster(of, slot)
    img = Image.new("RGBA", (IMG_SIZE, IMG_SIZE))
    pixels = []
    for i in range(IMG_SIZE * IMG_SIZE):
        byte_idx = i // 2
        bv = raster[byte_idx] if byte_idx < len(raster) else 0
        ci = (bv >> 4) & 0xF if (i % 2 == 0) else bv & 0xF
        pixels.append(palette[ci] if ci < len(palette) else (0, 0, 0, 0))
    img.putdata(pixels)
    img.save(path, "PNG")
