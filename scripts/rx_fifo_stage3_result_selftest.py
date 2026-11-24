#!/usr/bin/env python3
"""Exercise result gates by mutating a REAL completed TP07 log, not a fake PASS."""
import argparse
import json
from pathlib import Path
import re
import runpy

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    parse=runpy.run_path(str(Path(__file__).with_name('uartvip.py')))['parse_result']
    original=a.log.read_text();base=parse(original,0,False)
    assert base['status']=='PASS' and base['irq']['merge_holds']==1
    mutations={
      'missing_irq_summary':re.sub(r'^.*\[RX_IRQ_SUMMARY\].*\n','',original,flags=re.M),
      'zero_irq_comparisons':original.replace(f"cycles={base['irq']['cycles']}",'cycles=0',1),
      'irq_errors':re.sub(r'(\[RX_IRQ_SUMMARY\] cycles=\d+ errors=)0',r'\g<1>1',original),
      'missing_merge_hold':original.replace('merge_holds=1','merge_holds=0',1),
      'missing_scenario':re.sub(r'^.*\[RX_TP07_HIT\] id=11 hits=1.*\n','',original,flags=re.M),
      'duplicate_scenario':original.replace('[RX_TP07_HIT] id=11 hits=1','[RX_TP07_HIT] id=11 hits=2',1),
      'missing_functional_samples':re.sub(r'^.*\[RX_FC_EVENT\] id=44 hits=\d+.*\n','',original,flags=re.M),
      'zero_data_comparisons':original.replace('data_compares=36','data_compares=0',1),
      'unfinalized_model':original.replace('finalized=1','finalized=0',1),
      'late_checker_error':original+'\nUVM_ERROR @ 999999999: checker [RX_DUT_IRQ] late failure\n'}
    results=[dict(case=k,status=parse(v,0,False)['status']) for k,v in mutations.items()]
    results += [dict(case='nonzero_exit',status=parse(original,9,False)['status']),
                dict(case='wall_timeout',status=parse(original,124,True)['status'])]
    ok=all(x['status']=='FAIL' for x in results)
    a.output.write_text(json.dumps(dict(status='PASS' if ok else 'FAIL',source_log=str(a.log),
      valid_log_status=base['status'],expected_failures=len(results),results=results),indent=2))
    print(f"Stage3 result gates: {sum(x['status']=='FAIL' for x in results)}/{len(results)} rejected as expected")
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
