# Transport Thread Manager 🚚📧

**Automatically organize, analyze, and visualize email threads for transport coordination**

This tool helps transport coordinators manage complex email conversations by:
- Identifying email threads automatically
- Organizing them into dedicated folders
- Generating AI-powered summaries
- Creating visual timelines of events
- Tracking stakeholders and action items

---

## Features

### 🔍 **Automatic Thread Detection**
- Uses Outlook's native `ConversationID` to reliably identify threads
- Configurable minimum email count (default: 3+ emails)
- Scans your inbox and identifies ongoing conversations

### 📁 **Smart Organization**
- Creates a "Threads" folder in your Outlook inbox
- Each thread gets its own subfolder with a descriptive name
- Automatically moves all related emails to the thread folder

### 🤖 **AI-Powered Summaries**
- Generates executive summaries of each thread
- Extracts key events in chronological order
- Identifies stakeholders and their roles
- Lists action items and pending tasks
- Flags issues, delays, and urgent items
- Works with OpenAI API or falls back to rule-based analysis

### 📊 **Timeline Visualizations**
- Creates visual timelines showing email flow
- Color-coded by sender
- Interactive HTML timelines (with Plotly)
- Static PNG charts (with Matplotlib)
- Gantt-style charts showing conversation flow

### 📋 **Comprehensive Reports**
- Individual Markdown summaries for each thread
- Excel spreadsheet with all thread metadata
- Text-based summary report
- Flags for urgent, delayed, transport, and customs threads

---

## Installation

### 1. Prerequisites
- **Python 3.8+**
- **Microsoft Outlook** (desktop application, must be logged in)
- **Windows OS** (required for `win32com`)

### 2. Install Dependencies

```bash
cd Outlook_automation_AI
pip install -r requirements.txt
```

### 3. Optional: Configure OpenAI (for AI summaries)

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-api-key-here
```

**Without OpenAI:** The system will use rule-based summarization (still effective!)

---

## Usage

### Quick Start

Run the application:

```bash
python main.py
```

You'll see a menu:

```
Options:
1. Scan and Process Threads (move emails, create summaries)
2. Scan Only (analyze without moving)
3. Custom Configuration
```

**Option 1** (Recommended for first use):
- Scans inbox for threads with 3+ emails
- Moves them to the "Threads" folder
- Generates summaries and timelines

**Option 2** (Preview mode):
- Analyzes threads without moving emails
- Good for testing before committing

**Option 3** (Advanced):
- Customize minimum email count
- Choose whether to move emails

### Configuration

Edit `config.py` to customize:

```python
# Thread Detection
THREAD_MIN_EMAILS = 3  # Minimum emails to consider as thread

# AI Settings
OPENAI_MODEL = "gpt-4o-mini"  # Cost-effective model
USE_LOCAL_AI = False  # Set True to skip OpenAI

# Keywords for Detection
KEYWORDS_URGENT = ["urgent", "asap", "emergency"]
KEYWORDS_DELAY = ["delay", "delayed", "late"]
KEYWORDS_TRANSPORT = ["truck", "driver", "delivery"]
```

---

## Output Structure

After processing, you'll find:

```
Outlook_automation_AI/
├── output/
│   ├── threads/
│   │   ├── 2024-01-15_Transport_to_Germany_a1b2c3d4/
│   │   │   ├── thread_summary.md          # Human-readable summary
│   │   │   ├── thread_metadata.json       # Structured data
│   │   │   ├── timeline.png               # Visual timeline
│   │   │   └── timeline.html              # Interactive timeline
│   │   └── [other threads...]
│   ├── thread_summary.xlsx                # Excel with all threads
│   └── threads_report.txt                 # Text summary
│   └── logs/
│       └── thread_manager.log             # Detailed logs
```

### Outlook Structure

```
Inbox/
└── Threads/                               # Created automatically
    ├── 2024-01-15_Transport_to_Germany_a1b2c3d4/
    │   └── [all emails in this thread]
    ├── 2024-01-20_Customs_clearance_xyz123/
    │   └── [all emails in this thread]
    └── [other thread folders...]
