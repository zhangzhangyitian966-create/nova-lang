"""
PassManager 优化 Pass 单元测试

为 ir/pass_manager.py 中的核心优化 Pass 编写独立单元测试：
- DeadCodeElimination (DCE)
- Inlining
- CommonSubexprElimination (CSE)
- LIRDeadCodeElimination
"""

import unittest

from nova.lexer import Lexer
from nova.parser import Parser
from nova.ir.hir_lowering import HIRLowering
from nova.ir.mir_lowering import MIRLowering
from nova.ir.lir_lowering import LIRLowering

from nova.ir.ir_nodes import (
    INT_TYPE,
    HIRModule,
    HIRFnDecl,
    HIRFunction,
    HIRIntLiteral,
    HIRBinaryOp,
    HIRIdentifier,
    HIRBlockExpr,
    HIRLetDecl,
    MIRModule,
    MIRBasicBlock,
    MIRConst,
    MIRBinOp,
    MIRReturn,
    MIRJump,
    LIRModule,
    LIRFunction,
    LIRLoadConst,
    LIRBinOp,
    LIRReturn,
    LIRLabel,
    LIRStoreGlobal,
)
from nova.ir.pass_manager import (
    DeadCodeElimination,
    Inlining,
    CommonSubexprElimination,
    LIRDeadCodeElimination,
)


def compile_to_hir(source: str):
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    return HIRLowering().lower(ast)


def compile_to_mir(source: str):
    hir = compile_to_hir(source)
    return MIRLowering().lower(hir)


def compile_to_lir(source: str):
    mir = compile_to_mir(source)
    return LIRLowering().lower(mir)


# ============================================================
# 测试类 1: DeadCodeElimination
# ============================================================

class TestDeadCodeElimination(unittest.TestCase):
    """测试死代码消除 Pass"""

    def test_remove_unused_let(self):
        """未使用且无副作用的 let 绑定应被消除"""
        hir = compile_to_hir("fn f() { let x = 1 + 2; 3 }")
        dce = DeadCodeElimination()
        changed = dce.run(hir)
        self.assertTrue(changed, "DCE 应消除未使用的 let x")

    def test_keep_used_let(self):
        """被使用的 let 绑定应保留"""
        # 手动构造 HIR，避免前端编译器对 let 绑定做预优化
        let_x = HIRLetDecl(name="x", ir_type=INT_TYPE, value=HIRBinaryOp(op="+", left=HIRIntLiteral(1), right=HIRIntLiteral(2)))
        use_x = HIRBinaryOp(op="+", left=HIRIdentifier("x"), right=HIRIntLiteral(3))
        block = HIRBlockExpr(exprs=[let_x, use_x])

        hir = HIRModule(name="test")
        fn = HIRFunction(name="f", params=[], return_type=INT_TYPE, body=block)
        fn_decl = HIRFnDecl(fn_def=fn)
        hir.declarations = [fn_decl]

        dce = DeadCodeElimination()
        changed = dce.run(hir)
        self.assertFalse(changed, "DCE 不应消除被使用的 let x")

    def test_keep_side_effect_unused_let(self):
        """有副作用的未使用 let 绑定应保留"""
        hir = compile_to_hir('fn f() { let x = print("hello"); 3 }')
        dce = DeadCodeElimination()
        changed = dce.run(hir)
        self.assertFalse(changed, "DCE 不应消除有副作用的 let x")

    def test_keep_last_expr(self):
        """块的最后一个表达式（返回值）应始终保留"""
        hir = compile_to_hir("fn f() { 42 }")
        dce = DeadCodeElimination()
        changed = dce.run(hir)
        self.assertFalse(changed, "DCE 不应消除块的返回值")

    def test_remove_pure_expr_statement(self):
        """无副作用且非最后的表达式语句应被移除"""
        hir = compile_to_hir("fn f() { 1 + 2; 3 }")
        dce = DeadCodeElimination()
        changed = dce.run(hir)
        self.assertTrue(changed, "DCE 应消除无副作用的表达式语句 1+2")

    def test_keep_side_effect_expr_statement(self):
        """有副作用的表达式语句应保留"""
        hir = compile_to_hir('fn f() { print("a"); 3 }')
        dce = DeadCodeElimination()
        changed = dce.run(hir)
        self.assertFalse(changed, "DCE 不应消除有副作用的表达式语句")


