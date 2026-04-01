# UI/UX Restructure Plan - GitHub Organizer Dashboard

## Project Analysis

**Product Type:** Dashboard / Data Visualization
**Industry:** Developer Tools / Analytics
**Current State:** Functional dashboard with improved structure, but now expanding into a collection-first archive experience

---

## Current Design Assessment

### Strengths
- Clean grid-based layout
- Good information hierarchy
- Responsive breakpoints exist
- Semantic HTML structure
- Daily report flow already supports strong score-based scanning

### Areas for Improvement
1. **Collection Discoverability** - archive browsing needs a permanent side-menu home
2. **Middle-Panel Focus** - the main content area should reveal one selected collection group at a time
3. **Lifecycle Clarity** - recurring concepts need semantic grouping plus momentum, not just name matching
4. **Card Density** - idea cards remain information-rich and need clearer breathing room on smaller screens
5. **Interactive States** - filters, search, and open-day actions need stronger visual feedback
6. **Visual Cohesion** - collection, daily report, ranking, and history should feel like one system
7. **Theme Depth** - still light-only and visually soft, with room for richer state styling

---

## Product Structure Recommendations

### Information Architecture
- Keep the daily report view as the operational page for the newest run
- Keep collection titles in a dedicated left-side menu so archive browsing remains available while reading the main page
- Use the middle panel as the single detail surface for the selected collection group
- Reuse the same category language across daily and archive views to reduce cognitive load
- Let the collection become the quick-access layer and the middle panel become the semantic lifecycle detail layer
- Surface semantic recurrence windows and momentum so users can tell whether an idea is genuinely strengthening or just recurring

### Mobile-First Collection Behavior
- Search should sit first because it is the fastest action for repeated visits
- Date and sort controls should collapse cleanly into a single-column stack on smaller widths
- Collection titles should stay short in the side menu and show just enough metadata for fast scanning
- The middle detail panel should carry the heavier content: summary, momentum, lifecycle window, and report history
- Action buttons need clear tap targets and a direct route into the selected report

### Visual System
- Preserve the calm warm-light palette already used in production
- Distinguish state through labels such as latest, fresh, and recurring rather than louder colors
- Keep rounded containers and soft borders to avoid visual noise while adding archive complexity
- Use the same score and tag language across daily cards and collection cards

---

## Proposed Changes

### Phase 1: Collection Layer
1. **Add collection side menu** - keep cross-date archive titles always visible with search, date filter, and sort
2. **Add middle detail panel** - render the selected collection group's content without another dense card grid
3. **Add collection stats** - show total groups, total dates, recurring groups, and top category
4. **Add open-day flow** - jump from any selected collection group into the matching report
5. **Add lifecycle window** - show first-seen and last-seen dates for semantic recurrence groups

### Phase 2: Responsive Cleanup
6. **Refine toolbar stacking** - keep search and filters legible on tablet and mobile
7. **Refine side menu states** - keep active, hover, and focus states visible without visual noise
8. **Unify tag rhythm** - keep dates, categories, trends, and momentum states visually balanced
9. **Preserve scan speed** - keep summaries short and actions obvious

### Phase 3: Next Polish Pass
10. **Lifecycle momentum** - rank semantic groups by whether they are strengthening, steady, or cooling
11. **Focus states** - visible keyboard focus for search, filters, and open-day controls
12. **Hover states** - subtle interaction feedback without layout shift
13. **Theme extension** - optional gentle dark mode once the archive interaction settles

---

## Implementation Order

1. `generate_opportunities.py` - emit `collection.json`, semantic signatures, recurrence-group metadata, and lifecycle momentum
2. `index.html` - move collection into the side menu and add a dedicated middle detail panel
3. `app.js` - wire archive loading, filtering, sidebar selection, sorting, open-day navigation, and lifecycle windows
4. `styles.css` - support the three-column layout on desktop and the stacked flow on mobile
5. Validate the daily view, collection view, and history navigation together

---

## Verification Checklist

- [ ] Collection titles stay visible in the side menu without crowding the page
- [ ] Search, date filter, and sort work together without breaking the daily report view
- [ ] Open-day navigation loads the correct report from the archive
- [ ] Recurring ideas show first-seen and last-seen windows plus lifecycle momentum derived from semantic groups
- [ ] No overlap or horizontal scroll appears on mobile or tablet
- [ ] Interactive controls remain touch-friendly and keyboard accessible
- [ ] Daily report and collection styling feel consistent
