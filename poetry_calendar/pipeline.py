import copy
import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from .adapters import ADAPTERS, Result
from .fetch import Fetcher
from .model import SCHEMA_VERSION, content_identity, canonical_url, forthcoming, parse_date

def atomic_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    os.replace(temp,path)

@contextmanager
def update_lock(root):
    path=root/'data/.update.lock'; path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: raise RuntimeError('An update lock exists. Check for a running update before removing it.')
    try:
        os.write(fd,str(os.getpid()).encode()); os.close(fd); yield
    finally: path.unlink(missing_ok=True)

def load_state(root):
    path=root/'data/state.json'
    if not path.exists(): return {'schema_version':SCHEMA_VERSION,'records':[],'sources':{},'last_attempt_at':None}
    state=json.loads(path.read_text(encoding='utf-8'))
    if state['schema_version']!=SCHEMA_VERSION: raise ValueError('Unsupported dataset schema; explicit migration required')
    return state

def load_registry(root):
    registry=json.loads((root/'config/publishers.json').read_text(encoding='utf-8'))
    ids=set()
    for p in registry:
        if p['id'] in ids or not p['id']: raise ValueError('Duplicate or empty publisher ID')
        ids.add(p['id'])
        for url in p['sources']: canonical_url(url)
        if p['enabled'] and p['adapter'] not in ADAPTERS: raise ValueError(f"Unknown adapter for {p['id']}")
    return registry

def reconcile(state,publisher,result,now,today):
    """Never delete on absence. Merge verified changes; quarantine unexplained collapse."""
    pid=publisher['id']; old_status=state['sources'].get(pid,{})
    old=[r for r in state['records'] if r['publisher_id']==pid]
    previous_count=old_status.get('accepted_count',0)
    incoming={}; incoming_identity={}; conflicts=set()
    identity={content_identity(r):r for r in old}
    by_url={r['source_url']:r for r in old}
    for r in result.records:
        prior=by_url.get(r['source_url']) or identity.get(content_identity(r)) or incoming_identity.get(content_identity(r))
        if prior: r['id']=prior['id']
        if r['id'] in conflicts: continue
        match=incoming.get(r['id'])
        if match and match['date']!=r['date']:
            result.warn(r['source_url'],'Conflicting dates for the same publication; existing value retained')
            incoming.pop(r['id'],None)
            conflicts.add(r['id'])
            # Further conflicting observations cannot restore this item in this run.
            continue
        incoming[r['id']]=r
        incoming_identity[content_identity(r)]=r
    suspicious=previous_count>=3 and len(incoming)<previous_count*0.5
    if suspicious:
        result.warn(publisher['sources'][0],'Candidate count fell by more than half; update quarantined')
        incoming={}
    merged=[]; seen=set()
    for prior in old:
        r=incoming.get(prior['id'])
        if r:
            r=copy.deepcopy(r); seen.add(r['id'])
            r['first_seen_at']=prior['first_seen_at']; r['last_seen_at']=now; r['last_verified_at']=now
            r['missing_checks']=0
            history=prior.get('history',[])
            before={k:prior.get(k) for k in ('title','contributors','date','source_url','record_status')}
            after={k:r.get(k) for k in before}
            if before!=after: history=history+[{'observed_at':now,'previous':before}]
            r['history']=history
        else:
            r=copy.deepcopy(prior)
            if result.complete:
                if r.get('last_missing_date')!=today.isoformat():
                    r['missing_checks']=r.get('missing_checks',0)+1
                    r['last_missing_date']=today.isoformat()
                if r['missing_checks']>=3:
                    r['record_status']='uncertain'
                    result.warnings.append({'url':r['source_url'],'reason':'Missing from three complete checks; held for review'})
        merged.append(r)
    for rid,r in incoming.items():
        if rid not in seen:
            r=copy.deepcopy(r); r.update(first_seen_at=now,last_seen_at=now,last_verified_at=now,missing_checks=0,history=[])
            merged.append(r)
    state['records']=[r for r in state['records'] if r['publisher_id']!=pid]+merged
    status='ok' if result.complete else 'partial'
    if not result.complete and not result.records: status='failed'
    state['sources'][pid]={
        'status':status,'attempted_at':now,
        'last_success_at':now if result.complete else old_status.get('last_success_at'),
        'last_data_at':now if incoming else old_status.get('last_data_at'),
        'candidates':result.candidates,'valid_records':len(result.records),'excluded':result.excluded,
        'accepted_count':len(incoming) if result.complete else previous_count,
        'forthcoming_count':sum(forthcoming(r,today) for r in merged),
        'warnings':result.warnings,'scope':publisher['coverage']}

def effective_records(state,overrides,today):
    records=copy.deepcopy(state['records']); known={r['id'] for r in records}
    if set(overrides)-known: raise ValueError('Override references an unknown record ID')
    for r in records:
        override=overrides.get(r['id'])
        if override:
            if not override.get('reason') or not override.get('evidence_url'): raise ValueError('Overrides require reason and evidence_url')
            canonical_url(override['evidence_url'])
            allowed={'title','contributors','record_status','date','source_url'}
            changes=override.get('set',{})
            if set(changes)-allowed: raise ValueError('Unsupported override fields')
            if 'date' in changes: changes={**changes,'date':parse_date(changes['date'])}
            if 'source_url' in changes: canonical_url(changes['source_url'])
            r.update(changes); r['override_reason']=override['reason']
        if r['date']['precision'] in ('unknown','year') and (today-date.fromisoformat(r['last_verified_at'][:10])).days>180:
            r['record_status']='uncertain'
    return records

def collect(root,today,publisher_ids=None):
    registry=load_registry(root)
    if publisher_ids and set(publisher_ids)-{p['id'] for p in registry}: raise ValueError('Unknown publisher requested')
    with update_lock(root):
        state=load_state(root); now=datetime.now(timezone.utc).isoformat(timespec='seconds')
        for p in registry:
            if publisher_ids and p['id'] not in publisher_ids: continue
            if not p['enabled']:
                state['sources'][p['id']]={**state['sources'].get(p['id'],{}),'status':p['access_status'],'warnings':[],'scope':p['coverage']}
                continue
            fetch=Fetcher(p['allowed_hosts'],root/'.cache'/p['id'],max_requests=p.get('max_requests',100))
            adapter_config={**p,'recheck_urls':[r['source_url'] for r in state['records'] if r['publisher_id']==p['id'] and forthcoming(r,today)]}
            try: result=ADAPTERS[p['adapter']](adapter_config,fetch,today)
            except Exception as e:
                result=Result(); result.warn(p['sources'][0],e)
            reconcile(state,p,result,now,today)
            print(f"{p['id']}: {state['sources'][p['id']]['status']}; {len(result.records)} records; {len(result.warnings)} warnings",flush=True)
        state['last_attempt_at']=now
        state['records'].sort(key=lambda r:r['id'])
        atomic_json(root/'data/state.json',state)
        atomic_json(root/'data/review.json',{pid:s for pid,s in state['sources'].items() if s.get('warnings')})
        return state