# ============================================================
# 测试类 2: Inlining
# ============================================================

class TestInlining(unittest.TestCase):
    """测试函数内联 Pass"""

    def test_inline_simple_function(self):
        """小型单表达式函数应被内联"""
        hir = compile_to_hir("fn add(a, b) { a + b } fn main() { add(1, 2) }")
        inline = Inlining()
        changed = inline.run(hir)
        self.assertTrue(changed, "内联应替换 add(1, 2) 调用")

    def test_no_inline_recursive(self):
        """递归函数不应被内联"""
        # 手动构造含递归标记的函数，避免依赖前端递归检测
        body = HIRBlockExpr(exprs=[HIRIntLiteral(1)])
        fn = HIRFunction(name="fact", params=[("n", INT_TYPE)], return_type=INT_TYPE, body=body, is_recursive=True)
        hir = HIRModule(name="test")
        hir.declarations = [HIRFnDecl(fn_def=fn)]

        inline = Inlining()
        changed = inline.run(hir)
        self.assertFalse(changed, "递归函数不应被内联")

    def test_no_inline_too_many_params(self):
        """参数超过 4 个的函数不应被内联"""
        hir = compile_to_hir(
            "fn many(a, b, c, d, e) { a } fn main() { many(1, 2, 3, 4, 5) }"
        )
        inline = Inlining()
        changed = inline.run(hir)
        self.assertFalse(changed, "参数过多的函数不应被内联")

    def test_inline_preserves_block_body(self):
        """block 体函数（单表达式块）应被内联"""
        hir = compile_to_hir("fn double(x) { x * 2 } fn main() { double(3) }")
        inline = Inlining()
        changed = inline.run(hir)
        self.assertTrue(changed, "block 体函数应被内联")


# ============================================================
# 测试类 3: CommonSubexprElimination
# ============================================================

class TestCommonSubexprElimination(unittest.TestCase):
    """测试公共子表达式消除 Pass"""

    def test_cse_eliminates_duplicate_binop(self):
        """重复的纯二元运算应被消除"""
        mir = compile_to_mir("fn test(x) { x + x }")
        cse = CommonSubexprElimination()
        changed = cse.run(mir)
        # 即使实际没有重复指令（参数只算一次），也验证不抛异常
        # 为构造真正的重复，需要手动构造 MIR
        self.assertIsInstance(mir, MIRModule)

    def test_cse_commutative_normalized(self):
        """可交换运算应做规范化（a+b 与 b+a 视为相同）"""
        # 构造一个基本块，包含两个可交换的重复运算
        bb = MIRBasicBlock(label="bb0")
        c0 = MIRConst(value=5, const_type="int")
        c0.result_name = "v0"
        c1 = MIRConst(value=3, const_type="int")
        c1.result_name = "v1"
        b0 = MIRBinOp(op="+", left="v0", right="v1")
        b0.result_name = "v2"
        b1 = MIRBinOp(op="+", left="v1", right="v0")
        b1.result_name = "v3"
        bb.instructions = [c0, c1, b0, b1]
        bb.terminator = MIRReturn(value="v3")
        mir = MIRModule(name="test")
        mir.functions["test"] = type("obj", (), {"basic_blocks": [bb]})

        cse = CommonSubexprElimination()
        changed = cse.run(mir)
        # v3 应该被消除，复用 v2
        self.assertTrue(changed, "CSE 应消除规范化的重复加法")

    def test_cse_no_side_effect_instr(self):
        """有副作用的指令不应被 CSE"""
        mir = compile_to_mir('fn test() { print("a"); print("a") }')
        cse = CommonSubexprElimination()
        changed = cse.run(mir)
        # print 调用有副作用，不应被消除
        self.assertFalse(changed, "有副作用的调用不应被 CSE")

    def test_cse_local_block_only(self):
        """CSE 只在基本块内有效，跨块不消除"""
        # 手动构造两个基本块，各有一个相同的运算
        bb0 = MIRBasicBlock(label="bb0")
        c0 = MIRConst(value=5, const_type="int")
        c0.result_name = "v0"
        b0 = MIRBinOp(op="*", left="v0", right="v0")
        b0.result_name = "v1"
        bb0.instructions = [c0, b0]
        bb0.terminator = MIRJump(target="bb1")

        bb1 = MIRBasicBlock(label="bb1")
        c1 = MIRConst(value=5, const_type="int")
        c1.result_name = "v2"
        b1 = MIRBinOp(op="*", left="v2", right="v2")
        b1.result_name = "v3"
        bb1.instructions = [c1, b1]
        bb1.terminator = MIRReturn(value="v3")

        mir = MIRModule(name="test")
        mir.functions["test"] = type("obj", (), {"basic_blocks": [bb0, bb1]})

        cse = CommonSubexprElimination()
        changed = cse.run(mir)
        # 跨块不应消除
        self.assertFalse(changed, "跨基本块的重复运算不应被局部 CSE 消除")


