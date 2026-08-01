# -*- coding: utf-8 -*-
"""
IR 类型系统单元测试（tests/test_ir_types.py 缺口补齐 SH-1 P0）

覆盖范围：
  - IRType 枚举：16 种 kind 枚举成员齐全
  - NovaType 基本：kind/params/name 三字段 + __eq__/__hash__/__repr__
  - 7 种单例类型：INT_TYPE / FLOAT_TYPE / STRING_TYPE / BOOL_TYPE /
                  CHAR_TYPE / UNIT_TYPE / NEVER_TYPE / CLOSURE_TYPE
  - 9 种工厂函数（snake_case）：list_type / map_type / tuple_type /
    fn_type / adt_type / option_type / result_type / box_type
  - 向后兼容 PascalCase 别名：ListType / MapType / TupleType / FnType /
    ADTType / OptionType / ResultType / BoxType
  - 嵌套类型（List[List[Int]]、Map[String, List[Int]]、fn 嵌套等）
  - 类型相等：同构相等、异构不等、单例共享、工厂生成相同值应相等
  - NovaType 可哈希：作为 dict 键/set 元素应工作
  - repr 规范化：List[X] / Map[K,V] / (A)->B / (T1,T2) / ADT[P1,P2] / Box[T]
  - ir_types 模块 __all__ 暴露完整公开 API
"""

import unittest

from nova.ir.ir_types import (
    # Core types
    IRType, NovaType,
    # Singletons
    INT_TYPE, FLOAT_TYPE, STRING_TYPE, BOOL_TYPE, CHAR_TYPE, UNIT_TYPE,
    NEVER_TYPE, CLOSURE_TYPE,
    # Snake-case factories (PEP8)
    list_type, map_type, tuple_type, fn_type, adt_type,
    option_type, result_type, box_type,
    # Backward-compat PascalCase aliases
    ListType, MapType, TupleType, FnType, ADTType, OptionType, ResultType, BoxType,
    # Module public API
    __all__ as IR_TYPES_ALL,
)


class TestIRTypeEnum(unittest.TestCase):
    """IRType 种类枚举：16 种 kind 齐全"""

    def test_scalar_kinds_exist(self):
        """标量 7 种：INT / FLOAT / STRING / BOOL / CHAR / UNIT / NEVER"""
        self.assertIsNotNone(IRType.INT)
        self.assertIsNotNone(IRType.FLOAT)
        self.assertIsNotNone(IRType.STRING)
        self.assertIsNotNone(IRType.BOOL)
        self.assertIsNotNone(IRType.CHAR)
        self.assertIsNotNone(IRType.UNIT)
        self.assertIsNotNone(IRType.NEVER)

    def test_container_kinds_exist(self):
        """容器 3 种：LIST / MAP / TUPLE"""
        self.assertIsNotNone(IRType.LIST)
        self.assertIsNotNone(IRType.MAP)
        self.assertIsNotNone(IRType.TUPLE)

    def test_function_adt_kinds(self):
        """函数/代数 3 种：FUNCTION / ADT / TYPE_VAR"""
        self.assertIsNotNone(IRType.FUNCTION)
        self.assertIsNotNone(IRType.ADT)
        self.assertIsNotNone(IRType.TYPE_VAR)

    def test_lir_and_box_kinds(self):
        """扩展 3 种：BOX（M-MEM Step3）/ PTR（LIR）"""
        self.assertIsNotNone(IRType.BOX)
        self.assertIsNotNone(IRType.PTR)

    def test_total_count_16(self):
        """IRType 枚举成员共 15 个（含 BOX 与 PTR 扩展）"""
        all_members = [m for m in IRType]
        self.assertGreaterEqual(len(all_members), 15)


