# 🎉 New Features Added!

## 1. 💡 Conversation Insights

Each thread summary now includes detailed conversation insights to help you quickly understand:

### What You Get:

**⚠️ Response Needed**
- Automatically detects if the last email contains questions or requests
- Tells you if YOU need to respond

**📋 Next Action**
- Clear recommendation on what to do next:
  - "Response required - question or request in last email"
  - "Waiting on external party"
  - "Follow up - no activity for X days"
  - "Monitor - no immediate action required"

**👤 Last Response From**
- Shows who sent the last email
- Helps you know whose turn it is

**⏳ Waiting On**
- Extracts information about who/what you're waiting for
- Pulls relevant snippets from emails

**💬 Recent Conversation Flow**
- Last 5 emails with date, sender, and preview
- Quick scan of "who said what"
- See the conversation at a glance

**🔑 Key Discussion Points**
- Automatically extracts important statements containing:
  - Decisions
  - Agreements
  - Confirmations
  - Issues/Problems
  - Solutions
  - Actions
  - Deadlines

### Example Output:

```markdown
## 💡 Conversation Insights

### ⚠️ Response Needed
**Next Action**: Response required - question or request in last email

**Last Response From**: John Smith

### Recent Conversation Flow

**2025-10-15 14:30** - John Smith
> Can you confirm the delivery date for the Munich shipment? We need to update our schedule...

**2025-10-14 09:15** - You
> The truck is scheduled to arrive tomorrow morning. I'll send the tracking details shortly...

**2025-10-13 16:45** - Maria Garcia
> There's a delay at customs. Documents are missing. Please provide the CMR copy...

### Key Discussion Points

- [Maria Garcia] There's a delay at customs due to missing documents
- [John Smith] Confirmed the delivery date needs to be updated in the system
- [You] Agreed to send tracking details by end of day
```

---

## 2. 📦 Auto-Archive for Old Threads

Threads older than **2 months** (60 days) are automatically moved to an **Archive** folder instead of the main Threads folder.

### How It Works:

1. **Automatic Detection**: System checks the date of the last email in each thread
2. **Smart Organization**: 
   - **Recent threads** (< 2 months) → `Inbox/Threads/[thread_name]`
   - **Old threads** (> 2 months) → `Inbox/Archive/[thread_name]`
3. **Same Processing**: Archived threads still get full summaries, timelines, and insights
4. **Clean Inbox**: Keeps your active Threads folder focused on current work

### Configuration:

Edit `config.py` to change the threshold:

```python
ARCHIVE_THRESHOLD_DAYS = 60  # Default: 2 months
# Change to 30 for 1 month, 90 for 3 months, etc.
```

### In Outlook:

```
Inbox/
├── Threads/                    ← Active threads (< 2 months)
│   ├── 2025-10-15_Transport_Munich_abc123/
│   ├── 2025-10-10_Customs_Issue_xyz789/
│   └── ...
└── Archive/                    ← Old threads (> 2 months)
    ├── 2025-08-01_Delivery_Prague_def456/
    ├── 2025-07-20_Quality_Issue_ghi789/
    └── ...
```

---

## 3. 🔗 Git Integration

Repository synced with GitHub: **qaaph-zyld/outlook_threads**

### Commands:

```bash
# Pull latest changes
git pull

# Make changes, then commit
git add .
git commit -m "Your message"
git push

# Check status
git status
```

---

## 📊 Enhanced Thread Summary Example

Your thread summaries now look like this:

