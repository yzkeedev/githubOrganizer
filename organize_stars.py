#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


CATEGORIES = [
    "AI Agents & Automation",
    "AI Coding Tools",
    "AI Models & Research",
    "AI Content & Media",
    "Web Scraping & Browser Automation",
    "SEO & Marketing",
    "Web Development",
    "Developer Tools",
    "Data & Analytics",
    "Infrastructure & DevOps",
    "Security & Privacy",
    "Design & UI",
    "Mobile & Desktop",
    "Finance & Trading",
    "Productivity",
    "Fun & Experimental",
    "Other",
]

BATCH_SIZE = 30
LLM_TIMEOUT_SECONDS = 20
LLM_WORKERS = 5
TAXONOMY_VERSION = 3

SYSTEM_PROMPT = """You categorize GitHub repositories into one primary category.
Return strict JSON only with this shape:
{
  "category": "one of the provided categories",
  "tags": ["up to 4 short tags"]
}
Choose exactly one primary category from the provided list.
Category guidance:
- AI Agents & Automation: agent frameworks, orchestration, copilots, autonomous workflows, MCP-first assistants, AI bots.
- AI Coding Tools: coding assistants, Claude Code/Codex/OpenCode tooling, code intelligence, dev workflows centered on AI coding.
- AI Models & Research: model training, inference stacks, evals, RL, papers, research repos, model serving.
- AI Content & Media: image, video, audio, voice, design, content generation with AI.
- Web Scraping & Browser Automation: scraping, crawling, extraction, browser control, Playwright/Puppeteer/Selenium.
- SEO & Marketing: SEO, GEO, search visibility, content audits, growth, marketing automation.
- Finance & Trading: trading bots, valuation, market making, finance analytics.
- Developer Tools: general developer utilities not primarily AI coding tools.
- Web Development: websites, frontend, backend, full-stack apps not better matched elsewhere.
- General CLI utilities, terminal UI kits, charting tools, editors, note tools, and docs search tools belong in Developer Tools or Productivity, not AI Agents.
- If a repo mainly generates images, video, voice, logos, presentations, or media with AI, place it in AI Content & Media.
- If a repo is about SEO/GEO, ranking, keywords, audits, distribution channels, or growth, place it in SEO & Marketing.
Prefer concise, concrete labels and avoid markdown."""

