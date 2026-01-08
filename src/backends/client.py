import asyncio
import websockets
import json

SERVER_URI = "ws://172.16.100.99:8765"


def chunk_text_no_split_lines(text: str, max_chars: int = 2000):
    lines = text.splitlines(keepends=True)
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) > max_chars:
            if current.strip():
                chunks.append(current)
            current = line
        else:
            current += line

    if current.strip():
        chunks.append(current)

    return chunks


async def main():
    # Example transcript text
    transcript = """[0.00 -> 17.64]  Okay, so this course follows on very naturally from introductory calculus that you did last
[17.64 -> 21.68]  term. And in fact, there's some overlapping material, which is quite nice, it gets us
[21.68 -> 25.96]  going, gets us familiar with the notation and the methods we're going to use. But essentially
[25.96 -> 29.48]  we're going to take a lot of the ideas from introductory calculus and extend them into
[29.48 -> 35.44]  multiple dimensions and work in 3D and think about how we can do integrals in 3D, how we
[35.44 -> 40.32]  can differentiate things in 3D, and how we can develop various theorems that allow us
[40.32 -> 45.84]  to write down physical laws using some of the approaches that we derive.
"""

    chunks = chunk_text_no_split_lines(transcript, max_chars=2000)
    print(f"Prepared {len(chunks)} chunk(s).")

    async with websockets.connect(SERVER_URI, max_size=None) as ws:
        # Send each chunk
        for idx, chunk in enumerate(chunks):
            packet = {
                "command": "summarize",
                "chunk_id": idx,
                "text": chunk
            }
            raw_out = json.dumps(packet, ensure_ascii=False)
            print("\nCLIENT → SERVER:")
            print(raw_out)

            await ws.send(raw_out)

            response_raw = await ws.recv()
            print("\nSERVER → CLIENT:")
            print(response_raw)

            response = json.loads(response_raw)
            # do something with response["notes"] if you want

        # Send finish
        finish_packet = {
            "command": "finish"
        }
        raw_out = json.dumps(finish_packet, ensure_ascii=False)
        print("\nCLIENT → SERVER (finish):")
        print(raw_out)
        await ws.send(raw_out)

        final_raw = await ws.recv()
        print("\nSERVER → CLIENT (final):")
        print(final_raw)

        final_response = json.loads(final_raw)
        if final_response.get("command") == "final_output":
            print("\n=== FINAL SUMMARY ===")
            print(final_response.get("summary", ""))
        else:
            print("\nUnexpected final response:", final_response)


if __name__ == "__main__":
    asyncio.run(main())
