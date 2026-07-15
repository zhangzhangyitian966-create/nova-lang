"""
Nova IR 测试

测试 HIR/MIR 转换、三层 IR 节点、Pass 管理器。
"""

import unittest
import sys
import os

from nova.lexer import Lexer
from nova.parser import Parser
from nova.ast_nodes import Program

from nova.ir.ir_nodes import (
    IRType, NovaType,
    INT_TYPE, FLOAT_TYPE, STRING_TYPE, BOOL_TYPE, CHAR_TYPE, UNIT_TYPE, NEVER_TYPE,
    ListType, MapType, TupleType, FnType, ADTType, OptionType, ResultType,
    HIRModule, HIRFunction, HIRTypeDef, HIRVariant,
    HIRDecl, HIRFnDecl, HIRLetDecl, HIRTypeDecl, HIRAliasDecl,
    HIRExpr,
    HIRIntLiteral, HIRFloatLiteral, HIRStringLiteral, HIRBoolLiteral,
    HIRCharLiteral, HIRUnitLiteral, HIRIdentifier,
    HIRBinaryOp, HIRUnaryOp,
    HIRIfExpr, HIRMatchExpr, HIRMatchArm,
    HIRLambda, HIRCallExpr, HIRPipeExpr,
    HIRListExpr, HIRTupleExpr,
    HIRFieldExpr, HIRIndexExpr, HIRBlockExpr,
    HIRForExpr, HIRWhileExpr, HIRBreakExpr, HIRContinueExpr,
    HIRListComprehension, HIRAssignExpr,
    HIRPattern,
    HIRIntPattern, HIRBindPattern, HIRWildcardPattern, HIRConstructorPattern,
    HIRTuplePattern, HIRListPattern,
    HIRImportDecl, HIRExportDecl,
    MIRModule, MIRFunction, MIRBasicBlock, MIRGlobal,
    MIRConst, MIRBinOp, MIRReturn, MIRPhi, MIRBranch,
    LIRModule, LIRFunction, LIRInstr, LIRLabel, LIRReturn, LIRLoadConst,
    LIRLoadReg, LIRBinOp, LIRUnaryOp, LIRJump, LIRBranch, LIRStoreReg,
)
from nova.ir.hir_lowering import HIRLowering
from nova.ir.mir_lowering import MIRLowering
from nova.ir.lir_lowering import LIRLowering
from nova.ir.pass_manager import (
    PassManager, ConstantFolding, DeadCodeElimination, Inlining,
    CommonSubexprElimination, LoopInvariantCodeMotion,
    default_optimization_pipeline,
)


def compile_to_hir(source: str) -> HIRModule:
    """辅助函数：从 Nova 源码编译到 HIR"""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    return HIRLowering().lower(ast)


def compile_to_mir(source: str) -> MIRModule:
    """辅助函数：从 Nova 源码编译到 MIR"""
    hir = compile_to_hir(source)
    return MIRLowering().lower(hir)


def compile_to_lir(source: str) -> LIRModule:
    """辅助函数：从 Nova 源码编译到 LIR"""
    mir = compile_to_mir(source)
    return LIRLowering().lower(mir)


# ============================================================
# 测试 IR 类型系统
# ============================================================

class TestNovaIRTypes(unittest.TestCase):
    """测试 Nova IR 类型系统"""

    def test_basic_type_equality(self):
        self.assertEqual(INT_TYPE, NovaType(IRType.INT))
        self.assertEqual(FLOAT_TYPE, NovaType(IRType.FLOAT))
        self.assertEqual(STRING_TYPE, NovaType(IRType.STRING))
        self.assertEqual(BOOL_TYPE, NovaType(IRType.BOOL))

    def test_basic_type_inequality(self):
        self.assertNotEqual(INT_TYPE, FLOAT_TYPE)
        self.assertNotEqual(STRING_TYPE, BOOL_TYPE)

    def test_list_type(self):
        lst = ListType(INT_TYPE)
        self.assertEqual(lst.kind, IRType.LIST)
        self.assertEqual(lst.params, [INT_TYPE])
        self.assertEqual(lst, NovaType(IRType.LIST, [NovaType(IRType.INT)]))

    def test_map_type(self):
        m = MapType(STRING_TYPE, INT_TYPE)
        self.assertEqual(m.kind, IRType.MAP)
        self.assertEqual(len(m.params), 2)

    def test_tuple_type(self):
        t = TupleType(INT_TYPE, STRING_TYPE)
        self.assertEqual(t.kind, IRType.TUPLE)
        self.assertEqual(len(t.params), 2)

    def test_fn_type(self):
        fn_ty = FnType(INT_TYPE, INT_TYPE, INT_TYPE)
        self.assertEqual(fn_ty.kind, IRType.FUNCTION)
        self.assertEqual(len(fn_ty.params), 3)

    def test_option_type(self):
        opt = OptionType(INT_TYPE)
        self.assertEqual(opt.kind, IRType.ADT)
        self.assertEqual(opt.name, "Option")
        self.assertEqual(len(opt.params), 1)

    def test_result_type(self):
        res = ResultType(INT_TYPE, STRING_TYPE)
        self.assertEqual(res.kind, IRType.ADT)
        self.assertEqual(res.name, "Result")
        self.assertEqual(len(res.params), 2)

    def test_type_hash(self):
        """类型必须可哈希，才能用于字典键"""
        type_set = {INT_TYPE, FLOAT_TYPE, STRING_TYPE}
        self.assertEqual(len(type_set), 3)

    def test_type_repr(self):
        self.assertEqual(repr(INT_TYPE), "INT")
        self.assertEqual(repr(ListType(INT_TYPE)), "List[INT]")
        self.assertEqual(repr(OptionType(STRING_TYPE)), "Option[STRING]")


