# UART-APB UVM 最终简历交付审核

审核日期：2026-11-24（Asia/Shanghai）。

审核对象：D:/Documents/projects/验证/UvmEnvUartApb；分支 work/uart-rx-fifo-verification；HEAD 88f1a218b89b9a80ac15b30053e6edd121aab93a。

**结论：已实现的单向 8N1 RX FIFO / RXF / OV / IE / 合并 IRQ 专项成果可以用于简历，须保留下文的范围及统计口径。基本 TP01～TP07 均有实际 Testcase、自动检查和真实 PASS 证据；原 F2 计划的扩展范围尚未全部完成。**

本次只读审核既有报告、源码、JSON、日志、VCD 和 Coverage 数据。唯一新增项目文件为本报告。未执行 gen、build、仿真、回归、覆盖率工具或新开发；未修改既有源码、脚本、报告、结果或工具安装，未 Commit、Push。下文的“重新解析”“重算”均指读取已存在的数据，在内存完成核对。

## 审核结论与必须保留的限定

| 审核项 | 结论 |
|---|---|
| TP01～TP07 对应实现与证据 | 基本冻结范围通过；TP03 分 a/b，共 8 个 TP pattern，另有观察 smoke 和既有 complete 测试 |
| 正式正向回归 | 最终 Stage 3 套件 10 个不同正向测试，各 seed=1、各执行 1 次，10/10 PASS；另有 5 个预期 FAIL 的 IRQ 自测 |
| 原生 SV Functional Coverage | 原生 covergroup 导出项目模型 71 个 bin，按命中至少 1 次等权重算为 66/71=92.9577%；不是工具默认 LCOV 汇总值 |
| 默认 LCOV 汇总 | 正式 functional.info 为 BRH=59、BRF=71，即 83.0986%；本机工具默认按至少 10 次命中统计，差异可解释 |
| 自定义阶段内事件 | 47/47 仅是冻结范围的语义事件命中；完整语义清单为 47/52，不能写 UART 功能覆盖率 100% |
| IRQ Checker | 对有效观察窗口的每个 UART1 pclk 周期做独立预期比较；TP07 比较 522,966 周期、0 错误 |
| IRQ 负向失败链路 | 5 个模式均实际 FAIL；Python run 返回失败、Make 返回 2；模拟器本身返回 0 |
| 17 / 16 / 1 与 OV | TP03a 为 17 个完整串行帧、16 接纳、1 拒收、16 按序读回；TP03b 另加恢复帧，所以为 18 / 17 / 1 |
| DUT 与既有文件 | DUT 无逻辑修改；历史文件无缺失，历史 build 内容保留；既有验证组件存在明确的增量修改，不能称全部验证代码原样未变 |
| 可复现性 | 当前 WSL 本机工具链具备构建、单测、正式回归和功能覆盖数据生成方法；异机安装和 Questa 路径尚未验收 |

重要的交付区别：通用 make cov 的最后一次成功导出合并 13 个合格 PASS 运行，包含调试/早期套件的正常运行；正式 66/71 的输入严格限定为最终套件的 10 个正向运行。两份数据不能互换引用。Stage 3 的报告已经说明“阈值 1、项目模型等权”，但没有解释 functional.info 默认汇总 59/71，本报告补充该项。

## 证据入口与本次核对方法
| 材料 | 路径 |
|---|---|
| Stage 1 报告 | [RX_FIFO_VERIFICATION_STAGE1.md](D:/Documents/projects/验证/UvmEnvUartApb/docs/RX_FIFO_VERIFICATION_STAGE1.md) |
| Stage 2 报告 | [RX_FIFO_VERIFICATION_STAGE2.md](D:/Documents/projects/验证/UvmEnvUartApb/docs/RX_FIFO_VERIFICATION_STAGE2.md) |
| Stage 3 报告 | [RX_FIFO_VERIFICATION_STAGE3.md](D:/Documents/projects/验证/UvmEnvUartApb/docs/RX_FIFO_VERIFICATION_STAGE3.md) |
| Stage 1 验收 | [stage1_acceptance.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/stage1_acceptance.json) |
| Stage 2 验收 | [stage2_acceptance.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/stage2_acceptance.json) |
| Stage 3 验收 | [stage3_acceptance.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/stage3_acceptance.json) |
| Stage 1 正式套件 | [results.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/suite-1795449674214908704/results.json) |
| Stage 2 正式套件 | [results.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/suite-1795451588600425534/results.json) |
| Stage 3 正式套件 | [results.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/results.json) |
| 最终构建清单 | [build_manifest.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/build_manifest.json) |
| 最终源码清单 | [source-final.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/source-final.json) |
| 原 F2 可行性审核 | [04_F2_implementation_feasibility.md](D:/Documents/projects/验证/docs/apb_uart_source_audit_20261123/04_F2_implementation_feasibility.md) |

本次实际完成的复核：

- 对三阶段正式套件的 11+14+15=40 份原始 simulator.log 逐项核对运行结果、UVM severity、FIFO/IRQ/Stage 2 汇总、每运行 result.json、Make 命令退出记录及 VCD/命令文件存在性，未发现不一致。对正常专项逐条统计 RX_PIN_START、RX_PIN_FRAME、RX_COMMIT、RX_POP 的实时日志，均与汇总一致；排除了 UVM 页脚 ID 计数，避免重复算一次事件。
- 以 python -B 只调用现有 VCD audit 函数，重新解析 Stage 1 的 5 份专项、Stage 2 的 TP04/05/06、Stage 3 的正式 TP07，共 9 份关键 VCD。未执行会写 JSON 的脚本主入口。状态、计数、检查结果、SHA256 及适用的 IRQ 跳变字段均与已保存审计一致，全部 PASS。这是既有波形复核，不是新执行 9 次仿真。
- 独立解析原生 coverage.dat / merged.dat 记录，逐 bin 相加最终 10 份输入，得到的全部记录与正式 merged.dat 完全一致。10 份输入 SHA256 全部匹配 inputs.json；52 个语义 bin 和 12 个 cross bin 的累计数与原始日志逐项一致。
- 重新计算 Stage 3 开发前清单内 23,090 份文件的 SHA256，再核对当前 95 份最终源码/文档清单、92 份构建输入和可执行文件指纹。前两阶段历史清单逐路径映射到这份已重新核实的清单，未出现未覆盖路径、缺失历史文件或历史 build 内容变化。
- 读取本机实际 Verilator coverage 导出实现，核实 LCOV 默认命中阈值差异；没有重新运行 coverage 工具。

## 真实完成的功能与自动 Checker

固定条件为 UART0→UART1，UART0/1 pclk 周期 50/86ns，BR=130/75，D9=0、EP=0、TXT=00，合法对齐 APB 地址、全 strobe 写。专项不是通用任意格式 UART 参考模型。

每个 pat/rx_fifo_* 入口均实例化 cRxFifoSequence、设置 scenario；同目录 test_base.txt 指定 cRxFifoTest。生成库实际编入最终构建，factory 只在专项中把 cScoreboard 替换为 cRxFifoScoreboard。旧正常测试继续用原 Scoreboard。

