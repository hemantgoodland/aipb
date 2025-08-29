#!/usr/bin/env python3
"""
Goodland Pickleball - Clean Production System
Fixed for Railway deployment
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import sqlite3
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Goodland Pickleball AI System")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Configuration
LOREX_IP = os.getenv("LOREX_IP", "192.168.1.108")
LOREX_USERNAME = os.getenv("LOREX_USERNAME", "hemant@goodlandpickleball.com")  
LOREX_PASSWORD = os.getenv("LOREX_PASSWORD", "Rohan12#")
PORT = int(os.getenv("PORT", 8000))

# Global stats
stats = {
    "highlights_created": 0,
    "cameras_online": 0,
    "uptime_start": datetime.now(),
    "system_status": "starting"
}

class SimplePickleballSystem:
    """Simplified camera system for Goodland Pickleball"""
    
    def __init__(self):
        self.cameras = {}
        self.running = False
        
        # Create directories
        Path("data").mkdir(exist_ok=True)
        Path("output/highlights").mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.init_database()
        logger.info("System Initialized")
    
    def init_database(self):
        """Initialize database"""
        conn = sqlite3.connect("data/pickleball.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                duration REAL,
                description TEXT,
                video_path TEXT,
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def connect_cameras(self):
        """Connect to Lorex cameras"""
        logger.info(f"Connecting to Lorex at {LOREX_IP}")
        
        camera_urls = [
            f"rtsp://{LOREX_USERNAME}:{LOREX_PASSWORD}@{LOREX_IP}:554/cam/realmonitor?channel=1&subtype=0",
            f"rtsp://{LOREX_USERNAME}:{LOREX_PASSWORD}@{LOREX_IP}:554/cam/realmonitor?channel=2&subtype=0"
        ]
        
        for i, url in enumerate(camera_urls):
            try:
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        camera_id = f"camera_{i+1}"
                        self.cameras[camera_id] = {
                            "capture": cap,
                            "url": url,
                            "last_frame": frame,
                            "status": "online"
                        }
                        stats["cameras_online"] += 1
                        logger.info(f"Camera {i+1} connected")
                    else:
                        cap.release()
                else:
                    logger.warning(f"Camera {i+1} failed to connect")
            except Exception as e:
                logger.error(f"Camera {i+1} error: {e}")
        
        return len(self.cameras) > 0
    
    def start_processing(self):
        """Start simple processing"""
        if not self.cameras:
            stats["system_status"] = "no_cameras"
            return False
        
        self.running = True
        stats["system_status"] = "running"
        
        # Start background thread
        thread = threading.Thread(target=self._processing_loop, daemon=True)
        thread.start()
        
        logger.info("Processing started")
        return True
    
    def _processing_loop(self):
        """Simple processing loop"""
        last_highlight = 0
        
        while self.running:
            try:
                # Update camera frames
                for camera_id, camera in self.cameras.items():
                    try:
                        ret, frame = camera["capture"].read()
                        if ret:
                            camera["last_frame"] = frame
                            camera["status"] = "online"
                        else:
                            camera["status"] = "error"
                    except:
                        camera["status"] = "error"
                
                # Create test highlight every 3 minutes
                current_time = time.time()
                if current_time - last_highlight > 180:  # 3 minutes
                    self._create_test_highlight()
                    last_highlight = current_time
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                time.sleep(5)
    
    def _create_test_highlight(self):
        """Create a test highlight"""
        try:
            if not self.cameras:
                return
            
            # Get first camera
            camera = list(self.cameras.values())[0]
            frame = camera.get("last_frame")
            
            if frame is None:
                return
            
            # Create filename
            timestamp = time.time()
            dt = datetime.fromtimestamp(timestamp)
            filename = f"highlight_{dt.strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = f"output/highlights/{filename}"
            
            # Create video
            height, width = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height))
            
            # Create 5-second clip
            for i in range(150):  # 5 seconds
                frame_copy = frame.copy()
                
                # Add text
                cv2.putText(frame_copy, "GOODLAND PICKLEBALL", (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame_copy, dt.strftime('%m/%d/%Y %H:%M'), (20, height-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                if i < 60:  # First 2 seconds
                    cv2.putText(frame_copy, "HIGHLIGHT", (width//2-80, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                
                out.write(frame_copy)
            
            out.release()
            
            # Save to database
            conn = sqlite3.connect("data/pickleball.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO highlights (timestamp, duration, description, video_path)
                VALUES (?, ?, ?, ?)
            """, (timestamp, 5.0, "Auto-generated highlight", filepath))
            conn.commit()
            conn.close()
            
            stats["highlights_created"] += 1
            logger.info(f"Created highlight: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to create highlight: {e}")
    
    def get_camera_frame(self, camera_id):
        """Get camera frame"""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get("last_frame")
        return None

