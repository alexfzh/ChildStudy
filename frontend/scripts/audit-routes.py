"""前端路由 meta 审计脚本（替代 vue-tsc：JS 项目用更轻量的方式）

检查 router/index.js 中所有路由的 meta 字段：
- 必须有 title（用户可见）
- 必须显式声明 role：parent / child / [parent, child] / undefined
  - public 路由（login/setup）必须只有 public=true
- 不允许出现非法角色字符串（拼写错误不会生效，TODO 是静默漏洞）

用法：
  python scripts/audit-routes.py [--strict]
  --strict: 把 WARN 当 ERROR，非零退出
  退出码：0 = 全部通过；1 = 有 ERROR
"""
import argparse
import os
import re
import sys

ROUTE_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'router', 'index.js')

ap = argparse.ArgumentParser()
ap.add_argument('--strict', action='store_true', help='把 WARN 当 ERROR')
args = ap.parse_args()

# ==== 解析 ====
with open(ROUTE_FILE, 'r', encoding='utf-8') as f:
    src = f.read()

# 找到所有路由条目：{ path: ..., ..., meta: { ... } }
# 简化：每行一个 meta 字段；外层用花括号深度匹配
route_pattern = re.compile(
    r'\{\s*path:\s*[\'"]?(/[^\'"}]*)[\'"]?,.*?meta:\s*\{([^}]*)\}',
    re.DOTALL,
)

valid_roles = {'parent', 'child'}

errors = []
warnings = []
ok_count = 0

for m in route_pattern.finditer(src):
    path = m.group(1)
    meta_body = m.group(2)

    # title
    title_m = re.search(r'title:\s*[\'"]([^\'"]*)[\'"]', meta_body)
    title = title_m.group(1) if title_m else None

    # public
    public_m = re.search(r'public:\s*(true|false)', meta_body)
    is_public = bool(public_m and public_m.group(1) == 'true')

    # role (string 或 array)
    role_m = re.search(r'role:\s*[\'"](\w+)[\'"]', meta_body)
    roles = None
    if role_m:
        roles = [role_m.group(1)]
    else:
        # array form: ["parent", "child"] 或 [parent, child]
        arr_m = re.search(r'role:\s*\[([^\]]+)\]', meta_body)
        if arr_m:
            inner = arr_m.group(1)
            roles = re.findall(r'[\'"](\w+)[\'"]', inner)

    # 校验
    if not is_public and path != '/':
        if title is None or title == '':
            warnings.append(f'WARN  {path:30s}  缺少 title（用户看到的浏览器标签）')
        if roles is None:
            warnings.append(f'WARN  {path:30s}  未声明 role（默认 parent + child 都可访问；如预期，请显式 role: ["parent", "child"]）')
        else:
            for r in roles:
                if r not in valid_roles:
                    errors.append(f'ERROR {path:30s}  非法角色 {r!r}，合法: {sorted(valid_roles)}（拼写错误会让角色守卫静默失效！）')

    if is_public:
        if roles is not None:
            warnings.append(f'WARN  {path:30s}  公开路由不应有 role 字段（public 已放行）')

    ok_count += 1

print(f'共扫描 {ok_count} 条路由')

fails = errors + (warnings if args.strict else [])

if fails:
    print(f'\n发现 {len(errors)} 个 ERROR + {len(warnings)} 个 WARN' + (' [strict]' if args.strict else ''))
    for line in errors + warnings:
        print(f'  {line}')
    sys.exit(1 if errors else (1 if args.strict else 0))
else:
    print('✓ 全部通过')
    sys.exit(0)