#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "nova_runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <ctype.h>
#include <float.h>
#include <errno.h>

#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#include <process.h>
#define NOVA_PATH_SEP '\\'
#define nova_mkdir(path) _mkdir(path)
#define nova_getcwd_func(buf, size) _getcwd(buf, size)
#define nova_rmdir(path) _rmdir(path)
#else
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/wait.h>
#define NOVA_PATH_SEP '/'
#define nova_mkdir(path) mkdir(path, 0755)
#define nova_getcwd_func(buf, size) getcwd(buf, size)
#define nova_rmdir(path) rmdir(path)
#endif

// ============================================================
// 全局状态
// ============================================================

static int g_argc = 0;
static char** g_argv = NULL;

static int64_t g_alloc_count = 0;
static int64_t g_free_count = 0;

// Option/Result 类型 ID（编译器会分配唯一的）
#define NOVA_TYPE_ID_OPTION  1
#define NOVA_TYPE_ID_RESULT  2

// Option variant tags
#define NOVA_OPTION_NONE_TAG 0
#define NOVA_OPTION_SOME_TAG 1

// Result variant tags
#define NOVA_RESULT_OK_TAG   0
#define NOVA_RESULT_ERR_TAG  1

// ============================================================
// 内存管理
// ============================================================

void* nova_alloc(int64_t size) {
    if (size <= 0) size = 1;
    void* ptr = malloc((size_t)size);
    if (!ptr) {
        fprintf(stderr, "Nova runtime: out of memory (allocating %lld bytes)\n", (long long)size);
        abort();
    }
    g_alloc_count++;
    return ptr;
}

void nova_free(void* ptr) {
    if (ptr) {
        g_free_count++;
        free(ptr);
    }
}

void* nova_realloc(void* ptr, int64_t size) {
    if (size <= 0) size = 1;
    void* new_ptr = realloc(ptr, (size_t)size);
    if (!new_ptr) {
        fprintf(stderr, "Nova runtime: out of memory (realloc to %lld bytes)\n", (long long)size);
        abort();
    }
    return new_ptr;
}

void nova_init(void) {
    g_alloc_count = 0;
    g_free_count = 0;
}

void nova_cleanup(void) {
    // 引用计数模式下，由用户负责释放所有对象
    // 此函数可用于最终诊断
}

int64_t nova_gc_collect(void) {
    // 简单引用计数模型下，无循环引用的 GC 操作
    // 返回净分配数（诊断用）
    return g_alloc_count - g_free_count;
}

// ============================================================
// panic / assert
// ============================================================

void nova_panic(const char* message, const char* file, int32_t line) {
    fprintf(stderr, "Nova panic: %s\n  at %s:%d\n", message, file, line);
    abort();
}

void nova_assert(bool condition, const char* message, const char* file, int32_t line) {
    if (!condition) {
        fprintf(stderr, "Nova assertion failed: %s\n  at %s:%d\n", message, file, line);
        abort();
    }
}

// ============================================================
// 内部辅助：UTF-8 字节长度计算
// ============================================================

// ============================================================
// 字符串操作
// ============================================================

NovaString* nova_string_new(const char* str) {
    if (!str) str = "";
    int64_t len = (int64_t)strlen(str);
    return nova_string_new_len(str, len);
}

NovaString* nova_string_new_len(const char* str, int64_t len) {
    NovaString* s = (NovaString*)nova_alloc(sizeof(NovaString));
    int64_t cap = len + 1;
    if (cap < 16) cap = 16;
    s->data = (char*)nova_alloc(cap);
    if (str && len > 0) {
        memcpy(s->data, str, (size_t)len);
    }
    s->data[len] = '\0';
    s->length = len;
    s->capacity = cap;
    s->ref_count = 1;
    return s;
}

NovaString* nova_string_concat(NovaString* a, NovaString* b) {
    if (!a) {
        NovaString* result = b ? b : nova_string_new("");
        nova_string_retain(result);
        return result;
    }
    if (!b) {
        nova_string_retain(a);
        return a;
    }
    int64_t new_len = a->length + b->length;
    NovaString* result = nova_string_new_len(NULL, new_len);
    memcpy(result->data, a->data, (size_t)a->length);
    memcpy(result->data + a->length, b->data, (size_t)b->length);
    result->data[new_len] = '\0';
    return result;
}

NovaString* nova_string_from_int(int64_t n) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%lld", (long long)n);
    return nova_string_new(buf);
}

NovaString* nova_string_from_float(double f) {
    char buf[64];
    snprintf(buf, sizeof(buf), "%.17g", f);
    return nova_string_new(buf);
}

NovaString* nova_string_slice(NovaString* s, int64_t start, int64_t end) {
    if (!s) return nova_string_new("");
    if (start < 0) start = 0;
    if (end > s->length) end = s->length;
    if (start >= end) return nova_string_new("");
    return nova_string_new_len(s->data + start, end - start);
}

int64_t nova_string_length(NovaString* s) {
    if (!s) return 0;
    return s->length;
}

char nova_string_char_at(NovaString* s, int64_t idx) {
    if (!s || idx < 0 || idx >= s->length) return '\0';
    return s->data[idx];
}

bool nova_string_eq(NovaString* a, NovaString* b) {
    if (a == b) return true;
    if (!a || !b) return false;
    if (a->length != b->length) return false;
    return memcmp(a->data, b->data, (size_t)a->length) == 0;
}

int64_t nova_string_find(NovaString* s, NovaString* substr) {
    if (!s || !substr || substr->length == 0) return 0;
    if (substr->length > s->length) return -1;
    const char* found = strstr(s->data, substr->data);
    if (!found) return -1;
    return (int64_t)(found - s->data);
}

NovaList* nova_string_split(NovaString* s, NovaString* delim) {
    if (!s) return nova_list_new(0);
    NovaList* result = nova_list_new(8);

    if (!delim || delim->length == 0) {
        // 按每个字符拆分
        for (int64_t i = 0; i < s->length; i++) {
            NovaString* ch = nova_string_new_len(s->data + i, 1);
            nova_list_push(result, ch);
        }
        return result;
    }

    int64_t pos = 0;
    while (pos <= s->length) {
        const char* found = strstr(s->data + pos, delim->data);
        int64_t end;
        if (found) {
            end = (int64_t)(found - s->data);
        } else {
            end = s->length;
        }
        NovaString* part = nova_string_new_len(s->data + pos, end - pos);
        nova_list_push(result, part);
        if (!found) break;
        pos = end + delim->length;
    }
    return result;
}

