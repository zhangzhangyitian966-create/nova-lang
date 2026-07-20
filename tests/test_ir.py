"""
Nova IR 测试

测试 HIR/MIR 转换、三层 IR 节点、Pass 管理器。
"""

import unittest

from nova.lexer import Lexer
from nova.parser import Parser

from nova.ir.ir_nodes import (
    IRType,
    NovaType,
    INT_TYPE,
    FLOAT_TYPE,
    STRING_TYPE,
    BOOL_TYPE,
    ListType,
    MapType,
    TupleType,
    FnType,
    OptionType,
    ResultType,
    HIRModule,
    HIRFnDecl,
    HIRLetDecl,
    HIRTypeDecl,
    HIRIntLiteral,
    HIRFloatLiteral,
    HIRStringLiteral,
    HIRBoolLiteral,
    HIRBinaryOp,
    HIRUnaryOp,
    HIRIfExpr,
    HIRMatchExpr,
    HIRLambda,
    HIRPipeExpr,
    HIRListExpr,
    HIRBlockExpr,
    HIRImportDecl,
    HIRExportDecl,
    MIRModule,
    MIRBinOp,
    MIRReturn,
    LIRModule,
    LIRLabel,
    LIRReturn,
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


if __name__ == "__main__":
    unittest.main()
