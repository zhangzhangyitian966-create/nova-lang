"""
CFG 基础设施单元测试

覆盖 ir/cfg_utils.py 的核心功能：
- CFG 基础工具（build_block_map, get_successors, build_predecessors）
- 支配树计算（compute_dominators）
- 回边检测（find_back_edges）
- 自然循环分析（analyze_loops）
"""

import unittest

from nova.ir.ir_nodes import (
    IRType,
    MIRBasicBlock,
    MIRBinOp,
    MIRBranch,
    MIRConst,
    MIRFunction,
    MIRJump,
    MIRPhi,
    MIRReturn,
    NovaType,
)
from nova.ir.cfg_utils import (
    BackEdge,
    Loop,
    LoopInfo,
    analyze_loops,
    build_block_map,
    build_predecessors,
    compute_dominators,
    find_back_edges,
    get_successors,
)


class TestBuildBlockMap(unittest.TestCase):
    """测试 build_block_map"""

    def test_linear_blocks(self):
        """线性块序列能正确映射"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRJump("bb2"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRReturn())
        fn = MIRFunction("test", [], NovaType(IRType.UNIT), [bb0, bb1, bb2])

        block_map = build_block_map(fn)
        self.assertEqual(block_map["bb0"], bb0)
        self.assertEqual(block_map["bb1"], bb1)
        self.assertEqual(block_map["bb2"], bb2)


class TestGetSuccessors(unittest.TestCase):
    """测试 get_successors"""

    def test_jump_successor(self):
        """MIRJump 返回单后继"""
        self.assertEqual(get_successors(MIRJump("bb1")), ["bb1"])

    def test_branch_successors(self):
        """MIRBranch 返回两个后继"""
        term = MIRBranch("c", "bb_true", "bb_false")
        self.assertEqual(get_successors(term), ["bb_true", "bb_false"])

    def test_return_successor(self):
        """MIRReturn 返回空列表"""
        self.assertEqual(get_successors(MIRReturn("x")), [])
        self.assertEqual(get_successors(MIRReturn()), [])

    def test_none_terminator(self):
        """None 终结器返回空列表"""
        self.assertEqual(get_successors(None), [])


class TestBuildPredecessors(unittest.TestCase):
    """测试 build_predecessors"""

    def test_linear_chain(self):
        """线性链：每个块只有一个前驱"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRJump("bb2"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRReturn())
        fn = MIRFunction("test", [], NovaType(IRType.UNIT), [bb0, bb1, bb2])

        preds = build_predecessors(fn)
        self.assertEqual(preds["bb0"], [])
        self.assertEqual(preds["bb1"], ["bb0"])
        self.assertEqual(preds["bb2"], ["bb1"])

    def test_if_else_merge(self):
        """if-else 汇合点有两个前驱"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRBranch("c", "bb1", "bb2"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRJump("bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb3"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = MIRFunction("test", [], NovaType(IRType.UNIT), [bb0, bb1, bb2, bb3])

        preds = build_predecessors(fn)
        self.assertEqual(preds["bb3"], ["bb1", "bb2"])


class TestComputeDominators(unittest.TestCase):
    """测试 compute_dominators"""

    def _make_fn(self, blocks, entry="bb0"):
        """辅助方法：快速创建 MIRFunction"""
        return MIRFunction("test", [], NovaType(IRType.UNIT), blocks, entry)

    def test_linear_chain(self):
        """线性链：每个块支配自己和所有后续块"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRJump("bb2"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2])

        dom = compute_dominators(fn)
        self.assertEqual(dom["bb0"], {"bb0"})
        self.assertEqual(dom["bb1"], {"bb0", "bb1"})
        self.assertEqual(dom["bb2"], {"bb0", "bb1", "bb2"})

    def test_diamond_if_else(self):
        """菱形 if-else：merge 块支配集是两个分支的交集"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRBranch("c", "bb1", "bb2"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRJump("bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb3"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        dom = compute_dominators(fn)
        self.assertEqual(dom["bb0"], {"bb0"})
        self.assertEqual(dom["bb1"], {"bb0", "bb1"})
        self.assertEqual(dom["bb2"], {"bb0", "bb2"})
        self.assertEqual(dom["bb3"], {"bb0", "bb3"})

    def test_simple_loop(self):
        """简单循环：循环头支配循环体"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRBranch("c", "bb2", "bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb1"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        dom = compute_dominators(fn)
        self.assertEqual(dom["bb0"], {"bb0"})
        self.assertEqual(dom["bb1"], {"bb0", "bb1"})
        self.assertEqual(dom["bb2"], {"bb0", "bb1", "bb2"})
        self.assertEqual(dom["bb3"], {"bb0", "bb1", "bb3"})

    def test_unreachable_block(self):
        """不可达块只支配自己"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRReturn())
        bb1 = MIRBasicBlock("bb1", terminator=MIRReturn())  # 无前驱，不可达
        fn = self._make_fn([bb0, bb1])

        dom = compute_dominators(fn)
        self.assertEqual(dom["bb0"], {"bb0"})
        self.assertEqual(dom["bb1"], {"bb1"})


class TestFindBackEdges(unittest.TestCase):
    """测试 find_back_edges"""

    def _make_fn(self, blocks, entry="bb0"):
        return MIRFunction("test", [], NovaType(IRType.UNIT), blocks, entry)

    def test_no_back_edge_linear(self):
        """线性链无回边"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1])

        back_edges = find_back_edges(fn)
        self.assertEqual(back_edges, [])

    def test_simple_loop_back_edge(self):
        """简单循环有一条回边 bb2 -> bb1"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRBranch("c", "bb2", "bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb1"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        back_edges = find_back_edges(fn)
        self.assertEqual(len(back_edges), 1)
        self.assertEqual(back_edges[0], BackEdge("bb2", "bb1"))

    def test_no_back_edge_branch(self):
        """if-else 无回边"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRBranch("c", "bb1", "bb2"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRJump("bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb3"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        back_edges = find_back_edges(fn)
        self.assertEqual(back_edges, [])