# Initialize system
camera_system = None

@app.on_event("startup")
async def startup_event():
    """Initialize system"""
    global camera_system
    
    logger.info("Starting Goodland Pickleball System...")
    
    try:
        camera_system = SimplePickleballSystem()
        
        if camera_system.connect_cameras():
            camera_system.start_processing()
            logger.info("System is LIVE!")
        else:
            logger.warning("Running in demo mode - no cameras")
            stats["system_status"] = "demo_mode"
            
    except Exception as e:
        logger.error(f"Startup error: {e}")
        stats["system_status"] = "error"

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard"""
    uptime_minutes = (datetime.now() - stats["uptime_start"]).seconds // 60
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Goodland Pickleball - AI System</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                color: white; 
                margin: 0;
                padding: 20px;
            }}
            .header {{ 
                text-align: center; 
                padding: 40px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                margin-bottom: 30px;
            }}
            .logo {{ font-size: 3em; margin-bottom: 10px; }}
            .grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
            }}
            .card {{ 
                background: rgba(255,255,255,0.95); 
                color: #333; 
                padding: 25px; 
                border-radius: 15px; 
            }}
            .stat {{ 
                text-align: center; 
                padding: 15px; 
                background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; 
                border-radius: 10px;
                margin: 10px;
            }}
            .stat-number {{ font-size: 2em; font-weight: bold; }}
            .btn {{ 
                background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; 
                border: none; 
                padding: 12px 24px; 
                border-radius: 25px; 
                margin: 5px;
                text-decoration: none;
                display: inline-block;
            }}
            .status-good {{ color: #28a745; }}
            .status-warning {{ color: #ffc107; }}
        </style>
        <script>
            setTimeout(() => window.location.reload(), 30000);
        </script>
    </head>
    <body>
        <div class="header">
            <div class="logo">🎾 Goodland Pickleball</div>
            <div>AI-Powered Camera System</div>
            <div style="margin-top: 15px;">
                Status: <strong class="{'status-good' if stats['cameras_online'] > 0 else 'status-warning'}">
                    {stats['system_status'].upper()}
                </strong>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📊 System Stats</h3>
                <div class="stat">
                    <div class="stat-number">{stats['highlights_created']}</div>
                    <div>Highlights Created</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{stats['cameras_online']}</div>
                    <div>Cameras Online</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{uptime_minutes}</div>
                    <div>Minutes Running</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🎥 Lorex System</h3>
                <p><strong>IP:</strong> {LOREX_IP}</p>
                <p><strong>Status:</strong> {'Connected' if stats['cameras_online'] > 0 else 'Checking...'}</p>
                <div>
                    <a href="/live/camera_1" class="btn">📹 Camera 1</a>
                    <a href="/live/camera_2" class="btn">📹 Camera 2</a>
                </div>
            </div>
            
            <div class="card">
                <h3>🎬 Highlights</h3>
                <p>Auto-generated from your games</p>
                <div>
                    <a href="/highlights" class="btn">View All</a>
                    <a href="/api/create-highlight" class="btn">Create Test</a>
                </div>
            </div>
            
            <div class="card">
                <h3>💰 Business</h3>
                <p><strong>System:</strong> Operational</p>
                <p><strong>Ready for:</strong> Player sales</p>
                <p><strong>Deployment:</strong> Railway Cloud</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

@app.get("/live/{camera_id}")
async def live_stream(camera_id: str):
    """Live camera stream"""
    def generate():
        while True:
            if camera_system:
                frame = camera_system.get_camera_frame(camera_id)
                if frame is not None:
                    # Add overlay
                    frame_copy = frame.copy()
                    cv2.putText(frame_copy, "GOODLAND PICKLEBALL LIVE", (20, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    
                    ret, buffer = cv2.imencode('.jpg', frame_copy)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + 
                               buffer.tobytes() + b'\r\n')
                else:
                    # Offline placeholder
                    placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "Camera Offline", (200, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    ret, buffer = cv2.imencode('.jpg', placeholder)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + 
                               buffer.tobytes() + b'\r\n')
            time.sleep(0.1)
    
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/highlights")
async def highlights_page():
    """Highlights page"""
    try:
        conn = sqlite3.connect("data/pickleball.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM highlights ORDER BY created_at DESC LIMIT 20")
        highlights = cursor.fetchall()
        conn.close()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Highlights - Goodland Pickleball</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .header { background: linear-gradient(135deg, #1e3c72, #2a5298); 
                         color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .card { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .btn { background: #667eea; color: white; border: none; padding: 10px 15px; 
                      border-radius: 5px; margin: 5px; text-decoration: none; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎬 Goodland Pickleball Highlights</h1>
                <a href="/" class="btn">← Back to Dashboard</a>
            </div>
            <div class="grid">
        """
        
        for highlight in highlights:
            id_, timestamp, duration, description, video_path, views, created_at = highlight
            dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
            
            html += f"""
                <div class="card">
                    <h4>{description}</h4>
                    <p><strong>Date:</strong> {dt.strftime('%m/%d/%Y %I:%M %p')}</p>
                    <p><strong>Duration:</strong> {duration}s</p>
                    <p><strong>Views:</strong> {views}</p>
                    <a href="/video/{id_}" class="btn" target="_blank">▶️ Play</a>
                    <button class="btn" onclick="alert('Purchase system ready!')">💰 Buy ($5)</button>
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
        
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {e}</h1>")

@app.get("/video/{highlight_id}")
async def serve_video(highlight_id: int):
    """Serve video file"""
    try:
        conn = sqlite3.connect("data/pickleball.db")
        cursor = conn.cursor()
        cursor.execute("SELECT video_path FROM highlights WHERE id = ?", (highlight_id,))
        result = cursor.fetchone()
        
        cursor.execute("UPDATE highlights SET views = views + 1 WHERE id = ?", (highlight_id,))
        conn.commit()
        conn.close()
        
        if result and Path(result[0]).exists():
            return FileResponse(result[0], media_type="video/mp4")
        else:
            return HTMLResponse("<h1>Video not found</h1>")
            
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {e}</h1>")

@app.get("/api/create-highlight")
async def create_test_highlight():
    """Create test highlight"""
    try:
        if camera_system:
            camera_system._create_test_highlight()
            return {"success": True, "message": "Test highlight created"}
        return {"success": False, "message": "System not ready"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/status")
async def status():
    """System status"""
    return {
        "stats": stats,
        "lorex_ip": LOREX_IP,
        "uptime_minutes": (datetime.now() - stats["uptime_start"]).seconds // 60,
        "cameras": len(camera_system.cameras) if camera_system else 0
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Goodland Pickleball"
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🎾 Starting Goodland Pickleball System")
    print(f"📡 Lorex: {LOREX_IP}")
    print(f"🚀 Port: {PORT}")
    
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
