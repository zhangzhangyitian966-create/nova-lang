"""
TypeChecker 单元测试基线

覆盖类型合一核心算法、泛型实例化、基本表达式类型检查等核心路径。
"""

import unittest

from nova.ast_nodes import (
    BinaryOp,
    BoolLiteral,
    CharLiteral,
    FloatLiteral,
    Identifier,
    IfExpr,
    IntLiteral,
    ListExpr,
    MatchArm,
    MatchExpr,
    PatternBool,
    PatternConstructor,
    PatternFloat,
    PatternIdentifier,
    PatternInt,
    PatternList,
    PatternString,
    PatternTuple,
    PatternWildcard,
    Span,
    StringLiteral,
    UnitLiteral,
)
from nova.type_checker import (
    ADTType,
    BOOL_T,
    CHAR_T,
    FLOAT_T,
    FnType,
    INT_T,
    ListType,
    MapType,
    STRING_T,
    TupleType,
    TypeChecker,
    TypeVar,
    UNIT_T,
)


class TestUnification(unittest.TestCase):
    """类型合一 (_unify) 核心算法测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def test_unify_same_primitive(self):
        """合一相同基本类型应成功"""
        self.assertTrue(self.tc._unify(INT_T, INT_T))

    def test_unify_different_primitive(self):
        """合一不同基本类型应失败"""
        self.assertFalse(self.tc._unify(INT_T, BOOL_T))

    def test_unify_typevar_with_primitive(self):
        """类型变量与基本类型合一应成功并绑定"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._unify(tv, INT_T))
        # 通过 _find 验证绑定
        result = self.tc._find(tv)
        self.assertEqual(result, INT_T)

    def test_unify_two_unbound_typevars(self):
        """两个未绑定类型变量合一应成功"""
        tv1 = TypeVar("A")
        tv2 = TypeVar("B")
        self.assertTrue(self.tc._unify(tv1, tv2))
        # 验证 tv1 被绑定到 tv2（或反之）
        root1 = self.tc._find(tv1)
        root2 = self.tc._find(tv2)
        self.assertIs(root1, root2)

    def test_unify_list_same_element(self):
        """合一相同元素类型的列表"""
        self.assertTrue(self.tc._unify(ListType(INT_T), ListType(INT_T)))

    def test_unify_list_different_element(self):
        """合一不同元素类型的列表应失败"""
        self.assertFalse(self.tc._unify(ListType(INT_T), ListType(BOOL_T)))

    def test_unify_tuple_same_length(self):
        """合一相同长度和元素类型的元组"""
        a = TupleType([INT_T, BOOL_T])
        b = TupleType([INT_T, BOOL_T])
        self.assertTrue(self.tc._unify(a, b))

    def test_unify_tuple_different_length(self):
        """合一不同长度的元组应失败"""
        a = TupleType([INT_T])
        b = TupleType([INT_T, BOOL_T])
        self.assertFalse(self.tc._unify(a, b))

    def test_unify_fn_same_signature(self):
        """合一相同签名的函数类型"""
        a = FnType([INT_T], BOOL_T)
        b = FnType([INT_T], BOOL_T)
        self.assertTrue(self.tc._unify(a, b))

    def test_unify_fn_different_params(self):
        """合一不同参数数量的函数类型应失败"""
        a = FnType([INT_T], BOOL_T)
        b = FnType([INT_T, INT_T], BOOL_T)
        self.assertFalse(self.tc._unify(a, b))

    def test_unify_map_same_types(self):
        """合一相同键值类型的 Map"""
        a = MapType(STRING_T, INT_T)
        b = MapType(STRING_T, INT_T)
        self.assertTrue(self.tc._unify(a, b))

    def test_unify_map_different_value(self):
        """合一不同值类型的 Map 应失败"""
        a = MapType(STRING_T, INT_T)
        b = MapType(STRING_T, BOOL_T)
        self.assertFalse(self.tc._unify(a, b))

    def test_unify_adt_same(self):
        """合一相同 ADT 类型"""
        a = ADTType("Option", [INT_T])
        b = ADTType("Option", [INT_T])
        self.assertTrue(self.tc._unify(a, b))

    def test_unify_adt_different_param(self):
        """合一参数不同的 ADT 应失败"""
        a = ADTType("Option", [INT_T])
        b = ADTType("Option", [BOOL_T])
        self.assertFalse(self.tc._unify(a, b))


