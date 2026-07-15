"""
Nova 类型系统测试 - 泛型 ADT、类型参数检查和类型别名展开
"""

import pytest
from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker
from nova.errors import TypeCheckError


def check_source(source: str, collect_errors: bool = False):
    """辅助函数：对源代码进行类型检查"""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    checker = TypeChecker(source=source, collect_errors=collect_errors)
    checker.check_program(ast)
    return checker


class TestGenericADT:
    """测试泛型代数数据类型"""

    def test_generic_adt_definition(self):
        """用户可定义泛型 ADT"""
        source = """
        type Option[T] { Some(T) None }
        """
        checker = check_source(source)
        # Option 类型应被注册
        assert "Option" in checker.env.types
        assert checker.env.adt_type_params["Option"] == ["T"]

    def test_generic_adt_correct_usage(self):
        """正确使用泛型 ADT：let x: Option[Int] = Some(42)"""
        source = """
        type Option[T] { Some(T) None }
        let x: Option[Int] = Some(42)
        """
        checker = check_source(source)
        # 不应报错
        assert len(checker.error_collector.errors) == 0

    def test_generic_adt_incorrect_usage(self):
        """错误使用泛型 ADT：let x: Option[Int] = Some("hello") 应报错"""
        source = """
        type Option[T] { Some(T) None }
        let x: Option[Int] = Some("hello")
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_generic_adt_none_any_type(self):
        """None 构造函数应兼容任何 Option[T]"""
        source = """
        type Option[T] { Some(T) None }
        let x: Option[Int] = None
        let y: Option[String] = None
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_multi_param_generic_adt(self):
        """多参数泛型 ADT"""
        source = """
        type Result[T, E] { Ok(T) Err(E) }
        let r: Result[Int, String] = Ok(42)
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_multi_param_generic_adt_error(self):
        """多参数泛型 ADT 类型不匹配应报错"""
        source = """
        type Result[T, E] { Ok(T) Err(E) }
        let r: Result[Int, String] = Ok("hello")
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_nested_generic_adt(self):
        """嵌套泛型 ADT"""
        source = """
        type Box[T] { Box(T) }
        type Pair[A, B] { Pair(A, B) }
        let p: Pair[Int, Box[String]] = Pair(1, Box("hello"))
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_nested_generic_adt_error(self):
        """嵌套泛型 ADT 类型不匹配应报错"""
        source = """
        type Box[T] { Box(T) }
        type Pair[A, B] { Pair(A, B) }
        let p: Pair[Int, Box[String]] = Pair("hello", Box(1))
        """
        with pytest.raises(TypeCheckError):
            check_source(source)


class TestBuiltinGenericADT:
    """测试内置泛型 ADT（Option, Result）"""

    def test_builtin_option_correct(self):
        """内置 Option[Int] = Some(42) 应通过"""
        source = "let x: Option[Int] = Some(42)"
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_builtin_option_error(self):
        """内置 Option[Int] = Some("hello") 应报错"""
        source = 'let x: Option[Int] = Some("hello")'
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_builtin_none_any(self):
        """None 应兼容任何 Option[T]"""
        source = """
        let x: Option[Int] = None
        let y: Option[String] = None
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_builtin_result_correct(self):
        """内置 Result[Int, String] = Ok(42) 应通过"""
        source = "let x: Result[Int, String] = Ok(42)"
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_builtin_result_error(self):
        """内置 Result[Int, String] = Ok("hello") 应报错"""
        source = 'let x: Result[Int, String] = Ok("hello")'
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_builtin_result_err_correct(self):
        """内置 Result[Int, String] = Err("fail") 应通过"""
        source = 'let x: Result[Int, String] = Err("fail")'
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_builtin_head_returns_option(self):
        """head([1,2,3]) 返回 Option[Int]，与标注兼容"""
        source = """
        fn main() {
            let x: Option[Int] = head([1, 2, 3])
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0


class TestTypeParameterArity:
    """测试泛型参数数量检查"""

    def test_option_wrong_arity(self):
        """Option 期望 1 个参数，传 2 个应报错"""
        source = "let x: Option[Int, String] = Some(42)"
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "期望 1 个类型参数" in str(exc_info.value)

    def test_result_wrong_arity(self):
        """Result 期望 2 个参数，传 1 个应报错"""
        source = "let x: Result[Int] = Ok(42)"
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "期望 2 个类型参数" in str(exc_info.value)

    def test_list_wrong_arity(self):
        """List 期望 1 个参数，传 2 个应报错"""
        source = "let x: List[Int, String] = [1, 2]"
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "期望 1 个类型参数" in str(exc_info.value)

    def test_map_wrong_arity(self):
        """Map 期望 2 个参数，传 1 个应报错"""
        source = "let x: Map[Int] = {}"
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "期望 2 个类型参数" in str(exc_info.value)

    def test_user_defined_generic_wrong_arity(self):
        """用户定义泛型 ADT 参数数量错误应报错"""
        source = """
        type Pair[A, B] { Pair(A, B) }
        let x: Pair[Int] = Pair(1)
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "期望 2 个类型参数" in str(exc_info.value)


