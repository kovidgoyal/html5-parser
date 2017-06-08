/*
 * Copyright (C) 2017 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the Apache 2.0 license.
 */


#define STACK_ITEM_CLASS(name) typedef struct { Item1 gumbo; Item2 xml; } name;
STACK_ITEM_CLASS(StackItemClass)
#undef STACK_ITEM_CLASS

#define STACK_CLASS(name) typedef struct { size_t length; size_t capacity; StackItemClass *items; } name;
STACK_CLASS(StackClass)
#undef STACK_CLASS

#define CONC(a, b) a ## _ ## b
#define EVAL(x, y) CONC(x, y)
#define FNAME(x) EVAL(StackClass, x)

static inline StackClass*
FNAME(alloc)(size_t sz) {
    StackClass *ans = calloc(sizeof(StackClass), 1);
    if (ans) {
        ans->items = (StackItemClass*)malloc(sizeof(StackItemClass) * sz);
        if (ans->items) ans->capacity = sz;
        else { free(ans); ans = NULL; }
    }
    return ans;
}

static inline void
FNAME(free)(StackClass *s) { if (s) { free(s->items); free(s); } }

static inline void
FNAME(pop)(StackClass *s, Item1 *g, Item2 *x) { StackItemClass *si = &(s->items[--(s->length)]); *g = si->gumbo; *x = si->xml; }

#ifndef SAFE_REALLOC_DEFINED
#define SAFE_REALLOC_DEFINED
static inline void*
safe_realloc(void *p, size_t sz) {
    void *orig = p;
    void *ans = realloc(p, sz);
    if (ans == NULL) free(orig);
    return ans;
}
#endif


static inline bool
FNAME(push)(StackClass *s, Item1 g, Item2 x) {
    if (s->length >= s->capacity) {
        s->capacity *= 2;
        s->items = (StackItemClass*)safe_realloc(s->items, s->capacity * sizeof(StackItemClass));
        if (!s->items) return false;
    }
    StackItemClass *si = &(s->items[(s->length)++]);
    si->gumbo = g; si->xml = x;
    return true;
}

#undef EVAL
#undef CONC
#undef FNAME
