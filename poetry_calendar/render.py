import html
import json
import os
from datetime import date
from pathlib import Path
from .model import forthcoming, sort_key
from .pipeline import load_registry, load_state, effective_records

def esc(value): return html.escape(str(value),quote=True)

def render(root,today):
    state=load_state(root); registry=load_registry(root); pubs={p['id']:p for p in registry}
    overrides=json.loads((root/'config/overrides.json').read_text(encoding='utf-8'))
    records=effective_records(state,overrides,today)
    records=sorted((r for r in records if forthcoming(r,today)),key=sort_key)
    rows=[]; heading=None
    for r in records:
        d=r['date']; p=pubs[r['publisher_id']]
        group='Dates to be confirmed' if d['precision'] in ('unknown','year') else (date.fromisoformat(d['start']).strftime('%B %Y') if d['precision']!='season' else d['label'].replace(', provisional',''))
        if group!=heading:
            rows.append(f'<li class="month"><h2>{esc(group)}</h2></li>'); heading=group
        verified=r.get('last_verified_at','')[:10]
        source=state['sources'].get(p['id'],{})
        stale=(today-date.fromisoformat(verified)).days>8 if verified else True
        notes=[]
        if stale: notes.append('Source check overdue')
        if r.get('missing_checks'): notes.append('Awaiting reconfirmation')
        if source.get('status') not in ('ok',): notes.append('Publisher coverage incomplete')
        subtitle=f'<span class="subtitle">{esc(r["subtitle"])}</span>' if r.get('subtitle') else ''
        contributors=' · '.join(x['name']+(f" ({x['role']})" if x['role']!='author' else '') for x in r['contributors'])
        rows.append(f'''<li class="book" data-publisher="{esc(p['id'])}" data-search="{esc((r['title']+' '+contributors+' '+p['name']).lower())}">
          <div class="book-date">{esc(d['label'])}</div>
          <div class="book-main"><h3><a href="{esc(r['source_url'])}">{esc(r['title'])}<span aria-hidden="true" class="arrow"> ↗</span></a></h3>{subtitle}<p class="contributors">{esc(contributors)}</p></div>
          <div class="book-source"><span>{esc(p['name'])}</span><small>Checked {esc(verified or 'not yet')}</small>{''.join(f'<small class="warning">{esc(n)}</small>' for n in notes)}</div>
        </li>''')
    health=[]; checked=0
    labels={'ok':'Checked','partial':'Partial coverage','failed':'Check failed','permission_review':'Access review needed','robots_disallowed':'Collector disallowed','access_blocked':'Access blocked','not_checked':'Not checked'}
    for p in registry:
        s=state['sources'].get(p['id'],{}); status=s.get('status','not_checked')
        if status=='ok': checked+=1
        last=s.get('last_success_at') or s.get('last_data_at')
        visible=sum(r['publisher_id']==p['id'] for r in records)
        health.append(f'''<tr><th scope="row">{esc(p['name'])}</th><td><span class="status {esc(status)}">{esc(labels.get(status,status))}</span><small>{visible} forthcoming · {('last data '+esc(last[:10])) if last else 'no verified collection'}</small></td><td>{esc(p['coverage'])}</td></tr>''')
    last_attempt=(state.get('last_attempt_at') or 'Not yet run')[:10]
    options=''.join(f'<option value="{esc(p["id"])}">{esc(p["name"])}</option>' for p in sorted(registry,key=lambda p:p['name']))
    template=(root/'site/template.html').read_text(encoding='utf-8')
    replacements={'{{BOOKS}}':''.join(rows) or '<li class="empty">No verified forthcoming titles are currently available. See coverage below.</li>',
        '{{HEALTH}}':''.join(health),'{{OPTIONS}}':options,'{{COUNT}}':str(len(records)),
        '{{PUBLISHERS}}':str(len(registry)),'{{CHECKED}}':str(checked),'{{ATTEMPT}}':esc(last_attempt),
        '{{AS_OF}}':today.isoformat(),
        '{{AUTOMATION}}':('Built by GitHub Actions. Collection is scheduled for Mondays at 08:17 UK time; the calendar is rebuilt daily. Check the timestamps above for missed updates.' if os.getenv('GITHUB_ACTIONS')=='true' else 'Weekly collection and daily rebuilding are provided in the project workflow. <strong>This locally generated preview is not itself an unattended service.</strong>')}
    for token,value in replacements.items(): template=template.replace(token,value)
    dist=root/'dist'; dist.mkdir(exist_ok=True)
    temp=dist/'index.html.tmp'; temp.write_text(template,encoding='utf-8'); os.replace(temp,dist/'index.html')
    for name in ('style.css','app.js'): (dist/name).write_text((root/'site'/name).read_text(encoding='utf-8'),encoding='utf-8')
    (dist/'robots.txt').write_text('User-agent: *\nAllow: /\n',encoding='utf-8')
    print(f'Built {len(records)} forthcoming titles from {len(set(r["publisher_id"] for r in records))} publishers; {checked}/{len(registry)} source scans complete.')