class TestOccurCheck(unittest.TestCase):
    """发生检查 (_occur_check) 测试 —— 防止无限递归类型"""

    def setUp(self):
        self.tc = TypeChecker()

    def test_occur_in_primitive(self):
        """基本类型中不应出现类型变量"""
        tv = TypeVar("X")
        self.assertFalse(self.tc._occur_check(tv, INT_T))

    def test_occur_in_itself(self):
        """类型变量自身出现应返回 True"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._occur_check(tv, tv))

    def test_occur_in_list(self):
        """类型变量出现在列表元素类型中"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._occur_check(tv, ListType(tv)))

    def test_occur_not_in_list(self):
        """类型变量未出现在列表元素类型中"""
        tv = TypeVar("X")
        self.assertFalse(self.tc._occur_check(tv, ListType(INT_T)))

    def test_occur_in_tuple(self):
        """类型变量出现在元组元素中"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._occur_check(tv, TupleType([INT_T, tv])))

    def test_occur_in_fn_param(self):
        """类型变量出现在函数参数中"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._occur_check(tv, FnType([tv], INT_T)))

    def test_occur_in_fn_return(self):
        """类型变量出现在函数返回类型中"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._occur_check(tv, FnType([INT_T], tv)))

    def test_occur_in_adt_param(self):
        """类型变量出现在 ADT 参数中"""
        tv = TypeVar("X")
        self.assertTrue(self.tc._occur_check(tv, ADTType("Option", [tv])))

    def test_occur_prevents_infinite_type(self):
        """发生检查应阻止 List[X] = X 这类无限类型"""
        tv = TypeVar("X")
        self.assertFalse(self.tc._unify(tv, ListType(tv)))


class TestFindAndPathCompression(unittest.TestCase):
    """_find 与 Union-Find 路径压缩测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def test_find_unbound_typevar(self):
        """未绑定类型变量应返回自身"""
        tv = TypeVar("X")
        result = self.tc._find(tv)
        self.assertIs(result, tv)

    def test_find_bound_typevar(self):
        """绑定后应返回绑定的类型"""
        tv = TypeVar("X")
        self.tc._subst[id(tv)] = INT_T
        result = self.tc._find(tv)
        self.assertEqual(result, INT_T)

    def test_path_compression(self):
        """路径压缩：链式绑定应直接指向根"""
        tv1 = TypeVar("A")
        tv2 = TypeVar("B")
        tv3 = TypeVar("C")
        # 构建链：tv1 -> tv2 -> tv3 -> INT_T
        self.tc._subst[id(tv1)] = tv2
        self.tc._subst[id(tv2)] = tv3
        self.tc._subst[id(tv3)] = INT_T

        result = self.tc._find(tv1)
        self.assertEqual(result, INT_T)
        # 验证路径压缩后 tv1 直接指向 INT_T
        self.assertEqual(self.tc._subst[id(tv1)], INT_T)


