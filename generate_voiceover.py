import asyncio
import os
import json
import subprocess
import edge_tts
import imageio_ffmpeg

VOICE = "en-US-ChristopherNeural"
AUDIO_DIR = "~/Documents/Google anti-gravity projects/mindset_upgrade_reel/audio"

SEGMENTS = [
    {
        "id": "vo_1",
        "text": "AI isn't making you less capable.",
        "target_start": 1.1,
        "rate": "+38%",
        "pitch": "-1Hz"
    },
    {
        "id": "vo_2a",
        "text": "For most people, the problem isn't a lack of time.",
        "target_start": 3.3,
        "rate": "+42%",
        "pitch": "+0Hz"
    },
    {
        "id": "vo_2b",
        "text": "It's a lack of leverage.",
        "target_start": 5.7,
        "rate": "+34%",
        "pitch": "-1Hz"
    },
    {
        "id": "vo_3",
        "text": "AI gives one person access to capabilities that once required entire teams.",
        "target_start": 7.3,
        "rate": "+32%",
        "pitch": "+0Hz"
    },
    {
        "id": "vo_4a",
        "text": "The real shift happens when you stop asking AI to replace your effort...",
        "target_start": 11.8,
        "rate": "+40%",
        "pitch": "+0Hz"
    },
    {
        "id": "vo_4b",
        "text": "...and start using it to expand your ability.",
        "target_start": 14.8,
        "rate": "+34%",
        "pitch": "-1Hz"
    },
    {
        "id": "vo_5a",
        "text": "An idea can become a plan.",
        "target_start": 17.1,
        "rate": "+36%",
        "pitch": "+0Hz"
    },
    {
        "id": "vo_5b",
        "text": "A plan can become action.",
        "target_start": 18.8,
        "rate": "+36%",
        "pitch": "+0Hz"
    },
    {
        "id": "vo_5c",
        "text": "And action can become output, faster than ever before.",
        "target_start": 20.4,
        "rate": "+40%",
        "pitch": "-1Hz"
    },
    {
        "id": "vo_6a",
        "text": "The advantage won't come from simply using AI.",
        "target_start": 23.0,
        "rate": "+35%",
        "pitch": "+0Hz"
    },
    {
        "id": "vo_6b",
        "text": "It will come from learning how to think with it.",
        "target_start": 25.1,
        "rate": "+26%",
        "pitch": "-1Hz"
    },
    {
        "id": "vo_7",
        "text": "Your mindset is the real upgrade.",
        "target_start": 28.0,
        "rate": "+30%",
        "pitch": "-2Hz"
    }
]

async def generate_speech():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    manifest = []
    
    for seg in SEGMENTS:
        output_file = os.path.join(AUDIO_DIR, f"{seg['id']}.mp3")
        communicate = edge_tts.Communicate(
            text=seg["text"],
            voice=VOICE,
            rate=seg.get("rate", "+0%"),
            pitch=seg.get("pitch", "+0Hz")
        )
        
        with open(output_file, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                    
        manifest.append({
            "id": seg["id"],
            "text": seg["text"],
            "target_start": seg["target_start"],
            "file": output_file
        })
        
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    for m in manifest:
        cmd = [FFMPEG, '-i', m['file']]
        p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        for line in p.stderr.split('\n'):
            if 'Duration:' in line:
                dur_str = line.split('Duration:')[1].split(',')[0].strip()
                h, mn, s = dur_str.split(':')
                dur = float(h)*3600 + float(mn)*60 + float(s)
                m['duration'] = dur
                print(f"[{m['id']:6s}] Start: {m['target_start']:5.2f}s | Dur: {dur:4.2f}s | End: {(m['target_start']+dur):5.2f}s | {m['text']}")

    manifest_path = os.path.join(AUDIO_DIR, "vo_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print("Voiceover manifest saved successfully.")

if __name__ == "__main__":
    asyncio.run(generate_speech())
