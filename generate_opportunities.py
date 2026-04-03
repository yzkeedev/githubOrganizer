#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from organize_stars import http_json, load_json_file, parse_json_object, read_minimax_env, save_json_file


NEWSNOW_ENDPOINT = "https://newsnow.busiyi.world/api/s/entire"
DEFAULT_SOURCES = [
    "36kr-renqi",
    "baidu",
    "bilibili-hot-search",
    "chongbuluo-hot",
    "cls-hot",
    "coolapk",
    "douban",
    "douyin",
    "freebuf",
    "github-trending-today",
    "hackernews",
    "hupu",
    "ifeng",
    "juejin",
    "nowcoder",
    "producthunt",
    "qqvideo-tv-hotsearch",
    "sspai",
    "steam",
    "tencent-hot",
    "thepaper",
    "tieba",
    "toutiao",
    "wallstreetcn-hot",
    "weibo",
    "xueqiu-hotstock",
    "zhihu",
]
MAX_TRENDS = 18
MAX_REPOS = 36
REPO_THEMES = [
    {"keywords": ["seo", "geo", "keyword", "audit", "growth", "ranking"], "limit": 4},
    {"keywords": ["crawl", "scrap", "browser", "playwright", "puppeteer", "extract"], "limit": 4},
    {"keywords": ["claude code", "codex", "cursor", "coding agent", "code intelligence", "developer"], "limit": 4},
    {"keywords": ["video", "voice", "audio", "image", "content", "logo"], "limit": 4},
    {"keywords": ["trading", "quant", "finance", "market", "stock", "polymarket"], "limit": 4},
]
CREATIVE_ANGLES = [
    {
        "label": "Assumption inversion",
        "directive": "Challenge the default workflow and build around the friction, latency, or trust gap everyone currently accepts.",
        "audiences": ["category owners", "risk teams", "operators with manual bottlenecks", "technical strategists"],
        "formats": ["protocol", "charter", "exchange", "switchboard"],
    },
    {
        "label": "Capability transplant",
        "directive": "Steal a proven mechanism from one domain and transplant it into a completely different market with stronger urgency.",
        "audiences": ["frontier teams", "specialist consultancies", "research operators", "industrial builders"],
        "formats": ["mirror", "compiler", "broker", "fabric"],
    },
    {
        "label": "Second-order market",
        "directive": "Ignore the loud headline product and monetize the reactions, exceptions, compliance gaps, and coordination overhead created around it.",
        "audiences": ["analysts", "compliance leads", "market makers", "ecosystem aggregators"],
        "formats": ["ledger", "prism", "relay", "exchange"],
    },
    {
        "label": "Boundary collapse",
        "directive": "Merge tools that normally live in separate teams so a new workflow only becomes possible when the boundary disappears.",
        "audiences": ["cross-functional teams", "platform builders", "ops architects", "technical founders"],
        "formats": ["bridge", "fabric", "operating system", "protocol"],
    },
    {
        "label": "Hidden stakeholder",
        "directive": "Build for the user who is downstream from the trend but feels the pain first, even if they are ignored by the mainstream narrative.",
        "audiences": ["back-office teams", "field operators", "review desks", "specialized service firms"],
        "formats": ["lens", "charter", "switch", "foundry"],
    },
    {
        "label": "Synthetic twin",
        "directive": "Turn live signals into simulations, rehearsal loops, or synthetic environments that help buyers practice before acting.",
        "audiences": ["decision teams", "training leads", "scenario planners", "high-stakes operators"],
        "formats": ["twin", "lab", "simulator", "atlas"],
    },
]
FALLBACK_PREFIXES = ["Latent", "Counter", "Shadow", "Boundary", "Signal", "Third", "Quiet", "Vector", "Flux", "Strange"]
FALLBACK_SUFFIXES = ["Protocol", "Exchange", "Mirror", "Foundry", "Charter", "Atlas", "Fabric", "Prism", "Relay", "Switch"]
MAX_IDEA_COUNT = 10
IDEA_CANDIDATE_COUNT = 10
FALLBACK_IDEA_CANDIDATE_COUNT = 24
IDEA_SIMILARITY_THRESHOLD = 0.72

