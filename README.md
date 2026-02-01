# Dalgo Lite

**Lightweight data transformation for NGOs**

A no-code data platform that lets M&E teams transform Google Sheets data using familiar Excel-like operations.

---

## Vision

Enable non-technical NGO staff to:
1. **Connect** multiple Google Sheets to a central data warehouse
2. **Transform** data using click-based operations (no SQL required)
3. **Output** clean, aggregated tables for reporting and visualization

---

## Documentation

| Document | Description |
|----------|-------------|
| [01_PRD_RESEARCH.md](./docs/01_PRD_RESEARCH.md) | Product requirements, market research, tool evaluations |
| [02_TECH_STACK.md](./docs/02_TECH_STACK.md) | Technology choices, libraries, infrastructure |
| [03_ARCHITECTURE.md](./docs/03_ARCHITECTURE.md) | System design, data flows, API specifications |

---

## Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Data Source** | Google Sheets only | 80% of NGO data, single OAuth flow |
| **Data Warehouse** | MotherDuck (user's account) | 10GB free, user owns data |
| **Metadata DB** | Supabase PostgreSQL | Free tier, built-in auth, RLS |
| **Auth** | Supabase + Google OAuth | SSO + Sheets API access |
| **Frontend** | Next.js 15 | Modern React, good DX |
| **Backend** | Python + FastAPI | Best for data processing |
| **Transformations** | Click UI → SQL | No technical barrier |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DALGO LITE                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────┐  │
│  │   INGEST      │    │   TRANSFORM   │    │     OUTPUT        │  │
│  │               │    │               │    │                   │  │
│  │ Google Sheets │───▶│ Visual Canvas │───▶│ Tables in         │  │
│  │ Picker        │    │ Click Actions │    │ MotherDuck        │  │
│  └───────────────┘    └───────────────┘    └───────────────────┘  │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Frontend: Next.js 15 + TypeScript + Tailwind                      │
│  Backend: Python 3.12 + FastAPI                                    │
│  Auth/Metadata: Supabase                                           │
│  Data Warehouse: MotherDuck (user's account)                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Transformation Actions (Click-Based)

Users never write SQL. Instead, they use these click interfaces:

| Action | Excel Equivalent | What It Does |
|--------|-----------------|--------------|
| Filter | AutoFilter | Keep rows matching conditions |
| Join | VLOOKUP | Combine tables on matching columns |
| Group & Summarize | Pivot Table | Aggregate data by categories |
| Add Column | IF formula | Create calculated columns |
| Clean Data | TRIM, UPPER | Fix messy text data |
| Remove Duplicates | Remove Duplicates | Dedupe rows |
| Sort | Sort | Order data |
| Select Columns | Hide Columns | Choose columns to keep |

---

## Project Structure

```
dalgo-lite/
├── README.md
├── docs/
│   ├── 01_PRD_RESEARCH.md      # Product & research documentation
│   ├── 02_TECH_STACK.md        # Technology decisions
│   └── 03_ARCHITECTURE.md      # System architecture
│
├── frontend/                    # Next.js application
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── stores/
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
│
└── infrastructure/              # Deployment configs
    ├── docker-compose.yml
    └── railway.toml
```

---

## Getting Started (Development)

### Prerequisites

- Node.js 20+
- Python 3.12+
- Supabase CLI
- Google Cloud project (for Sheets API)

### Setup

```bash
# Clone and enter directory
cd dalgo-lite

# Frontend
cd frontend
npm install
cp .env.example .env.local
npm run dev

# Backend (new terminal)
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# Supabase (new terminal)
supabase start
```

---

## Roadmap

### Phase 1: MVP
- [ ] Google Sheets OAuth integration
- [ ] Sheet picker and preview
- [ ] Basic sync to MotherDuck
- [ ] Filter, Select, Sort actions
- [ ] Preview grid with AG Grid

### Phase 2: Core Transforms
- [ ] Join tables (VLOOKUP equivalent)
- [ ] Group & Summarize
- [ ] Add calculated columns
- [ ] Clean data actions
- [ ] Visual transformation canvas

### Phase 3: Polish
- [ ] Scheduled syncs
- [ ] Export back to Sheets
- [ ] Share transformations
- [ ] Transformation templates

---

## Contributing

This is an internal project. See CLAUDE.md in the parent Dalgo directory for development guidelines.

---

## License

Proprietary - Tech4Dev

---

*Built with care for the NGO community*
