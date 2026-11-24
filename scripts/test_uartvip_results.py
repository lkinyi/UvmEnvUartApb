"""Result-parser regression guards; real simulator negative tests live in the suite."""
from pathlib import Path
import runpy
import unittest

parse_result = runpy.run_path(str(Path(__file__).with_name("uartvip.py")))["parse_result"]
GOOD = "** TEST PASSED **\nUVM_ERROR : 0\nUVM_FATAL : 0\n"


class ResultPropagation(unittest.TestCase):
    def test_zero_error_pass(self):
        self.assertEqual(parse_result(GOOD, 0, False)["status"], "PASS")

    def test_display_error_even_after_pass_and_summary(self):
        for tag in ("APB_ERROR", "UART_ERROR"):
            with self.subTest(tag=tag):
                self.assertEqual(parse_result(GOOD + f"[{tag}] late final error\n", 0, False)["status"], "FAIL")

    def test_late_uvm_fatal_and_nonzero_exit(self):
        for text, rc in ((GOOD + "UVM_FATAL @ 900: late failure\n", 0), (GOOD, 9)):
            self.assertEqual(parse_result(text, rc, False)["status"], "FAIL")

    def test_missing_summary_or_result(self):
        for text in ("** TEST PASSED **\n", "UVM_ERROR : 0\nUVM_FATAL : 0\n"):
            self.assertEqual(parse_result(text, 0, False)["status"], "FAIL")

    def test_stage1_cannot_pass_without_contract(self):
        text = "Running test test_rx_fifo_tp01...\n" + GOOD
        self.assertEqual(parse_result(text, 0, False)["status"], "FAIL")

    def test_timeout_overrides_pass(self):
        self.assertEqual(parse_result(GOOD, 124, True)["status"], "FAIL")

    def test_stage1_exact_contract_is_checked_independently(self):
        summary = ("sent=1 pin_started=1 pin_completed=1 completed=1 accepted=1 rejected=0 popped=1 "
                   "empty_reads=0 data_compares=1 pin_compares=1 state_checks=20000 status_compares=9 "
                   "holds=1 max_occupancy=1 boundary15=0 boundary16=0 overflow_hits=0 errors=0 finalized=1")
        prefix = ("Running test test_rx_fifo_observation_smoke...\n"
                  "[RX_CONTRACT] scenario=smoke required_frames=1 required_accepts=1 required_rejects=0 "
                  "required_pops=1 required_empty=0 required_holds=1\n[RX_FIFO_SUMMARY] ")
        self.assertEqual(parse_result(prefix+summary+"\n"+GOOD, 0, False)["status"], "PASS")
        for original, bad in (("data_compares=1", "data_compares=0"), ("pin_completed=1", "pin_completed=0"),
                              ("holds=1", "holds=0"), ("completed=1", "completed=0")):
            with self.subTest(counter=original):
                text = prefix+summary.replace(original, bad)+"\n"+GOOD
                self.assertEqual(parse_result(text, 0, False)["status"], "FAIL")

    def test_stage2_requires_real_boundary_and_dynamic_hits(self):
        text = ("Running test test_rx_fifo_tp04...\n[RX_CONTRACT] scenario=tp04 required_frames=39 "
                "required_accepts=39 required_rejects=0 required_pops=39 required_empty=0 required_holds=5\n"
                "[RX_FIFO_SUMMARY] sent=39 pin_started=39 pin_completed=39 completed=39 accepted=39 rejected=0 popped=39 "
                "empty_reads=0 data_compares=39 pin_compares=39 state_checks=100 status_compares=50 holds=5 "
                "max_occupancy=16 boundary15=1 boundary16=1 overflow_hits=0 errors=0 finalized=1\n"
                "[RX_STAGE2_SUMMARY] flushed=0 required_flushed=0 raw_compares=10 masked_compares=10 "
                "con_compares=10 ie_compares=1 rxf_rises=6 rxf_falls=6 ov_rises=0 ov_falls=0\n")
        text += ''.join(f'[RX_STAGE2_RXT] rxt={r} below=1 at=1 above={0 if r==0 else 1} down=1 dynamic=1\n' for r in range(4))
        text += ''.join(f'[RX_STAGE2_IE] source={s} ie={i} hits=0\n' for s in (2,4,6) for i in (0,2,4,6))
        self.assertEqual(parse_result(text+GOOD+'[RX_STAGE2_RXT] 4\n[RX_STAGE2_IE] 12\n',0,False)['status'],'PASS')
        for good,bad in [('dynamic=1','dynamic=0'),('down=1','down=0'),('rxf_falls=6','rxf_falls=0')]:
            self.assertEqual(parse_result(text.replace(good,bad,1)+GOOD,0,False)['status'],'FAIL')
        self.assertEqual(parse_result(text.split('[RX_STAGE2_SUMMARY]')[0]+GOOD,0,False)['status'],'FAIL')

    def test_stage2_requires_every_source_enable_pair_and_flush_accounting(self):
        text = ("Running test test_rx_fifo_tp06...\n[RX_CONTRACT] scenario=tp06 required_frames=36 "
                "required_accepts=34 required_rejects=2 required_pops=18 required_empty=1 required_holds=3\n"
                "[RX_FIFO_SUMMARY] sent=36 pin_started=36 pin_completed=36 completed=36 accepted=34 rejected=2 popped=18 "
                "empty_reads=1 data_compares=18 pin_compares=36 state_checks=100 status_compares=50 holds=3 "
                "max_occupancy=16 boundary15=2 boundary16=2 overflow_hits=2 errors=0 finalized=1\n"
                "[RX_STAGE2_SUMMARY] flushed=16 required_flushed=16 raw_compares=10 masked_compares=10 "
                "con_compares=1 ie_compares=31 rxf_rises=3 rxf_falls=3 ov_rises=2 ov_falls=2\n")
        text += ''.join(f'[RX_STAGE2_RXT] rxt={r} below=0 at=0 above=0 down=0 dynamic=0\n' for r in range(4))
        text += ''.join(f'[RX_STAGE2_IE] source={s} ie={i} hits=2\n' for s in (2,4,6) for i in (0,2,4,6))
        self.assertEqual(parse_result(text+GOOD,0,False)['status'],'PASS')
        for good,bad in [('source=4 ie=2 hits=2','source=4 ie=2 hits=0'),('flushed=16','flushed=0'),('ov_rises=2','ov_rises=0')]:
            self.assertEqual(parse_result(text.replace(good,bad,1)+GOOD,0,False)['status'],'FAIL')


if __name__ == "__main__":
    unittest.main()
