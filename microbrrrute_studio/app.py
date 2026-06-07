from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
import uuid
import tempfile
import sys
if sys.platform == 'win32':
    import ctypes

from .mbseq import (
    MbseqProject, midi_to_name, transpose_steps,
    MIN_PLAYABLE, MAX_PLAYABLE
)
from .synth import (
    play_note, get_last_audio_error, stop_all, render_steps_wav,
    render_steps_to_data, render_pre_rendered_wav, play_pre_rendered_wav
)
from .midi_export import export_midi, export_song_midi, import_midi

MAX_STEPS = 64  # MicroBrute SE hardware limit: 64 steps per pattern bank
WHITE_OFFSETS = [0,2,4,5,7,9,11,12,14,16,17,19,21,23,24]
BLACK_OFFSETS = [1,3,6,8,10,13,15,18,20,22]
BLACK_POS = {1:0.65, 3:1.65, 6:3.65, 8:4.65, 10:5.65, 13:7.65, 15:8.65, 18:10.65, 20:11.65, 22:12.65}
PC_KEYS = list('awsedftgyhujkolpö')

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
        label = tk.Label(tw, text=self.text, justify='left',
                         background='#ffffe0', relief='solid', borderwidth=1,
                         font=('tahoma', '9', 'normal'))
        label.pack(ipadx=1)

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class MbseqStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('microBRRRute Studio - MicroBrute SE Composer')
        self.geometry('1380x850')
        self.minsize(1050, 700)
        self._set_icon()

        self.project = MbseqProject.empty()
        self.file_path: Path | None = None
        self.slot = tk.IntVar(value=1)
        self.cursor = tk.IntVar(value=0)
        self.octave_shift = tk.IntVar(value=0)
        self.root_note = 48  # C3 at octave 0, gives 25 keys C3..C5
        self.tempo = tk.IntVar(value=120)
        self.wave_shape = tk.StringVar(value='square')
        self.volume = tk.DoubleVar(value=0.28)
        self.loop = tk.BooleanVar(value=True)
        self.metronome = tk.BooleanVar(value=False)
        self.count_in = tk.BooleanVar(value=False)
        self.dark_mode = tk.BooleanVar(value=False)
        self.step_res = tk.StringVar(value='1/8')
        self.bank_length = tk.IntVar(value=MAX_STEPS)
        self.playing = False
        
        self._load_settings()
        self.dirty = False
        self._undo: list[dict[int, list[int | None]]] = []
        self._redo: list[dict[int, list[int | None]]] = []
        self._after_id: str | None = None
        self._pre_render_file: Path | None = None
        self._play_idx = 0
        self._playhead = -1            # step currently sounding (-1 = none)
        self._play_banks: list[int] = []  # bank queue when playing all banks
        self._drag_idx: int | None = None
        self._selection: set[int] = set()
        self.step_buttons: list[tk.Button] = []
        self.key_rects: dict[int, int] = {}
        self.recent_files: list[str] = self._load_recent()
        self.play_btn: ttk.Button | None = None
        self.stop_btn: ttk.Button | None = None

        self._setup_dnd()
        self._build()
        self._bind_keys()
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.refresh_all()

    def _set_icon(self) -> None:
        # Find icon file (handles running from source or frozen EXE)
        icon_dir = Path(__file__).parent.parent
        icon_png = icon_dir / 'icon.png'
        icon_ico = icon_dir / 'icon.ico'
        
        try:
            if icon_png.exists():
                self._icon_img = tk.PhotoImage(file=str(icon_png))
                self.iconphoto(True, self._icon_img)
            elif icon_ico.exists() and sys.platform == 'win32':
                self.iconbitmap(str(icon_ico))
        except Exception:
            pass

    def _setup_dnd(self) -> None:
        if sys.platform != 'win32':
            return
        
        # Simple Windows-only drop handler using ctypes
        try:
            self.update_idletasks() # Ensure winfo_id is valid
            hwnd = self.winfo_id()
            # type ignore because we can't reliably type ctypes.windll at runtime
            ctypes.windll.shell32.DragAcceptFiles(hwnd, True) # type: ignore
        except Exception:
            pass

    def _build(self) -> None:
        self._build_menu()
        top = ttk.Frame(self, padding=8)
        top.pack(fill='x')
        ttk.Label(top, text='Pattern bank').pack(side='left')
        slot_box = ttk.Combobox(top, textvariable=self.slot, values=list(range(1,9)), width=4, state='readonly')
        slot_box.pack(side='left', padx=(4,14))
        slot_box.bind('<<ComboboxSelected>>', lambda e: self.change_slot())
        ttk.Separator(top, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Label(top, text='Cursor').pack(side='left')
        spin = ttk.Spinbox(top, from_=1, to=MAX_STEPS, textvariable=self.cursor, width=5, command=self.refresh_grid)
        spin.pack(side='left', padx=(4,14))
        ToolTip(spin, 'Selected step for editing')
        ttk.Label(top, text='Len').pack(side='left', padx=(8,2))
        len_spin = ttk.Spinbox(top, from_=1, to=MAX_STEPS, textvariable=self.bank_length, width=4)
        len_spin.pack(side='left')
        ToolTip(len_spin, 'Active length of current bank (1-64 steps)')
        b = ttk.Button(top, text='Open', command=self.open_file)
        b.pack(side='left', padx=(10,0))
        ToolTip(b, 'Open a .mbseq file')
        b = ttk.Button(top, text='Save', command=self.save_file)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Save the current project')
        b = ttk.Button(top, text='Save As', command=self.save_as)
        b.pack(side='left')
        ToolTip(b, 'Save project to a new file')
        ttk.Separator(top, orient='vertical').pack(side='left', fill='y', padx=10)
        self.play_btn = ttk.Button(top, text='▶ Play Bank', command=self.play_sequence)
        self.play_btn.pack(side='left')
        ToolTip(self.play_btn, 'Play the currently selected bank (Space)')
        self.stop_btn = ttk.Button(top, text='■ Stop', command=self.stop_sequence, state='disabled')
        self.stop_btn.pack(side='left', padx=3)
        ToolTip(self.stop_btn, 'Stop playback immediately (Esc)')
        ttk.Checkbutton(top, text='Loop', variable=self.loop).pack(side='left')
        ttk.Checkbutton(top, text='Metronome', variable=self.metronome).pack(side='left', padx=3)
        ttk.Checkbutton(top, text='Count-in', variable=self.count_in).pack(side='left', padx=3)
        b = ttk.Button(top, text='Test Sound', command=lambda: self.preview_note(60))
        b.pack(side='left', padx=3)
        ToolTip(b, 'Play a middle C to check audio output')
        ttk.Label(top, text='BPM').pack(side='left', padx=(10,2))
        bpm_spin = ttk.Spinbox(top, from_=30, to=300, textvariable=self.tempo, width=5)
        bpm_spin.pack(side='left')
        ToolTip(bpm_spin, 'Playback speed in Beats Per Minute')
        ttk.Label(top, text='Res').pack(side='left', padx=(8,2))
        res_box = ttk.Combobox(top, textvariable=self.step_res, values=['1/8','1/16'], width=5, state='readonly')
        res_box.pack(side='left')
        ToolTip(res_box, 'Step resolution: 1/8 note (default) or 1/16 note')
        b = ttk.Button(top, text='Export Bank MIDI', command=self.export_midi_file)
        b.pack(side='left', padx=4)
        ToolTip(b, 'Export current bank as a MIDI file')
        b = ttk.Button(top, text='Export Song MIDI', command=self.export_song_midi_file)
        b.pack(side='left', padx=2)
        ToolTip(b, 'Export all banks as a single MIDI file')
        b = ttk.Button(top, text='Export Bank WAV', command=self.export_bank_wav)
        b.pack(side='left', padx=2)
        ToolTip(b, 'Render current bank to a WAV audio file')
        b = ttk.Button(top, text='Show Audio Error', command=self.show_audio_error)
        b.pack(side='left', padx=(6,0))
        ToolTip(b, 'Display the last reported audio backend error')

        edit = ttk.Frame(self, padding=(8,0,8,6))
        edit.pack(fill='x')
        b = ttk.Button(edit, text='+ Step', command=self.add_step)
        b.pack(side='left')
        ToolTip(b, 'Insert an empty step at the cursor')
        b = ttk.Button(edit, text='Delete Step', command=self.delete_step)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Remove the step at the cursor')
        b = ttk.Button(edit, text='Rest at Cursor', command=self.insert_rest)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Set the current step to a rest (R)')
        b = ttk.Button(edit, text='Clear Bank', command=self.clear_slot)
        b.pack(side='left', padx=10)
        ToolTip(b, 'Reset all 64 steps in this bank to rests')
        b = ttk.Button(edit, text='Duplicate Bank To...', command=self.duplicate_bank_dialog)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Copy this bank to another slot')
        b = ttk.Button(edit, text='Copy Bank', command=self.copy_bank)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Copy whole bank text to clipboard (Ctrl+Shift+C)')
        b = ttk.Button(edit, text='Paste Bank', command=self.paste_bank)
        b.pack(side='left', padx=3)
        ToolTip(b, 'Paste whole bank text from clipboard (Ctrl+Shift+V)')
        ttk.Label(edit, text='Transpose').pack(side='left', padx=(14,3))
        b1 = ttk.Button(edit, text='-12', width=4, command=lambda: self.transpose_bank(-12))
        b1.pack(side='left')
        ToolTip(b1, 'Transpose bank down one octave')
        b2 = ttk.Button(edit, text='-1', width=4, command=lambda: self.transpose_bank(-1))
        b2.pack(side='left')
        ToolTip(b2, 'Transpose bank down one semitone')
        b3 = ttk.Button(edit, text='+1', width=4, command=lambda: self.transpose_bank(1))
        b3.pack(side='left')
        ToolTip(b3, 'Transpose bank up one semitone')
        b4 = ttk.Button(edit, text='+12', width=4, command=lambda: self.transpose_bank(12))
        b4.pack(side='left')
        ToolTip(b4, 'Transpose bank up one octave')

        self.grid_container = ttk.Frame(self, padding=8)
        self.grid_container.pack(fill='both', expand=True)
        self.grid_inner = ttk.Frame(self.grid_container)
        self.grid_inner.pack(anchor='nw')
        self.bind('<Configure>', lambda e: self.on_resize(e))

        kb_wrap = ttk.Frame(self, padding=8)
        kb_wrap.pack(fill='x')
        ttk.Label(kb_wrap, text='MicroBrute 25-key composer: click key = insert/play, right-click = preview. PC keys A W S E D F T G Y H U J K ... | Space = Play/Stop, R = rest, Esc = stop, Ctrl+Z/Y = undo/redo, Ctrl+C/V = copy/paste step, Ctrl+Shift+C/V = bank').pack(anchor='w')
        self.keyboard = tk.Canvas(kb_wrap, width=1030, height=210, bg='#666666', highlightthickness=0)
        self.keyboard.pack(fill='x', pady=6)

        text_frame = ttk.LabelFrame(self, text='Raw .mbseq text', padding=6)
        text_frame.pack(fill='both', expand=True, padx=8, pady=8)
        self.raw = tk.Text(text_frame, height=5, font=('Consolas', 10), undo=True)
        self.raw.pack(fill='both', expand=True)
        raw_btns = ttk.Frame(text_frame, padding=(0,6,0,0))
        raw_btns.pack(fill='x')
        ttk.Button(raw_btns, text='Apply Raw Text', command=self.apply_raw).pack(side='left')
        ttk.Button(raw_btns, text='Refresh Raw Text', command=self.refresh_raw).pack(side='left', padx=4)
        
        edit_controls = ttk.Frame(self, padding=(8,0,8,6))
        edit_controls.pack(fill='x')
        ttk.Label(edit_controls, text='Oscillator').pack(side='left')
        for shape in ['square', 'saw', 'triangle', 'sine']:
            ttk.Radiobutton(edit_controls, text=shape.capitalize(), variable=self.wave_shape, value=shape).pack(side='left', padx=3)
        ttk.Label(edit_controls, text='Volume').pack(side='left', padx=(14,3))
        ttk.Scale(edit_controls, from_=0.0, to=0.8, variable=self.volume, length=140).pack(side='left')
        ttk.Label(edit_controls, text='Octave').pack(side='left', padx=(20,3))
        for v in [-2,-1,0,1,2]:
            ttk.Radiobutton(edit_controls, text=f'{v:+d}', variable=self.octave_shift, value=v, command=self.refresh_keyboard).pack(side='left')
            
        self.status = ttk.Label(self, padding=(8,0,8,8), text='')
        self.status.pack(fill='x')

    def _build_menu(self) -> None:
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=False)
        fm.add_command(label='Open .mbseq', command=self.open_file)
        self.recent_menu = tk.Menu(fm, tearoff=False)
        fm.add_cascade(label='Open Recent', menu=self.recent_menu)
        self._refresh_recent_menu()
        fm.add_command(label='Save', command=self.save_file)
        fm.add_command(label='Save As...', command=self.save_as)
        fm.add_separator()
        fm.add_command(label='Import MIDI into selected bank...', command=self.import_midi_file)
        fm.add_separator()
        fm.add_command(label='Export selected bank as MIDI...', command=self.export_midi_file)
        fm.add_command(label='Export all 8 banks as MIDI files...', command=self.export_all_midi_files)
        fm.add_command(label='Export song (all banks) as one MIDI...', command=self.export_song_midi_file)
        fm.add_command(label='Export selected bank as WAV...', command=self.export_bank_wav)
        fm.add_separator()
        fm.add_command(label='Exit', command=self.on_close)
        m.add_cascade(label='File', menu=fm)
        
        em = tk.Menu(m, tearoff=False)
        em.add_command(label='Undo', accelerator='Ctrl+Z', command=self.undo)
        em.add_command(label='Redo', accelerator='Ctrl+Y', command=self.redo)
        em.add_separator()
        em.add_command(label='Copy Step', accelerator='Ctrl+C', command=self.copy_step)
        em.add_command(label='Paste Step', accelerator='Ctrl+V', command=self.paste_step)
        em.add_separator()
        em.add_command(label='Copy Whole Bank', accelerator='Ctrl+Shift+C', command=self.copy_bank)
        em.add_command(label='Paste Whole Bank', accelerator='Ctrl+Shift+V', command=self.paste_bank)
        em.add_separator()
        em.add_command(label='Clear Selection', command=self.clear_selection)
        m.add_cascade(label='Edit', menu=em)
        
        vm = tk.Menu(m, tearoff=False)
        vm.add_checkbutton(label='Dark Mode', variable=self.dark_mode, command=self.toggle_theme)
        vm.add_separator()
        vm.add_command(label='Settings...', command=self.show_settings_dialog)
        m.add_cascade(label='View', menu=vm)
        self.config(menu=m)

    def _bind_keys(self) -> None:
        self.bind('<space>', lambda e: self.toggle_play())   # DAW convention
        self.bind('r', lambda e: self.insert_rest())
        self.bind('<Insert>', lambda e: self.insert_rest())
        self.bind('<Escape>', lambda e: self.stop_sequence())
        self.bind('<Control-z>', lambda e: self.undo())
        self.bind('<Control-y>', lambda e: self.redo())
        self.bind('<Control-Z>', lambda e: self.redo())      # Ctrl+Shift+Z
        self.bind('<Control-c>', lambda e: self.copy_step())
        self.bind('<Control-v>', lambda e: self.paste_step())
        self.bind('<Control-C>', lambda e: self.copy_bank()) # Ctrl+Shift+C
        self.bind('<Control-V>', lambda e: self.paste_bank()) # Ctrl+Shift+V
        self.bind('<Left>', lambda e: self.move_cursor(-1))
        self.bind('<Right>', lambda e: self.move_cursor(1))
        for idx, key in enumerate(PC_KEYS[:25]):
            try:
                self.bind(key, lambda e, i=idx: self.insert_note(self.note_for_index(i)))
            except tk.TclError:
                pass

    def steps(self) -> list[int | None]:
        s = int(self.slot.get())
        if s not in self.project.sequences:
            self.project.sequences[s] = [None] * MAX_STEPS
        return self.project.sequences[s]

    def note_for_index(self, idx: int) -> int:
        return max(0, min(127, self.root_note + self.octave_shift.get() * 12 + idx))

    def _at_step_limit(self) -> bool:
        if len(self.steps()) >= MAX_STEPS:
            self.status.config(text=f'Bank is full: MicroBrute SE allows at most {MAX_STEPS} steps per bank.')
            return True
        return False

    def toggle_theme(self) -> None:
        style = ttk.Style()
        if self.dark_mode.get():
            self.configure(bg='#2b2b2b')
            style.theme_use('clam')
            style.configure('TFrame', background='#2b2b2b')
            style.configure('TLabel', background='#2b2b2b', foreground='#ffffff')
            style.configure('TButton', background='#404040', foreground='#ffffff')
            style.configure('TCheckbutton', background='#2b2b2b', foreground='#ffffff')
            style.configure('TRadiobutton', background='#2b2b2b', foreground='#ffffff')
            style.configure('TLabelframe', background='#2b2b2b', foreground='#ffffff')
            style.configure('TLabelframe.Label', background='#2b2b2b', foreground='#ffffff')
            self.raw.configure(bg='#1e1e1e', fg='#ffffff', insertbackground='white')
        else:
            self.configure(bg='#f0f0f0')
            style.theme_use('default')
            style.configure('TFrame', background='#f0f0f0')
            style.configure('TLabel', background='#f0f0f0', foreground='#000000')
            style.configure('TButton', background='#e1e1e1', foreground='#000000')
            style.configure('TCheckbutton', background='#f0f0f0', foreground='#000000')
            style.configure('TRadiobutton', background='#f0f0f0', foreground='#000000')
            style.configure('TLabelframe', background='#f0f0f0', foreground='#000000')
            style.configure('TLabelframe.Label', background='#f0f0f0', foreground='#000000')
            self.raw.configure(bg='#ffffff', fg='#000000', insertbackground='black')
        self._save_settings()
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_grid()
        self.refresh_keyboard()
        self.refresh_raw()
        self.refresh_status()

    def _recent_config_path(self) -> Path:
        return Path.home() / '.microbrrrute_studio_recent.json'

    def _settings_path(self) -> Path:
        return Path.home() / '.microbrrrute_studio_settings.json'

    def _load_settings(self) -> None:
        p = self._settings_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                if 'volume' in data:
                    self.volume.set(data['volume'])
                if 'tempo' in data:
                    self.tempo.set(data['tempo'])
                if 'dark_mode' in data:
                    self.dark_mode.set(data['dark_mode'])
                if 'wave_shape' in data:
                    self.wave_shape.set(data['wave_shape'])
                if 'step_res' in data:
                    self.step_res.set(data['step_res'])
            except Exception:
                pass

    def _save_settings(self) -> None:
        try:
            data = {
                'volume': self.volume.get(),
                'tempo': self.tempo.get(),
                'dark_mode': self.dark_mode.get(),
                'wave_shape': self.wave_shape.get(),
                'step_res': self.step_res.get(),
            }
            self._settings_path().write_text(json.dumps(data), encoding='utf-8')
        except Exception:
            pass

    def _load_recent(self) -> list[str]:
        p = self._recent_config_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    return [f for f in data if isinstance(f, str) and Path(f).exists()][:10]
            except Exception:
                pass
        return []

    def _save_recent(self) -> None:
        try:
            self._recent_config_path().write_text(json.dumps(self.recent_files), encoding='utf-8')
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
        if not hasattr(self, 'recent_menu'):
            return
        self.recent_menu.delete(0, 'end')
        if not self.recent_files:
            self.recent_menu.add_command(label='(No recent files)', state='disabled')
        else:
            for p in self.recent_files:
                self.recent_menu.add_command(label=p, command=lambda x=p: self.open_recent(x))

    def open_recent(self, path: str) -> None:
        if not Path(path).exists():
            messagebox.showerror('Open Recent', f'File not found: {path}')
            self.recent_files.remove(path)
            self._save_recent()
            self._refresh_recent_menu()
            return
        self._do_open(path)

    def refresh_status(self) -> None:
        path = str(self.file_path) if self.file_path else 'unsaved'
        cur = self.cursor.get()+1
        loaded = ','.join(str(i) for i in range(1, 9) if i in self.project.sequences)
        flag = ' *modified' if self.dirty else ''
        
        # Validate hardware range
        steps = self.steps()
        out_of_range = any(n is not None and (n < MIN_PLAYABLE or n > MAX_PLAYABLE) for n in steps)
        range_warn = ' | ⚠️ Note outside MicroBrute range!' if out_of_range else ''
        
        self.status.config(text=f'{path}{flag} | Bank {self.slot.get()}/8 | Steps {len(steps)} | Cursor {cur} | Banks: {loaded}{range_warn}')
        name = self.file_path.name if self.file_path else 'untitled'
        self.title(f'{"*" if self.dirty else ""}{name} - microBRRRute Studio')

    def show_settings_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title('App Settings')
        win.geometry('300x250')
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding=20)
        f.pack(fill='both', expand=True)

        ttk.Checkbutton(f, text='Dark Mode', variable=self.dark_mode, command=self.toggle_theme).pack(anchor='w', pady=5)
        
        ttk.Label(f, text='Default Volume').pack(anchor='w', pady=(10,0))
        ttk.Scale(f, from_=0.0, to=0.8, variable=self.volume, orient='horizontal').pack(fill='x', pady=5)

        ttk.Label(f, text='Default Tempo (BPM)').pack(anchor='w', pady=(10,0))
        ttk.Spinbox(f, from_=30, to=300, textvariable=self.tempo).pack(anchor='w', pady=5)

        ttk.Button(f, text='Close', command=win.destroy).pack(side='bottom', pady=(20,0))

    def mark_dirty(self) -> None:
        self.dirty = True

    # --- Undo / redo --------------------------------------------------------
    def _snapshot(self) -> dict[int, list[int | None]]:
        return {k: list(v) for k, v in self.project.sequences.items()}

    def push_undo(self) -> None:
        """Capture the current state before a mutating edit."""
        self._undo.append(self._snapshot())
        if len(self._undo) > 100:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(self._snapshot())
        self.project.sequences = self._undo.pop()
        self.mark_dirty()
        self.refresh_all()

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(self._snapshot())
        self.project.sequences = self._redo.pop()
        self.mark_dirty()
        self.refresh_all()

    def copy_step(self) -> None:
        idx = self.cursor.get()
        steps = self.steps()
        if idx < len(steps):
            val = steps[idx]
            text = 'x' if val is None else str(val)
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text=f'Step {idx+1} ({text}) copied to clipboard.')

    def paste_step(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return

        # If it's a single token, paste to step. If multiple, maybe it's a bank?
        # For simplicity, if it's one token, we paste to current step.
        tokens = text.split()
        if not tokens:
            return

        if len(tokens) > 1:
            # Fallback to bank paste if user pressed Ctrl+V with a bank in clipboard
            return self.paste_bank()

        t = tokens[0]
        val: int | None = None
        if t.lower() == 'x':
            val = None
        else:
            try:
                n = int(t)
                if 0 <= n <= 127:
                    val = n
                else:
                    raise ValueError()
            except ValueError:
                return

        self.push_undo()
        steps = self.steps()
        idx = self.cursor.get()
        if idx >= len(steps):
            steps.append(val)
        else:
            steps[idx] = val
        self.mark_dirty()
        self.refresh_grid()
        self.refresh_raw()
        self.status.config(text=f'Pasted {t} into step {idx+1}.')

    def copy_bank(self) -> None:
        steps = self.steps()
        tokens = ['x' if n is None else str(n) for n in steps]
        text = ' '.join(tokens)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.config(text=f'Whole Bank {self.slot.get()} copied to clipboard.')

    def paste_bank(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return messagebox.showinfo('Paste Bank', 'Clipboard is empty.')
        
        # Simple validation: space-separated notes or 'x'
        tokens = text.split()
        if not tokens:
            return messagebox.showinfo('Paste Bank', 'Clipboard does not contain valid step data.')
        
        new_steps = []
        for t in tokens:
            if t.lower() == 'x':
                new_steps.append(None)
            else:
                try:
                    n = int(t)
                    if 0 <= n <= 127:
                        new_steps.append(n)
                    else:
                        raise ValueError()
                except ValueError:
                    return messagebox.showerror('Paste Bank', f'Invalid step data: {t}')
        
        if len(new_steps) > MAX_STEPS:
            messagebox.showinfo('Paste Bank', f'Data has {len(new_steps)} steps; truncated to {MAX_STEPS}.')
            new_steps = new_steps[:MAX_STEPS]
        
        self.push_undo()
        self.project.sequences[int(self.slot.get())] = new_steps
        self.mark_dirty()
        self.refresh_all()
        self.status.config(text=f'Pasted {len(new_steps)} steps into bank {self.slot.get()}.')

    # --- Transpose ----------------------------------------------------------
    def transpose_bank(self, semitones: int) -> None:
        self.push_undo()
        slot = int(self.slot.get())
        steps = self.steps()

        # If selection exists, only transpose those indices
        if self._selection:
            for idx in self._selection:
                if 0 <= idx < len(steps):
                    val = steps[idx]
                    if val is not None:
                        steps[idx] = max(0, min(127, val + semitones))
        else:
            self.project.sequences[slot] = transpose_steps(steps, semitones)

        self.mark_dirty()
        self.refresh_grid()
        self.refresh_keyboard()
        self.refresh_raw()

    # --- MIDI / WAV import & export ----------------------------------------
    def import_midi_file(self) -> None:
        p = filedialog.askopenfilename(filetypes=[('MIDI file','*.mid'),('All files','*.*')])
        if not p:
            return
        try:
            steps = import_midi(p)
        except Exception as e:
            messagebox.showerror('MIDI import failed', str(e))
            return
        if not steps:
            messagebox.showinfo('MIDI import', 'No notes found in that file.')
            return
        if len(steps) > MAX_STEPS:
            messagebox.showinfo('MIDI import',
                f'File has {len(steps)} steps; truncated to the MicroBrute limit of {MAX_STEPS}.')
            steps = steps[:MAX_STEPS]
        self.push_undo()
        self.project.sequences[int(self.slot.get())] = steps
        self.mark_dirty()
        self.cursor.set(0)
        self.refresh_all()

    def export_song_midi_file(self) -> None:
        banks = [self.project.sequences[b] for b in range(1, 9)
                 if any(n is not None for n in self.project.sequences.get(b, []))]
        if not banks:
            messagebox.showinfo('Export song', 'All banks are empty.')
            return
        p = filedialog.asksaveasfilename(defaultextension='.mid',
            filetypes=[('MIDI file','*.mid'),('All files','*.*')])
        if not p:
            return
        try:
            export_song_midi(p, banks, bpm=self.tempo.get())
        except Exception as e:
            messagebox.showerror('Export song failed', str(e))

    def export_bank_wav(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension='.wav',
            filetypes=[('WAV audio','*.wav'),('All files','*.*')])
        if not p:
            return
        try:
            render_steps_wav(p, self.steps(), bpm=self.tempo.get(),
                             wave_shape=self.wave_shape.get(), volume=self.volume.get())
        except Exception as e:
            messagebox.showerror('WAV export failed', str(e))

    def on_close(self) -> None:
        self.stop_sequence()
        self._save_settings()
        if self.dirty and not messagebox.askokcancel('Unsaved changes',
                'You have unsaved changes. Quit without saving?'):
            return
        self.destroy()

    def refresh_raw(self) -> None:
        self.raw.delete('1.0','end')
        self.raw.insert('1.0', self.project.serialize())

    def on_resize(self, event: tk.Event) -> None:
        # Only trigger reflow if it's the main window resizing and width actually changed
        if event.widget == self:
            self.refresh_grid()

    def refresh_grid(self) -> None:
        steps = self.steps()
        if self.cursor.get() < 0:
            self.cursor.set(0)
        if self.cursor.get() >= len(steps):
            self.cursor.set(max(0, len(steps) - 1))

        # Calculate how many columns can fit
        win_width = self.winfo_width()
        btn_width = 65  # approx width of button + padding
        cols = max(1, (win_width - 40) // btn_width)

        # Ensure we have enough widgets
        children = self.grid_inner.winfo_children()
        required_widgets = len(steps) * 2 # Label + Button for each step

        # If structure changed (cols) or count changed, full rebuild is safer/easier
        # but for simple note updates, we can just update.
        # We'll store current cols to detect layout changes.
        if not hasattr(self, '_last_cols') or self._last_cols != cols or len(children) != required_widgets:
            for w in children:
                w.destroy()
            self.step_buttons.clear()
            self._last_cols = cols

            for i, n in enumerate(steps):
                row = (i // cols) * 2
                col = i % cols
                lbl = ttk.Label(self.grid_inner, text=str(i+1), anchor='center')
                lbl.grid(row=row, column=col, padx=1)

                b = tk.Button(self.grid_inner, width=7, height=2, highlightthickness=0)
                b.grid(row=row+1, column=col, padx=1, pady=(0,4))
                b.bind('<Button-3>', lambda e, x=i: self.set_step_rest(x))
                b.bind('<ButtonPress-1>', lambda e, x=i: self._on_step_click(e, x))
                b.bind('<B1-Motion>', self._on_drag_motion)
                b.bind('<ButtonRelease-1>', lambda e, x=i: self._on_drag_stop(e, x))
                self.step_buttons.append(b)

            children = self.grid_inner.winfo_children()

        # Update existing widgets
        for i, n in enumerate(steps):
            txt = 'REST\nx' if n is None else f'{midi_to_name(n)}\n{n}'
            
            is_playing = (i == self._playhead)
            is_cursor = (i == self.cursor.get())
            is_selected = (i in self._selection)
            
            if is_playing:
                bg = '#7CFC8A'  # green = currently sounding
                fg = '#000000'
            elif is_selected:
                bg = '#ffa500' if self.dark_mode.get() else '#ffcc00' # orange/gold selection
                fg = '#000000'
            elif is_cursor:
                bg = '#0078d7' if self.dark_mode.get() else '#d7f0ff'
                fg = '#ffffff' if self.dark_mode.get() else '#000000'
            else:
                bg = '#404040' if self.dark_mode.get() else '#ffffff'
                fg = '#ffffff' if self.dark_mode.get() else '#000000'

            btn = self.step_buttons[i]
            # Use a slight border for selection if it's also the cursor
            border = 2 if is_selected else 0
            btn.config(text=txt, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, 
                       highlightbackground='#ffffff', highlightthickness=border,
                       command=lambda x=i: self.select_step(x))

        self.refresh_status()

    def _on_drag_start(self, idx: int) -> None:
        self._drag_idx = idx

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag_idx is None:
            return
        
        # Identify the widget under the mouse
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        
        # Reset all button borders/highlights
        for btn in self.step_buttons:
            btn.config(highlightbackground='SystemButtonFace' if not self.dark_mode.get() else '#2b2b2b', highlightthickness=0)

        # Highlight target
        for btn in self.step_buttons:
            if btn == target:
                btn.config(highlightbackground='#7CFC8A', highlightthickness=2)
                break

    def _on_drag_stop(self, event: tk.Event, src_idx: int) -> None:
        if self._drag_idx is None:
            return
        
        # Reset highlights
        for btn in self.step_buttons:
            btn.config(highlightthickness=0)
        
        # Identify the widget under the mouse
        target = event.widget.winfo_containing(event.x_root, event.y_root)
        dst_idx = None
        
        # Check if the target is one of our step buttons
        for i, btn in enumerate(self.step_buttons):
            if btn == target:
                dst_idx = i
                break
        
        if dst_idx is not None and dst_idx != src_idx:
            self.push_undo()
            steps = self.steps()
            # Move step from src to dst
            val = steps.pop(src_idx)
            steps.insert(dst_idx, val)
            self.mark_dirty()
            self.refresh_all()
        
        self._drag_idx = None

    def _on_step_click(self, event: tk.Event, idx: int) -> None:
        self._on_drag_start(idx)
        self.select_step(idx, event)

    def select_step(self, idx: int, event: tk.Event | None = None) -> None:
        old_cursor = self.cursor.get()
        self.cursor.set(idx)
        
        if event and event.state & 0x0001: # Shift key
            start = min(old_cursor, idx)
            end = max(old_cursor, idx)
            for i in range(start, end + 1):
                self._selection.add(i)
        elif event and (event.state & 0x0004 or event.state & 0x20000): # Control or Command
            if idx in self._selection:
                self._selection.remove(idx)
            else:
                self._selection.add(idx)
        else:
            self._selection.clear()
            self._selection.add(idx)
            
        self.refresh_grid()
        n = self.steps()[idx]
        if n is not None:
            self.preview_note(n)

    def refresh_keyboard(self) -> None:
        bg_col = '#333333' if self.dark_mode.get() else '#666666'
        txt_col = '#ffffff'
        self.keyboard.configure(bg=bg_col)
        self.keyboard.delete('all')
        self.key_rects.clear()
        white_w, white_h = 66, 180
        black_w, black_h = 42, 108
        x0, y0 = 10, 10
        # white keys spanning C..C two octaves plus C
        for wi, off in enumerate(WHITE_OFFSETS):
            note = self.root_note + self.octave_shift.get()*12 + off
            x = x0 + wi*white_w
            rect = self.keyboard.create_rectangle(x,y0,x+white_w,y0+white_h, fill='white', outline='black')
            self.key_rects[note] = rect
            self.keyboard.tag_bind(rect, '<Button-1>', lambda e, n=note: self.insert_note(n))
            self.keyboard.tag_bind(rect, '<Button-3>', lambda e, n=note: self.preview_note(n))
            label = self.keyboard.create_text(x+white_w/2, y0+white_h-22, text=midi_to_name(note), fill='black')
            self.keyboard.tag_bind(label, '<Button-1>', lambda e, n=note: self.insert_note(n))
        for off in BLACK_OFFSETS:
            note = self.root_note + self.octave_shift.get()*12 + off
            x = x0 + BLACK_POS[off]*white_w
            rect = self.keyboard.create_rectangle(x,y0,x+black_w,y0+black_h, fill='black', outline='black')
            self.key_rects[note] = rect
            self.keyboard.tag_bind(rect, '<Button-1>', lambda e, n=note: self.insert_note(n))
            self.keyboard.tag_bind(rect, '<Button-3>', lambda e, n=note: self.preview_note(n))
            label = self.keyboard.create_text(x+black_w/2, y0+black_h-18, text=midi_to_name(note), fill='white')
            self.keyboard.tag_bind(label, '<Button-1>', lambda e, n=note: self.insert_note(n))
        self.keyboard.create_text(20, 202, anchor='w', fill=txt_col, text=f'Range: {midi_to_name(self.root_note + self.octave_shift.get()*12)} to {midi_to_name(self.root_note + self.octave_shift.get()*12 + 24)}')

    def preview_note(self, note:int, duration: float = 0.18) -> None:
        play_note(note, duration=duration, wave_shape=self.wave_shape.get(), volume=self.volume.get())
        self.highlight_note(note)

    def highlight_note(self, note: int) -> None:
        if note not in self.key_rects:
            return
        rect = self.key_rects[note]
        # Determine original color
        # The scale repeats every 24 keys in the canvas (2 octaves), 
        # but offsets are absolute from root.
        rel = note - (self.root_note + self.octave_shift.get()*12)
        orig = 'black' if rel in BLACK_OFFSETS else 'white'
        self.keyboard.itemconfig(rect, fill='#7CFC8A')  # green highlight
        self.after(200, lambda: self.keyboard.itemconfig(rect, fill=orig))

    def insert_note(self, note:int) -> None:
        self.preview_note(note)
        steps = self.steps()
        idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit():
            return
        self.push_undo()
        if idx >= len(steps):
            steps.append(note)
        else:
            steps[idx] = note
        self.mark_dirty()
        self.move_cursor(1, refresh=False)
        self.refresh_grid()
        self.refresh_raw()

    def insert_rest(self) -> None:
        steps = self.steps()
        idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit():
            return
        self.push_undo()
        if idx >= len(steps):
            steps.append(None)
        else:
            steps[idx] = None
        self.mark_dirty()
        self.move_cursor(1, refresh=False)
        self.refresh_grid()
        self.refresh_raw()

    def set_step_rest(self, idx:int) -> None:
        self.push_undo()
        self.steps()[idx] = None
        self.mark_dirty()
        self.cursor.set(idx)
        self.refresh_grid()
        self.refresh_raw()

    def move_cursor(self, delta:int, refresh=True) -> None:
        self.cursor.set(max(0, min(len(self.steps())-1, self.cursor.get()+delta)))
        if refresh:
            self.refresh_grid()

    def change_slot(self) -> None:
        self.cursor.set(0)
        self.clear_selection()
        self.refresh_all()

    def clear_selection(self) -> None:
        self._selection.clear()
        self.refresh_grid()

    def add_step(self) -> None:
        if self._at_step_limit():
            return
        self.push_undo()
        steps = self.steps()
        idx = self.cursor.get()+1
        steps.insert(idx, None)
        self.mark_dirty()
        self.cursor.set(idx)
        self.refresh_grid()
        self.refresh_raw()

    def delete_step(self) -> None:
        steps = self.steps()
        if not steps:
            return
        self.push_undo()
        
        if self._selection:
            # Sort indices in descending order to avoid shift issues
            for idx in sorted(list(self._selection), reverse=True):
                if idx < len(steps):
                    steps.pop(idx)
            self.clear_selection()
        else:
            steps.pop(self.cursor.get())
            
        if not steps:
            steps.append(None)
        self.mark_dirty()
        self.cursor.set(min(self.cursor.get(), len(steps)-1))
        self.refresh_grid()
        self.refresh_raw()

    def clear_slot(self) -> None:
        if messagebox.askyesno('Clear bank', f'Clear pattern bank {self.slot.get()}?'):
            self.push_undo()
            self.project.sequences[int(self.slot.get())] = [None]*MAX_STEPS
            self.mark_dirty()
            self.cursor.set(0)
            self.refresh_all()


    def duplicate_bank_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title('Duplicate Pattern Bank')
        win.geometry('300x150')
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding=20)
        f.pack(fill='both', expand=True)

        ttk.Label(f, text=f'Duplicate bank {self.slot.get()} to:').grid(row=0, column=0, pady=(0,10))
        target = tk.IntVar(value=1)
        cb = ttk.Combobox(f, textvariable=target, values=list(range(1,9)), width=4, state='readonly')
        cb.grid(row=0, column=1, padx=10, pady=(0,10))

        def do_copy():
            dst = target.get()
            if dst == int(self.slot.get()):
                return messagebox.showwarning('Duplicate', 'Target must be a different bank.')
            self.push_undo()
            self.project.sequences[dst] = list(self.steps())
            self.mark_dirty()
            self.refresh_status()
            win.destroy()
            messagebox.showinfo('Duplicate', f'Bank {self.slot.get()} copied to {dst}.')

        ttk.Button(f, text='Copy', command=do_copy).grid(row=1, column=0, padx=12, pady=(0,12))
        ttk.Button(f, text='Cancel', command=win.destroy).grid(row=1, column=1, padx=12, pady=(0,12))

    def show_audio_error(self) -> None:
        err = get_last_audio_error()
        if err:
            messagebox.showerror('Audio backend error', err)
        else:
            messagebox.showinfo('Audio backend', 'No audio error reported. If you still hear nothing, check Windows output device and app volume mixer.')

    def toggle_play(self) -> None:
        if self.playing:
            self.stop_sequence()
        else:
            self.play_sequence()

    def play_sequence(self) -> None:
        self.stop_sequence()
        # Always only play the selected bank
        self._play_banks = [int(self.slot.get())]
        self._start_playback()

    def _start_playback(self) -> None:
        bank = self._play_banks[0]
        steps = self.project.sequences.get(bank, [None]*MAX_STEPS)
        if not any(n is not None for n in steps):
            messagebox.showinfo('Play', f'Bank {bank} is empty.')
            return

        self.playing = True
        self._play_idx = 0
        if self.play_btn:
            self.play_btn.config(state='disabled')
        if self.stop_btn:
            self.stop_btn.config(state='normal')
        self.refresh_all()

        # Pre-render ONLY the current bank for rock-solid timing
        data = render_steps_to_data(steps, bpm=self.tempo.get(),
                                   wave_shape=self.wave_shape.get(),
                                   volume=self.volume.get(),
                                   metronome=self.metronome.get())

        self._pre_render_file = Path(tempfile.gettempdir()) / f'mbseq_render_{uuid.uuid4().hex}.wav'
        render_pre_rendered_wav(self._pre_render_file, data)

        if self.count_in.get():
            self._play_count_in(8)  # 4 beats = 8 steps
        else:
            self._start_audio_and_tick()

    def _start_audio_and_tick(self) -> None:
        if not self.playing or not self._pre_render_file:
            return
        play_pre_rendered_wav(self._pre_render_file)
        self._play_tick()

    def _play_count_in(self, steps_left: int) -> None:
        if not self.playing:
            return
        if steps_left <= 0:
            return self._start_audio_and_tick()
        div = 4 if self.step_res.get() == '1/16' else 2
        ms = int(60000 / max(1, self.tempo.get()) / div)
        is_beat = (steps_left % 2 == 0)
        self.preview_note(84 if is_beat else 72, duration=0.03)
        self._after_id = self.after(ms, lambda: self._play_count_in(steps_left - 1))

    def _play_tick(self) -> None:
        if not self.playing:
            return
        steps = self.steps()
        div = 4 if self.step_res.get() == '1/16' else 2
        ms = int(60000 / max(1, self.tempo.get()) / div)  # eighth-note-ish steps
        if not steps or self._play_idx >= len(steps):
            self._advance_bank()
            return
        idx = self._play_idx
        self._playhead = idx
        self.refresh_grid()
        
        # Audio is pre-rendered in the WAV file, so we just highlight the note for visual feedback
        note = steps[idx]
        if note is not None:
            self.highlight_note(note)
        
        self._play_idx += 1
        self._after_id = self.after(ms, self._play_tick)

    def _advance_bank(self) -> None:
        """Reached the end of the current bank's steps; move on or stop."""
        if self.loop.get():
            # Restart pre-rendered audio for looping
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
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        stop_all()                             # silence the in-flight note now

        # Cleanup pre-rendered file
        if self._pre_render_file:
            try:
                self._pre_render_file.unlink()
            except Exception:
                pass
            self._pre_render_file = None

        self._playhead = -1
        if self.play_btn:
            self.play_btn.config(state='normal')
        if self.stop_btn:
            self.stop_btn.config(state='disabled')
        self.refresh_grid()

def main():
    MbseqStudio().mainloop()

if __name__ == '__main__':
    main()
