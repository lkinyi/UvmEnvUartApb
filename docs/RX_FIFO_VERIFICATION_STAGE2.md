# RX FIFO Verification Stage 2 开发与验收报告

交付日期：2026-11-24（Asia/Shanghai）。范围为 TP04、TP05、TP06；在当前开发分支增量开发，没有进入 TP07。

## 1. 验收结论与真实运行

TP04、TP05、TP06、Stage 1 回归和原有正常测试均 PASS。完成一次真实 Verilator 编译；正式套件含9个正向运行及5个负向失败传播运行，14个验收条目均满足预期。负向运行本身为 FAIL，并未计为功能 PASS。另有8份正式套件 VCD 二次比较全部 PASS、9项结果解析回归检查通过。初次TP04仿真及解析故障另见调试记录。

DUT RTL 未修改，两个 APB Agent、原有 IRQ 观察及失败判定未修改。没有 Commit、Push 或创建 PR。

机器验收：[stage2_acceptance.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/stage2_acceptance.json)；套件：[results.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/suite-1795451588600425534/results.json)；构建身份：[build_manifest.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/build_manifest.json)；工具环境：[environment.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/suite-1795451588600425534/environment.json)。

## 2. 基线核对与文件变化

开始时实际分支为 `work/uart-rx-fifo-verification`，HEAD 为 `88f1a218b89b9a80ac15b30053e6edd121aab93a`。重读 Stage 1 报告、验收 JSON、原始日志、收帧观察、FIFO/OV Checker、失败传播和 RTL，再比较 Stage 1 最终清单：82份源码/文档在开发前全部逐字节一致。

本批修改4份既有文件：

| 文件 | 增量职责 |
|---|---|
| `uvm_comp/cRxFifoScoreboard.sv` | RXT/IE影子、独立RXF/Raw/Masked预期、阈值和准入命中、OV生命周期、明确的停用清空守恒 |
| `uvm_comp/cRxFifoSequence.sv` | 参数化四档边界、三档到16项、稳定窗口改RXT、三种Raw源状态与IE sweep |
| `scripts/uartvip.py` | Stage 2计数解析、逐项必达门禁、flush守恒、准确记录动态配置 |
| `scripts/test_uartvip_results.py` | 增加缺边界/缺动态命中/缺源与IE组合/错误flush计数的拒绝PASS检查 |

新增9份项目文件：`pat/rx_fifo_tp04/`、`pat/rx_fifo_tp05/`、`pat/rx_fifo_tp06/`各含 `cVSequence.sv` 与 `test_base.txt`；`scripts/rx_fifo_stage2.py`；`scripts/rx_fifo_stage2_wave_audit.py`；本报告。三个入口均选择原 `cRxFifoTest`，共用已有环境和模型。

## 3. Checker、独立预期与有界执行

保持 BR=130/75、50/86ns时钟、8N1、TXT=00、UART0→UART1。仍逐帧等待独立串行解码完成和RX提交精确计数，局部上限2ms，每10us检查；全局上限100ms，仿真进程wall上限1800s。下一帧只在上一帧结束后投放，避免TX FIFO先溢满。BR、D9、EP均不热改。

期望数据来自固定APB输入并经独立串行START/8数据位/STOP观察核对。参考队列物理容量固定16，按独立占用决定接纳/拒收，指针由接纳/出队计数推导。RXF=(占用≥RXT阈值)，OV由真正满时拒收置位、DATA读请求清除；Raw/Masked读取和IE写入均不改变预测源。每个目标时钟沿后2ns继续比较7项指针/状态，避开RTL的#1更新。

CON、IE从合法APB写入维护影子，完整读回自动比较。独立Raw=TXE | RXF<<1 | OV<<2；UART1从未写TX DATA，因此TXE期望为1，合法8N1使PE/FE为0。Masked与独立Raw及IE影子逐位比较，完整32位比较也要求保留高位读零。没有用实际Raw或DUT rx_rxf生成期望，没有使用外部ctrl_if替代源判断。

`RX_ENV_TP04_HITS`、`RX_ENV_TP05_HITS`、`RX_ENV_TP06_HITS`和最终守恒在check_phase中执行，任何缺场景都会进入原UVM失败链路。Python再次核对完成契约、非零有效比较、全部必达计数及全输出错误。沿后连续状态检查、APB完成沿寄存器检查、串行计数、队列和结束检查共同约束结果。

