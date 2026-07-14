"""
Nova Pass 管理器

支持在 HIR/MIR/LIR 各层插入优化 Pass。
Pass 管理器负责按序运行各层 Pass，并在达到不动点（无新变化）时停止。
"""

from typing import List, Dict, Set, Tuple, Any
from nova.ir.ir_nodes import (
    IRType, NovaType,
    INT_TYPE, FLOAT_TYPE, BOOL_TYPE,
    HIRModule, HIRFnDecl, HIRLetDecl,
    HIRExpr,
    HIRIntLiteral, HIRFloatLiteral, HIRBoolLiteral, HIRStringLiteral,
    HIRBinaryOp, HIRBlockExpr, HIRCallExpr, HIRIfExpr, HIRUnitLiteral,
    MIRModule,
    LIRModule, LIRFunction,
    LIRInstr, LIRLoadConst, LIRLoadReg, LIRStoreReg,
    LIRBinOp, LIRUnaryOp, LIRJump, LIRLabel, LIRBranch, LIRReturn,
)


class Pass:
    """优化 Pass 基类"""
    name = ""

    def run(self, module) -> bool:
        raise NotImplementedError


class ConstantFolding(Pass):
    """常量折叠

    工作在 HIR 层和 LIR 层。
    - HIR 层：折叠 HIRBinaryOp 中的常量表达式。
    - LIR 层：将两个 LIRLoadConst 操作数参与的 LIRBinOp 替换为
      一条 LIRLoadConst；支持链式折叠（PassManager 会在不动点时
      反复执行）。
    """

    name = "constant_folding"

    # ---- 整数运算表 ----
    _INT_OPS: Dict[str, Any] = {
        "+":  lambda a, b: a + b,
        "-":  lambda a, b: a - b,
        "*":  lambda a, b: a * b,
        "/":  lambda a, b: a // b if b != 0 else None,
        "%":  lambda a, b: a % b  if b != 0 else None,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "<":  lambda a, b: a < b,
        ">":  lambda a, b: a > b,
        "<=": lambda a, b: a <= b,
        ">=": lambda a, b: a >= b,
        "&&": lambda a, b: bool(a) and bool(b),
        "||": lambda a, b: bool(a) or bool(b),
    }

    # ---- 浮点运算表 ----
    _FLOAT_OPS: Dict[str, Any] = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b if b != 0 else None,
    }

    # ---- 运行入口（根据模块类型自动分发） ----

    def run(self, module) -> bool:
        if isinstance(module, LIRModule):
            return self._run_lir(module)
        if isinstance(module, HIRModule):
            return self._run_hir(module)
        if isinstance(module, MIRModule):
            return self._run_mir(module)
        return False

    # ========== HIR 层常量折叠 ==========

    def _run_hir(self, hir_module: HIRModule) -> bool:
        changed = False
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                changed |= self._fold_hir_expr(decl.fn_def.body)
            elif isinstance(decl, HIRLetDecl):
                changed |= self._fold_hir_expr(decl.value)
        return changed

    def _fold_hir_expr(self, expr) -> bool:
        if not isinstance(expr, HIRBinaryOp):
            return False

        changed = False
        if isinstance(expr.left, HIRBinaryOp):
            changed |= self._fold_hir_expr(expr.left)
        if isinstance(expr.right, HIRBinaryOp):
            changed |= self._fold_hir_expr(expr.right)

        # 整数折叠
        if isinstance(expr.left, HIRIntLiteral) and isinstance(expr.right, HIRIntLiteral):
            result = self._safe_eval(self._INT_OPS, expr.op, expr.left.value, expr.right.value)
            if result is not None:
                expr.__class__ = HIRIntLiteral
                expr.value = result
                expr.ir_type = BOOL_TYPE if isinstance(result, bool) else INT_TYPE
                del expr.op; del expr.left; del expr.right
                return True

        # 浮点折叠
        if isinstance(expr.left, HIRFloatLiteral) and isinstance(expr.right, HIRFloatLiteral):
            result = self._safe_eval(self._FLOAT_OPS, expr.op, expr.left.value, expr.right.value)
            if result is not None:
                expr.__class__ = HIRFloatLiteral
                expr.value = result
                expr.ir_type = FLOAT_TYPE
                del expr.op; del expr.left; del expr.right
                return True

        return changed

    # ========== MIR 层常量折叠 ==========

    def _run_mir(self, mir_module: MIRModule) -> bool:
        changed = False
        for fn in mir_module.functions.values():
            changed |= self._fold_mir_function(fn)
        return changed

    def _fold_mir_function(self, fn) -> bool:
        """遍历所有基本块，查找 MIRBinOp(op, MIRConst, MIRConst) 并折叠。"""
        from nova.ir.ir_nodes import (
            MIRConst, MIRBinOp as MIRBinOpNode,
        )
        changed = False
        for bb in fn.basic_blocks:
            ssa_map: Dict[str, Any] = {}  # ssa_name -> (value, const_type, NovaType)
            new_instrs = list(bb.instructions)
            for idx, instr in enumerate(new_instrs):
                if isinstance(instr, MIRConst):
                    ssa_map[instr.result_name] = (instr.value, instr.const_type, instr.result_type)
                if isinstance(instr, MIRBinOpNode):
                    left_val = ssa_map.get(instr.left)
                    right_val = ssa_map.get(instr.right)
                    if left_val and right_val:
                        lv, lt, lty = left_val
                        rv, rt, rty = right_val
                        if lt == "int" and rt == "int":
                            result = self._safe_eval(self._INT_OPS, instr.op, lv, rv)
                            if result is not None:
                                new_instr = MIRConst(instr.result_type)
                                new_instr.value = result
                                new_instr.const_type = "bool" if isinstance(result, bool) else "int"
                                new_instr.result_name = instr.result_name
                                new_instrs[idx] = new_instr
                                ssa_map[instr.result_name] = (new_instr.value, new_instr.const_type, instr.result_type)
                                changed = True
                                continue
                        elif lt == "float" and rt == "float":
                            result = self._safe_eval(self._FLOAT_OPS, instr.op, lv, rv)
                            if result is not None:
                                new_instr = MIRConst(instr.result_type)
                                new_instr.value = result
                                new_instr.const_type = "float"
                                new_instr.result_name = instr.result_name
                                new_instrs[idx] = new_instr
                                ssa_map[instr.result_name] = (new_instr.value, new_instr.const_type, instr.result_type)
                                changed = True
                                continue
            bb.instructions = new_instrs
        return changed

    # ========== LIR 层常量折叠 ==========

    def _run_lir(self, lir_module: LIRModule) -> bool:
        changed = False
        for fn in lir_module.functions.values():
            changed |= self._fold_lir_function(fn)
        return changed

    def _fold_lir_function(self, fn: LIRFunction) -> bool:
        """遍历 LIR 指令序列，将两个 LIRLoadConst 操作数的 LIRBinOp
        替换为一条 LIRLoadConst。支持链式折叠。"""
        changed = False
        # 构建寄存器 -> LIRLoadConst 值的映射
        const_map: Dict[str, Tuple[Any, str]] = {}  # reg -> (value, const_type)

        new_body: List[LIRInstr] = []
        for instr in fn.body:
            if isinstance(instr, LIRLoadConst) and instr.dst_loc:
                reg = instr.dst_loc[0]
                const_map[reg] = (instr.value, instr.const_type)
                new_body.append(instr)
                continue

            if isinstance(instr, LIRBinOp) and instr.op:
                # 获取两个操作数的值
                left_val = None
                left_type = None
                if len(instr.src_locs) >= 1:
                    left_reg = instr.src_locs[0][0]
                    if left_reg in const_map:
                        left_val, left_type = const_map[left_reg]
                right_val = None
                right_type = None
                if len(instr.src_locs) >= 2:
                    right_reg = instr.src_locs[1][0]
                    if right_reg in const_map:
                        right_val, right_type = const_map[right_reg]

                if left_val is not None and right_val is not None:
                    result = self._try_fold(instr.op, left_val, left_type,
                                            right_val, right_type)
                    if result is not None:
                        folded_val, folded_type = result
                        replacement = LIRLoadConst()
                        replacement.value = folded_val
                        replacement.const_type = folded_type
                        replacement.dst_loc = instr.dst_loc
                        new_body.append(replacement)
                        # 更新 const_map 以支持链式折叠
                        if instr.dst_loc:
                            const_map[instr.dst_loc[0]] = (folded_val, folded_type)
                        changed = True
                        continue

            new_body.append(instr)

        fn.body = new_body
        return changed

    # ---- 折叠辅助 ----

    @staticmethod
    def _safe_eval(ops_table: dict, op: str, left, right):
        fn = ops_table.get(op)
        if fn is None:
            return None
        try:
            return fn(left, right)
        except (ZeroDivisionError, OverflowError, ValueError):
            return None

    def _try_fold(self, op: str, left_val, left_type, right_val, right_type):
        if left_type == "int" and right_type == "int":
            result = self._safe_eval(self._INT_OPS, op, left_val, right_val)
            if result is not None:
                return (result, "bool" if isinstance(result, bool) else "int")
        elif left_type == "float" and right_type == "float":
            result = self._safe_eval(self._FLOAT_OPS, op, left_val, right_val)
            if result is not None:
                return (result, "float")
        return None


