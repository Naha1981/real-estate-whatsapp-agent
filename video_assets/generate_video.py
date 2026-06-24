#!/usr/bin/env python3
"""
iGosa Promo Video Generator
Produces a 90-second promotional video using FFmpeg.
Uses text-based animation, brand colors, and professional typography.
No external API keys needed — pure FFmpeg composition.
"""
import subprocess
import os
import math

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(WORK_DIR, "igosa_promo.mp4")
ASSETS = os.path.join(WORK_DIR, "video_assets")

# Video settings
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_DURATION = 90  # seconds

# Brand colors (hex without #)
GREEN = "128C7E"
DARK_GREEN = "075E54"
WHITE = "FFFFFF"
AMBER = "F5A623"
DARK_BG = "0D1117"
LIGHT_BG = "F0F2F5"
RED_ACCENT = "E74C3C"
GOLD = "F4C430"
SA_GREEN = "007A4D"
SA_RED = "DE3831"
SA_BLUE = "002395"
SA_YELLOW = "FFB612"
SA_BLACK = "000000"

def create_color_frame(color, filename, duration=1):
    """Create a solid color frame as MP4 clip."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=0x{color}:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", filename
    ]
    subprocess.run(cmd, capture_output=True)
    return filename

def create_text_clip(text, filename, duration=3, font_size=60, color=WHITE, 
                     bg_color=DARK_BG, position="center", subtitle="", subtitle_size=40):
    """Create a text overlay clip with optional subtitle."""
    # Escape special characters for drawtext
    text_escaped = text.replace("'", "'\\''").replace(":", "\\:").replace(",", "\\,")
    
    color_hex = f"0x{color}"
    bg_hex = f"0x{bg_color}"
    
    if position == "center":
        x = "(w-text_w)/2"
        y = "(h-text_h)/2"
    elif position == "top":
        x = "(w-text_w)/2"
        y = "h*0.15"
    elif position == "bottom":
        x = "(w-text_w)/2"
        y = "h*0.75"
    elif position == "center_left":
        x = "w*0.15"
        y = "(h-text_h)/2"
    
    # Create base with background + text
    vf_parts = [
        f"drawtext=text='{text_escaped}':fontcolor={color_hex}:fontsize={font_size}:"
        f"x={x}:y={y}:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"box=1:boxcolor=0x000000@0.0:boxborderw=0"
    ]
    
    if subtitle:
        sub_escaped = subtitle.replace("'", "'\\''")
        vf_parts.append(
            f"drawtext=text='{sub_escaped}':fontcolor=0x{AMBER}:fontsize={subtitle_size}:"
            f"x=(w-text_w)/2:y=h*0.78:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )
    
    vf_filter = ",".join(vf_parts)
    
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={bg_hex}:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-vf", vf_filter,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", filename
    ]
    subprocess.run(cmd, capture_output=True)
    return filename

def create_multi_text_clip(lines, filename, duration=3, bg_color=DARK_BG):
    """Create a clip with multiple lines of text stacked."""
    vf_parts = []
    line_height = 80
    start_y = HEIGHT * 0.15
    
    for i, (text, size, color) in enumerate(lines):
        text_escaped = text.replace("'", "'\\''")
        y_pos = start_y + (i * line_height)
        vf_parts.append(
            f"drawtext=text='{text_escaped}':fontcolor=0x{color}:fontsize={size}:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        )
    
    vf_filter = ",".join(vf_parts)
    
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=0x{bg_color}:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-vf", vf_filter,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", filename
    ]
    subprocess.run(cmd, capture_output=True)
    return filename

def add_fade_in(clip_path, output_path, duration=0.5):
    """Add fade-in effect to a clip."""
    cmd = [
        "ffmpeg", "-y", "-i", clip_path,
        "-vf", f"fade=in:0:{int(duration*FPS)}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path

def add_fade_out(clip_path, duration=0.5):
    """Add fade-out to clip (in-place)."""
    import tempfile
    tmp = tempfile.mktemp(suffix=".mp4")
    cmd = [
        "ffmpeg", "-y", "-i", clip_path,
        "-vf", f"fade=out:{int(duration*FPS)}:{(3-int(duration))*FPS}:alpha=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", tmp
    ]
    subprocess.run(cmd, capture_output=True)
    os.replace(tmp, clip_path)
    return clip_path

def create_silent_audio(duration):
    """Create silent audio track."""
    path = os.path.join(ASSETS, f"silence_{duration}.aac")
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:a", "aac", path
    ]
    subprocess.run(cmd, capture_output=True)
    return path

def concat_clips(clip_list, output_path, durations=None):
    """Concatenate multiple MP4 clips with optional crossfade."""
    # Simple concat
    concat_file = os.path.join(ASSETS, "concat_list.txt")
    with open(concat_file, "w") as f:
        for clip in clip_list:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path

def create_scene_transition(from_clip, to_clip, output_path, duration=0.5):
    """Create a smooth crossfade transition between two clips."""
    cmd = [
        "ffmpeg", "-y",
        "-i", from_clip,
        "-i", to_clip,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset=2.5[outv]",
        "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


# ============================================================
# VIDEO GENERATION
# ============================================================

print("🎬 iGosa Promo Video Generator")
print("=" * 50)

# Create title card clip with logo-style text
print("\n📺 Scene 1: Title Card")
create_multi_text_clip([
    ("iGosa", 120, GREEN),
    ("Your Phone. Your Business. 24/7.", 48, WHITE),
    ("", 30, WHITE),
    ("WhatsApp AI for South African Estate Agents", 36, AMBER),
], os.path.join(ASSETS, "s01_title.mp4"), 4, DARK_BG)

# Scene 2: The Problem
print("📺 Scene 2: The Problem")
create_multi_text_clip([
    ("47 unread WhatsApp messages.", 64, RED_ACCENT),
    ("3 buyers waiting for a reply.", 48, WHITE),
    ("1 deal slipping away.", 40, AMBER),
], os.path.join(ASSETS, "s02_problem.mp4"), 4, DARK_BG)

# Scene 3: The Solution
print("📺 Scene 3: The Solution")
create_multi_text_clip([
    ("Introducing iGosa", 80, GREEN),
    ("The AI assistant that lives in your WhatsApp.", 44, WHITE),
    ("", 30, WHITE),
    ("Replies in 2 seconds. 24 hours a day. 7 days a week.", 40, AMBER),
], os.path.join(ASSETS, "s03_solution.mp4"), 5, DARK_BG)

# Scene 4: WhatsApp Demo
print("📺 Scene 4: WhatsApp Demo")
create_multi_text_clip([
    ('Buyer: "Sawubona, ngifuna i-house eSoweto"', 44, WHITE),
    ("", 20, WHITE),
    ('iGosa: "Yebo! 🏠 I found 3 options in Soweto"', 44, GREEN),
    ("", 20, WHITE),
    ('• Pimville — 3 bed, R450K', 36, WHITE),
    ('• Diepkloof — 3 bed, R480K', 36, WHITE),
    ('• Meadowlands — 3 bed, R420K', 36, WHITE),
], os.path.join(ASSETS, "s04_demo.mp4"), 8, DARK_BG)

# Scene 5: SA Features
print("📺 Scene 5: SA Features")
create_multi_text_clip([
    ("Built for South Africa", 72, SA_GREEN),
    ("", 20, WHITE),
    ("🇿🇦 Knows RDP rules & FLISP subsidies", 40, WHITE),
    ("🏠 Understands township property values", 40, WHITE),
    ("🗣️ Speaks Zulu • Sotho • English", 40, WHITE),
    ("📱 Works entirely in WhatsApp", 40, WHITE),
], os.path.join(ASSETS, "s05_features.mp4"), 7, DARK_BG)

# Scene 6: Pipeline
print("📺 Scene 6: Pipeline Dashboard")
create_multi_text_clip([
    ("Your Business. Under Control.", 64, GREEN),
    ("", 20, WHITE),
    ("Lead → Viewing → Offer → Accepted → Closed 🎉", 42, AMBER),
    ("", 20, WHITE),
    ("12 leads this week  •  3 viewings booked", 36, WHITE),
    ("Pipeline: R2.1M  •  Commission: R147K", 36, WHITE),
], os.path.join(ASSETS, "s06_pipeline.mp4"), 7, DARK_BG)

# Scene 7: How to Share
print("📺 Scene 7: Distribution")
create_multi_text_clip([
    ("Share iGosa Everywhere", 64, GREEN),
    ("", 15, WHITE),
    ("📱 WhatsApp number on business cards & flyers", 36, WHITE),
    ("📲 Click-to-chat links on Facebook & Instagram", 36, WHITE),
    ("🏷️ QR codes on 'For Sale' boards", 36, WHITE),
    ("🌐 Your number on Property24 & Private Property", 36, WHITE),
], os.path.join(ASSETS, "s07_distribution.mp4"), 7, DARK_BG)

# Scene 8: Pricing
print("📺 Scene 8: Pricing")
create_multi_text_clip([
    ("Start Today", 72, GREEN),
    ("", 20, WHITE),
    ("Starter  R499/mo  •  Pro  R999/mo", 48, AMBER),
    ("Enterprise  R1,999/mo", 44, WHITE),
    ("", 20, WHITE),
    ("Less than half a commission pays for a year.", 36, WHITE),
], os.path.join(ASSETS, "s08_pricing.mp4"), 6, DARK_BG)

# Scene 9: Call to Action
print("📺 Scene 9: Call to Action")
create_multi_text_clip([
    ("iGosa", 100, GREEN),
    ("Your Phone. Your Business. 24/7.", 52, WHITE),
    ("", 30, WHITE),
    ("wa.me/27612980377", 48, AMBER),
    ("", 20, WHITE),
    ("Start your free trial today.", 36, WHITE),
], os.path.join(ASSETS, "s09_cta.mp4"), 6, DARK_BG)

# Build background music with FFmpeg (simple tone sequence)
print("\n🎵 Creating background audio...")
# Generate a simple rhythmic audio track
audio_cmd = [
    "ffmpeg", "-y", "-f", "lavfi",
    "-i", f"sine=frequency=440:duration={TOTAL_DURATION}",
    "-af", "volume=0.15",
    "-c:a", "aac", os.path.join(ASSETS, "bg_music.aac")
]
subprocess.run(audio_cmd, capture_output=True)

# Concatenate all scenes
print("\n🔗 Assembling video...")
clips = [
    os.path.join(ASSETS, "s01_title.mp4"),
    os.path.join(ASSETS, "s02_problem.mp4"),
    os.path.join(ASSETS, "s03_solution.mp4"),
    os.path.join(ASSETS, "s04_demo.mp4"),
    os.path.join(ASSETS, "s05_features.mp4"),
    os.path.join(ASSETS, "s06_pipeline.mp4"),
    os.path.join(ASSETS, "s07_distribution.mp4"),
    os.path.join(ASSETS, "s08_pricing.mp4"),
    os.path.join(ASSETS, "s09_cta.mp4"),
]

# Create concat file
concat_file = os.path.join(ASSETS, "concat.txt")
with open(concat_file, "w") as f:
    for clip in clips:
        if os.path.exists(clip):
            f.write(f"file '{os.path.abspath(clip)}'\n")

# Check all clips exist
for clip in clips:
    if not os.path.exists(clip):
        print(f"❌ Missing: {clip}")

# Concat with xfade transitions
filter_parts = []
for i in range(len(clips)):
    filter_parts.append(f"[{i}:v]")

# Build crossfade filter chain  
xfade_chain = ""
current = "0v"
for i in range(len(clips) - 1):
    next_v = f"{i+1}v"
    out = f"xfade{i}"
    offset = 2.5  # crossfade offset
    xfade_chain += f"[{current}][{next_v}]xfade=transition=fade:duration=0.5:offset={offset}[{out}];"
    current = out

# Simple concat approach (reliable)
concat_cmd = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", concat_file,
    "-i", os.path.join(ASSETS, "bg_music.aac"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-shortest",
    "-crf", "20",
    "-movflags", "+faststart",
    OUTPUT
]

result = subprocess.run(concat_cmd, capture_output=True, text=True)
if result.returncode == 0:
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"\n✅ Video generated: {OUTPUT}")
    print(f"📁 Size: {size_mb:.1f} MB")
    print(f"⏱️  Duration: {TOTAL_DURATION}s")
    print(f"📐 Resolution: {WIDTH}x{HEIGHT}")
else:
    print(f"❌ FFmpeg error:\n{result.stderr[-500:]}")
