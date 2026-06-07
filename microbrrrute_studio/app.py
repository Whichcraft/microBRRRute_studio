from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from .mbseq import MbseqProject, midi_to_name, name_to_midi, transpose_steps
from .synth import play_note, get_last_audio_error, stop_all, render_steps_wav
from .midi_export import export_midi, export_song_midi, import_midi

MAX_STEPS = 64  # MicroBrute SE hardware limit: 64 steps per pattern bank
WHITE_OFFSETS = [0,2,4,5,7,9,11,12,14,16,17,19,21,23,24]
BLACK_OFFSETS = [1,3,6,8,10,13,15,18,20,22]
BLACK_POS = {1:0.65, 3:1.65, 6:3.65, 8:4.65, 10:5.65, 13:7.65, 15:8.65, 18:10.65, 20:11.65, 22:12.65}
PC_KEYS = list('awsedftgyhujkolpö')

class MbseqStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('microBRRRute Studio - MicroBrute SE Composer')
        self.geometry('1380x850')
        self.minsize(1050, 700)

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
        self.playing = False
        self.dirty = False
        self._undo: list[dict[int, list[int | None]]] = []
        self._redo: list[dict[int, list[int | None]]] = []
        self._after_id = None
        self._play_idx = 0
        self._playhead = -1            # step currently sounding (-1 = none)
        self._play_banks: list[int] = []  # bank queue when playing all banks
        self.step_buttons: list[tk.Button] = []
        self.key_rects: dict[int, int] = {}
        self.play_btn: ttk.Button | None = None
        self.stop_btn: ttk.Button | None = None

        self._build()
        self._bind_keys()
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.refresh_all()

    def _build(self):
        self._build_menu()
        top = ttk.Frame(self, padding=8)
        top.pack(fill='x')
        ttk.Label(top, text='Pattern bank').pack(side='left')
        slot_box = ttk.Combobox(top, textvariable=self.slot, values=list(range(1,9)), width=4, state='readonly')
        slot_box.pack(side='left', padx=(4,8))
        slot_box.bind('<<ComboboxSelected>>', lambda e: self.change_slot())
        for bank in range(1, 9):
            ttk.Radiobutton(top, text=str(bank), variable=self.slot, value=bank, command=self.change_slot).pack(side='left')
        ttk.Separator(top, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Label(top, text='Cursor').pack(side='left')
        ttk.Spinbox(top, from_=1, to=MAX_STEPS, textvariable=self.cursor, width=5, command=self.refresh_grid).pack(side='left', padx=(4,14))
        ttk.Button(top, text='Open', command=self.open_file).pack(side='left')
        ttk.Button(top, text='Save', command=self.save_file).pack(side='left', padx=3)
        ttk.Button(top, text='Save As', command=self.save_as).pack(side='left')
        ttk.Separator(top, orient='vertical').pack(side='left', fill='y', padx=10)
        self.play_btn = ttk.Button(top, text='▶ Play Bank', command=self.play_sequence)
        self.play_btn.pack(side='left')
        ttk.Button(top, text='▶▶ Play All', command=self.play_all_banks).pack(side='left', padx=3)
        self.stop_btn = ttk.Button(top, text='■ Stop', command=self.stop_sequence, state='disabled')
        self.stop_btn.pack(side='left', padx=3)
        ttk.Checkbutton(top, text='Loop', variable=self.loop).pack(side='left')
        ttk.Checkbutton(top, text='Metronome', variable=self.metronome).pack(side='left', padx=3)
        ttk.Button(top, text='Test Sound', command=lambda: self.preview_note(60)).pack(side='left', padx=3)
        ttk.Label(top, text='BPM').pack(side='left', padx=(10,2))
        ttk.Spinbox(top, from_=30, to=300, textvariable=self.tempo, width=5).pack(side='left')
        ttk.Button(top, text='Export Bank MIDI', command=self.export_midi_file).pack(side='left', padx=4)
        ttk.Button(top, text='Export Song MIDI', command=self.export_song_midi_file).pack(side='left', padx=2)
        ttk.Button(top, text='Export Bank WAV', command=self.export_bank_wav).pack(side='left', padx=2)
        ttk.Button(top, text='Export Song WAV', command=self.export_song_wav).pack(side='left', padx=2)
        ttk.Button(top, text='Show Audio Error', command=self.show_audio_error).pack(side='left', padx=(6,0))

        edit = ttk.Frame(self, padding=(8,0,8,6))
        edit.pack(fill='x')
        ttk.Button(edit, text='+ Step', command=self.add_step).pack(side='left')
        ttk.Button(edit, text='Delete Step', command=self.delete_step).pack(side='left', padx=3)
        ttk.Button(edit, text='Rest at Cursor', command=self.insert_rest).pack(side='left', padx=3)
        ttk.Button(edit, text='Clear Bank', command=self.clear_slot).pack(side='left', padx=10)
        ttk.Button(edit, text='Duplicate Bank To...', command=self.duplicate_bank_dialog).pack(side='left', padx=3)
        ttk.Label(edit, text='Transpose').pack(side='left', padx=(14,3))
        ttk.Button(edit, text='-12', width=4, command=lambda: self.transpose_bank(-12)).pack(side='left')
        ttk.Button(edit, text='-1', width=4, command=lambda: self.transpose_bank(-1)).pack(side='left')
        ttk.Button(edit, text='+1', width=4, command=lambda: self.transpose_bank(1)).pack(side='left')
        ttk.Button(edit, text='+12', width=4, command=lambda: self.transpose_bank(12)).pack(side='left')
        ttk.Label(edit, text='Oscillator').pack(side='left', padx=(20,3))
        ttk.Combobox(edit, textvariable=self.wave_shape, values=['square','saw','triangle','sine'], width=9, state='readonly').pack(side='left')
        ttk.Label(edit, text='Volume').pack(side='left', padx=(14,3))
        ttk.Scale(edit, from_=0.0, to=0.8, variable=self.volume, length=140).pack(side='left')
        ttk.Label(edit, text='Octave').pack(side='left', padx=(20,3))
        for v in [-2,-1,0,1,2]:
            ttk.Radiobutton(edit, text=f'{v:+d}', variable=self.octave_shift, value=v, command=self.refresh_keyboard).pack(side='left')

        self.grid_canvas = tk.Canvas(self, height=145, bg='#eeeeee', highlightthickness=0)
        self.grid_scroll = ttk.Scrollbar(self, orient='horizontal', command=self.grid_canvas.xview)
        self.grid_inner = ttk.Frame(self.grid_canvas)
        self.grid_inner.bind('<Configure>', lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox('all')))
        self.grid_canvas.create_window((0,0), window=self.grid_inner, anchor='nw')
        self.grid_canvas.configure(xscrollcommand=self.grid_scroll.set)
        self.grid_canvas.pack(fill='x', padx=8, pady=(4,0))
        self.grid_scroll.pack(fill='x', padx=8)

        kb_wrap = ttk.Frame(self, padding=8)
        kb_wrap.pack(fill='x')
        ttk.Label(kb_wrap, text='MicroBrute 25-key composer: click key = insert/play, right-click = preview. PC keys A W S E D F T G Y H U J K ... | Space = Play/Stop, R = rest, Esc = stop, Ctrl+Z/Y = undo/redo').pack(anchor='w')
        self.keyboard = tk.Canvas(kb_wrap, width=1030, height=210, bg='#666666', highlightthickness=0)
        self.keyboard.pack(fill='x', pady=6)

        text_frame = ttk.LabelFrame(self, text='Raw .mbseq text', padding=6)
        text_frame.pack(fill='both', expand=True, padx=8, pady=8)
        self.raw = tk.Text(text_frame, height=8, wrap='none')
        self.raw.pack(fill='both', expand=True)
        raw_btns = ttk.Frame(text_frame)
        raw_btns.pack(fill='x', pady=(5,0))
        ttk.Button(raw_btns, text='Apply Raw Text', command=self.apply_raw).pack(side='left')
        ttk.Button(raw_btns, text='Refresh Raw Text', command=self.refresh_raw).pack(side='left', padx=4)
        self.status = ttk.Label(self, padding=(8,0,8,8), text='')
        self.status.pack(fill='x')

    def _build_menu(self):
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=False)
        fm.add_command(label='Open .mbseq', command=self.open_file)
        fm.add_command(label='Save', command=self.save_file)
        fm.add_command(label='Save As...', command=self.save_as)
        fm.add_separator()
        fm.add_command(label='Import MIDI into selected bank...', command=self.import_midi_file)
        fm.add_separator()
        fm.add_command(label='Export selected bank as MIDI...', command=self.export_midi_file)
        fm.add_command(label='Export all 8 banks as MIDI files...', command=self.export_all_midi_files)
        fm.add_command(label='Export song (all banks) as one MIDI...', command=self.export_song_midi_file)
        fm.add_command(label='Export selected bank as WAV...', command=self.export_bank_wav)
        fm.add_command(label='Export song (all banks) as one WAV...', command=self.export_song_wav)
        fm.add_separator()
        fm.add_command(label='Exit', command=self.on_close)
        m.add_cascade(label='File', menu=fm)
        em = tk.Menu(m, tearoff=False)
        em.add_command(label='Undo', accelerator='Ctrl+Z', command=self.undo)
        em.add_command(label='Redo', accelerator='Ctrl+Y', command=self.redo)
        m.add_cascade(label='Edit', menu=em)
        self.config(menu=m)

    def _bind_keys(self):
        self.bind('<space>', lambda e: self.toggle_play())   # DAW convention
        self.bind('r', lambda e: self.insert_rest())
        self.bind('<Insert>', lambda e: self.insert_rest())
        self.bind('<Escape>', lambda e: self.stop_sequence())
        self.bind('<Control-z>', lambda e: self.undo())
        self.bind('<Control-y>', lambda e: self.redo())
        self.bind('<Control-Z>', lambda e: self.redo())      # Ctrl+Shift+Z
        self.bind('<Left>', lambda e: self.move_cursor(-1))
        self.bind('<Right>', lambda e: self.move_cursor(1))
        for idx, key in enumerate(PC_KEYS[:25]):
            # Tkinter's bind() only accepts ASCII key chars; skip any that don't
            # (e.g. 'ö') rather than crashing on startup.
            try:
                self.bind(key, lambda e, i=idx: self.insert_note(self.note_for_index(i)))
            except tk.TclError:
                pass

    def steps(self):
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

    def refresh_all(self):
        self.refresh_grid(); self.refresh_keyboard(); self.refresh_raw(); self.refresh_status()

    def refresh_status(self):
        path = str(self.file_path) if self.file_path else 'unsaved'
        cur = self.cursor.get()+1
        loaded = ','.join(str(i) for i in range(1, 9) if i in self.project.sequences)
        flag = ' *modified' if self.dirty else ''
        self.status.config(text=f'{path}{flag} | Bank {self.slot.get()}/8 | Steps {len(self.steps())} | Cursor {cur} | Banks: {loaded}')
        name = self.file_path.name if self.file_path else 'untitled'
        self.title(f'{"*" if self.dirty else ""}{name} - microBRRRute Studio')

    def mark_dirty(self):
        self.dirty = True

    # --- Undo / redo --------------------------------------------------------
    def _snapshot(self) -> dict[int, list[int | None]]:
        return {k: list(v) for k, v in self.project.sequences.items()}

    def push_undo(self):
        """Capture the current state before a mutating edit."""
        self._undo.append(self._snapshot())
        if len(self._undo) > 100:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self):
        if not self._undo:
            return
        self._redo.append(self._snapshot())
        self.project.sequences = self._undo.pop()
        self.mark_dirty()
        self.refresh_all()

    def redo(self):
        if not self._redo:
            return
        self._undo.append(self._snapshot())
        self.project.sequences = self._redo.pop()
        self.mark_dirty()
        self.refresh_all()

    # --- Transpose ----------------------------------------------------------
    def transpose_bank(self, semitones: int):
        self.push_undo()
        slot = int(self.slot.get())
        self.project.sequences[slot] = transpose_steps(self.steps(), semitones)
        self.mark_dirty()
        self.refresh_grid(); self.refresh_keyboard(); self.refresh_raw()

    # --- MIDI / WAV import & export ----------------------------------------
    def import_midi_file(self):
        p = filedialog.askopenfilename(filetypes=[('MIDI file','*.mid'),('All files','*.*')])
        if not p: return
        try:
            steps = import_midi(p)
        except Exception as e:
            return messagebox.showerror('MIDI import failed', str(e))
        if not steps:
            return messagebox.showinfo('MIDI import', 'No notes found in that file.')
        if len(steps) > MAX_STEPS:
            messagebox.showinfo('MIDI import',
                f'File has {len(steps)} steps; truncated to the MicroBrute limit of {MAX_STEPS}.')
            steps = steps[:MAX_STEPS]
        self.push_undo()
        self.project.sequences[int(self.slot.get())] = steps
        self.mark_dirty()
        self.cursor.set(0); self.refresh_all()

    def export_song_midi_file(self):
        banks = [self.project.sequences[b] for b in range(1, 9)
                 if any(n is not None for n in self.project.sequences.get(b, []))]
        if not banks:
            return messagebox.showinfo('Export song', 'All banks are empty.')
        p = filedialog.asksaveasfilename(defaultextension='.mid',
            filetypes=[('MIDI file','*.mid'),('All files','*.*')])
        if not p: return
        try:
            export_song_midi(p, banks, bpm=self.tempo.get())
        except Exception as e:
            messagebox.showerror('Export song failed', str(e))

    def export_bank_wav(self):
        p = filedialog.asksaveasfilename(defaultextension='.wav',
            filetypes=[('WAV audio','*.wav'),('All files','*.*')])
        if not p: return
        try:
            render_steps_wav(p, self.steps(), bpm=self.tempo.get(),
                             wave_shape=self.wave_shape.get(), volume=self.volume.get())
        except Exception as e:
            messagebox.showerror('WAV export failed', str(e))

    def export_song_wav(self):
        banks = [self.project.sequences[b] for b in range(1, 9)
                 if any(n is not None for n in self.project.sequences.get(b, []))]
        if not banks:
            return messagebox.showinfo('Export song WAV', 'All banks are empty.')
        p = filedialog.asksaveasfilename(defaultextension='.wav',
            filetypes=[('WAV audio','*.wav'),('All files','*.*')])
        if not p: return
        try:
            all_steps = [step for bank in banks for step in bank]
            render_steps_wav(p, all_steps, bpm=self.tempo.get(),
                             wave_shape=self.wave_shape.get(), volume=self.volume.get())
        except Exception as e:
            messagebox.showerror('Export song WAV failed', str(e))

    def on_close(self):
        self.stop_sequence()
        if self.dirty and not messagebox.askokcancel('Unsaved changes',
                'You have unsaved changes. Quit without saving?'):
            return
        self.destroy()

    def refresh_raw(self):
        self.raw.delete('1.0','end')
        self.raw.insert('1.0', self.project.serialize())

    def refresh_grid(self):
        for w in self.grid_inner.winfo_children(): w.destroy()
        self.step_buttons.clear()
        steps = self.steps()
        if self.cursor.get() < 0: self.cursor.set(0)
        if self.cursor.get() >= len(steps): self.cursor.set(max(0,len(steps)-1))
        for i, n in enumerate(steps):
            ttk.Label(self.grid_inner, text=str(i+1), anchor='center').grid(row=0,column=i, padx=1)
            txt = 'REST\nx' if n is None else f'{midi_to_name(n)}\n{n}'
            if i == self._playhead:
                bg = '#7CFC8A'  # green = currently sounding
            elif i == self.cursor.get():
                bg = '#d7f0ff'  # blue = edit cursor
            else:
                bg = '#ffffff'
            b = tk.Button(self.grid_inner, text=txt, width=7, height=3, bg=bg, command=lambda x=i: self.select_step(x))
            b.grid(row=1,column=i, padx=1, pady=2)
            b.bind('<Button-3>', lambda e, x=i: self.set_step_rest(x))
            self.step_buttons.append(b)
        self.refresh_status()

    def refresh_keyboard(self):
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
        self.keyboard.create_text(20, 202, anchor='w', fill='white', text=f'Range: {midi_to_name(self.root_note + self.octave_shift.get()*12)} to {midi_to_name(self.root_note + self.octave_shift.get()*12 + 24)}')

    def preview_note(self, note:int, duration: float = 0.18):
        play_note(note, duration=duration, wave_shape=self.wave_shape.get(), volume=self.volume.get())
        self.highlight_note(note)

    def highlight_note(self, note: int):
        if note not in self.key_rects:
            return
        rect = self.key_rects[note]
        # Determine original color
        off = (note - self.root_note - self.octave_shift.get()*12) % 24
        orig = 'black' if off in BLACK_OFFSETS else 'white'
        self.keyboard.itemconfig(rect, fill='#7CFC8A')  # same green as playhead
        self.after(200, lambda: self.keyboard.itemconfig(rect, fill=orig))

    def insert_note(self, note:int):
        self.preview_note(note)
        steps = self.steps()
        idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit():
            return
        self.push_undo()
        if idx >= len(steps): steps.append(note)
        else: steps[idx] = note
        self.mark_dirty()
        self.move_cursor(1, refresh=False)
        self.refresh_grid(); self.refresh_raw()

    def insert_rest(self):
        steps = self.steps(); idx = self.cursor.get()
        if idx >= len(steps) and self._at_step_limit():
            return
        self.push_undo()
        if idx >= len(steps): steps.append(None)
        else: steps[idx] = None
        self.mark_dirty()
        self.move_cursor(1, refresh=False)
        self.refresh_grid(); self.refresh_raw()

    def select_step(self, idx:int):
        self.cursor.set(idx); self.refresh_grid()
        n = self.steps()[idx]
        if n is not None: self.preview_note(n)

    def set_step_rest(self, idx:int):
        self.push_undo()
        self.steps()[idx] = None; self.mark_dirty(); self.cursor.set(idx); self.refresh_grid(); self.refresh_raw()

    def move_cursor(self, delta:int, refresh=True):
        self.cursor.set(max(0, min(len(self.steps())-1, self.cursor.get()+delta)))
        if refresh: self.refresh_grid()

    def change_slot(self):
        self.cursor.set(0); self.refresh_all()

    def add_step(self):
        if self._at_step_limit(): return
        self.push_undo()
        steps = self.steps(); idx = self.cursor.get()+1
        steps.insert(idx, None); self.mark_dirty(); self.cursor.set(idx); self.refresh_grid(); self.refresh_raw()

    def delete_step(self):
        steps = self.steps()
        if not steps: return
        self.push_undo()
        steps.pop(self.cursor.get())
        if not steps: steps.append(None)
        self.mark_dirty()
        self.cursor.set(min(self.cursor.get(), len(steps)-1))
        self.refresh_grid(); self.refresh_raw()

    def clear_slot(self):
        if messagebox.askyesno('Clear bank', f'Clear pattern bank {self.slot.get()}?'):
            self.push_undo()
            self.project.sequences[int(self.slot.get())] = [None]*MAX_STEPS
            self.mark_dirty()
            self.cursor.set(0); self.refresh_all()


    def duplicate_bank_dialog(self):
        win = tk.Toplevel(self)
        win.title('Duplicate Pattern Bank')
        win.resizable(False, False)
        ttk.Label(win, text=f'Copy bank {self.slot.get()} to bank:').grid(row=0, column=0, padx=12, pady=10)
        target = tk.IntVar(value=1 if self.slot.get() != 1 else 2)
        box = ttk.Combobox(win, textvariable=target, values=list(range(1,9)), width=4, state='readonly')
        box.grid(row=0, column=1, padx=12, pady=10)
        def do_copy():
            dst = int(target.get())
            src = int(self.slot.get())
            if dst == src:
                messagebox.showinfo('Duplicate bank', 'Source and target are the same bank.')
                return
            if messagebox.askyesno('Overwrite bank', f'Overwrite bank {dst} with bank {src}?'):
                self.push_undo()
                self.project.sequences[dst] = list(self.project.sequences[src])
                self.mark_dirty()
                self.slot.set(dst)
                self.cursor.set(0)
                win.destroy()
                self.refresh_all()
        ttk.Button(win, text='Copy', command=do_copy).grid(row=1, column=0, padx=12, pady=(0,12))
        ttk.Button(win, text='Cancel', command=win.destroy).grid(row=1, column=1, padx=12, pady=(0,12))

    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[('MicroBrute sequence','*.mbseq'),('All files','*.*')])
        if not p: return
        try:
            self.project = MbseqProject.load(p)
            self.file_path = Path(p)
            self.dirty = False
            self._undo.clear(); self._redo.clear()
            self.slot.set(1)
            self.cursor.set(0); self.refresh_all()
        except Exception as e:
            messagebox.showerror('Open failed', str(e))

    def save_file(self):
        if not self.file_path:
            return self.save_as()
        try:
            self.project.save(self.file_path); self.dirty = False; self.refresh_status()
        except Exception as e:
            messagebox.showerror('Save failed', str(e))

    def save_as(self):
        p = filedialog.asksaveasfilename(defaultextension='.mbseq', filetypes=[('MicroBrute sequence','*.mbseq'),('All files','*.*')])
        if not p: return
        self.file_path = Path(p); self.save_file()

    def apply_raw(self):
        try:
            self.push_undo()
            self.project = MbseqProject.parse(self.raw.get('1.0','end'))
            if int(self.slot.get()) not in self.project.sequences:
                self.slot.set(1)
            self.mark_dirty()
            self.cursor.set(0); self.refresh_grid(); self.refresh_keyboard(); self.refresh_status()
        except Exception as e:
            messagebox.showerror('Raw parse failed', str(e))

    def export_midi_file(self):
        p = filedialog.asksaveasfilename(defaultextension='.mid', filetypes=[('MIDI file','*.mid'),('All files','*.*')])
        if not p: return
        try:
            export_midi(p, self.steps(), bpm=self.tempo.get())
        except Exception as e:
            messagebox.showerror('MIDI export failed', str(e))


    def export_all_midi_files(self):
        folder = filedialog.askdirectory(title='Choose folder for 8 MIDI bank exports')
        if not folder: return
        try:
            base = self.file_path.stem if self.file_path else 'mbseq'
            out = Path(folder)
            for bank in range(1, 9):
                export_midi(out / f'{base}_bank_{bank}.mid', self.project.sequences.get(bank, [None]*MAX_STEPS), bpm=self.tempo.get())
            messagebox.showinfo('Export complete', f'Exported 8 MIDI files to:\n{folder}')
        except Exception as e:
            messagebox.showerror('MIDI export failed', str(e))

    def show_audio_error(self):
        err = get_last_audio_error()
        if err:
            messagebox.showerror('Audio backend error', err)
        else:
            messagebox.showinfo('Audio backend', 'No audio error reported. If you still hear nothing, check Windows output device and app volume mixer.')

    def toggle_play(self):
        if self.playing:
            self.stop_sequence()
        else:
            self.play_sequence()

    def play_sequence(self):
        self.stop_sequence()
        self._play_banks = [int(self.slot.get())]
        self._start_playback()

    def play_all_banks(self):
        self.stop_sequence()
        banks = [b for b in range(1, 9) if any(n is not None for n in self.project.sequences.get(b, []))]
        if not banks:
            messagebox.showinfo('Play All', 'All banks are empty.')
            return
        self._play_banks = banks
        self._start_playback()

    def _start_playback(self):
        if not any(self.project.sequences.get(b) for b in self._play_banks):
            messagebox.showinfo('Play', 'Nothing to play (no steps).')
            return
        self.playing = True
        self._play_idx = 0
        self.slot.set(self._play_banks[0])
        if self.play_btn: self.play_btn.config(state='disabled')
        if self.stop_btn: self.stop_btn.config(state='normal')
        self.refresh_all()
        self._play_tick()

    def _play_tick(self):
        if not self.playing: return
        steps = self.steps()
        ms = int(60000 / max(1, self.tempo.get()) / 2)  # eighth-note-ish steps
        if not steps or self._play_idx >= len(steps):
            return self._advance_bank()
        idx = self._play_idx
        self._playhead = idx
        self.refresh_grid()
        if self.metronome.get():
            # Play a click on quarter-note beats (every 2 steps)
            is_beat = (idx % 2 == 0)
            self.preview_note(84 if is_beat else 72, duration=0.03)
        note = steps[idx]
        if note is not None:
            self.preview_note(note, duration=max(0.05, ms / 1000 * 0.82))
        self._play_idx += 1
        self._after_id = self.after(ms, self._play_tick)

    def _advance_bank(self):
        """Reached the end of the current bank's steps; move on or stop."""
        current = int(self.slot.get())
        order = self._play_banks
        pos = order.index(current) if current in order else 0
        if pos + 1 < len(order):
            next_bank = order[pos + 1]         # next bank in the queue
        elif self.loop.get():
            next_bank = order[0]               # wrap back to the first bank
        else:
            return self.stop_sequence()
        self.slot.set(next_bank)
        self._play_idx = 0
        self._playhead = -1
        self.refresh_all()
        # Schedule (don't recurse) so an empty bank can't blow the stack.
        self._after_id = self.after(1, self._play_tick)

    def stop_sequence(self):
        self.playing = False
        if self._after_id:
            try: self.after_cancel(self._after_id)
            except Exception: pass
            self._after_id = None
        stop_all()                             # silence the in-flight note now
        self._playhead = -1
        if self.play_btn: self.play_btn.config(state='normal')
        if self.stop_btn: self.stop_btn.config(state='disabled')
        self.refresh_grid()


def main():
    MbseqStudio().mainloop()

if __name__ == '__main__':
    main()
