"""Static code analysis — file stats, module detection, dependency mapping."""

import os
import re
from pathlib import Path
from collections import defaultdict


class StaticAnalyzer:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    # ── file stats ──────────────────────────────────────────────
    def file_stats(self) -> dict:
        total_files = 0
        total_lines = 0
        ext_counts: dict[str, int] = defaultdict(int)
        ext_lines: dict[str, int] = defaultdict(int)

        SKIP_DIRS = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            "dist", "build", "target", ".next", ".turbo", "vendor",
            ".cache", ".idea", ".vscode", "coverage", ".nyc_output",
        }

        for f in self.repo_path.rglob("*"):
            if f.is_file() and not any(p in SKIP_DIRS for p in f.parts):
                total_files += 1
                ext = f.suffix or "(no ext)"
                ext_counts[ext] += 1
                try:
                    lines = sum(1 for _ in open(f, encoding="utf-8", errors="replace"))
                    total_lines += lines
                    ext_lines[ext] += lines
                except Exception:
                    pass

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "extensions": dict(sorted(ext_counts.items(), key=lambda x: -x[1])[:15]),
        }

    # ── module detection ────────────────────────────────────────
    def detect_modules(self) -> list[dict]:
        """Group top-level and second-level dirs into logical modules."""
        modules = []
        SKIP = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            "dist", "build", "target", ".next", ".github", ".circleci",
            "test", "tests", "spec", "__tests__", "e2e", "coverage",
            "docs", "doc", "examples", "example", "assets", "static",
            "public", "scripts", "tools", ".vscode", ".idea", "vendor",
        }

        for entry in sorted(self.repo_path.iterdir()):
            if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP:
                continue

            subdirs = [d.name for d in entry.iterdir() if d.is_dir() and not d.name.startswith(".")]
            files = [f.name for f in entry.iterdir() if f.is_file() and not f.name.startswith(".")]

            # Count lines in this module
            line_count = 0
            for f in entry.rglob("*"):
                if f.is_file():
                    try:
                        line_count += sum(1 for _ in open(f, encoding="utf-8", errors="replace"))
                    except Exception:
                        pass

            modules.append({
                "name": entry.name,
                "subdirs": subdirs[:10],
                "files": files[:15],
                "file_count": sum(1 for _ in entry.rglob("*") if _.is_file()),
                "line_count": line_count,
            })

        modules.sort(key=lambda m: m["line_count"], reverse=True)
        return modules

    # ── dependency detection ────────────────────────────────────
    def detect_dependencies(self) -> dict:
        """Extract explicit dependencies from package manifests."""
        deps = {}

        # Python
        req = self.repo_path / "requirements.txt"
        if req.exists():
            lines = req.read_text().splitlines()
            py_deps = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    pkg = re.split(r"[=<>~!]", line)[0].strip()
                    py_deps.append(pkg)
            if py_deps:
                deps["python"] = py_deps[:30]

        # Node.js
        pkg_json = self.repo_path / "package.json"
        if pkg_json.exists():
            import json
            try:
                data = json.loads(pkg_json.read_text())
                all_deps = {}
                all_deps.update(data.get("dependencies", {}))
                all_deps.update(data.get("devDependencies", {}))
                deps["nodejs"] = list(all_deps.keys())[:40]
            except Exception:
                pass

        # Go
        go_mod = self.repo_path / "go.mod"
        if go_mod.exists():
            go_deps = []
            for line in go_mod.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("module") and not line.startswith("go "):
                    parts = line.split()
                    if parts:
                        go_deps.append(parts[0])
            if go_deps:
                deps["go"] = go_deps[:30]

        # Rust
        cargo = self.repo_path / "Cargo.toml"
        if cargo.exists():
            rust_deps = []
            in_deps = False
            for line in cargo.read_text().splitlines():
                if line.strip().startswith("[dependencies"):
                    in_deps = True
                elif line.strip().startswith("["):
                    in_deps = False
                elif in_deps and "=" in line:
                    rust_deps.append(line.split("=")[0].strip())
            if rust_deps:
                deps["rust"] = rust_deps[:30]

        return deps

    # ── import graph (simple heuristic) ─────────────────────────
    def build_import_graph(self, max_files: int = 100) -> dict[str, list[str]]:
        """Build a simple import graph: {file: [imported_modules]}."""
        graph: dict[str, list[str]] = {}
        import_patterns = {
            ".py": [re.compile(r"^(?:from|import)\s+(\S+)")],
            ".js": [re.compile(r"(?:import|require)\s*\(?['\"](\S+)['\"]"), re.compile(r"from\s+['\"](\S+)['\"]")],
            ".ts": [re.compile(r"(?:import|require)\s*\(?['\"](\S+)['\"]"), re.compile(r"from\s+['\"](\S+)['\"]")],
            ".go": [re.compile(r"import\s+[\"(](\S+)[\"\)]"), re.compile(r"^\s+\"(\S+)\"")],
        }

        files = [f for f in self.repo_path.rglob("*") if f.is_file() and f.suffix in import_patterns]
        for f in files[:max_files]:
            rel = str(f.relative_to(self.repo_path))
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            imports = set()
            for pat in import_patterns.get(f.suffix, []):
                for m in pat.findall(content):
                    # clean up multi-import lines
                    mod = m.split("/")[0].split(".")[0].strip("\"'")
                    if mod and len(mod) > 1 and not mod.startswith((".", "/", "@")):
                        imports.add(mod)
            if imports:
                graph[rel] = sorted(imports)[:15]
        return graph

    # ── deployment flow inference ───────────────────────────────
    def infer_deployment_flow(self, deployment_files: list[str]) -> str:
        """Infer a deployment flow narrative from config files."""
        flow = []
        if any("Dockerfile" in f for f in deployment_files):
            flow.append("1. Container build via Docker")
        if any("docker-compose" in f for f in deployment_files):
            flow.append("2. Multi-service orchestration via Docker Compose")
        if any(".github/workflows" in f for f in deployment_files):
            flow.append("3. CI/CD pipeline via GitHub Actions")
        if any("kubernetes" in f.lower() for f in deployment_files):
            flow.append("4. Orchestrated deployment to Kubernetes cluster")
        if any("terraform" in f.lower() for f in deployment_files):
            flow.append("5. Infrastructure as Code via Terraform")
        if any("helm" in f.lower() for f in deployment_files):
            flow.append("6. Package management via Helm charts")
        if any("fly.toml" in f for f in deployment_files):
            flow.append("→ Deploy to Fly.io")
        if any("vercel.json" in f for f in deployment_files):
            flow.append("→ Deploy to Vercel")
        if any("netlify.toml" in f for f in deployment_files):
            flow.append("→ Deploy to Netlify")
        if any("render.yaml" in f for f in deployment_files):
            flow.append("→ Deploy to Render")
        return "\n".join(flow) if flow else "No automated deployment configuration detected."
