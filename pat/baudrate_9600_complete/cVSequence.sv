// Local completion variant; original pat/baudrate_9600 is unchanged.
//--------------------------------------
//Project: The UVM environemnt for UART (Universal Asynchronous Receiver Transmitter)
//Function: User UVM Sequence - This is the TEST PATTERN created by user
//  - User modifty this class to create the expected transactions for the test purpose
//Author:  Pham Thanh Tram, Nguyen Sinh Ton, Doan Duc Hoang, Truong Cong Hoang Viet, Nguyen Hung Quan
//Page:    VLSI Technology
//--------------------------------------

class cVSequence extends uvm_sequence#(cApbTransaction);
  //Register to Factory
	`uvm_object_utils(cVSequence)
  `uvm_declare_p_sequencer(cVSequencer)

  cApbMasterWriteSeq WriteSeq;
  cApbMasterReadSeq ReadSeq;
  // Object must not have veriable "parent" (refer to class cVSequencer)
	function new (string name = "cVSequence");
		super.new(name);
	endfunction
  //TEST PATTERN is written at here
  task body();
    logic [31:0] txStatus;

//------------------------------------------------
//Setting baudrate 9600 bps
//------------------------------------------------
    #50ns
    //--------------------------------------------
    //Setting UART-TX (uart_0)
    //--------------------------------------------
    //Set baud rate
    `ApbWriteTX(32'h00000008,32'h00000082)
    `ApbReadTX(32'h00000008,32'h00000082,32'hffffffff)
    //Enable
    `ApbWriteTX(32'h00000004,32'h00000001)
    `ApbReadTX(32'h00000004,32'h00000003,32'h00000001)
    //--------------------------------------------
    //Setting UART-RX (uart_1)
    //--------------------------------------------
    //Set baud rate
    `ApbWriteRX(32'h00000008,32'h000004B)
    `ApbReadRX(32'h00000008,32'h0000004B,32'hffffffff)
    //Enable
    `ApbWriteRX(32'h00000004,32'h00000001)
    `ApbReadRX(32'h00000004,32'h00000003,32'h00000001)
//---------------------------------------------------
// I, Send 32'h0 DATA continually
//---------------------------------------------------
	for (int i = 0; i < 8; i=i+1) begin
    `ApbWriteTX(32'h0000000C,32'h00000000)
    //Ccheck DATA on UART RX
     while (1) begin
      `ApbReadRX(32'h00000004,32'h00000040,32'h00000000)
      if (ReadSeq.coApbTransaction.prdata[6]) begin
        `ApbReadRX(32'h0000000C,32'h00000000,32'h000000ff)
        #50ns
        break;
      end
     end
	end
//---------------------------------------------------
// II, Send 32'hFF DATA continually
//---------------------------------------------------
	for (int i = 0; i < 8; i=i+1) begin
    `ApbWriteTX(32'h0000000C,32'h000000FF)
    //Ccheck DATA on UART RX
     while (1) begin
      `ApbReadRX(32'h00000004,32'h00000040,32'h00000000)
      if (ReadSeq.coApbTransaction.prdata[6]) begin
        `ApbReadRX(32'h0000000C,32'h000000FF,32'h000000ff)
        #50ns
        break;
      end
     end
	end
    // Require the original first two groups to have reached the monitor/scoreboard.
    if (p_sequencer.coScoreboard.cntCompareOk != 16 ||
        p_sequencer.coScoreboard.cntCompareErr != 0) begin
      `uvm_fatal("COMPLETE_FIRST16", "The first 16 transfers were not all checked successfully")
    end
    `uvm_info("COMPLETE_FIRST16", "Original 8 x 00 and 8 x FF transfers checked", UVM_LOW)
//----------------------------------------------------------------
// III, Original 8-byte queued stimulus (not a FIFO-full test)
//----------------------------------------------------------------
	for (int i = 0; i < 8; i=i+1) begin
    `ApbWriteTX(32'h0000000C,i)
    //Ccheck DATA on UART RX
     while (1) begin
      `ApbReadRX(32'h00000004,32'h00000040,32'h00000000)
      if (ReadSeq.coApbTransaction.prdata[6]) begin

        #50ns
        break;
      end
     end
	end

    // The original sequence returns here with 8 unchecked writes. Keep its
    // stimulus intact, then drain all 8 bytes in order through real APB reads.
    for (int i = 0; i < 8; i++) begin
      while (1) begin
        `ApbReadRX(32'h00000004,32'h00000000,32'h00000000)
        if (ReadSeq.coApbTransaction.prdata[6]) begin
          `ApbReadRX(32'h0000000C,i,32'h000000ff)
          #50ns;
          break;
        end
      end
    end

    // Wait for both serial engines to become idle. All polling loops remain
    // bounded by the unmodified cTest watchdog (+TIMEOUT_NS, an error on expiry).
    while (1) begin
      `ApbReadTX(32'h00000004,32'h00000000,32'h00000000)
      txStatus = ReadSeq.coApbTransaction.prdata;
      `ApbReadRX(32'h00000004,32'h00000000,32'h00000000)
      if (!txStatus[7] && !ReadSeq.coApbTransaction.prdata[7]) break;
      #1us;
    end
    // Enabled, idle, RX empty; TX empty, RX not full, no overflow/parity/frame error.
    `ApbReadTX(32'h00000004,32'h00000001,32'h000000c1)
    `ApbReadRX(32'h00000004,32'h00000001,32'h000000c1)
    `ApbReadTX(32'h00000014,32'h00000001,32'h0000001f)
    `ApbReadRX(32'h00000014,32'h00000001,32'h0000001f)
    #50ns;

    // Read statistics only: never clear queues, alter expected data, or downgrade errors.
    if (p_sequencer.coScoreboard.cntCompareOk != 24 ||
        p_sequencer.coScoreboard.cntCompareErr != 0 ||
        p_sequencer.coScoreboard.queueTransTX.size() != 0 ||
        p_sequencer.coScoreboard.queueTransRX.size() != 0) begin
      `uvm_fatal("COMPLETE_CHECK", $sformatf("ok=%0d failed=%0d pending_tx=%0d pending_rx=%0d",
        p_sequencer.coScoreboard.cntCompareOk, p_sequencer.coScoreboard.cntCompareErr,
        p_sequencer.coScoreboard.queueTransTX.size(), p_sequencer.coScoreboard.queueTransRX.size()))
    end
    `uvm_info("COMPLETE_CHECK", $sformatf("ok=%0d failed=%0d pending_tx=%0d pending_rx=%0d",
      p_sequencer.coScoreboard.cntCompareOk, p_sequencer.coScoreboard.cntCompareErr,
      p_sequencer.coScoreboard.queueTransTX.size(), p_sequencer.coScoreboard.queueTransRX.size()), UVM_NONE)
  endtask
endclass