## 4. TP04：四档边界与动态选择

Testcase：`rx_fifo_tp04`。每档先到T−1，再到T；非00档增加到T+1，再读回T，随后由T读到T−1；最后排空。表中为在线自动比较成功后记录的实际命中数。

| RXT | T | T−1/RXF0 | T/RXF1 | T+1/RXF1 | T→T−1解除 | 稳定窗口改配置 |
|---|---:|---:|---:|---:|---:|---:|
| 00 | 16 | 1 | 1 | 不适用（容量16） | 1 | 3 |
| 01 | 8 | 1 | 1 | 1 | 1 | 2 |
| 10 | 4 | 1 | 1 | 1 | 1 | 2 |
| 11 | 2 | 1 | 1 | 1 | 1 | 1 |

动态场景固定保存6项，配置顺序00→01→10→11→00→10→01→00。实际完整Raw依次为 `[1, 1, 3, 3, 1, 3, 1, 1]`（含TXE=1），对应RXF为 `[0, 0, 1, 1, 0, 1, 0, 0]`。8个改写窗口中完成帧数和DATA出队数保持不变；每次改写后等待20us再读状态。最后6个实际DATA为 `[5, 24, 43, 62, 81, 100]`，与固定输入逐项一致。

## 5. TP05：水位与物理容量独立

Testcase：`rx_fifo_tp05`。RXT=01/10/11达到阈值并读到RXF=1后，在禁止DATA读取期间继续逐帧接收；每帧检查占用与Raw，直到16项，再保持200us后排空，全部16项逐个比较内容和顺序。

| RXT | 阈值 | 水位后新接纳帧 | 到16项命中 | 有效读回 | 真正拒收 | OV置位 |
|---|---:|---:|---:|---:|---:|---:|
| 01 | 8 | 8 | 1 | 16 | 0 | 0 |
| 10 | 4 | 12 | 1 | 16 | 0 | 0 |
| 11 | 2 | 14 | 1 | 16 | 0 | 0 |

VCD再次确认每档16次提交期间有效DATA出队数没有变化；独立参考容量保持16，未按水位截断。RXT=00容量及17帧拒收复用本次TP03a/TP03b回归，不复制同内容场景。

## 6. TP06：IE、Raw、Masked独立性

Testcase：`rx_fifo_tp06`。顺序为RXF单源、OV单源、两源组合。每个源状态执行IE顺序00、02、00、04、00、06、02、04、06、00；每次写IE后读回并重复两轮SE/Raw/Masked读取。交替写入高位全1（如FFFFFFE2），仍要求完整IE读回仅为02，未使用高位为0。

| 源状态 | 独立完整Raw | IE00 Masked | IE02 Masked | IE04 Masked | IE06 Masked |
|---|---:|---:|---:|---:|---:|
| RXF单源 | 03 | 00 | 02 | 00 | 02 |
| OV单源 | 05 | 00 | 00 | 04 | 04 |
| RXF+OV | 07 | 00 | 02 | 04 | 06 |

以上为独立期望，也是实际32位读回比较结果；所有组合均实际到达，Raw含TXE，Masked没有使能TXE。

**OV单源的准备条件：** EN=1且不读DATA时，OV只能在满16项拒收后产生，而所有RXT阈值在16项均使RXF=1；读取DATA又会清OV，因此无法直接得到稳定的Raw OV单源。这里先完成真正的第17帧拒收，再在串行完全安静、禁止DATA读取的窗口写EN=0并等待2us。RTL明确清FIFO写指针而保持OV，模型将16项计为显式flush；重新使能后仍为占用0、Raw=05，再做OV单源IE验证。清空前后的OV均由Checker与Raw读回比较，结束后用一次空DATA读明确清OV。该准备动作没有改BR/D9/EP，也没有强制内部信号。

随后重新接收16项并制造第二次真正拒收，验证两源组合后完整读回这16项；首次正常DATA读清OV而RXF仍由占用决定。接纳34=有效读出18+显式清空16，拒收2，空读1，最终队列和在途帧均为空。不是把flush当作读出，也不是静默删除待比较数据。

| Raw所需源 | IE00命中 | IE02命中 | IE04命中 | IE06命中 |
|---|---:|---:|---:|---:|
| 2 | 8 | 4 | 4 | 4 |
| 4 | 8 | 4 | 4 | 4 |
| 6 | 8 | 4 | 4 | 4 |

