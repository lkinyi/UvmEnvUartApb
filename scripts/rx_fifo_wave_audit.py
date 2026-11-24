#!/usr/bin/env python3
"""Cross-check an existing Stage1 VCD against fixed scenario requirements.

This is additional evidence, not a replacement for the live independent model.
Only pre-clock values at actual APB/RX commit edges are counted; initialization
before reset release is excluded. Writes a new audit JSON beside the VCD.
"""
import argparse
import hashlib
import json
from pathlib import Path


def audit(path: Path, scenario: str) -> dict:
    expected = {
        "smoke": (1, 1, 0, [0x69], 0),
        "tp01": (2, 2, 0, [0x96, 0x3d], 6),
        "tp02": (40, 40, 0, [(i*37+11) & 255 for i in range(40)], 0),
        "tp03a": (17, 16, 1, [i*13+7 for i in range(16)], 0),
        "tp03b": (18, 17, 1, [i*13+7 for i in range(16)] + [0xa5], 0),
    }[scenario]
    scope, variables = [], {}
    base = "TOP.testTop.dut_top"
    with path.open() as fh:
        for line in fh:
            f = line.split()
            if not f: continue
            if f[0] == "$scope": scope.append(f[2])
            elif f[0] == "$upscope": scope.pop()
            elif f[0] == "$var": variables[".".join(scope+[f[4]])] = f[3]
            elif f[0] == "$enddefinitions": break
        # Some Verilator versions omit TOP in the VCD scope.
        if base + ".pclk_1" not in variables: base = "testTop.dut_top"
        signals = {k: variables[base+"."+k+"_1"] for k in
                   ("pclk", "preset_n", "psel", "penable", "pready", "pwrite", "paddr", "prdata")}
        for name in ("rx_complete", "rx_fifo_we", "rx_fifo_re", "rx_wptr", "rx_rptr", "rx_fifo_ov", "rx_fifo_full"):
            signals[name] = variables[base+".uart_1.receiver."+name]
        wanted = set(signals.values()); values = {}; before = {}; now = 0
        counts = {"completed": 0, "accepted": 0, "rejected": 0, "popped": 0, "empty_reads": 0}
        reads, commits, status_reads = [], [], []
        max_occ = 0; last_rptr = None; last_wptr = None; wraps = {"write": 0, "read": 0}

        def consume():
            nonlocal max_occ, last_rptr, last_wptr
            def v(name, state=before): return state.get(signals[name])
            if v("pclk") != 0 or v("pclk", values) != 1 or v("preset_n") != 1: return
            w, r = v("rx_wptr"), v("rx_rptr")
            occ = (w-r) & 31; max_occ = max(max_occ, occ)
            if last_rptr == 31 and r == 0: wraps["read"] += 1
            if last_wptr == 31 and w == 0: wraps["write"] += 1
            last_rptr, last_wptr = r, w
            if v("rx_complete") == 1:
                counts["completed"] += 1
                commits.append({"id": counts["completed"], "time_ns": now, "occupancy_before": occ,
                                "we": v("rx_fifo_we"), "full_before": v("rx_fifo_full"), "ov_before": v("rx_fifo_ov"),
                                "popped_before": counts["popped"],
                                "DATA_read_request": all(v(k) == 1 for k in ("psel", "penable", "pready")) and v("pwrite") == 0 and v("paddr") == 12})
                if v("rx_fifo_we") == 0: counts["rejected"] += 1
            if v("rx_fifo_we") == 1: counts["accepted"] += 1
            if v("rx_fifo_re") == 1: counts["popped"] += 1
            if all(v(k) == 1 for k in ("psel", "penable", "pready")) and v("pwrite") == 0:
                if v("paddr") == 12:
                    if v("rx_fifo_re") == 1: reads.append(v("prdata"))
                    else: counts["empty_reads"] += 1
                if v("paddr") in (20, 24):
                    status_reads.append({"time_ns": now, "address": v("paddr"), "value": v("prdata"), "occupancy": occ})
        for line in fh:
            s = line.strip()
            if not s: continue
            if s.startswith("#"):
                consume(); before = dict(values); now = int(s[1:])
            elif s[0] in "01xz" and s[1:] in wanted:
                values[s[1:]] = int(s[0]) if s[0] in "01" else None
            elif s[0] in "bB":
                value, code = s[1:].split()
                if code in wanted: values[code] = int(value, 2) if set(value) <= {"0", "1"} else None
        consume()
    frames, accepts, drops, expected_reads, empties = expected
    expected_counts = dict(completed=frames, accepted=accepts, rejected=drops, popped=len(expected_reads), empty_reads=empties)
    checks = {"exact_counts": counts == expected_counts, "ordered_data": reads == expected_reads,
              "capacity_never_above_16": max_occ <= 16,
              "masked_zero": all(x["value"] == 0 for x in status_reads if x["address"] == 24)}
    if drops:
        checks["actual_15_16_17_admission"] = (commits[14]["occupancy_before"] == 14 and commits[14]["we"] == 1
            and commits[15]["occupancy_before"] == 15 and commits[15]["we"] == 1
            and commits[16]["occupancy_before"] == 16 and commits[16]["we"] == 0 and commits[16]["full_before"] == 1
            and commits[16]["popped_before"] == 0 and not commits[16]["DATA_read_request"])
        checks["full_without_OV"] = any(x["address"] == 20 and x["occupancy"] == 16 and x["value"] == 3 for x in status_reads)
        checks["OV_held_on_status_reads"] = sum(x["address"] == 20 and x["value"] == 7 for x in status_reads) >= 4
        checks["DATA_read_cleared_OV"] = any(x["address"] == 20 and x["occupancy"] == 15 and x["value"] == 1 for x in status_reads)
    if scenario == "tp02": checks["full_pointer_wraps"] = wraps["read"] > 0 and wraps["write"] > 0
    with path.open("rb") as f: digest = hashlib.file_digest(f, "sha256").hexdigest()
    return {"scenario": scenario, "wave": str(path), "wave_sha256": digest, "end_ns": now,
            "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "counts": counts,
            "max_occupancy": max_occ, "full_pointer_wraps": wraps, "data_reads": reads,
            "commits": commits, "status_reads": status_reads}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wave", type=Path)
    ap.add_argument("scenario", choices=("smoke", "tp01", "tp02", "tp03a", "tp03b"))
    a = ap.parse_args()
    result = audit(a.wave, a.scenario)
    output = a.wave.with_name("wave-audit.json")
    with output.open("x", encoding="utf-8") as f: json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in ("scenario", "status", "checks", "counts", "max_occupancy")}))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
