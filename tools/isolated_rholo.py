"""Standalone loopback-only Rholo lifecycle. Adapted from Rho Weave at cbfa663. No live node URL or signing."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for data in iter(lambda:f.read(1<<20),b''): h.update(data)
    return h.hexdigest()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect denied")

def fresh_ports():
    sockets=[]
    try:
        for _ in range(6):
            s=socket.socket(); s.bind(('127.0.0.1',0)); sockets.append(s)
        return [s.getsockname()[1] for s in sockets]
    finally:
        for s in sockets:s.close()

def run(binary,expected_hash,expected_commit,repeats,probe):
    if sha(binary)!=expected_hash: raise ValueError('binary digest mismatch')
    if not re.fullmatch('[0-9a-f]{40}',expected_commit): raise ValueError('invalid commit')
    if not 1<=repeats<=10: raise ValueError('repeats must be 1..10')
    with tempfile.TemporaryDirectory(prefix='forge-rholo-') as d:
        d=Path(d); home=d/'home';home.mkdir()
        env={'PATH':os.defpath,'HOME':str(home)}
        version=subprocess.check_output([str(binary),'--version'],env=env,stderr=subprocess.DEVNULL,timeout=10,text=True).strip()
        if version!=f'rnode 0.1.0 ({expected_commit})':raise ValueError('binary revision mismatch: '+version)
        keypem=subprocess.check_output(['openssl','ecparam','-name','secp256k1','-genkey','-noout'],env=env,stderr=subprocess.DEVNULL,timeout=10)
        keytext=subprocess.check_output(['openssl','ec','-text','-noout'],input=keypem,env=env,stderr=subprocess.DEVNULL,timeout=10).decode()
        priv,pub=keytext.split('priv:',1)[1].split('pub:',1)
        priv=re.sub(r'[^a-fA-F0-9]','',priv);pub=re.sub(r'[^a-fA-F0-9]','',pub.split('ASN1 OID:',1)[0])
        if len(priv)!=64 or len(pub)!=130 or not pub.startswith('04'):raise ValueError('unexpected synthetic key format')
        key=d/'validator.hex';key.write_text(priv+'\n');key.chmod(0o600)
        bonds=d/'bonds.txt';bonds.write_text(pub+' 100\n');wallets=d/'wallets.txt';wallets.touch()
        port,disc,external,internal,http,admin=fresh_ports();network='forge-'+uuid.uuid4().hex
        args=[str(binary),'run','--standalone','--no-upnp','--dev-mode','--host','127.0.0.1','--api-host','127.0.0.1','--network-id',network,'--shard-name','forge-isolated','--data-dir',str(d/'data'),'--protocol-port',str(port),'--discovery-port',str(disc),'--api-port-grpc-external',str(external),'--api-port-grpc-internal',str(internal),'--api-port-http',str(http),'--api-port-admin-http',str(admin),'--thread-pool-size','2','--autogen-shard-size','1','--validator-private-key-path',str(key),'--validator-public-key',pub,'--bonds-file',str(bonds),'--wallets-file',str(wallets),'--allow-under-minimum','--accept-under-minimum-risk','--no-attest-on-new-blocks']
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        def request(path,body=None):
            req=urllib.request.Request(f'http://127.0.0.1:{http}'+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with opener.open(req,timeout=5) as r:
                data=r.read(2_000_001)
            if len(data)>2_000_000: raise ValueError('oversize node response')
            return json.loads(data)
        with open(d/'node.log','wb') as log:
            proc=subprocess.Popen(args,env=env,cwd=d,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
            try:
                deadline=time.monotonic()+20;status=None
                while time.monotonic()<deadline and proc.poll() is None:
                    try:
                        candidate=request('/api/status')
                        if isinstance(candidate,dict) and isinstance(candidate.get('checkpoint'),dict) and candidate['checkpoint'].get('anchor') and candidate.get('syncPhase')=='running':
                            status=candidate; break
                    except (ValueError,OSError): pass
                    time.sleep(.2)
                if status is None: raise ValueError('isolated node failed to become ready')
                if status.get('networkId')!=network or status.get('shardId')!='/forge-isolated' or status.get('peers')!=0 or status.get('devMode') is not True:raise ValueError('isolation status mismatch')
                anchor=status['checkpoint']['anchor']
                rows=probe(request,repeats,anchor)
                end=request('/api/status')
                if end.get('networkId')!=network or end.get('peers')!=0 or end.get('latestBlockNumber')!=status.get('latestBlockNumber') or end['checkpoint']['anchor']!=anchor:raise ValueError('chain changed during probe')
                return {'binary_sha256':expected_hash,'binary_commit':expected_commit,'runtime_version':version,'fixture_count':len(rows),'repeats':repeats,'peer_count':0,'block_height_before':status['latestBlockNumber'],'block_height_after':end['latestBlockNumber'],'passed':all(r['passed'] for r in rows),'fixtures':rows}
            finally:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
