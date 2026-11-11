#!/usr/bin/env python3
"""CPU-only H3 source/padding/guard/audio validation and native-lossless evaluation."""
import argparse
from fractions import Fraction
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import sys

import av
import numpy as np

from h3_manifest import file_digest


class Video:
    def __init__(self, path, count, fps, size=None, native16=False, silent_lossless=False, native_pixels=False):
        self.path, self.expected_count, self.fps = path, count, Fraction(fps)
        self.size, self.native16, self.silent_lossless = size, native16, silent_lossless
        self.native_pixels = native_pixels
        self.count = 0

    def __iter__(self):
        with av.open(str(self.path)) as container:
            if len(container.streams.video) != 1:
                raise ValueError(f'{self.path}: expected one video stream')
            stream = container.streams.video[0]
            if stream.average_rate != self.fps:
                raise ValueError(f'{self.path}: video rate differs from {self.fps}')
            if self.silent_lossless and (stream.codec_context.name != 'ffv1' or container.streams.audio):
                raise ValueError(f'{self.path}: prepared working/guard video must be silent FFV1')
            if self.native16 and (stream.codec_context.name != 'ffv1' or stream.codec_context.format.name not in
                                  {'rgba64le', 'gbrap16le', 'rgb48le', 'gbrp16le'}):
                raise ValueError(f'{self.path}: final must be native RGB16 lossless FFV1')
            previous = None
            for index, frame in enumerate(container.decode(video=0)):
                if frame.pts is None or frame.time_base is None:
                    raise ValueError(f'{self.path}: missing video timestamps')
                timestamp = frame.pts * frame.time_base
                if (index == 0 and timestamp != 0) or abs(timestamp - Fraction(index, 1) / self.fps) > frame.time_base / 2:
                    raise ValueError(f'{self.path}: video frame {index} is off the zero-based frame timeline')
                if previous is not None and timestamp <= previous:
                    raise ValueError(f'{self.path}: video timestamps are not increasing')
                previous = timestamp
                kwargs = {'width': self.size[0], 'height': self.size[1]} if self.size else {}
                self.count = index + 1
                if self.native_pixels:
                    # RGB0/BGR0's fourth byte is padding, not pixel data.
                    fmt = 'rgb24' if frame.format.name in {'rgb0', 'bgr0'} else frame.format.name
                    yield frame.format.name, frame.to_ndarray(format=fmt)
                else:
                    yield frame.to_ndarray(format='rgba64le' if self.native16 else 'rgb24', **kwargs)
            if self.count != self.expected_count:
                raise ValueError(f'{self.path}: decoded {self.count} frames, expected {self.expected_count}')


def audio_identity(path, rate, channels):
    """Hash interleaved signed PCM32 without resampling, channel remix or frame buffering."""
    digest = hashlib.sha256()
    samples = 0
    with av.open(str(path)) as container:
        if len(container.streams.audio) != 1:
            raise ValueError(f'{path}: expected one audio stream')
        stream = container.streams.audio[0]
        if stream.codec_context.name != 'flac' and not stream.codec_context.name.startswith('pcm_'):
            raise ValueError(f'{path}: expected lossless PCM/FLAC audio')
        if stream.codec_context.sample_rate != rate or stream.codec_context.layout.nb_channels != channels:
            raise ValueError(f'{path}: audio sample rate/channels disagree with contract')
        channel_names = [channel.name for channel in stream.codec_context.layout.channels]
        if 'NONE' in channel_names:
            raise ValueError(f'{path}: unknown audio channel identities')
        for frame in container.decode(audio=0):
            if [channel.name for channel in frame.layout.channels] != channel_names:
                raise ValueError(f'{path}: audio channel identities changed during decode')
            if frame.sample_rate != rate or frame.layout.nb_channels != channels:
                raise ValueError(f'{path}: audio format changed during decode')
            if frame.pts is None or frame.time_base is None:
                raise ValueError(f'{path}: missing audio timestamps')
            timestamp = frame.pts * frame.time_base
            if (samples == 0 and timestamp != 0) or abs(timestamp - Fraction(samples, rate)) > frame.time_base / 2:
                raise ValueError(f'{path}: audio samples are off the zero-based sample timeline')
            data = frame.to_ndarray()
            if frame.format.is_planar:
                data = data.T
            data = data.reshape(-1, channels)
            fmt = frame.format.name.removesuffix('p')
            if fmt == 's16':
                data = data.astype(np.int32) << 16
            elif fmt == 'u8':
                data = (data.astype(np.int32) - 128) << 24
            elif fmt != 's32':
                raise ValueError(f'{path}: unsupported lossless audio sample format {fmt}')
            digest.update(data.astype('<i4', copy=False).tobytes())
            samples += frame.samples
    return {'samples_per_channel': samples, 'sample_rate': rate, 'channels': channels,
            'channel_names': channel_names, 'pcm32_sha256': digest.hexdigest()}


