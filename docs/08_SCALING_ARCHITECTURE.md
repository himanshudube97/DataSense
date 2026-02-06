# DataSense: Scaling Architecture — From 1 Org to 1,000

**Version:** 1.0
**Date:** February 2026
**Status:** Decision Record

---

## Table of Contents

1. [What Are We Building?](#what-are-we-building)
2. [The Naive Architecture (And Why It Breaks)](#the-naive-architecture)
3. [Option A: ARQ — The Lightweight Attempt](#option-a-arq)
4. [Option B: Celery + Redis + RedBeat — The Right Fit](#option-b-celery--redis--redbeat)
5. [Why Not Prefect?](#why-not-prefect)
6. [Final Architecture](#final-architecture)
7. [Scaling Playbook](#scaling-playbook)
8. [Component Deep Dives](#component-deep-dives)
9. [Deep Dive: DLT State Problem & Multi-Worker Solution](#deep-dive-dlt-state-problem)
10. [Deep Dive: What Actually Scales & How](#deep-dive-what-actually-scales)
11. [Deep Dive: Connection Pooling (PgBouncer)](#deep-dive-connection-pooling)
12. [Cost & Resource Estimates](#cost--resource-estimates)
13. [Failure Modes & Recovery](#failure-modes--recovery)

---

## What Are We Building?

DataSense is a no-code data platform for NGOs. The core pipeline is:

```
Data Sources (Google Sheets, Kobo, SurveyCTO, CSV)
        │
        ▼
   [ INGEST ]  ← DLT fetches data, loads into Postgres
        │
        ▼
   [ TRANSFORM ]  ← Ibis converts click-based recipes to SQL
        │
        ▼
   [ SERVE ]  ← AG Grid shows results in spreadsheet view
```

### The Scale We're Designing For

| Metric | Value |
|--------|-------|
| Organizations | 1,000 |
| Sources per org (avg) | 5 |
| Total sources | 5,000 |
| Syncs per hour (peak) | ~4,500 |
| Syncs per minute (peak) | ~75 |
| Avg sync duration | 30-60 seconds |
| Data per org (avg) | 50-500 MB |
| Total data | 50-500 GB |

### The Analogy: A Restaurant Kitchen

Think of DataSense as a **restaurant chain** with 1,000 locations (orgs).

- Each location sends **orders** (sync requests) to a central kitchen
- The kitchen has **cooks** (workers) who prepare the orders
- A **manager** (scheduler) decides when each location's orders should be prepared
- The **pantry** (PostgreSQL) stores all the ingredients and finished dishes
- The **order board** (Redis) tracks which orders are pending, in-progress, or done

The question is: how do we design this kitchen so it handles 75 orders per minute without burning anything?

---

## The Naive Architecture

### What it looks like

The simplest possible design — everything runs inside the FastAPI web server:

```
┌─────────────────────────────────────────────────┐
│                  FastAPI Server                   │
│                                                   │
│   POST /api/sources/{id}/sync                     │
│        │                                          │
│        ▼                                          │
│   async def sync_source():                        │
│       connector = get_connector(source)           │
│       pipeline = dlt.pipeline(...)                │
│       result = pipeline.run(source)  # BLOCKING!  │
│       return {"rows": result.rows}                │
│                                                   │
│   Background: APScheduler polls next_sync_at      │
│        │                                          │
│        ▼                                          │
│   Every minute, check DB for due syncs            │
│   Run them with asyncio.create_task()             │
│                                                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │   PostgreSQL    │
          └────────────────┘
```

### Why it seems appealing

- Zero extra infrastructure (no Redis, no worker processes)
- Simple deployment (one container + one database)
- Fast to build
- Works perfectly for 1-10 orgs

### Why it breaks: The Restaurant Analogy

Imagine a restaurant where the **waiter is also the cook**. When a customer orders a steak (sync request), the waiter walks to the kitchen, cooks the steak for 30 minutes, then brings it back. Meanwhile, every other customer is staring at the door wondering where their waiter went.

That's exactly what happens here:

#### Problem 1: API Starvation

```
Timeline of a single FastAPI worker (4 workers total):

00:00  Worker 1: Handling API request (fast, 50ms) ✓
00:01  Worker 1: Starts DLT sync for Org A (takes 45 seconds)
00:02  Worker 2: Handling API request ✓
00:03  Worker 2: Starts DLT sync for Org B (takes 30 seconds)
00:04  Worker 3: Starts DLT sync for Org C
00:05  Worker 4: Starts DLT sync for Org D
00:06  USER TRIES TO LOAD DASHBOARD → All workers busy → 504 Gateway Timeout ✗
```

DLT's `pipeline.run()` is **CPU-bound** (parsing, type inference) and **IO-bound** (HTTP requests, DB writes). Even though FastAPI is async, DLT itself runs synchronously. It blocks the event loop or ties up the thread pool.

**At 75 syncs/minute**, you'd need 40-75 API workers just to handle syncs — leaving nothing for actual user requests.

#### Problem 2: No Horizontal Scaling

```
┌─────────────┐     ┌─────────────┐
│  FastAPI 1   │     │  FastAPI 2   │
│              │     │              │
│  Scheduler ✓ │     │  Scheduler ✓ │   ← BOTH schedulers fire!
│  "Sync Org A"│     │  "Sync Org A" │   ← DUPLICATE SYNCS
└─────────────┘     └─────────────┘
```

APScheduler runs inside each process. If you scale to 2 API instances (behind a load balancer), both instances will trigger the same scheduled syncs. You get duplicate work, race conditions, and data corruption.

**The Restaurant Analogy:** Two managers both read the same order board and send two cooks to make the same dish. You waste food and confuse the customer.

#### Problem 3: No Retry Isolation

If a sync fails halfway through (Google Sheets API timeout), the entire request fails. There's no automatic retry, no dead letter queue, no way to inspect what failed and why.

```python
# What happens when Google returns a 429:
async def sync_source(source_id):
    pipeline = dlt.pipeline(...)
    result = pipeline.run(source)  # 💥 HTTPError: 429 Too Many Requests
    # Exception propagates to API response
    # User sees "Internal Server Error"
    # No retry. Data is partially loaded. State is inconsistent.
```

#### Problem 4: Memory Pressure

Each DLT sync loads data into memory before writing to Postgres. At 75 concurrent syncs:

```
75 syncs × ~50MB memory each = 3.75 GB just for sync buffers
+ FastAPI process memory (~200MB)
+ PostgreSQL connections (75 × ~10MB = 750MB)
= ~4.7 GB minimum

Single server with 8GB RAM? You're swapping to disk. OOM killer incoming.
```

### Verdict: Naive Architecture

| Metric | Rating |
|--------|--------|
| Works at 1-10 orgs | Yes |
| Works at 100 orgs | Barely |
| Works at 1,000 orgs | No |
| Effort to build | Low |
| Effort to fix later | Very High (rewrite) |

**Lesson:** Separating "accepting work" from "doing work" is the single most important scaling decision. This is the **waiter vs cook** separation.

---

## Option A: ARQ

### What is ARQ?

ARQ (Asynchronous Redis Queue) is a lightweight Python job queue built on asyncio and Redis. Think of it as "Celery but tiny."

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ FastAPI   │────▶│  Redis    │◀────│ ARQ      │
│ (waiter)  │     │ (order    │     │ Worker   │
│           │     │  board)   │     │ (cook)   │
└──────────┘     └──────────┘     └──────────┘
       │                                │
       ▼                                ▼
┌─────────────────────────────────────────────┐
│                PostgreSQL                    │
└─────────────────────────────────────────────┘
```

### What ARQ gets right

1. **Separation of concerns**: API server enqueues tasks, worker executes them
2. **Async-native**: Built on asyncio, matches FastAPI's model
3. **Built-in cron**: Can schedule recurring jobs
4. **Tiny footprint**: ~500 lines of source code, ~2MB memory overhead
5. **Simple API**:

```python
# Enqueue a sync task
await arq_redis.enqueue_job("sync_source", source_id="src_123")

# Worker function
async def sync_source(ctx, source_id: str):
    connector = get_connector(source_id)
    result = await connector.sync(...)
    return result

# Cron schedule
class WorkerSettings:
    cron_jobs = [
        cron(check_due_syncs, hour=None, minute={0, 15, 30, 45})
    ]
```

### Where ARQ breaks at scale

#### Problem 1: Single-Worker Cron

ARQ's cron jobs run on **every worker instance**. If you run 5 ARQ workers, your `check_due_syncs` function fires 5 times simultaneously.

```
Worker 1: check_due_syncs() → finds 100 due syncs → enqueues them
Worker 2: check_due_syncs() → finds same 100 → enqueues DUPLICATES
Worker 3: check_due_syncs() → finds same 100 → enqueues DUPLICATES
```

**The Restaurant Analogy:** You hired 5 managers to check the order board. They all read it at the same time and each one tells the kitchen to make every dish. Now you have 5x the food being made.

You can work around this with distributed locking (Redis `SETNX`), but now you're building infrastructure that other tools give you for free.

#### Problem 2: No Task Routing or Queues

ARQ has **one queue**. Every task goes into the same queue, and every worker pulls from it.

At 1,000 orgs, you want:
- **Sync queue**: Heavy IO tasks (DLT pipelines)
- **Transform queue**: Light CPU tasks (Ibis/SQL)
- **Urgent queue**: Manual sync triggers (user is waiting)
- **Notification queue**: Email/Slack alerts

With ARQ, a burst of 500 sync tasks blocks your transform tasks. The user who just clicked "Run Transform" waits behind 500 scheduled syncs.

```
ARQ Queue (single):
[sync_org_1, sync_org_2, ..., sync_org_500, TRANSFORM_user_clicked, sync_org_501...]
                                              ↑
                                    User is waiting for THIS
                                    but it's behind 500 syncs
```

**The Restaurant Analogy:** One kitchen line for everything. Appetizers, mains, desserts, takeout — all in one queue. A rush of takeout orders means dine-in customers wait 45 minutes for their salad.

#### Problem 3: No Rate Limiting Per Task Type

Google Sheets API has a rate limit of ~100 requests per 100 seconds per user. KoboToolbox has different limits. ARQ has no built-in mechanism to say "max 30 Google Sheets syncs per minute."

You'd need to build this yourself:

```python
# You'd have to write all of this:
RATE_LIMITS = {"google_sheets": 30, "kobo": 50}
counters = {}

async def sync_source(ctx, source_id):
    source = await get_source(source_id)
    while counters.get(source.type, 0) >= RATE_LIMITS[source.type]:
        await asyncio.sleep(1)  # Busy-wait? Not great.
    counters[source.type] += 1
    try:
        await do_sync(source)
    finally:
        counters[source.type] -= 1
```

This is fragile, doesn't work across multiple workers, and wastes memory holding tasks in a sleep loop.

#### Problem 4: Limited Observability

ARQ has no built-in dashboard. To know "how many syncs are running right now?" or "which orgs have failing syncs?", you need to build monitoring from scratch.

At 10 orgs, you check logs. At 1,000 orgs, you need:
- Real-time task counts by status (active, queued, failed)
- Worker health (is worker 3 stuck?)
- Task duration trends (are syncs getting slower?)
- Failure rates by connector type

With ARQ, all of this is custom code.

### ARQ Resource Profile

| Resource | Usage |
|----------|-------|
| Redis memory | ~10-20 MB (queue + results) |
| Worker memory | ~100-200 MB per worker |
| Workers needed at 1,000 orgs | 10-15 (with concurrency=5-10 each) |
| Cron coordination | Manual (distributed locks) |
| Monitoring | None built-in |

### Verdict: ARQ

| Metric | Rating |
|--------|--------|
| Works at 1-10 orgs | Excellent |
| Works at 100 orgs | Good (with workarounds) |
| Works at 1,000 orgs | Possible but painful |
| Effort to build | Low |
| Effort to scale | High (reinvent many wheels) |

**ARQ is a great tool for the wrong scale.** It's like buying a Honda Civic for a delivery business. Perfect for a few deliveries a day. At 75 deliveries per hour, you need a fleet with dispatchers, and the Civic wasn't designed for fleet management.

---

## Option B: Celery + Redis + RedBeat

### Why Celery?

Celery is the **most battle-tested distributed task queue in Python**. Instagram, Stripe, Mozilla, and thousands of companies process billions of tasks per day with Celery.

It was designed from the ground up for exactly our problem: "I have thousands of background jobs, I need them executed reliably across multiple workers, with scheduling, retries, rate limiting, and monitoring."

### The Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FastAPI (API Layer)                          │
│                                                                      │
│  "The Waiter" — Takes orders, sends them to the kitchen              │
│                                                                      │
│  POST /api/sources/{id}/sync  →  sync_source.delay(source_id)       │
│  POST /api/pipelines/{id}/run →  run_pipeline.delay(pipeline_id)     │
│                                                                      │
│  Returns immediately: {"task_id": "abc123", "status": "queued"}      │
│                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                          Enqueue task
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Redis (Message Broker)                        │
│                                                                      │
│  "The Order Board" — Holds all pending tasks organized by queue      │
│                                                                      │
│  Queue: sync       [sync_org_1, sync_org_2, sync_org_3, ...]        │
│  Queue: transform  [transform_42, transform_18, ...]                 │
│  Queue: urgent     [manual_sync_org_500]                              │
│  Queue: notify     [email_org_1, slack_org_2, ...]                   │
│                                                                      │
│  RedBeat Schedules:                                                  │
│  "sync_src_001": every 1 hour    → next: 14:00                      │
│  "sync_src_002": every 15 min    → next: 13:45                      │
│  "sync_src_003": daily at 06:00  → next: tomorrow 06:00             │
│  ... (5,000 schedules)                                               │
│                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    Workers pull tasks from queues
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
┌────────────────────┐ ┌───────────────────┐ ┌───────────────────────┐
│   Worker 1         │ │   Worker 2        │ │   Worker 3            │
│   Queue: sync      │ │   Queue: sync     │ │   Queue: transform    │
│   Concurrency: 10  │ │   Concurrency: 10 │ │   Concurrency: 20    │
│                    │ │                   │ │                       │
│   "The Cook"       │ │   "Another Cook"  │ │   "The Pastry Chef"   │
│                    │ │                   │ │                       │
│   Running:         │ │   Running:        │ │   Running:            │
│   - sync_org_1     │ │   - sync_org_11   │ │   - transform_42     │
│   - sync_org_2     │ │   - sync_org_12   │ │   - transform_43     │
│   - sync_org_3     │ │   - sync_org_13   │ │   - transform_44     │
│   ...              │ │   ...             │ │   ...                 │
└────────┬───────────┘ └────────┬──────────┘ └────────┬──────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + PgBouncer                              │
│                                                                      │
│  "The Pantry" — Stores everything                                    │
│                                                                      │
│  Metadata: users, orgs, sources, sync_runs                           │
│  Raw Data: org_1.beneficiaries, org_2.health_checks, ...             │
│  Transforms: org_1.active_summary, org_2.monthly_report, ...         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### How Each Piece Solves a Problem

#### 1. Celery Workers: The Cooks

Each worker is a separate process that pulls tasks from Redis and executes them. You scale by adding more workers.

```python
# app/tasks/sync.py

from celery import shared_task

@shared_task(
    bind=True,
    queue="sync",              # Goes to sync queue only
    max_retries=3,             # Retry up to 3 times
    retry_backoff=True,        # Exponential backoff: 1s, 2s, 4s
    retry_backoff_max=300,     # Max 5 minutes between retries
    rate_limit="30/m",         # Max 30 of these tasks per minute per worker
    acks_late=True,            # Don't mark as done until actually done
    reject_on_worker_lost=True,# Re-queue if worker crashes mid-task
    soft_time_limit=300,       # Warn at 5 minutes
    time_limit=600,            # Kill at 10 minutes
)
def sync_source(self, source_id: str):
    """
    Sync a single data source using DLT.

    This runs in a Celery worker process, NOT in the API server.
    The API server is free to handle user requests.
    """
    try:
        source = get_source(source_id)
        connector = ConnectorRegistry.get(source.connector_type)

        result = connector.sync(
            config=source.config,
            resources=source.selected_resources,
            destination_url=source.organization.warehouse_url,
            schema_name=f"org_{source.organization_id}"
        )

        save_sync_result(source_id, result)
        return {"rows": result.rows_synced, "success": True}

    except GoogleAPIError as e:
        # Retry on rate limits and transient errors
        raise self.retry(exc=e)
    except Exception as e:
        save_sync_failure(source_id, str(e))
        raise
```

**The Restaurant Analogy:** Each cook works independently. If cook 1 burns a dish (task fails), they retry it without affecting cook 2 or cook 3. If cook 1 has a heart attack (worker crashes), the unfinished order goes back on the board (`acks_late=True`) for another cook to pick up.

#### 2. Task Routing: Separate Queues

```python
# celery_config.py

task_routes = {
    "app.tasks.sync.*":      {"queue": "sync"},
    "app.tasks.transform.*": {"queue": "transform"},
    "app.tasks.notify.*":    {"queue": "notify"},
}

# Start workers assigned to specific queues:
# celery -A app worker --queues=sync --concurrency=10
# celery -A app worker --queues=transform --concurrency=20
# celery -A app worker --queues=notify --concurrency=5
```

Why this matters:

```
WITHOUT routing (ARQ-style):
──────────────────────────────────────────────────────────────
Queue: [sync, sync, sync, sync, TRANSFORM, sync, sync, sync]
                                    ↑
                        Stuck behind syncs.
                        User waits 5+ minutes.

WITH routing (Celery):
──────────────────────────────────────────────────────────────
Sync queue:      [sync, sync, sync, sync, sync, sync]    → sync workers
Transform queue: [TRANSFORM]                              → transform worker
                     ↑
                 Runs immediately!
                 User sees result in seconds.
```

**The Restaurant Analogy:** Separate stations in the kitchen. The grill station (sync workers) handles steaks. The dessert station (transform workers) handles cakes. A rush on steaks doesn't delay desserts.

#### 3. RedBeat: Dynamic Scheduling

The default Celery scheduler (`celery-beat`) reads schedules from a config file. You'd have to restart the scheduler every time a user changes their sync frequency. That's unacceptable.

**RedBeat** stores schedules in Redis, making them dynamic:

```python
# When a user creates a source and sets "sync every hour":
from redbeat import RedBeatSchedulerEntry
from celery.schedules import timedelta, crontab

def create_sync_schedule(source_id: str, frequency: str):
    schedule_map = {
        "15min":   timedelta(minutes=15),
        "hourly":  timedelta(hours=1),
        "daily":   crontab(hour=6, minute=0),
    }

    entry = RedBeatSchedulerEntry(
        name=f"sync:{source_id}",
        task="app.tasks.sync.sync_source",
        schedule=schedule_map[frequency],
        args=[source_id],
        app=celery_app,
    )
    entry.save()  # Saved to Redis. Takes effect immediately.

# When user changes from hourly to daily:
def update_sync_schedule(source_id: str, frequency: str):
    entry = RedBeatSchedulerEntry.from_key(
        f"redbeat:sync:{source_id}",
        app=celery_app
    )
    entry.schedule = crontab(hour=6, minute=0)
    entry.save()  # Updated instantly. No restart needed.

# When user deletes a source:
def delete_sync_schedule(source_id: str):
    entry = RedBeatSchedulerEntry.from_key(
        f"redbeat:sync:{source_id}",
        app=celery_app
    )
    entry.delete()  # Gone. No orphan schedules.
```

With 5,000 sources, RedBeat manages 5,000 individual schedules in Redis. Each schedule is ~200 bytes. Total memory: **~1 MB**. Redis handles this trivially.

**The Restaurant Analogy:** RedBeat is a digital order board where customers can update their standing orders anytime — "Change my weekly pizza from Friday to Saturday." The kitchen sees the change instantly without a manager having to manually update the board.

#### 4. Pipeline Execution: Celery Chord + Chain

The ingestion plan says: "Sync all sources in parallel, then run transforms in dependency order." Celery has native primitives for exactly this:

```python
from celery import chord, chain, group

@shared_task(queue="sync")
def sync_source(source_id: str):
    """Sync one source. Returns sync result."""
    ...

@shared_task(queue="transform")
def run_transform(transform_id: str, previous_results=None):
    """Run one transformation. Returns transform result."""
    ...

@shared_task
def run_pipeline(pipeline_id: str):
    """
    Execute a complete pipeline:
    1. Sync all sources in parallel
    2. When ALL syncs complete, run transforms in order
    """
    pipeline = get_pipeline(pipeline_id)

    # chord = "do these in parallel, then call this callback"
    # chain = "do these one after another"

    workflow = chord(
        # Header: parallel syncs
        group(
            sync_source.s(source.id)
            for source in pipeline.sources
        ),
        # Callback: sequential transforms (after ALL syncs done)
        chain(
            run_transform.s(transform.id)
            for transform in topological_sort(pipeline.transforms)
        )
    )

    workflow.apply_async()
```

Visually:

```
chord(
    group(                          chain(
        sync_source("sheets_1"),        run_transform("clean_data"),
        sync_source("kobo_2"),    →     run_transform("join_tables"),
        sync_source("csv_3"),           run_transform("summarize"),
    ),                              )
)

Execution:
  t=0s   sync_sheets_1 ──┐
  t=0s   sync_kobo_2   ──┼── all run in parallel
  t=0s   sync_csv_3    ──┘
  t=45s  (all syncs complete)
  t=45s  clean_data ──► join_tables ──► summarize  (sequential)
  t=50s  Pipeline complete ✓
```

**The Restaurant Analogy:** A chord is like a multi-course meal. The kitchen prepares all appetizers at the same time (parallel). Only after ALL appetizers are served does the kitchen start on the main course (sequential transforms). If one appetizer fails, the whole meal is paused — you don't serve half a table.

#### 5. Rate Limiting: Don't Hammer APIs

```python
@shared_task(
    rate_limit="30/m",  # At most 30 executions per minute per worker
)
def sync_google_sheets(source_id: str):
    ...

@shared_task(
    rate_limit="50/m",  # Kobo is more generous
)
def sync_kobo(source_id: str):
    ...
```

With 5 sync workers, `rate_limit="30/m"` means 150 Google Sheets syncs per minute across all workers. Google's limit is ~100 requests per 100 seconds. You can tune this per connector type.

**The Restaurant Analogy:** The kitchen knows the oven can only cook 4 pizzas at once. Even if 50 pizza orders come in, the kitchen doesn't try to stuff 50 pizzas in the oven. It queues them and sends 4 at a time.

#### 6. Monitoring: Flower

Flower is a real-time web UI for Celery. It comes free with Celery.

```bash
# Start Flower
celery -A app flower --port=5555
```

What it shows:

```
┌──────────────────────────────────────────────────────────┐
│  Flower Dashboard                                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  WORKERS                                                 │
│  ┌────────────┬──────────┬───────────┬────────────────┐ │
│  │ Worker     │ Status   │ Active    │ Processed      │ │
│  ├────────────┼──────────┼───────────┼────────────────┤ │
│  │ sync-1     │ Online ● │ 8/10     │ 1,234          │ │
│  │ sync-2     │ Online ● │ 7/10     │ 1,198          │ │
│  │ sync-3     │ Online ● │ 10/10    │ 1,301          │ │
│  │ transform  │ Online ● │ 3/20     │ 892            │ │
│  │ notify     │ Online ● │ 1/5      │ 456            │ │
│  └────────────┴──────────┴───────────┴────────────────┘ │
│                                                          │
│  TASKS (last hour)                                       │
│  Total: 4,625  Success: 4,580  Failed: 12  Retry: 33   │
│                                                          │
│  TASK TYPES                                              │
│  sync_source:     3,200 (avg 34s, p95 120s)              │
│  run_transform:   1,100 (avg 2s, p95 8s)                 │
│  send_notification: 325 (avg 0.5s)                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

At 1,000 orgs, you'd check this daily. At a glance: are workers healthy? Are failure rates spiking? Are syncs getting slower? This is operationally critical and costs zero effort to set up.

---

## Why Not Prefect?

Since the original Dalgo product used Prefect, this deserves an explicit comparison.

### What Prefect Gives You

- Visual DAG editor
- Full pipeline observability UI
- Run history, logs, retry policies
- Deployment/scheduling management
- Artifact tracking

### What Prefect Costs You

```
┌───────────────────────────────────────────────────────────────┐
│                    PREFECT INFRASTRUCTURE                      │
│                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ Prefect      │   │ Prefect      │   │ Prefect          │ │
│  │ Server/Cloud │   │ Agent        │   │ PostgreSQL       │ │
│  │ (API + UI)   │   │ (polls for   │   │ (Prefect's own   │ │
│  │              │   │  flow runs)  │   │  metadata DB)    │ │
│  │ ~512MB RAM   │   │ ~256MB RAM   │   │ ~256MB RAM       │ │
│  └──────────────┘   └──────────────┘   └──────────────────┘ │
│                                                               │
│  Total overhead: ~1GB RAM + 3 additional containers           │
│  Complexity: Prefect deployment YAML, work pools, blocks      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### The Mismatch

Prefect excels at **complex DAGs** — pipelines with conditional branching, dynamic task generation, heterogeneous compute requirements, and cross-pipeline dependencies.

DataSense's pipeline is:

```
Step 1: Sync sources (parallel)
Step 2: Run transforms (sequential)
Done.
```

That's a 2-step linear DAG. Using Prefect for this is like hiring a **air traffic controller** to manage a **single-lane road**. The controller is world-class at coordinating 200 planes, but you just need a traffic light.

### Head-to-Head Comparison

| Dimension | Prefect | Celery + RedBeat |
|-----------|---------|-----------------|
| Infrastructure | Server + Agent + DB (3 containers) | Redis only (1 container) |
| RAM overhead | ~1 GB | ~50-100 MB (Redis) |
| DAG complexity supported | Unlimited | 2-step linear (all we need) |
| Dynamic scheduling | Work pools + deployments | RedBeat (1 line of code) |
| Learning curve | High (blocks, deployments, work pools, artifacts) | Moderate (tasks, queues, workers) |
| Monitoring | Built-in UI (excellent) | Flower (good enough) |
| Rate limiting | Custom (write your own) | Built-in decorator |
| Task routing | Possible but complex | Native queue routing |
| Vendor lock-in | Prefect Cloud or self-hosted Prefect Server | Redis (commodity, any provider) |
| Community size | Growing but smaller | Massive (15+ years, millions of users) |

### The Cost Difference

```
Prefect Cloud (managed):
  Free tier:    3 users, limited history
  Pro:          $500/month (10 users, 100K task runs)
  At 1,000 orgs: ~$2,000-5,000/month

Celery + Redis (self-hosted):
  Redis:        Free (self-hosted) or $15-50/month (managed)
  Flower:       Free
  At 1,000 orgs: $15-50/month for Redis
```

### Verdict: Prefect

Keep Prefect for the full Dalgo product where you have complex orchestration needs. For DataSense (Dalgo Lite), it's unnecessary overhead.

---

## Final Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           DATASENSE ARCHITECTURE                            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        FRONTEND (Next.js 15)                          │  │
│  │  Dashboard │ Source Setup │ Transform Editor │ Pipeline Canvas        │  │
│  └────────────────────────────────┬──────────────────────────────────────┘  │
│                                   │                                         │
│                              REST API                                       │
│                                   │                                         │
│  ┌────────────────────────────────▼──────────────────────────────────────┐  │
│  │                         API LAYER (FastAPI)                            │  │
│  │                                                                       │  │
│  │  Responsibilities:                                                    │  │
│  │  • Authenticate requests                                              │  │
│  │  • Validate input                                                     │  │
│  │  • Enqueue tasks to Celery                                            │  │
│  │  • Query results from PostgreSQL                                      │  │
│  │  • Return responses fast (< 100ms)                                    │  │
│  │                                                                       │  │
│  │  Does NOT:                                                            │  │
│  │  • Run DLT pipelines                                                  │  │
│  │  • Execute transforms                                                 │  │
│  │  • Wait for long-running operations                                   │  │
│  │                                                                       │  │
│  │  Scaling: Horizontal (add more instances behind load balancer)        │  │
│  │  Memory: ~200MB per instance                                          │  │
│  │  CPU: Minimal (I/O bound)                                             │  │
│  │                                                                       │  │
│  └────────────────────────────────┬──────────────────────────────────────┘  │
│                                   │                                         │
│                          task.delay(args)                                    │
│                                   │                                         │
│  ┌────────────────────────────────▼──────────────────────────────────────┐  │
│  │                       REDIS (Broker + Schedules)                       │  │
│  │                                                                       │  │
│  │  Queues:  sync │ transform │ urgent │ notify                          │  │
│  │  RedBeat: 5,000 dynamic schedules (~1MB)                              │  │
│  │  Results: Task results cached for 24h                                 │  │
│  │                                                                       │  │
│  │  Scaling: Vertical (more RAM) → Redis Sentinel → Redis Cluster       │  │
│  │  Memory: 50-200MB                                                     │  │
│  │  CPU: Minimal                                                         │  │
│  │                                                                       │  │
│  └───────┬──────────────────┬───────────────────┬────────────────────────┘  │
│          │                  │                   │                            │
│          ▼                  ▼                   ▼                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │  Sync Workers │  │  Transform   │  │  Notify      │                      │
│  │  (2-10)       │  │  Workers     │  │  Worker      │                      │
│  │              │  │  (1-5)       │  │  (1)         │                      │
│  │  Queue: sync │  │  Queue:      │  │  Queue:      │                      │
│  │  Concur: 10  │  │  transform   │  │  notify      │                      │
│  │              │  │  Concur: 20  │  │  Concur: 10  │                      │
│  │  Runs DLT    │  │  Runs Ibis   │  │  Sends       │                      │
│  │  pipelines   │  │  SQL via     │  │  emails,     │                      │
│  │              │  │  SQLAlchemy  │  │  Slack msgs  │                      │
│  │  ~300MB each │  │  ~200MB each │  │  ~100MB      │                      │
│  │  CPU: Medium │  │  CPU: Low    │  │  CPU: Low    │                      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                      │
│         │                 │                  │                               │
│         ▼                 ▼                  ▼                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     PostgreSQL + PgBouncer                             │  │
│  │                                                                       │  │
│  │  PgBouncer: Connection pooling (max 20 connections to PG)             │  │
│  │  PostgreSQL: Metadata + Raw Data + Transforms                         │  │
│  │                                                                       │  │
│  │  Scaling: Vertical → Read replicas → Partitioning                     │  │
│  │  Memory: 1-4 GB (shared_buffers)                                      │  │
│  │  Storage: 50-500 GB                                                   │  │
│  │  CPU: Medium (query execution)                                        │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Flower (Monitoring Dashboard)                       │  │
│  │                                                                       │  │
│  │  Port: 5555                                                           │  │
│  │  Workers, tasks, queues, success rates — all real-time                │  │
│  │  Memory: ~100MB                                                       │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Docker Compose (Development & Small Deployment)

```yaml
services:
  # API Server
  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8057
    ports: ["8057:8057"]
    depends_on: [redis, postgres]
    environment:
      - DATABASE_URL=postgresql+asyncpg://datasense:datasense@postgres:5432/datasense
      - REDIS_URL=redis://redis:6379/0

  # Celery Sync Workers (scale this: docker-compose up --scale sync-worker=5)
  sync-worker:
    build: ./backend
    command: celery -A app.celery_app worker --queues=sync --concurrency=10 -n sync@%h
    depends_on: [redis, postgres]
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"

  # Celery Transform Worker
  transform-worker:
    build: ./backend
    command: celery -A app.celery_app worker --queues=transform --concurrency=20 -n transform@%h
    depends_on: [redis, postgres]
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"

  # RedBeat Scheduler (only ONE instance — it's the clock)
  scheduler:
    build: ./backend
    command: celery -A app.celery_app beat -S redbeat.RedBeatScheduler
    depends_on: [redis]
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"

  # Monitoring
  flower:
    build: ./backend
    command: celery -A app.celery_app flower --port=5555
    ports: ["5555:5555"]
    depends_on: [redis]

  # Infrastructure
  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]
    deploy:
      resources:
        limits:
          memory: 256M

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: datasense
      POSTGRES_USER: datasense
      POSTGRES_PASSWORD: datasense
    volumes: ["pg_data:/var/lib/postgresql/data"]
    deploy:
      resources:
        limits:
          memory: 1G

  # Frontend
  frontend:
    build: ./frontend
    ports: ["3000:3000"]

volumes:
  redis_data:
  pg_data:
```

---

## Scaling Playbook

### Stage 1: Launch (1-50 orgs)

```
Containers: 6
  api (1)           — 200MB RAM, 0.5 CPU
  sync-worker (1)   — 300MB RAM, 1.0 CPU (concurrency=5)
  transform-worker  — 200MB RAM, 0.5 CPU
  scheduler (1)     — 128MB RAM, 0.25 CPU
  redis (1)         — 100MB RAM
  postgres (1)      — 512MB RAM

Total: ~1.4 GB RAM, 2.25 CPU cores
Hosting: Single $20-40/month VPS (4GB RAM, 2 vCPU)
Syncs/hour capacity: ~300

Monitoring: Check Flower weekly. Watch for failed tasks.
```

**What you're watching for:**
- Sync queue depth > 50 consistently → need more sync workers
- API response time > 500ms → need another API instance
- PostgreSQL connections > 80% of max → add PgBouncer

### Stage 2: Growing (50-200 orgs)

```
Changes:
  + sync-worker (2nd instance)     — handles burst load
  + PgBouncer                      — connection pooling
  + Redis persistence (AOF)        — don't lose schedules on restart

Containers: 8
Total: ~2.5 GB RAM, 4 CPU cores
Hosting: $40-80/month VPS (8GB RAM, 4 vCPU) or 2 small VMs
Syncs/hour capacity: ~1,200
```

**The Restaurant Analogy:** You hired a second cook and installed a ticket printer (PgBouncer) so cooks don't have to walk to the order board. The restaurant is humming.

### Stage 3: Scaling (200-500 orgs)

```
Changes:
  + API instance (2nd, behind nginx)
  + sync-worker (3rd, 4th instances)
  + Dedicated notification worker
  + Redis Sentinel (high availability)
  + Postgres: increase shared_buffers to 2GB

Containers: 12
Total: ~5 GB RAM, 8 CPU cores
Hosting: $100-200/month or small Kubernetes cluster
Syncs/hour capacity: ~3,000
```

**What changes operationally:**
- You start caring about Google Sheets API rate limits
- Stagger sync schedules (don't fire 500 syncs at exactly :00)
- Add alerting: if failure rate > 5%, page someone

### Stage 4: At Scale (500-1,000 orgs)

```
Changes:
  + sync-workers (5-10 instances)
  + transform-workers (2-3 instances)
  + API instances (3-4)
  + PostgreSQL read replica (for API queries)
  + Proper load balancer (nginx or cloud LB)
  + Priority queues (premium orgs get faster syncs)

Containers: 20-25
Total: ~12-16 GB RAM, 16-20 CPU cores
Hosting: Kubernetes (EKS/GKE) or 4-5 VMs
  - 3 workers VMs × 4GB RAM each
  - 1 API/scheduler VM × 4GB RAM
  - 1 DB VM × 8GB RAM (or managed RDS)
Syncs/hour capacity: ~6,000+

Monthly cost: $200-500 (self-managed) or $500-800 (managed services)
```

**New operational concerns:**
- **Database size:** At 500 orgs × 200MB avg = 100GB of data. Need to monitor disk.
- **PgBouncer tuning:** Set `max_client_conn=200`, `default_pool_size=20`.
- **Worker auto-scaling:** With Kubernetes HPA, scale workers based on queue depth:

```yaml
# Kubernetes HPA for sync workers
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sync-worker-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: sync-worker
  minReplicas: 2
  maxReplicas: 15
  metrics:
    - type: External
      external:
        metric:
          name: celery_queue_length
          selector:
            matchLabels:
              queue: sync
        target:
          type: AverageValue
          averageValue: "50"  # Scale up when >50 tasks queued per worker
```

### Stage 5: Beyond (1,000+ orgs)

| Component | Scaling Strategy |
|-----------|-----------------|
| API | Horizontal + CDN for static assets |
| Sync Workers | Kubernetes HPA based on queue depth |
| Transform Workers | Kubernetes HPA based on queue depth |
| Redis | Redis Cluster (3+ nodes) or managed (ElastiCache) |
| PostgreSQL | Managed (RDS/Cloud SQL) + read replicas + table partitioning by org |
| PgBouncer | Sidecar pattern (one per API/worker pod) |
| Monitoring | Prometheus + Grafana (replace or supplement Flower) |

---

## Component Deep Dives

### DLT Pipeline State: The Gotcha

DLT tracks incremental loading state — "I last synced this Google Sheet at row 1,234." By default, it stores this on the **local filesystem** in a `.dlt/` directory.

**The Problem at Scale:**

```
Worker 1 syncs source A → saves state to Worker 1's disk
Worker 2 syncs source A next time → doesn't see Worker 1's state → FULL RE-SYNC
```

This means every sync re-downloads all data instead of just new rows. At 1,000 orgs, you'd be transferring terabytes of redundant data.

**The Fix:**

DLT stores state in the destination database when using a database destination. The state goes into `_dlt_pipeline_state` table in the target schema. Since all workers write to the same PostgreSQL, they all see the same state.

```python
# This automatically stores state in PostgreSQL (no local filesystem)
pipeline = dlt.pipeline(
    pipeline_name=f"source_{source_id}",
    destination=dlt.destinations.postgres(warehouse_url),
    dataset_name=f"org_{org_id}",
)
# State stored in: org_{org_id}._dlt_pipeline_state
```

Verify this is working by checking:
```sql
SELECT * FROM org_1._dlt_pipeline_state;
-- Should show incremental cursors and schema version
```

### PgBouncer: Why You Need It

PostgreSQL creates **one process per connection**. Each process uses ~10MB of RAM.

```
Without PgBouncer:
  10 sync workers × 10 concurrency = 100 connections
  + 3 API instances × 5 connections = 15 connections
  + scheduler, flower, etc. = 10 connections
  Total: 125 connections × ~10MB = 1.25 GB just for connection overhead

With PgBouncer (transaction pooling):
  All workers connect to PgBouncer → PgBouncer maintains 20 actual PG connections
  20 connections × ~10MB = 200 MB
  Savings: 1 GB of RAM
```

**The Restaurant Analogy:** Without PgBouncer, every waiter has their own dedicated window to the kitchen. With 100 waiters, you need 100 windows. PgBouncer is a single counter where waiters line up and take turns using 20 windows — much more efficient.

### Redis Memory: What Actually Gets Stored

```
Item                          Count     Size Each    Total
──────────────────────────────────────────────────────────
RedBeat schedules             5,000     ~200 bytes   ~1 MB
Queued tasks (peak)           500       ~1 KB        ~500 KB
Task results (24h retention)  10,000    ~500 bytes   ~5 MB
Redis overhead                                       ~20 MB
──────────────────────────────────────────────────────────
Total:                                               ~27 MB
```

Redis with 256 MB is more than enough for 1,000 orgs. You won't hit memory pressure here unless something is leaking (e.g., results not being cleaned up).

---

## Deep Dive: DLT State Problem

### What "state" are we talking about?

When DLT syncs a Google Sheet with 10,000 rows, the first sync fetches all 10,000. The second sync should only fetch new rows (say, rows 10,001-10,050). To do that, DLT needs to remember: **"I already synced up to row 10,000"** or **"I last synced at timestamp 2026-02-07T14:00:00"**.

This is called **incremental loading state** — a cursor that marks "where I left off."

DLT also tracks:
- **Schema version** — what columns existed last time (to detect changes)
- **Schema hash** — fingerprint to quickly detect if anything changed
- **Load metadata** — which load IDs succeeded, for deduplication

### Where DLT stores state — two places

```
┌────────────────────────────────────────────────────────────┐
│                    DLT State Storage                        │
│                                                            │
│   PLACE 1: Local Filesystem (fast, ephemeral)              │
│   ──────────────────────────────────────────                │
│   ~/.dlt/pipelines/<pipeline_name>/                        │
│   ├── state/                                               │
│   │   └── pipeline_state.json    ← incremental cursors     │
│   ├── schemas/                                             │
│   │   ├── extracted.schema.json  ← what DLT saw from API   │
│   │   └── normalized.schema.json ← what DLT wrote to DB    │
│   └── trace/                                               │
│       └── trace.json             ← execution metadata      │
│                                                            │
│   PLACE 2: Destination Database (slow, durable)            │
│   ──────────────────────────────────────────                │
│   org_1._dlt_pipeline_state     ← same cursors, in PG      │
│   org_1._dlt_version            ← schema version + hash    │
│   org_1._dlt_loads              ← load history              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### The lifecycle of a sync

```
pipeline.run(source) internally does:

Step 1: "Do I have local state?"
        ├── YES → Use local cursor (fast, no DB query)
        └── NO  → "Do I have state in destination DB?"
                  ├── YES → Download it, save locally, use it
                  └── NO  → This is a fresh sync, fetch everything

Step 2: Extract data (using cursor to fetch only new rows)
Step 3: Normalize data (flatten JSON, infer types)
Step 4: Load into destination DB

Step 5: Update state in BOTH places:
        ├── Write new cursor to local filesystem
        └── Write new cursor to _dlt_pipeline_state table in DB
```

### Why this breaks with multiple workers

**The analogy:** Imagine a library with two librarians (workers). Each librarian has their own personal notebook (local filesystem) where they write "I shelved books up to #500." The library also has an official logbook (database) at the front desk.

```
┌─────────────────────────────────────────────────────────────────┐
│                     SINGLE WORKER (works fine)                   │
│                                                                 │
│   Worker 1's disk:                                              │
│   cursor = "2026-02-07T14:00:00"                                │
│                                                                 │
│   Run 1: Fetch all data              → cursor = 14:00           │
│   Run 2: Fetch data since 14:00      → cursor = 15:00  ✓       │
│   Run 3: Fetch data since 15:00      → cursor = 16:00  ✓       │
│                                                                 │
│   Local state is always up-to-date because the same worker      │
│   runs every time.                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  MULTIPLE WORKERS (breaks)                       │
│                                                                 │
│   Worker 1's disk: cursor = "2026-02-07T14:00:00"               │
│   Worker 2's disk: (empty — never synced this source before)    │
│   Worker 3's disk: (empty)                                      │
│                                                                 │
│   Run 1 (Worker 1): Fetch all data              → cursor = 14:00│
│   Run 2 (Worker 2): "I have no local state..."                  │
│                      → Falls back to DB state   → cursor = 14:00│
│                      → Fetch since 14:00        → cursor = 15:00│
│   Run 3 (Worker 1): Local cursor says 14:00 (STALE!)           │
│                      → Fetches 14:00-16:00 AGAIN                │
│                      → Duplicate data inserted ✗                │
│                                                                 │
│   The problem: Worker 1's local cache is stale because          │
│   Worker 2 advanced the cursor in the DB but Worker 1           │
│   doesn't know.                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Library analogy expanded:** Librarian A writes in their notebook "shelved up to book #500." Librarian B checks the official logbook, sees #500, shelves up to #600, updates the official logbook. Next day, Librarian A looks at their personal notebook — it still says #500. They re-shelve books #500-#600 that were already done.

### The solution: `pipeline.sync_destination()`

Force DLT to skip its local cache and always read state from the destination DB before running:

```python
pipeline = dlt.pipeline(
    pipeline_name=f"source_{source_id}",
    destination=dlt.destinations.postgres(warehouse_url),
    dataset_name=f"org_{org_id}",
)

# CRITICAL: Always sync state FROM the destination DB.
# This forces DLT to overwrite stale local state with the
# source-of-truth from PostgreSQL.
pipeline.sync_destination()

# Now run — cursor is guaranteed fresh, regardless of which worker this is
load_info = pipeline.run(source)
```

What `sync_destination()` does:

```
Step 1: Connect to destination PostgreSQL
Step 2: Read _dlt_pipeline_state table
Step 3: OVERWRITE local state files with DB values
Step 4: Now local state = DB state (guaranteed)
```

```
┌─────────────────────────────────────────────────────────────────┐
│              WITH sync_destination() — FIXED                     │
│                                                                 │
│   Run 1 (Worker 1):                                             │
│     sync_destination() → DB state: empty → fresh sync           │
│     Fetch all data → cursor = 14:00                             │
│     Save to DB: cursor = 14:00                                  │
│                                                                 │
│   Run 2 (Worker 2):                                             │
│     sync_destination() → DB state: cursor = 14:00               │
│     Overwrites Worker 2's local state with 14:00                │
│     Fetch since 14:00 → cursor = 15:00                          │
│     Save to DB: cursor = 15:00                                  │
│                                                                 │
│   Run 3 (Worker 1):                                             │
│     sync_destination() → DB state: cursor = 15:00               │
│     Overwrites Worker 1's STALE 14:00 with 15:00 from DB        │
│     Fetch since 15:00 → cursor = 16:00  ✓  NO DUPLICATES       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### The complete Celery task with DLT state handling

```python
from celery import shared_task
from redis import Redis

redis_client = Redis.from_url(REDIS_URL)

@shared_task(bind=True, queue="sync", acks_late=True)
def sync_source(self, source_id: str):
    # Prevent concurrent syncs of the same source
    lock_key = f"sync_lock:{source_id}"
    acquired = redis_client.set(lock_key, "1", nx=True, ex=600)

    if not acquired:
        return {"skipped": True, "reason": "sync already in progress"}

    try:
        source = get_source(source_id)
        connector = ConnectorRegistry.get(source.connector_type)

        pipeline = dlt.pipeline(
            pipeline_name=f"source_{source_id}",
            destination=dlt.destinations.postgres(source.warehouse_url),
            dataset_name=f"org_{source.organization_id}",
        )

        # CRITICAL: Sync state from DB before running
        pipeline.sync_destination()

        dlt_source = connector.create_dlt_source(
            config=source.config,
            resources=source.selected_resources,
        )

        load_info = pipeline.run(dlt_source)

        return {
            "rows": load_info.metrics.get("rows_total", 0),
            "success": not load_info.has_failed_jobs,
        }
    finally:
        redis_client.delete(lock_key)
```

The Redis lock (`nx=True, ex=600`) prevents two workers from syncing the same source simultaneously. `nx=True` means "set only if not exists" (atomic). `ex=600` means the lock auto-expires after 10 minutes (safety net if a worker crashes without releasing).

---

## Deep Dive: What Actually Scales

### API vs Workers — Two Independent Bottlenecks

Your "app" is actually **three different programs** sharing the same codebase:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SAME CODEBASE, DIFFERENT ROLES                      │
│                                                                         │
│   $ uvicorn app.main:app             ← PROGRAM 1: API Server            │
│     "I handle HTTP requests"                                            │
│     "I validate, authenticate, query DB, return JSON"                   │
│     "I enqueue tasks but NEVER execute them"                            │
│     "I respond in < 100ms"                                              │
│                                                                         │
│   $ celery -A app worker -Q sync     ← PROGRAM 2: Sync Worker          │
│     "I pull tasks from Redis and execute DLT pipelines"                 │
│     "I talk to Google Sheets, Kobo APIs"                                │
│     "I write data to PostgreSQL"                                        │
│     "Each task takes 30-60 seconds"                                     │
│                                                                         │
│   $ celery -A app beat -S redbeat    ← PROGRAM 3: Scheduler            │
│     "I check which syncs are due"                                       │
│     "I enqueue tasks at the right time"                                 │
│     "I don't execute anything myself"                                   │
│     "There's only ONE of me"                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

These run on separate machines (or containers) and scale **independently**:

```
                    HTTP traffic                      Sync workload
                    (user clicks)                     (background DLT)
                         │                                  │
         ┌───────────────┼───────────────┐    ┌────────────┼────────────┐
         │               │               │    │            │            │
         ▼               ▼               ▼    ▼            ▼            ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │ API #1  │    │ API #2  │    │ API #3  │ │Worker 1│ │Worker 2│ │Worker 3│
    └─────────┘    └─────────┘    └─────────┘ └────────┘ └────────┘ └────────┘

    Scale when:                               Scale when:
    ALB latency > 200ms                       Redis queue depth > 100
    HTTP 5xx rate > 1%                        Sync delay > 10 minutes
```

**The analogy:** Waiters (API) and cooks (workers) scale independently. A packed dining room with simple orders? Hire more waiters. Complex dishes but empty dining room? Hire more cooks. You never hire waiters to cook faster.

### Why concurrency=10 works (IO-bound tasks)

A DLT sync is 89% waiting, 11% computing:

```
DLT sync timeline for ONE task:

0ms    ─── Send HTTP request to Google Sheets ──────────┐
                                                         │ WAITING (CPU idle)
300ms  ─── Response received ◄──────────────────────────┘
300ms  ─── Parse 1,000 rows of JSON ──┐
                                       │ CPU ACTIVE
350ms  ─── Done parsing ◄─────────────┘
350ms  ─── Send HTTP request for next page ─────────────┐
                                                         │ WAITING (CPU idle)
650ms  ─── Response received ◄──────────────────────────┘
650ms  ─── Parse next 1,000 rows ──┐
                                    │ CPU ACTIVE
700ms  ─── Done ◄─────────────────┘
700ms  ─── Write batch to PostgreSQL ───────────────────┐
                                                         │ WAITING (CPU idle)
900ms  ─── Write confirmed ◄────────────────────────────┘

Total: 900ms elapsed. CPU active: ~100ms (11%).
```

With concurrency=10 on one worker:

```
Time     CPU working on:             Meanwhile waiting:
0ms      Task 1 (parsing JSON)       Tasks 2-10 (HTTP wait)
50ms     Task 3 (parsing JSON)       Tasks 1,2,4-10 (HTTP wait)
100ms    Task 5 (parsing JSON)       Rest waiting
150ms    Task 7 (DB write setup)     Rest waiting

CPU utilization: ~60-80% (healthy)
Instead of 11% with single task (wasteful)
```

**The analogy:** A cook can watch 10 pots on the stove. Each pot is simmering 89% of the time (IO wait). The cook stirs one pot (CPU work), moves to the next. Running only 1 pot at a time wastes 89% of the cook's attention.

---

## Deep Dive: Connection Pooling

### How PostgreSQL handles connections (the expensive truth)

Unlike MySQL (threads), **PostgreSQL creates one OS process per connection**:

```
┌───────────────────────────────────────────────────────────┐
│                    POSTGRESQL SERVER                       │
│                                                           │
│  Main process (postmaster) — listens for connections      │
│       │                                                   │
│       ├── Fork → Backend Process #1 (from API)            │
│       │          RAM: ~10MB (shared_buffers + work_mem)    │
│       │          State: idle (waiting for query)           │
│       │                                                   │
│       ├── Fork → Backend Process #2 (from API)            │
│       │          RAM: ~10MB                                │
│       │          State: executing SELECT                   │
│       │                                                   │
│       ├── Fork → Backend Process #3 (from Worker)         │
│       │          RAM: ~15MB (large INSERT buffer)          │
│       │          State: executing COPY                     │
│       │                                                   │
│       ...                                                 │
│       └── Fork → Backend Process #100                     │
│                  RAM: ~10MB                                │
│                  State: idle                               │
│                                                           │
│  Total RAM: 100 × ~10MB = 1 GB (mostly idle, wasted)     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### The math at 1,000 orgs (without PgBouncer)

```
API instances (3 × pool_size=10):           30 connections
Sync workers (5 × concurrency=10):         50 connections  (DLT opens its own)
Transform workers (2 × concurrency=20):    40 connections
Scheduler + Flower + misc:                  5 connections
─────────────────────────────────────────────────────────
TOTAL:                                    125 connections

PostgreSQL default max_connections = 100 → CONNECTION REFUSED ✗

Increase to max_connections = 200:
  200 × ~10MB = 2 GB RAM just for connection overhead
  On a 4GB server: 2GB connections + 1GB shared_buffers + 0.5GB OS
  = 0.5GB left for actual query execution → OOM on complex JOINs ✗
```

### PgBouncer: The multiplexer

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   API #1 ────┐                                                   │
│   API #2 ────┤                                                   │
│   API #3 ────┤     ┌──────────────────┐     ┌──────────────────┐ │
│              ├────▶│    PgBouncer     │────▶│   PostgreSQL      │ │
│   Worker 1 ──┤     │                  │     │                  │ │
│   Worker 2 ──┤     │  125 incoming    │     │  20 actual       │ │
│   Worker 3 ──┤     │  connections     │     │  connections     │ │
│   Worker 4 ──┤     │  (~2KB each)     │     │  (~10MB each)    │ │
│   Worker 5 ──┘     │                  │     │                  │ │
│                    └──────────────────┘     └──────────────────┘ │
│                                                                  │
│   PgBouncer RAM:   125 × 2KB = 250KB (negligible)               │
│   PostgreSQL RAM:  20 × 10MB = 200MB (instead of 1.25GB)        │
│   RAM SAVED:       ~1 GB → goes to shared_buffers (data cache)  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Transaction pooling — how it works

PgBouncer's `pool_mode = transaction` means a real PG connection is borrowed ONLY during a transaction:

```
t=0ms   Client A: BEGIN     → borrows PG conn #1
t=5ms   Client A: SELECT... → uses PG conn #1
t=10ms  Client A: COMMIT    → returns PG conn #1 to pool

t=11ms  Client B: BEGIN     → borrows PG conn #1 (SAME connection!)
t=15ms  Client B: INSERT... → uses PG conn #1
t=20ms  Client B: COMMIT    → returns PG conn #1 to pool

At any instant, only ~20 of 125 clients are mid-transaction.
The rest are idle (waiting for next API request, waiting for DLT
to fetch data from Google, etc.) — they don't need a PG connection.
```

**The analogy:** Transaction pooling is like **hotel rooms billed by the hour**. Without PgBouncer: 125 guests each rent a room 24/7, even though they only sleep 8 hours. Need 125 rooms. With PgBouncer: guests get a room only when sleeping. 20 rooms serve 125 guests because only ~20 sleep at once.

### The performance impact — real numbers

```
WITHOUT PgBouncer (4GB server):                WITH PgBouncer (same 4GB server):
─────────────────────────────                  ──────────────────────────────────
Connection RAM: 125×10MB = 1,250 MB            PgBouncer:        50 MB
shared_buffers:             1,024 MB            Connection RAM: 20×10MB = 200 MB
OS:                           512 MB            shared_buffers:         2,048 MB ← 2x more!
Query execution:              250 MB            OS:                       512 MB
─────────────────────────────                  Query execution:        1,200 MB
Data cache:                ~0 MB ← BAD         ──────────────────────────────────
                                                Data cache:           2 GB ← hot data in RAM

Queries hitting disk: ~10ms per read            Queries hitting cache: ~0.1ms per read
                                                → 100x faster for frequent queries
```

### PgBouncer configuration for DataSense

```ini
; /etc/pgbouncer/pgbouncer.ini

[databases]
datasense = host=postgres-host port=5432 dbname=datasense

[pgbouncer]
max_client_conn = 300        ; Accept up to 300 app connections
default_pool_size = 20       ; Maintain 20 real PG connections
reserve_pool_size = 5        ; 5 extra for burst traffic
pool_mode = transaction      ; Borrow connection only during transaction
server_idle_timeout = 600    ; Close idle PG connections after 10 min
listen_port = 6432           ; Convention: PgBouncer on 6432
listen_addr = 0.0.0.0
```

App connection strings change to point at PgBouncer:

```python
# FastAPI / SQLAlchemy
DATABASE_URL = "postgresql+asyncpg://user:pass@pgbouncer:6432/datasense"

# DLT (uses its own connection)
DLT_DESTINATION_URL = "postgresql://user:pass@pgbouncer:6432/datasense"
```

---

## Cost & Resource Estimates

### Monthly Hosting Cost by Scale

| Scale | Self-Hosted (VPS) | Managed Services (AWS/GCP) |
|-------|-------------------|---------------------------|
| 1-50 orgs | $20-40/mo (single 4GB VPS) | $80-120/mo (smallest RDS + EC2) |
| 50-200 orgs | $40-80/mo (8GB VPS or 2 VMs) | $150-250/mo |
| 200-500 orgs | $100-200/mo (3-4 VMs) | $300-500/mo |
| 500-1,000 orgs | $200-500/mo (Kubernetes or 5+ VMs) | $500-1,000/mo |
| 1,000+ orgs | $500-1,000/mo | $1,000-2,000/mo |

### Resource Budget Per Component

| Component | RAM | CPU | Instances | Notes |
|-----------|-----|-----|-----------|-------|
| FastAPI | 200MB | 0.5 | 1-4 | Stateless, scale freely |
| Sync Worker | 300-500MB | 1.0 | 2-10 | Main scaling target |
| Transform Worker | 200MB | 0.5 | 1-3 | Light (SQL pushdown) |
| Scheduler (RedBeat) | 128MB | 0.25 | 1 | Only one instance |
| Flower | 100MB | 0.25 | 1 | Optional in prod |
| Redis | 50-256MB | 0.25 | 1 | Rarely the bottleneck |
| PgBouncer | 50MB | 0.1 | 1 | Add at 100+ orgs |
| PostgreSQL | 1-4GB | 1-4 | 1 | Vertical first, then replicas |

### CPU Breakdown: Where Does Compute Go?

```
At 1,000 orgs, processing 75 syncs/minute:

DLT Sync (per sync):
  HTTP requests to source API:    ~5-30 seconds  (IO-bound, waiting)
  Data parsing/type inference:    ~2-5 seconds   (CPU-bound)
  Write to PostgreSQL:            ~3-10 seconds  (IO-bound)
  Total per sync:                 ~10-45 seconds

Ibis Transform (per transform):
  Recipe → Ibis expression:       ~10ms          (CPU, negligible)
  Ibis → SQL compilation:         ~20ms          (CPU, negligible)
  SQL execution in PostgreSQL:    ~0.5-5 seconds (DB-bound)
  Total per transform:            ~0.5-5 seconds

The sync workers are the bottleneck. They spend most time waiting for IO,
so high concurrency (10 per worker) is efficient. Transforms are fast
because the heavy lifting happens in PostgreSQL, not in Python.
```

---

## Failure Modes & Recovery

### Scenario 1: Worker Crashes Mid-Sync

```
t=0s   Worker 1 picks up sync_source("src_123")
t=15s  Worker 1 crashes (OOM, hardware failure, deployment)
t=16s  Celery detects worker lost (via heartbeat)
t=16s  Task re-queued (because acks_late=True + reject_on_worker_lost=True)
t=17s  Worker 2 picks up sync_source("src_123")
t=45s  Sync completes successfully ✓
```

**User sees:** "Syncing..." for a bit longer than usual. No data loss. No manual intervention.

**Without acks_late:** The task is marked as "done" when the worker picks it up. If the worker crashes, the task is lost forever. Data never syncs. User has to manually trigger a re-sync.

### Scenario 2: Google Sheets API Rate Limit

```
t=0s   50 sync tasks fire simultaneously
t=2s   First 30 succeed
t=3s   Next 20 get HTTP 429 (rate limited)
t=3s   Celery retries with exponential backoff:
         Retry 1: wait 4 seconds
         Retry 2: wait 8 seconds
         Retry 3: wait 16 seconds
t=35s  All retries succeed ✓
```

**User sees:** A slight delay. Sync history shows "completed" with no error.

### Scenario 3: Redis Goes Down

```
t=0s   Redis crashes
t=0s   New API requests fail to enqueue → API returns 503
t=0s   Workers lose connection → stop pulling tasks
t=0s   Scheduled syncs stop firing
t=5m   Redis restarts (with AOF persistence)
t=5m   All schedules restored from disk
t=5m   Workers reconnect automatically
t=5m   Pending tasks in queues restored
t=6m   Everything back to normal ✓
```

**User sees:** A 5-minute window where syncs don't run and manual triggers fail. After Redis is back, everything resumes. No data loss.

**Mitigation:** Redis Sentinel (automatic failover) reduces downtime to ~10 seconds.

### Scenario 4: PostgreSQL Connection Exhaustion

```
t=0s   100 sync tasks running, each holding a DB connection
t=0s   PostgreSQL max_connections = 100 (default)
t=1s   New connection attempt → "FATAL: too many connections" ✗
```

**Fix:** PgBouncer in transaction pooling mode. Workers connect to PgBouncer (unlimited connections), PgBouncer maintains 20 actual PG connections and multiplexes.

### Scenario 5: One Org's Data Is Corrupted

```
t=0s   Org 42's Google Sheet has invalid data (text in number column)
t=1s   DLT sync detects type mismatch
t=1s   DLT creates variant column: age__v_text (keeps original age column)
t=2s   Schema change detected → saved to schema_changes table
t=2s   User notified: "Your data structure changed. [Review]"
t=2s   Other orgs' syncs continue unaffected ✓
```

**Key insight:** Each org's sync is an independent task. One org's failure NEVER affects another org. This is the beauty of task isolation.

**The Restaurant Analogy:** If one customer's steak is undercooked, the cook re-makes that steak. They don't throw away everyone else's food.

---

## Summary: Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Task execution | Celery | Battle-tested at our target scale, horizontal scaling, task routing, rate limiting |
| Message broker | Redis | Lightweight, fast, doubles as RedBeat storage |
| Scheduling | RedBeat | Dynamic schedules via API, stored in Redis, no restarts needed |
| Pipeline orchestration | Celery chord + chain | Native primitives for parallel→sequential execution |
| Connection pooling | PgBouncer | Reduces PG connection overhead from GB to MB |
| Monitoring | Flower | Free, zero-config, sufficient for operations |
| NOT using | Prefect | Overkill for 2-step linear DAG, adds 1GB overhead + 3 containers |
| NOT using | ARQ | No task routing, cron duplication issues, limited observability at scale |
| NOT using | In-process (APScheduler) | Blocks API workers, no horizontal scaling, no task isolation |

---

*Document maintained by: DataSense Engineering*
*Last updated: February 2026*
*Next review: When approaching 500 orgs*
