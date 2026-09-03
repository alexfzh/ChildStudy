import importlib.util

spec = importlib.util.spec_from_file_location("seed", "_seed_knowledge_points.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for i, item in enumerate(mod.DATA):
    if "grade_level" not in item:
        print(i, item)
print("total:", len(mod.DATA))
