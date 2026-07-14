/**
 * Nova Programming Language Grammar for Tree-sitter
 *
 * Nova is an expression-oriented, statically-typed, functional-core language.
 * This grammar defines the complete syntax including:
 *   - Declarations: let, mut, fn, type, alias, import, export
 *   - Expressions: pipe, logical, comparison, arithmetic, unary, call, field, primary
 *   - Control flow: if, match, for, while, break, continue
 *   - Types: Int, Float, String, Bool, Char, Unit, List, Map, Tuple, Function, ADT
 *   - Patterns: literal, wildcard, binding, constructor, tuple, list
 *   - Lambda: |params| expr
 */

module.exports = grammar({
  name: 'nova',

  extras: $ => [
    /\s/,
    $.comment,
  ],

  inline: $ => [
    $._expression,
    $._type,
  ],

  conflicts: $ => [
    [$.call_expr, $.primary_expr],
    [$.lambda, $.pipe_expr],
  ],

  supertypes: $ => [
    $._expression,
    $._type,
    $._pattern,
  ],

  rules: {

    // ============================================================
    // Top-level
    // ============================================================

    source_file: $ => repeat($._expression),

    // ============================================================
    // Declarations (treated as expressions in expression-oriented language)
    // ============================================================

    let_binding: $ => seq(
      'let',
      field('name', $.identifier),
      optional(seq(':', field('type_annotation', $._type))),
      '=',
      field('value', $._expression),
    ),

    mut_binding: $ => seq(
      'mut',
      field('name', $.identifier),
      optional(seq(':', field('type_annotation', $._type))),
      '=',
      field('value', $._expression),
    ),

    fn_def: $ => seq(
      'fn',
      field('name', $.identifier),
      '(',
      optional(seq(
        field('parameters', $.parameters),
      )),
      ')',
      optional(seq('->', field('return_type', $._type))),
      field('body', $.block_expr),
    ),

    parameters: $ => prec.right(seq(
      $.parameter,
      repeat(seq(',', $.parameter)),
    )),

    parameter: $ => seq(
      field('name', $.identifier),
      optional(seq(':', field('type', $._type))),
    ),

    type_def: $ => seq(
      'type',
      field('name', $.identifier),
      '{',
      optional(seq(
        $.variant_def,
        repeat(seq('|', $.variant_def)),
      )),
      '}',
    ),

    variant_def: $ => seq(
      field('name', $.identifier),
      optional(seq(
        '(',
        optional(seq(
          $.variant_field,
          repeat(seq(',', $.variant_field)),
        )),
        ')',
      )),
    ),

    variant_field: $ => seq(
      field('name', $.identifier),
      ':',
      field('type', $._type),
    ),

    alias_def: $ => seq(
      'alias',
      field('name', $.identifier),
      '=',
      field('target', $._type),
    ),

    import_decl: $ => seq(
      'import',
      field('module', $.string_literal),
    ),

    export_decl: $ => seq(
      'export',
      field('name', $.identifier),
    ),

    // ============================================================
    // Expressions (by precedence, lowest to highest)
    // ============================================================

    _expression: $ => choice(
      $.pipe_expr,
      $.or_expr,
      $.and_expr,
      $.equality_expr,
      $.comparison_expr,
      $.additive_expr,
      $.multiplicative_expr,
      $.concat_expr,
      $.unary_expr,
      $.call_expr,
      $.index_expr,
      $.field_expr,
      $.primary_expr,
      // Declarations at expression level
      $.let_binding,
      $.mut_binding,
      $.fn_def,
      $.type_def,
      $.alias_def,
      $.import_decl,
      $.export_decl,
      // Control flow
      $.for_expr,
      $.while_expr,
      $.if_expr,
      $.match_expr,
      $.block_expr,
      // Special
      $.lambda,
      $.break_expr,
      $.continue_expr,
      $.list_comprehension,
      $.assignment_expr,
    ),

    // Pipe: expr |> fn_call  (lowest precedence)
    pipe_expr: $ => prec.left(PREC.PIPE, seq(
      field('left', $._expression),
      '|>',
      field('right', $._expression),
    )),

    // Logical OR: expr || expr
    or_expr: $ => prec.left(PREC.OR, seq(
      field('left', $._expression),
      '||',
      field('right', $._expression),
    )),

    // Logical AND: expr && expr
    and_expr: $ => prec.left(PREC.AND, seq(
      field('left', $._expression),
      '&&',
      field('right', $._expression),
    )),

    // Equality: expr == expr, expr != expr
    equality_expr: $ => prec.left(PREC.EQUALITY, seq(
      field('left', $._expression),
      field('operator', choice('==', '!=')),
      field('right', $._expression),
    )),

    // Comparison: expr < expr, expr > expr, expr <= expr, expr >= expr
    comparison_expr: $ => prec.left(PREC.COMPARISON, seq(
      field('left', $._expression),
      field('operator', choice('<', '>', '<=', '>=')),
      field('right', $._expression),
    )),

    // Additive: expr + expr, expr - expr
    additive_expr: $ => prec.left(PREC.ADD, seq(
      field('left', $._expression),
      field('operator', choice('+', '-')),
      field('right', $._expression),
    )),

    // Multiplicative: expr * expr, expr / expr, expr % expr
    multiplicative_expr: $ => prec.left(PREC.MULT, seq(
      field('left', $._expression),
      field('operator', choice('*', '/', '%')),
      field('right', $._expression),
    )),

    // String concatenation: expr ++ expr
    concat_expr: $ => prec.left(PREC.CONCAT, seq(
      field('left', $._expression),
      '++',
      field('right', $._expression),
    )),

    // Unary: -expr, !expr
    unary_expr: $ => prec(PREC.UNARY, choice(
      seq('-', field('operand', $._expression)),
      seq('!', field('operand', $._expression)),
    )),

    // Function call: expr(args)
    call_expr: $ => prec(PREC.CALL, seq(
      field('function', $._expression),
      '(',
      optional(seq(
        $._expression,
        repeat(seq(',', $._expression)),
      )),
      ')',
    )),

    // Index: expr[expr]
    index_expr: $ => prec(PREC.CALL, seq(
      field('object', $._expression),
      '[',
      field('index', $._expression),
      ']',
    )),

    // Field access: expr.name
    field_expr: $ => prec(PREC.CALL, seq(
      field('object', $._expression),
      '.',
      field('field', $.identifier),
    )),

    // ============================================================
    // Primary expressions
    // ============================================================

    primary_expr: $ => choice(
      $.integer_literal,
      $.float_literal,
      $.string_literal,
      $.bool_literal,
      $.char_literal,
      $.unit_literal,
      $.identifier,
      $.list_expr,
      $.tuple_expr,
      $.map_expr,
      $.grouped_expr,
    ),

    integer_literal: $ => /\d+/,

    float_literal: $ => /\d+\.\d+/,

    string_literal: $ => seq(
      '"',
      repeat(choice(
        /[^"\\]/,
        $.escape_sequence,
      )),
      '"',
    ),

    escape_sequence: $ => token.immediate(seq(
      '\\',
      choice(/[^ntr"\\]/, /n/, /t/, /r/, /\\/, /"/),
    )),

    char_literal: $ => seq(
      "'",
      choice(
        /[^'\\]/,
        seq('\\', choice(/[^ntr'\\]/, /n/, /t/, /r/, /\\/, /'/)),
      ),
      "'",
    ),

    bool_literal: $ => choice('true', 'false'),

    unit_literal: $ => seq('(', ')'),

    identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,

    list_expr: $ => seq(
      '[',
      optional(seq(
        $._expression,
        repeat(seq(',', $._expression)),
      )),
      ']',
    ),

    tuple_expr: $ => seq(
      '(',
      $._expression,
      ',',
      seq(
        $._expression,
        repeat(seq(',', $._expression)),
      ),
      ')',
    ),

    map_expr: $ => seq(
      '{',
      optional(seq(
        $.map_entry,
        repeat(seq(',', $.map_entry)),
      )),
      '}',
    ),

    map_entry: $ => seq(
      field('key', $._expression),
      '=>',
      field('value', $._expression),
    ),

    grouped_expr: $ => seq(
      '(',
      field('inner', $._expression),
      ')',
    ),

    // ============================================================
    // Lambda: |params| expr or |params| -> Type { body }
    // ============================================================

    lambda: $ => seq(
      '|',
      optional(seq(
        $.lambda_param,
        repeat(seq(',', $.lambda_param)),
      )),
      '|',
      optional(seq('->', $._type)),
      field('body', choice($.block_expr, $._expression)),
    ),

    lambda_param: $ => seq(
      field('name', $.identifier),
      optional(seq(':', field('type', $._type))),
    ),

    // ============================================================
    // Control flow
    // ============================================================

    if_expr: $ => seq(
      'if',
      field('condition', $._expression),
      'then',
      field('consequence', choice($.block_expr, $._expression)),
      optional(seq('else', field('alternative', choice($.block_expr, $._expression)))),
    ),

    match_expr: $ => prec.right(seq(
      'match',
      field('value', $._expression),
      '{',
      optional(seq(
        $.match_arm,
        repeat(seq(',', $.match_arm)),
        optional(','),
      )),
      '}',
    )),

    match_arm: $ => seq(
      field('pattern', $._pattern),
      '->',
      field('body', $._expression),
      optional(field('guard', seq('if', $._expression))),
    ),

    for_expr: $ => seq(
      'for',
      field('variable', $.identifier),
      choice(
        // for x in expr { body }
        seq(
          'in',
          field('iterable', $._expression),
          field('body', choice($.block_expr, $._expression)),
        ),
        // for i <- start..end { body }
        // for i <- start..end step n { body }
        seq(
          '<-',
          field('start', $._expression),
          '..',
          field('end', $._expression),
          optional(seq('step', field('step', $._expression))),
          field('body', choice($.block_expr, $._expression)),
        ),
      ),
    ),

    while_expr: $ => seq(
      'while',
      field('condition', $._expression),
      field('body', choice($.block_expr, $._expression)),
    ),

    block_expr: $ => seq(
      '{',
      repeat($._expression),
      optional(seq(';', $._expression)),
      '}',
    ),

    break_expr: $ => 'break',

    continue_expr: $ => 'continue',

    list_comprehension: $ => seq(
      '[',
      field('result', $._expression),
      'for',
      field('variable', $.identifier),
      choice(
        seq(
          'in',
          field('iterable', $._expression),
        ),
        seq(
          '<-',
          field('start', $._expression),
          '..',
          field('end', $._expression),
        ),
      ),
      optional(seq('if', field('filter', $._expression))),
      ']',
    ),

    assignment_expr: $ => prec.right(PREC.ASSIGNMENT, seq(
      field('target', $.identifier),
      '=',
      field('value', $._expression),
    )),

    // ============================================================
    // Patterns (for match expressions)
    // ============================================================

    _pattern: $ => choice(
      $.integer_pattern,
      $.float_pattern,
      $.string_pattern,
      $.bool_pattern,
      $.char_pattern,
      $.wildcard_pattern,
      $.binding_pattern,
      $.constructor_pattern,
      $.tuple_pattern,
      $.list_pattern,
      $.negative_pattern,
    ),

    integer_pattern: $ => /\d+/,

    float_pattern: $ => /\d+\.\d+/,

    string_pattern: $ => $.string_literal,

    bool_pattern: $ => choice('true', 'false'),

    char_pattern: $ => $.char_literal,

    wildcard_pattern: $ => '_',

    binding_pattern: $ => $.identifier,

    constructor_pattern: $ => seq(
      field('name', $.identifier),
      '(',
      optional(seq(
        $._pattern,
        repeat(seq(',', $._pattern)),
      )),
      ')',
    ),

    tuple_pattern: $ => seq(
      '(',
      $._pattern,
      ',',
      seq(
        $._pattern,
        repeat(seq(',', $._pattern)),
      ),
      ')',
    ),

    list_pattern: $ => seq(
      '[',
      optional(seq(
        $._pattern,
        repeat(seq(',', $._pattern)),
      )),
      ']',
    ),

    negative_pattern: $ => seq('-', choice($.integer_pattern, $.float_pattern)),

    // ============================================================
    // Types
    // ============================================================

    _type: $ => choice(
      $.int_type,
      $.float_type,
      $.string_type,
      $.bool_type,
      $.char_type,
      $.unit_type,
      $.list_type,
      $.map_type,
      $.tuple_type,
      $.function_type,
      $.option_type,
      $.result_type,
      $.named_type,
    ),

    int_type: $ => 'Int',

    float_type: $ => 'Float',

    string_type: $ => 'String',

    bool_type: $ => 'Bool',

    char_type: $ => 'Char',

    unit_type: $ => 'Unit',

    list_type: $ => seq('List', '[', $._type, ']'),

    map_type: $ => seq('Map', '[', $._type, ',', $._type, ']'),

    tuple_type: $ => seq(
      '(',
      $._type,
      ',',
      seq(
        $._type,
        repeat(seq(',', $._type)),
      ),
      ')',
    ),

    function_type: $ => prec.right(seq(
      '(',
      optional(seq(
        $._type,
        repeat(seq(',', $._type)),
      )),
      ')',
      '->',
      $._type,
    )),

    option_type: $ => seq('Option', '[', $._type, ']'),

    result_type: $ => seq('Result', '[', $._type, ',', $._type, ']'),

    named_type: $ => $.identifier,

    // ============================================================
    // Comments
    // ============================================================

    comment: $ => token(prec(-1, seq('//', /[^\n]*/))),
  },
});

// ============================================================
// Precedence levels
// ============================================================

const PREC = {
  ASSIGNMENT: 1,
  PIPE: 2,
  OR: 3,
  AND: 4,
  EQUALITY: 5,
  COMPARISON: 6,
  CONCAT: 7,
  ADD: 8,
  MULT: 9,
  UNARY: 10,
  CALL: 11,
};
