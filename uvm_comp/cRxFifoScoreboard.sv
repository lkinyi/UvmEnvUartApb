// BR=130/75, D9=0, TXT=0, UART0 -> UART1. Stage2 adds RXT/IE shadows.
// Expected data originates in APB intent; pin decoding and DUT commit are checked
// separately. Neither DUT WE/full/pointers nor returned DATA constructs expectations.
class cRxFifoScoreboard extends cScoreboard;
  `uvm_component_utils(cRxFifoScoreboard)
  localparam time BIT_TIME = 104800ns;
  virtual ifRxFifoProbe probe;
  virtual ifApbMaster rx_apb;
  byte unsigned source_pending[$], decoded_pending[$], expected_rx[$];
  time decoded_start[$];
  bit tx_enabled, rx_enabled, ov_expected, serial_busy, forbid_reads, finalized;
  int unsigned expected_wptr, expected_rptr;
  int unsigned sent, pin_started, pin_decoded, pin_completed, completed;
  int unsigned accepted, rejected, popped, empty_reads;
  int unsigned state_checks, pin_compares, status_compares, hold_hits;
  int unsigned boundary15, boundary16, overflow_hits, max_occupancy;
  int unsigned required_frames, required_accepts, required_rejects;
  int unsigned required_pops, required_empty, required_holds;
  string scenario, checkpoint;
  bit stage2, allow_disable_flush, flush_pending;
  bit [1:0] rxt_shadow;
  bit [4:0] ie_shadow;
  int unsigned flushed, required_flushed;
  int unsigned below_hits[4], at_hits[4], above_hits[4], down_hits[4];
  int unsigned continued_hits[4], capacity_hits[4], dynamic_hits[4];
  int unsigned ie_hits[3][4], ie_compares, con_compares, raw_compares, masked_compares;
  int unsigned rxf_rises, rxf_falls, ov_rises, ov_falls;
  bit previous_rxf, previous_ov;
  int last_pop_before;
  cRxFunctionalCoverage fc;
  cRxIrqChecker irq_checker;
  int fc_accepted, fc_popped, fc_empty, fc_rejected;
  int tp07_hits[14];
  bit enabled_before;

  // Each state sample follows all DUT state comparisons and the IRQ comparison.
  // Event counters discriminate real operations from repeated state samples.
  function void sample_functional();
    int n;
    logic [4:0] raw_model;
    n=expected_rx.size(); raw_model=5'(expected_raw());
    fc.hit(n==0?0:1);
    if(n==15) fc.hit(2);
    if(n==16) fc.hit(3);
    if(accepted>fc_accepted) begin
      fc.hit(4);
      if(n>threshold()) fc.hit(31);
      if(expected_wptr==0) fc.hit(12);
    end
    if(popped>fc_popped) begin
      fc.hit(5); fc.hit(11);
      if(expected_rptr==0) fc.hit(13);
    end
    if(empty_reads>fc_empty) fc.hit(6);
    if(rejected>fc_rejected) fc.hit(7);
    if(!previous_ov && ov_expected) fc.hit(8);
    if(previous_ov && ov_expected) fc.hit(9);
    if(previous_ov && !ov_expected) fc.hit(10);
    if(rx_enabled) begin
      fc.hit(14+int'(rxt_shadow));
      if(n==threshold()-1) fc.hit(18+int'(rxt_shadow));
      if(n==threshold()) fc.hit(22+int'(rxt_shadow));
      if(rxt_shadow!=0 && n==threshold()+1) fc.hit(25+int'(rxt_shadow));
    end
    if(!previous_rxf && n>=threshold()) fc.hit(29);
    if(previous_rxf && n<threshold()) fc.hit(30);
    fc.hit(ie_shadow==0?32:33);
    if((raw_model & 6)!=0) begin
      fc.gate(int'(raw_model & 6),int'(ie_shadow & 6));
      fc.hit((raw_model & ie_shadow)==0?34:35);
    end
    if((raw_model & ie_shadow & 6)==2) fc.hit(37);
    if((raw_model & ie_shadow & 6)==4) fc.hit(38);
    if((raw_model & ie_shadow & 6)==6) fc.hit(39);
    fc_accepted=accepted; fc_popped=popped; fc_empty=empty_reads; fc_rejected=rejected;
  endfunction

  function int threshold();
    case(rxt_shadow)
      0: return 16; 1: return 8; 2: return 4; 3: return 2;
    endcase
  endfunction

  function logic [31:0] expected_raw();
    // UART1 never transmits: independent TXE=1. Valid 8N1 frames => PE/FE=0.
    return 32'd1 | ((expected_rx.size()>=threshold())?32'd2:0) | (ov_expected?32'd4:0);
  endfunction

  function new(string name = "cRxFifoScoreboard", uvm_component parent = null);
    super.new(name, parent);
    fc=new; irq_checker=new;
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual ifRxFifoProbe)::get(this,"","rx_probe",probe) ||
        !uvm_config_db#(virtual ifApbMaster)::get(this,"","rx_apb",rx_apb))
      `uvm_fatal("RX_ENV_INTERFACE", "Stage1 passive probe/APB interface missing")
  endfunction

  function void require_ok(bit condition, string id, string detail);
    if (!condition) begin
      cntCompareErr++;
      `uvm_error(id, detail)
      if (cntCompareErr>=20)
        `uvm_fatal("RX_CHECKER_ABORT","Stopping after 20 model errors; retain the first root-cause messages")
    end
  endfunction

  virtual function void write_resetfrmTX(logic preset_n);
    super.write_resetfrmTX(preset_n);
    if (preset_n === 0) begin
      source_pending.delete(); decoded_pending.delete(); decoded_start.delete();
      expected_rx.delete(); tx_enabled=0; rx_enabled=0; ov_expected=0;
      expected_wptr=0; expected_rptr=0;
      rxt_shadow=0; ie_shadow=0;
    end
  endfunction

  virtual function void write_frmMonitorTX(cApbTransaction t);
    if (rst_flg) return;
    require_ok(t.pslverr === 0, "RX_DUT_APB", "Unexpected source APB error");
    if (t.pwrite && t.pstrb === 4'hf) begin
      if (t.paddr == 4) tx_enabled=t.pwdata[0];
      if (t.paddr == 12 && tx_enabled) begin
        source_pending.push_back(t.pwdata[7:0]); sent++;
      end
    end
  endfunction

  virtual function void write_frmMonitorRX(cApbTransaction t);
    byte unsigned expected_byte;
    logic [31:0] raw_expected;
    if (rst_flg) return;
    require_ok(t.pslverr === 0, "RX_DUT_APB", "Unexpected target APB error");
    if (t.pwrite && t.pstrb === 4'hf) begin
      if (t.paddr == 4) begin
        require_ok(t.pwdata[2:1] === 0 && (t.pwdata[0] || (stage2 && allow_disable_flush)),
          "RX_ENV_CONFIG","Requires 8N1; disable only in explicit TP06 OV isolation setup");
        rx_enabled=t.pwdata[0];
        if (!rx_enabled) flush_pending=1;
      end
      if (t.paddr == 0) begin
        require_ok(t.pwdata[1:0] === 0 && (stage2 || t.pwdata[3:2] === 0),
          "RX_ENV_CONFIG","TXT must remain 00; Stage1 RXT must remain 00");
        rxt_shadow=t.pwdata[3:2];
      end
      if (t.paddr == 16) begin
        require_ok((t.pwdata[4:0] & 5'h19) === 0 && (stage2 || t.pwdata[4:0] === 0),
          "RX_ENV_CONFIG","Only RXF/OV IE bits allowed; Stage1 IE must remain zero");
        ie_shadow=t.pwdata[4:0];
      end
      require_ok(t.paddr!=12,"RX_ENV_CONFIG","UART1 TX must remain idle for independent TXE prediction");
    end
    if (!t.pwrite && (rx_enabled || stage2)) begin
      if (t.paddr == 12) begin
        require_ok(!forbid_reads,"RX_ENV_EARLY_READ","DATA read inside accumulation/hold window");
        require_ok(t.prdata[31:8] === 0,"RX_DUT_DATA","DATA high 24 bits must be zero");
        require_ok(probe.rx_complete === 0,"RX_ENV_CONCURRENT","Same-edge RX/read is outside Stage1 scope");
        if (expected_rx.size() == 0) begin
          empty_reads++;
          require_ok(probe.fifo_re === 0,"RX_DUT_EMPTY_READ","Empty read asserted FIFO pop");
          // Deliberately do NOT compare the undefined/stale low byte.
        end else begin
          last_pop_before=expected_rx.size();
          expected_byte=expected_rx.pop_front();
          require_ok(t.prdata[7:0] === expected_byte,"RX_DUT_ORDER",
            $sformatf("pop=%0d actual=%02h expected=%02h",popped,t.prdata[7:0],expected_byte));
          require_ok(probe.fifo_re === 1,"RX_DUT_POP","Nonempty DATA read did not pop");
          popped++; expected_rptr=(expected_rptr+1)%32;
          if (t.prdata[7:0] === expected_byte) cntCompareOk++;
          `uvm_info("RX_POP",$sformatf("index=%0d data=%02h occupancy=%0d time_ns=%0t",popped,expected_byte,expected_rx.size(),$time),UVM_LOW)
        end
        ov_expected=0;
      end
      raw_expected=expected_raw();
      if (t.paddr == 20) begin
        require_ok(t.prdata === raw_expected,"RX_DUT_RAW",
          $sformatf("actual=%08h expected=%08h",t.prdata,raw_expected)); status_compares++;
        raw_compares++;
        if (t.prdata === raw_expected && scenario=="tp04") begin
          if(checkpoint=="below" && expected_rx.size()==threshold()-1) below_hits[rxt_shadow]++;
          if(checkpoint=="at" && expected_rx.size()==threshold()) at_hits[rxt_shadow]++;
          if(checkpoint=="above" && threshold()<16 && expected_rx.size()==threshold()+1) above_hits[rxt_shadow]++;
          if(checkpoint=="down" && last_pop_before==threshold() && expected_rx.size()==threshold()-1) down_hits[rxt_shadow]++;
          if(checkpoint=="dynamic") dynamic_hits[rxt_shadow]++;
        end
      end
      if (t.paddr == 24) begin
        require_ok(t.prdata === (raw_expected & {27'd0,ie_shadow}),"RX_DUT_MASKED",
          $sformatf("actual=%08h expected=%08h independent_raw=%08h IE=%02h",t.prdata,raw_expected & {27'd0,ie_shadow},raw_expected,ie_shadow));
        status_compares++; masked_compares++;
        if(scenario=="tp06" && checkpoint=="ie" && t.prdata === (raw_expected & {27'd0,ie_shadow})) begin
          if(raw_expected[2:1]!=0) ie_hits[int'(raw_expected[2:1])-1][int'(ie_shadow[2:1])]++;
        end
      end
      if (t.paddr == 16) begin
        require_ok(t.prdata === {27'd0,ie_shadow},"RX_DUT_IE","IE readback/reserved high bits mismatch");
        status_compares++; ie_compares++;
      end
      if (t.paddr == 0) begin
        require_ok(t.prdata === {28'd0,rxt_shadow,2'b00},"RX_DUT_CON","CON readback mismatch");
        status_compares++; con_compares++;
      end
      if (t.paddr == 4) begin
        require_ok(t.prdata[6] === (expected_rx.size()!=0),"RX_DUT_NE","SE.NE differs from model");
        status_compares++;
      end
    end
  endfunction

  task run_phase(uvm_phase phase);
    fork
      decode_serial();
      observe_receiver();
    join
  endtask

  // Independent fixed-baud pin decoder: start midpoint, 8 LSB-first data
  // midpoints, STOP midpoint, then full STOP elapsed. DUT completion can precede
  // STOP midpoint, so a checked data token is published at the eighth data bit.
  task decode_serial();
    byte unsigned data_byte, expected_byte;
    time started;
    forever begin
      @(negedge probe.serial_rx);
      if (probe.preset_n !== 1 || !rx_enabled) continue;
      serial_busy=1; started=$time; pin_started++;
      `uvm_info("RX_PIN_START",$sformatf("id=%0d start_ns=%0t",pin_started,started),UVM_LOW)
      #(BIT_TIME/2);
      require_ok(probe.serial_rx === 0,"RX_DUT_SERIAL_START","Invalid start midpoint");
      for (int b=0;b<8;b++) begin
        #(BIT_TIME); data_byte[b]=probe.serial_rx;
      end
      if (source_pending.size()==0)
        `uvm_fatal("RX_DUT_EXTRA_FRAME","Serial frame without corresponding APB source intent")
      expected_byte=source_pending.pop_front();
      require_ok(data_byte === expected_byte,"RX_DUT_SERIAL_DATA",
        $sformatf("pin=%02h source=%02h",data_byte,expected_byte));
      pin_compares++; pin_decoded++;
      decoded_pending.push_back(expected_byte); decoded_start.push_back(started);
      #(BIT_TIME);
      require_ok(probe.serial_rx === 1,"RX_DUT_SERIAL_STOP","STOP midpoint must be high");
      #(BIT_TIME/2);
      pin_completed++; serial_busy=0;
      `uvm_info("RX_PIN_FRAME",$sformatf("id=%0d data=%02h start_ns=%0t end_ns=%0t",pin_completed,data_byte,started,$time),UVM_LOW)
    end
  endtask

  task observe_receiver();
    byte unsigned data_byte;
    time started;
    int old_occupancy;
    bit should_accept;
    forever begin
      @(posedge probe.pclk);
      if (probe.preset_n !== 1 || (!rx_enabled && !stage2)) continue;
      if (probe.rx_complete === 1) begin
        if (decoded_pending.size()==0)
          `uvm_fatal("RX_DUT_UNPAIRED_COMPLETE","RX complete without independently decoded serial data")
        require_ok(!(rx_apb.psel && rx_apb.penable && !rx_apb.pwrite && rx_apb.paddr==12),
          "RX_ENV_CONCURRENT","Same-edge RX/read is outside Stage1 scope");
        data_byte=decoded_pending.pop_front(); started=decoded_start.pop_front();
        require_ok(($time-started)>=9*BIT_TIME && ($time-started)<=10*BIT_TIME,
          "RX_DUT_COMPLETE_TIME","RX completion outside independent serial STOP window");
        old_occupancy=expected_rx.size(); should_accept=(old_occupancy<16);
        require_ok(probe.fifo_we === should_accept,"RX_DUT_ADMISSION",
          $sformatf("old_occupancy=%0d actual_WE=%b expected_WE=%b",old_occupancy,probe.fifo_we,should_accept));
        completed++;
        if (should_accept) begin
          expected_rx.push_back(data_byte); accepted++; expected_wptr=(expected_wptr+1)%32;
          if(old_occupancy>=threshold()) continued_hits[rxt_shadow]++;
          if(expected_rx.size()==16) capacity_hits[rxt_shadow]++;
        end else begin
          rejected++; ov_expected=1; overflow_hits++;
        end
        if (expected_rx.size()>max_occupancy) max_occupancy=expected_rx.size();
        if (expected_rx.size()==15) boundary15++;
        if (expected_rx.size()==16 && should_accept) boundary16++;
        `uvm_info("RX_COMMIT",$sformatf("id=%0d data=%02h accepted=%0d rejected=%0d occupancy=%0d ov=%0d start_ns=%0t commit_ns=%0t",completed,data_byte,accepted,rejected,expected_rx.size(),ov_expected,started,$time),UVM_LOW)
      end
      // Explicitly after RTL's #1 updates, not racing the APB completion sample.
      #2ns;
      // IRQ samples the previous edge's settled independent model. APB monitor
      // callbacks may already have changed this edge's shadows in active region.
      if(irq_checker.raw_before==5'(expected_raw()) && irq_checker.ie_before!=ie_shadow && cntCompareErr==0)
        fc.hit(36);
      require_ok(irq_checker.check(5'(expected_raw()),ie_shadow,probe.irq,completed,popped,fc),
        "RX_DUT_IRQ",irq_checker.detail);
      // EN=0 flushes wptr on the following edge. Skip only that transition
      // edge; every subsequent disabled edge and all register reads are checked.
      if(flush_pending && enabled_before) begin
        enabled_before=rx_enabled;
        continue;
      end
      if(flush_pending) begin
        require_ok(!serial_busy && decoded_pending.size()==0 && source_pending.size()==0,
          "RX_ENV_FLUSH","Disable requires a quiet fully completed serial window");
        flushed+=expected_rx.size(); expected_rx.delete(); expected_wptr=expected_rptr;
        flush_pending=0;
        // The flush occurs at this edge: next edge must see the flushed Raw.
        irq_checker.raw_before=5'(expected_raw());
      end
      state_checks++;
      require_ok(probe.wptr === 5'(expected_wptr),"RX_DUT_WPTR","Write pointer differs from independent accept count");
      require_ok(probe.rptr === 5'(expected_rptr),"RX_DUT_RPTR","Read pointer differs from independent nonempty-pop count");
      require_ok(probe.fifo_empty === (expected_rx.size()==0),"RX_DUT_EMPTY","Empty mismatch");
      require_ok(probe.fifo_full === (expected_rx.size()==16),"RX_DUT_FULL","Full mismatch");
      require_ok(probe.rx_ne === (expected_rx.size()!=0),"RX_DUT_NE","NE mismatch");
      require_ok(probe.rx_rxf === (expected_rx.size()>=threshold()),"RX_DUT_RXF","RXF differs from occupancy/RXT model");
      require_ok(probe.rx_ov === ov_expected,"RX_DUT_OV","Raw overflow mismatch");
      if(cntCompareErr==0) sample_functional();
      enabled_before=rx_enabled;
      if(!previous_rxf && expected_rx.size()>=threshold()) rxf_rises++;
      if(previous_rxf && expected_rx.size()<threshold()) rxf_falls++;
      if(!previous_ov && ov_expected) ov_rises++;
      if(previous_ov && !ov_expected) ov_falls++;
      previous_rxf=(expected_rx.size()>=threshold()); previous_ov=ov_expected;
    end
  endtask

  function void check_phase(uvm_phase phase);
    super.check_phase(phase);
    require_ok(finalized,"RX_ENV_INCOMPLETE","Sequence did not reach its final contract");
    require_ok(!serial_busy && source_pending.size()==0 && decoded_pending.size()==0 && expected_rx.size()==0,
      "RX_DUT_UNFINISHED","In-flight serial event or unread expected FIFO data at end");
    require_ok(sent==required_frames && pin_started==required_frames && pin_decoded==required_frames &&
      pin_completed==required_frames && completed==required_frames,"RX_DUT_FRAME_COUNT","Missing/extra/incomplete frame count");
    require_ok(accepted==required_accepts && rejected==required_rejects && popped==required_pops &&
      empty_reads==required_empty,"RX_DUT_COUNTS","Admission/pop/empty-read contract mismatch");
    require_ok(completed==accepted+rejected && accepted==popped+flushed+expected_rx.size() && flushed==required_flushed,
      "RX_ENV_CONSERVATION","FIFO event conservation/explicit flush contract failed");
    require_ok(cntCompareOk==required_pops && pin_compares==required_frames && state_checks>0 &&
      status_compares>0 && hold_hits==required_holds,"RX_ENV_CHECK_COUNTS","Required comparisons/hold scenarios not reached");
    if (required_rejects>0)
      require_ok(boundary15>0 && boundary16>0 && overflow_hits==required_rejects && max_occupancy==16,
        "RX_ENV_BOUNDARY_HITS","15/16/17 boundary was not genuinely exercised");
    require_ok(irq_checker.cycles>0 && irq_checker.errors==0,"RX_ENV_IRQ_COUNTS","IRQ comparisons missing or failed");
    if(irq_checker.fault!="")
      require_ok(irq_checker.injected,"IRQ_SELFTEST_NOT_REACHED","Requested IRQ corruption did not execute");
    if(scenario=="tp07") begin
      foreach(tp07_hits[i]) require_ok(tp07_hits[i]==1,"RX_ENV_TP07_HITS",$sformatf("Missing/duplicate checkpoint %0d",i));
      require_ok(irq_checker.rises>=4 && irq_checker.falls>=4 && irq_checker.holds>0 && irq_checker.merge_holds==1,
        "RX_ENV_TP07_TIMING","IRQ transitions or multi-source hold missing");
    end
    if(scenario=="tp04") begin
      foreach(below_hits[r]) require_ok(below_hits[r]==1 && at_hits[r]==1 && down_hits[r]==1 &&
        above_hits[r]==((r==0)?0:1) && dynamic_hits[r]>0,"RX_ENV_TP04_HITS","Missing four-level boundary/dynamic checkpoint");
      require_ok(rxf_rises>=6 && rxf_falls>=6,"RX_ENV_TP04_TRANSITIONS","Missing RXF assertion/deassertion");
    end
    if(scenario=="tp05") begin
      for(int r=1;r<4;r++) require_ok(capacity_hits[r]==1 && continued_hits[r]==16-(16>>r),
        "RX_ENV_TP05_HITS","Missing continued admission above watermark up to physical capacity");
      require_ok(rejected==0 && overflow_hits==0 && ov_rises==0,"RX_DUT_EARLY_OV","OV before actual overflow");
    end
    if(scenario=="tp06") begin
      foreach(ie_hits[s,i]) require_ok(ie_hits[s][i]>=2,"RX_ENV_TP06_HITS","Required raw-source/IE combination or repeated status read missing");
      require_ok(ie_compares>=31 && required_flushed==16 && ov_rises==2 && ov_falls==2,
        "RX_ENV_TP06_TRANSITIONS","Missing IE readbacks/real OV lifecycle/isolation flush");
    end
  endfunction

  function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    irq_checker.report(); fc.report();
    if(scenario=="tp07") foreach(tp07_hits[i])
      `uvm_info("RX_TP07_HIT",$sformatf("id=%0d hits=%0d",i,tp07_hits[i]),UVM_NONE)
    if(stage2) begin
      foreach(below_hits[r])
        `uvm_info("RX_STAGE2_RXT",$sformatf("rxt=%0d below=%0d at=%0d above=%0d down=%0d continued=%0d capacity=%0d dynamic=%0d",r,below_hits[r],at_hits[r],above_hits[r],down_hits[r],continued_hits[r],capacity_hits[r],dynamic_hits[r]),UVM_NONE)
      foreach(ie_hits[s,i])
        `uvm_info("RX_STAGE2_IE",$sformatf("source=%0d ie=%0d hits=%0d",(s+1)*2,i*2,ie_hits[s][i]),UVM_NONE)
      `uvm_info("RX_STAGE2_SUMMARY",$sformatf("flushed=%0d required_flushed=%0d ie_compares=%0d con_compares=%0d raw_compares=%0d masked_compares=%0d rxf_rises=%0d rxf_falls=%0d ov_rises=%0d ov_falls=%0d",flushed,required_flushed,ie_compares,con_compares,raw_compares,masked_compares,rxf_rises,rxf_falls,ov_rises,ov_falls),UVM_NONE)
    end
    `uvm_info("RX_FIFO_SUMMARY",$sformatf("sent=%0d pin_started=%0d pin_completed=%0d completed=%0d accepted=%0d rejected=%0d popped=%0d empty_reads=%0d data_compares=%0d pin_compares=%0d state_checks=%0d status_compares=%0d holds=%0d max_occupancy=%0d boundary15=%0d boundary16=%0d overflow_hits=%0d errors=%0d finalized=%0d",sent,pin_started,pin_completed,completed,accepted,rejected,popped,empty_reads,cntCompareOk,pin_compares,state_checks,status_compares,hold_hits,max_occupancy,boundary15,boundary16,overflow_hits,cntCompareErr,finalized),UVM_NONE)
  endfunction
endclass
