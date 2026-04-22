from fastapi.templating import Jinja2Templates

import weakref

templates = Jinja2Templates(directory="templates")

print(f"Loader type: {type(templates.env.loader)}")
print(f"Loader: {templates.env.loader}")

try:
    ref = weakref.ref(templates.env.loader)
    print(f"Weakref created: {ref}")
except Exception as exc:
    print(f"Error creating weakref: {exc}")

try:
    ref = weakref.ref(templates.env.loader)
    hash_val = hash(ref)
    print(f"Weakref hash: {hash_val}")
except Exception as exc:
    print(f"Error hashing weakref: {exc}")

try:
    cache_key = (weakref.ref(templates.env.loader), "index.html")
    hash_val = hash(cache_key)
    print(f"Cache key hash: {hash_val}")
except Exception as exc:
    print(f"Error creating cache key: {exc}")
