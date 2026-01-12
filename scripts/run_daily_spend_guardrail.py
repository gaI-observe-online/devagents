from __future__ import annotations

import argparse

from gados_control_plane.beta_spend_guardrail import run_daily_spend_guardrail
from gados_control_plane.paths import get_paths


def _parse_steps(raw: str) -> list[float] | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def main() -> int:
    p = argparse.ArgumentParser(description="Run the beta Daily Spend Guardrail scenario.")
    p.add_argument("--budget-usd", type=float, default=10.0)
    p.add_argument("--steps", type=str, default="", help="Comma-separated spend steps in USD, e.g. '4,4,3'")
    args = p.parse_args()

    out = run_daily_spend_guardrail(paths=get_paths(), budget_usd=args.budget_usd, spend_steps_usd=_parse_steps(args.steps))
    print("guardrail_result:")
    print(f"- correlation_id: {out.correlation_id}")
    print(f"- scope_id: {out.scope_id}")
    print(f"- budget_usd: {out.budget_usd}")
    print(f"- spend_usd: {out.spend_usd}")
    print(f"- threshold: {out.threshold}")
    print(f"- ledger: gados-project/{out.ledger_rel_path}")
    print(f"- escalation: {('gados-project/' + out.escalation_rel_path) if out.escalation_rel_path else '(none)'}")
    print(f"- bus_message_id: {out.bus_message_id}")
    print(f"- notification_queue: {out.notification_queued_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

