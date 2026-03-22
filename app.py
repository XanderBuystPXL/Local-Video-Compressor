import os
import subprocess
import json
import uuid
import math
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

app = FastAPI()

# Setup directories
TEMP_DIR = Path("/tmp/video_compressor")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_video_info(file_path: str):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,bit_rate:format=duration,size",
        "-of", "json", file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ffprobe error: {e.stderr}")
        return None

def cleanup_files(files: list[str]):
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Cleanup error for {file}: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/compress")
async def compress_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_size: float = Form(10.0)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    base_name = Path(file.filename).stem
    job_id = str(uuid.uuid4())
    input_path = TEMP_DIR / f"{job_id}_input{file_ext}"
    output_path = TEMP_DIR / f"{job_id}_output.mp4"
    pass_log_prefix = str(TEMP_DIR / f"{job_id}_passlog")

    try:
        # Save file
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
        
        original_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        print(f"Original size: {original_size_mb:.2f} MB")
        
        if target_size >= original_size_mb:
            cleanup_files([str(input_path)])
            raise HTTPException(status_code=400, detail="Target size must be strictly smaller than original file size.")

        info = get_video_info(str(input_path))
        if not info or 'format' not in info or 'duration' not in info['format']:
            cleanup_files([str(input_path)])
            raise HTTPException(status_code=400, detail="Could not read video information.")

        duration = float(info['format']['duration'])
        
        # Audio bitrate assumption
        audio_bitrate_k = 128
        
        # Calculate video bitrate (aim for 95% of target to allow for muxing overhead)
        safe_target_mb = target_size * 0.95
        total_bitrate_k = (safe_target_mb * 8192) / duration
        video_bitrate_k = max(10, int(total_bitrate_k - audio_bitrate_k))

        scale_filter = ""
        if video_bitrate_k < 500:
            scale_filter = "scale=-2:480"
        elif video_bitrate_k < 1500:
            scale_filter = "scale=-2:720"
        elif video_bitrate_k < 3000:
            scale_filter = "scale=-2:1080"
            
        common_ffmpeg_args = [
            "-i", str(input_path),
            "-b:v", f"{video_bitrate_k}k",
            "-maxrate", f"{int(video_bitrate_k * 1.5)}k",
            "-bufsize", f"{video_bitrate_k * 2}k",
            "-passlogfile", pass_log_prefix
        ]
        
        if scale_filter:
            common_ffmpeg_args.extend(["-vf", scale_filter])
            
        # Pass 1
        pass1_cmd = ["ffmpeg", "-y"] + common_ffmpeg_args + ["-c:v", "libx264", "-pass", "1", "-an", "-f", "mp4", os.devnull]
        subprocess.run(pass1_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Pass 2
        pass2_cmd = ["ffmpeg", "-y"] + common_ffmpeg_args + ["-c:v", "libx264", "-pass", "2", "-c:a", "aac", "-b:a", f"{audio_bitrate_k}k", str(output_path)]
        subprocess.run(pass2_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return_filename = f"{base_name}_compressed.mp4"
        
        log_files = [f"{pass_log_prefix}-0.log", f"{pass_log_prefix}-0.log.mbtree"]
        background_tasks.add_task(cleanup_files, [str(input_path), str(output_path)] + log_files)
        
        return FileResponse(
            path=str(output_path), 
            filename=return_filename,
            media_type="video/mp4"
        )
        
    except subprocess.CalledProcessError as e:
        cleanup_files([str(input_path), str(output_path), f"{pass_log_prefix}-0.log", f"{pass_log_prefix}-0.log.mbtree"])
        print(f"FFmpeg error")
        raise HTTPException(status_code=500, detail="Compression failed during FFmpeg execution.")
    except Exception as e:
        cleanup_files([str(input_path), str(output_path)])
        print(f"Error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
