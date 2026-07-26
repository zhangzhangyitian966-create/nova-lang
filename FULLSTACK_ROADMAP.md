# Nova 前后端专项开发路线图

**更新时间**: 2026-07-26
**上次评审**: 第 30 轮
**当前轮次**: 第 32 轮
**下次评审**: 第 33 轮

本路线图由前后端专项开发系统维护，专注于前端类型系统和后端代码生成的核心功能开发。

## 进度概览

| 轨道 | 总数 | 已完成 | 待做 | 废弃 | 完成率 |
|------|------|--------|------|------|--------|
| 前端 | 23 | 22 | 0 | 1 | 95.7% |
| 后端 | 33 | 25 | 6 | 4 | 75.8% |
| **总计** | **56** | **47** | **6** | **5** | **83.9%** |

## 前端开发线

**状态：维护模式（22/23 完成）**

前端核心功能已完成，进入维护模式。持续修复正确性 bug 和提升 DX。

### 历史已完成（22/22）

| 状态 | 任务 | 难度 | 优先级 |
|------|------|------|--------|
| 完成 | 修复赋值可变性检查+未知类型名报错 | easy | 65 |
| 完成 | 精确化列表模式完备性检查 | easy | 50 |
| 完成 | 增强 parser 块内错误恢复粒度 | easy | 35 |
| 完成 | 修复 parser 错误列表只抛出第一个的问题 | easy | 45 |
| 完成 | 增强 parser 错误恢复对 lambda 起始符的支持 | easy | 55 |
| 完成 | 实现列表模式完备性检查 | medium | 65 |
| 完成 | 实现嵌套模式完备性检查 | medium | 60 |
| 完成 | 实现字面量模式冗余检测 | easy | 55 |
| 完成 | 清理 _types_compatible 遗留方法 | easy | 52 |
| 完成 | 修复 for 循环和列表推导的迭代器类型推断 | medium | 72 |
| 完成 | 实现 match guard 条件类型检查 | medium | 72 |
| 完成 | 实现模式匹配完备性检查（基础版） | hard | 86 |
| 完成 | 深化类型合一：全面替换 _types_compatible | hard | 94 |
| 完成 | 增强解析器错误恢复能力 | medium | 60 |
| 完成 | 实现真正的类型合一（unification）算法 | hard | 95 |
| 完成 | 修复 TupleType 兼容检查属性名 bug | easy | 85 |
| 完成 | 修复 ADT 类型参数相等性比较 | easy | 80 |
| 完成 | 修复 ==/!= 比较运算符类型检查 | easy | 75 |
| 完成 | 完善 ? 操作符类型检查 | medium | 78 |
| 完成 | 修复字段访问异常静默吞噬 | easy | 65 |
| 完成 | 修复 Mut 绑定忽略类型注解 bug | easy | 80 |
| 完成 | 实现 Map 字面量解析与类型检查 | medium | 58 |
| ~~废弃~~ | ~~收紧 TypeVar 兼容性判断~~ | medium | 72 |

## 后端开发线

### 高优先级任务（下 2 轮聚焦）

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 | 轮次计划 |
|------|------|------|--------|------|------|----------|
| 待做 | 实现 Wasm 后端闭包 fn_ptr 回填 | hard | **90** | 4-6小时 | wasm_closure_impl | **第 33 轮** |
| 待做 | 修复 C 后端 trampoline double 返回值 UB | easy | **55** | 1-2小时 | - | **第 33 轮** |

### 其他待做任务

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| 待做 | 实现原生后端指令选择优化 | easy | 50 | 2-4小时 | regalloc_fix |
| 待做 | 实现 Wasm 后端栈平衡验证器 | medium | 45 | 1-2天 | - |
| 待做 | 验证 Phi 节点 LIR 降级正确性 | medium | 42 | 3-5小时 | - |
| 待做 | 统一 C 后端（旧路径迁移到 LIR 路径） | hard | 40 | 2-3天 | - |
| ~~废弃~~ | ~~实现 Wasm 多参数闭包调用~~ | medium | 54 | - | 并入 wasm_closure_impl |
| ~~废弃~~ | ~~完善 WasmGC 原生类型定义~~ | hard | 50 | - | 推迟到闭包后评估 |
| ~~废弃~~ | ~~原生后端闭包 fn_ptr 回填（旧方案）~~ | hard | 95 | - | 升级为 trampoline 方案 |

### 历史已完成（25/29）

