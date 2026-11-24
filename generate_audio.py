import os
import json
import numpy as np
import scipy.io.wavfile as wavfile
import subprocess
import imageio_ffmpeg

SAMPLE_RATE = 44100
DURATION = 30.0
TOTAL_SAMPLES = int(SAMPLE_RATE * DURATION)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

AUDIO_DIR = "~/Documents/Google anti-gravity projects/mindset_upgrade_reel/audio"

def make_stereo(arr):
    if arr.ndim == 1:
        return np.column_stack((arr, arr))
    elif arr.shape[1] == 1:
        return np.column_stack((arr[:, 0], arr[:, 0]))
    return arr

# Audio tracks
music_track = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
sfx_track = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
vo_track = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)

def add_sound(target, sound, start_time, gain=1.0):
    start_idx = int(start_time * SAMPLE_RATE)
    sound = make_stereo(sound) * gain
    num_samples = len(sound)
    if start_idx >= TOTAL_SAMPLES or start_idx < 0:
        return
    end_idx = min(start_idx + num_samples, TOTAL_SAMPLES)
    valid_len = end_idx - start_idx
    target[start_idx:end_idx] += sound[:valid_len]

# ----------------- SYNTHESIZER MODULES -----------------

def synth_sub_impact(dur=2.0, f_start=140.0, f_end=32.0, gain=0.9):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = f_start * (f_end / f_start) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    env = np.exp(-3.5 * t / dur)
    wave = np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.15 * np.sin(3 * phase)
    wave = np.tanh(wave * 2.0) * env * gain
    # Click transient
    punch = np.sin(2 * np.pi * 200 * t[:int(0.03*SAMPLE_RATE)]) * np.exp(-120 * t[:int(0.03*SAMPLE_RATE)])
    wave[:len(punch)] += punch * 0.5
    return np.column_stack((wave, wave))

def synth_braam(dur=3.2, f0=50.0, gain=0.85):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f = f0 * (1.0 - 0.04 * (t / dur))
    p1 = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    p2 = 2 * np.pi * np.cumsum(f * 1.007) / SAMPLE_RATE
    p3 = 2 * np.pi * np.cumsum(f * 0.993) / SAMPLE_RATE
    saw1 = 2.0 * (p1 / (2*np.pi) - np.floor(p1 / (2*np.pi) + 0.5))
    saw2 = 2.0 * (p2 / (2*np.pi) - np.floor(p2 / (2*np.pi) + 0.5))
    saw3 = 2.0 * (p3 / (2*np.pi) - np.floor(p3 / (2*np.pi) + 0.5))
    raw = saw1 * 0.5 + saw2 * 0.25 + saw3 * 0.25
    dist = np.tanh(raw * 4.5)
    env = np.clip(t / 0.06, 0, 1) * np.exp(-1.4 * t / dur)
    left = dist * env * gain
    right = np.tanh((saw1*0.25 + saw2*0.5 + saw3*0.25) * 4.5) * env * gain
    return np.column_stack((left, right))

def synth_glitch(dur=0.35, gain=0.7):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    square = np.sign(np.sin(2 * np.pi * 1200 * t + np.sin(2 * np.pi * 40 * t) * 5))
    glitch = (noise * 0.6 + square * 0.4) * np.exp(-8 * t / dur) * gain
    # Bitcrush simulation
    glitch = np.round(glitch * 8) / 8
    pan = np.sin(2 * np.pi * 15 * t) * 0.5 + 0.5
    return np.column_stack((glitch * (1 - pan), glitch * pan))

def synth_whoosh(dur=0.7, pan_dir=1, gain=0.6):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    env = np.sin(np.pi * t / dur) ** 2
    f_center = 200 + 4000 * np.sin(np.pi * t / dur) ** 2
    mod = noise * env * gain
    pan = t / dur if pan_dir > 0 else (1 - t / dur)
    return np.column_stack((mod * (1.0 - pan), mod * pan))

def synth_ui_click(gain=0.4):
    dur = 0.05
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    click = np.sin(2 * np.pi * 2800 * t) * np.exp(-150 * t) * gain
    return np.column_stack((click, click))

def synth_riser(dur=2.5, f_start=150.0, f_end=3200.0, gain=0.5):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = f_start * (f_end / f_start) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    noise = np.random.uniform(-0.4, 0.4, n) * (t / dur) ** 2
    wave = (np.sin(phase) * 0.7 + noise * 0.3) * (t / dur) ** 2.0 * gain
    lfo = np.sin(2 * np.pi * 10 * t)
    return np.column_stack((wave * (0.8 + 0.2 * lfo), wave * (0.8 - 0.2 * lfo)))

