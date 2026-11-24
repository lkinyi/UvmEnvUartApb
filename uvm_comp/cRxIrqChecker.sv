// Dedicated per-UART1-pclk checker. Inputs are independently modeled settled
// state, never DUT Masked. The previous settled model is the next edge's RHS.
class cRxIrqChecker;
  logic [4:0] raw_before=1, ie_before=0;
  bit last_expected, injected;
  int unsigned cycles, errors, rises, falls, holds, merge_holds, faults;
  int fd;
  string fault, detail;
  function new();
    fd=$fopen("irq-events.csv","w");
    if(!fd) `uvm_fatal("IRQ_TRACE","Cannot open IRQ evidence")
    $fdisplay(fd,"cycle,time_ns,pre_raw,pre_ie,pre_masked,post_raw,post_ie,post_masked,expected,actual,observed,complete,pops,event");
    if($value$plusargs("IRQ_FAULT=%s",fault)) begin
      if(!(fault inside {"missing","stuck","early","late","merge"}))
        `uvm_fatal("IRQ_SELFTEST_CONFIG","Unknown IRQ_FAULT mode")
    end
  endfunction
  function bit check(logic [4:0] raw_now, logic [4:0] ie_now, logic actual,
                     int completed, int pops, cRxFunctionalCoverage fc);
    bit expected, mask_now, removed;
    logic observed;
    string event_name;
    cycles++;
    expected=|(raw_before & ie_before);
    mask_now=|(raw_now & ie_now);
    removed=(raw_before[2:1]==3 && raw_now[2:1]==1 && ie_now==6 && expected && mask_now);
    observed=actual; event_name="steady";
    if(raw_now!=raw_before) event_name="source";
    if(ie_now!=ie_before) event_name="IE";
    if(expected!=last_expected) event_name=expected?"IRQ_rise":"IRQ_fall";
    if(removed) event_name="OV_removed_RXF_holds";
    // Change only this checker's sampled input. No DUT signal is driven/forced.
    // A single corruption must create a normal UVM failure and a nonzero runner exit.
    if(!injected && fault!="") begin
      if((fault=="missing" && expected && !last_expected) ||
         (fault=="stuck" && !expected && last_expected) ||
         (fault=="early" && mask_now!=expected) ||
         (fault=="late" && expected!=last_expected) ||
         (fault=="merge" && removed)) begin
        observed=~expected; injected=1; faults++;
        `uvm_info("IRQ_FAULT",$sformatf("mode=%s cycle=%0d actual=%b corrupted_sample=%b",fault,cycles,actual,observed),UVM_NONE)
      end
    end
    detail=$sformatf("cycle=%0d time_ns=%0t expectedIRQ=%b actualIRQ=%b observedIRQ=%b modelRaw=%02h IE=%02h Masked=%02h postRaw=%02h postIE=%02h postMasked=%02h event=%s complete=%0d pops=%0d fault=%s",
      cycles,$time,expected,actual,observed,raw_before,ie_before,raw_before & ie_before,
      raw_now,ie_now,raw_now & ie_now,event_name,completed,pops,fault);
    if(cycles<10 || raw_now!=raw_before || ie_now!=ie_before || expected!=last_expected || observed!==expected)
      $fdisplay(fd,"%0d,%0t,%02h,%02h,%02h,%02h,%02h,%02h,%b,%b,%b,%0d,%0d,%s",cycles,$time,
        raw_before,ie_before,raw_before & ie_before,raw_now,ie_now,raw_now & ie_now,expected,actual,observed,completed,pops,event_name);
    if(observed!==expected) errors++;
    else begin
      if(expected && !last_expected) begin rises++; fc.hit(40); fc.hit(45); end
      if(expected && last_expected) begin holds++; fc.hit(41); end
      if(!expected && last_expected) begin falls++; fc.hit(42); fc.hit(46); end
      if(expected && (raw_before & ie_before & 6)==6) fc.hit(43);
      if(removed) begin merge_holds++; fc.hit(44); end
    end
    raw_before=raw_now; ie_before=ie_now; last_expected=expected;
    return observed===expected;
  endfunction
  function void report();
    $fflush(fd); $fclose(fd);
    `uvm_info("RX_IRQ_SUMMARY",$sformatf("cycles=%0d errors=%0d rises=%0d falls=%0d holds=%0d merge_holds=%0d faults=%0d",cycles,errors,rises,falls,holds,merge_holds,faults),UVM_NONE)
  endfunction
endclass
