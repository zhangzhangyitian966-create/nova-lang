# -*- coding: utf-8 -*-
"""
AST 节点单元测试（tests/test_ast_nodes.py 缺口补齐 SH-1 P0）

覆盖范围：
  - Span 位置信息（行号/列号 + repr/equality）
  - 7 种字面量节点（Int/Float/String/Char/Bool/Unit）
  - Identifier 标识符节点
  - 表达式节点：BinaryOp / UnaryOp / PipeExpr / TryExpr
  - 函数定义与调用：Param / Lambda / FnDef / FnCall
  - 绑定与赋值：LetBinding / MutBinding / Assignment
  - 控制流：IfExpr / ForExpr / WhileExpr / BreakExpr / ContinueExpr
  - 模式匹配：MatchArm / MatchExpr + 10 种 Pattern* 节点
  - 复合表达式：ListExpr / ListComprehension / TupleExpr / MapExpr / FieldAccess
  - 顶层声明：Block / ImportDecl / ExportDecl / TypeDef / VariantDef / AliasDef / Program
  - AST Types：TypeInt / TypeFloat / TypeString / TypeBool / TypeChar / TypeUnit /
               TypeIdentifier / TypeGeneric / TypeTuple / TypeFn
"""

import unittest

from nova.ast_nodes import (
    # Position
    Span,
    # Literals
    IntLiteral, FloatLiteral, StringLiteral, CharLiteral, BoolLiteral, UnitLiteral,
    # Identifier
    Identifier,
    # Expressions
    BinaryOp, UnaryOp, PipeExpr, TryExpr,
    # Function
    Param, Lambda, FnDef, FnCall,
    # Bindings
    LetBinding, MutBinding, Assignment,
    # Control flow
    IfExpr, ForExpr, WhileExpr, BreakExpr, ContinueExpr, ErrorExpr,
    # Match
    MatchArm, MatchExpr,
    # Patterns
    PatternWildcard, PatternInt, PatternFloat, PatternString, PatternBool,
    PatternChar, PatternIdentifier, PatternConstructor, PatternTuple, PatternList,
    # Compound
    ListExpr, ListComprehension, TupleExpr, MapExpr, FieldAccess,
    # Declarations
    Block, ImportDecl, ExportDecl, TypeDef, VariantDef, AliasDef, Program,
    # AST-level type annotations
    TypeInt, TypeFloat, TypeString, TypeBool, TypeChar, TypeUnit,
    TypeIdentifier, TypeGeneric, TypeTuple, TypeFn,
)


class TestSpan(unittest.TestCase):
    """源代码位置信息 Span"""

    def test_span_basic_fields(self):
        """测试 Span 基本字段：line=5, column=12"""
        s = Span(line=5, column=12)
        self.assertEqual(s.line, 5)
        self.assertEqual(s.column, 12)

    def test_span_equality(self):
        """测试 Span 值相等：两个同 line/column 的 Span 应相等"""
        self.assertEqual(Span(1, 1), Span(1, 1))
        self.assertNotEqual(Span(1, 2), Span(1, 3))

    def test_span_repr_diagnostic(self):
        """测试 Span repr 包含行号列号可用于诊断"""
        s = Span(line=7, column=3)
        r = repr(s)
        self.assertIn("7", r)
        self.assertIn("3", r)


class TestLiterals(unittest.TestCase):
    """7 种字面量节点"""

    def test_int_literal(self):
        """IntLiteral(42) → value=42, span=None"""
        n = IntLiteral(value=42)
        self.assertEqual(n.value, 42)
        self.assertIsNone(n.span)

    def test_int_literal_with_span(self):
        """IntLiteral(7, span) → span 应可保留"""
        s = Span(1, 1)
        n = IntLiteral(value=7, span=s)
        self.assertIs(n.span, s)

    def test_float_literal(self):
        """FloatLiteral(3.14) → value=3.14"""
        self.assertAlmostEqual(FloatLiteral(3.14).value, 3.14, places=5)

    def test_string_literal(self):
        """StringLiteral('hello') → value='hello'"""
        self.assertEqual(StringLiteral("hello").value, "hello")

    def test_char_literal_single_char(self):
        """CharLiteral 只能放单个字符"""
        c = CharLiteral(value="x")
        self.assertEqual(c.value, "x")
        self.assertEqual(len(c.value), 1)

    def test_bool_literal_true(self):
        """BoolLiteral(True) / BoolLiteral(False)"""
        self.assertTrue(BoolLiteral(value=True).value)
        self.assertFalse(BoolLiteral(value=False).value)

    def test_unit_literal_no_args(self):
        """UnitLiteral 即 ()，无需 value 字段"""
        u = UnitLiteral()
        self.assertIsNone(u.span)
        # repr 应包含 'Unit' 字样
        self.assertIn("Unit", repr(u))


