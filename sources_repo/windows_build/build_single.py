"""Fabriquer le fichier Windows autonome, sans collecte globale de sklearn."""
from pathlib import Path
import importlib.metadata,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
assert sys.platform=='win32' and sys.version_info[:2]==(3,12)
licenses=ROOT/'Licences';licenses.mkdir(exist_ok=True)
for name in ['numpy','scipy','pandas','scikit-learn','joblib','threadpoolctl','python-dateutil','pytz','tzdata','six']:
    dist=importlib.metadata.distribution(name)
    for item in dist.files or []:
        if any(token in item.name.lower() for token in ['license','licence','copying','notice']) and '.dist-info' in str(item):
            source=Path(dist.locate_file(item))
            if source.is_file():
                target=licenses/name/item.name;target.parent.mkdir(exist_ok=True);shutil.copy2(source,target)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copy2(python_license,licenses/'Python_LICENSE.txt')
tk=Path(sys.base_prefix)/'Library/lib'
for name in ['tcl8.6','tk8.6']:
    source=tk/name/'license.terms'
    if source.exists():shutil.copy2(source,licenses/(name+'_license.txt'))
notices=['AeroDesign AI — bibliothèques intégrées et licences','']
for item in sorted(licenses.rglob('*')):
    if item.is_file() and item.name!='NOTICES.txt':
        notices.extend(['\n'+str(item.relative_to(licenses)),'-'*60,item.read_text(encoding='utf8',errors='replace')])
(licenses/'NOTICES.txt').write_text('\n'.join(notices),encoding='utf8')
hidden=['sklearn.pipeline','sklearn.compose._column_transformer','sklearn.preprocessing._data','sklearn.neural_network._multilayer_perceptron','sklearn.ensemble._hist_gradient_boosting.gradient_boosting','sklearn.ensemble._hist_gradient_boosting.predictor','sklearn.ensemble._hist_gradient_boosting._predictor']
command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--noupx','--name','AeroDesign AI','--distpath',str(ROOT/'dist_single'),'--workpath',str(ROOT/'build_single'),'--specpath',str(ROOT/'spec_single'),'--paths',str(ROOT/'app')]
for name in hidden:command+=['--hidden-import',name]
for name in ['pytest','IPython','matplotlib','sklearn.tests','scipy.tests','pandas.tests','numpy.tests']:command+=['--exclude-module',name]
for name in ['index.html','app.js','flow.js','optimize.js','style.css','reference_cases.json','case_exclusions.json']:
    path=ROOT/'app'/name
    if path.exists():command+=['--add-data',str(path)+':app']
for name in ['modeles','Licences']:command+=['--add-data',str(ROOT/name)+':'+name]
for name in ['ffi.dll','sqlite3.dll','tk86t.dll','tcl86t.dll']:
    dll=Path(sys.base_prefix)/'Library/bin'/name
    if dll.exists():command+=['--add-binary',str(dll)+':.']
command.append(str(ROOT/'desktop.py'))
subprocess.run(command,cwd=ROOT,check=True)
print('Exécutable :',ROOT/'dist_single/AeroDesign AI.exe')
