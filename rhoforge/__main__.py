import argparse,json,sys
from pathlib import Path
from .compiler import compile_workflow,ForgeError,LimitError
from .partition import compile_partitioned

def load(path):
    def pairs(xs):
        out={}
        for k,v in xs:
            if k in out: raise ForgeError('duplicate key: '+k)
            out[k]=v
        return out
    with open(path,'rb') as f: b=f.read(262145)
    if len(b)>262144: raise LimitError('input byte limit')
    return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda v: (_ for _ in ()).throw(ForgeError('nonfinite value')))

def main():
    p=argparse.ArgumentParser(description='Compile bounded resource workflows to Rholang capability actors')
    p.add_argument('spec')
    p.add_argument('--out',type=Path,required=True,help='new directory (must not exist)')
    p.add_argument('--partition',action='store_true',help='emit a private factory with independent resource lanes')
    a=p.parse_args()
    try:
        compile_spec = compile_partitioned if a.partition else compile_workflow
        m,s=compile_spec(load(a.spec));a.out.mkdir(parents=False,exist_ok=False)
        (a.out/'factory.rho').write_text(s,encoding='utf-8');(a.out/'manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        tables = list(m['lanes'].values()) if a.partition else [m]
        result = {'status':'COMPILED','states':sum(len(t['markings']) for t in tables),
                  'primitive_edges':sum(t['primitive_edges'] for t in tables),
                  'factory':m['factory'],'output':str(a.out)}
        if a.partition:
            result['lanes'] = list(m['lanes'])
        print(json.dumps(result));return 0
    except LimitError as e: print(json.dumps({'status':'UNKNOWN','reason':str(e)}),file=sys.stderr);return 2
    except (ValueError,OSError,TypeError,KeyError,RecursionError) as e: print(json.dumps({'status':'ERROR','reason':str(e)}),file=sys.stderr);return 2
if __name__=='__main__': raise SystemExit(main())
