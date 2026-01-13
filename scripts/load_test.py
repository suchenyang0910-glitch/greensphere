import argparse
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


LANGS = ["en", "zh", "th", "vi", "km"]


def run_one(base: str, user_id: int, lang: str, scenario: str) -> dict:
    s = requests.Session()
    headers = {"X-GS-Lang": lang}

    t0 = time.perf_counter()
    try:
        r1 = s.get(f"{base}/", headers={"Accept-Language": lang}, timeout=10)
        if r1.status_code != 200:
            return {"ok": False, "status": r1.status_code, "step": "home", "ms": int((time.perf_counter() - t0) * 1000)}

        uid = user_id
        if scenario == "full":
            r2 = s.post(
                f"{base}/api/init_user",
                headers={**headers, "Content-Type": "application/json"},
                json={"telegram_id": user_id, "username": f"U{user_id}"},
                timeout=10,
            )
            if r2.status_code != 200:
                return {"ok": False, "status": r2.status_code, "step": "init_user", "ms": int((time.perf_counter() - t0) * 1000)}
            uid = r2.json().get("user_id")

        r3 = s.get(f"{base}/api/tasks", params={"user_id": uid}, headers=headers, timeout=10)
        if r3.status_code != 200:
            return {"ok": False, "status": r3.status_code, "step": "tasks", "ms": int((time.perf_counter() - t0) * 1000)}
        tasks = (r3.json().get("tasks") or [])
        if not tasks:
            return {"ok": False, "status": 0, "step": "tasks_empty", "ms": int((time.perf_counter() - t0) * 1000)}
        task_id = int(tasks[0]["id"])

        r4 = s.post(
            f"{base}/api/complete",
            headers={**headers, "Content-Type": "application/json"},
            json={"user_id": uid, "task_id": task_id},
            timeout=10,
        )
        t1 = time.perf_counter()

        ok = (r3.status_code == 200) and (r4.status_code in (200, 429))
        return {"ok": ok, "status": r4.status_code, "step": "done" if ok else "complete", "ms": int((t1 - t0) * 1000)}
    except Exception:
        return {"ok": False, "status": -1, "step": "exception", "ms": int((time.perf_counter() - t0) * 1000)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--users", type=int, default=120)
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--lang", default="en", help="en/zh/th/vi/km or 'mix'")
    ap.add_argument("--scenario", default="tasks", choices=["tasks", "full"])
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    random.seed(args.seed)

    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = []
        for i in range(args.users):
            uid = 200000 + i
            lang = args.lang
            if lang == "mix":
                lang = random.choice(LANGS)
            futs.append(ex.submit(run_one, base, uid, lang, args.scenario))
        for f in as_completed(futs):
            results.append(f.result())

    total = len(results)
    oks = sum(1 for r in results if r["ok"])
    by_status = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    ms = [r["ms"] for r in results]

    print("Total:", total, "OK:", oks, "Error:", total - oks)
    print("Status counts:", dict(sorted(by_status.items(), key=lambda x: x[0])))
    if ms:
        print("Latency ms: p50=%d p90=%d p99=%d avg=%d" % (
            int(statistics.median(ms)),
            int(statistics.quantiles(ms, n=10)[8]) if len(ms) >= 10 else int(max(ms)),
            int(sorted(ms)[max(0, int(len(ms) * 0.99) - 1)]),
            int(sum(ms) / len(ms)),
        ))

    hard_fail = any(r["status"] >= 500 for r in results)
    if hard_fail:
        print("Found 5xx responses.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

