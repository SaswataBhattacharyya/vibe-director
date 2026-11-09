"""Read-only, revision-bound HyperFrames preview. No Studio server or raw HTML input."""
from . import editor_layers, editor_composition, vibe_editor, vibe_editor_render

# Static runtime files only; never expose the CLI's filesystem, AI or export routes.
def runtime_file(name):
    paths = {
        'gsap.js': vibe_editor_render.RUNTIME / 'dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js',
        'runtime.js': vibe_editor_render.RUNTIME / 'dist/hyperframe.runtime.iife.js',
        'shaders.js': vibe_editor_render.SHADER,
    }
    path = paths.get(name)
    if path is None or not path.is_file():
        raise ValueError('Editor preview runtime file unavailable.')
    return path


def prepare(root, project_id, body):
    if not isinstance(body, dict) or set(body) != {'revision', 'plan'}:
        raise ValueError('Preview requires exactly revision and plan.')
    with vibe_editor.state(root, readonly=True) as data:
        p = vibe_editor.project(data, project_id)
        if type(body['revision']) is not int or body['revision'] != p['revision']:
            raise ValueError('Stale revision. Refresh before previewing a plan.')
        plan = vibe_editor.selected_plan(root, p, body['plan'])
        # shortcut: effects and speed require CPU preprocessing; use approved render until a preview cache exists.
        if any(c['effect']['preset'] != 'none' or c['speed'] != {'start': 1, 'end': 1} for c in plan['clips']):
            raise ValueError('Filters and speed ramps require the approved CPU render. Live preview supports unfiltered clips at 1× speed.')
        sources = {c['asset_id']: f"/api/media/{p['workspace_id']}/assets/{c['asset_id']}/content"
                   for c in editor_layers.media_ranges(plan)}
        for name in ('gsap.js', 'runtime.js', 'shaders.js'):
            runtime_file(name)
        document, duration = editor_composition.document(plan, sources,
            gsap='/api/editor/runtime/gsap.js', shaders='/api/editor/runtime/shaders.js')
        document = document.replace('</body>', BRIDGE + '</body>')
        return {'revision': p['revision'], 'duration': duration, 'document': document}


BRIDGE = '''<script src="/api/editor/runtime/runtime.js"></script><script>
const main=document.getElementById('main');
function scale(){const s=Math.min(innerWidth/Number(main.dataset.width),innerHeight/Number(main.dataset.height));
main.style.width=main.dataset.width+'px';main.style.height=main.dataset.height+'px';main.style.transformOrigin='top left';
main.style.transform='translate('+((innerWidth-Number(main.dataset.width)*s)/2)+'px,'+((innerHeight-Number(main.dataset.height)*s)/2)+'px) scale('+s+')';}
scale();addEventListener('resize',scale);
addEventListener('message',event=>{if(event.source!==parent||!window.__playerReady)return;
const d=event.data;if(d?.type!=='vibe-editor-transport')return;
if(d.action==='play')window.__player.play();else if(d.action==='pause')window.__player.pause();
else if(d.action==='seek'&&Number.isFinite(d.time))window.__player.seek(Math.max(0,Math.min(d.time,Number(main.dataset.duration))));});
const began=performance.now();const timer=setInterval(()=>{
if(window.__hfStartupError||(!window.__playerReady&&performance.now()-began>15000)){
parent.postMessage({type:'vibe-editor-preview',error:'HyperFrames preview could not initialize.'},'*');clearInterval(timer);return;}
if(window.__playerReady)parent.postMessage({type:'vibe-editor-preview',time:window.__player.getTime(),playing:window.__player.isPlaying()},'*');
},100);
</script>'''
