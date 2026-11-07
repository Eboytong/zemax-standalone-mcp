from pathlib import Path
import ast,json,re,os,subprocess
R=Path(__file__).resolve().parent
def write(p,s):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def original(p):return subprocess.check_output(['git','show','46da540:'+p],cwd=R).decode('utf-8-sig')
# Canonical development tool, with fixtures in the new layout.
t=original('tests/support/development_status.py')
t=t.replace("ROOT / 'docs' / name", "ROOT / 'development/ledgers' / {'development-tasks.csv':'packages.csv','development-items.csv':'operations.csv','development-backlog.csv':'analyses.csv'}[name]")
t=t.replace('verification/development/BASE-04','development/evidence/BASE-04').replace('docs/development-functional-groups.json','development/tracking/functional-groups.json').replace('docs/development-batches.json','development/tracking/batches.json').replace("'docs/'+record['source']", "'development/ledgers/'+{'development-tasks.csv':'packages.csv','development-items.csv':'operations.csv','development-backlog.csv':'analyses.csv'}[record['source']]").replace('docs/next-development-plan.md','development/current.md')
t=t.replace('ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(__file__).resolve().parents[2]\nimport sys\nsys.path[:0] = [str(ROOT), str(ROOT / "src")]')
write('scripts/development/status.py',t)
write('tests/support/development_status.py','import sys\nfrom scripts.development import status\nsys.modules[__name__] = status\n')
test=R/'tests/unit/test_development_status_report.py';t=test.read_text(encoding='utf-8')
t=t.replace("(root / 'docs' / name)","(root / 'development/ledgers' / {'development-tasks.csv':'packages.csv','development-items.csv':'operations.csv','development-backlog.csv':'analyses.csv'}[name])")
t=t.replace("(tmp_path/'docs').mkdir()", "(tmp_path/'development/ledgers').mkdir(parents=True)\n    (tmp_path/'development/tracking').mkdir()")
t=t.replace("(tmp_path / 'docs').mkdir()", "(tmp_path / 'development/ledgers').mkdir(parents=True)\n    (tmp_path / 'development/tracking').mkdir()")
t=t.replace('verification/development/BASE-04','development/evidence/BASE-04').replace('docs/development-functional-groups.json','development/tracking/functional-groups.json').replace('docs/development-batches.json','development/tracking/batches.json')
test.write_text(t,encoding='utf-8')
# Explicit environment paths.
p=R/'install.ps1';t=p.read_text(encoding='utf-8');t=t.replace('requirements\\\\all.lock.txt','requirements\\all.lock.txt');p.write_text(t,encoding='utf-8')
p=R/'examples/config/mcp.config.example.json';t=p.read_text(encoding='utf-8');t=t.replace('outputs\\\\runs','.local\\\\runs').replace('outputs\\\\state','.local\\\\state');p.write_text(t,encoding='utf-8')
for p in (R/'examples/workflows').glob('*.py'):
 t=p.read_text(encoding='utf-8');t=t.replace('Path(__file__).with_name("extended_workflows.json")','PROJECT_ROOT/"examples/requests/extended_workflows.json"').replace('PROJECT_ROOT/"outputs"','PROJECT_ROOT/".local"/"runs"')
 p.write_text(t,encoding='utf-8')
# Split the one mixed test file; keep helper definitions shared.
p=R/'tests/unit/test_point_cloud.py';t=p.read_text(encoding='utf-8');tree=ast.parse(t);lines=t.splitlines(keepends=True);native=[];ranges=[]
for n in tree.body:
 if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and any('zemax' in ast.unparse(d) for d in n.decorator_list):
  a=min([n.lineno]+[d.lineno for d in n.decorator_list])-1;b=n.end_lineno;native.append(''.join(lines[a:b]));ranges.append((a,b))
if native:
 header='from pathlib import Path\nimport pytest\nfrom zemax_mcp.config import PROJECT_ROOT\n'
 write('tests/native/test_point_cloud_live.py',header+'\n\n'.join(native)+'\n')
 for a,b in reversed(ranges):del lines[a:b]
 p.write_text(''.join(lines),encoding='utf-8')