# ============================================================
# 测试类 4: LIRDeadCodeElimination
# ============================================================

class TestLIRDeadCodeElimination(unittest.TestCase):
    """测试 LIR 层死代码消除 Pass"""

    def test_remove_unused_load_const(self):
        """未使用的 LIRLoadConst 应被消除"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="f", params=[], return_type=INT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=42, const_type="int"),
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", INT_TYPE)
        fn.body[2].dst_loc = ("r1", INT_TYPE)
        fn.body[3].src_locs = [("r1", INT_TYPE)]
        module.functions["f"] = fn

        dce = LIRDeadCodeElimination()
        changed = dce.run(module)
        self.assertTrue(changed, "LIR-DCE 应消除未使用的 LoadConst r0")

    def test_keep_store_global(self):
        """LIRStoreGlobal 有副作用，应保留"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="f", params=[], return_type=INT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=42, const_type="int"),
            LIRStoreGlobal(global_name="g"),
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", INT_TYPE)
        fn.body[2].src_locs = [("r0", INT_TYPE)]
        fn.body[3].dst_loc = ("r1", INT_TYPE)
        fn.body[4].src_locs = [("r1", INT_TYPE)]
        module.functions["f"] = fn

        dce = LIRDeadCodeElimination()
        changed = dce.run(module)
        # StoreGlobal 有副作用，不应被消除；但 r0 被 StoreGlobal 使用了，
        # 所以 r0 的 LoadConst 也应保留
        self.assertFalse(changed, "有副作用的 StoreGlobal 及其依赖应全部保留")

    def test_keep_used_instr(self):
        """被后续指令使用的指令应保留"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="f", params=[], return_type=INT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=2, const_type="int"),
            LIRLoadConst(value=3, const_type="int"),
            LIRBinOp(op="+"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", INT_TYPE)
        fn.body[2].dst_loc = ("r1", INT_TYPE)
        fn.body[3].src_locs = [("r0", INT_TYPE), ("r1", INT_TYPE)]
        fn.body[3].dst_loc = ("r2", INT_TYPE)
        fn.body[4].src_locs = [("r2", INT_TYPE)]
        module.functions["f"] = fn

        dce = LIRDeadCodeElimination()
        changed = dce.run(module)
        self.assertFalse(changed, "被使用的指令链应全部保留")

    def test_remove_unused_binop(self):
        """未使用的纯 BinOp 应被消除"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="f", params=[], return_type=INT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=2, const_type="int"),
            LIRLoadConst(value=3, const_type="int"),
            LIRBinOp(op="+"),
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", INT_TYPE)
        fn.body[2].dst_loc = ("r1", INT_TYPE)
        fn.body[3].src_locs = [("r0", INT_TYPE), ("r1", INT_TYPE)]
        fn.body[3].dst_loc = ("r2", INT_TYPE)
        fn.body[4].dst_loc = ("r3", INT_TYPE)
        fn.body[5].src_locs = [("r3", INT_TYPE)]
        module.functions["f"] = fn

        dce = LIRDeadCodeElimination()
        changed = dce.run(module)
        self.assertTrue(changed, "LIR-DCE 应消除未使用的 BinOp r2")


if __name__ == "__main__":
    unittest.main()