OPPORTUNITY_CLUSTERS = [
    {
        "name": "SEO Lead Engine",
        "description": "Combine crawling, AI analysis, and SEO workflows into an audit or lead-gen product for websites.",
        "categories": ["SEO & Marketing", "Web Scraping & Browser Automation", "AI Agents & Automation"],
        "keywords": ["seo", "geo", "crawl", "scrap", "audit", "lead", "browser", "agent"],
    },
    {
        "name": "AI Coding Workflow SaaS",
        "description": "Combine coding agents, code intelligence, and developer tooling into a team productivity product.",
        "categories": ["AI Coding Tools", "AI Agents & Automation", "Developer Tools"],
        "keywords": ["claude code", "codex", "cursor", "code intelligence", "developer", "coding agent", "plugin", "cli"],
    },
    {
        "name": "Content Repurposing Studio",
        "description": "Combine media generation, marketing workflows, and web delivery into content production services or products.",
        "categories": ["AI Content & Media", "SEO & Marketing", "Web Development"],
        "keywords": ["content", "video", "image", "voice", "logo", "marketing", "landing", "media"],
    },
    {
        "name": "Trading Intelligence Stack",
        "description": "Combine trading engines, analytics, and agent automation into niche research or automation products.",
        "categories": ["Finance & Trading", "Data & Analytics", "AI Agents & Automation"],
        "keywords": ["trading", "quant", "market", "finance", "forecast", "analytics", "research", "agent"],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "target",
        nargs="?",
        default="https://github.com/yzkeedev?tab=stars",
        help="GitHub stars URL or GitHub username",
    )
    parser.add_argument(
        "--config",
        default="minimax.json",
        help="Path to the MiniMax Anthropic-compatible config file",
    )
    parser.add_argument(
        "--readme",
        default="README.md",
        help="Path to the generated README file",
    )
    parser.add_argument(
        "--cache",
        default="stars_cache.json",
        help="Path to the classification cache file",
    )
    parser.add_argument(
        "--github-token-env",
        default="GITHUB_TOKEN",
        help="Optional environment variable name for a GitHub token",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_username(target: str) -> str:
    if target.startswith("http://") or target.startswith("https://"):
        parsed = parse.urlparse(target)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise ValueError("Could not extract a GitHub username from the provided URL.")
        return parts[0]
    return target.strip().lstrip("@")


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_file(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_minimax_env(config_path: Path) -> dict[str, str]:
    config = load_json_file(config_path, {})
    merged = {key: str(value) for key, value in os.environ.items()}
    if isinstance(config, dict):
        env_block = config.get("env", {})
        if isinstance(env_block, dict):
            for key, value in env_block.items():
                merged[key] = str(value)
    required = ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"]
    missing = [key for key in required if not merged.get(key)]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    return merged


def http_json(
    url: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[dict[str, Any], dict[str, str]]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = request.Request(url=url, data=data, headers=request_headers, method="POST" if data else "GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body), dict(response.headers.items())
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Request failed with status {exc.code}: {body}") from exc


def fetch_starred_repositories(username: str, github_token: str | None) -> list[dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-star-organizer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/starred?per_page=100&page={page}"
        response, _ = http_json(url, headers=headers, timeout=60)
        if not isinstance(response, list) or not response:
            break
        repos.extend(response)
        if len(response) < 100:
            break
        page += 1
    return repos


def extract_repo_metadata(repo: dict[str, Any]) -> dict[str, Any]:
    topics = repo.get("topics") or []
    return {
        "full_name": repo.get("full_name", ""),
        "name": repo.get("name", ""),
        "html_url": repo.get("html_url", ""),
        "description": (repo.get("description") or "").strip(),
        "language": repo.get("language") or "Unknown",
        "topics": topics if isinstance(topics, list) else [],
        "homepage": repo.get("homepage") or "",
        "stargazers_count": repo.get("stargazers_count") or 0,
        "updated_at": repo.get("updated_at") or "",
    }


def build_classification_prompt(repos: list[dict[str, Any]]) -> str:
    categories = ", ".join(CATEGORIES)
    metadata = [
        {
            "full_name": repo["full_name"],
            "description": repo["description"],
            "language": repo["language"],
            "topics": repo["topics"],
            "homepage": repo["homepage"],
            "stars": repo["stargazers_count"],
        }
        for repo in repos
    ]
    return (
        f"Allowed categories: {categories}\n"
        "Return strict JSON only with this shape:\n"
        '{\n  "results": [\n    {\n      "full_name": "owner/repo",\n      "category": "one allowed category",\n'
        '      "tags": ["up to 4 short tags"]\n    }\n  ]\n}\n'
        "Choose the single best category for each repository.\n"
        f"Repositories to classify:\n{json.dumps(metadata, ensure_ascii=False, indent=2)}"
    )


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        raise ValueError("Model response did not contain a JSON object.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Model response was not a JSON object.")
    return payload


def fallback_classification(repo: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        [
            repo["full_name"],
            repo["description"],
            repo["language"],
            " ".join(repo["topics"]),
            repo["homepage"],
        ]
    ).lower()
    keyword_map = {
        "AI Agents & Automation": [
            "ai",
            "agent",
            "mcp",
            "assistant",
            "autonomous",
            "orchestration",
            "workflow",
            "copilot",
            "multi-agent",
        ],
        "AI Coding Tools": [
            "claude code",
            "codex",
            "opencode",
            "code intelligence",
            "ai coding",
            "developer agent",
            "code review",
            "codebase",
        ],
        "AI Models & Research": [
            "llm",
            "model",
            "inference",
            "training",
            "fine-tuning",
            "eval",
            "benchmark",
            "rl",
            "reasoning",
            "research",
            "rag",
        ],
        "AI Content & Media": [
            "image",
            "video",
            "audio",
            "voice",
            "music",
            "logo",
            "avatar",
            "deepfake",
            "content generator",
            "audiobook",
        ],
        "Web Scraping & Browser Automation": [
            "scrap",
            "crawler",
            "crawl",
            "browser",
            "playwright",
            "selenium",
            "automation",
            "puppeteer",
            "extract",
            "chrome",
            "web data",
        ],
        "SEO & Marketing": [
            "seo",
            "geo",
            "marketing",
            "growth",
            "content audit",
            "search visibility",
            "search engine",
            "keyword",
            "landing page",
            "analytics seo",
        ],
        "Web Development": [
            "next.js",
            "react",
            "vue",
            "tailwind",
            "frontend",
            "website",
            "landing page",
            "web app",
        ],
        "Developer Tools": [
            "cli",
            "editor",
            "plugin",
            "developer",
            "tooling",
            "sdk",
            "codegen",
            "workflow",
        ],
        "Data & Analytics": [
            "data",
            "analytics",
            "visualization",
            "pipeline",
            "etl",
            "dashboard",
        ],
        "Finance & Trading": [
            "trading",
            "arbitrage",
            "polymarket",
            "valuation",
            "market maker",
            "stock",
            "finance",
            "quant",
            "dcf",
        ],
        "Infrastructure & DevOps": [
            "docker",
            "kubernetes",
            "terraform",
            "cloud",
            "deploy",
            "devops",
            "ci",
            "cd",
        ],
        "Security & Privacy": [
            "security",
            "auth",
            "privacy",
            "encryption",
            "vulnerability",
            "cyber",
            "sandbox",
        ],
        "Design & UI": [
            "design",
            "ui",
            "ux",
            "component",
            "animation",
            "figma",
            "theme",
        ],
        "Mobile & Desktop": [
            "ios",
            "android",
            "swift",
            "kotlin",
            "desktop",
            "electron",
            "tauri",
            "macos",
        ],
        "Fun & Experimental": [
            "game",
            "fun",
            "experimental",
            "toy",
            "meme",
            "creative",
            "art",
        ],
        "Productivity": [
            "todo",
            "notes",
            "calendar",
            "task",
            "productivity",
            "organizer",
        ],
    }
    scores = {category: 0 for category in CATEGORIES}
    for category, keywords in keyword_map.items():
        scores[category] = sum(1 for keyword in keywords if keyword in text)
    category = max(scores, key=scores.get)
    if scores[category] == 0:
        category = "Other"
    tags = repo["topics"][:4]
    summary = repo["description"] or f"{repo['full_name']} repository."
    reason = "Fallback keyword classification based on repository metadata."
    return {
        "category": category,
        "tags": tags,
        "summary": summary[:160],
        "reason": reason,
    }


def apply_category_overrides(repo: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        [
            repo.get("full_name", ""),
            repo.get("description", ""),
            repo.get("language", ""),
            " ".join(repo.get("topics", [])),
            repo.get("homepage", ""),
        ]
    ).lower()
    category = classification.get("category") or "Other"

    if any(keyword in text for keyword in ["awesome-list", "curated list", "collection of", "list of free apis", "public-apis/public-apis"]):
        category = "Other"
    elif any(keyword in text for keyword in ["seo", "geo", "keyword", "marketing", "growth", "early user", "search visibility"]):
        category = "SEO & Marketing"
    elif any(keyword in text for keyword in ["arbitrage", "polymarket", "trading", "quant", "valuation", "dcf", "market maker", "stock"]):
        category = "Finance & Trading"
    elif any(keyword in text for keyword in ["crawler", "scraper", "scraping", "playwright", "puppeteer", "selenium", "browser automation", "web extraction"]):
        category = "Web Scraping & Browser Automation"
    elif any(keyword in text for keyword in ["logo generator", "video", "voice", "audio", "image generation", "audiobook", "deepfake", "ppt", "presentation", "content generator"]):
        category = "AI Content & Media"
    elif any(keyword in text for keyword in ["claude code", "codex", "opencode", "cursor", "code intelligence", "coding agent", "code review", "agentic coding"]):
        category = "AI Coding Tools"
    elif any(keyword in text for keyword in ["terminal ui", "tui", "cli tool", "markdown editor", "plugin", "speed reader", "docs search", "search engine for your docs", "terminal charts", "chart cli"]):
        category = "Developer Tools"
    elif any(keyword in text for keyword in ["agent", "orchestrator", "assistant", "mcp", "autonomous", "coworker", "multi-agent", "workflow automation"]):
        category = "AI Agents & Automation"

    result = dict(classification)
    result["category"] = category
    return result


def classify_with_llm(repos: list[dict[str, Any]], env: dict[str, str]) -> dict[str, dict[str, Any]]:
    base_url = env["ANTHROPIC_BASE_URL"].rstrip("/")
    endpoint = f"{base_url}/v1/messages"
    payload = {
        "model": env.get("ANTHROPIC_MODEL") or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or "MiniMax-M2.7",
        "max_tokens": 1600,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": build_classification_prompt(repos)}],
            }
        ],
    }
    headers = {
        "x-api-key": env["ANTHROPIC_AUTH_TOKEN"],
        "anthropic-version": "2023-06-01",
    }
    response, _ = http_json(endpoint, headers=headers, payload=payload, timeout=LLM_TIMEOUT_SECONDS)
    content = response.get("content", [])
    text = "\n".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ).strip()
    if not text:
        raise ValueError("Model response did not include text content.")
    parsed = parse_json_object(text)
    results = parsed.get("results")
    if not isinstance(results, list):
        raise ValueError("Model response did not include a results array.")
    indexed: dict[str, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        full_name = str(item.get("full_name") or "").strip()
        category = item.get("category")
        if not full_name or category not in CATEGORIES:
            continue
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        indexed[full_name] = {
            "category": category,
            "tags": [str(tag).strip() for tag in tags[:4] if str(tag).strip()],
            "summary": "",
            "reason": "LLM classification from repository metadata.",
        }
    return indexed


def classify_repos(repos: list[dict[str, Any]], env: dict[str, str]) -> dict[str, dict[str, Any]]:
    classified: dict[str, dict[str, Any]] = {}
    batches = [repos[index : index + BATCH_SIZE] for index in range(0, len(repos), BATCH_SIZE)]
    batch_results_map: dict[int, dict[str, dict[str, Any]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        future_map = {
            executor.submit(classify_with_llm, batch, env): batch_index
            for batch_index, batch in enumerate(batches)
        }
        for future in concurrent.futures.as_completed(future_map):
            batch_index = future_map[future]
            try:
                batch_results_map[batch_index] = future.result()
            except Exception:
                batch_results_map[batch_index] = {}
    for batch_index, batch in enumerate(batches):
        batch_results = batch_results_map.get(batch_index, {})
        for repo in batch:
            result = batch_results.get(repo["full_name"]) or fallback_classification(repo)
            result = apply_category_overrides(repo, result)
            result["classified_at"] = utc_now()
            result["taxonomy_version"] = TAXONOMY_VERSION
            if not result.get("summary"):
                result["summary"] = repo["description"] or repo["full_name"]
            if not result.get("reason"):
                result["reason"] = "LLM classification from repository metadata."
            classified[repo["full_name"]] = result
    return classified


def markdown_escape(value: str) -> str:
    return value.replace("\n", " ").strip()


def score_opportunity_repo(repo: dict[str, Any], cluster: dict[str, Any]) -> int:
    text = " ".join(
        [
            repo.get("full_name", ""),
            repo.get("description", ""),
            repo.get("language", ""),
            " ".join(repo.get("topics", [])),
        ]
    ).lower()
    excluded_terms = [
        "awesome",
        "curated list",
        "collection of",
        "template",
        "starter",
        "boilerplate",
        "public api",
        "list of",
    ]
    if any(term in text for term in excluded_terms):
        return -1
    keyword_score = sum(1 for keyword in cluster.get("keywords", []) if keyword in text)
    if keyword_score == 0:
        return -1
    category_bonus = 5 if repo["category"] == cluster["categories"][0] else 0
    stars_bonus = min(repo["stargazers_count"] // 5000, 20)
    return keyword_score * 10 + category_bonus + stars_bonus


def build_opportunity_section(repos: list[dict[str, Any]]) -> list[str]:
    lines = ["## Opportunity Clusters", ""]
    for cluster in OPPORTUNITY_CLUSTERS:
        cluster_repos = [repo for repo in repos if repo["category"] in cluster["categories"]]
        scored_repos = [
            (score_opportunity_repo(repo, cluster), repo)
            for repo in cluster_repos
        ]
        ranked_repos = sorted(scored_repos, key=lambda item: (item[0], item[1]["stargazers_count"]), reverse=True)
        top_repos = [repo for score, repo in ranked_repos if score >= 0][:5]
        lines.append(f"### {cluster['name']}")
        lines.append(cluster["description"])
        lines.append(f"Focus categories: {', '.join(cluster['categories'])}")
        if top_repos:
            repo_links = ", ".join(f"[{repo['full_name']}]({repo['html_url']})" for repo in top_repos[:3])
            lines.append(f"Starter repos: {repo_links}")
        lines.append("")
    return lines


def render_readme(username: str, repos: list[dict[str, Any]], generated_at: str, new_count: int) -> str:
    counts = Counter(repo["category"] for repo in repos)
    lines = [
        f"# {username}'s Starred Repositories",
        "",
        f"Source: https://github.com/{username}?tab=stars",
        f"Last generated: {generated_at}",
        f"Total repositories: {len(repos)}",
        f"New classifications this run: {new_count}",
        "",
        "## Category Summary",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category in CATEGORIES:
        if counts.get(category):
            lines.append(f"| {category} | {counts[category]} |")
    lines.extend([""] + build_opportunity_section(repos))
    for category in CATEGORIES:
        category_repos = [repo for repo in repos if repo["category"] == category]
        if not category_repos:
            continue
        lines.extend(["", f"## {category}", ""])
        for repo in sorted(category_repos, key=lambda item: item["full_name"].lower()):
            description = markdown_escape(repo["description"] or repo["summary"] or "No description provided.")
            details = [
                f"Language: {repo['language']}",
                f"Stars: {repo['stargazers_count']}",
            ]
            if repo["tags"]:
                details.append(f"Tags: {', '.join(markdown_escape(tag) for tag in repo['tags'])}")
            lines.append(
                f"- [{repo['full_name']}]({repo['html_url']}) — {description} ({' | '.join(details)})"
            )
    lines.append("")
    return "\n".join(lines)


def merge_cache_entry(repo: dict[str, Any], existing: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    if existing and existing.get("category") in CATEGORIES and existing.get("taxonomy_version") == TAXONOMY_VERSION:
        classification = {
            "category": existing["category"],
            "tags": existing.get("tags") or [],
            "summary": existing.get("summary") or repo["description"] or repo["full_name"],
            "reason": existing.get("reason") or "Cached classification.",
            "classified_at": existing.get("classified_at") or utc_now(),
            "taxonomy_version": existing.get("taxonomy_version") or TAXONOMY_VERSION,
        }
        is_new = False
    else:
        classification = {}
        is_new = True
    merged = dict(repo)
    merged.update(classification)
    return merged, is_new


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    config_path = (root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    readme_path = (root / args.readme).resolve() if not Path(args.readme).is_absolute() else Path(args.readme)
    cache_path = (root / args.cache).resolve() if not Path(args.cache).is_absolute() else Path(args.cache)

    username = parse_username(args.target)
    env = read_minimax_env(config_path)
    github_token = os.environ.get(args.github_token_env) or env.get(args.github_token_env)
    cache = load_json_file(cache_path, {"repos": {}})
    cached_repos = cache.get("repos", {}) if isinstance(cache, dict) else {}
    if not isinstance(cached_repos, dict):
        cached_repos = {}

    fetch_warning = ""
    try:
        raw_repos = fetch_starred_repositories(username, github_token)
        repos = [extract_repo_metadata(raw_repo) for raw_repo in raw_repos]
    except Exception as exc:
        if not cached_repos:
            raise
        fetch_warning = str(exc)
        repos = [extract_repo_metadata(repo) for repo in cached_repos.values() if isinstance(repo, dict)]

    organized: list[dict[str, Any]] = []
    repos_to_classify: list[dict[str, Any]] = []
    new_count = 0
    for repo in repos:
        merged, is_new = merge_cache_entry(repo, cached_repos.get(repo["full_name"]))
        organized.append(merged)
        if is_new:
            new_count += 1
            repos_to_classify.append(repo)

    classifications = classify_repos(repos_to_classify, env) if repos_to_classify else {}
    for repo in organized:
        if repo.get("category") in CATEGORIES:
            continue
        repo.update(apply_category_overrides(repo, classifications.get(repo["full_name"]) or fallback_classification(repo)))
        repo["classified_at"] = repo.get("classified_at") or utc_now()
        repo["taxonomy_version"] = repo.get("taxonomy_version") or TAXONOMY_VERSION

    generated_at = utc_now()
    organized.sort(key=lambda item: (CATEGORIES.index(item["category"]), item["full_name"].lower()))

    readme_text = render_readme(username, organized, generated_at, new_count)
    readme_path.write_text(readme_text, encoding="utf-8")

    cache_payload = {
        "generated_at": generated_at,
        "username": username,
        "taxonomy_version": TAXONOMY_VERSION,
        "repos": {repo["full_name"]: repo for repo in organized},
    }
    save_json_file(cache_path, cache_payload)

    if fetch_warning:
        print(f"Warning: using cached repository data because live fetch failed: {fetch_warning}")
    print(f"Generated {readme_path}")
    print(f"Updated cache: {cache_path}")
    print(f"Repositories processed: {len(organized)}")
    print(f"New classifications: {new_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
