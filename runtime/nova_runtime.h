#ifndef NOVA_RUNTIME_H
#define NOVA_RUNTIME_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdarg.h>

// ============================================================
// 基本类型定义
// ============================================================

// Nova String（引用计数 UTF-8 字符串）
typedef struct NovaString {
    char* data;
    int64_t length;
    int64_t capacity;
    int64_t ref_count;
} NovaString;

// Nova List（动态数组，引用计数）
typedef struct NovaList {
    void** items;
    int64_t length;
    int64_t capacity;
    int64_t ref_count;
} NovaList;

// Nova Map Entry
typedef struct NovaMapEntry {
    NovaString* key;
    void* value;
    struct NovaMapEntry* next;
} NovaMapEntry;

// Nova Map（哈希表，引用计数）
typedef struct NovaMap {
    NovaMapEntry** buckets;
    int64_t bucket_count;
    int64_t size;
    int64_t ref_count;
} NovaMap;

// ADT Tagged Union（代数数据类型）
// NovaADT 用于表示 Option, Result 以及用户自定义 ADT
typedef struct NovaADT {
    int32_t type_id;      // 类型 ID（全局唯一）
    int32_t variant_tag;   // 变体标签（在该类型内的索引）
    void** fields;         // 字段数组
    int32_t field_count;
    int64_t ref_count;
} NovaADT;

// Closure（闭包）
typedef struct NovaClosure {
    void* fn_ptr;         // 函数指针
    void** captured;      // 捕获的变量数组
    int32_t capture_count;
    int64_t ref_count;
} NovaClosure;

// 通用 Value 类型（用于动态场景如 JSON、列表混合类型）
typedef enum NovaValueType {
    NOVA_VAL_INT,
    NOVA_VAL_FLOAT,
    NOVA_VAL_STRING,
    NOVA_VAL_BOOL,
    NOVA_VAL_UNIT,
    NOVA_VAL_LIST,
    NOVA_VAL_MAP,
    NOVA_VAL_ADT,
    NOVA_VAL_CLOSURE,
    NOVA_VAL_NULL,
} NovaValueType;

typedef struct NovaValue {
    NovaValueType type;
    union {
        int64_t int_val;
        double float_val;
        NovaString* string_val;
        bool bool_val;
        NovaList* list_val;
        NovaMap* map_val;
        NovaADT* adt_val;
        NovaClosure* closure_val;
    };
    int64_t ref_count;
} NovaValue;

// ============================================================
// 字符串操作
// ============================================================

NovaString* nova_string_new(const char* str);
NovaString* nova_string_new_len(const char* str, int64_t len);
NovaString* nova_string_concat(NovaString* a, NovaString* b);
NovaString* nova_string_from_int(int64_t n);
NovaString* nova_string_from_float(double f);
NovaString* nova_string_slice(NovaString* s, int64_t start, int64_t end);
int64_t nova_string_length(NovaString* s);
char nova_string_char_at(NovaString* s, int64_t idx);
bool nova_string_eq(NovaString* a, NovaString* b);
int64_t nova_string_find(NovaString* s, NovaString* substr);
NovaList* nova_string_split(NovaString* s, NovaString* delim);
NovaString* nova_string_trim(NovaString* s);
NovaString* nova_string_upper(NovaString* s);
NovaString* nova_string_lower(NovaString* s);
NovaString* nova_string_replace(NovaString* s, NovaString* old, NovaString* new_s);
void nova_string_retain(NovaString* s);
void nova_string_release(NovaString* s);

// ============================================================
// 列表操作
// ============================================================

NovaList* nova_list_new(int64_t initial_capacity);
void nova_list_push(NovaList* list, void* item);
void* nova_list_get(NovaList* list, int64_t idx);
void nova_list_set(NovaList* list, int64_t idx, void* item);
NovaList* nova_list_concat(NovaList* a, NovaList* b);
NovaList* nova_list_slice(NovaList* list, int64_t start, int64_t end);
NovaList* nova_list_map(NovaList* list, void* fn);
NovaList* nova_list_filter(NovaList* list, void* pred_fn);
void* nova_list_reduce(NovaList* list, void* fn, void* initial);
int64_t nova_list_length(NovaList* list);
void* nova_list_head(NovaList* list);
NovaList* nova_list_tail(NovaList* list);
bool nova_list_contains(NovaList* list, void* item);
int64_t nova_list_index_of(NovaList* list, void* item);
void nova_list_retain(NovaList* l);
void nova_list_release(NovaList* l);

// ============================================================
// Map 操作
// ============================================================

NovaMap* nova_map_new(int64_t initial_buckets);
void nova_map_put(NovaMap* map, NovaString* key, void* value);
void* nova_map_get(NovaMap* map, NovaString* key);
bool nova_map_has(NovaMap* map, NovaString* key);
void nova_map_remove(NovaMap* map, NovaString* key);
NovaList* nova_map_keys(NovaMap* map);
NovaList* nova_map_values(NovaMap* map);
int64_t nova_map_size(NovaMap* map);
void nova_map_retain(NovaMap* m);
void nova_map_release(NovaMap* m);

