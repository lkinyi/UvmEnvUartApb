#!/usr/bin/env python3
"""Bounded, serial Stage3 regression and audited functional-coverage merge.

WSL: source scripts/env_local.sh; python3 scripts/rx_fifo_stage3.py --root NEW_ROOT
No existing build is overwritten. Expected IRQ failures never contribute coverage.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
EVENTS=[
 'fifo_empty','fifo_nonempty','occupancy_15','occupancy_16','enqueue','dequeue',
 'empty_read','full_reject','ov_set','ov_hold','ov_clear','ordered_read',
 'write_pointer_31_to_0','read_pointer_31_to_0',
 'rxt_00','rxt_01','rxt_10','rxt_11',
 'below_T_rxt00','below_T_rxt01','below_T_rxt10','below_T_rxt11',
 'at_T_rxt00','at_T_rxt01','at_T_rxt10','at_T_rxt11',
 'above_T_rxt01','above_T_rxt10','above_T_rxt11','rxf_rise','rxf_fall',
 'receive_above_watermark','ie_off','ie_on','raw_active_masked_off',
 'raw_active_masked_on','ie_changed_raw_stable','masked_rxf_only',
 'masked_ov_only','masked_both','irq_rise','irq_hold','irq_fall',
 'irq_both_sources','remove_OV_keep_RXF_IRQ','irq_rise_correct_clock',
 'irq_fall_correct_clock','concurrent_read_receive','reset_recovery',
 'parity_error','frame_error','reverse_direction']
DEFERRED={47:'同拍收读仲裁本阶段未实施',48:'仅初始复位；非运行中复位恢复',
          49:'完整Parity Error注入不在本阶段范围',50:'完整Frame Error注入不在本阶段范围',
          51:'反向UART1→UART0不在本阶段范围'}
POSITIVE=[('TP07','rx_fifo_tp07'),('TP01','rx_fifo_tp01'),('TP02','rx_fifo_tp02'),
 ('TP03a','rx_fifo_tp03a'),('TP03b','rx_fifo_tp03b'),('TP04','rx_fifo_tp04'),
 ('TP05','rx_fifo_tp05'),('TP06','rx_fifo_tp06'),
 ('legacy_complete','baudrate_9600_complete'),('observation_smoke','rx_fifo_observation_smoke')]
NEGATIVE=[('negative_'+m,'rx_fifo_tp07',m) for m in ('missing','stuck','early','late','merge')]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def records(path):
    rows=[]
    for line in path.read_text().splitlines():
        m=re.fullmatch(r"C '(.*)' (\d+)",line)
        if not m: continue
        fields=dict(part.split('\x02',1) for part in m[1].split('\x01') if '\x02' in part)
        if fields.get('t')=='covergroup': rows.append(dict(fields,hits=int(m[2])))
    return rows

def merge_coverage(evidence, suite, results, command, manifest_path):
    manifest=json.loads(manifest_path.read_text()); mh=sha(manifest_path)
    eligible=[]; excluded=[]; counters=[0]*52; cross_counts={f'{s}:{i}':0 for s in (2,4,6) for i in (0,2,4,6)}
    for row in results:
        a=row['actual']; reason=None
        if row['expected_status']!='PASS': reason='expected-failure checker selftest'
        elif row['acceptance']!='PASS' or a['status']!='PASS' or row['make_exit']!=0: reason='not a successful run'
        elif a.get('build_identity',{}).get('manifest_sha256')!=mh: reason='different build identity'
        elif not a.get('coverage') or not (ROOT/a['coverage']).is_file(): reason='missing coverage database'
        if reason:
            excluded.append(dict(label=row['label'],reason=reason)); continue
        p=ROOT/a['coverage']
        if a.get('sim_exit')!=0 or not a['build_identity'].get('cov'):
            raise RuntimeError('invalid simulator exit/coverage instrumentation')
        eligible.append(dict(label=row['label'],file=str(p),sha256=sha(p),build_manifest_sha256=mh))
        for k,v in a.get('functional_events',{}).items(): counters[int(k)]+=v
        for k,v in a.get('functional_cross',{}).items(): cross_counts[k]+=v
    if not eligible: raise RuntimeError('No qualified coverage inputs')
    cov=suite/'functional-coverage'; cov.mkdir()
    (cov/'inputs.json').write_text(json.dumps(dict(eligible=eligible,excluded=excluded),indent=2))
    merged=cov/'merged.dat'
    if command('coverage_merge',['verilator_coverage','--write',str(merged),*[x['file'] for x in eligible]]):
        raise RuntimeError('coverage merge failed')
    if command('coverage_info',['verilator_coverage','--write-info',str(cov/'functional.info'),str(merged)]):
        raise RuntimeError('coverage export failed')
    all_data=records(merged)
    data=[x for x in all_data if x.get('f','').endswith('cRxFunctionalCoverage.sv')]
    other_models=[x for x in all_data if x not in data]
    semantic={}
    for row in data:
        m=re.fullmatch(r'event_bin\[(\d+)\]',row.get('bin',''))
        if m: semantic[int(m[1])]=semantic.get(int(m[1]),0)+row['hits']
    if len(semantic)!=52: raise RuntimeError(f'Expected 52 exported semantic bins, got {len(semantic)}')
    if any(semantic[i]!=counters[i] for i in range(52)):
        raise RuntimeError('Tool functional bins disagree with independently logged hit counts')
    event_rows=[dict(id=i,name=name,hits=semantic[i],in_scope=i not in DEFERRED,
                     reason=DEFERRED.get(i,'')) for i,name in enumerate(EVENTS)]
    missed=[x for x in event_rows if x['hits']==0]
    other=[x for x in data if 'event_bin[' not in x.get('bin','')]
    # The meaningful 3x4 Raw/IE grid also exports its 3+4 marginal bins.
    if len(other)!=19: raise RuntimeError(f'Expected 19 source/IE bins including 12 cross bins, got {len(other)}')
    source_names={'rxf':2,'ov':4,'both':6}; ie_names={'off':0,'rxf':2,'ov':4,'both':6}
    for row in other:
        if row.get('cross')=='1':
            s,i=row['Cb'].split(',')
            if row['hits']!=cross_counts[f'{source_names[s]}:{ie_names[i]}']:
                raise RuntimeError('Tool cross bin disagrees with logged source/IE hit count')
    hit=sum(x['hits']>0 for x in data); scope=[x for x in event_rows if x['in_scope']]
    report=dict(kind='SystemVerilog covergroup/coverpoint/cross; Verilator --coverage-user',
      tool_bins_hit=hit,tool_bins_total=len(data),tool_percent=round(100*hit/len(data),4),
      scoped_semantic_hit=sum(x['hits']>0 for x in scope),scoped_semantic_total=len(scope),
      semantic=event_rows,source_ie_bins=other,unhit=missed,
      separate_existing_protocol_covergroups=other_models,
      all_tool_covergroup_bins=dict(hit=sum(x['hits']>0 for x in all_data),total=len(all_data)),
      in_scope_unhit=[x for x in missed if x['in_scope']],
      excluded_unreachable=[dict(name='RXT00 T+1',reason='T=16，17项超出物理容量；第17帧按拒收覆盖')],
      merge_inputs=str(cov/'inputs.json'),merged_sha256=sha(merged),
      counter_reconciliation='all 52 event bins and all 12 cross bins equal qualified per-run logged counters')
    (cov/'coverage.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    (cov/'unhit.json').write_text(json.dumps(missed,indent=2,ensure_ascii=False))
    lines=['# Functional Coverage', '',f"工具功能覆盖：{hit}/{len(data)} = {report['tool_percent']}%。",
      f"阶段内语义事件：{report['scoped_semantic_hit']}/{len(scope)}。有效分母及未实施项目均在下表保留。",
      '代码覆盖率未启用，不进入此分母；计数已与原始 coverage.dat 逐 bin 核对。','',
      '| ID | 事件 | 命中数 | 范围/原因 |','|---|---|---:|---|']
    lines += [f"| {x['id']} | {x['name']} | {x['hits']} | {x['reason'] or '本阶段'} |" for x in event_rows]
    lines += ['', '| Raw/IE bin | 命中数 |','|---|---:|']
    lines += [f"| {x['h']} | {x['hits']} |" for x in other]
    (cov/'coverage.md').write_text('\n'.join(lines)+'\n')
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True); ap.add_argument('--build-name',default='build-01')
    ap.add_argument('--skip-build',action='store_true'); ap.add_argument('--tests',default='all')
    a=ap.parse_args(); evidence=(ROOT/a.root).resolve(); evidence.mkdir(parents=True,exist_ok=True)
    build=evidence/a.build_name; suite=evidence/('suite-'+str(time.time_ns())); suite.mkdir()
    common=['make',f'BUILD_DIR={build}','WAVE=1','COV=1','JOBS=2','SEED=1']
    def command(label,args):
        start=time.time()
        with (suite/(label+'.console.txt')).open('w') as f:
            p=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,text=True)
        (suite/(label+'.command.json')).write_text(json.dumps(dict(command=args,cwd=str(ROOT),
          exit=p.returncode,wall_s=round(time.time()-start,3)),indent=2))
        print(f'{label}: exit={p.returncode} wall={time.time()-start:.1f}s',flush=True)
        if p.returncode: print((suite/(label+'.console.txt')).read_text()[-2200:],flush=True)
        return p.returncode
    env=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,
      UVM_HOME=os.environ.get('UVM_HOME'),VERILATOR_ROOT=os.environ.get('VERILATOR_ROOT'))
    for key,cmd in [('verilator',['verilator','--version']),('gcc',['g++','--version']),
      ('head',['git','rev-parse','HEAD']),('branch',['git','branch','--show-current']),
      ('git_status',['git','status','--porcelain=v1','--untracked-files=all']),
      ('uvm_head',['git','-C',os.environ.get('UVM_HOME','.'),'rev-parse','HEAD']),
      ('questa',['bash','-c','command -v vsim && vsim -version'])]:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        env[key]=dict(exit=p.returncode,output=p.stdout.strip(),stderr=p.stderr.strip())
    (suite/'environment.json').write_text(json.dumps(env,indent=2))
    print('SUITE '+str(suite),flush=True)
    if not a.skip_build:
        if build.exists(): raise SystemExit('Refusing to overwrite existing build')
        if command('build',common+['build']): return 1
    mf=build/'build_manifest.json'; m=json.loads(mf.read_text())
    if not m['cov'] or not m['wave'] or '--coverage-user' not in m['command'] or m['build_exit']!=0:
        raise SystemExit('Build lacks required functional coverage/wave instrumentation')
    # uartvip additionally checks every compile input and the binary before each run.
    cases=[(l,t,None) for l,t in POSITIVE[:1]]+NEGATIVE+[(l,t,None) for l,t in POSITIVE[1:]]
    if a.tests!='all':
        wanted=set(a.tests.split(','))
        if wanted-{x[0] for x in cases}: raise SystemExit('Unknown tests')
        cases=[x for x in cases if x[0] in wanted]
    results=[]
    for label,test,fault in cases:
        before=set((build/'runs').glob('*/result.json'))
        rc=command(label,common+['run',f'TEST={test}']+([f'PLUSARGS=IRQ_FAULT={fault}'] if fault else []))
        new=set((build/'runs').glob('*/result.json'))-before
        actual=json.loads(next(iter(new)).read_text()) if len(new)==1 else dict(status='FAIL',reason='missing/ambiguous result')
        irq=actual.get('irq',{}); log=(ROOT/actual['log']).read_text() if actual.get('log') else ''
        if fault:
            allowed=['[RX_DUT_IRQ]','[RX_ENV_IRQ_COUNTS]']
            # Successful-transition hit counters intentionally omit the one
            # corrupted sample. Assert the exact resulting deficit, rather
            # than accepting arbitrary missing coverage or unrelated errors.
            expected_counts={'missing':(3,4,1),'stuck':(4,3,1),'early':(4,4,1),
                             'late':(3,4,1),'merge':(4,4,0)}[fault]
            if fault!='early': allowed.append('[RX_ENV_TP07_TIMING]')
            unexpected=[s for s in actual.get('error_messages',[]) if not any(tag in s for tag in allowed)]
            ok=rc!=0 and actual['status']=='FAIL' and irq.get('faults')==1 and irq.get('errors')==1
            ok=ok and tuple(irq.get(k) for k in ('rises','falls','merge_holds'))==expected_counts
            ok=ok and '[RX_DUT_IRQ]' in log and f'mode={fault} ' in log and not unexpected
            if fault=='merge': ok=ok and 'event=OV_removed_RXF_holds' in log
        else:
            unexpected=actual.get('error_messages',[])
            ok=rc==0 and actual['status']=='PASS' and actual.get('coverage') and actual.get('sim_exit')==0
            if test.startswith('rx_fifo_'):
                ok=ok and irq.get('cycles',0)>0 and irq.get('errors')==0 and len(actual.get('functional_events',{}))==52
            if label=='legacy_complete':
                ok=ok and actual.get('compares_ok')==24 and 'pending_tx=0 pending_rx=0' in log
        row=dict(label=label,expected_status='FAIL' if fault else 'PASS',fault=fault,make_exit=rc,
          acceptance='PASS' if ok else 'FAIL',unexpected_errors=unexpected,actual=actual)
        results.append(row); (suite/'results.json').write_text(json.dumps(results,indent=2))
        print(f'ACCEPTANCE {label}: {row["acceptance"]} actual={actual["status"]}',flush=True)
    coverage=None
    if a.tests=='all': coverage=merge_coverage(evidence,suite,results,command,mf)
    ok=all(x['acceptance']=='PASS' for x in results)
    if coverage: ok=ok and not coverage['in_scope_unhit']
    inventory=[]
    normal_results={x['actual'].get('test','').removeprefix('test_'):x for x in results if x['expected_status']=='PASS'}
    for d in sorted((ROOT/'pat').iterdir()):
        if not d.is_dir(): continue
        status='SKIP' if (d/'SKIP').exists() else ('PASS' if normal_results[d.name]['acceptance']=='PASS' else 'FAIL') if d.name in normal_results else 'NOT_RUN'
        if (d/'SKIP').exists(): status='SKIP'
        inventory.append(dict(test=d.name,current_regression=status,historical_status='FAIL' if d.name=='baudrate_9600' else 'see Stage1/2 and source audit',
          reason=(d/'SKIP').read_text() if status=='SKIP' else ('historical unfinished 24-write/16-read pattern; not rerun' if d.name=='baudrate_9600' else 'outside explicit bounded suite' if status=='NOT_RUN' else '')))
    (suite/'pattern-inventory.json').write_text(json.dumps(inventory,indent=2))
    final=dict(status='PASS' if ok else 'FAIL',real_simulation=True,build_manifest=str(mf),
      positive={s:sum(x['actual']['status']==s for x in results if x['expected_status']=='PASS') for s in ('PASS','FAIL')},
      negative_selftests=dict(executed=sum(x['expected_status']=='FAIL' for x in results),
        expected_FAIL_detected=sum(x['expected_status']=='FAIL' and x['acceptance']=='PASS' for x in results)),
      inventory_counts={s:sum(x['current_regression']==s for x in inventory) for s in ('PASS','FAIL','SKIP','NOT_RUN')},
      results=str(suite/'results.json'),coverage_report=str(suite/'functional-coverage/coverage.json') if coverage else None)
    (suite/'suite_result.json').write_text(json.dumps(final,indent=2))
    lines=['| Test | seed | actual | acceptance | seconds | data compares | IRQ cycles/errors | make/sim exit |',
      '|---|---:|---|---|---:|---:|---|---|']
    for x in results:
        q=x['actual'];irq=q.get('irq',{})
        lines.append(f"| {x['label']} | {q.get('seed')} | {q['status']} | {x['acceptance']} | {q.get('wall')} | {q.get('compares_ok')} | {irq.get('cycles','N/A')}/{irq.get('errors','N/A')} | {x['make_exit']}/{q.get('sim_exit')} |")
    (suite/'results.md').write_text('\n'.join(lines)+'\n')
    print('STAGE3 '+final['status']+': '+str(suite),flush=True)
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
