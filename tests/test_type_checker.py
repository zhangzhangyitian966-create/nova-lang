"""
TypeChecker 单元测试基线

覆盖类型合一核心算法、泛型实例化、基本表达式类型检查等核心路径。
"""

import unittest

from nova.ast_nodes import (
    BinaryOp,
    Block,
    BoolLiteral,
    CharLiteral,
    FloatLiteral,
    FnDef,
    Identifier,
    IfExpr,
    IntLiteral,
    LetBinding,
    ListExpr,
    StringLiteral,
    TypeInt,
    TypeBool,
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
    PrimType,
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


if __name__ == "__main__":
    unittest.main()