class TestAnalyzeLoops(unittest.TestCase):
    """测试 analyze_loops"""

    def _make_fn(self, blocks, entry="bb0"):
        return MIRFunction("test", [], NovaType(IRType.UNIT), blocks, entry)

    def test_single_loop(self):
        """分析简单循环：循环体包含 header 和 latch"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRBranch("c", "bb2", "bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb1"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        loop_info = analyze_loops(fn)
        self.assertIn("bb1", loop_info.loops)

        loop = loop_info.loops["bb1"]
        self.assertEqual(loop.header, "bb1")
        self.assertIn("bb1", loop.body)
        self.assertIn("bb2", loop.body)
        self.assertEqual(loop.latches, {"bb2"})

    def test_no_loop(self):
        """无循环时返回空 LoopInfo"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1])

        loop_info = analyze_loops(fn)
        self.assertEqual(loop_info.loops, {})

    def test_get_loop_for_block(self):
        """LoopInfo.get_loop_for_block 返回块所在的最内层循环"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRBranch("c", "bb2", "bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb1"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        loop_info = analyze_loops(fn)
        loop = loop_info.get_loop_for_block("bb2")
        self.assertIsNotNone(loop)
        self.assertEqual(loop.header, "bb1")

        # 循环外块返回 None
        self.assertIsNone(loop_info.get_loop_for_block("bb3"))

    def test_loop_contains(self):
        """Loop.contains 检查块是否在循环内"""
        loop = Loop(header="bb1", body={"bb1", "bb2"})
        self.assertTrue(loop.contains("bb1"))
        self.assertTrue(loop.contains("bb2"))
        self.assertFalse(loop.contains("bb3"))

    def test_is_loop_header(self):
        """LoopInfo.is_loop_header 正确识别循环头"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRBranch("c", "bb2", "bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb1"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        loop_info = analyze_loops(fn)
        self.assertTrue(loop_info.is_loop_header("bb1"))
        self.assertFalse(loop_info.is_loop_header("bb2"))


class TestLoopExits(unittest.TestCase):
    """测试循环出口识别"""

    def _make_fn(self, blocks, entry="bb0"):
        return MIRFunction("test", [], NovaType(IRType.UNIT), blocks, entry)

    def test_loop_exit_detected(self):
        """循环出口块正确识别"""
        bb0 = MIRBasicBlock("bb0", terminator=MIRJump("bb1"))
        bb1 = MIRBasicBlock("bb1", terminator=MIRBranch("c", "bb2", "bb3"))
        bb2 = MIRBasicBlock("bb2", terminator=MIRJump("bb1"))
        bb3 = MIRBasicBlock("bb3", terminator=MIRReturn())
        fn = self._make_fn([bb0, bb1, bb2, bb3])

        loop_info = analyze_loops(fn)
        loop = loop_info.loops["bb1"]
        # bb1 有后继 bb3 在循环外，所以 bb1 是出口
        self.assertIn("bb1", loop.exits)


if __name__ == "__main__":
    unittest.main()
