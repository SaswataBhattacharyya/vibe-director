import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.services import agent_skills as skills, director_skills
from story_builder.services.storage_paths import project_root


class AgentSkillsTests(unittest.TestCase):
    def test_model_prompting_skills_are_discoverable_and_routed(self):
        refs={row['ref'] for row in skills.discover(self.root, 'tool-library')['skills'] if row['available']}
        for name in ('prompt-craft', 'z-image-prompting', 'qwen-image-edit-prompting', 'flux-kontext-prompting', 'frame-interpolation', 'kdenlive-clip-continuity-and-stitching'):
            self.assertIn('application/vibe/'+name, refs)
        z=director_skills.director_skill_context(image_workflow='z_image_turbo')
        q=director_skills.director_skill_context(image_workflow='qwen_image_multi_angle_2511')
        self.assertIn('z-image-prompting/SKILL.md',z)
        self.assertNotIn('qwen-image-edit-prompting/SKILL.md',z)
        self.assertIn('qwen-image-edit-prompting/SKILL.md',q)
        self.assertIn('Use discuss while awaiting these choices',q)
        for context in (z, q, director_skills.director_skill_context(video=True)):
            self.assertIn('prompt-craft/references/visual-glossary.md', context)
            self.assertIn('Speed ramp', context)
            self.assertIn('Chiaroscuro', context)
        self.assertNotIn('visual-glossary.md', director_skills.director_skill_context())

    def test_blueprint_craft_skills_are_registered_and_load_the_shared_contract(self):
        rows = skills.discover(self.root, 'tool-library')['skills']
        craft = [row for row in rows if row['provider'] == 'filmmaking']
        self.assertEqual(len(craft), 13)
        self.assertTrue(all(row['available'] and row['scope'] == 'application' for row in craft))
        loaded = skills.selected_context(self.root, 'tool-library', [craft[0]['ref']])
        self.assertEqual(loaded[-1]['ref'], 'application/filmmaking/shared-contract')
        self.assertIn('content', loaded[0])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-skills-test-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.cleanup)
        self.workspace = 'story-aaaaaaaaaaaa'

    def cleanup(self):
        self.temp.cleanup()
        self.assertFalse(self.root.exists())

    def skill(self, folder, text='---\nname: same\ndescription: Useful craft\nversion: 2\n---\nGuide'):
        path = folder / 'same/SKILL.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_scopes_collisions_updates_and_removal(self):
        global_root = self.root / 'global'
        first = self.skill(global_root)
        self.skill(project_root(self.root, self.workspace) / 'skills')
        with patch.dict(os.environ, {'VIBE_DIRECTOR_AGENT_SKILL_ROOTS': json.dumps({'codex': str(global_root)})}):
            rows = skills.discover(self.root, self.workspace)['skills']
            matching = [r for r in rows if r['id'] == 'same']
            self.assertEqual({r['scope'] for r in matching}, {'global', 'project'})
            self.assertEqual(len({r['ref'] for r in matching}), 2)
            self.assertTrue(all(r['available'] and r['version'] == '2' for r in matching))
            old = matching[0]['sha256']
            first.write_text('Updated')
            changed = next(r for r in skills.discover(self.root, self.workspace)['skills'] if r['scope'] == 'global')
            self.assertNotEqual(old, changed['sha256'])
            first.unlink()
            missing = next(r for r in skills.discover(self.root, self.workspace)['skills'] if r['scope'] == 'global')
            self.assertFalse(missing['available'])
            self.assertFalse(any(r['scope'] == 'project' for r in skills.discover(self.root, 'tool-library')['skills']))
            self.assertFalse(any(r['id'] == 'same' and r['scope'] == 'project' for r in skills.discover(self.root, 'story-bbbbbbbbbbbb')['skills']))

    def test_safe_bounded_context_and_references(self):
        path = self.skill(self.root)
        for relative in ('../outside', str(path)):
            with self.assertRaises(ValueError):
                skills.read_content(self.root, relative)
        (path.parent / 'escape.md').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):
            skills.read_content(self.root, 'same/escape.md')
        path.write_text('x'*24001)
        with self.assertRaises(ValueError):
            skills.read_content(self.root, 'same/SKILL.md')
        os.mkfifo(path.parent / 'pipe.md')
        with self.assertRaises(FileNotFoundError):
            skills.read_content(self.root, 'same/pipe.md')
        path.write_text('short')
        self.assertEqual(skills.read_content(self.root, 'same/SKILL.md'), 'short')

    def test_unavailable_provider_and_bounded_listing(self):
        with patch.dict(os.environ, {'VIBE_DIRECTOR_AGENT_SKILL_ROOTS': json.dumps({'codex': str(self.root / 'missing')})}):
            rows = skills.discover(self.root, 'tool-library')['skills']
            self.assertFalse(rows[-1]['available'])
            self.assertNotIn(str(self.root), json.dumps(rows))
        for index in range(5):
            self.skill(self.root / 'provider' / str(index))
        with patch.dict(os.environ, {'VIBE_DIRECTOR_AGENT_SKILL_ROOTS': json.dumps({'codex': str(self.root / 'provider')})}), \
             patch.object(skills, 'MAX_SKILLS', 4):
            listing = skills.discover(self.root, 'tool-library')
            self.assertTrue(listing['truncated'])
            self.assertLessEqual(len(listing['skills']), 4)
        with patch.dict(os.environ, {'VIBE_DIRECTOR_AGENT_SKILL_ROOTS': '{"codex":"relative"}'}):
            with self.assertRaises(ValueError):
                skills.discover(self.root, 'tool-library')

    def test_legacy_director_and_editor_context_parity(self):
        for video in (False, True):
            paths = ['vibe-director/SKILL.md']
            if video:
                paths += ['prompt-craft/SKILL.md', 'prompt-craft/references/visual-glossary.md', 'video-prompting/SKILL.md', 'video-prompting/references/minimax-h3.md', 'video-prompting/references/examples.md']
            expected = []
            for relative in paths:
                text = (director_skills._ROOT / relative).read_text(encoding='utf-8')
                digest = hashlib.sha256(text.encode()).hexdigest()[:16]
                expected.append(f'PROJECT SKILL {relative} sha256:{digest}\n{text}')
            self.assertEqual(director_skills.director_skill_context(video=video), '\n\n'.join(expected))
        root = skills.REPO / 'design/vibe-editor/skills'
        self.assertEqual(skills.read_content(root, 'vibe-editor-director/SKILL.md'), (root / 'vibe-editor-director/SKILL.md').read_text())
        self.skill(self.root, 'x'*24001)
        with patch.object(director_skills, '_ROOT', self.root):
            (self.root / 'vibe-director').mkdir()
            (self.root / 'vibe-director/SKILL.md').write_text('x'*24001)
            with self.assertRaisesRegex(ValueError, 'Project directing skill exceeds its context budget: vibe-director/SKILL.md'):
                director_skills.director_skill_context()
