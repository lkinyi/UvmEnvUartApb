#!/usr/bin/env python3
"""Independently reconstruct TP07 FIFO/IE/RXT/OV and exact #1 IRQ VCD timing.
No DUT Raw, Masked, pointers, WE, or IRQ creates a prediction.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

def audit(path):
    frames=[0x31,0x72,0xa6,0x59]+[(i*9+5)&255 for i in range(16)]+[0xfd]+[(i*13+19)&255 for i in range(16)]+[0xfc]
    queue=deque(); en=0; rxt=0; ie=0; ov=0; wptr=0; rptr=0
    counts=dict(completed=0,accepted=0,rejected=0,popped=0,empty_reads=0)
    required=dict(completed=38,accepted=36,rejected=2,popped=36,empty_reads=0)
    errors=[]; error_count=0; cycles=0; groups=0; transitions=[]; events=[]; merge_hits=0
    ideal_irq=0; pending=None; expected_change_time=None
    scope=[]; variables={}; values={}; before={}; now=0
    def check(ok,detail):
        nonlocal error_count
        if not ok:
            error_count+=1
            if len(errors)<30: errors.append(dict(time_ns=now,detail=detail))
    with path.open() as fh:
        for line in fh:
            f=line.split()
            if not f: continue
            if f[0]=='$scope': scope.append(f[2])
            elif f[0]=='$upscope': scope.pop()
            elif f[0]=='$var': variables['.'.join(scope+[f[4]])]=f[3]
            elif f[0]=='$timescale':
                if len(f)>1: check(f[1:] in (['1ns','$end'],['1','ns','$end']),'VCD timescale must be 1ns')
            elif f[0]=='$enddefinitions': break
        base='TOP.testTop.dut_top'
        if base+'.pclk_1' not in variables: base='testTop.dut_top'
        signals={k:variables[base+'.'+k+'_1'] for k in ('pclk','preset_n','psel','penable','pready','pwrite','paddr','pwdata','prdata','ctrl_if')}
        for k in ('rx_complete','rx_fifo_we','rx_fifo_re','rx_fifo_full','rx_fifo_ov','rx_wptr','rx_rptr','rx_rxf'):
            signals[k]=variables[base+'.uart_1.receiver.'+k]
        wanted=set(signals.values())
        def consume():
            nonlocal en,rxt,ie,ov,wptr,rptr,cycles,groups,ideal_irq,pending,expected_change_time,merge_hits
            if not values or now==0: return
            def v(k,s=before): return s.get(signals[k])
            if v('preset_n',values)!=1: return
            groups+=1
            if pending is not None and now>=pending[0]:
                ideal_irq=pending[1]; pending=None
            # Compare all VCD time groups, including the interval between pclk
            # edges. An actual transition must occur at the predicted edge+1ns.
            check(v('ctrl_if',values)==ideal_irq,'IRQ differs from exact registered model')
            if v('ctrl_if')!=v('ctrl_if',values):
                check(now==expected_change_time,'IRQ transition not at receiving pclk +1ns')
                transitions.append(dict(time_ns=now,irq=v('ctrl_if',values),expected=ideal_irq))
            if v('pclk')!=0 or v('pclk',values)!=1: return
            cycles+=1; occ=len(queue); raw=1|(2 if occ>=(16>>rxt) else 0)|(4 if ov else 0)
            target=int(bool(raw&ie)); pending=(now+1,target)
            if target!=ideal_irq: expected_change_time=now+1
            check(v('rx_wptr')==wptr and v('rx_rptr')==rptr,'independent pointer mismatch')
            check(v('rx_fifo_full')==int(occ==16),'full mismatch')
            check(v('rx_rxf')==int(occ>=(16>>rxt)) and v('rx_fifo_ov')==ov,'independent RXF/OV mismatch')
            apb=all(v(k)==1 for k in ('psel','penable','pready'))
            event=None
            if apb and v('pwrite')==0:
                addr=v('paddr'); data=v('prdata')
                if addr in (20,24): check(data==(raw if addr==20 else raw&ie),'Raw/Masked read mismatch')
                if addr==16: check(data==ie,'IE readback mismatch')
                if addr==12:
                    check(not v('rx_complete'),'simultaneous read/RX outside scope')
                    if queue:
                        check(data==queue.popleft() and v('rx_fifo_re')==1,'ordered data mismatch')
                        counts['popped']+=1; rptr=(rptr+1)%32
                    else:
                        check(data>>8==0 and v('rx_fifo_re')==0,'empty read side effect')
                        counts['empty_reads']+=1
                    if ov and occ==16 and ie==6:
                        merge_hits+=1
                        check(target==1 and len(queue)==15 and len(queue)>=8,'OV removal must retain RXF IRQ')
                        event='OV_clear_RXF_remains'
                    else: event='DATA'
                    ov=0
            if v('rx_complete')==1:
                idx=counts['completed']; check(idx<len(frames),'extra completion')
                data=frames[idx] if idx<len(frames) else 0
                accept=occ<16; check(v('rx_fifo_we')==int(accept),'admission mismatch')
                counts['completed']+=1
                if accept:
                    queue.append(data); counts['accepted']+=1; wptr=(wptr+1)%32
                else: counts['rejected']+=1; ov=1
                event='accept' if accept else 'full_reject'
            check(en or not queue,'unexpected disabled FIFO contents in TP07')
            if apb and v('pwrite')==1:
                addr=v('paddr'); data=v('pwdata')
                if addr==0: rxt=(data>>2)&3;event='RXT'
                if addr==16: ie=data&31;event='IE'
                if addr==4: en=data&1;event='EN'
            if event or target!=ideal_irq:
                events.append(dict(cycle=cycles,time_ns=now,event=event,pre_occupancy=occ,pre_raw=raw,
                  registered_rhs=target,irq_at_edge=ideal_irq,post_occupancy=len(queue),post_rxt=rxt,post_ie=ie,
                  post_raw=1|(2 if len(queue)>=(16>>rxt) else 0)|(4 if ov else 0),irq_due_ns=now+1))
        for line in fh:
            s=line.strip()
            if not s: continue
            if s[0]=='#': consume();before=dict(values);now=int(s[1:])
            elif s[0] in '01xz' and s[1:] in wanted:
                values[s[1:]]=int(s[0]) if s[0] in '01' else None
            elif s[0] in 'bB':
                value,code=s[1:].split()
                if code in wanted: values[code]=int(value,2) if set(value)<={'0','1'} else None
        consume()
    checks=dict(exact_counts=counts==required,independent_comparisons=error_count==0,
      final_empty=not queue and ov==0 and ideal_irq==0,nonzero_comparisons=cycles>0 and groups>cycles,
      exact_irq_transitions=len(transitions)==8 and sum(t['irq']==1 for t in transitions)==4,
      merge_remaining_source=merge_hits==1)
    with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,error_count=error_count,errors=errors,
      counts=counts,required=required,pclk_cycles=cycles,all_time_group_checks=groups,irq_transitions=transitions,
      merged_source_hits=merge_hits,events=events,wave=str(path),wave_sha256=digest,end_ns=now)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('wave',type=Path);a=p.parse_args()
    result=audit(a.wave)
    with a.wave.with_name('stage3-wave-audit.json').open('x') as f: json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('events',)}))
    raise SystemExit(result['status']!='PASS')
