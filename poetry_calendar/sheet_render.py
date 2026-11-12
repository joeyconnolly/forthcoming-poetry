"""Render only the allowlisted, approved bibliographic projection."""
import html
import os
from datetime import date
from .sheets import FORMATS, publisher_id

def esc(value):return html.escape(str(value),quote=True)

def render_sheet(root,today,records):
    rows=[];heading=None
    months = {}
    for r in records:
        d=r['date']
        group='Dates to be confirmed' if d['precision'] in ('unknown','year') else (d['label'] if d['precision']=='season' else date.fromisoformat(d['start']).strftime('%B %Y'))
        month = d['start'][:7] if d['precision'] in ('day', 'month') else 'unspecified'
        months[month] = 'No specific month' if month == 'unspecified' else group
        if group!=heading:rows.append(f'<li class="month"><h2>{esc(group)}</h2></li>');heading=group
        title=esc(r['title'])
        if r['url']:title=f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{title}</a>'
        credits = r['author']
        if r['translator']:
            credits += (' · ' if credits else '') + f'Translated by {r["translator"]}'
        date_label = esc(d['label'])
        if d['precision'] in ('day', 'month'):
            pub_date = date.fromisoformat(d['start'])
            if d['precision'] == 'day':
                date_label = f'<time datetime="{pub_date.isoformat()}">{pub_date.day} {pub_date:%b}</time>'
            else:
                date_label = f'<time datetime="{pub_date:%Y-%m}">{pub_date:%b %Y}</time>'
        elif d['precision'] == 'season':
            date_label = esc(d['label'].removesuffix(', provisional'))
        rows.append(f'''<li class="book" data-publisher="{publisher_id(r['publisher'])}" data-month="{month}" data-format="{esc(r['format'])}">
          <div class="book-date">{date_label}</div>
          <div class="book-main"><h3>{title}</h3><p class="contributors">{esc(credits)}</p></div>
          <details class="book-source"><summary>{esc(r['publisher'])}</summary><small>{esc(r['format']) if r['format'] else 'Poetry'}</small></details>
        </li>''')
    publishers=sorted({r['publisher'] for r in records},key=str.casefold)
    options=''.join(f'<option value="{publisher_id(p)}">{esc(p)}</option>' for p in publishers)
    month_options = ''.join(f'<option value="{month}">{esc(label)}</option>' for month, label in sorted(months.items()))
    format_options = ''.join(f'<option value="{esc(label)}">{esc(label)}</option>' for label in FORMATS.values())
    template=(root/'site/sheet-template.html').read_text(encoding='utf-8')
    replacements={'{{BOOKS}}':''.join(rows) or '<li class="empty">No titles are currently listed.</li>',
        '{{MONTH_OPTIONS}}':month_options,'{{FORMAT_OPTIONS}}':format_options,'{{OPTIONS}}':options,'{{COUNT}}':str(len(records)),'{{VISIBLE_PUBLISHERS}}':str(len(publishers))}
    for token,value in replacements.items():template=template.replace(token,value)
    # A separate publication directory prevents legacy JSON/cache files entering artifacts.
    output=root/'public-site';output.mkdir(exist_ok=True)
    temp=output/'index.html.tmp';temp.write_text(template,encoding='utf-8');os.replace(temp,output/'index.html')
    for filename, asset in (('style.css', 'sheet-style.css'), ('app.js', 'app.js')):
        (output / filename).write_text((root / 'site' / asset).read_text(encoding='utf-8'), encoding='utf-8')
    (output/'robots.txt').write_text('User-agent: *\nAllow: /\n',encoding='utf-8')
