from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
import uuid
import tempfile
import sys
import random
if sys.platform == 'win32':
    import ctypes

from .mbseq import (
    MbseqProject, Step, midi_to_name, transpose_steps,
    MIN_PLAYABLE, MAX_PLAYABLE
)
from .synth import (
    play_note, get_last_audio_error, stop_all, render_steps_wav,
    render_steps_to_data, render_pre_rendered_wav, play_pre_rendered_wav
)
from .midi_export import export_midi, export_song_midi, import_midi

MAX_STEPS = 64
WHITE_OFFSETS = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24]
BLACK_OFFSETS = [1, 3, 6, 8, 10, 13, 15, 18, 20, 22]
BLACK_POS = {1: 0.65, 3: 1.65, 6: 3.65, 8: 4.65, 10: 5.65, 13: 7.65, 15: 8.65, 18: 10.65, 20: 11.65, 22: 12.65}
PC_KEYS = list('awsedftgyhujkolpö')

SCALES = {
    'Chromatic': list(range(12)),
    'Major': [0, 2, 4, 5, 7, 9, 11],
    'Minor': [0, 2, 3, 5, 7, 8, 10],
    'Major Pentatonic': [0, 2, 4, 7, 9],
    'Minor Pentatonic': [0, 3, 5, 7, 10],
    'Blues': [0, 3, 5, 6, 7, 10],
    'Phrygian Dominant': [0, 1, 4, 5, 7, 8, 10],
}

