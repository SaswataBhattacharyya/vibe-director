#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
for name,record in manifest.items():
 p=root/name
 assert p.exists(),name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],name
for p in (root/'skills').glob('*/SKILL.md'):
 t=p.read_text();assert t.startswith('---\n') and '\nname:' in t and '\ndescription:' in t,p
for p in (root/'contracts').glob('*.json'):json.loads(p.read_text())
print('OK',len(manifest),'files;',len(list((root/'skills').glob('*/SKILL.md'))),'skills;',len(list((root/'contracts').glob('*.json'))),'JSON contracts')