class Inlining(Pass):
    """函数内联"""
    name = "inlining"

    def run(self, hir_module):
        return False


class DeadCodeElimination(Pass):
    """死代码消除

    工作在 LIR 层（同时保持对 HIR/MIR 的兼容）。

    LIR 层策略：
    1. 收集所有「被使用」的寄存器（从 src_locs、跳转目标、调用参数中提取）。
    2. 标记 LIRLoadConst / LIRLoadReg / LIRUnaryOp 为无副作用的指令，
       若其 dst_loc 不在 used 集合中则删除。
    3. 移除无条件跳转 (LIRJump) 之后的不可达代码。
    4. 重复上述过程直到无变化（不动点）。
    """

    name = "dead_code_elimination"

    # 有副作用的指令类型（不会作为死代码被删除）
    _SIDE_EFFECT_TYPES = (
        LIRJump, LIRBranch, LIRReturn, LIRLabel,
        # LIRCall, LIRStoreGlobal, LIRPanic 等也是副作用指令
    )

    def run(self, module) -> bool:
        if isinstance(module, LIRModule):
            return self._run_lir(module)
        if isinstance(module, HIRModule):
            return False
        if isinstance(module, MIRModule):
            return False
        return False

    def _run_lir(self, lir_module: LIRModule) -> bool:
        changed = False
        for fn in lir_module.functions.values():
            changed |= self._eliminate_lir_fn(fn)
        return changed

    def _eliminate_lir_fn(self, fn: LIRFunction) -> bool:
        total_changed = False
        # 反复运行直到不动点
        while True:
            changed = self._one_round_dce(fn)
            if not changed:
                break
            total_changed = True
        return total_changed

    def _one_round_dce(self, fn: LIRFunction) -> bool:
        """执行一轮 DCE，返回是否有变化。"""
        from nova.ir.ir_nodes import (
            LIRCall, LIRStoreGlobal, LIRCallIndirect,
            LIRPanic, LIRBuildList, LIRBuildTuple, LIRBuildADT,
            LIRIndex, LIRFieldAccess, LIRLoadGlobal, LIRStoreReg,
        )

        body = fn.body

        # 1. 收集所有被使用的寄存器
        used: Set[str] = set()

        for instr in body:
            # 所有 src_locs 中的寄存器都是被使用的
            for reg, _ in instr.src_locs:
                if reg:
                    used.add(reg)

            # 特殊指令中引用的寄存器
            if isinstance(instr, LIRBranch) and instr.cond_reg:
                used.add(instr.cond_reg)

        # 2. 标记无条件跳转后的不可达指令
        unreachable_indices: Set[int] = set()
        for i, instr in enumerate(body):
            if isinstance(instr, LIRJump):
                for j in range(i + 1, len(body)):
                    # 跳转后只允许遇到 LIRLabel（作为其他代码的入口标记）
                    if isinstance(body[j], LIRLabel):
                        break
                    unreachable_indices.add(j)

        # 3. 判断哪些无副作用指令是死代码
        # 无副作用的指令类型
        side_effect_free_types = (LIRLoadConst, LIRLoadReg, LIRUnaryOp)

        new_body: List[LIRInstr] = []
        changed = False

        for i, instr in enumerate(body):
            # 不可达代码直接删除
            if i in unreachable_indices:
                changed = True
                continue

            # 有副作用的指令保留
            if not isinstance(instr, side_effect_free_types):
                new_body.append(instr)
                continue

            # 无副作用指令：检查 dst_loc 是否被使用
            if instr.dst_loc is not None:
                dst_reg = instr.dst_loc[0]
                if dst_reg in used:
                    new_body.append(instr)
                    continue

            # dst_loc 不被使用，或者没有 dst_loc 的无副作用指令 -> 删除
            changed = True

        if changed:
            fn.body = new_body
        return changed