```markdown
# 2025-10-14 - Loading Adient Loznica (MSAN) - week 42/2025

## Thread Information

- **Emails**: 7
- **Participants**: 4
- **Date Range**: 2025-10-14 to 2025-10-16
- **Duration**: 2 days
- **Attachments**: 0

**Flags**: 🚚 TRANSPORT

## Executive Summary

Email thread 'Loading Adient Loznica (MSAN) - week 42/2025' with 7 emails over 2 days involving 4 participants.

## Current Status

Active today

## 💡 Conversation Insights

**Next Action**: Response required - question or request in last email

**Last Response From**: Transport Coordinator

### Recent Conversation Flow

**2025-10-16 15:30** - Transport Coordinator
> Please confirm if the loading dock will be available tomorrow morning at 8 AM...

**2025-10-16 10:15** - Warehouse Manager
> We have a delay with the previous shipment. Loading dock might not be ready until 10 AM...

**2025-10-15 14:00** - You
> Confirmed the truck for tomorrow. Driver will arrive at scheduled time...

### Key Discussion Points

- [Warehouse Manager] There's a delay with the previous shipment affecting dock availability
- [Transport Coordinator] Confirmed loading dock availability is critical for schedule
- [You] Agreed to coordinate with driver for potential time adjustment

## Key Events

- [2025-10-14 09:00] Thread started by Logistics Team: Loading schedule for week 42
- [2025-10-16 15:30] Latest update from Transport Coordinator

## Stakeholders

- Transport Coordinator (3 emails)
- You (2 emails)
- Warehouse Manager (1 email)
- Logistics Team (1 email)

## Action Items

- [ ] Confirm loading dock availability for tomorrow 8 AM
- [ ] Coordinate with driver if time adjustment needed
- [ ] Update transport schedule in system

---
*Summary generated using rule_based method*
```

---

## 🚀 How to Use

### Run the Application:

```powershell
python main.py
```

### When Prompted:

1. **Exclude folders**: Type `Customs` or leave empty
2. **Continue**: Type `y`

### What Happens:

1. ✅ Scans inbox for threads (3+ emails)
2. ✅ Checks each thread's age
3. ✅ Moves recent threads to `Threads/` folder
4. ✅ Moves old threads (>2 months) to `Archive/` folder
5. ✅ Generates summaries with conversation insights
6. ✅ Creates timelines
7. ✅ Exports to Excel

### Check Results:

- **Summaries**: `output/threads/[thread_name]/thread_summary.md`
- **Excel**: `output/thread_summary.xlsx`
- **Outlook**: Check `Inbox/Threads/` and `Inbox/Archive/` folders

---

## 💡 Use Cases

### 1. Quick Triage
Open summary → Check "Conversation Insights" → See if response needed → Take action

### 2. Handoff to Colleague
Share summary → They see conversation flow → Know exactly what's happening → Can respond intelligently

### 3. Follow-up Management
Check "Next Action" → Know what to do → Set reminders for waiting items

### 4. Archive Management
Old threads automatically archived → Clean active folder → Still searchable in Archive

### 5. Status Updates
Check "Last Response From" → Know whose turn it is → Follow up if needed

---

## 🎯 Benefits

✅ **Save Time**: No more reading entire threads to understand context
✅ **Never Miss**: Automatic detection of questions/requests needing response
✅ **Stay Organized**: Auto-archive keeps active threads visible
✅ **Better Handoffs**: Complete context in one document
✅ **Smarter Decisions**: Key discussion points extracted automatically

---

## 🔧 Configuration

Edit `config.py`:

```python
# Archive threshold (days)
ARCHIVE_THRESHOLD_DAYS = 60  # 2 months

# Thread minimum
THREAD_MIN_EMAILS = 3  # Minimum emails to consider as thread

# Keywords for detection
KEYWORDS_URGENT = ["urgent", "asap", "emergency", "critical", "immediate"]
KEYWORDS_DELAY = ["delay", "delayed", "postponed", "late", "waiting"]
KEYWORDS_TRANSPORT = ["truck", "driver", "transport", "delivery", "shipment"]
KEYWORDS_CUSTOMS = ["customs", "carinska", "border", "clearance"]
```

---

## 📝 Notes

- **AI Summarization**: Currently using rule-based (HuggingFace had Keras compatibility issue)
- **Performance**: ~1 email/second scanning, ~2-3 seconds per summary
- **Privacy**: All processing local, no external APIs
- **Git**: Synced with https://github.com/qaaph-zyld/outlook_threads

---

**Enjoy your enhanced thread management! 🎉**
