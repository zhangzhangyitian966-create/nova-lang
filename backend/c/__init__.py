"""Nova C 后端包（架构手术 B Phase 1 · §2.2 路径隔离）。"""

from .lir_to_c import LIRCBackend  # noqa: F401

__all__ = ["LIRCBackend"]
