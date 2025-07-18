import os
import tkinter as tk
from tkinter import filedialog, messagebox
from music21 import stream, note, meter, key, midi, tempo

VOICE_ORDER = ["soprano", "alto", "tenor", "bass"]
OCTAVE_BASE = {"soprano": 5, "alto": 4, "tenor": 3, "bass": 2}
JIANPU_PITCH = {'1': 'C', '2': 'D', '3': 'E', '4': 'F', '5': 'G', '6': 'A', '7': 'B'}

DOTTED_DURATION_MAP = {
    '1': 1.5,
    '2': 0.75,
    '4': 0.375,
    '8': 0.1875,
    '16': 0.09375,
    '32': 0.046875,
    '64': 0.0234375
}

def parse_jianpu_line(line, voice):
    line = line.strip()
    if not line or line.startswith("#"): return None
    items = line.replace('|', '').split()
    notes = []
    for item in items:
        dur = 1.0
        if 'd' in item:
            pitch_text, dot_val = item.split('d')
            dur = DOTTED_DURATION_MAP.get(dot_val, 1.0)
        elif '*' in item:
            pitch_text, dur_text = item.split('*')
            try:
                dur = float(dur_text)
            except:
                dur = 1.0
        elif '/' in item:
            pitch_text, dur_div = item.split('/')
            try:
                dur = 1.0 / float(dur_div)
            except:
                dur = 1.0
        elif item.endswith('.'):
            dur = 1.5
            item = item[:-1]
            pitch_text = item
        else:
            pitch_text = item
        if pitch_text in ['-', '0', 'rest']:
            notes.append(note.Rest(quarterLength=dur))
        else:
            pitch_text = pitch_text.replace("'", "").replace(",", "")
            octave_shift = item.count("'") - item.count(",")
            base_octave = OCTAVE_BASE[voice] + octave_shift
            note_name = None
            if pitch_text.startswith('#') or pitch_text.startswith('b'):
                base = pitch_text[1]
                acc = pitch_text[0]
                if base not in JIANPU_PITCH:
                    continue
                if acc == '#':
                    note_name = JIANPU_PITCH[base] + '#'
                elif acc == 'b':
                    note_name = JIANPU_PITCH[base] + '-'
            else:
                base = pitch_text
                if base not in JIANPU_PITCH:
                    continue
                note_name = JIANPU_PITCH[base]
            n = note.Note(note_name + str(base_octave))
            n.quarterLength = dur
            notes.append(n)
    return notes

def build_score(part_data):
    score = stream.Score()
    for voice in VOICE_ORDER:
        part = stream.Part()
        part.id = voice
        current_ts = '4/4'
        current_tempo = 90
        part.append(key.Key('C'))
        part.append(meter.TimeSignature(current_ts))
        part.append(tempo.MetronomeMark(number=current_tempo))
        for entry in part_data[voice]:
            if isinstance(entry, str):
                if entry.startswith('# time:'):
                    current_ts = entry.split(':')[1].strip()
                    part.append(meter.TimeSignature(current_ts))
                elif entry.startswith('# tempo:'):
                    current_tempo = int(entry.split(':')[1].strip())
                    part.append(tempo.MetronomeMark(number=current_tempo))
            else:
                for n in entry:
                    part.append(n)
        score.append(part)
    return score

