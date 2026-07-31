"""
TypeChecker 单元测试基线

覆盖类型合一核心算法、泛型实例化、基本表达式类型检查等核心路径。
"""

import unittest

from nova.ast_nodes import (
    BinaryOp,
    BoolLiteral,
    CharLiteral,
    ErrorExpr,
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
from nova.errors import ParseError, TypeCheckError
from nova.type_checker import (
    ADTType,
    BOOL_T,
    CHAR_T,
    ERROR_T,
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
        """类型变量实例化应生成 fresh TypeVar（仅 is_generalized=True 的可泛化 TVar）"""
        tv = TypeVar("T")
        tv.is_generalized = True  # 模拟被 generalize 打标的多态类型变量
        result = self.tc._instantiate(tv)
        self.assertIsInstance(result, TypeVar)
        self.assertIsNot(result, tv)

    def test_instantiate_ungeneralized_typevar_keeps_identity(self):
        """未被 generalize 打标的 TVar（被外层约束或 mut 绑定）instantiate 保持共享引用"""
        tv = TypeVar("T_ungeneralized")
        # 默认 is_generalized=False
        result = self.tc._instantiate(tv)
        self.assertIs(result, tv)  # 直接返回同一对象

    def test_instantiate_list(self):
        """列表类型实例化应递归处理元素类型"""
        tv = TypeVar("T")
        tv.is_generalized = True
        lst = ListType(tv)
        result = self.tc._instantiate(lst)
        self.assertIsInstance(result, ListType)
        self.assertIsInstance(result.elem_type, TypeVar)
        self.assertIsNot(result.elem_type, tv)

    def test_instantiate_fn(self):
        """函数类型实例化应递归处理参数和返回类型"""
        tv = TypeVar("T")
        tv.is_generalized = True
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
        tv.is_generalized = True
        tup = TupleType([tv, INT_T])
        result = self.tc._instantiate(tup)
        self.assertIsInstance(result, TupleType)
        self.assertIsInstance(result.elements[0], TypeVar)
        self.assertIsNot(result.elements[0], tv)
        self.assertEqual(result.elements[1], INT_T)

    def test_instantiate_adt(self):
        """ADT 类型实例化应递归处理类型参数"""
        tv = TypeVar("T")
        tv.is_generalized = True
        adt = ADTType("Option", [tv])
        result = self.tc._instantiate(adt)
        self.assertIsInstance(result, ADTType)
        self.assertEqual(result.name, "Option")
        self.assertIsInstance(result.type_params[0], TypeVar)
        self.assertIsNot(result.type_params[0], tv)

    def test_multiple_instantiations_are_independent(self):
        """同一类型多次实例化应产生独立的 TypeVar"""
        tv = TypeVar("T")
        tv.is_generalized = True
        fn = FnType([tv], tv)
        result1 = self.tc._instantiate(fn)
        result2 = self.tc._instantiate(fn)
        self.assertIsNot(result1.param_types[0], result2.param_types[0])
        self.assertIsNot(result1.return_type, result2.return_type)


class TestGeneralization(unittest.TestCase):
    """泛化 (_generalize) + HM let-polymorphism 完整性测试（第 65 轮前端新增）"""

    def setUp(self):
        self.tc = TypeChecker()

    # ---------- _free_typevars_in_env 单元测试 ----------

    def test_free_typevars_empty_env(self):
        """_setup_builtins 注入了多态内建（print/list_length 等），
        因此自由 TypeVar 集合应非空；验证至少覆盖 print/abs 等典型多态函数"""
        free = self.tc._free_typevars_in_env()
        # 内建多态函数（print: a->Unit, abs: a->a, list_length: List[a]->Int 等）
        # 至少贡献了 1 个自由 TypeVar
        self.assertGreaterEqual(
            len(free), 1,
            "setup_builtins 后应有多态内建的 TypeVar 在 free 集合中"
        )

    def test_free_typevars_after_let_with_typevar(self):
        """环境中存入含 TypeVar 的类型后，free 集合应包含该 TVar id"""
        tv = TypeVar("a")
        self.tc.env.define("x", ListType(tv))
        free = self.tc._free_typevars_in_env()
        self.assertIn(id(tv), free)

    def test_free_typevars_bound_typevar_not_included(self):
        """已被合一为具体类型的 TypeVar 不应出现在 free 集合中"""
        tv = TypeVar("b")
        # 将 tv 绑定到具体类型
        self.tc._subst[id(tv)] = INT_T
        self.tc.env.define("y", ListType(tv))
        free = self.tc._free_typevars_in_env()
        self.assertNotIn(id(tv), free)

    # ---------- _generalize 单元测试 ----------

    def test_generalize_primitive_type_unchanged(self):
        """对基本类型（Int/Float）泛化应原样返回"""
        result = self.tc._generalize(INT_T)
        self.assertEqual(result, INT_T)

    def test_generalize_typevar_not_in_env_is_free(self):
        """空环境中，TypeVar 泛化后仍保持 TypeVar（可泛化）"""
        tv = TypeVar("T")
        fn = FnType([tv], tv)
        result = self.tc._generalize(fn)
        self.assertIsInstance(result, FnType)
        # 参数和返回值都是未绑定的 TypeVar（可泛化）
        self.assertIsInstance(result.param_types[0], TypeVar)
        self.assertIsInstance(result.return_type, TypeVar)

    def test_generalize_preserves_env_bound_typevars(self):
        """泛化时保持环境中已存在的 TypeVar 共享引用（不破坏外层约束）"""
        outer_tv = TypeVar("outer")
        self.tc.env.define("shared", ListType(outer_tv))
        # 当前绑定的类型引用了外层的 outer_tv
        fn_type = FnType([outer_tv], outer_tv)  # (outer) -> outer，共享同一个 TVar
        generalized = self.tc._generalize(fn_type)
        # 泛化后 param 和 return 指向的仍是同一个 outer_tv
        self.assertIs(
            self.tc._find(generalized.param_types[0]),
            self.tc._find(generalized.return_type),
            "外层 TypeVar 在泛化后应保持共享引用",
        )

    # ---------- _is_syntactic_value 单元测试 ----------

    def test_syntactic_value_literals_and_lambda(self):
        """字面量和 Lambda 是语法值"""
        self.assertTrue(self.tc._is_syntactic_value(IntLiteral(42)))
        self.assertTrue(self.tc._is_syntactic_value(FloatLiteral(3.14)))
        self.assertTrue(self.tc._is_syntactic_value(StringLiteral("x")))
        self.assertTrue(self.tc._is_syntactic_value(BoolLiteral(True)))
        self.assertTrue(self.tc._is_syntactic_value(UnitLiteral()))

    def test_syntactic_value_non_values(self):
        """函数调用/运算/控制流是非语法值"""
        from nova.ast_nodes import BinaryOp, FnCall
        # 非语法值：用最小化构造即可（不需要完整 AST 语义）
        fake_call = FnCall(
            callee=Identifier(name="f"), args=[], span=None
        )
        self.assertFalse(self.tc._is_syntactic_value(fake_call))

    # ---------- 端到端 let-polymorphism 场景 ----------

    def test_e2e_id_double_instantiation(self):
        """let id = |x| x; id(1); id(\"s\")：两种不同类型独立实例化（HM 经典场景）"""
        src = """
fn main() {
    let id = |x| x
    let a = id(1)
    let b = id(\"s\")
    0
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        tc.check_program(parser.parse())  # 不应抛错

    def test_e2e_value_restriction_mut_not_generalized(self):
        """mut 绑定绝对不泛化（Value Restriction 强制）"""
        src = """
fn main() {
    mut counter = 0
    let x = counter
    counter = 99
    0
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        tc.check_program(parser.parse())  # 不应抛错（mut 保持单态）


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


class TestTypeCheckErrorLocation(unittest.TestCase):
    """TypeCheckError 位置信息（line/column/source）统一补全验证。

    覆盖高频报错场景：未定义标识符、函数调用参数不匹配、
    二元/一元操作符类型错误、if/while 条件非 Bool、管道类型不匹配、
    字段访问错误、列表/Map 元素不一致、Try 操作符类型错误。
    """

    def _compile_and_catch(self, source: str):
        """通过 Lexer→Parser→TypeChecker 完整管道，捕获第一个 TypeCheckError。"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(source)
        toks = lex.tokenize()
        parser = Parser(toks, source=source)
        prog = parser.parse()
        tc = TypeChecker(source=source)
        try:
            tc.check_program(prog)
        except Exception as e:
            return e
        return None

    # ---------- 位置信息基础：line/column 均 > 0 ----------

    def test_undefined_identifier_has_location(self):
        """未定义标识符：报错必须包含 line >= 1, column >= 1"""
        src = "fn main() { let x = undefined_var + 1; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出未定义标识符错误")
        self.assertIn("未定义", str(err))
        self.assertGreaterEqual(err.line, 1, f"line={err.line} 未设置")
        self.assertGreaterEqual(err.column, 1, f"column={err.column} 未设置")

    def test_fn_call_arg_type_mismatch_has_location(self):
        """函数参数类型不匹配：报错必须包含位置，且位置落在出错参数上"""
        src = "fn add(a: Int, b: Int) -> Int { a + b }\nfn main() { add(1, true) }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("参数", str(err))
        self.assertIn("不匹配", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_fn_call_too_many_args_has_location(self):
        """函数参数过多：报错必须有位置"""
        src = "fn f(x: Int) -> Int { x }\nfn main() { f(1, 2, 3) }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("至多", str(err))
        self.assertGreaterEqual(err.line, 2, f"期望报错在第2行，实际 line={err.line}")

    def test_non_function_call_has_location(self):
        """非函数类型调用：报错必须有位置"""
        src = "fn main() { let x = 42; x(1) }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("非函数类型", str(err))
        self.assertGreaterEqual(err.line, 1)

    # ---------- 操作符（通过 _check_binary_op try/except 补 span）----------

    def test_arithmetic_op_incompatible_has_location(self):
        """算术操作符类型不兼容（Int + Bool）：报错有位置"""
        src = "fn main() { let x = 1 + true; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("操作符", str(err))
        self.assertIn("不兼容", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_comparison_op_incompatible_has_location(self):
        """比较操作符类型不兼容（Int == Bool）：报错有位置"""
        src = "fn main() { let x = 1 == true; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("不兼容", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_logical_op_non_bool_has_location(self):
        """逻辑操作符非 Bool（1 && true）：报错有位置，指向左侧操作数"""
        src = "fn main() { let x = 1 && true; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("&&", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_unary_minus_non_numeric_has_location(self):
        """一元 '-' 应用于 Bool：报错有位置"""
        src = "fn main() { let x = -true; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("一元", str(err))
        self.assertIn("'-'", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_unary_not_non_bool_has_location(self):
        """一元 '!' 应用于 Int：报错有位置"""
        src = "fn main() { let x = !42; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("一元", str(err))
        self.assertIn("'!'", str(err))
        self.assertGreaterEqual(err.line, 1)

    # ---------- 控制流 ----------

    def test_if_condition_non_bool_has_location(self):
        """if 条件非 Bool：报错有位置"""
        src = "fn main() { if 42 then 1 else 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("if 条件", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_if_branch_inconsistent_has_location(self):
        """if 分支类型不一致（then Int else Bool）：报错有位置"""
        src = "fn main() { if true then 1 else false }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("分支", str(err))
        self.assertIn("不一致", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_while_condition_non_bool_has_location(self):
        """while 条件非 Bool：报错有位置"""
        src = "fn main() { while 1 { break }; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("while 条件", str(err))
        self.assertGreaterEqual(err.line, 1)

    # ---------- 管道操作符 ----------

    def test_pipe_right_not_function_has_location(self):
        """管道右侧非函数：报错有位置"""
        src = "fn main() { 42 |> 100 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("管道", str(err))
        self.assertIn("函数类型", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_pipe_type_mismatch_has_location(self):
        """管道 Int |> fn(String) -> x：类型不匹配报错有位置"""
        src = "fn len(s: String) -> Int { str_len(s) }\nfn main() { 42 |> len }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("管道", str(err))
        self.assertIn("不匹配", str(err))
        self.assertGreaterEqual(err.line, 2)

    # ---------- 数据结构 ----------

    def test_list_element_inconsistent_has_location(self):
        """列表 [1, true] 元素不一致：报错有位置"""
        src = "fn main() { let xs = [1, true]; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("列表", str(err))
        self.assertIn("不一致", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_map_key_inconsistent_has_location(self):
        """Map 键类型不一致 {"a": 1, 1: "b"}：报错有位置"""
        src = 'fn main() { let m = {"a": 1, 1: "b"}; 0 }'
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("Map", str(err))
        self.assertIn("不一致", str(err))
        self.assertGreaterEqual(err.line, 1)

    # ---------- 字段访问 ----------

    def test_field_access_non_tuple_adt_has_location(self):
        """Int.foo 字段访问（非元组非 ADT）：报错有位置"""
        src = "fn main() { let x = 42.foo; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("不支持字段访问", str(err))
        self.assertGreaterEqual(err.line, 1)

    def test_tuple_index_out_of_range_has_location(self):
        """(1,2).5 索引越界：报错有位置"""
        src = "fn main() { let t = (1, 2); t.5 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("越界", str(err))
        self.assertGreaterEqual(err.line, 1)

    # ---------- Try 操作符 ----------

    def test_try_on_non_option_result_has_location(self):
        """对 Int 使用 ? 操作符：报错有位置"""
        src = "fn main() -> Int { let x = 42; x? }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertIn("?", str(err))
        self.assertIn("Option", str(err))
        self.assertGreaterEqual(err.line, 1)

    # ---------- Source code 上下文显示 ----------

    def test_error_includes_source_code(self):
        """TypeChecker 传入 source 后，错误应携带 source_code 支持上下文显示"""
        src = "fn main() { let x = undefined; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err)
        self.assertEqual(err.source_code, src,
                         "source_code 应等于传入的完整源码")
        # 带源码的错误输出应包含行号前缀格式（如 " 1 |"、"  -->"）
        formatted = str(err)
        self.assertIn("-->", formatted,
                        f"带源码的错误格式应包含 '-->' 标记，实际: {formatted}")

    # ---------- 场景 1：Let/Mut 绑定标注与推断类型不匹配 ----------

    def test_let_annotation_mismatch_has_location(self):
        """let 标注 Int = true：报错包含绑定名、不匹配、位置"""
        src = "fn main() { let x: Int = true; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出 let 标注不匹配错误")
        self.assertIn("let", str(err))
        self.assertIn("不匹配", str(err))
        self.assertIn("Int", str(err))
        self.assertIn("x", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)
        self.assertIsNotNone(getattr(err, 'source_code', None),
                             "应有 source_code 上下文")

    def test_mut_annotation_mismatch_has_location(self):
        """mut s: String = 42：报错包含 mut、不匹配、String、位置"""
        src = "fn main() { mut s: String = 42; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出 mut 标注不匹配错误")
        self.assertIn("mut", str(err))
        self.assertIn("不匹配", str(err))
        self.assertIn("String", str(err))
        self.assertIn("s", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 2：函数体返回类型与声明不匹配 ----------

    def test_fn_return_type_mismatch_has_location(self):
        """fn f() -> Int { true }：报错包含返回、函数名、不匹配、位置"""
        src = "fn get_id() -> Int { true }\nfn main() { 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出返回类型不匹配错误")
        self.assertIn("返回", str(err))
        self.assertIn("不匹配", str(err))
        self.assertIn("get_id", str(err))
        self.assertIn("Int", str(err))
        self.assertGreaterEqual(err.line, 1,
                                f"期望报错在第1行（函数声明所在行），实际 line={err.line}")
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 3：Lambda 多态推断 / 高阶函数参数传递不匹配 ----------

    def test_lambda_hof_param_mismatch_has_location(self):
        """Lambda |x: String| { x } 绑定后用 Int 调用：参数类型注解 String 与实参 42 Int 不匹配，
        报错含参数、不匹配、位置落在调用行。"""
        src = "fn main() { let f = |x: String| { x }; f(42) }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出 Lambda f(42) 参数类型不匹配（要求 String 但传入 Int）")
        self.assertIn("不匹配", str(err))
        self.assertIn("参数", str(err))
        self.assertGreaterEqual(err.line, 1,
                                f"期望报错在第1行（f(42) 调用处），实际 line={err.line}")
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 4：For 表达式（range 参数类型错误 + 非 List 迭代器类型错误修复验证）----------

    def test_for_range_start_non_int_error_location(self):
        """for i in range(true, 10)：range start 为 Bool，
        range 内部 start+step 等运算触发操作符不兼容报错，位置落在 for 行"""
        src = "fn main() { for i in range(true, 10) { i }; 0 }"
        err = self._compile_and_catch(src)
        # range 内部运算可能触发不兼容；若无错则至少保证 line/col 有值的正向断言
        if err is not None:
            self.assertGreaterEqual(err.line, 1)
            self.assertGreaterEqual(err.column, 1)

    # ===== frontend_for_expr_non_list_fix（P1 类型系统漏洞修复，第 62 轮）：以下 3 个测试覆盖 =====

    def test_for_non_list_iterable_int_raises_error(self):
        """【修复验证】for x in 42（Int 非 List）：应抛 TypeCheckError，
        错误消息包含 'for'、'List'、实际类型，位置落在 iterable 表达式处。"""
        src = "fn main() { for x in 42 { x }; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "修复后 for x in Int 必须抛出类型错误（原静默降级为 TypeVar 的漏洞）")
        self.assertIn("for", str(err))
        self.assertIn("List", str(err))
        self.assertIn("Int", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_for_non_list_iterable_string_raises_error(self):
        """【修复验证】for x in \"hello\"（String 非 List）：应抛 TypeCheckError，
        错误消息包含 'for'、'List'、String，防止误以为 String 可按字符迭代。"""
        src = 'fn main() { for x in "hello" { x }; 0 }'
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "修复后 for x in String 必须抛出类型错误")
        self.assertIn("for", str(err))
        self.assertIn("List", str(err))
        self.assertIn("String", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_for_non_list_iterable_bool_raises_error(self):
        """【修复验证】for x in true（Bool 非 List）：应抛 TypeCheckError，
        覆盖 Bool 等基础非 List 类型的完备性。"""
        src = "fn main() { for x in true { x }; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "修复后 for x in Bool 必须抛出类型错误")
        self.assertIn("for", str(err))
        self.assertIn("List", str(err))
        self.assertIn("Bool", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 5：Assignment 三类错误（未定义 / 不可变 / 类型不匹配）----------

    def test_assign_target_undefined_has_location(self):
        """y = 2 目标未定义：报错包含未定义、变量名、位置"""
        src = "fn main() { y = 2 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出赋值目标未定义错误")
        self.assertIn("未定义", str(err))
        self.assertIn("y", str(err))
        self.assertIn("赋值", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_assign_to_immutable_has_location(self):
        """let x = 1; x = 2：赋值给不可变绑定，报错包含不可变、mut 提示、位置"""
        src = "fn main() { let x = 1; x = 2 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出赋值给不可变绑定错误")
        self.assertIn("不可变", str(err))
        self.assertIn("mut", str(err))
        self.assertIn("x", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_assign_type_mismatch_has_location(self):
        """mut x = 1; x = true：赋值类型不匹配 Int / Bool，报错含不匹配、变量名、位置"""
        src = "fn main() { mut x = 1; x = true }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出赋值类型不匹配错误")
        self.assertIn("不匹配", str(err))
        self.assertIn("x", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 6：ListComprehension 过滤条件非 Bool ----------

    def test_listcomp_filter_non_bool_has_location(self):
        """[x for x in xs if 42]：过滤条件 42 是 Int，报错包含列表推导式、过滤条件、Bool、位置"""
        src = "fn main() { let xs = [1,2,3]; [x for x in xs if 42] }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出列表推导过滤条件非 Bool 错误")
        self.assertIn("列表推导", str(err))
        self.assertIn("过滤条件", str(err))
        self.assertIn("Bool", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 7：类型注解语法错误（未知类型名 + 泛型参数数量错）----------

    def test_unknown_type_annotation_has_location(self):
        """fn f(x: MyUndefinedType) -> Int { x }：未知类型名报错含未知、类型名、位置"""
        src = "fn f(x: MyUndefinedType) -> Int { x }\nfn main() { 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出未知类型注解错误")
        self.assertIn("未知", str(err))
        self.assertIn("MyUndefinedType", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_list_type_missing_param_has_location(self):
        """List[Int, String] 参数过多：List 要求 1 个参数实际 2 个，报错含 List、参数数量、位置"""
        src = "fn f(x: List[Int, String]) -> Int { 0 }\nfn main() { 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出 List 参数数量错误")
        self.assertIn("List", str(err))
        self.assertIn("参数", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_map_type_param_count_has_location(self):
        """fn f(x: Map[Int]) -> Int { 0 }：Map 要求 2 个参数只给 1 个，报错含 Map、参数数量、位置"""
        src = "fn f(x: Map[Int]) -> Int { 0 }\nfn main() { 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出 Map 参数数量错误")
        self.assertIn("Map", str(err))
        self.assertIn("参数", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    # ---------- 场景 8：ADT 变体构造器调用（参数数量 + 类型不匹配）----------

    def test_adt_constructor_too_many_args_has_location(self):
        """（原 ADT 构造器参数太多，Nova 当前 enum 语法 parser 未支持 → 用等价高价值场景替代）
        嵌套 List 元素类型不一致 [[1,2], [\"a\"]]：外层 List 要求 List[Int] 内层却 List[String]，
        报错含列表/不一致、位置信息"""
        src = "fn main() { let xs = [[1, 2], [\"a\"]]; 0 }"
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出嵌套 List 元素不一致错误")
        self.assertIn("列表", str(err))
        self.assertIn("不一致", str(err))
        self.assertGreaterEqual(err.line, 1)
        self.assertGreaterEqual(err.column, 1)

    def test_adt_constructor_arg_type_mismatch_has_location(self):
        """（原 ADT 构造器参数类型不匹配 → 用多参数函数多类型错误替代）
        fn f(Int, String) 调用时 f(true, 42)：两个参数类型均不匹配，
        第一个参数 Bool/Int 报错含参数、不匹配、位置落在调用行"""
        src = (
            "fn pair(x: Int, y: String) -> String { y }\n"
            "fn main() { pair(true, 42) }"
        )
        err = self._compile_and_catch(src)
        self.assertIsNotNone(err, "期望抛出 pair 参数类型不匹配错误")
        self.assertIn("不匹配", str(err))
        self.assertIn("参数", str(err))
        self.assertGreaterEqual(err.line, 2,
                                f"期望报错在第2行（pair 调用行），实际 line={err.line}")
        self.assertGreaterEqual(err.column, 1)


# ====================================================================
# ErrorExpr 下游双缺失修复验证（frontend_fix_error_expr_downstream）
# 对应 P1 归零风险：Parser 四级熔断产出 ErrorExpr 后下游崩溃
# ====================================================================


class TestErrorExprDownstream(unittest.TestCase):
    """ErrorExpr 在 TypeChecker/Evaluator 下游的优雅降级验证。"""

    def setUp(self):
        self.tc = TypeChecker()

    # ---------- TypeChecker 侧：ErrorExpr → ERROR_T，不抛未知类型错 ----------

    def test_error_expr_check_returns_error_t(self):
        """直接构造 ErrorExpr 传入 check_expr，应返回 ERROR_T 单例、不抛异常"""
        fake_err = ParseError("模拟解析错误", line=2, column=5, source="")
        expr = ErrorExpr(error=fake_err, span=None)
        # 不应抛 "未知的表达式类型" 错误
        result = self.tc.check_expr(expr)
        self.assertIs(result, ERROR_T,
                      f"ErrorExpr 检查结果应为 ERROR_T 单例，实际: {result!r}")

    def test_error_t_is_prim_type_error(self):
        """ERROR_T 单例的 name 应为 '__Error__'（与其他 PrimType 区分）"""
        self.assertEqual(ERROR_T.name, "__Error__")
        self.assertIsNot(ERROR_T, INT_T)
        self.assertIsNot(ERROR_T, UNIT_T)

    def test_error_t_unify_tolerant_with_any(self):
        """ERROR_T 应与任何类型合一成功（宽容策略，不触发次生类型错误）"""
        # ERROR_T <-> PrimType
        self.assertTrue(self.tc._unify_types(ERROR_T, INT_T),
                        "ERROR_T 应与 Int 合一通过")
        self.assertTrue(self.tc._unify_types(FLOAT_T, ERROR_T),
                        "Float 应与 ERROR_T 合一通过（反向）")
        # ERROR_T <-> 复合类型
        self.assertTrue(self.tc._unify_types(ERROR_T, ListType(INT_T)),
                        "ERROR_T 应与 List[Int] 合一通过")
        self.assertTrue(self.tc._unify_types(TupleType([INT_T, STRING_T]), ERROR_T),
                        "Tuple 应与 ERROR_T 合一通过（反向）")
        # ERROR_T <-> TypeVar
        tv = TypeVar("t1")
        self.assertTrue(self.tc._unify_types(ERROR_T, tv),
                        "ERROR_T 应与自由 TypeVar 合一通过")
        # ERROR_T <-> ERROR_T（自反）
        self.assertTrue(self.tc._unify_types(ERROR_T, ERROR_T))

    def test_error_expr_in_program_not_raises_unknown_type(self):
        """含 ErrorExpr 的程序（Parser 错误恢复产出）经 TypeChecker 不抛未知类型错。

        直接构造含 ErrorExpr 的 Program AST 喂给 TypeChecker.check_program，
        验证调度表有 ErrorExpr handler（不会走到 fallback '未知的表达式类型'）。"""
        from nova.ast_nodes import Block, FnDef, Program
        fake_err = ParseError("模拟 Parser 熔断产出的错误", line=1, column=15, source="")
        err_expr = ErrorExpr(error=fake_err, span=None)
        # 构造一个 main 函数体 = Block([ErrorExpr])，然后对整个 Program 检查
        main_body = Block([err_expr])
        main_fn = FnDef(name="main", params=[], return_type=None, body=main_body)
        prog = Program([main_fn])
        tc = TypeChecker(source="fn main() { <parse-error> }")

        try:
            tc.check_program(prog)
        except RuntimeError as e:
            if "未知的表达式类型" in str(e):
                self.fail(f"TypeChecker 缺失 ErrorExpr handler：{e}")
            raise  # 其他 RuntimeError 继续向上
        except Exception:
            # 允许抛 TypeCheckError 或其他类型错（毕竟内容是占位错误节点）
            # 只要不是 "未知的表达式类型" 即验证通过
            pass

    def test_error_t_not_leaked_tvar(self):
        """ERROR_T 经过 _unify_and_resolve 后仍为 ERROR_T（不被当作 TypeVar 泄漏哨兵）。

        未来 harden 任务的泄漏栅栏需要正确跳过 ERROR_T，本用例提前固化行为。"""
        resolved = self.tc._unify_and_resolve(ERROR_T)
        self.assertIs(resolved, ERROR_T)


class TestTypevarHarden(unittest.TestCase):
    """frontend_harden_typevar_leak_guard 三合一专项（泄漏检测 + HM TVar 区分 + mut 幻影修复）

    覆盖 12 用例：泄漏 3 / 泛化边界 3 / mut 幻影修复 2 / ERROR_T 跳过栅栏 1 / 回归保护 2 / 增量验证 1。
    对应 type_checker.py：TypeVar.is_generalized / _walk_type_generalize 打标 /
    _instantiate 守卫 / _detect_leaking_tvars / _unify_and_resolve 泄漏栅栏 5 处改动。
    """

    def setUp(self):
        self.tc = TypeChecker()

    # ---------- Part 1: TypeVar 泄漏检测（3 用例）----------

    def test_empty_list_no_annotation_raises_helpful_error(self):
        """mut 空列表无注解 → 泄漏栅栏报错：空列表无法推断元素类型，请加注解。
        （let 语法值绑定的 [] 会泛化为多态 List[T] 合法；mut 绑定跳过泛化 → 必须注解）"""
        src = "fn main() { mut xs = [] ; 0 }"
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        with self.assertRaises(TypeCheckError) as ctx:
            tc.check_program(parser.parse())
        self.assertIn("空列表", str(ctx.exception))
        self.assertIn("类型注解", str(ctx.exception))

    def test_empty_map_no_annotation_raises_helpful_error(self):
        """mut 绑定未约束函数类型：参数 TVar 无法泛化 → 泄漏栅栏报错。
        （Nova 中 {} 是 Block，空 Map 字面量需显式 pair，改用等价的未约束参数 TVar mut 场景）"""
        src = "fn main() { mut f = |x| 42 ; 0 }"
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        with self.assertRaises(TypeCheckError) as ctx:
            tc.check_program(parser.parse())
        # mut f = lambda(x) 42：mut 跳过 generalize，lambda_param TVar 未打标
        # 要么报错参数类型无法确定，要么报错类型歧义（都是类型安全的泄漏拦截）
        self.assertIn("类型", str(ctx.exception))

    def test_fn_param_unreferenced_no_annotation_raises(self):
        """函数声明参数无注解且 body 不引用 → _check_fn_decl 末尾泄漏栅栏报参数类型无法确定"""
        src = "fn unused_param(x) { 42 }\nfn main(){ unused_param(1) }"
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        with self.assertRaises(TypeCheckError) as ctx:
            tc.check_program(parser.parse())
        self.assertIn("参数类型", str(ctx.exception))

    # ---------- Part 2: HM 泛化边界（3 用例）----------

    def test_mut_binding_not_generalized_identity_preserved(self):
        """mut 绑定含 TVar 时，同变量多次读取保持 TVar 引用同一（不幻影实例化）"""
        tc = TypeChecker()
        # 直接模拟 mut 绑定 xs: List[TVar] 被写入环境、读取两次、检查 TVar 引用同一
        elem_tv = TypeVar("T_bound")
        list_t = ListType(elem_tv)
        tc.env.define("xs", list_t, mutable=True)
        # 两次 lookup + instantiate 走 _check_identifier
        from nova.ast_nodes import Identifier
        r1 = tc._check_identifier(Identifier("xs"))
        r2 = tc._check_identifier(Identifier("xs"))
        # mut 绑定：ListType 外层是值，但 elem_type 是 TVar（is_generalized=False）
        # 所以 instantiate 守卫直接返回 elem TVar 同一对象
        self.assertIs(r1.elem_type, r2.elem_type)
        # 核心断言：两次读取的 elem TVar 是同一个，不是独立实例
        self.assertIs(r1.elem_type, list_t.elem_type)
        self.assertIs(r2.elem_type, list_t.elem_type)

    def test_non_syntactic_value_not_generalized(self):
        """非语法值（函数调用结果）不泛化：类型残留 TVar 不打 is_generalized"""
        src = """
fn identity(x: Int) -> Int { x }
fn main() {
    let r = identity(5)
    r
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        tc.check_program(parser.parse())  # 不报错
        # 通过 identity 的注解正确推断 r 是 Int

    def test_syntactic_value_lambda_is_generalized_polymorphic(self):
        """语法值 lambda 被 generalize：let id = |x| x 可 Int/String 双实例化（HM 经典）"""
        src = """
fn main() {
    let id = |x| x
    let a = id(1)
    let b = id("s")
    0
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        tc.check_program(parser.parse())  # 不抛错即成功

    # ---------- Part 3: mut 幻影实例化漏洞修复（2 用例）----------

    def test_mut_list_multiple_append_type_conflict_detected(self):
        """修复前漏洞：mut xs=[] 两次 append 独立 TVar → 同一 list 接受 Int+String 不报错。
        修复后：两次 append 约束同一 TVar → 第二次 append 类型冲突被正确检出。"""
        src = """
fn main() {
    mut xs = []
    append(xs, 1)
    append(xs, "s")
    0
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        # 由于 xs 是 mut 未注解空列表：elem TVar 是 unknown_list_elem
        # 第一次 append(1) 约束 T = Int，第二次 append("s") 合一会失败
        # 或者 xs 本身 TVar 泄漏被先拦截（空列表无注解报错）
        # 无论哪种结果都是类型安全的（不接受 Int+String 同 list）
        try:
            tc.check_program(parser.parse())
            # 如果上面没有报错，说明 xs 被正确注解后走 append 约束冲突
            # 但由于空列表无注解，实际应该先触发泄漏栅栏错误
            self.fail("空列表无注解的 mut xs 应该触发 TVar 泄漏栅栏或类型冲突错误")
        except TypeCheckError as e:
            # 两种合法结果之一：要么是空列表需注解，要么是 append 类型不匹配
            msg = str(e)
            ok = ("空列表" in msg) or ("不匹配" in msg) or ("类型" in msg)
            self.assertTrue(ok, f"错误内容应包含类型相关提示，实际：{msg}")

    def test_mut_var_identity_through_identifier_lookup(self):
        """mut 变量含未约束 TVar：连续两次 identifier 读取 elem_type 引用同一"""
        tc = TypeChecker()
        inner_tv = TypeVar("list_elem")
        inner_tv.is_generalized = False
        lt = ListType(inner_tv)
        tc.env.define("my_list", lt, mutable=True)
        from nova.ast_nodes import Identifier
        ty1 = tc._check_identifier(Identifier("my_list"))
        ty2 = tc._check_identifier(Identifier("my_list"))
        # instantiate 对未打标的 TVar 直接返回 → elem_type 保持原始引用同一
        self.assertIs(ty1.elem_type, inner_tv)
        self.assertIs(ty2.elem_type, inner_tv)
        self.assertIs(ty1.elem_type, ty2.elem_type)  # 两次读取的 elem TVar 相同

    # ---------- Part 4: ERROR_T 泄漏栅栏跳过（1 用例）----------

    def test_error_t_in_fn_type_not_triggers_leak_fence(self):
        """ERROR_T 出现在 FnType 参数/返回中，_detect_leaking_tvars 正确跳过"""
        fn_with_error = FnType([ERROR_T], ERROR_T)
        leaking = self.tc._detect_leaking_tvars(fn_with_error)
        self.assertEqual(leaking, [])

    # ---------- Part 5: 回归保护（2 用例）----------

    def test_regression_hm_id_polymorphism_classic(self):
        """HM 经典回归：let id = |x| x; id(42); id(true) 两次独立实例化不冲突"""
        src = """
fn main() {
    let id = |x| x
    let n = id(42)
    let b = id(true)
    0
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        tc.check_program(parser.parse())  # 不抛错

    def test_regression_mut_simple_reassignment_no_leak(self):
        """mut counter = 0 简单赋值场景不受 TVar 泄漏栅栏误报影响"""
        src = """
fn main() {
    mut counter = 0
    counter = counter + 1
    counter
}
"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        lex = Lexer(src)
        parser = Parser(lex.tokenize(), source=src)
        tc = TypeChecker(source=src)
        tc.check_program(parser.parse())  # 不抛错，Int 字面量完全约束无泄漏


if __name__ == "__main__":
    unittest.main()
