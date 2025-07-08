import webrtcvad
import collections
import numpy as np
import wave

# Aggressivity Level
vad = webrtcvad.Vad(2);

def frame_generator(frame_duration_ms, audio, sample_rate):
	bytes_for_frame = int(sample_rate * frame_duration_ms / 1000) * 2
	offset = 0
	while offset + bytes_for_frame < len(audio):
		yield audio[offset:offset + bytes_for_frame]
		offset += bytes_for_frame

def vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, audio):
	frames = frame_generator(frame_duration_ms, audio, sample_rate)
	num_padding_frames = int(padding_duration_ms / frame_duration_ms)

	ring_buffer = collections.deque(maxlen=num_padding_frames)
	triggered = False

	voiced_frames = []

	for frame in frames:
		is_speech = vad.is_speech(frame, sample_rate)
		if not triggered:
			ring_buffer.append((frame, is_speech))
			num_voiced = len ([f for f, speech in ring_buffer if speech])
			if num_voiced > 0.9 * ring_buffer.maxlen:
				triggered = True
				for f, s in ring_buffer:
					voiced_frames.append(f)
				ring_buffer.clear()
		else:
			voiced_frames.append(frame)
			ring_buffer.append((frame, is_speech))
			num_unvoiced = len([f for f, speech in ring_buffer if not speech])
			if num_unvoiced > 0.9 * ring_buffer.maxlen:
				triggered = False
				yield b''.join(voiced_frames)
				ring_buffer.clear()
				voiced_frames = []
	if(voiced_frames):
		yield b''.join(voiced_frames)
			
def write_wave(path, audio, sample_rate):
	with wave.open(path, 'wb') as wf:
		wf.setnchannels(1)
		wf.setsampwidth(2)
		wf.setframerate(sample_rate)
		wf.writeframes(audio)			
