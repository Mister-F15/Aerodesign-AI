"""Construction native sur macOS uniquement ; aucun lancement de navigateur."""
from pathlib import Path
import argparse, importlib.metadata, platform, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parent
HIDDEN=['sklearn.pipeline','sklearn.compose._column_transformer',
        'sklearn.preprocessing._data','sklearn.neural_network._multilayer_perceptron',
        'sklearn.ensemble._hist_gradient_boosting.gradient_boosting',
        'sklearn.ensemble._hist_gradient_boosting.predictor',
        'sklearn.ensemble._hist_gradient_boosting._predictor']

def command(arch):
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',
          '--onedir','--noupx','--name','AeroDesign AI',
          '--osx-bundle-identifier','org.aerodesignai.desktop',
          '--target-architecture',arch,'--distpath',str(ROOT/'dist'),
          '--workpath',str(ROOT/'build'),'--specpath',str(ROOT/'spec'),
          '--paths',str(ROOT/'app')]
    for name in HIDDEN:args+=['--hidden-import',name]
    for name in ['pytest','IPython','matplotlib','sklearn.tests','scipy.tests','pandas.tests','numpy.tests']:
        args+=['--exclude-module',name]
    for name in ['index.html','app.js','flow.js','optimize.js','style.css','reference_cases.json','case_exclusions.json']:
        args+=['--add-data',str(ROOT/'app'/name)+':app']
    for name in ['modeles','Licences']:args+=['--add-data',str(ROOT/name)+':'+name]
    return args+[str(ROOT/'desktop.py')]

def licenses():
    target=ROOT/'Licences';target.mkdir(exist_ok=True)
    for name in ['numpy','scipy','pandas','scikit-learn','joblib','threadpoolctl','python-dateutil','pytz','tzdata','six']:
        dist=importlib.metadata.distribution(name)
        for item in dist.files or []:
            if '.dist-info' in str(item) and any(x in item.name.lower() for x in ['license','licence','copying','notice']):
                source=Path(dist.locate_file(item))
                if source.is_file():
                    dest=target/name/item.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(source,dest)
    for source in [Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'Resources/LICENSE.txt']:
        if source.is_file():shutil.copy2(source,target/'Python_LICENSE.txt');break
    notices=['AeroDesign AI — licences des bibliothèques intégrées']
    for path in sorted(target.rglob('*')):
        if path.is_file() and path.name!='NOTICES.txt':
            notices+=['\n'+str(path.relative_to(target)),'-'*60,path.read_text(encoding='utf8',errors='replace')]
    (target/'NOTICES.txt').write_text('\n'.join(notices),encoding='utf8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--expected-arch',required=True,choices=['arm64','x86_64']);parser.add_argument('--plan',action='store_true');args=parser.parse_args()
    if args.plan:print(command(args.expected_arch));sys.exit(0)
    assert platform.system()=='Darwin','Construire sur un Mac.'
    assert platform.machine()==args.expected_arch,(platform.machine(),args.expected_arch)
    assert sys.version_info[:2]==(3,12),'Python 3.12 requis.'
    licenses();subprocess.run(command(args.expected_arch),cwd=ROOT,check=True)
    bundle=ROOT/'dist/AeroDesign AI.app'
    assert (bundle/'Contents/MacOS/AeroDesign AI').is_file()
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(bundle)],check=True)
    print('Application native construite :',bundle)
