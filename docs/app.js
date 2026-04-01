const reportSelect = document.getElementById("report-select");
const categoryFilter = document.getElementById("category-filter");
const sortSelect = document.getElementById("sort-select");
const modePill = document.getElementById("mode-pill");
const datePill = document.getElementById("date-pill");
const markdownLink = document.getElementById("markdown-link");
const stats = document.getElementById("stats");
const executiveSummary = document.getElementById("executive-summary");
const executiveCount = document.getElementById("executive-count");
const ideasList = document.getElementById("ideas-list");
const rankingList = document.getElementById("ranking-list");
const trendsList = document.getElementById("trends-list");
const sourceHealth = document.getElementById("source-health");
const historyList = document.getElementById("history-list");
const ideaCount = document.getElementById("idea-count");
const trendCount = document.getElementById("trend-count");
const sourceCount = document.getElementById("source-count");
const rankingLabel = document.getElementById("ranking-label");
const railLabel = document.getElementById("rail-label");
const railTabs = document.getElementById("rail-tabs");
const historyCount = document.getElementById("history-count");
const collectionSearch = document.getElementById("collection-search");
const collectionDateFilter = document.getElementById("collection-date-filter");
const collectionSort = document.getElementById("collection-sort");
const collectionCount = document.getElementById("collection-count");
const collectionStats = document.getElementById("collection-stats");
const collectionNav = document.getElementById("collection-nav");
const collectionDetail = document.getElementById("collection-detail");
const collectionSelectionLabel = document.getElementById("collection-selection-label");
const workspaceTabs = document.getElementById("workspace-tabs");
const workspaceLabel = document.getElementById("workspace-label");
const emptyCardTemplate = document.getElementById("empty-card-template");
const COLLECTIONS_PER_PAGE = 8;

const state = {
  index: null,
  collection: null,
  reports: new Map(),
  currentPath: "",
  currentReport: null,
  currentCollectionGroupId: "",
  currentCollectionPage: 1,
  currentCollectionDetailTab: "overview",
  currentWorkspaceTab: "executive",
  currentRailTab: "ranking",
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

function toTenPointScore(value) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  if (numeric > 10) {
    return Math.max(1, Math.min(10, Math.round(numeric / 10)));
  }
  return Math.max(0, Math.min(10, Math.round(numeric)));
}

function scoreValue(item, key) {
  const tenPointValue = item?.[`${key}_10`];
  if (tenPointValue !== undefined && tenPointValue !== null && tenPointValue !== "") {
    return toTenPointScore(tenPointValue);
  }
  return toTenPointScore(item?.[key]);
}

function scoreText(item, key) {
  return `${scoreValue(item, key)}/10`;
}

function numericScoreText(value) {
  return `${toTenPointScore(value)}/10`;
}

function scoreDeltaText(value) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return "0.0";
  }
  const normalized = Math.round(numeric) / 10;
  return `${normalized > 0 ? "+" : ""}${normalized.toFixed(1)}`;
}