class TestInstantiation(unittest.TestCase):
    """泛型实例化 (_instantiate) 测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def test_instantiate_primitive(self):
        """基本类型实例化应返回自身"""
        self.assertEqual(self.tc._instantiate(INT_T), INT_T)

    def test_instantiate_typevar(self):
        """类型变量实例化应生成 fresh TypeVar"""
        tv = TypeVar("T")
        result = self.tc._instantiate(tv)
        self.assertIsInstance(result, TypeVar)
        self.assertIsNot(result, tv)

    def test_instantiate_list(self):
        """列表类型实例化应递归处理元素类型"""
        tv = TypeVar("T")
        lst = ListType(tv)
        result = self.tc._instantiate(lst)
        self.assertIsInstance(result, ListType)
        self.assertIsInstance(result.elem_type, TypeVar)
        self.assertIsNot(result.elem_type, tv)

    def test_instantiate_fn(self):
        """函数类型实例化应递归处理参数和返回类型"""
        tv = TypeVar("T")
        fn = FnType([tv], tv)
        result = self.tc._instantiate(fn)
        self.assertIsInstance(result, FnType)
        self.assertEqual(len(result.param_types), 1)
        self.assertIsInstance(result.param_types[0], TypeVar)
        self.assertIsInstance(result.return_type, TypeVar)
        # 参数和返回的 fresh TypeVar 应不同
        self.assertIsNot(result.param_types[0], tv)
        self.assertIsNot(result.return_type, tv)

    def test_instantiate_tuple(self):
        """元组类型实例化应递归处理所有元素"""
        tv = TypeVar("T")
        tup = TupleType([tv, INT_T])
        result = self.tc._instantiate(tup)
        self.assertIsInstance(result, TupleType)
        self.assertIsInstance(result.elements[0], TypeVar)
        self.assertIsNot(result.elements[0], tv)
        self.assertEqual(result.elements[1], INT_T)

    def test_instantiate_adt(self):
        """ADT 类型实例化应递归处理类型参数"""
        tv = TypeVar("T")
        adt = ADTType("Option", [tv])
        result = self.tc._instantiate(adt)
        self.assertIsInstance(result, ADTType)
        self.assertEqual(result.name, "Option")
        self.assertIsInstance(result.type_params[0], TypeVar)
        self.assertIsNot(result.type_params[0], tv)

    def test_multiple_instantiations_are_independent(self):
        """同一类型多次实例化应产生独立的 TypeVar"""
        tv = TypeVar("T")
        fn = FnType([tv], tv)
        result1 = self.tc._instantiate(fn)
        result2 = self.tc._instantiate(fn)
        self.assertIsNot(result1.param_types[0], result2.param_types[0])
        self.assertIsNot(result1.return_type, result2.return_type)


class TestExprTypeChecking(unittest.TestCase):
    """表达式类型检查 (check_expr) 测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def test_int_literal(self):
        """整数字面量类型应为 Int"""
        ty = self.tc.check_expr(IntLiteral(value=42))
        self.assertEqual(ty, INT_T)

    def test_float_literal(self):
        """浮点数字面量类型应为 Float"""
        ty = self.tc.check_expr(FloatLiteral(value=3.14))
        self.assertEqual(ty, FLOAT_T)

    def test_string_literal(self):
        """字符串字面量类型应为 String"""
        ty = self.tc.check_expr(StringLiteral(value="hello"))
        self.assertEqual(ty, STRING_T)

    def test_bool_literal(self):
        """布尔字面量类型应为 Bool"""
        ty = self.tc.check_expr(BoolLiteral(value=True))
        self.assertEqual(ty, BOOL_T)

    def test_char_literal(self):
        """字符字面量类型应为 Char"""
        ty = self.tc.check_expr(CharLiteral(value="a"))
        self.assertEqual(ty, CHAR_T)

    def test_unit_literal(self):
        """Unit 字面量类型应为 Unit"""
        ty = self.tc.check_expr(UnitLiteral())
        self.assertEqual(ty, UNIT_T)

    def test_arithmetic_binary_op(self):
        """整数加法类型应为 Int"""
        expr = BinaryOp(op="+", left=IntLiteral(1), right=IntLiteral(2))
        ty = self.tc.check_expr(expr)
        self.assertEqual(ty, INT_T)

    def test_comparison_binary_op(self):
        """比较运算类型应为 Bool"""
        expr = BinaryOp(op="<", left=IntLiteral(1), right=IntLiteral(2))
        ty = self.tc.check_expr(expr)
        self.assertEqual(ty, BOOL_T)

    def test_logical_binary_op(self):
        """逻辑运算类型应为 Bool"""
        expr = BinaryOp(op="&&", left=BoolLiteral(True), right=BoolLiteral(False))
        ty = self.tc.check_expr(expr)
        self.assertEqual(ty, BOOL_T)

    def test_if_expr_same_branches(self):
        """if 表达式两个分支类型相同"""
        expr = IfExpr(
            condition=BoolLiteral(True),
            then_branch=IntLiteral(1),
            else_branch=IntLiteral(2),
        )
        ty = self.tc.check_expr(expr)
        self.assertEqual(ty, INT_T)

    def test_list_expr_homogeneous(self):
        """同类型元素列表类型应为 List[Int]"""
        expr = ListExpr(elements=[IntLiteral(1), IntLiteral(2)])
        ty = self.tc.check_expr(expr)
        self.assertIsInstance(ty, ListType)
        self.assertEqual(ty.elem_type, INT_T)

    def test_identifier_lookup(self):
        """环境查找已定义标识符"""
        self.tc.env.define("x", INT_T)
        ty = self.tc.check_expr(Identifier(name="x"))
        self.assertEqual(ty, INT_T)