class TestIdentifier(unittest.TestCase):
    """标识符节点"""

    def test_identifier_name(self):
        """Identifier('foo').name == 'foo'"""
        ident = Identifier(name="foo")
        self.assertEqual(ident.name, "foo")

    def test_identifier_inequality(self):
        """不同名称的 Identifier 不相等"""
        self.assertNotEqual(Identifier("a"), Identifier("b"))


class TestOperatorExpressions(unittest.TestCase):
    """BinaryOp / UnaryOp / PipeExpr / TryExpr"""

    def test_binary_op_plus(self):
        """BinaryOp('+', a, b) → 字段正确保留"""
        a = IntLiteral(1)
        b = IntLiteral(2)
        expr = BinaryOp(op="+", left=a, right=b)
        self.assertEqual(expr.op, "+")
        self.assertIs(expr.left, a)
        self.assertIs(expr.right, b)

    def test_unary_op_minus(self):
        """UnaryOp('-', x) → 负号操作"""
        x = IntLiteral(5)
        expr = UnaryOp(op="-", operand=x)
        self.assertEqual(expr.op, "-")
        self.assertIs(expr.operand, x)

    def test_pipe_expr(self):
        """PipeExpr(x, f) → x |> f"""
        x = Identifier("x")
        f = Identifier("double")
        p = PipeExpr(left=x, right=f)
        self.assertIs(p.left, x)
        self.assertIs(p.right, f)

    def test_try_expr(self):
        """TryExpr(e) → 错误传播 ?"""
        e = Identifier("opt")
        t = TryExpr(expr=e)
        self.assertIs(t.expr, e)


class TestFunctionNodes(unittest.TestCase):
    """Param / Lambda / FnDef / FnCall"""

    def test_param_defaults(self):
        """Param(name='x') → type_annotation=None"""
        p = Param(name="x")
        self.assertEqual(p.name, "x")
        self.assertIsNone(p.type_annotation)

    def test_lambda_body(self):
        """Lambda([Param('a')], body) → 字段保留"""
        body = Identifier("a")
        lam = Lambda(params=[Param("a")], body=body)
        self.assertEqual(len(lam.params), 1)
        self.assertIs(lam.body, body)

    def test_fn_def_basic(self):
        """FnDef('f', [Param], ret_ann, body)"""
        fn = FnDef(
            name="f",
            params=[Param("x")],
            return_type=None,
            body=Identifier("x"),
        )
        self.assertEqual(fn.name, "f")
        self.assertEqual(len(fn.params), 1)

    def test_fn_call_args(self):
        """FnCall(callee, [arg1, arg2])"""
        callee = Identifier("add")
        args = [IntLiteral(1), IntLiteral(2)]
        call = FnCall(callee=callee, args=args)
        self.assertIs(call.callee, callee)
        self.assertEqual(len(call.args), 2)


class TestBindings(unittest.TestCase):
    """LetBinding / MutBinding / Assignment"""

    def test_let_immutable(self):
        """LetBinding('x', value=42) 是不可变绑定"""
        b = LetBinding(name="x", value=IntLiteral(42))
        self.assertEqual(b.name, "x")
        self.assertIsNone(b.type_annotation)

    def test_mut_mutable(self):
        """MutBinding('y', value=0) 是可变绑定"""
        b = MutBinding(name="y", value=IntLiteral(0))
        self.assertEqual(b.name, "y")
        self.assertIsNone(b.type_annotation)

    def test_assignment_target(self):
        """Assignment(name='x', value=100) → 赋值语句"""
        v = IntLiteral(100)
        a = Assignment(name="x", value=v)
        self.assertEqual(a.name, "x")
        self.assertIs(a.value, v)


