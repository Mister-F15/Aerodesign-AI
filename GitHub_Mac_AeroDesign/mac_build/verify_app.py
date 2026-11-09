"""Vérifier les calculs et le service local, sans ouvrir de navigateur."""
from pathlib import Path
import argparse, hashlib, json, os, platform, subprocess, sys, tempfile, time
import urllib.request, urllib.error

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source',action='store_true');mode.add_argument('--frozen',action='store_true')
    parser.add_argument('--expected-arch',choices=['arm64','x86_64']);args=parser.parse_args()
    if args.expected_arch:assert platform.machine()==args.expected_arch
    pointer=json.loads((ROOT/'modeles/MODELE_ACTUEL.json').read_text(encoding='utf8'))
    digest=hashlib.sha256((ROOT/pointer['model_file']).read_bytes()).hexdigest()
    assert digest==pointer['model_sha256']
    executable=ROOT/'dist/AeroDesign AI.app/Contents/MacOS/AeroDesign AI'
    launcher=[str(executable)] if args.frozen else [sys.executable,str(ROOT/'desktop.py')]
    env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','CONDA'))}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin' if args.frozen else os.environ.get('PATH',''),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2')
    name='frozen' if args.frozen else 'source'
    with tempfile.TemporaryDirectory(prefix='AeroDesign essai déplacé ') as folder:
        work=Path(folder);check=work/'check.json'
        subprocess.run(launcher+['--check','--report',str(check)],cwd=work,env=env,check=True,timeout=180)
        result=json.loads(check.read_text(encoding='utf8'));assert result['passed']
        assert result['frozen']==args.frozen
        ready=work/'ready.json';stop=work/'stop.flag'
        child=subprocess.Popen(launcher+['--serve-test','--port','0','--report',str(ready),'--stop-file',str(stop)],cwd=work,env=env)
        try:
            for _ in range(200):
                if ready.exists():break
                if child.poll() is not None:raise RuntimeError('Arrêt avant démarrage du serveur.')
                time.sleep(.2)
            status=json.loads(ready.read_text(encoding='utf8'));assert status.get('ready'),status
            base=status['url'];client=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def get(route):return json.load(client.open(base+route,timeout=60))
            assert get('/api/evaluate?naca=2412&alpha=4&re=1000000')['available']
            assert not get('/api/evaluate?naca=6715&alpha=0&re=1000000')['available']
            assert get('/api/evaluate?naca=6715&alpha=4&re=2000000')['available']
            default=get('/api/optimize')
            assert [r['code'] for r in default['candidates']]==['6512','6612','6513','6514','5512']
            for objective in ['min_CD','max_CL']:
                assert len(get('/api/optimize?objective='+objective)['candidates'])==5
            flow=get('/api/flow?naca=0012&alpha=4');assert len(flow['streamlines'])>10
            for path in ['/','/app.js','/flow.js','/optimize.js','/style.css']:
                assert client.open(base+path,timeout=15).status==200
            try:client.open(base+'/api/xfoil',timeout=10)
            except urllib.error.HTTPError as error:assert error.code==404
            else:raise AssertionError('XFOIL ne doit pas être livré.')
            result.update(http=True,three_objectives=True,static_assets=True,no_xfoil=True,
                          machine=platform.machine(),system=platform.platform(),model_sha256=digest)
        finally:
            stop.write_text('stop',encoding='ascii')
            try:child.wait(timeout=30)
            except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=15);raise
    (ROOT/f'verification_{name}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