| 测试点 | 实际 Testcase / 已检查行为 | 自动判据与主要实现 |
|---|---|---|
| TP01 | rx_fifo_tp01：初始空读 3 次、有效收读、排空后再空读 3 次、再收读恢复 | 空读 RE=0，读指针/占用/NE 保持；高 24 位读零，空低 8 位不约束；2 次有效数据按序比较 |
| TP02 | rx_fifo_tp02：1/5/16/10/8 五批，共 40 帧；先积累、保持，再部分/全部排空 | 独立有界队列、固定字节序列比较；无拒收、无 OV；读写 5 位指针实际跨 31→0；5 个保持窗口 |
| TP03a | rx_fifo_tp03a：先收 15，再第 16、第 17 帧；此前禁止 DATA 读 | 15 未满、16 满但 OV=0、第 17 拒收且 OV=1；前 16 项未被覆盖、按序全读回 |
| TP03b | rx_fifo_tp03b：相同 17 帧边界，反复读 Raw/Masked，再首读清 OV、补 0xA5、排空 | 状态读不清 OV；DATA 读清 OV；恢复帧被接纳、旧 D1～D15 与 A5 顺序正确；本例总 18 帧 |
| TP04 | rx_fifo_tp04：RXT=00/01/10/11，阈值 16/8/4/2；固定存量 6 项改变 RXT | 各档 T−1/T、下降到 T−1；后三档 T+1；稳定窗口动态 RXT 读回及 RXF/Raw 重计算；全部 39 字节最终读对 |
| TP05 | rx_fifo_tp05：RXT=01/10/11 达水位后继续到物理满 | 水位后分别再接纳 8/12/14 项，三档各保存并读回 16 项；无提前 OV、无按水位丢弃；RXT00 复用 TP03 |
| TP06 | rx_fifo_tp06：RXF、OV、两源三种 Raw 状态下 IE=0/2/4/6 | 每个源状态 IE sweep、完整 IE/Raw/Masked 读回，三源×四档均实际检查；Raw 不随 IE 清除，保留高位读零；含有界安静停用 flush 准备 |
| TP07 | rx_fifo_tp07：RXF 源与 IE 的先后、关 IE、OV 唯一使能源、合并源清除 | UART1 周期 IRQ 预期、14 个必达检查点，触发/保持/撤销；OV 清而 RXF 仍有效时 IRQ 保持，最终 RXF 解除后撤销 |

代码定位：[uvm_comp/cRxFifoTest.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoTest.sv:7)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:149)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:157)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:172)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:189)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:228)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:244)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:276)。

### 独立预期是否成立

数据预期来自源端已完成的 APB TX 写入；固定 BIT_TIME=104800ns 的被动串行解码检查 START 中点、8 个 LSB-first 数据位、STOP 中点及完整 STOP 时间。FIFO 模型用队列占用是否小于 16 决定接纳，未用实际 WE/full/指针/DATA 值生成预期。预期读写指针来自接纳/有效出队计数 mod32。

DUT rx_complete 仍被用作接收提交时刻，属于带内部被动探针的验证。它必须与独立解码 token 配对，落在独立 START 后 9～10 bit 时间窗；每帧同时等待 pin_completed 和 completed，2ms 局部期限，最终计数必须与固定场景相等。缺完成、多完成或缺串行帧均失败。因此不能把此模型称为完全不依赖 DUT 内部事件的黑盒 UART VIP，也没有把“实际 WE=1”直接记为预期接纳成功。

Raw 由模型预测：UART1 不发送使 TXE=1，RXF=(参考占用≥RXT 阈值)，OV 由真实满拒收预测并由 DATA 读清；本批合法 8N1 场景预测 PE/FE=0。Masked 用模型 Raw 与 APB 写维护的 IE 影子相与。实际 Raw、Masked、RXF、OV、IRQ 都是被比较对象。

check_phase 要求 finalized、无在途/残留队列、精确帧数/接纳/拒收/出队/空读/保持数量、非零数据和状态比较、容量边界必达，以及守恒：
完成=接纳+拒收；接纳=有效出队+显式 flush+最终占用。TP04/05/06/07 另有必达计数。这里认可的是刺激与检查同时存在并已实际命中的范围。

实现：[uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv:131)；[uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv:222)；[uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv:250)；[uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv:322)；[uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv:10)。

## 正式回归的实际数量、原始日志及统计口径

最终权威套件为 Stage 3 的 suite-1795453124432259108。下表每行只有一次正向执行，seed 均为 1，actual/acceptance 均为 PASS，Make/sim 退出均为 0/0，UVM_ERROR/FATAL、协议 Checker 错误均为 0。表内帧数和计数来自真实日志；旧测试没有新模型统计，记为不适用。

| 正向测试 | 串行完整帧 / RX提交 | 接纳 / 拒收 | 有效出队 / 数据比较 | flush / 空读 | 状态寄存器比较 | IRQ周期 / 错误 | 耗时秒 |
|---|---:|---:|---:|---:|---:|---:|---:|
| TP07 | 38/38 | 36/2 | 36/36 | 0/0 | 66 | 522966/0 | 46.9 |
| TP01 | 2/2 | 2/0 | 2/2 | 0/6 | 31 | 33933/0 | 3.1 |
| TP02 | 40/40 | 40/0 | 40/40 | 0/0 | 49 | 551357/0 | 45.1 |
| TP03a | 17/17 | 16/1 | 16/16 | 0/0 | 31 | 232907/0 | 19.1 |
| TP03b | 18/18 | 17/1 | 17/17 | 0/0 | 34 | 248628/0 | 20.0 |
| TP04 | 39/39 | 39/0 | 39/39 | 0/0 | 125 | 535721/0 | 44.3 |
| TP05 | 48/48 | 48/0 | 48/48 | 0/0 | 139 | 653297/0 | 51.8 |
| TP06 | 36/36 | 34/2 | 18/18 | 16/1 | 248 | 492739/0 | 37.2 |
| legacy_complete | 不适用 | 不适用 | 24/24（旧SB） | 不适用 | 不适用 | 不适用 | 38.2 |
| observation_smoke | 1/1 | 1/0 | 1/1 | 0/0 | 10 | 18189/0 | 1.8 |

9 个新专项合计 239 个完整串行帧/提交、233 接纳、6 拒收、217 有效出队与数据比较、16 项显式 flush、7 次空读、733 次状态寄存器比较、27 个保持窗口。守恒为 239=233+6、233=217+16。加上旧正常测试的 24 次比较，本次正向共 241 次数据比较；不能把 flush 的 16 项写成已读回比较。有效 IRQ 比较合计 3,289,737 周期，状态沿后采样为 3,289,736 次；TP06 在 EN 过渡沿多一次 IRQ 检查，解释差 1。

这些都是 10 个定向测试的一轮 seed1 结果；不能写“10 轮回归”“25 个不同测试”或“多 seed 随机收敛”。旧 complete 的历史 seed1/2/3 运行属于 Day 0.5，刺激固定，不进入本次 10/10 的次数。

### 最终 10 个正向运行的逐项证据

每个目录还保存 command.json；正式套件的同名 *.command.json 保存 Make 参数、真实退出和耗时。下列日志、VCD、结果、命令均在审核时存在。