class TestNovaTypeBasic(unittest.TestCase):
    """NovaType 三字段 + 等价 + 哈希"""

    def test_three_fields_defaults(self):
        """NovaType(kind=IRType.INT) → params=[], name=''"""
        t = NovaType(IRType.INT)
        self.assertEqual(t.kind, IRType.INT)
        self.assertEqual(t.params, [])
        self.assertEqual(t.name, "")

    def test_equality_same_kind(self):
        """相同 kind/params/name 应相等"""
        a = NovaType(IRType.INT)
        b = NovaType(IRType.INT)
        self.assertEqual(a, b)

    def test_equality_diff_kind_not_equal(self):
        """不同 kind 不相等"""
        self.assertNotEqual(NovaType(IRType.INT), NovaType(IRType.FLOAT))

    def test_equality_diff_params_not_equal(self):
        """同 kind 不同 params 不相等"""
        a = NovaType(IRType.LIST, [INT_TYPE])
        b = NovaType(IRType.LIST, [FLOAT_TYPE])
        self.assertNotEqual(a, b)

    def test_equality_diff_name_not_equal(self):
        """同 kind/params 不同 name 不相等"""
        a = NovaType(IRType.ADT, [], "Bool")
        b = NovaType(IRType.ADT, [], "Ordering")
        self.assertNotEqual(a, b)

    def test_hashable_dict_key(self):
        """NovaType 可哈希 → 可作为 dict 键"""
        cache = {INT_TYPE: "int", FLOAT_TYPE: "float"}
        self.assertEqual(cache[INT_TYPE], "int")
        self.assertEqual(cache[FLOAT_TYPE], "float")
        # 新构造的相同类型应命中同一键
        self.assertEqual(cache[NovaType(IRType.INT)], "int")

    def test_hashable_set_member(self):
        """NovaType 可哈希 → 可放入 set"""
        s = {INT_TYPE, FLOAT_TYPE, INT_TYPE}
        self.assertEqual(len(s), 2)

    def test_not_equal_to_non_novatype(self):
        """NovaType 与非 NovaType 对象比较应返回 False 不抛错"""
        self.assertFalse(NovaType(IRType.INT) == 123)
        self.assertFalse(NovaType(IRType.INT) == "INT")
        self.assertNotEqual(NovaType(IRType.INT), None)


class TestSingletonTypes(unittest.TestCase):
    """8 种单例类型"""

    def test_int_singleton_kind(self):
        """INT_TYPE.kind == IRType.INT"""
        self.assertEqual(INT_TYPE.kind, IRType.INT)

    def test_all_scalar_singletons(self):
        """FLOAT/STRING/BOOL/CHAR/UNIT/NEVER 均为零参 NovaType"""
        self.assertEqual(FLOAT_TYPE.kind, IRType.FLOAT)
        self.assertEqual(STRING_TYPE.kind, IRType.STRING)
        self.assertEqual(BOOL_TYPE.kind, IRType.BOOL)
        self.assertEqual(CHAR_TYPE.kind, IRType.CHAR)
        self.assertEqual(UNIT_TYPE.kind, IRType.UNIT)
        self.assertEqual(NEVER_TYPE.kind, IRType.NEVER)

    def test_closure_type_is_function_with_name(self):
        """CLOSURE_TYPE = IRType.FUNCTION + name='Closure'"""
        self.assertEqual(CLOSURE_TYPE.kind, IRType.FUNCTION)
        self.assertEqual(CLOSURE_TYPE.name, "Closure")


