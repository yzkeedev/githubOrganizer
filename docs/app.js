const reportSelect = document.getElementById("report-select");
const categoryFilter = document.getElementById("category-filter");
const sortSelect = document.getElementById("sort-select");
const modePill = document.getElementById("mode-pill");
const datePill = document.getElementById("date-pill");
const markdownLink = document.getElementById("markdown-link");
const stats = document.getElementById("stats");
const ideasList = document.getElementById("ideas-list");
const rankingList = document.getElementById("ranking-list");
const trendsList = document.getElementById("trends-list");
const sourceHealth = document.getElementById("source-health");
const historyList = document.getElementById("history-list");
const ideaCount = document.getElementById("idea-count");
const trendCount = document.getElementById("trend-count");
const sourceCount = document.getElementById("source-count");
const rankingLabel = document.getElementById("ranking-label");
const historyCount = document.getElementById("history-count");
const comparisonLabel = document.getElementById("comparison-label");
const comparisonGrid = document.getElementById("comparison-grid");
const emptyCardTemplate = document.getElementById("empty-card-template");

const state = {
  index: null,
  reports: new Map(),
  currentPath: "",
  currentReport: null,
  previousReport: null,
};

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statCard(label, value) {
  const card = document.createElement("div");
  card.className = "stat";
  card.innerHTML = `<div class="stat-label">${escapeHtml(label)}</div><div class="stat-value">${escapeHtml(value)}</div>`;
  return card;
}

function tag(label) {
  return `<span class="tag">${escapeHtml(label)}</span>`;
}

