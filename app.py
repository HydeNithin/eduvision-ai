"""
EduVision AI v3 — Stable, synced, longer videos
"""

import os, json, uuid, subprocess, threading, time, re, textwrap
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY",  "your-key")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "your-key")
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
jobs = {}

# ── Step 1: Claude writes timed lesson plan ───────────────────────────────────
def generate_lesson_plan(question, audience):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    audience_map = {
        "child":        "a curious 6-10 year old. Simple words, fun analogies. 90 seconds total.",
        "student":      "a high school or university student. Clear, structured, with examples. 120 seconds total.",
        "professional": "a busy professional. Concise, practical. 90 seconds total.",
    }
    desc = audience_map.get(audience, audience_map["student"])

    prompt = f"""You are an expert educational video script writer. Question: "{question}"
Audience: {desc}

Return ONLY valid JSON, no markdown fences, no extra text whatsoever:
{{
  "title": "Catchy lesson title under 50 chars",
  "key_points": ["point 1", "point 2", "point 3"],
  "scenes": [
    {{
      "id": 1,
      "duration": 8,
      "narration": "What teacher says during this scene. 1-3 sentences max.",
      "visual": "What appears on screen in plain English",
      "manim_snippet": "ONLY the Python statements for this scene — one statement per line, properly indented with 8 spaces, NO semicolons between statements"
    }}
  ]
}}

SCENE STRUCTURE (create exactly 8-10 scenes):
- Scene 1 (8s): Bold title card
- Scene 2 (10s): Introduce the concept simply  
- Scene 3 (12s): Core idea with first example
- Scene 4 (12s): Second example or diagram
- Scene 5 (12s): Third example, deepen understanding
- Scene 6 (10s): Common mistake or edge case
- Scene 7 (10s): Real world application
- Scene 8 (10s): Summary and key points
- Scene 9 (8s): Closing encouragement

MANIM SNIPPET RULES — critical, follow every one:
- Each snippet is the BODY of the construct method for that scene only
- Every line must start with exactly 8 spaces of indentation
- ONE Python statement per line — NEVER use semicolons to join statements
- ALL coordinate arrays MUST be 3-element: use np.array([x, y, 0]) or constants like UP, DOWN, LEFT, RIGHT, ORIGIN
- NEVER write [x, y] — always [x, y, 0]
- Only use these safe shapes: Circle, Rectangle, Square, Arrow, Line, Dot, Text
- NEVER use Polygon, Triangle, or RegularPolygon — they cause crashes
- Colors: BLUE, YELLOW, GREEN, RED, ORANGE, PURPLE, WHITE, TEAL, PINK, GOLD
- Text strings must use double quotes inside the Python string
- End every scene snippet with: self.play(FadeOut(*self.mobjects))
- self.wait() total across all self.play() and self.wait() must equal scene duration"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    # Strip any markdown fences
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:]
            part = part.strip()
            if part.startswith("{"):
                raw = part
                break
    return json.loads(raw.strip())


# ── Step 2: Build Manim script — one statement per line, no semicolons ────────
def build_manim_script(lesson):
    scenes = lesson.get("scenes", [])
    lines = [
        "from manim import *",
        "import numpy as np",
        "",
        "class EduScene(Scene):",
        "    def construct(self):",
    ]

    for i, scene in enumerate(scenes):
        snippet = scene.get("manim_snippet", "        self.wait(5)")
        lines.append(f"        # ── Scene {i+1} ──────────────────────")

        # Fix common issues in Claude-generated code:
        # 1. Split semicolons into separate lines
        fixed_lines = []
        for raw_line in snippet.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            # Split on semicolons that aren't inside strings
            if ";" in stripped:
                # Simple split — works for most cases
                parts = stripped.split(";")
                for part in parts:
                    part = part.strip()
                    if part:
                        fixed_lines.append("        " + part)
            else:
                # Preserve existing indentation if it has 8+ spaces, else add it
                if raw_line.startswith("        "):
                    fixed_lines.append(raw_line)
                else:
                    fixed_lines.append("        " + stripped)

        lines.extend(fixed_lines)
        lines.append("")

    return "\n".join(lines)


# ── Step 3: Build full narration ──────────────────────────────────────────────
def build_narration(lesson):
    scenes = lesson.get("scenes", [])
    parts = []
    timing = []
    cursor = 0.0
    for scene in scenes:
        dur = float(scene.get("duration", 8))
        narr = scene.get("narration", "").strip()
        timing.append({"start": cursor, "end": cursor + dur, "text": narr})
        parts.append(narr)
        cursor += dur
    return " ".join(parts), timing, cursor


# ── Step 4: Voice generation ──────────────────────────────────────────────────
def generate_voice(narration, output_path):
    # Try ElevenLabs with newer model
    try:
        from elevenlabs import ElevenLabs, save
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            text=narration,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_turbo_v2"   # newer free-tier model
        )
        save(audio, str(output_path))
        print("ElevenLabs voice OK (turbo_v2)")
        return True
    except Exception as e:
        print(f"ElevenLabs turbo_v2 error: {e}")

    # Try flash model
    try:
        from elevenlabs import ElevenLabs, save
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            text=narration,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_flash_v2_5"
        )
        save(audio, str(output_path))
        print("ElevenLabs voice OK (flash_v2_5)")
        return True
    except Exception as e:
        print(f"ElevenLabs flash error: {e}")

    # macOS say fallback
    try:
        aiff = output_path.with_suffix(".aiff")
        subprocess.run(["say", "-r", "170", "-v", "Samantha", "-o", str(aiff), narration],
                       check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-i", str(aiff), str(output_path), "-y"],
                       check=True, capture_output=True)
        print("macOS Samantha voice fallback OK")
        return True
    except Exception as e:
        print(f"Voice all failed: {e}")
        return False


# ── Step 5: Manim render ──────────────────────────────────────────────────────
def generate_animation(manim_code, job_dir):
    script_path = job_dir / "scene.py"
    script_path.write_text(manim_code)
    # Also save a readable copy for debugging
    (job_dir / "scene_debug.py").write_text(manim_code)
    print("Manim script written")

    try:
        result = subprocess.run(
            ["manim", "render", str(script_path), "EduScene",
             "--format", "mp4",
             "--media_dir", str(job_dir / "media"),
             "-q", "m",
             "--disable_caching"],
            capture_output=True, text=True, timeout=600
        )
        print("Manim exit code:", result.returncode)
        if result.returncode != 0:
            print("MANIM STDERR:\n", result.stderr[-3000:])
            return None
        for mp4 in (job_dir / "media").rglob("*.mp4"):
            print("Manim output:", mp4)
            return mp4
        return None
    except Exception as e:
        print(f"Manim exception: {e}")
        return None


# ── Step 6: Get duration ──────────────────────────────────────────────────────
def get_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True
        )
        return float(r.stdout.strip())
    except:
        return None


# ── Step 7: Sync and merge ────────────────────────────────────────────────────
def sync_and_merge(video_path, audio_path, output_path):
    audio_dur = get_duration(audio_path) if audio_path.exists() else None
    video_dur = get_duration(video_path)
    print(f"Video: {video_dur:.1f}s | Audio: {audio_dur:.1f}s" if audio_dur and video_dur else "Duration unknown")

    if not audio_path.exists():
        import shutil; shutil.copy(video_path, output_path)
        return True

    try:
        if audio_dur and video_dur and abs(video_dur - audio_dur) > 2:
            speed = max(0.5, min(2.0, video_dur / audio_dur))
            print(f"Speed adjusting video by {speed:.3f}x")
            subprocess.run([
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter:v", f"setpts={1/speed:.4f}*PTS",
                "-c:a", "aac",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", str(output_path), "-y"
            ], check=True, capture_output=True, timeout=180)
        else:
            subprocess.run([
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", str(output_path), "-y"
            ], check=True, capture_output=True, timeout=180)
        print("Merge done")
        return True
    except Exception as e:
        print(f"Merge error: {e}")
        import shutil; shutil.copy(video_path, output_path)
        return True


# ── Step 8: Fallback video — clean text only, no special chars ───────────────
def clean(text, maxlen=55):
    """Remove characters that break ffmpeg drawtext"""
    text = text or ""
    # Remove problematic characters
    for ch in ["'", '"', ":", "[", "]", "{", "}", "(", ")", "\\", "/", "%", "=", "!", "?", "#", "&", "*", "`", "<", ">", "|"]:
        text = text.replace(ch, "")
    # Collapse whitespace
    text = " ".join(text.split())
    return text[:maxlen]

def create_fallback_video(lesson, job_dir, audio_path=None):
    try:
        scenes = lesson.get("scenes", [])
        title = clean(lesson.get("title", "Lesson"), 45)

        total_dur = (get_duration(audio_path)
                     if audio_path and audio_path.exists()
                     else sum(s.get("duration", 8) for s in scenes))
        total_dur = max(30, float(total_dur))

        output = job_dir / "fallback.mp4"
        filters = []

        # Title bar — always visible
        filters.append(
            f"drawtext=text='{title}':fontcolor=0x64ffda:fontsize=38:"
            f"x=(w-text_w)/2:y=36:box=1:boxcolor=0x0e1018@0.7:boxborderw=8"
        )
        # EduVision watermark
        filters.append(
            "drawtext=text='EduVision AI':fontcolor=0x444466:fontsize=20:"
            "x=w-160:y=h-36"
        )
        # Progress bar
        filters.append(
            f"drawbox=x=0:y=h-8:w='iw*min(t\\,{total_dur:.1f})/{total_dur:.1f}':h=8:"
            "color=0x64ffda@0.9:t=fill"
        )

        # Per-scene text — visual description + narration
        cursor = 0
        for i, scene in enumerate(scenes):
            dur = scene.get("duration", 8)
            t0, t1 = cursor, cursor + dur
            vis  = clean(scene.get("visual",""), 52)
            narr = clean(scene.get("narration",""), 70)

            # Scene number badge
            filters.append(
                f"drawtext=text='Scene {i+1}':fontcolor=0xaaaaff:fontsize=18:"
                f"x=40:y=100:enable='between(t,{t0},{t1})'"
            )
            # Visual description
            if vis:
                filters.append(
                    f"drawtext=text='{vis}':fontcolor=white:fontsize=30:"
                    f"x=40:y=140:enable='between(t,{t0},{t1})'"
                )
            # Narration (split into two lines if long)
            if narr:
                line1 = narr[:55]
                line2 = narr[55:110]
                filters.append(
                    f"drawtext=text='{line1}':fontcolor=0x88ccff:fontsize=24:"
                    f"x=40:y=560:enable='between(t,{t0},{t1})'"
                )
                if line2:
                    filters.append(
                        f"drawtext=text='{line2}':fontcolor=0x88ccff:fontsize=24:"
                        f"x=40:y=595:enable='between(t,{t0},{t1})'"
                    )
            cursor += dur

        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", f"color=c=0x0e1018:size=1280x720:duration={total_dur:.0f}:rate=24",
            "-vf", ",".join(filters),
            "-c:v", "libx264", "-preset", "fast",
            "-t", f"{total_dur:.1f}",
            str(output), "-y"
        ], check=True, capture_output=True, timeout=180)
        print(f"Fallback video OK — {total_dur:.0f}s")
        return output
    except Exception as e:
        print(f"Fallback error: {e}")
        import traceback; print(traceback.format_exc())
        return None


# ── Pipeline ──────────────────────────────────────────────────────────────────
def run_pipeline(job_id, question, audience):
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    def update(status, progress, message):
        print(f"[{job_id[:8]}] {progress}% — {message}")
        jobs[job_id].update({"status": status, "progress": progress, "message": message})

    try:
        update("running", 8, "Claude AI is writing your lesson script...")
        lesson = generate_lesson_plan(question, audience)
        (job_dir / "lesson.json").write_text(json.dumps(lesson, indent=2))
        scenes = lesson.get("scenes", [])
        total_dur = sum(s.get("duration", 8) for s in scenes)
        print(f"Lesson: '{lesson.get('title')}' | {len(scenes)} scenes | ~{total_dur}s")

        update("running", 22, f"Script done — {len(scenes)} scenes, ~{total_dur}s. Generating voice...")
        full_narration, timing, _ = build_narration(lesson)
        audio_path = job_dir / "narration.mp3"
        generate_voice(full_narration, audio_path)

        update("running", 42, "Building animation script...")
        manim_code = build_manim_script(lesson)
        (job_dir / "manim_script.py").write_text(manim_code)

        update("running", 52, f"Rendering {len(scenes)}-scene animation (2-4 mins)...")
        video_path = generate_animation(manim_code, job_dir)

        if not video_path:
            update("running", 68, "Building fallback video...")
            video_path = create_fallback_video(lesson, job_dir, audio_path)

        if not video_path:
            update("error", 0, "Video generation failed. Please try again.")
            return

        update("running", 84, "Syncing audio to video...")
        final_path = job_dir / "final.mp4"
        sync_and_merge(video_path, audio_path, final_path)

        jobs[job_id]["video_url"] = f"/video/{job_id}"
        jobs[job_id]["lesson"]    = lesson
        jobs[job_id]["timing"]    = timing
        update("done", 100, f"Ready! {total_dur}s video, {len(scenes)} scenes")

    except json.JSONDecodeError as e:
        update("error", 0, f"AI response parse error: {e}")
    except Exception as e:
        import traceback; print(traceback.format_exc())
        update("error", 0, f"Error: {str(e)}")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    question = data.get("question", "").strip()
    audience = data.get("audience", "student")
    if not question:
        return jsonify({"error": "Question required"}), 400
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id, "question": question, "audience": audience,
        "status": "queued", "progress": 0, "message": "Queued...",
        "video_url": None, "lesson": None, "created_at": time.time()
    }
    t = threading.Thread(target=run_pipeline, args=(job_id, question, audience))
    t.daemon = True
    t.start()
    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404
    return jsonify(job)

@app.route("/video/<job_id>")
def serve_video(job_id):
    p = OUTPUT_DIR / job_id / "final.mp4"
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    return send_file(str(p), mimetype="video/mp4")

@app.route("/lesson/<job_id>")
def get_lesson(job_id):
    p = OUTPUT_DIR / job_id / "lesson.json"
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    return jsonify(json.loads(p.read_text()))

if __name__ == "__main__":
    print("=" * 60)
    print("  EduVision AI v3 — http://localhost:8080")
    print("=" * 60)
    app.run(debug=True, port=8080, host="0.0.0.0", use_reloader=False, threaded=True)