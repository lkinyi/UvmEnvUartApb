#!/usr/bin/env python3
"""Verification tasks of the UART-APB UVM environment on Windows and Linux.

One backend for every task; the Makefile and the command line call it.

  doctor      show the platform, the tools found, and the UVM source in use
  lint        lint the DUT and the checkers (Verilator, then slang)
  check       type-check the whole UVM testbench with the official UVM (slang), no simulator needed
  gen         generate build/gen/tests.svh: one uvm_test per directory of pat/ (no file is copied)
  build       compile the testbench into one executable (Verilator, or Questa)
  run         run one test:        run --test baudrate_9600 --seed 3
  regress     run many tests:      regress --tests all --seeds 1,2 --jobs 4
  cov         merge and report coverage (build with --cov)
  fetch-uvm   clone the pinned Accellera UVM 2020.3.1 (Apache-2.0)
  clean       remove build/

Options that choose commands
  --platform auto|windows|linux   tool names, search paths, executable suffix, temp directory
  --sim verilator|questa          open-source default, or the commercial Questa flow

A test result comes from the line printed by cTest: "** TEST PASSED **" / "** TEST FAILED **".
A run with no such line, a simulator error, or a wall-clock timeout is a failure.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
UVM_TAG = "2020.3.1"
UVM_REPO = "https://github.com/accellera-official/uvm-core.git"
DUT_FILES = ["dut/uart_apb_if.v", "dut/uart_receiver.v", "dut/uart_transmitter.v", "dut/uart_top.v", "dut/dut_top.v"]
CHECKER_FILES = ["checker/apb_protocol_checker.sv", "checker/apb_protocol_checker_top.sv",
                 "checker/uart_protocol_checker.sv", "checker/uart_protocol_checker_top.sv"]
TB_FILES = ["uvm_comp/ifDut.sv", "sim/testTop.sv"]
DEFINES = ["UVM_NO_DPI", "UVM_CMDLINE_NO_DPI", "UVM_REGEX_NO_DPI", "INTERRUPT_COM"]


# ----------------------------------------------------------------------------
# platform and tools
# ----------------------------------------------------------------------------

class Platform:
    """Everything that differs between Windows and Linux."""

    def __init__(self, name: str):
        self.name = "windows" if (name == "auto" and os.name == "nt") else ("linux" if name == "auto" else name)
        self.win = self.name == "windows"
        self.exe = ".exe" if self.win else ""
        home = Path.home()
        if self.win:
            oss = Path(os.environ.get("OSS_CAD_HOME", "C:/Tools/oss-cad-suite"))
            msys = [Path(p) for p in [os.environ.get("MSYS2_HOME", ""), "C:/msys64", str(home / "Tools/msys64")] if p]
            # The compiler's own runtime DLLs (ucrt64) must come before the ones shipped with OSS CAD Suite,
            # otherwise a built simulator fails to start (exit code 0xC0000139).
            self.extra_path = [m / "ucrt64/bin" for m in msys] + [oss / "bin", oss / "lib"] + [m / "usr/bin" for m in msys]
            share = oss / "share" / "verilator"
            self.verilator_root = str(share) if share.is_dir() else None
            self.verilator_names = ["verilator_bin.exe"]       # the perl launcher needs Pod::Usage on Windows
            self.coverage_names = ["verilator_coverage_bin.exe", "verilator_coverage.exe"]
            self.uvm_candidates = ["C:/Tools/uvm-core", str(home / "uvm-core")]
            self.questa_dirs = [os.environ.get("QUESTA_HOME", ""), "C:/questasim64_10.2c/win64"]
        else:
            self.extra_path = []
            self.verilator_root = os.environ.get("VERILATOR_ROOT")
            self.verilator_names = ["verilator"]
            self.coverage_names = ["verilator_coverage"]
            self.uvm_candidates = [str(home / "uvm-core"), "/opt/uvm-core", "/usr/local/uvm-core"]
            self.questa_dirs = [os.environ.get("QUESTA_HOME", "")]

    def env(self) -> dict:
        """Environment for the tools. Computed once: run_one calls it from several threads."""
        if getattr(self, "_env", None) is None:
            e = dict(os.environ)
            tmp = BUILD / "tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            dirs = [str(p) for p in self.extra_path if os.path.isdir(str(p))]
            e["PATH"] = os.pathsep.join(dirs + [e.get("PATH", "")])
            e["TEMP"] = e["TMP"] = e["TMPDIR"] = str(tmp)      # the compiler needs a writable temp directory
            if self.verilator_root and "VERILATOR_ROOT" not in os.environ:
                e["VERILATOR_ROOT"] = self.verilator_root
            e.setdefault("VERILATOR_SOLVER", "z3 --in")
            self._env = e
        return dict(self._env)

    @staticmethod
    def env_for(tool: str, env: dict) -> dict:
        """Environment for one prebuilt tool: its own directory first, so it loads its own DLLs (slang vs MSYS2)."""
        e = dict(env)
        d = os.path.dirname(tool)
        e["PATH"] = os.pathsep.join([d, os.path.join(os.path.dirname(d), "lib"), e.get("PATH", "")])
        return e

    def which(self, names, env=None) -> str | None:
        path = (env or self.env())["PATH"]
        for n in names if isinstance(names, list) else [names]:
            found = shutil.which(n, path=path)
            if found:
                return found
        return None


def run_cmd(cmd: list[str], env: dict, cwd: Path | None = None, log: Path | None = None, timeout: int | None = None) -> tuple[int, str]:
    """Run a command, return (exit code, combined output). Output also goes to `log`."""
    t0 = time.time()
    # The output goes straight to the log file, so a run that is killed on timeout still leaves its log.
    raw = (log if log else BUILD / "tmp" / f"cmd_{os.getpid()}_{int(t0 * 1000) % 100000}.out")
    raw.parent.mkdir(parents=True, exist_ok=True)
    rc = 0
    note = ""
    with open(raw, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(f"# {' '.join(cmd)}\n# cwd {cwd}\n")
        fh.flush()
        try:
            rc = subprocess.run(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc, note = 124, f"\n[uartvip] WALL-CLOCK TIMEOUT after {timeout}s\n"
        except FileNotFoundError as exc:
            rc, note = 127, f"[uartvip] cannot run {cmd[0]}: {exc}\n"
        fh.write(f"{note}\n# seconds {time.time() - t0:.1f}  exit {rc}\n")
    out = raw.read_text(encoding="utf-8", errors="replace")
    if not log:
        raw.unlink(missing_ok=True)
    return rc, out


def posix(p: Path | str) -> str:
    return str(p).replace("\\", "/")


def resolve_uvm(plat: Platform, arg: str | None) -> Path | None:
    """Return the UVM src directory (the one that holds uvm_pkg.sv) or None."""
    cands = [arg, os.environ.get("UVM_SRC"), os.environ.get("UVM_HOME"), os.environ.get("VLSIT_UVM_HOME")] + plat.uvm_candidates
    for c in cands:
        if not c:
            continue
        for sub in ("", "src"):
            d = Path(c) / sub
            if (d / "uvm_pkg.sv").is_file():
                return d
    return None


def gxx_major(env: dict) -> int:
    gxx = shutil.which("g++", path=env["PATH"])
    if not gxx:
        return 0
    try:
        return int(subprocess.run([gxx, "-dumpversion"], capture_output=True, text=True, env=env).stdout.split(".")[0])
    except Exception:
        return 0


# ----------------------------------------------------------------------------
# tests
# ----------------------------------------------------------------------------

def pattern_dirs(include_skipped: bool = False) -> list[Path]:
    """Pattern directories. A directory with a file named SKIP is left out (the file says why)."""
    return sorted(d for d in (ROOT / "pat").iterdir()
                  if (d / "cVSequence.sv").is_file() and (include_skipped or not (d / "SKIP").exists()))


def ident(name: str) -> str:
    return re.sub(r"\W", "_", name)


def test_names() -> list[str]:
    return [f"test_{ident(d.name)}" for d in pattern_dirs()]


def cmd_gen(_a, _p) -> int:
    """Create build/gen/tests.svh. Each pattern keeps its own file; only a renamed copy is generated."""
    gen = BUILD / "gen"
    gen.mkdir(parents=True, exist_ok=True)
    inc, cls = [], []
    for d in pattern_dirs():
        i = ident(d.name)
        src = (d / "cVSequence.sv").read_text(encoding="utf-8", errors="replace")
        # The pattern becomes a subclass of the default cVSequence, as the factory override requires
        hdr = re.compile(r"class\s+cVSequence\s+extends\s+uvm_sequence\s*#\(\s*cApbTransaction\s*\)\s*;")
        if not hdr.search(src):
            raise SystemExit(f"gen: pat/{d.name}/cVSequence.sv: the class header was not recognised")
        body = hdr.sub("class @@HDR@@;", src)
        # A pattern that ends with $stop would stop the simulator with an error; end the sequence instead
        # (generated copy only; the source of the pattern is not touched)
        body = re.sub(r"^(?![ \t]*//)([^\n]*?)\$stop\s*;", r"\1return;", body, flags=re.M)
        body = re.sub(r"\bcVSequence\b", f"cVSeq_{i}", body).replace("@@HDR@@", f"cVSeq_{i} extends cVSequence")
        (gen / f"pat_{i}.svh").write_text(body, encoding="utf-8", newline="\n")
        inc.append(f'`include "pat_{i}.svh"')
        base_file = d / "test_base.txt"
        base = base_file.read_text().strip() if base_file.exists() else "cTest"
        if base not in ("cTest", "cRxFifoTest"):
            raise SystemExit(f"gen: unsupported test base {base!r} in {d}")
        cls.append(f"""
  // Test of pattern pat/{d.name}
   class test_{i} extends {base};
    `uvm_component_utils(test_{i})
    function new (string name = "test_{i}", uvm_component parent = null);
      super.new(name, parent);
    endfunction
    function void build_phase(uvm_phase phase);
      // Replace the default test pattern before cTest creates it
      cVSequence::type_id::set_type_override(cVSeq_{i}::get_type());
      super.build_phase(phase);
    endfunction
  endclass""")
    (gen / "tests.svh").write_text("// Generated by scripts/uartvip.py gen. Do not edit.\n" + "\n".join(inc) + "\n" + "\n".join(cls) + "\n",
                                   encoding="utf-8", newline="\n")
    print(f"gen: {len(inc)} tests in {posix(gen / 'tests.svh')}")
    return 0


# ----------------------------------------------------------------------------
# lint and check
# ----------------------------------------------------------------------------

def cmd_doctor(a, plat: Platform) -> int:
    env = plat.env()
    print(f"platform   {plat.name}  (python {sys.version.split()[0]})")
    rows = [("verilator", plat.verilator_names), ("verilator cov", plat.coverage_names), ("slang", ["slang", "slang.exe"]),
            ("z3", ["z3"]), ("make", ["make"]), ("g++", ["g++"]), ("git", ["git"]), ("vsim (Questa)", ["vsim", "vsim.exe"])]
    for label, names in rows:
        p = plat.which(names, env)
        print(f"{label:14s} {p or 'missing'}")
    gm = gxx_major(env)
    if gm >= 16:
        print(f"note       g++ {gm}: -Os breaks the Verilator runtime link; the build uses -O1")
    uvm = resolve_uvm(plat, a.uvm_home)
    ver = ""
    if uvm:
        m = re.search(r'UVM_VERSION_STRING\s*=\s*"([^"]+)"', (uvm / "base/uvm_version.svh").read_text(errors="replace")) if (uvm / "base/uvm_version.svh").is_file() else None
        ver = m.group(1) if m else ""
    print(f"{'uvm src':14s} {uvm or 'missing (make fetch-uvm)'} {ver}")
    skipped = [d.name for d in pattern_dirs(True) if (d / "SKIP").exists()]
    print(f"{'patterns':14s} {len(pattern_dirs())} tests" + (f", {len(skipped)} skipped (see SKIP): {', '.join(skipped)}" if skipped else ""))
    return 0


def cmd_lint(a, plat: Platform) -> int:
    env = plat.env()
    files = [posix(ROOT / f) for f in DUT_FILES + CHECKER_FILES]
    incs = [f"+incdir+{posix(ROOT / 'sim')}"]
    vl = plat.which(plat.verilator_names, env)
    slang = plat.which(["slang", "slang.exe"], env)
    if not vl and not slang:
        print("lint: NOT_RUN (no verilator and no slang found; run: doctor)")
        return 2
    bad = 0
    if vl:
        cmd = [vl, "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSEDSIGNAL", "-Wno-UNUSEDPARAM", "-Wno-PINCONNECTEMPTY",
               "-Wno-fatal", "--timescale", "1ns/1ns", "-DINTERRUPT_COM", *incs, "--top-module", "dut_top", *files]
        rc, out = run_cmd(cmd, env, ROOT, BUILD / "logs" / "lint_verilator.log")
        errs, warns = len(re.findall(r"%Error", out)), len(re.findall(r"%Warning", out))
        kinds = sorted(set(re.findall(r"%Warning-(\w+)", out)))
        print(f"lint verilator: {errs} error(s), {warns} warning(s) {' '.join(kinds)}  log: build/logs/lint_verilator.log")
        if rc != 0 and not errs:
            print(f"lint verilator: tool failed, exit {rc}")
            errs = 1
        bad += errs + (warns if a.strict else 0)
    if slang:
        cmd = [slang, "-I", posix(ROOT / "sim"), "-DINTERRUPT_COM", "--timescale", "1ns/1ns", *files[:len(DUT_FILES)], "--top", "dut_top"]
        rc, out = run_cmd(cmd, plat.env_for(slang, env), ROOT, BUILD / "logs" / "lint_slang.log")
        n_err = len(re.findall(r"\berror:", out))
        if rc != 0 and not n_err:
            print(f"lint slang:     tool failed, exit {rc}")
            n_err = 1
        print(f"lint slang:     {n_err} error(s)  log: build/logs/lint_slang.log")
        bad += n_err
    return 1 if bad else 0


def tb_args(plat: Platform, uvm: Path, gen: bool = True) -> tuple[list[str], list[str]]:
    """(include/define options, source files) of the full testbench, as plain paths."""
    opts = [f"+incdir+{posix(ROOT / 'sim')}", f"+incdir+{posix(uvm)}"]
    if gen:
        opts.append(f"+incdir+{posix(BUILD / 'gen')}")
    opts += [f"-D{d}" for d in DEFINES]
    if gen:
        opts.append("-DPATTERN_LIBRARY")
    files = [posix(ROOT / f) for f in DUT_FILES + CHECKER_FILES + TB_FILES]
    return opts, files


def cmd_check(a, plat: Platform) -> int:
    env = plat.env()
    slang = plat.which(["slang", "slang.exe"], env)
    uvm = resolve_uvm(plat, a.uvm_home)
    if not slang or not uvm:
        print(f"check: NOT_RUN ({'slang missing' if not slang else 'UVM source missing, run: fetch-uvm'})")
        return 2
    cmd_gen(a, plat)
    opts, files = tb_args(plat, uvm)
    sl = []
    for o in opts:
        sl.append(f"-I{o[8:]}" if o.startswith("+incdir+") else o)
    cmd = [slang, *sl, "--timescale", "1ns/1ns", "--allow-use-before-declare", *files, "--top", "testTop"]
    rc, out = run_cmd(cmd, plat.env_for(slang, env), ROOT, BUILD / "logs" / "check_slang.log")
    mine = [ln for ln in out.splitlines() if re.search(r"\b(error|warning):", ln) and str(uvm).replace("\\", "/") not in ln.replace("\\", "/")]
    ok = rc == 0 and "Build succeeded" in out and not [ln for ln in mine if "error:" in ln]
    print(f"check slang+UVM: {'PASS' if ok else 'FAIL'}  ({len([m for m in mine if 'error:' in m])} error(s) in the testbench)  log: build/logs/check_slang.log")
    for ln in mine[:8]:
        print("   ", ln[:170])
    return 0 if ok else 1


# ----------------------------------------------------------------------------
# build and run
# ----------------------------------------------------------------------------

def exe_path(a, plat: Platform) -> Path:
    return BUILD / a.sim / ("obj" if a.sim == "verilator" else "work") / (f"VtestTop{plat.exe}" if a.sim == "verilator" else "")


def source_hashes() -> dict:
    """Lock all local compile inputs, including generated library and test bases."""
    paths = []
    for directory in ("dut", "checker", "uvm_comp", "sim", "pat"):
        paths.extend(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and (p.suffix in (".v", ".sv", ".svh", ".h") or p.name in ("SKIP", "test_base.txt")))
    paths.extend((BUILD / "gen").glob("*.svh"))
    return {posix(os.path.relpath(p, ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def cmd_build(a, plat: Platform) -> int:
    env = plat.env()
    uvm = resolve_uvm(plat, a.uvm_home)
    if not uvm:
        print("build: UVM source not found; run: fetch-uvm  (or set UVM_HOME / UVM_SRC)")
        return 2
    cmd_gen(a, plat)
    opts, files = tb_args(plat, uvm)
    log = BUILD / "logs" / f"build_{a.sim}.log"
    t0 = time.time()
    if a.sim == "verilator":
        vl = plat.which(plat.verilator_names, env)
        if not vl:
            print("build: verilator not found (run: doctor)")
            return 2
        obj = BUILD / "verilator" / "obj"
        if obj.exists():
            shutil.rmtree(obj, ignore_errors=True)
        obj.parent.mkdir(parents=True, exist_ok=True)   # Verilator creates one directory level only
        cmd = [vl, "--binary", "--timing", "-j", str(a.jobs), "--timescale", "1ns/1ns",
               "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-WIDTH", "-Wno-CASEINCOMPLETE", "-Wno-IMPLICIT",
               "--Mdir", posix(obj), "--top-module", "testTop", "--output-groups", "8"]
        if gxx_major(env) >= 16:
            cmd += ["-CFLAGS", "-O1"]            # gcc 16 with -Os fails to link the Verilator runtime
        if a.cov:
            cmd += ["--coverage-user"]  # functional covergroups; no code coverage denominator
        if a.wave:
            cmd += ["--trace", "-DWAVE"]
        cmd += opts + [posix(uvm / "uvm_pkg.sv")] + files   # Verilator wants the package first
    else:
        vlog = plat.which(["vlog", "vlog.exe"] , env)
        if not vlog:
            for d in plat.questa_dirs:
                if d and (Path(d) / f"vlog{plat.exe}").is_file():
                    env["PATH"] = d + os.pathsep + env["PATH"]
                    vlog = str(Path(d) / f"vlog{plat.exe}")
        if not vlog:
            print("build: vlog (Questa) not found; set QUESTA_HOME or PATH")
            return 2
        work = BUILD / "questa" / "work"
        run_cmd([str(Path(vlog).with_name("vlib" + plat.exe)), posix(work)], env, ROOT)
        cmd = [vlog, "-sv", "-work", posix(work), "-timescale", "1ns/1ns", "-l", posix(log),
               *[o.replace("-D", "+define+", 1) if o.startswith("-D") else o for o in opts],
               *(["+cover=bcestf"] if a.cov else []), *files]
    print(f"build [{a.sim}/{plat.name}] ... (a Verilator build of the UVM testbench takes a few minutes)")
    rc, out = run_cmd(cmd, env, ROOT, log)
    ok = rc == 0 and (a.sim != "verilator" or exe_path(a, plat).is_file())
    print(f"build: {'PASS' if ok else 'FAIL'} in {time.time() - t0:.0f}s  log: {posix(log.relative_to(ROOT))}")
    if not ok:
        for ln in [x for x in out.splitlines() if re.search(r"%Error|\berror\b|undefined reference", x)][:6]:
            print("   ", ln[:200])
    if ok:
        manifest = {"sources": source_hashes(), "sim": a.sim, "wave": a.wave, "cov": a.cov,
                    "command": cmd, "uvm": str(uvm), "log": str(log), "build_exit": rc}
        if a.sim == "verilator":
            manifest["binary_sha256"] = hashlib.sha256(exe_path(a, plat).read_bytes()).hexdigest()
        (BUILD / "build_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0 if ok else 1


def parse_result(text: str, rc: int, wall: bool) -> dict:
    res = {"status": "FAIL", "reason": ""}
    passed = "** TEST PASSED **" in text
    failed = re.search(r"\*\* TEST FAILED \*\*(.*)", text)
    m_err = re.search(r"UVM_ERROR\s*:\s*(\d+)", text)
    res["uvm_errors"] = int(m_err.group(1)) if m_err else None
    m_fatal = re.search(r"UVM_FATAL\s*:\s*(\d+)", text)
    res["uvm_fatals"] = int(m_fatal.group(1)) if m_fatal else None
    checker_errors = re.findall(r"\[(?:APB|UART)_ERROR\]", text)
    res["protocol_checker_errors"] = len(checker_errors)
    live_errors = re.findall(r"^UVM_(?:ERROR|FATAL)\s+(?!\s*:).+", text, re.M)
    res["error_messages"] = live_errors
    sim_err = re.search(r"%Error[^\n]*", text)
    if wall:
        res["reason"] = "wall-clock timeout"
    elif sim_err:
        res["reason"] = sim_err.group(0)[:120]
    elif failed:
        res["reason"] = "test failed" + failed.group(1).strip()
    elif not passed and rc not in (0, 124):
        hint = " (a runtime DLL does not match the compiler, check PATH order)" if rc in (3221225785, 3221225781) else ""
        fatal = re.search(r"UVM_FATAL .*", text)
        res["reason"] = (fatal.group(0)[:110] if fatal else f"exit code {rc:#x}{hint}")
    elif not passed:
        fatal = re.search(r"UVM_FATAL .*", text)
        res["reason"] = fatal.group(0)[:110] if fatal else "no result line"
    elif rc != 0:
        res["reason"] = f"exit code {rc}"
    elif res["uvm_errors"]:
        res["reason"] = f"{res['uvm_errors']} UVM_ERROR"
    elif res["uvm_fatals"] or live_errors or checker_errors:
        res["reason"] = "checker/UVM error in complete simulator output"
    elif m_err is None or m_fatal is None:
        res["reason"] = "missing UVM error/fatal totals"
    else:
        res["status"] = "PASS"
    res["compares_ok"] = int(m.group(1)) if (m := re.search(r"(\d+) passed, \d+ failed", text)) else None
    summary = re.search(r"\[RX_FIFO_SUMMARY\] ([^\n]+)", text)
    if summary:
        res["rx_fifo"] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", summary.group(1))}
    irq_summary = re.search(r"\[RX_IRQ_SUMMARY\] ([^\n]+)", text)
    if irq_summary:
        res["irq"] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", irq_summary.group(1))}
        res["functional_events"] = {int(i): int(n) for i,n in re.findall(r"\[RX_FC_EVENT\] id=(\d+) hits=(\d+)", text)}
        res["functional_cross"] = {f"{s}:{i}": int(n) for s,i,n in re.findall(r"\[RX_FC_CROSS\] source=(\d+) ie=(\d+) hits=(\d+)", text)}
        res["tp07_hits"] = {int(i): int(n) for i,n in re.findall(r"\[RX_TP07_HIT\] id=(\d+) hits=(\d+)", text)}
        if (res["irq"].get("cycles", 0) == 0 or res["irq"].get("errors") != 0) and res["status"] == "PASS":
            res.update(status="FAIL", reason="missing/failed IRQ comparisons")
    if re.search(r"Running test test_rx_fifo_tp07", text):
        q=res.get("irq", {})
        valid=bool(irq_summary) and len(res.get("functional_events", {}))==52
        valid=valid and len(res.get("tp07_hits", {}))==14 and all(n==1 for n in res.get("tp07_hits", {}).values())
        valid=valid and q.get("rises",0)>=4 and q.get("falls",0)>=4 and q.get("holds",0)>0 and q.get("merge_holds")==1
        if not valid and res["status"]=="PASS":
            res.update(status="FAIL",reason="missing/unmet TP07 IRQ/scenario contract")
    stage2_summary = re.search(r"\[RX_STAGE2_SUMMARY\] ([^\n]+)", text)
    if stage2_summary:
        res["rx_stage2"] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", stage2_summary.group(1))}
        res["rxt_hits"] = [{k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", row)}
                           for row in re.findall(r"\[RX_STAGE2_RXT\] (rxt=[^\n]+)", text)]
        res["ie_hits"] = [{k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", row)}
                          for row in re.findall(r"\[RX_STAGE2_IE\] (source=[^\n]+)", text)]
    if re.search(r"Running test test_rx_fifo_", text):
        contract = re.search(r"\[RX_CONTRACT\] ([^\n]+)", text)
        expected = dict(re.findall(r"required_(\w+)=(\d+)", contract.group(1))) if contract else {}
        actual = res.get("rx_fifo", {})
        pairs = {"frames": "completed", "accepts": "accepted", "rejects": "rejected",
                 "pops": "popped", "empty": "empty_reads", "holds": "holds"}
        res["rx_contract"] = {k: int(v) for k, v in expected.items()}
        valid = bool(contract and summary) and set(expected) == set(pairs)
        valid = valid and all(actual.get(pairs[k]) == int(v) for k, v in expected.items())
        valid = valid and actual.get("finalized") == 1 and actual.get("errors") == 0
        valid = valid and actual.get("state_checks", 0) > 0 and actual.get("status_compares", 0) > 0
        if valid:
            frames, pops, drops = int(expected["frames"]), int(expected["pops"]), int(expected["rejects"])
            valid = frames > 0 and pops > 0 and int(expected["holds"]) > 0
            valid = valid and all(actual.get(k) == frames for k in ("sent", "pin_started", "pin_completed", "pin_compares"))
            flushed = res.get("rx_stage2", {}).get("flushed", 0)
            valid = valid and actual.get("data_compares") == pops and actual.get("accepted") == pops + flushed
            valid = valid and actual.get("accepted", 0) + actual.get("rejected", 0) == frames
            valid = valid and 0 < actual.get("max_occupancy", 0) <= 16 and actual.get("overflow_hits") == drops
            if drops:
                valid = valid and actual.get("max_occupancy") == 16 and actual.get("boundary15", 0) > 0 and actual.get("boundary16", 0) > 0
        if not valid and res["status"] == "PASS":
            res.update(status="FAIL", reason="missing/unmet RX FIFO completion/check contract")
        stage2_test = re.search(r"Running test test_rx_fifo_(tp0[456])", text)
        if stage2_test:
            scenario = stage2_test.group(1)
            s = res.get("rx_stage2", {})
            levels = {r["rxt"]: r for r in res.get("rxt_hits", [])}
            sources = {(r["source"], r["ie"]): r["hits"] for r in res.get("ie_hits", [])}
            valid = bool(stage2_summary) and len(levels) == 4 and len(sources) == 12
            valid = valid and all(s.get(k, 0) > 0 for k in ("raw_compares", "masked_compares", "con_compares", "ie_compares", "rxf_rises", "rxf_falls"))
            valid = valid and s.get("flushed") == s.get("required_flushed") == (16 if scenario == "tp06" else 0)
            if valid and scenario == "tp04":
                valid = all(all(levels[r].get(k) == 1 for k in ("below", "at", "down"))
                            and levels[r].get("above") == (0 if r == 0 else 1)
                            and levels[r].get("dynamic", 0) > 0 for r in range(4))
                valid = valid and s["rxf_rises"] >= 6 and s["rxf_falls"] >= 6
            if valid and scenario == "tp05":
                valid = all(levels[r].get("capacity") == 1 and levels[r].get("continued") == 16-(16>>r) for r in (1, 2, 3))
                valid = valid and s.get("ov_rises") == 0
            if valid and scenario == "tp06":
                valid = all(sources.get((src, ie), 0) >= 2 for src in (2, 4, 6) for ie in (0, 2, 4, 6))
                valid = valid and s.get("ie_compares", 0) >= 31 and s.get("ov_rises") == s.get("ov_falls") == 2
            if not valid and res["status"] == "PASS":
                res.update(status="FAIL", reason="missing/unmet Stage2 transition/source/enable hit contract")
    return res


def run_one(a, plat: Platform, test: str, seed: int) -> dict:
    env = plat.env()
    name = test if test.startswith("test_") else f"test_{ident(test)}"
    run_id = f"{name}.s{seed}.{time.time_ns()}.{uuid.uuid4().hex[:6]}"
    cwd = BUILD / "runs" / run_id
    cwd.mkdir(parents=True, exist_ok=False)
    log = cwd / "simulator.log"
    coverage_file = cwd / ("coverage.dat" if a.sim == "verilator" else "coverage.ucdb")
    manifest_file = BUILD / "build_manifest.json"
    if not manifest_file.exists():
        return {"test": name, "seed": seed, "status": "FAIL", "reason": "missing build manifest; rebuild in an isolated --build-dir", "wall": 0}
    manifest = json.loads(manifest_file.read_text())
    if manifest["sources"] != source_hashes() or any(manifest[k] != getattr(a, k) for k in ("sim", "wave", "cov")):
        return {"test": name, "seed": seed, "status": "FAIL", "reason": "stale source/build options; rebuild", "wall": 0}
    t0 = time.time()
    if a.sim == "verilator":
        exe = exe_path(a, plat)
        if not exe.is_file():
            return {"test": name, "seed": seed, "status": "FAIL", "reason": "not built (run: build)", "wall": 0}
        if hashlib.sha256(exe.read_bytes()).hexdigest() != manifest.get("binary_sha256"):
            return {"test": name, "seed": seed, "status": "FAIL", "reason": "binary hash differs from build manifest", "wall": 0}
        cmd = [str(exe), f"+UVM_TESTNAME={name}", f"+UVM_VERBOSITY={a.verbosity}", f"+verilator+seed+{seed}",
               "+verilator+rand+reset+2", f"+TIMEOUT_NS={a.timeout_ns}", "+UVM_NO_RELNOTES"]
        if a.cov:
            cmd.append(f"+verilator+coverage+file+{posix(coverage_file)}")
    else:
        vsim = plat.which(["vsim", "vsim.exe"], env)
        if not vsim:
            for d in plat.questa_dirs:
                if d and (Path(d) / f"vsim{plat.exe}").is_file():
                    vsim = str(Path(d) / f"vsim{plat.exe}")
        if not vsim:
            return {"test": name, "seed": seed, "status": "FAIL", "reason": "vsim not found", "wall": 0}
        work = BUILD / "questa" / "work"
        do = "run -all; quit -f" if not a.cov else f"coverage save -onexit {posix(coverage_file)}; run -all; quit -f"
        (BUILD / "cov").mkdir(parents=True, exist_ok=True)
        cmd = [vsim, "-c", "-novopt", "-work", posix(work), "work.testTop", f"+UVM_TESTNAME={name}", f"+UVM_VERBOSITY={a.verbosity}",
               f"+TIMEOUT_NS={a.timeout_ns}", "-sv_seed", str(seed), *(["-coverage"] if a.cov else []), "-do", do]
    cmd.extend("+" + value.lstrip("+") for value in a.plusarg)
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / "command.json").write_text(json.dumps({"command": cmd, "cwd": str(cwd), "build_manifest": str(manifest_file), "seed": seed}, indent=2), encoding="utf-8")
    rc, out = run_cmd(cmd, env, cwd, log, timeout=a.wall_timeout)
    res = parse_result(out, rc, rc == 124)
    res.update({"test": name, "seed": seed, "wall": round(time.time() - t0, 1), "sim_exit": rc,
                "log": posix(log.relative_to(ROOT)), "run_dir": posix(cwd.relative_to(ROOT)),
                "wave": posix((cwd / "wave.vcd").relative_to(ROOT)) if (cwd / "wave.vcd").exists() else None})
    res["build_identity"] = {"manifest": posix(manifest_file.relative_to(ROOT)),
                             "manifest_sha256": hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
                             "binary_sha256": manifest.get("binary_sha256"), "cov": a.cov, "wave": a.wave}
    res["coverage"] = posix(coverage_file.relative_to(ROOT)) if coverage_file.exists() else None
    if a.cov and not res["coverage"] and res["status"]=="PASS":
        res.update(status="FAIL",reason="required coverage database missing")
    if name.startswith("test_rx_fifo_"):
        res["configuration"] = {"direction": "UART0->UART1", "pclk_ns": [50, 86], "BR": [130, 75],
                                "EN": 1, "D9": 0, "EP": 0, "TXT": 0, "RXT": 0, "IE": 0, "capacity": 16,
                                "timeout_ns": a.timeout_ns, "plusargs": a.plusarg,
                                "values_are": "test configuration contract",
                                "setup_checkpoint_reached": "[RX_MILESTONE] initial_empty" in out}
        if name in ("test_rx_fifo_tp04", "test_rx_fifo_tp05", "test_rx_fifo_tp06", "test_rx_fifo_tp07"):
            res["configuration"].update(RXT="runtime shadow; see RXT hits and milestones",
                                        IE="0/2/4/6 plus reserved high bits" if name.endswith("tp06") else 0,
                                        EN="1; bounded quiet disable for OV-only setup" if name.endswith("tp06") else 1)
            if name.endswith("tp07"):
                res["configuration"].update(RXT="11 then 01 (2 then 8)",IE="0/2/4/6; see IRQ checkpoints")
    elif name == "test_baudrate_9600_complete":
        res["configuration"] = {"direction":"UART0->UART1", "pclk_ns":[50,86], "BR":[130,75],
            "EN":1,"D9":0,"EP":0,"TXT":0,"RXT":0,"IE":0,"frames":24,
            "scoreboard":"legacy ordered queue with COMPLETE_CHECK pending=0",
            "timeout_ns":a.timeout_ns,"plusargs":a.plusarg}
    (cwd / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def cmd_run(a, plat: Platform) -> int:
    r = run_one(a, plat, a.test, a.seed)
    print(f"{r['status']:4s} {r['test']} seed={r['seed']} {r['wall']}s {r.get('reason', '')}  log: {r.get('log', '')}")
    return 0 if r["status"] == "PASS" else 1


def cmd_regress(a, plat: Platform) -> int:
    names = test_names() if a.tests == "all" else [t.strip() for t in a.tests.split(",") if t.strip()]
    seeds = [int(s) for s in a.seeds.split(",")]
    jobs = [(t, s) for t in names for s in seeds]
    print(f"regress: {len(jobs)} run(s), {a.jobs} in parallel, simulator {a.sim}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(run_one, a, plat, t, s): (t, s) for t, s in jobs}
        for f in cf.as_completed(futs):
            r = f.result()
            results.append(r)
            print(f"  {r['status']:4s} {r['test']:55s} seed={r['seed']} {r['wall']:>6}s {r.get('reason', '')}", flush=True)
    results.sort(key=lambda r: (r["test"], r["seed"]))
    npass = sum(r["status"] == "PASS" for r in results)
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "regress_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = ["| Test | Seed | Result | Wall s | Compares OK | Reason |", "|---|---:|---|---:|---:|---|"]
    lines += [f"| {r['test']} | {r['seed']} | {r['status']} | {r['wall']} | {r.get('compares_ok', '')} | {r.get('reason', '')} |" for r in results]
    lines += ["", f"{npass} of {len(results)} run(s) passed."]
    (BUILD / "regress_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"regress: {npass} of {len(results)} passed; summary in build/regress_summary.md")
    return 0 if npass == len(results) else 1


def cmd_cov(a, plat: Platform) -> int:
    env = plat.env()
    manifest_file = BUILD / "build_manifest.json"
    if not manifest_file.exists():
        print("cov: FAIL (missing build manifest)")
        return 1
    manifest = json.loads(manifest_file.read_text())
    if not manifest.get("cov") or manifest["sources"] != source_hashes():
        print("cov: FAIL (un-instrumented or stale build)")
        return 1
    identity = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    inputs, excluded = [], []
    for result_file in sorted((BUILD / "runs").glob("*/result.json")):
        r = json.loads(result_file.read_text())
        valid = r.get("status") == "PASS" and r.get("sim_exit") == 0
        valid = valid and r.get("build_identity", {}).get("manifest_sha256") == identity
        valid = valid and r.get("coverage") and (ROOT / r["coverage"]).is_file()
        valid = valid and not any("SELFTEST" in p or "IRQ_FAULT=" in p for p in r.get("configuration", {}).get("plusargs", []))
        if valid:
            p = ROOT / r["coverage"]
            inputs.append({"file": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "result": str(result_file)})
        else:
            excluded.append(str(result_file))
    if not inputs:
        print("cov: NOT_RUN (no qualified current-build PASS databases)")
        return 2
    cov = BUILD / "cov" / ("merge-" + str(time.time_ns()))
    cov.mkdir(parents=True, exist_ok=False)
    (cov / "inputs.json").write_text(json.dumps({"build_manifest_sha256": identity, "inputs": inputs, "excluded": excluded}, indent=2))
    if a.sim == "verilator":
        tool = plat.which(plat.coverage_names, env)
        dats = [x["file"] for x in inputs]
        if not tool or not dats:
            print("cov: NOT_RUN (needs verilator_coverage and .dat files; build and run with --cov)")
            return 2
        merged = cov / "merged.dat"
        rc, _ = run_cmd([tool, "--write", posix(merged), *map(posix, dats)], env, ROOT, cov / "merge.log")
        if rc != 0:
            return 1
        # This build collects functional bins. Export without reopening source:
        # 5.052 annotation mishandles encoded non-ASCII workspace paths.
        rc, out = run_cmd([tool, "--write-info", posix(cov / "functional.info"), posix(merged)], env, ROOT, cov / "report.log")
        print(f"cov: merged {len(dats)} qualified run(s); native bins: {posix(merged)}; export: {posix(cov / 'functional.info')}")
        print("   " + "\n   ".join(out.strip().splitlines()[:6]))
        return 0 if rc == 0 else 1
    vcover = plat.which(["vcover", "vcover.exe"], env)
    ucdbs = [x["file"] for x in inputs]
    if not vcover or not ucdbs:
        print("cov: NOT_RUN (needs vcover and .ucdb files)")
        return 2
    rc, _ = run_cmd([vcover, "merge", posix(cov / "merged.ucdb"), *map(posix, ucdbs)], env, ROOT, cov / "merge.log")
    if rc != 0:
        return 1
    rc, _ = run_cmd([vcover, "report", "-html", "-htmldir", posix(cov / "html"), "-code", "bcestf", "-cvg", posix(cov / "merged.ucdb")], env, ROOT)
    print("cov: report in build/cov/html")
    return rc


def cmd_fetch_uvm(a, plat: Platform) -> int:
    dest = Path(a.uvm_home or plat.uvm_candidates[0])
    if dest.exists():
        print(f"fetch-uvm: {dest} exists; it is not overwritten")
        return 1
    git = plat.which(["git"], plat.env())
    if not git:
        print("fetch-uvm: git not found")
        return 2
    rc, out = run_cmd([git, "clone", "--depth", "1", "--branch", UVM_TAG, UVM_REPO, str(dest)], plat.env())
    print(f"fetch-uvm: {'installed ' + UVM_TAG + ' at ' + str(dest) if rc == 0 else 'FAILED'}")
    if rc != 0:
        print(out[-400:])
    return rc


def cmd_clean(_a, _p) -> int:
    shutil.rmtree(BUILD, ignore_errors=True)
    print("clean: build/ removed")
    return 0


COMMANDS = {"doctor": cmd_doctor, "lint": cmd_lint, "check": cmd_check, "gen": cmd_gen, "build": cmd_build, "run": cmd_run,
            "regress": cmd_regress, "cov": cmd_cov, "fetch-uvm": cmd_fetch_uvm, "clean": cmd_clean}


def main() -> int:
    global BUILD
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=list(COMMANDS))
    ap.add_argument("--platform", default=os.environ.get("PLATFORM", "auto"), choices=["auto", "windows", "linux"])
    ap.add_argument("--sim", default=os.environ.get("SIM", "verilator"), choices=["verilator", "questa"])
    ap.add_argument("--uvm-home", default=None)
    ap.add_argument("--test", default="trialPat")
    ap.add_argument("--tests", default="all", help="'all' or a comma list of pattern names")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seeds", default="1", help="comma list for regress")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--timeout-ns", type=int, default=100_000_000, help="simulated time limit of a test (+TIMEOUT_NS)")
    ap.add_argument("--wall-timeout", type=int, default=1800, help="wall-clock limit of one run in seconds")
    ap.add_argument("--verbosity", default="UVM_LOW")
    ap.add_argument("--cov", action="store_true")
    ap.add_argument("--wave", action="store_true", help="Verilator: write build/verilator/wave.vcd")
    ap.add_argument("--strict", action="store_true", help="lint: warnings fail")
    ap.add_argument("--build-dir", default="build", help="isolated build/evidence root, relative to project or absolute")
    ap.add_argument("--plusarg", action="append", default=[], help="extra simulator plusarg (repeatable)")
    a = ap.parse_args()
    BUILD = (ROOT / a.build_dir).resolve()
    plat = Platform(a.platform)
    return COMMANDS[a.command](a, plat)


if __name__ == "__main__":
    sys.exit(main())
