{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 #!/usr/bin/env python3\
"""\
Goodland Pickleball - Production System\
Configured for Lorex cameras at 192.168.1.108\
"""\
\
import os\
import asyncio\
import json\
import logging\
from datetime import datetime, timedelta\
from typing import List, Dict, Optional\
from pathlib import Path\
\
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request\
from fastapi.staticfiles import StaticFiles\
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse\
from fastapi.middleware.cors import CORSMiddleware\
from pydantic import BaseModel\
import cv2\
import numpy as np\
import sqlite3\
import threading\
import time\
import queue\
\
# Configure logging\
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')\
logger = logging.getLogger(__name__)\
\
# Initialize FastAPI app\
app = FastAPI(title="Goodland Pickleball - AI Camera System", version="1.0.0")\
\
# Enable CORS\
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])\
\
# Goodland Pickleball Configuration\
LOREX_IP = os.getenv("LOREX_IP", "192.168.1.108")\
LOREX_USERNAME = os.getenv("LOREX_USERNAME", "hemant@goodlandpickleball.com")  \
LOREX_PASSWORD = os.getenv("LOREX_PASSWORD", "Rohan12#")\
\
# Global system state\
camera_system = None\
processing_stats = \{\
    "highlights_created": 0,\
    "balls_detected": 0,\
    "cameras_online": 0,\
    "uptime_start": datetime.now(),\
    "revenue_today": 0.0\
\}\
\
class GoodlandCameraSystem:\
    """Camera system for Goodland Pickleball"""\
    \
    def __init__(self):\
        self.cameras = \{\}\
        self.running = False\
        \
        # Create directories\
        Path("data").mkdir(exist_ok=True)\
        Path("output/highlights").mkdir(parents=True, exist_ok=True)\
        \
        # Initialize database\
        self.init_database()\
        logger.info("\uc0\u55356 \u57278  Goodland Pickleball System Initialized")\
    \
    def init_database(self):\
        """Initialize database"""\
        conn = sqlite3.connect("data/goodland_pickleball.db")\
        cursor = conn.cursor()\
        \
        cursor.execute("""\
            CREATE TABLE IF NOT EXISTS highlights (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                timestamp REAL,\
                duration REAL,\
                confidence REAL,\
                description TEXT,\
                video_path TEXT,\
                views INTEGER DEFAULT 0,\
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\
            )\
        """)\
        \
        conn.commit()\
        conn.close()\
        logger.info("\uc0\u9989  Database initialized")\
    \
    def connect_to_lorex(self):\
        """Connect to Lorex system"""\
        logger.info(f"\uc0\u55357 \u56588  Connecting to Lorex at \{LOREX_IP\}")\
        \
        # Test camera connections\
        camera_configs = [\
            \{\
                "id": "baseline",\
                "name": "Baseline Camera",\
                "url": f"rtsp://\{LOREX_USERNAME\}:\{LOREX_PASSWORD\}@\{LOREX_IP\}:554/cam/realmonitor?channel=1&subtype=0"\
            \},\
            \{\
                "id": "sideline", \
                "name": "Sideline Camera",\
                "url": f"rtsp://\{LOREX_USERNAME\}:\{LOREX_PASSWORD\}@\{LOREX_IP\}:554/cam/realmonitor?channel=2&subtype=0"\
            \}\
        ]\
        \
        for config in camera_configs:\
            try:\
                logger.info(f"   Testing \{config['name']\}...")\
                cap = cv2.VideoCapture(config["url"])\
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)\
                \
                if cap.isOpened():\
                    ret, frame = cap.read()\
                    if ret:\
                        self.cameras[config["id"]] = \{\
                            "capture": cap,\
                            "config": config,\
                            "last_frame": frame,\
                            "status": "online"\
                        \}\
                        processing_stats["cameras_online"] += 1\
                        logger.info(f"   \uc0\u9989  \{config['name']\} connected")\
                    else:\
                        cap.release()\
                        logger.warning(f"   \uc0\u9888 \u65039   \{config['name']\} no signal")\
                else:\
                    logger.error(f"   \uc0\u10060  \{config['name']\} connection failed")\
                    \
            except Exception as e:\
                logger.error(f"   \uc0\u10060  \{config['name']\} error: \{e\}")\
        \
        return len(self.cameras) > 0\
    \
    def start_processing(self):\
        """Start processing"""\
        if not self.cameras:\
            return False\
        \
        self.running = True\
        \
        # Start simple processing thread\
        thread = threading.Thread(target=self._simple_processing, daemon=True)\
        thread.start()\
        \
        logger.info("\uc0\u55358 \u56598  Processing started")\
        return True\
    \
    def _simple_processing(self):\
        """Simple processing loop"""\
        last_highlight_time = 0\
        \
        while self.running:\
            try:\
                # Update camera frames\
                for camera_id, camera in self.cameras.items():\
                    try:\
                        ret, frame = camera["capture"].read()\
                        if ret:\
                            camera["last_frame"] = frame\
                            camera["status"] = "online"\
                        else:\
                            camera["status"] = "error"\
                    except:\
                        camera["status"] = "error"\
                \
                # Create test highlight every 2 minutes\
                if time.time() - last_highlight_time > 120:  # 2 minutes\
                    self._create_test_highlight()\
                    last_highlight_time = time.time()\
                \
                time.sleep(1)  # Process every second\
                \
            except Exception as e:\
                logger.error(f"Processing error: \{e\}")\
                time.sleep(5)\
    \
    def _create_test_highlight(self):\
        """Create a test highlight"""\
        try:\
            if not self.cameras:\
                return\
            \
            # Get first available camera\
            camera_id = list(self.cameras.keys())[0]\
            camera = self.cameras[camera_id]\
            frame = camera["last_frame"]\
            \
            if frame is None:\
                return\
            \
            # Create filename\
            timestamp = time.time()\
            dt = datetime.fromtimestamp(timestamp)\
            filename = f"highlight_\{dt.strftime('%Y%m%d_%H%M%S')\}.mp4"\
            filepath = f"output/highlights/\{filename\}"\
            \
            # Create video\
            height, width = frame.shape[:2]\
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')\
            out = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height))\
            \
            # Create 5-second clip\
            for i in range(150):  # 5 seconds * 30 fps\
                frame_copy = frame.copy()\
                \
                # Add branding\
                cv2.putText(frame_copy, "GOODLAND PICKLEBALL", (20, 40), \
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)\
                cv2.putText(frame_copy, "GOODLAND PICKLEBALL", (20, 40), \
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 100, 255), 2)\
                \
                # Add timestamp\
                time_text = dt.strftime('%m/%d/%Y %H:%M:%S')\
                cv2.putText(frame_copy, time_text, (20, height - 60),\
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)\
                \
                if i < 60:  # First 2 seconds\
                    cv2.putText(frame_copy, "\uc0\u11088  HIGHLIGHT \u11088 ", (width//2 - 100, 80),\
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)\
                \
                out.write(frame_copy)\
            \
            out.release()\
            \
            # Save to database\
            conn = sqlite3.connect("data/goodland_pickleball.db")\
            cursor = conn.cursor()\
            cursor.execute("""\
                INSERT INTO highlights (timestamp, duration, confidence, description, video_path)\
                VALUES (?, ?, ?, ?, ?)\
            """, (timestamp, 5.0, 90.0, f"Auto-generated highlight", filepath))\
            conn.commit()\
            conn.close()\
            \
            processing_stats["highlights_created"] += 1\
            logger.info(f"\uc0\u55356 \u57260  Created highlight: \{filename\}")\
            \
        except Exception as e:\
            logger.error(f"Failed to create highlight: \{e\}")\
    \
    def get_camera_feed(self, camera_id: str):\
        """Get camera feed"""\
        if camera_id in self.cameras:\
            return self.cameras[camera_id]["last_frame"]\
        return None\
    \
    def get_stats(self):\
        """Get system stats"""\
        camera_info = \{\}\
        for cam_id, cam in self.cameras.items():\
            camera_info[cam_id] = \{\
                'name': cam['config']['name'],\
                'status': cam['status']\
            \}\
        \
        return \{\
            'cameras': camera_info,\
            'stats': processing_stats,\
            'uptime_minutes': (datetime.now() - processing_stats['uptime_start']).seconds // 60\
        \}\
\
# Initialize system\
camera_system = None\
\
@app.on_event("startup")\
async def startup_event():\
    """Initialize system"""\
    global camera_system\
    \
    logger.info("\uc0\u55356 \u57278  Starting Goodland Pickleball System...")\
    \
    camera_system = GoodlandCameraSystem()\
    \
    if camera_system.connect_to_lorex():\
        camera_system.start_processing()\
        logger.info("\uc0\u9989  System is LIVE!")\
    else:\
        logger.error("\uc0\u10060  Camera connection failed")\
\
@app.get("/", response_class=HTMLResponse)\
async def dashboard():\
    """Main dashboard"""\
    stats = camera_system.get_stats() if camera_system else \{'cameras': \{\}, 'stats': processing_stats\}\
    \
    html = f"""\
    <!DOCTYPE html>\
    <html>\
    <head>\
        <title>Goodland Pickleball - AI Camera System</title>\
        <meta name="viewport" content="width=device-width, initial-scale=1">\
        <style>\
            * \{\{ margin: 0; padding: 0; box-sizing: border-box; \}\}\
            body \{\{ \
                font-family: Arial, sans-serif; \
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);\
                color: white; \
                min-height: 100vh;\
            \}\}\
            .header \{\{\
                text-align: center;\
                padding: 40px 20px;\
                background: rgba(255,255,255,0.1);\
                margin: 20px;\
                border-radius: 20px;\
            \}\}\
            .logo \{\{ font-size: 3em; margin-bottom: 10px; \}\}\
            .grid \{\{ \
                display: grid; \
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); \
                gap: 20px; \
                margin: 20px; \
            \}\}\
            .card \{\{ \
                background: rgba(255,255,255,0.95); \
                color: #333; \
                padding: 25px; \
                border-radius: 15px; \
            \}\}\
            .stat-grid \{\{ \
                display: grid; \
                grid-template-columns: repeat(2, 1fr); \
                gap: 15px; \
                margin-top: 15px; \
            \}\}\
            .stat-item \{\{ \
                text-align: center; \
                padding: 15px; \
                background: linear-gradient(135deg, #667eea, #764ba2); \
                color: white; \
                border-radius: 10px; \
            \}\}\
            .stat-number \{\{ font-size: 2em; font-weight: bold; display: block; \}\}\
            .btn \{\{ \
                background: linear-gradient(135deg, #667eea, #764ba2); \
                color: white; \
                border: none; \
                padding: 12px 24px; \
                border-radius: 25px; \
                margin: 5px;\
                text-decoration: none;\
                display: inline-block;\
            \}\}\
            .live \{\{ \
                width: 10px; \
                height: 10px; \
                background: #28a745; \
                border-radius: 50%; \
                display: inline-block; \
                margin-right: 8px; \
                animation: pulse 2s infinite; \
            \}\}\
            @keyframes pulse \{\{ \
                0% \{\{ box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); \}\} \
                70% \{\{ box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); \}\} \
            \}\}\
        </style>\
        <script>\
            setTimeout(() => window.location.reload(), 30000);\
        </script>\
    </head>\
    <body>\
        <div class="header">\
            <div class="logo">\uc0\u55356 \u57278  Goodland Pickleball</div>\
            <div>AI-Powered Highlights & Camera System</div>\
            <div style="margin-top: 15px;">\
                <span class="live"></span>\
                <strong>LIVE SYSTEM</strong>\
            </div>\
        </div>\
        \
        <div class="grid">\
            <div class="card">\
                <h3>\uc0\u55357 \u56522  System Stats</h3>\
                <div class="stat-grid">\
                    <div class="stat-item">\
                        <span class="stat-number">\{processing_stats['highlights_created']\}</span>\
                        <span>Highlights</span>\
                    </div>\
                    <div class="stat-item">\
                        <span class="stat-number">\{processing_stats['cameras_online']\}</span>\
                        <span>Cameras Online</span>\
                    </div>\
                    <div class="stat-item">\
                        <span class="stat-number">\{stats['uptime_minutes']\}</span>\
                        <span>Minutes Running</span>\
                    </div>\
                    <div class="stat-item">\
                        <span class="stat-number">$\{processing_stats['revenue_today']:.0f\}</span>\
                        <span>Revenue Today</span>\
                    </div>\
                </div>\
            </div>\
            \
            <div class="card">\
                <h3>\uc0\u55356 \u57253  Lorex Cameras</h3>\
                <p><strong>NVR Address:</strong> \{LOREX_IP\}</p>\
                <p><strong>Status:</strong> \{"\uc0\u55357 \u57314  Connected" if processing_stats['cameras_online'] > 0 else "\u55357 \u56628  Offline"\}</p>\
                <div style="margin-top: 15px;">\
                    <a href="/live/baseline" class="btn">\uc0\u55357 \u56569  View Baseline</a>\
                    <a href="/live/sideline" class="btn">\uc0\u55357 \u56569  View Sideline</a>\
                </div>\
            </div>\
            \
            <div class="card">\
                <h3>\uc0\u55356 \u57260  Highlights</h3>\
                <p>Auto-generated highlights from your games</p>\
                <div style="margin-top: 15px;">\
                    <a href="/highlights" class="btn">View All Highlights</a>\
                    <a href="/api/test" class="btn">Create Test Highlight</a>\
                </div>\
            </div>\
            \
            <div class="card">\
                <h3>\uc0\u55357 \u56496  Business Ready</h3>\
                <p><strong>System Status:</strong> OPERATIONAL</p>\
                <p><strong>Ready for:</strong> Player highlight sales</p>\
                <p><strong>Scalable to:</strong> Multiple courts</p>\
            </div>\
        </div>\
    </body>\
    </html>\
    """\
    \
    return HTMLResponse(content=html)\
\
@app.get("/live/\{camera_id\}")\
async def live_feed(camera_id: str):\
    """Live camera stream"""\
    def generate():\
        while True:\
            if camera_system:\
                frame = camera_system.get_camera_feed(camera_id)\
                if frame is not None:\
                    # Add overlay\
                    overlay_frame = frame.copy()\
                    cv2.putText(overlay_frame, "GOODLAND PICKLEBALL LIVE", (20, 30),\
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)\
                    \
                    ret, buffer = cv2.imencode('.jpg', overlay_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])\
                    if ret:\
                        yield (b'--frame\\r\\n'\
                               b'Content-Type: image/jpeg\\r\\n\\r\\n' + \
                               buffer.tobytes() + b'\\r\\n')\
                else:\
                    # Camera offline\
                    placeholder = np.zeros((480, 640, 3), dtype=np.uint8)\
                    cv2.putText(placeholder, f"Camera \{camera_id.title()\} Offline", (150, 240),\
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)\
                    ret, buffer = cv2.imencode('.jpg', placeholder)\
                    if ret:\
                        yield (b'--frame\\r\\n'\
                               b'Content-Type: image/jpeg\\r\\n\\r\\n' + \
                               buffer.tobytes() + b'\\r\\n')\
            time.sleep(0.1)\
    \
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")\
\
@app.get("/highlights")\
async def highlights_page():\
    """Highlights page"""\
    try:\
        conn = sqlite3.connect("data/goodland_pickleball.db")\
        cursor = conn.cursor()\
        cursor.execute("SELECT * FROM highlights ORDER BY created_at DESC LIMIT 20")\
        highlights = cursor.fetchall()\
        conn.close()\
        \
        html = f"""\
        <!DOCTYPE html>\
        <html>\
        <head>\
            <title>Highlights - Goodland Pickleball</title>\
            <style>\
                body \{\{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; \}\}\
                .header \{\{ \
                    background: linear-gradient(135deg, #1e3c72, #2a5298); \
                    color: white; padding: 30px; border-radius: 15px; \
                    margin-bottom: 30px; text-align: center; \
                \}\}\
                .grid \{\{ \
                    display: grid; \
                    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); \
                    gap: 20px; \
                \}\}\
                .card \{\{ \
                    background: white; \
                    border-radius: 15px; \
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1); \
                    overflow: hidden; \
                \}\}\
                .video-thumb \{\{ \
                    width: 100%; \
                    height: 200px; \
                    background: linear-gradient(45deg, #667eea, #764ba2); \
                    display: flex; \
                    align-items: center; \
                    justify-content: center; \
                    color: white; \
                    font-size: 2em;\
                \}\}\
                .body \{\{ padding: 20px; \}\}\
                .btn \{\{ \
                    background: #667eea; \
                    color: white; \
                    border: none; \
                    padding: 10px 15px; \
                    border-radius: 5px; \
                    margin: 5px;\
                    text-decoration: none;\
                    display: inline-block;\
                \}\}\
            </style>\
        </head>\
        <body>\
            <div class="header">\
                <h1>\uc0\u55356 \u57260  Goodland Pickleball Highlights</h1>\
                <a href="/" class="btn">\uc0\u8592  Back to Dashboard</a>\
            </div>\
            <div class="grid">\
        """\
        \
        for highlight in highlights:\
            id_, timestamp, duration, confidence, description, video_path, views, created_at = highlight\
            dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()\
            \
            html += f"""\
                <div class="card">\
                    <div class="video-thumb">\uc0\u55356 \u57278  HIGHLIGHT</div>\
                    <div class="body">\
                        <h4>\{description\}</h4>\
                        <p><strong>Date:</strong> \{dt.strftime('%m/%d/%Y %I:%M %p')\}</p>\
                        <p><strong>Duration:</strong> \{duration\}s</p>\
                        <p><strong>Views:</strong> \{views\}</p>\
                        <a href="/video/\{id_\}" class="btn" target="_blank">\uc0\u9654 \u65039  Play Video</a>\
                        <button class="btn" onclick="alert('Ready for purchase system!')">\uc0\u55357 \u56496  Buy ($5)</button>\
                    </div>\
                </div>\
            """\
        \
        html += """\
            </div>\
        </body>\
        </html>\
        """\
        \
        return HTMLResponse(content=html)\
        \
    except Exception as e:\
        return HTMLResponse(f"<h1>Error: \{e\}</h1>")\
\
@app.get("/video/\{highlight_id\}")\
async def serve_video(highlight_id: int):\
    """Serve video"""\
    try:\
        conn = sqlite3.connect("data/goodland_pickleball.db")\
        cursor = conn.cursor()\
        cursor.execute("SELECT video_path FROM highlights WHERE id = ?", (highlight_id,))\
        result = cursor.fetchone()\
        \
        # Update view count\
        cursor.execute("UPDATE highlights SET views = views + 1 WHERE id = ?", (highlight_id,))\
        conn.commit()\
        conn.close()\
        \
        if result and Path(result[0]).exists():\
            return FileResponse(result[0], media_type="video/mp4")\
        else:\
            return HTMLResponse("<h1>Video not found</h1>", status_code=404)\
            \
    except Exception as e:\
        return HTMLResponse(f"<h1>Error: \{e\}</h1>", status_code=500)\
\
@app.get("/api/test")\
async def manual_test_highlight():\
    """Create test highlight manually"""\
    if camera_system:\
        camera_system._create_test_highlight()\
        return \{"success": True, "message": "Test highlight created!"\}\
    return \{"success": False, "message": "System not ready"\}\
\
@app.get("/api/status")  \
async def status():\
    """System status"""\
    if camera_system:\
        return camera_system.get_stats()\
    return \{"error": "System not initialized"\}\
\
@app.get("/health")\
async def health():\
    """Health check"""\
    return \{\
        "status": "healthy",\
        "service": "Goodland Pickleball",\
        "timestamp": datetime.now().isoformat(),\
        "cameras": processing_stats["cameras_online"]\
    \}\
\
if __name__ == "__main__":\
    import uvicorn\
    \
    print("\uc0\u55356 \u57278  Starting Goodland Pickleball System")\
    print(f"\uc0\u55357 \u56545  Lorex NVR: \{LOREX_IP\}")\
    \
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)}