// ============================================================
// ADT 操作
// ============================================================

NovaADT* nova_adt_new(int32_t type_id, int32_t variant_tag, int32_t field_count);
void nova_adt_set_field(NovaADT* adt, int32_t idx, void* value);
void* nova_adt_get_field(NovaADT* adt, int32_t idx);
NovaADT* nova_option_some(void* value);
NovaADT* nova_option_none(void);
bool nova_option_is_some(NovaADT* opt);
void* nova_option_unwrap(NovaADT* opt);
NovaADT* nova_result_ok(void* value);
NovaADT* nova_result_err(void* error);
bool nova_result_is_ok(NovaADT* result);
void* nova_result_unwrap(NovaADT* result);
void nova_adt_retain(NovaADT* a);
void nova_adt_release(NovaADT* a);

// ============================================================
// 闭包操作
// ============================================================

NovaClosure* nova_closure_new(void* fn_ptr, void** captured, int32_t capture_count);
void* nova_closure_call(NovaClosure* closure, void** args, int32_t arg_count);
void nova_closure_retain(NovaClosure* c);
void nova_closure_release(NovaClosure* c);

// ============================================================
// I/O 操作
// ============================================================

void nova_print(NovaString* s);
void nova_println(NovaString* s);
void nova_print_int(int64_t n);
void nova_print_float(double f);
void nova_print_bool(bool b);
NovaString* nova_read_line(void);
NovaString* nova_read_file(NovaString* path);
void nova_write_file(NovaString* path, NovaString* content);
bool nova_file_exists(NovaString* path);
NovaList* nova_list_dir(NovaString* path);
void nova_delete_file(NovaString* path);
bool nova_create_dir(NovaString* path);
NovaString* nova_get_cwd(void);
NovaString* nova_get_env(NovaString* name);
int32_t nova_set_env(NovaString* name, NovaString* value);

// ============================================================
// 数学函数
// ============================================================

double nova_sqrt(double x);
double nova_abs(double x);
int64_t nova_abs_int(int64_t x);
double nova_sin(double x);
double nova_cos(double x);
double nova_tan(double x);
double nova_log(double x);
double nova_log10(double x);
double nova_exp(double x);
double nova_pow(double base, double exp);
double nova_floor(double x);
double nova_ceil(double x);
double nova_round(double x);
double nova_min(double a, double b);
double nova_max(double a, double b);
double nova_fmod(double a, double b);
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
double nova_pi(void);

// ============================================================
// JSON 操作
// ============================================================

NovaValue* nova_json_parse(NovaString* text);
NovaString* nova_json_stringify(NovaValue* value);
void nova_value_retain(NovaValue* v);
void nova_value_release(NovaValue* v);

// ============================================================
// 进程/系统操作
// ============================================================

int32_t nova_system(NovaString* command);
int32_t nova_exit(int32_t code);
int32_t nova_getpid(void);
NovaString* nova_platform(void);
NovaString* nova_os_name(void);
NovaString* nova_arch(void);

// ============================================================
// 时间操作
// ============================================================

int64_t nova_time_now(void);        // Unix timestamp (ms)
int64_t nova_time_unix(void);       // Unix timestamp (s)
NovaString* nova_time_format(NovaString* fmt, int64_t timestamp);
int64_t nova_time_sleep_ms(int64_t ms);

// ============================================================
// 网络操作（基础 HTTP）
// ============================================================

typedef struct NovaHttpResponse {
    int32_t status_code;
    NovaMap* headers;
    NovaString* body;
} NovaHttpResponse;

NovaHttpResponse* nova_http_get(NovaString* url);
NovaHttpResponse* nova_http_post(NovaString* url, NovaString* body, NovaMap* headers);
void nova_http_response_release(NovaHttpResponse* resp);

// ============================================================
// 内存管理
// ============================================================

void* nova_alloc(int64_t size);
void nova_free(void* ptr);
void* nova_realloc(void* ptr, int64_t size);
void nova_init(void);
void nova_cleanup(void);
int64_t nova_gc_collect(void);  // 手动触发 GC

// ============================================================
// 环境变量 / 命令行参数
// ============================================================

NovaList* nova_args(void);  // 获取命令行参数列表

// ============================================================
// panic / assert
// ============================================================

void nova_panic(const char* message, const char* file, int32_t line);
void nova_assert(bool condition, const char* message, const char* file, int32_t line);

#define NOVA_PANIC(msg) nova_panic(msg, __FILE__, __LINE__)
#define NOVA_ASSERT(cond, msg) nova_assert(cond, msg, __FILE__, __LINE__)

#endif // NOVA_RUNTIME_H
