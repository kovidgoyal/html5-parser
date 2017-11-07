#pragma once

#include <stddef.h>

typedef struct {
  const char *const from;
  const char *const to;
} StringReplacement;

const StringReplacement *gumbo_get_svg_tag_replacement(
  const char* str,
  size_t len
);

const StringReplacement *gumbo_get_svg_attr_replacement(
  const char* str,
  size_t len
);
