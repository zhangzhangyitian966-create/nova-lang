#include <tree_sitter/api.h>
#include <stdio.h>

extern const TSLanguage *tree_sitter_nova(void);

TSLanguage *tree_sitter_nova_language(void) {
    return (TSLanguage *)tree_sitter_nova();
}

int tree_sitter_nova_abi_version(void) {
    return TREE_SITTER_LANGUAGE_VERSION;
}
