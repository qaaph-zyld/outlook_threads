"""
Modern Web Dashboard using FastAPI + TailwindCSS + Chart.js
Real-time email thread management dashboard with modern UI components

FREE OPEN SOURCE STACK:
- FastAPI: High-performance async web framework
- Jinja2: Template engine
- TailwindCSS (CDN): Modern utility-first CSS
- Chart.js (CDN): Interactive charts
- Alpine.js (CDN): Lightweight reactive framework
- HTMX (CDN): AJAX without JavaScript
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

import config

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Transport Thread Manager",
    description="AI-powered email thread management for transport coordination",
    version="2.0.0"
)

# Templates directory
TEMPLATES_DIR = config.BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


class DashboardDataLoader:
    """Load and process dashboard data from generated files"""
    
    @staticmethod
    def load_thread_summaries() -> List[Dict]:
        """Load all thread summaries from disk"""
        threads = []
        
        for thread_folder in config.THREADS_DIR.iterdir():
            if not thread_folder.is_dir():
                continue
            
            metadata_file = thread_folder / config.METADATA_FILE_NAME
            summary_file = thread_folder / config.SUMMARY_FILE_NAME
            triage_file = thread_folder / 'triage.json'
            
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check 60-day limit
                from dateutil import parser
                end_date = metadata.get('end_date')
                if end_date:
                    end_dt = parser.parse(end_date) if isinstance(end_date, str) else end_date
                    if end_dt:
                        days_old = (datetime.now() - end_dt.replace(tzinfo=None)).days
                        if days_old > 60:
                            continue
                
                # Load summary text
                summary_text = ""
                if summary_file.exists():
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_text = f.read()
                
                # Load triage data
                triage = {}
                if triage_file.exists():
                    with open(triage_file, 'r', encoding='utf-8') as f:
                        triage = json.load(f)

                # Calculate priority score: prefer value from summary markdown
                priority_score, priority_level = DashboardDataLoader._extract_priority(summary_text)
                if priority_score == 0:
                    # Fallback simple heuristic when priority isn't present in summary
                    if metadata.get('is_urgent'):
                        priority_score += 30
                    if metadata.get('has_delay'):
                        priority_score += 20
                    if metadata.get('email_count', 0) > 10:
                        priority_score += 10
                    if triage.get('escalate'):
                        priority_score += 25
                    if triage.get('due_soon'):
                        priority_score += 15

                threads.append({
                    'folder': str(thread_folder),
                    'folder_name': thread_folder.name,
                    'metadata': metadata,
                    'summary_text': summary_text,
                    'triage': triage,
                    'priority_score': priority_score
                })
                
            except Exception as e:
                logger.warning(f"Error loading thread {thread_folder}: {e}")
                continue
        
        # Sort by priority
        threads.sort(key=lambda x: x['priority_score'], reverse=True)
        return threads
    
    @staticmethod
    def get_dashboard_stats(threads: List[Dict]) -> Dict:
        """Calculate dashboard statistics"""
        total = len(threads)
        urgent = sum(1 for t in threads if t['metadata'].get('is_urgent'))
        delays = sum(1 for t in threads if t['metadata'].get('has_delay'))
        escalations = sum(1 for t in threads if t.get('triage', {}).get('escalate'))
        response_needed = sum(1 for t in threads if t.get('triage', {}).get('due_soon'))
        
        # Priority breakdown
        critical = sum(1 for t in threads if t['priority_score'] >= 70)
        high = sum(1 for t in threads if 50 <= t['priority_score'] < 70)
        medium = sum(1 for t in threads if 30 <= t['priority_score'] < 50)
        low = sum(1 for t in threads if t['priority_score'] < 30)
        
        return {
            'total_threads': total,
            'urgent_count': urgent,
            'delay_count': delays,
            'escalation_count': escalations,
            'response_needed': response_needed,
            'priority_breakdown': {
                'critical': critical,
                'high': high,
                'medium': medium,
                'low': low
            }
        }


    @staticmethod
    def _extract_priority(summary_text: str) -> tuple[int, str]:
        """Extract priority score/level from markdown summary, if present.

        Expects a line like: "## 🔴 Priority: Critical (100/100)".
        Returns (score, level) or (0, "Low") if not found.
        """
        try:
            import re

            for line in summary_text.splitlines():
                if "Priority:" not in line or "(" not in line:
                    continue
                m = re.search(r"Priority:\s*([A-Za-z]+)\s*\((\d+)/100\)", line)
                if m:
                    level = m.group(1)
                    score = int(m.group(2))
                    return score, level
        except Exception:
            pass
        return 0, "Low"


# Create the main HTML template
MAIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en" x-data="{ darkMode: localStorage.getItem('darkMode') === 'true' }" :class="{ 'dark': darkMode }">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transport Thread Manager - Dashboard</title>
    
    <!-- TailwindCSS via CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: {"50":"#eff6ff","100":"#dbeafe","200":"#bfdbfe","300":"#93c5fd","400":"#60a5fa","500":"#3b82f6","600":"#2563eb","700":"#1d4ed8","800":"#1e40af","900":"#1e3a8a","950":"#172554"}
                    }
                }
            }
        }
    </script>
    
    <!-- Alpine.js for reactivity -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    <!-- Chart.js for visualizations -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- HTMX for AJAX updates -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    
    <style>
        [x-cloak] { display: none !important; }
        .toast-enter { animation: slideIn 0.3s ease-out; }
        .toast-leave { animation: slideOut 0.3s ease-in; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
    </style>
</head>
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-200">
    <!-- Toast Notifications -->
    <div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2"></div>

    <!-- Navigation -->
    <nav class="bg-white dark:bg-gray-800 shadow-lg border-b border-gray-200 dark:border-gray-700">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-2xl mr-3">🚚</span>
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">Transport Thread Manager</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <span class="text-sm text-gray-500 dark:text-gray-400">
                        Last updated: {{ stats.last_updated if stats.last_updated else 'Just now' }}
                    </span>
                    <button 
                        @click="darkMode = !darkMode; localStorage.setItem('darkMode', darkMode)"
                        class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    >
                        <span x-show="!darkMode">🌙</span>
                        <span x-show="darkMode">☀️</span>
                    </button>
                    <button 
                        hx-get="/api/refresh"
                        hx-swap="none"
                        class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
                    >
                        <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                        Refresh
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Threads</p>
                        <p class="text-3xl font-bold text-gray-900 dark:text-white">{{ stats.total_threads }}</p>
                    </div>
                    <div class="p-3 bg-primary-100 dark:bg-primary-900 rounded-full">
                        <i data-lucide="mail" class="w-6 h-6 text-primary-600 dark:text-primary-400"></i>
                    </div>
                </div>
            </div>
            
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Urgent</p>
                        <p class="text-3xl font-bold text-red-600">{{ stats.urgent_count }}</p>
                    </div>
                    <div class="p-3 bg-red-100 dark:bg-red-900 rounded-full">
                        <i data-lucide="alert-circle" class="w-6 h-6 text-red-600 dark:text-red-400"></i>
                    </div>
                </div>
            </div>
            
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Delays</p>
                        <p class="text-3xl font-bold text-amber-600">{{ stats.delay_count }}</p>
                    </div>
                    <div class="p-3 bg-amber-100 dark:bg-amber-900 rounded-full">
                        <i data-lucide="clock" class="w-6 h-6 text-amber-600 dark:text-amber-400"></i>
                    </div>
                </div>
            </div>
            
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Escalations</p>
                        <p class="text-3xl font-bold text-purple-600">{{ stats.escalation_count }}</p>
                    </div>
                    <div class="p-3 bg-purple-100 dark:bg-purple-900 rounded-full">
                        <i data-lucide="trending-up" class="w-6 h-6 text-purple-600 dark:text-purple-400"></i>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- Priority Distribution Chart -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Priority Distribution</h3>
                <canvas id="priorityChart" height="200"></canvas>
            </div>
            
            <!-- Activity Timeline Chart -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Thread Activity (Last 7 Days)</h3>
                <canvas id="activityChart" height="200"></canvas>
            </div>
        </div>

        <!-- Filters -->
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 mb-6 border border-gray-200 dark:border-gray-700">
            <div class="flex flex-wrap gap-4 items-center">
                <div class="flex-1 min-w-[200px]">
                    <input 
                        type="text" 
                        id="searchInput"
                        placeholder="Search threads..." 
                        class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                        oninput="filterThreads()"
                    >
                </div>
                <div class="flex gap-2">
                    <button onclick="filterByPriority('all')" class="px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors filter-btn" data-filter="all">All</button>
                    <button onclick="filterByPriority('critical')" class="px-3 py-2 rounded-lg bg-red-100 text-red-700 hover:bg-red-200 transition-colors filter-btn" data-filter="critical">Critical</button>
                    <button onclick="filterByPriority('high')" class="px-3 py-2 rounded-lg bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors filter-btn" data-filter="high">High</button>
                    <button onclick="filterByPriority('urgent')" class="px-3 py-2 rounded-lg bg-red-100 text-red-700 hover:bg-red-200 transition-colors filter-btn" data-filter="urgent">Urgent Only</button>
                </div>
            </div>
        </div>

        <!-- Thread Cards -->
        <div id="threadList" class="space-y-4">
            {% for thread in threads %}
            <div 
                class="thread-card bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
                data-priority="{{ thread.priority_score }}"
                data-name="{{ thread.metadata.thread_name | lower }}"
                data-urgent="{{ 'true' if thread.metadata.is_urgent else 'false' }}"
            >
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                                {{ thread.metadata.thread_name[:80] }}{% if thread.metadata.thread_name|length > 80 %}...{% endif %}
                            </h3>
                            {% if thread.priority_score >= 70 %}
                            <span class="px-2 py-1 text-xs font-bold bg-red-600 text-white rounded-full">CRITICAL</span>
                            {% elif thread.priority_score >= 50 %}
                            <span class="px-2 py-1 text-xs font-bold bg-orange-500 text-white rounded-full">HIGH</span>
                            {% elif thread.priority_score >= 30 %}
                            <span class="px-2 py-1 text-xs font-bold bg-yellow-500 text-gray-900 rounded-full">MEDIUM</span>
                            {% else %}
                            <span class="px-2 py-1 text-xs font-bold bg-green-500 text-white rounded-full">LOW</span>
                            {% endif %}
                        </div>
                        
                        <div class="flex flex-wrap gap-2 mb-3">
                            {% if thread.metadata.is_urgent %}
                            <span class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">🔴 URGENT</span>
                            {% endif %}
                            {% if thread.metadata.has_delay %}
                            <span class="px-2 py-1 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">⏰ DELAY</span>
                            {% endif %}
                            {% if thread.metadata.is_transport %}
                            <span class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">🚚 TRANSPORT</span>
                            {% endif %}
                            {% if thread.metadata.is_customs %}
                            <span class="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded">📋 CUSTOMS</span>
                            {% endif %}
                            {% if thread.triage.escalate %}
                            <span class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">⚠️ ESCALATE</span>
                            {% endif %}
                        </div>
                        
                        <div class="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                            <span class="flex items-center gap-1">
                                <i data-lucide="mail" class="w-4 h-4"></i>
                                {{ thread.metadata.email_count }} emails
                            </span>
                            <span class="flex items-center gap-1">
                                <i data-lucide="users" class="w-4 h-4"></i>
                                {{ thread.metadata.participant_count }} participants
                            </span>
                            <span class="flex items-center gap-1">
                                <i data-lucide="calendar" class="w-4 h-4"></i>
                                {{ thread.metadata.duration_days }} days
                            </span>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-2 ml-4">
                        <a 
                            href="/thread/{{ thread.folder_name }}"
                            class="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm"
                        >
                            View Details
                        </a>
                    </div>
                </div>
                
                {% if thread.triage.suggested_next_step %}
                <div class="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border-l-4 border-primary-500">
                    <p class="text-sm text-gray-700 dark:text-gray-300">
                        <strong>Next Action:</strong> {{ thread.triage.suggested_next_step[:150] }}
                    </p>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        {% if not threads %}
        <div class="text-center py-12">
            <i data-lucide="inbox" class="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4"></i>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">No threads found</h3>
            <p class="text-gray-500 dark:text-gray-400">Run the thread processor to analyze your emails.</p>
        </div>
        {% endif %}
    </main>

    <!-- Footer -->
    <footer class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 py-4 mt-8">
        <div class="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500 dark:text-gray-400">
            Transport Thread Manager v2.0 | Built with FastAPI + TailwindCSS + Chart.js
        </div>
    </footer>

    <script>
        // Initialize Lucide icons
        lucide.createIcons();
        
        // Chart.js - Priority Distribution
        const priorityCtx = document.getElementById('priorityChart');
        if (priorityCtx) {
            new Chart(priorityCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Critical', 'High', 'Medium', 'Low'],
                    datasets: [{
                        data: [
                            {{ stats.priority_breakdown.critical }},
                            {{ stats.priority_breakdown.high }},
                            {{ stats.priority_breakdown.medium }},
                            {{ stats.priority_breakdown.low }}
                        ],
                        backgroundColor: ['#dc2626', '#f97316', '#eab308', '#22c55e'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                color: document.documentElement.classList.contains('dark') ? '#fff' : '#374151'
                            }
                        }
                    }
                }
            });
        }
        
        // Chart.js - Activity Timeline (placeholder data)
        const activityCtx = document.getElementById('activityChart');
        if (activityCtx) {
            const days = [];
            const values = [];
            for (let i = 6; i >= 0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                days.push(d.toLocaleDateString('en-US', { weekday: 'short' }));
                values.push(Math.floor(Math.random() * 10) + 1); // Placeholder
            }
            
            new Chart(activityCtx, {
                type: 'bar',
                data: {
                    labels: days,
                    datasets: [{
                        label: 'Emails',
                        data: values,
                        backgroundColor: '#3b82f6',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: document.documentElement.classList.contains('dark') ? '#9ca3af' : '#6b7280' }
                        },
                        x: {
                            ticks: { color: document.documentElement.classList.contains('dark') ? '#9ca3af' : '#6b7280' }
                        }
                    }
                }
            });
        }
        
        // Filter functions
        function filterThreads() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.thread-card').forEach(card => {
                const name = card.dataset.name || '';
                card.style.display = name.includes(searchTerm) ? 'block' : 'none';
            });
        }
        
        function filterByPriority(filter) {
            document.querySelectorAll('.thread-card').forEach(card => {
                const priority = parseInt(card.dataset.priority) || 0;
                const isUrgent = card.dataset.urgent === 'true';
                
                let show = true;
                if (filter === 'critical') show = priority >= 70;
                else if (filter === 'high') show = priority >= 50;
                else if (filter === 'urgent') show = isUrgent;
                
                card.style.display = show ? 'block' : 'none';
            });
            
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('ring-2', 'ring-primary-500');
                if (btn.dataset.filter === filter) {
                    btn.classList.add('ring-2', 'ring-primary-500');
                }
            });
        }
        
        // Toast notification
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500';
            toast.className = `toast-enter ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg`;
            toast.textContent = message;
            container.appendChild(toast);
            
            setTimeout(() => {
                toast.classList.remove('toast-enter');
                toast.classList.add('toast-leave');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
        
        // HTMX event handlers
        document.body.addEventListener('htmx:afterRequest', function(evt) {
            if (evt.detail.successful) {
                showToast('Data refreshed successfully', 'success');
            }
        });
    </script>
</body>
</html>'''


# Write template to file
def create_template():
    """Create the main template file"""
    template_file = TEMPLATES_DIR / "dashboard.html"
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(MAIN_TEMPLATE)
    logger.info(f"Dashboard template created: {template_file}")


# API Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    create_template()  # Ensure template exists
    
    threads = DashboardDataLoader.load_thread_summaries()
    stats = DashboardDataLoader.get_dashboard_stats(threads)
    stats['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "threads": threads,
        "stats": stats
    })


@app.get("/api/threads", response_class=JSONResponse)
async def get_threads():
    """API endpoint for thread data"""
    threads = DashboardDataLoader.load_thread_summaries()
    return {"threads": threads, "count": len(threads)}


@app.get("/api/stats", response_class=JSONResponse)
async def get_stats():
    """API endpoint for dashboard statistics"""
    threads = DashboardDataLoader.load_thread_summaries()
    stats = DashboardDataLoader.get_dashboard_stats(threads)
    return stats


@app.get("/api/refresh", response_class=JSONResponse)
async def refresh_data():
    """Refresh dashboard data"""
    threads = DashboardDataLoader.load_thread_summaries()
    stats = DashboardDataLoader.get_dashboard_stats(threads)
    return {"status": "refreshed", "thread_count": len(threads), "stats": stats}


@app.get("/thread/{folder_name}", response_class=HTMLResponse)
async def thread_detail(request: Request, folder_name: str):
    """Thread detail page"""
    thread_folder = config.THREADS_DIR / folder_name
    
    if not thread_folder.exists():
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Load thread data
    metadata_file = thread_folder / config.METADATA_FILE_NAME
    summary_file = thread_folder / config.SUMMARY_FILE_NAME
    
    metadata = {}
    summary_text = ""
    
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    
    if summary_file.exists():
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary_text = f.read()
    
    # Simple detail template
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{metadata.get('thread_name', 'Thread Detail')}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-8">
    <div class="max-w-4xl mx-auto">
        <a href="/" class="text-blue-600 hover:underline mb-4 block">← Back to Dashboard</a>
        <div class="bg-white rounded-xl shadow-sm p-6 mb-6">
            <h1 class="text-2xl font-bold mb-4">{metadata.get('thread_name', 'Unknown Thread')}</h1>
            <div class="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-6">
                <div><strong>Emails:</strong> {metadata.get('email_count', 0)}</div>
                <div><strong>Participants:</strong> {metadata.get('participant_count', 0)}</div>
                <div><strong>Duration:</strong> {metadata.get('duration_days', 0)} days</div>
                <div><strong>Attachments:</strong> {metadata.get('total_attachments', 0)}</div>
            </div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-6">
            <h2 class="text-xl font-semibold mb-4">Summary</h2>
            <div class="prose max-w-none">
                <pre class="whitespace-pre-wrap text-sm text-gray-700">{summary_text}</pre>
            </div>
        </div>
    </div>
</body>
</html>'''
    
    return HTMLResponse(content=html)


# V3 Dashboard with ApexCharts
@app.get("/v3", response_class=HTMLResponse)
async def dashboard_v3(request: Request):
    """Render the enhanced V3 dashboard with ApexCharts"""
    v3_template_path = TEMPLATES_DIR / "dashboard_v3.html"
    if not v3_template_path.exists():
        raise HTTPException(status_code=404, detail="V3 template not found")
    
    threads = DashboardDataLoader.load_thread_summaries()
    stats = DashboardDataLoader.get_dashboard_stats(threads)
    
    return templates.TemplateResponse(
        "dashboard_v3.html",
        {"request": request, "threads": threads, "stats": stats}
    )


# API endpoint for keywords (KeyBERT data)
@app.get("/api/keywords")
async def get_keywords():
    """Get aggregated keywords from all threads"""
    threads = DashboardDataLoader.load_thread_summaries()
    keywords = {}
    
    for thread in threads:
        metadata = thread.get('metadata', {})
        # Extract keywords from thread name and content
        name = metadata.get('thread_name', '').lower()
        for word in name.split():
            if len(word) > 3:
                keywords[word] = keywords.get(word, 0) + 1
    
    # Sort and return top keywords
    sorted_kw = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
    return {"keywords": [{"x": k, "y": v} for k, v in sorted_kw]}


# API endpoint for sentiment data
@app.get("/api/sentiment")
async def get_sentiment():
    """Get overall sentiment from thread analysis"""
    # This would be populated from actual NLP analysis
    return {"overall": 65, "positive": 40, "neutral": 45, "negative": 15}


# API endpoint for response times
@app.get("/api/response-times")
async def get_response_times():
    """Get response time distribution"""
    # This would be calculated from actual thread data
    return {
        "distribution": [
            {"range": "< 1h", "count": 5},
            {"range": "1-4h", "count": 12},
            {"range": "4-12h", "count": 8},
            {"range": "12-24h", "count": 3},
            {"range": "> 24h", "count": 2}
        ]
    }


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_update(message: dict):
    """Broadcast update to all connected clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass


def start_dashboard(host: str = "127.0.0.1", port: int = 8000):
    """Start the web dashboard"""
    print(f"\n{'='*60}")
    print("🚚 Transport Thread Manager - Web Dashboard")
    print(f"{'='*60}")
    print(f"\n  Open in browser: http://{host}:{port}")
    print(f"\n  Press Ctrl+C to stop\n")
    
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_dashboard()
