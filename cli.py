#!/usr/bin/env python3
"""Repo Reverse — Reverse-engineer any GitHub repository into design documentation.

Usage:
    python cli.py https://github.com/owner/repo
    python cli.py /path/to/local/repo
    python cli.py https://github.com/owner/repo --output report.html
    python cli.py https://github.com/owner/repo --no-ai  # static analysis only

Environment variables:
    ANTHROPIC_API_KEY   Your Anthropic API key (required for AI analysis)
"""

import os
import sys
import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.fetcher import RepoFetcher
from src.static_analyzer import StaticAnalyzer
from src.report_gen import generate_html

console = Console()


def build_ai_context(
    fetcher: RepoFetcher,
    analyzer: StaticAnalyzer,
    readme: str,
    file_tree: list[str],
    tech_stack: dict,
    deploys: list[str],
    deploy_flow: str,
    modules: list[dict],
    file_stats: dict,
    deps: dict,
    import_graph: dict,
    db_schemas: list[str],
    entry_points: list[str],
) -> str:
    """Assemble context for the AI model."""
    parts = []

    parts.append(f"=== README ===\n{readme}\n")

    parts.append("=== FILE TREE ===\n" + "\n".join(file_tree) + "\n")

    parts.append(f"=== TECH STACK ===\n{json.dumps(tech_stack, indent=2)}\n")

    parts.append(f"=== MODULES ===\n{json.dumps(modules[:15], indent=2)}\n")

    parts.append(f"=== FILE STATS ===\n{json.dumps(file_stats, indent=2)}\n")

    parts.append(f"=== DEPENDENCIES ===\n{json.dumps(deps, indent=2)}\n")

    parts.append(f"=== IMPORT GRAPH (sample) ===\n{json.dumps({k: v for k, v in list(import_graph.items())[:30]}, indent=2)}\n")

    parts.append(f"=== DATABASE SCHEMA FILES ===\n{json.dumps(db_schemas, indent=2)}\n")

    parts.append(f"=== ENTRY POINTS ===\n{json.dumps(entry_points, indent=2)}\n")

    parts.append(f"=== DEPLOYMENT CONFIGS ===\n{json.dumps(deploys, indent=2)}\n")
    parts.append(f"=== INFERRED DEPLOYMENT FLOW ===\n{deploy_flow}\n")

    # Read key source files
    key_files = entry_points[:5] + db_schemas[:3] + deploys[:5]
    if key_files:
        source_content = fetcher.read_key_files(key_files, max_bytes=6000)
        parts.append("=== KEY SOURCE FILES ===\n")
        for path, content in source_content.items():
            parts.append(f"--- {path} ---\n{content}\n")

    return "\n".join(parts)


