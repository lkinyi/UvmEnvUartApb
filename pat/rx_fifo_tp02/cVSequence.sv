class cVSequence extends uvm_sequence#(cApbTransaction);
  `uvm_object_utils(cVSequence)
  `uvm_declare_p_sequencer(cVSequencer)
  function new(string name="cVSequence"); super.new(name); endfunction
  task body();
    cRxFifoSequence seq;
    seq=cRxFifoSequence::type_id::create("directed_rx");
    seq.scenario="tp02";
    seq.start(p_sequencer,this);
  endtask
endclass
