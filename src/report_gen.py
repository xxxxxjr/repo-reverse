"""Generate a beautiful HTML report from all analysis results."""

import json
import datetime
from .diagram_gen import (
    architecture_diagram, module_relationship_diagram,
    call_flow_diagrams, er_diagram, deployment_flow_diagram,
)


def severity_color(severity: str) -> str:
    return {"high": "#ef4444", "medium": "#f59e0b", "low": "#3b82f6"}.get(severity, "#6b7280")


def effort_badge(effort: str) -> str:
    colors = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"}
    return f'<span style="background:{colors.get(effort, "#999")};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">{effort}</span>'


def impact_badge(impact: str) -> str:
    colors = {"low": "#3b82f6", "medium": "#8b5cf6", "high": "#ef4444"}
    return f'<span style="background:{colors.get(impact, "#999")};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">{impact}</span>'


def generate_html(
    repo_url: str,
    tech_stack: dict,
    file_stats: dict,
    modules: list[dict],
    analysis: dict,
    static_only: bool = False,
) -> str:
    """Generate the complete HTML report."""

    arch_diag = architecture_diagram(analysis, modules)
    mod_diag = module_relationship_diagram(analysis, modules)
    flow_diags = call_flow_diagrams(analysis)
    erd = er_diagram(analysis)
    deploy_diag = deployment_flow_diagram(analysis)

    owner, name = _parse_url(repo_url)
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Banner for static-only reports
    static_banner = ""
    if static_only:
        static_banner = f'''    <div style="background:linear-gradient(135deg,#78350f,#451a03);border:1px solid #f59e0b;border-radius:12px;padding:20px 28px;margin-bottom:20px">
          <strong style="color:#fbbf24;font-size:1.1rem">⚠ Static Analysis Only</strong>
          <p style="color:#fcd34d;margin-top:8px">
            This report lacks AI-powered sections: <b>Bug Detection</b>, <b>Security Audit</b>, <b>Improvement Suggestions</b>, and <b>Redesign Proposal</b>.
          </p>
          <p style="color:#fcd34d;margin-top:4px">
            Get a free API key at <a href="https://console.anthropic.com" style="color:#fbbf24">console.anthropic.com</a>, then run:
          </p>
          <code style="display:block;background:#1a1d27;padding:12px;border-radius:8px;margin-top:8px;color:#e1e4ed;font-size:13px">
            export ANTHROPIC_API_KEY=sk-ant-...<br>
            python cli.py {repo_url}
          </code>
        </div>'''

    bugs_html = _render_bugs(analysis)
    security_html = _render_security(analysis)
    improvements_html = _render_improvements(analysis)
    modules_html = _render_modules(analysis)
    flows_html = _render_call_flows(analysis, flow_diags)
    db_html = _render_database(analysis, erd)
    deploy_html = _render_deployment(analysis, deploy_diag)
    redesign_html = _render_redesign(analysis)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Repo Reverse — {owner}/{name}</title>
<script src="https://unpkg.com/mermaid@10/dist/mermaid.min.js"></script>
<script>window.mermaid||document.write('<script src="https://registry.npmmirror.com/mermaid/10/files/dist/mermaid.min.js"><\/script>')</script>
<style>
:root {{
  --bg: #0f1117;
  --surface: #1a1d27;
  --border: #2a2d3a;
  --text: #e1e4ed;
  --text-muted: #8b8fa3;
  --accent: #6366f1;
  --accent2: #a78bfa;
  --green: #34d399;
  --red: #f87171;
  --yellow: #fbbf24;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}

/* Header */
.hero {{
  background: linear-gradient(135deg, #1a1d27 0%, #1e1b4b 50%, #1a1d27 100%);
  border-bottom: 1px solid var(--border);
  padding: 80px 0 60px;
  text-align: center;
}}
.hero h1 {{
  font-size: 3rem;
  font-weight: 800;
  background: linear-gradient(135deg, #e1e4ed, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero .subtitle {{
  font-size: 1.2rem;
  color: var(--text-muted);
  margin-top: 12px;
}}
.hero .meta {{
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 20px;
  flex-wrap: wrap;
}}
.hero .meta span {{
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 14px;
  color: var(--text-muted);
}}

/* Navigation */
nav {{
  position: sticky; top: 0; z-index: 100;
  background: rgba(15, 17, 23, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}}
nav .container {{
  display: flex;
  gap: 24px;
  overflow-x: auto;
  padding: 12px 24px;
}}
nav a {{
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
  white-space: nowrap;
  transition: color 0.2s;
}}
nav a:hover {{ color: var(--text); }}

/* Sections */
section {{
  padding: 60px 0;
  border-bottom: 1px solid var(--border);
}}
section h2 {{
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}}
section h2 .icon {{ font-size: 1.5rem; }}
section > .container > p {{
  color: var(--text-muted);
  margin-bottom: 32px;
}}

/* Cards */
.card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}}
.card h3 {{ font-size: 1.1rem; margin-bottom: 12px; }}

/* Grid */
.grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}

/* Stat numbers */
.stat-num {{
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}

/* Mermaid */
.mermaid-container {{
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  margin: 20px 0;
  overflow-x: auto;
}}

/* Bug / Issue List */
.issue {{
  border-left: 4px solid var(--red);
  padding: 16px 20px;
  margin-bottom: 12px;
  background: var(--surface);
  border-radius: 0 8px 8px 0;
}}
.issue.severity-high {{ border-left-color: var(--red); }}
.issue.severity-medium {{ border-left-color: var(--yellow); }}
.issue.severity-low {{ border-left-color: var(--green); }}
.issue .severity-tag {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}
.issue .location {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}

/* Improvement card */
.improvement-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}}
.improvement-card .area {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 8px;
}}
.improvement-card .badges {{
  display: flex;
  gap: 8px;
  margin-top: 12px;
}}

