"""Explicit CPU canvas preparation; originals always remain separate assets."""
import subprocess
import uuid

from . import media_library, projects
from .storage_paths import generated_root

# Compatibility dimensions from the installed FluxKontextImageScale node.
KONTEXT_BUCKETS = [(672,1568),(688,1504),(720,1456),(752,1392),(800,1328),
    (832,1248),(880,1184),(944,1104),(1024,1024),(1104,944),(1184,880),
    (1248,832),(1328,800),(1392,752),(1456,720),(1504,688),(1568,672)]


def bucket(width, height):
    return min(KONTEXT_BUCKETS, key=lambda size: (abs(width/height-size[0]/size[1]), *size))


def normalize(root, owner, source):
    from .frame_interpolation import dimensions
    path = media_library.asset_path(root, owner, source['asset_id'])[0]
    width, height = bucket(source['width'], source['height'])
    relative = f'frame-pipeline/canvas-{uuid.uuid4().hex}.png'
    target = generated_root(root, owner) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.part.png')
    try:
        # Deliberate center crop matches Kontext's aspect-bucket policy.
        subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(path),
            '-vf',f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}',
            '-frames:v','1',str(temporary)], check=True, capture_output=True, timeout=60)
        if dimensions(temporary) != (width,height) or projects.digest(path) != source['sha256']:
            raise ValueError('Canvas preparation failed or the original changed.')
        temporary.replace(target)
        return media_library.register_generated_image(root, owner, relative,
            {'frame_canvas': {'source': source, 'method': 'lanczos_center_crop', 'dimensions': [width,height]}})['asset_id']
    finally:
        temporary.unlink(missing_ok=True)
