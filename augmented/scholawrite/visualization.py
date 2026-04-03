"""Visualization utilities for causal process trajectories."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .schema import AugmentedDocument, InjectionSpan
from .banner import VERSION

__all__ = [
    "generate_html_visualization",
    "generate_terminal_visualization",
    "generate_tex_report",
    "get_citation_info",
    "CITATION_BIBTEX",
    "CITATION_APA",
    "CITATION_MLA",
    "HTML_TEMPLATE",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Citation Information
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# Citation Templates
# ─────────────────────────────────────────────────────────────────────────────

CITATION_BIBTEX = r"""@dataset{scholawrite_augmented_2026,
  title        = {{ScholaWrite-Augmented: Process-Coupled Trajectories for AI Writing Detection}},
  author       = {{WritersLogic}},
  year         = {2026},
  note         = {Augmented derivative of ScholaWrite (MinnesotaNLP)},
  howpublished = {\url{https://github.com/writerslogic/scholawrite}},
}"""

CITATION_APA = (
    "WritersLogic. (2026). "
    "ScholaWrite-Augmented: Process-Coupled Trajectories for AI Writing Detection "
    "[Dataset]. Augmented derivative of ScholaWrite (MinnesotaNLP). "
    "https://github.com/writerslogic/scholawrite"
)

CITATION_MLA = (
    '"ScholaWrite-Augmented: Process-Coupled Trajectories for AI Writing Detection." '
    "WritersLogic, 2026. Augmented derivative of ScholaWrite (MinnesotaNLP). "
    "github.com/writerslogic/scholawrite."
)


def get_citation_info(format: str = "all") -> str:
    """Get citation information in various formats."""
    if format == "bibtex":
        return CITATION_BIBTEX
    elif format == "apa":
        return CITATION_APA
    elif format == "mla":
        return CITATION_MLA
    else:
        return f"""
HOW TO CITE SCHOLAWRITE
=======================

BibTeX:
{CITATION_BIBTEX}

APA: {CITATION_APA}

MLA: {CITATION_MLA}
"""


def _escape(text: str) -> str:
    """Safely escape HTML content."""
    return html.escape(text, quote=True)


def _generate_json_ld(docs: List[AugmentedDocument]) -> str:
    """Generate JSON-LD schema for the visualization."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "ScholaWrite Trajectory Visualization",
        "description": "Visualization of AI-generated text injection trajectories in scholarly writing",
        "version": VERSION,
        "dateCreated": datetime.now().isoformat(),
        "creator": {
            "@type": "Organization",
            "name": "ScholaWrite Project"
        },
        "distribution": {
            "@type": "DataDownload",
            "encodingFormat": "text/html"
        },
        "variableMeasured": [
            {
                "@type": "PropertyValue",
                "name": "trajectory_state",
                "description": "Injection evolution state (cold, warm, assimilated)"
            },
            {
                "@type": "PropertyValue",
                "name": "glucose_level",
                "description": "Simulated cognitive glucose at injection time"
            },
            {
                "@type": "PropertyValue",
                "name": "causal_trace",
                "description": "Sequence of causal events during generation"
            }
        ],
        "measurementTechnique": "Embodied Causal Process Simulation",
        "numberOfItems": len(docs)
    }
    return json.dumps(schema, indent=2)


def _build_annotation_data(annotations: List[InjectionSpan]) -> List[dict]:
    """Build annotation data for JavaScript."""
    data = []
    for ann in annotations:
        trace_summary = []
        if ann.causal_trace:
            for event in ann.causal_trace:
                trace_summary.append({
                    "intention": event.intention,
                    "output": event.actual_output[:50] + "..." if len(event.actual_output) > 50 else event.actual_output,
                    "status": event.status,
                    "glucose": round(event.glucose_at_event, 3) if event.glucose_at_event else None,
                    "latency": event.latency_ms,
                })

        data.append({
            "id": ann.injection_id,
            "start": ann.span_start_char,
            "end": ann.span_end_char,
            "state": ann.trajectory_state.value if ann.trajectory_state else "unknown",
            "level": ann.injection_level.value if ann.injection_level else "unknown",
            "label": ann.label.value if ann.label else "unknown",
            "generator": ann.generator_class,
            "trace": trace_summary,
            "repairs": sum(1 for e in ann.causal_trace if e.status == "repair") if ann.causal_trace else 0,
            "finalGlucose": round(ann.causal_trace[-1].glucose_at_event, 3) if ann.causal_trace and ann.causal_trace[-1].glucose_at_event else None,
        })
    return data


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="ScholaWrite Trajectory Visualization - Forensic analysis of AI-generated text in scholarly writing">
    <meta name="generator" content="ScholaWrite v{version}">
    <title>ScholaWrite Trajectory Visualizer</title>

    <!-- JSON-LD Schema -->
    <script type="application/ld+json">
{json_ld}
    </script>

    <style>
        /* ═══════════════════════════════════════════════════════════════════════
           CSS Custom Properties (Design Tokens)
           ═══════════════════════════════════════════════════════════════════════ */
        :root {{
            /* Colors */
            --color-bg: #0f172a;
            --color-bg-elevated: #1e293b;
            --color-bg-card: #1e293b;
            --color-bg-hover: #334155;
            --color-text: #f1f5f9;
            --color-text-muted: #94a3b8;
            --color-text-dim: #64748b;
            --color-border: #334155;
            --color-border-subtle: #1e293b;

            /* State Colors */
            --color-cold: #3b82f6;
            --color-cold-bg: rgba(59, 130, 246, 0.15);
            --color-cold-border: rgba(59, 130, 246, 0.4);
            --color-warm: #f59e0b;
            --color-warm-bg: rgba(245, 158, 11, 0.15);
            --color-warm-border: rgba(245, 158, 11, 0.4);
            --color-assimilated: #ef4444;
            --color-assimilated-bg: rgba(239, 68, 68, 0.15);
            --color-assimilated-border: rgba(239, 68, 68, 0.4);

            /* Accent */
            --color-accent: #06b6d4;
            --color-accent-hover: #22d3ee;

            /* Typography */
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace;

            /* Spacing */
            --space-xs: 0.25rem;
            --space-sm: 0.5rem;
            --space-md: 1rem;
            --space-lg: 1.5rem;
            --space-xl: 2rem;
            --space-2xl: 3rem;

            /* Transitions */
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-spring: 500ms cubic-bezier(0.34, 1.56, 0.64, 1);

            /* Shadows */
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.2);
            --shadow-glow: 0 0 20px rgba(6, 182, 212, 0.3);

            /* Border Radius */
            --radius-sm: 0.375rem;
            --radius-md: 0.5rem;
            --radius-lg: 0.75rem;
            --radius-xl: 1rem;
        }}

        /* Light mode */
        @media (prefers-color-scheme: light) {{
            :root {{
                --color-bg: #f8fafc;
                --color-bg-elevated: #ffffff;
                --color-bg-card: #ffffff;
                --color-bg-hover: #f1f5f9;
                --color-text: #0f172a;
                --color-text-muted: #475569;
                --color-text-dim: #94a3b8;
                --color-border: #e2e8f0;
                --color-border-subtle: #f1f5f9;
                --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
                --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
                --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
            }}
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Base Styles
           ═══════════════════════════════════════════════════════════════════════ */
        *, *::before, *::after {{
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            padding: 0;
            font-family: var(--font-sans);
            font-size: 16px;
            line-height: 1.6;
            color: var(--color-text);
            background: var(--color-bg);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Layout
           ═══════════════════════════════════════════════════════════════════════ */
        .app {{
            display: flex;
            min-height: 100vh;
        }}

        .sidebar {{
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            width: 280px;
            background: var(--color-bg-elevated);
            border-right: 1px solid var(--color-border);
            display: flex;
            flex-direction: column;
            z-index: 100;
            transform: translateX(0);
            transition: transform var(--transition-base);
        }}

        .sidebar-header {{
            padding: var(--space-lg);
            border-bottom: 1px solid var(--color-border);
        }}

        .sidebar-content {{
            flex: 1;
            overflow-y: auto;
            padding: var(--space-md);
        }}

        .main {{
            flex: 1;
            margin-left: 280px;
            padding: var(--space-xl);
            max-width: 1200px;
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Header & Branding
           ═══════════════════════════════════════════════════════════════════════ */
        .logo {{
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            text-decoration: none;
            color: var(--color-text);
            user-select: none;
        }}

        .logo-icon {{
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--color-accent), var(--color-cold));
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
            color: white;
        }}

        .logo-text {{
            font-weight: 700;
            font-size: 1.125rem;
            letter-spacing: -0.025em;
        }}

        .logo-version {{
            font-size: 0.75rem;
            color: var(--color-text-dim);
            font-weight: 400;
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Navigation
           ═══════════════════════════════════════════════════════════════════════ */
        .nav-section {{
            margin-bottom: var(--space-lg);
        }}

        .nav-section-title {{
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--color-text-dim);
            padding: var(--space-sm) var(--space-md);
            user-select: none;
        }}

        .nav-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}

        .nav-item {{
            margin: 2px 0;
        }}

        .nav-link {{
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-md);
            color: var(--color-text-muted);
            text-decoration: none;
            font-size: 0.875rem;
            transition: all var(--transition-fast);
            cursor: pointer;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
        }}

        .nav-link:hover, .nav-link:focus {{
            background: var(--color-bg-hover);
            color: var(--color-text);
            outline: none;
        }}

        .nav-link.active {{
            background: var(--color-accent);
            color: white;
        }}

        .nav-link-badge {{
            margin-left: auto;
            font-size: 0.75rem;
            padding: 2px 6px;
            border-radius: 9999px;
            background: var(--color-border);
            color: var(--color-text-muted);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Cards
           ═══════════════════════════════════════════════════════════════════════ */
        .card {{
            background: var(--color-bg-card);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-sm);
            margin-bottom: var(--space-lg);
            overflow: hidden;
            transition: all var(--transition-base);
        }}

        .card:hover {{
            box-shadow: var(--shadow-md);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--space-md) var(--space-lg);
            border-bottom: 1px solid var(--color-border);
            background: var(--color-bg-elevated);
        }}

        .card-title {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--color-text);
            margin: 0;
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }}

        .card-meta {{
            font-size: 0.75rem;
            color: var(--color-text-dim);
        }}

        .card-body {{
            padding: var(--space-lg);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Document Content
           ═══════════════════════════════════════════════════════════════════════ */
        .document-text {{
            font-family: var(--font-mono);
            font-size: 0.8125rem;
            line-height: 1.8;
            white-space: pre-wrap;
            word-break: break-word;
            color: var(--color-text-muted);
        }}

        /* Injection Spans */
        .injection-span {{
            position: relative;
            padding: 2px 4px;
            margin: 0 -2px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all var(--transition-fast);
            text-decoration: none;
        }}

        .injection-span:focus {{
            outline: 2px solid var(--color-accent);
            outline-offset: 2px;
        }}

        /* State-specific styles */
        .injection-span[data-state="cold"] {{
            background: var(--color-cold-bg);
            border-bottom: 2px solid var(--color-cold);
            color: var(--color-cold);
        }}

        .injection-span[data-state="cold"]:hover {{
            background: rgba(59, 130, 246, 0.25);
            box-shadow: 0 0 0 4px var(--color-cold-bg);
        }}

        .injection-span[data-state="warm"] {{
            background: var(--color-warm-bg);
            border-bottom: 2px solid var(--color-warm);
            color: var(--color-warm);
        }}

        .injection-span[data-state="warm"]:hover {{
            background: rgba(245, 158, 11, 0.25);
            box-shadow: 0 0 0 4px var(--color-warm-bg);
        }}

        .injection-span[data-state="assimilated"] {{
            background: var(--color-assimilated-bg);
            border-bottom: 2px solid var(--color-assimilated);
            color: var(--color-assimilated);
        }}

        .injection-span[data-state="assimilated"]:hover {{
            background: rgba(239, 68, 68, 0.25);
            box-shadow: 0 0 0 4px var(--color-assimilated-bg);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Tooltip / Detail Panel
           ═══════════════════════════════════════════════════════════════════════ */
        .tooltip {{
            position: fixed;
            z-index: 1000;
            background: var(--color-bg-elevated);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            padding: var(--space-md);
            max-width: 400px;
            opacity: 0;
            visibility: hidden;
            transform: translateY(8px) scale(0.96);
            transition: all var(--transition-fast);
            pointer-events: none;
        }}

        .tooltip.visible {{
            opacity: 1;
            visibility: visible;
            transform: translateY(0) scale(1);
        }}

        .tooltip-header {{
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            margin-bottom: var(--space-sm);
            padding-bottom: var(--space-sm);
            border-bottom: 1px solid var(--color-border);
        }}

        .tooltip-badge {{
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 2px 8px;
            border-radius: 9999px;
        }}

        .tooltip-badge.cold {{
            background: var(--color-cold-bg);
            color: var(--color-cold);
            border: 1px solid var(--color-cold-border);
        }}

        .tooltip-badge.warm {{
            background: var(--color-warm-bg);
            color: var(--color-warm);
            border: 1px solid var(--color-warm-border);
        }}

        .tooltip-badge.assimilated {{
            background: var(--color-assimilated-bg);
            color: var(--color-assimilated);
            border: 1px solid var(--color-assimilated-border);
        }}

        .tooltip-id {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--color-text-dim);
        }}

        .tooltip-grid {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: var(--space-xs) var(--space-md);
            font-size: 0.8125rem;
        }}

        .tooltip-label {{
            color: var(--color-text-dim);
        }}

        .tooltip-value {{
            color: var(--color-text);
            font-family: var(--font-mono);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Stats Bar
           ═══════════════════════════════════════════════════════════════════════ */
        .stats-bar {{
            display: flex;
            gap: var(--space-lg);
            padding: var(--space-lg);
            background: var(--color-bg-elevated);
            border-bottom: 1px solid var(--color-border);
            margin-bottom: var(--space-xl);
            border-radius: var(--radius-lg);
        }}

        .stat {{
            text-align: center;
        }}

        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--color-accent);
            line-height: 1;
        }}

        .stat-label {{
            font-size: 0.75rem;
            color: var(--color-text-dim);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: var(--space-xs);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Legend
           ═══════════════════════════════════════════════════════════════════════ */
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: var(--space-md);
            padding: var(--space-md);
            background: var(--color-bg-elevated);
            border-radius: var(--radius-md);
            margin-bottom: var(--space-lg);
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            font-size: 0.8125rem;
            color: var(--color-text-muted);
        }}

        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: var(--radius-sm);
        }}

        .legend-color.cold {{
            background: var(--color-cold);
        }}

        .legend-color.warm {{
            background: var(--color-warm);
        }}

        .legend-color.assimilated {{
            background: var(--color-assimilated);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Buttons
           ═══════════════════════════════════════════════════════════════════════ */
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            font-size: 0.875rem;
            font-weight: 500;
            border-radius: var(--radius-md);
            border: 1px solid transparent;
            cursor: pointer;
            transition: all var(--transition-fast);
            text-decoration: none;
            user-select: none;
        }}

        .btn:focus {{
            outline: 2px solid var(--color-accent);
            outline-offset: 2px;
        }}

        .btn-primary {{
            background: var(--color-accent);
            color: white;
            border-color: var(--color-accent);
        }}

        .btn-primary:hover {{
            background: var(--color-accent-hover);
            border-color: var(--color-accent-hover);
        }}

        .btn-secondary {{
            background: transparent;
            color: var(--color-text-muted);
            border-color: var(--color-border);
        }}

        .btn-secondary:hover {{
            background: var(--color-bg-hover);
            color: var(--color-text);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Footer
           ═══════════════════════════════════════════════════════════════════════ */
        .footer {{
            margin-top: auto;
            padding: var(--space-md);
            border-top: 1px solid var(--color-border);
            font-size: 0.75rem;
            color: var(--color-text-dim);
        }}

        .footer-actions {{
            display: flex;
            gap: var(--space-sm);
            margin-bottom: var(--space-sm);
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Animations
           ═══════════════════════════════════════════════════════════════════════ */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-20px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}

        .animate-fade-in {{
            animation: fadeIn var(--transition-slow) ease-out forwards;
        }}

        .animate-slide-in {{
            animation: slideIn var(--transition-slow) ease-out forwards;
        }}

        /* Staggered animations */
        .card {{ animation: fadeIn var(--transition-slow) ease-out forwards; }}
        .card:nth-child(1) {{ animation-delay: 0ms; }}
        .card:nth-child(2) {{ animation-delay: 50ms; }}
        .card:nth-child(3) {{ animation-delay: 100ms; }}
        .card:nth-child(4) {{ animation-delay: 150ms; }}
        .card:nth-child(5) {{ animation-delay: 200ms; }}

        /* ═══════════════════════════════════════════════════════════════════════
           Print Styles
           ═══════════════════════════════════════════════════════════════════════ */
        @media print {{
            .sidebar {{ display: none; }}
            .main {{ margin-left: 0; padding: 1cm; }}
            .btn {{ display: none; }}
            .card {{ break-inside: avoid; }}
            .injection-span {{
                border: 1px solid currentColor !important;
                background: transparent !important;
            }}
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Responsive
           ═══════════════════════════════════════════════════════════════════════ */
        @media (max-width: 768px) {{
            .sidebar {{
                transform: translateX(-100%);
            }}

            .sidebar.open {{
                transform: translateX(0);
            }}

            .main {{
                margin-left: 0;
                padding: var(--space-md);
            }}

            .stats-bar {{
                flex-wrap: wrap;
            }}
        }}

        /* ═══════════════════════════════════════════════════════════════════════
           Utility Classes
           ═══════════════════════════════════════════════════════════════════════ */
        .sr-only {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }}

        .no-select {{
            user-select: none;
            -webkit-user-select: none;
        }}
    </style>
</head>
<body>
    <div class="app">
        <!-- Sidebar Navigation -->
        <aside class="sidebar" role="navigation" aria-label="Document navigation">
            <header class="sidebar-header">
                <a href="#" class="logo" aria-label="ScholaWrite Visualizer">
                    <span class="logo-icon no-select" aria-hidden="true">SW</span>
                    <span>
                        <span class="logo-text">ScholaWrite</span>
                        <span class="logo-version">v{version}</span>
                    </span>
                </a>
            </header>

            <nav class="sidebar-content">
                <div class="nav-section">
                    <h2 class="nav-section-title no-select">Documents</h2>
                    <ul class="nav-list" role="list">
{nav_items}
                    </ul>
                </div>
            </nav>

            <footer class="footer">
                <div class="footer-actions">
                    <button class="btn btn-secondary" onclick="window.print()" aria-label="Export to PDF">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                            <path d="M6 9V2h12v7"></path>
                            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                            <rect x="6" y="14" width="12" height="8"></rect>
                        </svg>
                        Export PDF
                    </button>
                </div>
                <p class="no-select">Generated {timestamp}</p>
            </footer>
        </aside>

        <!-- Main Content -->
        <main class="main" role="main" aria-label="Visualization content">
            <header>
                <h1 class="sr-only">ScholaWrite Trajectory Visualization</h1>

                <!-- Stats Overview -->
                <div class="stats-bar" role="region" aria-label="Statistics overview">
                    <div class="stat">
                        <div class="stat-value">{total_docs}</div>
                        <div class="stat-label">Documents</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_revisions}</div>
                        <div class="stat-label">Revisions</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_injections}</div>
                        <div class="stat-label">Injections</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{cold_count}</div>
                        <div class="stat-label">Cold</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{warm_count}</div>
                        <div class="stat-label">Warm</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{assimilated_count}</div>
                        <div class="stat-label">Assimilated</div>
                    </div>
                </div>

                <!-- Legend -->
                <div class="legend" role="legend" aria-label="Trajectory state legend">
                    <div class="legend-item">
                        <span class="legend-color cold" aria-hidden="true"></span>
                        <span>Cold - Initial injection</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color warm" aria-hidden="true"></span>
                        <span>Warm - Partially integrated</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color assimilated" aria-hidden="true"></span>
                        <span>Assimilated - Fully evolved</span>
                    </div>
                </div>
            </header>

            <!-- Document Cards -->
            <section aria-label="Document visualizations">
{document_cards}
            </section>
        </main>
    </div>

    <!-- Tooltip -->
    <div class="tooltip" role="tooltip" aria-hidden="true" id="tooltip">
        <div class="tooltip-header">
            <span class="tooltip-badge" id="tooltip-badge"></span>
            <span class="tooltip-id" id="tooltip-id"></span>
        </div>
        <div class="tooltip-grid" id="tooltip-content"></div>
    </div>

    <!-- Scripts -->
    <script>
        // Annotation data
        const annotationData = {annotation_data};

        // Tooltip handling
        const tooltip = document.getElementById('tooltip');
        const tooltipBadge = document.getElementById('tooltip-badge');
        const tooltipId = document.getElementById('tooltip-id');
        const tooltipContent = document.getElementById('tooltip-content');

        function showTooltip(event, data) {{
            tooltipBadge.textContent = data.state;
            tooltipBadge.className = 'tooltip-badge ' + data.state;
            tooltipId.textContent = data.id;

            let html = `
                <span class="tooltip-label">Level</span>
                <span class="tooltip-value">${{data.level}}</span>
                <span class="tooltip-label">Generator</span>
                <span class="tooltip-value">${{data.generator}}</span>
                <span class="tooltip-label">Repairs</span>
                <span class="tooltip-value">${{data.repairs}}</span>
            `;

            if (data.finalGlucose !== null) {{
                html += `
                    <span class="tooltip-label">Final Glucose</span>
                    <span class="tooltip-value">${{data.finalGlucose}}</span>
                `;
            }}

            tooltipContent.innerHTML = html;

            // Position tooltip
            const rect = event.target.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();

            let x = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
            let y = rect.bottom + 8;

            // Keep in viewport
            x = Math.max(8, Math.min(x, window.innerWidth - tooltipRect.width - 8));
            if (y + tooltipRect.height > window.innerHeight - 8) {{
                y = rect.top - tooltipRect.height - 8;
            }}

            tooltip.style.left = x + 'px';
            tooltip.style.top = y + 'px';
            tooltip.classList.add('visible');
            tooltip.setAttribute('aria-hidden', 'false');
        }}

        function hideTooltip() {{
            tooltip.classList.remove('visible');
            tooltip.setAttribute('aria-hidden', 'true');
        }}

        // Initialize injection spans
        document.querySelectorAll('.injection-span').forEach(span => {{
            const id = span.dataset.id;
            const data = annotationData[id];

            if (data) {{
                span.addEventListener('mouseenter', (e) => showTooltip(e, data));
                span.addEventListener('mouseleave', hideTooltip);
                span.addEventListener('focus', (e) => showTooltip(e, data));
                span.addEventListener('blur', hideTooltip);
            }}
        }});

        // Smooth scroll for nav links
        document.querySelectorAll('.nav-link[href^="#"]').forEach(link => {{
            link.addEventListener('click', (e) => {{
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    // Update active state
                    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                }}
            }});
        }});

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                hideTooltip();
            }}
        }});
    </script>