# Diverse summary templates for fallback generator to avoid formulaic output
FALLBACK_SUMMARY_TEMPLATES = [
    "Use {mechanism} from {category_a} to exploit an overlooked coordination gap in {category_b} created by {trend_title}, targeting {customer} who currently absorbs the cost manually.",
    "Build a {category_b} system that applies {category_a} patterns to {trend_title}, allowing {customer} to reverse-engineer what competitors are testing.",
    "Create a broker layer between {category_a} and {category_b} that profits from the latency around {trend_title}, selling speed access to {customer}.",
    "Design a feedback loop where {category_a} observations from {trend_title} get routed to {category_b} interventions, monetized through {customer} subscriptions.",
    "Exploit the gap between how {category_a} tools work and how {category_b} teams actually operate around {trend_title}, offering {customer} a bridge they will pay for.",
    "Port the trust model from {category_a} into {category_b}, letting {customer} verify claims about {trend_title} before committing resources.",
    "Turn {category_a} data about {trend_title} into a prediction market for {category_b} decisions, with {customer} as the primary traders.",
    "Build an audit path through {trend_title} that surfaces {category_b} inefficiencies {customer} can correct before competitors notice.",
]
FALLBACK_REVENUE_MODELS = [
    "Sell verification subscriptions to {customer} who need proof before approving {category_b} spend.",
    "Take a percentage of the cost savings achieved when {customer} implements the insight.",
    "License the coordination protocol to {category_b} teams at {category_a} companies.",
    "Charge {customer} per decision routed through the new channel.",
    "Offer premium access to the signal feed for {customer} tracking {category_b} dynamics.",
]
BREAKTHROUGH_SCORE_THRESHOLD = 68
CROSS_DOMAIN_SCORE_THRESHOLD = 58
SERENDIPITY_SCORE_THRESHOLD = 62
NOVELTY_SCORE_THRESHOLD = 60
CONVENTIONALITY_SCORE_MAX = 45
HIDDEN_CUSTOMER_SCORE_THRESHOLD = 70
MINIMUM_MECHANISM_FAMILIES = 2
CATEGORY_ALIASES = {
    "SEO & Marketing": "SEO",
    "Web Scraping & Browser Automation": "Crawler",
    "AI Agents & Automation": "Agent",
    "AI Coding Tools": "Code",
    "AI Content & Media": "Media",
    "Developer Tools": "Dev",
    "Data & Analytics": "Data",
    "Finance & Trading": "Market",
    "Web Development": "Web",
    "Security & Privacy": "Trust",
    "Infrastructure & DevOps": "Infra",
    "Design & UI": "Design",
    "Productivity": "Ops",
    "Mobile & Desktop": "Mobile",
}
CATEGORY_VECTOR_MAP = {
    "SEO & Marketing": {"distribution", "attention", "ranking", "demand", "conversion", "language"},
    "Web Scraping & Browser Automation": {"capture", "extraction", "observation", "navigation", "automation", "surveillance"},
    "AI Agents & Automation": {"delegation", "orchestration", "autonomy", "coordination", "workflow", "planning"},
    "AI Coding Tools": {"developer", "abstraction", "iteration", "compilation", "reasoning", "productivity"},
    "AI Content & Media": {"generation", "narrative", "remix", "creative", "multimodal", "attention"},
    "AI Models & Research": {"reasoning", "simulation", "experimentation", "inference", "science", "forecasting"},
    "Developer Tools": {"debugging", "tooling", "productivity", "interfaces", "compilation", "infrastructure"},
    "Data & Analytics": {"measurement", "forecasting", "decision", "insight", "aggregation", "modeling"},
    "Finance & Trading": {"pricing", "risk", "incentives", "market", "timing", "arbitrage"},
    "Web Development": {"distribution", "interfaces", "delivery", "interaction", "commerce", "publishing"},
    "Security & Privacy": {"trust", "verification", "defense", "identity", "compliance", "risk"},
    "Infrastructure & DevOps": {"reliability", "automation", "deployment", "scale", "latency", "operations"},
    "Design & UI": {"interfaces", "taste", "communication", "human factors", "systems", "creative"},
    "Productivity": {"habits", "coordination", "time", "focus", "rituals", "workflow"},
    "Mobile & Desktop": {"devices", "presence", "offline", "interaction", "portability", "personalization"},
    "Fun & Experimental": {"play", "novelty", "culture", "exploration", "memes", "behavior"},
    "Other": {"generalist"},
}
MECHANISM_FAMILY_KEYWORDS = {
    "inversion": {"reverse", "invert", "constraint", "counter", "anti", "exception", "friction"},
    "protocol": {"protocol", "playbook", "charter", "governance", "compliance", "handshake"},
    "market": {"market", "exchange", "auction", "pricing", "broker", "bid", "arbitrage"},
    "simulation": {"simulation", "twin", "forecast", "scenario", "rehearsal", "sandbox"},
    "coordination": {"routing", "orchestration", "coordination", "dispatch", "switchboard", "workflow"},
    "knowledge": {"graph", "memory", "mapping", "taxonomy", "knowledge", "ontology"},
    "trust": {"verification", "proof", "audit", "trust", "guardrail", "trace"},
    "compression": {"compression", "distill", "synthesis", "brief", "compiler", "translation"},
    "distribution": {"distribution", "channel", "virality", "ranking", "attention", "outbound"},
}
GENERIC_CONCEPT_TERMS = {
    "dashboard",
    "assistant",
    "copilot",
    "workflow",
    "monitor",
    "alert",
    "radar",
    "desk",
    "studio",
    "console",
    "engine",
    "hub",
    "platform",
    "tooling",
    "productivity",
    "agency",
    "subscription",
    "inbox",
    "digest",
    "brief",
    "operator",
    "consultant",
    "manager",
    "repeatable",
    "narrow",
    "focused",
    "tracker",
    "pilot",
    "studio",
}
GENERIC_PATTERNS_TO_REJECT = [
    r"\bhelp\s+.+?\s+turn\s+.+?\s+into\b",
    r"\bcharge a monthly subscription\b",
    r"\bship a narrow\b",
    r"\brepeatable\b",
    r"\boperator workflow\b",
    r"\b(?:daily|weekly)\s+(?:digest|brief)\b",
    r"\bturn\s+.+?\s+into\s+(?:a|an)\s+(?:service|subscription|platform|engine|tooling|workflow)\b",
    r"\b(?:narrow|focused)\s+(?:radar|monitor|tracker|workflow|studio|desk|brief|digest)\b",
]
CONTRARIAN_SIGNAL_TERMS = {
    "instead",
    "hidden",
    "counter",
    "reverse",
    "secondary",
    "ignored",
    "non-obvious",
    "unexpected",
    "underpriced",
    "downstream",
    "exception",
    "assumption",
}
GENERIC_CUSTOMERS = {
    "teams",
    "founders",
    "operators",
    "developers",
    "companies",
    "startups",
    "agencies",
    "analysts",
}
BREAKTHROUGH_OPERATORS = [
    {
        "label": "Constraint inversion",
        "axes": ["constraint inversion", "hidden stakeholder", "trust wedge"],
        "mechanism_template": "Turn the pain created by {trend_title} into the product surface: capture exceptions with {left_alias} tooling, then route them through {right_alias} systems so every failure becomes proprietary training data.",
        "why_template": "Most teams will build the obvious wrapper around {trend_title}. This concept monetizes the costly exceptions and review burden that appear after adoption, which is where urgency and budget collect first.",
        "customer_templates": [
            "{trend_title} response teams inside regulated firms",
            "service operators who clean up failed {left_alias_lower} workflows",
            "specialists downstream from {right_alias_lower} decisions",
        ],
        "plan_templates": [
            "Instrument the exception path around {trend_title}",
            "Convert repeated failures into a scored review queue spanning {category_a} and {category_b}",
            "Sell the review protocol before automating the whole loop",
        ],
    },
    {
        "label": "Capability transplant",
        "axes": ["capability transplant", "cross-domain synthesis", "behavior redesign"],
        "mechanism_template": "Import the best mechanism from {category_a} into {category_b}: use {left_alias} methods to give {right_alias_lower} teams a new operating model triggered by {trend_title}.",
        "why_template": "{category_b} buyers do not expect a proven {category_a} pattern to solve their problem, so the idea feels discontinuous rather than incremental. The novelty comes from moving a working primitive instead of inventing new software from scratch.",
        "customer_templates": [
            "{right_alias_lower} teams with rising demand but stale playbooks",
            "operators managing complex {category_b} handoffs",
            "buyers who already pay for expertise but not yet for software in {category_b}",
        ],
        "plan_templates": [
            "Map the strongest primitive from {category_a} that {category_b} lacks",
            "Prototype one transplanted workflow around {trend_title}",
            "Package the new ritual as a premium operating layer before broad rollout",
        ],
    },
    {
        "label": "Second-order market",
        "axes": ["second-order demand", "market design", "timing edge"],
        "mechanism_template": "Build a secondary market around {trend_title}: let {hidden_customer_seed} trade speed, proof, or access using a broker layer powered by {left_alias} and {right_alias}.",
        "why_template": "The headline product attracts attention, but the scarce asset is not the headline itself. It is the response time, verification, and coordination capacity that appear around it, which are easier to monetize and harder to copy.",
        "customer_templates": [
            "buyers who need verified access before the market normalizes",
            "intermediaries exposed to timing risk from {trend_title}",
            "specialized desks coordinating around short-lived {trend_title} spikes",
        ],
        "plan_templates": [
            "Identify the scarce resource created by {trend_title}",
            "Broker it across {category_a} and {category_b} participants",
            "Add pricing and proof so the network compounds with each transaction",
        ],
    },
    {
        "label": "Synthetic twin",
        "axes": ["simulation loop", "decision rehearsal", "cross-domain transfer"],
        "mechanism_template": "Create a synthetic twin for decisions triggered by {trend_title}, combining {left_alias} observation with {right_alias} prediction so buyers can rehearse actions before committing real money or trust.",
        "why_template": "Most products help after a choice is made. This one wins earlier by simulating the decision boundary itself, which changes user behavior before mistakes happen.",
        "customer_templates": [
            "teams that make expensive or irreversible calls under uncertainty",
            "decision owners who need rehearsal before live execution",
            "operators whose mistakes ripple into customers or regulators",
        ],
        "plan_templates": [
            "Capture a live decision stream linked to {trend_title}",
            "Build a replay and rehearsal layer using {category_a} plus {category_b}",
            "Sell scenario planning subscriptions tied to avoided mistakes",
        ],
    },
]
OPPORTUNITY_SYSTEM_PROMPT = """Generate 10 breakthrough startup ideas from today's trends and repos.

Output JSON:
{"ideas":[{"name":"X","summary":"1 sentence","mechanism":"what makes it hard to copy","why_non_obvious":"the invisible connection","hidden_customer":"specific buyer","axes":["label"],"trends":["trend"],"repos":["owner/repo"]}]}

Rules:
- Use 2+ repos and 1+ trend per idea
- 5+ ideas must anchor to headline trends
- Think transfer, not templates: coordination layer > dashboard, broker > tool
- AVOID: "X Assistant", "Help X use Y", "platform for X", generic customers
- Breakthrough = reader thinks "why didn't I see that?"
- Keep language concrete, no hype."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="minimax.json",
        help="Path to the MiniMax Anthropic-compatible config file",
    )
    parser.add_argument(
        "--cache",
        default="stars_cache.json",
        help="Path to the stars cache file generated by organize_stars.py",
    )
    parser.add_argument(
        "--output-dir",
        default="opportunities",
        help="Directory for dated opportunity reports",
    )
    parser.add_argument(
        "--date",
        default="",
        help="UTC date override in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--site-dir",
        default="docs",
        help="Directory for generated GitHub Pages assets",
    )
    parser.add_argument(
        "--quality-gate",
        action="store_true",
        help="Fail if the generated portfolio does not meet the breakthrough quality thresholds",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (root / path).resolve()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "trend"


def stable_hash_int(*parts: str) -> int:
    joined = "||".join(parts)
    return int(hashlib.sha256(joined.encode("utf-8")).hexdigest(), 16)


def normalize_idea_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def idea_text_tokens(*parts: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\-\+]{2,}", " ".join(parts).lower())
    stop_words = {
        "and",
        "are",
        "but",
        "can",
        "for",
        "with",
        "from",
        "help",
        "into",
        "that",
        "this",
        "your",
        "their",
        "about",
        "there",
        "which",
        "while",
        "where",
        "daily",
        "today",
        "turn",
        "using",
        "build",
        "launch",
        "trend",
        "trends",
        "ideas",
        "idea",
        "project",
        "projects",
        "repo",
        "repos",
    }
    return {token for token in tokens if token not in stop_words}


def canonical_semantic_token(token: str) -> str:
    normalized = str(token).lower().strip()
    if normalized.endswith("ies") and len(normalized) > 4:
        normalized = f"{normalized[:-3]}y"
    elif normalized.endswith("s") and len(normalized) > 4 and not normalized.endswith("ss"):
        normalized = normalized[:-1]
    aliases = {
        "ops": "operator",
        "operator": "operator",
        "team": "team",
        "lead": "lead",
        "agency": "agency",
        "founder": "founder",
        "builder": "founder",
        "creator": "creator",
        "researcher": "research",
        "research": "research",
        "marketer": "marketing",
        "marketing": "marketing",
        "seller": "sales",
        "sale": "sales",
        "developer": "developer",
        "dev": "developer",
        "engineer": "developer",
        "operators": "operator",
        "founders": "founder",
        "builders": "founder",
        "developers": "developer",
        "engineers": "developer",
        "workflows": "workflow",
        "pipeline": "workflow",
        "pipelines": "workflow",
        "engine": "workflow",
        "automation": "workflow",
        "orchestration": "workflow",
        "monitoring": "monitor",
        "watch": "monitor",
        "watchtower": "monitor",
        "radar": "monitor",
        "tracker": "monitor",
        "tracking": "monitor",
        "monitor": "monitor",
        "alerts": "alert",
        "desk": "workspace",
        "console": "workspace",
        "studio": "workspace",
        "cockpit": "workspace",
        "portal": "workspace",
        "dashboard": "workspace",
        "hub": "workspace",
        "pilot": "workspace",
        "briefing": "brief",
        "brief": "brief",
        "report": "brief",
        "digest": "brief",
        "memo": "brief",
        "ledger": "review",
        "audit": "review",
        "review": "review",
        "validation": "review",
        "validator": "review",
        "signal": "signal",
        "signals": "signal",
        "infra": "infrastructure",
        "devops": "infrastructure",
        "mobiles": "mobile",
        "desktops": "desktop",
        "agentic": "agent",
        "analytics": "analytics",
    }
    return aliases.get(normalized, normalized)


def overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left | right), 1)


def audience_tokens_for_idea(idea: dict[str, Any]) -> set[str]:
    summary = str(idea.get("summary") or "")
    revenue_model = str(idea.get("revenue_model") or "")
    matches: list[str] = []
    for text, pattern in [
        (summary, r"help\s+(.+?)\s+turn\s"),
        (revenue_model, r"for\s+(.+?)(?:[.,;]|$)"),
    ]:
        result = re.search(pattern, text, re.IGNORECASE)
        if result:
            matches.append(result.group(1))
    allowed_tokens = {
        "agency",
        "analyst",
        "builder",
        "compliance",
        "content",
        "creator",
        "customer",
        "developer",
        "engineer",
        "finance",
        "founder",
        "freelancer",
        "growth",
        "lead",
        "market",
        "marketing",
        "motion",
        "niche",
        "operator",
        "outbound",
        "product",
        "research",
        "sales",
        "security",
        "team",
        "trader",
    }
    tokens = {
        canonical_semantic_token(token)
        for token in idea_text_tokens(*matches)
        if canonical_semantic_token(token) in allowed_tokens
    }
    return {token for token in tokens if token}


def workflow_tokens_for_idea(idea: dict[str, Any]) -> set[str]:
    workflow_aliases = {
        "workflow",
        "monitor",
        "alert",
        "workspace",
        "brief",
        "review",
        "signal",
        "agent",
        "automation",
    }
    text = " ".join(
        [
            str(idea.get("name") or ""),
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("why_non_obvious") or ""),
            str(idea.get("hidden_customer") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(str(step) for step in idea.get("build_plan", [])),
            " ".join(str(axis) for axis in idea.get("breakthrough_axes", [])),
        ]
    )
    tokens = {
        canonical_semantic_token(token)
        for token in keyword_tokens(text)
        if canonical_semantic_token(token) in workflow_aliases
    }
    if "workflow" in tokens and "automation" not in tokens:
        tokens.add("automation")
    return tokens


def category_tokens_for_idea(idea: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for category in idea.get("category_focus", []) if isinstance(idea.get("category_focus"), list) else []:
        label = str(category).strip()
        if not label:
            continue
        tokens.add(f"cat:{slugify(label)}")
        tokens.update(f"cat:{canonical_semantic_token(token)}" for token in keyword_tokens(label))
    return tokens


def repo_tokens_for_idea(idea: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for repo_name in idea.get("repos", []) if isinstance(idea.get("repos"), list) else []:
        normalized = str(repo_name).strip().lower()
        if not normalized:
            continue
        tokens.add(f"repo:{normalized}")
        if "/" in normalized:
            _, short_name = normalized.split("/", 1)
            tokens.add(f"repo:{short_name}")
    return tokens


def semantic_text_tokens_for_idea(idea: dict[str, Any]) -> set[str]:
    trend_tokens = idea_text_tokens(" ".join(str(item) for item in idea.get("trends", []) if isinstance(item, str)))
    tokens = {
        canonical_semantic_token(token)
        for token in keyword_tokens(
            " ".join(
                [
                    str(idea.get("name") or ""),
                    str(idea.get("summary") or ""),
                    str(idea.get("novel_mechanism") or ""),
                    str(idea.get("why_non_obvious") or ""),
                    str(idea.get("hidden_customer") or ""),
                    str(idea.get("why_now") or ""),
                    str(idea.get("revenue_model") or ""),
                    " ".join(str(step) for step in idea.get("build_plan", [])),
                    " ".join(str(axis) for axis in idea.get("breakthrough_axes", [])),
                ]
            )
        )
        if canonical_semantic_token(token)
        not in {
            "and",
            "repeatable",
            "narrow",
            "focus",
            "broad",
            "can",
            "charge",
            "connect",
            "create",
            "creates",
            "customer",
            "easier",
            "help",
            "price",
            "pricing",
            "market",
            "trend",
            "window",
            "demand",
            "monthly",
            "subscription",
            "setup",
            "ship",
            "tool",
            "tooling",
            "turn",
            "review",
            "service",
            "operator",
            "team",
            "lead",
            "agency",
            "founder",
            "research",
        }
        and token not in trend_tokens
    }
    return {token for token in tokens if token}


def build_semantic_profile(idea: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "categories": category_tokens_for_idea(idea),
        "audience": audience_tokens_for_idea(idea),
        "workflows": workflow_tokens_for_idea(idea),
        "repos": repo_tokens_for_idea(idea),
        "tokens": semantic_text_tokens_for_idea(idea),
    }


def semantic_signature(idea: dict[str, Any]) -> str:
    profile = build_semantic_profile(idea)
    parts = [
        "c:" + ",".join(sorted(profile["categories"])),
        "a:" + ",".join(sorted(profile["audience"])),
        "w:" + ",".join(sorted(profile["workflows"])),
        "t:" + ",".join(sorted(profile["tokens"])[:6]),
    ]
    return " | ".join(part for part in parts if not part.endswith(":"))


def idea_similarity_score(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_name = normalize_idea_name(left.get("name", ""))
    right_name = normalize_idea_name(right.get("name", ""))
    if left_name and left_name == right_name:
        return 1.0
    left_profile = build_semantic_profile(left)
    right_profile = build_semantic_profile(right)
    category_score = overlap_score(left_profile["categories"], right_profile["categories"])
    audience_score = overlap_score(left_profile["audience"], right_profile["audience"])
    workflow_score = overlap_score(left_profile["workflows"], right_profile["workflows"])
    repo_score = overlap_score(left_profile["repos"], right_profile["repos"])
    token_score = overlap_score(left_profile["tokens"], right_profile["tokens"])
    score = (
        category_score * 0.34
        + audience_score * 0.22
        + workflow_score * 0.18
        + repo_score * 0.12
        + token_score * 0.14
    )
    if category_score >= 1.0 and audience_score >= 0.5 and workflow_score >= 0.5:
        score = max(score, 0.82)
    if category_score >= 1.0 and workflow_score >= 1.0 and token_score >= 0.25:
        score = max(score, 0.76)
    if repo_score >= 1.0 and workflow_score >= 0.5:
        score = max(score, 0.72)
    return score


def idea_pattern_text(idea: dict[str, Any]) -> str:
    return " ".join(
        [
            str(idea.get("name") or ""),
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("why_non_obvious") or ""),
            str(idea.get("hidden_customer") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(str(step) for step in idea.get("build_plan", [])),
            " ".join(str(axis) for axis in idea.get("breakthrough_axes", [])),
        ]
    ).lower()


def generic_pattern_matches(text: str) -> list[str]:
    return [pattern for pattern in GENERIC_PATTERNS_TO_REJECT if re.search(pattern, text)]


def is_generic_pattern(idea: dict[str, Any]) -> bool:
    return bool(generic_pattern_matches(idea_pattern_text(idea)))


def load_recent_idea_snapshots(reports_dir: Path, limit: int = 18) -> list[dict[str, Any]]:
    if not reports_dir.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for file_path in sorted(reports_dir.glob("*.json"), reverse=True):
        report_payload = load_json_file(file_path, {})
        if not isinstance(report_payload, dict):
            continue
        for idea in report_payload.get("ideas", []) if isinstance(report_payload.get("ideas"), list) else []:
            if not isinstance(idea, dict):
                continue
            snapshots.append(
                {
                    "date": str(report_payload.get("date") or file_path.stem),
                    "name": str(idea.get("name") or "").strip(),
                    "summary": str(idea.get("summary") or "").strip(),
                    "novel_mechanism": str(idea.get("novel_mechanism") or "").strip(),
                    "why_non_obvious": str(idea.get("why_non_obvious") or "").strip(),
                    "hidden_customer": str(idea.get("hidden_customer") or "").strip(),
                    "breakthrough_axes": [str(axis) for axis in idea.get("breakthrough_axes", []) if isinstance(axis, str)],
                    "why_now": str(idea.get("why_now") or "").strip(),
                    "revenue_model": str(idea.get("revenue_model") or "").strip(),
                    "build_plan": [str(step) for step in idea.get("build_plan", []) if isinstance(step, str)],
                    "repos": [str(name) for name in idea.get("repos", []) if isinstance(name, str)],
                    "trends": [str(title) for title in idea.get("trends", []) if isinstance(title, str)],
                    "category_focus": [str(label) for label in idea.get("category_focus", []) if isinstance(label, str)],
                    "semantic_signature": str(idea.get("semantic_signature") or "").strip(),
                    "recurrence_group_id": str(idea.get("recurrence_group_id") or "").strip(),
                }
            )
            if len(snapshots) >= limit:
                return snapshots
    return snapshots


def choose_creative_angle(report_date: str, trends: list[dict[str, Any]], repos: list[dict[str, Any]], recent_ideas: list[dict[str, Any]]) -> dict[str, Any]:
    trend_titles = "|".join(trend.get("title", "") for trend in trends[:5])
    repo_names = "|".join(repo.get("full_name", "") for repo in repos[:5])
    seed = stable_hash_int(report_date, trend_titles, repo_names, str(len(recent_ideas)))
    return CREATIVE_ANGLES[seed % len(CREATIVE_ANGLES)]


def pick_surprise_trends(trends: list[dict[str, Any]], report_date: str, count: int = 4) -> list[dict[str, Any]]:
    if not trends:
        return []
    start_index = max(1, len(trends) // 3)
    pool = trends[start_index:] or trends
    ordered = sorted(pool, key=lambda trend: stable_hash_int(report_date, str(trend.get("title") or ""), str(trend.get("source_id") or "")))
    return ordered[: min(count, len(ordered))]


def build_repo_combo_candidates(repos: list[dict[str, Any]], report_date: str, limit: int = 10) -> list[dict[str, Any]]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for repo in repos:
        category = str(repo.get("category") or "Other")
        by_category[category].append(repo)
    for category in by_category:
        by_category[category].sort(key=lambda item: int(item.get("stargazers_count") or 0), reverse=True)
    combos: list[dict[str, Any]] = []
    for left_category, right_category in combinations(sorted(by_category), 2):
        left_options = by_category[left_category][:3]
        right_options = by_category[right_category][:3]
        if not left_options or not right_options:
            continue
        seed = stable_hash_int(report_date, left_category, right_category)
        left_repo = left_options[seed % len(left_options)]
        right_repo = right_options[(seed // 7) % len(right_options)]
        combos.append(
            {
                "categories": [left_category, right_category],
                "repos": [left_repo["full_name"], right_repo["full_name"]],
                "score": int(left_repo.get("stargazers_count") or 0) + int(right_repo.get("stargazers_count") or 0),
            }
        )
    combos.sort(key=lambda combo: (combo["score"], stable_hash_int(report_date, *combo["categories"])), reverse=True)
    selected: list[dict[str, Any]] = []
    category_usage: Counter[str] = Counter()
    for combo in combos:
        categories = combo["categories"]
        if any(category_usage[category] >= 2 for category in categories):
            continue
        selected.append(combo)
        for category in categories:
            category_usage[category] += 1
        if len(selected) >= limit:
            return selected
    for combo in combos:
        if combo in selected:
            continue
        selected.append(combo)
        if len(selected) >= limit:
            break
    return selected


def build_generation_context(
    report_date: str,
    trends: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    reports_dir: Path,
) -> dict[str, Any]:
    recent_ideas = load_recent_idea_snapshots(reports_dir)
    return {
        "angle": choose_creative_angle(report_date, trends, repos, recent_ideas),
        "recent_ideas": recent_ideas,
        "headline_trends": trends[:6],
        "surprise_trends": pick_surprise_trends(trends, report_date),
        "repo_combos": build_repo_combo_candidates(repos, report_date, limit=FALLBACK_IDEA_CANDIDATE_COUNT),
        "creative_operators": BREAKTHROUGH_OPERATORS,
    }


def load_starred_repos(cache_path: Path) -> list[dict[str, Any]]:
    cache = load_json_file(cache_path, {"repos": {}})
    repos = cache.get("repos", {}) if isinstance(cache, dict) else {}
    if not isinstance(repos, dict) or not repos:
        raise ValueError(f"Cache file is missing or empty: {cache_path}")
    items = [repo for repo in repos.values() if isinstance(repo, dict)]
    return sorted(items, key=lambda item: int(item.get("stargazers_count") or 0), reverse=True)


def fetch_newsnow_payload() -> list[dict[str, Any]]:
    payload = {"sources": DEFAULT_SOURCES}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    response, _ = http_json(NEWSNOW_ENDPOINT, headers=headers, payload=payload, timeout=30)
    if not isinstance(response, list):
        raise ValueError("Unexpected NewsNow response format.")
    return response


def format_source_name(source_id: str) -> str:
    parts = [part for part in source_id.replace("_", "-").split("-") if part]
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts)


def trend_relevance_score(item: dict[str, Any]) -> int:
    source_id = str(item.get("source_id") or "")
    text = f"{item.get('title', '')} {item.get('context', '')} {item.get('info', '')}".lower()
    source_bonus = {
        "github-trending-today": 30,
        "producthunt": 28,
        "hackernews": 28,
        "juejin": 24,
        "freebuf": 24,
        "sspai": 18,
        "wallstreetcn-hot": 18,
        "xueqiu-hotstock": 18,
        "cls-hot": 16,
        "36kr-renqi": 16,
        "nowcoder": 14,
    }.get(source_id, 0)
    positive_keywords = [
        "ai",
        "agent",
        "automation",
        "code",
        "developer",
        "github",
        "open source",
        "startup",
        "saas",
        "security",
        "search",
        "seo",
        "workflow",
        "data",
        "finance",
        "trading",
        "growth",
        "robot",
        "app",
        "模型",
        "代码",
        "安全",
        "开发",
        "产品",
        "创业",
        "增长",
        "数据",
        "金融",
    ]
    negative_keywords = [
        "电视剧",
        "电影",
        "综艺",
        "球员",
        "比赛",
        "演唱会",
        "票房",
        "恋爱",
        "明星",
        "动画",
        "idol",
        "celebrity",
        "football",
        "basketball",
        "anime",
        "movie",
        "show",
    ]
    return source_bonus + sum(8 for keyword in positive_keywords if keyword in text) - sum(10 for keyword in negative_keywords if keyword in text)


def dedupe_trends(payload: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flattened: list[dict[str, Any]] = []
    source_statuses: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for source_index, block in enumerate(payload):
        if not isinstance(block, dict):
            continue
        source_id = str(block.get("id") or f"source-{source_index}")
        status = str(block.get("status") or "unknown")
        items = block.get("items") if isinstance(block.get("items"), list) else []
        source_statuses.append(
            {
                "id": source_id,
                "name": format_source_name(source_id),
                "status": status,
                "item_count": len(items),
            }
        )
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            normalized = re.sub(r"\s+", " ", title).lower()
            if normalized in seen_titles:
                continue
            seen_titles.add(normalized)
            extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
            flattened.append(
                {
                    "source_id": source_id,
                    "source_name": format_source_name(source_id),
                    "source_rank": item_index + 1,
                    "status": status,
                    "title": title,
                    "context": str(extra.get("hover") or ""),
                    "info": str(extra.get("info") or ""),
                    "url": str(item.get("url") or ""),
                }
            )
    flattened.sort(
        key=lambda item: (
            trend_relevance_score(item),
            -int(item["source_rank"]),
            stable_hash_int(str(item.get("title") or ""), str(item.get("source_id") or "")),
        ),
        reverse=True,
    )
    return flattened[:MAX_TRENDS], source_statuses


def build_repo_shortlist(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excluded_terms = [
        "awesome",
        "public api",
        "public-apis",
        "curated list",
        "starter",
        "boilerplate",
        "template",
        "usecases",
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    filtered: list[dict[str, Any]] = []
    for repo in repos:
        category = str(repo.get("category") or "Other")
        if category == "Other":
            continue
        text = " ".join(
            [
                str(repo.get("full_name") or ""),
                str(repo.get("description") or ""),
                " ".join(repo.get("tags") or []),
            ]
        ).lower()
        if any(term in text for term in excluded_terms):
            continue
        filtered.append(repo)
        grouped[category].append(repo)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in sorted(grouped.keys()):
        top_items = sorted(
            grouped[category],
            key=lambda item: int(item.get("stargazers_count") or 0),
            reverse=True,
        )[:1]
        for repo in top_items:
            full_name = str(repo.get("full_name") or "")
            if full_name and full_name not in seen:
                selected.append(repo)
                seen.add(full_name)
    for theme in REPO_THEMES:
        ranked = sorted(
            filtered,
            key=lambda item: (
                sum(
                    1
                    for keyword in theme["keywords"]
                    if keyword in " ".join(
                        [
                            str(item.get("full_name") or ""),
                            str(item.get("description") or ""),
                            " ".join(item.get("tags") or []),
                            str(item.get("category") or ""),
                        ]
                    ).lower()
                ),
                int(item.get("stargazers_count") or 0),
            ),
            reverse=True,
        )
        added = 0
        for repo in ranked:
            if added >= theme["limit"]:
                break
            full_name = str(repo.get("full_name") or "")
            if not full_name or full_name in seen:
                continue
            text = " ".join(
                [
                    full_name,
                    str(repo.get("description") or ""),
                    " ".join(repo.get("tags") or []),
                    str(repo.get("category") or ""),
                ]
            ).lower()
            score = sum(1 for keyword in theme["keywords"] if keyword in text)
            if score <= 0:
                continue
            selected.append(repo)
            seen.add(full_name)
            added += 1
    selected.sort(key=lambda item: int(item.get("stargazers_count") or 0), reverse=True)
    trimmed = selected[:MAX_REPOS]
    return [
        {
            "full_name": repo.get("full_name", ""),
            "category": repo.get("category", "Other"),
            "description": repo.get("description", ""),
            "tags": repo.get("tags") or [],
            "stargazers_count": int(repo.get("stargazers_count") or 0),
            "html_url": repo.get("html_url", ""),
        }
        for repo in trimmed
        if repo.get("full_name")
    ]


def build_llm_prompt(
    report_date: str,
    trends: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    generation_context: dict[str, Any],
) -> str:
    # Only send top 10 repos, minimal info
    repo_payload = [
        f"{repo['full_name']} | {repo['category']}"
        for repo in repos[:10]
    ]
    angle = generation_context.get("angle", {})
    # Only send trend titles, no context/info/url
    headline_trends = [
        trend["title"]
        for trend in generation_context.get("headline_trends", [])[:6]
    ]
    surprise_trends = [
        trend["title"]
        for trend in generation_context.get("surprise_trends", [])[:4]
    ]
    creative_operators = [
        f"{op['label']}: {', '.join(op['axes'])}"
        for op in generation_context.get("creative_operators", [])
    ]
    return (
        f"Date: {report_date}\n"
        f"Lens: {angle.get('label', 'Fresh opportunity')} — {angle.get('directive', '')}\n\n"
        f"Trends (anchor at least 5 ideas): {', '.join(headline_trends)}\n"
        f"Surprise trends (use 2+): {', '.join(surprise_trends)}\n\n"
        f"Breakthrough lenses:\n" + "\n".join(f"- {op}" for op in creative_operators) + "\n\n"
        f"Repos to combine:\n" + "\n".join(f"- {r}" for r in repo_payload)
    )


def generate_ideas_with_llm(
    report_date: str,
    trends: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    env: dict[str, str],
    generation_context: dict[str, Any],
) -> list[dict[str, Any]]:
    base_url = env["ANTHROPIC_BASE_URL"].rstrip("/")
    endpoint = f"{base_url}/v1/messages"
    payload = {
        "model": env.get("ANTHROPIC_MODEL") or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or "MiniMax-M2.7",
        "max_tokens": 4200,
        "temperature": 0.63,
        "system": OPPORTUNITY_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": build_llm_prompt(report_date, trends, repos, generation_context)}],
            }
        ],
    }
    headers = {
        "x-api-key": env["ANTHROPIC_AUTH_TOKEN"],
        "anthropic-version": "2023-06-01",
    }
    response, _ = http_json(endpoint, headers=headers, payload=payload, timeout=45)
    content = response.get("content", [])
    text = "\n".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ).strip()
    if not text:
        raise ValueError("LLM did not return text content.")
    parsed = parse_json_object(text)
    ideas = parsed.get("ideas")
    if not isinstance(ideas, list):
        raise ValueError("LLM did not return an ideas array.")
    return [idea for idea in ideas if isinstance(idea, dict)]


def first_matching_trends(trends: list[dict[str, Any]], keywords: list[str], fallback_count: int = 2) -> list[dict[str, Any]]:
    matched = [
        trend
        for trend in trends
        if any(keyword in f"{trend['title']} {trend['context']}".lower() for keyword in keywords)
    ]
    return matched[:fallback_count] or trends[:fallback_count]


def pick_repo_group(repos: list[dict[str, Any]], categories: list[str], limit: int = 3) -> list[dict[str, Any]]:
    selected = [repo for repo in repos if repo["category"] in categories]
    return selected[:limit]


def pick_repos_by_keywords(repos: list[dict[str, Any]], keywords: list[str], limit: int = 3) -> list[dict[str, Any]]:
    ranked = sorted(
        repos,
        key=lambda repo: (
            sum(
                1
                for keyword in keywords
                if keyword in " ".join(
                    [
                        repo["full_name"],
                        repo["category"],
                        repo["description"],
                        " ".join(repo["tags"]),
                    ]
                ).lower()
            ),
            repo["stargazers_count"],
        ),
        reverse=True,
    )
    return [repo for repo in ranked if any(keyword in f"{repo['full_name']} {repo['category']} {repo['description']} {' '.join(repo['tags'])}".lower() for keyword in keywords)][:limit]


def format_breakthrough_template(template: str, values: dict[str, str]) -> str:
    return template.format(**{key: value for key, value in values.items() if isinstance(value, str)})


def short_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value).strip())
    if not cleaned:
        return ""
    return cleaned.split("/")[0] if " / " in cleaned else cleaned.split()[0]


def hidden_customer_seed(categories: list[str], trend_title: str) -> str:
    lowered = " ".join(categories).lower()
    if "security" in lowered:
        return "trust and risk operators"
    if "finance" in lowered or "trading" in lowered:
        return "timing-sensitive market desks"
    if "seo" in lowered or "marketing" in lowered:
        return "distribution teams defending demand capture"
    if "data" in lowered or "analytics" in lowered:
        return "analysts who carry explanation debt"
    return f"specialists reacting to {short_name(trend_title) or 'the shift'}"


def format_breakthrough_name(prefix: str, left_alias: str, right_alias: str, suffix: str, operator_label: str) -> str:
    operator_token = operator_label.split()[0]
    return f"{prefix} {left_alias}-{right_alias} {operator_token} {suffix}"


def fallback_revenue_model(operator_label: str) -> str:
    normalized = operator_label.lower()
    if "constraint" in normalized:
        return "Sell exception review retainers plus proprietary failure data feeds."
    if "capability" in normalized:
        return "Charge for the operating layer first, then add implementation retainers."
    if "second-order" in normalized:
        return "Take broker fees on verified access and sell the resulting market data."
    return "Sell rehearsal subscriptions tied to avoided mistakes and premium planning reviews."


def build_dynamic_fallback_ideas(
    report_date: str,
    trends: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    generation_context: dict[str, Any],
) -> list[dict[str, Any]]:
    ideas: list[dict[str, Any]] = []
    headline_trends = generation_context.get("headline_trends", []) or trends[:6]
    surprise_trends = generation_context.get("surprise_trends", []) or trends[:4]
    prioritized_trends = headline_trends + [
        trend for trend in surprise_trends if str(trend.get("title") or "") not in {str(item.get("title") or "") for item in headline_trends}
    ]
    combos = generation_context.get("repo_combos", []) or build_repo_combo_candidates(
        repos,
        report_date,
        limit=FALLBACK_IDEA_CANDIDATE_COUNT,
    )
    angle = generation_context.get("angle", CREATIVE_ANGLES[0])
    operators = generation_context.get("creative_operators", BREAKTHROUGH_OPERATORS) or BREAKTHROUGH_OPERATORS
    for index, combo in enumerate(combos[:FALLBACK_IDEA_CANDIDATE_COUNT]):
        categories = combo.get("categories", [])
        if len(categories) < 2:
            continue
        repos_for_idea = [name for name in combo.get("repos", []) if isinstance(name, str)]
        if len(repos_for_idea) < 2:
            continue
        seed = stable_hash_int(report_date, str(index), *categories, *repos_for_idea)
        trend = prioritized_trends[index % len(prioritized_trends)] if prioritized_trends else (trends[index % len(trends)] if trends else {})
        left_alias = CATEGORY_ALIASES.get(categories[0], categories[0].split()[0])
        right_alias = CATEGORY_ALIASES.get(categories[1], categories[1].split()[0])
        prefix = FALLBACK_PREFIXES[seed % len(FALLBACK_PREFIXES)]
        suffix = FALLBACK_SUFFIXES[(seed // 11) % len(FALLBACK_SUFFIXES)]
        operator = operators[(seed // 13) % len(operators)]
        hidden_customer = operator["customer_templates"][(seed // 17) % len(operator["customer_templates"])]
        seed_customer = hidden_customer_seed(categories, trend_title=str(trend.get("title") or ""))
        # First compute hidden_customer_text since it's needed for template_values
        hidden_customer_text = format_breakthrough_template(hidden_customer, {
            "trend_title": str(trend.get("title") or "a volatile shift"),
            "category_a": categories[0],
            "category_b": categories[1],
            "left_alias": left_alias,
            "right_alias": right_alias,
            "left_alias_lower": left_alias.lower(),
            "right_alias_lower": right_alias.lower(),
            "hidden_customer_seed": seed_customer,
        })
        template_values = {
            "trend_title": str(trend.get("title") or "a volatile shift"),
            "category_a": categories[0],
            "category_b": categories[1],
            "left_alias": left_alias,
            "right_alias": right_alias,
            "left_alias_lower": left_alias.lower(),
            "right_alias_lower": right_alias.lower(),
            "hidden_customer_seed": seed_customer,
            "mechanism": operator["label"].lower(),
            "customer": hidden_customer_text,
        }
        idea_name = format_breakthrough_name(prefix, left_alias, right_alias, suffix, operator["label"])
        trend_title = str(trend.get("title") or "a volatile trend window")
        # Pick a diverse summary template based on seed
        summary_template = FALLBACK_SUMMARY_TEMPLATES[seed % len(FALLBACK_SUMMARY_TEMPLATES)]
        revenue_template = FALLBACK_REVENUE_MODELS[(seed // 19) % len(FALLBACK_REVENUE_MODELS)]
        ideas.append(
            {
                "name": idea_name,
                "summary": format_breakthrough_template(summary_template, {**template_values, "trend_title": trend_title}),
                "novel_mechanism": format_breakthrough_template(operator["mechanism_template"], {**template_values, "trend_title": trend_title}),
                "why_non_obvious": format_breakthrough_template(operator["why_template"], {**template_values, "trend_title": trend_title}),
                "hidden_customer": hidden_customer_text,
                "breakthrough_axes": operator["axes"][:4],
                "why_now": f"{angle.get('directive', 'A new behavior just appeared.')} Today's NewsNow signal around {trend_title} changes who feels the pain first, so a specialized concept can win before the mainstream stack adapts.",
                "revenue_model": format_breakthrough_template(revenue_template, {**template_values, "trend_title": trend_title}),
                "build_plan": [format_breakthrough_template(step, {**template_values, "trend_title": trend_title}) for step in operator["plan_templates"][:3]],
                "trends": [trend_title],
                "repos": repos_for_idea,
                "category_focus": categories[:3],
                "confidence": "medium" if index % 4 else "high",
            }
        )
    return ideas


def ideas_are_similar(left: dict[str, Any], right: dict[str, Any]) -> bool:
    similarity = idea_similarity_score(left, right)
    if similarity >= IDEA_SIMILARITY_THRESHOLD:
        return True
    left_repos = set(left.get("repos", []))
    right_repos = set(right.get("repos", []))
    return bool(left_repos and right_repos and len(left_repos & right_repos) >= 2)


def select_fresh_ideas(
    candidates: list[dict[str, Any]],
    repo_lookup: dict[str, dict[str, Any]],
    repo_shortlist: list[dict[str, Any]],
    trend_titles: set[str],
    available_trends: list[dict[str, Any]],
    recent_ideas: list[dict[str, Any]],
    limit: int = MAX_IDEA_COUNT,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    comparison_pool = list(recent_ideas)
    sanitized_candidates = [sanitize_idea(candidate, repo_lookup, repo_shortlist, trend_titles, available_trends) for candidate in candidates]
    for idea in sanitized_candidates:
        if not idea.get("name"):
            continue
        if is_generic_pattern(idea):
            continue
        if any(ideas_are_similar(idea, seen) for seen in comparison_pool):
            continue
        selected.append(idea)
        comparison_pool.append(idea)
        if len(selected) >= limit:
            return selected
    return selected[:limit]


def sanitize_idea(
    idea: dict[str, Any],
    repo_lookup: dict[str, dict[str, Any]],
    repo_shortlist: list[dict[str, Any]],
    trend_titles: set[str],
    available_trends: list[dict[str, Any]],
) -> dict[str, Any]:
    repo_names = [name for name in idea.get("repos", []) if isinstance(name, str) and name in repo_lookup]
    selected_trends = [title for title in idea.get("trends", []) if isinstance(title, str) and title in trend_titles]
    build_plan = [str(step).strip() for step in idea.get("build_plan", []) if str(step).strip()][:3]
    category_focus = [str(label).strip() for label in idea.get("category_focus", []) if str(label).strip()][:3]
    breakthrough_axes = [str(axis).strip() for axis in idea.get("breakthrough_axes", []) if str(axis).strip()][:4]
    if len(repo_names) < 2:
        supplemental = [
            repo["full_name"]
            for repo in repo_shortlist
            if repo["full_name"] not in repo_names
            and (not category_focus or repo["category"] in category_focus)
        ]
        repo_names.extend(supplemental[: 2 - len(repo_names)])
    if not selected_trends and available_trends:
        selected_trends = [available_trends[0]["title"]]
    return {
        "name": str(idea.get("name") or "Untitled Opportunity").strip(),
        "summary": str(idea.get("summary") or "").strip(),
        "novel_mechanism": str(idea.get("novel_mechanism") or "").strip(),
        "why_non_obvious": str(idea.get("why_non_obvious") or "").strip(),
        "hidden_customer": str(idea.get("hidden_customer") or "").strip(),
        "breakthrough_axes": breakthrough_axes,
        "why_now": str(idea.get("why_now") or "").strip(),
        "revenue_model": str(idea.get("revenue_model") or "").strip(),
        "build_plan": build_plan or ["Capture one high-signal event", "Route it through one proof loop", "Sell the first paid wedge before full automation"],
        "trends": selected_trends,
        "repos": repo_names,
        "category_focus": category_focus,
        "confidence": str(idea.get("confidence") or "medium").strip().lower(),
    }


def keyword_tokens(text: str) -> set[str]:
    raw_tokens = re.findall(r"[a-z0-9][a-z0-9\-\+]{2,}", text.lower())
    stop_words = {
        "and",
        "are",
        "but",
        "can",
        "for",
        "with",
        "from",
        "help",
        "into",
        "that",
        "this",
        "your",
        "their",
        "about",
        "there",
        "which",
        "while",
        "where",
        "daily",
        "today",
        "turn",
        "using",
        "build",
        "launch",
        "trend",
        "trends",
        "ideas",
        "idea",
        "project",
        "projects",
        "repo",
        "repos",
    }
    return {token for token in raw_tokens if token not in stop_words}


def clamp_score(value: int) -> int:
    return max(0, min(100, value))


def score_on_ten(value: int | float) -> int:
    if value <= 0:
        return 1
    return max(1, min(10, int(round(float(value) / 10))))


def attach_ten_point_scores(idea: dict[str, Any]) -> dict[str, Any]:
    score_fields = [
        "trend_repo_match_score",
        "revenue_score",
        "niche_difficulty_score",
        "build_speed_score",
        "monetization_latency_score",
        "recurring_revenue_score",
        "novelty_score",
        "cross_domain_score",
        "serendipity_score",
        "breakthrough_score",
        "conventionality_score",
        "founder_score",
        "opportunity_score",
    ]
    return {f"{field}_10": score_on_ten(float(idea.get(field) or 0)) for field in score_fields}


def coerce_text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def idea_creativity_text(idea: dict[str, Any], repo_details: list[dict[str, Any]], trend_details: list[dict[str, Any]]) -> str:
    return " ".join(
        [
            str(idea.get("name") or ""),
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("why_non_obvious") or ""),
            str(idea.get("hidden_customer") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(coerce_text_list(idea.get("build_plan"))),
            " ".join(coerce_text_list(idea.get("breakthrough_axes"))),
            " ".join(str(repo.get("category") or "") for repo in repo_details),
            " ".join(
                f"{trend.get('title', '')} {trend.get('context', '')} {trend.get('info', '')}"
                for trend in trend_details
            ),
        ]
    )


def idea_category_set(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> set[str]:
    categories = {str(label).strip() for label in idea.get("category_focus", []) if str(label).strip()}
    categories.update(str(repo.get("category") or "").strip() for repo in repo_details if str(repo.get("category") or "").strip())
    return categories


def category_vector_distance(categories: set[str]) -> float:
    vectors = [CATEGORY_VECTOR_MAP.get(category, CATEGORY_VECTOR_MAP["Other"]) for category in categories if category]
    if len(vectors) < 2:
        return 0.0
    union = set().union(*vectors)
    pair_count = 0
    total_distance = 0.0
    for left_index, left in enumerate(vectors):
        for right in vectors[left_index + 1 :]:
            pair_count += 1
            overlap = len(left & right)
            total_distance += 1 - (overlap / max(1, len(union)))
    return total_distance / max(1, pair_count)


def mechanism_family_count(text: str) -> int:
    lowered = text.lower()
    return sum(1 for keywords in MECHANISM_FAMILY_KEYWORDS.values() if any(keyword in lowered for keyword in keywords))


# Template phrases from BREAKTHROUGH_OPERATORS that indicate literal template usage
TEMPLATE_LITERAL_PHRASES = {
    "turn the pain created by",
    "capture the exception surface",
    "instrument the exception path",
    "specialists downstream from",
    "monetizes the costly exceptions",
    "the review burden that appear after adoption",
    "most teams will build the obvious wrapper",
    "import the best mechanism from",
    "proven pattern to solve their problem",
    "build a secondary market around",
    "create a synthetic twin for decisions triggered by",
    "convert repeated failures into a scored review queue",
    "sell the review protocol before automating the whole loop",
    "package the new ritual as a premium",
}


def template_literal_count(text: str) -> int:
    lowered = text.lower()
    count = sum(1 for phrase in TEMPLATE_LITERAL_PHRASES if phrase in lowered)
    # Penalize structural template: "move a X mechanism from A into B"
    if re.search(r"\bmove a \w+ mechanism from \w+ into\b", lowered):
        count += 2
    # Penalize if the summary starts with "Move a" (formulaic opening)
    if lowered.strip().startswith("move a "):
        count += 1
    return count


def transfer_distance_score(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> int:
    """Measure the semantic gap between source mechanism and target application."""
    novel_mechanism = str(idea.get("novel_mechanism") or "").lower()
    summary = str(idea.get("summary") or "").lower()
    why_non_obvious = str(idea.get("why_non_obvious") or "").lower()

    # Penalize template literal usage
    literal_count = template_literal_count(novel_mechanism + " " + why_non_obvious)

    # Measure genuine transfer: mechanism words vs target domain words
    mechanism_words = {
        "inversion", "transplant", "market", "twin", "synthetic",
        "protocol", "broker", "exchange", "constraint", "wedge",
        "exception", "review", "queue", "simulation", "mirror"
    }
    mechanism_hits = sum(1 for w in mechanism_words if w in novel_mechanism or w in why_non_obvious)

    # Check if the idea actually describes a specific mechanism transfer
    has_mechanism_verb = any(v in summary for v in ["import", "移植", "move", "transplant", "borrow", "steal", "adopt"])
    has_specific_target = len([c for c in (idea.get("category_focus") or []) if c]) >= 2

    score = 20
    score += mechanism_hits * 8
    score += 15 if has_mechanism_verb else 0
    score += 12 if has_specific_target else 0
    score -= literal_count * 18
    score -= len(generic_pattern_matches(novel_mechanism + " " + why_non_obvious)) * 12

    return clamp_score(score)


def template_diversity_penalty(ideas: list[dict[str, Any]], current_idx: int) -> int:
    """Penalize ideas that reuse the same breakthrough_axes as recent ideas."""
    current_axes = set(coerce_text_list(ideas[current_idx].get("breakthrough_axes", [])))
    if not current_axes:
        return 0

    penalty = 0
    for i in range(max(0, current_idx - 4), current_idx):
        prev_axes = set(coerce_text_list(ideas[i].get("breakthrough_axes", [])))
        overlap = len(current_axes & prev_axes)
        if overlap >= 2:
            penalty += overlap * 12
        elif overlap >= 1:
            penalty += 6

    return min(penalty, 30)


def hidden_customer_specificity(hidden_customer: str) -> int:
    lowered = hidden_customer.lower().strip()
    if not lowered:
        return 10
    tokens = {canonical_semantic_token(token) for token in keyword_tokens(lowered)}
    generic_tokens = {canonical_semantic_token(token) for token in GENERIC_CUSTOMERS}
    descriptor_tokens = {token for token in tokens if token not in generic_tokens}
    penalty = 0
    if lowered in GENERIC_CUSTOMERS:
        penalty += 24
    if tokens & generic_tokens:
        penalty += 12
        penalty += max(0, 2 - len(descriptor_tokens)) * 10
    penalty += max(0, 3 - len(tokens)) * 8
    if re.search(r"\b(?:small|lean|growing|busy|modern|technical|vertical|ai)\s+(?:teams|founders|operators|developers|companies|startups|agencies|analysts)\b", lowered):
        penalty += 16
    if any(customer in lowered for customer in GENERIC_CUSTOMERS):
        penalty += 8
    bonus = 0
    if any(marker in lowered for marker in [" at ", " inside ", " after ", " before ", " during ", " responsible for ", " approving "]):
        bonus += 8
    if len(descriptor_tokens) >= 3:
        bonus += 6
    return clamp_score(100 - penalty + bonus)


def compute_cross_domain_score(
    idea: dict[str, Any],
    repo_details: list[dict[str, Any]],
    trend_details: list[dict[str, Any]],
) -> int:
    categories = idea_category_set(idea, repo_details)
    bridge_count = max(0, len(categories) - 1)
    vector_distance = category_vector_distance(categories)
    trend_count = len({str(trend.get("title") or "").strip() for trend in trend_details if str(trend.get("title") or "").strip()})
    repo_count = len({str(repo.get("full_name") or "").strip() for repo in repo_details if str(repo.get("full_name") or "").strip()})
    score = 26
    score += min(bridge_count, 4) * 13
    score += round(vector_distance * 28)
    score += min(max(trend_count - 1, 0), 2) * 10
    score += min(max(repo_count - 2, 0), 2) * 6
    if len(categories) >= 3:
        score += 8
    return clamp_score(score)


def compute_novelty_score(
    idea: dict[str, Any],
    repo_details: list[dict[str, Any]],
    trend_details: list[dict[str, Any]],
) -> int:
    text = idea_creativity_text(idea, repo_details, trend_details)
    tokens = keyword_tokens(text)
    lowered = text.lower()
    generic_penalty = sum(6 for term in GENERIC_CONCEPT_TERMS if term in tokens or term in lowered)
    generic_penalty += len(generic_pattern_matches(lowered)) * 14
    axes = coerce_text_list(idea.get("breakthrough_axes"))
    mechanism_count = mechanism_family_count(" ".join([lowered, " ".join(axes).lower()]))
    summary_text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("why_non_obvious") or ""),
        ]
    ).lower()
    contrarian_hits = sum(1 for term in CONTRARIAN_SIGNAL_TERMS if term in summary_text)
    literal_count = template_literal_count(summary_text)
    transfer_dist = transfer_distance_score(idea, repo_details)
    score = 26
    score += min(len(tokens), 24)
    score += min(mechanism_count, 3) * 7
    score += min(len(axes), 3) * 4
    score += min(contrarian_hits, 3) * 5
    score += min(len(idea_category_set(idea, repo_details)), 3) * 4
    score += transfer_dist // 4
    score -= generic_penalty
    score -= literal_count * 14
    return clamp_score(score)


def breakthrough_certified(idea: dict[str, Any]) -> bool:
    return (
        int(idea.get("breakthrough_score") or 0) >= BREAKTHROUGH_SCORE_THRESHOLD
        and int(idea.get("novelty_score") or 0) >= NOVELTY_SCORE_THRESHOLD
        and int(idea.get("serendipity_score") or 0) >= SERENDIPITY_SCORE_THRESHOLD
        and int(idea.get("cross_domain_score") or 0) >= CROSS_DOMAIN_SCORE_THRESHOLD
        and int(idea.get("conventionality_score") or 0) < CONVENTIONALITY_SCORE_MAX
        and not bool(idea.get("generic_pattern_match"))
        and int(idea.get("hidden_customer_score") or 0) >= HIDDEN_CUSTOMER_SCORE_THRESHOLD
        and int(idea.get("mechanism_family_count") or 0) >= MINIMUM_MECHANISM_FAMILIES
    )


def compute_serendipity_score(
    idea: dict[str, Any],
    repo_details: list[dict[str, Any]],
    trend_details: list[dict[str, Any]],
) -> int:
    categories = idea_category_set(idea, repo_details)
    text = idea_creativity_text(idea, repo_details, trend_details).lower()
    novel_mechanism = str(idea.get("novel_mechanism") or "").lower()
    why_non_obvious = str(idea.get("why_non_obvious") or "").lower()
    literal_count = template_literal_count(novel_mechanism + " " + why_non_obvious)
    score = 24
    score += round(category_vector_distance(categories) * 24)
    score += min(len(categories), 3) * 5
    score += min(sum(1 for term in CONTRARIAN_SIGNAL_TERMS if term in text), 4) * 6
    score += 10 if idea.get("hidden_customer") else 0
    score += 8 if len(trend_details) >= 2 else 0
    score -= literal_count * 14
    return clamp_score(score)


def compute_trend_repo_match_score(
    idea: dict[str, Any],
    repo_details: list[dict[str, Any]],
    trend_details: list[dict[str, Any]],
) -> int:
    trend_text = " ".join(
        f"{trend.get('title', '')} {trend.get('context', '')} {trend.get('info', '')}"
        for trend in trend_details
    )
    repo_text = " ".join(
        f"{repo.get('full_name', '')} {repo.get('category', '')} {repo.get('description', '')} {' '.join(repo.get('tags', []))}"
        for repo in repo_details
    )
    trend_tokens = keyword_tokens(trend_text)
    repo_tokens = keyword_tokens(repo_text)
    overlap = len(trend_tokens & repo_tokens)
    idea_tokens = keyword_tokens(
        " ".join(
            [
                str(idea.get("summary") or ""),
                str(idea.get("novel_mechanism") or ""),
                str(idea.get("why_non_obvious") or ""),
                str(idea.get("why_now") or ""),
            ]
        )
    )
    coverage = len(idea.get("trends", [])) * 6 + len(repo_details) * 5
    alignment = len(idea_tokens & (trend_tokens | repo_tokens))
    confidence_bonus = {"high": 10, "medium": 4, "low": 0}.get(str(idea.get("confidence") or "medium"), 0)
    return clamp_score(28 + overlap * 8 + alignment * 5 + coverage + confidence_bonus)


def compute_revenue_score(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> int:
    text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("hidden_customer") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(str(step) for step in idea.get("build_plan", [])),
            " ".join(repo.get("category", "") for repo in repo_details),
        ]
    ).lower()
    strong_terms = ["subscription", "saas", "b2b", "credits", "white-label", "api", "protocol", "broker", "compliance", "retainer"]
    medium_terms = ["audit", "marketplace", "data", "workflow", "review", "research", "verification", "simulation"]
    score = 30
    score += sum(10 for term in strong_terms if term in text)
    score += sum(6 for term in medium_terms if term in text)
    score += min(len(repo_details), 4) * 4
    score += min(hidden_customer_specificity(str(idea.get("hidden_customer") or "")) // 10, 8)
    score += {"high": 10, "medium": 4, "low": 0}.get(str(idea.get("confidence") or "medium"), 0)
    return clamp_score(score)


def compute_niche_difficulty_score(
    idea: dict[str, Any],
    repo_details: list[dict[str, Any]],
    trend_details: list[dict[str, Any]],
) -> int:
    text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("hidden_customer") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(repo.get("category", "") for repo in repo_details),
            " ".join(f"{trend.get('title', '')} {trend.get('context', '')}" for trend in trend_details),
        ]
    ).lower()
    hard_terms = ["security", "trading", "finance", "health", "legal", "compliance", "enterprise", "marketplace", "regulator"]
    medium_terms = ["team", "workflow", "data", "analytics", "research", "developer", "simulation", "broker"]
    easy_terms = ["brief", "content", "landing", "newsletter", "directory", "report", "advisory"]
    difficulty = 40
    difficulty += sum(9 for term in hard_terms if term in text)
    difficulty += sum(5 for term in medium_terms if term in text)
    difficulty -= sum(6 for term in easy_terms if term in text)
    difficulty += max(0, len(repo_details) - 2) * 4
    difficulty += max(0, len(trend_details) - 2) * 2
    difficulty += max(0, len(idea_category_set(idea, repo_details)) - 2) * 4
    return clamp_score(difficulty)


def compute_build_speed_score(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> int:
    text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(str(step) for step in idea.get("build_plan", [])),
            " ".join(repo.get("category", "") for repo in repo_details),
        ]
    ).lower()
    fast_terms = ["audit", "brief", "newsletter", "report", "content", "landing", "review", "broker", "protocol"]
    slow_terms = ["marketplace", "trading", "security", "video", "agent", "infrastructure", "real-time", "operating system", "simulation"]
    score = 56
    score += sum(7 for term in fast_terms if term in text)
    score -= sum(6 for term in slow_terms if term in text)
    score -= max(0, len(repo_details) - 2) * 4
    score -= max(0, len(idea_category_set(idea, repo_details)) - 2) * 3
    return clamp_score(score)


def compute_monetization_latency_score(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> int:
    text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("hidden_customer") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(repo.get("category", "") for repo in repo_details),
        ]
    ).lower()
    fast_terms = ["b2b", "subscription", "white-label", "audit", "service", "credits", "review", "compliance", "retainer"]
    slow_terms = ["ads", "consumer", "creator", "community", "media", "platform"]
    score = 50
    score += sum(8 for term in fast_terms if term in text)
    score -= sum(7 for term in slow_terms if term in text)
    score += min(hidden_customer_specificity(str(idea.get("hidden_customer") or "")) // 12, 8)
    return clamp_score(score)


def compute_recurring_revenue_score(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> int:
    text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(repo.get("category", "") for repo in repo_details),
        ]
    ).lower()
    recurring_terms = ["subscription", "saas", "retainer", "data", "b2b", "protocol", "review", "verification", "simulation"]
    one_off_terms = ["commission", "affiliate", "ad", "sponsorship", "one-time", "template"]
    score = 46
    score += sum(8 for term in recurring_terms if term in text)
    score -= sum(7 for term in one_off_terms if term in text)
    return clamp_score(score)


def compute_breakthrough_score(
    novelty_score: int,
    cross_domain_score: int,
    serendipity_score: int,
    trend_repo_match_score: int,
    revenue_score: int,
    hidden_customer_score: int,
) -> int:
    weighted = (
        novelty_score * 0.32
        + cross_domain_score * 0.24
        + serendipity_score * 0.2
        + trend_repo_match_score * 0.1
        + revenue_score * 0.06
        + hidden_customer_score * 0.08
    )
    return clamp_score(round(weighted))


def compute_founder_score(
    niche_difficulty_score: int,
    build_speed_score: int,
    monetization_latency_score: int,
    recurring_revenue_score: int,
    trend_repo_match_score: int,
    revenue_score: int,
    breakthrough_score: int,
) -> int:
    difficulty_tailwind = 100 - niche_difficulty_score
    weighted = (
        difficulty_tailwind * 0.18
        + build_speed_score * 0.18
        + monetization_latency_score * 0.18
        + recurring_revenue_score * 0.15
        + breakthrough_score * 0.17
        + trend_repo_match_score * 0.08
        + revenue_score * 0.06
    )
    return clamp_score(round(weighted))


def score_explanations(idea: dict[str, Any]) -> dict[str, str]:
    strengths = [
        ("breakthrough_score", "The concept crosses domains in a way that feels legitimately new."),
        ("novelty_score", "The mechanism is distinct enough to avoid the usual niche-SaaS trap."),
        ("cross_domain_score", "The repo stack bridges distant categories instead of staying inside one lane."),
        ("serendipity_score", "It creates a surprising connection that still feels strategically coherent."),
        ("build_speed_score", "It looks shippable as a narrow first release."),
        ("monetization_latency_score", "The revenue path can start early without waiting for scale."),
        ("recurring_revenue_score", "The usage pattern supports repeatable monthly value."),
        ("trend_repo_match_score", "The trend signal and repo stack already line up."),
        ("revenue_score", "The pricing surface is visible from day one."),
        ("niche_difficulty_score", "The niche is constrained enough for a focused wedge."),
    ]
    weaknesses = [
        ("breakthrough_score", "The concept still reads closer to a familiar product than a discontinuous one."),
        ("novelty_score", "The core mechanism is too generic and risks blending into standard tooling."),
        ("cross_domain_score", "The current repo mix is still too local to create a real conceptual leap."),
        ("serendipity_score", "The connection is understandable, but not surprising enough yet."),
        ("niche_difficulty_score", "The niche carries trust, workflow, or compliance weight."),
        ("build_speed_score", "The MVP scope is still heavier than a fast founder build."),
        ("monetization_latency_score", "Value may be obvious before willingness to pay is."),
        ("recurring_revenue_score", "The business model risks looking one-off instead of compounding."),
        ("trend_repo_match_score", "The repo stack is not yet tightly matched to the trend."),
        ("revenue_score", "Pricing is present, but not sharp enough yet."),
    ]
    best_metric = max(
        strengths,
        key=lambda item: 100 - idea[item[0]] if item[0] == "niche_difficulty_score" else idea[item[0]],
    )
    worst_metric = min(
        weaknesses,
        key=lambda item: 100 - idea[item[0]] if item[0] == "niche_difficulty_score" else idea[item[0]],
    )
    return {
        "best_part": best_metric[1],
        "biggest_risk": worst_metric[1],
    }


def build_penalties(idea: dict[str, Any]) -> list[str]:
    penalties: list[str] = []
    if idea["breakthrough_score"] <= 58:
        penalties.append("The idea still feels too close to a conventional product shape.")
    if idea["cross_domain_score"] <= 54:
        penalties.append("It needs a stronger bridge across distant categories or signals.")
    if idea["serendipity_score"] <= 54:
        penalties.append("The concept is coherent, but it does not surprise enough yet.")
    if idea["niche_difficulty_score"] >= 68:
        penalties.append("High-trust niche increases validation and delivery burden.")
    if idea["build_speed_score"] <= 56:
        penalties.append("Current MVP shape is too broad for a fast solo launch.")
    if idea["monetization_latency_score"] <= 56:
        penalties.append("Revenue likely arrives after proof, not at first contact.")
    if idea["recurring_revenue_score"] <= 56:
        penalties.append("Retention loop is weak, so monthly revenue is less certain.")
    if idea["trend_repo_match_score"] <= 58:
        penalties.append("Trend signal and repo stack are only loosely connected.")
    if idea["revenue_score"] <= 62:
        penalties.append("Packaging still needs a sharper buyer and price point.")
    return penalties[:3]


def fastest_mvp(idea: dict[str, Any]) -> str:
    first_step = next((str(step).strip() for step in idea.get("build_plan", []) if str(step).strip()), "")
    if first_step:
        return f"Ship only the first wedge: {first_step}."
    if idea.get("trends"):
        return f"Start with a manual signal digest around {idea['trends'][0]}."
    return "Start with one narrow workflow and one paying user before expanding."


def likely_first_customer(idea: dict[str, Any], repo_details: list[dict[str, Any]]) -> str:
    hidden_customer = str(idea.get("hidden_customer") or "").strip()
    if hidden_customer:
        return hidden_customer
    text = " ".join(
        [
            str(idea.get("summary") or ""),
            str(idea.get("novel_mechanism") or ""),
            str(idea.get("why_now") or ""),
            str(idea.get("revenue_model") or ""),
            " ".join(repo.get("category", "") for repo in repo_details),
        ]
    ).lower()
    customer_map = [
        ("security", "Security teams at software companies"),
        ("devsecops", "Engineering teams that own CI and dependency hygiene"),
        ("content", "Content platforms with moderation and rights risk"),
        ("copyright", "Media platforms and rights management teams"),
        ("finance", "Operators who react to live market or risk data"),
        ("trading", "Independent traders and small market intelligence desks"),
        ("agri", "Agricultural traders, cooperatives, and food operators"),
        ("agency", "Agencies packaging monitoring or audits for clients"),
        ("creator", "Creators and solo operators who need lightweight tooling"),
        ("dashboard", "Operators who already live inside recurring dashboards"),
    ]
    for term, customer in customer_map:
        if term in text:
            return customer
    return "Small teams with an urgent workflow and budget to pay for speed."


def improvement_actions(idea: dict[str, Any]) -> list[str]:
    priorities = [
        ("breakthrough_score", 100 - idea["breakthrough_score"]),
        ("cross_domain_score", 100 - idea["cross_domain_score"]),
        ("serendipity_score", 100 - idea["serendipity_score"]),
        ("niche_difficulty_score", idea["niche_difficulty_score"]),
        ("build_speed_score", 100 - idea["build_speed_score"]),
        ("monetization_latency_score", 100 - idea["monetization_latency_score"]),
        ("recurring_revenue_score", 100 - idea["recurring_revenue_score"]),
        ("trend_repo_match_score", 100 - idea["trend_repo_match_score"]),
    ]
    ordered = [name for name, _ in sorted(priorities, key=lambda item: item[1], reverse=True)]
    actions: list[str] = []
    for name in ordered:
        if name == "breakthrough_score":
            actions.append("Replace the obvious product wrapper with a sharper mechanism, market design, or protocol.")
        elif name == "cross_domain_score":
            actions.append("Add a third category or borrow a proven mechanism from a distant field.")
        elif name == "serendipity_score":
            actions.append("Retarget the idea toward a hidden stakeholder who is downstream from the trend.")
        elif name == "niche_difficulty_score":
            actions.append("Narrow the buyer to one painful workflow and one high-urgency trigger.")
        elif name == "build_speed_score":
            actions.append(fastest_mvp(idea))
        elif name == "monetization_latency_score":
            actions.append("Sell the first version as a done-for-you service before broadening into product.")
        elif name == "recurring_revenue_score":
            actions.append("Add a recurring alert, report, or compliance loop so usage repeats monthly.")
        elif name == "trend_repo_match_score":
            actions.append("Swap one generic repo dependency for tooling that matches the active trend more directly.")
        if len(actions) == 2:
            break
    return actions


def founder_memo(
    idea: dict[str, Any],
    repo_details: list[dict[str, Any]],
) -> dict[str, Any]:
    explanations = score_explanations(idea)
    penalties = build_penalties(idea)
    improvements = improvement_actions(idea)
    why_high = " ".join(
        part
        for part in [
            explanations["best_part"],
            "The score rises when the concept is both non-obvious and still practical to sell."
            if idea["founder_score"] >= 60
            else "",
        ]
        if part
    )
    why_low = " ".join(
        part
        for part in [
            explanations["biggest_risk"],
            penalties[0] if penalties else "",
        ]
        if part
    )
    return {
        "best_part": explanations["best_part"],
        "biggest_risk": explanations["biggest_risk"],
        "fastest_mvp": fastest_mvp(idea),
        "first_customer": likely_first_customer(idea, repo_details),
        "novel_mechanism": str(idea.get("novel_mechanism") or "").strip(),
        "why_non_obvious": str(idea.get("why_non_obvious") or "").strip(),
        "why_high": why_high,
        "why_low": why_low,
        "top_penalties": penalties,
        "improve_next": improvements,
    }


def classify_build_decision(idea: dict[str, Any], memo: dict[str, Any]) -> dict[str, str]:
    if (
        idea["founder_score"] >= 62
        and bool(idea.get("breakthrough_certified"))
        and idea["build_speed_score"] >= 56
        and idea["monetization_latency_score"] >= 58
        and idea["niche_difficulty_score"] <= 62
    ):
        return {
            "label": "Build now",
            "tone": "good",
            "summary": memo["best_part"],
        }
    if (
        idea["founder_score"] >= 48
        and idea["breakthrough_score"] >= 50
        and idea["opportunity_score"] >= 52
        and idea["trend_repo_match_score"] >= 50
        and not bool(idea.get("generic_pattern_match"))
    ):
        return {
            "label": "Validate first",
            "tone": "caution",
            "summary": memo["biggest_risk"],
        }
    return {
        "label": "Avoid for now",
        "tone": "warning",
        "summary": memo["biggest_risk"],
    }


def enrich_ideas(
    ideas: list[dict[str, Any]],
    repo_lookup: dict[str, dict[str, Any]],
    trends: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trend_lookup = {trend["title"]: trend for trend in trends}
    enriched: list[dict[str, Any]] = []
    for idea in ideas:
        repo_details = [
            {
                "full_name": repo_name,
                "html_url": repo_lookup[repo_name]["html_url"],
                "category": repo_lookup[repo_name]["category"],
                "description": repo_lookup[repo_name]["description"],
                "stars": repo_lookup[repo_name]["stargazers_count"],
                "tags": repo_lookup[repo_name]["tags"],
            }
            for repo_name in idea["repos"]
            if repo_name in repo_lookup
        ]
        trend_details = [trend_lookup[title] for title in idea["trends"] if title in trend_lookup]
        match_score = compute_trend_repo_match_score(idea, repo_details, trend_details)
        revenue_score = compute_revenue_score(idea, repo_details)
        niche_difficulty_score = compute_niche_difficulty_score(idea, repo_details, trend_details)
        build_speed_score = compute_build_speed_score(idea, repo_details)
        monetization_latency_score = compute_monetization_latency_score(idea, repo_details)
        recurring_revenue_score = compute_recurring_revenue_score(idea, repo_details)
        novelty_score = compute_novelty_score(idea, repo_details, trend_details)
        cross_domain_score = compute_cross_domain_score(idea, repo_details, trend_details)
        serendipity_score = compute_serendipity_score(idea, repo_details, trend_details)
        hidden_customer_score = hidden_customer_specificity(str(idea.get("hidden_customer") or ""))
        mechanism_count = mechanism_family_count(
            " ".join(
                [
                    str(idea.get("novel_mechanism") or ""),
                    str(idea.get("why_non_obvious") or ""),
                    " ".join(coerce_text_list(idea.get("breakthrough_axes"))),
                ]
            ).lower()
        )
        generic_pattern_match = is_generic_pattern(idea)
        breakthrough_score = compute_breakthrough_score(
            novelty_score,
            cross_domain_score,
            serendipity_score,
            match_score,
            revenue_score,
            hidden_customer_score,
        )
        founder_score = compute_founder_score(
            niche_difficulty_score,
            build_speed_score,
            monetization_latency_score,
            recurring_revenue_score,
            match_score,
            revenue_score,
            breakthrough_score,
        )
        opportunity_score = clamp_score(round(revenue_score * 0.18 + match_score * 0.18 + founder_score * 0.26 + breakthrough_score * 0.38))
        conventionality_score = clamp_score(
            round(100 - (novelty_score * 0.42 + cross_domain_score * 0.28 + serendipity_score * 0.3))
        )
        idea_metrics = {
            **idea,
            "trend_repo_match_score": match_score,
            "revenue_score": revenue_score,
            "niche_difficulty_score": niche_difficulty_score,
            "build_speed_score": build_speed_score,
            "monetization_latency_score": monetization_latency_score,
            "recurring_revenue_score": recurring_revenue_score,
            "novelty_score": novelty_score,
            "cross_domain_score": cross_domain_score,
            "serendipity_score": serendipity_score,
            "breakthrough_score": breakthrough_score,
            "conventionality_score": conventionality_score,
            "hidden_customer_score": hidden_customer_score,
            "mechanism_family_count": mechanism_count,
            "generic_pattern_match": generic_pattern_match,
            "transfer_distance_score": transfer_distance_score(idea, repo_details),
            "founder_score": founder_score,
            "opportunity_score": opportunity_score,
            **attach_ten_point_scores(
                {
                    "trend_repo_match_score": match_score,
                    "revenue_score": revenue_score,
                    "niche_difficulty_score": niche_difficulty_score,
                    "build_speed_score": build_speed_score,
                    "monetization_latency_score": monetization_latency_score,
                    "recurring_revenue_score": recurring_revenue_score,
                    "novelty_score": novelty_score,
                    "cross_domain_score": cross_domain_score,
                    "serendipity_score": serendipity_score,
                    "breakthrough_score": breakthrough_score,
                    "conventionality_score": conventionality_score,
                    "founder_score": founder_score,
                    "opportunity_score": opportunity_score,
                }
            ),
        }
        idea_metrics["breakthrough_certified"] = breakthrough_certified(idea_metrics)
        memo = founder_memo(idea_metrics, repo_details)
        build_decision = classify_build_decision(idea_metrics, memo)
        enriched.append(
            {
                **idea_metrics,
                "semantic_signature": semantic_signature(idea_metrics),
                "repo_details": repo_details,
                "trend_details": trend_details,
                "founder_memo": memo,
                "build_decision": build_decision,
            }
        )
    # Sort first so template diversity penalty is applied in presentation order
    sorted_ideas = sorted(
        enriched,
        key=lambda item: (item["breakthrough_score"], item["founder_score"], item["opportunity_score"], item["revenue_score"]),
        reverse=True,
    )
    # Apply template diversity penalty across ideas
    for idx, idea in enumerate(sorted_ideas):
        penalty = template_diversity_penalty(sorted_ideas, idx)
        if penalty > 0:
            idea["breakthrough_score"] = max(0, idea["breakthrough_score"] - penalty)
            idea["novelty_score"] = max(0, idea["novelty_score"] - penalty // 2)
            idea["serendipity_score"] = max(0, idea["serendipity_score"] - penalty // 2)
    # Re-sort after penalty application
    return sorted(
        sorted_ideas,
        key=lambda item: (item["breakthrough_score"], item["founder_score"], item["opportunity_score"], item["revenue_score"]),
        reverse=True,
    )


def portfolio_quality_summary(ideas: list[dict[str, Any]]) -> dict[str, Any]:
    if not ideas:
        return {
            "avg_breakthrough_score": 0,
            "avg_conventionality_score": 0,
            "breakthrough_ideas": 0,
            "conventional_ideas": 0,
            "cross_domain_ideas": 0,
            "hidden_customer_ideas": 0,
            "certified_ideas": 0,
            "generic_pattern_ideas": 0,
        }
    breakthrough_threshold = BREAKTHROUGH_SCORE_THRESHOLD
    conventional_threshold = 62
    return {
        "avg_breakthrough_score": round(sum(int(idea.get("breakthrough_score") or 0) for idea in ideas) / len(ideas), 1),
        "avg_conventionality_score": round(sum(int(idea.get("conventionality_score") or 0) for idea in ideas) / len(ideas), 1),
        "breakthrough_ideas": sum(1 for idea in ideas if int(idea.get("breakthrough_score") or 0) >= breakthrough_threshold),
        "conventional_ideas": sum(1 for idea in ideas if int(idea.get("conventionality_score") or 0) >= conventional_threshold),
        "cross_domain_ideas": sum(1 for idea in ideas if int(idea.get("cross_domain_score") or 0) >= CROSS_DOMAIN_SCORE_THRESHOLD),
        "hidden_customer_ideas": sum(1 for idea in ideas if str(idea.get("hidden_customer") or "").strip()),
        "certified_ideas": sum(1 for idea in ideas if bool(idea.get("breakthrough_certified"))),
        "generic_pattern_ideas": sum(1 for idea in ideas if bool(idea.get("generic_pattern_match"))),
    }


def breakthrough_quality_checks(ideas: list[dict[str, Any]]) -> list[str]:
    if not ideas:
        return ["No ideas were generated."]
    summary = portfolio_quality_summary(ideas)
    minimum_breakthrough_ideas = max(3, math.ceil(len(ideas) * 0.3))
    minimum_certified_ideas = max(2, math.ceil(len(ideas) * 0.2))
    maximum_conventional_ideas = max(2, math.floor(len(ideas) * 0.4))
    minimum_cross_domain_ideas = max(4, math.ceil(len(ideas) * 0.4))
    failures: list[str] = []
    if summary["avg_breakthrough_score"] < 60:
        failures.append(f"Average breakthrough score is too low at {summary['avg_breakthrough_score']}.")
    if summary["avg_conventionality_score"] > 45:
        failures.append(f"Average conventionality score is too high at {summary['avg_conventionality_score']}.")
    if summary["breakthrough_ideas"] < minimum_breakthrough_ideas:
        failures.append(
            f"Only {summary['breakthrough_ideas']} ideas cleared the breakthrough threshold; need at least {minimum_breakthrough_ideas}."
        )
    if summary["conventional_ideas"] > maximum_conventional_ideas:
        failures.append(
            f"{summary['conventional_ideas']} ideas still look conventional; need {maximum_conventional_ideas} or fewer."
        )
    if summary["cross_domain_ideas"] < minimum_cross_domain_ideas:
        failures.append(
            f"Only {summary['cross_domain_ideas']} ideas show enough cross-domain synthesis; need at least {minimum_cross_domain_ideas}."
        )
    if summary["hidden_customer_ideas"] < len(ideas):
        failures.append("Every idea must name a hidden customer.")
    if summary["certified_ideas"] < minimum_certified_ideas:
        failures.append(
            f"Only {summary['certified_ideas']} ideas meet the full breakthrough certification bar; need at least {minimum_certified_ideas}."
        )
    if summary["generic_pattern_ideas"] > 0:
        failures.append(f"{summary['generic_pattern_ideas']} ideas still match rejected generic patterns.")
    return failures


def render_report(
    report_date: str,
    generated_at: str,
    source_statuses: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    repo_lookup: dict[str, dict[str, Any]],
    generation_mode: str,
) -> str:
    quality_summary = portfolio_quality_summary(ideas)
    lines = [
        f"# Opportunity Radar - {report_date}",
        "",
        f"Generated at: {generated_at}",
        f"Trend source: {NEWSNOW_ENDPOINT}",
        f"Star repo source: stars_cache.json",
        f"Mode: {generation_mode}",
        "",
        "## Breakthrough Quality",
        "",
        f"- Average breakthrough score: {quality_summary['avg_breakthrough_score']}",
        f"- Average conventionality score: {quality_summary['avg_conventionality_score']}",
        f"- Breakthrough ideas (>={BREAKTHROUGH_SCORE_THRESHOLD}): {quality_summary['breakthrough_ideas']}/{len(ideas)}",
        f"- Certified breakthrough ideas: {quality_summary['certified_ideas']}/{len(ideas)}",
        f"- Conventional ideas (>=62 conventionality): {quality_summary['conventional_ideas']}/{len(ideas)}",
        f"- Cross-domain ideas (>={CROSS_DOMAIN_SCORE_THRESHOLD} cross-domain): {quality_summary['cross_domain_ideas']}/{len(ideas)}",
        "",
        "## Source Health",
        "",
    ]
    for source in source_statuses:
        lines.append(f"- {source['name']} — {source['status']} ({source['item_count']} items)")
    lines.extend(["", "## Trend Snapshot", ""])
    for trend in trends:
        detail = trend["context"] or trend["info"] or "No extra context."
        lines.append(f"- [{trend['title']}]({trend['url']}) — {trend['source_name']} | {detail}")
    lines.extend(["", "## Project Ideas", ""])
    for idea in ideas:
        lines.append(f"### {idea['name']}")
        if idea["summary"]:
            lines.append(idea["summary"])
        if idea["trends"]:
            lines.append(f"Signals: {', '.join(idea['trends'])}")
        if idea["repos"]:
            repo_links = ", ".join(f"[{name}]({repo_lookup[name]['html_url']})" for name in idea["repos"] if name in repo_lookup)
            lines.append(f"Repo stack: {repo_links}")
        if idea["category_focus"]:
            lines.append(f"Category focus: {', '.join(idea['category_focus'])}")
        if idea.get("breakthrough_axes"):
            lines.append(f"Breakthrough axes: {', '.join(idea['breakthrough_axes'])}")
        if idea.get("hidden_customer"):
            lines.append(f"Hidden customer: {idea['hidden_customer']}")
        if idea.get("novel_mechanism"):
            lines.append(f"Novel mechanism: {idea['novel_mechanism']}")
        if idea.get("why_non_obvious"):
            lines.append(f"Why non-obvious: {idea['why_non_obvious']}")
        if idea["why_now"]:
            lines.append(f"Why now: {idea['why_now']}")
        if idea["revenue_model"]:
            lines.append(f"Revenue path: {idea['revenue_model']}")
        if idea["build_plan"]:
            lines.append(f"Launch path: {' -> '.join(idea['build_plan'])}")
        lines.append(
            "Founder score: "
            f"{idea.get('founder_score_10', score_on_ten(idea['founder_score']))}/10 | "
            f"Difficulty {idea.get('niche_difficulty_score_10', score_on_ten(idea['niche_difficulty_score']))}/10 | "
            f"Build speed {idea.get('build_speed_score_10', score_on_ten(idea['build_speed_score']))}/10 | "
            f"Monetization {idea.get('monetization_latency_score_10', score_on_ten(idea['monetization_latency_score']))}/10 | "
            f"Recurring {idea.get('recurring_revenue_score_10', score_on_ten(idea['recurring_revenue_score']))}/10"
        )
        lines.append(
            "Signal score: "
            f"Radar {idea.get('opportunity_score_10', score_on_ten(idea['opportunity_score']))}/10 | "
            f"Revenue {idea.get('revenue_score_10', score_on_ten(idea['revenue_score']))}/10 | "
            f"Fit {idea.get('trend_repo_match_score_10', score_on_ten(idea['trend_repo_match_score']))}/10"
        )
        lines.append(
            "Breakthrough score: "
            f"{idea.get('breakthrough_score_10', score_on_ten(idea['breakthrough_score']))}/10 | "
            f"Novelty {idea.get('novelty_score_10', score_on_ten(idea['novelty_score']))}/10 | "
            f"Cross-domain {idea.get('cross_domain_score_10', score_on_ten(idea['cross_domain_score']))}/10 | "
            f"Serendipity {idea.get('serendipity_score_10', score_on_ten(idea['serendipity_score']))}/10 | "
            f"Conventionality {idea.get('conventionality_score_10', score_on_ten(idea['conventionality_score']))}/10"
        )
        founder_memo_payload = idea.get("founder_memo", {})
        build_decision = idea.get("build_decision", {})
        if build_decision:
            lines.append(
                f"Decision: {build_decision.get('label', '')} — {build_decision.get('summary', '')}"
            )
        if founder_memo_payload:
            lines.append(f"Best part: {founder_memo_payload.get('best_part', '')}")
            lines.append(f"Biggest risk: {founder_memo_payload.get('biggest_risk', '')}")
            lines.append(f"Fastest MVP: {founder_memo_payload.get('fastest_mvp', '')}")
            lines.append(f"Likely first customer: {founder_memo_payload.get('first_customer', '')}")
            lines.append(f"Why this scores high: {founder_memo_payload.get('why_high', '')}")
            lines.append(f"What drags it down: {founder_memo_payload.get('why_low', '')}")
            penalties = founder_memo_payload.get("top_penalties", [])
            if penalties:
                lines.append(f"Top penalties: {' | '.join(penalties)}")
            improvements = founder_memo_payload.get("improve_next", [])
            if improvements:
                lines.append(f"Improve next: {' | '.join(improvements)}")
        lines.append(f"Confidence: {idea['confidence']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_site_payload(
    report_date: str,
    generated_at: str,
    source_statuses: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    generation_mode: str,
) -> dict[str, Any]:
    categories = sorted(
        {
            repo["category"]
            for idea in ideas
            for repo in idea.get("repo_details", [])
            if repo.get("category")
        }
        | {category for idea in ideas for category in idea.get("category_focus", []) if category}
    )
    return {
        "date": report_date,
        "generated_at": generated_at,
        "trend_source": NEWSNOW_ENDPOINT,
        "star_repo_source": "stars_cache.json",
        "mode": generation_mode,
        "available_categories": categories,
        "source_health": source_statuses,
        "trends": trends,
        "quality_summary": portfolio_quality_summary(ideas),
        "ideas": ideas,
    }


def lifecycle_momentum_label(score: int) -> str:
    if score >= 72:
        return "Accelerating"
    if score >= 58:
        return "Steady"
    if score >= 44:
        return "Watching"
    return "Cooling"


def build_lifecycle_momentum(members: list[dict[str, Any]], latest_collection_date: str) -> dict[str, Any]:
    ordered_members = sorted(
        members,
        key=lambda item: (item["date"], item["opportunity_score"], item["founder_score"], item["name"]),
    )
    latest_item = ordered_members[-1]
    previous_item = ordered_members[-2] if len(ordered_members) > 1 else None
    avg_founder = round(sum(item["founder_score"] for item in ordered_members) / len(ordered_members), 1)
    avg_opportunity = round(sum(item["opportunity_score"] for item in ordered_members) / len(ordered_members), 1)
    avg_revenue = round(sum(item["revenue_score"] for item in ordered_members) / len(ordered_members), 1)
    unique_dates = sorted({item["date"] for item in ordered_members})
    appearance_bonus = min(max(len(unique_dates) - 1, 0) * 6 + max(len(ordered_members) - 1, 0) * 2, 18)
    freshness_bonus = 8 if latest_item["date"] == latest_collection_date else 0
    delta_opportunity = latest_item["opportunity_score"] - (previous_item["opportunity_score"] if previous_item else avg_opportunity)
    delta_founder = latest_item["founder_score"] - (previous_item["founder_score"] if previous_item else avg_founder)
    delta_revenue = latest_item["revenue_score"] - (previous_item["revenue_score"] if previous_item else avg_revenue)
    score = clamp_score(
        round(
            latest_item["opportunity_score"] * 0.42
            + latest_item["founder_score"] * 0.18
            + avg_opportunity * 0.18
            + avg_founder * 0.1
            + avg_revenue * 0.06
            + appearance_bonus
            + freshness_bonus
            + max(delta_opportunity, 0) * 1.1
            + max(delta_founder, 0) * 0.6
            + max(delta_revenue, 0) * 0.45
            - max(-delta_opportunity, 0) * 0.9
            - max(-delta_founder, 0) * 0.4
        )
    )
    return {
        "momentum_score": score,
        "momentum_label": lifecycle_momentum_label(score),
        "avg_founder_score": avg_founder,
        "avg_opportunity_score": avg_opportunity,
        "avg_revenue_score": avg_revenue,
        "delta_founder_score": round(delta_founder, 1),
        "delta_opportunity_score": round(delta_opportunity, 1),
        "delta_revenue_score": round(delta_revenue, 1),
        "active_dates": len(unique_dates),
        "score_history": [
            {
                "date": item["date"],
                "name": item["name"],
                "founder_score": item["founder_score"],
                "revenue_score": item["revenue_score"],
                "opportunity_score": item["opportunity_score"],
                "report_path": item["report_path"],
            }
            for item in ordered_members
        ],
    }


def build_collection_payload(report_files: list[Path]) -> dict[str, Any]:
    raw_items: list[dict[str, Any]] = []
    categories: Counter[str] = Counter()
    trends: Counter[str] = Counter()
    exact_names: Counter[str] = Counter()
    reports_by_date: dict[str, int] = {}
    founder_scores: list[int] = []
    for file_path in report_files:
        report_payload = load_json_file(file_path, {})
        if not isinstance(report_payload, dict):
            continue
        report_date = str(report_payload.get("date") or file_path.stem)
        report_items = report_payload.get("ideas", []) if isinstance(report_payload.get("ideas"), list) else []
        reports_by_date[report_date] = len(report_items)
        for position, idea in enumerate(report_items):
            if not isinstance(idea, dict):
                continue
            name = str(idea.get("name") or "").strip()
            normalized_name = normalize_idea_name(name)
            if normalized_name:
                exact_names[normalized_name] += 1
            founder_score = int(idea.get("founder_score") or 0)
            founder_scores.append(founder_score)
            for category in idea.get("category_focus", []) if isinstance(idea.get("category_focus"), list) else []:
                categories[str(category)] += 1
            for trend in idea.get("trends", []) if isinstance(idea.get("trends"), list) else []:
                trends[str(trend)] += 1
            item_id = hashlib.sha256(f"{report_date}::{position}::{name}".encode("utf-8")).hexdigest()[:16]
            raw_items.append(
                {
                    "id": item_id,
                    "date": report_date,
                    "report_path": f"data/reports/{file_path.name}",
                    "name": name,
                    "summary": str(idea.get("summary") or "").strip(),
                    "founder_score": founder_score,
                    "revenue_score": int(idea.get("revenue_score") or 0),
                    "opportunity_score": int(idea.get("opportunity_score") or 0),
                    "trend_repo_match_score": int(idea.get("trend_repo_match_score") or 0),
                    "breakthrough_score": int(idea.get("breakthrough_score") or 0),
                    "cross_domain_score": int(idea.get("cross_domain_score") or 0),
                    "serendipity_score": int(idea.get("serendipity_score") or 0),
                    "conventionality_score": int(idea.get("conventionality_score") or 0),
                    "confidence": str(idea.get("confidence") or ""),
                    "category_focus": [str(label) for label in idea.get("category_focus", []) if isinstance(label, str)],
                    "trends": [str(label) for label in idea.get("trends", []) if isinstance(label, str)],
                    "repos": [str(label) for label in idea.get("repos", []) if isinstance(label, str)],
                    "build_decision": idea.get("build_decision") if isinstance(idea.get("build_decision"), dict) else {},
                    "hidden_customer": str(idea.get("hidden_customer") or "").strip(),
                    "novel_mechanism": str(idea.get("novel_mechanism") or "").strip(),
                    "why_non_obvious": str(idea.get("why_non_obvious") or "").strip(),
                    "breakthrough_axes": [str(step) for step in idea.get("breakthrough_axes", []) if isinstance(step, str)],
                    "why_now": str(idea.get("why_now") or "").strip(),
                    "revenue_model": str(idea.get("revenue_model") or "").strip(),
                    "build_plan": [str(step) for step in idea.get("build_plan", []) if isinstance(step, str)],
                    "semantic_signature": str(idea.get("semantic_signature") or "").strip(),
                }
            )
    latest_date = max(reports_by_date) if reports_by_date else ""
    raw_items.sort(key=lambda item: (item["date"], item["founder_score"], item["revenue_score"], item["name"]))
    recurrence_groups: list[dict[str, Any]] = []
    grouped_items: list[dict[str, Any]] = []
    for item in raw_items:
        best_group: dict[str, Any] | None = None
        best_score = 0.0
        for group in recurrence_groups:
            score = max(idea_similarity_score(item, member) for member in group["members"])
            if score > best_score:
                best_score = score
                best_group = group
        if best_group is None or best_score < IDEA_SIMILARITY_THRESHOLD:
            seed_signature = item.get("semantic_signature") or semantic_signature(item)
            group_id = hashlib.sha256(f"{seed_signature}::{item['date']}".encode("utf-8")).hexdigest()[:12]
            best_group = {
                "group_id": group_id,
                "members": [],
                "first_seen": item["date"],
                "last_seen": item["date"],
                "label": item["name"],
            }
            recurrence_groups.append(best_group)
        best_group["members"].append(item)
        best_group["first_seen"] = min(best_group["first_seen"], item["date"])
        best_group["last_seen"] = max(best_group["last_seen"], item["date"])
        grouped_items.append(
            {
                **item,
                "recurrence_group_id": best_group["group_id"],
                "recurrence_group_label": best_group["label"],
                "semantic_similarity": round(best_score, 2),
            }
        )
    group_counts = {group["group_id"]: len(group["members"]) for group in recurrence_groups}
    group_summaries: dict[str, dict[str, Any]] = {}
    recurrence_group_payloads: list[dict[str, Any]] = []
    for group in recurrence_groups:
        members = sorted(
            group["members"],
            key=lambda item: (item["date"], item["opportunity_score"], item["founder_score"], item["name"]),
        )
        latest_item = members[-1]
        momentum = build_lifecycle_momentum(members, latest_date)
        category_counter = Counter(
            label
            for member in members
            for label in member.get("category_focus", [])
            if isinstance(label, str) and label
        )
        trend_counter = Counter(
            label
            for member in members
            for label in member.get("trends", [])
            if isinstance(label, str) and label
        )
        repo_counter = Counter(
            label
            for member in members
            for label in member.get("repos", [])
            if isinstance(label, str) and label
        )
        summary = {
            "group_id": group["group_id"],
            "label": latest_item["name"],
            "semantic_signature": latest_item.get("semantic_signature") or semantic_signature(latest_item),
            "first_seen": group["first_seen"],
            "last_seen": group["last_seen"],
            "appearance_count": len(members),
            "is_recurring": len(members) > 1,
            "category_focus": [name for name, _ in category_counter.most_common(6)],
            "trends": [name for name, _ in trend_counter.most_common(6)],
            "repos": [name for name, _ in repo_counter.most_common(6)],
            "latest_item": {
                "id": latest_item["id"],
                "date": latest_item["date"],
                "report_path": latest_item["report_path"],
                "name": latest_item["name"],
                "summary": latest_item["summary"],
                "founder_score": latest_item["founder_score"],
                "revenue_score": latest_item["revenue_score"],
                "opportunity_score": latest_item["opportunity_score"],
                "trend_repo_match_score": latest_item["trend_repo_match_score"],
                "breakthrough_score": latest_item.get("breakthrough_score", 0),
                "cross_domain_score": latest_item.get("cross_domain_score", 0),
                "serendipity_score": latest_item.get("serendipity_score", 0),
                "conventionality_score": latest_item.get("conventionality_score", 0),
                "confidence": latest_item["confidence"],
                "build_decision": latest_item["build_decision"],
                "hidden_customer": latest_item.get("hidden_customer", ""),
                "novel_mechanism": latest_item.get("novel_mechanism", ""),
                "why_non_obvious": latest_item.get("why_non_obvious", ""),
                "breakthrough_axes": latest_item.get("breakthrough_axes", []),
                "why_now": latest_item["why_now"],
                "revenue_model": latest_item["revenue_model"],
                "build_plan": latest_item["build_plan"],
            },
            "items": [
                {
                    "id": member["id"],
                    "date": member["date"],
                    "report_path": member["report_path"],
                    "name": member["name"],
                    "summary": member["summary"],
                    "founder_score": member["founder_score"],
                    "revenue_score": member["revenue_score"],
                    "opportunity_score": member["opportunity_score"],
                    "breakthrough_score": member.get("breakthrough_score", 0),
                    "conventionality_score": member.get("conventionality_score", 0),
                }
                for member in reversed(members)
            ],
            **momentum,
        }
        group_summaries[group["group_id"]] = summary
        recurrence_group_payloads.append(summary)
    all_ideas: list[dict[str, Any]] = []
    for item in grouped_items:
        normalized_name = normalize_idea_name(item["name"])
        group_id = item["recurrence_group_id"]
        appearance_count = group_counts.get(group_id, 1)
        group_summary = group_summaries[group_id]
        all_ideas.append(
            {
                "id": item["id"],
                "date": item["date"],
                "report_path": item["report_path"],
                "name": item["name"],
                "summary": item["summary"],
                "founder_score": item["founder_score"],
                "revenue_score": item["revenue_score"],
                "opportunity_score": item["opportunity_score"],
                "trend_repo_match_score": item["trend_repo_match_score"],
                "breakthrough_score": item.get("breakthrough_score", 0),
                "cross_domain_score": item.get("cross_domain_score", 0),
                "serendipity_score": item.get("serendipity_score", 0),
                "conventionality_score": item.get("conventionality_score", 0),
                "confidence": item["confidence"],
                "category_focus": item["category_focus"],
                "trends": item["trends"],
                "repos": item["repos"],
                "build_decision": item["build_decision"],
                "hidden_customer": item.get("hidden_customer", ""),
                "novel_mechanism": item.get("novel_mechanism", ""),
                "why_non_obvious": item.get("why_non_obvious", ""),
                "breakthrough_axes": item.get("breakthrough_axes", []),
                "semantic_signature": item["semantic_signature"] or semantic_signature(item),
                "recurrence_group_id": group_id,
                "recurrence_group_label": item["recurrence_group_label"],
                "group_momentum_score": group_summary["momentum_score"],
                "group_momentum_label": group_summary["momentum_label"],
                "is_latest": item["date"] == latest_date,
                "is_recurring": appearance_count > 1,
                "appearance_count": appearance_count,
                "exact_appearance_count": exact_names[normalized_name] if normalized_name else 1,
                "first_seen": group_summary["first_seen"],
                "last_seen": group_summary["last_seen"],
            }
        )
    all_ideas.sort(key=lambda item: (item["date"], item["founder_score"], item["revenue_score"]), reverse=True)
    recurrence_group_payloads.sort(
        key=lambda item: (item["momentum_score"], item["last_seen"], item["latest_item"]["founder_score"]),
        reverse=True,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "latest_date": latest_date,
        "all_ideas": all_ideas,
        "recurrence_groups": recurrence_group_payloads,
        "unique_categories": sorted([category for category in categories if category]),
        "unique_trends": sorted([trend for trend in trends if trend]),
        "stats": {
            "total_ideas": len(all_ideas),
            "total_dates": len(reports_by_date),
            "total_groups": len(recurrence_group_payloads),
            "avg_founder_score": round(sum(founder_scores) / len(founder_scores), 1) if founder_scores else 0,
            "avg_breakthrough_score": round(sum(int(item.get("breakthrough_score") or 0) for item in all_ideas) / len(all_ideas), 1) if all_ideas else 0,
            "avg_conventionality_score": round(sum(int(item.get("conventionality_score") or 0) for item in all_ideas) / len(all_ideas), 1) if all_ideas else 0,
            "top_categories": [{"name": name, "count": count} for name, count in categories.most_common(6)],
            "top_trends": [{"name": name, "count": count} for name, count in trends.most_common(6)],
            "ideas_by_date": reports_by_date,
            "recurring_ideas": sum(1 for count in group_counts.values() if count > 1),
            "exact_recurring_ideas": sum(1 for count in exact_names.values() if count > 1),
            "top_momentum_group": recurrence_group_payloads[0]["label"] if recurrence_group_payloads else "",
        },
    }


def write_site_data(site_dir: Path, payload: dict[str, Any], markdown_report: str) -> tuple[Path, Path, Path]:
    data_dir = site_dir / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    site_reports_dir = site_dir / "reports"
    site_reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{payload['date']}.json"
    save_json_file(report_path, payload)
    markdown_path = site_reports_dir / f"{payload['date']}.md"
    markdown_path.write_text(markdown_report, encoding="utf-8")

    report_files = sorted(reports_dir.glob("*.json"), reverse=True)
    reports_index = []
    for file_path in report_files:
        report_payload = load_json_file(file_path, {})
        if not isinstance(report_payload, dict):
            continue
        reports_index.append(
            {
                "date": report_payload.get("date", file_path.stem),
                "generated_at": report_payload.get("generated_at", ""),
                "mode": report_payload.get("mode", ""),
                "idea_count": len(report_payload.get("ideas", [])) if isinstance(report_payload.get("ideas"), list) else 0,
                "trend_count": len(report_payload.get("trends", [])) if isinstance(report_payload.get("trends"), list) else 0,
                "path": f"data/reports/{file_path.name}",
                "top_idea": (
                    report_payload.get("ideas", [{}])[0].get("name", "")
                    if isinstance(report_payload.get("ideas"), list) and report_payload.get("ideas")
                    else ""
                ),
                "top_revenue_score": (
                    report_payload.get("ideas", [{}])[0].get("revenue_score", 0)
                    if isinstance(report_payload.get("ideas"), list) and report_payload.get("ideas")
                    else 0
                ),
                "top_founder_score": (
                    report_payload.get("ideas", [{}])[0].get("founder_score", 0)
                    if isinstance(report_payload.get("ideas"), list) and report_payload.get("ideas")
                    else 0
                ),
            }
        )
    index_payload = {
        "generated_at": payload["generated_at"],
        "latest": payload["date"],
        "reports": reports_index,
    }
    index_path = data_dir / "index.json"
    save_json_file(index_path, index_payload)
    collection_path = data_dir / "collection.json"
    save_json_file(collection_path, build_collection_payload(report_files))
    latest_path = data_dir / "latest.json"
    save_json_file(latest_path, payload)
    return report_path, index_path, collection_path


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    config_path = resolve_path(root, args.config)
    cache_path = resolve_path(root, args.cache)
    output_dir = resolve_path(root, args.output_dir)
    site_dir = resolve_path(root, args.site_dir)
    report_date = args.date or utc_today()
    reports_dir = site_dir / "data" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    repos = load_starred_repos(cache_path)
    repo_shortlist = build_repo_shortlist(repos)
    repo_lookup = {repo["full_name"]: repo for repo in repo_shortlist}
    trends_payload = fetch_newsnow_payload()
    trends, source_statuses = dedupe_trends(trends_payload)
    generation_context = build_generation_context(report_date, trends, repo_shortlist, reports_dir)
    generation_mode = "live-with-llm"

    try:
        env = read_minimax_env(config_path)
    except Exception:
        env = {}
        generation_mode = "live-with-deterministic-ideas"

    try:
        if not env:
            raise ValueError("Missing LLM configuration.")
        idea_candidates = generate_ideas_with_llm(report_date, trends, repo_shortlist, env, generation_context)
    except Exception:
        idea_candidates = build_dynamic_fallback_ideas(report_date, trends, repo_shortlist, generation_context)
        generation_mode = "live-with-deterministic-ideas"

    trend_titles = {trend["title"] for trend in trends}
    ideas = select_fresh_ideas(
        idea_candidates,
        repo_lookup,
        repo_shortlist,
        trend_titles,
        trends,
        generation_context.get("recent_ideas", []),
        limit=MAX_IDEA_COUNT,
    )
    if not ideas:
        ideas = select_fresh_ideas(
            build_dynamic_fallback_ideas(report_date, trends, repo_shortlist, generation_context),
            repo_lookup,
            repo_shortlist,
            trend_titles,
            trends,
            generation_context.get("recent_ideas", []),
            limit=MAX_IDEA_COUNT,
        )
        generation_mode = "live-with-deterministic-ideas"
    if len(ideas) < MAX_IDEA_COUNT:
        top_up_ideas = select_fresh_ideas(
            build_dynamic_fallback_ideas(report_date, trends, repo_shortlist, generation_context),
            repo_lookup,
            repo_shortlist,
            trend_titles,
            trends,
            generation_context.get("recent_ideas", []) + ideas,
            limit=MAX_IDEA_COUNT - len(ideas),
        )
        if top_up_ideas:
            ideas.extend(top_up_ideas)
            if generation_mode == "live-with-llm":
                generation_mode = "live-with-llm-plus-deterministic-top-up"
    ideas = enrich_ideas(ideas, repo_lookup, trends)
    quality_failures = breakthrough_quality_checks(ideas)
    quality_summary = portfolio_quality_summary(ideas)

    generated_at = utc_now()
    report = render_report(report_date, generated_at, source_statuses, trends, ideas, repo_lookup, generation_mode)
    output_path = output_dir / f"{report_date}.md"
    output_path.write_text(report, encoding="utf-8")
    site_payload = build_site_payload(report_date, generated_at, source_statuses, trends, ideas, generation_mode)
    site_report_path, site_index_path, site_collection_path = write_site_data(site_dir, site_payload, report)

    print(f"Generated {output_path}")
    print(f"Generated {site_report_path}")
    print(f"Updated {site_index_path}")
    print(f"Updated {site_collection_path}")
    print(f"Trends analyzed: {len(trends)}")
    print(f"Starred repos considered: {len(repo_shortlist)}")
    print(f"Ideas generated: {len(ideas)}")
    print(
        "Breakthrough quality: "
        f"avg {quality_summary['avg_breakthrough_score']} | "
        f"conventionality {quality_summary['avg_conventionality_score']} | "
        f"breakthrough ideas {quality_summary['breakthrough_ideas']}/{len(ideas)}"
    )
    if args.quality_gate and quality_failures:
        for failure in quality_failures:
            print(f"QUALITY GATE FAILED: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