def synth_crystal_chord(dur=3.5, base_freq=220.0, gain=0.45):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    chord_freqs = [base_freq, base_freq * 1.25, base_freq * 1.5, base_freq * 1.875, base_freq * 2.0]
    out = np.zeros(n, dtype=np.float32)
    for i, f in enumerate(chord_freqs):
        phase = 2 * np.pi * f * t
        sine = np.sin(phase) + 0.2 * np.sin(2 * phase)
        decay = 1.0 / (1.0 + (i * 0.3))
        env = np.exp(-1.2 * decay * t / dur)
        out += sine * env * (0.2 / len(chord_freqs))
    left = out * gain * (0.9 + 0.1 * np.sin(2 * np.pi * 0.5 * t))
    right = out * gain * (0.9 - 0.1 * np.sin(2 * np.pi * 0.5 * t))
    return np.column_stack((left, right))

# ----------------- MUSIC PRODUCTION GENERATOR -----------------

def generate_cinematic_music():
    print("Generating cinematic score & electronic pulses...")
    # BPM = 120 (0.5s per beat, 2.0s per measure)
    bpm = 120.0
    beat_dur = 60.0 / bpm  # 0.5s
    
    # 1. Atmospheric Drone (0.0 to 28.0s)
    t = np.linspace(0, 28.0, int(SAMPLE_RATE * 28.0), endpoint=False)
    drone_f = 43.65  # F0
    drone_p = 2 * np.pi * drone_f * t
    drone = (np.sin(drone_p) * 0.5 + np.sin(2 * drone_p) * 0.3 + np.sin(3 * drone_p) * 0.1) * 0.3
    # Low pass / warm filter simulation
    drone_env = np.ones_like(t)
    drone_env[:int(SAMPLE_RATE * 2.0)] = np.linspace(0, 1, int(SAMPLE_RATE * 2.0))
    # Silence at 6.3 - 6.8s (The freeze moment)
    freeze_start = int(6.3 * SAMPLE_RATE)
    freeze_end = int(6.8 * SAMPLE_RATE)
    drone_env[freeze_start:freeze_end] = np.linspace(1, 0, freeze_end - freeze_start) ** 2
    drone_env[freeze_end:freeze_end + int(0.5 * SAMPLE_RATE)] = np.linspace(0, 1, int(0.5 * SAMPLE_RATE))
    # Fade out before payoff silence (at 28.0s)
    drone_env[-int(SAMPLE_RATE * 1.5):] = np.linspace(1, 0, int(SAMPLE_RATE * 1.5))
    
    drone_track = np.column_stack((drone * drone_env, drone * drone_env))
    add_sound(music_track, drone_track, 0.0, gain=0.6)
    
    # 2. Rhythmic Tech Arp & Sub Bass (7.0 to 12.0s - Scene 3)
    notes_s3 = [110.0, 130.81, 146.83, 164.81, 196.0, 220.0]
    for beat_idx in range(10):  # 7.0s to 12.0s
        t_pos = 7.0 + beat_idx * 0.5
        note_freq = notes_s3[beat_idx % len(notes_s3)]
        dur_note = 0.4
        tn = np.linspace(0, dur_note, int(SAMPLE_RATE * dur_note), endpoint=False)
        wave = np.sin(2 * np.pi * note_freq * tn) * np.exp(-6.0 * tn) * 0.35
        # Sub kick on downbeats
        if beat_idx % 2 == 0:
            kick = np.sin(2 * np.pi * 55 * tn) * np.exp(-12.0 * tn) * 0.5
            wave += kick
        add_sound(music_track, wave, t_pos, gain=0.7)
        
    # 3. Driving Four-on-the-Floor Tech Beats & Synth Stabs (12.0 to 23.0s - Scenes 4 & 5)
    for beat_idx in range(22):  # 12.0s to 23.0s (every 0.5s)
        t_pos = 12.0 + beat_idx * 0.5
        dur_beat = 0.45
        tn = np.linspace(0, dur_beat, int(SAMPLE_RATE * dur_beat), endpoint=False)
        # Tight Electronic Kick
        kick_freq = 130.0 * (45.0 / 130.0) ** (tn / 0.15)
        kick_p = 2 * np.pi * np.cumsum(kick_freq) / SAMPLE_RATE
        kick = np.tanh(np.sin(kick_p) * 2.5) * np.exp(-14.0 * tn) * 0.8
        
        # Crisp Hi-hat on offbeats
        hat = np.random.uniform(-0.3, 0.3, len(tn)) * np.exp(-35.0 * tn) * 0.35
        
        # Bass Ostinato
        f_bass = 55.0 if (beat_idx // 4) % 2 == 0 else 65.4  # A1 to C2
        bass = np.sin(2 * np.pi * f_bass * tn) * np.exp(-4.0 * tn) * 0.45
        
        beat_wave = kick + bass
        if beat_idx % 2 == 1:
            beat_wave += hat
            
        # Progressive energy build from 17.0s to 23.0s
        prog_gain = 0.75 + (0.25 * (beat_idx / 22.0))
        add_sound(music_track, beat_wave, t_pos, gain=prog_gain)

    # 4. Cinematic Tension & Chord Swell (23.0 to 27.0s - Scene 6)
    chord_s6 = synth_crystal_chord(dur=3.8, base_freq=174.61, gain=0.6)  # F3 minor crystal chord
    add_sound(music_track, chord_s6, 23.0, gain=0.8)
    
    # 5. Final Climax Hits (27.0s, 27.4s, 27.8s - Scene 7)
    hit1 = synth_sub_impact(dur=0.4, f_start=180.0, f_end=45.0, gain=1.0)
    hit2 = synth_sub_impact(dur=0.4, f_start=200.0, f_end=50.0, gain=1.05)
    hit3 = synth_sub_impact(dur=0.5, f_start=240.0, f_end=35.0, gain=1.2)
    add_sound(music_track, hit1, 27.0, gain=1.0)
    add_sound(music_track, hit2, 27.4, gain=1.0)
    add_sound(music_track, hit3, 27.8, gain=1.1)
    
    # 6. Final Shimmer after silence (28.4 to 30.0s)
    final_shimmer = synth_crystal_chord(dur=1.6, base_freq=261.63, gain=0.35)
    add_sound(music_track, final_shimmer, 28.4, gain=0.6)

# ----------------- SOUND DESIGN & SFX GENERATOR -----------------

def generate_sfx():
    print("Generating synchronized SFX...")
    # Scene 1 (0.0 - 3.0s):
    # 0.0s subtle high-tech tick
    add_sound(sfx_track, synth_ui_click(0.3), 0.05)
    # 0.5s glitch tear
    add_sound(sfx_track, synth_glitch(0.3, 0.7), 0.5)
    # 0.8s Massive Braam Impact on "WRONG."
    add_sound(sfx_track, synth_braam(dur=2.8, f0=55.0, gain=0.9), 0.78)
    add_sound(sfx_track, synth_sub_impact(dur=1.8, f_start=160.0, f_end=35.0, gain=0.95), 0.78)
    # 2.2s expand whoosh on "CAPABLE"
    add_sound(sfx_track, synth_whoosh(dur=0.6, pan_dir=1, gain=0.5), 2.2)
    
    # Scene 2 (3.0 - 7.0s):
    # 3.0 to 5.5s: Cascade of floating task clicks & digital flutter
    for i in range(12):
        t_click = 3.0 + (i * 0.18) + (np.sin(i)*0.04)
        add_sound(sfx_track, synth_ui_click(0.25 + (i * 0.02)), t_click)
    # 6.0s riser into freeze
    add_sound(sfx_track, synth_riser(dur=0.6, f_start=300.0, f_end=1600.0, gain=0.4), 5.8)
    # 6.4s - 6.8s SILENCE (Freeze)
    # 6.8s Sub drop impact on "LEVERAGE."
    add_sound(sfx_track, synth_sub_impact(dur=1.8, f_start=130.0, f_end=32.0, gain=0.85), 6.8)
    
    # Scene 3 (7.0 - 12.0s):
    # Orbital capability modules activating
    for idx in range(8):
        t_mod = 8.0 + (idx * 0.45)
        add_sound(sfx_track, synth_ui_click(0.3), t_mod)
        if idx % 2 == 0:
            add_sound(sfx_track, synth_whoosh(dur=0.4, pan_dir=(1 if idx%4==0 else -1), gain=0.35), t_mod)
    # 11.5s transition riser
    add_sound(sfx_track, synth_riser(dur=0.8, f_start=200.0, f_end=2400.0, gain=0.5), 11.2)
    
    # Scene 4 (12.0 - 17.0s):
    # Hard transition at 12.0s
    add_sound(sfx_track, synth_sub_impact(dur=1.2, f_start=150.0, f_end=40.0, gain=0.7), 12.0)
    # Beat punch changes
    add_sound(sfx_track, synth_whoosh(dur=0.35, pan_dir=1, gain=0.5), 13.0)  # THINK BIGGER
    add_sound(sfx_track, synth_whoosh(dur=0.35, pan_dir=-1, gain=0.5), 14.0) # BUILD FASTER
    add_sound(sfx_track, synth_whoosh(dur=0.35, pan_dir=1, gain=0.5), 15.0)  # LEARN FASTER
    # 16.2s expand ability burst
    add_sound(sfx_track, synth_braam(dur=1.5, f0=65.0, gain=0.7), 16.2)
    
    # Scene 5 (17.0 - 23.0s):
    # 17.0s IDEA -> 18.2s PLAN -> 19.4s ACTION -> 20.6s OUTPUT
    add_sound(sfx_track, synth_whoosh(0.5, 1, 0.45), 17.0)
    add_sound(sfx_track, synth_whoosh(0.5, -1, 0.45), 18.2)
    add_sound(sfx_track, synth_whoosh(0.5, 1, 0.45), 19.4)
    add_sound(sfx_track, synth_sub_impact(1.2, 160.0, 42.0, 0.8), 20.6) # Output explosion
    # 21.5s to 22.8s: Pillar connect clicks (THINK -> BUILD -> LEARN -> IMPROVE)
    for k in range(4):
        add_sound(sfx_track, synth_ui_click(0.35), 21.6 + k * 0.3)
        
    # Scene 6 (23.0 - 27.0s):
    # 23.0s Typewriter cascade
    for ch in range(10):
        add_sound(sfx_track, synth_ui_click(0.2), 23.0 + ch * 0.08)
    # 24.6s Glitch transition
    add_sound(sfx_track, synth_glitch(0.4, 0.75), 24.6)
    # 25.0s Resonant Braam on "THE FUTURE BELONGS TO PEOPLE WHO THINK WITH AI"
    add_sound(sfx_track, synth_braam(dur=2.0, f0=52.0, gain=0.85), 25.0)
    
    # Scene 7 (27.0 - 30.0s):
    # Rapid flashes at 27.0, 27.4, 27.8
    add_sound(sfx_track, synth_glitch(0.2, 0.6), 27.0)
    add_sound(sfx_track, synth_glitch(0.2, 0.6), 27.4)
    add_sound(sfx_track, synth_glitch(0.2, 0.7), 27.8)
    # 28.4s Sub drop under final payoff
    add_sound(sfx_track, synth_sub_impact(dur=1.5, f_start=100.0, f_end=28.0, gain=0.6), 28.4)

# ----------------- MIXING & MASTERING -----------------

def load_voiceovers_and_mix():
    print("Mixing voiceover with dynamic ducking...")
    manifest_path = os.path.join(AUDIO_DIR, "vo_manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    for m in manifest:
        # Decode mp3 to wav using ffmpeg
        mp3_file = m["file"]
        wav_temp = mp3_file.replace(".mp3", "_temp.wav")
        cmd = [FFMPEG, "-y", "-i", mp3_file, "-ar", str(SAMPLE_RATE), "-ac", "2", wav_temp]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        _, vo_data = wavfile.read(wav_temp)
        if vo_data.dtype == np.int16:
            vo_data = vo_data.astype(np.float32) / 32768.0
        elif vo_data.dtype == np.int32:
            vo_data = vo_data.astype(np.float32) / 2147483648.0
            
        start_t = m["target_start"]
        add_sound(vo_track, vo_data, start_t, gain=1.15)
        
        if os.path.exists(wav_temp):
            os.remove(wav_temp)

    # Dynamic ducking of music track where voiceover is active
    vo_envelope = np.maximum(np.abs(vo_track[:, 0]), np.abs(vo_track[:, 1]))
    # Smooth envelope with moving window
    win_size = int(SAMPLE_RATE * 0.15)
    kernel = np.ones(win_size) / win_size
    vo_smooth = np.convolve(vo_envelope, kernel, mode='same')
    
    duck_gain = np.clip(1.0 - (vo_smooth * 1.8), 0.35, 1.0)
    ducked_music = music_track * duck_gain[:, np.newaxis]
    
    # Master Composite
    master = ducked_music + sfx_track * 0.95 + vo_track * 1.05
    
    # Soft limiter / normalization to -0.5 dB
    peak = np.max(np.abs(master))
    print(f"Master peak before limiting: {peak:.3f}")
    if peak > 0.001:
        target_peak = 0.94
        master = np.tanh(master / target_peak) * target_peak
        
    master_int16 = np.clip(master * 32767.0, -32768.0, 32767.0).astype(np.int16)
    out_master_path = os.path.join(AUDIO_DIR, "master_soundtrack.wav")
    wavfile.write(out_master_path, SAMPLE_RATE, master_int16)
    print(f"Master soundtrack written successfully to: {out_master_path}")

if __name__ == "__main__":
    generate_cinematic_music()
    generate_sfx()
    load_voiceovers_and_mix()