def check(contract, root):
    root = Path(root).resolve()
    if contract['version'] != 1:
        raise ValueError('unsupported media contract version')
    source = contract['source']
    for field in ('delivery_frames', 'working_frames', 'width', 'height', 'sample_rate', 'channels', 'fps'):
        if type(source[field]) is not int or source[field] <= 0:
            raise ValueError(f'{field}: expected a positive integer')
    delivered, working = source['delivery_frames'], source['working_frames']
    width, height, fps = source['width'], source['height'], source['fps']
    if working < max(5, delivered) or (working - 5) % 17:
        raise ValueError('working frames must cover delivery on the 5+17k grid')
    sample_count = Fraction(delivered * source['sample_rate'], fps)
    if sample_count.denominator != 1:
        raise ValueError('delivery duration must correspond to an integer audio sample count')
    required = {'original', 'working', 'guard', 'guard_array', 'audio'}
    if set(contract['assets']) not in (required, required | {'final'}):
        raise ValueError('media assets must contain original, working, guard, guard_array, audio and optional final')
    paths, identities, stats = {}, {}, {}
    for role, entry in contract['assets'].items():
        path = (root / entry['path']).resolve()
        stats[role] = path.stat()
        identity = file_digest(path)
        if identity != entry['sha256']:
            raise ValueError(f'{role}: content hash mismatch')
        paths[role] = path
        identities[role] = identity

    original = Video(paths['original'], delivered, fps, native_pixels=True)
    padded = Video(paths['working'], working, fps, silent_lossless=True, native_pixels=True)
    last = None
    for index, (a, b) in enumerate(zip_longest(original, padded)):
        if index < delivered:
            if a is None or b is None or a[0] != b[0] or not np.array_equal(a[1], b[1]):
                raise ValueError(f'working source differs from original at frame {index}')
            last = a
        elif b is None or last is None or last[0] != b[0] or not np.array_equal(last[1], b[1]):
            raise ValueError(f'working padding does not repeat final original frame at {index}')

    guards = np.load(paths['guard_array'], mmap_mode='r', allow_pickle=False)
    if not isinstance(guards, np.ndarray):
        guards.close()
        raise ValueError('prepared guard must be a single NPY array, not an archive')
    if guards.dtype != np.uint8 or guards.shape != (working, height, width):
        raise ValueError('prepared guard array must be uint8 [working_frames, height, width]')
    guard_video = Video(paths['guard'], working, fps, silent_lossless=True)
    for i, guard in enumerate(guard_video):
        if guard.shape != (height, width, 3) or not np.array_equal(guard, np.repeat(guards[i, :, :, None], 3, axis=2)):
            raise ValueError(f'guard video differs from prepared array at frame {i}')
    padding_policy = contract['guard_padding_policy']
    if padding_policy not in ('repeat_last', 'tracked'):
        raise ValueError('guard_padding_policy must be repeat_last or tracked')
    tail_changes = [int((guards[i] != guards[delivered - 1]).sum()) for i in range(delivered, working)]
    guard_padding_exact = not any(tail_changes)
    if padding_policy == 'repeat_last' and not guard_padding_exact:
        raise ValueError('guard padding does not repeat final delivery guard')

    expected_audio = audio_identity(paths['audio'], source['sample_rate'], source['channels'])
    if expected_audio['samples_per_channel'] != sample_count:
        raise ValueError('prepared audio sample count differs from exact delivery duration')
    result = {'version': 1, 'passed': True, 'asset_sha256': identities,
              'software': {'validator_sha256': file_digest(Path(__file__)),
                           'pyav': av.__version__, 'numpy': np.__version__},
              'source_comparison': 'same native pixel format and precision',
              'delivery_frames': delivered, 'working_frames': working,
              'source_original_frames_exact': True, 'repeat_last_padding_exact': True,
              'guard_video_array_exact': True, 'guard_padding_policy': padding_policy,
              'guard_padding_exact': guard_padding_exact,
              'guard_padding_changed_pixels_by_frame': tail_changes,
              'warnings': [] if guard_padding_exact else ['Guard tracking changes on repeated source-padding frames; no creative quality judgment is implied.'],
              'prepared_audio': expected_audio,
              'limitations': ['Source window/editorial intent and original-film audio alignment are not certified.',
                              'Guard agreement is not segmentation/occlusion correctness.',
                              'No likeness, facial-performance, lip-sync or full-motion quality approval.']}
    if 'final' in paths:
        source_frames = Video(paths['working'], working, fps, size=(width, height))
        final_frames = Video(paths['final'], delivered, fps, native16=True)
        protected = changed = maximum = 0
        regions = {'feather_pixels': 0, 'opaque_edit_pixels': 0, 'changed_edit_pixels': 0}
        for i, (reference, final) in enumerate(zip_longest(source_frames, final_frames)):
            if i >= delivered:
                continue
            if reference is None or final is None or final.shape != (height, width, 4):
                raise ValueError(f'final shape/count differs at delivery frame {i}')
            if not np.all(final[:, :, 3] == 65535):
                raise ValueError(f'final alpha must be opaque at delivery frame {i}')
            error = np.abs(final[:, :, :3].astype(np.int32) - reference.astype(np.int32) * 257)
            outside = guards[i] == 0
            edited = ~outside
            changed_pixels = error.max(axis=2) != 0
            protected += int(outside.sum())
            changed += int((changed_pixels & outside).sum())
            if outside.any():
                maximum = max(maximum, int(error[outside].max()))
            regions['feather_pixels'] += int(((guards[i] > 0) & (guards[i] < 255)).sum())
            regions['opaque_edit_pixels'] += int((guards[i] == 255).sum())
            regions['changed_edit_pixels'] += int((changed_pixels & edited).sum())
        if protected == 0:
            raise ValueError('no protected pixels: exact-copy gate would be vacuous')
        if changed:
            raise ValueError(f'final changed {changed} protected pixels; max native16 channel error {maximum}')
        final_audio = audio_identity(paths['final'], source['sample_rate'], source['channels'])
        if final_audio != expected_audio:
            raise ValueError('final audio differs from prepared source samples')
        result['final'] = {'protected_pixels': protected, 'changed_protected_pixels': changed,
                           'max_native16_channel_error': maximum, **regions, 'audio_exact': True,
                           'audio': final_audio}
    for role, path in paths.items():
        current = path.stat()
        before = stats[role]
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (current.st_ino, current.st_size, current.st_mtime_ns):
            raise ValueError(f'{role}: file changed during validation')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = check(json.loads(args.contract.read_text()), args.root)
    except (KeyError, TypeError, ValueError, OSError, av.error.FFmpegError) as error:
        print(f'H3 media validation failed: {error}', file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