@click.command()
@click.argument("repo_url")
@click.option("--output", "-o", default=None, help="Output HTML file path")
@click.option("--output-dir", "-d", default=".", help="Output directory")
@click.option("--api-key", "-k", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY)")
@click.option("--model", "-m", default="claude-sonnet-4-6", help="Claude model to use")
@click.option("--no-ai", is_flag=True, help="Skip AI analysis (static only)")
@click.option("--keep-repo", is_flag=True, help="Keep cloned repo after analysis")
@click.option("--max-depth", default=4, help="Max file tree depth")
def main(repo_url, output, output_dir, api_key, model, no_ai, keep_repo, max_depth):
    """Reverse-engineer a GitHub repository into design documentation."""

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    static_only = no_ai or not api_key
    if not no_ai and not api_key:
        console.print()
        console.print(Panel.fit(
            "[bold yellow]⚠ No API Key Detected[/bold yellow]\n\n"
            "Running [bold]static analysis only[/bold].\n"
            "The report will NOT include:\n"
            "  • Bug detection\n"
            "  • Security audit\n"
            "  • Improvement suggestions\n"
            "  • Redesign proposal\n\n"
            "[dim]Get your free API key at https://console.anthropic.com\n"
            "Then run again with: --api-key YOUR_KEY  or  export ANTHROPIC_API_KEY=YOUR_KEY[/dim]",
            border_style="yellow"
        ))
        console.print()
        no_ai = True

    is_local = os.path.isdir(repo_url)
    if is_local:
        abs_path = os.path.abspath(repo_url)
        owner = os.path.basename(os.path.dirname(abs_path)) or "local"
        name = os.path.basename(abs_path)
        display_url = abs_path
    else:
        display_url = repo_url
        parts = repo_url.rstrip("/").split("/")
        owner, name = parts[-2], parts[-1]

    if not output:
        output = os.path.join(output_dir, f"repo-reverse-{owner}-{name}.html")

    # ── Phase 1: Fetch ────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Repo Reverse[/bold cyan]\n[dim]{display_url}[/dim]",
        border_style="cyan"
    ))

    fetcher = RepoFetcher(repo_url)
    if is_local:
        console.print(f"  [dim]Using local directory: {fetcher.repo_path}[/dim]")
    else:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
            task = p.add_task("[cyan]Cloning repository...", total=None)
            try:
                fetcher.clone()
            except Exception as e:
                console.print(f"[red]Failed to clone: {e}[/red]")
                console.print("[yellow]Try using a local path or check your network/GitHub proxy settings.[/yellow]")
                sys.exit(1)
            p.update(task, description="[green]Cloned successfully")

    # ── Phase 2: Static analysis ──────────────────────────────
    analyzer = StaticAnalyzer(fetcher.repo_path)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Running static analysis...", total=None)

        readme = fetcher.get_readme()
        file_tree = fetcher.get_file_tree(max_depth)
        tech_stack = fetcher.detect_tech_stack()
        deploys = fetcher.find_deployment_configs()
        db_schemas = fetcher.find_db_schemas()
        entry_points = fetcher.find_entry_points()

        file_stats = analyzer.file_stats()
        modules = analyzer.detect_modules()
        deps = analyzer.detect_dependencies()
        import_graph = analyzer.build_import_graph()
        deploy_flow = analyzer.infer_deployment_flow(deploys)

        p.update(task, description="[green]✓ Static analysis complete")

    # ── Print summary ─────────────────────────────────────────
    console.print()
    table = Table(title="Project Overview", title_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Primary Language", tech_stack["primary_language"])
    table.add_row("Total Files", f"{file_stats['total_files']:,}")
    table.add_row("Total Lines", f"{file_stats['total_lines']:,}")
    table.add_row("Modules Detected", str(len(modules)))
    table.add_row("Entry Points", str(len(entry_points)))
    table.add_row("DB Schema Files", str(len(db_schemas)))
    table.add_row("Deploy Configs", str(len(deploys)))
    table.add_row("Frameworks/Tools", ", ".join(tech_stack["frameworks_tools"][:6]) or "None detected")
    console.print(table)

    # ── Phase 3: AI analysis ──────────────────────────────────
    analysis = {}
    if not no_ai:
        console.print()
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
            task = p.add_task("[cyan]Running AI deep analysis (this may take 1-2 minutes)...", total=None)

            context = build_ai_context(
                fetcher, analyzer, readme, file_tree, tech_stack,
                deploys, deploy_flow, modules, file_stats, deps, import_graph,
                db_schemas, entry_points,
            )

            try:
                from src.ai_analyzer import analyze
                base_url = os.environ.get("ANTHROPIC_BASE_URL")
                analysis = analyze(context, api_key, model, base_url)
                p.update(task, description="[green]✓ AI analysis complete")
            except Exception as e:
                console.print(f"[red]AI analysis failed: {e}[/red]")
                console.print("[yellow]Falling back to static-only report.[/yellow]")
                analysis = {}

    # If AI analysis is empty, provide a minimal static-only analysis
    if not analysis:
        analysis = {
            "architecture_summary": f"A {tech_stack['primary_language']} project with {file_stats['total_files']:,} files across {len(modules)} modules.",
            "architecture_patterns": ["Detected from static analysis"],
            "module_analysis": [
                {
                    "name": m["name"],
                    "responsibility": f"Contains {m.get('file_count', 0)} files, ~{m.get('line_count', 0)} lines",
                    "dependencies": list(import_graph.get(m["name"], []))[:5] if m["name"] in import_graph else [],
                    "health": "good" if m.get("file_count", 0) < 50 else "warning",
                    "notes": "Static analysis only — run with AI for deeper insights",
                }
                for m in modules[:10]
            ],
            "call_flows": [],
            "database_design": {
                "type": "Unknown",
                "orm": "None detected",
                "entities": [],
                "relationships": [],
                "concerns": ["Run with AI analysis enabled for database insights"],
            },
            "deployment_analysis": {
                "infrastructure": deploy_flow if deploy_flow else "No deployment configs found",
                "ci_cd": "Detected from config files" if deploys else "No CI/CD configs found",
                "concerns": [],
            },
            "potential_bugs": [],
            "security_concerns": [],
            "improvement_suggestions": [],
            "redesign_proposal": {},
        }

    # ── Phase 4: Generate report ──────────────────────────────
    console.print()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Generating HTML report...", total=None)
        html = generate_html(display_url, tech_stack, file_stats, modules, analysis, static_only=static_only)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
        p.update(task, description="[green]✓ Report generated")

    # ── Cleanup ───────────────────────────────────────────────
    if not is_local and not keep_repo:
        fetcher.cleanup()

    console.print()
    if static_only:
        console.print(Panel.fit(
            f"[bold]Report generated (static analysis only)[/bold]\n[dim]{output}[/dim]\n\n"
            f"Open with: [cyan]open {output}[/cyan] or [cyan]xdg-open {output}[/cyan]\n\n"
            f"[bold yellow]Want the full picture?[/bold yellow]\n"
            f"[dim]  export ANTHROPIC_API_KEY=sk-ant-...\n"
            f"  python cli.py {display_url}[/dim]",
            border_style="yellow"
        ))
    else:
        console.print(Panel.fit(
            f"[bold green]Report generated![/bold green]\n[dim]{output}[/dim]\n\n"
            f"Open with: [cyan]open {output}[/cyan] or [cyan]xdg-open {output}[/cyan]",
            border_style="green"
        ))
    console.print()


if __name__ == "__main__":
    main()
