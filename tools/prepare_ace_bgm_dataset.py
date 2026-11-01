#!/usr/bin/env python3
"""Append source-linked ACE-Step training triplets; never starts training."""
import csv, fcntl, hashlib, importlib.util, json, math, re, subprocess, sys, traceback
from pathlib import Path
from urllib.parse import unquote, urlsplit, urljoin
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'local_data/ace_step'
OUT=BASE/'datasets/ACE_STEP_READY'
CACHE=OUT/'_download_cache'
STATE=BASE/'datasets/download_preparation'
for p in (OUT,CACHE,STATE): p.mkdir(parents=True,exist_ok=True)
lock=(STATE/'runner.lock').open('w')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
spec=importlib.util.spec_from_file_location('builder',BASE/'ACE_STEP_BGM_Builder/build_ace_step_dataset.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
b.MAX_BYTES=2*1024**3
session=b.requests.Session(); session.headers['User-Agent']='VibeDirectorDataset/1.0 (personal music dataset preparation)'
manifest=OUT/'SOURCE_MANIFEST.csv'
records=b.load_manifest(manifest)
errors=[]; completed=[]
baseline={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*/*') if p.suffix in ('.mp3','.txt') and p.is_file()}
(STATE/'preservation_baseline.json').write_text(json.dumps(baseline,indent=2))
def save():
    tmp=manifest.with_suffix('.tmp.csv'); b.save_manifest(tmp,records); tmp.replace(manifest)
    (STATE/'progress.json').write_text(json.dumps({'sources_done':completed,'failures':errors,'training_clips':len(records)},indent=2))
def plain(x): return b.BeautifulSoup(x or '', 'html.parser').get_text(' ',strip=True)
def resolve(src):
    page=src.get('preferred_download_page') or src.get('url','')
    if 'commons.wikimedia.org' in page:
        filename=src.get('filename') or unquote(page.split('File:',1)[1])
        doc=b.request_get(session,'https://commons.wikimedia.org/w/api.php',params={'action':'query','format':'json','prop':'imageinfo','iiprop':'url|extmetadata','titles':'File:'+filename,'redirects':1}).json()
        info=next((p['imageinfo'][0] for p in doc.get('query',{}).get('pages',{}).values() if p.get('imageinfo')),None)
        if not info: raise ValueError('Commons file has no downloadable original')
        meta=info.get('extmetadata',{}); get=lambda k:plain(meta.get(k,{}).get('value',''))
        lic=get('LicenseShortName'); normalized=lic.lower()
        if not any(x in normalized for x in ('cc0','cc-zero','public domain','pdm','cc by','cc-by')) or any(x in normalized for x in ('-nc','-nd','noncommercial','no derivatives')):
            raise ValueError('Unsupported or unverified recording license: '+lic)
        return [{'url':info['url'],'name':filename,'license':lic,'license_evidence_url':info.get('descriptionurl',page),'license_evidence':get('UsageTerms'),'artist':get('Artist'),'attribution':get('Attribution') or get('Credit') or get('Artist')}]
    if 'opengameart.org' in page:
        return b.oga_sources(session,dict(src,url=page))
    if 'scottbuckley.com.au/library/' in page:
        html=b.request_get(session,page).text; soup=b.BeautifulSoup(html,'html.parser')
        license_links=[a['href'] for a in soup.select('a[href]') if 'creativecommons.org/licenses/by/4.0' in a['href']]
        if not license_links: raise ValueError('Recording page does not confirm CC BY 4.0')
        links=[]
        for a in soup.select('a[href]'):
            url=urljoin(page,a['href']); name=unquote(Path(urlsplit(url).path).name)
            if Path(name).suffix.lower() in b.AUDIO:
                links.append((url,name,plain(a.get_text(' ',strip=True))))
        # Some WordPress players expose the recording through an audio/source element.
        for a in soup.select('audio[src], source[src]'):
            url=urljoin(page,a['src']); name=unquote(Path(urlsplit(url).path).name)
            if Path(name).suffix.lower() in b.AUDIO: links.append((url,name,''))
        sid=src.get('source_id','')
        if sid=='action_red': links=[x for x in links if re.search(r'no[ _-]*vocals?',x[1]+' '+x[2],re.I)]
        elif sid=='peace_sleep': links=[x for x in links if re.search(r'piano[ _-]*only',x[1]+' '+x[2],re.I)]
        else: links=[x for x in links if not re.search(r'no[ _-]*vocals?|piano[ _-]*only',x[1]+' '+x[2],re.I)] or links
        unique=list(dict.fromkeys(links))
        if not unique: raise ValueError('Required downloadable recording/mix not found')
        url,name,_=unique[0]
        return [{'url':url,'name':name,'license':'CC BY 4.0','license_evidence_url':page,'license_evidence':license_links[0],'artist':'Scott Buckley','attribution':src['title']+' by Scott Buckley — '+page+' — CC BY 4.0'}]
    raise ValueError('No supported verified original download for '+page)
def gaps(total, covered):
    cursor=0.; result=[]
    for start,end in sorted(covered):
        start=max(0.,start); end=min(total,end)
        if start-cursor>=12: result.append((cursor,start))
        cursor=max(cursor,end)
    if total-cursor>=12: result.append((cursor,total))
    return result
def process(src,item,master,page):
    total=b.duration(master)
    # Match cache originals even when Commons query strings changed.
    identity=lambda u:unquote(urlsplit(u).path) + ('#'+unquote(urlsplit(u).fragment) if urlsplit(u).fragment else '')
    matching=[r for r in records if r.get('style')==src['style'] and identity(r.get('source_file',''))==identity(item['url'])]
    covered=[(float(r.get('clip_start') or 0),float(r.get('clip_start') or 0)+float(r.get('clip_seconds') or 0)) for r in matching]
    tags=src.get('suggested_prompt_tags') or src.get('tags','')
    for begin,end in gaps(total,covered):
        count=math.ceil((end-begin)/235); length=(end-begin)/count
        for n in range(count):
            start=begin+n*length; seconds=min(length,end-start)
            stem='song_'+b.digest(src['style']+'|'+identity(item['url'])+'|'+f'{start:.3f}|{seconds:.3f}',16)
            folder=OUT/src['style']; folder.mkdir(exist_ok=True)
            audio=folder/(stem+'.mp3'); prompt=folder/(stem+'_prompt.txt'); lyrics=folder/(stem+'_lyrics.txt')
            if any(p.exists() for p in (audio,prompt,lyrics)):
                print('  Preserving existing triplet/partial:',stem,flush=True); continue
            print(f'  Preparing {src["style"]}/{stem}: {start:.1f}–{start+seconds:.1f}s',flush=True)
            b.converted_mp3(master,audio,start=start,max_seconds=seconds)
            prompt.write_text(tags+'\n',encoding='utf-8')
            lyrics.write_text(src.get('lyrics_file_content') or '[instrumental]\n',encoding='utf-8')
            records.append(dict(track_id=b.digest(stem,16),style=src['style'],stem=stem,title=src['title'],artist=item.get('artist') or src.get('artist') or src.get('author',''),source_page=page,source_file=item['url'],license=item.get('license',''),license_evidence_url=item.get('license_evidence_url',page),license_evidence=item.get('license_evidence',''),attribution=item.get('attribution',''),audio_seconds=total,clip_start=round(start,3),clip_seconds=round(b.duration(audio),3),tags=tags,sha256_mp3=hashlib.sha256(audio.read_bytes()).hexdigest(),notes='Source-description tags; not an audio listening or vocal-detection assessment. '+src.get('music_and_quality_notes','')))
            save()
def get_master(item):
    identity=lambda u:unquote(urlsplit(u).path) + ('#'+unquote(urlsplit(u).fragment) if urlsplit(u).fragment else '')
    for r in records:
        old=r.get('source_file','')
        if identity(old)==identity(item['url']):
            cached=CACHE/(b.digest(old)+Path(item['name']).suffix.lower())
            if cached.exists() and cached.stat().st_size>1024: return cached
    print('  Downloading complete original:',item['url'],flush=True)
    return b.download(session,item,CACHE,max_mb=2048)
original=json.loads((BASE/'ACE_STEP_BGM_Builder/catalog.json').read_text())['sources']
additional=json.loads((BASE/'ACE_STEP_BGM_ADDITIONS_FOR_CODEX/ADDITIONAL_BGM_SOURCES.json').read_text())['sources']
print(f'Preparing {len(original)} original + {len(additional)} additional source pages. Output: {OUT}',flush=True)
for i,src in enumerate(original+additional,1):
    page=src.get('preferred_download_page') or src.get('url','')
    label=src.get('source_id') or src['title']
    print(f'\n[{i}/{len(original)+len(additional)}] {src["style"]}: {label}\n  {page}',flush=True)
    try:
        items=resolve(src)
        for item in items:
            master=get_master(item)
            if master.suffix.lower()=='.zip':
                for name,data in b.best_audio_from_zip(master,max_tracks=10000):
                    path=CACHE/(b.digest(item['url']+'#'+name)+Path(name).suffix.lower())
                    if not path.exists(): path.write_bytes(data)
                    process(src,dict(item,url=item['url']+'#'+name),path,page)
            else: process(src,item,master,page)
        completed.append(label)
    except Exception as exc:
        print('  FAILED:',str(exc),flush=True); errors.append({'source':label,'page':page,'reason':str(exc)})
    save()
changed=[p for p,h in baseline.items() if not (OUT/p).exists() or hashlib.sha256((OUT/p).read_bytes()).hexdigest()!=h]
validation=[]
for folder in sorted(OUT.iterdir()):
    if folder.is_dir() and not folder.name.startswith('_') and list(folder.glob('*.mp3')):
        result=subprocess.run([sys.executable,str(BASE/'ACE_STEP_BGM_Builder/validate_ace_step_dataset.py'),str(folder)],text=True,capture_output=True)
        print(result.stdout,flush=True)
        validation.append({'style':folder.name,'passed':result.returncode==0,'details':result.stdout+result.stderr})
report={'validation':validation,'completed_source_pages':len(completed),'pending_sources':errors,'training_clips':len(records),'existing_files_changed':changed,'output':str(OUT),'training_started':False}
(STATE/'REPORT.json').write_text(json.dumps(report,indent=2))
print('\nDONE\n'+json.dumps(report,indent=2),flush=True)
if changed: sys.exit('ERROR: existing-file preservation check failed')
