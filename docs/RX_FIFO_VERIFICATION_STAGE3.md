# RX FIFO Verification Stage 3 开发与验收报告

交付日期：2026-11-24（Asia/Shanghai）。本阶段完成 TP07、功能覆盖模型和正式回归，未进入后续功能开发。

## 验收结果与入口

TP07、RXF/OV 单使能源、多源合并、逐周期 IRQ Checker 均 PASS。正式套件10个正向运行全部 PASS；5个负向自测的实际结果全部为 FAIL，且都被回归脚本正确识别。Stage 1/2 的7个专项以及 `baudrate_9600_complete` 全部重新仿真通过。负向自测没有计入正向 PASS，也没有贡献正式 Coverage。

功能覆盖采用真实 SystemVerilog covergroup/coverpoint/cross，工具导出的项目模型 bins 等权命中率为 **66/71 = 92.9577%**。52个语义 bins 中47个命中，5个明确保留为未实施；Raw源/IE 的12个 cross bins及7个边缘 bins全部命中。阶段内语义需求为47/47，这个数不能表述为全部 UART 功能100%覆盖。

[最终验收JSON](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/stage3_acceptance.json)；[正式结果](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/results.json)；[结果表](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/results.md)；[覆盖报告](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/coverage.md)；[未命中清单](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/unhit.json)；[IRQ证据](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/irq-evidence.json)；[负向证据](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/negative-checker-evidence.json)。

DUT 未修改；未发现本阶段范围内的真实 DUT 设计问题。已真实编译、运行、保存日志及 VCD。没有 Commit、Push 或创建 PR。

## 基线和保全

开始时分支 `work/uart-rx-fifo-verification`，HEAD `88f1a218b89b9a80ac15b30053e6edd121aab93a`，已有9份已跟踪文件修改及 Stage 1/2 未跟踪文件。读取 F2 可行性审核、Stage 1/2 报告、Stage 2 原始验收结果和日志，并检查实际 RTL 与模型。Stage 2 最终源码清单86份文件在开发前全部一致，见 [基线核对](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/stage2-source-baseline-check.json)。

开发前对23,090份既有文件建立 SHA256 清单。交付核对5,198,394,073 bytes：缺失0，23,085份逐字节不变，仅下表5份既有验证文件发生授权修改。全部历史 build、日志、VCD、原有未跟踪文件均保留，Stage 1/2 报告未改。证据见 [开发前清单](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/preservation-before.json)、[完整保全核对](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/preservation-after.json)、[最终修改文件指纹](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/preservation-final.json)。

运行全部放在新目录 `build/rx-stage3-20261124-004204`；每次仿真使用唯一 test/seed/时间戳目录。已保存首次调试、被替代的分类失败套件和最终正式套件，未重用历史验收目录。

## 文件与组件

| 类型 | 文件 | 职责 |
|---|---|---|
| 修改 | [scripts/uartvip.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/uartvip.py) | 逐运行 IRQ/覆盖计数解析、严格 TP07 完成契约、覆盖数据库隔离、构建身份、限定有效输入合并 |
| 修改 | [sim/testTop.sv](D:/Documents/projects/验证/UvmEnvUartApb/sim/testTop.sv) | 连接 UART1 外部 ctrl_if 只读探针并引入两个新验证类 |
| 修改 | [uvm_comp/ifDut.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/ifDut.sv) | 被动探针增加 irq |
| 修改 | [uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv) | 复用独立模型接入 IRQ/覆盖；精确处理原 TP06 停用清空的下一拍时序；最终命中门禁 |
| 修改 | [uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv) | TP07 三组真实场景和14个有界检查点 |
| 新增 | [uvm_comp/cRxIrqChecker.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxIrqChecker.sv) | 专用逐周期 Checker、诊断、稀疏事件 CSV、五种采样副本负向注入 |
| 新增 | [uvm_comp/cRxFunctionalCoverage.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFunctionalCoverage.sv) | 52个语义事件 bins、3×4 Raw源/IE cross及可核对命中数 |
| 新增 | [pat/rx_fifo_tp07/cVSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/pat/rx_fifo_tp07/cVSequence.sv) | TP07 pattern入口 |
| 新增 | [pat/rx_fifo_tp07/test_base.txt](D:/Documents/projects/验证/UvmEnvUartApb/pat/rx_fifo_tp07/test_base.txt) | 复用 cRxFifoTest |
| 新增 | [scripts/rx_fifo_stage3.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3.py) | 串行正式套件、正负向分列、当前构建 Coverage 合并和全 pattern 状态 |
| 新增 | [scripts/rx_fifo_stage3_wave_audit.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3_wave_audit.py) | VCD独立 FIFO/IE/RXT/OV 与精确IRQ时序核验 |
| 新增 | [scripts/rx_fifo_stage3_result_selftest.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3_result_selftest.py) | 以真实TP07日志为输入的12项判定门禁自测 |
| 新增 | [docs/RX_FIFO_VERIFICATION_STAGE3.md](D:/Documents/projects/验证/UvmEnvUartApb/docs/RX_FIFO_VERIFICATION_STAGE3.md) | 本报告 |