| 标签 / 实际测试名 | 原始日志 | VCD | 每运行结果 | 仿真命令 |
|---|---|---|---|---|
| TP07 / test_rx_fifo_tp07 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/command.json) |
| TP01 / test_rx_fifo_tp01 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp01.s1.1795453402367041592.c328b4/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp01.s1.1795453402367041592.c328b4/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp01.s1.1795453402367041592.c328b4/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp01.s1.1795453402367041592.c328b4/command.json) |
| TP02 / test_rx_fifo_tp02 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp02.s1.1795453405982666947.309a18/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp02.s1.1795453405982666947.309a18/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp02.s1.1795453405982666947.309a18/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp02.s1.1795453405982666947.309a18/command.json) |
| TP03a / test_rx_fifo_tp03a | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03a.s1.1795453451566991396.5841f3/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03a.s1.1795453451566991396.5841f3/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03a.s1.1795453451566991396.5841f3/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03a.s1.1795453451566991396.5841f3/command.json) |
| TP03b / test_rx_fifo_tp03b | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03b.s1.1795453471191818770.533d20/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03b.s1.1795453471191818770.533d20/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03b.s1.1795453471191818770.533d20/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp03b.s1.1795453471191818770.533d20/command.json) |
| TP04 / test_rx_fifo_tp04 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp04.s1.1795453491666593073.5abce0/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp04.s1.1795453491666593073.5abce0/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp04.s1.1795453491666593073.5abce0/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp04.s1.1795453491666593073.5abce0/command.json) |
| TP05 / test_rx_fifo_tp05 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp05.s1.1795453536507329813.2c0e53/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp05.s1.1795453536507329813.2c0e53/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp05.s1.1795453536507329813.2c0e53/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp05.s1.1795453536507329813.2c0e53/command.json) |
| TP06 / test_rx_fifo_tp06 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp06.s1.1795453588817541245.36ae8b/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp06.s1.1795453588817541245.36ae8b/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp06.s1.1795453588817541245.36ae8b/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp06.s1.1795453588817541245.36ae8b/command.json) |
| legacy_complete / test_baudrate_9600_complete | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_baudrate_9600_complete.s1.1795453626512527273.f9c6f2/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_baudrate_9600_complete.s1.1795453626512527273.f9c6f2/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_baudrate_9600_complete.s1.1795453626512527273.f9c6f2/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_baudrate_9600_complete.s1.1795453626512527273.f9c6f2/command.json) |
| observation_smoke / test_rx_fifo_observation_smoke | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_observation_smoke.s1.1795453665156994026.a1fa4f/simulator.log) | [VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_observation_smoke.s1.1795453665156994026.a1fa4f/wave.vcd) | [result](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_observation_smoke.s1.1795453665156994026.a1fa4f/result.json) | [command](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_observation_smoke.s1.1795453665156994026.a1fa4f/command.json) |

### 阶段次数与历史结果

| 已保存的正式阶段套件 | 正向实际 PASS | 预期失败的实际 FAIL | 验收条目 |
|---|---:|---:|---:|
| Stage 1 最终 build-04 | 6 | 5 | 11/11 符合预期 |
| Stage 2 最终 build-01 | 9 | 5 | 14/14 符合预期 |
| Stage 3 最终 build-01 | 10 | 5 | 15/15 符合预期 |

合计是 25 次正向执行和 15 次预期失败执行，不是 40 个不同功能用例。Stage 1/2 的 5 类负向为 APB 协议、UART 位宽毛刺、读预期错误、全局超时、缺帧；它们在 Stage 2 重跑过，未冒称 Stage 3 当前二进制又重跑了这五项。

全 pattern 库为 26 项：正式本轮 10 PASS、0 正常 FAIL、1 SKIP、15 NOT_RUN。SKIP 是原有 9Bit8BitDataAnd1OddParityTransferRandomSequencially，因未完成代码编译问题被显式排除。NOT_RUN 完整清单如下，均不计入 PASS 分子或本轮 10 项分母：

| NOT_RUN pattern | 本次状态 |
|---|---|
| 8bit_transfer_all0_all1 | NOT_RUN |
| 8bit_transfer_random_value | NOT_RUN |
| 9Bit8BitDataAnd1OddParityTransferAll0 | NOT_RUN |
| 9Bit8BitDataAnd1OddParityTransferAll1 | NOT_RUN |
| 9Bit8BitDataAnd1OddParityTransferRandomSeparately | NOT_RUN |
| Even_parity_enable-all_0-all | NOT_RUN |
| Even_parity_enable_random_data | NOT_RUN |
| Odd_parity_enable-all_0-all | NOT_RUN |
| Odd_parity_enable_random_data | NOT_RUN |
| baudrate_115200 | NOT_RUN |
| baudrate_9600 | NOT_RUN |
| baudrate_MAX | NOT_RUN |
| baudrate_MIN | NOT_RUN |
| regInitialWriteReadCheck | NOT_RUN |
| trialPat | NOT_RUN |

库存原件：[pattern-inventory.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/pattern-inventory.json)；SKIP 依据：[pat/9Bit8BitDataAnd1OddParityTransferRandomSequencially/SKIP](D:/Documents/projects/验证/UvmEnvUartApb/pat/9Bit8BitDataAnd1OddParityTransferRandomSequencially/SKIP)。

原 baudrate_9600 保留历史 FAIL：24 次 TX 写，16 次数据比较成功，8 项未排空，SB UNFINISH-TX 与 TEST FAILED，Make=2；本次是 NOT_RUN。该结果属于旧测试未完成排空，不能用“已有 16 次比较成功”将整例改成 PASS，也不是本次确认的新 RTL 缺陷。
历史证据：[results.json](D:/Documents/projects/验证/UvmEnvUartApb/build/day05/results.json)、[baudrate_9600.baseline.s1.log](D:/Documents/projects/验证/UvmEnvUartApb/build/day05/logs/baudrate_9600.baseline.s1.log:42)。

审核还清点了阶段目录中的非正式尝试：

| 目录 | run 子目录 | simulator.log 数 | result.json 数 | 正式统计之外的材料 |
|---|---:|---:|---:|---|
| Stage 1 build-03 + build-04 | 17 | 17 | 17 | 早期 6 条目套件含 TP01 真正 FAIL；最终另用 build-04 全跑 |
| Stage 2 build-01 | 15 | 15 | 14 | 早期 TP04 仿真显示 PASS，但结果解析 KeyError，套件 BLOCKED/FAIL，没有 result.json |
| Stage 3 build-01 | 23 | 21 | 20 | 2 个调试结果、被替代套件 3 个结果；另有 1 份中止/截断日志无 result，以及 2 个空 run 目录 |

Stage 3 共 20 份结果为 13 PASS、7 FAIL，其中最终正式才是 10 正向 PASS+5 负向 FAIL。无 result 的截断日志不能补记 PASS，空目录也不代表仿真执行成功。正式 10/10 不排斥历史失败，它的范围由 suite 输入清单决定。
早期套件：[Stage 1](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/suite-1795449040080208050/results.json)、[Stage 2](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/suite-1795450942015144846/results.json)、[Stage 3](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795452951442207390/results.json)；停止说明：[superseded.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795452951442207390/superseded.json)；截断日志：[simulator.log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453081060526199.03d676/simulator.log)。

正常日志并非零 warning：TP07 为 6 个、TP06 为 11 个，其余正式正常项各 2 个。包含 UVM_NO_DPI/UVM_REGEX_NO_DPI 提示及既有 Monitor 对合法 IRQ 的 warning；不影响这里核实的 0 ERROR/FATAL，但简历不能写“零告警”。

## 17 帧、容量与 Overflow 生命周期的交叉核查

三阶段正式日志中 TP03a 始终为 17 完整帧/提交、16 接纳、1 拒收、16 出队；TP03b 始终为 18/17/1、17 出队。TP03b 比 TP03a 多的 1 帧是清 OV、释放一个位置后接收的 0xA5。两例前 17 帧边界相同，不能用 TP03b 的总接纳 17 推出容量是 17。

重新解析 Stage 1 原始 VCD 的沿前值：

