"""
Nova 编程语言 - AST 节点定义

使用 Python dataclass 定义所有抽象语法树（AST）节点类型。
AST 是源代码的结构化表示，是语法分析的输出，类型检查和求值的输入。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union


# ============================================================
# 位置信息
# ============================================================

@dataclass
class Span:
    """源代码位置信息（行号、列号）"""
    line: int
    column: int


# ============================================================
# 字面量节点
# ============================================================

@dataclass
class IntLiteral:
    """整数常量，如 42"""
    value: int
    span: Optional[Span] = None


@dataclass
class FloatLiteral:
    """浮点数常量，如 3.14"""
    value: float
    span: Optional[Span] = None


@dataclass
class StringLiteral:
    """字符串常量，如 "hello" """
    value: str
    span: Optional[Span] = None


@dataclass
class CharLiteral:
    """字符常量，如 'a'"""
    value: str
    span: Optional[Span] = None


@dataclass
class BoolLiteral:
    """布尔常量，如 true / false"""
    value: bool
    span: Optional[Span] = None


@dataclass
class UnitLiteral:
    """Unit 值，即 ()"""
    span: Optional[Span] = None


# ============================================================
# 标识符和路径
# ============================================================

@dataclass
class Identifier:
    """变量/函数名标识符"""
    name: str
    span: Optional[Span] = None


# ============================================================
# 操作符表达式
# ============================================================

@dataclass
class BinaryOp:
    """二元操作：a + b, x * y, "hello" ++ "world" 等"""
    op: str
    left: Any  # Expression
    right: Any  # Expression
    span: Optional[Span] = None


@dataclass
class UnaryOp:
    """一元操作：-x, !flag"""
    op: str
    operand: Any  # Expression
    span: Optional[Span] = None


@dataclass
class PipeExpr:
    """管道操作符：expr |> f"""
    left: Any  # Expression (被管道传递的值)
    right: Any  # Expression (接收管道值的函数/表达式)
    span: Optional[Span] = None


@dataclass
class TryExpr:
    """? 操作符：用于 Option/Result 的错误传播"""
    expr: Any  # Expression
    span: Optional[Span] = None


# ============================================================
# 函数相关
# ============================================================

@dataclass
class Param:
    """函数参数定义"""
    name: str
    type_annotation: Optional[Any] = None  # TypeExpr
    span: Optional[Span] = None


@dataclass
class Lambda:
    """Lambda 匿名函数：|x, y| { x + y }"""
    params: List[Param]
    return_type: Optional[Any] = None  # TypeExpr
    body: Any = None  # Expression (单个表达式或 Block)
    span: Optional[Span] = None


@dataclass
class FnDef:
    """命名函数定义：fn add(x: Int, y: Int) -> Int { ... }"""
    name: str
    params: List[Param]
    return_type: Optional[Any] = None  # TypeExpr
    body: Any = None  # Expression (通常是 Block)
    span: Optional[Span] = None


@dataclass
class FnCall:
    """函数调用：f(x, y)"""
    callee: Any  # Expression
    args: List[Any]  # List[Expression]
    span: Optional[Span] = None


# ============================================================
# 绑定和赋值
# ============================================================

@dataclass
class LetBinding:
    """let 绑定（不可变）：let x = expr"""
    name: str
    value: Any  # Expression
    type_annotation: Optional[Any] = None  # TypeExpr
    span: Optional[Span] = None


@dataclass
class MutBinding:
    """mut 绑定（可变）：mut counter = 0"""
    name: str
    value: Any  # Expression
    type_annotation: Optional[Any] = None  # TypeExpr
    span: Optional[Span] = None


@dataclass
class Assignment:
    """赋值操作：x = expr（仅对 mut 绑定有效）"""
    name: str
    value: Any  # Expression
    span: Optional[Span] = None


# ============================================================
# 控制流
# ============================================================

@dataclass
class IfExpr:
    """if-then-else 表达式：if cond then expr1 else expr2"""
    condition: Any  # Expression
    then_branch: Any  # Expression
    else_branch: Optional[Any] = None  # Expression (可省略，默认 Unit)
    span: Optional[Span] = None


@dataclass
class MatchArm:
    """match 的一个分支"""
    pattern: Any  # Pattern
    guard: Optional[Any] = None  # 可选守卫条件
    body: Any = None  # Expression


@dataclass
class MatchExpr:
    """模式匹配表达式：match expr { pat1 -> e1, pat2 -> e2, ... }"""
    subject: Any  # Expression
    arms: List[MatchArm]
    span: Optional[Span] = None


# ============================================================
# 循环表达式
# ============================================================

@dataclass
class ForExpr:
    """for 循环表达式（作为表达式，返回列表）
    两种形式：
    1. for x in list_expr { body }         -- 遍历列表
    2. for i <- start..end { body }       -- 范围循环
    3. for i <- start..end step n { body } -- 带步长的范围循环
    """
    var_name: str
    iterable: Any  # Expression (列表或范围)
    body: Any  # Expression (通常是 Block)
    step: Optional[Any] = None  # 步长表达式（仅范围循环）
    span: Optional[Span] = None


@dataclass
class WhileExpr:
    """while 循环表达式
    while condition { body }
    体中最后一个表达式的最后一次迭代的值作为返回值
    """
    condition: Any  # Expression
    body: Any  # Expression (通常是 Block)
    span: Optional[Span] = None


@dataclass
class BreakExpr:
    """break 表达式：跳出循环"""
    span: Optional[Span] = None


@dataclass
class ContinueExpr:
    """continue 表达式：跳过当前迭代"""
    span: Optional[Span] = None


# ============================================================
# 模式（用于 match 和 let 解构）
# ============================================================

@dataclass
class PatternWildcard:
    """通配符模式：_"""
    span: Optional[Span] = None


@dataclass
class PatternInt:
    """整数模式：42"""
    value: int
    span: Optional[Span] = None


@dataclass
class PatternFloat:
    """浮点数模式：3.14"""
    value: float
    span: Optional[Span] = None


@dataclass
class PatternString:
    """字符串模式："hello" """
    value: str
    span: Optional[Span] = None


@dataclass
class PatternBool:
    """布尔模式：true / false"""
    value: bool
    span: Optional[Span] = None


@dataclass
class PatternChar:
    """字符模式：'a'"""
    value: str
    span: Optional[Span] = None


@dataclass
class PatternIdentifier:
    """变量绑定模式：x（匹配任何值并绑定到 x）"""
    name: str
    span: Optional[Span] = None


@dataclass
class PatternConstructor:
    """构造器模式：Some(x), Cons(head, tail), Circle(r)"""
    name: str
    fields: List[Any]  # List[Pattern]
    span: Optional[Span] = None


@dataclass
class PatternTuple:
    """元组模式：(a, b)"""
    elements: List[Any]  # List[Pattern]
    span: Optional[Span] = None


@dataclass
class PatternList:
    """列表字面量模式：[1, 2, 3]"""
    elements: List[Any]  # List[Pattern]
    span: Optional[Span] = None


# ============================================================
# 复合数据类型
# ============================================================

@dataclass
class ListExpr:
    """列表表达式：[1, 2, 3]"""
    elements: List[Any]  # List[Expression]
    span: Optional[Span] = None


@dataclass
class ListComprehension:
    """列表推导式：[expr for var in list] 或 [expr for var <- start..end if cond]"""
    expr: Any  # Expression (映射表达式)
    var_name: str
    iterable: Any  # Expression (列表或范围)
    filter_cond: Optional[Any] = None  # 可选过滤条件
    span: Optional[Span] = None


@dataclass
class TupleExpr:
    """元组表达式：(1, "hello", true)"""
    elements: List[Any]  # List[Expression]
    span: Optional[Span] = None


@dataclass
class MapExpr:
    """Map 表达式：{"key" => value, ...}"""
    pairs: List[tuple]  # List[(Expression, Expression)]
    span: Optional[Span] = None


@dataclass
class FieldAccess:
    """字段访问：tuple.0, obj.field"""
    target: Any  # Expression
    field: str
    span: Optional[Span] = None


# ============================================================
# 代码块和程序结构
# ============================================================

@dataclass
class Block:
    """代码块：{ stmt1; stmt2; expr }"""
    statements: List[Any]  # List[Statement/Expression]
    tail_expression: Optional[Any] = None  # 最后一个表达式（作为块返回值）
    span: Optional[Span] = None


@dataclass
class ImportDecl:
    """导入声明：import "filename.nova" """
    module_name: str
    span: Optional[Span] = None


@dataclass
class ExportDecl:
    """导出声明：export name"""
    name: str
    span: Optional[Span] = None


@dataclass
class TypeDef:
    """类型定义（ADT）：type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }"""
    name: str
    variants: List[Any]  # List[VariantDef]
    span: Optional[Span] = None


@dataclass
class VariantDef:
    """ADT 变体定义：Circle(r: Float)"""
    name: str
    fields: List[tuple]  # List[(field_name, TypeExpr)]
    span: Optional[Span] = None


@dataclass
class AliasDef:
    """类型别名：alias Point = (Float, Float)"""
    name: str
    target_type: Any  # TypeExpr
    span: Optional[Span] = None


@dataclass
class Program:
    """完整的 Nova 程序"""
    declarations: List[Any]  # List[TopLevelDecl]
    span: Optional[Span] = None


# ============================================================
# 类型注解（TypeExpr）
# ============================================================

@dataclass
class TypeInt:
    """Int 类型"""
    span: Optional[Span] = None


@dataclass
class TypeFloat:
    """Float 类型"""
    span: Optional[Span] = None


@dataclass
class TypeString:
    """String 类型"""
    span: Optional[Span] = None


@dataclass
class TypeBool:
    """Bool 类型"""
    span: Optional[Span] = None


@dataclass
class TypeChar:
    """Char 类型"""
    span: Optional[Span] = None


@dataclass
class TypeUnit:
    """Unit 类型"""
    span: Optional[Span] = None


@dataclass
class TypeIdentifier:
    """命名类型引用：Int, Shape, MyType"""
    name: str
    span: Optional[Span] = None


@dataclass
class TypeGeneric:
    """泛型类型：List[Int], Map[String, Int], Option[Bool]"""
    base: str  # 类型名，如 "List"
    params: List[Any]  # List[TypeExpr]
    span: Optional[Span] = None


@dataclass
class TypeTuple:
    """元组类型：(Int, String, Bool)"""
    elements: List[Any]  # List[TypeExpr]
    span: Optional[Span] = None


@dataclass
class TypeFn:
    """函数类型：Fn[Int, Int, Bool] = (Int, Int) -> Bool"""
    param_types: List[Any]  # List[TypeExpr]
    return_type: Any  # TypeExpr
    span: Optional[Span] = None