NovaString* nova_string_trim(NovaString* s) {
    if (!s || s->length == 0) return nova_string_new("");
    int64_t start = 0;
    int64_t end = s->length;
    while (start < end && ((unsigned char)s->data[start] <= ' ')) start++;
    while (end > start && ((unsigned char)s->data[end - 1] <= ' ')) end--;
    return nova_string_slice(s, start, end);
}

NovaString* nova_string_upper(NovaString* s) {
    if (!s) return nova_string_new("");
    NovaString* result = nova_string_new_len(s->data, s->length);
    for (int64_t i = 0; i < result->length; i++) {
        result->data[i] = (char)toupper((unsigned char)result->data[i]);
    }
    return result;
}

NovaString* nova_string_lower(NovaString* s) {
    if (!s) return nova_string_new("");
    NovaString* result = nova_string_new_len(s->data, s->length);
    for (int64_t i = 0; i < result->length; i++) {
        result->data[i] = (char)tolower((unsigned char)result->data[i]);
    }
    return result;
}

NovaString* nova_string_replace(NovaString* s, NovaString* old_s, NovaString* new_s) {
    if (!s) return nova_string_new("");
    if (!old_s || old_s->length == 0) {
        nova_string_retain(s);
        return s;
    }

    // 计算替换后的大小
    int64_t count = 0;
    const char* p = s->data;
    while ((p = strstr(p, old_s->data)) != NULL) {
        count++;
        p += old_s->length;
    }

    if (count == 0) {
        nova_string_retain(s);
        return s;
    }

    int64_t new_len = s->length + count * (new_s->length - old_s->length);
    NovaString* result = nova_string_new_len(NULL, new_len);

    const char* src = s->data;
    char* dst = result->data;
    int64_t old_len = old_s->length;
    int64_t new_len_s = new_s ? new_s->length : 0;
    const char* new_data = new_s ? new_s->data : "";

    while (*src) {
        const char* found = strstr(src, old_s->data);
        if (found) {
            int64_t before = (int64_t)(found - src);
            memcpy(dst, src, (size_t)before);
            dst += before;
            memcpy(dst, new_data, (size_t)new_len_s);
            dst += new_len_s;
            src = found + old_len;
        } else {
            int64_t remaining = (int64_t)strlen(src);
            memcpy(dst, src, (size_t)remaining);
            dst += remaining;
            break;
        }
    }
    *dst = '\0';
    return result;
}

void nova_string_retain(NovaString* s) {
    if (s) s->ref_count++;
}

void nova_string_release(NovaString* s) {
    if (!s) return;
    s->ref_count--;
    if (s->ref_count <= 0) {
        nova_free(s->data);
        nova_free(s);
    }
}

// ============================================================
// 列表操作
// ============================================================

NovaList* nova_list_new(int64_t initial_capacity) {
    if (initial_capacity < 4) initial_capacity = 4;
    NovaList* list = (NovaList*)nova_alloc(sizeof(NovaList));
    list->items = (void**)nova_alloc(sizeof(void*) * (size_t)initial_capacity);
    list->length = 0;
    list->capacity = initial_capacity;
    list->ref_count = 1;
    return list;
}

void nova_list_push(NovaList* list, void* item) {
    if (!list) return;
    if (list->length >= list->capacity) {
        int64_t new_cap = list->capacity * 2;
        list->items = (void**)nova_realloc(list->items, sizeof(void*) * (size_t)new_cap);
        list->capacity = new_cap;
    }
    list->items[list->length++] = item;
}

void* nova_list_get(NovaList* list, int64_t idx) {
    if (!list) return NULL;
    if (idx < 0) idx += list->length;
    if (idx < 0 || idx >= list->length) return NULL;
    return list->items[idx];
}

void nova_list_set(NovaList* list, int64_t idx, void* item) {
    if (!list) return;
    if (idx < 0) idx += list->length;
    if (idx < 0 || idx >= list->length) return;
    list->items[idx] = item;
}

NovaList* nova_list_concat(NovaList* a, NovaList* b) {
    if (!a) {
        NovaList* result = b ? b : nova_list_new(4);
        nova_list_retain(result);
        return result;
    }
    if (!b) {
        nova_list_retain(a);
        return a;
    }
    NovaList* result = nova_list_new(a->length + b->length);
    for (int64_t i = 0; i < a->length; i++) {
        nova_list_push(result, a->items[i]);
    }
    for (int64_t i = 0; i < b->length; i++) {
        nova_list_push(result, b->items[i]);
    }
    return result;
}

NovaList* nova_list_slice(NovaList* list, int64_t start, int64_t end) {
    if (!list) return nova_list_new(4);
    if (start < 0) start = 0;
    if (end > list->length) end = list->length;
    if (start >= end) return nova_list_new(4);
    NovaList* result = nova_list_new(end - start);
    for (int64_t i = start; i < end; i++) {
        nova_list_push(result, list->items[i]);
    }
    return result;
}

// 闭包函数指针类型：void* fn(void* item)
typedef void* (*nova_map_fn_t)(void*);

NovaList* nova_list_map(NovaList* list, void* fn) {
    if (!list || !fn) return nova_list_new(4);
    nova_map_fn_t map_fn = (nova_map_fn_t)fn;
    NovaList* result = nova_list_new(list->length);
    for (int64_t i = 0; i < list->length; i++) {
        void* mapped = map_fn(list->items[i]);
        nova_list_push(result, mapped);
    }
    return result;
}

// 谓词函数指针类型：bool fn(void* item)
typedef bool (*nova_pred_fn_t)(void*);

NovaList* nova_list_filter(NovaList* list, void* pred_fn) {
    if (!list || !pred_fn) return nova_list_new(4);
    nova_pred_fn_t pred = (nova_pred_fn_t)pred_fn;
    NovaList* result = nova_list_new(list->length);
    for (int64_t i = 0; i < list->length; i++) {
        if (pred(list->items[i])) {
            nova_list_push(result, list->items[i]);
        }
    }
    return result;
}

// reduce 函数指针类型：void* fn(void* acc, void* item)
typedef void* (*nova_reduce_fn_t)(void*, void*);

void* nova_list_reduce(NovaList* list, void* fn, void* initial) {
    if (!list || !fn) return initial;
    nova_reduce_fn_t reduce_fn = (nova_reduce_fn_t)fn;
    void* acc = initial;
    for (int64_t i = 0; i < list->length; i++) {
        acc = reduce_fn(acc, list->items[i]);
    }
    return acc;
}

int64_t nova_list_length(NovaList* list) {
    if (!list) return 0;
    return list->length;
}

void* nova_list_head(NovaList* list) {
    if (!list || list->length == 0) return NULL;
    return list->items[0];
}

NovaList* nova_list_tail(NovaList* list) {
    if (!list || list->length <= 1) return nova_list_new(4);
    return nova_list_slice(list, 1, list->length);
}