class TestTypeCheckerBuiltins(unittest.TestCase):
    """内置函数类型签名测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def test_print_builtin(self):
        """print 应为多态函数 (a) -> Unit"""
        ty = self.tc.env.lookup("print")
        self.assertIsInstance(ty, FnType)
        self.assertEqual(len(ty.param_types), 1)
        self.assertIsInstance(ty.param_types[0], TypeVar)
        self.assertEqual(ty.return_type, UNIT_T)

    def test_read_line_builtin(self):
        """read_line 应为 () -> String"""
        ty = self.tc.env.lookup("read_line")
        self.assertIsInstance(ty, FnType)
        self.assertEqual(len(ty.param_types), 0)
        self.assertEqual(ty.return_type, STRING_T)

    def test_str_to_int_builtin(self):
        """str_to_int 应为 (String) -> Option[Int]"""
        ty = self.tc.env.lookup("str_to_int")
        self.assertIsInstance(ty, FnType)
        self.assertEqual(ty.param_types[0], STRING_T)
        self.assertIsInstance(ty.return_type, ADTType)
        self.assertEqual(ty.return_type.name, "Option")

    def test_list_length_builtin(self):
        """list_length 应为 (List[T]) -> Int"""
        ty = self.tc.env.lookup("list_length")
        self.assertIsInstance(ty, FnType)
        self.assertIsInstance(ty.param_types[0], ListType)
        self.assertEqual(ty.return_type, INT_T)


class TestGenericParamCount(unittest.TestCase):
    """泛型参数数量校验测试"""

    def setUp(self):
        from nova.type_checker import TypeChecker

        self.tc = TypeChecker()

    def _from_ast_type_str(self, src: str):
        """从类型表达式字符串解析为 NovaType"""
        from nova.parser import Parser
        from nova.lexer import Lexer

        tokens = Lexer(src).tokenize()
        # 包装为函数参数类型表达式以便解析
        ast = Parser(tokens, source=src).parse()
        # 提取函数声明的参数类型
        fn_decl = ast.body[0]
        return self.tc._from_ast_type(fn_decl.params[0].type_annotation)

    def test_list_correct_arity(self):
        """List[T] 参数数量正确时应通过"""
        ty = self.tc._make_generic_type("List", [INT_T])
        self.assertIsInstance(ty, ListType)

    def test_list_too_few_params(self):
        """List[] 参数数量不足时应报错"""
        with self.assertRaises(Exception) as ctx:
            self.tc._make_generic_type("List", [])
        self.assertIn("List 需要恰好 1 个类型参数", str(ctx.exception))

    def test_list_too_many_params(self):
        """List[Int, String] 参数数量过多时应报错"""
        with self.assertRaises(Exception) as ctx:
            self.tc._make_generic_type("List", [INT_T, STRING_T])
        self.assertIn("List 需要恰好 1 个类型参数", str(ctx.exception))

    def test_map_correct_arity(self):
        """Map[K, V] 参数数量正确时应通过"""
        ty = self.tc._make_generic_type("Map", [STRING_T, INT_T])
        self.assertIsInstance(ty, MapType)

    def test_map_too_few_params(self):
        """Map[Int] 参数数量不足时应报错"""
        with self.assertRaises(Exception) as ctx:
            self.tc._make_generic_type("Map", [INT_T])
        self.assertIn("Map 需要恰好 2 个类型参数", str(ctx.exception))

    def test_option_correct_arity(self):
        """Option[T] 参数数量正确时应通过"""
        ty = self.tc._make_generic_type("Option", [INT_T])
        self.assertIsInstance(ty, ADTType)
        self.assertEqual(ty.name, "Option")

    def test_option_too_many_params(self):
        """Option[Int, String] 参数数量过多时应报错"""
        with self.assertRaises(Exception) as ctx:
            self.tc._make_generic_type("Option", [INT_T, STRING_T])
        self.assertIn("Option 需要恰好 1 个类型参数", str(ctx.exception))

    def test_result_correct_arity(self):
        """Result[T, E] 参数数量正确时应通过"""
        ty = self.tc._make_generic_type("Result", [INT_T, STRING_T])
        self.assertIsInstance(ty, ADTType)
        self.assertEqual(ty.name, "Result")

    def test_result_too_few_params(self):
        """Result[Int] 参数数量不足时应报错"""
        with self.assertRaises(Exception) as ctx:
            self.tc._make_generic_type("Result", [INT_T])
        self.assertIn("Result 需要恰好 2 个类型参数", str(ctx.exception))

    def test_custom_adt_rejects_params(self):
        """自定义 ADT 不支持类型参数"""
        with self.assertRaises(Exception) as ctx:
            self.tc._make_generic_type("Color", [INT_T])
        self.assertIn("'Color' 不支持类型参数", str(ctx.exception))

    def test_custom_adt_no_params(self):
        """自定义 ADT 无类型参数时应通过"""
        ty = self.tc._make_generic_type("Color", [])
        self.assertIsInstance(ty, ADTType)
        self.assertEqual(ty.name, "Color")


# ============================================================
# match 完备性与冗余检测单元测试
# 覆盖 _detect_redundant_arms / _check_patterns_exhaustive 等模块
# ============================================================


class TestMatchRedundantArms(unittest.TestCase):
    """冗余分支检测 (_detect_redundant_arms) 测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def _make_match_expr(self, arms):
        """构造一个带 span 的 MatchExpr 供入口函数使用"""
        return MatchExpr(
            subject=IntLiteral(value=0, span=Span(line=1, column=1)),
            arms=arms,
            span=Span(line=1, column=1),
        )

    # ---- 通配符/变量绑定冗余 ----

    def test_redundant_duplicate_wildcard(self):
        """两个无 guard 通配符 _：第二个及之后冗余"""
        arms = [
            MatchArm(pattern=PatternWildcard()),
            MatchArm(pattern=PatternWildcard()),
        ]
        redundant, has_wild = self.tc._detect_redundant_arms(arms)
        self.assertEqual(redundant, [1])
        self.assertTrue(has_wild)

    def test_redundant_identifier_after_wildcard(self):
        """_ 之后的变量绑定 x 冗余（均视为 wildcard-like）"""
        arms = [
            MatchArm(pattern=PatternWildcard()),
            MatchArm(pattern=PatternIdentifier(name="x")),
        ]
        redundant, _ = self.tc._detect_redundant_arms(arms)
        self.assertEqual(redundant, [1])

    def test_guarded_wildcard_not_counted(self):
        """有 guard 的通配符不计入 wildcard 完备，也不触发冗余"""
        arms = [
            MatchArm(pattern=PatternWildcard(), guard=BoolLiteral(value=True)),
            MatchArm(pattern=PatternWildcard()),
        ]
        redundant, has_wild = self.tc._detect_redundant_arms(arms)
        # guarded 的不参与 has_wildcard_or_var 判定
        self.assertEqual(redundant, [])
        self.assertTrue(has_wild)  # 第 2 个无 guard 使 has_wild=True

    # ---- 字面量冗余 ----

    def test_redundant_duplicate_int_literal(self):
        """相同 int 字面量后出现的冗余"""
        arms = [
            MatchArm(pattern=PatternInt(value=42)),
            MatchArm(pattern=PatternInt(value=42)),
        ]
        redundant, _ = self.tc._detect_redundant_arms(arms)
        self.assertEqual(redundant, [1])

    def test_redundant_duplicate_string_literal(self):
        """相同字符串字面量后出现的冗余"""
        arms = [
            MatchArm(pattern=PatternString(value="hello")),
            MatchArm(pattern=PatternString(value="world")),
            MatchArm(pattern=PatternString(value="hello")),
        ]
        redundant, _ = self.tc._detect_redundant_arms(arms)
        self.assertEqual(redundant, [2])

    def test_redundant_duplicate_bool_literal(self):
        """相同 bool 字面量后出现的冗余"""
        arms = [
            MatchArm(pattern=PatternBool(value=True)),
            MatchArm(pattern=PatternBool(value=False)),
            MatchArm(pattern=PatternBool(value=True)),
        ]
        redundant, _ = self.tc._detect_redundant_arms(arms)
        self.assertEqual(redundant, [2])

    def test_different_literal_types_not_redundant(self):
        """不同类型的字面量不互相视为冗余（int 42 vs string "42"）"""
        arms = [
            MatchArm(pattern=PatternInt(value=42)),
            MatchArm(pattern=PatternString(value="42")),
        ]
        redundant, _ = self.tc._detect_redundant_arms(arms)
        self.assertEqual(redundant, [])

    def test_nan_float_not_redundant(self):
        """NaN（val is None）不参与字面量冗余比较"""
        nan = float("nan")
        arms = [
            MatchArm(pattern=PatternFloat(value=nan)),
            MatchArm(pattern=PatternFloat(value=nan)),
        ]
        redundant, _ = self.tc._detect_redundant_arms(arms)
        # NaN 不参与冗余检测，两个 NaN 模式均不视为冗余
        self.assertEqual(redundant, [])

    # ---- 入口抛错验证 ----

    def test_check_exhaustiveness_raises_on_redundant(self):
        """_check_match_exhaustiveness 入口检测到冗余分支时先抛错（不等到完备性阶段）"""
        # 使用两个相同的 int 字面量触发冗余（第二个 42 冗余）
        arms = [
            MatchArm(pattern=PatternInt(value=42)),
            MatchArm(pattern=PatternInt(value=42)),
            MatchArm(pattern=PatternWildcard()),
        ]
        match_expr = self._make_match_expr(arms)
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(INT_T, arms, match_expr)
        self.assertIn("冗余", str(ctx.exception))

    def test_empty_arms_raises(self):
        """空 match 表达式应抛 '必须至少有一个分支'"""
        match_expr = self._make_match_expr([])
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(INT_T, [], match_expr)
        self.assertIn("至少有一个分支", str(ctx.exception))