| 节点 | 提交时间 ns | 沿前占用 | 实际 WE | 此前有效出队 | 同拍 DATA 读 |
|---|---:|---:|---:|---:|---|
| 第 15 帧 | 17,237,109 | 14 | 1 | 0 | 否 |
| 第 16 帧 | 18,387,445 | 15 | 1 | 0 | 否 |
| 第 17 帧 | 19,544,317 | 16、full=1 | 0 | 0 | 否 |

第 16 帧后 Raw=3（TXE+RXF，OV=0）；第 17 帧拒收后 Raw=7，保持及反复 Raw/Masked 读不清 OV；首个 DATA 读后占用 15、Raw=1（RXT00 下 RXF 也撤销）。TP03a 实际读值为 7,20,33,46,59,72,85,98,111,124,137,150,163,176,189,202，拒收字节 FA 未覆盖这 16 项；TP03b 在剩余旧数据后最后读到 A5。

OV 的完整边界须分开描述：满本身不置 OV，真实满拒收置位，状态读/IE 改写保持，任意 DATA 读请求清除。TP06 还实际观察了空 DATA 读清 OV；本批没有验证同拍满收读时的清除优先级，也没有运行中 reset 清 OV 的验收。

TP06 总 36 帧，接纳 34、拒收 2、实际数据出队 18、显式 flush 16、空读 1。首次 17 帧拒收后，在串行安静窗口写 EN=0 清空 FIFO、OV 保持，再开 EN 得到 Raw=05 的 OV-only 源状态；随后由空读清 OV。第二次满拒收后完整读回 16 项。34=18+16，既没有丢失模型记录，也没有把 flush 计作成功读出。该停用准备动作仅验证现有 RTL 的局部行为，不代表完整停用/恢复规格已经通过。

| 关键轨迹 | 既有波形检查证据 |
|---|---|
| rx-stage1-20261123-232400 TP02 | [审计](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/build-04/runs/test_rx_fifo_tp02.s1.1795449693680569983.b9891b/wave-audit.json)、[原始 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/build-04/runs/test_rx_fifo_tp02.s1.1795449693680569983.b9891b/wave.vcd) |
| rx-stage1-20261123-232400 TP03a | [审计](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/build-04/runs/test_rx_fifo_tp03a.s1.1795449748930831407.aa4846/wave-audit.json)、[原始 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/build-04/runs/test_rx_fifo_tp03a.s1.1795449748930831407.aa4846/wave.vcd) |
| rx-stage1-20261123-232400 TP03b | [审计](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/build-04/runs/test_rx_fifo_tp03b.s1.1795449771238037565.821237/wave-audit.json)、[原始 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/build-04/runs/test_rx_fifo_tp03b.s1.1795449771238037565.821237/wave.vcd) |
| rx-stage2-20261124-001659 TP04 | [审计](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp04.s1.1795451589268128589.05e6f3/stage2-wave-audit.json)、[原始 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp04.s1.1795451589268128589.05e6f3/wave.vcd) |
| rx-stage2-20261124-001659 TP05 | [审计](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp05.s1.1795451648159860382.5ca32a/stage2-wave-audit.json)、[原始 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp05.s1.1795451648159860382.5ca32a/wave.vcd) |
| rx-stage2-20261124-001659 TP06 | [审计](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp06.s1.1795451715187705458.20e350/stage2-wave-audit.json)、[原始 VCD](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/build-01/runs/test_rx_fifo_tp06.s1.1795451715187705458.20e350/wave.vcd) |

Stage 1 与后续日志的状态读比较数有 +1 差异：smoke 9→10、TP01 30→31、TP02 48→49、TP03a 30→31、TP03b 33→34，来自 Stage 2 加入初始 IE 完整读回；帧/准入/读回契约没有变化。Stage 2 报告中“尚未做 TP07/工具 Coverage”和 Stage 3 后续完成它们是阶段时间差，不构成互相矛盾。

## IRQ Checker 的独立性、时序和负向自测

cRxIrqChecker 保存上一安全采样时刻的模型 raw_before/ie_before。每次 check 先算 expected=OR(raw_before & ie_before)，比较实际外部 IRQ，再保存本周期模型状态用于下一沿。Raw 的来源是独立 FIFO/OV/RXT 模型，IE 来自 APB 影子，不读取 DUT Masked 构造预期。

调用点为每个有效 UART1 pclk 上升沿后 2ns；Stage 1 类场景在未使能时不检查，复位期间也跳过。Stage 2 类场景还覆盖相关停用窗口。故“逐周期”指有效观察窗口，并非从 t=0 到结束无条件检查全部周期。

RTL 合并 IRQ 在 pclk 沿采入沿前门控源，#1 后更新。若源或 IE 在 E 沿改变，组合 Masked 在 E+1ns 改变，外部 IRQ 到下一接收沿 E+86ns 后 1ns 才反映，即 E+87ns；Checker 的 E+2ns 采样必须用旧快照。EN=0 的清空在下一沿发生，模型对过渡沿和 flush 后快照作了显式处理。不能把发送端 50ns 时钟用于接收端预期。

正式 TP07：522,966 次比较，0 错误，4 次上升、4 次下降，128,503 个高电平保持采样，去 OV 后 RXF 保持 IRQ 命中 1 次。14 个检查点全部恰好 1 次；38 帧/36 接纳/2 拒收/36 数据比较。VCD 重新核验 4,162,933 个时间组、522,966 个 pclk 周期，8 次实际跳变均落在预测沿后 1ns。

在线 #2ns 比较主要检查周期级行为；VCD 审计另检查已保存波形的时间组和精确 +1ns 跳变。未做任意亚周期毛刺的主动注入。
实现：[uvm_comp/cRxIrqChecker.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxIrqChecker.sv:18)；调用与 flush：[uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv:284)；RTL：[dut/uart_apb_if.v](D:/Documents/projects/验证/UvmEnvUartApb/dut/uart_apb_if.v:154)；波形方法：[scripts/rx_fifo_stage3_wave_audit.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3_wave_audit.py:13)。
正式证据：[稀疏事件轨迹](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/irq-events.csv)、[完整波形核验](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453124999495448.51ae29/stage3-wave-audit.json)、[IRQ 汇总](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/irq-evidence.json)。

### 五种 IRQ 负向模式的实际执行

负向模式只翻转 Checker 局部 observed 一次，不驱动 DUT，不改真实 IRQ 波形。每次 faults=1、errors=1，触发 RX_DUT_IRQ；结束时 RX_ENV_IRQ_COUNTS 仍失败，部分模式还因有效命中数缺额触发 RX_ENV_TP07_TIMING。

| 模式 | 注入周期 / 时间ns | 预期 / DUT实际 / 污染采样 | UVM错误 | 实际结果 | Make / sim | 原始日志 |
|---|---:|---|---:|---|---:|---|
| missing | 26163/2250149 | 1/1/0 | 3 | FAIL（预期） | 2/0 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453172411275086.6117a6/simulator.log) |
| stuck | 29267/2517093 | 0/0/1 | 3 | FAIL（预期） | 2/0 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453220908178535.5e2d06/simulator.log) |
| early | 26162/2250063 | 0/0/1 | 2 | FAIL（预期） | 2/0 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453269092799261.2b03a0/simulator.log) |
| late | 26163/2250149 | 1/1/0 | 3 | FAIL（预期） | 2/0 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453314903128811.144de4/simulator.log) |
| merge | 520375/44752381 | 1/1/0 | 3 | FAIL（预期） | 2/0 | [log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/runs/test_rx_fifo_tp07.s1.1795453359053536345.91131e/simulator.log) |

