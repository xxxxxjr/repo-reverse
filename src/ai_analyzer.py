"""AI-powered analysis using Claude API — architecture, bugs, improvements, redesign."""

import os
import anthropic


SYSTEM_PROMPT = """You are a senior software architect performing a deep reverse-engineering analysis of a codebase.

You will receive: the README, file tree, tech stack info, module list, dependency list, deployment configs, and key source files.

You must output a JSON object with the following structure. Do NOT include markdown code fences. Output ONLY the JSON object.

{
  "architecture_summary": "A concise 2-3 sentence summary of the project's overall architecture pattern (e.g., monolith, microservices, layered, hexagonal, etc.)",

  "architecture_patterns": ["pattern1", "pattern2"],

  "module_analysis": [
    {
      "name": "module_name",
      "responsibility": "What this module does",
      "dependencies": ["dep1", "dep2"],
      "health": "good|warning|bad",
      "notes": "Brief observation"
    }
  ],

  "call_flows": [
    {
      "name": "Flow description",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "components_involved": ["component1", "component2"]
    }
  ],

  "database_design": {
    "type": "PostgreSQL|MySQL|MongoDB|SQLite|etc",
    "orm": "Prisma|SQLAlchemy|TypeORM|etc",
    "entities": ["Entity1", "Entity2"],
    "relationships": ["User has_many Posts", "Post belongs_to User"],
    "concerns": ["Missing index on X", "No migration strategy found"]
  },

  "deployment_analysis": {
    "infrastructure": "Description of inferred infrastructure",
    "ci_cd": "CI/CD pipeline description",
    "concerns": ["No health checks configured", "Single point of failure in X"]
  },

  "potential_bugs": [
    {
      "severity": "high|medium|low",
      "location": "file or module",
      "description": "What the bug is",
      "impact": "What could go wrong"
    }
  ],

  "security_concerns": [
    {
      "severity": "high|medium|low",
      "description": "Security issue found",
      "recommendation": "How to fix"
    }
  ],

  "improvement_suggestions": [
    {
      "area": "performance|security|maintainability|testing|architecture|dx",
      "suggestion": "What to improve",
      "effort": "low|medium|high",
      "impact": "low|medium|high"
    }
  ],

  "redesign_proposal": {
    "would_rewrite": true,
    "architecture": "Monolith → Microservices",
    "tech_stack_changes": "Python → Go for performance-critical services",
    "design_rationale": "Why this approach is better",
    "key_diagram_description": "A Mermaid-compatible description of the new architecture",
    "estimated_effort": "3 months / 2 engineers"
  }
}
"""


def analyze(repo_context: str, api_key: str, model: str = "claude-sonnet-4-6", base_url: str | None = None) -> dict:
    """Send repo context to Claude and parse the analysis JSON."""
    client_kwargs = {"api_key": api_key}
    base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url
    client = anthropic.Anthropic(**client_kwargs)

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Analyze this codebase:\n\n{repo_context}"
        }],
        thinking={"type": "disabled"},
    )

    # Extract text from response, skipping thinking blocks
    raw = ""
    for block in response.content:
        if hasattr(block, 'text'):
            raw += block.text

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    import json
    return json.loads(raw)