/* Redesign */
.redesign-box {{
  background: linear-gradient(135deg, #1e1b4b, #1a1d27);
  border: 1px solid #4c1d95;
  border-radius: 16px;
  padding: 40px;
  margin-top: 20px;
}}
.redesign-box h3 {{ color: var(--accent2); font-size: 1.4rem; }}
.redesign-box .new-stack {{
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin: 16px 0;
}}
.redesign-box .new-stack span {{
  background: #4c1d95;
  color: #c4b5fd;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
}}

/* Tags */
.tag {{
  display: inline-block;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 13px;
  margin: 2px;
}}

/* Footer */
footer {{
  text-align: center;
  padding: 40px 0;
  color: var(--text-muted);
  font-size: 14px;
}}

@media (max-width: 768px) {{
  .hero h1 {{ font-size: 2rem; }}
  section {{ padding: 40px 0; }}
}}
</style>
</head>
<body>

<div class="hero">
  <div class="container">
    <h1>{owner}/{name}</h1>
    <p class="subtitle">{analysis.get('architecture_summary', 'Repository Reverse Engineering Report')}</p>
    <div class="meta">
      <span>🖥 {tech_stack.get('primary_language', 'Unknown')}</span>
      <span>📁 {file_stats.get('total_files', 0):,} files</span>
      <span>📝 {file_stats.get('total_lines', 0):,} lines</span>
      <span>📅 {generated}</span>
    </div>
  </div>
</div>

{static_banner}
<nav>
  <div class="container">
    <a href="#architecture">🏗 Architecture</a>
    <a href="#modules">📦 Modules</a>
    <a href="#callflows">🔗 Call Flows</a>
    <a href="#database">🗄 Database</a>
    <a href="#deployment">🚀 Deployment</a>
    <a href="#bugs">🐛 Bugs</a>
    <a href="#security">🔒 Security</a>
    <a href="#improvements">💡 Improvements</a>
    <a href="#redesign">🔄 Redesign</a>
  </div>
</nav>

<!-- Architecture -->
<section id="architecture">
  <div class="container">
    <h2><span class="icon">🏗</span> Architecture Overview</h2>
    <p>Auto-detected architecture patterns and high-level structure</p>

    <div class="grid-2">
      <div class="card">
        <h3>Detected Patterns</h3>
        {''.join(f'<span class="tag">{p}</span>' for p in analysis.get('architecture_patterns', []))}
      </div>
      <div class="card">
        <h3>Tech Stack</h3>
        <p><strong>Primary:</strong> {tech_stack.get('primary_language', 'Unknown')}</p>
        <p><strong>Frameworks:</strong> {', '.join(tech_stack.get('frameworks_tools', [])[:8]) or 'None detected'}</p>
      </div>
    </div>

    <div class="card">
      <h3>Architecture Diagram</h3>
      <div class="mermaid-container">
        <pre class="mermaid">
{arch_diag}
        </pre>
      </div>
    </div>

    <div class="card">
      <h3>Module Relationship Graph</h3>
      <div class="mermaid-container">
        <pre class="mermaid">
{mod_diag}
        </pre>
      </div>
    </div>
  </div>
</section>

<!-- Modules -->
<section id="modules">
  <div class="container">
    <h2><span class="icon">📦</span> Module Analysis</h2>
    <p>Each module's responsibility, dependencies, and health assessment</p>
    {modules_html}
  </div>
</section>

<!-- Call Flows -->
<section id="callflows">
  <div class="container">
    <h2><span class="icon">🔗</span> Call Flow Analysis</h2>
    <p>Key runtime flows traced through the codebase</p>
    {flows_html}
  </div>
</section>

<!-- Database -->
<section id="database">
  <div class="container">
    <h2><span class="icon">🗄</span> Database Design</h2>
    <p>Inferred data model, entities, and relationships</p>
    {db_html}
  </div>
</section>

<!-- Deployment -->
<section id="deployment">
  <div class="container">
    <h2><span class="icon">🚀</span> Deployment Analysis</h2>
    <p>Infrastructure, CI/CD pipeline, and deployment concerns</p>
    {deploy_html}
  </div>
</section>

<!-- Bugs -->
<section id="bugs">
  <div class="container">
    <h2><span class="icon">🐛</span> Potential Bugs</h2>
    <p>Issues detected through static analysis and AI review</p>
    {bugs_html}
  </div>
</section>

<!-- Security -->
<section id="security">
  <div class="container">
    <h2><span class="icon">🔒</span> Security Review</h2>
    <p>Security vulnerabilities and hardening recommendations</p>
    {security_html}
  </div>
</section>

<!-- Improvements -->
<section id="improvements">
  <div class="container">
    <h2><span class="icon">💡</span> Improvement Suggestions</h2>
    <p>Actionable suggestions ranked by effort and impact</p>
    {improvements_html}
  </div>
</section>

<!-- Redesign -->
<section id="redesign">
  <div class="container">
    <h2><span class="icon">🔄</span> If I Were to Rewrite This Project...</h2>
    <p>An alternative architecture proposal — a clean-slate redesign</p>
    {redesign_html}
  </div>
</section>

<footer>
  <div class="container">
    <p>Generated by <strong>Repo Reverse</strong> — Reverse-engineer any GitHub repository into comprehensive design documentation.</p>
    <p style="margin-top:8px"><a href="{repo_url}" style="color:var(--accent)">{repo_url}</a></p>
  </div>
</footer>

<script>
mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
</script>
</body>
</html>"""


def _render_bugs(analysis: dict) -> str:
    bugs = analysis.get("potential_bugs", [])
    if not bugs:
        return '<div class="card"><p>No significant bugs detected.</p></div>'
    items = []
    for b in bugs[:12]:
        items.append(f'''
        <div class="issue severity-{b.get('severity', 'low')}">
          <span class="severity-tag" style="color:{severity_color(b.get('severity', 'low'))}">{b.get('severity', '?').upper()}</span>
          <strong> {b.get('description', 'No description')}</strong>
          <p style="margin-top:4px;color:var(--text-muted)">{b.get('impact', '')}</p>
          <div class="location">📍 {b.get('location', 'Unknown location')}</div>
        </div>''')
    return "\n".join(items)


def _render_security(analysis: dict) -> str:
    items = analysis.get("security_concerns", [])
    if not items:
        return '<div class="card"><p>No major security concerns detected.</p></div>'
    parts = []
    for s in items:
        parts.append(f'''
        <div class="issue severity-{s.get('severity', 'low')}">
          <span class="severity-tag" style="color:{severity_color(s.get('severity', 'low'))}">{s.get('severity', '?').upper()}</span>
          <strong> {s.get('description', '')}</strong>
          <p style="margin-top:4px;color:var(--text-muted)">💡 {s.get('recommendation', '')}</p>
        </div>''')
    return "\n".join(parts)


def _render_improvements(analysis: dict) -> str:
    items = analysis.get("improvement_suggestions", [])
    if not items:
        return '<div class="card"><p>No suggestions at this time.</p></div>'
    cards = []
    for imp in items[:12]:
        cards.append(f'''
        <div class="improvement-card">
          <div class="area">{imp.get('area', 'general').upper()}</div>
          <p>{imp.get('suggestion', '')}</p>
          <div class="badges">
            {effort_badge(imp.get('effort', 'medium'))}
            {impact_badge(imp.get('impact', 'medium'))}
          </div>
        </div>''')
    return f'<div class="grid-3">{"".join(cards)}</div>'


def _render_modules(analysis: dict) -> str:
    mods = analysis.get("module_analysis", [])
    if not mods:
        return '<div class="card"><p>Module analysis not available.</p></div>'
    cards = []
    for m in mods[:12]:
        health_icon = {"good": "✅", "warning": "⚠️", "bad": "❌"}.get(m.get("health", "good"), "✅")
        cards.append(f'''
        <div class="card">
          <h3>{health_icon} {m.get('name', 'Unknown')}</h3>
          <p>{m.get('responsibility', 'No description')}</p>
          <p style="margin-top:8px">{" ".join(f'<span class="tag">{d}</span>' for d in m.get('dependencies', [])[:8])}</p>
          <p style="margin-top:8px;color:var(--text-muted);font-size:13px">{m.get('notes', '')}</p>
        </div>''')
    return "\n".join(cards)


def _render_call_flows(analysis: dict, flow_diags: list[dict]) -> str:
    flows = analysis.get("call_flows", [])
    if not flows:
        return '<div class="card"><p>No call flows analyzed.</p></div>'

    parts = []
    for i, flow in enumerate(flow_diags):
        flow_data = flows[i] if i < len(flows) else {}
        parts.append(f'''
        <div class="card">
          <h3>{flow_data.get('name', flow['name'])}</h3>
          <ol style="padding-left:20px;color:var(--text-muted)">
            {''.join(f'<li>{s}</li>' for s in flow_data.get('steps', []))}
          </ol>
          <div class="mermaid-container" style="margin-top:16px">
            <pre class="mermaid">
{flow['diagram']}
            </pre>
          </div>
        </div>''')
    return "\n".join(parts)


def _render_database(analysis: dict, er_diagram_str: str) -> str:
    db = analysis.get("database_design", {})
    entities = db.get("entities", [])
    relationships = db.get("relationships", [])
    concerns = db.get("concerns", [])

    parts = []
    parts.append(f'''
    <div class="grid-2">
      <div class="card">
        <h3>Database Info</h3>
        <p><strong>Type:</strong> {db.get('type', 'Unknown')}</p>
        <p><strong>ORM:</strong> {db.get('orm', 'None detected')}</p>
      </div>
      <div class="card">
        <h3>Entities ({len(entities)})</h3>
        <p>{" ".join(f'<span class="tag">{e}</span>' for e in entities[:15])}</p>
      </div>
    </div>''')

    if relationships:
        parts.append(f'''
    <div class="card">
      <h3>Relationships</h3>
      <ul style="padding-left:20px;color:var(--text-muted)">
        {"".join(f'<li>{r}</li>' for r in relationships)}
      </ul>
    </div>''')

    parts.append(f'''
    <div class="card">
      <h3>Entity-Relationship Diagram</h3>
      <div class="mermaid-container">
        <pre class="mermaid">
{er_diagram_str}
        </pre>
      </div>
    </div>''')

    if concerns:
        parts.append(f'''
    <div class="card">
      <h3>⚠️ Concerns</h3>
      <ul style="padding-left:20px;color:var(--text-muted)">
        {"".join(f'<li>{c}</li>' for c in concerns)}
      </ul>
    </div>''')

    return "\n".join(parts)


def _render_deployment(analysis: dict, deploy_diag: str) -> str:
    deploy = analysis.get("deployment_analysis", {})
    concerns = deploy.get("concerns", [])
    parts = [f'''
    <div class="grid-2">
      <div class="card">
        <h3>Infrastructure</h3>
        <p>{deploy.get('infrastructure', 'Not analyzed')}</p>
      </div>
      <div class="card">
        <h3>CI/CD</h3>
        <p>{deploy.get('ci_cd', 'Not analyzed')}</p>
      </div>
    </div>

    <div class="card">
      <h3>Deployment Pipeline</h3>
      <div class="mermaid-container">
        <pre class="mermaid">
{deploy_diag}
        </pre>
      </div>
    </div>''']
    if concerns:
        parts.append(f'''
    <div class="card">
      <h3>⚠️ Deployment Concerns</h3>
      <ul style="padding-left:20px;color:var(--text-muted)">
        {"".join(f'<li>{c}</li>' for c in concerns)}
      </ul>
    </div>''')
    return "\n".join(parts)


def _render_redesign(analysis: dict) -> str:
    redesign = analysis.get("redesign_proposal", {})
    if not redesign:
        return '<div class="card"><p>No redesign proposal generated.</p></div>'

    return f'''
    <div class="redesign-box">
      <h3>🎯 Proposed Architecture: {redesign.get('architecture', 'N/A')}</h3>
      <p style="margin-top:16px;font-size:1.1rem">{redesign.get('design_rationale', '')}</p>
      <div class="new-stack">
        {''.join(f'<span>{t.strip()}</span>' for t in redesign.get('tech_stack_changes', '').split('→') if t.strip())}
      </div>
      <p style="margin-top:16px;color:var(--text-muted)">📊 <strong>Estimated effort:</strong> {redesign.get('estimated_effort', 'Unknown')}</p>
      <div style="margin-top:16px">
        <h4 style="color:var(--accent2)">New Architecture Diagram</h4>
        <div class="mermaid-container">
          <pre class="mermaid">
graph TB
  title[{redesign.get('key_diagram_description', 'New Architecture')}]
          </pre>
        </div>
      </div>
    </div>'''


def _parse_url(url: str) -> tuple[str, str]:
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "unknown", "unknown"