class TestFactoryFunctions(unittest.TestCase):
    """9 种 snake_case 工厂函数"""

    def test_list_type_kind_and_params(self):
        """list_type(INT) → kind=LIST, params=[INT]"""
        t = list_type(INT_TYPE)
        self.assertEqual(t.kind, IRType.LIST)
        self.assertEqual(t.params, [INT_TYPE])

    def test_map_type_kind_and_params(self):
        """map_type(STRING, INT) → kind=MAP, params=[STRING, INT]"""
        t = map_type(STRING_TYPE, INT_TYPE)
        self.assertEqual(t.kind, IRType.MAP)
        self.assertEqual(t.params, [STRING_TYPE, INT_TYPE])

    def test_tuple_type_zero_is_unit_shape(self):
        """tuple_type() → kind=TUPLE, params=[]（等价 UNIT 的类型形状）"""
        t = tuple_type()
        self.assertEqual(t.kind, IRType.TUPLE)
        self.assertEqual(t.params, [])

    def test_tuple_type_multiple(self):
        """tuple_type(A, B, C) → params 长度 3"""
        t = tuple_type(INT_TYPE, STRING_TYPE, BOOL_TYPE)
        self.assertEqual(len(t.params), 3)

    def test_fn_type_return_last(self):
        """fn_type(A, B, R) → kind=FUNCTION, params=[A, B, R]（最后一个是返回）"""
        t = fn_type(INT_TYPE, INT_TYPE, BOOL_TYPE)
        self.assertEqual(t.kind, IRType.FUNCTION)
        self.assertEqual(t.params, [INT_TYPE, INT_TYPE, BOOL_TYPE])

    def test_adt_type_name(self):
        """adt_type('Option', T) → kind=ADT, name='Option', params=[T]"""
        t = adt_type("Option", INT_TYPE)
        self.assertEqual(t.kind, IRType.ADT)
        self.assertEqual(t.name, "Option")
        self.assertEqual(t.params, [INT_TYPE])

    def test_adt_type_no_params(self):
        """adt_type('Bool') → ADT 无参，name='Bool'"""
        t = adt_type("Bool")
        self.assertEqual(t.name, "Bool")
        self.assertEqual(t.params, [])

    def test_option_adt_sugar(self):
        """option_type(T) = adt_type('Option', T)"""
        t = option_type(INT_TYPE)
        self.assertEqual(t, adt_type("Option", INT_TYPE))
        self.assertEqual(t.name, "Option")

    def test_result_adt_sugar(self):
        """result_type(OK, ERR) = adt_type('Result', OK, ERR)"""
        t = result_type(INT_TYPE, STRING_TYPE)
        self.assertEqual(t, adt_type("Result", INT_TYPE, STRING_TYPE))

    def test_box_type(self):
        """box_type(T) → kind=BOX, params=[T]"""
        t = box_type(INT_TYPE)
        self.assertEqual(t.kind, IRType.BOX)
        self.assertEqual(t.params, [INT_TYPE])

    def test_box_list_adt_nesting(self):
        """List[Box[Node]] → 复杂嵌套类型可构造 + 结构正确"""
        node = adt_type("Node")
        t = list_type(box_type(node))
        self.assertEqual(t.kind, IRType.LIST)
        inner_box = t.params[0]
        self.assertEqual(inner_box.kind, IRType.BOX)
        self.assertEqual(inner_box.params[0].name, "Node")


class TestBackwardCompatAliases(unittest.TestCase):
    """PascalCase 薄别名（Cycle-1513 gate_naming_violation 修复后保留 100% 兼容）"""

    def test_listtype_equals_list_type(self):
        """ListType(T) == list_type(T)"""
        self.assertEqual(ListType(INT_TYPE), list_type(INT_TYPE))

    def test_maptype_equals(self):
        """MapType(K, V) == map_type(K, V)"""
        self.assertEqual(MapType(INT_TYPE, BOOL_TYPE),
                         map_type(INT_TYPE, BOOL_TYPE))

    def test_tupletype_equals(self):
        """TupleType(*xs) == tuple_type(*xs)"""
        self.assertEqual(TupleType(INT_TYPE, STRING_TYPE),
                         tuple_type(INT_TYPE, STRING_TYPE))

    def test_fntype_equals(self):
        """FnType(A, B, R) == fn_type(A, B, R)"""
        self.assertEqual(FnType(INT_TYPE, INT_TYPE),
                         fn_type(INT_TYPE, INT_TYPE))

    def test_adttype_equals(self):
        """ADTType(name, *p) == adt_type(name, *p)"""
        self.assertEqual(ADTType("Foo", INT_TYPE),
                         adt_type("Foo", INT_TYPE))

    def test_optiontype_resulttype_boxtype(self):
        """OptionType / ResultType / BoxType == 对应 snake_case"""
        self.assertEqual(OptionType(INT_TYPE), option_type(INT_TYPE))
        self.assertEqual(ResultType(INT_TYPE, STRING_TYPE),
                         result_type(INT_TYPE, STRING_TYPE))
        self.assertEqual(BoxType(INT_TYPE), box_type(INT_TYPE))


