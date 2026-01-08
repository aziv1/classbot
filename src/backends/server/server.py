import asyncio
import websockets
import json
import subprocess
import re

# Math Normalization
def normalize_math(text):
    text = re.sub(r'\\\((.*?)\\\)', r'$$\n\1\n$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\n\1\n$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\\\((.*?)\\\\\)', r'$$\n\1\n$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\\\[(.*?)\\\\\]', r'$$\n\1\n$$', text, flags=re.DOTALL)
    return text

# Start Worker Subprocess
worker = subprocess.Popen(
    ["python3", "qwen_worker.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
    bufsize=1
)

async def send_to_worker(packet):
    worker.stdin.write(json.dumps(packet) + "\n")
    worker.stdin.flush()

    line = await asyncio.get_event_loop().run_in_executor(
        None, worker.stdout.readline
    )
    return json.loads(line)

# Global Chunk Storage
chunk_results = []

# WebSocket Handler
async def handle(ws):
    global chunk_results
    chunk_results = []  # reset for each connection

    async for raw in ws:
        try:
            packet = json.loads(raw)
        except:
            await ws.send(json.dumps({"error": "invalid_json"}))
            continue

        command = packet.get("command")

        # PROCESS CHUNK
        if command == "summarize":
            text = packet.get("text", "")
            worker_response = await send_to_worker({
                "command": "summarize",
                "text": text
            })
            cleaned = normalize_math(worker_response["summary"])
            chunk_results.append(cleaned)
            await ws.send(json.dumps({
                "command": "chunk_done",
                "chunk_id": packet.get("chunk_id"),
                "notes": cleaned
            }))
        
        # FINISH — RETURN ALL CHUNKS        
        elif command == "finish":
            final_output = "\n\n".join(chunk_results)

            await ws.send(json.dumps({
                "command": "final_output",
                "summary": final_output
            }))

            chunk_results = []

        else:
            await ws.send(json.dumps({"error": "unknown_command"}))

# Start Server
async def main():
    async with websockets.serve(handle, "0.0.0.0", 8765, max_size=None):
        print("Server running on ws://0.0.0.0:8765")
        await asyncio.Future()

asyncio.run(main())