class TestControlFlow(unittest.TestCase):
    """IfExpr / ForExpr / WhileExpr / BreakExpr / ContinueExpr"""

    def test_if_three_branches(self):
        """IfExpr(cond, then, else_) 三字段"""
        ife = IfExpr(
            condition=BoolLiteral(True),
            then_branch=IntLiteral(1),
            else_branch=IntLiteral(2),
        )
        self.assertIsNotNone(ife.condition)
        self.assertIsNotNone(ife.then_branch)
        self.assertIsNotNone(ife.else_branch)

    def test_for_expr_fields(self):
        """ForExpr(var_name='i', iterable, body)"""
        f = ForExpr(
            var_name="i",
            iterable=Identifier("xs"),
            body=Identifier("i"),
        )
        self.assertEqual(f.var_name, "i")

    def test_while_condition(self):
        """WhileExpr(cond, body)"""
        w = WhileExpr(condition=BoolLiteral(True), body=IntLiteral(0))
        self.assertIsNotNone(w.condition)
        self.assertIsNotNone(w.body)

    def test_break_continue_no_fields(self):
        """BreakExpr / ContinueExpr 构造无参即可"""
        self.assertIsNone(BreakExpr().span)
        self.assertIsNone(ContinueExpr().span)


class TestMatchAndPatterns(unittest.TestCase):
    """MatchArm / MatchExpr + 10 种 Pattern*"""

    def test_wildcard(self):
        """PatternWildcard 即 _"""
        self.assertIsNotNone(PatternWildcard())

    def test_literal_patterns(self):
        """PatternInt/Float/String/Bool/Char → 保留 value"""
        self.assertEqual(PatternInt(5).value, 5)
        self.assertAlmostEqual(PatternFloat(1.5).value, 1.5)
        self.assertEqual(PatternString("s").value, "s")
        self.assertTrue(PatternBool(True).value)
        self.assertEqual(PatternChar("c").value, "c")

    def test_pattern_identifier(self):
        """PatternIdentifier('x') → 绑定模式"""
        self.assertEqual(PatternIdentifier(name="x").name, "x")

    def test_pattern_constructor(self):
        """PatternConstructor('Some', fields=[p])"""
        inner = PatternIdentifier(name="x")
        pc = PatternConstructor(name="Some", fields=[inner])
        self.assertEqual(pc.name, "Some")
        self.assertEqual(len(pc.fields), 1)

    def test_pattern_tuple_and_list(self):
        """PatternTuple / PatternList → elements 列表"""
        p1 = PatternInt(1)
        p2 = PatternInt(2)
        self.assertEqual(len(PatternTuple(elements=[p1, p2]).elements), 2)
        self.assertEqual(len(PatternList(elements=[p1, p2]).elements), 2)

    def test_match_expr(self):
        """MatchExpr(subject=x, arms=[MatchArm(pat, expr)])"""
        arm = MatchArm(pattern=PatternWildcard(), body=IntLiteral(0))
        m = MatchExpr(subject=Identifier("x"), arms=[arm])
        self.assertEqual(len(m.arms), 1)


class TestCompoundExpressions(unittest.TestCase):
    """ListExpr / ListComprehension / TupleExpr / MapExpr / FieldAccess / Block"""

    def test_list_expr_elements(self):
        """ListExpr([1,2,3]) → elements.length == 3"""
        elems = [IntLiteral(1), IntLiteral(2), IntLiteral(3)]
        l = ListExpr(elements=elems)
        self.assertEqual(len(l.elements), 3)

    def test_list_comprehension_required_fields(self):
        """ListComprehension(expr, var_name, iterable)"""
        lc = ListComprehension(
            expr=Identifier("x"),
            var_name="x",
            iterable=Identifier("xs"),
            filter_cond=None,
        )
        self.assertEqual(lc.var_name, "x")
        self.assertIsNone(lc.filter_cond)

    def test_tuple_expr(self):
        """TupleExpr([a,b])"""
        t = TupleExpr(elements=[IntLiteral(1), Identifier("x")])
        self.assertEqual(len(t.elements), 2)

    def test_map_expr_pairs(self):
        """MapExpr(pairs=[(k,v)])"""
        pairs = [(StringLiteral("a"), IntLiteral(1))]
        m = MapExpr(pairs=pairs)
        self.assertEqual(len(m.pairs), 1)

    def test_field_access(self):
        """FieldAccess(target=rec, field='x')"""
        fa = FieldAccess(target=Identifier("rec"), field="x")
        self.assertEqual(fa.field, "x")

    def test_block_statements(self):
        """Block([stmt1, stmt2]) → statements"""
        s1 = LetBinding(name="a", value=IntLiteral(1))
        s2 = Identifier("a")
        b = Block(statements=[s1, s2])
        self.assertEqual(len(b.statements), 2)
        self.assertIsNone(b.tail_expression)


