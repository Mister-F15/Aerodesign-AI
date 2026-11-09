"""Préserver les permissions et liens de la .app dans une archive macOS."""
from pathlib import Path
import argparse, hashlib, json, platform, shutil, subprocess

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--edition',choices=['Intel','AppleSilicon'],required=True);args=parser.parse_args()
    expected={'Intel':'x86_64','AppleSilicon':'arm64'}[args.edition]
    assert platform.system()=='Darwin' and platform.machine()==expected
    report=json.loads((ROOT/'verification_frozen.json').read_text(encoding='utf8'))
    assert report['passed'] and report['frozen'] and report['machine']==expected
    bundle=ROOT/'dist/AeroDesign AI.app';out=ROOT/'livraison';out.mkdir(exist_ok=True)
    archive=out/f'AeroDesign_AI_Mac_{args.edition}.zip'
    subprocess.run(['/usr/bin/ditto','-c','-k','--sequesterRsrc','--keepParent',str(bundle),str(archive)],check=True)
    # Vérifier aussi la copie extraite de l'archive réellement livrée.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='AeroDesign archive ') as temp:
        subprocess.run(['/usr/bin/ditto','-x','-k',str(archive),temp],check=True)
        copied=Path(temp)/'AeroDesign AI.app';binary=copied/'Contents/MacOS/AeroDesign AI'
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(copied)],check=True)
        check=Path(temp)/'archive_check.json'
        subprocess.run([str(binary),'--check','--report',str(check)],cwd=temp,check=True,timeout=180)
        assert json.loads(check.read_text(encoding='utf8'))['passed']
    report.update(edition=args.edition,archive_tested=True,archive_bytes=archive.stat().st_size,
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  signing='signature ad hoc locale ; application non notariée par Apple',
                  compatibility='fabriquée et testée sur macOS 15 ; autres versions à vérifier')
    (out/'VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    shutil.copy2(ROOT/'LIRE_SUR_MAC.txt',out/'LIRE_SUR_MAC.txt')
    print('Archive prête :',archive)
if __name__=='__main__':main()
