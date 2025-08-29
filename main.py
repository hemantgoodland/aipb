from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

LOREX_IP = os.getenv("LOREX_IP", "192.168.1.108")
PORT = int(os.getenv("PORT", 8000))

@app.get("/")
async def dashboard():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Goodland Pickleball - Test</title>
    </head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>Goodland Pickleball System</h1>
        <h2>Basic Test - Working!</h2>
        <p>Lorex IP: {LOREX_IP}</p>
        <p>System Status: Online</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
