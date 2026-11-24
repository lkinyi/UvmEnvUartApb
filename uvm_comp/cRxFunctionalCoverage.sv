// Semantic event bins, sampled only after the corresponding checks succeeded.
// 47..51 deliberately retain deferred requirements as visible zero-hit bins.
class cRxFunctionalCoverage;
  int unsigned hits[52];
  int unsigned source_ie_hits[3][4];
  covergroup events with function sample(int event_id);
    option.per_instance=1;
    semantic: coverpoint event_id { bins event_bin[]={[0:51]}; }
  endgroup
  covergroup gating with function sample(int source, int enables);
    option.per_instance=1;
    raw_sources: coverpoint source { bins rxf={2}; bins ov={4}; bins both={6}; }
    ie: coverpoint enables { bins off={0}; bins rxf={2}; bins ov={4}; bins both={6}; }
    source_by_ie: cross raw_sources,ie;
  endgroup
  function new(); events=new; gating=new; endfunction
  function void hit(int id);
    hits[id]++; events.sample(id);
  endfunction
  function void gate(int source, int enables);
    if(source==2 || source==4 || source==6) begin
      source_ie_hits[source/2-1][enables/2]++;
      gating.sample(source,enables);
    end
  endfunction
  function void report();
    foreach(hits[i])
      `uvm_info("RX_FC_EVENT",$sformatf("id=%0d hits=%0d",i,hits[i]),UVM_NONE)
    foreach(source_ie_hits[s,i])
      `uvm_info("RX_FC_CROSS",$sformatf("source=%0d ie=%0d hits=%0d",(s+1)*2,i*2,source_ie_hits[s][i]),UVM_NONE)
  endfunction
endclass