继续复用 Stage 1 的固定波特率串行解码、独立源端APB输入队列、完成帧配对、容量16的FIFO模型、顺序比较、OV置位/读清模型和结束守恒；复用 Stage 2 的RXT阈值、IE影子、完整Raw/Masked寄存器比较。两个APB Agent、factory选择、全局watchdog及原有协议Checker继续使用。没有引入RAL、改APB Agent或修改DUT来适配测试。

## IRQ 时钟与 Checker 方法

目标是UART1的pclk，周期86ns；UART0周期50ns，不能用发送端时钟预测接收端IRQ。RTL的Masked是组合值：`Raw & IE`。合并外部IRQ在pclk沿采入沿前Masked，并通过非阻塞赋值的`#1`在沿后1ns更新。

设E为一次APB写IE、FIFO入队/出队或OV更新沿。E+1ns之后，新Raw/IE/Masked已经生效，但外部IRQ仍是E沿采入的旧Masked。E+86ns的下一沿采入新Masked，外部IRQ在E+87ns更新。Checker在每个接收端沿后2ns比较，避开RTL沿后1ns的更新与组合收敛。

Checker持有上一周期安全采样后的**独立模型**Raw与IE快照。当前沿的IRQ预期由这份沿前快照做OR得出；当前沿后模型更新只用于下一个沿的预期。APB Monitor可能在当前沿的active区先更新IE、RXT或队列，因此不能直接在当前沿用已更新模型替代沿前状态。DUT的Raw、Masked、RXF、OV及IRQ均不构造唯一预期；实际外部IRQ仅作为比较对象。

原TP06的EN写零在下一沿清FIFO。模型保留EN写入过渡沿，随后按沿前EN为零处理flush，再为下个IRQ沿保存清空后的独立Raw快照。flush仍单独计入守恒，不计为DATA读出。

每个有效接收端周期均检查应出现、不得误出现、保持和撤销。错误输出包含cycle、time、expectedIRQ、actualIRQ、验证采样副本、沿前模型Raw/IE/Masked、沿后模型状态及完成/出队事件。所有IRQ错误通过`require_ok`进入UVM_ERROR和最终FAIL；不是只在IRQ上升沿观察。

`irq-events.csv`保留源/IE变化、IRQ跳变、错误及初始节点，稳态周期由汇总计数证明持续比较。另用VCD脚本重建FIFO/IE/RXT/OV，在每个波形时间组比较外部IRQ，并要求实际跳变恰好位于预测接收端沿后1ns。

## TP07 实际场景

固定UART0→UART1、BR=130/75、EN=1、8N1、TXT=00；RXT先11（阈值2）后01（阈值8）。逐帧等待真实串行完整帧及RX提交，不用TX写次数代替完成帧。

RXF组先开IE02，再收两项，验证触发和保持；读一项到占用1验证撤销。随后IE00时接收两项，先确认Raw有效且IRQ0，再开IE02触发，关闭IE后Raw仍有效但IRQ撤销，最后排空。

OV组在IE00下先收满16项，再真实完成第17帧且拒收。OV原始位为1而IRQ保持0；写IE04后仅OV可产生外部中断，保持OV，再读首项清OV并撤销IRQ。这里Raw仍可包含RXF，但RXF IE关闭；“OV单源”指唯一使能的中断源。剩余15项全部按序读回。

合并组IE06、阈值8，从占用8的RXF单源继续接收至16，并真实拒收第17帧。首个DATA读使OV清零、占用降到15，RXF继续有效，IRQ保持1；累计读出9项后占用7，RXF解除，IRQ才撤销。余7项继续按序读回。所有状态由正常串行/APB行为产生，没有force内部源。