class ToolTip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind('<Enter>', lambda e: self.show_tip())
        widget.bind('<Leave>', lambda e: self.hide_tip())

    def show_tip(self):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox('insert')
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        tk.Label(tw, text=self.text, justify='left', background='#ffffe0', relief='solid', borderwidth=1, font=('tahoma', '9', 'normal')).pack(ipadx=1)

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class MbseqStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('microBRRRute Studio - MicroBrute SE Composer')
        self.geometry('1380x950')
        self.minsize(1100, 800)
        self._set_icon()
        
        self.project = MbseqProject.empty()
        self.file_path: Path | None = None
        self.slot = tk.IntVar(value=1)
        self.bank_name_var = tk.StringVar(value='Bank 1')
        self.cursor = tk.IntVar(value=0)
        self.octave_shift = tk.IntVar(value=0)
        self.root_note = 48
        self.tempo = tk.IntVar(value=120)
        self.wave_shape = tk.StringVar(value='square')
        self.volume = tk.DoubleVar(value=0.28)
        self.loop = tk.BooleanVar(value=True)
        self.metronome = tk.BooleanVar(value=False)
        self.count_in = tk.BooleanVar(value=False)
        self.dark_mode = tk.BooleanVar(value=False)
        self.step_res = tk.StringVar(value='1/8')
        self.bank_length = tk.IntVar(value=MAX_STEPS)
        self.attack = tk.DoubleVar(value=0.005)
        self.decay = tk.DoubleVar(value=0.1)
        self.sustain = tk.DoubleVar(value=0.5)
        self.release = tk.DoubleVar(value=0.05)
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
        self._piano_roll_off_y = 0
        
        self.step_buttons: list[tk.Button] = []
        self.key_rects: dict[int, int] = {}
        self.recent_files = self._load_recent()
        self.play_btn: ttk.Button | None = None
        self.stop_btn: ttk.Button | None = None

        self._setup_dnd()
        self._build()
        self._bind_keys()
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.refresh_all()

    def _set_icon(self) -> None:
        icon_dir = Path(__file__).parent.parent
        ip = icon_dir / 'icon.png'
        ii = icon_dir / 'icon.ico'
        try:
            if ip.exists():
                self._icon_img = tk.PhotoImage(file=str(ip))
                self.iconphoto(True, self._icon_img)
            elif ii.exists() and sys.platform == 'win32':
                self.iconbitmap(str(ii))
        except Exception: pass

    def _setup_dnd(self) -> None:
        if sys.platform != 'win32': return
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            ctypes.windll.shell32.DragAcceptFiles(hwnd, True) # type: ignore
        except Exception: pass

    def _build(self) -> None:
        self._build_menu()
        top = ttk.Frame(self, padding=8)
        top.pack(fill='x')
        ttk.Label(top, text='Pattern bank').pack(side='left')
        sb = ttk.Combobox(top, textvariable=self.slot, values=list(range(1, 9)), width=4, state='readonly')
        sb.pack(side='left', padx=(4, 8))
        sb.bind('<<ComboboxSelected>>', lambda e: self.change_slot())
        
        self.name_entry = ttk.Entry(top, textvariable=self.bank_name_var, width=15)
        self.name_entry.pack(side='left', padx=(0, 10))
        self.name_entry.bind('<FocusOut>', lambda e: self.update_bank_name())
        self.name_entry.bind('<Return>', lambda e: self.update_bank_name())
        ToolTip(self.name_entry, 'Name this bank (Ctrl+N)')

        ttk.Separator(top, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Label(top, text='Cursor').pack(side='left')
        sp = ttk.Spinbox(top, from_=1, to=MAX_STEPS, textvariable=self.cursor, width=5, command=self.refresh_grid)
        sp.pack(side='left', padx=(4, 14))
        ToolTip(sp, 'Edit cursor position')
        
        ttk.Label(top, text='Len').pack(side='left', padx=(8, 2))
        ls = ttk.Spinbox(top, from_=1, to=MAX_STEPS, textvariable=self.bank_length, width=4)
        ls.pack(side='left')
        ToolTip(ls, 'Bank length')

        b = ttk.Button(top, text='Open', command=self.open_file)
        b.pack(side='left', padx=(10, 0))
        ToolTip(b, 'Open .mbseq')
        b = ttk.Button(top, text='Save', command=self.save_file)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Save current project')
        
        self.play_btn = ttk.Button(top, text='▶ Play', command=self.play_sequence)
        self.play_btn.pack(side='left', padx=(10, 0))
        ToolTip(self.play_btn, 'Play the selected bank (Space)')
        self.stop_btn = ttk.Button(top, text='■ Stop', command=self.stop_sequence, state='disabled')
        self.stop_btn.pack(side='left', padx=3)
        ToolTip(self.stop_btn, 'Stop playback (Esc)')
        
        ttk.Checkbutton(top, text='Loop', variable=self.loop).pack(side='left')
        ttk.Checkbutton(top, text='Metronome', variable=self.metronome).pack(side='left', padx=3)
        
        dt = ttk.Checkbutton(top, text='Dark Mode', variable=self.dark_mode, command=self.toggle_theme)
        dt.pack(side='right', padx=10)
        ToolTip(dt, 'Toggle high-contrast Dark Mode')

        edit = ttk.Frame(self, padding=(8, 0, 8, 6))
        edit.pack(fill='x')
        
        b = ttk.Button(edit, text='Randomize...', command=self.show_randomizer_dialog)
        b.pack(side='left')
        ToolTip(b, 'Generate random sequence within scale (Ctrl+R)')
        b = ttk.Button(edit, text='Arpeggiate...', command=self.show_arpeggiator_dialog)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Arpeggiate selection')
        
        ttk.Separator(edit, orient='vertical').pack(side='left', fill='y', padx=10)
        b = ttk.Button(edit, text='+ Step', command=self.add_step)
        b.pack(side='left')
        ToolTip(b, 'Insert an empty step')
        b = ttk.Button(edit, text='Delete', command=self.delete_step)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Remove step or selection')
        b = ttk.Button(edit, text='Rest', command=self.insert_rest)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Set current step to rest (R)')
        b = ttk.Button(edit, text='Clear', command=self.clear_slot)
        b.pack(side='left', padx=10)
        ToolTip(b, 'Reset bank to rests')
        
        b = ttk.Button(edit, text='Copy', command=self.copy_selection)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Copy selection (Ctrl+C). Shift+C for bank.')
        b = ttk.Button(edit, text='Paste', command=self.paste_selection)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Paste from clipboard (Ctrl+V). Shift+V for bank.')
        
        ttk.Label(edit, text='Transpose').pack(side='left', padx=(14, 3))
        for v in [-12, -1, 1, 12]:
            b = ttk.Button(edit, text=f'{v:+d}', width=4, command=lambda x=v: self.transpose_bank(x))
            b.pack(side='left')
            ToolTip(b, f'Transpose by {v} semitones')

        self.paned = ttk.PanedWindow(self, orient='vertical')
        self.paned.pack(fill='both', expand=True, padx=8, pady=4)

        self.grid_container = ttk.Frame(self.paned, padding=8)
        self.paned.add(self.grid_container, weight=1)
        self.grid_inner = ttk.Frame(self.grid_container)
        self.grid_inner.pack(anchor='nw')
        self.bind('<Configure>', lambda e: self.on_resize(e))

        self.piano_roll_frame = ttk.LabelFrame(self.paned, text='Visual Piano Roll (Ctrl+Scroll = Zoom, Scroll = Pan)', padding=6)
        self.paned.add(self.piano_roll_frame, weight=2)
        self.piano_roll = tk.Canvas(self.piano_roll_frame, bg='#333333', highlightthickness=0)
        self.piano_roll.pack(fill='both', expand=True)
        self.piano_roll.bind('<Button-1>', self._on_piano_roll_click)

        kb_wrap = ttk.Frame(self, padding=8)
        kb_wrap.pack(fill='x')
        self.keyboard = tk.Canvas(kb_wrap, width=1030, height=210, bg='#666666', highlightthickness=0)
        self.keyboard.pack(fill='x', pady=6)

        text_frame = ttk.LabelFrame(self, text='Raw .mbseq text', padding=6)
        text_frame.pack(fill='x', padx=8, pady=4)
        self.raw = tk.Text(text_frame, height=3, font=('Consolas', 10), undo=True)
        self.raw.pack(fill='both', expand=True)
        
        ec = ttk.Frame(self, padding=(8, 0, 8, 6))
        ec.pack(fill='x')
        ttk.Label(ec, text='Oscillator').pack(side='left')
        for s in ['square', 'saw', 'triangle', 'sine']:
            ttk.Radiobutton(ec, text=s.capitalize(), variable=self.wave_shape, value=s).pack(side='left', padx=3)
        ttk.Label(ec, text='Volume').pack(side='left', padx=(14, 3))
        ttk.Scale(ec, from_=0.0, to=0.8, variable=self.volume, length=140).pack(side='left')
        ttk.Label(ec, text='Octave').pack(side='left', padx=(20, 3))
        for v in [-2, -1, 0, 1, 2]:
            ttk.Radiobutton(ec, text=f'{v:+d}', variable=self.octave_shift, value=v, command=self.refresh_keyboard).pack(side='left')
        self.status = ttk.Label(self, padding=(8, 0, 8, 8), text='')
        self.status.pack(fill='x')

    def _build_menu(self) -> None:
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label='Open .mbseq', command=self.open_file)
        self.recent_menu = tk.Menu(fm, tearoff=0)
        fm.add_cascade(label='Open Recent', menu=self.recent_menu)
        self._refresh_recent_menu()
        fm.add_command(label='Save', command=self.save_file)
        fm.add_command(label='Save As...', command=self.save_as)
        fm.add_separator()
        fm.add_command(label='Import MIDI...', command=self.import_midi_file)
        fm.add_separator()
        fm.add_command(label='Export selected MIDI...', command=self.export_midi_file)
        fm.add_command(label='Export all 8 MIDI...', command=self.export_all_midi_files)
        fm.add_command(label='Export song MIDI...', command=self.export_song_midi_file)
        fm.add_command(label='Export bank WAV...', command=self.export_bank_wav)
        fm.add_separator()
        fm.add_command(label='Exit', command=self.on_close)
        m.add_cascade(label='File', menu=fm)
        
        em = tk.Menu(m, tearoff=0)
        em.add_command(label='Undo', accelerator='Ctrl+Z', command=self.undo)
        em.add_command(label='Redo', accelerator='Ctrl+Y', command=self.redo)
        em.add_separator()
        em.add_command(label='Copy Selection', accelerator='Ctrl+C', command=self.copy_selection)
        em.add_command(label='Paste Selection', accelerator='Ctrl+V', command=self.paste_selection)
        em.add_separator()
        em.add_command(label='Copy Whole Bank', accelerator='Ctrl+Shift+C', command=self.copy_bank)
        em.add_command(label='Paste Whole Bank', accelerator='Ctrl+Shift+V', command=self.paste_bank)
        em.add_separator()
        em.add_command(label='Clear Selection', command=self.clear_selection)
        m.add_cascade(label='Edit', menu=em)
        
        vm = tk.Menu(m, tearoff=0)
        vm.add_checkbutton(label='Dark Mode', variable=self.dark_mode, command=self.toggle_theme)
        vm.add_separator()
        vm.add_command(label='Settings...', command=self.show_settings_dialog)
        m.add_cascade(label='View', menu=vm)
        self.config(menu=m)

    def _bind_keys(self) -> None:
        self.bind('<space>', lambda e: self.toggle_play())
        self.bind('r', lambda e: self.insert_rest())
        self.bind('<Insert>', lambda e: self.insert_rest())
        self.bind('<Escape>', lambda e: self.stop_sequence())
        self.bind('<Control-z>', lambda e: self.undo())
        self.bind('<Control-y>', lambda e: self.redo())
        self.bind('<Control-Z>', lambda e: self.redo())
        self.bind('<Control-c>', lambda e: self.copy_selection())
        self.bind('<Control-v>', lambda e: self.paste_selection())
        self.bind('<Control-C>', lambda e: self.copy_bank())
        self.bind('<Control-V>', lambda e: self.paste_bank())
        self.bind('<Control-n>', lambda e: self.focus_bank_name())
        self.bind('<Control-r>', lambda e: self.show_randomizer_dialog())
        self.bind('<Left>', lambda e: self.move_cursor(-1))
        self.bind('<Right>', lambda e: self.move_cursor(1))
        for idx, key in enumerate(PC_KEYS[:25]):
            try:
                self.bind(key, lambda e, i=idx: self.insert_note(self.note_for_index(i)))
            except tk.TclError: pass
        self.piano_roll.bind('<MouseWheel>', self._on_piano_roll_scroll)
        self.piano_roll.bind('<Button-4>', self._on_piano_roll_scroll)
        self.piano_roll.bind('<Button-5>', self._on_piano_roll_scroll)

    def steps(self) -> list[Step]:
        s = int(self.slot.get())
        if s not in self.project.sequences:
            self.project.sequences[s] = [Step() for _ in range(MAX_STEPS)]
        return self.project.sequences[s]

    def focus_bank_name(self) -> None:
        if hasattr(self, 'name_entry'):
            self.name_entry.focus_set()
            self.name_entry.selection_range(0, 'end')

    def update_bank_name(self) -> None:
        self.project.bank_names[int(self.slot.get())] = self.bank_name_var.get()
        self.refresh_status()

    def _at_step_limit(self) -> bool:
        if len(self.steps()) >= MAX_STEPS:
            self.status.config(text=f'Bank full ({MAX_STEPS})')
            return True
        return False

    def toggle_theme(self) -> None:
        style = ttk.Style()
        if self.dark_mode.get():
            self.configure(bg='#2b2b2b')
            style.theme_use('clam')
            for w in ['TFrame', 'TLabel', 'TCheckbutton', 'TRadiobutton', 'TLabelframe', 'TLabelframe.Label']:
                style.configure(w, background='#2b2b2b', foreground='#ffffff')
            style.configure('TButton', background='#404040', foreground='#ffffff')
            self.raw.configure(bg='#1e1e1e', fg='#ffffff', insertbackground='white')
        else:
            self.configure(bg='#f0f0f0')
            style.theme_use('default')
            for w in ['TFrame', 'TLabel', 'TCheckbutton', 'TRadiobutton', 'TLabelframe', 'TLabelframe.Label']:
                style.configure(w, background='#f0f0f0', foreground='#000000')
            style.configure('TButton', background='#e1e1e1', foreground='#000000')
            self.raw.configure(bg='#ffffff', fg='#000000', insertbackground='black')
        self._save_settings()
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_grid()
        self.refresh_keyboard()
        self.refresh_raw()
        self.refresh_status()
        self.refresh_piano_roll()

    def _recent_config_path(self) -> Path: return Path.home() / '.microbrrrute_studio_recent.json'
    def _settings_path(self) -> Path: return Path.home() / '.microbrrrute_studio_settings.json'

    def _load_settings(self) -> None:
        p = self._settings_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                for k, v in data.items():
                    if hasattr(self, k): getattr(self, k).set(v)
                if self.dark_mode.get(): self.toggle_theme()
            except Exception: pass

    def _save_settings(self) -> None:
        try:
            d = {k: getattr(self, k).get() for k in ['volume', 'tempo', 'dark_mode', 'wave_shape', 'step_res', 'attack', 'decay', 'sustain', 'release']}
            self._settings_path().write_text(json.dumps(d), encoding='utf-8')
        except Exception: pass

    def _load_recent(self) -> list[str]:
        p = self._recent_config_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                if isinstance(data, list): return [f for f in data if isinstance(f, str) and Path(f).exists()][:10]
            except Exception: pass
        return []

    def _save_recent(self) -> None:
        try: self._recent_config_path().write_text(json.dumps(self.recent_files), encoding='utf-8')
        except Exception: pass

    def _add_recent(self, path: str | Path) -> None:
        p = str(Path(path).absolute())
        if p in self.recent_files: self.recent_files.remove(p)
        self.recent_files.insert(0, p); self.recent_files = self.recent_files[:10]
        self._save_recent(); self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, 'recent_menu'): return
        self.recent_menu.delete(0, 'end')
        if not self.recent_files:
            self.recent_menu.add_command(label='(No recent files)', state='disabled')
        else:
            for p in self.recent_files:
                self.recent_menu.add_command(label=p, command=lambda x=p: self.open_recent(x))

    def open_recent(self, path: str) -> None:
        if not Path(path).exists():
            messagebox.showerror('Error', 'File not found')
            self.recent_files.remove(path)
            self._save_recent()
            self._refresh_recent_menu()
            return
        self._do_open(path)

    def refresh_status(self) -> None:
        p = str(self.file_path) if self.file_path else 'unsaved'
        cur = self.cursor.get()+1
        flag = ' *' if self.dirty else ''
        steps = self.steps()
        out = any(s.note is not None and (s.note < MIN_PLAYABLE or s.note > MAX_PLAYABLE) for s in steps)
        range_warn = ' | ⚠️ Out of range!' if out else ''
        name = self.project.bank_names.get(int(self.slot.get()), f'Bank {self.slot.get()}')
        self.status.config(text=f'{p}{flag} | {name} | Steps {len(steps)} | Cursor {cur} | {range_warn}')

    def show_settings_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title('App Settings')
        win.geometry('400x450')
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        f = ttk.Frame(win, padding=20)
        f.pack(fill='both', expand=True)
        ttk.Checkbutton(f, text='Dark Mode', variable=self.dark_mode, command=self.toggle_theme).pack(anchor='w', pady=5)
        ttk.Label(f, text='Volume').pack(anchor='w')
        ttk.Scale(f, from_=0.0, to=0.8, variable=self.volume, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(f, text='Tempo (BPM)').pack(anchor='w')
        ttk.Spinbox(f, from_=30, to=300, textvariable=self.tempo).pack(anchor='w', pady=5)
        
        env = ttk.LabelFrame(f, text='ADSR Envelope', padding=10)
        env.pack(fill='x', pady=10)
        for p in [('Attack', self.attack, 0, 0.5), ('Decay', self.decay, 0, 1.0), ('Sustain', self.sustain, 0, 1.0), ('Release', self.release, 0, 1.0)]:
            ttk.Label(env, text=p[0]).pack(anchor='w')
            ttk.Scale(env, from_=p[2], to=p[3], variable=p[1], orient='horizontal').pack(fill='x')
        ttk.Button(f, text='Close', command=win.destroy).pack(side='bottom', pady=10)

    def show_randomizer_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title('Randomizer')
        win.geometry('350x300')
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        f = ttk.Frame(win, padding=20)
        f.pack(fill='both', expand=True)
        root_var = tk.StringVar(value='C')
        scale_var = tk.StringVar(value='Minor Pentatonic')
        oct_var = tk.IntVar(value=2)
        fill_var = tk.IntVar(value=75)
        ttk.Label(f, text='Root').grid(row=0, column=0, sticky='w')
        ttk.Combobox(f, textvariable=root_var, values=NOTE_NAMES, state='readonly').grid(row=0, column=1, pady=5)
        ttk.Label(f, text='Scale').grid(row=1, column=0, sticky='w')
        ttk.Combobox(f, textvariable=scale_var, values=list(SCALES.keys()), state='readonly').grid(row=1, column=1, pady=5)
        ttk.Label(f, text='Octaves').grid(row=2, column=0, sticky='w')
        ttk.Spinbox(f, from_=1, to=4, textvariable=oct_var).grid(row=2, column=1, pady=5)
        ttk.Label(f, text='Fill %').grid(row=3, column=0, sticky='w')
        ttk.Spinbox(f, from_=10, to=100, textvariable=fill_var).grid(row=3, column=1, pady=5)
        def do_rand():
            rm = NOTE_NAMES.index(root_var.get()) + 36
            ivs = SCALES[scale_var.get()]
            pool = [rm + o*12 + i for o in range(oct_var.get()) for i in ivs]
            self.push_undo()
            steps = self.steps()
            for i in range(len(steps)):
                if random.randint(1, 100) <= fill_var.get():
                    steps[i] = Step(note=random.choice(pool), accent=(random.random() < 0.2), slide=(random.random() < 0.1))
                else: steps[i] = Step(note=None)
            self.mark_dirty(); self.refresh_all(); win.destroy()
        ttk.Button(f, text='Generate', command=do_rand).grid(row=4, column=0, columnspan=2, pady=20)

    def show_arpeggiator_dialog(self) -> None:
        if not self._selection: return messagebox.showinfo('Arpeggiator', 'Please select steps to arpeggiate first.')
        win = tk.Toplevel(self); win.title('Arpeggiator'); win.geometry('300x200'); win.transient(self); win.grab_set()
        f = ttk.Frame(win, padding=20); f.pack(fill='both', expand=True)
        mode = tk.StringVar(value='Up')
        ttk.Label(f, text='Arp Mode').pack(anchor='w')
        ttk.Combobox(f, textvariable=mode, values=['Up', 'Down', 'Up-Down', 'Random'], state='readonly').pack(fill='x', pady=10)
        def do_arp():
            indices = sorted(list(self._selection)); steps = self.steps()
            notes = [steps[i].note for i in indices if steps[i].note is not None]
            if not notes: return win.destroy()
            if mode.get() == 'Up': arp_notes = sorted(notes)
            elif mode.get() == 'Down': arp_notes = sorted(notes, reverse=True)
            elif mode.get() == 'Up-Down': arp_notes = sorted(notes) + sorted(notes, reverse=True)[1:-1]
            else:
                arp_notes = list(notes)
                random.shuffle(arp_notes)
            self.push_undo()
            for i, idx in enumerate(indices): steps[idx].note = arp_notes[i % len(arp_notes)]
            self.mark_dirty(); self.refresh_all(); win.destroy()
        ttk.Button(f, text='Apply Arp', command=do_arp).pack(side='bottom', pady=10)

    def mark_dirty(self) -> None: self.dirty = True
    def _snapshot(self) -> dict[int, list[Step]]: return {k: [Step(s.note, s.gate, s.accent, s.slide) for s in v] for k, v in self.project.sequences.items()}
    def push_undo(self) -> None:
        self._undo.append(self._snapshot())
        if len(self._undo) > 100: self._undo.pop(0)
        self._redo.clear()
    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._snapshot())
            self.project.sequences = self._undo.pop()
            self.mark_dirty(); self.refresh_all()
    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._snapshot())
            self.project.sequences = self._redo.pop()
            self.mark_dirty(); self.refresh_all()

    def copy_selection(self) -> None:
        if not self._selection: return
        steps = self.steps()
        tokens = [('x' if steps[idx].note is None else str(steps[idx].note)) for idx in sorted(list(self._selection)) if idx < len(steps)]
        self.clipboard_clear(); self.clipboard_append(' '.join(tokens))
    def paste_selection(self) -> None:
        try: text = self.clipboard_get().strip()
        except tk.TclError: return
        tokens = text.split()
        if not tokens: return
        self.push_undo(); steps = self.steps(); start = self.cursor.get()
        for i, t in enumerate(tokens):
            idx = start + i
            if idx >= MAX_STEPS: break
            v = None if t.lower() == 'x' else int(t)
            if idx >= len(steps): steps.append(Step(note=v))
            else: steps[idx].note = v
        self.mark_dirty(); self.refresh_all()

    def copy_bank(self) -> None:
        steps = self.steps()
        tokens = ['x' if s.note is None else str(s.note) for s in steps]
        self.clipboard_clear(); self.clipboard_append(' '.join(tokens))
    def paste_bank(self) -> None:
        try: text = self.clipboard_get()
        except tk.TclError: return messagebox.showinfo('Paste Bank', 'Clipboard is empty.')
        tokens = text.split()
        if not tokens: return
        new = [Step(note=(None if t.lower() == 'x' else int(t))) for t in tokens][:MAX_STEPS]
        self.push_undo(); self.project.sequences[int(self.slot.get())] = new; self.mark_dirty(); self.refresh_all()

    def transpose_bank(self, semitones: int) -> None:
        self.push_undo(); steps = self.steps()
        if self._selection:
            for idx in self._selection:
                if 0 <= idx < len(steps) and steps[idx].note is not None:
                    steps[idx].note = max(0, min(127, steps[idx].note + semitones))
        else:
            self.project.sequences[int(self.slot.get())] = transpose_steps(steps, semitones)
        self.mark_dirty(); self.refresh_all()

    def import_midi_file(self) -> None:
        p = filedialog.askopenfilename(filetypes=[('MIDI file','*.mid'),('All files','*.*')])
        if not p: return
        try:
            raw = import_midi(p)
            steps = [Step(note=n) for n in raw][:MAX_STEPS]
            self.push_undo(); self.project.sequences[int(self.slot.get())] = steps
            self.mark_dirty(); self.cursor.set(0); self.refresh_all()
        except Exception as e: messagebox.showerror('Error', str(e))

    def export_song_midi_file(self) -> None:
        banks = {b: [s.note for s in self.project.sequences[b]] for b in range(1, 9) if b in self.project.sequences and any(s.note is not None for s in self.project.sequences[b])}
        if not banks: return
        p = filedialog.asksaveasfilename(defaultextension='.mid', filetypes=[('MIDI file','*.mid')])
        if p:
            try: export_song_midi(p, banks, bpm=self.tempo.get())
            except Exception as e: messagebox.showerror('Error', str(e))

    def export_bank_wav(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension='.wav', filetypes=[('WAV audio','*.wav')])
        if p:
            try: render_steps_wav(p, self.steps(), bpm=self.tempo.get(), wave_shape=self.wave_shape.get(), volume=self.volume.get())
            except Exception as e: messagebox.showerror('Error', str(e))

    def on_close(self) -> None:
        self.stop_sequence(); self._save_settings()
        if self.dirty and not messagebox.askokcancel('Unsaved changes', 'Quit?'): return
        self.destroy()

    def refresh_raw(self) -> None: self.raw.delete('1.0','end'); self.raw.insert('1.0', self.project.serialize())
    def on_resize(self, event: tk.Event) -> None:
        if event.widget == self: self.refresh_grid(); self.refresh_piano_roll()

    def refresh_grid(self) -> None:
        steps = self.steps()
        win_width = self.winfo_width()
        btn_width = 65
        cols = max(1, (win_width - 40) // btn_width)
        children = self.grid_inner.winfo_children()
        if not hasattr(self, '_last_cols') or self._last_cols != cols or len(children) != len(steps) * 2:
            for w in children: w.destroy()
            self.step_buttons.clear(); self._last_cols = cols
            for i in range(len(steps)):
                row, col = (i // cols) * 2, i % cols
                ttk.Label(self.grid_inner, text=str(i+1), anchor='center').grid(row=row, column=col, padx=1)
                b = tk.Button(self.grid_inner, width=7, height=2, highlightthickness=0); b.grid(row=row+1, column=col, padx=1, pady=(0,4))
                b.bind('<Button-3>', lambda e, x=i: self._show_step_context_menu(e, x))
                b.bind('<ButtonPress-1>', lambda e, x=i: self._on_step_click(e, x))
                b.bind('<B1-Motion>', self._on_drag_motion)
                b.bind('<ButtonRelease-1>', lambda e, x=i: self._on_drag_stop(e, x)); self.step_buttons.append(b)
        for i, s in enumerate(steps):
            txt = f'{"x" if s.note is None else midi_to_name(s.note)}{("•" if s.accent else "") + ("→" if s.slide else "")}\n{s.note if s.note is not None else "x"}'
            if i == self._playhead: bg, fg = '#7CFC8A', '#000000'
            elif i in self._selection: bg, fg = ('#ffa500' if self.dark_mode.get() else '#ffcc00'), '#000000'
            elif i == self.cursor.get(): bg, fg = ('#0078d7' if self.dark_mode.get() else '#d7f0ff'), ('#ffffff' if self.dark_mode.get() else '#000000')
            else: bg, fg = ('#404040' if self.dark_mode.get() else '#ffffff'), ('#ffffff' if self.dark_mode.get() else '#000000')
            self.step_buttons[i].config(text=txt, bg=bg, fg=fg, highlightthickness=2 if i in self._selection else 0, command=lambda x=i: self.select_step(x))
        self.refresh_status()

    def _on_piano_roll_scroll(self, event: tk.Event) -> None:
        if event.state & 0x0004:
            if event.num == 4 or event.delta > 0: self._piano_roll_zoom *= 1.1
            else: self._piano_roll_zoom /= 1.1
            self._piano_roll_zoom = max(0.5, min(5.0, self._piano_roll_zoom))
            self.refresh_piano_roll()
        else:
            if event.num == 4 or event.delta > 0: self._piano_roll_off_y += 30
            else: self._piano_roll_off_y -= 30
            self.refresh_piano_roll()

    def refresh_piano_roll(self) -> None:
        self.piano_roll.delete('all')
        w, h = self.piano_roll.winfo_width(), self.piano_roll.winfo_height()
        if w < 10: return
        steps = self.steps(); zoom = self._piano_roll_zoom; cell_w = (w / len(steps)) * zoom; cell_h = (h / 24) * zoom; off_y = self._piano_roll_off_y
        for n in range(MIN_PLAYABLE, MAX_PLAYABLE + 1):
            y = h - (n - MIN_PLAYABLE + 1) * cell_h + off_y
            if -cell_h < y < h + cell_h:
                self.piano_roll.create_rectangle(0, y, w, y + cell_h, fill=('#2a2a2a' if (n % 12) in [1, 3, 6, 8, 10] else '#333333'), outline='#222222')
                if n % 12 == 0: self.piano_roll.create_text(25, y + cell_h/2, text=f'C{n//12 - 1}', fill='#888888', font=('Consolas', int(8*zoom)))
        for i, s in enumerate(steps):
            x = i * cell_w
            if -cell_w < x < w:
                if i == self._playhead: self.piano_roll.create_rectangle(x, 0, x + cell_w, h, fill='#7CFC8A', stipple='gray25', outline='')
                if s.note is not None:
                    y = h - (s.note - MIN_PLAYABLE + 1) * cell_h + off_y
                    if -cell_h < y < h:
                        col = '#0078d7' if i == self.cursor.get() else ('#ffffff' if s.accent else '#ffcc00')
                        self.piano_roll.create_rectangle(x+1, y+1, x+cell_w-1, y+cell_h-1, fill=col, outline='white' if s.slide else '')

    def _on_piano_roll_click(self, event: tk.Event) -> None:
        w, h = self.piano_roll.winfo_width(), self.piano_roll.winfo_height(); steps = self.steps()
        zoom = self._piano_roll_zoom; cell_w = (w / len(steps)) * zoom; cell_h = (h / 24) * zoom; off_y = self._piano_roll_off_y
        step_idx = int(event.x / cell_w)
        note_val = int((h + off_y - event.y) / cell_h + MIN_PLAYABLE - 1)
        if 0 <= step_idx < len(steps) and MIN_PLAYABLE <= note_val <= MAX_PLAYABLE:
            self.select_step(step_idx)
            self.push_undo(); steps[step_idx].note = note_val; self.mark_dirty(); self.refresh_all()

    def _show_step_context_menu(self, event: tk.Event, idx: int):
        self.select_step(idx); m = tk.Menu(self, tearoff=0); s = self.steps()[idx]
        m.add_command(label='Set Rest', command=lambda: self.set_step_rest(idx))
        m.add_separator()
        m.add_command(label="Unset Accent" if s.accent else "Set Accent", command=lambda: self.toggle_step_accent(idx))
        m.add_command(label="Unset Slide" if s.slide else "Set Slide", command=lambda: self.toggle_step_slide(idx))
        gm = tk.Menu(m, tearoff=0)
        for g in [0.25, 0.5, 0.82, 1.0]:
            gm.add_radiobutton(label=f'{int(g*100)}%', command=lambda v=g: self.set_step_gate(idx, v))
        m.add_cascade(label='Gate Length', menu=gm)
        m.post(event.x_root, event.y_root)

    def toggle_step_accent(self, idx: int): self.push_undo(); self.steps()[idx].accent = not self.steps()[idx].accent; self.mark_dirty(); self.refresh_all()
    def toggle_step_slide(self, idx: int): self.push_undo(); self.steps()[idx].slide = not self.steps()[idx].slide; self.mark_dirty(); self.refresh_all()
    def set_step_gate(self, idx: int, val: float): self.push_undo(); self.steps()[idx].gate = val; self.mark_dirty(); self.refresh_grid()
    def set_step_rest(self, idx: int): self.push_undo(); self.steps()[idx].note = None; self.mark_dirty(); self.cursor.set(idx); self.refresh_all()
    def preview_note(self, note: int, duration: float = 0.18) -> None: play_note(note, duration=duration, wave_shape=self.wave_shape.get(), volume=self.volume.get()); self.highlight_note(note)
    def highlight_note(self, note: int) -> None:
        if note not in self.key_rects: return
        rect = self.key_rects[note]; rel = note - (self.root_note + self.octave_shift.get()*12)
        self.keyboard.itemconfig(rect, fill='#7CFC8A')
        self.after(200, lambda: self.keyboard.itemconfig(rect, fill=('black' if rel in BLACK_OFFSETS else 'white')))
    def insert_note(self, note: int) -> None:
        self.preview_note(note); steps = self.steps(); idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit(): return
        self.push_undo()
        if idx >= len(steps): steps.append(Step(note=note))
        else: steps[idx].note = note
        self.mark_dirty(); self.move_cursor(1, refresh=False); self.refresh_all()
    def insert_rest(self) -> None:
        steps = self.steps(); idx = self.cursor.get(); if idx >= len(steps) and self._at_step_limit(): return
        self.push_undo()
        if idx >= len(steps): steps.append(Step(note=None))
        else: steps[idx].note = None
        self.mark_dirty(); self.move_cursor(1, refresh=False); self.refresh_all()
    def move_cursor(self, delta: int, refresh=True) -> None: self.cursor.set(max(0, min(len(self.steps())-1, self.cursor.get()+delta))); if refresh: self.refresh_grid(); self.refresh_piano_roll()
    def change_slot(self) -> None:
        self.cursor.set(0); self.bank_name_var.set(self.project.bank_names.get(int(self.slot.get()), f'Bank {self.slot.get()}'))
        self.clear_selection(); self.refresh_all()
    def clear_selection(self) -> None: self._selection.clear(); self.refresh_grid(); self.refresh_piano_roll()
    def add_step(self) -> None:
        if not self._at_step_limit(): self.push_undo(); self.steps().insert(self.cursor.get()+1, Step()); self.mark_dirty(); self.move_cursor(1); self.refresh_raw()
    def delete_step(self) -> None:
        steps = self.steps()
        if not steps: return
        self.push_undo()
        if self._selection:
            for idx in sorted(list(self._selection), reverse=True):
                if idx < len(steps): steps.pop(idx)
            self.clear_selection()
        else: steps.pop(self.cursor.get())
        if not steps: steps.append(Step())
        self.mark_dirty(); self.cursor.set(min(self.cursor.get(), len(steps)-1)); self.refresh_all()
    def clear_slot(self) -> None:
        if messagebox.askyesno('Clear', 'Clear bank?'): self.push_undo(); self.project.sequences[int(self.slot.get())] = [Step() for _ in range(MAX_STEPS)]; self.mark_dirty(); self.cursor.set(0); self.refresh_all()
    def _do_open(self, p: str | Path) -> None:
        try:
            self.project = MbseqProject.load(p); self.file_path = Path(p); self.dirty = False; self._undo.clear(); self._redo.clear(); self.slot.set(1); self.bank_name_var.set(self.project.bank_names.get(1, 'Bank 1'))
            self.cursor.set(0); self.refresh_all(); self._add_recent(p)
        except Exception as e: messagebox.showerror('Error', str(e))
    def open_file(self) -> None:
        p = filedialog.askopenfilename(filetypes=[('MBSEQ','*.mbseq'),('All','*.*')])
        if p: self._do_open(p)
    def _do_save(self, p: str | Path) -> None:
        try: self.project.save(p); self.file_path = Path(p); self.dirty = False; self.refresh_status(); self._add_recent(p)
        except Exception as e: messagebox.showerror('Error', str(e))
    def save_file(self) -> None: self.save_as() if not self.file_path else self._do_save(self.file_path)
    def save_as(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension='.mbseq', filetypes=[('MBSEQ','*.mbseq')])
        if p: self._do_save(p)
    def apply_raw(self) -> None:
        try:
            self.push_undo(); self.project = MbseqProject.parse(self.raw.get('1.0','end')); self.slot.set(1); self.bank_name_var.set(self.project.bank_names.get(1, 'Bank 1')); self.mark_dirty(); self.cursor.set(0); self.refresh_all()
        except Exception as e: messagebox.showerror('Error', str(e))
    def toggle_play(self) -> None: self.stop_sequence() if self.playing else self.play_sequence()
    def play_sequence(self) -> None: self.stop_sequence(); self._play_banks = [int(self.slot.get())]; self._start_playback()
    def _start_playback(self) -> None:
        bank = self._play_banks[0]
        steps = self.project.sequences.get(bank, [Step() for _ in range(MAX_STEPS)])
        if not any(s.note is not None for s in steps): messagebox.showinfo('Info', 'Bank empty'); return
        self.playing = True; self._play_idx = 0
        if self.play_btn: self.play_btn.config(state='disabled')
        if self.stop_btn: self.stop_btn.config(state='normal')
        self.refresh_all()
        data = render_steps_to_data(steps, bpm=self.tempo.get(), wave_shape=self.wave_shape.get(), volume=self.volume.get(), 
                                   attack=self.attack.get(), decay=self.decay.get(), sustain=self.sustain.get(), release=self.release.get(),
                                   metronome=self.metronome.get())
        self._pre_render_file = Path(tempfile.gettempdir()) / f'mbseq_{uuid.uuid4().hex}.wav'
        render_pre_rendered_wav(self._pre_render_file, data)
        if self.count_in.get(): self._play_count_in(8)
        else: self._start_audio_and_tick()
    def _start_audio_and_tick(self) -> None:
        if self.playing and self._pre_render_file: play_pre_rendered_wav(self._pre_render_file); self._play_tick()
    def _play_count_in(self, s: int) -> None:
        if not self.playing: return
        if s <= 0: return self._start_audio_and_tick()
        ms = int(30000 / max(1, self.tempo.get()))
        self.preview_note(84 if s % 2 == 0 else 72, 0.03)
        self._after_id = self.after(ms, lambda: self._play_count_in(s - 1))
    def _play_tick(self) -> None:
        if not self.playing: return
        steps = self.steps(); div = 4 if self.step_res.get() == '1/16' else 2; ms = int(60000 / max(1, self.tempo.get()) / div)
        if not steps or self._play_idx >= len(steps): self._advance_bank(); return
        self._playhead = self._play_idx; self.refresh_grid(); self.refresh_piano_roll()
        n = steps[self._playhead].note
        if n is not None: self.highlight_note(n)
        self._play_idx += 1; self._after_id = self.after(ms, self._play_tick)
    def _advance_bank(self) -> None:
        if self.loop.get():
            self._play_idx = 0; self._playhead = -1; self.refresh_all()
            if self._pre_render_file: play_pre_rendered_wav(self._pre_render_file)
            self._after_id = self.after(1, self._play_tick)
        else: self.stop_sequence()
    def stop_sequence(self) -> None:
        self.playing = False
        if self._after_id: self.after_cancel(self._after_id); self._after_id = None
        stop_all()
        if self._pre_render_file:
            try: self._pre_render_file.unlink()
            except Exception: pass
            self._pre_render_file = None
        self._playhead = -1
        if self.play_btn: self.play_btn.config(state='normal')
        if self.stop_btn: self.stop_btn.config(state='disabled')
        self.refresh_grid(); self.refresh_piano_roll()
    def _on_drag_start(self, idx: int) -> None: self._drag_idx = idx
    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag_idx is None: return
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        for i, btn in enumerate(self.step_buttons):
            if btn == target: btn.config(highlightthickness=3, highlightbackground='#7CFC8A', bg='#e8ffea' if not self.dark_mode.get() else '#1a331c')
            else:
                is_sel = (i in self._selection); is_cur = (i == self.cursor.get())
                bg = ('#ffa500' if self.dark_mode.get() else '#ffcc00') if is_sel else (('#0078d7' if self.dark_mode.get() else '#d7f0ff') if is_cur else ('#404040' if self.dark_mode.get() else '#ffffff'))
                btn.config(highlightthickness=2 if is_sel else 0, highlightbackground='#ffffff', bg=bg)
    def _on_drag_stop(self, event: tk.Event, src_idx: int) -> None:
        if self._drag_idx is None: return
        for btn in self.step_buttons: btn.config(highlightthickness=0)
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        dst_idx = next((i for i, b in enumerate(self.step_buttons) if b == target), None)
        if dst_idx is not None and dst_idx != src_idx:
            self.push_undo(); steps = self.steps()
            steps.insert(dst_idx, steps.pop(src_idx))
            self.mark_dirty(); self.refresh_all()
        self._drag_idx = None
    def _on_step_click(self, event: tk.Event, idx: int) -> None: self._on_drag_start(idx); self.select_step(idx, event)

    def duplicate_bank_dialog(self) -> None:
        win = tk.Toplevel(self); win.title('Duplicate'); win.geometry('300x150'); win.transient(self); win.grab_set()
        f = ttk.Frame(win, padding=20); f.pack(fill='both', expand=True); target = tk.IntVar(value=1)
        ttk.Label(f, text=f'Duplicate bank {self.slot.get()} to:').grid(row=0, column=0); ttk.Combobox(f, textvariable=target, values=list(range(1, 9)), state='readonly').grid(row=0, column=1)
        def do():
            if target.get() == int(self.slot.get()): return
            self.push_undo()
            self.project.sequences[target.get()] = [Step(s.note, s.gate, s.accent, s.slide) for s in self.steps()]
            self.mark_dirty(); self.refresh_status(); win.destroy()
        ttk.Button(f, text='Copy', command=do).grid(row=1, column=0, pady=10); ttk.Button(f, text='Cancel', command=win.destroy).grid(row=1, column=1, pady=10)

def main(): MbseqStudio().mainloop()
if __name__ == '__main__': main()
