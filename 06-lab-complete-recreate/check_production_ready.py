import os
import sys


REQUIRED_FILES = [
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    ".env.example",
    ".dockerignore",
    "railway.toml",
    "app/main.py",
    "app/config.py",
    "app/auth.py",
    "app/rate_limiter.py",
    "app/cost_guard.py",
    "utils/mock_llm.py",
]


def check(name: str, ok: bool):
    print(f"{'✅' if ok else '❌'} {name}")
    return ok


def main() -> int:
    base = os.path.dirname(__file__)
    passed = 0
    total = 0

    print("\n=== Lab06 Recreate Readiness Check ===\n")

    for rel in REQUIRED_FILES:
        total += 1
        ok = os.path.exists(os.path.join(base, rel))
        passed += int(check(f"{rel} exists", ok))

    main_py = os.path.join(base, "app", "main.py")
    if os.path.exists(main_py):
        with open(main_py, "r", encoding="utf-8") as f:
            content = f.read()

        checks = {
            "/health endpoint": '"/health"' in content,
            "/ready endpoint": '"/ready"' in content,
            "auth dependency": "verify_api_key" in content,
            "rate limiting": "check_rate_limit" in content,
            "cost guard": "check_monthly_budget" in content,
            "sigterm handling": "SIGTERM" in content,
            "redis state": "redis" in content.lower(),
        }

        for title, ok in checks.items():
            total += 1
            passed += int(check(title, ok))

    print(f"\nResult: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