失败链路为 require_ok → UVM_ERROR → cTest 的 TEST FAILED → uartvip.py 全输出/契约判定 → cmd_run 返回 1 → Make 返回 2。最终套件程序因这些失败符合预期而返回验收 PASS；原始测试结果保持 FAIL。不能要求“负向模拟器也非零”，因为 UVM 以 $finish 结束时模拟器这里确实为 0。

missing 与 late 当前都在同一个上升预期沿把 observed 翻一次，实测注入时间相同；stuck 是单次本应低的采样被污染，并非永久卡高故障。可以称“5 个负向模式/自测”，不能称“五种不同 DUT 波形或 RTL 缺陷已注入检出”。merge 的正负向 DUT VCD 哈希相同，证明的是采样副本自测，不是 DUT 经修改后被成功查错。

脚本按精确的 rises/falls/merge_holds 缺额验收负向，拒绝无关错误。Stage 3 首轮负向分类遗漏派生的命中缺额，曾验收 FAIL，保留在 superseded 套件；最终重跑后全部符合预期。原有 9 项解析回归、Stage 3 基于真实日志的 12 项门禁自测有保存的 PASS 记录；这 21 项软件解析检查不是 21 个新 UART 仿真 Testcase。
相关证据：[negative-checker-evidence.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/negative-checker-evidence.json)、[parser-final.log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/parser-final.log)、[parser-stage3-selftest.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/parser-stage3-selftest.json)；判定代码：[scripts/uartvip.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/uartvip.py:397)、[scripts/uartvip.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/uartvip.py:580)、[scripts/rx_fifo_stage3.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3.py:174)。

## 原生 SV Functional Coverage 的独立审查

### 模型定义与分母

cRxFunctionalCoverage 中 events covergroup 的 semantic coverpoint 接收整数 event_id，定义 event_bin[0..51]，共 52 个值 bin。gating covergroup 定义 raw_sources={2,4,6} 的 3 个 bin、ie={0,2,4,6} 的 4 个 bin，以及 source_by_ie 的 3×4=12 个 cross bin。因此项目模型分母为 52+3+4+12=71。

这是真实编译和采样的 SV covergroup/coverpoint/cross；52 个语义 bin 的采样触发由自定义 hit(id) 调用完成，并非工具自动从需求推导全部 UART 功能。日志 hits[] 与原生采样来自同一事件调用，二者数值一致是采集/持久化核对，不是两套互相独立的功能正确性证明。功能正确性仍由在线模型、读回比较和波形核验支撑。

状态与操作覆盖主要在状态比较成功、cntCompareErr=0 后采样；IRQ 事件在对应 IRQ 比较成功分支采样，IE 改写事件另有采样点。不能泛化为所有 bin 都在同一条统一“全部检查成功”语句后才采样；最终合并又限制为整例 PASS。

| 统计对象 | 命中 / 分母 | 用途 |
|---|---:|---|
| 完整语义列表 | 47/52 | 原生事件 coverpoint，5 个延期 bin 保留零 |
| 冻结范围语义事件 | 47/47 | 自定义阶段内需求命中率；不含那 5 项 |
| Raw 源/IE cross | 12/12 | 原生交叉覆盖 |
| Raw 源与 IE 边缘 bins | 7/7 | 两个 coverpoint 的边缘 bins |
| 项目模型，至少 1 次即命中 | 66/71=92.9577% | 从原生工具记录等权重算 |
| 全部原生 covergroup 记录，至少 1 次 | 67/72 | 另含既有 UART back_2_back 的 1 个 bin，不能混为项目模型 |
| 正式 LCOV 文件默认摘要 | 59/71=83.0986% | 工具默认至少 10 次的 BRH 口径 |

47/47 和 66/71 源自同一批采样，不是两个范围相同的覆盖率。空/非空等状态 bin 会每个周期反复命中；百万级 hits 不能换算为百万条独立测试。只启用 --coverage-user，本次没有代码/分支/翻转覆盖率验收，也没有 Questa UCDB 结果。

SV 定义：[uvm_comp/cRxFunctionalCoverage.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFunctionalCoverage.sv:6)；采样语义：[uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv:38)；ID 名称与分母计算：[scripts/rx_fifo_stage3.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3.py:21)、[scripts/rx_fifo_stage3.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3.py:57)。

### 实际数据文件、合并输入与命中

正式构建含 --coverage-user，C++ 编译日志 VM_COVERAGE=1。10 个正向 run 各保存原生 coverage.dat，5 个负向数据库在 inputs.json 中明确 excluded。正式 merged.dat 为 19,241 bytes，SHA256：

2e57ac3dfdb86a14cfd0329567d813273988011c9412f7bf6dc21af8894fa61b

本次从 10 份原生数据库重算的逐 bin 总和与该文件完全一致；未混入历史构建、调试或负向数据。原 complete 使用旧 SB，不贡献新模型语义命中。merged.dat 包含项目 71 条与旧协议 1 条 covergroup 记录；必须按文件/模型筛选后再给项目数字。

| 正式覆盖证据 | 路径 |
|---|---|
| 原生合并数据库 | [merged.dat](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/merged.dat) |
| 原生 LCOV 导出 | [functional.info](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/functional.info) |
| 机器覆盖报告 | [coverage.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/coverage.json) |
| 逐 bin 人读报告 | [coverage.md](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/coverage.md) |
| 合格/排除输入与指纹 | [inputs.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/inputs.json) |
| 五个未命中 bin | [unhit.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/functional-coverage/unhit.json) |
merge/export 实际命令及退出：[coverage_merge.command.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/coverage_merge.command.json)、[coverage_info.command.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/coverage_info.command.json)，均为 0。

12 个 cross 的实际累计命中如下。这里 source 为 Raw & 6，排除了独立保持为 1 的 TXE；不是完整五源 Raw 的所有组合。

| Raw源 | IE=0 | IE=2 | IE=4 | IE=6 |
|---|---:|---:|---:|---:|
| RXF (2) | 1,077,886 | 3,189 | 194 | 122,098 |
| OV (4) | 2,534 | 70 | 70 | 70 |
| RXF+OV (6) | 13,228 | 70 | 329 | 3,171 |

五个未命中 bin 在源代码中已保留，并非审核时删除：

| ID | 原生 bin / 名称 | 命中 | 未完成范围 |
|---|---|---:|---|
| 47 | event_bin[47] / concurrent_read_receive | 0 | 空/中间/满时同拍接收与 DATA 读的仲裁 |
| 48 | event_bin[48] / reset_recovery | 0 | 运行中复位及后续恢复，含 IRQ/OV 撤销 |
| 49 | event_bin[49] / parity_error | 0 | 真实 PE 注入、队首错误和中断行为 |
| 50 | event_bin[50] / frame_error | 0 | 真实 FE 注入、队首错误和中断行为 |
| 51 | event_bin[51] / reverse_direction | 0 | UART1→UART0 反向专项 |

RXT00 的 T+1=17 超出物理容量，未建立不可达占用 bin；第 17 帧已按拒收测试。这个说明不能用来排除上表那些实际未验证但可实现的功能。

### 59/71 与 66/71 的差异来源

正式 functional.info 明确写 BRF:71、BRH:59；同文件逐条 BRDA 有 71 条，其中 66 条 count>0。读取本机工具源码确认 VlcTop::writeInfo 使用 opt.countOk(point->count()) 累计 BRH，而 VlcOptions 的 m_annotateMin 默认值为 10，countOk 判断 count>=10。正式 coverage_info.command.json 没有传 --annotate-min 1。

