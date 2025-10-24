from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from dateutil import parser

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
        self.view: List[Dict] = []
        self.index: int = 0
        self._state_path = config.OUTPUT_DIR / "review_state.json"
        self._state = self._load_state()
        self._done_set = {k for k, v in self._state.get('statuses', {}).items() if v.get('status') == 'done'}
        self._counters = {"done": len(self._done_set), "skipped": 0}

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
        self.pbar = ttk.Progressbar(top, mode="determinate", length=180)
        self.pbar.pack(side=tk.LEFT, padx=(10, 0))
        self.lbl_counts = ttk.Label(top, text="")
        self.lbl_counts.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(top, text="Open Dashboard", command=self._open_dashboard).pack(side=tk.RIGHT)
        ttk.Button(top, text="Previous", command=self._prev).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(top, text="Next", command=self._next).pack(side=tk.RIGHT, padx=(8, 12))

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        filters = ttk.Frame(body)
        filters.pack(fill=tk.X)
        self.only_attention_var = tk.BooleanVar(value=True)
        self.only_recent_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filters, text="Only attention", variable=self.only_attention_var, command=self._apply_filters).pack(side=tk.LEFT)
        ttk.Checkbutton(filters, text="Only recent", variable=self.only_recent_var, command=self._apply_filters).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(filters, text="Refresh", command=self._load_threads).pack(side=tk.LEFT, padx=(12, 0))

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
        ttk.Button(btns, text="Open Flow", command=self._open_flow).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Folder", command=self._open_folder).pack(side=tk.LEFT, padx=(8, 0))

        foot = ttk.Frame(self.root, padding=(10, 8))
        foot.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(foot, text="Skip", command=self._skip).pack(side=tk.RIGHT)
        ttk.Button(foot, text="Mark Done", command=self._done).pack(side=tk.RIGHT, padx=(8, 0))
        # Shortcuts
        self.root.bind('<Right>', lambda e: self._next())
        self.root.bind('<Left>', lambda e: self._prev())
        self.root.bind('n', lambda e: self._next())
        self.root.bind('p', lambda e: self._prev())
        self.root.bind('d', lambda e: self._done())
        self.root.bind('f', lambda e: self._flag_followup())
        self.root.bind('c', lambda e: self._create_draft())
        self.root.bind('s', lambda e: self._open_summary())
        self.root.bind('t', lambda e: self._open_timeline())
        self.root.bind('o', lambda e: self._open_folder())

    def _load_threads(self):
        threads = self.reviewer._load_thread_summaries(config.THREADS_DIR)
        threads = [t for t in threads if t.get('requires_attention', False)]
        threads = [t for t in threads if t.get('folder') and t['folder'].name not in self._done_set]
        threads.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        self.threads = threads
        self._apply_filters()
        self.index = 0
        self._render()

    def _apply_filters(self):
        only_attention = self.only_attention_var.get()
        only_recent = self.only_recent_var.get()

        def ok_recent(md: Dict) -> bool:
            try:
                end_date = md.get('end_date')
                if isinstance(end_date, str):
                    end_date = parser.parse(end_date)
                if end_date:
                    days = (datetime.now() - end_date.replace(tzinfo=None)).days
                    return days <= config.ARCHIVE_THRESHOLD_DAYS
            except Exception:
                pass
            return True

        view = []
        for t in self.threads:
            if only_attention and not t.get('requires_attention', False):
                continue
            if only_recent and not ok_recent(t.get('metadata', {})):
                continue
            view.append(t)
        self.view = view
        self.index = 0

    def _render(self):
        total = len(self.view)
        if total == 0:
            self.lbl_progress.configure(text="No threads require attention")
            self.lbl_title.configure(text="")
            self.lbl_meta.configure(text="")
            self.txt_summary.delete('1.0', tk.END)
            self.list_actions.delete(0, tk.END)
            return
        i = max(0, min(self.index, total - 1))
        t = self.view[i]
        self.lbl_progress.configure(text=f"Thread {i+1}/{total}")
        self._update_progressbar(i+1, total)
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
        self._update_counts(total)

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
        if not self.view:
            return None
        i = max(0, min(self.index, len(self.view) - 1))
        return self.view[i]

    def _create_draft(self):
        t = self._current()
        if not t:
            return
        try:
            self.reviewer._create_draft(t)
            self._mark_status(t, 'drafted')
            messagebox.showinfo("Draft created", "Draft saved to Outlook Drafts folder.")
            self._next()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create draft: {e}")

    def _flag_followup(self):
        t = self._current()
        if not t:
            return
        try:
            ok = self.outlook_manager.flag_thread_for_followup(t.get('name', ''))
            if ok:
                self._mark_status(t, 'flagged')
                messagebox.showinfo("Flagged", "Thread flagged for follow-up in Outlook.")
                self._next()
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

    def _open_flow(self):
        t = self._current()
        if not t:
            return
        folder: Path = t.get('folder')
        if not folder:
            return
        net = folder / 'flow_network.html'
        sankey = folder / 'flow_sankey.html'
        if net.exists():
            os.startfile(str(net))
        elif sankey.exists():
            os.startfile(str(sankey))
        else:
            messagebox.showinfo("Flow", "No flow graph found for this thread.")

    def _open_folder(self):
        t = self._current()
        if not t:
            return
        folder: Path = t.get('folder')
        if folder and folder.exists():
            os.startfile(str(folder))

    def _skip(self):
        if not self.view:
            return
        self._counters["skipped"] += 1
        self.index = min(self.index + 1, len(self.view) - 1)
        self._render()

    def _done(self):
        if not self.view:
            return
        i = max(0, min(self.index, len(self.view) - 1))
        t = self.view.pop(i)
        try:
            self._mark_status(t, 'done')
            self._counters["done"] += 1
        except Exception:
            pass
        try:
            folder = t.get('folder')
            if folder:
                self._done_set.add(folder.name)
                self._save_state()
        except Exception:
            pass
        if self.index >= len(self.view):
            self.index = max(0, len(self.view) - 1)
        self._render()

    def _next(self):
        if not self.view:
            return
        self.index = min(self.index + 1, len(self.view) - 1)
        self._render()

    def _prev(self):
        if not self.view:
            return
        self.index = max(self.index - 1, 0)
        self._render()

    def run(self):
        self.root.mainloop()

    def _load_state(self) -> dict:
        import json
        try:
            if self._state_path.exists():
                with open(self._state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if 'statuses' in data:
                            return data
                        # backward compatibility
                        done = set(data.get('done_folders', []))
                        return {"statuses": {k: {"status": "done", "timestamp": ""} for k in done}}
        except Exception:
            pass
        return {"statuses": {}}

    def _save_state(self):
        import json
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _mark_status(self, thread: Dict, status: str):
        folder = thread.get('folder')
        if not folder:
            return
        self._state.setdefault('statuses', {})[folder.name] = {
            "status": status,
            "timestamp": datetime.now().isoformat(timespec='seconds')
        }
        self._save_state()

    def _update_progressbar(self, position: int, total: int):
        try:
            val = 0 if total == 0 else int(position * 100 / total)
            self.pbar['value'] = val
        except Exception:
            pass

    def _update_counts(self, total: int):
        remaining = max(0, total - (self.index + 1))
        self.lbl_counts.configure(text=f"Done: {self._counters['done']} | Skipped: {self._counters['skipped']} | Remaining: {remaining}")

    def _open_dashboard(self):
        path = config.OUTPUT_DIR / 'dashboard.html'
        if path.exists():
            os.startfile(str(path))


def start_task_runner(outlook_manager):
    gui = TaskRunnerGUI(outlook_manager)
    gui.run()