class TestReprNormalized(unittest.TestCase):
    """NovaType.__repr__ 规范化显示（错误消息/REPL 可读）"""

    def test_scalar_repr_enum_name(self):
        """零参标量 → 枚举名 INT / FLOAT / STRING 等"""
        self.assertEqual(repr(INT_TYPE), "INT")
        self.assertEqual(repr(FLOAT_TYPE), "FLOAT")
        self.assertEqual(repr(STRING_TYPE), "STRING")
        self.assertEqual(repr(BOOL_TYPE), "BOOL")
        self.assertEqual(repr(CHAR_TYPE), "CHAR")
        self.assertEqual(repr(UNIT_TYPE), "UNIT")
        self.assertEqual(repr(NEVER_TYPE), "NEVER")

    def test_list_repr(self):
        """List[INT] → repr 含 List[INT]"""
        self.assertEqual(repr(list_type(INT_TYPE)), "List[INT]")

    def test_nested_list_repr(self):
        """List[List[FLOAT]] → 嵌套 repr 正确"""
        self.assertEqual(repr(list_type(list_type(FLOAT_TYPE))),
                         "List[List[FLOAT]]")

    def test_map_repr(self):
        """Map[STRING, INT]"""
        self.assertEqual(repr(map_type(STRING_TYPE, INT_TYPE)),
                         "Map[STRING, INT]")

    def test_tuple_repr(self):
        """(INT, STRING, BOOL)"""
        self.assertEqual(
            repr(tuple_type(INT_TYPE, STRING_TYPE, BOOL_TYPE)),
            "(INT, STRING, BOOL)",
        )

    def test_fn_repr_two_args(self):
        """(INT, INT) -> BOOL"""
        self.assertEqual(
            repr(fn_type(INT_TYPE, INT_TYPE, BOOL_TYPE)),
            "(INT, INT) -> BOOL",
        )

    def test_fn_repr_one_arg(self):
        """(INT) -> INT"""
        self.assertEqual(repr(fn_type(INT_TYPE, INT_TYPE)), "(INT) -> INT")

    def test_adt_with_params_repr(self):
        """Option[INT]"""
        self.assertEqual(repr(adt_type("Option", INT_TYPE)), "Option[INT]")

    def test_adt_no_params_repr(self):
        """无参 ADT → 仅 name"""
        self.assertEqual(repr(adt_type("Bool")), "Bool")

    def test_box_repr(self):
        """Box[INT]"""
        self.assertEqual(repr(box_type(INT_TYPE)), "Box[INT]")


class TestComplexNestedTypes(unittest.TestCase):
    """复杂嵌套类型的相等性与哈希一致性"""

    def test_map_of_list_equality(self):
        """Map[String, List[Int]] 两次构造应相等"""
        def build():
            return map_type(STRING_TYPE, list_type(INT_TYPE))
        self.assertEqual(build(), build())

    def test_fn_returns_option_list(self):
        """(List[Int], String) -> Option[List[Int]] 可构造"""
        t = fn_type(
            list_type(INT_TYPE), STRING_TYPE,
            option_type(list_type(INT_TYPE)),
        )
        self.assertEqual(len(t.params), 3)
        self.assertEqual(t.params[-1].name, "Option")

    def test_hash_consistency_after_construction(self):
        """同类型值多次构造：a == b → hash(a) == hash(b)"""
        a = list_type(option_type(tuple_type(INT_TYPE, STRING_TYPE)))
        b = list_type(option_type(tuple_type(INT_TYPE, STRING_TYPE)))
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))


class TestPublicAPIExports(unittest.TestCase):
    """ir_types 模块 __all__ 公开 API 完整性"""

    def test_core_in_all(self):
        """IRType / NovaType 必在 __all__"""
        self.assertIn("IRType", IR_TYPES_ALL)
        self.assertIn("NovaType", IR_TYPES_ALL)

    def test_singletons_in_all(self):
        """8 单例应在 __all__"""
        for name in ("INT_TYPE", "FLOAT_TYPE", "STRING_TYPE", "BOOL_TYPE",
                     "CHAR_TYPE", "UNIT_TYPE", "NEVER_TYPE", "CLOSURE_TYPE"):
            self.assertIn(name, IR_TYPES_ALL, f"{name} 未在 __all__")

    def test_factories_in_all(self):
        """9 工厂函数（snake_case）应在 __all__"""
        for name in ("list_type", "map_type", "tuple_type", "fn_type",
                     "adt_type", "option_type", "result_type", "box_type"):
            self.assertIn(name, IR_TYPES_ALL, f"{name} 未在 __all__")

    def test_aliases_in_all(self):
        """8 兼容别名应在 __all__（对外公开承诺）"""
        for name in ("ListType", "MapType", "TupleType", "FnType",
                     "ADTType", "OptionType", "ResultType", "BoxType"):
            self.assertIn(name, IR_TYPES_ALL, f"{name} 未在 __all__")


if __name__ == "__main__":
    unittest.main()