function scoreBadge(label, value) {
  return `
    <div class="score">
      <span class="score-label">${escapeHtml(label)}</span>
      <span class="score-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function renderMemoItems(items) {
  return (items || []).map((item) => `<span class="memo-chip">${escapeHtml(item)}</span>`).join("");
}

function decisionBadge(decision) {
  const label = decision?.label || "Validate first";
  const tone = decision?.tone || "caution";
  const summary = decision?.summary || "";
  return `
    <div class="decision decision-${escapeHtml(tone)}">
      <span class="decision-label">${escapeHtml(label)}</span>
      <span class="decision-copy">${escapeHtml(summary)}</span>
    </div>
  `;
}

function emptyCard(title, copy) {
  const node = emptyCardTemplate.content.firstElementChild.cloneNode(true);
  node.querySelector("h3").textContent = title;
  node.querySelector("p").textContent = copy;
  return node;
}

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function average(values) {
  if (!values.length) {
    return 0;
  }
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function getSelectedCategory() {
  return categoryFilter.value || "All categories";
}

function getSelectedSort() {
  return sortSelect.value || "founder";
}

function getCurrentIdeas() {
  if (!state.currentReport) {
    return [];
  }
  const selectedCategory = getSelectedCategory();
  const filtered = state.currentReport.ideas.filter((idea) => {
    if (selectedCategory === "All categories") {
      return true;
    }
    const categories = new Set([
      ...(idea.category_focus || []),
      ...(idea.repo_details || []).map((repo) => repo.category),
    ]);
    return categories.has(selectedCategory);
  });
  const sorters = {
    founder: (idea) => [idea.founder_score, idea.opportunity_score, idea.revenue_score],
    opportunity: (idea) => [idea.opportunity_score, idea.revenue_score, idea.trend_repo_match_score],
    revenue: (idea) => [idea.revenue_score, idea.opportunity_score, idea.trend_repo_match_score],
    match: (idea) => [idea.trend_repo_match_score, idea.opportunity_score, idea.revenue_score],
  };
  return [...filtered].sort((left, right) => {
    const leftMetrics = sorters[getSelectedSort()](left);
    const rightMetrics = sorters[getSelectedSort()](right);
    for (let index = 0; index < leftMetrics.length; index += 1) {
      if (leftMetrics[index] !== rightMetrics[index]) {
        return rightMetrics[index] - leftMetrics[index];
      }
    }
    return left.name.localeCompare(right.name);
  });
}

function renderStats(report, ideas) {
  stats.innerHTML = "";
  stats.append(
    statCard("Showing", `${ideas.length}/${report.ideas.length}`),
    statCard("Avg founder", average(ideas.map((idea) => idea.founder_score))),
    statCard("Avg revenue", average(ideas.map((idea) => idea.revenue_score))),
    statCard("Avg build speed", average(ideas.map((idea) => idea.build_speed_score))),
    statCard("Generated", formatDate(report.generated_at)),
  );
}

function renderIdeas(ideas) {
  ideasList.innerHTML = "";
  ideaCount.textContent = `${ideas.length} visible`;
  if (!ideas.length) {
    ideasList.appendChild(emptyCard("No ideas in this slice", "Try a broader category or a different sort order."));
    return;
  }
  for (const idea of ideas) {
    const card = document.createElement("article");
    card.className = "idea-card";
    const repoLinks = (idea.repo_details || [])
      .map(
        (repo) =>
          `<a href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(repo.full_name)}</a>`
      )
      .join(" · ");
    const launchPath = (idea.build_plan || []).map(escapeHtml).join(" → ");
    const signalTags = (idea.trends || []).map(tag).join("");
    const categoryTags = (idea.category_focus || []).map(tag).join("");
    const confidence = tag(`Confidence: ${idea.confidence}`);
    const memo = idea.founder_memo || {};
    const decision = idea.build_decision || {};
    card.innerHTML = `
      ${decisionBadge(decision)}
      <div class="idea-topline">
        <div>
          <h3>${escapeHtml(idea.name)}</h3>
          <p class="copy">${escapeHtml(idea.summary || "")}</p>
        </div>
        <div class="score-group">
          ${scoreBadge("Founder", idea.founder_score)}
          ${scoreBadge("Radar", idea.opportunity_score)}
          ${scoreBadge("Revenue", idea.revenue_score)}
          ${scoreBadge("Fit", idea.trend_repo_match_score)}
        </div>
      </div>
      <div class="meta-line">${signalTags}</div>
      <div class="meta-line">${categoryTags}${confidence}</div>
      <section class="memo-panel">
        <div class="memo-header">
          <span class="label">Founder memo</span>
          <span class="micro">Why it scores this way</span>
        </div>
        <div class="memo-grid">
          <div class="mini-block">
            <span class="label">Best part</span>
            <p class="copy">${escapeHtml(memo.best_part || "")}</p>
          </div>
          <div class="mini-block">
            <span class="label">Biggest risk</span>
            <p class="copy">${escapeHtml(memo.biggest_risk || "")}</p>
          </div>
          <div class="mini-block">
            <span class="label">Fastest MVP</span>
            <p class="copy">${escapeHtml(memo.fastest_mvp || "")}</p>
          </div>
          <div class="mini-block">
            <span class="label">First customer</span>
            <p class="copy">${escapeHtml(memo.first_customer || "")}</p>
          </div>
        </div>
        <div class="mini-grid memo-detail-grid">
          <div class="mini-block">
            <span class="label">Why high</span>
            <p class="copy">${escapeHtml(memo.why_high || "")}</p>
          </div>
          <div class="mini-block">
            <span class="label">Why low</span>
            <p class="copy">${escapeHtml(memo.why_low || "")}</p>
          </div>
        </div>
        <div class="mini-block">
          <span class="label">Top penalties</span>
          <div class="memo-chip-row">${renderMemoItems(memo.top_penalties)}</div>
        </div>
        <div class="mini-block">
          <span class="label">Improve next</span>
          <div class="memo-chip-row">${renderMemoItems(memo.improve_next)}</div>
        </div>
      </section>
      <div class="mini-grid">
        <div class="mini-block">
          <span class="label">Why now</span>
          <p class="copy">${escapeHtml(idea.why_now || "")}</p>
        </div>
        <div class="mini-block">
          <span class="label">Revenue path</span>
          <p class="copy">${escapeHtml(idea.revenue_model || "")}</p>
        </div>
        <div class="mini-block">
          <span class="label">Launch path</span>
          <p class="copy">${launchPath}</p>
        </div>
        <div class="mini-block">
          <span class="label">Founder lens</span>
          <p class="copy">Difficulty ${escapeHtml(idea.niche_difficulty_score)} · Build ${escapeHtml(idea.build_speed_score)} · Monetization ${escapeHtml(idea.monetization_latency_score)} · Recurring ${escapeHtml(idea.recurring_revenue_score)}</p>
        </div>
        <div class="mini-block">
          <span class="label">Repo stack</span>
          <p class="copy repo-list">${repoLinks}</p>
        </div>
      </div>
    `;
    ideasList.appendChild(card);
  }
}

function renderRanking(ideas) {
  rankingList.innerHTML = "";
  rankingLabel.textContent = `${Math.min(3, ideas.length)} shown`;
  if (!ideas.length) {
    rankingList.appendChild(emptyCard("No ranking yet", "Ranking appears once this view has at least one visible idea."));
    return;
  }
  const ranking = [...ideas]
    .sort((left, right) => right.founder_score - left.founder_score || right.revenue_score - left.revenue_score)
    .slice(0, 3);
  for (const idea of ranking) {
    const item = document.createElement("article");
    item.className = "ranking-item";
    item.innerHTML = `
      <div class="ranking-row">
        <strong>${escapeHtml(idea.name)}</strong>
        ${tag(`Founder ${idea.founder_score}`)}
      </div>
      ${decisionBadge(idea.build_decision)}
      <p class="copy">${escapeHtml(idea.summary || "")}</p>
      <p class="copy">${escapeHtml(idea.founder_memo?.best_part || "")}</p>
      <div class="meta-line">
        ${tag(`Build ${idea.build_speed_score}`)}
        ${tag(`Recurring ${idea.recurring_revenue_score}`)}
        ${tag(`Fit ${idea.trend_repo_match_score}`)}
        ${tag(`Revenue ${idea.revenue_score}`)}
      </div>
    `;
    rankingList.appendChild(item);
  }
}

function renderTrends(report, ideas) {
  trendsList.innerHTML = "";
  const trendTitles = new Set(ideas.flatMap((idea) => idea.trends || []));
  const selectedCategory = getSelectedCategory();
  const visibleTrends =
    selectedCategory === "All categories"
      ? report.trends
      : report.trends.filter((trend) => trendTitles.has(trend.title));
  trendCount.textContent = `${visibleTrends.length} visible`;
  if (!visibleTrends.length) {
    trendsList.appendChild(emptyCard("No related trends", "This category currently has no directly linked trend snapshot."));
    return;
  }
  for (const trend of visibleTrends) {
    const card = document.createElement("article");
    card.className = "trend-card";
    card.innerHTML = `
      <h3><a href="${escapeHtml(trend.url)}" target="_blank" rel="noreferrer">${escapeHtml(trend.title)}</a></h3>
      <p class="copy">${escapeHtml(trend.context || trend.info || "No extra context.")}</p>
      <div class="meta-line">
        ${tag(trend.source_name)}
        ${tag(`#${trend.source_rank}`)}
      </div>
    `;
    trendsList.appendChild(card);
  }
}

function renderSources(report) {
  sourceHealth.innerHTML = "";
  sourceCount.textContent = `${report.source_health.length} feeds`;
  for (const source of report.source_health) {
    const item = document.createElement("div");
    item.className = "source-item";
    item.innerHTML = `<strong>${escapeHtml(source.name)}</strong><span>${escapeHtml(source.status)} · ${escapeHtml(source.item_count)} items</span>`;
    sourceHealth.appendChild(item);
  }
}

function renderHistory() {
  historyList.innerHTML = "";
  const reports = state.index?.reports || [];
  historyCount.textContent = `${reports.length} days tracked`;
  for (const report of reports) {
    const item = document.createElement("article");
    item.className = "history-item";
    const activeTag = report.path === state.currentPath ? tag("Open") : "";
    item.innerHTML = `
      <div class="history-row">
        <div>
          <strong>${escapeHtml(report.date)}</strong>
          <p class="copy">${escapeHtml(report.top_idea || "Opportunity Radar")}</p>
        </div>
        <div class="meta-line">
          ${tag(`${report.idea_count} ideas`)}
          ${tag(`Founder ${report.top_founder_score || 0}`)}
          ${activeTag}
        </div>
      </div>
    `;
    historyList.appendChild(item);
  }
}

function comparisonCard(label, value, note) {
  const card = document.createElement("article");
  card.className = "comparison-card";
  card.innerHTML = `
    <div class="micro">${escapeHtml(label)}</div>
    <div class="comparison-value">${escapeHtml(value)}</div>
    <div class="comparison-note">${escapeHtml(note)}</div>
  `;
  return card;
}

function renderComparison(currentReport, previousReport) {
  comparisonGrid.innerHTML = "";
  if (!previousReport) {
    comparisonLabel.textContent = "Available after the next daily run";
    comparisonGrid.append(
      comparisonCard("New ideas", "—", "Need one earlier report to measure movement."),
      comparisonCard("Dropped ideas", "—", "Older ideas will appear here once history exists."),
      comparisonCard("New trends", "—", "Trend turnover is calculated day over day."),
      comparisonCard("Revenue leader", "—", "Leader shift appears after at least two days."),
    );
    return;
  }

  comparisonLabel.textContent = `${previousReport.date} → ${currentReport.date}`;
  const currentIdeas = new Set(currentReport.ideas.map((idea) => idea.name));
  const previousIdeas = new Set(previousReport.ideas.map((idea) => idea.name));
  const currentTrends = new Set(currentReport.trends.map((trend) => trend.title));
  const previousTrends = new Set(previousReport.trends.map((trend) => trend.title));
  const newIdeas = [...currentIdeas].filter((name) => !previousIdeas.has(name));
  const droppedIdeas = [...previousIdeas].filter((name) => !currentIdeas.has(name));
  const newTrends = [...currentTrends].filter((title) => !previousTrends.has(title));
  const currentLeader = [...currentReport.ideas].sort((a, b) => b.founder_score - a.founder_score)[0];
  const previousLeader = [...previousReport.ideas].sort((a, b) => b.founder_score - a.founder_score)[0];
  comparisonGrid.append(
    comparisonCard("New ideas", newIdeas.length, newIdeas[0] || "No new ideas in the current run."),
    comparisonCard("Dropped ideas", droppedIdeas.length, droppedIdeas[0] || "No idea fell out of the set."),
    comparisonCard("New trends", newTrends.length, newTrends[0] || "Trend set stayed stable."),
    comparisonCard(
      "Founder leader",
      currentLeader ? currentLeader.founder_score : "—",
      currentLeader && previousLeader && currentLeader.name !== previousLeader.name
        ? `${currentLeader.name} replaced ${previousLeader.name}`
        : currentLeader
          ? `${currentLeader.name} kept the top spot`
          : "No ideas available."
    )
  );
}

function populateCategoryFilter(report) {
  const categories = ["All categories", ...(report.available_categories || [])];
  const previousValue = categoryFilter.value || "All categories";
  categoryFilter.innerHTML = categories
    .map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`)
    .join("");
  categoryFilter.value = categories.includes(previousValue) ? previousValue : "All categories";
}