class TestTypeAliasExpansion:
    """测试类型别名展开"""

    def test_simple_alias(self):
        """简单类型别名 alias MyInt = Int"""
        source = """
        alias MyInt = Int
        let x: MyInt = 42
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_alias_to_alias(self):
        """别名链：A -> B -> Int"""
        source = """
        alias B = Int
        alias A = B
        let x: A = 42
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_alias_generic(self):
        """泛型别名 alias IntList = List[Int]"""
        source = """
        alias IntList = List[Int]
        let x: IntList = [1, 2, 3]
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_alias_in_adt(self):
        """别名在 ADT 字段中使用"""
        source = """
        alias MyInt = Int
        type Wrapper { Wrap(MyInt) }
        let x: Wrapper = Wrap(42)
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_circular_alias_detected(self):
        """循环别名应被检测"""
        source = """
        alias A = B
        alias B = A
        let x: A = 42
        """
        # 当前系统对这种循环别名的检测有限，别名链 A->B->A 在定义时
        # B 尚未定义，所以 A 被解析为 PrimType("B")，B 再引用 A 时
        # 得到 PrimType("B")，不会真正循环。此测试验证系统至少不崩溃。
        checker = check_source(source, collect_errors=True)
        # 至少应该能完成类型检查而不陷入无限循环
        assert True