| 状态 | 任务 | 难度 | 优先级 |
|------|------|------|--------|
| 完成 | 实现闭包后端执行测试（C 后端） | medium | 88 |
| 完成 | 修复 MIR 闭包调用降级为直接调用 bug | easy | 85 |
| 完成 | 实现原生后端闭包 fn_ptr trampoline 方案 | hard | 97 |
| 完成 | 修复原生后端 _emit_call_indirect 浮点返回值处理 | easy | 80 |
| 完成 | 修复 MIR lambda 降级的边界崩溃风险 | easy | 82 |
| 完成 | 实现 LIR 降级 MIRCall SSA callee 为 LIRCallIndirect | medium | 99 |
| 完成 | 实现 C 后端闭包函数指针非 NULL | medium | 68 |
| 完成 | 实现 Wasm 后端完整闭包支持 | hard | 90 |
| 完成 | 实现原生后端闭包创建与间接调用 | hard | 95 |
| 完成 | 修复 MIR lambda 降级——编译 lambda 函数体 | hard | 85 |
| 完成 | 修复原生后端 _emit_runtime_call P0 bug | easy | 99 |
| 完成 | 实现字面量模式冗余检测 | easy | 55 |
| 完成 | Wasm 后端数据结构构建指令完善 | medium | 65 |
| 完成 | 原生后端复合指令迁移到 _emit_runtime_call | medium | 90 |
| 完成 | 修复 nova_map_set/nova_map_put 命名不一致 | easy | 98 |
| 完成 | 为原生后端补全复合数据结构指令代码生成 | hard | 90 |
| 完成 | 实现原生后端 System V AMD64 ABI 调用约定 | hard | 99 |
| 完成 | 实现原生后端完整栈帧管理 | hard | 96 |
| 完成 | 修复原生后端 ELF phnum 不匹配 bug | easy | 95 |
| 完成 | 修复 Phi 降级 MIRMatchJump 后继块计算不全 | medium | 93 |
| 完成 | 修复 Phi 节点降级的边缘块问题 | medium | 86 |
| 完成 | 修复原生后端寄存器分配设计缺陷 | hard | 98 |
| 完成 | 修复原生后端 ELF 入口地址并接入编译管道 | medium | 96 |
| 完成 | 实现原生后端线性扫描寄存器分配器 | hard | 94 |
| 完成 | 实现原生后端函数间调用回填 | medium | 85 |
| 完成 | 实现原生后端两阶段汇编与标签回填 | medium | 92 |
| 完成 | 实现原生后端浮点/字符串常量加载 | medium | 75 |
| 完成 | 修复 Wasm 后端 LIRReturn 返回值处理 bug | medium | 88 |

## 各后端完成度排名

| 排名 | 后端 | 完成度 | 关键缺失 |
|------|------|--------|----------|
| 1 | **C 后端** | **~75%** | trampoline double UB；不区分内外函数；无执行验证 |
| 2 | **原生后端** | **~68%** | 无链接器；无端到端执行测试 |
| 3 | **Wasm 后端** | **~58%** | 闭包 fn_ptr 为 NULL 占位；栈平衡待验证 |
| 4 | **Cranelift 后端** | **<30%** | 仅有框架 |

注：C 后端因闭包 trampoline+fn_ptr 完整排名第 1。原生后端 fn_ptr 已修复（trampoline 方案），闭包可用，完成度从 62% 提升至 ~68%。Wasm 后端 fn_ptr 仍为 NULL。

## 第 30 轮评审发现的 P0/P1/P2 问题

### P0（立即阻塞）

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| ~~P0-1~~ | ~~native_backend _emit_closure_create fn_ptr 传 NULL~~ | ~~闭包无法调用目标函数~~ | **已修复**（第 31 轮，backend_native_fn_ptr_tramp） |
| P0-2 | wasm_backend _compile_closure_create fn_ptr 传 NULL | 闭包无法调用目标函数 | 待修复（backend_wasm_fn_ptr, P90） |
| ~~P0-3~~ | ~~lir_lowering _lower_call 未处理 SSA callee~~ | ~~闭包调用错误编译为直接调用~~ | **已修复**（第 28 轮） |

### P1（高优先级）

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| ~~P1-1~~ | ~~mir_lowering _lower_lambda return_type is None 崩溃~~ | ~~无返回类型注解的 lambda 编译器崩溃~~ | **已修复**（第 29 轮） |
| ~~P1-A~~ | ~~native_backend _emit_call_indirect 浮点返回值未处理~~ | ~~闭包返回浮点值时结果错误~~ | **已修复**（第 31 轮，随 trampoline 方案一并修复） |
| P1-3 | type_checker.py 1756 行大文件病 | 维护成本高 | P2 技术债，暂不拆分 |
| P1-4 | 无后端执行测试 | lambda 经后端编译后无端到端验证 | 待补充（backend_closure_e2e_test, P88） |