bool nova_list_contains(NovaList* list, void* item) {
    if (!list) return false;
    for (int64_t i = 0; i < list->length; i++) {
        if (list->items[i] == item) return true;
    }
    return false;
}

int64_t nova_list_index_of(NovaList* list, void* item) {
    if (!list) return -1;
    for (int64_t i = 0; i < list->length; i++) {
        if (list->items[i] == item) return i;
    }
    return -1;
}

void nova_list_retain(NovaList* l) {
    if (l) l->ref_count++;
}

void nova_list_release(NovaList* l) {
    if (!l) return;
    l->ref_count--;
    if (l->ref_count <= 0) {
        nova_free(l->items);
        nova_free(l);
    }
}

// ============================================================
// FNV-1a 哈希函数
// ============================================================

static uint64_t nova_fnv1a_hash(const char* data, int64_t len) {
    uint64_t hash = 14695981039346656037ULL;
    for (int64_t i = 0; i < len; i++) {
        hash ^= (unsigned char)data[i];
        hash *= 1099511628211ULL;
    }
    return hash;
}

// ============================================================
// Map 操作
// ============================================================

NovaMap* nova_map_new(int64_t initial_buckets) {
    if (initial_buckets < 8) initial_buckets = 8;
    NovaMap* map = (NovaMap*)nova_alloc(sizeof(NovaMap));
    map->buckets = (NovaMapEntry**)nova_alloc(sizeof(NovaMapEntry*) * (size_t)initial_buckets);
    memset(map->buckets, 0, sizeof(NovaMapEntry*) * (size_t)initial_buckets);
    map->bucket_count = initial_buckets;
    map->size = 0;
    map->ref_count = 1;
    return map;
}

void nova_map_put(NovaMap* map, NovaString* key, void* value) {
    if (!map || !key) return;
    uint64_t hash = nova_fnv1a_hash(key->data, key->length);
    int64_t bucket_idx = (int64_t)(hash % (uint64_t)map->bucket_count);

    // 检查是否已存在
    NovaMapEntry* entry = map->buckets[bucket_idx];
    while (entry) {
        if (nova_string_eq(entry->key, key)) {
            entry->value = value;
            return;
        }
        entry = entry->next;
    }

    // 创建新 entry
    NovaMapEntry* new_entry = (NovaMapEntry*)nova_alloc(sizeof(NovaMapEntry));
    nova_string_retain(key);
    new_entry->key = key;
    new_entry->value = value;
    new_entry->next = map->buckets[bucket_idx];
    map->buckets[bucket_idx] = new_entry;
    map->size++;

    // 负载因子 > 0.75 时扩容
    if (map->size * 4 > map->bucket_count * 3) {
        int64_t new_bucket_count = map->bucket_count * 2;
        NovaMapEntry** new_buckets = (NovaMapEntry**)nova_alloc(sizeof(NovaMapEntry*) * (size_t)new_bucket_count);
        memset(new_buckets, 0, sizeof(NovaMapEntry*) * (size_t)new_bucket_count);

        for (int64_t i = 0; i < map->bucket_count; i++) {
            NovaMapEntry* e = map->buckets[i];
            while (e) {
                NovaMapEntry* next = e->next;
                uint64_t h = nova_fnv1a_hash(e->key->data, e->key->length);
                int64_t idx = (int64_t)(h % (uint64_t)new_bucket_count);
                e->next = new_buckets[idx];
                new_buckets[idx] = e;
                e = next;
            }
        }

        nova_free(map->buckets);
        map->buckets = new_buckets;
        map->bucket_count = new_bucket_count;
    }
}

void* nova_map_get(NovaMap* map, NovaString* key) {
    if (!map || !key) return NULL;
    uint64_t hash = nova_fnv1a_hash(key->data, key->length);
    int64_t bucket_idx = (int64_t)(hash % (uint64_t)map->bucket_count);

    NovaMapEntry* entry = map->buckets[bucket_idx];
    while (entry) {
        if (nova_string_eq(entry->key, key)) {
            return entry->value;
        }
        entry = entry->next;
    }
    return NULL;
}

bool nova_map_has(NovaMap* map, NovaString* key) {
    return nova_map_get(map, key) != NULL;
}

void nova_map_remove(NovaMap* map, NovaString* key) {
    if (!map || !key) return;
    uint64_t hash = nova_fnv1a_hash(key->data, key->length);
    int64_t bucket_idx = (int64_t)(hash % (uint64_t)map->bucket_count);

    NovaMapEntry** pp = &map->buckets[bucket_idx];
    while (*pp) {
        NovaMapEntry* entry = *pp;
        if (nova_string_eq(entry->key, key)) {
            *pp = entry->next;
            nova_string_release(entry->key);
            nova_free(entry);
            map->size--;
            return;
        }
        pp = &entry->next;
    }
}

NovaList* nova_map_keys(NovaMap* map) {
    if (!map) return nova_list_new(4);
    NovaList* keys = nova_list_new((int64_t)map->size);
    for (int64_t i = 0; i < map->bucket_count; i++) {
        NovaMapEntry* entry = map->buckets[i];
        while (entry) {
            nova_list_push(keys, entry->key);
            entry = entry->next;
        }
    }
    return keys;
}

NovaList* nova_map_values(NovaMap* map) {
    if (!map) return nova_list_new(4);
    NovaList* values = nova_list_new((int64_t)map->size);
    for (int64_t i = 0; i < map->bucket_count; i++) {
        NovaMapEntry* entry = map->buckets[i];
        while (entry) {
            nova_list_push(values, entry->value);
            entry = entry->next;
        }
    }
    return values;
}

int64_t nova_map_size(NovaMap* map) {
    if (!map) return 0;
    return map->size;
}

void nova_map_retain(NovaMap* m) {
    if (m) m->ref_count++;
}

void nova_map_release(NovaMap* m) {
    if (!m) return;
    m->ref_count--;
    if (m->ref_count <= 0) {
        // 释放所有 entry
        for (int64_t i = 0; i < m->bucket_count; i++) {
            NovaMapEntry* entry = m->buckets[i];
            while (entry) {
                NovaMapEntry* next = entry->next;
                nova_string_release(entry->key);
                nova_free(entry);
                entry = next;
            }
        }
        nova_free(m->buckets);
        nova_free(m);
    }
}

// ============================================================
// ADT 操作
// ============================================================

