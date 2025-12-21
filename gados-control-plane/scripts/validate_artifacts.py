import os

REQUIRED_FILES = [
    # Core docs artifacts
    "gados-project/strategy/ARCHITECTURE.md",
    "gados-project/strategy/RUNBOOKS.md",
    "gados-project/memory/COMM_PROTOCOL.md",
    "gados-project/memory/NOTIFICATION_POLICY.md",
    "gados-project/memory/VERIFICATION_POLICY.md",
    "gados-project/memory/ECONOMICS_LEDGER.md",
    "gados-project/memory/WORKFLOW_GATES.md",
    # QA templates/artifacts (beta)
    "gados-project/verification/BETA-QA-evidence-TEMPLATE.md",
]


def main() -> int:
    missing: list[str] = []
    for rel in REQUIRED_FILES:
        if not os.path.exists(rel):
            missing.append(rel)

    if missing:
        print("artifact_validation=FAIL")
        for p in missing:
            print(f"missing={p}")
        return 2

    print("artifact_validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

