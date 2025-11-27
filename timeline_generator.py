"""
Timeline Generator
Creates visual timelines of email thread events
"""
import logging
from typing import List, Dict
from datetime import datetime
import config

logger = logging.getLogger(__name__)

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available. Timeline visualization disabled.")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available. Interactive timeline disabled.")


class TimelineGenerator:
    """Generates timeline visualizations for email threads"""
    
    def __init__(self, use_interactive: bool = False):
        """
        Initialize timeline generator
        
        Args:
            use_interactive: Use Plotly for interactive timelines (if available)
        """
        self.use_interactive = use_interactive and PLOTLY_AVAILABLE
        self.use_static = MATPLOTLIB_AVAILABLE
    
    def generate_timeline(self, thread_emails: List[Dict], summary: Dict, output_path: str) -> bool:
        """
        Generate timeline visualization
        
        Args:
            thread_emails: List of email info dictionaries
            summary: Thread summary dictionary
            output_path: Path to save timeline (without extension)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_interactive:
                ok_html = self._generate_interactive_timeline(thread_emails, summary, output_path)
                if self.use_static:
                    try:
                        self._generate_static_timeline(thread_emails, summary, output_path)
                    except Exception as e:
                        logger.warning("Static timeline generation failed: %s", e)
                return ok_html
            elif self.use_static:
                return self._generate_static_timeline(thread_emails, summary, output_path)
            else:
                logger.warning("No visualization library available")
                return self._generate_text_timeline(thread_emails, summary, output_path)
                
        except Exception as e:
            logger.error(f"Error generating timeline: {e}")
            return False
    
    def _generate_static_timeline(self, thread_emails: List[Dict], summary: Dict, output_path: str) -> bool:
        """Generate static timeline using Matplotlib"""
        try:
            if not summary:
                logger.warning("No summary provided for timeline generation")
                return False
            
            # Sort emails by date
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            
            # Prepare data
            dates = [email['received_time'] for email in sorted_emails]
            senders = [email['sender'] for email in sorted_emails]
            subjects = [email['subject'][:50] + '...' if len(email['subject']) > 50 
                       else email['subject'] for email in sorted_emails]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Color code by sender
            unique_senders = list(set(senders))
            colors = plt.cm.Set3(range(len(unique_senders)))
            sender_colors = {sender: colors[i] for i, sender in enumerate(unique_senders)}
            
            # Plot events
            for i, (date, sender, subject) in enumerate(zip(dates, senders, subjects)):
                color = sender_colors[sender]
                
                # Plot point
                ax.scatter(date, i, c=[color], s=200, zorder=3, edgecolors='black', linewidth=1)
                
                # Add label
                label_text = f"{sender[:20]}\n{subject[:40]}"
                ax.text(date, i + 0.3, label_text, fontsize=8, 
                       ha='left', va='bottom', wrap=True)
            
            # Draw connecting line
            ax.plot(dates, range(len(dates)), 'k-', alpha=0.3, zorder=1, linewidth=2)
            
            # Formatting
            ax.set_yticks(range(len(dates)))
            ax.set_yticklabels([f"Email {i+1}" for i in range(len(dates))])
            ax.set_xlabel('Date & Time', fontsize=12, fontweight='bold')
            ax.set_ylabel('Email Sequence', fontsize=12, fontweight='bold')
            ax.set_title(f"Timeline: {summary['thread_name']}", 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Format dates on x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
            plt.xticks(rotation=45, ha='right')
            
            # Add legend
            legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                         markerfacecolor=sender_colors[sender], 
                                         markersize=10, label=sender[:30])
                             for sender in unique_senders]
            ax.legend(handles=legend_elements, loc='upper left', fontsize=9)
            
            # Add grid
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Add metadata box
            metadata = summary['metadata']
            stats_text = (f"Total Emails: {metadata['email_count']}\n"
                         f"Participants: {metadata['participant_count']}\n"
                         f"Duration: {metadata['duration_days']} days\n"
                         f"Attachments: {metadata['total_attachments']}")
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                   fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            # Tight layout
            plt.tight_layout()
            
            # Save
            output_file_png = f"{output_path}.png"
            output_file_svg = f"{output_path}.svg"
            plt.savefig(output_file_png, dpi=300, bbox_inches='tight')
            try:
                plt.savefig(output_file_svg, format="svg", bbox_inches='tight')
            except Exception as e:
                logger.warning("Failed to save SVG timeline: %s", e)
            plt.close()
            
            logger.info(f"Static timeline saved to {output_file_png} (PNG) and {output_file_svg} (SVG)")
            return True
            
        except Exception as e:
            logger.error(f"Error generating static timeline: {e}")
            return False
    
    def _generate_interactive_timeline(self, thread_emails: List[Dict], summary: Dict, output_path: str) -> bool:
        """Generate interactive timeline using Plotly"""
        try:
            # Sort emails by date
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            
            # Prepare data
            # Convert all datetimes to ISO strings to avoid pywintypes serialization
            dates_dt = [self._to_py_dt(email['received_time']) for email in sorted_emails]
            dates = [d.strftime('%Y-%m-%d %H:%M:%S') for d in dates_dt]
            senders = [email['sender'] for email in sorted_emails]
            subjects = [email['subject'] for email in sorted_emails]
            
            # Create hover text
            hover_texts = []
            for email in sorted_emails:
                dt_txt = self._format_dt(email['received_time'])
                hover_text = (f"<b>{email['sender']}</b><br>"
                            f"{email['subject']}<br>"
                            f"{dt_txt}<br>"
                            f"<i>{email['body'][:200]}...</i>")
                hover_texts.append(hover_text)
            
            # Create figure
            fig = go.Figure()
            
            # Add trace for each unique sender
            unique_senders = list(set(senders))
            for sender in unique_senders:
                sender_dates = [date for date, s in zip(dates, senders) if s == sender]
                sender_indices = [i for i, s in enumerate(senders) if s == sender]
                sender_subjects = [subjects[i] for i in sender_indices]
                sender_hovers = [hover_texts[i] for i in sender_indices]
                
                fig.add_trace(go.Scatter(
                    x=sender_dates,
                    y=sender_indices,
                    mode='markers+text',
                    name=sender[:30],
                    text=[f"Email {i+1}" for i in sender_indices],
                    textposition="top center",
                    hovertext=sender_hovers,
                    hoverinfo='text',
                    marker=dict(size=15, line=dict(width=2, color='DarkSlateGrey'))
                ))
            
            # Add connecting line
            fig.add_trace(go.Scatter(
                x=dates,
                y=list(range(len(dates))),
                mode='lines',
                line=dict(color='gray', width=2, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            # Update layout
            fig.update_layout(
                title=f"Timeline: {summary['thread_name']}",
                xaxis_title="Date & Time",
                yaxis_title="Email Sequence",
                hovermode='closest',
                height=600,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                template='plotly_white'
            )
            
            # Update y-axis
            fig.update_yaxes(
                tickmode='array',
                tickvals=list(range(len(dates))),
                ticktext=[f"Email {i+1}" for i in range(len(dates))]
            )
            
            # Save
            output_file = f"{output_path}.html"
            fig.write_html(output_file, include_plotlyjs=True)
            
            logger.info(f"Interactive timeline saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating interactive timeline: {e}")
            return False
    
    def _clean_email_body(self, body: str) -> str:
        """Clean email body by removing greetings and signatures"""
        # Common greeting patterns to remove
        greetings = [
            'dear all', 'dear team', 'hi all', 'hello all', 'hi team', 'hello team',
            'dear', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening',
            'greetings', 'hey'
        ]
        
        # Common signature patterns to remove
        signatures = [
            'best regards', 'kind regards', 'regards', 'thank you', 'thanks',
            'sincerely', 'cheers', 'best', 'br', 'rgds', 'thx',
            'os melhores cumprimento', 'srdačan pozdrav', 'mit freundlichen grüßen',
            'cordialement', 'saludos', 'atentamente'
        ]
        
        # Split into lines
        lines = body.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Skip empty lines
            if not line_lower:
                continue
            
            # Skip greeting lines (first few lines)
            if len(cleaned_lines) < 2:
                is_greeting = any(greeting in line_lower for greeting in greetings)
                if is_greeting and len(line_lower) < 50:
                    continue
            
            # Skip signature lines
            is_signature = any(sig in line_lower for sig in signatures)
            if is_signature and len(line_lower) < 50:
                continue
            
            # Skip lines with only special characters or underscores
            if all(c in '_ -=*#' for c in line_lower.replace(' ', '')):
                continue
            
            cleaned_lines.append(line.strip())
        
        # Join and limit length
        cleaned = ' '.join(cleaned_lines)
        
        # Remove multiple spaces
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _generate_text_timeline(self, thread_emails: List[Dict], summary: Dict, output_path: str) -> bool:
        """Generate text-based timeline (fallback)"""
        try:
            # Sort emails by date
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            
            # Create text timeline
            timeline_text = f"TIMELINE: {summary['thread_name']}\n"
            timeline_text += "=" * 80 + "\n\n"
            
            for i, email in enumerate(sorted_emails, 1):
                date_str = email['received_time'].strftime('%Y-%m-%d %H:%M')
                timeline_text += f"[{date_str}] {email['sender']}\n"
                
                # Clean and add body snippet
                cleaned_body = self._clean_email_body(email['body'])
                body_snippet = cleaned_body[:200] if len(cleaned_body) > 200 else cleaned_body
                timeline_text += f"{body_snippet}\n\n"
            
            # Add metadata
            metadata = summary['metadata']
            timeline_text += "=" * 80 + "\n"
            timeline_text += f"Total Emails: {metadata['email_count']}\n"
            timeline_text += f"Participants: {metadata['participant_count']}\n"
            timeline_text += f"Duration: {metadata['duration_days']} days\n"
            timeline_text += f"Attachments: {metadata['total_attachments']}\n"
            
            # Save
            output_file = f"{output_path}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(timeline_text)
            
            logger.info(f"Text timeline saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating text timeline: {e}")
            return False
    
    def generate_gantt_chart(self, thread_emails: List[Dict], summary: Dict, output_path: str) -> bool:
        """Generate Gantt-style chart showing email flow by participant"""
        try:
            if not PLOTLY_AVAILABLE:
                logger.warning("Plotly not available for Gantt chart")
                return False
            
            # Sort emails by date
            sorted_emails = sorted(thread_emails, key=lambda x: x['received_time'])
            
            # Prepare data for Gantt chart (convert to strings)
            tasks = []
            for i, email in enumerate(sorted_emails):
                # Calculate duration to next email or end
                start_dt = self._to_py_dt(email['received_time'])
                if i < len(sorted_emails) - 1:
                    end_dt = self._to_py_dt(sorted_emails[i + 1]['received_time'])
                else:
                    # Last email: add 1 hour
                    from datetime import timedelta
                    end_dt = start_dt + timedelta(hours=1)
                
                tasks.append(dict(
                    Task=email['sender'][:30],
                    Start=start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    Finish=end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    Resource=email['subject'][:50]
                ))
            
            # Try Plotly Express timeline when pandas is available
            try:
                import pandas as pd  # type: ignore
                df = pd.DataFrame(tasks)
                fig = px.timeline(
                    df,
                    x_start="Start",
                    x_end="Finish",
                    y="Task",
                    color="Task",
                    hover_data=["Resource"],
                    title=f"Email Flow: {summary['thread_name']}"
                )
                fig.update_yaxes(categoryorder="total ascending")
                fig.update_layout(height=400, template='plotly_white')
            except Exception:
                # Fallback without pandas: render as horizontal line segments per task
                fig = go.Figure()
                order = []
                for t in tasks:
                    if t['Task'] not in order:
                        order.append(t['Task'])
                for t in tasks:
                    fig.add_trace(go.Scatter(
                        x=[t['Start'], t['Finish']],
                        y=[t['Task'], t['Task']],
                        mode='lines',
                        line=dict(width=14),
                        name=t['Task'],
                        hovertext=f"{t['Task']}<br>{t['Resource']}<br>{t['Start']} → {t['Finish']}",
                        hoverinfo='text',
                        showlegend=False
                    ))
                fig.update_layout(
                    title=f"Email Flow: {summary['thread_name']}",
                    xaxis_title="Date & Time",
                    yaxis_title="Participant",
                    template='plotly_white',
                    height=400
                )
                fig.update_yaxes(categoryorder='array', categoryarray=order)
            
            # Save
            output_file = f"{output_path}_gantt.html"
            fig.write_html(output_file, include_plotlyjs=True)
            
            logger.info(f"Gantt chart saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating Gantt chart: {e}")
            return False

    def _to_py_dt(self, dt_obj):
        """Convert Outlook/pywintypes datetime to Python datetime."""
        try:
            if isinstance(dt_obj, datetime):
                return dt_obj
            try:
                # Try dateutil for robust parsing
                from dateutil import parser
                dt = parser.parse(str(dt_obj))
                return dt
            except Exception:
                pass
            # Fallback: try common string format
            return datetime.fromisoformat(str(dt_obj))
        except Exception:
            # Last resort: now
            return datetime.now()

    def _format_dt(self, dt_obj) -> str:
        try:
            dt = self._to_py_dt(dt_obj)
            return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return str(dt_obj)