</body>
</html>'''


def _highlight_text(text: str, annotations: List[InjectionSpan]) -> str:
    """Apply injection highlighting to text with proper escaping."""
    if not annotations:
        return _escape(text)

    # Sort annotations by start position (descending) for safe replacement
    sorted_anns = sorted(annotations, key=lambda x: x.span_start_char, reverse=True)

    result = text
    for ann in sorted_anns:
        start, end = ann.span_start_char, ann.span_end_char
        state = ann.trajectory_state.value if ann.trajectory_state else "unknown"

        snippet = result[start:end]
        replacement = (
            f'<span class="injection-span" data-state="{state}" data-id="{ann.injection_id}" '
            f'tabindex="0" role="mark" aria-label="Injection: {state} state">'
            f'{_escape(snippet)}</span>'
        )
        result = result[:start] + replacement + result[end:]

    # Escape the non-annotated parts
    # This is tricky because we've already inserted HTML - we'll handle it differently
    # Actually, we need to escape BEFORE inserting spans

    return result


def _highlight_text_safe(text: str, annotations: List[InjectionSpan]) -> str:
    """Safely highlight text with proper HTML escaping."""
    if not annotations:
        return _escape(text)

    # Build segments
    sorted_anns = sorted(annotations, key=lambda x: x.span_start_char)

    segments = []
    last_end = 0

    for ann in sorted_anns:
        start, end = ann.span_start_char, ann.span_end_char
        state = ann.trajectory_state.value if ann.trajectory_state else "unknown"

        # Add text before this annotation (escaped)
        if start > last_end:
            segments.append(_escape(text[last_end:start]))

        # Add the annotated span
        snippet = text[start:end]
        segments.append(
            f'<span class="injection-span" data-state="{state}" data-id="{ann.injection_id}" '
            f'tabindex="0" role="mark" aria-label="Injection: {state} state">'
            f'{_escape(snippet)}</span>'
        )

        last_end = end

    # Add remaining text
    if last_end < len(text):
        segments.append(_escape(text[last_end:]))

    return ''.join(segments)


def generate_html_visualization(
    docs: List[AugmentedDocument],
    output_path: Optional[Path] = None,
    max_docs: int = 50,
) -> str:
    """Generate professional HTML visualization of trajectory data.

    Args:
        docs: List of augmented documents to visualize
        output_path: Optional path to write HTML file
        max_docs: Maximum number of documents to include

    Returns:
        Generated HTML string
    """
    docs = docs[:max_docs]

    # Calculate statistics
    total_revisions = sum(len(doc.revisions) for doc in docs)
    all_annotations = []
    for doc in docs:
        for rev in doc.revisions:
            all_annotations.extend(rev.annotations)

    cold_count = sum(1 for a in all_annotations if a.trajectory_state and a.trajectory_state.value == "cold")
    warm_count = sum(1 for a in all_annotations if a.trajectory_state and a.trajectory_state.value == "warm")
    assimilated_count = sum(1 for a in all_annotations if a.trajectory_state and a.trajectory_state.value == "assimilated")

    # Build annotation data for JavaScript
    annotation_data = {}
    for doc in docs:
        for rev in doc.revisions:
            for ann_data in _build_annotation_data(rev.annotations):
                annotation_data[ann_data['id']] = ann_data

    # Build navigation items
    nav_items = []
    for i, doc in enumerate(docs):
        ann_count = sum(len(rev.annotations) for rev in doc.revisions)
        nav_items.append(
            f'                        <li class="nav-item">\n'
            f'                            <a href="#doc-{i}" class="nav-link{"active" if i == 0 else ""}" '
            f'aria-label="Document {doc.doc_id[:8]}">\n'
            f'                                <span>{doc.doc_id[:12]}...</span>\n'
            f'                                <span class="nav-link-badge">{ann_count}</span>\n'
            f'                            </a>\n'
            f'                        </li>'
        )

    # Build document cards
    document_cards = []
    for i, doc in enumerate(docs):
        for rev in doc.revisions:
            if not rev.annotations:
                continue

            highlighted = _highlight_text_safe(rev.text, rev.annotations)

            card = f'''
                <article class="card" id="doc-{i}" aria-labelledby="doc-title-{i}">
                    <header class="card-header">
                        <h2 class="card-title" id="doc-title-{i}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            {_escape(doc.doc_id)}
                        </h2>
                        <span class="card-meta">Revision {rev.revision_index} &middot; {len(rev.annotations)} injections</span>
                    </header>
                    <div class="card-body">
                        <div class="document-text" role="article">{highlighted}</div>
                    </div>
                </article>'''
            document_cards.append(card)

    # Generate final HTML
    html = HTML_TEMPLATE.format(
        version=VERSION,
        json_ld=_generate_json_ld(docs),
        nav_items='\n'.join(nav_items),
        document_cards='\n'.join(document_cards),
        annotation_data=json.dumps(annotation_data),
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_docs=len(docs),
        total_revisions=total_revisions,
        total_injections=len(all_annotations),
        cold_count=cold_count,
        warm_count=warm_count,
        assimilated_count=assimilated_count,
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding='utf-8')

    return html


def generate_terminal_visualization(
    docs: List[AugmentedDocument],
    max_docs: int = 5,
    max_text_length: int = 500,
) -> str:
    """Generate terminal-friendly visualization of trajectory data.

    Args:
        docs: List of augmented documents
        max_docs: Maximum documents to show
        max_text_length: Maximum text length per revision

    Returns:
        Formatted string for terminal output
    """
    # ANSI color codes
    CYAN = '\033[36m'
    BLUE = '\033[34m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    DIM = '\033[2m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    STATE_COLORS = {
        'cold': BLUE,
        'warm': YELLOW,
        'assimilated': RED,
    }

    lines = []
    lines.append(f"\n{CYAN}{'═' * 70}{RESET}")
    lines.append(f"{BOLD}  TRAJECTORY VISUALIZATION{RESET}")
    lines.append(f"{CYAN}{'═' * 70}{RESET}\n")

    # Stats
    total_inj = sum(len(rev.annotations) for doc in docs[:max_docs] for rev in doc.revisions)
    lines.append(f"  {DIM}Documents:{RESET} {len(docs[:max_docs])}  {DIM}Injections:{RESET} {total_inj}\n")

    # Legend
    lines.append(f"  {DIM}Legend:{RESET} {BLUE}■{RESET} Cold  {YELLOW}■{RESET} Warm  {RED}■{RESET} Assimilated\n")
    lines.append(f"{DIM}{'─' * 70}{RESET}\n")

    for doc in docs[:max_docs]:
        lines.append(f"{BOLD}  Document: {doc.doc_id[:30]}...{RESET}\n")

        for rev in doc.revisions:
            if not rev.annotations:
                continue

            lines.append(f"  {DIM}Revision {rev.revision_index} ({len(rev.annotations)} injections){RESET}")

            # Show text with inline markers
            text = rev.text[:max_text_length]
            if len(rev.text) > max_text_length:
                text += "..."

            # Build marked text
            sorted_anns = sorted(rev.annotations, key=lambda x: x.span_start_char)

            for ann in sorted_anns:
                state = ann.trajectory_state.value if ann.trajectory_state else 'unknown'
                color = STATE_COLORS.get(state, DIM)
                marker = f"{color}[{state[0].upper()}]{RESET}"

                lines.append(f"    {marker} {DIM}@{ann.span_start_char}:{RESET} {ann.injection_id[:20]}")

                if ann.causal_trace:
                    repairs = sum(1 for e in ann.causal_trace if e.status == 'repair')
                    glucose = ann.causal_trace[-1].glucose_at_event if ann.causal_trace[-1].glucose_at_event else 0
                    lines.append(f"        {DIM}Repairs: {repairs}, Glucose: {glucose:.3f}{RESET}")

            lines.append("")

        lines.append(f"{DIM}{'─' * 70}{RESET}\n")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# LaTeX / TeX Report Generation
# ═══════════════════════════════════════════════════════════════════════════════

TEX_TEMPLATE = r"""\documentclass[11pt,a4paper]{article}

% ═══════════════════════════════════════════════════════════════════════════════
% Packages
% ═══════════════════════════════════════════════════════════════════════════════
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[margin=1in]{geometry}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{graphicx}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{soul}  % For highlighting

% ═══════════════════════════════════════════════════════════════════════════════
% Color Definitions (Trajectory States)
% ═══════════════════════════════════════════════════════════════════════════════
\definecolor{coldcolor}{RGB}{59, 130, 246}     % Blue
\definecolor{warmcolor}{RGB}{245, 158, 11}     % Amber
\definecolor{assimcolor}{RGB}{239, 68, 68}     % Red
\definecolor{accentcolor}{RGB}{6, 182, 212}    % Cyan
\definecolor{textmuted}{RGB}{100, 116, 139}    % Slate

% ═══════════════════════════════════════════════════════════════════════════════
% Hyperref Configuration
% ═══════════════════════════════════════════════════════════════════════════════
\hypersetup{
    colorlinks=true,
    linkcolor=accentcolor,
    urlcolor=accentcolor,
    citecolor=accentcolor,
    pdftitle={ScholaWrite Trajectory Report},
    pdfauthor={ScholaWrite Project},
}

% ═══════════════════════════════════════════════════════════════════════════════
% Header/Footer
% ═══════════════════════════════════════════════════════════════════════════════
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\textcolor{textmuted}{\small ScholaWrite Trajectory Report}}
\fancyhead[R]{\textcolor{textmuted}{\small v%(version)s}}
\fancyfoot[C]{\textcolor{textmuted}{\small Page \thepage\ of \pageref{LastPage}}}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0pt}

% ═══════════════════════════════════════════════════════════════════════════════
% Custom Commands
% ═══════════════════════════════════════════════════════════════════════════════
\newcommand{\statecold}[1]{\textcolor{coldcolor}{\textbf{[C]}} #1}
\newcommand{\statewarm}[1]{\textcolor{warmcolor}{\textbf{[W]}} #1}
\newcommand{\stateassim}[1]{\textcolor{assimcolor}{\textbf{[A]}} #1}
\newcommand{\injectspan}[2]{\hl{#1}\textsuperscript{\tiny #2}}

% Title formatting
\titleformat{\section}{\Large\bfseries\color{accentcolor}}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{1em}{}

% ═══════════════════════════════════════════════════════════════════════════════
% Document
% ═══════════════════════════════════════════════════════════════════════════════
\begin{document}

% ─────────────────────────────────────────────────────────────────────────────
% Title Page
% ─────────────────────────────────────────────────────────────────────────────
\begin{titlepage}
    \centering
    \vspace*{2cm}

    {\Huge\bfseries\textcolor{accentcolor}{ScholaWrite}\par}
    \vspace{0.5cm}
    {\Large Trajectory Visualization Report\par}
    \vspace{1cm}
    {\large\textcolor{textmuted}{Version %(version)s}\par}
    \vspace{2cm}

    \begin{tabular}{rl}
        \textbf{Generated:} & %(timestamp)s \\
        \textbf{Documents:} & %(total_docs)d \\
        \textbf{Revisions:} & %(total_revisions)d \\
        \textbf{Total Injections:} & %(total_injections)d \\
    \end{tabular}

    \vspace{2cm}

    % State Summary
    \begin{tabular}{ccc}
        \textcolor{coldcolor}{\rule{1cm}{1cm}} &
        \textcolor{warmcolor}{\rule{1cm}{1cm}} &
        \textcolor{assimcolor}{\rule{1cm}{1cm}} \\
        \textbf{%(cold_count)d Cold} &
        \textbf{%(warm_count)d Warm} &
        \textbf{%(assimilated_count)d Assimilated}
    \end{tabular}

    \vfill

    {\small\textcolor{textmuted}{
        This report was generated by ScholaWrite v%(version)s.\\
        For more information, visit:
        \url{https://github.com/writerslogic/scholawrite-augmented}
    }\par}
\end{titlepage}

% ─────────────────────────────────────────────────────────────────────────────
% Table of Contents
% ─────────────────────────────────────────────────────────────────────────────
\tableofcontents
\newpage

% ─────────────────────────────────────────────────────────────────────────────
% Introduction
% ─────────────────────────────────────────────────────────────────────────────
\section{Overview}

This report presents a forensic visualization of AI-generated text injection
trajectories detected in scholarly writing samples. Each injection is tracked
through its lifecycle from initial insertion (\textcolor{coldcolor}{\textbf{cold}})
through partial integration (\textcolor{warmcolor}{\textbf{warm}}) to full
assimilation (\textcolor{assimcolor}{\textbf{assimilated}}).

\subsection{Trajectory States}

\begin{description}[leftmargin=2cm, style=nextline]
    \item[\textcolor{coldcolor}{Cold}]
        Initial injection state. The AI-generated text has just been inserted
        and shows clear machine-generated characteristics.

    \item[\textcolor{warmcolor}{Warm}]
        Partially integrated state. The injection has been modified through
        revisions and shows signs of human editing or stylistic adaptation.

    \item[\textcolor{assimcolor}{Assimilated}]
        Fully evolved state. The injection has been substantially rewritten
        and integrated into the surrounding human-authored text.
\end{description}

\subsection{Metrics Tracked}

Each injection includes:
\begin{itemize}[noitemsep]
    \item \textbf{Injection ID:} Unique identifier for traceability
    \item \textbf{Generator Class:} The type of generator that produced the text
    \item \textbf{Causal Trace:} Sequence of events during generation
    \item \textbf{Repair Count:} Number of self-repair operations performed
    \item \textbf{Glucose Level:} Simulated cognitive load at generation time
\end{itemize}

\newpage

% ─────────────────────────────────────────────────────────────────────────────
% Statistics
% ─────────────────────────────────────────────────────────────────────────────
\section{Statistics Summary}

\begin{table}[h]
\centering
\begin{tabular}{lr}
\toprule
\textbf{Metric} & \textbf{Value} \\
\midrule
Total Documents & %(total_docs)d \\
Total Revisions & %(total_revisions)d \\
Total Injections & %(total_injections)d \\
\midrule
Cold Injections & %(cold_count)d \\
Warm Injections & %(warm_count)d \\
Assimilated Injections & %(assimilated_count)d \\
\bottomrule
\end{tabular}
\caption{Overview of trajectory statistics}
\end{table}

%(state_distribution_chart)s

\newpage

% ─────────────────────────────────────────────────────────────────────────────
% Document Details
% ─────────────────────────────────────────────────────────────────────────────
\section{Document Analysis}

%(document_sections)s

% ─────────────────────────────────────────────────────────────────────────────
% Appendix: Citation
% ─────────────────────────────────────────────────────────────────────────────
\appendix
\section{How to Cite}

If you use ScholaWrite or this visualization in your research, please cite:

\begin{verbatim}
%(bibtex_citation)s
\end{verbatim}

\end{document}
"""


def _tex_escape(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
        ('<', r'\textless{}'),
        ('>', r'\textgreater{}'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _generate_tex_document_section(doc: AugmentedDocument, doc_index: int) -> str:
    """Generate LaTeX section for a single document."""
    lines = []

    # Document header
    doc_id_safe = _tex_escape(doc.doc_id[:40])
    lines.append(f"\\subsection{{Document: {doc_id_safe}...}}")
    lines.append("")

    # Count annotations
    total_ann = sum(len(rev.annotations) for rev in doc.revisions)
    lines.append(f"\\textbf{{Total Injections:}} {total_ann}")
    lines.append("")

    # Process each revision with annotations
    for rev in doc.revisions:
        if not rev.annotations:
            continue

        lines.append(f"\\subsubsection*{{Revision {rev.revision_index}}}")
        lines.append("")

        # Annotation summary table
        lines.append("\\begin{longtable}{@{}p{3cm}p{2cm}p{2cm}p{2cm}p{2cm}@{}}")
        lines.append("\\toprule")
        lines.append("\\textbf{ID} & \\textbf{State} & \\textbf{Level} & \\textbf{Repairs} & \\textbf{Glucose} \\\\")
        lines.append("\\midrule")
        lines.append("\\endhead")

        for ann in rev.annotations:
            state = ann.trajectory_state.value if ann.trajectory_state else "unknown"
            level = ann.injection_level.value if ann.injection_level else "unknown"
            repairs = sum(1 for e in ann.causal_trace if e.status == "repair") if ann.causal_trace else 0
            glucose = f"{ann.causal_trace[-1].glucose_at_event:.3f}" if ann.causal_trace and ann.causal_trace[-1].glucose_at_event else "---"

            ann_id_short = _tex_escape(ann.injection_id[:12])

            # Color-code the state
            if state == "cold":
                state_fmt = f"\\textcolor{{coldcolor}}{{{state}}}"
            elif state == "warm":
                state_fmt = f"\\textcolor{{warmcolor}}{{{state}}}"
            elif state == "assimilated":
                state_fmt = f"\\textcolor{{assimcolor}}{{{state}}}"
            else:
                state_fmt = state

            lines.append(f"\\texttt{{{ann_id_short}}} & {state_fmt} & {level} & {repairs} & {glucose} \\\\")

        lines.append("\\bottomrule")
        lines.append("\\end{longtable}")
        lines.append("")

        # Show a snippet of the text (first 300 chars)
        text_snippet = rev.text[:300]
        if len(rev.text) > 300:
            text_snippet += "..."

        lines.append("\\textbf{Text Preview:}")
        lines.append("\\begin{quote}")
        lines.append(f"\\small\\texttt{{{_tex_escape(text_snippet)}}}")
        lines.append("\\end{quote}")
        lines.append("")

    return "\n".join(lines)


def generate_tex_report(
    docs: List[AugmentedDocument],
    output_path: Optional[Path] = None,
    max_docs: int = 20,
) -> str:
    """Generate LaTeX/TeX report of trajectory data.

    Args:
        docs: List of augmented documents
        output_path: Optional path to write .tex file
        max_docs: Maximum number of documents to include

    Returns:
        Generated LaTeX string
    """
    docs = docs[:max_docs]

    # Calculate statistics
    total_revisions = sum(len(doc.revisions) for doc in docs)
    all_annotations = []
    for doc in docs:
        for rev in doc.revisions:
            all_annotations.extend(rev.annotations)

    cold_count = sum(1 for a in all_annotations if a.trajectory_state and a.trajectory_state.value == "cold")
    warm_count = sum(1 for a in all_annotations if a.trajectory_state and a.trajectory_state.value == "warm")
    assimilated_count = sum(1 for a in all_annotations if a.trajectory_state and a.trajectory_state.value == "assimilated")

    # Generate document sections
    document_sections = []
    for i, doc in enumerate(docs):
        section = _generate_tex_document_section(doc, i)
        document_sections.append(section)

    # Simple text-based state distribution (since we're not using pgfplots)
    total_inj = len(all_annotations)
    if total_inj > 0:
        cold_pct = (cold_count / total_inj) * 100
        warm_pct = (warm_count / total_inj) * 100
        assim_pct = (assimilated_count / total_inj) * 100

        state_distribution_chart = f"""
\\subsection{{State Distribution}}

\\begin{{center}}
\\begin{{tabular}}{{lcr}}
\\textcolor{{coldcolor}}{{\\rule{{6cm}}{{0.5cm}}}} & Cold & {cold_pct:.1f}\\% \\\\[0.2cm]
\\textcolor{{warmcolor}}{{\\rule{{{warm_pct * 0.06:.2f}cm}}{{0.5cm}}}} & Warm & {warm_pct:.1f}\\% \\\\[0.2cm]
\\textcolor{{assimcolor}}{{\\rule{{{assim_pct * 0.06:.2f}cm}}{{0.5cm}}}} & Assimilated & {assim_pct:.1f}\\% \\\\
\\end{{tabular}}
\\end{{center}}

\\textit{{Note: Bar widths are proportional to percentage of total injections.}}
"""
    else:
        state_distribution_chart = "\\textit{No injection data available.}"

    # Generate final TeX
    tex = TEX_TEMPLATE % {
        'version': VERSION,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_docs': len(docs),
        'total_revisions': total_revisions,
        'total_injections': len(all_annotations),
        'cold_count': cold_count,
        'warm_count': warm_count,
        'assimilated_count': assimilated_count,
        'state_distribution_chart': state_distribution_chart,
        'document_sections': "\n\n".join(document_sections),
        'bibtex_citation': CITATION_BIBTEX,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(tex, encoding='utf-8')

    return tex
