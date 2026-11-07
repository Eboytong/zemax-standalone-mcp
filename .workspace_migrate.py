from pathlib import Path
import ast,json,re,shutil,subprocess,os
R=Path(__file__).resolve().parent
BASE='46da540'
originals=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=R).decode().splitlines()
mapping={};rows=[]
def move(src,dst):
 s=R/src;d=R/dst
 if s==d:return
 if s.exists():
  d.parent.mkdir(parents=True,exist_ok=True)
  if not d.exists():shutil.move(str(s),str(d))
 mapping[src]=dst
def write(p,s):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def read(p):return (R/p).read_text(encoding='utf-8-sig')
# Reconstruct original-to-current document locations.
explicit={'docs/development-plan.md':'development/plan.md','docs/next-development-plan.md':'development/current.md','docs/development-handoff.md':'development/handoff.md','docs/development-tasks.csv':'development/ledgers/packages.csv','docs/development-items.csv':'development/ledgers/operations.csv','docs/development-backlog.csv':'development/ledgers/analyses.csv','docs/development-functional-groups.json':'development/tracking/functional-groups.json','docs/development-batches.json':'development/tracking/batches.json','docs/development-remaining.md':'development/generated/remaining.md','docs/development-queue.json':'development/generated/queue.json','docs/development-remaining-ranked.md':'development/remaining-ranked.md','docs/history-archive.md':'development/archive/README.md','docs/history-archive-index.json':'development/archive/index.json','能力说明.md':'docs/README.md','验证记录.md':'development/evidence/verification-log.md','requirements-all.lock.txt':'requirements/all.lock.txt','requirements-core.lock.txt':'requirements/core.lock.txt','mcp.config.example.json':'examples/config/mcp.config.example.json'}
mapping.update(explicit)
for old in originals:
 if old in mapping:continue
 name=Path(old).name
 if old.startswith('docs/') and not (R/old).exists():
  hits=list((R/'docs').rglob(name))+list((R/'development').rglob(name))
  if len(hits)==1:mapping[old]=hits[0].relative_to(R).as_posix()
# Finish flat docs.
for p in list((R/'docs').glob('*')):
 if not p.is_file() or p.name=='README.md':continue
 if p.name.startswith('development-history') or p.name in ['rolling-development.md','development-difficulty-assessment.md']:
  move(p.relative_to(R).as_posix(),'development/archive/legacy/'+p.name)
 elif p.name=='capabilities.md':move('docs/'+p.name,'docs/reference/'+p.name)
 else:move('docs/'+p.name,'docs/topics/analysis/'+p.name)
# Evidence summaries retain their original bytes; raw histories stay local.
for old in originals:
 if old.startswith('verification/'):
  dest='development/evidence/'+old.removeprefix('verification/development/').removeprefix('verification/')
  d=R/dest;d.parent.mkdir(parents=True,exist_ok=True)
  d.write_bytes(subprocess.check_output(['git','show',BASE+':'+old],cwd=R))
  mapping[old]=dest
  local=R/'.local/evidence/development'/old.removeprefix('verification/development/')
  if old.startswith('verification/development/') and local.is_file():
   local.write_bytes(subprocess.check_output(['git','show',BASE+':'+old],cwd=R))
# Existing output directories are fixtures.
runroot=R/'.local/runs'
if (runroot/'runs').is_dir():
 for p in list((runroot/'runs').iterdir()):shutil.move(str(p),str(runroot/p.name))
 (runroot/'runs').rmdir()
for p in list(runroot.iterdir()):
 if p.is_dir():move(p.relative_to(R).as_posix(),'.local/fixtures/'+p.name)
# Tests in explicit packages, with a shared root constant.
write('tests/__init__.py','')
write('tests/unit/__init__.py','');write('tests/native/__init__.py','')
testmods={}
for p in list((R/'tests').glob('test_*.py')):
 target='native' if p.name.endswith('_live.py') else 'unit'
 dest='tests/'+target+'/'+p.name;move(p.relative_to(R).as_posix(),dest);testmods[p.stem]='tests.'+target+'.'+p.stem
# Keep mixed point-cloud tests intact initially; marker controls native entry.
# Shared support imports remain available through explicit tests.support package.
for p in (R/'tests').rglob('*.py'):
 text=p.read_text(encoding='utf-8-sig')
 text=re.sub(r'from support(?=[ .])','from tests.support',text)
 text=re.sub(r'from (test_\w+) import',lambda m:'from '+testmods.get(m[1],m[1])+' import',text)
 text=re.sub(r'Path\(__file__\)(?:\.resolve\(\))?\.parents\[[12]\]', 'PROJECT_ROOT',text)
 text=re.sub(r'Path\(__file__\)(?:\.resolve\(\))?\.parent\.parent', 'PROJECT_ROOT',text)
 if 'PROJECT_ROOT' in text and not re.search(r'from zemax_mcp.config import .*PROJECT_ROOT',text):text='from zemax_mcp.config import PROJECT_ROOT\n'+text
 p.write_text(text,encoding='utf-8')
# Conftest loads source before tests.support imports.
write('tests/conftest.py',subprocess.check_output(['git','show',BASE+':tests/conftest.py'],cwd=R).decode('utf-8'))
# Move standalone scripts after computing all module imports.
used=set()
for p in (R/'tests').rglob('*.py'):
 try:t=ast.parse(p.read_text(encoding='utf-8'))
 except SyntaxError:continue
 for n in ast.walk(t):
  if isinstance(n,ast.ImportFrom) and n.module:
   if n.module=='tests.support':used.update(a.name for a in n.names)
   elif n.module.startswith('tests.support.'):used.add(n.module.split('.')[2])
