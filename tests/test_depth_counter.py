"""
测试 _call_depth 和 _eval_depth 计数器在异常路径下的正确性。

验证：当递归超限抛出异常后，深度计数器能正确回退，
确保 finally 块统一处理所有清理路径，无双重递减或泄漏。
"""

import pytest
from nova.lexer import Lexer
from nova.parser import Parser
from nova.evaluator import Evaluator
from nova.errors import RuntimeError_


def _parse(source: str):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


class TestCallDepthCleanup:
    """测试 _call_depth 在递归超限后的正确回退"""

    def test_call_depth_resets_after_overflow(self):
        """递归调用超限后，_call_depth 应回到 0（进入前的状态）"""
        source = """
        fn recurse(n) {
            recurse(n + 1)
        }
        recurse(0)
        """
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        # 降低阈值以便快速触发
        evaluator.MAX_CALL_DEPTH = 10

        with pytest.raises(RuntimeError_, match="栈溢出"):
            evaluator.eval_program(ast)

        # 异常抛出后，_call_depth 必须回到 0
        assert evaluator._call_depth == 0, (
            f"栈溢出后 _call_depth 应为 0，实际为 {evaluator._call_depth}"
        )

    def test_call_depth_normal_execution(self):
        """正常函数调用后，_call_depth 应回到 0"""
        source = """
        fn add(a, b) {
            a + b
        }
        add(1, 2)
        """
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.eval_program(ast)
        assert evaluator._call_depth == 0

    def test_call_depth_nested_normal(self):
        """嵌套函数调用正常返回后，_call_depth 应回到 0"""
        source = """
        fn inner(n) { n + 1 }
        fn outer(n) { inner(n) + 1 }
        outer(5)
        """
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.eval_program(ast)
        assert evaluator._call_depth == 0

    def test_call_depth_env_restored_after_overflow(self):
        """递归超限后，环境也应被正确恢复（env 指针不变）"""
        source = """
        fn recurse(n) {
            recurse(n + 1)
        }
        recurse(0)
        """
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.MAX_CALL_DEPTH = 10
        old_env = evaluator.env

        with pytest.raises(RuntimeError_, match="栈溢出"):
            evaluator.eval_program(ast)

        # 环境应恢复到调用前的状态
        assert evaluator.env is old_env


class TestEvalDepthCleanup:
    """测试 _eval_depth 在表达式嵌套超限后的正确回退"""

    def test_eval_depth_resets_after_overflow(self):
        """表达式嵌套超限后，_eval_depth 应回到 0"""
        # 构造深度嵌套的算术表达式
        depth = 50
        expr = "1" + " + 1" * depth
        source = expr
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        # 降低阈值以便快速触发
        evaluator.MAX_EVAL_DEPTH = 10

        with pytest.raises(RuntimeError_, match="表达式嵌套过深"):
            evaluator.eval_program(ast)

        # 异常抛出后，_eval_depth 必须回到 0
        assert evaluator._eval_depth == 0, (
            f"表达式嵌套超限后 _eval_depth 应为 0，实际为 {evaluator._eval_depth}"
        )

    def test_eval_depth_normal_execution(self):
        """正常表达式求值后，_eval_depth 应回到 0"""
        source = "1 + 2 * 3"
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.eval_program(ast)
        assert evaluator._eval_depth == 0

    def test_eval_depth_nested_expr_normal(self):
        """深层嵌套表达式正常求值后，_eval_depth 应回到 0"""
        depth = 20
        expr = "1" + " + 1" * depth
        source = expr
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.eval_program(ast)
        assert evaluator._eval_depth == 0

    def test_eval_depth_after_call_overflow_independent(self):
        """_call_depth 溢出不应影响 _eval_depth 的归零"""
        source = """
        fn recurse(n) {
            recurse(n + 1)
        }
        recurse(0)
        """
        ast = _parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.MAX_CALL_DEPTH = 10

        with pytest.raises(RuntimeError_, match="栈溢出"):
            evaluator.eval_program(ast)

        # 两者都应归零
        assert evaluator._call_depth == 0
        assert evaluator._eval_depth == 0