function scoreBadge(label, value) {
  return `
    <div class="score">
      <span class="score-label">${escapeHtml(label)}</span>
      <span class="score-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function headerBadge(label) {
  return `<span class="section-badge">${escapeHtml(label)}</span>`;
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

function setActiveTab(container, selector, activeValue, attribute = "data-tab") {
  if (!container) {
    return;
  }
  for (const node of container.querySelectorAll(selector)) {
    const isActive = node.getAttribute(attribute) === activeValue;
    node.classList.toggle("is-active", isActive);
  }
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

function topItems(values, limit = 3) {
  return values.filter(Boolean).slice(0, limit);
}

function getSelectedCategory() {
  return categoryFilter.value || "All categories";
}

function getSelectedSort() {
  return sortSelect.value || "founder";
}

function getCollectionDate() {
  return collectionDateFilter.value || "All dates";
}

function getCollectionSort() {
  return collectionSort.value || "latest";
}

function getCollectionQuery() {
  return (collectionSearch.value || "").trim().toLowerCase();
}

function getCollectionPageCount(totalItems) {
  return Math.max(1, Math.ceil(totalItems / COLLECTIONS_PER_PAGE));
}

function clampCollectionPage(totalItems) {
  const pageCount = getCollectionPageCount(totalItems);
  state.currentCollectionPage = Math.max(1, Math.min(state.currentCollectionPage, pageCount));
  return pageCount;
}

function setWorkspaceTab(tabId) {
  state.currentWorkspaceTab = tabId === "radar" ? "today" : tabId;
  applyWorkspaceTabState();
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
    statCard("Avg founder", numericScoreText(average(ideas.map((idea) => idea.founder_score)))),
    statCard("Avg revenue", numericScoreText(average(ideas.map((idea) => idea.revenue_score)))),
    statCard("Avg build speed", numericScoreText(average(ideas.map((idea) => idea.build_speed_score)))),
    statCard("Generated", formatDate(report.generated_at)),
  );
}

function getVisibleTrends(report, ideas) {
  const trendTitles = new Set(ideas.flatMap((idea) => idea.trends || []));
  const selectedCategory = getSelectedCategory();
  return selectedCategory === "All categories"
    ? report.trends
    : report.trends.filter((trend) => trendTitles.has(trend.title));
}

function getTopIdea(ideas, primaryMetric, secondaryMetric = "revenue_score") {
  return [...ideas].sort((left, right) => right[primaryMetric] - left[primaryMetric] || right[secondaryMetric] - left[secondaryMetric])[0] || null;
}

function getExecutiveBullets(report, ideas) {
  const visibleTrends = getVisibleTrends(report, ideas);
  const topFounderIdea = getTopIdea(ideas, "founder_score");
  const topRevenueIdea = getTopIdea(ideas, "revenue_score", "founder_score");
  const topFitIdea = getTopIdea(ideas, "trend_repo_match_score", "opportunity_score");
  const topCollection = getCollectionGroups()[0] || null;
  const categoryCounts = new Map();
  for (const idea of ideas) {
    for (const category of idea.category_focus || []) {
      categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
    }
  }
  const leadingCategory =
    [...categoryCounts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))[0]?.[0] || "Mixed";
  return [
    {
      title: "Pulse",
      text: `${ideas.length} ideas are visible today across ${visibleTrends.length} active trends, with ${leadingCategory} showing the strongest build density.`,
    },
    {
      title: "Headlines",
      text: topItems(visibleTrends.map((trend) => `${trend.title} (${trend.source_name})`)).join(" · ") || "No major linked headlines surfaced in this slice.",
    },
    {
      title: "Best bet",
      text: topFounderIdea
        ? `${topFounderIdea.name} leads on founder fit at ${scoreText(topFounderIdea, "founder_score")} with ${topFounderIdea.summary || "a clear build wedge."}`
        : "No clear founder bet is available in this slice.",
    },
    {
      title: "Fast money",
      text: topRevenueIdea
        ? `${topRevenueIdea.name} leads revenue at ${scoreText(topRevenueIdea, "revenue_score")} with ${topRevenueIdea.revenue_model || "a monetization path still forming."}`
        : "No clear monetization leader is available in this slice.",
    },
    {
      title: "Signal fit",
      text: topFitIdea
        ? `${topFitIdea.name} has the strongest trend fit at ${scoreText(topFitIdea, "trend_repo_match_score")} and ties the current repo stack most tightly to today's pulse.`
        : "No strong trend-to-repo fit surfaced in this slice.",
    },
    {
      title: "Archive watch",
      text: topCollection
        ? `${topCollection.label} is the archive leader with ${topCollection.appearance_count || 1} appearances and ${topCollection.momentum_label || "steady"} momentum.`
        : "No collection signal is available yet.",
    },
  ];
}

function renderExecutiveSummary(report, ideas) {
  executiveSummary.innerHTML = "";
  const bullets = getExecutiveBullets(report, ideas);
  executiveCount.textContent = `${bullets.length} bullets`;
  const leadingIdea = getTopIdea(ideas, "founder_score");
  const visibleTrends = getVisibleTrends(report, ideas);
  const hero = document.createElement("article");
  hero.className = "executive-hero";
  hero.innerHTML = `
    <div class="executive-hero-copy">
      ${headerBadge("Busy-person read")}
      <h3>${escapeHtml(leadingIdea?.name || "Daily pulse")}</h3>
      <p class="copy">${escapeHtml(leadingIdea?.summary || "A compact read of today's most actionable signals and build wedges.")}</p>
    </div>
    <div class="score-group">
      ${scoreBadge("Ideas", ideas.length)}
      ${scoreBadge("Trends", visibleTrends.length)}
      ${scoreBadge("Mode", report.mode || "live")}
    </div>
  `;
  executiveSummary.appendChild(hero);
  const list = document.createElement("article");
  list.className = "executive-list";
  list.innerHTML = bullets
    .map(
      (bullet) => `
        <section class="executive-item">
          <span class="label">${escapeHtml(bullet.title)}</span>
          <p class="copy">• ${escapeHtml(bullet.text)}</p>
        </section>
      `
    )
    .join("");
  executiveSummary.appendChild(list);
}