VCD统计的屏蔽后状态真实转换（同一Raw源状态内）：

| 源 | RXF上升/下降 | OV上升/下降 |
|---|---:|---:|
| 2 | 3/3 | 0/0 |
| 4 | 0/0 | 3/3 |
| 6 | 3/3 | 3/3 |

## 7. 全部正向运行结果

下表全部来自本批原始日志与result.json，seed=1；全部UVM_ERROR/FATAL=0，协议错误=0，sim_exit与Make退出均为0。

| 测试 | 完整串行帧/提交 | 接纳/拒收 | 有效出队/数据比较 | 空读 | 状态读比较 | 状态周期 | 保持 | wall秒 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [TP04](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp04.s1.1795451589268128589.05e6f3/simulator.log) | 39/39 | 39/0 | 39/39 | 0 | 125 | 535721 | 5 | 58.3 |
| [TP05](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp05.s1.1795451648159860382.5ca32a/simulator.log) | 48/48 | 48/0 | 48/48 | 0 | 139 | 653297 | 3 | 66.5 |
| [TP06](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp06.s1.1795451715187705458.20e350/simulator.log) | 36/36 | 34/2 | 18/18 | 1 | 248 | 492738 | 3 | 51.9 |
| [observation_smoke](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451767753600904.799717/simulator.log) | 1/1 | 1/0 | 1/1 | 0 | 10 | 18189 | 1 | 2.6 |
| [TP01](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp01.s1.1795451770921357688.79bd80/simulator.log) | 2/2 | 2/0 | 2/2 | 6 | 31 | 33933 | 2 | 4.6 |
| [TP02](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp02.s1.1795451776318374716.94078b/simulator.log) | 40/40 | 40/0 | 40/40 | 0 | 49 | 551357 | 5 | 58.2 |
| [TP03a](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp03a.s1.1795451835287193651.7dce68/simulator.log) | 17/17 | 16/1 | 16/16 | 0 | 31 | 232907 | 1 | 24.8 |
| [TP03b](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp03b.s1.1795451860720495346.cb6c15/simulator.log) | 18/18 | 17/1 | 17/17 | 0 | 34 | 248628 | 2 | 24.7 |

原有 [baudrate_9600_complete](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_baudrate_9600_complete.s1.1795451886211419077.4843e3/simulator.log) 实际PASS：24次数据比较，0失败，COMPLETE_CHECK pending_tx/pending_rx均0，wall=55.6s。仍使用原Scoreboard。

Stage 2转换及寄存器比较计数：

| 测试 | RXF升/降 | OV升/降 | IE读回 | CON读回 | Raw/Masked比较 | flush |
|---|---:|---:|---:|---:|---:|---:|
| TP04 | 6/6 | 0/0 | 1 | 13 | 37/37 | 0 |
| TP05 | 3/3 | 0/0 | 1 | 3 | 45/45 | 0 |
| TP06 | 3/3 | 2/2 | 31 | 1 | 72/72 | 16 |

## 8. 失败传播、波形核验与Coverage边界

没有改协议Checker或IRQ Monitor以规避错误。本批在同一新二进制上重跑Stage 1五项故意失败，全部实际FAIL且Make返回2；预期错误均出现，没有额外非预期UVM错误。仿真器本身通过UVM finish返回0，最终失败由既有UVM错误统计和Python全输出判定传播。

| 负向测试 | 预期错误 | 实际结果 | Make退出 | 验收 |
|---|---|---|---:|---|
| [negative_protocol](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451942595435996.815d04/simulator.log) | `[APB_PROTOCOL]` | FAIL | 2 | PASS |
| [negative_uart_glitch](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451945437240093.29845d/simulator.log) | `[UART_PROTOCOL]` | FAIL | 2 | PASS |
| [negative_expectation](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451948069721268.c34a18/simulator.log) | `[READ FAIL]` | FAIL | 2 | PASS |
| [negative_global_timeout](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451950922178669.ea8df3/simulator.log) | `[CTEST TIMEOUT]` | FAIL | 2 | PASS |
| [negative_missing_frame](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451951948141319.bd2709/simulator.log) | `[RX_DUT_FRAME_TIMEOUT]` | FAIL | 2 | PASS |

8份波形核验：

