"""Field-map application (single, centralized concept).

A field_map is ``{source_key: target_key}``. Empty map = identity (the default).
The pipeline (``export_runner``) applies this once before handing books to an
adapter, so adapters do not each re-implement mapping. (review I1)

YAGNI: key renaming only, no value transforms.
"""


def apply_field_map(books, field_map):
    if not field_map:
        return books
    out = []
    for b in books:
        nb = dict(b)
        for src, tgt in field_map.items():
            if src in b:
                nb[tgt] = b[src]
        out.append(nb)
    return out