```

---

## Understanding Your Summaries

### Thread Summary (Markdown file)

Each thread gets a summary with:

- **Thread Information**: Email count, participants, date range
- **Flags**: 🔴 URGENT | ⏰ DELAY | 🚚 TRANSPORT | 📋 CUSTOMS
- **Executive Summary**: 2-3 sentence overview
- **Current Status**: What's happening now
- **Key Events**: Chronological timeline
- **Stakeholders**: Who's involved and their participation
- **Action Items**: Checkbox list of things to do
- **Issues & Risks**: Problems that need attention

### Timeline Visualization

- **PNG version**: Static image, great for presentations
- **HTML version**: Interactive, hover for details, zoom/pan
- Each email shown as a point on timeline
- Color-coded by sender
- Connecting lines show conversation flow

---

## Use Cases for Transport Coordinators

### 1. **Quick Status Check**
Open thread summary to instantly understand:
- Where is the shipment?
- Who's involved?
- What's the latest update?
- Are there any issues?

### 2. **Handoff to Colleague**
Share the summary and timeline when:
- Going on vacation
- Delegating a transport
- Bringing someone up to speed

### 3. **Management Reports**
Use Excel export for:
- Weekly status reports
- Identifying bottlenecks
- Tracking urgent items
- Measuring response times

### 4. **Issue Escalation**
Timeline visualization helps:
- Show when delays occurred
- Identify communication gaps
- Document timeline for disputes

### 5. **Knowledge Base**
Archive thread summaries for:
- Learning from past issues
- Training new coordinators
- Reference for similar situations

---

## How It Works

### Thread Detection
1. Connects to Outlook using `win32com`
2. Scans inbox emails
3. Groups by `ConversationID` (Outlook's native threading)
4. Filters to threads with 3+ emails

### AI Summarization (with OpenAI)
1. Prepares thread content (subjects + bodies)
2. Sends to OpenAI with specialized prompt
3. Extracts structured information:
   - Executive summary
   - Key events with timestamps
   - Stakeholders and roles
   - Action items
   - Current status
   - Issues/risks

### Rule-Based Summarization (fallback)
1. Analyzes email patterns
2. Extracts events using keyword detection
3. Identifies stakeholders by participation
4. Flags urgent/delay keywords
5. Generates structured summary

### Timeline Generation
1. Sorts emails chronologically
2. Extracts sender, subject, timestamp
3. Creates visual representation:
   - Matplotlib: Static PNG
   - Plotly: Interactive HTML
4. Color-codes by participant

---

## Advanced Usage

### Custom Keyword Detection

Edit `config.py` to add domain-specific keywords:

```python
KEYWORDS_TRANSPORT = [
    "truck", "driver", "transport", "delivery", 
    "FTL", "LTL", "pallets", "loading dock"
]

KEYWORDS_CUSTOMS = [
    "customs", "border", "clearance",
    "T1", "CMR", "carinska"
]
```

### Batch Processing

Process multiple inboxes or folders:

```python
from main import TransportThreadManager

manager = TransportThreadManager()

# Process specific folder
import win32com.client
outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
custom_folder = namespace.GetDefaultFolder(6).Folders["MyFolder"]

threads = manager.outlook_manager.identify_threads(folder=custom_folder)
# Process threads...
```

### Export to Other Formats

```python
# After running main.py, convert summaries
import json
from pathlib import Path

for thread_dir in Path("output/threads").iterdir():
    metadata_file = thread_dir / "thread_metadata.json"
    with open(metadata_file) as f:
        data = json.load(f)
        # Export to your system (database, API, etc.)
```

---

## Troubleshooting

### "No threads found"
- Check `THREAD_MIN_EMAILS` in config (try lowering to 2)
- Verify you have email conversations in inbox
- Run Option 2 (Scan Only) to see what's detected

### "OpenAI API error"
- Check `.env` file has correct API key
- Verify you have API credits
- System will automatically fall back to rule-based

### "Permission denied" creating folders
- Ensure Outlook is running and you're logged in
- Try running as Administrator
- Check Outlook isn't in offline mode

### Visualization not working
- Install missing libraries: `pip install matplotlib plotly`
- Check logs for specific error
- System will fall back to text timeline

### Emails not moving
- Verify you selected Option 1 (not Option 2)
- Check Outlook isn't blocking automation
- Review logs for specific errors

---

## Roadmap & Improvements

### Potential Enhancements
- [ ] Integration with calendar for deadline tracking
- [ ] Email templates for common responses
- [ ] Priority scoring algorithm
- [ ] Multi-language support (Croatian, German, etc.)
- [ ] Integration with transport management systems
- [ ] Automatic notification for urgent threads
- [ ] Dashboard web interface
- [ ] Mobile app for viewing summaries

### Ideas from Original Concept
✅ Thread identification
✅ Folder organization
✅ AI summarization
✅ Timeline visualization
🔄 Integration with existing customs automation
⏳ Real-time monitoring
⏳ Predictive analysis (delay prediction)

---

## Technical Architecture

### Modules

1. **outlook_thread_manager.py**: Outlook integration, thread detection, folder management
2. **thread_summarizer.py**: AI and rule-based summarization
3. **timeline_generator.py**: Visual timeline creation
4. **config.py**: Configuration and settings
5. **main.py**: Orchestration and CLI

### Dependencies

- **pywin32**: Outlook COM automation
- **pandas**: Data manipulation and Excel export
- **openpyxl**: Excel file handling
- **matplotlib**: Static chart generation
- **plotly**: Interactive visualizations
- **openai**: AI summarization (optional)
- **python-dotenv**: Environment configuration

---

## Security & Privacy

- **No data leaves your machine** (except OpenAI API calls if enabled)
- Email content sent to OpenAI is limited to 8000 chars per thread
- API key stored in `.env` file (add to `.gitignore`)
- All outputs stored locally in `output/` folder
- No cloud storage or external databases

---

## Contributing

This tool was built to solve real transport coordination challenges. 

**Have ideas?** Edit the code and customize for your workflow!

**Found a bug?** Check the logs and add error handling.

**Want to share?** Document your improvements for others.

---

## License

Internal tool for Adient transport coordination. Modify as needed.

---

## Support

For issues or questions:
1. Check logs in `output/logs/thread_manager.log`
2. Review this README
3. Examine code comments for technical details

---

**Built with ❤️ for transport coordinators who deserve better tools**