| 测试 | 独立VCD比较 | 原始VCD |
|---|---|---|
| TP04 | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp04.s1.1795451589268128589.05e6f3/stage2-wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp04.s1.1795451589268128589.05e6f3/wave.vcd) |
| TP05 | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp05.s1.1795451648159860382.5ca32a/stage2-wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp05.s1.1795451648159860382.5ca32a/wave.vcd) |
| TP06 | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp06.s1.1795451715187705458.20e350/stage2-wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp06.s1.1795451715187705458.20e350/wave.vcd) |
| observation_smoke | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451767753600904.799717/wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_observation_smoke.s1.1795451767753600904.799717/wave.vcd) |
| TP01 | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp01.s1.1795451770921357688.79bd80/wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp01.s1.1795451770921357688.79bd80/wave.vcd) |
| TP02 | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp02.s1.1795451776318374716.94078b/wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp02.s1.1795451776318374716.94078b/wave.vcd) |
| TP03a | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp03a.s1.1795451835287193651.7dce68/wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp03a.s1.1795451835287193651.7dce68/wave.vcd) |
| TP03b | [PASS](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp03b.s1.1795451860720495346.cb6c15/wave-audit.json) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp03b.s1.1795451860720495346.cb6c15/wave.vcd) |

本次WAVE=1、COV=0。功能证据使用在线必达事件计数、逐转换比较和VCD复核；这些计数不等于仿真工具功能覆盖率，不给覆盖率百分比。当前项目功能coverage导出/合并链路未在本批验证，也未将既有UART示例covergroup或代码coverage冒充TP04～06覆盖闭合。四档阈值、下降解除、动态选择、继续接纳、三种源状态、四种IE组合以及Raw/Masked变化均有可审计命中。

## 9. 调试、DUT问题与执行方式

首次真实构建成功，Make退出0，wall=520.407s。首次TP04仿真本身PASS（39帧、39次数据比较、0模型错误），但Python解析把UVM页脚消息ID计数误作RXT数据行，触发KeyError，初次套件实际FAIL/BLOCKED。修复为只解析以rxt=/source=开头的数据行，并在解析回归加入真实页脚格式；没有改SV预期或检查。原失败套件、日志和VCD保留：[results.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/suite-1795450942015144846/results.json)。

正式套件使用同一指纹匹配二进制重跑，TP04→TP05→TP06及全部回归通过。编译保留既有宏重复定义警告，没有新DUT疑似问题。OV在停用清空后保留属于本次明确检查的现有RTL行为，后续若系统规格要求不同应另行讨论。

复现全套时需选择新的构建名，避免覆盖本批证据：

```bash
source scripts/env_local.sh
python3 scripts/rx_fifo_stage2.py --root build/rx-stage2-NEW --build-name build-01
```

复用本批二进制重新运行可用`--skip-build`；只有源码、生成文件、WAVE/COV选项和二进制SHA256均匹配才允许运行，每次仍创建新的suite/run目录。

## 10. Git状态与历史保全

开发前对19041份既有文件建立SHA256清单，交付核对缺失0；仅上述4份既有验证文件按授权改变。DUT全部文件、Stage 1及更早build中的日志/VCD/验收JSON全部逐字节保持。原28份未跟踪文件均保留，其中3份（两份专项类及解析测试）按本批要求增量修改，其余未覆盖。

基线核对：[stage1-source-baseline-check.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/stage1-source-baseline-check.json)；文件清单：[preservation-before.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/preservation-before.json)；保全结果：[preservation-after.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/preservation-after.json)。Git状态详见验收JSON；分支`work/uart-rx-fifo-verification`，HEAD`88f1a218b89b9a80ac15b30053e6edd121aab93a`，暂存区无变化，未Commit/Push。CRLF文件按`git -c core.whitespace=cr-at-eol diff --check`检查通过，保留原行尾而未批量改写Stage 1文件。

## 11. 未完成项与第三批建议

本批TP04～TP06没有未完成验收项。未实现TP07的精确逐周期IRQ检查，也未宣称IRQ时序已闭合；原有IRQ观察、错误判定和双APB Agent保持原实现。

第三批建议在本模型上建立本端pclk逐周期IRQ期望，明确源/IE变化到寄存IRQ的采样延迟；验证先源后IE、先IE后源、组合源分别撤销、关IE、OV清而RXF仍保持等轨迹，并增加缺IRQ负向检查。随后处理同拍收读、复位/停用恢复及工具功能coverage导出和合并资格。保留本次OV单源准备动作的明确语义，不扩大到运行中改BR/D9/EP。本次开发在Stage 2结束。
