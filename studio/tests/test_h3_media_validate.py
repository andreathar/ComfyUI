from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave

import av
import numpy as np

from h3_manifest import file_digest
from h3_media_validate import audio_identity, check, main


def video(path, arrays, fps=24, native16=False, pts_step=1):
    with av.open(str(path), 'w') as container:
        stream = container.add_stream('ffv1', rate=fps)
        stream.width, stream.height = arrays[0].shape[1], arrays[0].shape[0]
        stream.pix_fmt = 'gbrap16le' if native16 else 'bgr0'
        for i, array in enumerate(arrays):
            frame = av.VideoFrame.from_ndarray(array, format='rgba64le' if native16 else 'rgb24')
            frame.pts = i * pts_step
            frame.time_base = Fraction(1, fps)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def wav(path, samples=6000, rate=48000, channels=2, value=123, layout=None):
    raw = path.with_suffix('.raw.wav')
    with wave.open(str(raw), 'wb') as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(np.full((samples, channels), value, dtype='<i2').tobytes())
    options = ['-channel_layout', layout] if layout else []
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-c:a', 'pcm_s24le',
                    *options, str(path)], check=True)
    raw.unlink()


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg is needed to mux fixture audio')
class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        rng = np.random.default_rng(22)
        self.original = rng.integers(0, 256, size=(3, 6, 8, 3), dtype=np.uint8)
        self.working = np.concatenate([self.original, np.repeat(self.original[-1:], 2, axis=0)])
        self.guards = np.zeros((5, 6, 8), dtype=np.uint8)
        self.guards[:, 2:4, 2:6] = 255
        self.guards[:, 1, 2:6] = 128
        self.result = np.concatenate([self.original.astype(np.uint16) * 257,
                                      np.full((3, 6, 8, 1), 65535, dtype=np.uint16)], axis=3)
        self.result[:, 2:4, 2:6, :3] = 1000
        video(self.root / 'original.mkv', self.original)
        video(self.root / 'working.mkv', self.working)
        self.write_guards()
        wav(self.root / 'audio.wav')
        self.write_final()
        self.contract = {'version': 1, 'guard_padding_policy': 'repeat_last',
                         'source': {'delivery_frames': 3, 'working_frames': 5, 'width': 8, 'height': 6,
                                    'fps': 24, 'sample_rate': 48000, 'channels': 2},
                         'assets': {}}
        for role, filename in {'original': 'original.mkv', 'working': 'working.mkv', 'guard': 'guard.mkv',
                               'guard_array': 'guard.npy', 'audio': 'audio.wav', 'final': 'final.mkv'}.items():
            self.contract['assets'][role] = {'path': filename, 'sha256': file_digest(self.root / filename)}

    def write_guards(self):
        video(self.root / 'guard.mkv', np.repeat(self.guards[:, :, :, None], 3, axis=3))
        np.save(self.root / 'guard.npy', self.guards)

    def write_final(self):
        video(self.root / 'result.mkv', self.result, native16=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(self.root / 'result.mkv'),
                        '-i', str(self.root / 'audio.wav'), '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'flac', str(self.root / 'final.mkv')], check=True)

    def update(self, role):
        entry = self.contract['assets'][role]
        entry['sha256'] = file_digest(self.root / entry['path'])

    def run_check(self):
        return check(self.contract, self.root)

    def test_valid_padding_guard_audio_and_exact_copy(self):
        report = self.run_check()
        self.assertTrue(report['passed'])
        self.assertEqual(report['final']['changed_protected_pixels'], 0)
        self.assertEqual(report['final']['changed_edit_pixels'], 24)
        self.assertEqual(report['final']['feather_pixels'], 12)
        self.assertEqual(report['prepared_audio']['samples_per_channel'], 6000)

    def test_read_only_and_deterministic(self):
        before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in self.root.iterdir()}
        self.assertEqual(self.run_check(), self.run_check())
        self.assertEqual(before, {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in self.root.iterdir()})

    def test_source_only_contract(self):
        del self.contract['assets']['final']
        self.assertNotIn('final', self.run_check())

    def test_hash_mismatch(self):
        self.contract['assets']['original']['sha256'] = 'old'
        with self.assertRaisesRegex(ValueError, 'content hash mismatch'):
            self.run_check()

    def test_changed_original_pixels(self):
        self.working[0, 0, 0, 0] ^= 1
        video(self.root / 'working.mkv', self.working)
        self.update('working')
        with self.assertRaisesRegex(ValueError, 'differs from original'):
            self.run_check()

    def test_wrong_padding_pixels(self):
        self.working[-1, 0, 0, 0] ^= 1
        video(self.root / 'working.mkv', self.working)
        self.update('working')
        with self.assertRaisesRegex(ValueError, 'padding does not repeat'):
            self.run_check()

    def test_frame_count(self):
        video(self.root / 'working.mkv', self.working[:-1])
        self.update('working')
        with self.assertRaisesRegex(ValueError, 'decoded 4 frames'):
            self.run_check()

    def test_frame_timeline(self):
        video(self.root / 'original.mkv', self.original, pts_step=2)
        self.update('original')
        with self.assertRaisesRegex(ValueError, 'off the zero-based frame timeline'):
            self.run_check()

    def test_rate_mismatch(self):
        video(self.root / 'original.mkv', self.original, fps=25)
        self.update('original')
        with self.assertRaisesRegex(ValueError, 'video rate differs'):
            self.run_check()

    def test_guard_array_alignment(self):
        self.guards[0, 0, 0] = 255
        np.save(self.root / 'guard.npy', self.guards)
        self.update('guard_array')
        with self.assertRaisesRegex(ValueError, 'guard video differs'):
            self.run_check()

    def test_guard_shape(self):
        np.save(self.root / 'guard.npy', self.guards[:-1])
        self.update('guard_array')
        with self.assertRaisesRegex(ValueError, 'prepared guard array must'):
            self.run_check()

    def test_guard_padding(self):
        self.guards[-1, 0, 0] = 255
        self.write_guards()
        self.update('guard')
        self.update('guard_array')
        with self.assertRaisesRegex(ValueError, 'guard padding does not repeat'):
            self.run_check()

    def test_tracked_padding_drift_is_explicit_not_silently_equal(self):
        self.guards[-1, 0, 0] = 255
        self.write_guards()
        self.update('guard')
        self.update('guard_array')
        self.contract['guard_padding_policy'] = 'tracked'
        report = self.run_check()
        self.assertTrue(report['passed'])
        self.assertFalse(report['guard_padding_exact'])
        self.assertEqual(report['guard_padding_changed_pixels_by_frame'], [0, 1])
        self.assertTrue(report['warnings'])

    def test_guard_archive_rejected_cleanly(self):
        path = self.root / 'guard.npz'
        np.savez(path, guard=self.guards)
        self.contract['assets']['guard_array'] = {'path': 'guard.npz', 'sha256': file_digest(path)}
        with self.assertRaisesRegex(ValueError, 'not an archive'):
            self.run_check()

    def test_extra_final_frames_are_not_hidden_by_delivery_trim(self):
        self.result = np.concatenate([self.result, self.result[-1:]])
        self.write_final()
        self.update('final')
        with self.assertRaisesRegex(ValueError, 'decoded 4 frames, expected 3'):
            self.run_check()

    def test_final_shape_mismatch(self):
        self.result = self.result[:, :4]
        self.write_final()
        self.update('final')
        with self.assertRaisesRegex(ValueError, 'final shape/count differs'):
            self.run_check()

    def test_native8_final_rejected(self):
        video(self.root / 'result.mkv', self.original)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(self.root / 'result.mkv'),
                        '-i', str(self.root / 'audio.wav'), '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'flac', str(self.root / 'final.mkv')], check=True)
        self.update('final')
        with self.assertRaisesRegex(ValueError, 'native RGB16'):
            self.run_check()

    def test_all_protected_with_no_edit_region(self):
        self.guards[:] = 0
        self.write_guards()
        self.update('guard')
        self.update('guard_array')
        self.result[:, :, :, :3] = self.original.astype(np.uint16) * 257
        self.write_final()
        self.update('final')
        self.assertEqual(self.run_check()['final']['changed_edit_pixels'], 0)

    def test_prepared_audio_sample_count(self):
        wav(self.root / 'audio.wav', samples=5999)
        self.update('audio')
        with self.assertRaisesRegex(ValueError, 'sample count differs'):
            self.run_check()

    def test_audio_channel_rate(self):
        wav(self.root / 'audio.wav', channels=1)
        self.update('audio')
        with self.assertRaisesRegex(ValueError, 'sample rate/channels disagree'):
            self.run_check()

    def test_final_audio_mismatch(self):
        wav(self.root / 'audio.wav', value=333)
        self.write_final()
        self.update('final')
        wav(self.root / 'audio.wav')
        self.update('audio')
        with self.assertRaisesRegex(ValueError, 'final audio differs'):
            self.run_check()

    def test_exact_16bit_protected_pixel_error(self):
        self.result[0, 0, 0, 0] += 1
        self.write_final()
        self.update('final')
        with self.assertRaisesRegex(ValueError, 'changed 1 protected pixels; max native16 channel error 1'):
            self.run_check()

    def test_transparent_final_rejected(self):
        self.result[:, :, :, 3] = 0
        self.write_final()
        self.update('final')
        with self.assertRaisesRegex(ValueError, 'final alpha must be opaque'):
            self.run_check()

    def test_native16_source_padding_low_bit_error(self):
        original = self.result.copy()
        working = np.concatenate([original, np.repeat(original[-1:], 2, axis=0)])
        working[-1, 0, 0, 0] += 1
        video(self.root / 'original.mkv', original, native16=True)
        video(self.root / 'working.mkv', working, native16=True)
        self.update('original')
        self.update('working')
        with self.assertRaisesRegex(ValueError, 'padding does not repeat'):
            self.run_check()

    def test_native16_source_exact_copy_preserves_low_bits(self):
        self.result[0, 0, 0, 0] += 1
        original = self.result.copy()
        working = np.concatenate([original, np.repeat(original[-1:], 2, axis=0)])
        video(self.root / 'original.mkv', original, native16=True)
        video(self.root / 'working.mkv', working, native16=True)
        self.write_final()
        for role in ('original', 'working', 'final'):
            self.update(role)
        self.assertEqual(self.run_check()['final']['changed_protected_pixels'], 0)
        self.result[0, 0, 0, 0] -= 1
        self.write_final()
        self.update('final')
        with self.assertRaisesRegex(ValueError, 'changed 1 protected pixels'):
            self.run_check()

    def test_true_audio_start_delay_rejected(self):
        path = self.root / 'delayed.mkv'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(self.root / 'result.mkv'),
                        '-itsoffset', '0.001', '-i', str(self.root / 'audio.wav'),
                        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'flac', str(path)], check=True)
        self.contract['assets']['final'] = {'path': 'delayed.mkv', 'sha256': file_digest(path)}
        with self.assertRaisesRegex(ValueError, 'off the zero-based sample timeline'):
            self.run_check()

    def test_multichannel_layout_identities_differ(self):
        a, b = self.root / 'back.wav', self.root / 'side.wav'
        wav(a, channels=6, layout='5.1')
        wav(b, channels=6, layout='5.1(side)')
        first, second = audio_identity(a, 48000, 6), audio_identity(b, 48000, 6)
        self.assertEqual(first['pcm32_sha256'], second['pcm32_sha256'])
        self.assertNotEqual(first['channel_names'], second['channel_names'])

    def test_no_protected_pixels(self):
        self.guards[:] = 255
        self.write_guards()
        self.update('guard')
        self.update('guard_array')
        with self.assertRaisesRegex(ValueError, 'vacuous'):
            self.run_check()

    def test_audio_normalization_matches_pcm_and_flac(self):
        self.assertEqual(audio_identity(self.root / 'audio.wav', 48000, 2),
                         audio_identity(self.root / 'final.mkv', 48000, 2))

    def test_invalid_contract_cli(self):
        path = self.root / 'bad.json'
        path.write_text('{}')
        self.assertEqual(main([str(path), '--root', str(self.root)]), 1)


if __name__ == '__main__':
    unittest.main()