class TestMatchPatternsExhaustive(unittest.TestCase):
    """模式完备性 (_check_patterns_exhaustive 及其子方法) 测试"""

    def setUp(self):
        self.tc = TypeChecker()

    # ---- Bool 类型完备性 ----

    def test_bool_exhaustive_true_and_false(self):
        """PatternBool(true) + PatternBool(false) → 完备"""
        pats = [PatternBool(value=True), PatternBool(value=False)]
        self.assertTrue(self.tc._check_patterns_exhaustive(pats, BOOL_T))

    def test_bool_not_exhaustive_only_true(self):
        """只有 true → 不完备"""
        pats = [PatternBool(value=True)]
        self.assertFalse(self.tc._check_bool_exhaustive(pats))

    def test_bool_wildcard_exhaustive(self):
        """Bool + 通配符 _ → 直接完备（不走 _check_bool_exhaustive）"""
        pats = [PatternBool(value=True), PatternWildcard()]
        self.assertTrue(self.tc._check_patterns_exhaustive(pats, BOOL_T))

    # ---- ADT Option 完备性 ----

    def test_option_exhaustive_some_wildcard_and_none(self):
        """Some(_) + None → Option[Int] 完备"""
        option_int = ADTType("Option", [INT_T])
        pats = [
            PatternConstructor(name="Some", fields=[PatternWildcard()]),
            PatternConstructor(name="None", fields=[]),
        ]
        self.assertTrue(self.tc._check_patterns_exhaustive(pats, option_int))

    def test_option_exhaustive_some_identifier_and_none(self):
        """Some(x) + None → 变量绑定也视为子模式完备"""
        option_int = ADTType("Option", [INT_T])
        pats = [
            PatternConstructor(name="Some", fields=[PatternIdentifier(name="n")]),
            PatternConstructor(name="None", fields=[]),
        ]
        self.assertTrue(self.tc._check_patterns_exhaustive(pats, option_int))

    def test_option_missing_none_not_exhaustive(self):
        """只有 Some(x) 缺少 None → 不完备，缺失构造器"""
        option_int = ADTType("Option", [INT_T])
        pats = [
            PatternConstructor(name="Some", fields=[PatternWildcard()]),
        ]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, option_int))

    def test_option_subpattern_not_exhaustive(self):
        """Some(1) + Some(2) + None → 构造器都覆盖了但 Some 的子模式（Int 字面量）不完备"""
        option_int = ADTType("Option", [INT_T])
        pats = [
            PatternConstructor(name="Some", fields=[PatternInt(value=1)]),
            PatternConstructor(name="Some", fields=[PatternInt(value=2)]),
            PatternConstructor(name="None", fields=[]),
        ]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, option_int))

    # ---- 元组类型完备性 ----

    def test_tuple_exhaustive_bool_wildcard_combination(self):
        """(true, _) + (false, _) → (Bool, Int) 完备"""
        ty = TupleType([BOOL_T, INT_T])
        pats = [
            PatternTuple(elements=[PatternBool(value=True), PatternWildcard()]),
            PatternTuple(elements=[PatternBool(value=False), PatternWildcard()]),
        ]
        self.assertTrue(self.tc._check_patterns_exhaustive(pats, ty))

    def test_tuple_not_exhaustive_missing_first_elem(self):
        """只有 (true, _) 缺少 false 分支 → 不完备"""
        ty = TupleType([BOOL_T, INT_T])
        pats = [
            PatternTuple(elements=[PatternBool(value=True), PatternWildcard()]),
        ]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, ty))

    def test_tuple_not_exhaustive_second_elem_literal(self):
        """(true, 0) + (false, 1)：两位置都是字面量不完备"""
        ty = TupleType([BOOL_T, INT_T])
        pats = [
            PatternTuple(elements=[PatternBool(value=True), PatternInt(value=0)]),
            PatternTuple(elements=[PatternBool(value=False), PatternInt(value=1)]),
        ]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, ty))

    def test_tuple_three_elem_exhaustive(self):
        """三元素 (_, _, true) + (_, _, false) → 仅最后一位 Bool 完备，前两位 _"""
        ty = TupleType([INT_T, STRING_T, BOOL_T])
        pats = [
            PatternTuple(
                elements=[
                    PatternWildcard(),
                    PatternWildcard(),
                    PatternBool(value=True),
                ]
            ),
            PatternTuple(
                elements=[
                    PatternWildcard(),
                    PatternWildcard(),
                    PatternBool(value=False),
                ]
            ),
        ]
        self.assertTrue(self.tc._check_patterns_exhaustive(pats, ty))

    # ---- 无限域类型 (Int/String/Float) ----

    def test_int_literal_not_exhaustive_no_wildcard(self):
        """Int 字面量 1 + 2 → 无限域，无通配符不完备"""
        pats = [PatternInt(value=1), PatternInt(value=2)]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, INT_T))

    def test_string_literal_not_exhaustive(self):
        """固定字符串字面量不完备（字符串域无限）"""
        pats = [PatternString(value="a"), PatternString(value="b")]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, STRING_T))

    # ---- 列表类型（长度无限，恒返回 False）----

    def test_list_always_not_exhaustive(self):
        """空列表 [] + [_] + [_, _] 覆盖了 0-2 长度但整体仍不完备（长度无限）"""
        list_int = ListType(INT_T)
        pats = [
            PatternList(elements=[]),
            PatternList(elements=[PatternWildcard()]),
            PatternList(elements=[PatternWildcard(), PatternWildcard()]),
        ]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, list_int))

    def test_list_empty_pattern_not_exhaustive(self):
        """只有 [] 不完备"""
        list_int = ListType(INT_T)
        pats = [PatternList(elements=[])]
        self.assertFalse(self.tc._check_patterns_exhaustive(pats, list_int))

    # ---- 通配符直接完备 ----

    def test_wildcard_always_exhaustive_for_any_type(self):
        """单个 _ 对任何类型都完备（Int/Bool/ADT/List 全部）"""
        types = [
            INT_T,
            BOOL_T,
            ADTType("Option", [INT_T]),
            ListType(STRING_T),
            TupleType([INT_T, BOOL_T]),
        ]
        for t in types:
            with self.subTest(ty=str(t)):
                self.assertTrue(
                    self.tc._check_patterns_exhaustive([PatternWildcard()], t)
                )


