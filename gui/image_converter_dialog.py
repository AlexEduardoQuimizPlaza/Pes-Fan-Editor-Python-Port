"""
PES Editor 6 - Python Port
ImageConverterDialog — "Convertir cualquier imagen" del panel de emblemas.

Rendimiento:
  • Paleta (Median Cut via PIL/C)  → se calcula una vez al cargar imagen.
  • Preview del slider             → dithering ordenado Bayer, 100 % numpy,
                                     sin bucle Python  ≈ 2–5 ms.
  • Importar al OF                 → Floyd-Steinberg exacto (numpy),
                                     solo una vez al pulsar el botón.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import emblems as Emblems

_PREV = 256   # tamaño del canvas de vista previa (px)

# Matriz de Bayer 8×8, normalizada a [-0.5, 0.5)
_BAYER_8 = None   # se inicializa con numpy al primer uso


def _bayer_matrix():
    global _BAYER_8
    if _BAYER_8 is None:
        import numpy as np
        B = [[ 0, 32,  8, 40,  2, 34, 10, 42],
             [48, 16, 56, 24, 50, 18, 58, 26],
             [12, 44,  4, 36, 14, 46,  6, 38],
             [60, 28, 52, 20, 62, 30, 54, 22],
             [ 3, 35, 11, 43,  1, 33,  9, 41],
             [51, 19, 59, 27, 49, 17, 57, 25],
             [15, 47,  7, 39, 13, 45,  5, 37],
             [63, 31, 55, 23, 61, 29, 53, 21]]
        _BAYER_8 = np.array(B, dtype=np.float32) / 64.0 - 0.5
    return _BAYER_8


class ImageConverterDialog(tk.Toplevel):
    def __init__(self, parent, of, emblem_panel=None):
        super().__init__(parent)
        self.title("Convertir imagen")
        self.resizable(False, False)
        self._of           = of
        self._emblem_panel = emblem_panel
        self._scaled       = None   # PIL Image 64×64 RGBA
        self._rgba_np      = None   # ndarray (64,64,4) int32 — cacheado
        self._palette      = None   # list de (r,g,b,a), índice 0 = transparente
        self._pal_np       = None   # ndarray (N-1,3) int32 — cacheado
        self._pal_rgba_np  = None   # ndarray (N,4) uint8  — para el preview
        self._indices      = None   # ndarray (4096,) int32
        self._orig_photo   = None
        self._conv_photo   = None
        self._build_ui()
        self.bind("<Control-v>", lambda e: self._pegar_portapapeles())
        self.bind("<Control-V>", lambda e: self._pegar_portapapeles())
        self.update_idletasks()
        self.grab_set()

    # ── construcción de la interfaz ───────────────────────────────────────────
    def _build_ui(self):
        # ── Fila 1: modo de colores + transparencia ────────────────────────
        r1 = ttk.Frame(self)
        r1.pack(fill=tk.X, padx=8, pady=(8, 2))
        ttk.Label(r1, text="Colores:").pack(side=tk.LEFT)
        self._modo_var = tk.StringVar(value="128 colores (mejor calidad, 1 slot)")
        self._modo_cb  = ttk.Combobox(r1, textvariable=self._modo_var,
                                       state="readonly", width=36,
                                       values=["128 colores (mejor calidad, 1 slot)",
                                               " 16 colores (menor calidad, ocupa menos)"])
        self._modo_cb.pack(side=tk.LEFT, padx=(4, 12))
        self._modo_cb.bind("<<ComboboxSelected>>", lambda e: self._reconstruir_paleta())

        self._transp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r1, text="Fondo transparente",
                        variable=self._transp_var,
                        command=self._reconstruir_paleta).pack(side=tk.LEFT)

        # ── Fila 2: dithering ──────────────────────────────────────────────
        r2 = ttk.Frame(self)
        r2.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(r2, text="Dithering:").pack(side=tk.LEFT)
        self._dither_var = tk.IntVar(value=80)
        ttk.Scale(r2, from_=0, to=100,
                  variable=self._dither_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=self._on_slider).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(r2, text="← plano  /  tramado →",
                  foreground="gray").pack(side=tk.LEFT)

        # ── Fila 3: instrucciones ──────────────────────────────────────────
        self._estado_var = tk.StringVar(
            value="  Arrastra una imagen aquí, pega con Ctrl+V, o pulsa 'Abrir imagen'")
        self._estado_lbl = ttk.Label(self, textvariable=self._estado_var,
                                      foreground="#3C3CB4")
        self._estado_lbl.pack(fill=tk.X, padx=8, pady=2)

        # ── Fila 4: etiquetas de vista previa ──────────────────────────────
        lf = ttk.Frame(self)
        lf.pack(fill=tk.X, padx=8)
        ttk.Label(lf, text="Original",
                  anchor=tk.CENTER).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(lf, text="Resultado — 64×64 exacto",
                  anchor=tk.CENTER).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ── Fila 5: canvas de vista previa ─────────────────────────────────
        pf = ttk.Frame(self)
        pf.pack(padx=8, pady=2)
        self._canvas_orig = tk.Canvas(pf, width=_PREV, height=_PREV,
                                       bg="#1E1E1E", cursor="hand2",
                                       relief=tk.SOLID, borderwidth=2)
        self._canvas_orig.pack(side=tk.LEFT, padx=(0, 8))
        self._canvas_orig.create_text(_PREV//2, _PREV//2,
                                       text="Click aquí o arrastra una imagen",
                                       fill="#AAAAAA", font=("TkDefaultFont", 10))
        self._canvas_orig.bind("<Button-1>", lambda e: self._abrir_imagen())

        self._canvas_conv = tk.Canvas(pf, width=_PREV, height=_PREV,
                                       bg="#1E1E1E",
                                       relief=tk.SOLID, borderwidth=2)
        self._canvas_conv.pack(side=tk.LEFT)
        self._canvas_conv.create_text(_PREV//2, _PREV//2,
                                       text="(aquí aparecerá la previsualización)",
                                       fill="#AAAAAA", font=("TkDefaultFont", 10))

        # ── Fila 6: botones + contador de slots ────────────────────────────
        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, padx=8, pady=(4, 8))
        ttk.Button(bf, text="Abrir imagen…",
                   command=self._abrir_imagen).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Pegar (Ctrl+V)",
                   command=self._pegar_portapapeles).pack(side=tk.LEFT, padx=2)
        self._importar_btn = ttk.Button(bf, text="Importar al OF",
                                         command=self._importar, state=tk.DISABLED)
        self._importar_btn.pack(side=tk.LEFT, padx=2)
        self._slots_var = tk.StringVar()
        ttk.Label(bf, textvariable=self._slots_var,
                  foreground="#444444").pack(side=tk.LEFT, padx=8)
        self._actualizar_slots()

    # ── slider en tiempo real ─────────────────────────────────────────────────
    def _on_slider(self, _val=None):
        if self._pal_np is not None:
            self._redither_preview()

    # ── carga de imagen ───────────────────────────────────────────────────────
    def _abrir_imagen(self):
        path = filedialog.askopenfilename(
            title="Abrir imagen",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("Todos los archivos", "*.*")],
            parent=self)
        if path:
            self._cargar_desde_ruta(path)

    def _cargar_desde_ruta(self, path):
        try:
            from PIL import Image
            self._cargar_desde_pil(Image.open(path).convert("RGBA"))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _pegar_portapapeles(self):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("Portapapeles",
                                    "No se encontró ninguna imagen en el portapapeles.",
                                    parent=self)
                return
            if hasattr(img, '__iter__') and not hasattr(img, 'size'):
                import os
                rutas = [p for p in img if os.path.isfile(p)]
                if rutas:
                    self._cargar_desde_ruta(rutas[0])
                return
            self._cargar_desde_pil(img.convert("RGBA"))
        except Exception as e:
            messagebox.showerror("Error de portapapeles", str(e), parent=self)

    def _cargar_desde_pil(self, raw):
        import numpy as np
        from PIL import Image, ImageTk

        w, h   = raw.size
        escala = min(_PREV / w, _PREV / h)
        pw, ph = int(w * escala), int(h * escala)
        thumb  = raw.resize((pw, ph), Image.LANCZOS)
        bg     = Image.new("RGBA", (_PREV, _PREV), (30, 30, 30, 255))
        bg.paste(thumb, ((_PREV - pw)//2, (_PREV - ph)//2))
        self._orig_photo = ImageTk.PhotoImage(bg)
        self._canvas_orig.delete("all")
        self._canvas_orig.create_image(0, 0, anchor=tk.NW, image=self._orig_photo)

        scale  = min(64 / w, 64 / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        _fit   = raw.resize((nw, nh), Image.LANCZOS)
        _pad   = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        _pad.paste(_fit, ((64 - nw) // 2, (64 - nh) // 2))
        self._scaled  = _pad
        self._rgba_np = np.array(self._scaled, dtype=np.int32)   # (64,64,4)

        self._estado_var.set(f"  Imagen cargada: {w}×{h} → ajustada a 64×64 (sin deformar)")
        self._estado_lbl.config(foreground="#007800")
        self._reconstruir_paleta()

    # ── dos pasos de cuantización ─────────────────────────────────────────────
    def _reconstruir_paleta(self):
        """Median Cut con PIL (C puro). Solo se ejecuta al cambiar modo/imagen."""
        if self._scaled is None:
            return
        import numpy as np
        from PIL import Image

        num = 128 if self._modo_var.get().startswith("128") else 16
        q   = self._scaled.convert("RGB").quantize(
                  colors=num - 1, method=Image.Quantize.MEDIANCUT, dither=0)
        rp  = q.getpalette()

        # Índice 0 = transparente
        self._palette = [(0, 0, 0, 0)]
        for i in range(num - 1):
            self._palette.append((rp[i*3], rp[i*3+1], rp[i*3+2], 255))
        while len(self._palette) < num:
            self._palette.append((0, 0, 0, 255))

        # Arrays numpy cacheados para el preview rápido
        self._pal_np      = np.array([(r, g, b) for r, g, b, a in self._palette[1:]],
                                      dtype=np.int32)          # (N-1, 3)
        self._pal_rgba_np = np.array(self._palette, dtype=np.uint8)  # (N, 4)

        self._redither_preview()

    def _redither_preview(self):
        """
        Dithering ordenado Bayer — 100 % numpy, sin bucle Python.
        Llama el slider en cada tick → tiempo real.
        """
        if self._rgba_np is None or self._pal_np is None:
            return
        import numpy as np

        h, w     = 64, 64
        transp   = self._transp_var.get()
        strength = self._dither_var.get() / 100.0

        # Ruido Bayer escalado al rango de color (0–255) × strength
        bayer   = np.tile(_bayer_matrix(), (8, 8))          # (64,64)
        noise   = bayer[:, :, np.newaxis] * 255.0 * strength   # (64,64,1)
        noisy   = np.clip(self._rgba_np[:, :, :3] + noise, 0, 255).astype(np.int32)

        # Búsqueda del color más cercano con pesos perceptuales (3R² + 4G² + 2B²)
        # diff: (64,64,1,3) - (1,1,N-1,3)  →  (64,64,N-1,3)
        diff    = noisy[:, :, np.newaxis, :] - self._pal_np[np.newaxis, np.newaxis, :, :]
        dist    = diff[:,:,:,0]**2 * 3 + diff[:,:,:,1]**2 * 4 + diff[:,:,:,2]**2 * 2
        best    = np.argmin(dist, axis=2).astype(np.int32) + 1  # +1 → índice 0 libre

        if transp:
            best[self._rgba_np[:, :, 3] < 128] = 0

        self._indices = best.flatten()
        self._actualizar_preview()
        self._importar_btn.config(state=tk.NORMAL)
        self._actualizar_slots()

    def _actualizar_preview(self):
        import numpy as np
        from PIL import Image, ImageTk

        # Lookup RGBA por índice con indexación numpy (muy rápido)
        rgba_out = self._pal_rgba_np[self._indices].reshape(64, 64, 4)
        img      = Image.fromarray(rgba_out.astype(np.uint8), mode="RGBA")
        big      = img.resize((_PREV, _PREV), Image.NEAREST)
        bg       = Image.new("RGBA", (_PREV, _PREV), (30, 30, 30, 255))
        bg.paste(big, mask=big)
        self._conv_photo = ImageTk.PhotoImage(bg)
        self._canvas_conv.delete("all")
        self._canvas_conv.create_image(0, 0, anchor=tk.NW, image=self._conv_photo)

    # ── importar al OF (Floyd-Steinberg exacto) ───────────────────────────────
    def _importar(self):
        if self._palette is None or self._scaled is None:
            return
        usar128 = self._modo_var.get().startswith("128")
        transp  = self._transp_var.get()
        fuerza  = self._dither_var.get() / 100.0

        # Recalcular con FS exacto para el guardado
        indices = _floyd_steinberg(self._rgba_np, self._pal_np,
                                    self._palette, transp, fuerza)

        if usar128:
            if Emblems.get_free128(self._of) <= 0:
                messagebox.showerror("Sin slots",
                    "No hay slots libres de 128 colores.", parent=self)
                return
            slot   = Emblems.count128(self._of)
            raster = bytes(int(v) for v in indices[:Emblems.RASTER_128])
            Emblems.set_palette_128(self._of, slot, self._palette)
            Emblems.set_raster_128(self._of, slot, raster)
            Emblems.set_count128(self._of, slot + 1)
        else:
            if Emblems.get_free16(self._of) <= 0:
                messagebox.showerror("Sin slots",
                    "No hay slots libres de 16 colores.", parent=self)
                return
            slot   = Emblems.count16(self._of)
            raster = bytearray(Emblems.RASTER_16)
            for i in range(0, 64*64, 2):
                hi = int(indices[i])     & 0xF
                lo = int(indices[i+1])   & 0xF if i+1 < len(indices) else 0
                raster[i//2] = (hi << 4) | lo
            Emblems.set_palette_16(self._of, slot, self._palette)
            Emblems.set_raster_16(self._of, slot, bytes(raster))
            Emblems.set_count16(self._of, slot + 1)

        if self._emblem_panel is not None:
            self._emblem_panel.refresh()
        self._actualizar_slots()
        messagebox.showinfo("¡Listo!",
            "Emblema importado correctamente.\n"
            "Guarda el Option File para conservar los cambios.", parent=self)

    def _actualizar_slots(self):
        if self._of is None:
            return
        f128 = Emblems.get_free128(self._of)
        f16  = Emblems.get_free16(self._of)
        self._slots_var.set(f"{f128}×128c / {f16}×16c")


# ── Floyd-Steinberg exacto (para importar al OF) ─────────────────────────────

def _floyd_steinberg(rgba_np, pal_np, palette, transparent_bg, dither_strength):
    import numpy as np

    h, w   = 64, 64
    indices = np.zeros(h * w, dtype=np.int32)
    err_r  = np.zeros((h, w), dtype=np.float32)
    err_g  = np.zeros((h, w), dtype=np.float32)
    err_b  = np.zeros((h, w), dtype=np.float32)

    for y in range(h):
        for x in range(w):
            pr, pg, pb, pa = rgba_np[y, x]
            i = y * w + x

            if transparent_bg and pa < 128:
                continue

            tr = int(np.clip(pr + err_r[y, x], 0, 255))
            tg = int(np.clip(pg + err_g[y, x], 0, 255))
            tb = int(np.clip(pb + err_b[y, x], 0, 255))

            diff = pal_np - np.array([tr, tg, tb])
            dist = diff[:,0]**2 * 3 + diff[:,1]**2 * 4 + diff[:,2]**2 * 2
            best = int(np.argmin(dist)) + 1

            indices[i] = best

            if dither_strength > 0.0:
                cr, cg, cb, _ = palette[best]
                er = (tr - cr) * dither_strength
                eg = (tg - cg) * dither_strength
                eb = (tb - cb) * dither_strength
                if x + 1 < w:
                    err_r[y, x+1] += er * 7/16
                    err_g[y, x+1] += eg * 7/16
                    err_b[y, x+1] += eb * 7/16
                if y + 1 < h:
                    if x > 0:
                        err_r[y+1, x-1] += er * 3/16
                        err_g[y+1, x-1] += eg * 3/16
                        err_b[y+1, x-1] += eb * 3/16
                    err_r[y+1, x]   += er * 5/16
                    err_g[y+1, x]   += eg * 5/16
                    err_b[y+1, x]   += eb * 5/16
                    if x + 1 < w:
                        err_r[y+1, x+1] += er * 1/16
                        err_g[y+1, x+1] += eg * 1/16
                        err_b[y+1, x+1] += eb * 1/16

    return indices