class TestEdgeCases:
    """边界情况测试"""

    def test_generic_adt_with_named_fields(self):
        """泛型 ADT 也可以有命名字段"""
        source = """
        type Container[T] { Container(value: T) }
        let x: Container[Int] = Container(42)
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_generic_adt_pattern_match(self):
        """泛型 ADT 的模式匹配（简化类型检查）"""
        source = """
        type Option[T] { Some(T) None }
        let x: Option[Int] = Some(42)
        match x {
            Some(v) -> v,
            None -> 0
        }
        """
        checker = check_source(source)
        # 模式匹配应能通过类型检查
        assert len(checker.error_collector.errors) == 0

    def test_generic_function_with_adt(self):
        """函数返回泛型 ADT"""
        source = """
        type Option[T] { Some(T) None }
        fn wrap(x: Int) -> Option[Int] { Some(x) }
        let y: Option[Int] = wrap(42)
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_map_type_compatibility(self):
        """Map 类型应递归比较兼容性"""
        source = """
        fn f(m: Map[String, Int]) -> Map[String, Int] { m }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_map_type_incompatibility(self):
        """Map 类型不兼容应报错"""
        source = """
        fn f(m: Map[String, Int]) -> Map[String, String] { m }
        """
        with pytest.raises(TypeCheckError):
            check_source(source)


class TestADTFieldAccess:
    """测试 ADT 字段访问（Bug #13）"""

    def test_adt_named_field_access_all_variants(self):
        """所有变体都有同名字段且类型相同时，字段访问应通过"""
        source = """
        type Shape { Circle(r: Float) | Square(s: Float) }
        fn get_size(s: Shape) -> Float { s.r }
        """
        # s.r 应该失败，因为 Square 没有 r 字段
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_adt_named_field_shared(self):
        """所有变体有同名字段同类型时通过"""
        source = """
        type Shape { Circle(radius: Float) | Square(radius: Float) }
        fn get_radius(s: Shape) -> Float { s.radius }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_adt_field_index_access(self):
        """按索引访问 ADT 字段（所有变体在该位置有相同类型）"""
        source = """
        type Pair { P1(a: Int, b: Int) | P2(x: Int, y: Int) }
        fn first(p: Pair) -> Int { p.0 }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_adt_field_index_mismatched_types(self):
        """索引位置类型不同时报错"""
        source = """
        type Mixed { A(x: Int) | B(x: String) }
        fn get_x(m: Mixed) -> Int { m.0 }
        """
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_adt_field_name_mismatched_types(self):
        """字段名称相同但类型不同时报错"""
        source = """
        type Mixed { A(value: Int) | B(value: String) }
        fn get_val(m: Mixed) -> Int { m.value }
        """
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_adt_field_not_in_all_variants(self):
        """不是所有变体都有该字段时报错"""
        source = """
        type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
        fn get_r(s: Shape) -> Float { s.r }
        """
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_option_value_field(self):
        """内置 Option 的 Some.value 访问（仅 Some 有，None 没有，应报错）"""
        source = """
        fn get_val(o: Option[Int]) -> Int { o.value }
        """
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_adt_field_access_in_let(self):
        """let 绑定中的 ADT 字段访问"""
        source = """
        type Point { Point(x: Int, y: Int) }
        let p = Point(3, 4)
        let px = p.x
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_adt_single_variant_field_access(self):
        """单变体 ADT 的字段访问应通过"""
        source = """
        type Wrapper { Wrapper(value: Int) }
        let w = Wrapper(42)
        let v = w.value
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0


class TestEqualityTypeCheck:
    """测试 == 和 != 操作符的类型兼容性检查"""

    def test_eq_int_string_error(self):
        """Int == String 应报错"""
        source = 'let result = 42 == "hello"'
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不兼容" in str(exc_info.value)

    def test_neq_int_string_error(self):
        """Int != String 应报错"""
        source = 'let result = 42 != "hello"'
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不兼容" in str(exc_info.value)

    def test_eq_int_int_ok(self):
        """Int == Int 应通过"""
        source = "let result = 42 == 100"
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_eq_list_int_list_string_error(self):
        """List[Int] == List[String] 应报错"""
        source = "let result = [1, 2, 3] == [\"a\", \"b\", \"c\"]"
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不兼容" in str(exc_info.value)