class TestMatchExhaustiveIntegration(unittest.TestCase):
    """_check_match_exhaustiveness 完整入口 + 错误消息测试"""

    def setUp(self):
        self.tc = TypeChecker()

    def _make_match_expr(self, arms):
        return MatchExpr(
            subject=IntLiteral(value=0, span=Span(line=10, column=5)),
            arms=arms,
            span=Span(line=10, column=5),
        )

    def test_adt_missing_variant_message(self):
        """ADT 缺少构造器时错误消息包含缺失构造器名"""
        option_int = ADTType("Option", [INT_T])
        arms = [
            MatchArm(pattern=PatternConstructor(name="Some", fields=[PatternWildcard()])),
        ]
        match_expr = self._make_match_expr(arms)
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(option_int, arms, match_expr)
        self.assertIn("缺失构造器 None", str(ctx.exception))

    def test_adt_subpattern_message(self):
        """Some(1) + Some(2) + None → 消息提示子模式未完全覆盖"""
        option_int = ADTType("Option", [INT_T])
        arms = [
            MatchArm(pattern=PatternConstructor(name="Some", fields=[PatternInt(value=1)])),
            MatchArm(pattern=PatternConstructor(name="Some", fields=[PatternInt(value=2)])),
            MatchArm(pattern=PatternConstructor(name="None", fields=[])),
        ]
        match_expr = self._make_match_expr(arms)
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(option_int, arms, match_expr)
        self.assertIn("子模式未完全覆盖", str(ctx.exception))

    def test_bool_missing_branch_message(self):
        """Bool 缺分支消息包含 '缺失 true 或 false'"""
        arms = [MatchArm(pattern=PatternBool(value=True))]
        match_expr = self._make_match_expr(arms)
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(BOOL_T, arms, match_expr)
        self.assertIn("缺失 true 或 false", str(ctx.exception))

    def test_tuple_missing_message(self):
        """(Bool, Int) 只用 (true, 0) 匹配：消息提示元组元素位置未覆盖"""
        ty = TupleType([BOOL_T, INT_T])
        arms = [MatchArm(pattern=PatternTuple(elements=[PatternBool(value=True), PatternInt(value=0)]))]
        match_expr = self._make_match_expr(arms)
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(ty, arms, match_expr)
        msg = str(ctx.exception).lower()
        self.assertTrue("元组" in msg or "tuple" in msg or "元素" in msg)

    def test_list_length_message(self):
        """List[Int] 只用 [] 和 [_]：消息提示仅覆盖了长度 0,1"""
        list_int = ListType(INT_T)
        arms = [
            MatchArm(pattern=PatternList(elements=[])),
            MatchArm(pattern=PatternList(elements=[PatternWildcard()])),
        ]
        match_expr = self._make_match_expr(arms)
        with self.assertRaises(Exception) as ctx:
            self.tc._check_match_exhaustiveness(list_int, arms, match_expr)
        msg = str(ctx.exception)
        # 消息中应出现长度提示
        self.assertIn("长度", msg)


if __name__ == "__main__":
    unittest.main()
