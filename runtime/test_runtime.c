#include "nova_runtime.h"
#include <stdio.h>
#include <assert.h>
#include <math.h>

int main() {
    nova_init();

    // ========== 字符串测试 ==========
    printf("=== String tests ===\n");

    NovaString* s1 = nova_string_new("Hello");
    NovaString* s2 = nova_string_new(" World");
    NovaString* s3 = nova_string_concat(s1, s2);
    assert(nova_string_length(s3) == 11);
    nova_println(s3);

    // string_eq
    NovaString* s_copy = nova_string_new("Hello World");
    assert(nova_string_eq(s3, s_copy));
    NovaString* s_diff = nova_string_new("HelloX");
    assert(!nova_string_eq(s3, s_diff));

    // string_slice
    NovaString* sl = nova_string_slice(s3, 0, 5);
    assert(nova_string_eq(sl, s1));
    assert(nova_string_length(sl) == 5);

    // string_find
    assert(nova_string_find(s3, nova_string_new("World")) == 6);
    assert(nova_string_find(s3, nova_string_new("xyz")) == -1);

    // string_trim
    NovaString* s_trim = nova_string_new("  hello  ");
    NovaString* trimmed = nova_string_trim(s_trim);
    assert(nova_string_eq(trimmed, nova_string_new("hello")));

    // string_upper / lower
    NovaString* s_up = nova_string_upper(nova_string_new("hello"));
    assert(nova_string_eq(s_up, nova_string_new("HELLO")));
    NovaString* s_lo = nova_string_lower(nova_string_new("HELLO"));
    assert(nova_string_eq(s_lo, nova_string_new("hello")));

    // string_from_int / from_float
    NovaString* si = nova_string_from_int(-42);
    assert(nova_string_eq(si, nova_string_new("-42")));
    NovaString* sf = nova_string_from_float(3.14);
    // 3.14 的 double 表示
    assert(nova_string_length(sf) > 0);

    // string_replace
    NovaString* sr = nova_string_replace(nova_string_new("aabbcc"), nova_string_new("bb"), nova_string_new("XX"));
    assert(nova_string_eq(sr, nova_string_new("aaXXcc")));

    // string_split
    NovaList* parts = nova_string_split(nova_string_new("a,b,c"), nova_string_new(","));
    assert(nova_list_length(parts) == 3);

    // string_char_at
    assert(nova_string_char_at(s3, 0) == 'H');
    assert(nova_string_char_at(s3, 4) == 'o');

    // 引用计数
    nova_string_release(s1);
    nova_string_release(s2);
    nova_string_release(s3);
    nova_string_release(s_copy);
    nova_string_release(s_diff);
    nova_string_release(sl);
    nova_string_release(s_trim);
    nova_string_release(trimmed);
    nova_string_release(s_up);
    nova_string_release(s_lo);
    nova_string_release(si);
    nova_string_release(sf);
    nova_string_release(sr);
    nova_list_release(parts);

    // ========== 列表测试 ==========
    printf("=== List tests ===\n");

    NovaList* list = nova_list_new(8);
    int64_t values[] = {1, 2, 3, 4, 5};
    for (int i = 0; i < 5; i++) {
        nova_list_push(list, (void*)(intptr_t)values[i]);
    }
    assert(nova_list_length(list) == 5);
    assert((int64_t)(intptr_t)nova_list_get(list, 0) == 1);
    assert((int64_t)(intptr_t)nova_list_get(list, 4) == 5);
    assert((int64_t)(intptr_t)nova_list_head(list) == 1);

    // tail
    NovaList* tail = nova_list_tail(list);
    assert(nova_list_length(tail) == 4);
    assert((int64_t)(intptr_t)nova_list_get(tail, 0) == 2);

    // contains / index_of
    assert(nova_list_contains(list, (void*)(intptr_t)3));
    assert(!nova_list_contains(list, (void*)(intptr_t)99));
    assert(nova_list_index_of(list, (void*)(intptr_t)4) == 3);
    assert(nova_list_index_of(list, (void*)(intptr_t)99) == -1);

    // slice
    NovaList* sl2 = nova_list_slice(list, 1, 3);
    assert(nova_list_length(sl2) == 2);
    assert((int64_t)(intptr_t)nova_list_get(sl2, 0) == 2);

    // concat
    NovaList* list2 = nova_list_new(4);
    nova_list_push(list2, (void*)(intptr_t)6);
    nova_list_push(list2, (void*)(intptr_t)7);
    NovaList* concat = nova_list_concat(list, list2);
    assert(nova_list_length(concat) == 7);
    assert((int64_t)(intptr_t)nova_list_get(concat, 5) == 6);

    // set
    nova_list_set(list, 0, (void*)(intptr_t)10);
    assert((int64_t)(intptr_t)nova_list_get(list, 0) == 10);
    nova_list_set(list, 0, (void*)(intptr_t)1); // restore

    // 负索引
    assert((int64_t)(intptr_t)nova_list_get(list, -1) == 5);

    nova_list_release(tail);
    nova_list_release(sl2);
    nova_list_release(list2);
    nova_list_release(concat);
    nova_list_release(list);

    // ========== Map 测试 ==========
    printf("=== Map tests ===\n");

    NovaMap* mymap = nova_map_new(8);
    nova_map_put(mymap, nova_string_new("name"), nova_string_new("Nova"));
    nova_map_put(mymap, nova_string_new("version"), nova_string_new("1.0"));

    assert(nova_map_size(mymap) == 2);
    assert(nova_map_has(mymap, nova_string_new("name")));
    assert(!nova_map_has(mymap, nova_string_new("missing")));

    void* map_name_v = nova_map_get(mymap, nova_string_new("name"));
    assert(map_name_v != NULL);
    assert(nova_string_eq((NovaString*)map_name_v, nova_string_new("Nova")));

    // keys and values
    NovaList* keys = nova_map_keys(mymap);
    NovaList* vals = nova_map_values(mymap);
    assert(nova_list_length(keys) == 2);
    assert(nova_list_length(vals) == 2);

    // remove
    nova_map_remove(mymap, nova_string_new("version"));
    assert(nova_map_size(mymap) == 1);
    assert(!nova_map_has(mymap, nova_string_new("version")));

    // update
    nova_map_put(mymap, nova_string_new("name"), nova_string_new("NovaLang"));
    assert(nova_string_eq((NovaString*)nova_map_get(mymap, nova_string_new("name")), nova_string_new("NovaLang")));

    nova_list_release(keys);
    nova_list_release(vals);
    nova_map_release(mymap);

    // ========== Option 测试 ==========
    printf("=== Option tests ===\n");

    NovaADT* some = nova_option_some((void*)(intptr_t)42);
    assert(nova_option_is_some(some));
    assert((int64_t)(intptr_t)nova_option_unwrap(some) == 42);

    NovaADT* none = nova_option_none();
    assert(!nova_option_is_some(none));

    // Option with string
    NovaADT* some_str = nova_option_some(nova_string_new("hello"));
    assert(nova_option_is_some(some_str));
    NovaString* unwrapped = (NovaString*)nova_option_unwrap(some_str);
    assert(nova_string_eq(unwrapped, nova_string_new("hello")));

    nova_adt_release(some);
    nova_adt_release(none);
    nova_string_release(unwrapped);
    nova_adt_release(some_str);

    // ========== Result 测试 ==========
    printf("=== Result tests ===\n");

    NovaADT* ok = nova_result_ok((void*)(intptr_t)100);
    assert(nova_result_is_ok(ok));
    assert((int64_t)(intptr_t)nova_result_unwrap(ok) == 100);

    NovaADT* err = nova_result_err((void*)(intptr_t)404);
    assert(!nova_result_is_ok(err));

    nova_adt_release(ok);
    nova_adt_release(err);

    // ========== ADT 通用测试 ==========
    printf("=== ADT tests ===\n");

    NovaADT* custom = nova_adt_new(100, 0, 3);
    nova_adt_set_field(custom, 0, (void*)(intptr_t)10);
    nova_adt_set_field(custom, 1, (void*)(intptr_t)20);
    nova_adt_set_field(custom, 2, (void*)(intptr_t)30);
    assert(custom->type_id == 100);
    assert(custom->variant_tag == 0);
    assert(custom->field_count == 3);
    assert((int64_t)(intptr_t)nova_adt_get_field(custom, 1) == 20);
    nova_adt_release(custom);

    // ========== 数学测试 ==========
    printf("=== Math tests ===\n");

    assert(nova_abs(-5.0) == 5.0);
    assert(nova_abs_int(-42) == 42);
    assert(nova_sqrt(16.0) == 4.0);
    assert(nova_min(3.0, 7.0) == 3.0);
    assert(nova_max(3.0, 7.0) == 7.0);
    assert(nova_floor(3.7) == 3.0);
    assert(nova_ceil(3.2) == 4.0);
    assert(nova_round(3.5) == 4.0);
    assert(nova_fmod(10.0, 3.0) == 1.0);
    assert(fabs(nova_pi() - M_PI) < 1e-10);
    assert(fabs(nova_pow(2.0, 10.0) - 1024.0) < 1e-10);
    assert(fabs(nova_log(nova_exp(5.0)) - 5.0) < 1e-10);

    // ========== I/O 测试 ==========
    printf("=== I/O tests ===\n");

    nova_print_int(42);
    printf("\n");
    nova_print_float(3.14);
    printf("\n");
    nova_print_bool(true);
    printf("\n");
    nova_print_bool(false);
    printf("\n");

    // read_file / write_file
    NovaString* test_path = nova_string_new("/tmp/nova_test_file.txt");
    NovaString* test_content = nova_string_new("Hello from Nova runtime!");
    nova_write_file(test_path, test_content);
    assert(nova_file_exists(test_path));
    NovaString* read_back = nova_read_file(test_path);
    assert(nova_string_eq(read_back, test_content));

    nova_string_release(test_path);
    nova_string_release(test_content);
    nova_string_release(read_back);
    nova_delete_file(nova_string_new("/tmp/nova_test_file.txt"));

    // get_cwd
    NovaString* cwd = nova_get_cwd();
    assert(nova_string_length(cwd) > 0);
    nova_string_release(cwd);

    // env
    NovaString* path_env = nova_get_env(nova_string_new("PATH"));
    assert(nova_string_length(path_env) > 0);
    nova_string_release(path_env);

    // ========== 系统测试 ==========
    printf("=== System tests ===\n");

    NovaString* platform = nova_platform();
    assert(nova_string_length(platform) > 0);
    printf("Platform: ");
    nova_println(platform);

    NovaString* arch = nova_arch();
    assert(nova_string_length(arch) > 0);
    printf("Arch: ");
    nova_println(arch);

    int32_t pid = nova_getpid();
    assert(pid > 0);
    printf("PID: %d\n", pid);

    nova_string_release(platform);
    nova_string_release(arch);

    // ========== 时间测试 ==========
    printf("=== Time tests ===\n");

    int64_t now_ms = nova_time_now();
    assert(now_ms > 0);
    int64_t now_s = nova_time_unix();
    assert(now_s > 0);
    assert(now_s == now_ms / 1000);

    // time_format
    NovaString* fmt_time = nova_time_format(nova_string_new("%Y-%m-%d"), now_s);
    assert(nova_string_length(fmt_time) > 0);
    printf("Formatted time: ");
    nova_println(fmt_time);
    nova_string_release(fmt_time);

    // time_sleep (short sleep, 10ms)
    int64_t before = nova_time_now();
    nova_time_sleep_ms(10);
    int64_t after = nova_time_now();
    assert(after - before >= 10);

    // ========== JSON 测试 ==========
    printf("=== JSON tests ===\n");

    // Parse object
    NovaString* json_str = nova_string_new("{\"name\": \"Nova\", \"version\": 1}");
    NovaValue* val = nova_json_parse(json_str);
    assert(val != NULL);
    assert(val->type == NOVA_VAL_MAP);

    // Get map fields
    void* name_v = nova_map_get(val->map_val, nova_string_new("name"));
    assert(name_v != NULL);
    NovaValue* name_val = (NovaValue*)name_v;
    assert(name_val->type == NOVA_VAL_STRING);
    assert(nova_string_eq(name_val->string_val, nova_string_new("Nova")));

    void* ver_v = nova_map_get(val->map_val, nova_string_new("version"));
    assert(ver_v != NULL);
    NovaValue* ver_val = (NovaValue*)ver_v;
    assert(ver_val->type == NOVA_VAL_INT);
    assert(ver_val->int_val == 1);

    // Stringify
    NovaString* out = nova_json_stringify(val);
    assert(nova_string_length(out) > 0);
    printf("JSON stringify: ");
    nova_println(out);

    nova_string_release(json_str);
    nova_string_release(out);
    nova_value_release(val);

    // Parse array
    NovaString* json_arr = nova_string_new("[1, 2, 3, \"hello\", true, null]");
    NovaValue* arr_val = nova_json_parse(json_arr);
    assert(arr_val != NULL);
    assert(arr_val->type == NOVA_VAL_LIST);
    assert(nova_list_length(arr_val->list_val) == 6);

    NovaValue* elem0 = (NovaValue*)nova_list_get(arr_val->list_val, 0);
    assert(elem0->type == NOVA_VAL_INT);
    assert(elem0->int_val == 1);

    NovaValue* elem3 = (NovaValue*)nova_list_get(arr_val->list_val, 3);
    assert(elem3->type == NOVA_VAL_STRING);
    assert(nova_string_eq(elem3->string_val, nova_string_new("hello")));

    NovaValue* elem4 = (NovaValue*)nova_list_get(arr_val->list_val, 4);
    assert(elem4->type == NOVA_VAL_BOOL);
    assert(elem4->bool_val == true);

    NovaValue* elem5 = (NovaValue*)nova_list_get(arr_val->list_val, 5);
    assert(elem5->type == NOVA_VAL_NULL);

    nova_string_release(json_arr);
    nova_value_release(arr_val);

    // Parse number types
    NovaString* json_num = nova_string_new("42");
    NovaValue* num_val = nova_json_parse(json_num);
    assert(num_val && num_val->type == NOVA_VAL_INT && num_val->int_val == 42);
    nova_string_release(json_num);
    nova_value_release(num_val);

    NovaString* json_float = nova_string_new("3.14");
    NovaValue* float_val = nova_json_parse(json_float);
    assert(float_val && float_val->type == NOVA_VAL_FLOAT);
    assert(fabs(float_val->float_val - 3.14) < 1e-10);
    nova_string_release(json_float);
    nova_value_release(float_val);

    // Parse true/false/null
    NovaString* json_true = nova_string_new("true");
    NovaValue* true_val = nova_json_parse(json_true);
    assert(true_val && true_val->type == NOVA_VAL_BOOL && true_val->bool_val == true);
    nova_string_release(json_true);
    nova_value_release(true_val);

    // ========== 闭包测试 ==========
    printf("=== Closure tests ===\n");

    // 简单的闭包：无捕获
    typedef void* (*simple_fn_t)(void** captured, void** args, int32_t arg_count);
    NovaClosure* closure = nova_closure_new((void*)(simple_fn_t)NULL, NULL, 0);
    assert(closure != NULL);
    assert(closure->capture_count == 0);
    nova_closure_release(closure);

    // 带捕获的闭包
    void* captured_vals[] = {(void*)(intptr_t)10, (void*)(intptr_t)20};
    NovaClosure* captured_closure = nova_closure_new((void*)(simple_fn_t)NULL, captured_vals, 2);
    assert(captured_closure->capture_count == 2);
    assert((int64_t)(intptr_t)captured_closure->captured[0] == 10);
    assert((int64_t)(intptr_t)captured_closure->captured[1] == 20);
    nova_closure_release(captured_closure);

    // ========== Value 引用计数测试 ==========
    printf("=== Value refcount tests ===\n");

    NovaValue* v = (NovaValue*)nova_alloc(sizeof(NovaValue));
    v->type = NOVA_VAL_INT;
    v->int_val = 99;
    v->ref_count = 1;
    nova_value_retain(v);
    assert(v->ref_count == 2);
    nova_value_release(v);
    assert(v->ref_count == 1);
    nova_value_release(v);

    printf("All runtime tests passed!\n");

    nova_cleanup();
    return 0;
}