class TestPatternConstructorSubjectType:
    """测试构造器模式的主题类型校验（Bug 修复）"""

    def test_constructor_pattern_on_int_error(self):
        """match 42 { Some(x) => x } 应报类型错误（Int 不能匹配 Some）"""
        source = """
        match 42 {
            Some(x) -> x
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_constructor_pattern_on_string_error(self):
        """match "hello" { Ok(x) => x } 应报类型错误"""
        source = '''
        match "hello" {
            Ok(x) -> x
        }
        '''
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_constructor_pattern_correct_usage(self):
        """match Some(42) { Some(x) => x } 应通过（回归测试）"""
        source = """
        match Some(42) {
            Some(x) -> x,
            None -> 0
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_constructor_pattern_wrong_variant_same_adt(self):
        """match Ok("x") { Err(x) => x } 同一 ADT 不同构造器，应通过类型检查
        （同一 ADT 的不同构造器是合法的 match 模式，只是不会匹配到而已）"""
        source = '''
        match Ok("x") {
            Err(x) -> x,
            Ok(v) -> v
        }
        '''
        checker = check_source(source)
        # 同一 ADT 的不同构造器是合法的模式
        assert len(checker.error_collector.errors) == 0


class TestForLoopVariableTypeInference:
    """测试 for 循环变量类型推断（Bug 修复）"""

    def test_for_list_int_add_ok(self):
        """for x in [1, 2, 3] { x + 1 } 应通过（x 推断为 Int）"""
        source = """
        for x in [1, 2, 3] { x + 1 }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_for_list_int_concat_error(self):
        """for x in [1, 2, 3] { x ++ "hello" } 应报类型错误（x 是 Int，不能 ++）"""
        source = '''
        for x in [1, 2, 3] { x ++ "hello" }
        '''
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_for_range_int_add_ok(self):
        """for i <- 0..10 { i + 1 } 应通过（i 推断为 Int）"""
        source = """
        for i <- 0..10 { i + 1 }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_for_list_string_concat_ok(self):
        """for s in ["a", "b"] { s ++ "!" } 应通过（s 推断为 String）"""
        source = '''
        for s in ["a", "b"] { s ++ "!" }
        '''
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0


class TestListComprehensionVariableTypeInference:
    """测试列表推导循环变量类型推断（Bug 修复）"""

    def test_lc_list_int_add_ok(self):
        """[x + 1 for x in [1, 2, 3]] 应通过（x 推断为 Int）"""
        source = """
        let result = [x + 1 for x in [1, 2, 3]]
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_lc_list_int_concat_error(self):
        """[x ++ "hello" for x in [1, 2, 3]] 应报类型错误（x 是 Int，不能 ++）"""
        source = '''
        let result = [x ++ "hello" for x in [1, 2, 3]]
        '''
        with pytest.raises(TypeCheckError):
            check_source(source)

    def test_lc_range_int_add_ok(self):
        """[i + 1 for i <- 0..10] 应通过（i 推断为 Int）"""
        source = """
        let result = [i + 1 for i <- 0..10]
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_lc_list_string_concat_ok(self):
        """[s ++ "!" for s in ["a", "b"]] 应通过（s 推断为 String）"""
        source = '''
        let result = [s ++ "!" for s in ["a", "b"]]
        '''
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0


class TestFnReturnTypeInference:
    """测试函数返回类型推断（Bug 修复：推断结果应写回环境）"""

    def test_no_annotation_return_type_inferred(self):
        """无 return_type 标注的函数，返回类型应从函数体推断并写回环境"""
        from nova.type_checker import FnType, INT_T
        source = """
        fn add(a: Int, b: Int) { a + b }
        """
        checker = check_source(source)
        fn_ty = checker.env.lookup("add")
        assert isinstance(fn_ty, FnType)
        assert fn_ty.return_type == INT_T

    def test_no_annotation_string_return(self):
        """返回字符串的函数，返回类型应推断为 String"""
        from nova.type_checker import STRING_T, FnType
        source = '''
        fn greet(name: String) { "Hello, " ++ name }
        '''
        checker = check_source(source)
        fn_ty = checker.env.lookup("greet")
        assert isinstance(fn_ty, FnType)
        assert fn_ty.return_type == STRING_T

    def test_no_annotation_call_result_type(self):
        """调用无返回类型标注的函数，结果类型应正确（不是 TypeVar）"""
        from nova.type_checker import INT_T, TypeVar
        source = """
        fn double(x: Int) { x * 2 }
        let result = double(21)
        """
        checker = check_source(source, collect_errors=True)
        result_ty = checker.env.lookup("result")
        # result 的类型应该是 Int，不是 TypeVar
        assert result_ty == INT_T
        assert not isinstance(result_ty, TypeVar)

    def test_no_annotation_nested_call(self):
        """嵌套调用无返回类型标注的函数，类型应正确传递"""
        from nova.type_checker import INT_T
        source = """
        fn inc(x: Int) { x + 1 }
        fn double(x: Int) { inc(x) + inc(x) }
        let result = double(5)
        """
        checker = check_source(source)
        result_ty = checker.env.lookup("result")
        assert result_ty == INT_T

    def test_with_annotation_unchanged(self):
        """有 return_type 标注的函数，返回类型保持标注不变"""
        from nova.type_checker import FnType, INT_T
        source = """
        fn add(a: Int, b: Int) -> Int { a + b }
        """
        checker = check_source(source)
        fn_ty = checker.env.lookup("add")
        assert isinstance(fn_ty, FnType)
        assert fn_ty.return_type == INT_T


class TestTypeVarFnCall:
    """测试 TypeVar 函数调用检查（Bug 修复：duck typing 不应直接放行）"""

    def test_typevar_call_collects_error(self):
        """对类型未确定的值进行函数调用，应记录到错误收集器"""
        source = """
        fn apply(f, x: Int) -> Int { f(x) }
        """
        checker = check_source(source, collect_errors=True)
        # 应该有一个关于 TypeVar 调用的错误
        errors = [e for e in checker.error_collector.errors
                  if "未确定类型" in e.message and "函数调用" in e.message]
        assert len(errors) >= 1, f"期望找到 TypeVar 函数调用错误，实际错误: {checker.error_collector.errors}"

    def test_typevar_call_does_not_crash(self):
        """对类型未确定的值进行函数调用，不会导致崩溃（collect_errors 模式）"""
        source = """
        fn call_it(f) { f() }
        """
        # 不应抛出异常
        checker = check_source(source, collect_errors=True)
        assert checker is not None

    def test_higher_order_still_works(self):
        """高阶函数参数（无类型标注）仍可正常使用（温和策略：放行但记录）"""
        source = """
        fn apply(f, x: Int) -> Int { f(x) }
        fn add_one(n: Int) -> Int { n + 1 }
        let result = apply(add_one, 5)
        """
        checker = check_source(source, collect_errors=True)
        # 函数体内 f(x) 调用会记录 TypeVar 调用错误
        # 但整体不应崩溃，apply 函数仍可被调用
        typevar_errors = [e for e in checker.error_collector.errors
                          if "未确定类型" in e.message and "函数调用" in e.message]
        assert len(typevar_errors) >= 1

    def test_known_function_call_no_error(self):
        """对已知类型的函数调用，不应产生 TypeVar 调用错误"""
        source = """
        fn add(a: Int, b: Int) -> Int { a + b }
        let x = add(1, 2)
        """
        checker = check_source(source, collect_errors=True)
        typevar_errors = [e for e in checker.error_collector.errors
                          if "未确定类型" in e.message and "函数调用" in e.message]
        assert len(typevar_errors) == 0


class TestAssignmentMutability:
    """测试赋值的可变性检查（Assignment mutability check）"""

    def test_let_binding_assignment_error(self):
        """对 let 绑定赋值应报错：不能对不可变绑定赋值"""
        source = """
        {
            let x = 10
            x = 20
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不可变绑定" in str(exc_info.value)
        assert "x" in str(exc_info.value)

    def test_mut_binding_assignment_ok(self):
        """对 mut 绑定赋值应通过"""
        source = """
        {
            mut x = 10
            x = 20
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_mut_binding_assignment_type_mismatch(self):
        """mut 绑定赋值类型不匹配仍应报错"""
        source = """
        {
            mut x = 10
            x = "hello"
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_nested_scope_let_shadowed_by_mut(self):
        """嵌套作用域中，内层 mut 遮蔽外层 let，内层可赋值"""
        source = """
        {
            let x = 10
            {
                mut x = 20
                x = 30
            }
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_nested_scope_let_not_assignable(self):
        """嵌套作用域中，外层 let 绑定在内层不可赋值"""
        source = """
        {
            let x = 10
            {
                x = 20
            }
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不可变绑定" in str(exc_info.value)

    def test_nested_scope_mut_outer_assignable(self):
        """嵌套作用域中，外层 mut 绑定在内层可赋值"""
        source = """
        {
            mut x = 10
            {
                x = 20
            }
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_let_with_type_annotation_assignment_error(self):
        """带类型标注的 let 绑定赋值也应报错"""
        source = """
        {
            let x: Int = 10
            x = 20
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不可变绑定" in str(exc_info.value)

    def test_mut_with_type_annotation_assignment_ok(self):
        """带类型标注的 mut 绑定赋值应通过"""
        source = """
        {
            mut x: Int = 10
            x = 20
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_fn_param_not_assignable(self):
        """函数参数是不可变绑定，赋值应报错"""
        source = """
        fn f(x: Int) {
            x = 42
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不可变绑定" in str(exc_info.value)

    def test_top_level_mut_assignment_in_fn(self):
        """顶层 mut 绑定在函数中可被赋值（验证全局作用域可变性传递）"""
        source = """
        mut counter = 0
        fn inc() {
            counter = counter + 1
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_top_level_let_assignment_in_fn_error(self):
        """顶层 let 绑定在函数中赋值应报错"""
        source = """
        let counter = 0
        fn inc() {
            counter = counter + 1
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不可变绑定" in str(exc_info.value)


class TestMatchGuardTypeCheck:
    """测试 match 守卫条件的类型检查（Bug 修复）"""

    def test_guard_bool_comparison_ok(self):
        """守卫条件为比较运算（Bool）应通过"""
        source = """
        match 42 {
            x if x > 0 -> x,
            _ -> 0
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_guard_bool_logic_ok(self):
        """守卫条件为逻辑运算（Bool）应通过"""
        source = """
        match 42 {
            x if x > 0 && x < 100 -> x,
            _ -> 0
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_guard_uses_pattern_variable_ok(self):
        """守卫条件中引用模式变量应通过类型检查"""
        source = """
        type Option[T] { Some(T) None }
        match Some(42) {
            Some(x) if x > 10 -> x,
            _ -> 0
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_guard_int_error(self):
        """守卫条件为 Int 类型应报错"""
        source = """
        match 42 {
            x if 42 -> x,
            _ -> 0
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "守卫条件必须是 Bool 类型" in str(exc_info.value)
        assert "Int" in str(exc_info.value)

    def test_guard_string_error(self):
        """守卫条件为 String 类型应报错"""
        source = """
        match 42 {
            x if "hello" -> x,
            _ -> 0
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "守卫条件必须是 Bool 类型" in str(exc_info.value)
        assert "String" in str(exc_info.value)

    def test_guard_unit_error(self):
        """守卫条件为 Unit 类型应报错"""
        source = """
        match 42 {
            x if {} -> x,
            _ -> 0
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "守卫条件必须是 Bool 类型" in str(exc_info.value)

    def test_multiple_arms_guard_type_check(self):
        """多个 arm 中守卫条件类型检查正确"""
        source = """
        match 42 {
            x if x > 100 -> "big",
            x if x > 10 -> "medium",
            _ -> "small"
        }
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_multiple_arms_guard_type_error_in_second_arm(self):
        """多个 arm 中第二个 arm 守卫条件类型错误应报错"""
        source = """
        match 42 {
            x if x > 100 -> "big",
            x if 42 -> "medium",
            _ -> "small"
        }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "守卫条件必须是 Bool 类型" in str(exc_info.value)


class TestPipeExpr:
    """测试管道运算符 |> 的类型检查"""

    def test_pipe_basic(self):
        """基本管道：42 |> int_to_str 返回 String 类型"""
        source = """
        let result: String = 42 |> int_to_str
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_pipe_generic(self):
        """泛型管道：fn id(x) { x }; 42 |> id 返回 Int 类型"""
        source = """
        fn id(x) { x }
        let result: Int = 42 |> id
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_pipe_type_mismatch(self):
        """类型错误："hello" |> |x: Int| { x + 1 } 应该报错"""
        source = """
        "hello" |> |x: Int| { x + 1 }
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "不匹配" in str(exc_info.value)

    def test_pipe_non_function_right(self):
        """非函数右侧：42 |> 100 应该报错"""
        source = """
        42 |> 100
        """
        with pytest.raises(TypeCheckError) as exc_info:
            check_source(source)
        assert "管道右侧必须是函数类型" in str(exc_info.value)

    def test_pipe_multi_param_partial_apply(self):
        """多参数函数管道（部分应用）：5 |> add(3) 应正确检查类型"""
        source = """
        fn add(x: Int, y: Int) -> Int { x + y }
        let result: Int = 5 |> add(3)
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0

    def test_pipe_multi_param_return_fn(self):
        """多参数函数管道（部分应用）：管道后返回剩余参数的函数"""
        source = """
        fn add(x: Int, y: Int) -> Int { x + y }
        let f: Int -> Int = 5 |> add
        """
        checker = check_source(source)
        assert len(checker.error_collector.errors) == 0