因此这不是原生数据库丢了 7 个已命中 bin，也不是 66 的算术造假，而是报告的“阈值 1”与工具默认摘要的“阈值 10”不同。差额全部是以下 7 个低频语义 bin：empty_read=7、full_reject=6、ov_set=6、ov_clear=6、write_pointer_31_to_0=4、read_pointer_31_to_0=4、remove_OV_keep_RXF_IRQ=1。66−7=59，与真实导出完全对应。

简历可写“原生 SV 项目功能模型 66/71 bins 命中，判定阈值 1 次”；不能无说明写“工具默认覆盖率 92.96%”。若引用原 LCOV 默认摘要，应写 59/71；若后续需要生成阈值一致的 LCOV，应在新输出路径显式传 --annotate-min 1。本次未重新导出或改写既有文件。
本机工具源码依据：[VlcOptions.h:40](/home/icverify/ic-verification/axi4lite-uvm-verification/.tools/verilator-src/src/VlcOptions.h:40)、[VlcOptions.h:74](/home/icverify/ic-verification/axi4lite-uvm-verification/.tools/verilator-src/src/VlcOptions.h:74)、[VlcTop.cpp:288](/home/icverify/ic-verification/axi4lite-uvm-verification/.tools/verilator-src/src/VlcTop.cpp:288)（WSL 内路径）；工具来源及编译身份见 [manifest.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/coverage-tool/manifest.json)。

## 实际修改、新增和复用的验证组件

相对 HEAD，当前有 9 份已跟踪文件修改；它们均属于验证环境，没有 DUT 文件。Stage 1/2/3 共新增 34 份项目文件（17+9+8），不含本审核报告；进入本次审核时加上原有 11 份未跟踪文件，共 45 份未跟踪文件。不能把这些未提交文件漏算成“没有实现”。

| 修改的已跟踪文件 | 实际职责变化 |
|---|---|
| [Makefile](D:/Documents/projects/验证/UvmEnvUartApb/Makefile) | BUILD_DIR 与 PLUSARGS，隔离构建/负向参数入口 |
| [scripts/uartvip.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/uartvip.py) | pattern 基类生成、唯一 run、构建/二进制身份、完整错误解析、完成契约、IRQ/覆盖统计和合格数据合并 |
| [sim/testTop.sv](D:/Documents/projects/验证/UvmEnvUartApb/sim/testTop.sv) | 只读内部 RX/IRQ probe 与 config_db；独立 APB/UART Checker 自测线；包含专项验证类 |
| [uvm_comp/ifDut.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/ifDut.sv) | 新增被动 ifRxFifoProbe，观察串行/完成/WE/RE/指针/状态/外部 IRQ |
| [uvm_comp/cScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cScoreboard.sv) | analysis 回调可覆写；残留检查移至 check_phase；保留原正常顺序比较 |
| [uvm_comp/cCommonSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cCommonSequence.sv) | mask 比较用严格不等零判断，使受检未知值走错误路径 |
| [checker/apb_protocol_checker.sv](D:/Documents/projects/验证/UvmEnvUartApb/checker/apb_protocol_checker.sv) | 原 display 协议错误进入 UVM_ERROR |
| [checker/uart_protocol_checker.sv](D:/Documents/projects/验证/UvmEnvUartApb/checker/uart_protocol_checker.sv) | 协议错误进入 UVM；初始化每帧 START 位宽参考，保留后续位宽检查，修正 final 格式 |
| [checker/uart_protocol_checker_top.sv](D:/Documents/projects/验证/UvmEnvUartApb/checker/uart_protocol_checker_top.sv) | uart1 PREADY 修正为本端 pready_1 |

| 新增组件组 | 文件及职责 |
|---|---|
| 新增 SV 类 | [uvm_comp/cRxFifoScoreboard.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoScoreboard.sv)：有限 FIFO、独立 pin 解码、完成配对、顺序/指针/水位/OV/寄存器预期、flush 守恒、必达门禁 |
| 新增 SV 类 | [uvm_comp/cRxFifoSequence.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoSequence.sv)：定向场景、有界逐帧投放、保持、排空、IE/RXT sweep、TP07 检查点 |
| 新增 SV 类 | [uvm_comp/cRxFifoTest.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFifoTest.sv)：仅专项 factory override |
| 新增 SV 类 | [uvm_comp/cRxIrqChecker.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxIrqChecker.sv)：逐接收端周期 IRQ 预期、事件 CSV 和采样副本负向模式 |
| 新增 SV 类 | [uvm_comp/cRxFunctionalCoverage.sv](D:/Documents/projects/验证/UvmEnvUartApb/uvm_comp/cRxFunctionalCoverage.sv)：原生 52 语义 bin、3/4 边缘 bin 和 12 cross bin |
| 9 个 pattern、18 文件 | rx_fifo_observation_smoke 与 rx_fifo_tp01/02/03a/03b/04/05/06/07；各 cVSequence.sv + test_base.txt |
| 8 个 Python 文件 | [scripts/rx_fifo_stage1.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage1.py)、[scripts/rx_fifo_wave_audit.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_wave_audit.py)、[scripts/test_uartvip_results.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/test_uartvip_results.py)、[scripts/rx_fifo_stage2.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage2.py)、[scripts/rx_fifo_stage2_wave_audit.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage2_wave_audit.py)、[scripts/rx_fifo_stage3.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3.py)、[scripts/rx_fifo_stage3_wave_audit.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3_wave_audit.py)、[scripts/rx_fifo_stage3_result_selftest.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/rx_fifo_stage3_result_selftest.py) |
| 3 份阶段文档 | Stage 1/2/3 报告；本最终审核另计 1 份 |

复用两个 APB Agent、Driver、Monitor、Sequencer、Virtual Sequencer、Env 连接、cTest 的 watchdog/objection/结果统计。它们的既有实现不是本次重新开发成果。没有增加 RAL、主动 UART VIP 或新 DUT 功能。

Stage 2 相对开始现场修改 4 份既有验证文件，Stage 3 修改 5 份，其中包括前阶段新建文件，所以不能把 9+4+5 当作 18 份不同的已跟踪文件修改。报告的增量清单与当前差异可对应。

## DUT、历史结果和未跟踪文件的保全

git diff HEAD -- dut 为空。实际参与构建的 5 份 RTL 均在当前构建输入清单中；未参与构建的 wrapper 也保留，不把它当成另一种已验收集成。

独立比对 Git 原始对象时，部分 DUT 文件的 CRLF/LF 规范化造成原始字节不同；归一化后内容一致。更关键的是，与 Stage 1 开发前保存的工作树 SHA256 比较，全部 DUT 文件逐字节不变。因此可以说“本轮未修改 DUT RTL”，不应说“所有工作树字节都与 Git blob 原样一致”。

| 清单基线 | 文件数 | 相对当前缺失 | 相对当前差异解释 |
|---|---:|---:|---|
| Stage 1 preservation-before | 3,681 | 0 | 仅最初 9 份既有验证文件；原 11 份未跟踪文件全部 SHA256 不变，历史 build 无变化 |
| Stage 2 preservation-before | 19,041 | 0 | 到最终现场共 6 份验证文件有累计变化（Stage 2 的 4 份及 Stage 3 的增量并集）；历史 build 无变化 |
| Stage 3 preservation-before | 23,090 | 0 | 仅 uartvip.py、testTop.sv、cRxFifoScoreboard.sv、cRxFifoSequence.sv、ifDut.sv 五份；其余 23,085 份逐字节保持 |
| Stage 3 source-final | 95 | 0 | 当前全部匹配 |
| 最终 build manifest.sources | 92 | 0 | 当前全部匹配，含生成库 |

