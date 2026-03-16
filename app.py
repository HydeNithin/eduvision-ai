"""
EduVision AI v2 — Better sync, longer videos, richer animations
"""

import os, json, uuid, subprocess, threading, time, textwrap
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

# ── Step 1: Claude writes a TIMED script with per-scene narration ─────────────
def generate_lesson_plan(question, audience):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    audience_map = {
        "child":        "a curious 6-10 year old. Simple words, fun analogies, exciting. 90 seconds total.",
        "student":      "a high school or university student. Clear, structured, examples. 120 seconds total.",
        "professional": "a busy professional. Concise, practical. 90 seconds total.",
    }
    desc = audience_map.get(audience, audience_map["student"])

    prompt = f"""You are an expert educational video script writer. Question: "{question}"
Audience: {desc}

Return ONLY valid JSON, no markdown:
{{
  "title": "Catchy lesson title",
  "key_points": ["point 1", "point 2", "point 3"],
  "scenes": [
    {{
      "id": 1,
      "duration": 8,
      "narration": "Exactly what the teacher says during this scene. 1-3 sentences.",
      "visual": "Exactly what appears on screen — describe shapes, text, arrows",
      "manim_code": "self.play(...); self.wait(N)  — just the body code for this scene"
    }}
  ]
}}

SCENE RULES:
- Create 8-12 scenes. Each scene 6-12 seconds. Total 90-120 seconds.
- Scene 1: Title card
- Scenes 2-3: Introduce the concept simply
- Scenes 4-7: Core explanation with examples, diagrams, comparisons
- Scenes 8-9: Real-world application
- Scene 10+: Summary and key takeaways
- Each scene narration matches exactly what is shown visually

MANIM CODE RULES per scene:
- Use only these imports (already done): from manim import *
- Variables must be unique per scene: use scene1_title, scene2_circle etc
- ALL Polygon vertices must be 3D: [x, y, 0] NEVER [x, y]
- Use Text() not Tex() unless it's actual math
- MathTex only for real equations
- Shapes: Circle, Rectangle, Square, Arrow, Line, Dot, RoundedRectangle
- Colors: BLUE, YELLOW, GREEN, RED, ORANGE, PURPLE, WHITE, TEAL, PINK
- Animations: Write, FadeIn, FadeOut, Create, GrowFromCenter, DrawBorderThenFill
- End every scene with self.play(FadeOut(*self.mobjects)) to clear screen
- self.wait() values must match scene duration exactly"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())


# ── Step 2: Build one combined Manim scene from all scene codes ───────────────
def build_manim_script(lesson):
    scenes = lesson.get("scenes", [])
    lines = ["from manim import *", "import numpy as np", "", "class EduScene(Scene):", "    def construct(self):"]

    for i, scene in enumerate(scenes):
        code = scene.get("manim_code", "self.wait(5)")
        # indent properly
        indented = "\n".join("        " + l for l in code.strip().splitlines())
        lines.append(f"        # Scene {i+1}: {scene.get('visual','')[:60]}")
        lines.append(indented)
        lines.append("")

    return "\n".join(lines)


# ── Step 3: Build full narration with SSML-style timing markers ───────────────
def build_narration_with_timing(lesson):
    """Returns (full_text, list of (start_sec, end_sec, text) per scene)"""
    scenes = lesson.get("scenes", [])
    full_parts = []
    timing = []
    cursor = 0.0

    for scene in scenes:
        dur = float(scene.get("duration", 8))
        narr = scene.get("narration", "").strip()
        timing.append({"start": cursor, "end": cursor + dur, "text": narr})
        full_parts.append(narr)
        cursor += dur

    return " ".join(full_parts), timing, cursor


# ── Step 4: Generate voice ────────────────────────────────────────────────────
def generate_voice(narration, output_path):
    try:
        from elevenlabs import ElevenLabs, save
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            text=narration,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_monolingual_v1"
        )
        save(audio, str(output_path))
        print("ElevenLabs voice OK")
        return True
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        try:
            aiff = output_path.with_suffix(".aiff")
            subprocess.run(["say", "-r", "175", "-o", str(aiff), narration],
                           check=True, capture_output=True)
            subprocess.run(["ffmpeg", "-i", str(aiff), str(output_path), "-y"],
                           check=True, capture_output=True)
            print("macOS say fallback OK")
            return True
        except Exception as e2:
            print(f"Voice fallback error: {e2}")
            return False


# ── Step 5: Render Manim ──────────────────────────────────────────────────────
def generate_animation(manim_code, job_dir):
    script_path = job_dir / "scene.py"
    script_path.write_text(manim_code)
    print("Manim script written")
    try:
        result = subprocess.run(
            ["manim", "render", str(script_path), "EduScene",
             "--format", "mp4", "--media_dir", str(job_dir / "media"),
             "-q", "m", "--disable_caching"],
            capture_output=True, text=True, timeout=600
        )
        print("Manim exit code:", result.returncode)
        if result.returncode != 0:
            print("MANIM ERROR:\n", result.stderr[-4000:])
            return None
        for mp4 in (job_dir / "media").rglob("*.mp4"):
            print("Manim output:", mp4)
            return mp4
        return None
    except Exception as e:
        print(f"Manim exception: {e}")
        return None


# ── Step 6: Get audio duration ────────────────────────────────────────────────
def get_audio_duration(audio_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except:
        return None


# ── Step 7: Sync — stretch/compress video to match audio length ───────────────
def sync_video_to_audio(video_path, audio_path, output_path, total_scene_duration):
    audio_dur = get_audio_duration(audio_path)
    video_dur_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True
    )
    video_dur = float(video_dur_result.stdout.strip()) if video_dur_result.returncode == 0 else total_scene_duration

    print(f"Video duration: {video_dur:.1f}s, Audio duration: {audio_dur:.1f}s")

    if audio_dur and abs(video_dur - audio_dur) > 2:
        # Speed up or slow down video to match audio
        speed = video_dur / audio_dur
        speed = max(0.5, min(2.0, speed))  # clamp between 0.5x and 2x
        print(f"Adjusting video speed by {speed:.2f}x to match audio")
        try:
            subprocess.run([
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter:v", f"setpts={1/speed:.4f}*PTS",
                "-c:a", "aac",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", str(output_path), "-y"
            ], check=True, capture_output=True, timeout=180)
            print("Sync merge done")
            return True
        except Exception as e:
            print(f"Sync error: {e}")

    # No speed adjustment needed — just merge
    try:
        subprocess.run([
            "ffmpeg",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", str(output_path), "-y"
        ], check=True, capture_output=True, timeout=180)
        print("Direct merge done")
        return True
    except Exception as e:
        print(f"Merge error: {e}")
        import shutil; shutil.copy(video_path, output_path)
        return True


# ── Fallback video ────────────────────────────────────────────────────────────
def create_fallback_video(lesson, job_dir, audio_path=None):
    try:
        scenes = lesson.get("scenes", [])
        title = lesson.get("title", "Lesson").replace("'","").replace('"','')[:50]

        # Get total duration from audio if available, else sum scene durations
        if audio_path and audio_path.exists():
            total_dur = get_audio_duration(audio_path) or sum(s.get("duration",8) for s in scenes)
        else:
            total_dur = sum(s.get("duration", 8) for s in scenes)
        total_dur = max(30, total_dur)

        output = job_dir / "fallback.mp4"
        filters = []
        cursor = 0

        for i, scene in enumerate(scenes):
            dur = scene.get("duration", 8)
            vis = scene.get("visual","").replace("'","").replace('"','')[:60]
            narr = scene.get("narration","").replace("'","").replace('"','')[:80]
            t_start = cursor
            t_end = cursor + dur

            # Scene number + visual description
            filters.append(
                f"drawtext=text='Scene {i+1}\\: {vis}':fontcolor=white:fontsize=28:"
                f"x=60:y=120:enable='between(t,{t_start},{t_end})'"
            )
            # Narration text at bottom
            # wrap long narration
            wrapped = textwrap.fill(narr, 55).replace("\n", " | ")
            filters.append(
                f"drawtext=text='{wrapped}':fontcolor=0xaaddff:fontsize=22:"
                f"x=60:y=580:enable='between(t,{t_start},{t_end})'"
            )
            cursor += dur

        # Title always visible
        filters.insert(0,
            f"drawtext=text='{title}':fontcolor=0x64ffda:fontsize=40:"
            f"x=(w-text_w)/2:y=40:fontweight=bold"
        )
        # Progress bar
        if total_dur > 0:
            filters.append(
                f"drawbox=x=0:y=710:w='iw*t/{total_dur:.1f}':h=10:color=0x64ffda:t=fill"
            )

        subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", f"color=c=0x0e1018:size=1280x720:duration={total_dur:.0f}:rate=24",
            "-vf", ",".join(filters),
            "-c:v", "libx264", "-t", str(total_dur),
            str(output), "-y"
        ], check=True, capture_output=True, timeout=180)
        print(f"Fallback video OK ({total_dur:.0f}s)")
        return output
    except Exception as e:
        print(f"Fallback error: {e}")
        return None


# ── Pipeline ──────────────────────────────────────────────────────────────────
def run_pipeline(job_id, question, audience):
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    def update(status, progress, message):
        print(f"[{job_id[:8]}] {progress}% — {message}")
        jobs[job_id].update({"status": status, "progress": progress, "message": message})

    try:
        update("running", 8,  "Claude AI is writing your lesson script...")
        lesson = generate_lesson_plan(question, audience)
        (job_dir / "lesson.json").write_text(json.dumps(lesson, indent=2))
        scenes = lesson.get("scenes", [])
        total_dur = sum(s.get("duration", 8) for s in scenes)
        print(f"Lesson: {lesson.get('title')} | {len(scenes)} scenes | {total_dur}s")

        update("running", 20, f"Script ready — {len(scenes)} scenes, ~{total_dur}s video. Generating voice...")
        full_narration, timing, _ = build_narration_with_timing(lesson)
        audio_path = job_dir / "narration.mp3"
        generate_voice(full_narration, audio_path)

        update("running", 40, "Building animation code...")
        manim_code = build_manim_script(lesson)
        (job_dir / "manim_script.py").write_text(manim_code)

        update("running", 50, f"Rendering {len(scenes)}-scene animation (2-4 mins)...")
        video_path = generate_animation(manim_code, job_dir)

        if not video_path:
            update("running", 65, "Manim failed — building fallback video...")
            video_path = create_fallback_video(lesson, job_dir, audio_path)

        if not video_path:
            update("error", 0, "Rendering failed. Try a simpler question.")
            return

        update("running", 82, "Syncing audio to video...")
        final_path = job_dir / "final.mp4"
        sync_video_to_audio(video_path, audio_path, final_path, total_dur)

        jobs[job_id]["video_url"]   = f"/video/{job_id}"
        jobs[job_id]["lesson"]      = lesson
        jobs[job_id]["timing"]      = timing
        jobs[job_id]["total_duration"] = total_dur
        update("done", 100, f"Video ready! ({total_dur}s, {len(scenes)} scenes)")

    except json.JSONDecodeError as e:
        update("error", 0, f"AI parse error: {e}")
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
    question = data.get("question","").strip()
    audience = data.get("audience","student")
    if not question:
        return jsonify({"error": "Question required"}), 400
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id, "question": question, "audience": audience,
        "status": "queued", "progress": 0, "message": "Queued...",
        "video_url": None, "lesson": None, "created_at": time.time()
    }
    t = threading.Thread(target=run_pipeline, args=(job_id, question, audience))
    t.daemon = True; t.start()
    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job: return jsonify({"error": "Not found"}), 404
    return jsonify(job)

@app.route("/video/<job_id>")
def serve_video(job_id):
    p = OUTPUT_DIR / job_id / "final.mp4"
    if not p.exists(): return jsonify({"error": "Not found"}), 404
    return send_file(str(p), mimetype="video/mp4")

@app.route("/lesson/<job_id>")
def get_lesson(job_id):
    p = OUTPUT_DIR / job_id / "lesson.json"
    if not p.exists(): return jsonify({"error": "Not found"}), 404
    return jsonify(json.loads(p.read_text()))

if __name__ == "__main__":
    print("=" * 60)
    print("  EduVision AI v2 — http://localhost:8080")
    print("=" * 60)
    app.run(debug=True, port=8080, host="0.0.0.0", use_reloader=False, threaded=True)