class TestDeclarations(unittest.TestCase):
    """ImportDecl / ExportDecl / TypeDef / VariantDef / AliasDef / Program"""

    def test_import_decl(self):
        """ImportDecl(module_name='std.list')"""
        self.assertEqual(ImportDecl(module_name="std.list").module_name, "std.list")

    def test_export_decl(self):
        """ExportDecl(name='x')"""
        self.assertEqual(ExportDecl(name="x").name, "x")

    def test_variant_def(self):
        """VariantDef('None', fields=[]) / VariantDef('Some', fields=[(name, Type)])"""
        v0 = VariantDef(name="None", fields=[])
        v1 = VariantDef(name="Some", fields=[("value", TypeInt())])
        self.assertEqual(v0.name, "None")
        self.assertEqual(len(v1.fields), 1)
        self.assertEqual(v1.fields[0][0], "value")

    def test_type_def_variants(self):
        """TypeDef('Option', [Variant('None'), Variant('Some', [T])])"""
        td = TypeDef(
            name="Option",
            variants=[
                VariantDef("None", fields=[]),
                VariantDef("Some", fields=[("value", TypeIdentifier("T"))]),
            ],
        )
        self.assertEqual(td.name, "Option")
        self.assertEqual(len(td.variants), 2)

    def test_alias_def(self):
        """AliasDef('Age', target_type=TypeInt())"""
        a = AliasDef(name="Age", target_type=TypeInt())
        self.assertEqual(a.name, "Age")
        self.assertIsInstance(a.target_type, TypeInt)

    def test_program_declarations(self):
        """Program([decls...])"""
        p = Program(declarations=[
            ImportDecl(module_name="std.list"),
            FnDef(name="main", params=[], return_type=None, body=IntLiteral(0)),
        ])
        self.assertEqual(len(p.declarations), 2)


class TestAstTypeAnnotations(unittest.TestCase):
    """AST 层 10 种 Type* 注解节点"""

    def test_primitive_types_no_params(self):
        """TypeInt / TypeFloat / TypeString / TypeBool / TypeChar / TypeUnit 零参"""
        self.assertIsNotNone(TypeInt())
        self.assertIsNotNone(TypeFloat())
        self.assertIsNotNone(TypeString())
        self.assertIsNotNone(TypeBool())
        self.assertIsNotNone(TypeChar())
        self.assertIsNotNone(TypeUnit())

    def test_type_identifier(self):
        """TypeIdentifier('Foo') → name='Foo'"""
        self.assertEqual(TypeIdentifier(name="Foo").name, "Foo")

    def test_type_generic(self):
        """TypeGeneric(base='List', params=[TypeInt()]) → List[Int]"""
        tg = TypeGeneric(base="List", params=[TypeInt()])
        self.assertEqual(tg.base, "List")
        self.assertEqual(len(tg.params), 1)

    def test_type_tuple(self):
        """TypeTuple([Int, String])"""
        tt = TypeTuple(elements=[TypeInt(), TypeString()])
        self.assertEqual(len(tt.elements), 2)

    def test_type_fn(self):
        """TypeFn(param_types=[Int, Int], return_type=Bool) → (Int, Int) -> Bool"""
        tf = TypeFn(param_types=[TypeInt(), TypeInt()], return_type=TypeBool())
        self.assertEqual(len(tf.param_types), 2)
        self.assertIsInstance(tf.return_type, TypeBool)


if __name__ == "__main__":
    unittest.main()