NovaADT* nova_adt_new(int32_t type_id, int32_t variant_tag, int32_t field_count) {
    NovaADT* adt = (NovaADT*)nova_alloc(sizeof(NovaADT));
    adt->type_id = type_id;
    adt->variant_tag = variant_tag;
    adt->field_count = field_count;
    if (field_count > 0) {
        adt->fields = (void**)nova_alloc(sizeof(void*) * (size_t)field_count);
        memset(adt->fields, 0, sizeof(void*) * (size_t)field_count);
    } else {
        adt->fields = NULL;
    }
    adt->ref_count = 1;
    return adt;
}

void nova_adt_set_field(NovaADT* adt, int32_t idx, void* value) {
    if (!adt || idx < 0 || idx >= adt->field_count) return;
    adt->fields[idx] = value;
}

void* nova_adt_get_field(NovaADT* adt, int32_t idx) {
    if (!adt || idx < 0 || idx >= adt->field_count) return NULL;
    return adt->fields[idx];
}

NovaADT* nova_option_some(void* value) {
    NovaADT* opt = nova_adt_new(NOVA_TYPE_ID_OPTION, NOVA_OPTION_SOME_TAG, 1);
    nova_adt_set_field(opt, 0, value);
    return opt;
}

NovaADT* nova_option_none(void) {
    return nova_adt_new(NOVA_TYPE_ID_OPTION, NOVA_OPTION_NONE_TAG, 0);
}

bool nova_option_is_some(NovaADT* opt) {
    if (!opt) return false;
    return opt->variant_tag == NOVA_OPTION_SOME_TAG;
}

void* nova_option_unwrap(NovaADT* opt) {
    if (!opt || opt->variant_tag != NOVA_OPTION_SOME_TAG) {
        nova_panic("called unwrap() on a None value", __FILE__, __LINE__);
    }
    return opt->fields[0];
}

NovaADT* nova_result_ok(void* value) {
    NovaADT* result = nova_adt_new(NOVA_TYPE_ID_RESULT, NOVA_RESULT_OK_TAG, 1);
    nova_adt_set_field(result, 0, value);
    return result;
}

NovaADT* nova_result_err(void* error) {
    NovaADT* result = nova_adt_new(NOVA_TYPE_ID_RESULT, NOVA_RESULT_ERR_TAG, 1);
    nova_adt_set_field(result, 0, error);
    return result;
}

bool nova_result_is_ok(NovaADT* result) {
    if (!result) return false;
    return result->variant_tag == NOVA_RESULT_OK_TAG;
}

void* nova_result_unwrap(NovaADT* result) {
    if (!result || result->variant_tag != NOVA_RESULT_OK_TAG) {
        nova_panic("called unwrap() on an Err value", __FILE__, __LINE__);
    }
    return result->fields[0];
}

void nova_adt_retain(NovaADT* a) {
    if (a) a->ref_count++;
}

void nova_adt_release(NovaADT* a) {
    if (!a) return;
    a->ref_count--;
    if (a->ref_count <= 0) {
        if (a->fields) nova_free(a->fields);
        nova_free(a);
    }
}

// ============================================================
// 闭包操作
// ============================================================

NovaClosure* nova_closure_new(void* fn_ptr, void** captured, int32_t capture_count) {
    NovaClosure* closure = (NovaClosure*)nova_alloc(sizeof(NovaClosure));
    closure->fn_ptr = fn_ptr;
    closure->capture_count = capture_count;
    if (capture_count > 0) {
        closure->captured = (void**)nova_alloc(sizeof(void*) * (size_t)capture_count);
        for (int32_t i = 0; i < capture_count; i++) {
            closure->captured[i] = captured[i];
        }
    } else {
        closure->captured = NULL;
    }
    closure->ref_count = 1;
    return closure;
}

// 通用闭包调用函数指针类型：void* fn(void** captured, void** args, int32_t arg_count)
typedef void* (*nova_closure_fn_t)(void**, void**, int32_t);

void* nova_closure_call(NovaClosure* closure, void** args, int32_t arg_count) {
    if (!closure || !closure->fn_ptr) return NULL;
    nova_closure_fn_t fn = (nova_closure_fn_t)closure->fn_ptr;
    return fn(closure->captured, args, arg_count);
}

void nova_closure_retain(NovaClosure* c) {
    if (c) c->ref_count++;
}

void nova_closure_release(NovaClosure* c) {
    if (!c) return;
    c->ref_count--;
    if (c->ref_count <= 0) {
        if (c->captured) nova_free(c->captured);
        nova_free(c);
    }
}

// ============================================================
// I/O 操作
// ============================================================

void nova_print(NovaString* s) {
    if (s && s->data) {
        fwrite(s->data, 1, (size_t)s->length, stdout);
    }
}

void nova_println(NovaString* s) {
    nova_print(s);
    putchar('\n');
}

void nova_print_int(int64_t n) {
    printf("%lld", (long long)n);
}

void nova_print_float(double f) {
    printf("%.17g", f);
}

void nova_print_bool(bool b) {
    printf("%s", b ? "true" : "false");
}

NovaString* nova_read_line(void) {
    char buf[4096];
    if (!fgets(buf, sizeof(buf), stdin)) {
        return nova_string_new("");
    }
    // 去掉换行符
    int64_t len = (int64_t)strlen(buf);
    if (len > 0 && buf[len - 1] == '\n') {
        buf[len - 1] = '\0';
        len--;
    }
    if (len > 0 && buf[len - 1] == '\r') {
        buf[len - 1] = '\0';
        len--;
    }
    return nova_string_new_len(buf, len);
}

NovaString* nova_read_file(NovaString* path) {
    if (!path) return nova_string_new("");
    FILE* f = fopen(path->data, "rb");
    if (!f) return nova_string_new("");
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size < 0) {
        fclose(f);
        return nova_string_new("");
    }
    NovaString* result = nova_string_new_len(NULL, (int64_t)size);
    size_t read = fread(result->data, 1, (size_t)size, f);
    result->data[read] = '\0';
    result->length = (int64_t)read;
    fclose(f);
    return result;
}

void nova_write_file(NovaString* path, NovaString* content) {
    if (!path) return;
    FILE* f = fopen(path->data, "wb");
    if (!f) return;
    if (content && content->data && content->length > 0) {
        fwrite(content->data, 1, (size_t)content->length, f);
    }
    fclose(f);
}

bool nova_file_exists(NovaString* path) {
    if (!path) return false;
    FILE* f = fopen(path->data, "rb");
    if (f) {
        fclose(f);
        return true;
    }
    return false;
}

NovaList* nova_list_dir(NovaString* path) {
    NovaList* result = nova_list_new(16);
    if (!path) return result;

#ifdef _WIN32
    WIN32_FIND_DATAA find_data;
    char search_path[MAX_PATH];
    snprintf(search_path, sizeof(search_path), "%s\\*", path->data);
    HANDLE hFind = FindFirstFileA(search_path, &find_data);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (strcmp(find_data.cFileName, ".") != 0 && strcmp(find_data.cFileName, "..") != 0) {
                nova_list_push(result, nova_string_new(find_data.cFileName));
            }
        } while (FindNextFileA(hFind, &find_data));
        FindClose(hFind);
    }