| ID | 场景 | 占用 | Raw（含TXE） | IE | IRQ | 时间ns |
|---|---|---:|---|---|---:|---:|
| 0 | RXF_assert_and_hold_IE_first | 2 | 03 | 02 | 1 | 2516749 |
| 1 | RXF_DATA_deassert | 1 | 01 | 02 | 0 | 2518985 |
| 2 | RXF_raw_active_IE_off | 2 | 03 | 00 | 0 | 5032507 |
| 3 | RXF_enable_after_source | 2 | 03 | 02 | 1 | 5033797 |
| 4 | RXF_disable_preserves_raw | 2 | 03 | 00 | 0 | 5035087 |
| 5 | OV_real_rejection_IE_off | 16 | 07 | 00 | 0 | 24833319 |
| 6 | OV_enable_after_source | 16 | 07 | 04 | 1 | 24834609 |
| 7 | OV_held | 16 | 07 | 04 | 1 | 24855593 |
| 8 | OV_DATA_clear_no_other_enabled_source | 15 | 03 | 04 | 0 | 24857829 |
| 9 | merged_RXF_only | 8 | 03 | 06 | 1 | 34269067 |
| 10 | merged_RXF_and_OV | 16 | 07 | 06 | 1 | 44752123 |
| 11 | merged_OV_removed_RXF_keeps_IRQ | 15 | 03 | 06 | 1 | 44754359 |
| 12 | merged_RXF_below_8_IRQ_deasserts | 7 | 01 | 06 | 0 | 44765023 |
| 13 | merged_final_empty_no_IRQ | 0 | 01 | 06 | 0 | 44774483 |

TP07实测：完整串行帧/提交38，接纳36，满拒收2，有效出队及数据比较36，串行数据比较38，状态寄存器比较66，保持窗口5，最大占用16。IRQ比较522,966周期、0错误、4次上升、4次下降、128,503次高电平保持，多源去OV仍保持命中1次。最终队列和在途帧全部为空。

[正式TP07日志](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/simulator.log)；[正式TP07 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/wave.vcd)；[在线事件轨迹](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/irq-events.csv)；[独立波形核验](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/stage3-wave-audit.json)。

独立VCD核验PASS：522,966个pclk周期、4,162,933个时间组，实际8次IRQ跳变全部符合精确时序；拒收、顺序、守恒和清OV后剩余RXF维持IRQ均通过。五个负向测试仍使用相同DUT刺激，其中merge负向的DUT VCD与正向VCD SHA256完全相同，说明故障只进入Checker采样副本。

## Checker 负向自测

五种`+IRQ_FAULT=...`都只改Checker的局部`observed`，不改DUT RTL或驱动信号。每项恰好注入一次，触发一个`RX_DUT_IRQ`时序错误。结束时的IRQ错误计数门禁仍失败；被故意污染的有效命中数还会按预期触发场景计数门禁。脚本核对每种模式精确的上升/下降/合并保持缺额，拒绝其他错误。

| 故障 | 周期 | 时间ns | 预期 | DUT实际 | 注入采样 | IRQ错误 | UVM错误 | 实际结果 | Make/sim退出 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| missing | 26163 | 2250149 | 1 | 1 | 0 | 1 | 3 | FAIL（预期） | 2/0 |
| stuck | 29267 | 2517093 | 0 | 0 | 1 | 1 | 3 | FAIL（预期） | 2/0 |
| early | 26162 | 2250063 | 0 | 0 | 1 | 1 | 2 | FAIL（预期） | 2/0 |
| late | 26163 | 2250149 | 1 | 1 | 0 | 1 | 3 | FAIL（预期） | 2/0 |
| merge | 520375 | 44752381 | 1 | 1 | 0 | 1 | 3 | FAIL（预期） | 2/0 |

missing检出应拉高却未拉高；stuck检出应撤销却仍高；early在源更新沿提前一周期出现；late在应到达沿仍未出现；merge在OV解除而RXF继续有效时错误撤销。5项自测验收均PASS，但原始测试结果保留FAIL。UVM用`$finish`结束时模拟器退出0，Python依完整错误输出和契约返回失败，Make退出2，因此不能只看模拟器退出码。

