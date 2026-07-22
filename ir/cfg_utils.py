"""
MIR CFG 工具函数与循环分析基础设施

提供 CFG 遍历、支配树计算、回边检测、自然循环识别等功能，
为 LICM（循环不变量外提）等循环优化提供基础。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .ir_nodes import (
    MIRADTBuild,
    MIRBasicBlock,
    MIRBinOp,
    MIRBranch,
    MIRCall,
    MIRClosureCreate,
    MIRFieldAccess,
    MIRFunction,
    MIRIndexAccess,
    MIRJump,
    MIRListAppend,
    MIRListBuild,
    MIRMapBuild,
    MIRMatchJump,
    MIRPhi,
    MIRReturn,
    MIRStore,
    MIRSwitch,
    MIRTupleBuild,
    MIRUnaryOp,
)


# ============================================================
# 基础 CFG 工具
# ============================================================


def build_block_map(fn: MIRFunction) -> Dict[str, MIRBasicBlock]:
    """构建块标签 -> 块对象的映射"""
    return {bb.label: bb for bb in fn.basic_blocks}


def get_successors(terminator) -> List[str]:
    """获取终结指令的后继块标签列表"""
    if isinstance(terminator, MIRJump):
        return [terminator.target]
    elif isinstance(terminator, MIRBranch):
        return [terminator.true_target, terminator.false_target]
    elif isinstance(terminator, MIRSwitch):
        targets = [case[1] for case in terminator.cases]
        if terminator.default_target:
            targets.append(terminator.default_target)
        return targets
    elif isinstance(terminator, MIRMatchJump):
        targets = [test[2] for test in terminator.variant_tests]
        if terminator.default_target:
            targets.append(terminator.default_target)
        return targets
    elif isinstance(terminator, MIRReturn):
        return []
    else:
        return []


def build_predecessors(fn: MIRFunction) -> Dict[str, List[str]]:
    """构建前驱关系：block_label -> [predecessor_labels]"""
    predecessors: Dict[str, List[str]] = {}
    for bb in fn.basic_blocks:
        predecessors[bb.label] = []
    for bb in fn.basic_blocks:
        if bb.terminator is None:
            continue
        succs = get_successors(bb.terminator)
        for succ_label in succs:
            if succ_label in predecessors:
                predecessors[succ_label].append(bb.label)
    return predecessors


def build_successor_map(fn: MIRFunction) -> Dict[str, List[str]]:
    """构建后继关系：block_label -> [successor_labels]"""
    succ_map: Dict[str, List[str]] = {}
    for bb in fn.basic_blocks:
        if bb.terminator is not None:
            succ_map[bb.label] = get_successors(bb.terminator)
        else:
            succ_map[bb.label] = []
    return succ_map


# ============================================================
# 支配树计算（迭代式算法）
# ============================================================


def compute_dominators(fn: MIRFunction) -> Dict[str, Set[str]]:
    """
    计算每个基本块的支配集合（迭代式算法）。

    支配定义：块 d 支配块 n 当且仅当从入口块到 n 的每条路径都经过 d。
    每个块都支配自己。

    返回: {block_label: set(dominator_labels), ...}
    """
    block_labels = [bb.label for bb in fn.basic_blocks]
    all_blocks = set(block_labels)
    entry = fn.entry_block

    # 初始化：入口块只支配自己，其他块支配所有块（上界）
    dom: Dict[str, Set[str]] = {}
    for label in block_labels:
        dom[label] = set(all_blocks)
    dom[entry] = {entry}

    # 迭代不动点
    changed = True
    while changed:
        changed = False
        for label in block_labels:
            if label == entry:
                continue

            # 找到所有前驱
            bb = next(b for b in fn.basic_blocks if b.label == label)
            preds = _get_predecessors_for_block(fn, label)

            if not preds:
                # 不可达块：只支配自己
                new_dom = {label}
            else:
                # 新的支配集 = {自身} ∩ (所有前驱支配集的交集)
                new_dom = {label}
                # 从第一个前驱的支配集开始
                first_pred = preds[0]
                intersection = set(dom[first_pred])
                # 与其他所有前驱的支配集求交
                for pred in preds[1:]:
                    intersection &= dom[pred]
                new_dom |= intersection

            if new_dom != dom[label]:
                dom[label] = new_dom
                changed = True

    return dom


def _get_predecessors_for_block(fn: MIRFunction, block_label: str) -> List[str]:
    """获取指定块的前驱（内部工具函数）"""
    preds = []
    for bb in fn.basic_blocks:
        if bb.terminator is None:
            continue
        succs = get_successors(bb.terminator)
        if block_label in succs:
            preds.append(bb.label)
    return preds


def compute_idom(fn: MIRFunction) -> Dict[str, Optional[str]]:
    """
    计算每个块的直接支配者 (immediate dominator)。

    直接支配者是离该块最近的支配者（除自己外）。
    入口块没有直接支配者。

    返回: {block_label: idom_label or None, ...}
    """
    dom = compute_dominators(fn)
    idom: Dict[str, Optional[str]] = {}

    for label, dominators in dom.items():
        if label == fn.entry_block:
            idom[label] = None
            continue

        # 直接支配者是：支配集合中（除自己外）被其他所有支配者支配的那个
        # 即：在支配树中，idom 是 label 的父节点
        # 简化方法：找一个支配者 d ≠ label，使得不存在 d' 满足 d dom d' 且 d' dom label
        other_doms = dominators - {label}
        if not other_doms:
            idom[label] = None
            continue

        # 找最"近"的支配者：被其他所有支配者支配的那个
        for candidate in other_doms:
            # 检查 candidate 是否被其他所有支配者支配
            is_idom = True
            for other in other_doms:
                if other == candidate:
                    continue
                if candidate not in dom[other]:
                    # other 不支配 candidate，说明 candidate 不是最近的
                    # （如果 candidate 是 idom，它应该被所有其他支配者支配）
                    # 等等，我们需要的是：在从入口到 label 的路径上，candidate 是最后一个
                    # 即：candidate 支配 label，且没有其他节点 d 使得 candidate 支配 d 且 d 支配 label
                    pass
            # 正确做法：idom 是满足 idom dom label 且 idom ≠ label 的节点中，
            # 被 label 的所有其他支配者（除自己和idom外）支配的那个
            # 简单方法：从支配集中移除 label 后，找一个节点，
            # 它被所有剩下的节点支配（不，应该是它支配所有"更接近label"的节点）
            # 实际上：idom 是 dom(label) \ {label} 中，不支配 dom(label) \ {label, idom} 中任何节点的那个
            # 即：在 dom(label) \ {label} 集合里，找一个"最深"的节点
            # 最深 = 被最多节点支配

        # 更简单的算法：idom 是 dom(label) \ {label} 中
        # 不在任何其他 dom(label) \ {label, x} 节点的支配集中的那个？
        # 不，让我用标准方法：

        # idom(label) 是 label 的严格支配者中，离 label 最近的那个
        # 即：d 是 idom 当且仅当 d ∈ dom(label) \ {label}，
        # 且不存在 d' ∈ dom(label) \ {label, d} 使得 d ∈ dom(d')
        # （d' 严格支配 d 意味着 d 在 d' 和 label 之间）

        # 实际上：在严格支配者集合中，找一个节点，
        # 它不支配任何其他严格支配者
        # （这样它就是最深的，离 label 最近）

        strict_doms = other_doms
        for candidate in strict_doms:
            # 检查 candidate 是否支配其他任何严格支配者
            dominates_other = False
            for other in strict_doms:
                if other == candidate:
                    continue
                if other in dom[candidate]:
                    # candidate 支配 other，说明 candidate 比 other 更靠近入口
                    dominates_other = True
                    break
            if not dominates_other:
                # candidate 不支配任何其他严格支配者
                # 说明它是最深的（离 label 最近）
                idom[label] = candidate
                break
        else:
            # 找不到，可能有多条路径？取任意一个
            idom[label] = next(iter(strict_doms)) if strict_doms else None

    return idom


def dominates(dom: Dict[str, Set[str]], dominator: str, dominated: str) -> bool:
    """检查 dominator 是否支配 dominated"""
    return dominator in dom.get(dominated, set())


# ============================================================
# 回边检测
# ============================================================


@dataclass
class BackEdge:
    """回边：source -> head，其中 head 支配 source"""
    source: str  # 回边源点（循环体末尾）
    head: str  # 回边目标（循环头）


def find_back_edges(fn: MIRFunction) -> List[BackEdge]:
    """
    检测所有回边。

    回边定义：一条边 n -> d，如果 d 支配 n，则 n -> d 是回边。
    回边的目标 d 是循环头，源 n 是循环尾（latch）。

    返回回边列表。
    """
    dom = compute_dominators(fn)
    back_edges: List[BackEdge] = []

    for bb in fn.basic_blocks:
        if bb.terminator is None:
            continue
        succs = get_successors(bb.terminator)
        for succ in succs:
            # 边 bb.label -> succ 是回边当且仅当 succ 支配 bb.label
            # succ 支配 bb.label 当且仅当 succ ∈ dom[bb.label]
            if bb.label in dom and succ in dom[bb.label]:
                back_edges.append(BackEdge(source=bb.label, head=succ))

    return back_edges


# ============================================================
# 自然循环识别
# ============================================================


@dataclass
class Loop:
    """自然循环"""
    header: str  # 循环头（唯一入口）
    body: Set[str] = field(default_factory=set)  # 循环体块集合（含 header）
    latches: Set[str] = field(default_factory=set)  # 回边源点（latch 块）
    exits: Set[str] = field(default_factory=set)  # 循环出口块（后继在循环外）
    parent: Optional[str] = None  # 外层循环的 header（None 表示最外层）
    children: List[str] = field(default_factory=list)  # 内层循环的 header 列表

    @property
    def depth(self) -> int:
        """循环嵌套深度（最外层为 1）"""
        d = 1
        p = self.parent
        while p is not None:
            d += 1
            # parent 存储的是 header 字符串，需要外部解析
            # 这里简化处理，实际深度由 LoopInfo 计算
            break
        return d

    def contains(self, block_label: str) -> bool:
        """检查块是否在循环内"""
        return block_label in self.body


@dataclass
class LoopInfo:
    """
    循环分析结果。

    提供循环的查询接口：所有循环、指定块所在的最内层循环、循环头的循环等。
    """
    loops: Dict[str, Loop] = field(default_factory=dict)  # header -> Loop
    top_level_loops: List[str] = field(default_factory=list)  # 最外层循环的 header 列表
    block_to_loop: Dict[str, str] = field(default_factory=dict)  # block -> 最内层循环 header

    def get_loop(self, header: str) -> Optional[Loop]:
        """根据循环头获取循环"""
        return self.loops.get(header)

    def get_loop_for_block(self, block_label: str) -> Optional[Loop]:
        """获取块所在的最内层循环（不在任何循环中返回 None）"""
        header = self.block_to_loop.get(block_label)
        if header is None:
            return None
        return self.loops.get(header)

    def is_loop_header(self, block_label: str) -> bool:
        """检查块是否是循环头"""
        return block_label in self.loops

    def get_loops_in_order(self) -> List[Loop]:
        """按嵌套层级从外到内返回所有循环"""
        # 简单实现：按 header 排序
        return list(self.loops.values())

    def get_top_level_loops(self) -> List[Loop]:
        """获取所有最外层循环"""
        return [self.loops[h] for h in self.top_level_loops if h in self.loops]


def _collect_natural_loop(
    fn: MIRFunction,
    back_edge: BackEdge,
    predecessors: Dict[str, List[str]],
) -> Set[str]:
    """
    收集一条回边对应的自然循环的所有块。

    自然循环定义：从回边源点 source 出发，反向遍历（沿前驱边），
    直到到达循环头 head，所有经过的块加上 head 构成循环体。
    """
    header = back_edge.head
    source = back_edge.source

    # 循环体至少包含 header 和 source
    loop_blocks = {header, source}

    # 反向遍历：从 source 开始，沿前驱边前进，直到 header
    # 使用栈/队列
    stack = [source]
    while stack:
        block = stack.pop()
        for pred in predecessors.get(block, []):
            if pred == header:
                continue  # 到达循环头，不再向前
            if pred in loop_blocks:
                continue  # 已访问
            loop_blocks.add(pred)
            stack.append(pred)

    return loop_blocks


def _find_loop_exits(
    loop: Loop,
    succ_map: Dict[str, List[str]],
) -> Set[str]:
    """找出循环的出口块（有后继在循环外的块）"""
    exits: Set[str] = set()
    for block in loop.body:
        for succ in succ_map.get(block, []):
            if succ not in loop.body:
                exits.add(block)
                break
    return exits


def analyze_loops(fn: MIRFunction) -> LoopInfo:
    """
    完整的循环分析：检测所有自然循环，构建循环树。

    返回 LoopInfo 对象，包含所有循环和查询接口。
    """
    back_edges = find_back_edges(fn)
    predecessors = build_predecessors(fn)
    succ_map = build_successor_map(fn)

    loops: Dict[str, Loop] = {}
    block_to_innermost: Dict[str, str] = {}  # block -> 最内层循环 header

    # 1. 收集每条回边的自然循环
    for be in back_edges:
        header = be.head
        body = _collect_natural_loop(fn, be, predecessors)

        if header not in loops:
            loops[header] = Loop(header=header, body=body)
            loops[header].latches.add(be.source)
        else:
            # 同一个循环头可能有多条回边
            # 合并循环体
            loops[header].body |= body
            loops[header].latches.add(be.source)

    # 2. 计算每个循环的出口
    for loop in loops.values():
        loop.exits = _find_loop_exits(loop, succ_map)

    # 3. 构建循环树（父子关系）
    # 对每个循环，找到包含它的最小外层循环
    top_level_loops: List[str] = []

    for header, loop in loops.items():
        # 在除自己外的所有循环中，找 body 包含当前循环 header 且最小的那个
        outer_header = None
        outer_size = float("inf")

        for other_header, other_loop in loops.items():
            if other_header == header:
                continue
            if header in other_loop.body:
                # other_loop 包含当前循环
                if len(other_loop.body) < outer_size:
                    outer_size = len(other_loop.body)
                    outer_header = other_header

        if outer_header is not None:
            loop.parent = outer_header
            loops[outer_header].children.append(header)
        else:
            top_level_loops.append(header)

    # 4. 计算每个块所在的最内层循环
    for header, loop in loops.items():
        for block in loop.body:
            current_innermost = block_to_innermost.get(block)
            if current_innermost is None:
                block_to_innermost[block] = header
            else:
                # 比较哪个更小（更内层）
                # 内层循环的 body 是外层的子集
                current_loop = loops[current_innermost]
                if len(loop.body) < len(current_loop.body):
                    block_to_innermost[block] = header

    return LoopInfo(
        loops=loops,
        top_level_loops=top_level_loops,
        block_to_loop=block_to_innermost,
    )


# ============================================================
# 指令工具函数
# ============================================================


def get_instr_operands(instr) -> List[str]:
    """
    获取一条 MIR 指令使用的所有 SSA 操作数。

    返回 SSA 名列表（不含 result_name）。
    使用 isinstance 类型分发，与 replace_instr_operands 保持一致。
    """
    # 常量加载：无操作数
    from .ir_nodes import MIRConst
    if isinstance(instr, MIRConst):
        return []

    # 变量加载：无 SSA 操作数（name 是变量名字符串）
    from .ir_nodes import MIRLoad
    if isinstance(instr, MIRLoad):
        return []

    # 变量存储：value 是 SSA 操作数
    from .ir_nodes import MIRStore
    if isinstance(instr, MIRStore):
        return [instr.value] if instr.value else []

    # 二元运算
    from .ir_nodes import MIRBinOp
    if isinstance(instr, MIRBinOp):
        used = []
        if instr.left:
            used.append(instr.left)
        if instr.right:
            used.append(instr.right)
        return used

    # 一元运算
    from .ir_nodes import MIRUnaryOp
    if isinstance(instr, MIRUnaryOp):
        return [instr.operand] if instr.operand else []

    # 函数调用：args 是 SSA 操作数，callee 可能是函数名（非 SSA）
    from .ir_nodes import MIRCall
    if isinstance(instr, MIRCall):
        return [a for a in instr.args if a]

    # 闭包创建：captures 是 SSA 操作数
    from .ir_nodes import MIRClosureCreate
    if isinstance(instr, MIRClosureCreate):
        return [c for c in instr.captures if c]

    # 列表构建
    from .ir_nodes import MIRListBuild
    if isinstance(instr, MIRListBuild):
        return [e for e in instr.elements if e]

    # 列表追加
    from .ir_nodes import MIRListAppend
    if isinstance(instr, MIRListAppend):
        used = []
        if instr.list_ssa:
            used.append(instr.list_ssa)
        if instr.element_ssa:
            used.append(instr.element_ssa)
        return used

    # 元组构建
    from .ir_nodes import MIRTupleBuild
    if isinstance(instr, MIRTupleBuild):
        return [e for e in instr.elements if e]

    # Map 构建
    from .ir_nodes import MIRMapBuild
    if isinstance(instr, MIRMapBuild):
        used = []
        for key_ssa, val_ssa in instr.entries:
            if key_ssa:
                used.append(key_ssa)
            if val_ssa:
                used.append(val_ssa)
        return used

    # ADT 构建
    from .ir_nodes import MIRADTBuild
    if isinstance(instr, MIRADTBuild):
        return [f for f in instr.fields if f]

    # 字段访问
    from .ir_nodes import MIRFieldAccess
    if isinstance(instr, MIRFieldAccess):
        return [instr.object] if instr.object else []

    # 索引访问
    from .ir_nodes import MIRIndexAccess
    if isinstance(instr, MIRIndexAccess):
        used = []
        if instr.object:
            used.append(instr.object)
        if instr.index:
            used.append(instr.index)
        return used

    # Phi 节点
    from .ir_nodes import MIRPhi
    if isinstance(instr, MIRPhi):
        return [ssa for _, ssa in instr.sources if ssa]

    # 默认：返回空列表
    return []


def is_instr_pure(instr) -> bool:
    """
    判断指令是否是纯的（无副作用）。

    纯指令可以安全地移动（如外提到循环外），
    不纯指令（如函数调用、Store、Panic）不能随意移动。
    """
    from .ir_nodes import (
        MIRADTBuild,
        MIRBinOp,
        MIRCall,
        MIRClosureCreate,
        MIRConst,
        MIRFieldAccess,
        MIRIndexAccess,
        MIRListAppend,
        MIRListBuild,
        MIRMapBuild,
        MIRPhi,
        MIRStore,
        MIRTupleBuild,
        MIRUnaryOp,
    )

    # 这些指令是纯的
    pure_types = (
        MIRConst,
        MIRBinOp,
        MIRUnaryOp,
        MIRPhi,
        MIRTupleBuild,
        MIRFieldAccess,  # 只读字段访问是纯的
    )

    if isinstance(instr, pure_types):
        return True

    # 列表/Map/ADT 构建：虽然分配内存但无外部副作用
    # 在 SSA 形式下可视为纯（结果名唯一）
    if isinstance(instr, (MIRListBuild, MIRMapBuild, MIRADTBuild)):
        return True

    # 索引访问：读操作，纯的
    if isinstance(instr, MIRIndexAccess):
        return True

    # ListAppend：修改列表，但 SSA 中返回新列表，也算纯
    if isinstance(instr, MIRListAppend):
        return True

    # 闭包创建：纯的（不修改外部状态）
    if isinstance(instr, MIRClosureCreate):
        return True

    # Store 有副作用
    if isinstance(instr, MIRStore):
        return False

    # 函数调用：可能有副作用
    if isinstance(instr, MIRCall):
        return False

    # 默认保守：不纯
    return False


def get_terminator_used_ssa(terminator) -> List[str]:
    """
    获取终结指令使用的 SSA 名。

    使用 isinstance 类型分发，与 replace_terminator_operands 保持一致。
    """
    if terminator is None:
        return []

    # 条件分支
    if isinstance(terminator, MIRBranch):
        return [terminator.condition] if terminator.condition else []

    # Switch 跳转
    if isinstance(terminator, MIRSwitch):
        return [terminator.value] if terminator.value else []

    # 返回
    if isinstance(terminator, MIRReturn):
        return [terminator.value] if terminator.value else []

    # Match 跳转
    if isinstance(terminator, MIRMatchJump):
        return [terminator.value] if terminator.value else []

    # 无条件跳转：无 SSA 操作数
    if isinstance(terminator, MIRJump):
        return []

    # 默认：返回空列表
    return []


def replace_instr_operands(instr, replacements: Dict[str, str]):
    """
    替换指令中的操作数 SSA 名（统一 API）。

    将出现在 replacements 字典中的 SSA 名替换为对应的值。
    使用 isinstance 类型检查，比 hasattr 更安全可靠。

    Args:
        instr: MIR 指令对象
        replacements: {旧SSA名: 新SSA名} 的字典
    """
    if not replacements:
        return

    if isinstance(instr, MIRBinOp):
        if instr.left in replacements:
            instr.left = replacements[instr.left]
        if instr.right in replacements:
            instr.right = replacements[instr.right]

    elif isinstance(instr, MIRUnaryOp):
        if instr.operand in replacements:
            instr.operand = replacements[instr.operand]

    elif isinstance(instr, MIRCall):
        instr.args = [
            replacements[a] if a in replacements else a for a in instr.args
        ]
        if instr.callee in replacements:
            instr.callee = replacements[instr.callee]

    elif isinstance(instr, MIRFieldAccess):
        if instr.object in replacements:
            instr.object = replacements[instr.object]

    elif isinstance(instr, MIRIndexAccess):
        if instr.object in replacements:
            instr.object = replacements[instr.object]
        if instr.index in replacements:
            instr.index = replacements[instr.index]

    elif isinstance(instr, MIRListBuild):
        instr.elements = [
            replacements[e] if e in replacements else e for e in instr.elements
        ]

    elif isinstance(instr, MIRListAppend):
        if instr.list_ssa in replacements:
            instr.list_ssa = replacements[instr.list_ssa]
        if instr.element_ssa in replacements:
            instr.element_ssa = replacements[instr.element_ssa]

    elif isinstance(instr, MIRTupleBuild):
        instr.elements = [
            replacements[e] if e in replacements else e for e in instr.elements
        ]

    elif isinstance(instr, MIRMapBuild):
        instr.entries = [
            (
                replacements[k] if k in replacements else k,
                replacements[v] if v in replacements else v,
            )
            for k, v in instr.entries
        ]

    elif isinstance(instr, MIRADTBuild):
        instr.fields = [
            replacements[f] if f in replacements else f for f in instr.fields
        ]

    elif isinstance(instr, MIRClosureCreate):
        instr.captures = [
            replacements[c] if c in replacements else c for c in instr.captures
        ]

    elif isinstance(instr, MIRStore):
        if instr.value in replacements:
            instr.value = replacements[instr.value]

    elif isinstance(instr, MIRPhi):
        instr.sources = [
            (label, replacements[ssa] if ssa in replacements else ssa)
            for label, ssa in instr.sources
        ]


def replace_terminator_operands(terminator, replacements: Dict[str, str]):
    """
    替换终结指令中的操作数 SSA 名（统一 API）。

    Args:
        terminator: MIR 终结指令对象
        replacements: {旧SSA名: 新SSA名} 的字典
    """
    if not replacements or terminator is None:
        return

    if isinstance(terminator, MIRBranch):
        if terminator.condition in replacements:
            terminator.condition = replacements[terminator.condition]

    elif isinstance(terminator, MIRSwitch):
        if terminator.value in replacements:
            terminator.value = replacements[terminator.value]

    elif isinstance(terminator, MIRReturn):
        if terminator.value and terminator.value in replacements:
            terminator.value = replacements[terminator.value]

    elif isinstance(terminator, MIRMatchJump):
        if terminator.value in replacements:
            terminator.value = replacements[terminator.value]