Stage 3 基线清单总字节数 5,198,394,073，本次重新哈希核对；前两阶段清单的所有路径均能映射到已重新核实的 Stage 3 基线/最终源码清单。Stage 1 最终源码 82 份与当前差异是后续合法增量；Stage 2 最终源码 86 份与当前差异为 Stage 3 的 5 份，不能要求历史源码快照永远等于最终源码。

本次审核开始/结束的全项目文件大小、mtime_ns 清单（排除 .git 和本报告）保持一致；对源码/构建身份/历史基线的内容核实另以 SHA256 为准。暂存区无变化，分支和 HEAD 不变。这里的保全是内容与路径核实，不是证明所有历史 run 都有完整结果；前述早期无 result/空目录本来就存在，已原样保留。

保全证据：[preservation-before.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/preservation-before.json)、[preservation-after.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage1-20261123-232400/preservation-after.json)、[preservation-before.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/preservation-before.json)、[preservation-after.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/preservation-after.json)、[preservation-before.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/preservation-before.json)、[preservation-final.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/preservation-final.json)、[stage1-source-baseline-check.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage2-20261124-001659/stage1-source-baseline-check.json)、[stage2-source-baseline-check.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/stage2-source-baseline-check.json)、[source-final.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/source-final.json)。

## 可复现构建、单测、回归及覆盖率方法

实际已验收平台是 WSL Ubuntu，Verilator 5.052、GCC 13.3.0、Python 3.12.3，UVM Git SHA 78c06547a2a0a29b3dc9dcafae62b75b2ff61544。脚本 source 后使用本机另一项目目录下的 .tools；不具备完全自包含的异机安装包。当前审核所用 Windows Python 仅作数据读取，不把它算作原仿真工具版本。

正式可执行文件大小 31,066,616 bytes，SHA256：
db97d0258d2dc7441b252c61678bea6a024066603ab74d8ede8c37cce899a77c

最终 build_manifest.json SHA256：
46707499b1894174a17fa73233cd10d9a8c85a0fdcb4de3e4ae75f7ae3910521

两者均与当前文件及每运行 build_identity 一致；源文件/生成库/选项/二进制不匹配时 run 拒绝执行。manifest 锁定本地 SV/RTL 编译输入，工具路径和 UVM Git 版本另记 environment；不能宣称记录了整个工具安装的全部字节或任意异机可确定性复现。
实际编译日志：[build_verilator.log](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/logs/build_verilator.log)；工具环境：[environment.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/suite-1795453124432259108/environment.json)；入口：[scripts/env_local.sh](D:/Documents/projects/验证/UvmEnvUartApb/scripts/env_local.sh)、[Makefile](D:/Documents/projects/验证/UvmEnvUartApb/Makefile)、[scripts/uartvip.py](D:/Documents/projects/验证/UvmEnvUartApb/scripts/uartvip.py:327)。

以下是可供后续操作者使用的方法，本次审核没有执行。NEW 必须是未使用的新目录；不要覆盖报告列出的历史目录。

~~~bash
cd /mnt/d/Documents/projects/验证/UvmEnvUartApb
source scripts/env_local.sh

# 一次完整 Stage 3：构建，10 个正向、5 个预期失败自测，合并正式覆盖数据
python3 -B scripts/rx_fifo_stage3.py --root build/rx-stage3-NEW --build-name build-01

# 独立构建与单项运行（另一未用目录）
make build BUILD_DIR=build/rx-single-NEW WAVE=1 COV=1 JOBS=2
make run BUILD_DIR=build/rx-single-NEW WAVE=1 COV=1 TEST=rx_fifo_tp03a SEED=1

# IRQ 采样副本负向；预期 Python run 非零、Make=2
make run BUILD_DIR=build/rx-single-NEW WAVE=1 COV=1 TEST=rx_fifo_tp07 SEED=1 PLUSARGS=IRQ_FAULT=merge

# 通用导出：合并该 BUILD_DIR 内全部合格当前构建 PASS；不自动等同正式套件输入
make cov BUILD_DIR=build/rx-single-NEW WAVE=1 COV=1
~~~

阶段专用入口 rx_fifo_stage1.py、rx_fifo_stage2.py 可各用新 root 构建运行自己的范围；最终项目源码下这些入口不重建历史旧版本，历史阶段源码有 source-final.json/zip 供核对。复用现有 Stage 3 构建可以 --skip-build，但仍要求身份匹配，并新建 suite/run；本次没有这样运行。

正式 Stage 3 的合并方法位于 merge_coverage：筛选本套件正常 PASS、Make=0、sim=0、当前 manifest、存在 coverage.dat，再调用 verilator_coverage --write 与 --write-info。它输出 inputs.json、merged.dat、functional.info、coverage.json/md、unhit.json。一般 make regress TESTS=all 会包含未完成旧 pattern，不等同本次正式 10 项回归。

若后续需要与“至少 1 次”一致的 LCOV 摘要，可对新目录的数据使用：

~~~bash
verilator_coverage --annotate-min 1 --write-info NEW-functional-atleast1.info NEW-merged.dat
~~~

这条阈值一致的导出命令在本次没有执行；现有已验收 .info 仍为默认阈值 10。Stage 3 从现有 Verilator 源码编译过独立 coverage 后端并保存 manifest，向工具目录补了原先不存在的 backend；已有文件未覆盖。异机若缺该后端，需按其 manifest 的实际编译方法准备。

Questa/UCDB、Windows 原生全流程及源码注释覆盖页面未验收。Stage 3 源码注释导出尝试因中文路径编码失败，失败材料保留；原生 .dat、LCOV 数据导出及 JSON/Markdown 成功不能扩大为源码注释页面也成功。通用 make cov 后续成功使用无需重新打开源码的方式。
成功的通用导出日志：[generic-cov-02.console.txt](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/generic-cov-02.console.txt)；该次 13 个输入：[inputs.json](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/build-01/cov/merge-1795481189619722964/inputs.json)；注释导出失败：[generic-cov.console.txt](D:/Documents/projects/验证/UvmEnvUartApb/build/rx-stage3-20261124-004204/generic-cov.console.txt)。

## 尚未完成的范围与审核发现

本次没有发现会推翻最终 10 项正向结果的证据矛盾；但不能给“UART 全功能验证完成”的结论。

