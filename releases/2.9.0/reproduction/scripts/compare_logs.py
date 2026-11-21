import re,sys,glob,os
S=sys.argv[1]
num=re.compile(r'[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?')
def norm(t):
    t=t.replace(S+'/tree','ROOT').replace(S+'/base','ROOT')
    t=re.sub(r'\b\d+(\.\d+)?\s*(s|sec|seconds|ms|min)\b','T',t)
    t=re.sub(r'(?i)(time|elapsed|wall|took)[^\n]*','TIMELINE',t)
    t=re.sub(r'0x[0-9a-f]+','ADDR',t)
    return t
rows=[]
for rc in sorted(glob.glob(S+'/slog/tree/*.rc')):
    k=os.path.basename(rc)[:-3]
    if not os.path.exists(f'{S}/slog/base/{k}.rc'): continue
    rt=open(rc).read().strip(); rb=open(f'{S}/slog/base/{k}.rc').read().strip()
    a=norm(open(f'{S}/slog/tree/{k}.log',errors='replace').read()); b=norm(open(f'{S}/slog/base/{k}.log',errors='replace').read())
    if a==b: cls='identical'; d=''
    else:
        ta=num.findall(a); tb=num.findall(b)
        sa=num.sub('#',a); sb=num.sub('#',b)
        if sa==sb and len(ta)==len(tb):
            m=0;n=0
            for x,y in zip(ta,tb):
                x=float(x);y=float(y)
                if x!=y:
                    n+=1; m=max(m,abs(x-y)/max(abs(x),abs(y),1e-12))
            cls='numeric'; d=f'{n} numbers differ, max rel {m:.2e}'
        else:
            cls='text'; d=f'{len(a.splitlines())} vs {len(b.splitlines())} lines'
    rows.append((k,rt,rb,cls,d))
for r in rows: print('\t'.join(r))
