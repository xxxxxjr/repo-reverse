"""GitHub repo fetcher — clone, extract metadata, parse README."""

import os
import re
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


class RepoFetcher:
    def __init__(self, url: str, work_dir: str | None = None):
        self.is_local = os.path.isdir(url)
        if self.is_local:
            self.url = url
            self.owner = "local"
            self.name = os.path.basename(os.path.abspath(url))
            self.repo_path: Path | None = Path(os.path.abspath(url))
        else:
            self.url = self._normalize_url(url)
            self.owner, self.name = self._parse_github_url(self.url)
            self.repo_path: Path | None = None
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="repo-reverse-"))

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = url.strip().rstrip("/")
        if not url.startswith("https://github.com/"):
            raise ValueError(f"Expected a GitHub URL, got: {url}")
        return url

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse owner/repo from: {url}")
        return parts[0], parts[1]

    def clone(self) -> Path:
        target = self.work_dir / self.name
        if target.exists():
            shutil.rmtree(target)

        print(f"  Cloning {self.owner}/{self.name} ...")
        subprocess.run(
            ["git", "clone", "--depth", "1", self.url, str(target)],
            check=True, capture_output=True, timeout=120,
        )
        self.repo_path = target
        return target

    def get_file_tree(self, max_depth: int = 4) -> list[str]:
        """Return a truncated file tree for AI context."""
        if not self.repo_path:
            raise RuntimeError("Clone first")

        lines = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
                "node_modules", "__pycache__", ".git", "venv", ".venv",
                "dist", "build", "target", ".next", ".turbo", "vendor",
            }]
            rel = os.path.relpath(root, self.repo_path)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth > max_depth:
                continue
            prefix = "  " * depth + ("├── " if depth > 0 else "")
            lines.append(f"{prefix}{os.path.basename(root)}/")
            for f in sorted(files)[:30]:
                if f.startswith("."):
                    continue
                file_prefix = "  " * (depth + 1) + "├── "
                lines.append(f"{file_prefix}{f}")
        return lines

    def detect_tech_stack(self) -> dict:
        """Detect languages, frameworks, and tools from config files."""
        if not self.repo_path:
            raise RuntimeError("Clone first")

        indicators = {
            "package.json": "Node.js / JavaScript",
            "tsconfig.json": "TypeScript",
            "requirements.txt": "Python",
            "pyproject.toml": "Python",
            "setup.py": "Python",
            "Pipfile": "Python",
            "go.mod": "Go",
            "go.sum": "Go",
            "Cargo.toml": "Rust",
            "Cargo.lock": "Rust",
            "Gemfile": "Ruby",
            "pom.xml": "Java (Maven)",
            "build.gradle": "Java/Kotlin (Gradle)",
            "build.gradle.kts": "Kotlin (Gradle)",
            "composer.json": "PHP",
            "CMakeLists.txt": "C/C++ (CMake)",
            "Makefile": "C/C++ (Make)",
            "Dockerfile": "Docker",
            "docker-compose.yml": "Docker Compose",
            "docker-compose.yaml": "Docker Compose",
            ".github/workflows/": "GitHub Actions",
            "next.config.js": "Next.js",
            "next.config.ts": "Next.js",
            "vite.config.js": "Vite",
            "vite.config.ts": "Vite",
            "webpack.config.js": "Webpack",
            "tailwind.config.js": "Tailwind CSS",
            "tailwind.config.ts": "Tailwind CSS",
            "prisma/schema.prisma": "Prisma ORM",
            "drizzle.config.ts": "Drizzle ORM",
            "knexfile.js": "Knex ORM",
            "alembic.ini": "SQLAlchemy/Alembic",
            "Dockerfile": "Docker",
            "kubernetes/": "Kubernetes",
            "helm/": "Helm",
            "terraform": "Terraform",
            "ansible.cfg": "Ansible",
            "nginx.conf": "Nginx",
        }

        found = []
        for filename, label in indicators.items():
            if filename.endswith("/"):
                if (self.repo_path / filename).is_dir():
                    found.append(label)
            elif (self.repo_path / filename).exists():
                found.append(label)

        # Count language extensions
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".tsx": "TypeScript/React", ".jsx": "JavaScript/React",
            ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
            ".swift": "Swift", ".c": "C", ".cpp": "C++", ".h": "C/C++ Header",
            ".rb": "Ruby", ".php": "PHP", ".scala": "Scala",
            ".vue": "Vue.js", ".svelte": "Svelte",
        }
        ext_counts: dict[str, int] = {}
        for f in self.repo_path.rglob("*"):
            if f.is_file() and f.suffix in ext_map:
                lang = ext_map[f.suffix]
                ext_counts[lang] = ext_counts.get(lang, 0) + 1

        primary_lang = max(ext_counts, key=ext_counts.get) if ext_counts else "Unknown"

        return {
            "primary_language": primary_lang,
            "languages": dict(sorted(ext_counts.items(), key=lambda x: -x[1])),
            "frameworks_tools": list(set(found)),
        }

    def find_entry_points(self) -> list[str]:
        """Find likely entry point files."""
        if not self.repo_path:
            raise RuntimeError("Clone first")

        patterns = [
            "main.py", "app.py", "server.py", "run.py", "manage.py", "wsgi.py",
            "index.js", "app.js", "server.js", "main.js",
            "main.go", "cmd/",
            "src/main.rs", "main.rs",
            "src/main/java/**/Application.java",
            "public/index.php", "index.php",
        ]

        found = []
        for pattern in patterns:
            if pattern.endswith("/"):
                p = self.repo_path / pattern
                if p.is_dir():
                    found.append(pattern)
            else:
                matches = list(self.repo_path.rglob(pattern))
                for m in matches:
                    rel = m.relative_to(self.repo_path)
                    found.append(str(rel))
        return found[:10]

    def find_db_schemas(self) -> list[str]:
        """Find database schema / migration files."""
        if not self.repo_path:
            raise RuntimeError("Clone first")

        patterns = [
            "**/migrations/**/*.sql",
            "**/migrations/**/*.py",
            "**/migrations/**/*.ts",
            "**/prisma/schema.prisma",
            "**/*.prisma",
            "**/schema.sql",
            "**/schema.rb",
            "**/models.py",
            "**/models/**/*.py",
            "**/entities/**/*.ts",
        ]
        found = set()
        for pattern in patterns:
            for m in self.repo_path.rglob(pattern):
                if m.is_file():
                    rel = m.relative_to(self.repo_path)
                    found.add(str(rel))
        return sorted(found)[:20]

    def find_deployment_configs(self) -> list[str]:
        """Find deployment and CI/CD configuration files."""
        if not self.repo_path:
            raise RuntimeError("Clone first")

        patterns = [
            "Dockerfile", "Dockerfile.*", "docker-compose.yml", "docker-compose.yaml",
            ".github/workflows/*.yml", ".github/workflows/*.yaml",
            ".gitlab-ci.yml", "Jenkinsfile",
            "kubernetes/**/*.yaml", "kubernetes/**/*.yml",
            "helm/**/*.yaml", "helm/**/*.yml",
            "terraform/**/*.tf",
            "ansible.cfg", "ansible/**/*.yml",
            "deploy/**/*", "deployment/**/*",
            "fly.toml", "vercel.json", "netlify.toml", "render.yaml",
            "railway.json", "heroku.yml", "app.yaml",
            ".github/**/*", "cloudbuild.yaml", "buildspec.yml",
        ]
        found = set()
        for pattern in patterns:
            for m in self.repo_path.glob(pattern):
                if m.is_file():
                    rel = m.relative_to(self.repo_path)
                    found.add(str(rel))
        return sorted(found)

    def read_key_files(self, paths: list[str], max_bytes: int = 8000) -> dict[str, str]:
        """Read specified files, truncating large ones."""
        if not self.repo_path:
            raise RuntimeError("Clone first")

        results = {}
        for p in paths:
            full = self.repo_path / p
            if not full.is_file():
                continue
            try:
                content = full.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_bytes:
                    content = content[:max_bytes] + f"\n... (truncated, {len(content)} bytes total)"
                results[p] = content
            except Exception:
                pass
        return results

    def get_readme(self) -> str:
        """Read README file if exists."""
        if not self.repo_path:
            raise RuntimeError("Clone first")
        for name in ["README.md", "README.rst", "README.txt", "readme.md"]:
            p = self.repo_path / name
            if p.exists():
                return p.read_text(encoding="utf-8", errors="replace")[:5000]
        return "(No README found)"

    def cleanup(self):
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