function renderCurrentView() {
  if (!state.currentReport) {
    return;
  }
  const report = state.currentReport;
  modePill.textContent = report.mode;
  datePill.textContent = report.date;
  markdownLink.href = `./reports/${report.date}.md`;
  const ideas = getCurrentIdeas();
  renderStats(report, ideas);
  renderIdeas(ideas);
  renderRanking(ideas);
  renderTrends(report, ideas);
  renderSources(report);
  renderHistory();
  renderComparison(report, state.previousReport);
}

async function getReport(path) {
  if (!state.reports.has(path)) {
    state.reports.set(path, fetchJson(`./${path}`));
  }
  return state.reports.get(path);
}

async function loadReport(path) {
  state.currentPath = path;
  state.currentReport = await getReport(path);
  const reports = state.index?.reports || [];
  const currentIndex = reports.findIndex((report) => report.path === path);
  const previousPath = currentIndex >= 0 ? reports[currentIndex + 1]?.path : "";
  state.previousReport = previousPath ? await getReport(previousPath) : null;
  populateCategoryFilter(state.currentReport);
  renderCurrentView();
}

async function init() {
  try {
    state.index = await fetchJson("./data/index.json");
    const reports = state.index.reports || [];
    reportSelect.innerHTML = reports
      .map(
        (report) =>
          `<option value="${escapeHtml(report.path)}" ${report.date === state.index.latest ? "selected" : ""}>${escapeHtml(report.date)} · ${escapeHtml(report.top_idea || "Opportunity Radar")}</option>`
      )
      .join("");
    reportSelect.addEventListener("change", (event) => loadReport(event.target.value));
    categoryFilter.addEventListener("change", renderCurrentView);
    sortSelect.addEventListener("change", renderCurrentView);
    const initialPath = reports.find((report) => report.date === state.index.latest)?.path || reports[0]?.path;
    if (initialPath) {
      await loadReport(initialPath);
    }
  } catch (error) {
    modePill.textContent = "unavailable";
    ideasList.innerHTML = "";
    ideasList.appendChild(emptyCard("Data unavailable", error.message));
  }
}

init();