function getCollectionGroups() {
  if (!state.collection?.recurrence_groups) {
    return [];
  }
  const selectedDate = getCollectionDate();
  const query = getCollectionQuery();
  const currentCategory = getSelectedCategory();
  const filtered = state.collection.recurrence_groups.filter((group) => {
    const latestItem = group.latest_item || {};
    if (selectedDate !== "All dates" && latestItem.date !== selectedDate) {
      return false;
    }
    if (currentCategory !== "All categories" && !(group.category_focus || []).includes(currentCategory)) {
      return false;
    }
    if (!query) {
      return true;
    }
    const searchText = [
      group.label,
      latestItem.name,
      latestItem.summary,
      latestItem.why_now,
      ...(group.category_focus || []),
      ...(group.trends || []),
      ...(group.repos || []),
    ]
      .join(" ")
      .toLowerCase();
    return searchText.includes(query);
  });
  const sortMode = getCollectionSort();
  return [...filtered].sort((left, right) => {
    if (sortMode === "momentum") {
      return right.momentum_score - left.momentum_score || right.last_seen.localeCompare(left.last_seen);
    }
    if (sortMode === "name") {
      return left.label.localeCompare(right.label) || right.last_seen.localeCompare(left.last_seen);
    }
    if (sortMode === "founder") {
      return right.latest_item.founder_score - left.latest_item.founder_score || right.last_seen.localeCompare(left.last_seen);
    }
    if (sortMode === "revenue") {
      return right.latest_item.revenue_score - left.latest_item.revenue_score || right.last_seen.localeCompare(left.last_seen);
    }
    return right.last_seen.localeCompare(left.last_seen) || right.momentum_score - left.momentum_score;
  });
}

function renderCollectionStats() {
  collectionStats.innerHTML = "";
  if (!state.collection?.stats) {
    return;
  }
  const topCategory = state.collection.stats.top_categories?.[0]?.name || "—";
  collectionStats.append(
    statCard("Groups", state.collection.stats.total_groups || 0),
    statCard("Dates", state.collection.stats.total_dates || 0),
    statCard("Avg founder", numericScoreText(state.collection.stats.avg_founder_score || 0)),
    statCard("Recurring groups", state.collection.stats.recurring_ideas || 0),
    statCard("Top category", topCategory)
  );
}

function openReportFromCollection(path) {
  if (!path) {
    return;
  }
  reportSelect.value = path;
  loadReport(path);
}

function ensureSelectedCollectionGroup(groups) {
  if (!groups.length) {
    state.currentCollectionGroupId = "";
    state.currentCollectionPage = 1;
    return null;
  }
  if (!groups.some((group) => group.group_id === state.currentCollectionGroupId)) {
    state.currentCollectionGroupId = groups[0].group_id;
    state.currentCollectionPage = 1;
  }
  clampCollectionPage(groups.length);
  return groups.find((group) => group.group_id === state.currentCollectionGroupId) || groups[0];
}

async function selectCollectionGroup(groupId) {
  const groups = getCollectionGroups();
  const selectedIndex = groups.findIndex((item) => item.group_id === groupId);
  state.currentCollectionGroupId = groupId;
  if (selectedIndex >= 0) {
    state.currentCollectionPage = Math.floor(selectedIndex / COLLECTIONS_PER_PAGE) + 1;
  }
  setWorkspaceTab("focus");
  const group = state.collection?.recurrence_groups?.find((item) => item.group_id === groupId);
  const targetPath = group?.latest_item?.report_path || "";
  if (targetPath && targetPath !== state.currentPath) {
    await loadReport(targetPath, true);
    return;
  }
  renderCollection();
}

