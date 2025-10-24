# Quick Start Guide - Transport Thread Manager

## 5-Minute Setup

### Step 1: Install Dependencies (2 minutes)

Open PowerShell in this folder and run:

```powershell
pip install -r requirements.txt
```

### Step 2: Optional - Add OpenAI API Key (1 minute)

**For AI-powered summaries** (recommended but not required):

1. Copy `.env.example` to `.env`
2. Get API key from https://platform.openai.com/api-keys
3. Edit `.env` and paste your key

**Without OpenAI**: The system works fine with rule-based summaries!

### Step 3: Run the Program (2 minutes)

```powershell
python main.py
```

Choose option **2** (Scan Only) first to preview without moving emails.

Then choose option **1** to process threads for real.

---

## What Happens?

1. **Connects to Outlook** - Uses your logged-in account
2. **Finds threads** - Emails with 3+ messages in conversation
3. **Creates "Threads" folder** - In your Inbox
4. **Organizes each thread** - Moves to subfolder with descriptive name
5. **Generates summaries** - AI or rule-based analysis
6. **Creates timelines** - Visual charts of email flow
7. **Exports to Excel** - All threads in spreadsheet

---

## Where to Find Results?

### In Outlook:
```
Inbox → Threads → [Your organized thread folders]
```

### On Your Computer:
```
Outlook_automation_AI/output/
├── threads/              ← Individual thread folders
├── thread_summary.xlsx   ← Excel with all threads
└── threads_report.txt    ← Text summary
```

---

## Example Use Case

**Before:**
- 50 emails about "Transport to Munich" scattered in inbox
- Hard to find latest update
- Don't remember who's involved

**After:**
- All 50 emails in "Threads/2024-01-15_Transport_to_Munich_abc123"
- Read `thread_summary.md` for instant overview
- See `timeline.png` for visual history
- Know current status and action items

---

## Customization

Edit `config.py`:

```python
THREAD_MIN_EMAILS = 3     # Lower to 2 for shorter threads
OPENAI_MODEL = "gpt-4o"   # Upgrade for better summaries
KEYWORDS_URGENT = [...]   # Add your company's terms
```

---

## Troubleshooting

**"No threads found"**
→ Lower `THREAD_MIN_EMAILS` in config.py

**"Module not found"**
→ Run `pip install -r requirements.txt` again

**"Outlook error"**
→ Make sure Outlook desktop app is open and logged in

**"OpenAI error"**
→ Check `.env` file or just skip - rule-based works too!

---

## Next Steps

1. ✅ Run with Option 2 (preview mode)
2. ✅ Check what threads it finds
3. ✅ Run with Option 1 (process threads)
4. ✅ Review output folder
5. ✅ Open Excel file to see all threads
6. ✅ Read individual summaries
7. ✅ Customize keywords in config.py

**Happy organizing! 📧🚚**