class CommonSubexprElimination(Pass):
    """公共子表达式消除

    工作在 LIR 层和 MIR 层。

    LIR 层策略：
    - 以 (op, src_reg_1, src_reg_2) 作为表达式签名。
    - 如果同一表达式被计算两次，第二次用 LIRLoadReg 替代 LIRBinOp/LIRUnaryOp，
      直接复用第一次的结果寄存器。

    MIR 层策略：
    - 以 (op, left_ssa, right_ssa) 作为表达式签名，在基本块内消除重复计算。
    """

    name = "cse"

    def run(self, module) -> bool:
        if isinstance(module, LIRModule):
            return self._run_lir(module)
        if isinstance(module, MIRModule):
            return self._run_mir(module)
        return False

    # ========== LIR 层 CSE ==========

    def _run_lir(self, lir_module: LIRModule) -> bool:
        changed = False
        for fn in lir_module.functions.values():
            changed |= self._cse_lir_fn(fn)
        return changed

    def _cse_lir_fn(self, fn: LIRFunction) -> bool:
        changed = False
        # 表达式签名 -> 第一次计算结果的 dst_loc
        expr_map: Dict[Tuple, Tuple[str, NovaType]] = {}

        new_body: List[LIRInstr] = []
        for instr in fn.body:
            # 遇到标签时重置 expr_map（不同基本块之间不做 CSE）
            if isinstance(instr, LIRLabel):
                expr_map.clear()
                new_body.append(instr)
                continue

            sig = self._lir_expr_signature(instr)
            if sig is not None:
                if sig in expr_map:
                    # 找到相同的表达式，用 LIRLoadReg 替代
                    first_reg, first_type = expr_map[sig]
                    replacement = LIRLoadReg()
                    replacement.src_locs = [(first_reg, first_type)]
                    replacement.dst_loc = instr.dst_loc
                    new_body.append(replacement)
                    changed = True
                    continue
                else:
                    # 首次出现，记录
                    if instr.dst_loc:
                        expr_map[sig] = instr.dst_loc

            new_body.append(instr)

        fn.body = new_body
        return changed

    @staticmethod
    def _lir_expr_signature(instr: LIRInstr):
        """为 LIR 指令生成表达式签名。"""
        if isinstance(instr, LIRBinOp) and instr.op:
            left = instr.src_locs[0][0] if len(instr.src_locs) >= 1 else ""
            right = instr.src_locs[1][0] if len(instr.src_locs) >= 2 else ""
            return ("binop", instr.op, left, right)

        if isinstance(instr, LIRUnaryOp) and instr.op:
            operand = instr.src_locs[0][0] if instr.src_locs else ""
            return ("unaryop", instr.op, operand)

        return None

    # ========== MIR 层 CSE ==========

    def _run_mir(self, mir_module: MIRModule) -> bool:
        from nova.ir.ir_nodes import (
            MIRBinOp as MIRBinOpNode, MIRUnaryOp as MIRUnaryOpNode,
        )
        changed = False
        for fn in mir_module.functions.values():
            for bb in fn.basic_blocks:
                expr_map: Dict[Tuple, str] = {}  # sig -> result ssa
                new_instrs = list(bb.instructions)
                for idx, instr in enumerate(new_instrs):
                    sig = None
                    if isinstance(instr, MIRBinOpNode):
                        sig = ("binop", instr.op, instr.left, instr.right)
                    elif isinstance(instr, MIRUnaryOpNode):
                        sig = ("unaryop", instr.op, instr.operand)

                    if sig is not None and sig in expr_map:
                        # 用一条 MIRLoad（从已有结果复制）替代
                        from nova.ir.ir_nodes import MIRLoad
                        repl = MIRLoad(instr.result_type)
                        repl.name = expr_map[sig]
                        repl.result_name = instr.result_name
                        new_instrs[idx] = repl
                        changed = True
                    elif sig is not None:
                        expr_map[sig] = instr.result_name
                bb.instructions = new_instrs
        return changed