另外，以真实完成TP07日志构造的12项结果门禁自测全部通过，覆盖缺IRQ汇总、零比较、错误数非零、缺/重复场景、缺多源保持、缺覆盖样本、缺数据比较、未finalize、迟发错误、非零进程退出和wall timeout。原有9项解析回归也全部通过。错误的COV选项在仿真启动前被拒绝，Make退出2。

## Functional Coverage 统计口径

实际工具为Verilator 5.052、GCC 13.3.0、Python 3.12.3，UVM沿用Stage 1/2固定版本。当前WSL及Windows PATH均未发现Questa，未宣称Questa编译或UCDB验收。

先执行独立coverpoint/cross小仿真，确认52类实际项目采样所需的值bins及cross可导出，零命中bins也保留。正式构建使用`--coverage-user`，C++日志确认`VM_COVERAGE=1`。这里没有用代码覆盖率替代功能覆盖率，也未采用`get_coverage()`的组间平均值；92.9577%是原生工具导出项目模型71个bins按命中阈值1等权计算。

52个语义事件覆盖FIFO空/非空/15/16、正常入出队、空读、满拒收、OV生命周期、顺序读回、31→0完整指针回绕、四档RXT的T−1/T/合法T+1、RXF上升/下降、水位后继续接收、IE开关、Raw/Masked关系、改IE而Raw不变、三种使能源和IRQ时序。覆盖事件仅在对应模型检查成功后采样。状态bin按符合条件的实际周期采样，操作bin按独立事件计数变化采样，所以“命中数”不等于独立测试数量。

Raw源2/4/6 × IE0/2/4/6的12格cross全部有设计意义，没有扩大到无关全笛卡尔积。该组同时导出3个源边缘bin及4个IE边缘bin。52个语义bin和12个cross bin的工具累计值与有效运行日志命中计数逐项完全一致。

| 统计项 | 实际命中/分母 | 说明 |
|---|---|---|
| 语义事件完整清单 | 47/52 | 5个未实施项目仍保留零命中 |
| 本阶段语义事件 | 47/47 | 只用于说明冻结范围达成情况 |
| 源/IE cross | 12/12 | 真正原生cross bins |
| 源/IE边缘bins | 7/7 | 同一covergroup的coverpoints |
| 项目模型总bins | 66/71（92.9577%） | 完整模型等权统计 |
| 工具内全部covergroup记录 | 67/72 | 额外含原有UART协议back_2_back bin，单列，不混入项目模型分母 |

未命中：同拍收读、运行中reset恢复、Parity Error、Frame Error、反向UART1→UART0，各0命中。它们在实现时已声明并保留，没有为凑百分比删bin。RXT00的T+1=17超出物理容量，明确列为不可达水位点，真实第17帧通过满拒收覆盖。运行中复杂BR/D9/EP切换、全五源中断及disable恢复未扩展；已有TP06的有界flush准备仍保留。

正式合并只含最终套件10个正常PASS运行，不纳入首次调试、被替代套件或五个负向数据库。输入清单逐文件保存SHA256和当前构建身份；工具merge/export退出码都必须为0。原有正常测试沿用旧SB，不伪造新模型事件贡献。

工具目录原先缺少`verilator_coverage`后端，已从现有5.052源码在Stage 3独立目录编译。保留该二进制，并向工具目录补充原本不存在的`bin/verilator_coverage_bin_dbg`，未覆盖已有文件，详见coverage-tool/manifest.json。额外的源码注释导出试验因5.052对中文路径的编码失败，保留FAIL；正式原生.dat、.info及逐bin JSON/Markdown均已成功导出。通用`make cov`改用无需重新打开源码的导出路径并再次实际PASS。这不影响正式功能bin计数。

## 正式回归

每项seed均为1，定向刺激固定，不能以多seed结论扩大随机空间覆盖。构建前/运行前保存源码、生成文件、binary SHA256、WAVE/COV选项和UVM版本。每次run再次拒绝过期源码、错误选项或二进制身份不符。

