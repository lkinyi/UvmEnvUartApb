#!/usr/bin/env python3
"""Second, fixed-input comparison of Stage2 VCDs. Does not infer expected
data/admission/Raw from DUT WE/full/Raw. Online pin decoding remains separate.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path


def audit(path, scenario):
    if scenario=='tp04':
        frames=[(r*41+i*7+3)&255 for r in range(4) for i in range((16>>r)+(r!=0))]+[(i*19+5)&255 for i in range(6)]
        required=dict(completed=39,accepted=39,rejected=0,popped=39,flushed=0,empty_reads=0)
    elif scenario=='tp05':
        frames=[(r*53+i*11)&255 for r in range(1,4) for i in range(16)]
        required=dict(completed=48,accepted=48,rejected=0,popped=48,flushed=0,empty_reads=0)
    else:
        frames=[0x36,0xc9]+[v for p in range(2) for v in ([(p*61+i*17+9)&255 for i in range(16)]+[0xfe])]
        required=dict(completed=36,accepted=34,rejected=2,popped=18,flushed=16,empty_reads=1)
    counts={k:0 for k in required}
    scope=[]; variables={}; errors=[]; error_count=0
    samples=[]; commits=[]; config=[]; data_reads=[]; continued=[0]*4; capacity=[0]*4
    dynamic=[]; grid={}; ie_readbacks=[]; state_checks=0
    rxt=0; ie=0; en=0; ov=0; wptr=0; rptr=0; queue=deque()
    last_pop_before=None

    def check(condition, detail):
        nonlocal error_count
        if not condition:
            error_count+=1
            if len(errors)<20: errors.append(dict(time_ns=now,detail=detail))

    with path.open() as fh:
        for line in fh:
            f=line.split()
            if not f: continue
            if f[0]=='$scope': scope.append(f[2])
            elif f[0]=='$upscope': scope.pop()
            elif f[0]=='$var': variables['.'.join(scope+[f[4]])]=f[3]
            elif f[0]=='$enddefinitions': break
        base='TOP.testTop.dut_top'
        if base+'.pclk_1' not in variables: base='testTop.dut_top'
        signals={k:variables[base+'.'+k+'_1'] for k in ('pclk','preset_n','psel','penable','pready','pwrite','paddr','pwdata','prdata')}
        for k in ('rx_complete','rx_fifo_we','rx_fifo_re','rx_fifo_full','rx_fifo_ov','rx_wptr','rx_rptr','rx_rxf'):
            signals[k]=variables[base+'.uart_1.receiver.'+k]
        wanted=set(signals.values()); values={}; before={}; now=0

        def consume():
            nonlocal rxt,ie,en,ov,wptr,rptr,last_pop_before,state_checks
            def v(k,state=before): return state.get(signals[k])
            if v('pclk')!=0 or v('pclk',values)!=1 or v('preset_n')!=1: return
            state_checks+=1
            occ=len(queue); threshold=16>>rxt
            raw=1 | (2 if occ>=threshold else 0) | (4 if ov else 0)
            check(v('rx_wptr')==wptr and v('rx_rptr')==rptr,'independent pointer mismatch')
            check(v('rx_fifo_full')==int(occ==16),'physical full mismatch')
            check(v('rx_rxf')==int(occ>=threshold) and v('rx_fifo_ov')==ov,'RXF/OV source mismatch')
            apb=all(v(k)==1 for k in ('psel','penable','pready'))
            if apb and v('pwrite')==0:
                addr=v('paddr'); actual=v('prdata')
                if addr in (20,24):
                    expected=raw if addr==20 else raw&ie
                    check(actual==expected,'full Raw/Masked register comparison')
                    row=dict(time_ns=now,address=addr,actual=actual,expected=expected,raw_expected=raw,occupancy=occ,rxt=rxt,ie=ie,
                             popped=counts['popped'],completed=counts['completed'],last_pop_before=last_pop_before)
                    samples.append(row)
                    if addr==24 and raw&6:
                        key=(raw&6,ie);grid[key]=grid.get(key,0)+1
                if addr==16:
                    check(actual==ie,'IE readback/reserved high bits')
                    ie_readbacks.append(dict(time_ns=now,actual=actual,expected=ie))
                if addr==0: check(actual==rxt<<2,'RXT readback')
                if addr==12:
                    check(not v('rx_complete'),'out-of-scope simultaneous RX/read')
                    if queue:
                        expected=queue.popleft();last_pop_before=occ
                        check(actual==expected and v('rx_fifo_re')==1,'ordered DATA/nonempty pop')
                        data_reads.append(dict(time_ns=now,actual=actual,expected=expected))
                        counts['popped']+=1;rptr=(rptr+1)%32
                    else:
                        check(actual>>8==0 and v('rx_fifo_re')==0,'empty read side effect/high bits')
                        counts['empty_reads']+=1
                    ov=0
            if v('rx_complete')==1:
                idx=counts['completed'];check(idx<len(frames),'unexpected extra completed frame')
                value=frames[idx] if idx<len(frames) else 0
                accept=occ<16
                check(v('rx_fifo_we')==int(accept),'independent admission mismatch')
                commits.append(dict(time_ns=now,frame=idx+1,data=value,occupancy_before=occ,rxt=rxt,
                                    expected_accept=accept,actual_we=v('rx_fifo_we'),popped_before=counts['popped']))
                counts['completed']+=1
                if accept:
                    queue.append(value);counts['accepted']+=1;wptr=(wptr+1)%32
                    if occ>=threshold: continued[rxt]+=1
                    if len(queue)==16: capacity[rxt]+=1
                else: counts['rejected']+=1;ov=1
            if not en:
                counts['flushed']+=len(queue);queue.clear();wptr=rptr
            if apb and v('pwrite')==1:
                addr=v('paddr'); val=v('pwdata')
                if addr==0:
                    config.append(dict(time_ns=now,register='CON',write=val,occupancy=len(queue),completed=counts['completed'],popped=counts['popped']))
                    if scenario=='tp04' and len(queue)==6:
                        dynamic.append(dict(time_ns=now,old_rxt=rxt,new_rxt=(val>>2)&3,completed=counts['completed'],popped=counts['popped']))
                    rxt=(val>>2)&3
                if addr==16:
                    config.append(dict(time_ns=now,register='IE',write=val,occupancy=len(queue),completed=counts['completed'],popped=counts['popped'],raw=raw))
                    ie=val&31
                if addr==4: en=val&1
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
    checks=dict(exact_counts=counts==required,independent_checks=error_count==0,final_empty=not queue,
                nonzero_checks=state_checks>0 and bool(samples) and bool(data_reads))
    boundary_hits=[]
    if scenario=='tp04':
        raw_reads=[s for s in samples if s['address']==20]
        for r in range(4):
            t=16>>r
            eligible=[s for s in raw_reads if s['rxt']==r]
            hits={k:any(s['occupancy']==o and s['actual']==(1|(2 if o>=t else 0)) and
                       (k!='down' or s['last_pop_before']==t) for s in eligible)
                  for k,o in [('below',t-1),('at',t),('down',t-1)]+([('above',t+1)] if r else [])}
            boundary_hits.append(dict(rxt=r,threshold=t,hits=hits))
        checks['all_boundary_checks']=all(all(r['hits'].values()) for r in boundary_hits)
        checks['stable_dynamic_configuration']=len(dynamic)==8 and len({(d['completed'],d['popped']) for d in dynamic})==1 and {d['new_rxt'] for d in dynamic}=={0,1,2,3}
        checks['dynamic_raw_reclassification']=all(any(s['rxt']==r and s['occupancy']==6 and s['actual']==(1|(2 if 6>=(16>>r) else 0)) for s in raw_reads) for r in range(4))
    if scenario=='tp05':
        checks['continued_admission_to_16']=all(continued[r]==16-(16>>r) and capacity[r]==1 for r in (1,2,3))
        checks['no_early_overflow']=all(not s['actual']&4 for s in samples if s['address']==20)
        checks['no_DATA_read_before_16_per_level']=all(len({c['popped_before'] for c in commits if c['rxt']==r})==1 for r in (1,2,3))
    if scenario=='tp06':
        checks['every_source_IE_combination']=all(grid.get((s,i),0)>=2 for s in (2,4,6) for i in (0,2,4,6))
        checks['OV_only_genuinely_present']=any(s['address']==20 and s['occupancy']==0 and s['actual']==5 for s in samples)
        checks['full_not_overflow']=sum(s['address']==20 and s['occupancy']==16 and s['actual']==3 for s in samples)>=2
        checks['IE_reserved_high_writes']=any(c['register']=='IE' and c['write']>>5 for c in config) and len(ie_readbacks)>=31
        checks['actual_full_rejection']=sum(c['occupancy_before']==16 and c['actual_we']==0 for c in commits)==2
    transitions=[]
    for source in (2,4,6):
        reads=[s for s in samples if s['address']==24 and s['raw_expected']&6==source]
        # Group by independently checked Raw read at the same stable status
        # window, then count actual masked bit transitions in that source state.
        previous=0; rises={2:0,4:0}; falls={2:0,4:0}
        for s in reads:
            for bit in (2,4):
                rises[bit]+=int(not previous&bit and bool(s['actual']&bit))
                falls[bit]+=int(bool(previous&bit) and not s['actual']&bit)
            previous=s['actual']
        transitions.append(dict(source=source,rxf_rises=rises[2],rxf_falls=falls[2],ov_rises=rises[4],ov_falls=falls[4]))
    if scenario=='tp06':
        checks['masked_on_off_transitions']=all((not t['source']&bit or (t[k+'_rises']>=3 and t[k+'_falls']>=3))
            for t in transitions for bit,k in [(2,'rxf'),(4,'ov')])
    with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(scenario=scenario,status='PASS' if all(checks.values()) else 'FAIL',checks=checks,counts=counts,
                required_counts=required,errors=errors,error_count=error_count,state_checks=state_checks,wave_sha256=digest,
                wave=str(path),end_ns=now,boundary_hits=boundary_hits,continued=continued,capacity=capacity,
                ie_grid=[dict(source=s,ie=i,hits=n) for (s,i),n in sorted(grid.items())],masked_transitions=transitions,dynamic=dynamic,
                commits=commits,status_reads=samples,configuration_writes=config,data_reads=data_reads,ie_readbacks=ie_readbacks)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('wave',type=Path);ap.add_argument('scenario',choices=['tp04','tp05','tp06'])
    a=ap.parse_args();result=audit(a.wave,a.scenario)
    with a.wave.with_name('stage2-wave-audit.json').open('x') as f: json.dump(result,f,indent=2)
    print(json.dumps({k:result[k] for k in ('scenario','status','checks','counts','error_count','errors')}))
    raise SystemExit(result['status']!='PASS')