used.update(['paths','native','development_status'])
for p in list((R/'tests/support').glob('*.py')):
 if p.stem in used or p.name=='__init__.py':continue
 if p.name=='installed_schema_smoke.py':dest='scripts/release/'+p.name
 else:
  n=p.stem
  cat='MA-01' if any(k in n for k in ['gradium','material']) else 'MF-01' if 'sag' in n or 'manufacturing' in n else 'CV-01' if 'surface_mtf' in n or 'coherent' in n else 'NS-02' if any(k in n for k in ['nsc','path','zrd','critical']) else 'BASE-01'
  dest='scripts/probes/'+cat+'/'+p.name
 move('tests/support/'+p.name,dest)
 p=R/dest;text=p.read_text(encoding='utf-8-sig')
 text=re.sub(r'from (diffraction_reference|surface_reference|material_reference) import',r'from tests.support.\1 import',text)
 text='import sys\nfrom pathlib import Path\n_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())\nsys.path[:0]=[str(_workspace),str(_workspace/"src")]\n'+text
 p.write_text(text,encoding='utf-8')
# Development script is canonical; keep import shim for existing unit mocks.
move('tests/support/development_status.py','scripts/development/status.py')
p=R/'scripts/development/status.py';t=p.read_text(encoding='utf-8');t=t.replace('ROOT = PROJECT_ROOT','ROOT = Path(__file__).resolve().parents[2]');t=t.replace('from zemax_mcp.config import PROJECT_ROOT\n','')
t=t.replace("'docs/'+record['source']","'development/ledgers/'+dict(zip(['development-tasks.csv','development-items.csv','development-backlog.csv'],['packages.csv','operations.csv','analyses.csv']))[record['source']]").replace("plan='docs/next-development-plan.md'","plan='development/current.md'")
t=t.replace('verification/development/BASE-04','development/evidence/BASE-04')
write('scripts/development/status.py',t)
write('tests/support/development_status.py','import sys\nfrom scripts.development import status\nsys.modules[__name__] = status\n')
write('scripts/__init__.py','');write('scripts/development/__init__.py','')
# Root-level and known static paths; rewrite source references, not evidence bytes.
for p in (R/'examples/requests').glob('*.json'):mapping['examples/'+p.name]=p.relative_to(R).as_posix()
for p in (R/'examples/workflows').glob('*.py'):mapping['examples/'+p.name]=p.relative_to(R).as_posix()
mapping['wheels/zemax_standalone_mcp-0.1.61-py3-none-any.whl']='releases/0.1.61/zemax_standalone_mcp-0.1.61-py3-none-any.whl'
for root in ['tests','scripts','examples']:
 for p in (R/root).rglob('*.py'):
  text=p.read_text(encoding='utf-8-sig')
  text=text.replace('outputs/runs/','.local/fixtures/').replace("PROJECT_ROOT / \"outputs\"","PROJECT_ROOT / \".local\" / \"runs\"")
  for old,new in sorted(mapping.items(),key=lambda x:-len(x[0])):text=text.replace(old,new)
  p.write_text(text,encoding='utf-8')
# Central test output path.
p=R/'tests/support/paths.py';t=p.read_text(encoding='utf-8');t=t.replace('OUTPUTS_DIR = PROJECT_ROOT / "outputs"','OUTPUTS_DIR = PROJECT_ROOT / ".local"');t=t.replace('OUTPUTS_DIR / "fixtures"','OUTPUTS_DIR / "fixtures"');p.write_text(t,encoding='utf-8')
# Create paths for archive relocation without changing historical member keys.
idx=json.loads(read('development/archive/index.json'))
for e in idx['entries']:
 e['archive_location']='.local/'+e['archive']
write('development/archive/index.json',json.dumps(idx,ensure_ascii=False,indent=2)+'\n')
# Fix markdown links using original location rather than moved file depth.
reverse={v:k for k,v in mapping.items()}
for p in list((R/'docs').rglob('*.md'))+list((R/'development').rglob('*.md'))+[R/'README.md',R/'examples/README.md']:
 if 'evidence' in p.parts:continue
 rel=p.relative_to(R).as_posix();old=reverse.get(rel,rel);text=p.read_text(encoding='utf-8-sig')
 def link(m):
  target=m[1]
  if '://' in target or target.startswith('#'):return m[0]
  path,sep,frag=target.partition('#')
  candidate=os.path.normpath(str(Path(old).parent/path)).replace('\\','/')
  dest=mapping.get(candidate,candidate)
  if not (R/dest).exists():
   hits=[v for k,v in mapping.items() if Path(k).name==Path(path).name]
   if len(hits)==1:dest=hits[0]
  if (R/dest).exists():return ']('+os.path.relpath(R/dest,p.parent).replace('\\','/')+(sep+frag if sep else '')+')'
  return m[0]
 text=re.sub(r'\]\(([^)]+)\)',link,text)
 for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):text=text.replace(a,b)
 p.write_text(text,encoding='utf-8')
for old,new in mapping.items():rows.append(dict(original_path=old,current_path=new,purpose='workspace organization',tracked=not new.startswith('.local/')))
write('development/tracking/workspace-migration.json',json.dumps(dict(entries=rows,legacy_evidence_root='verification/development',current_raw_root='.local/evidence/development',fixture_root='.local/fixtures',archives='.local/archives'),ensure_ascii=False,indent=2)+'\n')
print('migrated',len(rows))
