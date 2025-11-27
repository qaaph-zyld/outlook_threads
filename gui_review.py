"""
GUI Review Mode using Tkinter
Shows threads requiring attention and allows actions:
- Create draft reply (saved to Outlook Drafts)
- Flag for follow-up in Outlook
- Open summary Markdown and thread folder
- Open all created drafts for review
"""
from __future__ import annotations
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from dateutil import parser

import config
from interactive_review import InteractiveReviewer
from feedback_store import get_feedback_store
from notifications import show_attention_toast
try:
    import ttkbootstrap as tb
except Exception:
    tb = None


class GUIReviewer:
    def __init__(self, outlook_manager):
        self.outlook_manager = outlook_manager
        self.reviewer = InteractiveReviewer(outlook_manager)
        self.threads: List[Dict] = []
        self.filtered_threads: List[Dict] = []
        self.selected_idx: int | None = None
        self.feedback_store = get_feedback_store()
        self._wizard_indices: List[int] = []
        self._wizard_pos: int = 0
        self._wizard_window: tk.Toplevel | None = None

        self.root = tb.Window(themename="flatly") if tb else tk.Tk()
        self.root.title("Thread Review | Transport Threads")
        self.root.geometry("1100x700")
        self.root.minsize(980, 640)

        self._build_ui()
        self._load_threads_async()

    # -------------------- UI BUILD --------------------
    def _build_ui(self):
        # Top controls
        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(side=tk.TOP, fill=tk.X)

        self.search_var = tk.StringVar()
        self.only_attention_var = tk.BooleanVar(value=True)
        self.only_recent_var = tk.BooleanVar(value=True)

        ttk.Label(top, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(6, 12))
        search_entry.bind('<Return>', lambda e: self._apply_filters())

        ttk.Checkbutton(top, text="Only requiring attention", variable=self.only_attention_var,
                        command=self._apply_filters).pack(side=tk.LEFT)
        ttk.Checkbutton(top, text="Only recent activity", variable=self.only_recent_var,
                        command=self._apply_filters).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(top, text="Refresh", command=self._load_threads_async).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(top, text="Open Drafts", command=self._open_drafts).pack(side=tk.LEFT, padx=(6, 0))

        # Main split
        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # Left: thread list
        left = ttk.Frame(body, padding=(10, 0, 6, 10))
        left.grid(row=0, column=0, sticky="nsew")

        self.tree = ttk.Treeview(left, columns=("name", "priority", "emails", "flags"), show="headings",
                                 selectmode="browse", height=25)
        self.tree.heading("name", text="Thread")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("emails", text="Emails")
        self.tree.heading("flags", text="Flags")
        self.tree.column("name", width=420, stretch=True)
        self.tree.column("priority", width=90, stretch=False)
        self.tree.column("emails", width=70, stretch=False)
        self.tree.column("flags", width=220, stretch=True)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Right: details
        right = ttk.Frame(body, padding=(6, 0, 10, 10))
        right.grid(row=0, column=1, sticky="nsew")

        # Header area
        self.lbl_title = ttk.Label(right, text="Select a thread", font=("Segoe UI", 12, "bold"))
        self.lbl_title.pack(anchor="w", pady=(4, 6))

        meta_frame = ttk.Frame(right)
        meta_frame.pack(fill=tk.X)
        self.lbl_meta = ttk.Label(meta_frame, text="")
        self.lbl_meta.pack(anchor="w")

        # Summary text
        ttk.Label(right, text="Summary excerpt:").pack(anchor="w", pady=(10, 4))
        self.txt_summary = ScrolledText(right, height=10, wrap=tk.WORD)
        self.txt_summary.configure(font=("Segoe UI", 10))
        self.txt_summary.pack(fill=tk.BOTH, expand=False)

        # Suggested actions
        ttk.Label(right, text="Suggested actions:").pack(anchor="w", pady=(10, 4))
        self.list_actions = tk.Listbox(right, height=6)
        self.list_actions.pack(fill=tk.X)

        # Buttons
        btns = ttk.Frame(right)
        btns.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btns, text="Create Draft", command=self._create_draft).pack(side=tk.LEFT)
        ttk.Button(btns, text="Flag Follow-Up", command=self._flag_followup).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Summary", command=self._open_summary).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Folder", command=self._open_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Timeline", command=self._open_timeline).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Open Dashboard", command=self._open_dashboard).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Feedback", command=self._open_feedback_survey).pack(side=tk.LEFT, padx=(8, 0))

        # Status bar
        self.status_var = tk.StringVar(value="Loading threads...")
        status = ttk.Label(self.root, textvariable=self.status_var, anchor="w")
        status.pack(side=tk.BOTTOM, fill=tk.X)

    # -------------------- DATA LOADING --------------------
    def _load_threads_async(self):
        def _worker():
            try:
                threads = self.reviewer._load_thread_summaries(config.THREADS_DIR)
                threads.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
                self.threads = threads
                self._apply_filters()
                self._set_status(f"Loaded {len(self.threads)} threads. Showing {len(self.filtered_threads)}")
                self.root.after(0, self._post_load_hooks)
            except Exception as e:
                self._set_status(f"Error loading threads: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def _apply_filters(self):
        term = self.search_var.get().strip().lower()
        only_attention = self.only_attention_var.get()
        only_recent = self.only_recent_var.get()

        def matches(t: Dict) -> bool:
            if only_attention and not t.get('requires_attention', False):
                return False
            if only_recent:
                md = t.get('metadata', {})
                end_date = md.get('end_date')
                try:
                    if isinstance(end_date, str):
                        end_date = parser.parse(end_date)
                    if end_date:
                        days_since = (datetime.now() - end_date.replace(tzinfo=None)).days
                        if days_since > config.ARCHIVE_THRESHOLD_DAYS:
                            return False
                except Exception:
                    pass
            if not term:
                return True
            name = t.get('name', '').lower()
            summary = t.get('summary_text', '').lower()
            return term in name or term in summary

        self.filtered_threads = [t for t in self.threads if matches(t)]
        self._reload_tree()

    def _reload_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, t in enumerate(self.filtered_threads):
            flags = []
            md = t.get('metadata', {})
            if md.get('is_urgent'): flags.append('URGENT')
            if md.get('has_delay'): flags.append('DELAY')
            if md.get('is_transport'): flags.append('TRANSPORT')
            if md.get('is_customs'): flags.append('CUSTOMS')
            flags_text = ' | '.join(flags)
            emails = md.get('email_count', 0)
            pr = t.get('priority_score', 0)
            name = t.get('name', '')
            self.tree.insert('', 'end', iid=str(idx), values=(name, pr, emails, flags_text))

    # -------------------- SELECTION + DETAILS --------------------
    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self.selected_idx = None
            return
        idx = int(sel[0])
        if idx >= len(self.filtered_threads):
            return
        self.selected_idx = idx
        t = self.filtered_threads[idx]

        name = t.get('name', 'Unknown')
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

        self.lbl_title.configure(text=f"{name}")
        self.lbl_meta.configure(text=f"Priority: {pr} | Emails: {emails} | Participants: {participants} | Duration: {duration} days | {flags_text}")

        # Summary excerpt
        excerpt = self._get_exec_summary_excerpt(t.get('summary_text', ''))
        self.txt_summary.delete('1.0', tk.END)
        self.txt_summary.insert('1.0', excerpt)

        # Actions
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
        # Fallback: first non-empty paragraph
        for ln in lines:
            s = ln.strip()
            if s:
                return s[:500]
        return ""

    # -------------------- ACTIONS --------------------
    def _get_selected_thread(self) -> Dict | None:
        if self.selected_idx is None:
            messagebox.showinfo("Select thread", "Please select a thread first.")
            return None
        if self.selected_idx >= len(self.filtered_threads):
            return None
        return self.filtered_threads[self.selected_idx]

    def _create_draft(self):
        t = self._get_selected_thread()
        if not t:
            return
        try:
            self.reviewer._create_draft(t)
            messagebox.showinfo("Draft created", "Draft saved to Outlook Drafts folder.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create draft: {e}")

    def _flag_followup(self):
        t = self._get_selected_thread()
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
        t = self._get_selected_thread()
        if not t:
            return
        folder: Path = t.get('folder')
        if not folder:
            return
        summary = folder / config.SUMMARY_FILE_NAME
        try:
            if summary.exists():
                os.startfile(str(summary))  # Windows
            else:
                messagebox.showinfo("No file", "Summary file not found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open summary: {e}")

    def _open_folder(self):
        t = self._get_selected_thread()
        if not t:
            return
        folder = t.get('folder')
        if not folder:
            messagebox.showinfo("No folder", "No local folder is recorded for this thread.")
            return
        folder_path = Path(folder)
        if not folder_path.exists():
            messagebox.showinfo("No folder", "Local folder for this thread was not found on disk.")
            return
        try:
            os.startfile(str(folder_path))  # Windows
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")

    def _open_timeline(self):
        t = self._get_selected_thread()
        if not t:
            return
        folder = t.get('folder')
        if not folder:
            messagebox.showinfo("No file", "No local folder is recorded for this thread.")
            return
        folder_path = Path(folder)
        try:
            base = config.TIMELINE_FILE_NAME
            path_svg = folder_path / f"{base}.svg"
            path_html = folder_path / f"{base}.html"
            path_png = folder_path / f"{base}.png"
            if path_svg.exists():
                target = path_svg
            elif path_html.exists():
                target = path_html
            elif path_png.exists():
                target = path_png
            else:
                messagebox.showinfo("No file", "Timeline file not found.")
                return
            os.startfile(str(target))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open timeline: {e}")

    def _open_dashboard(self):
        try:
            dashboard = config.OUTPUT_DIR / "dashboard.html"
            if dashboard.exists():
                os.startfile(str(dashboard))
            else:
                messagebox.showinfo("No file", "Dashboard file not found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open dashboard: {e}")

    def _open_drafts(self):
        if not self.reviewer.drafts_created:
            messagebox.showinfo("No drafts", "No drafts have been created in this session.")
            return
        opened = 0
        for d in self.reviewer.drafts_created:
            try:
                d.Display()
                opened += 1
            except Exception:
                pass
        messagebox.showinfo("Drafts opened", f"Opened {opened} draft(s) in Outlook.")

    def _open_feedback_survey(self):
        t = self._get_selected_thread()
        if not t:
            return

        win = tk.Toplevel(self.root)
        win.title("Thread Feedback")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Help improve prioritization by rating this thread.", font=("Segoe UI", 10, "bold")).pack(padx=10, pady=(10, 6), anchor="w")
        tk.Label(win, text=t.get('name', ''), wraplength=420, justify=tk.LEFT).pack(padx=10, pady=(0, 10), anchor="w")

        frame = ttk.Frame(win, padding=(10, 0))
        frame.pack(fill=tk.BOTH, expand=True)

        pr_var = tk.StringVar(value="about_right")
        hot_var = tk.StringVar(value="yes")
        sla_var = tk.StringVar(value="2h")

        box1 = ttk.Labelframe(frame, text="Priority judgment")
        box1.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(box1, text="Too low", value="too_low", variable=pr_var).pack(anchor="w")
        ttk.Radiobutton(box1, text="About right", value="about_right", variable=pr_var).pack(anchor="w")
        ttk.Radiobutton(box1, text="Too high", value="too_high", variable=pr_var).pack(anchor="w")

        box2 = ttk.Labelframe(frame, text="Was this actually a hot thread?")
        box2.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(box2, text="Yes", value="yes", variable=hot_var).pack(anchor="w")
        ttk.Radiobutton(box2, text="No", value="no", variable=hot_var).pack(anchor="w")

        box3 = ttk.Labelframe(frame, text="Expected response time for this thread")
        box3.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(box3, text="Within 1 hour", value="1h", variable=sla_var).pack(anchor="w")
        ttk.Radiobutton(box3, text="Within 2 hours", value="2h", variable=sla_var).pack(anchor="w")
        ttk.Radiobutton(box3, text="Same day", value="same_day", variable=sla_var).pack(anchor="w")
        ttk.Radiobutton(box3, text="No strict SLA", value="none", variable=sla_var).pack(anchor="w")

        ttk.Label(frame, text="Optional comment:").pack(anchor="w", pady=(4, 2))
        txt_comment = ScrolledText(frame, height=4, wrap=tk.WORD)
        txt_comment.pack(fill=tk.X)

        btns = ttk.Frame(win)
        btns.pack(fill=tk.X, pady=(10, 10))

        def _save():
            answers = {
                "feedback_priority_judgment": pr_var.get(),
                "feedback_hot_thread": hot_var.get(),
                "feedback_expected_response": sla_var.get(),
                "feedback_comment": txt_comment.get("1.0", tk.END).strip(),
            }
            try:
                self.feedback_store.record_feedback(t, answers)
                self._set_status("Feedback saved.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save feedback: {e}")
            win.destroy()

        ttk.Button(btns, text="Save", command=_save).pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.RIGHT)

    # -------------------- WIZARD / POST-LOAD --------------------

    def _post_load_hooks(self):
        hot: List[int] = []
        for idx, t in enumerate(self.filtered_threads):
            if t.get('requires_attention', False) and t.get('priority_score', 0) >= 60:
                hot.append(idx)
        self._wizard_indices = hot
        self._wizard_pos = 0

        if hot:
            try:
                show_attention_toast(
                    "Transport Threads",
                    f"{len(hot)} high-priority threads need attention.",
                )
            except Exception:
                pass
            self._show_wizard_prompt(len(hot))

    def _show_wizard_prompt(self, count: int):
        if self._wizard_window is not None:
            try:
                self._wizard_window.destroy()
            except Exception:
                pass
        win = tk.Toplevel(self.root)
        self._wizard_window = win
        win.title("Hot Threads Review")
        win.transient(self.root)

        tk.Label(win, text=f"{count} hot threads detected.", font=("Segoe UI", 11, "bold")).pack(padx=10, pady=(10, 4))
        tk.Label(win, text="Click Next to step through them one by one, or Close to skip.").pack(padx=10, pady=(0, 10))

        btns = ttk.Frame(win)
        btns.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btns, text="Next", command=self._wizard_next).pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(btns, text="Close", command=win.destroy).pack(side=tk.RIGHT)

    def _wizard_next(self):
        if not self._wizard_indices or self._wizard_pos >= len(self._wizard_indices):
            if self._wizard_window is not None:
                try:
                    self._wizard_window.destroy()
                except Exception:
                    pass
            return
        idx = self._wizard_indices[self._wizard_pos]
        self._wizard_pos += 1
        iid = str(idx)
        try:
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self._on_select()
        except Exception:
            pass

    # -------------------- UTIL --------------------
    def _set_status(self, text: str):
        self.status_var.set(text)

    def run(self):
        self.root.mainloop()


def start_gui_review(outlook_manager):
    gui = GUIReviewer(outlook_manager)
    gui.run()
