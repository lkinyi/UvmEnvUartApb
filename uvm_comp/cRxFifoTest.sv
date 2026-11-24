// Selected only by patterns whose test_base.txt requests this base.
class cRxFifoTest extends cTest;
  `uvm_component_utils(cRxFifoTest)
  function new(string name = "cRxFifoTest", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    cScoreboard::type_id::set_type_override(cRxFifoScoreboard::get_type());
    super.build_phase(phase);
  endfunction
endclass
