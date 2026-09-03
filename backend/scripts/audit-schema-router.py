"""Schema vs Router 冲突审计（防 422 类 bug）

扫描规则：
1. 冲突 A（ERROR）：@router.post("/{child_id}", ...) + payload 中 child_id 必填
   -> router 从路径注入，前端不传 -> 必 422。修复：Base schema 中 child_id: int -> Optional[int] = None

2. 警告（WARN）：@router.post("", ...) + payload 中 child_id 必填
   -> child_id 来自 body，前端必须传。当前是设计预期，依赖前端正确性。

用法：
  python scripts/audit-schema-router.py [--strict]
退出码：0 = 无 ERROR；1 = 有 ERROR 或 strict 模式有 WARN
"""
import argparse
import os
import re
import sys

BACKEND = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))


def parse_schemas():
    """返回 {class_name: 'required'|'optional'|'absent'}"""
    schemas_dir = os.path.join(BACKEND, 'schemas')
    texts = []
    for fname in sorted(os.listdir(schemas_dir)):
        if not fname.endswith('.py') or fname == '__init__.py':
            continue
        with open(os.path.join(schemas_dir, fname), 'r', encoding='utf-8') as f:
            texts.append(f.read())
    text = '\n'.join(texts)

    result = {}
    for m in re.finditer(r'^class (\w+)\b[\s\S]*?(?=^class |\Z)', text, re.MULTILINE):
        name = m.group(1)
        body = m.group(0)
        cm = re.search(r'child_id:\s*(\w+[\w\[\], ]*?)(?:\s*=\s*[^,\n]+)?(?:,|\n)', body)
        if cm:
            type_str = cm.group(1).strip()
            next_line = body.split('child_id')[1].split('\n')[0] if 'child_id' in body else ''
            is_optional = 'Optional' in type_str or '= None' in next_line
            result[name] = 'optional' if is_optional else 'required'
        else:
            result[name] = 'absent'
    return result


def find_post_routes(text):
    """返回 [(path_arg, fn_name, params_block), ...]"""
    results = []
    for m in re.finditer(r'@router\.post\(["\']([^"\']*)["\']', text):
        path_arg = m.group(1)
        # 找紧随的 async def
        fn_match = re.search(r'async def (\w+)\(', text[m.end():])
        if not fn_match:
            continue
        fn = fn_match.group(1)

        # 提取参数块
        fn_def_pos = text.find(f'async def {fn}(', m.end())
        if fn_def_pos < 0:
            continue
        paren_start = text.find('(', fn_def_pos)
        depth = 0
        i = paren_start
        while i < len(text):
            c = text[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        params_block = text[paren_start+1:i]
        results.append((path_arg, fn, params_block))
    return results


def audit(strict=False):
    schemas = parse_schemas()
    errors = []
    warnings = []

    routers_dir = os.path.join(BACKEND, 'routers')
    for fname in sorted(os.listdir(routers_dir)):
        if not fname.endswith('.py') or fname == '__init__.py':
            continue
        path = os.path.join(routers_dir, fname)
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()

        for path_arg, fn, params_block in find_post_routes(text):
            payload_m = re.search(r'payload:\s*(\w+)', params_block)
            if not payload_m:
                continue
            payload = payload_m.group(1)
            cid_status = schemas.get(payload, 'absent')

            # 规则 1: ERROR
            if 'child_id' in path_arg and cid_status == 'required':
                errors.append(
                    f'ERROR routers/{fname}:{fn}: POST "{path_arg}" payload={payload} '
                    f'-> schema child_id 必填但 router 从路径注入 (frontend 必 422)'
                )

            # 规则 2: WARN
            if path_arg == '' and cid_status == 'required':
                warnings.append(
                    f'WARN  routers/{fname}:{fn}: POST "" payload={payload} '
                    f'-> child_id 必填，依赖前端 body 传入'
                )

    print(f'扫描完成：{len(errors)} ERROR + {len(warnings)} WARN')
    for line in errors + warnings:
        print(f'  {line}')

    if errors:
        return 1
    if warnings and strict:
        return 1
    return 0


if __name__ == '__main__':
    # 脚本会 print 中文;GitHub Windows runner(英文系统 cp1252)默认 stdout 无法编码
    # 中文会抛 UnicodeEncodeError。强制 UTF-8 输出,规避平台编码差异。
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()
    sys.exit(audit(strict=args.strict))
