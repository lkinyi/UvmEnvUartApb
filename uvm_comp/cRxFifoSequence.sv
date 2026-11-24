// Shared directed operations. All expected bytes/counts are specified by the
// scenario, never read back from DUT data or derived from actual admission.
class cRxFifoSequence extends cVSequence;
  `uvm_object_utils(cRxFifoSequence)
  string scenario;
  cRxFifoScoreboard model;
  bit bad_expectation_used;
  function new(string name="cRxFifoSequence"); super.new(name); endfunction

  task wait_frames(int target);
    time deadline;
    deadline=$time+2ms;
    while (model.completed<target || model.pin_completed<target || model.serial_busy) begin
      if ($time>=deadline)
        `uvm_fatal("RX_DUT_FRAME_TIMEOUT",$sformatf("target=%0d pin=%0d DUT_complete=%0d sent=%0d time_ns=%0t",target,model.pin_completed,model.completed,model.sent,$time))
      #10us;
    end
    model.require_ok(model.completed==target && model.pin_completed==target,
      "RX_DUT_EXTRA_FRAME","Completion count exceeded the exact target");
  endtask

  task send_byte(byte unsigned value);
    int target;
    target=model.sent+1;
    `ApbWriteTX(32'h0c,value)
    wait_frames(target);
  endtask

  task status_at(int occupancy, bit ov, string label);
    logic [31:0] raw_value;
    raw_value=1 | ((occupancy>=model.threshold())?2:0) | (ov?4:0);
    model.require_ok(model.expected_rx.size()==occupancy && model.ov_expected==ov,
      "RX_ENV_MILESTONE",$sformatf("%s occupancy=%0d expected=%0d ov=%0d expected_ov=%0d",label,model.expected_rx.size(),occupancy,model.ov_expected,ov));
    `ApbReadRX(32'h04,(occupancy!=0)?32'h40:32'h0,32'h40)
    `ApbReadRX(32'h14,raw_value,32'hffffffff)
    `ApbReadRX(32'h18,raw_value & {27'd0,model.ie_shadow},32'hffffffff)
    `uvm_info("RX_MILESTONE",$sformatf("%s occupancy=%0d full=%0d rxf=%0d ov=%0d rxt=%0d ie=%02h raw=%02h masked=%02h time_ns=%0t",label,occupancy,occupancy==16,occupancy>=model.threshold(),ov,model.rxt_shadow,model.ie_shadow,raw_value,raw_value & {27'd0,model.ie_shadow},$time),UVM_NONE)
  endtask

  task set_rxt(int rxt);
    `ApbWriteRX(32'h00,32'(rxt<<2))
    `ApbReadRX(32'h00,32'(rxt<<2),32'hffffffff)
    #1us;
  endtask

  task boundary(string kind, int occupancy);
    model.checkpoint=kind;
    status_at(occupancy,0,kind);
    model.checkpoint="";
  endtask

  // A constant raw-source state across repeated full-register reads and every
  // IE change. The scoreboard independently predicts Raw and Masked as well.
  task ie_sweep(int sources, int occupancy, bit ov);
    int settings[10]='{0,2,0,4,0,6,2,4,6,0};
    int frames_before, pops_before;
    logic [31:0] write_value;
    frames_before=model.completed; pops_before=model.popped;
    model.forbid_reads=1;
    foreach(settings[i]) begin
      model.require_ok((model.expected_raw() & 6)==sources,"RX_ENV_SOURCE","IE sweep did not reach required independent Raw sources");
      // Alternate reserved high bits, while unused implemented IE[4:3,0]=0.
      write_value=32'(settings[i]) | ((i%2)?32'hffffffe0:0);
      `ApbWriteRX(32'h10,write_value)
      `ApbReadRX(32'h10,32'(settings[i]),32'hffffffff)
      #1us;
      model.checkpoint="ie";
      repeat(2) status_at(occupancy,ov,"IE_preserves_Raw_status_reads_nondestructive");
      model.checkpoint="";
      model.require_ok(model.completed==frames_before && model.popped==pops_before &&
        model.expected_rx.size()==occupancy && model.ov_expected==ov,
        "RX_ENV_IE_STABLE","Source changed or DATA was read during IE sweep");
    end
  endtask

  task hold_fifo(int occupancy, bit ov);
    int reads_before, accepted_before;
    reads_before=model.popped+model.empty_reads; accepted_before=model.accepted;
    model.forbid_reads=1;
    #200us;
    status_at(occupancy,ov,"retained_without_DATA_read");
    model.require_ok(model.popped+model.empty_reads==reads_before && model.accepted==accepted_before,
      "RX_ENV_HOLD","FIFO retention window changed event counts");
    model.hold_hits++;
    model.forbid_reads=0;
  endtask

  task read_byte(byte unsigned value);
    logic [31:0] expected_value;
    expected_value={24'd0,value};
    if ($test$plusargs("RX_EXPECTATION_SELFTEST") && !bad_expectation_used) begin
      expected_value=expected_value^1; bad_expectation_used=1;
    end
    `ApbReadRX(32'h0c,expected_value,32'hffffffff)
    #1us;
  endtask

  task empty_read();
    // Only high bits are defined. Pointer/occupancy/NE checked independently.
    `ApbReadRX(32'h0c,32'h0,32'hffffff00)
    #1us;
    status_at(0,0,"empty_read_no_pop");
  endtask

  task set_contract(int frames, int accepts, int drops, int pops, int empties, int holds);
    model.required_frames=frames; model.required_accepts=accepts;
    model.required_rejects=drops; model.required_pops=pops;
    model.required_empty=empties; model.required_holds=holds;
  endtask

  task irq_checkpoint(int id, int occupancy, bit ov, bit irq_expected, string label);
    status_at(occupancy,ov,label);
    repeat(3) @(posedge model.probe.pclk);
    #2ns;
    model.require_ok(model.probe.irq===irq_expected,"RX_DUT_IRQ_CHECKPOINT",label);
    model.tp07_hits[id]++;
    `uvm_info("RX_IRQ_CHECKPOINT",$sformatf("id=%0d label=%s occupancy=%0d raw=%02h ie=%02h irq=%b time_ns=%0t",id,label,occupancy,model.expected_raw(),model.ie_shadow,model.probe.irq,$time),UVM_NONE)
  endtask

  task body();
    byte unsigned value;
    int batches[5]='{1,5,16,10,8};
    int offset;
    if (!$cast(model,p_sequencer.coScoreboard))
      `uvm_fatal("RX_ENV_FACTORY","RX testcase requires cRxFifoTest factory override")
    model.scenario=scenario;
    model.stage2=(scenario=="tp04" || scenario=="tp05" || scenario=="tp06" || scenario=="tp07");
    #200ns;
    `ApbWriteTX(32'h08,32'd130)
    `ApbWriteRX(32'h08,32'd75)
    `ApbWriteTX(32'h00,32'h0)
    `ApbWriteRX(32'h00,32'h0)
    `ApbWriteTX(32'h10,32'h0)
    `ApbWriteRX(32'h10,32'h0)
    `ApbWriteTX(32'h04,32'h1)
    `ApbWriteRX(32'h04,32'h1)
    `ApbReadTX(32'h08,32'd130,32'hffffffff)
    `ApbReadRX(32'h08,32'd75,32'hffffffff)
    `ApbReadRX(32'h10,32'h0,32'hffffffff)
    status_at(0,0,"initial_empty");
    model.forbid_reads=1;
    if ($test$plusargs("RX_MISSING_FRAME_SELFTEST")) wait_frames(1);

    case (scenario)
      "smoke": begin
        set_contract(1,1,0,1,0,1);
        send_byte(8'h69); hold_fifo(1,0); read_byte(8'h69);
      end
      "tp01": begin
        set_contract(2,2,0,2,6,2);
        model.forbid_reads=0;
        repeat(3) empty_read();
        model.forbid_reads=1; send_byte(8'h96); hold_fifo(1,0); read_byte(8'h96);
        repeat(3) empty_read();
        model.forbid_reads=1; send_byte(8'h3d); hold_fifo(1,0); read_byte(8'h3d);
      end
      "tp02": begin
        set_contract(40,40,0,40,0,5); offset=0;
        foreach(batches[b]) begin
          model.forbid_reads=1;
          for(int i=0;i<batches[b];i++) send_byte(8'((offset+i)*37+11));
          hold_fifo(batches[b],0);
          for(int i=0;i<batches[b];i++) begin
            read_byte(8'((offset+i)*37+11));
            if(i==1 && batches[b]>2) begin
              status_at(batches[b]-2,0,"partial_drain"); #50us;
            end
          end
          offset+=batches[b]; status_at(0,0,"batch_drained");
        end
      end
      "tp03a", "tp03b": begin
        if(scenario=="tp03a") set_contract(17,16,1,16,0,1);
        else set_contract(18,17,1,17,0,2);
        for(int i=0;i<15;i++) send_byte(8'(i*13+7));
        status_at(15,0,"15_not_full");
        send_byte(8'(15*13+7)); status_at(16,0,"16_full_without_overflow");
        send_byte(8'hfa); status_at(16,1,"17_completed_rejected");
        repeat(3) status_at(16,1,"status_reads_preserve_OV");
        hold_fifo(16,1);
        read_byte(8'h07); status_at(15,0,"first_DATA_read_clears_OV");
        if(scenario=="tp03b") begin
          model.forbid_reads=1;
          send_byte(8'ha5); hold_fifo(16,0);
        end
        for(int i=1;i<16;i++) read_byte(8'(i*13+7));
        if(scenario=="tp03b") read_byte(8'ha5);
      end
      "tp04": begin
        set_contract(39,39,0,39,0,5);
        for(int r=0;r<4;r++) begin
          int threshold;
          threshold=16>>r;
          set_rxt(r); model.forbid_reads=1;
          for(int i=0;i<threshold-1;i++) send_byte(8'(r*41+i*7+3));
          boundary("below",threshold-1);
          send_byte(8'(r*41+(threshold-1)*7+3)); boundary("at",threshold);
          hold_fifo(threshold,0);
          if(r!=0) begin
            model.forbid_reads=1;
            send_byte(8'(r*41+threshold*7+3)); boundary("above",threshold+1);
            model.forbid_reads=0; read_byte(8'(r*41+3));
            status_at(threshold,0,"above_to_T_still_asserted");
            read_byte(8'(r*41+10));
          end else read_byte(8'h03);
          boundary("down",threshold-1);
          for(int i=(r==0)?1:2;i<threshold+((r==0)?0:1);i++) read_byte(8'(r*41+i*7+3));
          status_at(0,0,"level_drained");
        end
        // Six retained bytes: RXT00/01 => 0, RXT10/11 => 1. No serial
        // completion or DATA read occurs in any reconfiguration window.
        set_rxt(0); model.forbid_reads=1;
        for(int i=0;i<6;i++) send_byte(8'(i*19+5));
        begin
          int levels[8]='{0,1,2,3,0,2,1,0};
          int frames_before, reads_before;
          frames_before=model.completed; reads_before=model.popped;
          foreach(levels[i]) begin
            set_rxt(levels[i]); #20us;
            model.require_ok(model.completed==frames_before && model.popped==reads_before && !model.serial_busy,
              "RX_ENV_DYNAMIC_STABLE","RXT change overlapped receive/read");
            boundary("dynamic",6);
          end
        end
        hold_fifo(6,0);
        for(int i=0;i<6;i++) read_byte(8'(i*19+5));
      end
      "tp05": begin
        set_contract(48,48,0,48,0,3);
        for(int r=1;r<4;r++) begin
          int threshold;
          threshold=16>>r; set_rxt(r); model.forbid_reads=1;
          for(int i=0;i<threshold;i++) send_byte(8'(r*53+i*11));
          status_at(threshold,0,"watermark_reached_not_full");
          for(int i=threshold;i<16;i++) begin
            send_byte(8'(r*53+i*11));
            status_at(i+1,0,"accepted_after_watermark_no_OV");
          end
          hold_fifo(16,0);
          for(int i=0;i<16;i++) read_byte(8'(r*53+i*11));
          status_at(0,0,"all_16_retained_in_order");
        end
      end
      "tp06": begin
        set_contract(36,34,2,18,1,3); model.required_flushed=16;
        set_rxt(3); model.forbid_reads=1;
        send_byte(8'h36); send_byte(8'hc9);
        hold_fifo(2,0); ie_sweep(2,2,0);
        model.forbid_reads=0; read_byte(8'h36); read_byte(8'hc9);
        for(int pass=0;pass<2;pass++) begin
          model.forbid_reads=1;
          for(int i=0;i<16;i++) send_byte(8'(pass*61+i*17+9));
          status_at(16,0,"full_is_not_OV");
          send_byte(8'hfe); status_at(16,1,"actual_full_rejection_sets_OV");
          if(pass==0) begin
            // Real OV-only Raw is unreachable with EN=1 and no DATA reads:
            // all thresholds assert at 16. Quiet EN disable clears FIFO only.
            model.allow_disable_flush=1;
            `ApbWriteRX(32'h04,32'h0)
            #2us;
            status_at(0,1,"disabled_FIFO_flush_preserves_OV");
            `ApbWriteRX(32'h04,32'h1)
            #2us; model.allow_disable_flush=0;
            hold_fifo(0,1); ie_sweep(4,0,1);
            model.forbid_reads=0;
            empty_read(); // Explicit OV clear, with no actual pop.
          end else begin
            hold_fifo(16,1);
            ie_sweep(6,16,1); // IE04 isolates OV in Masked; Raw includes RXF.
            model.forbid_reads=0;
            for(int i=0;i<16;i++) read_byte(8'(61+i*17+9));
            status_at(0,0,"DATA_read_cleared_OV");
          end
        end
      end
      "tp07": begin
        set_contract(38,36,2,36,0,5);
        // RXF only: IE before source, then source before IE and IE disable.
        set_rxt(3);
        `ApbWriteRX(32'h10,32'h2)
        send_byte(8'h31); send_byte(8'h72); hold_fifo(2,0);
        irq_checkpoint(0,2,0,1,"RXF_assert_and_hold_IE_first");
        read_byte(8'h31); irq_checkpoint(1,1,0,0,"RXF_DATA_deassert");
        read_byte(8'h72);
        `ApbWriteRX(32'h10,32'h0)
        model.forbid_reads=1;
        send_byte(8'ha6); send_byte(8'h59); hold_fifo(2,0);
        irq_checkpoint(2,2,0,0,"RXF_raw_active_IE_off");
        `ApbWriteRX(32'h10,32'h2)
        irq_checkpoint(3,2,0,1,"RXF_enable_after_source");
        `ApbWriteRX(32'h10,32'h0)
        irq_checkpoint(4,2,0,0,"RXF_disable_preserves_raw");
        read_byte(8'ha6); read_byte(8'h59);
        // OV only in Masked: real full rejection; RXF IE stays zero.
        set_rxt(1); model.forbid_reads=1;
        for(int i=0;i<16;i++) send_byte(8'(i*9+5));
        send_byte(8'hfd); hold_fifo(16,1);
        irq_checkpoint(5,16,1,0,"OV_real_rejection_IE_off");
        `ApbWriteRX(32'h10,32'h4)
        irq_checkpoint(6,16,1,1,"OV_enable_after_source");
        #20us; irq_checkpoint(7,16,1,1,"OV_held");
        read_byte(8'h05); irq_checkpoint(8,15,0,0,"OV_DATA_clear_no_other_enabled_source");
        for(int i=1;i<16;i++) read_byte(8'(i*9+5));
        // Both enabled: real RXF-only -> both -> remaining RXF -> none.
        `ApbWriteRX(32'h10,32'h6)
        model.forbid_reads=1;
        for(int i=0;i<8;i++) send_byte(8'(i*13+19));
        hold_fifo(8,0); irq_checkpoint(9,8,0,1,"merged_RXF_only");
        model.forbid_reads=1;
        for(int i=8;i<16;i++) send_byte(8'(i*13+19));
        send_byte(8'hfc); hold_fifo(16,1);
        irq_checkpoint(10,16,1,1,"merged_RXF_and_OV");
        read_byte(8'h13); irq_checkpoint(11,15,0,1,"merged_OV_removed_RXF_keeps_IRQ");
        for(int i=1;i<9;i++) read_byte(8'(i*13+19));
        irq_checkpoint(12,7,0,0,"merged_RXF_below_8_IRQ_deasserts");
        for(int i=9;i<16;i++) read_byte(8'(i*13+19));
        irq_checkpoint(13,0,0,0,"merged_final_empty_no_IRQ");
      end
      default: `uvm_fatal("RX_ENV_SCENARIO",$sformatf("Unknown scenario %s",scenario))
    endcase
    status_at(0,0,"final_empty");
    // Observe a quiet guard beyond one full bit, catching late/extra activity.
    #200us;
    model.finalized=1;
    `uvm_info("RX_CONTRACT",$sformatf("scenario=%s required_frames=%0d required_accepts=%0d required_rejects=%0d required_pops=%0d required_empty=%0d required_holds=%0d",scenario,model.required_frames,model.required_accepts,model.required_rejects,model.required_pops,model.required_empty,model.required_holds),UVM_NONE)
  endtask
endclass