#else
    DIR* dir = opendir(path->data);
    if (dir) {
        struct dirent* entry;
        while ((entry = readdir(dir)) != NULL) {
            if (strcmp(entry->d_name, ".") != 0 && strcmp(entry->d_name, "..") != 0) {
                nova_list_push(result, nova_string_new(entry->d_name));
            }
        }
        closedir(dir);
    }
#endif
    return result;
}

void nova_delete_file(NovaString* path) {
    if (!path) return;
    remove(path->data);
}

bool nova_create_dir(NovaString* path) {
    if (!path) return false;
    return nova_mkdir(path->data) == 0;
}

NovaString* nova_get_cwd(void) {
    char buf[4096];
    if (nova_getcwd_func(buf, sizeof(buf))) {
        return nova_string_new(buf);
    }
    return nova_string_new(".");
}

NovaString* nova_get_env(NovaString* name) {
    if (!name) return nova_string_new("");
    const char* val = getenv(name->data);
    return nova_string_new(val ? val : "");
}

int32_t nova_set_env(NovaString* name, NovaString* value) {
    if (!name) return -1;
#ifdef _WIN32
    return _putenv_s(name->data, value ? value->data : "") == 0 ? 0 : -1;
#else
    if (value) {
        return setenv(name->data, value->data, 1) == 0 ? 0 : -1;
    } else {
        return unsetenv(name->data) == 0 ? 0 : -1;
    }
#endif
}

// ============================================================
// 数学函数
// ============================================================

double nova_sqrt(double x) { return sqrt(x); }
double nova_abs(double x) { return fabs(x); }
int64_t nova_abs_int(int64_t x) { return x < 0 ? -x : x; }
double nova_sin(double x) { return sin(x); }
double nova_cos(double x) { return cos(x); }
double nova_tan(double x) { return tan(x); }
double nova_log(double x) { return log(x); }
double nova_log10(double x) { return log10(x); }
double nova_exp(double x) { return exp(x); }
double nova_pow(double base, double exp) { return pow(base, exp); }
double nova_floor(double x) { return floor(x); }
double nova_ceil(double x) { return ceil(x); }
double nova_round(double x) { return round(x); }
double nova_min(double a, double b) { return a < b ? a : b; }
double nova_max(double a, double b) { return a > b ? a : b; }
double nova_fmod(double a, double b) { return fmod(a, b); }
double nova_pi(void) { return M_PI; }

// ============================================================
// JSON 解析器 - 递归下降
// ============================================================

typedef struct {
    const char* input;
    int64_t pos;
    int64_t len;
} JsonParser;

static void json_skip_whitespace(JsonParser* p) {
    while (p->pos < p->len) {
        char c = p->input[p->pos];
        if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
            p->pos++;
        } else {
            break;
        }
    }
}

static char json_peek(JsonParser* p) {
    if (p->pos >= p->len) return '\0';
    return p->input[p->pos];
}

static char json_next(JsonParser* p) {
    if (p->pos >= p->len) return '\0';
    return p->input[p->pos++];
}

// 前向声明
static NovaValue* json_parse_value(JsonParser* p);

static NovaValue* json_parse_number(JsonParser* p) {
    int64_t start = p->pos;
    bool is_float = false;

    if (json_peek(p) == '-') p->pos++;

    while (p->pos < p->len && isdigit((unsigned char)p->input[p->pos])) p->pos++;

    if (p->pos < p->len && p->input[p->pos] == '.') {
        is_float = true;
        p->pos++;
        while (p->pos < p->len && isdigit((unsigned char)p->input[p->pos])) p->pos++;
    }

    if (p->pos < p->len && (p->input[p->pos] == 'e' || p->input[p->pos] == 'E')) {
        is_float = true;
        p->pos++;
        if (p->pos < p->len && (p->input[p->pos] == '+' || p->input[p->pos] == '-')) p->pos++;
        while (p->pos < p->len && isdigit((unsigned char)p->input[p->pos])) p->pos++;
    }

    int64_t num_len = p->pos - start;
    char num_buf[64];
    if (num_len >= (int64_t)sizeof(num_buf)) num_len = (int64_t)sizeof(num_buf) - 1;
    memcpy(num_buf, p->input + start, (size_t)num_len);
    num_buf[num_len] = '\0';

    NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
    val->ref_count = 1;

    if (is_float) {
        val->type = NOVA_VAL_FLOAT;
        val->float_val = strtod(num_buf, NULL);
    } else {
        val->type = NOVA_VAL_INT;
        val->int_val = strtoll(num_buf, NULL, 10);
    }

    return val;
}

static NovaValue* json_parse_array(JsonParser* p) {
    NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
    val->type = NOVA_VAL_LIST;
    val->list_val = nova_list_new(8);
    val->ref_count = 1;

    json_next(p); // skip '['
    json_skip_whitespace(p);

    if (json_peek(p) == ']') {
        json_next(p);
        return val;
    }

    while (1) {
        json_skip_whitespace(p);
        NovaValue* elem = json_parse_value(p);
        if (elem) nova_list_push(val->list_val, elem);

        json_skip_whitespace(p);
        if (json_peek(p) == ']') {
            json_next(p);
            break;
        }
        if (json_peek(p) == ',') {
            json_next(p);
        } else {
            break;
        }
    }
    return val;
}

