# Dalgo Lite: Product Requirements & Research Document

**Version:** 1.0
**Date:** February 2026
**Status:** Research & Planning

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Target Users](#target-users)
4. [Market Research](#market-research)
5. [Tool Evaluation & Decisions](#tool-evaluation--decisions)
6. [Product Requirements](#product-requirements)
7. [Competitive Analysis](#competitive-analysis)
8. [Risk Assessment](#risk-assessment)

---

## Executive Summary

Dalgo Lite is a lightweight data transformation platform designed specifically for NGO Monitoring & Evaluation (M&E) teams. It enables non-technical users to:

- Ingest data from multiple Google Sheets
- Transform data using a 100% click-based interface (no SQL or formulas required)
- Create metrics and outputs for reporting

**Key Differentiator:** Users interact with data using familiar Excel-like concepts, while the platform generates and executes SQL transformations under the hood.

---

## Problem Statement

### The Current Reality for NGO M&E Teams

1. **Data Lives in Spreadsheets**: 90%+ of NGO program data resides in Google Sheets or Excel
2. **Technical Barrier**: M&E officers understand Excel but not SQL, schemas, or data warehouses
3. **Manual Processes**: Data cleaning and transformation is done manually, repeatedly
4. **Tool Complexity**: Existing data tools (Airbyte, dbt, Prefect) require technical expertise
5. **Cost Sensitivity**: NGOs operate on limited budgets; enterprise tools are prohibitive

### User Quote (from research)

> "I can't run these queries easily so I have to export this into Excel but everything else related to the facility goes away so I have to work with MS Access. My approach to data cleaning is limited by my abilities in the tool."
>
> — NGO Data Manager, [ICTD Research Paper](https://ictd.cs.washington.edu/docs/papers/2019/pervaiz_compass2019_data.pdf)

### The Gap We're Filling

| What Users Know | What Tools Require | The Gap |
|-----------------|-------------------|---------|
| Excel filters | SQL WHERE clauses | Translation needed |
| VLOOKUP | JOIN statements | Concept mapping |
| Pivot tables | GROUP BY + aggregates | Visual interface |
| "Clean up this column" | TRIM, UPPER, CASE WHEN | Click-based actions |

---

## Target Users

### Primary Persona: M&E Officer

**Name:** Sarah
**Role:** Monitoring & Evaluation Officer at a health NGO
**Technical Skills:** Advanced Excel, basic Google Sheets formulas
**Pain Points:**
- Spends 2-3 days/month manually cleaning and combining data
- Struggles with data from multiple program sites
- Cannot create consistent metrics across reporting periods
- Relies on technical staff for anything beyond Excel

**Goals:**
- Combine beneficiary data from 5+ Google Sheets
- Clean inconsistent district names and dates
- Calculate program metrics (enrollment rate, completion rate)
- Generate quarterly reports

### Secondary Persona: Program Manager

**Name:** David
**Role:** Program Manager overseeing multiple projects
**Technical Skills:** Basic Excel, comfortable with dashboards
**Pain Points:**
- Needs visibility across all program data
- Cannot wait for technical team to build reports
- Data is often outdated by the time reports are ready

**Goals:**
- Self-service access to combined program data
- Real-time metrics without technical intervention
- Share data views with donors and stakeholders

---

## Market Research

### Existing Solutions Evaluated

#### 1. Heavy-Duty Data Platforms

| Tool | Pros | Cons | Why Not for Lite |
|------|------|------|------------------|
| **Airbyte** | 300+ connectors, robust | Complex setup, requires infrastructure | Too heavy for target users |
| **Prefect** | Powerful orchestration | Requires Python knowledge | Technical barrier |
| **dbt** | Industry standard transforms | SQL-first, steep learning curve | Users don't know SQL |
| **Fivetran** | Managed, reliable | Expensive ($$$), enterprise focus | Cost prohibitive |

#### 2. Spreadsheet-Database Hybrids

| Tool | Approach | Limitations |
|------|----------|-------------|
| **[Grist](https://github.com/gristlabs/grist-core)** | Open-source spreadsheet with database structure | SQLite-based, not warehouse-scale |
| **[NocoDB](https://github.com/nocodb/nocodb)** | Airtable alternative on any database | View layer only, no transformation |
| **[Teable](https://github.com/teableio/teable)** | Fast no-code database on Postgres | Limited transformation capabilities |
| **[Baserow](https://baserow.io/)** | Open-source Airtable | No SQL generation, limited scale |

**Insight:** These tools are great for viewing data as spreadsheets but don't solve the transformation problem.

#### 3. Visual Data Transformation Tools

| Tool | Approach | Limitations |
|------|----------|-------------|
| **[Sigma Computing](https://www.sigmacomputing.com/)** | Spreadsheet interface on cloud warehouses | Commercial, expensive |
| **[Trifacta](https://www.trifacta.com/)** | Visual data wrangling | Enterprise pricing, complex |
| **[Alteryx](https://www.alteryx.com/)** | Drag-and-drop workflows | Very expensive ($5k+/year) |
| **[Paxata](https://www.datarobot.com/)** | Self-service data prep | Acquired by DataRobot, enterprise |

**Insight:** These prove the concept works but are priced for enterprises, not NGOs.

#### 4. Code Generation Tools

| Tool | What It Does | Relevance |
|------|--------------|-----------|
| **[Mito](https://github.com/mito-ds/mito)** | Spreadsheet in Jupyter → generates pandas code | **Architecture inspiration** |
| **[Ibis](https://github.com/ibis-project/ibis)** | Python dataframe API → compiles to SQL | **Potential backend component** |
| **[dbt-ibis](https://ibis-project.org/posts/dbt-ibis/)** | Write dbt models in Python | Future integration path |

**Key Insight from Mito:**
> "Every edit made in the spreadsheet generates equivalent code in the cell below."

This is exactly our approach: every click-based action generates SQL.

#### 5. Data Warehouse Options

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **DuckDB-WASM** | Runs in browser, zero infra | No persistence, session-only | Good for preview |
| **[MotherDuck](https://motherduck.com/)** | 10GB free, hosted DuckDB, persistent | Requires account setup | **Primary choice** |
| **BigQuery** | Native Sheets integration, 10GB free | More complex setup | Alternative option |
| **Supabase Postgres** | Free tier, familiar | Not optimized for analytics | Metadata only |

---

## Tool Evaluation & Decisions

### Decision 1: Data Warehouse → MotherDuck

**Why MotherDuck?**

| Criteria | MotherDuck | BigQuery | DuckDB-WASM |
|----------|------------|----------|-------------|
| Free tier | 10GB storage | 10GB storage, 1TB queries | Unlimited (browser) |
| Persistence | Yes | Yes | No |
| Setup complexity | Low (OAuth) | Medium | None |
| SQL compatibility | DuckDB (modern) | GoogleSQL | DuckDB |
| User data ownership | User's account | User's account | Browser only |
| Performance | Excellent | Excellent | Good (limited by browser) |

**Decision:** MotherDuck as primary, with DuckDB-WASM for instant previews.

**Sources:**
- [MotherDuck Pricing](https://motherduck.com/pricing/)
- [DuckDB-WASM Documentation](https://duckdb.org/docs/api/wasm/overview.html)

---

### Decision 2: Transformation Approach → Click-Based UI Generating SQL

**Why not formulas?**

Even Excel formulas are a barrier for some users. Research shows:
- Users understand *what* they want (filter, combine, summarize)
- Users struggle with *how* to express it (syntax)

**Approach:** Map Excel *concepts* to SQL *operations* through UI clicks.

| User Action | UI Element | Generated SQL |
|-------------|------------|---------------|
| "Show only active" | Filter dialog with checkboxes | `WHERE status = 'Active'` |
| "Combine with programs" | Join wizard | `LEFT JOIN programs ON...` |
| "Count by district" | Group & Summarize panel | `GROUP BY district` |
| "Fix messy names" | Clean Data dialog | `TRIM(UPPER(...))` |

**Inspiration Sources:**
- [Mito](https://www.trymito.io/) - spreadsheet → pandas code
- [Sigma Computing](https://www.sigmacomputing.com/) - spreadsheet → SQL
- [React Query Builder](https://react-querybuilder.js.org/) - visual → SQL

---

### Decision 3: No Formulas, Pure Click Interface

**Research Finding:** Even "simple" Excel formulas create barriers.

From user research:
- `=IF(A1>18, "Adult", "Minor")` requires understanding:
  - Cell references
  - Function syntax
  - Quotation marks for strings
  - Nested logic

**Our Approach:** Replace formulas with guided wizards.

```
Instead of: =IF(Age>18, "Adult", IF(Age>12, "Teen", "Child"))

User clicks: Add Column → Categorize →
  Rule 1: If Age > 18 → "Adult"
  Rule 2: If Age > 12 → "Teen"
  Otherwise → "Child"
```

---

### Decision 4: Google Sheets Only (Initially)

**Why limit to Google Sheets?**

1. **80/20 Rule:** Google Sheets covers 80%+ of NGO data sources
2. **Unified Auth:** Single OAuth flow for both Sheets access and user identity
3. **Reduced Complexity:** One connector to build and maintain
4. **User Familiarity:** Target users already live in Google Sheets

**Future Expansion:** Excel files, CSV uploads, Kobo Toolbox, DHIS2

---

### Decision 5: Visual Transformation Canvas

**Why a canvas/flow view?**

Users need to understand:
1. Where data comes from
2. What transformations are applied
3. How tables connect

**Inspiration:**
- Alteryx workflow canvas
- Prefect flow visualization
- dbt lineage graphs

**Our Implementation:**
```
[Source: Beneficiaries] → [Join: Programs] → [Filter: Active] → [Output]
         │                       │                  │
      12,456 rows           12,456 rows         8,234 rows
```

Each node is clickable, editable, and shows row counts.

---

## Product Requirements

### Core Features (MVP)

#### Ingestion
| Feature | Priority | Description |
|---------|----------|-------------|
| Google Sheets picker | P0 | Browse and select sheets from user's Drive |
| Sheet preview | P0 | Show first N rows before importing |
| Auto-sync | P1 | Scheduled refresh (6hr, daily) |
| Multiple sheets | P0 | Connect 5+ sheets per workspace |

#### Transformation
| Feature | Priority | Description |
|---------|----------|-------------|
| Filter rows | P0 | Click-based condition builder |
| Select columns | P0 | Checkbox to include/exclude |
| Join tables | P0 | Visual join wizard (like VLOOKUP) |
| Group & summarize | P0 | Aggregate with COUNT, SUM, AVG |
| Clean data | P0 | Trim, case conversion, null handling |
| Add column (categorize) | P1 | Rule-based value assignment |
| Remove duplicates | P1 | Dedupe by selected columns |
| Sort | P1 | Multi-column sort |

#### Output
| Feature | Priority | Description |
|---------|----------|-------------|
| Preview results | P0 | Live preview of transformation output |
| Save as table | P0 | Persist to MotherDuck |
| Export to Sheets | P1 | Write back to Google Sheets |

### Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Page load time | < 3 seconds |
| Transformation preview | < 5 seconds for 100k rows |
| Concurrent users | 100+ per workspace |
| Data freshness | < 1 hour with auto-sync |
| Uptime | 99.5% |

---

## Competitive Analysis

### Positioning Map

```
                    Technical Expertise Required
                    Low ◄─────────────────────► High
                    │
        Expensive   │   [Alteryx]    [Fivetran]
            ▲       │
            │       │   [Sigma]      [dbt Cloud]
            │       │
    Cost    │       │
            │       │   ★ DALGO LITE
            │       │
            ▼       │   [Grist]      [dbt Core]
        Free/       │   [NocoDB]
        Cheap       │
```

### Competitive Advantages

| vs. Tool | Our Advantage |
|----------|---------------|
| vs. Alteryx/Trifacta | 100x cheaper, NGO-focused |
| vs. Sigma Computing | Free tier, simpler UX |
| vs. Grist/NocoDB | Actual transformations, not just viewing |
| vs. dbt | No SQL required, visual interface |
| vs. Manual Excel | Automated, repeatable, scalable |

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MotherDuck free tier changes | Medium | High | Abstract warehouse layer, support BigQuery fallback |
| Google Sheets API rate limits | Medium | Medium | Implement caching, batch operations |
| Complex joins confuse users | High | Medium | Guided wizards, smart defaults |
| SQL generation edge cases | Medium | High | Comprehensive test suite, user feedback loop |

### Product Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users still find it too complex | Medium | High | User testing, iterative simplification |
| Feature creep | High | Medium | Strict MVP scope, phased rollout |
| Adoption challenges | Medium | High | Partner with 2-3 NGOs for pilot |

### Market Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sigma/others launch free tier | Low | High | Focus on NGO-specific features |
| Google launches similar tool | Low | High | Build community, switch costs |

---

## Success Metrics

### North Star Metric
**Transformations successfully executed per week**

### Supporting Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Registered organizations | 50 |
| Active users (weekly) | 200 |
| Sheets connected | 500 |
| Transformations created | 1,000 |
| Time saved per user | 4 hrs/week |

---

## References & Sources

### Research Papers
- [Examining the Challenges in Development Data Pipeline](https://ictd.cs.washington.edu/docs/papers/2019/pervaiz_compass2019_data.pdf) - ICTD 2019

### Tool Documentation
- [Mito - Spreadsheet that generates Python](https://www.trymito.io/)
- [Ibis - Portable Python dataframe library](https://ibis-project.org/)
- [dbt-ibis integration](https://ibis-project.org/posts/dbt-ibis/)
- [MotherDuck](https://motherduck.com/)
- [DuckDB-WASM](https://duckdb.org/docs/api/wasm/overview.html)
- [React Query Builder](https://react-querybuilder.js.org/)
- [Sigma Computing](https://www.sigmacomputing.com/)
- [Grist](https://github.com/gristlabs/grist-core)

### Industry Analysis
- [dbt Alternatives Comparison](https://coalesce.io/data-insights/top-10-dbt-alternatives-and-competitors-for-modern-data-teams/)
- [Data Transformation Tools 2025](https://blog.coupler.io/data-transformation-tools/)
- [NGO Data Management Challenges - DHIS2](https://docs.dhis2.org/en/full/implement/dhis2-implementation-guide.html)

---

*Document maintained by: Dalgo Lite Product Team*
*Last updated: February 2026*
