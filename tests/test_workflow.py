import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from bohan.media import doctor
from bohan.pipeline import run
from bohan.batch import run_batch
from bohan.contracts import (Transcript, TranscriptSegment, VisionAnalysis, Observation,
                             validate_transcript, validate_vision)
from bohan.prompts import load_product


class ContractsTest(unittest.TestCase):
    def test_invalid_timestamps(self):
        for start, end in [(-1, 1), (2, 1), (0, 4), (0, float('nan')), (False, 1)]:
            with self.assertRaises(ValueError):
                validate_transcript(Transcript('de', [TranscriptSegment(start, end, 'Hallo')]), 2)

    def test_evidence_must_exist_in_frame_index(self):
        with self.assertRaises(ValueError):
            validate_vision(VisionAnalysis([Observation(0, 1, 'visible', ['other.jpg'])]),
                            2, [{'path': 'frames/000000.jpg'}])

    def test_product_requires_fact_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'product.json'
            path.write_text(json.dumps({'name': 'item', 'image_ref': '@image1',
                                        'facts': [{'claim': 'unverified'}]}))
            with self.assertRaises(ValueError):
                load_product(path)

    def test_batch_rejects_path_traversal_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'jobs.json'
            for ids in [['../bad'], ['same', 'same']]:
                path.write_text(json.dumps([{'id': i, 'source': 'x'} for i in ids]))
                with self.assertRaises(ValueError):
                    run_batch(path, root / 'out')
                self.assertFalse((root / 'out').exists())


@unittest.skipUnless(all(doctor().values()), 'FFmpeg and ffprobe required')
class IntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.video = cls.root / 'input.mp4'
        cls.silent = cls.root / 'silent.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=c=blue:s=160x120:r=10', '-f', 'lavfi', '-i',
                        'sine=frequency=440:sample_rate=16000', '-t', '2',
                        '-c:v', 'mpeg4', '-c:a', 'aac', str(cls.video)], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(cls.video), '-an',
                        '-c:v', 'copy', str(cls.silent)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_real_extraction_and_pending_stages(self):
        out = self.root / 'real'
        result = run(self.video, out, interval=1)
        self.assertEqual(result['stages'], {'extraction': 'completed', 'transcription': 'pending',
                                          'vision': 'pending', 'prompt': 'blocked_missing_product'})
        frames = json.loads((out / 'frames.json').read_text())
        self.assertEqual([f['timestamp'] for f in frames], [0, 1])
        self.assertTrue(all((out / f['path']).stat().st_size for f in frames))
        self.assertGreater((out / 'audio.wav').stat().st_size, 44)
        with self.assertRaises(FileExistsError):
            run(self.video, out)

    def test_silent_video(self):
        out = self.root / 'silent'
        result = run(self.silent, out)
        self.assertEqual(result['stages']['transcription'], 'skipped')
        self.assertFalse((out / 'audio.wav').exists())

    def test_failure_manifest(self):
        out = self.root / 'failed'
        with self.assertRaises(ValueError):
            run(self.video, out, interval=0)
        value = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(value['status'], 'failed')
        self.assertEqual(value['error']['stage'], 'extraction')

    def test_adapters_and_product_draft(self):
        class ASR:
            def transcribe(self, audio, language):
                return Transcript(language, [TranscriptSegment(0, 1, 'Test fixture')])
        class Vision:
            def analyze(self, frames, job_dir):
                return VisionAnalysis([Observation(0, 1, 'Synthetic blue frame', [frames[0]['path']])])
        product = load_product(Path(__file__).resolve().parents[1] / 'examples/product.json')
        out = self.root / 'adapters'
        result = run(self.video, out, product=product, transcriber=ASR(),
                     vision_analyzer=Vision(), language='de')
        self.assertEqual(result['stages']['transcription'], 'needs_review')
        self.assertEqual(result['stages']['vision'], 'needs_review')
        self.assertEqual(result['stages']['prompt'], 'draft_needs_review')
        self.assertIn('Test fixture', (out / 'transcript.json').read_text())

    def test_batch_continues_after_failure(self):
        path = self.root / 'batch-input.json'
        path.write_text(json.dumps([{'id': 'bad', 'source': 'missing.mp4'},
                                    {'id': 'good', 'source': 'silent.mp4'}]))
        results = run_batch(path, self.root / 'batch')
        self.assertEqual([j['status'] for j in results], ['failed', 'needs_review'])
        self.assertEqual(json.loads((self.root / 'batch/batch.json').read_text()), results)


if __name__ == '__main__':
    unittest.main()