static NovaValue* json_parse_object(JsonParser* p) {
    NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
    val->type = NOVA_VAL_MAP;
    val->map_val = nova_map_new(8);
    val->ref_count = 1;

    json_next(p); // skip '{'
    json_skip_whitespace(p);

    if (json_peek(p) == '}') {
        json_next(p);
        return val;
    }

    while (1) {
        json_skip_whitespace(p);

        // 解析 key（字符串）
        json_next(p); // skip opening "
        int64_t key_content_start = p->pos;
        while (p->pos < p->len && json_peek(p) != '"') {
            if (json_peek(p) == '\\') {
                p->pos += 2;
            } else {
                p->pos++;
            }
        }
        int64_t key_content_end = p->pos;
        if (json_peek(p) == '"') json_next(p);

        // 创建 key string
        int64_t key_len = key_content_end - key_content_start;
        NovaString* key_str = nova_string_new_len(p->input + key_content_start, key_len);

        // 去掉 key 中的转义字符以获得原始 key 名
        NovaString* raw_key = nova_string_new_len(NULL, key_len);
        int64_t ki = 0;
        for (int64_t i = 0; i < key_len; i++) {
            if (p->input[key_content_start + i] == '\\' && i + 1 < key_len) {
                i++;
                switch (p->input[key_content_start + i]) {
                    case '"':  raw_key->data[ki++] = '"'; break;
                    case '\\': raw_key->data[ki++] = '\\'; break;
                    case '/':  raw_key->data[ki++] = '/'; break;
                    case 'b':  raw_key->data[ki++] = '\b'; break;
                    case 'f':  raw_key->data[ki++] = '\f'; break;
                    case 'n':  raw_key->data[ki++] = '\n'; break;
                    case 'r':  raw_key->data[ki++] = '\r'; break;
                    case 't':  raw_key->data[ki++] = '\t'; break;
                    default:   raw_key->data[ki++] = p->input[key_content_start + i]; break;
                }
            } else {
                raw_key->data[ki++] = p->input[key_content_start + i];
            }
        }
        raw_key->data[ki] = '\0';
        raw_key->length = ki;
        nova_string_release(key_str);

        json_skip_whitespace(p);
        if (json_peek(p) == ':') json_next(p);
        json_skip_whitespace(p);

        // 解析 value
        NovaValue* v = json_parse_value(p);
        nova_map_put(val->map_val, raw_key, v);
        nova_string_release(raw_key);

        json_skip_whitespace(p);
        if (json_peek(p) == '}') {
            json_next(p);
            break;
        }
        if (json_peek(p) == ',') {
            json_next(p);
        } else {
            break;
        }
    }
    return val;
}

static NovaValue* json_parse_true(JsonParser* p) {
    NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
    val->type = NOVA_VAL_BOOL;
    val->bool_val = true;
    val->ref_count = 1;
    p->pos += 4; // skip "true"
    return val;
}

static NovaValue* json_parse_false(JsonParser* p) {
    NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
    val->type = NOVA_VAL_BOOL;
    val->bool_val = false;
    val->ref_count = 1;
    p->pos += 5; // skip "false"
    return val;
}

static NovaValue* json_parse_null(JsonParser* p) {
    NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
    val->type = NOVA_VAL_NULL;
    val->ref_count = 1;
    p->pos += 4; // skip "null"
    return val;
}

static NovaValue* json_parse_value(JsonParser* p) {
    json_skip_whitespace(p);
    char c = json_peek(p);
    if (c == '"') {
        // 解析字符串
        json_next(p); // skip opening "
        int64_t content_start = p->pos;
        while (p->pos < p->len && json_peek(p) != '"') {
            if (json_peek(p) == '\\') p->pos++;
            p->pos++;
        }
        int64_t content_end = p->pos;
        if (json_peek(p) == '"') json_next(p);

        // 解码转义
        int64_t raw_len = content_end - content_start;
        char* raw = (char*)nova_alloc(raw_len + 1);
        memcpy(raw, p->input + content_start, (size_t)raw_len);
        raw[raw_len] = '\0';

        int64_t decoded_len = 0;
        for (int64_t i = 0; i < raw_len; i++) {
            if (raw[i] == '\\' && i + 1 < raw_len) {
                i++;
                switch (raw[i]) {
                    case '"': case '\\': case '/': decoded_len++; break;
                    case 'b': case 'f': case 'n': case 'r': case 't': decoded_len++; break;
                    case 'u': decoded_len++; i += 4; break; // 粗略计算
                    default: decoded_len++;
                }
            } else {
                decoded_len++;
            }
        }

        NovaString* str = nova_string_new_len(NULL, decoded_len);
        int64_t wi = 0;
        for (int64_t i = 0; i < raw_len; i++) {
            if (raw[i] == '\\' && i + 1 < raw_len) {
                i++;
                switch (raw[i]) {
                    case '"':  str->data[wi++] = '"'; break;
                    case '\\': str->data[wi++] = '\\'; break;
                    case '/':  str->data[wi++] = '/'; break;
                    case 'b':  str->data[wi++] = '\b'; break;
                    case 'f':  str->data[wi++] = '\f'; break;
                    case 'n':  str->data[wi++] = '\n'; break;
                    case 'r':  str->data[wi++] = '\r'; break;
                    case 't':  str->data[wi++] = '\t'; break;
                    case 'u': {
                        char hex[5] = {0};
                        for (int j = 0; j < 4 && i + 1 < raw_len; j++) {
                            hex[j] = raw[++i];
                        }
                        int cp = (int)strtol(hex, NULL, 16);
                        if (cp < 0x80) {
                            str->data[wi++] = (char)cp;
                        } else if (cp < 0x800) {
                            str->data[wi++] = (char)(0xC0 | (cp >> 6));
                            str->data[wi++] = (char)(0x80 | (cp & 0x3F));
                        } else {
                            str->data[wi++] = (char)(0xE0 | (cp >> 12));
                            str->data[wi++] = (char)(0x80 | ((cp >> 6) & 0x3F));
                            str->data[wi++] = (char)(0x80 | (cp & 0x3F));
                        }
                        break;
                    }
                    default: str->data[wi++] = raw[i]; break;
                }
            } else {
                str->data[wi++] = raw[i];
            }
        }
        str->data[wi] = '\0';
        str->length = wi;
        nova_free(raw);

        NovaValue* val = (NovaValue*)nova_alloc(sizeof(NovaValue));
        val->type = NOVA_VAL_STRING;
        val->string_val = str;
        val->ref_count = 1;
        return val;
    } else if (c == '-' || (c >= '0' && c <= '9')) {
        return json_parse_number(p);
    } else if (c == '[') {
        return json_parse_array(p);
    } else if (c == '{') {
        return json_parse_object(p);
    } else if (c == 't') {
        return json_parse_true(p);
    } else if (c == 'f') {
        return json_parse_false(p);
    } else if (c == 'n') {
        return json_parse_null(p);
    }
    return NULL;
}

NovaValue* nova_json_parse(NovaString* text) {
    if (!text || text->length == 0) return NULL;
    JsonParser parser;
    parser.input = text->data;
    parser.pos = 0;
    parser.len = text->length;
    return json_parse_value(&parser);
}

// ============================================================
// JSON 序列化
// ============================================================

// 使用动态缓冲区构建 JSON 字符串
typedef struct {
    char* data;
    int64_t len;
    int64_t cap;
} JsonBuf;

static void json_buf_init(JsonBuf* buf) {
    buf->cap = 256;
    buf->data = (char*)nova_alloc(buf->cap);
    buf->data[0] = '\0';
    buf->len = 0;
}

static void json_buf_grow(JsonBuf* buf, int64_t needed) {
    while (buf->cap < buf->len + needed + 1) {
        buf->cap *= 2;
    }
    buf->data = (char*)nova_realloc(buf->data, buf->cap);
}

