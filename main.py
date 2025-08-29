from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import os
import json
import random

app = FastAPI(title="Goodland Pickleball AI System")

# Environment variables
LOREX_IP = os.getenv("LOREX_IP", "192.168.1.108")
LOREX_USERNAME = os.getenv("LOREX_USERNAME", "hemant@goodlandpickleball.com")
LOREX_PASSWORD = os.getenv("LOREX_PASSWORD", "Rohan12#")
PORT = int(os.getenv("PORT", 8000))

# Simulated data storage
highlights_db = []
camera_status = {"baseline": "Demo Mode", "sideline": "Demo Mode"}

@app.get("/")
async def dashboard():
    """Main dashboard with professional interface"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Goodland Pickleball - AI Camera System</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            .header {{
                background: white;
                border-radius: 10px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .status {{
                display: inline-block;
                padding: 5px 15px;
                background: #10b981;
                color: white;
                border-radius: 20px;
                font-size: 0.9em;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .card {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .card h2 {{
                color: #444;
                margin-bottom: 15px;
                font-size: 1.3em;
            }}
            .stat {{
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
                margin: 10px 0;
            }}
            .camera-feed {{
                background: #f3f4f6;
                height: 200px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
                margin: 10px 0;
            }}
            button {{
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1em;
                transition: background 0.3s;
            }}
            button:hover {{
                background: #764ba2;
            }}
            .highlight-list {{
                max-height: 300px;
                overflow-y: auto;
            }}
            .highlight-item {{
                background: #f9fafb;
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .price {{
                color: #10b981;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎾 Goodland Pickleball AI System</h1>
                <span class="status">● System Online</span>
                <p style="margin-top: 10px; color: #666;">
                    Lorex System: {LOREX_IP} | Camera Status: Demo Mode (Cloud deployment detected)
                </p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h2>📊 Live Statistics</h2>
                    <div class="stat" id="total-highlights">0</div>
                    <p>Total Highlights Generated</p>
                    <div class="stat" id="revenue">$0</div>
                    <p>Revenue Generated</p>
                </div>
                
                <div class="card">
                    <h2>🎥 Camera Status</h2>
                    <p><strong>Baseline Camera:</strong> <span id="baseline-status">Demo Mode</span></p>
                    <p><strong>Sideline Camera:</strong> <span id="sideline-status">Demo Mode</span></p>
                    <div class="camera-feed">
                        <p>Camera feeds require local network access</p>
                    </div>
                    <button onclick="testCameras()">Test Connection</button>
                </div>
                
                <div class="card">
                    <h2>🎬 Recent Highlights</h2>
                    <div class="highlight-list" id="highlights">
                        <p style="color: #999;">No highlights yet. System will generate automatically when cameras are connected.</p>
                    </div>
                    <button onclick="generateDemoHighlight()">Generate Demo Highlight</button>
                </div>
                
                <div class="card">
                    <h2>⚙️ System Controls</h2>
                    <button onclick="location.href='/api/health'">Check API Health</button>
                    <button onclick="location.href='/api/stats'">View Stats</button>
                    <button onclick="alert('Line calling requires camera connection')">Test Line Calls</button>
                </div>
            </div>
            
            <div class="card">
                <h2>📈 Business Dashboard</h2>
                <p>Ready to scale to multiple courts. Camera integration will activate when accessible from local network.</p>
                <ul style="margin: 20px; color: #666;">
                    <li>✅ Cloud deployment successful</li>
                    <li>✅ API endpoints ready</li>
                    <li>✅ Database configured</li>
                    <li>⏳ Awaiting camera network access</li>
                    <li>⏳ AI processing on standby</li>
                </ul>
            </div>
        </div>
        
        <script>
            let highlightCount = 0;
            let revenue = 0;
            
            function updateStats() {{
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(data => {{
                        document.getElementById('total-highlights').textContent = data.total_highlights;
                        document.getElementById('revenue').textContent = '$' + data.revenue;
                    }});
            }}
            
            function testCameras() {{
                alert('Cameras are on local network (192.168.1.108).\\nCloud server cannot directly access.\\nConsider setting up a local bridge or VPN.');
            }}
            
            function generateDemoHighlight() {{
                highlightCount++;
                revenue += 5;
                const highlightList = document.getElementById('highlights');
                const newHighlight = document.createElement('div');
                newHighlight.className = 'highlight-item';
                newHighlight.innerHTML = `
                    <div>
                        <strong>Demo Highlight #${{highlightCount}}</strong>
                        <br><small>${{new Date().toLocaleTimeString()}}</small>
                    </div>
                    <span class="price">$5.00</span>
                `;
                highlightList.insertBefore(newHighlight, highlightList.firstChild);
                document.getElementById('total-highlights').textContent = highlightCount;
                document.getElementById('revenue').textContent = '$' + revenue;
            }}
            
            // Update stats every 5 seconds
            setInterval(updateStats, 5000);
            updateStats();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "lorex_ip": LOREX_IP,
        "camera_status": camera_status
    }

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "total_highlights": len(highlights_db),
        "revenue": len(highlights_db) * 5,
        "cameras_online": 0,  # Will be 2 when cameras are accessible
        "system_uptime": "Active",
        "last_highlight": highlights_db[-1]["timestamp"] if highlights_db else None
    }

@app.post("/api/highlight/create")
async def create_highlight():
    """Create a demo highlight"""
    highlight = {
        "id": len(highlights_db) + 1,
        "timestamp": datetime.now().isoformat(),
        "duration": random.randint(5, 30),
        "type": random.choice(["Rally", "Winner", "Great Shot", "Line Call"]),
        "price": 5.00,
        "camera": random.choice(["baseline", "sideline"])
    }
    highlights_db.append(highlight)
    return JSONResponse(content=highlight)

@app.get("/api/highlights")
async def list_highlights():
    """List all highlights"""
    return JSONResponse(content=highlights_db)

@app.get("/api/camera/status")
async def camera_status_check():
    """Check camera connectivity"""
    # In production, this would actually try to connect to Lorex
    return {
        "lorex_system": {
            "ip": LOREX_IP,
            "status": "Not accessible from cloud",
            "reason": "Cameras are on local network",
            "solution": "Implement local bridge or VPN"
        },
        "cameras": camera_status
    }

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Goodland Pickleball System on port {PORT}")
    print(f"Lorex IP configured: {LOREX_IP}")
    print(f"Note: Camera access requires local network connection")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
