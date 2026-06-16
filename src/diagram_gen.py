"""Generate Mermaid diagrams from analysis results."""


def architecture_diagram(analysis: dict, modules: list[dict]) -> str:
    """Generate a high-level architecture overview diagram."""
    lines = ["graph TB"]
    lines.append("  title[Project Architecture Overview]")
    lines.append("  style title fill:none,stroke:none")

    mod_names = [m["name"] for m in modules[:10]]
    if not mod_names:
        mod_names = ["src", "lib", "api", "db", "ui"]

    # Entry point
    lines.append("  User([User/Client]) --> API[API Layer]")

    # Group modules
    for i, mod in enumerate(mod_names):
        node_id = mod.replace("-", "_").replace(".", "_")
        lines.append(f"  API --> {node_id}[{mod}]")

    # Data layer
    lines.append(f'  {mod_names[0].replace("-", "_").replace(".", "_")} --> DB[(Database)]')
    lines.append("  DB --> Cache[(Cache)]")

    # External
    for mod in analysis.get("module_analysis", [])[:8]:
        for dep in mod.get("dependencies", [])[:2]:
            dep_id = dep.replace("-", "_").replace(".", "_")
            src_id = mod["name"].replace("-", "_").replace(".", "_")
            lines.append(f"  {src_id} -.-> {dep_id}[{dep}]")

    return "\n".join(lines)


def module_relationship_diagram(analysis: dict, modules: list[dict]) -> str:
    """Generate a module dependency graph."""
    lines = ["graph LR"]

    for mod in modules[:12]:
        node_id = mod["name"].replace("-", "_").replace(".", "_")
        file_count = mod.get("file_count", 0)
        lines.append(f"  {node_id}[[{mod['name']}<br/>({file_count} files)]]")

    # Edges from AI analysis
    for mod in analysis.get("module_analysis", [])[:12]:
        src_id = mod["name"].replace("-", "_").replace(".", "_")
        for dep in mod.get("dependencies", [])[:3]:
            dep_id = dep.replace("-", "_").replace(".", "_")
            lines.append(f"  {src_id} --> {dep_id}")

    return "\n".join(lines)


def call_flow_diagrams(analysis: dict) -> list[dict]:
    """Generate a sequence diagram for each call flow."""
    diagrams = []
    for flow in analysis.get("call_flows", [])[:5]:
        lines = ["sequenceDiagram"]
        participants = set()
        for step in flow.get("steps", []):
            for comp in flow.get("components_involved", []):
                if comp not in participants:
                    lines.append(f"  participant {comp}")
                    participants.add(comp)
        for i, step in enumerate(flow.get("steps", [])):
            comp = flow["components_involved"][i % len(flow["components_involved"])] if flow.get("components_involved") else "System"
            lines.append(f"  Note over {comp}: {step}")
        diagrams.append({
            "name": flow.get("name", "Flow"),
            "diagram": "\n".join(lines),
        })
    return diagrams


def er_diagram(analysis: dict) -> str:
    """Generate an entity-relationship diagram from DB analysis."""
    db = analysis.get("database_design", {})
    entities = db.get("entities", [])
    relationships = db.get("relationships", [])

    if not entities:
        return "erDiagram\n  // No entities detected by AI analysis"

    lines = ["erDiagram"]
    for rel in relationships[:20]:
        # Simple format: "User ||--o{ Post : has"
        lines.append(f"  {rel}")

    for entity in entities[:10]:
        lines.append(f"  {entity} {{")
        lines.append("    int id PK")
        lines.append(f"    // See database analysis for full schema")
        lines.append("  }")

    return "\n".join(lines)


def deployment_flow_diagram(analysis: dict) -> str:
    """Generate a deployment pipeline diagram."""
    deploy = analysis.get("deployment_analysis", {})
    infra = deploy.get("infrastructure", "")

    lines = ["graph LR"]
    lines.append("  Dev[Developer Push] --> CI[CI Pipeline]")

    if "GitHub Actions" in infra or "GitHub" in infra:
        lines.append("  CI --> GH[GitHub Actions]")
        lines.append("  GH --> Test[Run Tests]")
    elif "GitLab" in infra:
        lines.append("  CI --> GL[GitLab CI]")
        lines.append("  GL --> Test[Run Tests]")
    else:
        lines.append("  CI --> Test[Run Tests]")

    lines.append("  Test --> Build[Build Image]")

    if "Docker" in infra:
        lines.append("  Build --> Registry[Container Registry]")

    if "Kubernetes" in infra or "K8s" in infra:
        lines.append("  Registry --> K8s[Kubernetes Cluster]")
        lines.append("  K8s --> Prod[Production]")
    elif "Vercel" in infra:
        lines.append("  Build --> Vercel[Vercel Deploy]")
        lines.append("  Vercel --> Prod[Production]")
    elif "Fly" in infra:
        lines.append("  Build --> Fly[Fly.io Deploy]")
        lines.append("  Fly --> Prod[Production]")
    else:
        lines.append("  Build --> Server[Server Deploy]")
        lines.append("  Server --> Prod[Production]")

    lines.append("  Prod --> Monitor[Monitoring]")
    return "\n".join(lines)
