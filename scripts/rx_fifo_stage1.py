#!/usr/bin/env python3
"""Run the bounded Stage1 acceptance suite in a new, isolated build directory.

From the project root after sourcing scripts/env_local.sh:
  python3 scripts/rx_fifo_stage1.py --root build/rx-stage1-<unique-id>
Use --skip-build only for an existing matching build under that root.
Every simulator run gets a distinct directory through uartvip.py.
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="build/rx-stage1-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--build-name", default="build-01")
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()
    evidence = (ROOT / a.root).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    build = evidence / a.build_name
    suite_dir = evidence / ("suite-" + str(time.time_ns()))
    suite_dir.mkdir()
    common = ["make", f"BUILD_DIR={build}", "WAVE=1", "JOBS=2", "SEED=1"]

    def command(label: str, args: list[str]) -> tuple[int, str]:
        started = time.time()
        p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (suite_dir / (label + ".console.txt")).write_text(p.stdout, encoding="utf-8")
        (suite_dir / (label + ".command.json")).write_text(json.dumps({
            "command": args, "cwd": str(ROOT), "make_exit": p.returncode,
            "wall_s": round(time.time()-started, 3)}, indent=2), encoding="utf-8")
        print(p.stdout, flush=True)
        return p.returncode, p.stdout

    environment = {"created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "python": sys.version, "platform": sys.platform,
                   "UVM_HOME": os.environ.get("UVM_HOME"), "VERILATOR_ROOT": os.environ.get("VERILATOR_ROOT")}
    for key, cmd in [("git_head", ["git", "rev-parse", "HEAD"]),
                     ("git_branch", ["git", "branch", "--show-current"]),
                     ("git_status", ["git", "status", "--porcelain=v1", "--untracked-files=all"]),
                     ("verilator", ["verilator", "--version"]),
                     ("uvm_head", ["git", "-C", os.environ.get("UVM_HOME", "."), "rev-parse", "HEAD"])]:
        p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        environment[key] = {"exit": p.returncode, "output": p.stdout.strip()}
    (suite_dir / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    if not a.skip_build:
        if build.exists():
            raise SystemExit("Refusing to rebuild over existing evidence; choose a new --build-name")
        rc, _ = command("build", common + ["build"])
        if rc:
            return rc

    # A negative selftest is accepted ONLY when its intended real error is
    # present, the run result is FAIL, and make returned a nonzero exit.
    cases = [
        ("observation_smoke", "rx_fifo_observation_smoke", [], None),
        ("negative_protocol", "rx_fifo_observation_smoke", ["PLUSARGS=PROTOCOL_CHECKER_SELFTEST"], "[APB_PROTOCOL]"),
        ("negative_uart_glitch", "rx_fifo_observation_smoke", ["PLUSARGS=UART_CHECKER_SELFTEST"], "[UART_PROTOCOL]"),
        ("negative_expectation", "rx_fifo_observation_smoke", ["PLUSARGS=RX_EXPECTATION_SELFTEST"], "[READ FAIL]"),
        ("negative_global_timeout", "rx_fifo_observation_smoke", ["TIMEOUT_NS=1000"], "[CTEST TIMEOUT]"),
        ("negative_missing_frame", "rx_fifo_observation_smoke", ["PLUSARGS=RX_MISSING_FRAME_SELFTEST"], "[RX_DUT_FRAME_TIMEOUT]"),
        ("TP01", "rx_fifo_tp01", [], None),
        ("TP02", "rx_fifo_tp02", [], None),
        ("TP03a", "rx_fifo_tp03a", [], None),
        ("TP03b", "rx_fifo_tp03b", [], None),
        ("legacy_complete", "baudrate_9600_complete", [], None),
    ]
    results = []
    for label, test, extra, expected_error in cases:
        before = set((build / "runs").glob("*/result.json"))
        rc, console = command(label, common + ["run", f"TEST={test}"] + extra)
        after = set((build / "runs").glob("*/result.json")) - before
        actual = json.loads(next(iter(after)).read_text()) if len(after) == 1 else {"status": "BLOCKED", "reason": "missing or ambiguous run result"}
        log_path = ROOT / actual["log"] if actual.get("log") else None
        log = log_path.read_text(errors="replace") if log_path else console
        accepted = (rc != 0 and actual["status"] == "FAIL" and expected_error in log) if expected_error else (rc == 0 and actual["status"] == "PASS")
        allowed = [expected_error] if expected_error else []
        if label == "negative_global_timeout":
            allowed += ["[RX_ENV_INCOMPLETE]", "[RX_ENV_CHECK_COUNTS]"]
        unexpected = [line for line in actual.get("error_messages", [])
                      if not any(tag in line for tag in allowed)]
        if expected_error:
            accepted = accepted and not unexpected
        if label in ("negative_protocol", "negative_uart_glitch"):
            accepted = accepted and "[UART_CHK_CHECKER]" in log
        if label == "negative_expectation":
            accepted = accepted and "Expected data: 00000068, Actual data: 00000069" in log
        row = {"label": label, "test": test, "expected_status": "FAIL" if expected_error else "PASS",
               "expected_error": expected_error, "unexpected_errors": unexpected,
               "make_exit": rc, "acceptance": "PASS" if accepted else "FAIL", "actual": actual}
        results.append(row)
        (suite_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"ACCEPTANCE {label}: {row['acceptance']} (actual={actual['status']} make_exit={rc})", flush=True)
        # Foundation failures block dependent checks; no falsely green partial suite.
        if not accepted:
            break
    success = len(results) == len(cases) and all(r["acceptance"] == "PASS" for r in results)
    (suite_dir / "suite_result.json").write_text(json.dumps({"status": "PASS" if success else "FAIL", "cases_executed": len(results),
        "cases_required": len(cases), "results": str(suite_dir / "results.json")}, indent=2), encoding="utf-8")
    print(f"STAGE1 {'PASS' if success else 'FAIL'}: {suite_dir}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