static void json_buf_append(JsonBuf* buf, const char* str, int64_t len) {
    json_buf_grow(buf, len);
    memcpy(buf->data + buf->len, str, (size_t)len);
    buf->len += len;
    buf->data[buf->len] = '\0';
}

static void json_buf_append_c(JsonBuf* buf, char c) {
    json_buf_grow(buf, 1);
    buf->data[buf->len++] = c;
    buf->data[buf->len] = '\0';
}

static void json_stringify_value(JsonBuf* buf, NovaValue* value);

static void json_stringify_string(JsonBuf* buf, const char* str, int64_t len) {
    json_buf_append_c(buf, '"');
    for (int64_t i = 0; i < len; i++) {
        char c = str[i];
        switch (c) {
            case '"':  json_buf_append(buf, "\\\"", 2); break;
            case '\\': json_buf_append(buf, "\\\\", 2); break;
            case '\b': json_buf_append(buf, "\\b", 2); break;
            case '\f': json_buf_append(buf, "\\f", 2); break;
            case '\n': json_buf_append(buf, "\\n", 2); break;
            case '\r': json_buf_append(buf, "\\r", 2); break;
            case '\t': json_buf_append(buf, "\\t", 2); break;
            default:
                if ((unsigned char)c < 0x20) {
                    char esc[8];
                    snprintf(esc, sizeof(esc), "\\u%04x", (unsigned char)c);
                    json_buf_append(buf, esc, (int64_t)strlen(esc));
                } else {
                    json_buf_append_c(buf, c);
                }
                break;
        }
    }
    json_buf_append_c(buf, '"');
}

static void json_stringify_value(JsonBuf* buf, NovaValue* value) {
    if (!value) {
        json_buf_append(buf, "null", 4);
        return;
    }
    switch (value->type) {
        case NOVA_VAL_NULL:
            json_buf_append(buf, "null", 4);
            break;
        case NOVA_VAL_INT: {
            char tmp[32];
            snprintf(tmp, sizeof(tmp), "%lld", (long long)value->int_val);
            json_buf_append(buf, tmp, (int64_t)strlen(tmp));
            break;
        }
        case NOVA_VAL_FLOAT: {
            char tmp[64];
            snprintf(tmp, sizeof(tmp), "%.17g", value->float_val);
            json_buf_append(buf, tmp, (int64_t)strlen(tmp));
            break;
        }
        case NOVA_VAL_STRING:
            json_stringify_string(buf, value->string_val->data, value->string_val->length);
            break;
        case NOVA_VAL_BOOL:
            if (value->bool_val) {
                json_buf_append(buf, "true", 4);
            } else {
                json_buf_append(buf, "false", 5);
            }
            break;
        case NOVA_VAL_UNIT:
            json_buf_append(buf, "null", 4);
            break;
        case NOVA_VAL_LIST: {
            json_buf_append_c(buf, '[');
            NovaList* list = value->list_val;
            for (int64_t i = 0; i < list->length; i++) {
                if (i > 0) json_buf_append_c(buf, ',');
                json_stringify_value(buf, (NovaValue*)list->items[i]);
            }
            json_buf_append_c(buf, ']');
            break;
        }
        case NOVA_VAL_MAP: {
            json_buf_append_c(buf, '{');
            NovaMap* map = value->map_val;
            bool first = true;
            for (int64_t i = 0; i < map->bucket_count; i++) {
                NovaMapEntry* entry = map->buckets[i];
                while (entry) {
                    if (!first) json_buf_append_c(buf, ',');
                    first = false;
                    json_stringify_string(buf, entry->key->data, entry->key->length);
                    json_buf_append_c(buf, ':');
                    json_stringify_value(buf, (NovaValue*)entry->value);
                    entry = entry->next;
                }
            }
            json_buf_append_c(buf, '}');
            break;
        }
        case NOVA_VAL_ADT: {
            json_buf_append_c(buf, '{');
            NovaADT* adt = value->adt_val;
            json_buf_append_c(buf, '"');
            json_buf_append(buf, "tag", 3);
            json_buf_append_c(buf, '"');
            json_buf_append_c(buf, ':');
            char tag_buf[16];
            snprintf(tag_buf, sizeof(tag_buf), "%d", adt->variant_tag);
            json_buf_append(buf, tag_buf, (int64_t)strlen(tag_buf));
            for (int32_t i = 0; i < adt->field_count; i++) {
                json_buf_append_c(buf, ',');
                json_buf_append_c(buf, '"');
                char field_name[16];
                snprintf(field_name, sizeof(field_name), "f%d", i);
                json_buf_append(buf, field_name, (int64_t)strlen(field_name));
                json_buf_append_c(buf, '"');
                json_buf_append_c(buf, ':');
                json_stringify_value(buf, (NovaValue*)adt->fields[i]);
            }
            json_buf_append_c(buf, '}');
            break;
        }
        case NOVA_VAL_CLOSURE:
            json_buf_append(buf, "\"<closure>\"", 11);
            break;
    }
}

NovaString* nova_json_stringify(NovaValue* value) {
    JsonBuf buf;
    json_buf_init(&buf);
    json_stringify_value(&buf, value);
    NovaString* result = nova_string_new(buf.data);
    nova_free(buf.data);
    return result;
}

void nova_value_retain(NovaValue* v) {
    if (v) v->ref_count++;
}

void nova_value_release(NovaValue* v) {
    if (!v) return;
    v->ref_count--;
    if (v->ref_count <= 0) {
        // 递减子对象的引用
        switch (v->type) {
            case NOVA_VAL_STRING:
                nova_string_release(v->string_val);
                break;
            case NOVA_VAL_LIST:
                nova_list_release(v->list_val);
                break;
            case NOVA_VAL_MAP:
                nova_map_release(v->map_val);
                break;
            case NOVA_VAL_ADT:
                nova_adt_release(v->adt_val);
                break;
            case NOVA_VAL_CLOSURE:
                nova_closure_release(v->closure_val);
                break;
            default:
                break;
        }
        nova_free(v);
    }
}

// ============================================================
// 进程/系统操作
// ============================================================

int32_t nova_system(NovaString* command) {
    if (!command) return -1;
    return system(command->data);
}

int32_t nova_exit(int32_t code) {
    exit(code);
    return code; // 不会执行到这里
}

int32_t nova_getpid(void) {
#ifdef _WIN32
    return (int32_t)_getpid();
#else
    return (int32_t)getpid();
#endif
}