def process_folder(folder_path):
    part_data = {}
    for voice in VOICE_ORDER:
        file_path = os.path.join(folder_path, f"{voice}.txt")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"缺少文件：{voice}.txt")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        part_data[voice] = []
        for line in lines:
            if line.startswith("# time:") or line.startswith("# tempo:"):
                part_data[voice].append(line.strip())
            else:
                notes = parse_jianpu_line(line, voice)
                if notes:
                    part_data[voice].append(notes)
    # 写入 musicxml
    score = build_score(part_data)
    folder_name = os.path.basename(folder_path)
    output_file = os.path.join(folder_path, f"{folder_name}.musicxml")
    score.write('musicxml', fp=output_file)
    # 写入每个声部 midi
    for voice in VOICE_ORDER:
        part = stream.Part()
        part.id = voice
        current_ts = '4/4'
        current_tempo = 90
        part.append(meter.TimeSignature(current_ts))
        part.append(tempo.MetronomeMark(number=current_tempo))
        for entry in part_data[voice]:
            if isinstance(entry, str):
                if entry.startswith('# time:'):
                    current_ts = entry.split(':')[1].strip()
                    part.append(meter.TimeSignature(current_ts))
                elif entry.startswith('# tempo:'):
                    current_tempo = int(entry.split(':')[1].strip())
                    part.append(tempo.MetronomeMark(number=current_tempo))
            else:
                for n in entry:
                    part.append(n)
        midi_fp = os.path.join(folder_path, f"{voice}.mid")
        mf = midi.translate.streamToMidiFile(part)
        mf.open(midi_fp, 'wb')
        mf.write()
        mf.close()

def launch_gui():
    root = tk.Tk()
    root.title("简谱转五线谱 & MIDI 工具")
    root.geometry("720x400")
    tk.Label(
          root,
          text=(
                "功能：将四声部简谱 txt 批量转换为 MusicXML 与 MIDI 文件"
                "支持节奏、节拍、附点、八度、升降、休止、# tempo: # time: 标记等"
                "支持 * 自定义节奏（如 1*0.5 表示八分音符，1*4 表示全音符）"
                "支持 / 分数节奏（如 1/2 表示八分音符，1/4 表示十六分音符）"
                "支持 t 连音（如 1t3 为三连音，2t6 为六连音）"
        ),
        font=("Arial", 11),
        wraplength=680,
        justify="left"
    ).pack(pady=10)

    tk.Label(root, text="选择歌曲总文件夹路径（包含多个子文件夹）：").pack()
    path_var = tk.StringVar()
    tk.Entry(root, textvariable=path_var, width=80).pack()
    def browse():
        path = filedialog.askdirectory()
        if path:
            path_var.set(path)
    tk.Button(root, text="浏览", command=browse).pack(pady=5)

    progress_var = tk.StringVar()
    tk.Label(root, textvariable=progress_var, fg="blue").pack(pady=5)

    def run():
        base_path = path_var.get()
        if not os.path.isdir(base_path):
            messagebox.showerror("错误", "路径无效")
            return
        folders = [os.path.join(base_path, f) for f in os.listdir(base_path)
                   if os.path.isdir(os.path.join(base_path, f)) and
                   all(os.path.exists(os.path.join(base_path, f, f"{v}.txt")) for v in VOICE_ORDER)]
        total = len(folders)
        success = 0
        for i, folder in enumerate(folders, 1):
            progress_var.set(f"正在处理：{i}/{total} → {os.path.basename(folder)}")
            root.update()
            try:
                process_folder(folder)
                success += 1
            except Exception as e:
                print(f"失败：{folder} → {e}")
        progress_var.set(f"完成！成功：{success}/{total}")
        messagebox.showinfo("处理完成", f"共处理 {total} 个文件夹，成功 {success} 个。")

    tk.Button(root, text="开始批量生成 MusicXML + MIDI", bg="lightblue", command=run).pack(pady=10)
    tk.Label(root, text="或单独选择一个子文件夹进行转换：").pack(pady=(10, 0))
    single_path_var = tk.StringVar()
    tk.Entry(root, textvariable=single_path_var, width=80).pack()
    def single_browse():
        path = filedialog.askdirectory()
        if path:
            single_path_var.set(path)
    tk.Button(root, text="选择子文件夹", command=single_browse).pack(pady=5)
    def single_run():
        folder = single_path_var.get()
        if not os.path.isdir(folder):
            messagebox.showerror("错误", "路径无效")
            return
        try:
            process_folder(folder)
            messagebox.showinfo("成功", f"已成功生成该文件夹的 MusicXML 与 MIDI 文件。")
        except Exception as e:
            messagebox.showerror("失败", str(e))
    tk.Button(root, text="生成当前子文件夹 MusicXML + MIDI", bg="lightgreen", command=single_run).pack(pady=10)

    root.mainloop()

if __name__ == '__main__':
    launch_gui()
