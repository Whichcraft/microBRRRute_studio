from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
import math
import uuid
import tempfile
import sys
import random
import threading
import urllib.request
import urllib.error
import zipfile
import webbrowser

if sys.platform == "win32":
    import ctypes

from .mbseq import (
    MAX_PLAYABLE,
    MIN_PLAYABLE,
    NOTE_NAMES,
    MbseqProject,
    Step,
    midi_to_name,
    name_to_midi,
    transpose_steps,
)
from .synth import (
    play_note,
    play_pre_rendered_wav,
    render_pre_rendered_wav,
    render_steps_to_data,
    render_steps_wav,
    stop_all,
)
from .midi_export import export_midi, export_song_midi, import_midi

MAX_STEPS = 64
APP_TITLE = "microBRRRute Studio - MicroBrute SE Composer"
WHITE_OFFSETS = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24]
BLACK_OFFSETS = [1, 3, 6, 8, 10, 13, 15, 18, 20, 22]
BLACK_POS = {
    1: 0.65,
    3: 1.65,
    6: 3.65,
    8: 4.65,
    10: 5.65,
    13: 7.65,
    15: 8.65,
    18: 10.65,
    20: 11.65,
    22: 12.65,
}
PC_KEYS = list("awsedftgyhujkolpö")

SCALES = {
    "Chromatic": list(range(12)),
    "Major": [0, 2, 4, 5, 7, 9, 11],
    "Minor": [0, 2, 3, 5, 7, 8, 10],
    "Major Pentatonic": [0, 2, 4, 7, 9],
    "Minor Pentatonic": [0, 3, 5, 7, 10],
    "Blues": [0, 3, 5, 6, 7, 10],
    "Phrygian Dominant": [0, 1, 4, 5, 7, 8, 10],
}


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", lambda e: self.show_tip())
        widget.bind("<Leave>", lambda e: self.hide_tip())

    def show_tip(self):
        if self.tip_window or not self.text:
            return
        try:
            bbox = self.widget.bbox("insert")
        except Exception:
            bbox = None
        if bbox:
            x, y, _, _ = bbox
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
        else:
            x = self.widget.winfo_rootx() + max(20, self.widget.winfo_width() // 2)
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("tahoma", "9", "normal"),
        ).pack(ipadx=1)

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class MbseqStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1380x950")
        self.minsize(1100, 800)
        self._set_icon()

        self.project = MbseqProject.empty()
        self.file_path: Path | None = None
        self.slot = tk.IntVar(value=1)
        self.bank_name_var = tk.StringVar(value="Bank 1")
        self.cursor = tk.IntVar(value=0)
        self.cursor_display = tk.IntVar(value=1)
        self.octave_shift = tk.IntVar(value=0)
        self.root_note = 48
        self.tempo = tk.IntVar(value=120)
        self.wave_shape = tk.StringVar(value="square")
        self.volume = tk.DoubleVar(value=0.28)
        self.loop = tk.BooleanVar(value=True)
        self.metronome = tk.BooleanVar(value=False)
        self.count_in = tk.BooleanVar(value=False)
        self.dark_mode = tk.BooleanVar(value=False)
        self.step_res = tk.StringVar(value="1/8")
        self.piano_roll_orientation = tk.StringVar(value="horizontal")
        self.bank_length = tk.IntVar(value=MAX_STEPS)
        self.attack = tk.DoubleVar(value=0.005)
        self.decay = tk.DoubleVar(value=0.1)
        self.sustain = tk.DoubleVar(value=0.5)
        self.release = tk.DoubleVar(value=0.05)
        self.auto_update = tk.BooleanVar(value=True)
        self.playing = False

        self._load_settings()
        self.dirty = False
        self._undo: list[dict[int, list[Step]]] = []
        self._redo: list[dict[int, list[Step]]] = []
        self._after_id: str | None = None
        self._pre_render_file: Path | None = None
        self._play_idx = 0
        self._playhead = -1
        self._play_banks: list[int] = []
        self._drag_idx: int | None = None
        self._selection: set[int] = set()
        self._piano_roll_zoom = 1.0
        self._piano_roll_zoom_x = 1.0
        self._piano_roll_off_x = 0.0
        self._piano_roll_off_y = 0
        self._piano_roll_drag_start: tuple[float, float] | None = None
        self._piano_roll_drag_current: tuple[float, float] | None = None
        self._piano_roll_drag_state = 0
        self._last_cols: int | None = None
        self.step_buttons: list[tk.Button] = []

        self.key_rects: dict[int, int] = {}
        self.recent_files = self._load_recent()
        self.play_btn: ttk.Button | None = None
        self.stop_btn: ttk.Button | None = None

        self._setup_dnd()
        self._build()
        if self.dark_mode.get():
            self.toggle_theme()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_all()
        self.after(1000, self.check_for_updates)

    def _set_icon(self) -> None:
        icon_dir = Path(__file__).parent.parent
        ip = icon_dir / "icon.png"
        ii = icon_dir / "icon.ico"
        try:
            if ip.exists():
                self._icon_img = tk.PhotoImage(file=str(ip))
                self.iconphoto(True, self._icon_img)
            elif ii.exists() and sys.platform == "win32":
                self.iconbitmap(str(ii))
        except Exception:
            pass

    def _setup_dnd(self) -> None:
        if sys.platform != "win32":
            return
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            ctypes.windll.shell32.DragAcceptFiles(hwnd, True)  # type: ignore
        except Exception:
            pass

    def _build(self) -> None:
        self._build_menu()
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Pattern bank").pack(side="left")
        sb = ttk.Combobox(
            top,
            textvariable=self.slot,
            values=tuple(str(i) for i in range(1, 9)),
            width=4,
            state="readonly",
        )
        sb.pack(side="left", padx=(4, 8))
        sb.bind("<<ComboboxSelected>>", lambda e: self.change_slot())

        self.name_entry = ttk.Entry(top, textvariable=self.bank_name_var, width=15)
        self.name_entry.pack(side="left", padx=(0, 10))
        self.name_entry.bind("<FocusOut>", lambda e: self.update_bank_name())
        self.name_entry.bind("<Return>", lambda e: self.update_bank_name())
        ToolTip(self.name_entry, "Name this bank (Ctrl+N)")

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(top, text="Cursor").pack(side="left")
        sp = ttk.Spinbox(
            top,
            from_=1,
            to=MAX_STEPS,
            textvariable=self.cursor_display,
            width=5,
            command=self._apply_cursor_display,
        )
        sp.pack(side="left", padx=(4, 14))
        sp.bind("<FocusOut>", lambda e: self._apply_cursor_display())
        sp.bind("<Return>", lambda e: self._apply_cursor_display())
        ToolTip(sp, "Edit cursor position")

        ttk.Label(top, text="Len").pack(side="left", padx=(8, 2))
        ls = ttk.Spinbox(
            top,
            from_=1,
            to=MAX_STEPS,
            textvariable=self.bank_length,
            width=4,
            command=self._change_bank_length,
        )
        ls.pack(side="left")
        ls.bind("<FocusOut>", lambda e: self._change_bank_length())
        ls.bind("<Return>", lambda e: self._change_bank_length())
        ToolTip(ls, "Bank length")

        b = ttk.Button(top, text="Open", command=self.open_file)
        b.pack(side="left", padx=(10, 0))
        ToolTip(b, "Open .mbseq")
        b = ttk.Button(top, text="Save", command=self.save_file)
        b.pack(side="left", padx=3)
        ToolTip(b, "Save current project")

        self.play_btn = ttk.Button(top, text="▶ Play", command=self.play_sequence)
        self.play_btn.pack(side="left", padx=(10, 0))
        ToolTip(self.play_btn, "Play the selected bank (Space)")
        self.stop_btn = ttk.Button(
            top, text="■ Stop", command=self.stop_sequence, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=3)
        ToolTip(self.stop_btn, "Stop playback (Esc)")

        ttk.Checkbutton(top, text="Loop", variable=self.loop).pack(side="left")
        ttk.Checkbutton(top, text="Metronome", variable=self.metronome).pack(
            side="left", padx=3
        )
        ttk.Checkbutton(top, text="Count-in", variable=self.count_in).pack(
            side="left", padx=3
        )
        ttk.Label(top, text="Res").pack(side="left", padx=(10, 2))
        for label, value in [("1/8", "1/8"), ("1/16", "1/16")]:
            ttk.Radiobutton(
                top,
                text=label,
                value=value,
                variable=self.step_res,
                command=self._save_settings,
            ).pack(side="left")

        dt = ttk.Checkbutton(
            top, text="Dark Mode", variable=self.dark_mode, command=self.toggle_theme
        )
        dt.pack(side="right", padx=10)
        ToolTip(dt, "Toggle high-contrast Dark Mode")

        edit = ttk.Frame(self, padding=(8, 0, 8, 6))
        edit.pack(fill="x")

        b = ttk.Button(edit, text="Randomize...", command=self.show_randomizer_dialog)
        b.pack(side="left")
        ToolTip(b, "Generate random sequence within scale (Ctrl+R)")
        b = ttk.Button(edit, text="Arpeggiate...", command=self.show_arpeggiator_dialog)
        b.pack(side="left", padx=3)
        ToolTip(b, "Choose source notes and target steps for an arpeggio")

        ttk.Separator(edit, orient="vertical").pack(side="left", fill="y", padx=10)
        b = ttk.Button(edit, text="+ Step", command=self.add_step)
        b.pack(side="left")
        ToolTip(b, "Insert an empty step")
        b = ttk.Button(edit, text="Delete", command=self.delete_step)
        b.pack(side="left", padx=3)
        ToolTip(b, "Remove step or selection")
        b = ttk.Button(edit, text="Rest", command=self.insert_rest)
        b.pack(side="left", padx=3)
        ToolTip(b, "Set current step to rest (R)")
        b = ttk.Button(edit, text="Clear", command=self.clear_slot)
        b.pack(side="left", padx=10)
        ToolTip(b, "Reset bank to rests")

        b = ttk.Button(edit, text="Copy", command=self.copy_selection)
        b.pack(side="left", padx=3)
        ToolTip(b, "Copy selection (Ctrl+C). Shift+C for bank.")
        b = ttk.Button(edit, text="Paste", command=self.paste_selection)
        b.pack(side="left", padx=3)
        ToolTip(b, "Paste from clipboard (Ctrl+V). Shift+V for bank.")

        ttk.Label(edit, text="Transpose").pack(side="left", padx=(14, 3))
        transpose_options = [
            ("-2 oct", -24, "Transpose by -2 octaves"),
            ("-1 oct", -12, "Transpose by -1 octave"),
            ("-1", -1, "Transpose by -1 semitone"),
            ("+1", 1, "Transpose by +1 semitone"),
            ("+1 oct", 12, "Transpose by +1 octave"),
            ("+2 oct", 24, "Transpose by +2 octaves"),
        ]
        for label, v, tip in transpose_options:
            b = ttk.Button(
                edit,
                text=label,
                width=6,
                command=lambda x=v: self.transpose_bank(x),  # type: ignore[misc]
            )
            b.pack(side="left")
            ToolTip(b, tip)

        self.paned = ttk.PanedWindow(self, orient="vertical")
        self.paned.pack(fill="both", expand=True, padx=8, pady=4)

        self.grid_container = ttk.Frame(self.paned, padding=8)
        self.paned.add(self.grid_container, weight=1)
        self.grid_inner = ttk.Frame(self.grid_container)
        self.grid_inner.pack(anchor="nw")
        self.bind("<Configure>", lambda e: self.on_resize(e))

        self.piano_roll_frame = ttk.LabelFrame(
            self.paned, text="Visual Piano Roll", padding=6
        )
        self.paned.add(self.piano_roll_frame, weight=2)
        piano_roll_toolbar = ttk.Frame(self.piano_roll_frame)
        piano_roll_toolbar.pack(fill="x", pady=(0, 4))
        ttk.Label(piano_roll_toolbar, text="Orientation").pack(side="left")
        for label, value in [("Horizontal", "horizontal"), ("Vertical", "vertical")]:
            ttk.Radiobutton(
                piano_roll_toolbar,
                text=label,
                value=value,
                variable=self.piano_roll_orientation,
                command=self._change_piano_roll_orientation,
            ).pack(side="left", padx=(6, 0))
        ttk.Label(
            piano_roll_toolbar,
            text="Ctrl+Wheel: vertical zoom | Ctrl+Shift+Wheel: horizontal zoom",
        ).pack(side="right")
        self.piano_roll = tk.Canvas(
            self.piano_roll_frame,
            height=280,
            bg="#333333",
            highlightthickness=0,
        )
        self.piano_roll.pack(fill="both", expand=True)
        self.piano_roll.bind("<Configure>", self._on_piano_roll_resize)
        self.piano_roll.bind("<ButtonPress-1>", self._on_piano_roll_press)
        self.piano_roll.bind("<B1-Motion>", self._on_piano_roll_drag)
        self.piano_roll.bind("<ButtonRelease-1>", self._on_piano_roll_release)
        self.after_idle(self._set_initial_piano_roll_size)

        kb_wrap = ttk.Frame(self, padding=8)
        kb_wrap.pack(fill="x")
        self.keyboard = tk.Canvas(
            kb_wrap, width=1030, height=210, bg="#666666", highlightthickness=0
        )
        self.keyboard.pack(fill="x", pady=6)

        text_frame = ttk.LabelFrame(self, text="Raw .mbseq text", padding=6)
        text_frame.pack(fill="x", padx=8, pady=4)
        self.raw = tk.Text(text_frame, height=3, font=("Consolas", 10), undo=True)
        self.raw.pack(fill="both", expand=True)
        self.raw.bind("<Control-Return>", lambda e: self.apply_raw())
        ttk.Button(text_frame, text="Apply raw", command=self.apply_raw).pack(
            side="right", padx=6
        )

        ec = ttk.Frame(self, padding=(8, 0, 8, 6))
        ec.pack(fill="x")
        ttk.Label(ec, text="Oscillator").pack(side="left")
        for s in ["square", "saw", "triangle", "sine"]:
            ttk.Radiobutton(
                ec, text=s.capitalize(), variable=self.wave_shape, value=s
            ).pack(side="left", padx=3)
        ttk.Label(ec, text="Volume").pack(side="left", padx=(14, 3))
        ttk.Scale(ec, from_=0.0, to=0.8, variable=self.volume, length=140).pack(
            side="left"
        )
        ttk.Label(ec, text="Octave").pack(side="left", padx=(20, 3))
        for v in [-2, -1, 0, 1, 2]:
            ttk.Radiobutton(
                ec,
                text=f"{v:+d}",
                variable=self.octave_shift,
                value=v,
                command=self.refresh_keyboard,
            ).pack(side="left")
        self.status = ttk.Label(self, padding=(8, 0, 8, 8), text="")
        self.status.pack(fill="x")

    def _build_menu(self) -> None:
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label="Open .mbseq", command=self.open_file)
        self.recent_menu = tk.Menu(fm, tearoff=0)
        fm.add_cascade(label="Open Recent", menu=self.recent_menu)
        self._refresh_recent_menu()
        fm.add_command(label="Save", command=self.save_file)
        fm.add_command(label="Save As...", command=self.save_as)
        fm.add_separator()
        fm.add_command(label="Import MIDI...", command=self.import_midi_file)
        fm.add_separator()
        fm.add_command(label="Export selected MIDI...", command=self.export_midi_file)
        fm.add_command(label="Export all 8 MIDI...", command=self.export_all_midi_files)
        fm.add_command(label="Export song MIDI...", command=self.export_song_midi_file)
        fm.add_command(label="Export bank WAV...", command=self.export_bank_wav)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.on_close)
        m.add_cascade(label="File", menu=fm)

        em = tk.Menu(m, tearoff=0)
        em.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        em.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        em.add_separator()
        em.add_command(
            label="Copy Selection", accelerator="Ctrl+C", command=self.copy_selection
        )
        em.add_command(
            label="Paste Selection", accelerator="Ctrl+V", command=self.paste_selection
        )
        em.add_separator()
        em.add_command(
            label="Copy Whole Bank", accelerator="Ctrl+Shift+C", command=self.copy_bank
        )
        em.add_command(
            label="Paste Whole Bank",
            accelerator="Ctrl+Shift+V",
            command=self.paste_bank,
        )
        em.add_separator()
        em.add_command(label="Duplicate Bank...", command=self.duplicate_bank_dialog)
        em.add_separator()
        em.add_command(label="Clear Selection", command=self.clear_selection)
        m.add_cascade(label="Edit", menu=em)

        vm = tk.Menu(m, tearoff=0)
        vm.add_checkbutton(
            label="Dark Mode", variable=self.dark_mode, command=self.toggle_theme
        )
        vm.add_separator()
        vm.add_command(label="Settings...", command=self.show_settings_dialog)
        vm.add_command(label="Check for Updates...", command=lambda: self.check_for_updates(manual=True))
        m.add_cascade(label="View", menu=vm)
        self.config(menu=m)

    def _bind_keys(self) -> None:
        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("r", lambda e: self.insert_rest())
        self.bind("<Insert>", lambda e: self.insert_rest())
        self.bind("<Escape>", lambda e: self.stop_sequence())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-Z>", lambda e: self.redo())
        self.bind("<Control-c>", lambda e: self.copy_selection())
        self.bind("<Control-v>", lambda e: self.paste_selection())
        self.bind("<Control-C>", lambda e: self.copy_bank())
        self.bind("<Control-V>", lambda e: self.paste_bank())
        self.bind("<Control-n>", lambda e: self.focus_bank_name())
        self.bind("<Control-r>", lambda e: self.show_randomizer_dialog())
        self.bind("<Left>", lambda e: self.move_cursor(-1))
        self.bind("<Right>", lambda e: self.move_cursor(1))
        for idx, key in enumerate(PC_KEYS[:25]):
            try:
                self.bind(
                    key,
                    lambda e, i=idx: self.insert_note(  # type: ignore[misc]
                        self.note_for_index(i)
                    ),
                )
            except tk.TclError:
                pass
        self.piano_roll.bind("<MouseWheel>", self._on_piano_roll_scroll)
        self.piano_roll.bind("<Button-4>", self._on_piano_roll_scroll)
        self.piano_roll.bind("<Button-5>", self._on_piano_roll_scroll)

    def steps(self) -> list[Step]:
        s = int(self.slot.get())
        if s not in self.project.sequences:
            self.project.sequences[s] = [Step() for _ in range(MAX_STEPS)]
        return self.project.sequences[s]

    def _active_length(self) -> int:
        try:
            length = int(self.bank_length.get())
        except tk.TclError:
            length = MAX_STEPS
        length = max(1, min(MAX_STEPS, length))
        try:
            current = int(self.bank_length.get())
        except tk.TclError:
            current = None
        if current != length:
            self.bank_length.set(length)
        return length

    def active_steps(self, bank: int | None = None) -> list[Step]:
        if bank is None:
            steps = self.steps()
        else:
            steps = self.project.sequences.get(bank, [Step() for _ in range(MAX_STEPS)])
        return steps[: self._active_length()]

    def _sync_cursor_display(self) -> None:
        self.cursor_display.set(self.cursor.get() + 1)

    def _apply_cursor_display(self) -> None:
        try:
            display = int(self.cursor_display.get())
        except (tk.TclError, ValueError):
            display = self.cursor.get() + 1
        active_len = len(self.active_steps())
        self.cursor.set(max(0, min(active_len - 1, display - 1)))
        self._sync_cursor_display()
        self.refresh_grid()
        self.refresh_piano_roll()

    def _change_bank_length(self) -> None:
        self._active_length()
        if self.cursor.get() >= self._active_length():
            self.cursor.set(self._active_length() - 1)
        self._sync_cursor_display()
        self._save_settings()
        self.refresh_all()

    def note_for_index(self, idx: int) -> int:
        return max(0, min(127, self.root_note + self.octave_shift.get() * 12 + idx))

    def _set_initial_piano_roll_size(self) -> None:
        height = self.paned.winfo_height()
        if height <= 1:
            self.after(50, self._set_initial_piano_roll_size)
            return
        self.paned.sashpos(0, max(250, height // 2))
        self.update_idletasks()
        self.refresh_piano_roll()

    def _on_piano_roll_resize(self, event: tk.Event) -> None:
        if event.widget == self.piano_roll:
            self.refresh_piano_roll()

    def focus_bank_name(self) -> None:
        if hasattr(self, "name_entry"):
            self.name_entry.focus_set()
            self.name_entry.selection_range(0, "end")

    def update_bank_name(self) -> None:
        self.project.bank_names[int(self.slot.get())] = self.bank_name_var.get()
        self.refresh_status()

    def _at_step_limit(self) -> bool:
        if self._active_length() >= MAX_STEPS:
            self.status.config(text=f"Bank full ({MAX_STEPS})")
            return True
        return False

    def toggle_theme(self) -> None:
        style = ttk.Style()
        if self.dark_mode.get():
            self.configure(bg="#2b2b2b")
            style.theme_use("clam")
            for w in [
                "TFrame",
                "TLabel",
                "TCheckbutton",
                "TRadiobutton",
                "TLabelframe",
                "TLabelframe.Label",
            ]:
                style.configure(w, background="#2b2b2b", foreground="#ffffff")
            style.configure("TButton", background="#404040", foreground="#ffffff")
            self.raw.configure(bg="#1e1e1e", fg="#ffffff", insertbackground="white")
        else:
            self.configure(bg="#f0f0f0")
            style.theme_use("default")
            for w in [
                "TFrame",
                "TLabel",
                "TCheckbutton",
                "TRadiobutton",
                "TLabelframe",
                "TLabelframe.Label",
            ]:
                style.configure(w, background="#f0f0f0", foreground="#000000")
            style.configure("TButton", background="#e1e1e1", foreground="#000000")
            self.raw.configure(bg="#ffffff", fg="#000000", insertbackground="black")
        self._save_settings()
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_grid()
        self.refresh_keyboard()
        self.refresh_raw()
        self.refresh_status()
        self.refresh_piano_roll()

    def _recent_config_path(self) -> Path:
        return Path.home() / ".microbrrrute_studio_recent.json"

    def _settings_path(self) -> Path:
        return Path.home() / ".microbrrrute_studio_settings.json"

    def _load_settings(self) -> None:
        p = self._settings_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(self, k):
                        getattr(self, k).set(v)
            except Exception:
                pass

    def _save_settings(self) -> None:
        try:
            d = {
                k: getattr(self, k).get()
                for k in [
                    "volume",
                    "tempo",
                    "dark_mode",
                    "count_in",
                    "wave_shape",
                    "step_res",
                    "bank_length",
                    "octave_shift",
                    "piano_roll_orientation",
                    "attack",
                    "decay",
                    "sustain",
                    "release",
                    "auto_update",
                ]
            }
            self._settings_path().write_text(json.dumps(d), encoding="utf-8")
        except Exception:
            pass

    def _load_recent(self) -> list[str]:
        p = self._recent_config_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [f for f in data if isinstance(f, str) and Path(f).exists()][
                        :10
                    ]
            except Exception:
                pass
        return []

    def _save_recent(self) -> None:
        try:
            self._recent_config_path().write_text(
                json.dumps(self.recent_files), encoding="utf-8"
            )
        except Exception:
            pass

    def _add_recent(self, path: str | Path) -> None:
        p = str(Path(path).absolute())
        if p in self.recent_files:
            self.recent_files.remove(p)
        self.recent_files.insert(0, p)
        self.recent_files = self.recent_files[:10]
        self._save_recent()
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.delete(0, "end")
        if not self.recent_files:
            self.recent_menu.add_command(label="(No recent files)", state="disabled")
        else:
            for p in self.recent_files:
                self.recent_menu.add_command(
                    label=p,
                    command=lambda x=p: self.open_recent(x),  # type: ignore[misc]
                )

    def open_recent(self, path: str) -> None:
        if not Path(path).exists():
            messagebox.showerror("Error", "File not found")
            self.recent_files.remove(path)
            self._save_recent()
            self._refresh_recent_menu()
            return
        if not self._confirm_discard_changes():
            return
        self._do_open(path)

    def refresh_status(self) -> None:
        p = str(self.file_path) if self.file_path else "unsaved"
        cur = self.cursor.get() + 1
        flag = " *" if self.dirty else ""
        steps = self.steps()
        out = any(
            s.note is not None and (s.note < MIN_PLAYABLE or s.note > MAX_PLAYABLE)
            for s in steps
        )
        range_warn = " | ⚠️ Out of range!" if out else ""
        name = self.project.bank_names.get(
            int(self.slot.get()), f"Bank {self.slot.get()}"
        )
        self.status.config(
            text=f"{p}{flag} | {name} | Steps {len(steps)} | Cursor {cur} | {range_warn}"
        )
        self.title(("* " if self.dirty else "") + APP_TITLE)

    def show_settings_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("App Settings")
        win.geometry("400x480")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        f = ttk.Frame(win, padding=20)
        f.pack(fill="both", expand=True)
        ttk.Checkbutton(
            f, text="Dark Mode", variable=self.dark_mode, command=self.toggle_theme
        ).pack(anchor="w", pady=5)
        ttk.Checkbutton(
            f, text="Auto-update on startup", variable=self.auto_update, command=self._save_settings
        ).pack(anchor="w", pady=5)
        ttk.Label(f, text="Volume").pack(anchor="w")
        ttk.Scale(f, from_=0.0, to=0.8, variable=self.volume, orient="horizontal").pack(
            fill="x", pady=5
        )
        ttk.Label(f, text="Tempo (BPM)").pack(anchor="w")
        ttk.Spinbox(f, from_=30, to=300, textvariable=self.tempo).pack(
            anchor="w", pady=5
        )

        env = ttk.LabelFrame(f, text="ADSR Envelope", padding=10)
        env.pack(fill="x", pady=10)
        for p in [
            ("Attack", self.attack, 0, 0.5),
            ("Decay", self.decay, 0, 1.0),
            ("Sustain", self.sustain, 0, 1.0),
            ("Release", self.release, 0, 1.0),
        ]:
            ttk.Label(env, text=p[0]).pack(anchor="w")
            ttk.Scale(
                env, from_=p[2], to=p[3], variable=p[1], orient="horizontal"
            ).pack(fill="x")
        ttk.Button(f, text="Close", command=win.destroy).pack(side="bottom", pady=10)

    def check_for_updates(self, manual: bool = False) -> None:
        if not manual and not self.auto_update.get():
            return
        threading.Thread(target=self._run_update_check, args=(manual,), daemon=True).start()

    def _run_update_check(self, manual: bool) -> None:
        try:
            url = "https://api.github.com/repos/Whichcraft/microBRRRute_studio/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "microBRRRute-Studio-Updater"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            
            latest_tag = data.get("tag_name", "")
            if not latest_tag:
                if manual:
                    self.after(0, lambda: messagebox.showerror("Update Check", "Could not fetch release information from GitHub."))
                return
            
            from . import __version__ as current_version
            
            if self._is_newer_version(current_version, latest_tag):
                self.after(0, lambda: self._prompt_update(data))
            else:
                if manual:
                    self.after(0, lambda: messagebox.showinfo(
                        "Up to Date",
                        f"You are up to date!\n\n"
                        f"microBRRRute Studio v{current_version} is the latest version."
                    ))
        except Exception as e:
            if manual:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror(
                    "Update Check Failed",
                    f"An error occurred while checking for updates:\n\n{err_msg}"
                ))

    @staticmethod
    def _is_newer_version(current: str, latest: str) -> bool:
        def parse_v(v_str: str) -> list[int]:
            cleaned = v_str.strip().lower()
            if cleaned.startswith("v"):
                cleaned = cleaned[1:]
            parts = []
            for x in cleaned.split("."):
                x_clean = "".join(char for char in x if char.isdigit())
                parts.append(int(x_clean) if x_clean else 0)
            return parts
        v_curr = parse_v(current)
        v_late = parse_v(latest)
        max_len = max(len(v_curr), len(v_late))
        v_curr += [0] * (max_len - len(v_curr))
        v_late += [0] * (max_len - len(v_late))
        return v_late > v_curr

    def _prompt_update(self, release_data: dict) -> None:
        latest_version = release_data.get("tag_name", "unknown")
        ans = messagebox.askyesno(
            "Update Available",
            f"A new version ({latest_version}) of microBRRRute Studio is available.\n\n"
            "Would you like to download and install the update now?"
        )
        if ans:
            threading.Thread(target=self._perform_update, args=(release_data,), daemon=True).start()

    def _perform_update(self, release_data: dict) -> None:
        assets = release_data.get("assets", [])
        download_url = None
        asset_name = None
        
        sys_plat = sys.platform
        if sys_plat == "win32":
            platform_keyword = "windows"
        elif sys_plat == "darwin":
            platform_keyword = "macos"
        else:
            platform_keyword = "linux"
            
        for asset in assets:
            name = asset.get("name", "").lower()
            if platform_keyword in name and name.endswith(".zip"):
                download_url = asset.get("browser_download_url")
                asset_name = asset.get("name")
                break
                
        is_frozen = getattr(sys, "frozen", False)
        
        if not download_url or not is_frozen:
            self.after(0, lambda: self._open_release_webpage(release_data.get("html_url")))
            return
            
        self.after(0, lambda: self._show_update_progress_ui(asset_name or ""))
        
        try:
            import io
            req = urllib.request.Request(download_url, headers={"User-Agent": "microBRRRute-Studio-Updater"})
            
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                buffer = io.BytesIO()
                block_size = 1024 * 64
                
                while True:
                    block = response.read(block_size)
                    if not block:
                        break
                    buffer.write(block)
                    downloaded += len(block)
                    if total_size > 0:
                        pct = int(downloaded * 100 / total_size)
                        self.after(0, self._update_progress_val, pct)
                        
            self.after(0, lambda: self._update_progress_status("Extracting update..."))
            
            buffer.seek(0)
            with zipfile.ZipFile(buffer) as z:
                exe_name = "microBRRRute_Studio.exe" if sys_plat == "win32" else "microBRRRute_Studio"
                
                exe_member = None
                for member in z.namelist():
                    if member.endswith(exe_name):
                        exe_member = member
                        break
                        
                if not exe_member:
                    raise Exception(f"Executable {exe_name} not found in the downloaded zip archive.")
                
                exe_data = z.read(exe_member)
                
            current_exe = Path(sys.executable).absolute()
            
            self.after(0, lambda: self._update_progress_status("Replacing executable..."))
            
            if sys_plat == "win32":
                old_exe = current_exe.with_name(current_exe.name + ".old")
                if old_exe.exists():
                    try:
                        old_exe.unlink()
                    except Exception:
                        pass
                
                current_exe.rename(old_exe)
                current_exe.write_bytes(exe_data)
                
                self.after(0, lambda: self._finish_update_and_restart(True, old_exe))
            else:
                temp_exe = current_exe.with_name(current_exe.name + ".tmp")
                temp_exe.write_bytes(exe_data)
                temp_exe.chmod(0o755)
                temp_exe.replace(current_exe)
                
                self.after(0, lambda: self._finish_update_and_restart(False, None))
                
        except Exception as e:
            self.after(0, self._handle_update_error, str(e))

    def _open_release_webpage(self, url: str | None) -> None:
        target_url = url or "https://github.com/Whichcraft/microBRRRute_studio/releases/latest"
        ans = messagebox.askyesno(
            "Auto-update Not Supported",
            "Auto-update is only supported when running the pre-built standalone executable.\n\n"
            "Would you like to open the latest release webpage in your browser instead?"
        )
        if ans:
            webbrowser.open(target_url)

    def _show_update_progress_ui(self, asset_name: str) -> None:
        self.update_win = tk.Toplevel(self)
        self.update_win.title("Downloading Update")
        self.update_win.geometry("350x150")
        self.update_win.resizable(False, False)
        self.update_win.transient(self)
        self.update_win.grab_set()
        
        self.update_win.protocol("WM_DELETE_WINDOW", lambda: None)
        
        f = ttk.Frame(self.update_win, padding=20)
        f.pack(fill="both", expand=True)
        
        self.update_label = ttk.Label(f, text=f"Downloading {asset_name}...", wraplength=310)
        self.update_label.pack(anchor="w", pady=5)
        
        self.update_progress = ttk.Progressbar(f, orient="horizontal", mode="determinate")
        self.update_progress.pack(fill="x", pady=10)
        
        self.update_status = ttk.Label(f, text="Connecting...")
        self.update_status.pack(anchor="w")

    def _update_progress_val(self, val: int) -> None:
        if hasattr(self, "update_progress") and self.update_progress.winfo_exists():
            self.update_progress["value"] = val
            self.update_status.config(text=f"Downloaded {val}%")

    def _update_progress_status(self, text: str) -> None:
        if hasattr(self, "update_status") and self.update_status.winfo_exists():
            self.update_status.config(text=text)

    def _handle_update_error(self, err_msg: str) -> None:
        if hasattr(self, "update_win") and self.update_win.winfo_exists():
            self.update_win.destroy()
        messagebox.showerror("Update Error", f"An error occurred during update:\n\n{err_msg}")

    def _finish_update_and_restart(self, is_windows: bool, old_exe_path: Path | None) -> None:
        if hasattr(self, "update_win") and self.update_win.winfo_exists():
            self.update_win.destroy()
            
        messagebox.showinfo("Update Successful", "The update has been successfully installed. The application will now restart.")
        
        self.stop_sequence()
        
        import subprocess
        current_exe = sys.executable
        
        if is_windows and old_exe_path:
            cmd = f'timeout /t 1 /nobreak > nul & del "{old_exe_path}"'
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
            subprocess.Popen([current_exe])
        else:
            subprocess.Popen([current_exe])
            
        self.destroy()
        sys.exit(0)

    def show_randomizer_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("Randomizer")
        win.geometry("350x300")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        f = ttk.Frame(win, padding=20)
        f.pack(fill="both", expand=True)
        root_var = tk.StringVar(value="C")
        scale_var = tk.StringVar(value="Minor Pentatonic")
        oct_var = tk.IntVar(value=2)
        fill_var = tk.IntVar(value=75)
        ttk.Label(f, text="Root").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            f, textvariable=root_var, values=NOTE_NAMES, state="readonly"
        ).grid(row=0, column=1, pady=5)
        ttk.Label(f, text="Scale").grid(row=1, column=0, sticky="w")
        ttk.Combobox(
            f, textvariable=scale_var, values=list(SCALES.keys()), state="readonly"
        ).grid(row=1, column=1, pady=5)
        ttk.Label(f, text="Octaves").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(f, from_=1, to=4, textvariable=oct_var).grid(
            row=2, column=1, pady=5
        )
        ttk.Label(f, text="Fill %").grid(row=3, column=0, sticky="w")
        ttk.Spinbox(f, from_=10, to=100, textvariable=fill_var).grid(
            row=3, column=1, pady=5
        )

        def do_rand():
            rm = NOTE_NAMES.index(root_var.get()) + 36
            ivs = SCALES[scale_var.get()]
            pool = [rm + o * 12 + i for o in range(oct_var.get()) for i in ivs]
            self.push_undo()
            steps = self.steps()
            for i in range(len(steps)):
                if random.randint(1, 100) <= fill_var.get():
                    steps[i] = Step(
                        note=random.choice(pool),
                        accent=(random.random() < 0.2),
                        slide=(random.random() < 0.1),
                    )
                else:
                    steps[i] = Step(note=None)
            self.mark_dirty()
            self.refresh_all()
            win.destroy()

        ttk.Button(f, text="Generate", command=do_rand).grid(
            row=4, column=0, columnspan=2, pady=20
        )

    def show_arpeggiator_dialog(self) -> None:
        steps = self.steps()
        selected = sorted(i for i in self._selection if 0 <= i < len(steps))
        if len(selected) >= 2:
            default_start = selected[0] + 1
            default_end = selected[-1] + 1
        else:
            default_start = min(len(steps), self.cursor.get() + 1)
            default_end = min(len(steps), default_start + 7)

        win = tk.Toplevel(self)
        win.title("Arpeggiator")
        win.geometry("420x460")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        f = ttk.Frame(win, padding=20)
        f.pack(fill="both", expand=True)

        mode = tk.StringVar(value="Up")
        ttk.Label(f, text="Arp Mode").pack(anchor="w")
        ttk.Combobox(
            f,
            textvariable=mode,
            values=["Up", "Down", "Up-Down", "Random"],
            state="readonly",
        ).pack(fill="x", pady=(4, 10))

        target = ttk.LabelFrame(f, text="Target steps", padding=8)
        target.pack(fill="x", pady=(0, 10))
        start_var = tk.IntVar(value=default_start)
        end_var = tk.IntVar(value=default_end)
        ttk.Label(target, text="Start").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            target,
            from_=1,
            to=max(1, len(steps)),
            textvariable=start_var,
            width=6,
        ).grid(row=0, column=1, padx=(4, 16))
        ttk.Label(target, text="End").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(
            target,
            from_=1,
            to=max(1, len(steps)),
            textvariable=end_var,
            width=6,
        ).grid(row=0, column=3, padx=4)

        notes_frame = ttk.LabelFrame(f, text="Source notes", padding=8)
        notes_frame.pack(fill="both", expand=True)
        ttk.Label(
            notes_frame,
            text="Click notes to include or exclude them from the arpeggio.",
        ).pack(anchor="w")
        note_list = tk.Listbox(
            notes_frame,
            selectmode="multiple",
            exportselection=False,
            height=9,
        )
        note_list.pack(fill="both", expand=True, pady=(6, 8))
        available_notes = sorted({step.note for step in steps if step.note is not None})

        def refresh_note_list(select_all: bool = False) -> None:
            note_list.delete(0, "end")
            for note in available_notes:
                note_list.insert("end", f"{midi_to_name(note)} ({note})")
            if select_all and available_notes:
                note_list.selection_set(0, "end")

        refresh_note_list(select_all=True)

        add_row = ttk.Frame(notes_frame)
        add_row.pack(fill="x")
        note_entry = ttk.Entry(add_row)
        note_entry.pack(side="left", fill="x", expand=True)
        note_entry.insert(0, "C3 E3 G3")

        def add_notes() -> None:
            tokens = note_entry.get().replace(",", " ").split()
            if not tokens:
                return
            try:
                new_notes = [name_to_midi(token) for token in tokens]
            except (TypeError, ValueError) as exc:
                messagebox.showerror("Arpeggiator", str(exc), parent=win)
                return
            for note in new_notes:
                if note not in available_notes:
                    available_notes.append(note)
            available_notes.sort()
            refresh_note_list()
            for i, note in enumerate(available_notes):
                if note in new_notes:
                    note_list.selection_set(i)
            note_entry.delete(0, "end")

        ttk.Button(add_row, text="Add notes", command=add_notes).pack(
            side="left", padx=(6, 0)
        )

        def do_arp() -> None:
            start = max(1, min(len(steps), start_var.get()))
            end = max(1, min(len(steps), end_var.get()))
            start, end = sorted((start, end))
            indices = list(range(start - 1, end))
            notes = [available_notes[i] for i in note_list.curselection()]
            if not notes:
                messagebox.showinfo(
                    "Arpeggiator",
                    "Select at least one source note.",
                    parent=win,
                )
                return
            arp_notes = self._build_arpeggio(notes, mode.get())
            self.push_undo()
            for i, idx in enumerate(indices):
                steps[idx].note = arp_notes[i % len(arp_notes)]
            self._selection = set(indices)
            self.cursor.set(indices[0])
            self.mark_dirty()
            self.refresh_all()
            win.destroy()

        buttons = ttk.Frame(f)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Apply Arp", command=do_arp).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(
            side="right", padx=6
        )

    @staticmethod
    def _build_arpeggio(notes: list[int], mode: str) -> list[int]:
        ordered = sorted(set(notes))
        if mode == "Down":
            return list(reversed(ordered))
        if mode == "Up-Down" and len(ordered) > 1:
            return ordered + list(reversed(ordered[1:-1]))
        if mode == "Random":
            shuffled = list(ordered)
            random.shuffle(shuffled)
            return shuffled
        return ordered

    def mark_dirty(self) -> None:
        self.dirty = True
        self.title("* " + APP_TITLE)

    def _snapshot(self) -> dict[int, list[Step]]:
        return {
            k: [Step(s.note, s.gate, s.accent, s.slide) for s in v]
            for k, v in self.project.sequences.items()
        }

    def push_undo(self) -> None:
        self._undo.append(self._snapshot())
        if len(self._undo) > 100:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._snapshot())
            self.project.sequences = self._undo.pop()
            self.mark_dirty()
            self.refresh_all()

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._snapshot())
            self.project.sequences = self._redo.pop()
            self.mark_dirty()
            self.refresh_all()

    def copy_selection(self) -> None:
        if not self._selection:
            return
        steps = self.steps()
        tokens = [
            ("x" if steps[idx].note is None else str(steps[idx].note))
            for idx in sorted(list(self._selection))
            if idx < len(steps)
        ]
        self.clipboard_clear()
        self.clipboard_append(" ".join(tokens))

    @staticmethod
    def _parse_step_tokens(tokens: list[str], limit: int = MAX_STEPS) -> list[int | None]:
        parsed: list[int | None] = []
        for token in tokens[: max(0, limit)]:
            if token.lower() == "x":
                parsed.append(None)
                continue
            note = int(token)
            if not 0 <= note <= 127:
                raise ValueError("MIDI note out of range")
            parsed.append(note)
        return parsed

    def paste_selection(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        tokens = text.split()
        if not tokens:
            return
        paste_limit = max(0, MAX_STEPS - self.cursor.get())
        if paste_limit == 0:
            return
        try:
            parsed = self._parse_step_tokens(tokens, paste_limit)
        except ValueError:
            messagebox.showinfo("Paste Selection", "Clipboard contains invalid data.")
            return
        self.push_undo()
        steps = self.steps()
        start = self.cursor.get()
        for i, v in enumerate(parsed):
            idx = start + i
            if idx >= MAX_STEPS:
                break
            if idx >= len(steps):
                steps.append(Step(note=v))
            else:
                steps[idx].note = v
        self.mark_dirty()
        self.refresh_all()

    def copy_bank(self) -> None:
        steps = self.steps()
        tokens = ["x" if s.note is None else str(s.note) for s in steps]
        self.clipboard_clear()
        self.clipboard_append(" ".join(tokens))

    def paste_bank(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Paste Bank", "Clipboard is empty.")
            return
        tokens = text.split()
        if not tokens:
            return
        try:
            new = [Step(note=note) for note in self._parse_step_tokens(tokens)]
        except ValueError:
            messagebox.showinfo("Paste Bank", "Clipboard contains invalid data.")
            return
        self.push_undo()
        self.project.sequences[int(self.slot.get())] = new
        self.mark_dirty()
        self.refresh_all()

    def transpose_bank(self, semitones: int) -> None:
        self.push_undo()
        steps = self.steps()
        if self._selection:
            for idx in self._selection:
                if 0 <= idx < len(steps):
                    note = steps[idx].note
                    if note is not None:
                        steps[idx].note = max(0, min(127, note + semitones))
        else:
            self.project.sequences[int(self.slot.get())] = transpose_steps(
                steps, semitones
            )
        self.mark_dirty()
        self.refresh_all()

    def import_midi_file(self) -> None:
        p = filedialog.askopenfilename(
            filetypes=[("MIDI file", "*.mid"), ("All files", "*.*")]
        )
        if not p:
            return
        try:
            raw = import_midi(p)
            steps = [Step(note=n) for n in raw][:MAX_STEPS]
            self.push_undo()
            self.project.sequences[int(self.slot.get())] = steps
            self.mark_dirty()
            self.cursor.set(0)
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_midi_file(self) -> None:
        p = filedialog.asksaveasfilename(
            defaultextension=".mid",
            filetypes=[("MIDI file", "*.mid"), ("All files", "*.*")],
        )
        if not p:
            return
        try:
            export_midi(
                p,
                [step.note for step in self.active_steps()],
                bpm=self.tempo.get(),
                ticks_per_step=self._ticks_per_step(),
            )
        except Exception as e:
            messagebox.showerror("MIDI export failed", str(e))

    def export_all_midi_files(self) -> None:
        folder = filedialog.askdirectory(title="Choose folder for 8 MIDI bank exports")
        if not folder:
            return
        try:
            base = self.file_path.stem if self.file_path else "mbseq"
            out = Path(folder)
            for bank in range(1, 9):
                steps = self.project.sequences.get(
                    bank, [Step() for _ in range(MAX_STEPS)]
                )
                export_midi(
                    out / f"{base}_bank_{bank}.mid",
                    [step.note for step in steps[: self._active_length()]],
                    bpm=self.tempo.get(),
                    ticks_per_step=self._ticks_per_step(),
                )
            messagebox.showinfo(
                "Export complete", f"Exported 8 MIDI files to:\n{folder}"
            )
        except Exception as e:
            messagebox.showerror("MIDI export failed", str(e))

    def export_song_midi_file(self) -> None:
        banks = [
            [s.note for s in self.active_steps(b)]
            for b in range(1, 9)
            if b in self.project.sequences
            and any(s.note is not None for s in self.active_steps(b))
        ]
        if not banks:
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".mid", filetypes=[("MIDI file", "*.mid")]
        )
        if p:
            try:
                export_song_midi(
                    p,
                    banks,
                    bpm=self.tempo.get(),
                    ticks_per_step=self._ticks_per_step(),
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def export_bank_wav(self) -> None:
        p = filedialog.asksaveasfilename(
            defaultextension=".wav", filetypes=[("WAV audio", "*.wav")]
        )
        if p:
            try:
                render_steps_wav(
                    p,
                    self.active_steps(),
                    bpm=self.tempo.get(),
                    wave_shape=self.wave_shape.get(),
                    volume=self.volume.get(),
                    attack=self.attack.get(),
                    decay=self.decay.get(),
                    sustain=self.sustain.get(),
                    release=self.release.get(),
                    metronome=self.metronome.get(),
                    steps_per_quarter=self._step_divisor(),
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def on_close(self) -> None:
        self.stop_sequence()
        self._save_settings()
        if self.dirty and not messagebox.askokcancel("Unsaved changes", "Quit?"):
            return
        self.destroy()

    def refresh_raw(self) -> None:
        self.raw.delete("1.0", "end")
        self.raw.insert("1.0", self.project.serialize())

    def on_resize(self, event: tk.Event) -> None:
        if event.widget == self:
            self.refresh_grid()
            self.refresh_piano_roll()

    def refresh_grid(self) -> None:
        steps = self.active_steps()
        if self.cursor.get() >= len(steps):
            self.cursor.set(max(0, len(steps) - 1))
        self._sync_cursor_display()
        win_width = self.winfo_width()
        btn_width = 65
        cols = max(1, (win_width - 40) // btn_width)
        children = self.grid_inner.winfo_children()
        if self._last_cols != cols or len(children) != len(steps) * 2:
            for w in children:
                w.destroy()
            self.step_buttons.clear()
            self._last_cols = cols
            for i in range(len(steps)):
                row, col = (i // cols) * 2, i % cols
                ttk.Label(self.grid_inner, text=str(i + 1), anchor="center").grid(
                    row=row, column=col, padx=1
                )
                b = tk.Button(self.grid_inner, width=7, height=2, highlightthickness=0)
                b.grid(row=row + 1, column=col, padx=1, pady=(0, 4))
                b.bind(
                    "<Button-3>",
                    lambda e, x=i: self._show_step_context_menu(e, x),  # type: ignore[misc]
                )
                b.bind(
                    "<ButtonPress-1>",
                    lambda e, x=i: self._on_step_click(e, x),  # type: ignore[misc]
                )
                b.bind("<B1-Motion>", self._on_drag_motion)
                b.bind(
                    "<ButtonRelease-1>",
                    lambda e, x=i: self._on_drag_stop(e, x),  # type: ignore[misc]
                )
                self.step_buttons.append(b)
        for i, s in enumerate(steps):
            txt = f"{'x' if s.note is None else midi_to_name(s.note)}{('•' if s.accent else '') + ('→' if s.slide else '')}\n{s.note if s.note is not None else 'x'}"
            if i == self._playhead:
                bg, fg = "#7CFC8A", "#000000"
            elif i in self._selection:
                bg, fg = ("#ffa500" if self.dark_mode.get() else "#ffcc00"), "#000000"
            elif i == self.cursor.get():
                bg, fg = (
                    ("#0078d7" if self.dark_mode.get() else "#d7f0ff"),
                    ("#ffffff" if self.dark_mode.get() else "#000000"),
                )
            else:
                bg, fg = (
                    ("#404040" if self.dark_mode.get() else "#ffffff"),
                    ("#ffffff" if self.dark_mode.get() else "#000000"),
                )
            self.step_buttons[i].config(
                text=txt,
                bg=bg,
                fg=fg,
                highlightthickness=2 if i in self._selection else 0,
                command=lambda x=i: self.select_step(x),
            )
        self.refresh_status()

    def _change_piano_roll_orientation(self) -> None:
        self._piano_roll_off_x = 0.0
        self._piano_roll_off_y = 0
        self._piano_roll_drag_start = None
        self._piano_roll_drag_current = None
        self._save_settings()
        self.refresh_piano_roll()

    def _piano_roll_metrics(
        self,
    ) -> tuple[float, float, float, float, float, float, float]:
        w = float(self.piano_roll.winfo_width())
        h = float(self.piano_roll.winfo_height())
        steps = self.active_steps()
        if self.piano_roll_orientation.get() == "vertical":
            keyboard_size = 50.0
            draw_w = max(1.0, w)
            draw_h = max(1.0, h - keyboard_size)
            step_size = draw_h / max(1, len(steps)) * self._piano_roll_zoom
            note_size = draw_w / 24 * self._piano_roll_zoom_x
        else:
            keyboard_size = 60.0
            draw_w = max(1.0, w - keyboard_size)
            draw_h = max(1.0, h)
            step_size = draw_w / max(1, len(steps)) * self._piano_roll_zoom_x
            note_size = draw_h / 24 * self._piano_roll_zoom
        return w, h, keyboard_size, draw_w, draw_h, step_size, note_size

    def _clamp_piano_roll_x(self) -> None:
        _, _, _, draw_w, _, step_size, note_size = self._piano_roll_metrics()
        if self.piano_roll_orientation.get() == "vertical":
            content_w = note_size * (MAX_PLAYABLE - MIN_PLAYABLE + 1)
        else:
            content_w = step_size * len(self.active_steps())
        self._piano_roll_off_x = min(
            0.0,
            max(min(0.0, draw_w - content_w), self._piano_roll_off_x),
        )

    @staticmethod
    def _wheel_up(event: tk.Event) -> bool:
        return getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0

    def _on_piano_roll_scroll(self, event: tk.Event) -> None:
        wheel_up = self._wheel_up(event)
        state = int(event.state)
        ctrl = bool(state & (0x0004 | 0x20000))
        shift = bool(state & 0x0001)
        if ctrl and shift:
            factor = 1.1 if wheel_up else 1 / 1.1
            self._piano_roll_zoom_x = max(
                1.0,
                min(10.0, self._piano_roll_zoom_x * factor),
            )
            self._clamp_piano_roll_x()
        elif ctrl:
            factor = 1.1 if wheel_up else 1 / 1.1
            self._piano_roll_zoom = max(
                0.5,
                min(5.0, self._piano_roll_zoom * factor),
            )
        elif shift:
            self._piano_roll_off_x += 60 if wheel_up else -60
            self._clamp_piano_roll_x()
        else:
            self._piano_roll_off_y += 30 if wheel_up else -30
        self.refresh_piano_roll()

    def refresh_piano_roll(self) -> None:
        self.piano_roll.delete("all")
        w, h, keyboard_size, _, _, step_size, note_size = self._piano_roll_metrics()
        if w < 10 or h < 10:
            return
        steps = self.active_steps()
        cursor_note = None
        if 0 <= self.cursor.get() < len(steps):
            cursor_note = steps[self.cursor.get()].note
        selected_notes: set[int] = set()
        for i in self._selection:
            if 0 <= i < len(steps):
                note = steps[i].note
                if note is not None:
                    selected_notes.add(note)
        playing_note = None
        if self.playing and 0 <= self._playhead < len(steps):
            playing_note = steps[self._playhead].note
        if self.piano_roll_orientation.get() == "vertical":
            self._draw_vertical_piano_roll(
                w,
                h,
                keyboard_size,
                step_size,
                note_size,
                steps,
                cursor_note,
                selected_notes,
                playing_note,
            )
        else:
            self._draw_horizontal_piano_roll(
                w,
                h,
                keyboard_size,
                step_size,
                note_size,
                steps,
                cursor_note,
                selected_notes,
                playing_note,
            )
        if self._piano_roll_drag_start and self._piano_roll_drag_current:
            x1, y1 = self._piano_roll_drag_start
            x2, y2 = self._piano_roll_drag_current
            self.piano_roll.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline="#7CFC8A",
                width=2,
                dash=(4, 2),
                tags="selection_box",
            )

    @staticmethod
    def _piano_key_colors(
        note: int,
        cursor_note: int | None,
        selected_notes: set[int],
        playing_note: int | None,
    ) -> tuple[str, str]:
        if note == playing_note:
            bg = "#7CFC8A"
        elif note == cursor_note:
            bg = "#0078d7"
        elif note in selected_notes:
            bg = "#ffa500"
        else:
            bg = "#000000" if note % 12 in [1, 3, 6, 8, 10] else "#ffffff"
        fg = "#ffffff" if bg in ("#000000", "#0078d7") else "#000000"
        return bg, fg

    def _draw_horizontal_piano_roll(
        self,
        w: float,
        h: float,
        keyboard_w: float,
        step_w: float,
        note_h: float,
        steps: list[Step],
        cursor_note: int | None,
        selected_notes: set[int],
        playing_note: int | None,
    ) -> None:
        for note in range(MIN_PLAYABLE, MAX_PLAYABLE + 1):
            y = h - (note - MIN_PLAYABLE + 1) * note_h + self._piano_roll_off_y
            if -note_h < y < h + note_h:
                fill = "#2a2a2a" if note % 12 in [1, 3, 6, 8, 10] else "#333333"
                self.piano_roll.create_rectangle(
                    keyboard_w, y, w, y + note_h, fill=fill, outline="#222222"
                )
        for i, step in enumerate(steps):
            x = keyboard_w + self._piano_roll_off_x + i * step_w
            if keyboard_w - step_w < x < w:
                if i == self._playhead:
                    self.piano_roll.create_rectangle(
                        x,
                        0,
                        x + step_w,
                        h,
                        fill="#7CFC8A",
                        stipple="gray25",
                        outline="",
                    )
                if step.note is not None:
                    y = (
                        h
                        - (step.note - MIN_PLAYABLE + 1) * note_h
                        + self._piano_roll_off_y
                    )
                    self._draw_piano_roll_note(i, step, x, y, step_w, note_h)
                self._draw_step_indicator(i, x, 0, step_w, 18, vertical=False)
        for note in range(MIN_PLAYABLE, MAX_PLAYABLE + 1):
            y = h - (note - MIN_PLAYABLE + 1) * note_h + self._piano_roll_off_y
            if -note_h < y < h + note_h:
                bg, fg = self._piano_key_colors(
                    note, cursor_note, selected_notes, playing_note
                )
                self.piano_roll.create_rectangle(
                    0, y, keyboard_w, y + note_h, fill=bg, outline="#888888"
                )
                if note % 12 == 0 or note in (playing_note, cursor_note):
                    self.piano_roll.create_text(
                        keyboard_w / 2,
                        y + note_h / 2,
                        text=midi_to_name(note),
                        fill=fg,
                        font=("Consolas", max(6, int(8 * self._piano_roll_zoom))),
                    )
        self.piano_roll.create_line(keyboard_w, 0, keyboard_w, h, fill="#aaaaaa")

    def _draw_vertical_piano_roll(
        self,
        w: float,
        h: float,
        keyboard_h: float,
        step_h: float,
        note_w: float,
        steps: list[Step],
        cursor_note: int | None,
        selected_notes: set[int],
        playing_note: int | None,
    ) -> None:
        for note in range(MIN_PLAYABLE, MAX_PLAYABLE + 1):
            x = (note - MIN_PLAYABLE) * note_w + self._piano_roll_off_x
            if -note_w < x < w + note_w:
                fill = "#2a2a2a" if note % 12 in [1, 3, 6, 8, 10] else "#333333"
                self.piano_roll.create_rectangle(
                    x, keyboard_h, x + note_w, h, fill=fill, outline="#222222"
                )
        for i, step in enumerate(steps):
            y = keyboard_h + self._piano_roll_off_y + i * step_h
            if keyboard_h - step_h < y < h:
                if i == self._playhead:
                    self.piano_roll.create_rectangle(
                        0,
                        y,
                        w,
                        y + step_h,
                        fill="#7CFC8A",
                        stipple="gray25",
                        outline="",
                    )
                if step.note is not None:
                    x = (step.note - MIN_PLAYABLE) * note_w + self._piano_roll_off_x
                    self._draw_piano_roll_note(i, step, x, y, note_w, step_h)
                self._draw_step_indicator(i, 0, y, 34, step_h, vertical=True)
        for note in range(MIN_PLAYABLE, MAX_PLAYABLE + 1):
            x = (note - MIN_PLAYABLE) * note_w + self._piano_roll_off_x
            if -note_w < x < w + note_w:
                bg, fg = self._piano_key_colors(
                    note, cursor_note, selected_notes, playing_note
                )
                self.piano_roll.create_rectangle(
                    x, 0, x + note_w, keyboard_h, fill=bg, outline="#888888"
                )
                if note % 12 == 0 or note in (playing_note, cursor_note):
                    self.piano_roll.create_text(
                        x + note_w / 2,
                        keyboard_h / 2,
                        text=midi_to_name(note),
                        fill=fg,
                        angle=90,
                        font=("Consolas", max(6, int(8 * self._piano_roll_zoom_x))),
                    )
        self.piano_roll.create_line(0, keyboard_h, w, keyboard_h, fill="#aaaaaa")

    def _draw_step_indicator(
        self,
        idx: int,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        vertical: bool,
    ) -> None:
        if idx == self._playhead:
            fill, fg = "#7CFC8A", "#000000"
        elif idx == self.cursor.get():
            fill, fg = "#0078d7", "#ffffff"
        elif idx in self._selection:
            fill, fg = "#ffa500", "#000000"
        else:
            fill, fg = "#202020", "#cccccc"
        if vertical:
            self.piano_roll.create_rectangle(
                x, y, x + width, y + height, fill=fill, outline="#555555"
            )
            if height >= 12 and (idx % 4 == 0 or height >= 18):
                self.piano_roll.create_text(
                    x + width / 2,
                    y + height / 2,
                    text=str(idx + 1),
                    fill=fg,
                    font=("Consolas", 7),
                )
            self.piano_roll.create_line(
                0, y, self.piano_roll.winfo_width(), y, fill="#444444"
            )
        else:
            self.piano_roll.create_rectangle(
                x, y, x + width, y + height, fill=fill, outline="#555555"
            )
            if width >= 18 and (idx % 4 == 0 or width >= 24):
                self.piano_roll.create_text(
                    x + width / 2,
                    y + height / 2,
                    text=str(idx + 1),
                    fill=fg,
                    font=("Consolas", 7),
                )
            self.piano_roll.create_line(
                x, 0, x, self.piano_roll.winfo_height(), fill="#444444"
            )

    def _draw_piano_roll_note(
        self,
        idx: int,
        step: Step,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        if idx in self._selection:
            color = "#ffa500"
        elif idx == self.cursor.get():
            color = "#0078d7"
        else:
            color = "#ffffff" if step.accent else "#ffcc00"
        if step.slide:
            self.piano_roll.create_rectangle(
                x + 1, y + 1, x + width - 1, y + height - 1,
                fill=color, outline="#ffffff",
            )
        elif idx in self._selection:
            self.piano_roll.create_rectangle(
                x + 1, y + 1, x + width - 1, y + height - 1,
                fill=color, outline="#ffa500",
            )
        else:
            self.piano_roll.create_rectangle(
                x + 1, y + 1, x + width - 1, y + height - 1,
                fill=color,
            )

    def _piano_roll_position(self, x: float, y: float) -> tuple[int, int]:
        _, h, keyboard_size, _, _, step_size, note_size = self._piano_roll_metrics()
        if self.piano_roll_orientation.get() == "vertical":
            step_idx = math.floor(
                (y - keyboard_size - self._piano_roll_off_y) / step_size
            )
            note_val = (
                math.floor((x - self._piano_roll_off_x) / note_size) + MIN_PLAYABLE
            )
        else:
            step_idx = math.floor(
                (x - keyboard_size - self._piano_roll_off_x) / step_size
            )
            note_val = math.floor(
                (h + self._piano_roll_off_y - y) / note_size + MIN_PLAYABLE - 1
            )
        return step_idx, note_val

    def _on_piano_roll_press(self, event: tk.Event) -> None:
        _, _, keyboard_size, _, _, _, _ = self._piano_roll_metrics()
        on_keyboard = (
            event.y < keyboard_size
            if self.piano_roll_orientation.get() == "vertical"
            else event.x < keyboard_size
        )
        if on_keyboard:
            _, note_val = self._piano_roll_position(event.x, event.y)
            if MIN_PLAYABLE <= note_val <= MAX_PLAYABLE:
                self.preview_note(note_val)
            self._piano_roll_drag_start = None
            return
        self._piano_roll_drag_start = (event.x, event.y)
        self._piano_roll_drag_current = (event.x, event.y)
        self._piano_roll_drag_state = int(event.state)

    def _on_piano_roll_drag(self, event: tk.Event) -> None:
        if self._piano_roll_drag_start is None:
            return
        self._piano_roll_drag_current = (event.x, event.y)
        self.refresh_piano_roll()

    def _on_piano_roll_release(self, event: tk.Event) -> None:
        if self._piano_roll_drag_start is None:
            return
        start_x, start_y = self._piano_roll_drag_start
        dragged = abs(event.x - start_x) >= 4 or abs(event.y - start_y) >= 4
        if dragged:
            start_step, start_note = self._piano_roll_position(start_x, start_y)
            end_step, end_note = self._piano_roll_position(event.x, event.y)
            first_step, last_step = sorted((start_step, end_step))
            low_note, high_note = sorted((start_note, end_note))
            matched = {
                i
                for i, step in enumerate(self.active_steps())
                if first_step <= i <= last_step
                and step.note is not None
                and low_note <= step.note <= high_note
            }
            if self._piano_roll_drag_state & (0x0004 | 0x20000):
                self._selection.symmetric_difference_update(matched)
            elif self._piano_roll_drag_state & 0x0001:
                self._selection.update(matched)
            else:
                self._selection = matched
            if matched:
                self.cursor.set(min(matched))
            self.refresh_grid()
        else:
            self._on_piano_roll_click(event)
        self._piano_roll_drag_start = None
        self._piano_roll_drag_current = None
        self.refresh_piano_roll()

    def _on_piano_roll_click(self, event: tk.Event) -> None:
        steps = self.active_steps()
        step_idx, note_val = self._piano_roll_position(event.x, event.y)
        if 0 <= step_idx < len(steps) and MIN_PLAYABLE <= note_val <= MAX_PLAYABLE:
            self.select_step(step_idx)
            self.push_undo()
            steps[step_idx].note = note_val
            self.mark_dirty()
            self.refresh_all()

    def _show_step_context_menu(self, event: tk.Event, idx: int):
        self.select_step(idx)
        m = tk.Menu(self, tearoff=0)
        s = self.steps()[idx]
        m.add_command(
            label="Set Rest",
            command=lambda i=idx: self.set_step_rest(i),  # type: ignore[misc]
        )
        m.add_separator()
        m.add_command(
            label="Unset Accent" if s.accent else "Set Accent",
            command=lambda i=idx: self.toggle_step_accent(i),  # type: ignore[misc]
        )
        m.add_command(
            label="Unset Slide" if s.slide else "Set Slide",
            command=lambda i=idx: self.toggle_step_slide(i),  # type: ignore[misc]
        )
        gm = tk.Menu(m, tearoff=0)
        for g in [0.25, 0.5, 0.82, 1.0]:
            gm.add_radiobutton(
                label=f"{int(g * 100)}%",
                command=lambda v=g, i=idx: self.set_step_gate(i, v),  # type: ignore[misc]
            )
        m.add_cascade(label="Gate Length", menu=gm)
        m.post(event.x_root, event.y_root)

    def toggle_step_accent(self, idx: int):
        self.push_undo()
        self.steps()[idx].accent = not self.steps()[idx].accent
        self.mark_dirty()
        self.refresh_all()

    def toggle_step_slide(self, idx: int):
        self.push_undo()
        self.steps()[idx].slide = not self.steps()[idx].slide
        self.mark_dirty()
        self.refresh_all()

    def set_step_gate(self, idx: int, val: float):
        self.push_undo()
        self.steps()[idx].gate = val
        self.mark_dirty()
        self.refresh_grid()

    def set_step_rest(self, idx: int):
        self.push_undo()
        self.steps()[idx].note = None
        self.mark_dirty()
        self.cursor.set(idx)
        self.refresh_all()

    def preview_note(self, note: int, duration: float = 0.18) -> None:
        play_note(
            note,
            duration=duration,
            wave_shape=self.wave_shape.get(),
            volume=self.volume.get(),
        )
        self.highlight_note(note)

    def highlight_note(self, note: int) -> None:
        if note not in self.key_rects:
            return
        rect = self.key_rects[note]
        rel = note - (self.root_note + self.octave_shift.get() * 12)
        self.keyboard.itemconfig(rect, fill="#7CFC8A")

        def _restore(r: int = rect, rl: int = rel) -> None:
            self.keyboard.itemconfig(
                r, fill=("black" if rl in BLACK_OFFSETS else "white")
            )

        self.after(200, _restore)

    def insert_note(self, note: int) -> None:
        self.preview_note(note)
        steps = self.steps()
        idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit():
            return
        self.push_undo()
        if idx >= len(steps):
            steps.append(Step(note=note))
        else:
            steps[idx].note = note
        self.mark_dirty()
        self.move_cursor(1, refresh=False)
        self.refresh_all()

    def insert_rest(self) -> None:
        steps = self.steps()
        idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit():
            return
        self.push_undo()
        if idx >= len(steps):
            steps.append(Step(note=None))
        else:
            steps[idx].note = None
        self.mark_dirty()
        self.move_cursor(1, refresh=False)
        self.refresh_all()

    def move_cursor(self, delta: int, refresh=True) -> None:
        self.cursor.set(
            max(0, min(len(self.active_steps()) - 1, self.cursor.get() + delta))
        )
        self._sync_cursor_display()
        if refresh:
            self.refresh_grid()
            self.refresh_piano_roll()

    def change_slot(self) -> None:
        self.cursor.set(0)
        self.bank_name_var.set(
            self.project.bank_names.get(int(self.slot.get()), f"Bank {self.slot.get()}")
        )
        self.clear_selection()
        self.refresh_all()

    def clear_selection(self) -> None:
        self._selection.clear()
        self.refresh_grid()
        self.refresh_piano_roll()

    def add_step(self) -> None:
        if not self._at_step_limit():
            self.push_undo()
            active_len = self._active_length()
            pos = (
                min(sorted(self._selection)[0] + 1, active_len)
                if self._selection
                else min(self.cursor.get() + 1, active_len)
            )
            self.steps().insert(pos, Step())
            del self.steps()[MAX_STEPS:]
            self.bank_length.set(min(MAX_STEPS, active_len + 1))
            self.mark_dirty()
            self.cursor.set(pos)
            self.refresh_all()
            self.refresh_raw()

    def delete_step(self) -> None:
        steps = self.steps()
        if not steps:
            return
        self.push_undo()
        active_len = self._active_length()
        if self._selection:
            removed = 0
            for idx in sorted(list(self._selection), reverse=True):
                if 0 <= idx < active_len and idx < len(steps):
                    steps.pop(idx)
                    removed += 1
            steps.extend(Step() for _ in range(MAX_STEPS - len(steps)))
            self.bank_length.set(max(1, active_len - removed))
            self.clear_selection()
        else:
            idx = min(self.cursor.get(), active_len - 1)
            steps.pop(idx)
            steps.append(Step())
            self.bank_length.set(max(1, active_len - 1))
        if not steps:
            steps.append(Step())
        self.mark_dirty()
        self.cursor.set(min(self.cursor.get(), self._active_length() - 1))
        self.refresh_all()

    def clear_slot(self) -> None:
        if messagebox.askyesno("Clear", "Clear bank?"):
            self.push_undo()
            self.project.sequences[int(self.slot.get())] = [
                Step() for _ in range(MAX_STEPS)
            ]
            self.mark_dirty()
            self.cursor.set(0)
            self.refresh_all()

    def _confirm_discard_changes(self) -> bool:
        return not self.dirty or messagebox.askokcancel(
            "Unsaved changes",
            "Discard unsaved changes?",
        )

    def _do_open(self, p: str | Path) -> None:
        try:
            self.project = MbseqProject.load(p)
            self.file_path = Path(p)
            self.dirty = False
            self._undo.clear()
            self._redo.clear()
            self.slot.set(1)
            self.bank_name_var.set(self.project.bank_names.get(1, "Bank 1"))
            self.cursor.set(0)
            self.refresh_all()
            self._add_recent(p)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_file(self) -> None:
        if not self._confirm_discard_changes():
            return
        p = filedialog.askopenfilename(filetypes=[("MBSEQ", "*.mbseq"), ("All", "*.*")])
        if p:
            self._do_open(p)

    def _do_save(self, p: str | Path) -> None:
        try:
            self.project.save(p)
            self.file_path = Path(p)
            self.dirty = False
            self.refresh_status()
            self._add_recent(p)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_file(self) -> None:
        self.save_as() if not self.file_path else self._do_save(self.file_path)

    def save_as(self) -> None:
        p = filedialog.asksaveasfilename(
            defaultextension=".mbseq", filetypes=[("MBSEQ", "*.mbseq")]
        )
        if p:
            self._do_save(p)

    def apply_raw(self) -> None:
        try:
            project = MbseqProject.parse(self.raw.get("1.0", "end"))
            self.push_undo()
            self.project = project
            self.slot.set(1)
            self.bank_name_var.set(
                self.project.bank_names.get(
                    int(self.slot.get()), f"Bank {self.slot.get()}"
                )
            )
            self.mark_dirty()
            self.cursor.set(0)
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _step_divisor(self) -> int:
        return 4 if self.step_res.get() == "1/16" else 2

    def _ticks_per_step(self) -> int:
        return 480 // self._step_divisor()

    def toggle_play(self) -> None:
        self.stop_sequence() if self.playing else self.play_sequence()

    def play_sequence(self) -> None:
        self.stop_sequence()
        self._play_banks = [int(self.slot.get())]
        self._start_playback()

    def _start_playback(self) -> None:
        bank = self._play_banks[0]
        steps = self.active_steps(bank)
        if not any(s.note is not None for s in steps):
            messagebox.showinfo("Info", "Bank empty")
            return
        self.playing = True
        self._play_idx = 0
        if self.play_btn:
            self.play_btn.config(state="disabled")
        if self.stop_btn:
            self.stop_btn.config(state="normal")
        self.refresh_all()
        data = render_steps_to_data(
            steps,
            bpm=self.tempo.get(),
            wave_shape=self.wave_shape.get(),
            volume=self.volume.get(),
            attack=self.attack.get(),
            decay=self.decay.get(),
            sustain=self.sustain.get(),
            release=self.release.get(),
            metronome=self.metronome.get(),
            steps_per_quarter=self._step_divisor(),
        )
        self._pre_render_file = (
            Path(tempfile.gettempdir()) / f"mbseq_{uuid.uuid4().hex}.wav"
        )
        render_pre_rendered_wav(self._pre_render_file, data)
        if self.count_in.get():
            self._play_count_in(8)
        else:
            self._start_audio_and_tick()

    def _start_audio_and_tick(self) -> None:
        if self.playing and self._pre_render_file:
            play_pre_rendered_wav(self._pre_render_file)
            self._play_tick()

    def _play_count_in(self, s: int) -> None:
        if not self.playing:
            return
        if s <= 0:
            return self._start_audio_and_tick()
        ms = int(30000 / max(1, self.tempo.get()))
        self.preview_note(84 if s % 2 == 0 else 72, 0.03)
        self._after_id = self.after(ms, lambda: self._play_count_in(s - 1))

    def _play_tick(self) -> None:
        if not self.playing:
            return
        steps = self.active_steps()
        ms = int(60000 / max(1, self.tempo.get()) / self._step_divisor())
        if not steps or self._play_idx >= len(steps):
            self._advance_bank()
            return
        self._playhead = self._play_idx
        self.refresh_grid()
        self.refresh_piano_roll()
        n = steps[self._playhead].note
        if n is not None:
            self.highlight_note(n)
        self._play_idx += 1
        self._after_id = self.after(ms, self._play_tick)

    def _advance_bank(self) -> None:
        if self.loop.get():
            self._play_idx = 0
            self._playhead = -1
            self.refresh_all()
            if self._pre_render_file:
                play_pre_rendered_wav(self._pre_render_file)
            self._after_id = self.after(1, self._play_tick)
        else:
            self.stop_sequence()

    def stop_sequence(self) -> None:
        self.playing = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        stop_all()
        if self._pre_render_file:
            try:
                self._pre_render_file.unlink()
            except Exception:
                pass
            self._pre_render_file = None
        self._playhead = -1
        if self.play_btn:
            self.play_btn.config(state="normal")
        if self.stop_btn:
            self.stop_btn.config(state="disabled")
        self.refresh_grid()
        self.refresh_piano_roll()

    def _on_drag_start(self, idx: int) -> None:
        self._drag_idx = idx

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag_idx is None:
            return
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        for i, btn in enumerate(self.step_buttons):
            if btn == target:
                btn.config(
                    highlightthickness=3,
                    highlightbackground="#7CFC8A",
                    bg="#e8ffea" if not self.dark_mode.get() else "#1a331c",
                )
            else:
                is_sel = i in self._selection
                is_cur = i == self.cursor.get()
                bg = (
                    ("#ffa500" if self.dark_mode.get() else "#ffcc00")
                    if is_sel
                    else (
                        ("#0078d7" if self.dark_mode.get() else "#d7f0ff")
                        if is_cur
                        else ("#404040" if self.dark_mode.get() else "#ffffff")
                    )
                )
                btn.config(
                    highlightthickness=2 if is_sel else 0,
                    highlightbackground="#ffffff",
                    bg=bg,
                )

    def _on_drag_stop(self, event: tk.Event, src_idx: int) -> None:
        if self._drag_idx is None:
            return
        for btn in self.step_buttons:
            btn.config(highlightthickness=0)
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        dst_idx = next(
            (i for i, b in enumerate(self.step_buttons) if b == target), None
        )
        if dst_idx is not None and dst_idx != src_idx:
            self.push_undo()
            steps = self.steps()
            steps.insert(dst_idx, steps.pop(src_idx))
            self.mark_dirty()
            self.refresh_all()
        self._drag_idx = None

    def _on_step_click(self, event: tk.Event, idx: int) -> None:
        self._on_drag_start(idx)
        self.select_step(idx, event)

    def select_step(self, idx: int, event: tk.Event | None = None) -> None:
        steps = self.active_steps()
        if not 0 <= idx < len(steps):
            return
        old_cursor = self.cursor.get()
        self.cursor.set(idx)
        state = int(event.state) if event else 0
        if state & 0x0001:
            start, end = sorted((old_cursor, idx))
            self._selection.update(range(start, end + 1))
        elif state & (0x0004 | 0x20000):
            if idx in self._selection:
                self._selection.remove(idx)
            else:
                self._selection.add(idx)
        else:
            self._selection = {idx}
        self.refresh_grid()
        self.refresh_piano_roll()
        note = steps[idx].note
        if note is not None:
            self.preview_note(note)

    def refresh_keyboard(self) -> None:
        bg_col = "#333333" if self.dark_mode.get() else "#666666"
        self.keyboard.configure(bg=bg_col)
        self.keyboard.delete("all")
        self.key_rects.clear()
        white_w, white_h = 66, 180
        black_w, black_h = 42, 108
        x0, y0 = 10.0, 10.0
        for wi, off in enumerate(WHITE_OFFSETS):
            note = self.note_for_index(off)
            x = x0 + wi * white_w
            rect = self.keyboard.create_rectangle(
                x, y0, x + white_w, y0 + white_h, fill="white", outline="black"
            )
            self.key_rects[note] = rect
            self.keyboard.tag_bind(
                rect,
                "<Button-1>",
                lambda e, n=note: self.insert_note(n),  # type: ignore[misc]
            )
            self.keyboard.tag_bind(
                rect,
                "<Button-3>",
                lambda e, n=note: self.preview_note(n),  # type: ignore[misc]
            )
            self.keyboard.create_text(
                x + white_w / 2,
                y0 + white_h - 22,
                text=midi_to_name(note),
                fill="black",
                state="disabled",
            )
        for off in BLACK_OFFSETS:
            note = self.note_for_index(off)
            x = x0 + BLACK_POS[off] * white_w
            rect = self.keyboard.create_rectangle(
                x, y0, x + black_w, y0 + black_h, fill="black", outline="black"
            )
            self.key_rects[note] = rect
            self.keyboard.tag_bind(
                rect,
                "<Button-1>",
                lambda e, n=note: self.insert_note(n),  # type: ignore[misc]
            )
            self.keyboard.tag_bind(
                rect,
                "<Button-3>",
                lambda e, n=note: self.preview_note(n),  # type: ignore[misc]
            )
            self.keyboard.create_text(
                x + black_w / 2,
                y0 + black_h - 18,
                text=midi_to_name(note),
                fill="white",
                state="disabled",
            )
        low = self.note_for_index(0)
        high = self.note_for_index(24)
        self.keyboard.create_text(
            20,
            202,
            anchor="w",
            fill="#ffffff",
            text=f"Range: {midi_to_name(low)} to {midi_to_name(high)}",
        )

    def duplicate_bank_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("Duplicate")
        win.geometry("300x150")
        win.transient(self)
        win.grab_set()
        f = ttk.Frame(win, padding=20)
        f.pack(fill="both", expand=True)
        source = int(self.slot.get())
        target = tk.IntVar(value=1 if source != 1 else 2)
        ttk.Label(f, text=f"Duplicate bank {self.slot.get()} to:").grid(row=0, column=0)
        ttk.Combobox(
            f,
            textvariable=target,
            values=tuple(str(i) for i in range(1, 9)),
            state="readonly",
        ).grid(row=0, column=1)

        def do():
            t = target.get()
            if not (1 <= t <= 8):
                messagebox.showinfo("Duplicate", "Choose a bank from 1 to 8.", parent=win)
                return
            if t == source:
                messagebox.showinfo("Duplicate", "Choose a different target bank.", parent=win)
                return
            self.push_undo()
            self.project.sequences[t] = [
                Step(s.note, s.gate, s.accent, s.slide) for s in self.steps()
            ]
            self.mark_dirty()
            self.refresh_status()
            win.destroy()

        ttk.Button(f, text="Copy", command=do).grid(row=1, column=0, pady=10)
        ttk.Button(f, text="Cancel", command=win.destroy).grid(row=1, column=1, pady=10)


def main():
    MbseqStudio().mainloop()


if __name__ == "__main__":
    main()
