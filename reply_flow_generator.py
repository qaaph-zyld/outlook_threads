from __future__ import annotations
import math
from pathlib import Path
from typing import Dict, List, Tuple

import plotly.graph_objects as go
import networkx as nx
import re


class ReplyFlowGenerator:
    def __init__(self) -> None:
        pass

    def generate_flows(self, thread_emails: List[Dict], summary: Dict, output_folder: Path) -> Tuple[Path | None, Path | None]:
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        network_path = output_folder / "flow_network.html"
        sankey_path = output_folder / "flow_sankey.html"

        nodes, edges = self._build_edges(thread_emails)
        if not nodes:
            return None, None

        # Network
        try:
            fig_net = self._build_network_figure(nodes, edges, thread_emails)
            fig_net.write_html(str(network_path), include_plotlyjs=True)
        except Exception:
            network_path = None

        # Sankey
        try:
            fig_sankey = self._build_sankey_figure(nodes, edges)
            fig_sankey.write_html(str(sankey_path), include_plotlyjs=True)
        except Exception:
            sankey_path = None

        return network_path, sankey_path

    def _build_edges(self, thread_emails: List[Dict]) -> Tuple[List[str], Dict[Tuple[str, str], Dict]]:
        # Nodes are email addresses (fallback to names)
        nodes_set = set()
        edges: Dict[Tuple[str, str], Dict] = {}

        for m in sorted(thread_emails, key=lambda x: x.get("received_time")):
            sender = (m.get("sender_email") or m.get("sender") or "Unknown").lower()
            nodes_set.add(sender)
            recips = m.get("recipients", []) or []
            if not recips:
                # Try To/CC string if present in raw Outlook item
                pass
            for r in recips:
                addr = (r.get("address") or r.get("name") or "unknown").lower()
                if not addr or addr == sender:
                    continue
                nodes_set.add(addr)
                key = (sender, addr)
                if key not in edges:
                    edges[key] = {
                        "count": 0,
                        "last_subject": m.get("subject", ""),
                        "last_time": m.get("received_time"),
                        "last_body": m.get("body", ""),
                    }
                edges[key]["count"] += 1
                # Update last seen subject/time
                edges[key]["last_subject"] = m.get("subject", edges[key]["last_subject"]) or edges[key]["last_subject"]
                edges[key]["last_time"] = m.get("received_time") or edges[key]["last_time"]
                edges[key]["last_body"] = m.get("body", edges[key].get("last_body", "")) or edges[key].get("last_body", "")

        nodes = sorted(nodes_set)
        return nodes, edges

    def _build_network_figure(self, nodes: List[str], edges: Dict[Tuple[str, str], Dict], thread_emails: List[Dict]) -> go.Figure:
        G = nx.DiGraph()
        for n in nodes:
            G.add_node(n)
        for (u, v), data in edges.items():
            G.add_edge(u, v, weight=data["count"], last_subject=data["last_subject"], last_time=str(data["last_time"]))

        pos = nx.spring_layout(G, seed=42, k=0.7 / math.sqrt(max(1, len(G.nodes()))))

        # Edges
        edge_x, edge_y, edge_text = [], [], []
        for u, v, d in G.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            core = self._classify_core(str(d.get('last_subject','')), str(d.get('last_time','')), str(d.get('last_body','')))
            edge_text.append(f"{u} → {v}<br>emails: {d.get('weight', 1)}<br>last: {d.get('last_time','')}<br>{d.get('last_subject','')}<br><b>{core}</b>")

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=1, color="#888"),
            hoverinfo="text",
            text=[" ".join(edge_text)],
            mode="lines"
        )

        # Nodes
        node_x, node_y, node_text, node_size = [], [], [], []
        for n in G.nodes():
            x, y = pos[n]
            node_x.append(x)
            node_y.append(y)
            out_weight = sum(d.get("weight", 1) for _, _, d in G.out_edges(n, data=True))
            in_weight = sum(d.get("weight", 1) for _, _, d in G.in_edges(n, data=True))
            size = 10 + 2 * (out_weight + in_weight)
            node_size.append(size)
            node_text.append(f"{n}<br>out: {out_weight} | in: {in_weight}")

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=[n.split("@")[0] if "@" in n else n for n in G.nodes()],
            textposition="top center",
            hoverinfo="text",
            hovertext=node_text,
            marker=dict(
                showscale=False,
                color="#1f77b4",
                size=node_size,
                line_width=1,
                line_color="#ffffff"
            )
        )

        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            template="plotly_white",
            title="Conversation Flow (Network)",
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="closest"
        )
        return fig

    def _build_sankey_figure(self, nodes: List[str], edges: Dict[Tuple[str, str], Dict]) -> go.Figure:
        index = {n: i for i, n in enumerate(nodes)}
        source, target, value, hover = [], [], [], []
        for (u, v), d in edges.items():
            if u in index and v in index:
                source.append(index[u])
                target.append(index[v])
                value.append(int(d.get("count", 1)))
                core = self._classify_core(str(d.get('last_subject','')), str(d.get('last_time','')), str(d.get('last_body','')))
                hover.append(f"{u} → {v}: {d.get('count',1)} emails\n{d.get('last_time','')}\n{d.get('last_subject','')}\n{core}")

        sankey = go.Sankey(
            node=dict(
                pad=15,
                thickness=14,
                line=dict(color="black", width=0.3),
                label=[n.split("@")[0] if "@" in n else n for n in nodes],
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                hovertemplate="%{customdata}",
                customdata=hover
            )
        )

        fig = go.Figure(data=[sankey])
        fig.update_layout(
            template="plotly_white",
            title="Conversation Flow (Sankey)",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        return fig

    def _classify_core(self, subject: str, last_time: str, body: str) -> str:
        """Heuristic classification of the last message content for hover hints."""
        text = f"{subject} {body}".lower()
        text = re.sub(r"\s+", " ", text)
        labels = []
        if '?' in text or any(p in text for p in ['please confirm', 'could you', 'can you', 'please provide', 'please send']):
            labels.append('question/request')
        if any(p in text for p in ['deadline', 'by ', 'eod', 'tomorrow', 'today', 'friday', 'monday']):
            labels.append('deadline/time')
        if any(p in text for p in ['confirmed', 'agreed', 'approved', 'resolved']):
            labels.append('decision/confirmation')
        if any(p in text for p in ['delay', 'blocked', 'issue', 'problem', 'urgent', 'asap']):
            labels.append('issue/urgent')
        return ' | '.join(labels) if labels else 'message'