function renderCollectionNav(groups, selectedGroup) {
  collectionNav.innerHTML = "";
  const totalGroups = state.collection?.stats?.total_groups || 0;
  const pageCount = clampCollectionPage(groups.length);
  const pageStart = (state.currentCollectionPage - 1) * COLLECTIONS_PER_PAGE;
  const pagedGroups = groups.slice(pageStart, pageStart + COLLECTIONS_PER_PAGE);
  collectionCount.textContent = `${groups.length}/${totalGroups} groups · Page ${state.currentCollectionPage}/${pageCount}`;
  if (!groups.length) {
    collectionNav.appendChild(emptyCard("No collection matches", "Try another search term, date, or category."));
    return;
  }
  for (const group of pagedGroups) {
    const latestItem = group.latest_item || {};
    const button = document.createElement("button");
    button.type = "button";
    button.className = `collection-link${group.group_id === selectedGroup?.group_id ? " is-active" : ""}`;
    button.dataset.groupId = group.group_id;
    button.innerHTML = `
      <span class="collection-link-top">
        <span class="collection-link-title">${escapeHtml(group.label)}</span>
        <span class="collection-link-badge">${escapeHtml(group.momentum_label)}</span>
      </span>
      <span class="collection-link-meta">
        ${escapeHtml(latestItem.date || "—")} · ${escapeHtml(group.appearance_count || 1)}x · Founder ${escapeHtml(scoreText(latestItem, "founder_score"))}
      </span>
    `;
    collectionNav.appendChild(button);
  }
  for (const button of collectionNav.querySelectorAll(".collection-link")) {
    button.addEventListener("click", () => {
      selectCollectionGroup(button.dataset.groupId);
    });
  }
  if (pageCount > 1) {
    const pager = document.createElement("div");
    pager.className = "collection-pagination";
    pager.innerHTML = `
      <button class="button button-compact" type="button" data-page-action="previous"${state.currentCollectionPage === 1 ? " disabled" : ""}>Previous</button>
      <span class="collection-pagination-label">${escapeHtml(`${pageStart + 1}-${Math.min(pageStart + pagedGroups.length, groups.length)} of ${groups.length}`)}</span>
      <button class="button button-compact" type="button" data-page-action="next"${state.currentCollectionPage === pageCount ? " disabled" : ""}>Next</button>
    `;
    collectionNav.appendChild(pager);
    for (const button of pager.querySelectorAll("[data-page-action]")) {
      button.addEventListener("click", () => {
        state.currentCollectionPage += button.dataset.pageAction === "next" ? 1 : -1;
        renderCollection();
      });
    }
  }
}

