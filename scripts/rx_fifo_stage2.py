#!/usr/bin/env python3
"""Stage2 ordered real-simulation acceptance, with immutable per-run artifacts.

Run from WSL after sourcing scripts/env_local.sh. An existing build is used
only with --skip-build; uartvip still verifies its sources/options/binary hash.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--build-name', default='build-01')
    ap.add_argument('--skip-build', action='store_true')
    ap.add_argument('--tests', default='all', help='all or comma-separated labels')
    a = ap.parse_args()
    evidence = (ROOT/a.root).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    build = evidence/a.build_name
    suite = evidence/('suite-'+str(time.time_ns()))
    suite.mkdir()
    common = ['make', f'BUILD_DIR={build}', 'WAVE=1', 'JOBS=2', 'SEED=1']

    def command(label, args):
        start = time.time()
        with (suite/(label+'.console.txt')).open('w') as f:
            p = subprocess.run(args, cwd=ROOT, text=True, stdout=f, stderr=subprocess.STDOUT)
        (suite/(label+'.command.json')).write_text(json.dumps(dict(command=args, cwd=str(ROOT),
            make_exit=p.returncode, wall_s=round(time.time()-start, 3)), indent=2))
        print(f'{label}: exit={p.returncode} wall={time.time()-start:.1f}s', flush=True)
        if p.returncode: print((suite/(label+'.console.txt')).read_text()[-4000:], flush=True)
        return p.returncode

    env = dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(), python=sys.version,
               UVM_HOME=os.environ.get('UVM_HOME'), VERILATOR_ROOT=os.environ.get('VERILATOR_ROOT'))
    for key, cmd in [('verilator',['verilator','--version']), ('gcc',['g++','--version']),
                     ('head',['git','rev-parse','HEAD']), ('branch',['git','branch','--show-current']),
                     ('git_status',['git','status','--porcelain=v1','--untracked-files=all']),
                     ('uvm_head',['git','-C',os.environ.get('UVM_HOME','.'),'rev-parse','HEAD'])]:
        p = subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        env[key] = dict(exit=p.returncode,output=p.stdout.strip())
    (suite/'environment.json').write_text(json.dumps(env,indent=2))
    print(f'SUITE {suite}',flush=True)
    if not a.skip_build:
        if build.exists(): raise SystemExit('Refusing to overwrite existing build; choose --build-name')
        if command('build',common+['build']): return 1
    cases = [('TP04','rx_fifo_tp04',[],None), ('TP05','rx_fifo_tp05',[],None),
             ('TP06','rx_fifo_tp06',[],None), ('observation_smoke','rx_fifo_observation_smoke',[],None),
             ('TP01','rx_fifo_tp01',[],None), ('TP02','rx_fifo_tp02',[],None),
             ('TP03a','rx_fifo_tp03a',[],None), ('TP03b','rx_fifo_tp03b',[],None),
             ('legacy_complete','baudrate_9600_complete',[],None),
             ('negative_protocol','rx_fifo_observation_smoke',['PLUSARGS=PROTOCOL_CHECKER_SELFTEST'],'[APB_PROTOCOL]'),
             ('negative_uart_glitch','rx_fifo_observation_smoke',['PLUSARGS=UART_CHECKER_SELFTEST'],'[UART_PROTOCOL]'),
             ('negative_expectation','rx_fifo_observation_smoke',['PLUSARGS=RX_EXPECTATION_SELFTEST'],'[READ FAIL]'),
             ('negative_global_timeout','rx_fifo_observation_smoke',['TIMEOUT_NS=1000'],'[CTEST TIMEOUT]'),
             ('negative_missing_frame','rx_fifo_observation_smoke',['PLUSARGS=RX_MISSING_FRAME_SELFTEST'],'[RX_DUT_FRAME_TIMEOUT]')]
    if a.tests!='all':
        selected=set(a.tests.split(','))
        unknown=selected-{c[0] for c in cases}
        if unknown: raise SystemExit('Unknown/empty test labels: '+','.join(sorted(unknown)))
        cases=[c for c in cases if c[0] in selected]
    results=[]
    for label,test,extra,expected_error in cases:
        before=set((build/'runs').glob('*/result.json'))
        rc=command(label,common+['run',f'TEST={test}']+extra)
        new=set((build/'runs').glob('*/result.json'))-before
        actual=json.loads(next(iter(new)).read_text()) if len(new)==1 else dict(status='BLOCKED',reason='missing/ambiguous result')
        log=(ROOT/actual['log']).read_text(errors='replace') if actual.get('log') else ''
        allowed=[expected_error] if expected_error else []
        if label=='negative_global_timeout': allowed+=['[RX_ENV_INCOMPLETE]','[RX_ENV_CHECK_COUNTS]']
        unexpected=[line for line in actual.get('error_messages',[]) if not any(tag in line for tag in allowed)]
        ok=(rc!=0 and actual['status']=='FAIL' and expected_error in log and not unexpected) if expected_error else (rc==0 and actual['status']=='PASS')
        if label=='legacy_complete': ok=ok and actual.get('compares_ok')==24 and '[COMPLETE_CHECK]' in log and 'pending_tx=0 pending_rx=0' in log
        if label in ('negative_protocol','negative_uart_glitch'): ok=ok and '[UART_CHK_CHECKER]' in log
        if label=='negative_expectation': ok=ok and 'Expected data: 00000068, Actual data: 00000069' in log
        row=dict(label=label,expected_status='FAIL' if expected_error else 'PASS',expected_error=expected_error,
                 make_exit=rc,acceptance='PASS' if ok else 'FAIL',unexpected_errors=unexpected,actual=actual)
        results.append(row)
        (suite/'results.json').write_text(json.dumps(results,indent=2))
        print(f'ACCEPTANCE {label}: {row["acceptance"]} actual={actual["status"]}',flush=True)
        if not ok: break
    ok=len(results)==len(cases) and all(r['acceptance']=='PASS' for r in results)
    final=dict(status='PASS' if ok else 'FAIL',cases_required=len(cases),cases_executed=len(results),results=str(suite/'results.json'))
    (suite/'suite_result.json').write_text(json.dumps(final,indent=2))
    print(f'STAGE2 {final["status"]}: {suite}',flush=True)
    return 0 if ok else 1


if __name__=='__main__': raise SystemExit(main())
