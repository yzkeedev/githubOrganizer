# LLM Prompt Optimization

## Before vs After

| Metric | Before | After | Savings |
|--------|-------|-------|---------|
| Prompt chars | ~15,000 | ~1,350 | **91%** |
| System prompt | ~1,500 | ~300 | **80%** |
| Idea schema | 12 fields | 7 fields | **42%** |

## Optimized System Prompt (~300 chars)

```
Generate 10 breakthrough startup ideas from today's trends and repos.

Output JSON:
{"ideas":[{"Name":"X","summary":"1 sentence","mechanism":"what makes it hard to copy","why_non_obvious":"the invisible connection","hidden_customer":"specific buyer","axes":["label"],"trends":["trend"],"repos":["owner/repo"]}]}

Rules:
- Use 2+ repos and 1+ trend per idea
- 5+ ideas must anchor to headline trends
- Think transfer, not templates: coordination layer > dashboard, broker > tool
- AVOID: "X Assistant", "Help X use Y", "platform for X", generic customers
- Breakthrough = reader thinks "why didn't I see that?"
- Keep language concrete, no hype.
```

## Optimized User Prompt (~1,050 chars)

```
Date: 2026-04-03
Lens: Capability transplant — Steal a proven mechanism from one domain and transplant it into a completely different market with stronger urgency.

Trends (anchor at least 5 ideas): Agentplace AI Agents, Naoma AI Demo Agent, Claude Code Review, Claude Code 源码泄漏...

Surprise trends (use 2+): Chronicle 2.0, asgeirtj/system_prompts_leaks, Tobira.ai, Qwen3.6-Plus

Breakthrough lenses:
- Constraint inversion: constraint inversion, hidden stakeholder, trust wedge
- Capability transplant: capability transplant, cross-domain synthesis, behavior redesign
- Second-order market: second-order demand, market design, timing edge
- Synthetic twin: simulation loop, decision rehearsal, cross-domain transfer

Repos to combine:
- openclaw/openclaw | AI Agents & Automation
- affaan-m/everything-claude-code | AI Coding Tools
- rustdesk/rustdesk | Mobile & Desktop
- hacksider/Deep-Live-Cam | AI Content & Media
- ruvnet/RuView | AI Content & Media
- remotion-dev/remotion | AI Content & Media
- moeru-ai/airi | AI Content & Media
- aquasecurity/trivy | Infrastructure & DevOps
- Lissy93/web-check | Security & Privacy
- ChromeDevTools/chrome-devtools-mcp | Web Scraping & Browser Automation
```

## Key Optimizations

1. **Removed JSON formatting** - plain text list format
2. **Removed verbose context** - only trend titles, no context/url/info
3. **Removed redundant sections** - no "current trends", "recent ideas", "cross-domain seeds"
4. **Limited repos** - only top 10 most relevant
5. **Simplified schema** - 7 fields instead of 12
6. **Concise rules** - bullet points instead of paragraphs

## Remaining Issue: Rate Limiting

The MiniMax API is rate-limiting our calls. The GitHub Actions workflow at UTC midnight should work when the API is less congested.