# Capability overview and fresh concise navigation.
write('docs/README.md',original('能力说明.md').replace('(docs/', '(')+ '\n\n文档分区：guides为调用指南，reference为接口参考，topics为业务专题。开发入口为[development/README](../development/README.md)。\n')
write('development/README.md','''# 开发入口

依次阅读 [长期规范](plan.md)、[当前计划](current.md)、[当前交接](handoff.md)。三份台账位于 `ledgers/`；共同功能和批次位于 `tracking/`；生成汇总位于 `generated/`。

```powershell
.\\.venv\\Scripts\\python.exe -B scripts/development/status.py --output development/generated/status.json --markdown development/generated/remaining.md --queue development/generated/queue.json
.\\.venv\\Scripts\\python.exe -B -m pytest tests/unit -q -p no:cacheprovider
.\\.venv\\Scripts\\python.exe -B -m pytest tests/native --run-zemax -q -p no:cacheprovider
```

原生测试串行执行。证据摘要在 `evidence/`；原始数据在 `.local/evidence`，大复现输入在 `.local/fixtures`；历史ZIP在 `.local/archives`。迁移清单为 `tracking/workspace-migration.json`。
''')
write('tests/README.md','''# 测试入口

`unit/`：普通测试；`native/`：OpticStudio串行测试；`support/`：共享夹具与数值参考。

普通测试：`.venv/Scripts/python.exe -B -m pytest tests/unit -q -p no:cacheprovider`。
原生测试：追加 `--run-zemax`，从 `tests/native` 选择单个用例执行。
''')
write('README.md','''# Zemax Standalone MCP 0.1.61

本机Windows x64、Python 3.14、OpticStudio 2024 R2的stdio MCP服务。100工具、110种分析。B005已发行；B006为5/10，目标0.1.62。

- [使用文档](docs/README.md) · [工具参考](docs/reference/tools.md) · [请求schema](docs/reference/tool-schemas.json)
- [开发入口](development/README.md) · [当前交接](development/handoff.md) · [剩余排序](development/remaining-ranked.md)
- [调用示例](examples/README.md) · [测试说明](tests/README.md)

安装：`powershell -NoProfile -ExecutionPolicy Bypass -File .\\install.ps1 -PythonExe C:\\Users\\tonge\\anaconda3\\python.exe -WithReports -WithGeometry`。
启动：`powershell -NoProfile -ExecutionPolicy Bypass -File .\\start.ps1`。
安装生成的客户端配置位于 `.local/config/mcp.config.json`。

| 目录 | 用途 |
| --- | --- |
| src | 产品源码 |
| docs | 使用指南、接口和专题 |
| development | 计划、台账、证据和交接 |
| tests | 普通/原生测试与共享参考 |
| scripts | 开发统计、探查和发行工具 |
| examples | 工作流、请求和输入资源 |
| requirements | 锁定依赖 |
| releases | 已发行wheel |
| .local | 本机运行、状态、复现数据和历史归档 |

`.local/runs`为默认运行目录；`.local/state`为状态目录。显式环境变量优先采用。当前wheel保留0.1.61原始产物。
''')
# Repair navigation after the final overview rewrite.
manifest=json.loads((R/'development/tracking/workspace-migration.json').read_text(encoding='utf-8'))
maps={e['original_path']:e['current_path'] for e in manifest['entries']}
for p in (R/'docs').rglob('*.md'):
 t=p.read_text(encoding='utf-8');old=next((a for a,b in maps.items() if b==p.relative_to(R).as_posix()),'docs/'+p.name)
 def fix(m):
  v=m[1]
  if '://' in v or v.startswith('#'):return m[0]
  v,sep,frag=v.partition('#');dest=maps.get(os.path.normpath(str(Path(old).parent/v)).replace('\\','/'))
  if not dest:
   found={b for a,b in maps.items() if Path(a).name==Path(v).name}
   if len(found)==1:dest=found.pop()
  if dest and (R/dest).exists():return ']('+os.path.relpath(R/dest,p.parent).replace('\\','/')+(sep+frag if sep else '')+')'
  return m[0]
 p.write_text(re.sub(r'\]\(([^)]+)\)',fix,t),encoding='utf-8')
print('finished layout')