| 限制 / 发现 | 对简历或面试表述的影响 |
|---|---|
| 原 F2 包含 reset 撤销/恢复、空/中间/满同拍收读，现阶段都未执行 | TP01～TP07 仅基本冻结范围通过；不能称原 F2 全部扩展闭合 |
| TP07 的 RXF 覆盖先 IE 后源、先源后 IE；OV 唯一使能源组主要覆盖先源后 IE | 不能说 RXF/OV 两源各自所有先后组合均闭合；IE06 合并组有预先使能 OV，但不是孤立 OV 场景的同等替代 |
| 动态 RXT 在 TP04 的 IE=0 窗口验证 | 不能据此称“IE 开启时仅改 RXT 引起 IRQ 的精确时序”已单独验收 |
| 5 个延期 bins 仍未命中；额外需求也未必各有专用 bin | 47/47 与 66/71 只评价当前模型，不能推及完整规格 |
| TP06 的 EN 停用用于造 OV-only，并显式丢弃/flush 16 项 | 不代表运行中任意停用、带在途帧或并发读的恢复全部验证 |
| 单向、固定 8N1、固定时钟/波特率；逐帧等完成后再发 | 未验证反向、全双工、连续最小帧间隔/吞吐极限、系统性速差/相位扫描或随机压力 |
| RXF/OV 两类使能源，TXE/PE/FE IE 关闭 | 未完成五源 IRQ 全组合；没有 PE/FE 正向错误注入和队首元数据检查 |
| 合法 APB 访问为主 | 未验证非法地址/别名、部分 strobe、PSLVERR 完整时序、wait-state 注入等完整 APB 行为 |
| Verilator 运行 | 完整四态 X/Z、Questa 及独立 IRQ 输出宏模式无验收证据；源码严格比较不等于完整四态运行已通过 |
| SV 模型含内部完成/指针被动探针；局部 flush 和 IRQ 延迟按现有 RTL 契约 | 有独立数据/占用预期，但不等同外部产品规格已签署或形式化证明 |
| 默认 LCOV 为 59/71，项目阈值1统计为 66/71 | 92.9577% 必须带阈值和模型范围，不能称工具无条件默认值 |
| 负向 5 模式是采样副本自测，missing/late 相同注入条件 | 不计为新增 DUT bug、5 个不同 RTL 缺陷或五种独立实际故障波形 |
| 历史 FAIL/未完整产出继续保留 | 10/10 仅最终显式清单；不能把全库 26 项、或所有历史运行写成全通过 |

原 F2 和重建 Spec 中的满同拍丢帧但清 OV、停用不清 OV、Parity 极性等疑似设计意图问题，不能因本专题的正常结果就视为修复。本次新增的是验证成果；未确认新的真实 DUT 缺陷。协议 Checker 的误报修复、Python 解析/验收分类修复属于验证基础设施问题，不能包装成修复 UART RTL bug。

对 README 中旧的 pattern 数量、仅旧 Scoreboard 能力或 coverage 说明，应以当前源码和本报告为准。为遵守只读范围，本次没有更新这些旧文档。

## 可安全写入简历的成果

推荐表述（本轮 Stage 1～3 的增量成果）：

> 在既有双 APB Agent 的 UART UVM 环境上完成单向 8N1 RX FIFO 专项验证，建立 16 项有限参考模型、独立串行帧解码和准入/顺序/水位/Overflow 自动检查；实现 TP01～TP07 基本场景，最终 10 个定向测试各执行一次，全部 PASS。

> 实现基于接收端时钟和模型 Raw/IE 快照的逐周期合并 IRQ Checker；TP07 完成 522,966 周期比较，验证 RXF/OV 门控、IRQ 撤销和剩余源保持，并通过 5 个预期失败采样自测验证最终非零退出链路。

> 建立原生 SystemVerilog covergroup/coverpoint/cross 项目功能模型；限定最终 10 个正向 PASS 数据库合并，按至少命中 1 次统计为 66/71 bins（92.9577%），保留 5 个未命中延期 bins。

更短的简历可保留前两条，把 coverage 细节放项目说明。若写覆盖率，至少保留“项目功能模型、66/71、阈值 1”三项限定。

可直接举证的数字：TP02 40 帧且读写指针 31→0；TP03a 17 帧/16 接纳/1 拒收及 16 次顺序比较；TP04 四档水位 16/8/4/2；TP05 三档各 16 项读回，共 48；TP06 三源×四档 IE；TP07 14 个检查点、4 升/4 降、1 次剩余源保持。不要把这些不同层级的计数相加成“覆盖了多少种 UART 功能”。

不应使用的表述：UART 全功能覆盖率 100%、随机回归全部通过、26 个测试全通过、Questa 验收、五源中断全覆盖、完整 reset/并发/全双工验证、发现并修复多个 UART RTL 缺陷、5 个不同 DUT 故障波形均检出、零 warning。

## 面试官可能追问的实现细节

| 追问 | 可据源码与原始证据回答的要点 |
|---|---|
| 怎么证明发了 17 帧，不是只写 17 次 TX DATA？ | 源 APB intent、独立串行 START/数据/完整 STOP、DUT 完成 token 一一配对，逐帧双计数有界等待；17 个实时 RX_PIN_FRAME/RX_COMMIT 和 VCD 边沿可查 |
| 深度 16，为何 TP03b 接纳 17？ | 总计跨两个时间段；首 17 帧接纳 16，读一个释放槽后再接纳 A5，任何时刻占用都未超过 16 |
| 为何空读不比较低 8 位？ | 数组未复位、DATA 直接映射队首位置；空时低字节无定义，检查 RE=0、指针/占用/NE 和高 24 位即可 |
| FIFO 水位和 full 有何区别？ | RXF 阈值 16/8/4/2，物理容量仍 16；TP05 对后三档验证达到水位后继续接纳并读回全部 16 项 |
| 为什么 OV-only 要停用？ | EN=1 满拒收时 RXF 必为 1，DATA 读又清 OV；安静 EN=0 会清 FIFO 而保持 OV，可得到 Raw=05；16 项计入 flush，不能声称全部读回 |
| IRQ 为何用上一周期快照？ | IRQ 寄存器采沿前门控源；APB 回调可能已更改当前模型影子。旧快照保留沿前值，#2ns 避开 RTL #1 更新 |
| 怎么发现缺 IRQ？ | 每周期比较包括预期 1、实际 0，非只监听上升沿；missing 自测触发 RX_DUT_IRQ 和最终 Make=2 |
| 一源解除后怎么证明 IRQ 仍保持？ | IE06、RXT01，真实满拒收后读首项清 OV，占用15≥8，RXF 仍高；在线 merge_holds=1，VCD 精确时序也核对 |
| 为什么模拟器 exit=0 仍算 FAIL？ | UVM $finish 返回 0，run 解析完整错误/契约后返回 1，Make 返回 2；suite 再将预期 FAIL 分类为自测验收通过 |
| 66/71 从哪来，为什么 .info 写59？ | 52 语义+3源+4IE+12cross=71；count>0 有66；默认 LCOV count>=10 有59。7 个低频已命中 bins 恰好解释差额 |
| 47/47 是否也是工具覆盖率？ | 它是同一语义采样的冻结范围命中，完整语义清单47/52；原生模型总66/71。不能将自定义分母当全部 UART 需求 |
| 5 个故障模式是否各不相同？ | 名称5个，都是一次 observed 反转；missing/late 同条件同周期，stuck非永久卡高；证明 Checker/退出链路，未修改 DUT |
| 模型是否照抄了 DUT？ | 数据来自源 intent、串行独立解码，队列容量按参考占用，DUT输出仅比较；完成时刻仍用被动内部事件，并有计数/窗口/超时约束 |
| 复位/同拍收读做了吗？ | 没做；5个延期bin明确保留0，F2扩展不宣称闭合；同拍时不能简单按先pop再push假定准入 |
| 如何防陈旧二进制、覆盖数据混入？ | run核对当前92份构建输入、WAVE/COV与binary SHA；正式merge按suite、PASS、退出、manifest与文件筛选，记录输入SHA；通用cov13输入另列 |
| 实际个人改了什么？ | 复用APB架构，增量写有限SB/序列/专项Test/IRQ Checker/原生coverage及回归审计脚本；9份既有验证文件修改，不把已有Agent或DUT算新增成果 |

本审核交付到此结束。未要求或执行后续功能开发，未 Commit、Push。