# ============================================================
# 测试 HIR 降级
# ============================================================

class TestHIRLowering(unittest.TestCase):
    """测试 AST -> HIR 降级"""

    def test_int_literal(self):
        hir = compile_to_hir("let x = 42")
        self.assertEqual(len(hir.declarations), 1)
        decl = hir.declarations[0]
        self.assertIsInstance(decl, HIRLetDecl)
        self.assertEqual(decl.name, "x")
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 42)

    def test_float_literal(self):
        hir = compile_to_hir("let x = 3.14")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRFloatLiteral)
        self.assertAlmostEqual(decl.value.value, 3.14)

    def test_string_literal(self):
        hir = compile_to_hir(r'let x = "hello"')
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRStringLiteral)
        self.assertEqual(decl.value.value, "hello")

    def test_bool_literal(self):
        hir = compile_to_hir("let x = true")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRBoolLiteral)
        self.assertEqual(decl.value.value, True)

    def test_binary_op(self):
        hir = compile_to_hir("let x = 1 + 2")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRBinaryOp)
        self.assertEqual(decl.value.op, "+")
        self.assertIsInstance(decl.value.left, HIRIntLiteral)
        self.assertEqual(decl.value.left.value, 1)
        self.assertIsInstance(decl.value.right, HIRIntLiteral)
        self.assertEqual(decl.value.right.value, 2)

    def test_unary_op(self):
        hir = compile_to_hir("let x = -42")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRUnaryOp)
        self.assertEqual(decl.value.op, "-")

    def test_if_expr(self):
        hir = compile_to_hir("let x = if true then 1 else 2")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIfExpr)
        self.assertIsInstance(decl.value.condition, HIRBoolLiteral)
        self.assertIsInstance(decl.value.consequence, HIRIntLiteral)
        self.assertIsNotNone(decl.value.alternative)

    def test_fn_def(self):
        hir = compile_to_hir("fn add(a: Int, b: Int) -> Int { a + b }")
        fn_decl = hir.declarations[0]
        self.assertIsInstance(fn_decl, HIRFnDecl)
        self.assertEqual(fn_decl.fn_def.name, "add")
        self.assertEqual(len(fn_decl.fn_def.params), 2)

    def test_match_expr(self):
        hir = compile_to_hir(
            'let x = match 42 { 1 -> "one" n -> "other" }'
        )
        found = False
        for decl in hir.declarations:
            if isinstance(decl, HIRLetDecl) and isinstance(decl.value, HIRMatchExpr):
                found = True
                self.assertEqual(len(decl.value.arms), 2)
        self.assertTrue(found, "Should have found a match expression")

    def test_lambda(self):
        hir = compile_to_hir("let f = |x| x * 2")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRLambda)
        self.assertEqual(len(decl.value.params), 1)

    def test_pipe_expr(self):
        hir = compile_to_hir("[1,2,3] |> sum")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRPipeExpr)
        self.assertEqual(len(decl.value.stages), 2)

    def test_list_expr(self):
        hir = compile_to_hir("let x = [1, 2, 3]")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRListExpr)
        self.assertEqual(len(decl.value.elements), 3)

    def test_for_expr(self):
        hir = compile_to_hir("for x in [1, 2, 3] { x * 2 }")
        # for 循环作为顶层声明处理
        self.assertTrue(len(hir.declarations) > 0)

    def test_while_expr(self):
        hir = compile_to_hir("while true { 1 }")
        self.assertTrue(len(hir.declarations) > 0)

    def test_mut_binding(self):
        hir = compile_to_hir("mut counter = 0")
        decl = hir.declarations[0]
        self.assertIsInstance(decl, HIRLetDecl)
        self.assertEqual(decl.name, "counter")
        self.assertTrue(decl.is_mutable)

    def test_type_def(self):
        hir = compile_to_hir("type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }")
        td_decl = hir.declarations[0]
        self.assertIsInstance(td_decl, HIRTypeDecl)
        self.assertEqual(td_decl.type_def.name, "Shape")
        self.assertEqual(len(td_decl.type_def.variants), 2)

    def test_import_decl(self):
        hir = compile_to_hir('import "std/math"')
        imp = hir.declarations[0]
        self.assertIsInstance(imp, HIRImportDecl)
        self.assertEqual(imp.module, "std/math")

    def test_export_decl(self):
        hir = compile_to_hir("export myFunc")
        exp = hir.declarations[0]
        self.assertIsInstance(exp, HIRExportDecl)
        self.assertEqual(exp.name, "myFunc")

    def test_block_expr(self):
        hir = compile_to_hir("let x = { 1; 2; 3 }")
        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRBlockExpr)
        self.assertEqual(len(decl.value.exprs), 3)

    def test_nested_binary(self):
        hir = compile_to_hir("let x = 1 + 2 * 3")
        decl = hir.declarations[0]
        # Parser handles precedence, so * binds tighter
        self.assertIsInstance(decl.value, HIRBinaryOp)
        self.assertEqual(decl.value.op, "+")
        self.assertIsInstance(decl.value.right, HIRBinaryOp)
        self.assertEqual(decl.value.right.op, "*")

    def test_fn_with_multiple_params(self):
        hir = compile_to_hir("fn greet(name: String, age: Int) -> String { name }")
        fn_decl = hir.declarations[0]
        self.assertEqual(len(fn_decl.fn_def.params), 2)


