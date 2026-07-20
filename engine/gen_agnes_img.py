#!/usr/bin/env python3
"""Generate images using Agnes AI image models."""
import json, base64, sys, os
from pathlib import Path
import requests

API_KEY = "sk-Pfl2IbSgKiQTTi6vWWL9lo7Cwsabjs9jexXqyvL8iS08xXgp"
BASE_URL = "https://apihub.agnes-ai.com/v1"

def generate(prompt, output_path, model="agnes-image-2.0-flash", size="1792x1024"):
    print(f"🎨 Generating: {Path(output_path).name}")
    print(f"   Model: {model}")
    print(f"   Size: {size}")

    resp = requests.post(
        f"{BASE_URL}/images/generations",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "prompt": prompt, "n": 1, "size": size},
        timeout=120
    )

    if resp.status_code != 200:
        print(f"❌ Error {resp.status_code}: {resp.text[:500]}")
        return False

    data = resp.json()
    if data.get('data') and len(data['data']) > 0:
        img_data = data['data'][0]
        if img_data.get('url'):
            print(f"   Downloading from URL...")
            img_resp = requests.get(img_data['url'])
            Path(output_path).write_bytes(img_resp.content)
            print(f"✅ Saved to: {output_path}")
            return True
        elif img_data.get('b64_json'):
            Path(output_path).write_bytes(base64.b64decode(img_data['b64_json']))
            print(f"✅ Saved to: {output_path}")
            return True

    print(f"❌ No image data in response: {json.dumps(data, indent=2)[:500]}")
    return False

if __name__ == '__main__':
    prompt = sys.argv[1]
    output = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "agnes-image-2.0-flash"
    size = sys.argv[4] if len(sys.argv) > 4 else "1792x1024"
    generate(prompt, output, model, size)