NovaString* nova_platform(void) {
#ifdef _WIN32
    return nova_string_new("windows");
#elif defined(__linux__)
    return nova_string_new("linux");
#elif defined(__APPLE__)
    return nova_string_new("macos");
#elif defined(__FreeBSD__)
    return nova_string_new("freebsd");
#else
    return nova_string_new("unknown");
#endif
}

NovaString* nova_os_name(void) {
#ifdef _WIN32
    return nova_string_new("Windows");
#elif defined(__linux__)
    return nova_string_new("Linux");
#elif defined(__APPLE__)
    return nova_string_new("macOS");
#elif defined(__FreeBSD__)
    return nova_string_new("FreeBSD");
#else
    return nova_string_new("Unknown");
#endif
}

NovaString* nova_arch(void) {
#if defined(__x86_64__) || defined(_M_X64)
    return nova_string_new("x86_64");
#elif defined(__i386__) || defined(_M_IX86)
    return nova_string_new("x86");
#elif defined(__aarch64__) || defined(_M_ARM64)
    return nova_string_new("aarch64");
#elif defined(__arm__) || defined(_M_ARM)
    return nova_string_new("arm");
#elif defined(__powerpc64__)
    return nova_string_new("powerpc64");
#elif defined(__riscv)
    return nova_string_new("riscv");
#else
    return nova_string_new("unknown");
#endif
}

// ============================================================
// 命令行参数
// ============================================================

NovaList* nova_args(void) {
    NovaList* args = nova_list_new(g_argc > 0 ? g_argc : 1);
    for (int i = 0; i < g_argc; i++) {
        nova_list_push(args, nova_string_new(g_argv[i]));
    }
    return args;
}

// ============================================================
// 时间操作
// ============================================================

int64_t nova_time_now(void) {
#ifdef _WIN32
    FILETIME ft;
    GetSystemTimeAsFileTime(&ft);
    // FILETIME 是 100纳秒间隔，从 1601-01-01
    // 转换为 Unix epoch (1970-01-01)
    int64_t ticks = ((int64_t)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
    // 100ns ticks to ms, minus epoch offset
    int64_t ms = (ticks / 10000) - 11644473600000LL;
    return ms;
#else
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (int64_t)ts.tv_sec * 1000 + (int64_t)ts.tv_nsec / 1000000;
#endif
}

int64_t nova_time_unix(void) {
    return (int64_t)time(NULL);
}

NovaString* nova_time_format(NovaString* fmt, int64_t timestamp) {
    if (!fmt) return nova_string_new("");
    time_t t = (time_t)timestamp;
    struct tm* tm_info;

#ifdef _WIN32
    struct tm tm_buf;
    localtime_s(&tm_buf, &t);
    tm_info = &tm_buf;
#else
    struct tm tm_buf;
    localtime_r(&t, &tm_buf);
    tm_info = &tm_buf;
#endif

    char buf[256];
    strftime(buf, sizeof(buf), fmt->data, tm_info);
    return nova_string_new(buf);
}

int64_t nova_time_sleep_ms(int64_t ms) {
#ifdef _WIN32
    Sleep((DWORD)ms);
#else
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000;
    nanosleep(&ts, NULL);
#endif
    return 0;
}

// ============================================================
// 网络操作（基础 HTTP）
// ============================================================

NovaHttpResponse* nova_http_get(NovaString* url) {
    // 不依赖 libcurl 的简单实现：使用 system 调用 curl 命令
    // 如果没有 curl，返回 500 错误
    NovaHttpResponse* resp = (NovaHttpResponse*)nova_alloc(sizeof(NovaHttpResponse));
    resp->headers = nova_map_new(4);

    if (!url) {
        resp->status_code = 400;
        resp->body = nova_string_new("Bad Request: URL is null");
        return resp;
    }

    // 构造临时文件名
    char tmpfile[256];
#ifdef _WIN32
    snprintf(tmpfile, sizeof(tmpfile), "nova_http_%d.tmp", nova_getpid());
#else
    snprintf(tmpfile, sizeof(tmpfile), "/tmp/nova_http_%d.tmp", nova_getpid());
#endif

    // 使用 curl 命令
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "curl -s -o \"%s\" -w \"%%{http_code}\" \"%s\" 2>/dev/null", tmpfile, url->data);
    int ret = system(cmd);

    if (ret != 0) {
        resp->status_code = 503;
        resp->body = nova_string_new("Service Unavailable: curl command failed or not installed");
        return resp;
    }

    // 读取状态码（curl 写入了 stdout）
    // 简化实现：直接读取文件内容
    NovaString* content = nova_read_file(nova_string_new(tmpfile));
    resp->status_code = 200;
    resp->body = content;

    // 清理临时文件
    remove(tmpfile);

    return resp;
}

NovaHttpResponse* nova_http_post(NovaString* url, NovaString* body, NovaMap* headers) {
    (void)headers; // 暂未使用自定义 headers
    NovaHttpResponse* resp = (NovaHttpResponse*)nova_alloc(sizeof(NovaHttpResponse));
    resp->headers = nova_map_new(4);

    if (!url) {
        resp->status_code = 400;
        resp->body = nova_string_new("Bad Request: URL is null");
        return resp;
    }

    // 构造临时文件名
    char tmpfile_post[256];
    char tmpfile_data[256];
#ifdef _WIN32
    snprintf(tmpfile_post, sizeof(tmpfile_post), "nova_http_post_%d.tmp", nova_getpid());
    snprintf(tmpfile_data, sizeof(tmpfile_data), "nova_http_data_%d.tmp", nova_getpid());
#else
    snprintf(tmpfile_post, sizeof(tmpfile_post), "/tmp/nova_http_post_%d.tmp", nova_getpid());
    snprintf(tmpfile_data, sizeof(tmpfile_data), "/tmp/nova_http_data_%d.tmp", nova_getpid());
#endif

    // 写入请求体到临时文件
    nova_write_file(nova_string_new(tmpfile_data), body);

    // 使用 curl 命令 POST
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "curl -s -o \"%s\" -w \"%%{http_code}\" -d @\"%s\" \"%s\" 2>/dev/null",
             tmpfile_post, tmpfile_data, url->data);
    int ret = system(cmd);

    if (ret != 0) {
        resp->status_code = 503;
        resp->body = nova_string_new("Service Unavailable: curl command failed or not installed");
        remove(tmpfile_data);
        return resp;
    }

    NovaString* content = nova_read_file(nova_string_new(tmpfile_post));
    resp->status_code = 200;
    resp->body = content;

    remove(tmpfile_post);
    remove(tmpfile_data);

    return resp;
}

void nova_http_response_release(NovaHttpResponse* resp) {
    if (!resp) return;
    if (resp->body) nova_string_release(resp->body);
    if (resp->headers) nova_map_release(resp->headers);
    nova_free(resp);
}
