"""Example 7: talk to the Sonoglyph REST API from Python.

Start the server in another terminal:
    sonoglyph serve

Then run:
    python examples/07_server_client.py
"""

from pathlib import Path

import httpx

API_URL = "http://127.0.0.1:8000"
TIMEOUT = httpx.Timeout(60.0, connect=5.0)

TRACK = Path(__file__).parent / "ginseng_strip.mp3"


def check_server() -> bool:
    try:
        r = httpx.get(f"{API_URL}/api/health", timeout=5.0)
        r.raise_for_status()
        print(f"Server OK — version {r.json()['version']}")
        return True
    except (httpx.ConnectError, httpx.HTTPStatusError):
        print(f"Cannot reach {API_URL}. Start it with: sonoglyph serve")
        return False


def analyze_by_path() -> dict:
    r = httpx.post(
        f"{API_URL}/api/analyze-by-path",
        json={"path": str(TRACK), "features": ["tempo", "mood"]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def analyze_upload() -> dict:
    with open(TRACK, "rb") as f:
        r = httpx.post(
            f"{API_URL}/api/analyze",
            files={"file": (TRACK.name, f, "audio/mpeg")},
            params={"features": "tempo,mood"},
            timeout=TIMEOUT,
        )
    r.raise_for_status()
    return r.json()


def list_features() -> list[str]:
    r = httpx.get(f"{API_URL}/api/features", timeout=5.0)
    r.raise_for_status()
    return r.json()["features"]


def main() -> None:
    if not check_server():
        return

    print(f"\nAvailable analyzers: {', '.join(list_features())}\n")

    print("--- analyze by path ---")
    data = analyze_by_path()
    print(f"BPM:  {data['tempo']['bpm']:.1f}")
    print(f"Mood: {data['mood']['label']}  tags={data['mood']['tags']}")

    print("\n--- analyze by upload ---")
    data = analyze_upload()
    print(f"BPM:  {data['tempo']['bpm']:.1f}")
    print(f"Mood: {data['mood']['label']}")


if __name__ == "__main__":
    main()
