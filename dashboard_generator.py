"""
Dashboard Generator - Creates HTML dashboard for thread overview
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Generates HTML dashboard with thread statistics and priorities"""
    
    def __init__(self):
        """Initialize dashboard generator"""
        self.threads_data = []
    
    def add_thread(self, summary: Dict, is_archived: bool = False):
        """Add a thread summary to the dashboard data"""
        try:
            metadata = summary.get('metadata', {})
            priority = summary.get('priority', {'score': 0, 'priority': 'Low', 'factors': []})
            insights = summary.get('conversation_insights', {})
            
            thread_data = {
                'name': summary.get('thread_name', 'Unknown'),
                'emails': metadata.get('email_count', 0),
                'participants': metadata.get('participant_count', 0),
                'duration_days': metadata.get('duration_days', 0),
                'start_date': str(metadata.get('start_date', '')),
                'end_date': str(metadata.get('end_date', '')),
                'priority_score': priority.get('score', 0),
                'priority_level': priority.get('priority', 'Low'),
                'response_needed': insights.get('response_needed', False),
                'next_action': insights.get('next_action', 'Unknown'),
                'is_urgent': metadata.get('is_urgent', False),
                'has_delay': metadata.get('has_delay', False),
                'is_transport': metadata.get('is_transport', False),
                'is_customs': metadata.get('is_customs', False),
                'is_archived': is_archived,
            }
            
            self.threads_data.append(thread_data)
            
        except Exception as e:
            logger.error(f"Error adding thread to dashboard: {e}")
    
    def generate_html(self, output_path: Path) -> bool:
        """Generate HTML dashboard"""
        try:
            # Filter out archived threads for dashboard display
            active_threads = [t for t in self.threads_data if not t.get('is_archived', False)]
            
            # Calculate statistics (only for active threads)
            total_threads = len(active_threads)
            if total_threads == 0:
                logger.warning("No active threads to generate dashboard")
                return False
            
            response_needed_count = sum(1 for t in active_threads if t['response_needed'])
            critical_count = sum(1 for t in active_threads if t['priority_level'] == 'Critical')
            high_count = sum(1 for t in active_threads if t['priority_level'] == 'High')
            urgent_count = sum(1 for t in active_threads if t['is_urgent'])
            delay_count = sum(1 for t in active_threads if t['has_delay'])
            
            # Sort threads by priority score
            sorted_threads = sorted(active_threads, key=lambda x: x['priority_score'], reverse=True)
            
            # Generate HTML
            html = self._generate_html_content(
                total_threads, response_needed_count, critical_count, 
                high_count, urgent_count, delay_count, sorted_threads
            )
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f"Dashboard generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return False
    
    def _generate_html_content(self, total, response_needed, critical, high, 
                                urgent, delay, threads) -> str:
        """Generate the HTML content"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transport Thread Manager - Dashboard</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/2.1.8/css/dataTables.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.datatables.net/2.1.8/js/dataTables.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .header .timestamp {{
            color: #666;
            font-size: 14px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .stat-card .number {{
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .stat-card .label {{
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card.critical .number {{ color: #dc3545; }}
        .stat-card.high .number {{ color: #fd7e14; }}
        .stat-card.response .number {{ color: #ffc107; }}
        .stat-card.total .number {{ color: #667eea; }}
        
        .threads-section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .threads-section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        
        .thread-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}
        
        .thread-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }}
        
        .thread-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .thread-name {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            flex: 1;
        }}
        
        .priority-badge {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .priority-critical {{
            background: #dc3545;
            color: white;
        }}
        
        .priority-high {{
            background: #fd7e14;
            color: white;
        }}
        
        .priority-medium {{
            background: #ffc107;
            color: #333;
        }}
        
        .priority-low {{
            background: #28a745;
            color: white;
        }}
        
        .thread-meta {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 10px;
            font-size: 14px;
            color: #666;
        }}
        
        .thread-meta span {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .thread-flags {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .flag {{
            padding: 3px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .flag-urgent {{ background: #ffe5e5; color: #dc3545; }}
        .flag-delay {{ background: #fff3cd; color: #856404; }}
        .flag-transport {{ background: #d1ecf1; color: #0c5460; }}
        .flag-customs {{ background: #e7e7ff; color: #383d9d; }}
        .flag-response {{ background: #ffebcc; color: #cc7a00; }}
        
        .next-action {{
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            font-size: 14px;
        }}
        
        .next-action strong {{
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚚 Transport Thread Manager Dashboard</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card total">
                <div class="number">{total}</div>
                <div class="label">Total Threads</div>
            </div>
            <div class="stat-card critical">
                <div class="number">{critical}</div>
                <div class="label">Critical Priority</div>
            </div>
            <div class="stat-card high">
                <div class="number">{high}</div>
                <div class="label">High Priority</div>
            </div>
            <div class="stat-card response">
                <div class="number">{response_needed}</div>
                <div class="label">Response Needed</div>
            </div>
            <div class="stat-card">
                <div class="number" style="color: #dc3545;">{urgent}</div>
                <div class="label">Urgent Flags</div>
            </div>
            <div class="stat-card">
                <div class="number" style="color: #ffc107;">{delay}</div>
                <div class="label">Delays Reported</div>
            </div>
        </div>
        
        <div class="threads-section">
            <h2>📋 All Threads (Sorted by Priority)</h2>
"""
        
        # Add thread cards
        for thread in threads:
            priority_class = f"priority-{thread['priority_level'].lower()}"
            
            flags_html = ""
            if thread['response_needed']:
                flags_html += '<span class="flag flag-response">⚠️ RESPONSE NEEDED</span>'
            if thread['is_urgent']:
                flags_html += '<span class="flag flag-urgent">🔴 URGENT</span>'
            if thread['has_delay']:
                flags_html += '<span class="flag flag-delay">⏰ DELAY</span>'
            if thread['is_transport']:
                flags_html += '<span class="flag flag-transport">🚚 TRANSPORT</span>'
            if thread['is_customs']:
                flags_html += '<span class="flag flag-customs">📋 CUSTOMS</span>'
            
            html += f"""
            <div class="thread-card">
                <div class="thread-header">
                    <div class="thread-name">{thread['name']}</div>
                    <span class="priority-badge {priority_class}">
                        {thread['priority_level']} ({thread['priority_score']})
                    </span>
                </div>
                <div class="thread-meta">
                    <span>📧 {thread['emails']} emails</span>
                    <span>👥 {thread['participants']} participants</span>
                    <span>📅 {thread['duration_days']} days</span>
                    <span>🕒 {thread['start_date']} to {thread['end_date']}</span>
                </div>
                <div class="thread-flags">
                    {flags_html}
                </div>
                <div class="next-action">
                    <strong>Next Action:</strong> {thread['next_action']}
                </div>
            </div>
"""
        
        html += """
        </div>
        
        <div class="threads-section" style="margin-top:20px;">
            <h2>📊 Table View (Sortable)</h2>
            <table id="threadsTable" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Priority</th>
                        <th>Level</th>
                        <th>Emails</th>
                        <th>Participants</th>
                        <th>Duration (days)</th>
                        <th>Flags</th>
                        <th>Next Action</th>
                        <th>Response Needed</th>
                        <th>Dates</th>
                    </tr>
                </thead>
                <tbody>
        """
        for thread in threads:
            flags = []
            if thread['response_needed']:
                flags.append('RESPONSE')
            if thread['is_urgent']:
                flags.append('URGENT')
            if thread['has_delay']:
                flags.append('DELAY')
            if thread['is_transport']:
                flags.append('TRANSPORT')
            if thread['is_customs']:
                flags.append('CUSTOMS')
            flags_text = ' | '.join(flags)
            dates = f"{thread['start_date']} → {thread['end_date']}"
            html += f"""
                <tr>
                    <td>{thread['name']}</td>
                    <td>{thread['priority_score']}</td>
                    <td>{thread['priority_level']}</td>
                    <td>{thread['emails']}</td>
                    <td>{thread['participants']}</td>
                    <td>{thread['duration_days']}</td>
                    <td>{flags_text}</td>
                    <td>{thread['next_action']}</td>
                    <td>{'Yes' if thread['response_needed'] else 'No'}</td>
                    <td>{dates}</td>
                </tr>
            """
        html += """
                </tbody>
            </table>
        </div>
    </div>
    <script>
    const dt = new DataTable('#threadsTable', {
        pageLength: 25,
        order: [[1, 'desc']],
        responsive: true
    });
    </script>
</body>
</html>
"""
        
        return html
