#!/usr/bin/env python3
"""
seed_demo.py — Populate Membread with 50 rich demo episodes.
================================================================

Generates a realistic timeline of events spanning ~18 months across
multiple entities (people, projects, companies) so the dashboard,
temporal search, and entity history features have meaningful data
to showcase.

Usage:
    # Against a running API server
    python scripts/seed_demo.py

    # Custom API base / JWT token
    MEMBREAD_API=http://localhost:8000 MEMBREAD_TOKEN=<jwt> python scripts/seed_demo.py

    # Direct engine mode (no server needed)
    python scripts/seed_demo.py --direct
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─────────────────────────────────────────────────────────────────────
# 50 demo episodes
# ─────────────────────────────────────────────────────────────────────

_T0 = datetime(2023, 7, 1, 9, 0, 0, tzinfo=timezone.utc)


def _ts(days: int, hours: int = 0) -> str:
    return (_T0 + timedelta(days=days, hours=hours)).isoformat()


EPISODES: list[dict] = [
    # ── Alice's career journey ───────────────────────────────────────
    {"text": "Alice joined Google as a software engineer in Mountain View.",       "ts": _ts(0),     "source": "linkedin"},
    {"text": "Alice is working on the Google Search ranking team.",                "ts": _ts(14),    "source": "slack"},
    {"text": "Alice completed her first quarter OKRs with exceeds expectations.",  "ts": _ts(90),    "source": "hr_system"},
    {"text": "Alice presented at Google I/O on next-gen search features.",         "ts": _ts(120),   "source": "calendar"},
    {"text": "Alice received a promotion to Senior Software Engineer at Google.",  "ts": _ts(180),   "source": "hr_system"},
    {"text": "Alice started interviewing at Meta for a Staff Engineer role.",      "ts": _ts(270),   "source": "email"},
    {"text": "Alice accepted an offer from Meta and resigned from Google.",        "ts": _ts(300),   "source": "hr_system"},
    {"text": "Alice joined Meta as Staff Engineer on the Llama team.",             "ts": _ts(330),   "source": "linkedin"},
    {"text": "Alice relocated from Mountain View to Menlo Park.",                  "ts": _ts(335),   "source": "slack"},
    {"text": "Alice published a paper on efficient LLM inference at Meta.",        "ts": _ts(400),   "source": "arxiv"},

    # ── Bob's tech stack evolution ───────────────────────────────────
    {"text": "Bob's favourite programming language is Python.",                     "ts": _ts(0),     "source": "survey"},
    {"text": "Bob started learning Rust through the Rust Book.",                   "ts": _ts(60),    "source": "github"},
    {"text": "Bob contributed his first PR to the Tokio async runtime.",           "ts": _ts(120),   "source": "github"},
    {"text": "Bob switched his primary language from Python to Rust.",             "ts": _ts(200),   "source": "blog"},
    {"text": "Bob gave a talk at RustConf 2024 on async patterns.",                "ts": _ts(250),   "source": "conference"},
    {"text": "Bob released an open-source Rust crate for temporal graphs.",        "ts": _ts(310),   "source": "github"},

    # ── Project Phoenix ──────────────────────────────────────────────
    {"text": "Project Phoenix was created as an internal ML platform.",             "ts": _ts(10),    "source": "jira"},
    {"text": "Phoenix v0.1 released with basic model training pipeline.",           "ts": _ts(45),    "source": "release_notes"},
    {"text": "Phoenix team adopted Kubernetes for orchestration.",                  "ts": _ts(80),    "source": "slack"},
    {"text": "Phoenix added support for distributed training on 8 GPUs.",          "ts": _ts(130),   "source": "pr"},
    {"text": "Project Phoenix was renamed to Falcon for trademark reasons.",        "ts": _ts(200),   "source": "announcement"},
    {"text": "Falcon v1.0 released with multi-cloud support.",                     "ts": _ts(260),   "source": "release_notes"},
    {"text": "Falcon team expanded from 5 to 12 engineers.",                       "ts": _ts(310),   "source": "hr_system"},
    {"text": "Falcon achieved SOC2 compliance certification.",                     "ts": _ts(370),   "source": "audit"},

    # ── Infrastructure & DevOps ──────────────────────────────────────
    {"text": "Carol was hired as Head of Infrastructure.",                          "ts": _ts(5),     "source": "hr_system"},
    {"text": "The infrastructure team migrated from AWS EC2 to EKS.",              "ts": _ts(40),    "source": "jira"},
    {"text": "Carol implemented a GitOps workflow with ArgoCD.",                    "ts": _ts(75),    "source": "pr"},
    {"text": "Monthly cloud spending reduced from $45k to $28k after optimisation.", "ts": _ts(110),  "source": "finance"},
    {"text": "Carol's team adopted Terraform for infrastructure-as-code.",          "ts": _ts(150),   "source": "confluence"},
    {"text": "The team set up Prometheus + Grafana for observability.",              "ts": _ts(190),   "source": "pr"},
    {"text": "99.99% uptime achieved for the first time in Q3 2024.",               "ts": _ts(240),   "source": "status_page"},

    # ── Data & analytics ─────────────────────────────────────────────
    {"text": "Dave joined as a data engineer working on the warehouse.",             "ts": _ts(30),    "source": "hr_system"},
    {"text": "Migrated the data warehouse from Redshift to BigQuery.",               "ts": _ts(100),   "source": "jira"},
    {"text": "Dave built a real-time streaming pipeline using Apache Flink.",         "ts": _ts(160),   "source": "pr"},
    {"text": "The analytics dashboard was rebuilt with Streamlit.",                   "ts": _ts(210),   "source": "demo"},
    {"text": "Dave introduced dbt for data transformation and testing.",              "ts": _ts(280),   "source": "confluence"},

    # ── Team & culture ───────────────────────────────────────────────
    {"text": "The engineering team grew from 15 to 35 people in 2024.",              "ts": _ts(365),   "source": "hr_system"},
    {"text": "The company adopted a 4-day work week policy.",                        "ts": _ts(140),   "source": "announcement"},
    {"text": "Quarterly hackathon produced 8 projects, 2 shipped to production.",     "ts": _ts(180),   "source": "slack"},
    {"text": "The team adopted trunk-based development with 15-minute CI.",          "ts": _ts(220),   "source": "engineering_blog"},
    {"text": "Annual developer survey showed 92% satisfaction rate.",                 "ts": _ts(350),   "source": "survey"},

    # ── Product milestones ───────────────────────────────────────────
    {"text": "The product launched its public API with 50 endpoints.",                "ts": _ts(90),    "source": "changelog"},
    {"text": "First paying enterprise customer (Acme Corp) onboarded.",               "ts": _ts(130),   "source": "crm"},
    {"text": "API rate limiting was introduced at 1000 req/min per key.",             "ts": _ts(170),   "source": "changelog"},
    {"text": "The iOS mobile app reached 10,000 downloads.",                          "ts": _ts(230),   "source": "analytics"},
    {"text": "Launched webhook support for real-time event notifications.",            "ts": _ts(290),   "source": "changelog"},
    {"text": "Revenue crossed $1M ARR milestone.",                                    "ts": _ts(340),   "source": "finance"},

    # ── Security & compliance ────────────────────────────────────────
    {"text": "Completed first penetration test with zero critical findings.",         "ts": _ts(115),   "source": "security"},
    {"text": "Implemented SSO with SAML 2.0 for enterprise customers.",               "ts": _ts(195),   "source": "pr"},
    {"text": "GDPR data deletion pipeline deployed and verified.",                    "ts": _ts(260),   "source": "compliance"},
    {"text": "Bug bounty programme launched with $500-$5000 rewards.",                "ts": _ts(320),   "source": "security"},
]


assert len(EPISODES) == 50, f"Expected 50 episodes, got {len(EPISODES)}"


# ─────────────────────────────────────────────────────────────────────
# Ingestion — HTTP mode
# ─────────────────────────────────────────────────────────────────────

def seed_via_api(api_base: str, token: str) -> int:
    """POST each episode to the /api/memory/store endpoint."""
    import requests

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    count = 0

    for ep in EPISODES:
        payload = {
            "observation": ep["text"],
            "metadata": {
                "source": ep.get("source", "seed"),
                "timestamp": ep["ts"],
            },
        }
        try:
            r = requests.post(
                f"{api_base}/api/memory/store",
                json=payload,
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            count += 1
            print(f"  [{count:02d}/50] {ep['text'][:60]}…")
        except Exception as e:
            print(f"  [FAIL] {ep['text'][:50]}… — {e}")

    return count


# ─────────────────────────────────────────────────────────────────────
# Ingestion — direct engine mode (no server needed)
# ─────────────────────────────────────────────────────────────────────

async def seed_direct() -> int:
    """Ingest episodes directly via GraphitiEngine."""
    from src.config import Config
    from src.memory_engine.engines.graphiti_engine import GraphitiEngine

    config = Config()
    engine = GraphitiEngine(config)
    await engine.initialize()

    count = 0
    for ep in EPISODES:
        ts = datetime.fromisoformat(ep["ts"])
        await engine.add_episode(
            text=ep["text"],
            group_id="demo",
            timestamp=ts,
            source=ep.get("source", "seed"),
        )
        count += 1
        print(f"  [{count:02d}/50] {ep['text'][:60]}…")

    await engine.close()
    return count


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Membread with 50 demo episodes")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the HTTP API and ingest via GraphitiEngine directly",
    )
    parser.add_argument("--api", type=str, default=None, help="API base URL")
    parser.add_argument("--token", type=str, default=None, help="JWT token")
    args = parser.parse_args()

    print("=" * 60)
    print("  Membread — Seeding 50 demo episodes")
    print("=" * 60)

    t0 = time.time()

    if args.direct:
        count = asyncio.run(seed_direct())
    else:
        api_base = args.api or os.getenv("MEMBREAD_API", "http://localhost:8000")
        token = args.token or os.getenv("MEMBREAD_TOKEN", "")
        count = seed_via_api(api_base, token)

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Done — {count}/50 episodes ingested in {elapsed:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
