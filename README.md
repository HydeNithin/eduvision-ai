<div align="center">

# 🎬 EduVision AI

### Turn any question into an educational video — instantly.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?style=flat-square&logo=flask&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4-orange?style=flat-square)
![Manim](https://img.shields.io/badge/Manim-0.20-purple?style=flat-square)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

<br/>

**[Live Demo](#demo) · [Quick Start](#quick-start) · [How It Works](#how-it-works) · [Roadmap](#roadmap)**

<br/>

> *"ChatGPT gives you text. YouTube gives you someone else's explanation. Coursera charges $500. EduVision gives you a personalized animated video of exactly what YOU asked — in minutes."*

</div>

---

## 🎯 What Is This?

**EduVision AI** is an open-source AI pipeline that converts any natural language question into a fully animated educational video — complete with voice narration, synchronized animations, and structured lesson content.

Ask it anything:

```
"Explain how Python loops work to a beginner"
"Why is the sky blue? Explain to a 7 year old"
"What is machine learning and why does it matter?"
```

And get back a **30-60 second animated video** with:
- 📝 AI-written lesson script (Claude Sonnet)
- 🎙️ Natural teacher voice narration (ElevenLabs)
- 🎨 Animated visuals synchronized to the narration (Manim)
- 🎬 Final MP4 ready to watch, download, and share

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Lesson Planning** | Claude writes a structured 8–12 scene lesson with timed narration per scene |
| 🎙️ **Voice Narration** | ElevenLabs generates natural teacher-quality voice |
| 🎨 **Animated Visuals** | Manim renders smooth mathematical/conceptual animations |
| 🔄 **Audio-Video Sync** | ffprobe measures durations, ffmpeg adjusts video speed to match audio |
| 👥 **3 Audience Modes** | Child (6–10), Student (high school/uni), Professional |
| 📱 **Real-time Progress** | Live progress tracking with step-by-step status updates |
| 💾 **Download Videos** | Every generated video is downloadable as MP4 |
| 🔄 **Fallback Renderer** | If Manim fails, ffmpeg fallback ensures a video always generates |

---

## 🏗️ Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────┐
│              Flask Backend (app.py)              │
│                                                 │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐  │
│  │  Claude  │    │ElevenLabs │    │  Manim   │  │
│  │Sonnet API│    │  TTS API  │    │ Renderer │  │
│  └────┬─────┘    └─────┬─────┘    └────┬─────┘  │
│       │                │               │        │
│  Lesson script    Voice MP3      Animation MP4  │
│  + Manim code                                   │
│       │                │               │        │
│       └────────────────┴───────────────┘        │
│                        │                        │
│                   ffmpeg merge                  │
│                  (audio-synced)                 │
└─────────────────────────┬───────────────────────┘
                          │
                          ▼
                   Final Video MP4
```

**Tech Stack:**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI Brain | Claude Sonnet (Anthropic) | Lesson script + animation code generation |
| Voice | ElevenLabs | Natural teacher voice narration |
| Animation | Manim (ManimCE) | Mathematical/educational animations |
| Video | ffmpeg | Audio-video merge + sync |
| Backend | Flask + Python | API server + pipeline orchestration |
| Frontend | Vanilla HTML/CSS/JS | Beautiful dark-themed UI |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11
- ffmpeg
- Cairo + Pango (for Manim)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/eduvision-ai.git
cd eduvision-ai
```

### 2. Install system dependencies

```bash
# macOS
brew install ffmpeg cairo pango pkg-config

# Ubuntu/Debian
sudo apt install ffmpeg libcairo2-dev libpango1.0-dev pkg-config
```

### 3. Create virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
```

### 4. Install Python packages

```bash
pip install -r requirements.txt
```

### 5. Get your API keys (both free tiers)

| Service | Free Tier | Sign Up |
|---------|-----------|---------|
| Anthropic (Claude) | $5 free credit | [console.anthropic.com](https://console.anthropic.com) |
| ElevenLabs | 10,000 chars/month | [elevenlabs.io](https://elevenlabs.io) |

### 6. Set environment variables

```bash
export ANTHROPIC_API_KEY=your-claude-key-here
export ELEVENLABS_API_KEY=your-elevenlabs-key-here
```

### 7. Run

```bash
python app.py
```

Open [http://localhost:8080](http://localhost:8080) 🎉

---

## 📁 Project Structure

```
eduvision-ai/
│
├── app.py                  # Flask backend — full AI pipeline
├── requirements.txt        # Python dependencies
├── README.md               # You are here
│
├── static/
│   └── index.html          # Frontend — dark-themed UI
│
└── outputs/                # Generated videos (auto-created)
    └── {job-id}/
        ├── lesson.json     # AI-generated lesson plan
        ├── scene.py        # Manim animation script
        ├── narration.mp3   # ElevenLabs voice audio
        └── final.mp4       # Final merged video
```

---

## 💡 Example Prompts

**For Children 🧒**
```
Why is the sky blue?
How do rainbows form?
What is gravity?
Why do we dream?
```

**For Students 🎓**
```
Explain how Python for loops work
What is the Pythagorean theorem?
How does the internet work?
Explain recursion in programming
What is photosynthesis?
```

**For Professionals 💼**
```
What is machine learning?
Explain REST APIs simply
What is compound interest?
How does blockchain work?
```

---

## 💰 Cost Per Video

| Service | Cost per video |
|---------|---------------|
| Claude API | ~$0.03–0.05 |
| ElevenLabs | ~150 chars from 10k free monthly limit |
| Manim | FREE (runs locally) |
| ffmpeg | FREE |
| **Total** | **~$0.03–0.05** |

---

## 🗺️ Roadmap

- [x] Claude AI lesson script generation
- [x] ElevenLabs voice narration
- [x] Manim animation rendering
- [x] Audio-video sync engine
- [x] 3 audience modes (Child / Student / Professional)
- [x] Real-time progress tracking
- [x] Fallback video renderer
- [ ] HeyGen AI avatar teacher (talking head)
- [ ] Subtitle/caption overlay
- [ ] Multi-language support
- [ ] User accounts + video history
- [ ] YouTube auto-upload
- [ ] Mobile app (React Native)
- [ ] API access for developers

---

## 🤝 Contributing

Contributions are welcome! This project is actively developed and I'd love help with:

- Improving Manim animation quality
- Adding HeyGen avatar integration
- Building a better frontend
- Adding more audience modes
- Fixing bugs and edge cases

```bash
# Fork the repo
# Create your branch
git checkout -b feature/your-feature-name

# Commit your changes
git commit -m "Add: your feature description"

# Push and open a PR
git push origin feature/your-feature-name
```

---

## 👤 Built By

**Hyde Nithin Sumithra Owk**

Software Engineer | MS Information Technology (4.0 GPA) | AI Builder

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/nithinoh)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat-square&logo=github)](https://github.com/YOUR_USERNAME)

> Built this as a solo developer in a few weeks using free API tiers.
> Looking for collaborators, mentors, and feedback.
> Open to full-time roles in AI/ML engineering.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**If this project helped you or inspired you, please ⭐ star the repo.**

It helps more people find it and motivates continued development.

</div>