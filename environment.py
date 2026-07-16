"""
Nova 编程语言 - 环境管理

实现作用域链（嵌套环境）和变量绑定/查找机制。
每个作用域都有自己的变量绑定，查找时沿作用域链向上搜索。
支持不可变绑定和可变绑定。
"""

from typing import Dict, Optional, Any, List


class BindingInfo:
    """绑定信息：记录一个变量的值和可变性"""

    def __init__(self, name: str, value: Any, mutable: bool = False):
        self.name = name
        self.value = value
        self.mutable = mutable


class Environment:
    """Nova 运行时环境（作用域）"""

    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.bindings: Dict[str, BindingInfo] = {}

    def define(self, name: str, value: Any, mutable: bool = False):
        """在当前作用域定义绑定"""
        self.bindings[name] = BindingInfo(name, value, mutable)

    def lookup(self, name: str) -> Any:
        """查找变量值（沿作用域链向上搜索）"""
        if name in self.bindings:
            return self.bindings[name].value
        if self.parent is not None:
            return self.parent.lookup(name)
        raise NameError(f"未定义的变量 '{name}'")

    def lookup_binding(self, name: str) -> BindingInfo:
        """查找绑定信息（包含可变性等元数据）"""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup_binding(name)
        raise NameError(f"未定义的变量 '{name}'")

    def assign(self, name: str, value: Any):
        """对变量赋值（必须找到可变绑定）"""
        if name in self.bindings:
            binding = self.bindings[name]
            if not binding.mutable:
                raise RuntimeError(f"变量 '{name}' 不可变，无法赋值")
            binding.value = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise NameError(f"未定义的变量 '{name}'")

    def child(self) -> "Environment":
        """创建子作用域"""
        return Environment(parent=self)

    def all_bindings(self) -> Dict[str, Any]:
        """获取当前作用域及所有父作用域的所有绑定（用于调试）"""
        result = {}
        if self.parent:
            result.update(self.parent.all_bindings())
        result.update({k: v.value for k, v in self.bindings.items()})
        return result