| Test | seed | actual | acceptance | seconds | data compares | IRQ cycles/errors | make/sim exit |
|---|---:|---|---|---:|---:|---|---|
| TP07 | 1 | PASS | PASS | 46.9 | 36 | 522966/0 | 0/0 |
| negative_missing | 1 | FAIL | PASS | 47.9 | 36 | 522966/1 | 2/0 |
| negative_stuck | 1 | FAIL | PASS | 47.6 | 36 | 522966/1 | 2/0 |
| negative_early | 1 | FAIL | PASS | 45.3 | 36 | 522966/1 | 2/0 |
| negative_late | 1 | FAIL | PASS | 43.7 | 36 | 522966/1 | 2/0 |
| negative_merge | 1 | FAIL | PASS | 42.8 | 36 | 522966/1 | 2/0 |
| TP01 | 1 | PASS | PASS | 3.1 | 2 | 33933/0 | 0/0 |
| TP02 | 1 | PASS | PASS | 45.1 | 40 | 551357/0 | 0/0 |
| TP03a | 1 | PASS | PASS | 19.1 | 16 | 232907/0 | 0/0 |
| TP03b | 1 | PASS | PASS | 20.0 | 17 | 248628/0 | 0/0 |
| TP04 | 1 | PASS | PASS | 44.3 | 39 | 535721/0 | 0/0 |
| TP05 | 1 | PASS | PASS | 51.8 | 48 | 653297/0 | 0/0 |
| TP06 | 1 | PASS | PASS | 37.2 | 18 | 492739/0 | 0/0 |
| legacy_complete | 1 | PASS | PASS | 38.2 | 24 | N/A/N/A | 0/0 |
| observation_smoke | 1 | PASS | PASS | 1.8 | 1 | 18189/0 | 0/0 |

所有正常专项的UVM_ERROR/FATAL、IRQ错误、协议Checker错误均为0；结束时契约满足，FIFO模型排空，源端/串行/完成计数配对，无异常pending或缺帧。旧正常测试比较24次，COMPLETE_CHECK明确pending_tx=0、pending_rx=0。它使用旧SB，因此IRQ周期记N/A，不伪造新Checker覆盖。

全pattern库存26项：本次10 PASS、0正常FAIL、1 SKIP、15 NOT_RUN。原`baudrate_9600`本次NOT_RUN，另保留其历史FAIL（24写16读、8项未排空）；其余未执行pattern和原有SKIP均保持状态。没有宣称整个历史pattern库全部通过，逐项见pattern-inventory.json。

## 构建、运行与调试记录

WSL项目目录：`/mnt/d/Documents/projects/验证/UvmEnvUartApb`。实际主要命令：

```bash
source scripts/env_local.sh
make build BUILD_DIR=build/rx-stage3-20261124-004204/build-01 WAVE=1 COV=1 JOBS=2
python3 scripts/rx_fifo_stage3.py --root build/rx-stage3-20261124-004204 --skip-build --tests TP07
python3 scripts/rx_fifo_stage3.py --root build/rx-stage3-20261124-004204 --skip-build --tests TP06
python3 scripts/rx_fifo_stage3.py --root build/rx-stage3-20261124-004204 --skip-build
```

完整构建实际PASS，约357秒。每次Make命令及仿真器参数、seed、cwd、配置、退出码和耗时保存在suite的`*.command.json`、run内`command.json`与`result.json`；实际Verilator编译命令和指纹保存在build_manifest.json。

首次TP07和TP06调试均PASS。首次正式套件中，Checker已经正确FAIL，但脚本未将故意失配导致的有效命中数减少归为预期派生失败，造成负向验收FAIL。停止该套件并保留superseded.json和全部原始文件；只修复负向验收规则，核对精确计数缺额，没有放松正常Checker。随后完整重新执行15项，最终套件全部符合预期。Coverage后端缺失、源码注释导出失败记录也保留。

## Git 与可用结论

分支和HEAD与开发前一致。最终仍有原9份已跟踪文件修改及Stage 1/2/3未跟踪文件；本批相对开始现场只修改5份既有文件，新增8份项目文件。完整状态见git-status-final.txt。全工作树git diff --check仍报告继承的Stage 1/2行尾空白；对字节指纹核实过的Stage 2快照逐行比较，Stage 3新增行没有行尾空白。没有为格式问题改写既有历史组件。DUT diff为空，历史证据哈希不变。source-final.json与source-final.zip保存交付源码快照。

可用于项目总结的真实结果：在UART-APB UVM环境中完成RX FIFO容量/溢出/水位/IE及合并IRQ验证；以独立参考模型实现逐接收端时钟IRQ检查，完成5类预期失败自测；正式10个正向测试PASS，功能模型66/71 bins命中。该表述限定于本报告的8N1、单向、RXF/OV两类源范围。
