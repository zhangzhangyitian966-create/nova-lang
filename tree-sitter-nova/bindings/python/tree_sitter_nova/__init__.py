"""Nova Tree-sitter Python binding

Provides a Python interface to the Nova Tree-sitter parser.
Requires the compiled shared library (tree_sitter_nova.so) to be available.
"""

import os

try:
    from tree_sitter import Language, Parser
except ImportError:
    raise ImportError(
        "tree-sitter Python package is required. "
        "Install it with: pip install tree-sitter"
    )

# Try to locate the compiled shared library
_possible_paths = [
    os.path.join(
        os.path.dirname(__file__), "..", "..", "build", "Release", "tree_sitter_nova.so"
    ),
    os.path.join(
        os.path.dirname(__file__), "..", "..", "build", "Debug", "tree_sitter_nova.so"
    ),
    os.path.join(os.path.dirname(__file__), "..", "..", "tree_sitter_nova.so"),
    os.path.join(os.path.dirname(__file__), "..", "..", "tree_sitter_nova.dylib"),
]

_lib_path = None
for _path in _possible_paths:
    if os.path.exists(_path):
        _lib_path = _path
        break

if _lib_path is None:
    raise FileNotFoundError(
        "Cannot find compiled tree_sitter_nova shared library. "
        "Please run 'tree-sitter generate' and 'tree-sitter build' first."
    )

NOVA_LANGUAGE = Language(_lib_path, "nova")


def create_parser() -> Parser:
    """Create a new Tree-sitter parser configured for Nova."""
    parser = Parser(NOVA_LANGUAGE)
    return parser


def parse(source: bytes) -> "tree_sitter.Tree":
    """Parse Nova source code and return a syntax tree.

    Args:
        source: The Nova source code as bytes (use source.encode('utf-8')).

    Returns:
        A tree_sitter.Tree representing the parsed source.
    """
    parser = create_parser()
    return parser.parse(source)


def parse_incremental(
    tree: "tree_sitter.Tree",
    source: bytes,
    edit: "tree_sitter.InputEdit",
) -> "tree_sitter.Tree":
    """Incrementally re-parse a modified source using the previous tree.

    Args:
        tree: The previous syntax tree.
        source: The updated source code as bytes.
        edit: The InputEdit describing the change.

    Returns:
        A new tree_sitter.Tree reflecting the edits.
    """
    parser = create_parser()
    return parser.parse(source, tree)
