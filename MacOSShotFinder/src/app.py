from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from models import IndexData
from pipeline import build_index, search
from video_analysis import sec_to_timecode


class ShotFinderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MacOS Shot Finder")
        self.root.geometry("1080x700")

        self.project_dir: Path | None = None
        self.index_data: IndexData | None = None
        self.thumb_cache = {}

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top, text="选择视频并建立索引", command=self.pick_video).pack(side=tk.LEFT)
        ttk.Button(top, text="打开已有项目", command=self.open_project).pack(side=tk.LEFT, padx=8)

        self.query_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.query_var, width=60)
        entry.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        entry.bind("<Return>", lambda _e: self.on_search())

        ttk.Button(top, text="搜索", command=self.on_search).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(self.root, textvariable=self.status_var).pack(anchor="w", padx=12)

        self.canvas = tk.Canvas(self.root)
        self.scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.container = ttk.Frame(self.canvas)
        self.container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.container, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def pick_video(self):
        video = filedialog.askopenfilename(title="选择视频文件")
        if not video:
            return
        project = filedialog.askdirectory(title="选择项目输出目录")
        if not project:
            return

        self.project_dir = Path(project)
        self.status_var.set("正在建立索引，请稍候…")

        def worker():
            try:
                data = build_index(Path(video), self.project_dir)
                self.index_data = data
                self.root.after(0, lambda: self.status_var.set(f"索引完成：{len(data.shots)} 个镜头"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("索引失败", str(e)))
                self.root.after(0, lambda: self.status_var.set("索引失败"))

        threading.Thread(target=worker, daemon=True).start()

    def open_project(self):
        project = filedialog.askdirectory(title="选择项目目录")
        if not project:
            return
        try:
            self.project_dir = Path(project)
            self.index_data = IndexData.load(self.project_dir)
            self.status_var.set(f"已加载项目：{project}（{len(self.index_data.shots)} 个镜头）")
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    def on_search(self):
        if not self.index_data:
            messagebox.showwarning("提示", "请先建立索引或打开已有项目")
            return
        query = self.query_var.get().strip()
        if not query:
            return

        results = search(self.index_data, query, top_k=20)
        for w in self.container.winfo_children():
            w.destroy()

        if not results:
            ttk.Label(self.container, text="未找到结果").pack(anchor="w", padx=10, pady=10)
            return

        for row in results:
            shot = row["shot"]
            card = ttk.Frame(self.container, padding=8)
            card.pack(fill=tk.X, padx=8, pady=4)

            try:
                img = self._load_thumb(shot.thumbnail_path)
                ttk.Label(card, image=img).pack(side=tk.LEFT)
            except Exception:
                ttk.Label(card, text="[无缩略图]", width=20).pack(side=tk.LEFT)

            info = (
                f"score: {row['score']:.3f}\n"
                f"时间: {sec_to_timecode(shot.start_sec)} - {sec_to_timecode(shot.end_sec)}\n"
                f"标签: {', '.join(shot.tags)}\n"
                f"演员: {', '.join(shot.actors) if shot.actors else '(未识别)'}\n"
                f"特效: {', '.join(shot.effects) if shot.effects else '(无明显特效)'}\n"
                f"台词: {shot.transcript or '(无)'}"
            )
            ttk.Label(card, text=info, justify=tk.LEFT).pack(side=tk.LEFT, padx=10)

    def _load_thumb(self, path: str):
        if path in self.thumb_cache:
            return self.thumb_cache[path]
        img = Image.open(path).convert("RGB")
        img.thumbnail((220, 124))
        tk_img = ImageTk.PhotoImage(img)
        self.thumb_cache[path] = tk_img
        return tk_img


def main():
    root = tk.Tk()
    app = ShotFinderApp(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