class LoopInvariantCodeMotion(Pass):
    """循环不变量外提

    工作在 LIR 层和 MIR 层。

    LIR 层策略：
    1. 通过识别 back-edge（跳回前一个 LIRLabel 的 LIRJump）来定位循环。
       一个循环定义为 (header_label, back_edge_start) 区间。
    2. 收集循环内部定义和修改的寄存器集合。
    3. 查找循环体内无副作用的指令（LIRLoadConst / LIRLoadReg / LIRBinOp / LIRUnaryOp），
       若其所有操作数寄存器都不在循环内定义/修改，则可外提到 header 之前。

    MIR 层策略：
    1. 通过回边 (branch/jump -> header) 识别循环。
    2. 收集循环内定义的 SSA 名。
    3. 将不依赖循环内定义值的纯计算指令外提到循环头基本块之前。
    """

    name = "licm"

    def run(self, module) -> bool:
        if isinstance(module, LIRModule):
            return self._run_lir(module)
        if isinstance(module, MIRModule):
            return self._run_mir(module)
        return False

    # ========== LIR 层 LICM ==========

    def _run_lir(self, lir_module: LIRModule) -> bool:
        changed = False
        for fn in lir_module.functions.values():
            changed |= self._licm_lir_fn(fn)
        return changed

    def _licm_lir_fn(self, fn: LIRFunction) -> bool:
        body = fn.body

        # 1. 建立标签 -> 索引 的映射
        label_indices: Dict[str, int] = {}
        for i, instr in enumerate(body):
            if isinstance(instr, LIRLabel):
                label_indices[instr.name] = i

        # 2. 识别 back-edges，构建循环集合
        # back-edge: LIRJump 的 target 指向某个在它之前出现的标签
        loops: List[Tuple[str, int]] = []  # (header_label, header_index)
        for i, instr in enumerate(body):
            if isinstance(instr, LIRJump) and instr.target:
                if instr.target in label_indices:
                    header_idx = label_indices[instr.target]
                    if header_idx < i:
                        loops.append((instr.target, header_idx))

        if not loops:
            return False

        # 3. 对每个循环执行 LICM
        changed = False
        for header_label, header_idx in loops:
            # 找到 back-edge 指令的索引
            back_edge_end = len(body) - 1
            for i in range(len(body) - 1, header_idx, -1):
                if isinstance(body[i], LIRJump) and body[i].target == header_label:
                    back_edge_end = i
                    break

            # 循环体：[header_idx+1, back_edge_end]（不包含 header 标签本身）
            loop_start = header_idx + 1
            loop_end = back_edge_end  # inclusive

            if loop_start >= loop_end:
                continue

            # 3a. 收集循环内定义/修改的寄存器
            loop_defined: Set[str] = set()
            for i in range(loop_start, loop_end + 1):
                instr = body[i]
                if instr.dst_loc:
                    loop_defined.add(instr.dst_loc[0])
                if isinstance(instr, LIRStoreReg) and instr.dst_loc:
                    loop_defined.add(instr.dst_loc[0])

            # 3b. 找出可外提的指令
            # 可外提的条件：无副作用，且所有操作数不在 loop_defined 中
            side_effect_free = (LIRLoadConst, LIRLoadReg, LIRBinOp, LIRUnaryOp)
            to_hoist: List[int] = []  # 指令索引

            for i in range(loop_start, loop_end + 1):
                instr = body[i]
                if not isinstance(instr, side_effect_free):
                    continue
                if instr.dst_loc is None:
                    continue
                # 检查操作数
                all_ops_outside = True
                for reg, _ in instr.src_locs:
                    if reg in loop_defined:
                        all_ops_outside = False
                        break
                if isinstance(instr, LIRBranch) and instr.cond_reg in loop_defined:
                    all_ops_outside = False
                if all_ops_outside:
                    to_hoist.append(i)

            if not to_hoist:
                continue

            # 3c. 外提：把指令移到 header 标签之后（但在循环体第一条有效指令之前）
            # 收集要外提的指令
            hoisted_instrs = [body[i] for i in to_hoist]

            # 从循环体中删除这些指令（从后往前删以保持索引正确）
            for i in reversed(to_hoist):
                del body[i]

            # 插入到 header 标签之后
            insert_pos = header_idx + 1
            for h_instr in hoisted_instrs:
                body.insert(insert_pos, h_instr)
                insert_pos += 1

            changed = True

        return changed

    # ========== MIR 层 LICM ==========

    def _run_mir(self, mir_module: MIRModule) -> bool:
        from nova.ir.ir_nodes import (
            MIRConst, MIRLoad, MIRBinOp as MIRBinOpNode,
            MIRUnaryOp as MIRUnaryOpNode,
            MIRJump as MIRJumpNode, MIRBranch as MIRBranchNode,
        )
        changed = False
        for fn in mir_module.functions.values():
            # 建立标签 -> 基本块 的映射
            bb_map: Dict[str, Any] = {}
            for bb in fn.basic_blocks:
                bb_map[bb.label] = bb

            # 识别回边
            back_edges: List[Tuple[str, str]] = []  # (from_label, header_label)
            for bb in fn.basic_blocks:
                if isinstance(bb.terminator, MIRJumpNode):
                    target = bb.terminator.target
                    if target in bb_map and target != bb.label:
                        # 检查是否是回边（header 在 bb 之前或同一循环内）
                        back_edges.append((bb.label, target))
                elif isinstance(bb.terminator, MIRBranchNode):
                    for tgt in [bb.terminator.true_target, bb.terminator.false_target]:
                        if tgt in bb_map and tgt != bb.label:
                            # 只将 true_target 视为可能的回边（简化）
                            pass

            if not back_edges:
                continue

            # 对每个回边对应的循环执行 LICM
            for _, header_label in back_edges:
                if header_label not in bb_map:
                    continue
                header_bb = bb_map[header_label]

                # 收集循环内定义的 SSA 名（简化：只看 header 块）
                loop_defined: Set[str] = set()
                for instr in header_bb.instructions:
                    if instr.result_name:
                        loop_defined.add(instr.result_name)

                # 找出可外提的指令
                hoistable = []
                remaining = []
                for instr in header_bb.instructions:
                    can_hoist = False
                    if isinstance(instr, (MIRConst, MIRLoad)):
                        # 纯加载
                        deps = set()
                        if isinstance(instr, MIRLoad):
                            pass  # MIRLoad 不依赖 SSA 寄存器
                        if not (deps & loop_defined):
                            can_hoist = True
                    elif isinstance(instr, MIRBinOpNode):
                        if instr.left not in loop_defined and instr.right not in loop_defined:
                            can_hoist = True
                    elif isinstance(instr, MIRUnaryOpNode):
                        if instr.operand not in loop_defined:
                            can_hoist = True

                    if can_hoist:
                        hoistable.append(instr)
                    else:
                        remaining.append(instr)

                if hoistable:
                    # 找到 header 块的前驱，将指令插入到前驱末尾
                    # 简化处理：如果前驱是 entry block，就放在 entry 末尾
                    for bb in fn.basic_blocks:
                        if bb.terminator and isinstance(bb.terminator, MIRJumpNode):
                            if bb.terminator.target == header_label:
                                bb.instructions.extend(hoistable)
                                header_bb.instructions = remaining
                                changed = True
                                break

        return changed