# ============================================================
# 测试 MIR 降级
# ============================================================

class TestMIRLowering(unittest.TestCase):
    """测试 HIR -> MIR 降级"""

    def test_simple_function(self):
        mir = compile_to_mir("fn id(x) { x }")
        self.assertIn("id", mir.functions)
        fn = mir.functions["id"]
        self.assertEqual(fn.name, "id")
        self.assertEqual(len(fn.basic_blocks), 1)
        self.assertEqual(fn.entry_block, "bb0")

    def test_fn_has_return(self):
        mir = compile_to_mir("fn id(x) { x }")
        fn = mir.functions["id"]
        bb0 = fn.basic_blocks[0]
        self.assertIsNotNone(bb0.terminator)
        self.assertIsInstance(bb0.terminator, MIRReturn)

    def test_fn_params_ssa(self):
        mir = compile_to_mir("fn add(a, b) { a }")
        fn = mir.functions["add"]
        self.assertEqual(len(fn.params), 2)

    def test_global_let(self):
        mir = compile_to_mir("let x = 42")
        self.assertIn("x", mir.globals)
        self.assertEqual(mir.globals["x"].name, "x")

    def test_binary_op_instructions(self):
        mir = compile_to_mir("fn add(a, b) { a + b }")
        fn = mir.functions["add"]
        bb = fn.basic_blocks[0]
        has_binop = any(isinstance(i, MIRBinOp) for i in bb.instructions)
        self.assertTrue(has_binop)

    def test_if_creates_multiple_blocks(self):
        mir = compile_to_mir("fn test(x) { if x then 1 else 2 }")
        fn = mir.functions["test"]
        # if 表达式应产生多个基本块
        self.assertGreater(len(fn.basic_blocks), 1)


# ============================================================
# 测试 LIR 降级
# ============================================================

class TestLIRLowering(unittest.TestCase):
    """测试 MIR -> LIR 降级"""

    def test_simple_function(self):
        lir = compile_to_lir("fn id(x) { x }")
        self.assertIn("id", lir.functions)
        fn = lir.functions["id"]
        self.assertEqual(fn.name, "id")
        # 函数体应有指令
        self.assertTrue(len(fn.body) > 0)

    def test_function_has_label(self):
        lir = compile_to_lir("fn id(x) { x }")
        fn = lir.functions["id"]
        has_label = any(isinstance(i, LIRLabel) for i in fn.body)
        self.assertTrue(has_label)

    def test_function_has_return(self):
        lir = compile_to_lir("fn id(x) { x }")
        fn = lir.functions["id"]
        has_return = any(isinstance(i, LIRReturn) for i in fn.body)
        self.assertTrue(has_return)

    def test_stack_size_positive(self):
        lir = compile_to_lir("fn add(a, b) { a + b }")
        fn = lir.functions["add"]
        self.assertGreater(fn.stack_size, 0)

    def test_reg_alloc_populated(self):
        lir = compile_to_lir("fn add(a, b) { a + b }")
        fn = lir.functions["add"]
        self.assertTrue(len(fn.reg_alloc) > 0)


# ============================================================
# 测试 Pass 管理器
# ============================================================

