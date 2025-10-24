from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from typing import List, Dict

import config
from interactive_review import InteractiveReviewer
try:
    import ttkbootstrap as tb
except Exception:
    tb = None


class TaskRunnerGUI:
    def __init__(self, outlook_manager):
        self.outlook_manager = outlook_manager
        self.reviewer = InteractiveReviewer(outlook_manager)
        self.threads: List[Dict] = []
        self.index: int = 0
        self._state_path = config.OUTPUT_DIR / "review_state.json"
        self._done_set = self._load_state()

        self.root = tb.Window(themename="flatly") if tb else tk.Tk()
        self.root.title("Task Runner | Transport Threads")
        self.root.geometry("900x620")
        self.root.minsize(820, 560)

        self._build_ui()
        self._load_threads()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(side=tk.TOP, fill=tk.X)
        self.lbl_progress = ttk.Label(top, text="")
        self.lbl_progress.pack(side=tk.LEFT)
        ttk.Button(top, text="Previous", command=self._prev).pack(side=tk.RIGHT)
        ttk.Button(top, text="Next", command=self._next).pack(side=tk.RIGHT, padx=(8, 12))

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.lbl_title = ttk.Label(body, text="", font=("Segoe UI", 12, "bold"))
        self.lbl_title.pack(anchor="w", pady=(6, 4))

        self.lbl_meta = ttk.Label(body, text="")
        self.lbl_meta.pack(anchor="w")

        ttk.Label(body, text="Summary excerpt:").pack(anchor="w", pady=(10, 4))
        self.txt_summary = ScrolledText(body, height=10, wrap=tk.WORD)
        self.txt_summary.configure(font=("Segoe UI", 10))
        self.txt_summary.pack(fill=tk.BOTH, expand=False)

        ttk.Label(body, text="Suggested actions:").pack(anchor="w", pady=(10, 4))
        self.list_actions = tk.Listbox(body, height=5)
        self.list_actions.pack(fill=tk.X)

        btns = ttk.Frame(body)
        btns.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(btns, text="Create Draft", command=self._create_draft).pack(side=tk.LEFT)
        ttk.Button(btns, text="Flag Follow-Up", command=self._flag_followup).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Summary", command=self._open_summary).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Timeline", command=self._open_timeline).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Folder", command=self._open_folder).pack(side=tk.LEFT, padx=(8, 0))

        foot = ttk.Frame(self.root, padding=(10, 8))
        foot.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(foot, text="Skip", command=self._skip).pack(side=tk.RIGHT)
        ttk.Button(foot, text="Mark Done", command=self._done).pack(side=tk.RIGHT, padx=(8, 0))

    def _load_threads(self):
        threads = self.reviewer._load_thread_summaries(config.THREADS_DIR)
        threads = [t for t in threads if t.get('requires_attention', False)]
        threads = [t for t in threads if t.get('folder') and t['folder'].name not in self._done_set]
        threads.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        self.threads = threads
        self.index = 0
        self._render()

    def _render(self):
        total = len(self.threads)
        if total == 0:
            self.lbl_progress.configure(text="No threads require attention")
            self.lbl_title.configure(text="")
            self.lbl_meta.configure(text="")
            self.txt_summary.delete('1.0', tk.END)
            self.list_actions.delete(0, tk.END)
            return
        i = max(0, min(self.index, total - 1))
        t = self.threads[i]
        self.lbl_progress.configure(text=f"Thread {i+1}/{total}")
        name = t.get('name', '')
        pr = t.get('priority_score', 0)
        md = t.get('metadata', {})
        emails = md.get('email_count', 0)
        participants = md.get('participant_count', 0)
        duration = md.get('duration_days', 0)
        flags = []
        if md.get('is_urgent'): flags.append('URGENT')
        if md.get('has_delay'): flags.append('DELAY')
        if md.get('is_transport'): flags.append('TRANSPORT')
        if md.get('is_customs'): flags.append('CUSTOMS')
        flags_text = ' | '.join(flags)
        self.lbl_title.configure(text=name)
        self.lbl_meta.configure(text=f"Priority: {pr} | Emails: {emails} | Participants: {participants} | Duration: {duration} days | {flags_text}")
        excerpt = self._get_exec_summary_excerpt(t.get('summary_text', ''))
        self.txt_summary.delete('1.0', tk.END)
        self.txt_summary.insert('1.0', excerpt)
        actions = self.reviewer._suggest_actions(t)
        self.list_actions.delete(0, tk.END)
        for a in actions:
            self.list_actions.insert(tk.END, f"• {a}")

    def _get_exec_summary_excerpt(self, summary_text: str) -> str:
        if not summary_text:
            return "No summary available."
        lines = summary_text.split('\n')
        for i, line in enumerate(lines):
            if '## Executive Summary' in line and i + 2 < len(lines):
                return lines[i + 2].strip()
        for ln in lines:
            s = ln.strip()
            if s:
                return s[:500]
        return ""

    def _current(self) -> Dict | None:
        if not self.threads:
            return None
        i = max(0, min(self.index, len(self.threads) - 1))
        return self.threads[i]

    def _create_draft(self):
        t = self._current()
        if not t:
            return
        try:
            self.reviewer._create_draft(t)
            messagebox.showinfo("Draft created", "Draft saved to Outlook Drafts folder.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create draft: {e}")

    def _flag_followup(self):
        t = self._current()
        if not t:
            return
        try:
            ok = self.outlook_manager.flag_thread_for_followup(t.get('name', ''))
            if ok:
                messagebox.showinfo("Flagged", "Thread flagged for follow-up in Outlook.")
            else:
                messagebox.showwarning("Not flagged", "Could not flag the emails in this thread.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to flag thread: {e}")

    def _open_summary(self):
        t = self._current()
        if not t:
            return
        folder: Path = t.get('folder')
        if not folder:
            return
        path = folder / config.SUMMARY_FILE_NAME
        if path.exists():
            os.startfile(str(path))

    def _open_timeline(self):
        t = self._current()
        if not t:
            return
        folder: Path = t.get('folder')
        if not folder:
            return
        base = config.TIMELINE_FILE_NAME
        ext = ".html" if getattr(config, 'TIMELINE_OUTPUT_FORMAT', 'png') == 'html' else ".png"
        path_html = folder / f"{base}.html"
        path_png = folder / f"{base}.png"
        target = path_html if path_html.exists() else (path_png if path_png.exists() else folder / f"{base}{ext}")
        if target.exists():
            os.startfile(str(target))

    def _open_folder(self):
        t = self._current()
        if not t:
            return
        folder: Path = t.get('folder')
        if folder and folder.exists():
            os.startfile(str(folder))

    def _skip(self):
        if not self.threads:
            return
        self.index = min(self.index + 1, len(self.threads) - 1)
        self._render()

    def _done(self):
        if not self.threads:
            return
        i = max(0, min(self.index, len(self.threads) - 1))
        t = self.threads.pop(i)
        try:
            folder = t.get('folder')
            if folder:
                self._done_set.add(folder.name)
                self._save_state()
        except Exception:
            pass
        if self.index >= len(self.threads):
            self.index = max(0, len(self.threads) - 1)
        self._render()

    def _next(self):
        if not self.threads:
            return
        self.index = min(self.index + 1, len(self.threads) - 1)
        self._render()

    def _prev(self):
        if not self.threads:
            return
        self.index = max(self.index - 1, 0)
        self._render()

    def run(self):
        self.root.mainloop()

    def _load_state(self) -> set:
        import json
        try:
            if self._state_path.exists():
                with open(self._state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('done_folders', []))
        except Exception:
            pass
        return set()

    def _save_state(self):
        import json
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, 'w', encoding='utf-8') as f:
                json.dump({"done_folders": sorted(self._done_set)}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def start_task_runner(outlook_manager):
    gui = TaskRunnerGUI(outlook_manager)
    gui.run()