class PassManager:
    """优化 Pass 管理器"""

    def __init__(self):
        self.hir_passes = []
        self.mir_passes = []
        self.lir_passes = []
        self._verbose = False

    def add_hir_pass(self, pass_):
        self.hir_passes.append(pass_)

    def add_mir_pass(self, pass_):
        self.mir_passes.append(pass_)

    def add_lir_pass(self, pass_):
        self.lir_passes.append(pass_)

    def run_hir_passes(self, hir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.hir_passes:
                try:
                    changed |= pass_.run(hir_module)
                except Exception:
                    pass
            if not changed:
                break
            total_changed = True
        return total_changed

    def run_mir_passes(self, mir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.mir_passes:
                try:
                    changed |= pass_.run(mir_module)
                except Exception:
                    pass
            if not changed:
                break
            total_changed = True
        return total_changed

    def run_lir_passes(self, lir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.lir_passes:
                try:
                    changed |= pass_.run(lir_module)
                except Exception:
                    pass
            if not changed:
                break
            total_changed = True
        return total_changed


def default_optimization_pipeline():
    """创建默认的优化 Pass 管道

    HIR 层：常量折叠、内联
    MIR 层：CSE、LICM、常量折叠
    LIR 层：常量折叠、DCE、CSE、LICM
    """
    pm = PassManager()
    # HIR 层
    pm.add_hir_pass(ConstantFolding())
    pm.add_hir_pass(Inlining())
    # MIR 层
    pm.add_mir_pass(ConstantFolding())
    pm.add_mir_pass(CommonSubexprElimination())
    pm.add_mir_pass(LoopInvariantCodeMotion())
    # LIR 层
    pm.add_lir_pass(ConstantFolding())
    pm.add_lir_pass(DeadCodeElimination())
    pm.add_lir_pass(CommonSubexprElimination())
    pm.add_lir_pass(LoopInvariantCodeMotion())
    return pm