function renderCollectionDetail(group) {
  collectionDetail.innerHTML = "";
  if (!group) {
    collectionSelectionLabel.textContent = "Choose a title";
    collectionDetail.appendChild(emptyCard("No selection", "Pick a collection title from the side menu."));
    return;
  }
  const latestItem = group.latest_item || {};
  const recurringTag = group.is_recurring ? tag(`Recurring ${group.appearance_count || 2}x`) : tag("Fresh");
  const categoryTags = (group.category_focus || []).slice(0, 4).map(tag).join("");
  const trendTags = (group.trends || []).slice(0, 3).map(tag).join("");
  const repoTags = (group.repos || []).slice(0, 4).map(tag).join("");
  const historyRows = (group.score_history || [])
    .slice()
    .reverse()
    .map(
      (entry) => `
        <button class="collection-history-item" data-path="${escapeHtml(entry.report_path)}" type="button">
          <span class="collection-history-date">${escapeHtml(entry.date)}</span>
          <span class="collection-history-name">${escapeHtml(entry.name)}</span>
          <span class="collection-history-scores">Founder ${escapeHtml(scoreText(entry, "founder_score"))} · Revenue ${escapeHtml(scoreText(entry, "revenue_score"))} · Radar ${escapeHtml(scoreText(entry, "opportunity_score"))}</span>
        </button>
      `
    )
    .join("");
  const detailTabs = [
    { id: "overview", label: "Overview" },
    { id: "signals", label: "Signals" },
    { id: "history", label: "History" },
  ];
  const detailPanels = {
    overview: `
      ${decisionBadge(latestItem.build_decision || {})}
      <div class="mini-grid">
        <div class="mini-block">
          <span class="label">Lifecycle</span>
          <p class="copy">First seen ${escapeHtml(group.first_seen || "—")} · Last seen ${escapeHtml(group.last_seen || "—")} · ${escapeHtml(group.active_dates || 1)} active dates</p>
        </div>
        <div class="mini-block">
          <span class="label">Momentum read</span>
          <p class="copy">Founder ${escapeHtml(scoreDeltaText(group.delta_founder_score || 0))} · Revenue ${escapeHtml(scoreDeltaText(group.delta_revenue_score || 0))} · Radar ${escapeHtml(scoreDeltaText(group.delta_opportunity_score || 0))} versus the previous appearance.</p>
        </div>
        <div class="mini-block">
          <span class="label">Why now</span>
          <p class="copy">${escapeHtml(latestItem.why_now || "")}</p>
        </div>
        <div class="mini-block">
          <span class="label">Revenue path</span>
          <p class="copy">${escapeHtml(latestItem.revenue_model || "")}</p>
        </div>
      </div>
    `,
    signals: `
      <div class="mini-grid">
        <div class="mini-block">
          <span class="label">Current scores</span>
          <p class="copy">Founder ${escapeHtml(scoreText(latestItem, "founder_score"))} · Revenue ${escapeHtml(scoreText(latestItem, "revenue_score"))} · Radar ${escapeHtml(scoreText(latestItem, "opportunity_score"))} · Fit ${escapeHtml(scoreText(latestItem, "trend_repo_match_score"))}</p>
        </div>
        <div class="mini-block">
          <span class="label">Group averages</span>
          <p class="copy">Founder ${escapeHtml(numericScoreText(group.avg_founder_score || 0))} · Revenue ${escapeHtml(numericScoreText(group.avg_revenue_score || 0))} · Radar ${escapeHtml(numericScoreText(group.avg_opportunity_score || 0))}</p>
        </div>
      </div>
      <div class="meta-line">${categoryTags}</div>
      <div class="meta-line">${trendTags}</div>
      <div class="meta-line">${repoTags}</div>
    `,
    history: `
      <section class="collection-history">
        <div class="panel-header">
          <div class="panel-title">
            ${headerBadge("Timeline")}
            <h3>Lifecycle History</h3>
          </div>
          <span>${escapeHtml((group.score_history || []).length)} entries</span>
        </div>
        <div class="stack">${historyRows}</div>
      </section>
    `,
  };
  if (!detailTabs.some((tab) => tab.id === state.currentCollectionDetailTab)) {
    state.currentCollectionDetailTab = "overview";
  }
  collectionSelectionLabel.textContent = `${group.momentum_label} · ${group.appearance_count || 1} appearances`;
  collectionDetail.innerHTML = `
    <div class="collection-detail-head">
      <div class="stack">
        ${headerBadge("Collection brief")}
        <div class="meta-line">
          ${tag(latestItem.date || "—")}
          ${recurringTag}
          ${tag(`Momentum ${group.momentum_score || 0}`)}
          ${tag(group.momentum_label || "Watching")}
        </div>
        <h3>${escapeHtml(group.label || latestItem.name || "Collection item")}</h3>
        <p class="copy">${escapeHtml(latestItem.summary || "")}</p>
      </div>
      <div class="collection-actions">
        ${scoreBadge("Momentum", group.momentum_score || 0)}
        ${scoreBadge("Founder", scoreText(latestItem, "founder_score"))}
        ${scoreBadge("Revenue", scoreText(latestItem, "revenue_score"))}
        <button class="button collection-open" data-path="${escapeHtml(latestItem.report_path || "")}" type="button">Open day</button>
      </div>
    </div>
    <div class="tabs tabs-inline">
      ${detailTabs
        .map(
          (tab) =>
            `<button class="tab-button${tab.id === state.currentCollectionDetailTab ? " is-active" : ""}" type="button" data-detail-tab="${escapeHtml(tab.id)}">${escapeHtml(tab.label)}</button>`
        )
        .join("")}
    </div>
    <div class="tab-panel is-active collection-detail-body">${detailPanels[state.currentCollectionDetailTab]}</div>
  `;
  const openButton = collectionDetail.querySelector(".collection-open");
  if (openButton) {
    openButton.addEventListener("click", (event) => openReportFromCollection(event.currentTarget.dataset.path));
  }
  for (const button of collectionDetail.querySelectorAll("[data-detail-tab]")) {
    button.addEventListener("click", () => {
      state.currentCollectionDetailTab = button.dataset.detailTab;
      renderCollectionDetail(group);
    });
  }
  for (const button of collectionDetail.querySelectorAll(".collection-history-item")) {
    button.addEventListener("click", (event) => openReportFromCollection(event.currentTarget.dataset.path));
  }
}