### P2（中等优先级）

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| P2-1 | wasm _compile_call_indirect 边界检查不完整 | 参数数组可能越界写入 | 待改进 |
| ~~P2-2~~ | ~~列表模式完备性过于保守（恒为 False）~~ | ~~精确列表模式误报不完备~~ | **已修复**（第 31 轮，frontend_list_pattern_precise） |
| P2-A | C 后端 trampoline double 返回值 (intptr_t) 强转 UB | 浮点闭包返回值精度丢失 | 待修复（backend_c_trampoline_double_fix, P55） |
| P2-B | test_vm_higher_order flaky | 测试间全局状态污染 | 待隔离 |
| ~~P2-3~~ | ~~parser 错误列表只抛出第一个~~ | ~~DX 不佳~~ | **已修复**（第 28 轮） |
| ~~P2-4~~ | ~~parser 块内错误恢复粒度偏粗~~ | ~~同步失败可能丢弃剩余整个块~~ | **已修复**（第 29 轮） |

## 说明

- 前端线：**21/22 完成（含 1 废弃），任务池已空**，进入纯维护模式
- 后端线：下 2 轮聚焦闭包闭环（执行测试 → Wasm fn_ptr）
- 闭包进度：MIR 降级已完成（含鲁棒性修复），LIR 降级 SSA callee 已修复（第 28 轮），三后端中 C 后端最完整（trampoline+fn_ptr），Native 已修复（trampoline 方案，第 31 轮），Wasm fn_ptr 待回填
- P0 修复进度：3 个 P0 中 P0-1/P0-3 已清零，剩余 P0-2（wasm fn_ptr, P90）
- P1 修复进度：P1-1/P1-A 已清零，剩余 P1-4（闭包端到端测试, P88）
- 第 31 轮新增：frontend_list_pattern_precise（前端维护任务）完成，backend_native_fn_ptr_tramp（P97）完成（同时清零 P1-A），backend_native_call_indirect_float（P80）随 trampoline 一并完成
- 第 30 轮评审新增 3 个任务：backend_native_fn_ptr_tramp(P97)、backend_native_call_indirect_float(P80)、backend_c_trampoline_double_fix(P55)
- 每轮开发：1 个前端任务 + 1 个后端任务（前端维护模式时可为轻量增量）
- 每 3 轮一次评审，调整优先级和任务池

## 评审记录

- **第 33 轮评审**（待执行）：第十一次三轮回顾（第 31-33 轮）。
- **第 30 轮评审**（2026-07-26）：第十次三轮回顾（第 28-30 轮）。深度代码审计发现 2 个 P0（native/wasm fn_ptr 仍 NULL）、2 个新 P1（native call_indirect 浮点返回值、闭包后端端到端测试缺失）、2 个新 P2（C trampoline double UB、test_vm_higher_order flaky）。前端评估：质量 86/100（+1），20/21 完成（95.2%），parser DX 显著改善，type_checker 暂不拆分。后端评估：C 75%/Native 62%/Wasm 58%——与上轮持平，P0 fn_ptr 回填未推进（三轮只完成了 LIR callee 降级和 MIR lambda 鲁棒性修复）。综合：投入比前端 0% / 后端 100%。新增 3 个任务（native trampoline P97、call_indirect float P80、C trampoline double P55），调整 2 个优先级。
- **第 27 轮评审**（2026-07-25）：第九次三轮回顾。发现 3 个 P0、4 个 P1、4 个 P2。前端 85/100，后端 C 75%/Native 62%/Wasm 58%。新增 3 个任务，调整多个优先级。
- **第 24 轮评审**（2026-07-25）：第八次三轮回顾。发现 3 个 P0、4 个 P1、3 个 P2。前端 82/100，后端 Native 55%/Wasm 60%/C 70%。新增 4 个任务。
- **第 21 轮评审**（2026-07-25）：第七次三轮回顾。前端线达到 100%。发现 3 个 P0、3 个 P1。新增 6 个任务，废弃 2 个。
- **第 18 轮评审**（2026-07-24）：第六次三轮回顾。发现 P0 nova_map_set/put 命名不一致（已修复）。
- **第 15 轮评审**（2026-07-24）：第五次三轮回顾。发现前端合一算法接入面极窄、后端原生参数传递完全缺失。
- **第 12 轮评审**（2026-07-24）：第四次三轮回顾。发现前端 TupleType 属性名 bug、后端原生寄存器分配有设计级缺陷。
- **第 9 轮评审**（2026-07-23）：第三次三轮回顾。发现原生后端未接入编译管道（P0 bug）。
- **第 6 轮评审**（2026-07-22）：第二次三轮回顾。发现前端 TupleType 属性名 bug、后端原生寄存器分配有设计级缺陷。
- **第 3 轮评审**（2026-07-22）：首次三轮回顾。发现原生后端未接入编译管道（P0 bug）。
