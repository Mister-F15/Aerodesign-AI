"""Point d'entrée commun Windows/Mac, sans installation côté utilisateur."""
from pathlib import Path
import argparse, json, os, sys, tempfile, threading, traceback, webbrowser

BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
sys.path.insert(0,str(BASE/'app'))

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--serve-test',action='store_true')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--stop-file',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    report=args.report or Path(tempfile.gettempdir())/'AeroDesign_AI_diagnostic.json'
    def write_report(data):
        report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    try:
        import server
        server.APP=BASE/'app';server.ROOT=BASE
        predictor=server.Predictor()
        if args.check:
            server.self_check(predictor)
            from optimizer import Optimizer
            value=Optimizer(predictor).search()
            assert [r['code'] for r in value['candidates']]==['6512','6612','6513','6514','5512']
            assert not predictor.evaluate('6715',0,1000000)['available']
            assert predictor.evaluate('6715',4,2000000)['available']
            import tkinter as tk
            from tkinter import ttk
            check_window=tk.Tk();check_window.withdraw()
            ttk.Button(check_window,text='Quitter').pack();check_window.update_idletasks();check_window.destroy()
            write_report(dict(passed=True,version='v0.1.1-beta',cases=27,flow=True,optimization=True,latest_quarantine=True,desktop_controls=True,model=predictor.pointer['identifiant'],frozen=bool(getattr(sys,'frozen',False))))
            return 0
        http=server.ThreadingHTTPServer(('127.0.0.1',args.port),server.Handler)
        http.predictor=predictor
        url=f'http://127.0.0.1:{http.server_port}'
        if args.serve_test:
            write_report(dict(ready=True,url=url,frozen=bool(getattr(sys,'frozen',False))))
            try:
                if args.stop_file:
                    http.timeout=.3
                    while not args.stop_file.exists():http.handle_request()
                else:http.serve_forever()
            finally:http.server_close()
            return 0
        import tkinter as tk
        from tkinter import ttk
        window=tk.Tk();window.title('AeroDesign AI');window.geometry('500x265');window.resizable(False,False)
        frame=ttk.Frame(window,padding=24);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='AeroDesign AI',font=('',20,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Votre application est ouverte dans le navigateur.\nLes calculs restent sur cet ordinateur.',padding=(0,12)).pack(anchor='w')
        address=tk.StringVar(value=url);ttk.Entry(frame,textvariable=address,state='readonly',width=56).pack(fill='x',pady=(0,15))
        def close():
            window.withdraw();http.shutdown();http.server_close();window.destroy()
        ttk.Button(frame,text='Ouvrir dans le navigateur',command=lambda:webbrowser.open(url)).pack(side='left')
        ttk.Button(frame,text='Licences',command=lambda:webbrowser.open((BASE/'Licences/NOTICES.txt').as_uri())).pack(side='left',padx=7)
        ttk.Button(frame,text='Quitter',command=close).pack(side='right')
        window.protocol('WM_DELETE_WINDOW',close)
        threading.Thread(target=http.serve_forever,daemon=True).start()
        window.after(200,lambda:webbrowser.open(url));window.mainloop()
        return 0
    except Exception:
        write_report(dict(passed=False,error=traceback.format_exc()))
        if not args.check and not args.serve_test:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root=tk.Tk();root.withdraw()
                messagebox.showerror('AeroDesign AI',f"Impossible de démarrer. Le diagnostic a été enregistré :\n{report}")
                root.destroy()
            except Exception:pass
        return 1

if __name__=='__main__':
    # Les exécutables sans console n'ont pas de stdout/stderr. Fournir un journal
    # plutôt que laisser les bibliothèques ou les requêtes HTTP écrire dans None.
    log=None
    if sys.stdout is None or sys.stderr is None:
        log=open(Path(tempfile.gettempdir())/'AeroDesign_AI.log','a',encoding='utf8')
        sys.stdout=sys.stderr=log
    result=run()
    if log:log.close()
    sys.exit(result)