function renderCollection() {
  const groups = getCollectionGroups();
  const selectedGroup = ensureSelectedCollectionGroup(groups);
  renderCollectionNav(groups, selectedGroup);
  renderCollectionDetail(selectedGroup);
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
          ${scoreBadge("Founder", scoreText(idea, "founder_score"))}
          ${scoreBadge("Radar", scoreText(idea, "opportunity_score"))}
          ${scoreBadge("Revenue", scoreText(idea, "revenue_score"))}
          ${scoreBadge("Fit", scoreText(idea, "trend_repo_match_score"))}
        </div>
      </div>
      <div class="meta-line">${signalTags}</div>
      <div class="meta-line">${categoryTags}${confidence}</div>
      <details class="disclosure-panel idea-disclosure">
        <summary class="disclosure-summary disclosure-inline">
          <div class="memo-header">
            <span class="label">Founder memo</span>
            <span class="micro">Why it scores this way</span>
          </div>
        </summary>
        <section class="memo-panel">
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
      </details>
      <details class="disclosure-panel idea-disclosure">
        <summary class="disclosure-summary disclosure-inline">
          <div class="memo-header">
            <span class="label">Build notes</span>
            <span class="micro">Launch, monetization, and stack</span>
          </div>
        </summary>
        <div class="mini-grid compact-grid">
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
            <p class="copy">Difficulty ${escapeHtml(scoreText(idea, "niche_difficulty_score"))} · Build ${escapeHtml(scoreText(idea, "build_speed_score"))} · Monetization ${escapeHtml(scoreText(idea, "monetization_latency_score"))} · Recurring ${escapeHtml(scoreText(idea, "recurring_revenue_score"))}</p>
          </div>
          <div class="mini-block">
            <span class="label">Repo stack</span>
            <p class="copy repo-list">${repoLinks}</p>
          </div>
        </div>
      </details>
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
        ${tag(`Founder ${scoreText(idea, "founder_score")}`)}
      </div>
      ${decisionBadge(idea.build_decision)}
      <p class="copy">${escapeHtml(idea.summary || "")}</p>
      <p class="copy">${escapeHtml(idea.founder_memo?.best_part || "")}</p>
      <div class="meta-line">
        ${tag(`Build ${scoreText(idea, "build_speed_score")}`)}
        ${tag(`Recurring ${scoreText(idea, "recurring_revenue_score")}`)}
        ${tag(`Fit ${scoreText(idea, "trend_repo_match_score")}`)}
        ${tag(`Revenue ${scoreText(idea, "revenue_score")}`)}
      </div>
    `;
    rankingList.appendChild(item);
  }
}

function renderTrends(report, ideas) {
  trendsList.innerHTML = "";
  const visibleTrends = getVisibleTrends(report, ideas);
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
  if (!reports.length) {
    historyList.appendChild(emptyCard("No history yet", "Daily reports will appear here once they are generated."));
    return;
  }
  for (const report of reports) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `history-item${report.path === state.currentPath ? " is-active" : ""}`;
    item.dataset.path = report.path;
    const activeTag = report.path === state.currentPath ? tag("Open") : "";
    item.innerHTML = `
      <div class="history-row">
        <div>
          <strong>${escapeHtml(report.date)}</strong>
          <p class="copy">${escapeHtml(report.top_idea || "Opportunity Radar")}</p>
        </div>
        <div class="meta-line">
          ${tag(`${report.idea_count} ideas`)}
          ${tag(`Founder ${numericScoreText(report.top_founder_score || 0)}`)}
          ${activeTag}
        </div>
      </div>
    `;
    historyList.appendChild(item);
  }
  for (const button of historyList.querySelectorAll(".history-item")) {
    button.addEventListener("click", () => loadReport(button.dataset.path, true));
  }
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
  renderExecutiveSummary(report, ideas);
  renderIdeas(ideas);
  renderRanking(ideas);
  renderTrends(report, ideas);
  renderSources(report);
  renderHistory();
  renderCollection();
  applyWorkspaceTabState();
  applyRailTabState();
}

function applyWorkspaceTabState() {
  if (state.currentWorkspaceTab === "radar") {
    state.currentWorkspaceTab = "today";
  }
  setActiveTab(workspaceTabs, ".tab-button", state.currentWorkspaceTab, "data-workspace-tab");
  const panelContainer = workspaceTabs?.parentElement;
  if (!panelContainer) {
    return;
  }
  for (const panel of panelContainer.querySelectorAll("[data-workspace-panel]")) {
    panel.classList.toggle("is-active", panel.dataset.workspacePanel === state.currentWorkspaceTab);
  }
  const labels = {
    executive: "Executive summary",
    focus: "Selected collection",
    today: "Ideas and signals",
    history: "History",
  };
  if (workspaceLabel) {
    workspaceLabel.textContent = labels[state.currentWorkspaceTab] || "Daily workspace";
  }
}

function applyRailTabState() {
  setActiveTab(railTabs, ".tab-button", state.currentRailTab);
  const panelContainer = railTabs?.parentElement;
  if (!panelContainer) {
    return;
  }
  for (const panel of panelContainer.querySelectorAll(".tab-panel")) {
    panel.classList.toggle("is-active", panel.dataset.panel === state.currentRailTab);
  }
  const labels = {
    ranking: "Founder bets",
    trends: "Trend snapshot",
    sources: "Source health",
  };
  if (railLabel) {
    railLabel.textContent = labels[state.currentRailTab] || "Signals";
  }
}

async function getReport(path) {
  if (!state.reports.has(path)) {
    state.reports.set(path, fetchJson(`./${path}`));
  }
  return state.reports.get(path);
}

async function loadReport(path, preserveCollectionSelection = false) {
  state.currentPath = path;
  state.currentReport = await getReport(path);
  const reports = state.index?.reports || [];
  populateCategoryFilter(state.currentReport);
  if (!preserveCollectionSelection && !state.currentCollectionGroupId) {
    const groups = getCollectionGroups();
    if (groups[0]) {
      state.currentCollectionGroupId = groups[0].group_id;
    }
  }
  renderCurrentView();
}

async function init() {
  try {
    const [index, collection] = await Promise.all([
      fetchJson("./data/index.json"),
      fetchJson("./data/collection.json"),
    ]);
    state.index = index;
    state.collection = collection;
    const reports = state.index.reports || [];
    reportSelect.innerHTML = reports
      .map(
        (report) =>
          `<option value="${escapeHtml(report.path)}" ${report.date === state.index.latest ? "selected" : ""}>${escapeHtml(report.date)} · ${escapeHtml(report.top_idea || "Opportunity Radar")}</option>`
      )
      .join("");
    const collectionDates = ["All dates", ...Object.keys(state.collection?.stats?.ideas_by_date || {}).sort().reverse()];
    collectionDateFilter.innerHTML = collectionDates
      .map((date) => `<option value="${escapeHtml(date)}">${escapeHtml(date)}</option>`)
      .join("");
    renderCollectionStats();
    reportSelect.addEventListener("change", (event) => loadReport(event.target.value));
    categoryFilter.addEventListener("change", renderCurrentView);
    sortSelect.addEventListener("change", renderCurrentView);
    collectionSearch.addEventListener("input", () => {
      state.currentCollectionPage = 1;
      renderCollection();
    });
    collectionDateFilter.addEventListener("change", () => {
      state.currentCollectionPage = 1;
      renderCollection();
    });
    collectionSort.addEventListener("change", () => {
      state.currentCollectionPage = 1;
      renderCollection();
    });
    for (const button of workspaceTabs?.querySelectorAll(".tab-button") || []) {
      button.addEventListener("click", () => {
        setWorkspaceTab(button.dataset.workspaceTab);
      });
    }
    for (const button of railTabs?.querySelectorAll(".tab-button") || []) {
      button.addEventListener("click", () => {
        state.currentRailTab = button.dataset.tab;
        applyRailTabState();
      });
    }
    const initialPath = reports.find((report) => report.date === state.index.latest)?.path || reports[0]?.path;
    const initialGroup = getCollectionGroups()[0];
    if (initialGroup) {
      state.currentCollectionGroupId = initialGroup.group_id;
    }
    applyWorkspaceTabState();
    applyRailTabState();
    if (initialPath) {
      await loadReport(initialPath);
    }
  } catch (error) {
    modePill.textContent = "unavailable";
    ideasList.innerHTML = "";
    ideasList.appendChild(emptyCard("Data unavailable", error.message));
    collectionNav.innerHTML = "";
    collectionNav.appendChild(emptyCard("Collection unavailable", error.message));
    collectionDetail.innerHTML = "";
    collectionDetail.appendChild(emptyCard("Selection unavailable", error.message));
  }
}

init();