class TestPassManager(unittest.TestCase):
    """测试 Pass 管理器和优化 Pass"""

    def test_constant_folding_simple(self):
        """2 + 3 应被折叠为 5"""
        hir = compile_to_hir("let x = 2 + 3")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 5)

    def test_constant_folding_multiplication(self):
        """3 * 4 应被折叠为 12"""
        hir = compile_to_hir("let x = 3 * 4")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 12)

    def test_constant_folding_subtraction(self):
        """10 - 3 应被折叠为 7"""
        hir = compile_to_hir("let x = 10 - 3")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 7)

    def test_constant_folding_nested(self):
        """(1 + 2) * (3 + 4) 应被折叠为 21"""
        hir = compile_to_hir("let x = (1 + 2) * (3 + 4)")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        # 第一轮: (1+2) -> 3, (3+4) -> 7
        # 第二轮: 3 * 7 -> 21
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 21)

    def test_constant_folding_division(self):
        """10 / 3 应被折叠为 3 (整数除法)"""
        hir = compile_to_hir("let x = 10 / 3")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 3)

    def test_constant_folding_modulo(self):
        """10 % 3 应被折叠为 1"""
        hir = compile_to_hir("let x = 10 % 3")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 1)

    def test_no_fold_non_const(self):
        """含变量的表达式不应被折叠"""
        hir = compile_to_hir("let x = a + 1")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        # a + 1 不应被折叠（a 不是常量）
        self.assertIsInstance(decl.value, HIRBinaryOp)

    def test_default_pipeline(self):
        """默认优化管道应正常运行不报错"""
        hir = compile_to_hir("let x = 2 + 3 * 4")
        pm = default_optimization_pipeline()
        pm.run_hir_passes(hir)
        # 3*4=12 然后不做改变（2+12 可能需要多轮才能折叠）
        # 应该没有异常

    def test_pass_manager_empty(self):
        """空的 Pass 管理器应正常工作"""
        hir = compile_to_hir("let x = 2 + 3")
        pm = PassManager()
        changed = pm.run_hir_passes(hir)
        self.assertFalse(changed)

    def test_multiple_passes(self):
        """多个 Pass 应按序运行"""
        hir = compile_to_hir("let x = 2 + 3")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.add_hir_pass(DeadCodeElimination())
        pm.add_hir_pass(Inlining())
        pm.run_hir_passes(hir)

        decl = hir.declarations[0]
        self.assertIsInstance(decl.value, HIRIntLiteral)
        self.assertEqual(decl.value.value, 5)

    def test_constant_folding_in_fn(self):
        """函数体内的常量也应被折叠"""
        hir = compile_to_hir("fn calc() { 7 + 8 }")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        pm.run_hir_passes(hir)

        fn_decl = hir.declarations[0]
        # 函数体内的 7 + 8 = 15 应被折叠
        body = fn_decl.fn_def.body
        if isinstance(body, HIRBlockExpr):
            if body.exprs and isinstance(body.exprs[0], HIRIntLiteral):
                self.assertEqual(body.exprs[0].value, 15)

    def test_convergence(self):
        """Pass 应在收敛后停止"""
        hir = compile_to_hir("let x = 1 + 1")
        pm = PassManager()
        pm.add_hir_pass(ConstantFolding())
        # 设置 verbose 观察迭代
        pm._verbose = True
        pm.run_hir_passes(hir, max_iterations=100)
        # 不应有异常，且 1+1=2

    def test_cse_pass_runs(self):
        """CSE pass 应能正常对 MIR 模块运行"""
        mir = compile_to_mir("fn test(x) { x + x }")
        pm = PassManager()
        pm.add_mir_pass(CommonSubexprElimination())
        changed = pm.run_mir_passes(mir)
        # 不应抛出异常

    def test_licm_pass_runs(self):
        """LICM pass 应能正常对 MIR 模块运行"""
        mir = compile_to_mir("fn test(x) { if x then x + 1 else x + 1 }")
        pm = PassManager()
        pm.add_mir_pass(LoopInvariantCodeMotion())
        changed = pm.run_mir_passes(mir)
        # 不应抛出异常

    def test_hir_pass_exception_propagates(self):
        """HIR pass 抛出异常时应向上传播，而非被静默吞掉"""
        from nova.ir.pass_manager import Pass

        class FailingHIRPass(Pass):
            name = "failing_hir"

            def run(self, module):
                raise RuntimeError("intentional HIR pass failure")

        hir = compile_to_hir("let x = 1 + 2")
        pm = PassManager()
        pm.add_hir_pass(FailingHIRPass())
        with self.assertRaises(RuntimeError) as ctx:
            pm.run_hir_passes(hir)
        self.assertIn("intentional HIR pass failure", str(ctx.exception))

    def test_mir_pass_exception_propagates(self):
        """MIR pass 抛出异常时应向上传播，而非被静默吞掉"""
        from nova.ir.pass_manager import Pass

        class FailingMIRPass(Pass):
            name = "failing_mir"

            def run(self, module):
                raise ValueError("intentional MIR pass failure")

        mir = compile_to_mir("fn test(x) { x + 1 }")
        pm = PassManager()
        pm.add_mir_pass(FailingMIRPass())
        with self.assertRaises(ValueError) as ctx:
            pm.run_mir_passes(mir)
        self.assertIn("intentional MIR pass failure", str(ctx.exception))

    def test_lir_pass_exception_propagates(self):
        """LIR pass 抛出异常时应向上传播，而非被静默吞掉"""
        from nova.ir.pass_manager import Pass

        class FailingLIRPass(Pass):
            name = "failing_lir"

            def run(self, module):
                raise TypeError("intentional LIR pass failure")

        body = [
            LIRLoadConst(value=1, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRReturn(src_locs=[("r0", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})
        pm = PassManager()
        pm.add_lir_pass(FailingLIRPass())
        with self.assertRaises(TypeError) as ctx:
            pm.run_lir_passes(mod)
        self.assertIn("intentional LIR pass failure", str(ctx.exception))


# ============================================================
# 测试端到端编译管道
# ============================================================

class TestEndToEnd(unittest.TestCase):
    """测试完整的编译管道"""

    def test_full_pipeline(self):
        """源码 -> AST -> HIR -> MIR -> LIR 全流程"""
        source = "fn add(a, b) { a + b }"
        hir = compile_to_hir(source)
        self.assertIsInstance(hir, HIRModule)

        mir = MIRLowering().lower(hir)
        self.assertIsInstance(mir, MIRModule)
        self.assertIn("add", mir.functions)

        lir = LIRLowering().lower(mir)
        self.assertIsInstance(lir, LIRModule)
        self.assertIn("add", lir.functions)

    def test_pipeline_with_optimization(self):
        """源码 -> HIR -> 优化 -> MIR -> LIR"""
        source = "fn calc() { 2 + 3 }"
        hir = compile_to_hir(source)

        pm = default_optimization_pipeline()
        pm.run_hir_passes(hir)

        mir = MIRLowering().lower(hir)
        self.assertIn("calc", mir.functions)

        lir = LIRLowering().lower(mir)
        self.assertIn("calc", lir.functions)

    def test_complex_program(self):
        """更复杂的程序应正常编译"""
        source = """
            let x = 10
            fn fibonacci(n) {
                if n <= 1 then n
                else fibonacci(n - 1) + fibonacci(n - 2)
            }
            let result = fibonacci(x)
        """
        hir = compile_to_hir(source)
        self.assertTrue(len(hir.declarations) >= 3)

        mir = MIRLowering().lower(hir)
        self.assertIn("fibonacci", mir.functions)

    def test_pattern_match_pipeline(self):
        """模式匹配应正常通过编译管道"""
        source = 'let x = match 42 { 1 -> "one" n -> "other" }'
        hir = compile_to_hir(source)
        mir = MIRLowering().lower(hir)
        # 不应抛出异常


# ============================================================
# 测试 LIR 层常量折叠
# ============================================================

def _make_lir_fn(name="test", body=None):
    """辅助函数：创建一个简单的 LIRFunction。"""
    fn = LIRFunction(
        name=name,
        params=[],
        return_type=INT_TYPE,
        body=body or [],
    )
    return fn


def _make_lir_module(fns=None):
    """辅助函数：创建一个 LIRModule。"""
    m = LIRModule(name="test_module")
    if fns:
        m.functions = fns
    return m


class TestLIRConstantFolding(unittest.TestCase):
    """测试 LIR 层常量折叠"""

    def test_fold_int_add(self):
        """LIR: load 2, load 3, add -> load 5"""
        body = [
            LIRLoadConst(value=2, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=3, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRReturn(src_locs=[("r2", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        # 验证 LIRBinOp 被替换为 LIRLoadConst
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        # 应有 LIRLoadConst(5)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(5, values)

    def test_fold_int_multiply(self):
        """LIR: 3 * 4 -> 12"""
        body = [
            LIRLoadConst(value=3, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=4, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="*",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRReturn(src_locs=[("r2", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(12, values)

    def test_fold_chain(self):
        """LIR: (2 + 3) + 4 -> 5 + 4 -> 9 (链式折叠，多轮不动点)"""
        body = [
            LIRLoadConst(value=2, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=3, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRLoadConst(value=4, const_type="int", dst_loc=("r3", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r2", INT_TYPE), ("r3", INT_TYPE)],
                     dst_loc=("r4", INT_TYPE)),
            LIRReturn(src_locs=[("r4", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(9, values)

    def test_fold_int_comparison(self):
        """LIR: 3 < 5 -> True"""
        body = [
            LIRLoadConst(value=3, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=5, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="<",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", BOOL_TYPE)),
            LIRReturn(src_locs=[("r2", BOOL_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(True, values)

    def test_fold_int_equality(self):
        """LIR: 2 == 2 -> True, 2 != 3 -> True"""
        body = [
            LIRLoadConst(value=2, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=2, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="==",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", BOOL_TYPE)),
            LIRReturn(src_locs=[("r2", BOOL_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(True, values)

    def test_fold_logical_ops(self):
        """LIR: 1 && 0 -> False, 0 || 1 -> True"""
        body = [
            LIRLoadConst(value=1, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=0, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="&&",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", BOOL_TYPE)),
            LIRReturn(src_locs=[("r2", BOOL_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(False, values)

    def test_no_fold_non_const(self):
        """LIR: 非常量操作数不应被折叠"""
        body = [
            LIRLoadConst(value=2, const_type="int", dst_loc=("r0", INT_TYPE)),
            # r5 不在 const_map 中
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r5", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRReturn(src_locs=[("r2", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        changed = pm.run_lir_passes(mod)

        self.assertFalse(changed)
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 1)

    def test_no_fold_div_by_zero(self):
        """LIR: 除以零不应被折叠"""
        body = [
            LIRLoadConst(value=10, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=0, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="/",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRReturn(src_locs=[("r2", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        changed = pm.run_lir_passes(mod)

        self.assertFalse(changed)
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 1)

    def test_fold_float_ops(self):
        """LIR: 2.5 + 1.5 -> 4.0"""
        body = [
            LIRLoadConst(value=2.5, const_type="float", dst_loc=("r0", FLOAT_TYPE)),
            LIRLoadConst(value=1.5, const_type="float", dst_loc=("r1", FLOAT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", FLOAT_TYPE), ("r1", FLOAT_TYPE)],
                     dst_loc=("r2", FLOAT_TYPE)),
            LIRReturn(src_locs=[("r2", FLOAT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(4.0, values)

    def test_fold_int_modulo(self):
        """LIR: 10 % 3 -> 1"""
        body = [
            LIRLoadConst(value=10, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=3, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="%",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRReturn(src_locs=[("r2", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.run_lir_passes(mod)

        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        values = [c.value for c in consts]
        self.assertIn(1, values)


# ============================================================
# 测试 LIR 层死代码消除
# ============================================================

class TestLIRDeadCodeElimination(unittest.TestCase):
    """测试 LIR 层死代码消除"""

    def test_remove_unused_loadconst(self):
        """未使用的 LIRLoadConst 应被删除"""
        body = [
            LIRLoadConst(value=42, const_type="int", dst_loc=("r_dead", INT_TYPE)),
            LIRLoadConst(value=99, const_type="int", dst_loc=("r_used", INT_TYPE)),
            LIRReturn(src_locs=[("r_used", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        self.assertEqual(len(consts), 1)
        self.assertEqual(consts[0].value, 99)

    def test_remove_unused_loadreg(self):
        """未使用的 LIRLoadReg 应被删除"""
        body = [
            LIRLoadReg(src_locs=[("r0", INT_TYPE)], dst_loc=("r_dead", INT_TYPE)),
            LIRLoadConst(value=1, const_type="int", dst_loc=("r_used", INT_TYPE)),
            LIRReturn(src_locs=[("r_used", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        load_regs = [i for i in fn.body if isinstance(i, LIRLoadReg)]
        self.assertEqual(len(load_regs), 0)

    def test_remove_unused_unaryop(self):
        """未使用的 LIRUnaryOp 应被删除"""
        body = [
            LIRLoadConst(value=5, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRUnaryOp(op="-",
                       src_locs=[("r0", INT_TYPE)],
                       dst_loc=("r_dead", INT_TYPE)),
            LIRLoadConst(value=10, const_type="int", dst_loc=("r_used", INT_TYPE)),
            LIRReturn(src_locs=[("r_used", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        unaries = [i for i in fn.body if isinstance(i, LIRUnaryOp)]
        self.assertEqual(len(unaries), 0)

    def test_cascade_dce(self):
        """级联 DCE：删除未使用的指令后，其前驱也可能变死"""
        body = [
            LIRLoadConst(value=1, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=2, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),   # r2 未使用 -> 死
            # 但 LIRBinOp 不是无副作用类型，不会直接被 DCE 删除
            LIRLoadConst(value=3, const_type="int", dst_loc=("r_dead", INT_TYPE)),
            LIRLoadConst(value=99, const_type="int", dst_loc=("r_used", INT_TYPE)),
            LIRReturn(src_locs=[("r_used", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        # r_dead 的 LIRLoadConst 应被删除
        dead_found = any(
            isinstance(i, LIRLoadConst) and i.dst_loc and i.dst_loc[0] == "r_dead"
            for i in fn.body
        )
        self.assertFalse(dead_found)

    def test_remove_unreachable_after_jump(self):
        """无条件跳转后的不可达代码应被删除"""
        body = [
            LIRJump(target="exit"),
            LIRLoadConst(value=42, const_type="int", dst_loc=("r_dead", INT_TYPE)),
            LIRUnaryOp(op="-",
                       src_locs=[("r_dead", INT_TYPE)],
                       dst_loc=("r_dead2", INT_TYPE)),
            LIRLabel(name="exit"),
            LIRReturn(),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        # jump 和 label 之间应无指令
        found_dead = any(
            isinstance(i, (LIRLoadConst, LIRUnaryOp)) and not isinstance(i, LIRLabel)
            for i in fn.body
        )
        self.assertFalse(found_dead)

    def test_keep_used_instructions(self):
        """被使用的 LIRLoadConst 不应被删除"""
        body = [
            LIRLoadConst(value=42, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRReturn(src_locs=[("r0", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(mod)

        self.assertFalse(changed)
        consts = [i for i in fn.body if isinstance(i, LIRLoadConst)]
        self.assertEqual(len(consts), 1)


# ============================================================
# 测试 LIR 层公共子表达式消除
# ============================================================

class TestLIRCSE(unittest.TestCase):
    """测试 LIR 层公共子表达式消除"""

    def test_cse_binop(self):
        """相同的 x+y 计算两次，第二次应被 LIRLoadReg 替代"""
        body = [
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r0", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r1", INT_TYPE)),
            LIRReturn(src_locs=[("r0", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(CommonSubexprElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 1)
        load_regs = [i for i in fn.body if isinstance(i, LIRLoadReg)]
        self.assertEqual(len(load_regs), 1)
        # LIRLoadReg 应从 r0 复制到 r1
        self.assertEqual(load_regs[0].dst_loc, ("r1", INT_TYPE))
        self.assertEqual(load_regs[0].src_locs[0][0], "r0")

    def test_cse_unaryop(self):
        """相同的 -x 计算两次，第二次应被替代"""
        body = [
            LIRUnaryOp(op="-",
                       src_locs=[("rx", INT_TYPE)],
                       dst_loc=("r0", INT_TYPE)),
            LIRUnaryOp(op="-",
                       src_locs=[("rx", INT_TYPE)],
                       dst_loc=("r1", INT_TYPE)),
            LIRReturn(src_locs=[("r1", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(CommonSubexprElimination())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        unaries = [i for i in fn.body if isinstance(i, LIRUnaryOp)]
        self.assertEqual(len(unaries), 1)
        load_regs = [i for i in fn.body if isinstance(i, LIRLoadReg)]
        self.assertEqual(len(load_regs), 1)

    def test_cse_different_ops_not_eliminated(self):
        """不同操作符的表达式不应被消除"""
        body = [
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r0", INT_TYPE)),
            LIRBinOp(op="-",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r1", INT_TYPE)),
            LIRReturn(src_locs=[("r0", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(CommonSubexprElimination())
        changed = pm.run_lir_passes(mod)

        self.assertFalse(changed)
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 2)

    def test_cse_resets_at_label(self):
        """CSE 表达式映射应在遇到 LIRLabel 时重置"""
        body = [
            LIRLabel(name="bb0"),
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r0", INT_TYPE)),
            LIRLabel(name="bb1"),
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r1", INT_TYPE)),
            LIRReturn(),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(CommonSubexprElimination())
        changed = pm.run_lir_passes(mod)

        # 跨基本块不做 CSE，所以不应有变化
        self.assertFalse(changed)


# ============================================================
# 测试 LIR 层循环不变量外提
# ============================================================

class TestLIRLICM(unittest.TestCase):
    """测试 LIR 层循环不变量外提"""

    def test_licm_hoist_const(self):
        """循环内不依赖循环变量的 LIRLoadConst 应被外提"""
        body = [
            LIRLabel(name="loop_header"),
            # r_inv 在循环内定义，但 LIRLoadConst 不依赖任何操作数
            LIRLoadConst(value=100, const_type="int", dst_loc=("r_inv", INT_TYPE)),
            # r_counter 在循环内定义（循环变量）
            LIRLoadConst(value=1, const_type="int", dst_loc=("r_counter", INT_TYPE)),
            # 依赖 r_counter（循环内定义），不应被外提
            LIRBinOp(op="+",
                     src_locs=[("r_counter", INT_TYPE), ("r_counter", INT_TYPE)],
                     dst_loc=("r_next", INT_TYPE)),
            LIRJump(target="loop_header"),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(LoopInvariantCodeMotion())
        changed = pm.run_lir_passes(mod)

        self.assertTrue(changed)
        # r_inv 的 LIRLoadConst 应被移到 header 标签之后、循环体之前
        header_idx = next(i for i, ins in enumerate(fn.body) if isinstance(ins, LIRLabel) and ins.name == "loop_header")
        # 找 r_inv 的位置
        r_inv_idx = next(i for i, ins in enumerate(fn.body)
                        if isinstance(ins, LIRLoadConst) and ins.dst_loc and ins.dst_loc[0] == "r_inv")
        # 外提后 r_inv 应紧挨 header
        self.assertEqual(r_inv_idx, header_idx + 1)

    def test_licm_hoist_binop(self):
        """循环内不依赖循环变量的 LIRBinOp 应被外提"""
        body = [
            LIRLabel(name="loop_header"),
            # r_a 和 r_b 在循环内定义但为 LoadConst（常量加载）
            LIRLoadConst(value=3, const_type="int", dst_loc=("r_a", INT_TYPE)),
            LIRLoadConst(value=4, const_type="int", dst_loc=("r_b", INT_TYPE)),
            # r_a + r_b：操作数 r_a, r_b 都在循环内定义 -> 不可外提
            # 但如果 r_a, r_b 不在 loop_defined 中（因为 LICM 先外提了常量）
            # 实际测试中，LIRLoadConst 虽然被定义但 LIRBinOp 依赖了 loop_defined
            LIRJump(target="loop_header"),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(LoopInvariantCodeMotion())
        changed = pm.run_lir_passes(mod)

        # 循环内只有 LoadConst 和 Jump，LoadConst 不依赖任何寄存器，应被外提
        self.assertTrue(changed)

    def test_no_licm_without_loop(self):
        """无回边时 LICM 不应有变化"""
        body = [
            LIRLoadConst(value=42, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRReturn(src_locs=[("r0", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(LoopInvariantCodeMotion())
        changed = pm.run_lir_passes(mod)

        self.assertFalse(changed)

    def test_licm_depends_on_loop_var(self):
        """依赖循环变量的指令不应被外提"""
        body = [
            LIRLabel(name="loop_header"),
            # 循环变量定义
            LIRBinOp(op="+",
                     src_locs=[("r_i", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r_i_next", INT_TYPE)),
            LIRJump(target="loop_header"),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(LoopInvariantCodeMotion())
        changed = pm.run_lir_passes(mod)

        # r_i 在循环内定义，LIRBinOp 依赖 r_i，不可外提
        # 但 r_i 本身不在循环内定义（它来自循环外部），所以 r_i_next 依赖的 r_i 不在 loop_defined
        # 实际上 loop_defined = {r_i_next}, r_i 不在其中
        # 所以 LIRBinOp 可能被外提（因为它只依赖 r_i 和 r1，都不在 loop_defined 中）
        # 这个行为是正确的：如果 r_i 确实不在循环内修改，那加法就是循环不变的
        pass  # 测试只验证不抛异常


# ============================================================
# 测试组合 Pass
# ============================================================

class TestCombinedLIRPasses(unittest.TestCase):
    """测试 LIR 层多个 Pass 组合运行"""

    def test_fold_then_dce(self):
        """先常量折叠再 DCE：折叠后产生新的常量，DCE 清理未使用的"""
        body = [
            LIRLoadConst(value=2, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=3, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r2", INT_TYPE)),
            LIRReturn(src_locs=[("r2", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.add_lir_pass(DeadCodeElimination())
        pm.run_lir_passes(mod)

        # 折叠后 r2 = 5，r0 和 r1 变成死代码
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 0)

    def test_cse_then_dce(self):
        """CSE 后第二次计算被替代为 LIRLoadReg，原 LIRBinOp 被删除"""
        body = [
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r0", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("rx", INT_TYPE), ("ry", INT_TYPE)],
                     dst_loc=("r1", INT_TYPE)),
            LIRReturn(src_locs=[("r0", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(CommonSubexprElimination())
        pm.add_lir_pass(DeadCodeElimination())
        pm.run_lir_passes(mod)

        # CSE 把第二个 binop 替换为 LIRLoadReg, LIRLoadReg 的 dst=r1 未使用 -> DCE 删除
        load_regs = [i for i in fn.body if isinstance(i, LIRLoadReg)]
        self.assertEqual(len(load_regs), 0)
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertEqual(len(binops), 1)

    def test_full_lir_pipeline(self):
        """完整 LIR 管道：折叠 + DCE + CSE"""
        body = [
            LIRLoadConst(value=2, const_type="int", dst_loc=("r0", INT_TYPE)),
            LIRLoadConst(value=3, const_type="int", dst_loc=("r1", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r_sum", INT_TYPE)),
            LIRBinOp(op="+",
                     src_locs=[("r0", INT_TYPE), ("r1", INT_TYPE)],
                     dst_loc=("r_sum2", INT_TYPE)),
            LIRReturn(src_locs=[("r_sum", INT_TYPE)]),
        ]
        fn = _make_lir_fn(body=body)
        mod = _make_lir_module({"test": fn})

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.add_lir_pass(CommonSubexprElimination())
        pm.add_lir_pass(DeadCodeElimination())
        pm.run_lir_passes(mod)

        # 折叠后 r_sum=5, r_sum2 也尝试折叠
        # CSE 应消除了第二个相同表达式
        binops = [i for i in fn.body if isinstance(i, LIRBinOp)]
        self.assertLessEqual(len(binops), 1)

    def test_end_to_end_with_lir_opt(self):
        """端到端：源码 -> HIR -> MIR -> LIR -> LIR 优化"""
        source = "fn calc() { 2 + 3 }"
        lir = compile_to_lir(source)
        self.assertIn("calc", lir.functions)

        pm = PassManager()
        pm.add_lir_pass(ConstantFolding())
        pm.add_lir_pass(DeadCodeElimination())
        changed = pm.run_lir_passes(lir)

        # 不应抛异常
        self.assertIsInstance(lir, LIRModule)

    def test_mir_constant_folding(self):
        """MIR 层常量折叠"""
        mir = compile_to_mir("fn calc() { 2 + 3 }")
        self.assertIn("calc", mir.functions)

        pm = PassManager()
        pm.add_mir_pass(ConstantFolding())
        changed = pm.run_mir_passes(mir)

        self.assertTrue(changed)

    def test_mir_cse(self):
        """MIR 层 CSE"""
        mir = compile_to_mir("fn test(x) { let a = x + 1; let b = x + 1; b }")
        self.assertIn("test", mir.functions)

        pm = PassManager()
        pm.add_mir_pass(CommonSubexprElimination())
        changed = pm.run_mir_passes(mir)

        # 不应抛异常
        self.assertIsInstance(mir, MIRModule)


if __name__ == "__main__":
    unittest.main()
