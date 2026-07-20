#!/usr/bin/env python3
"""Generate image using Agnes AI flash model (OpenAI-compatible)."""

import sys, json, base64, os, requests
from pathlib import Path

def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith('AGNES_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('AGNES_API_KEY')

def main():
    api_key = load_env()
    if not api_key:
        print("❌ AGNES_API_KEY not found in .env")
        sys.exit(1)

    prompt = sys.argv[1] if len(sys.argv) > 1 else None
    if not prompt:
        print("❌ No prompt provided")
        sys.exit(1)

    output_path = sys.argv[2] if len(sys.argv) > 2 else 'generated_image.png'

    print(f"🎨 Generating with agnes-2.0-flash...")

    # Try OpenAI-compatible chat completions with image modality
    resp = requests.post(
        url="https://apihub.agnes-ai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "agnes-2.0-flash",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "modalities": ["image", "text"]
        },
        timeout=120
    )

    if resp.status_code != 200:
        print(f"⚠️ Chat API failed ({resp.status_code}), trying image generation endpoint...")
        print(f"Response: {resp.text[:500]}")

        # Try the images generations endpoint (OpenAI-compatible)
        resp2 = requests.post(
            url="https://apihub.agnes-ai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "agnes-2.0-flash",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1024"
            },
            timeout=120
        )

        if resp2.status_code != 200:
            print(f"❌ Both endpoints failed. Chat: {resp.status_code}, Images: {resp2.status_code}")
            print(f"Images API response: {resp2.text[:500]}")
            sys.exit(1)

        result = resp2.json()
        if result.get('data') and len(result['data']) > 0:
            img_data = result['data'][0]
            if 'b64_json' in img_data:
                image_bytes = base64.b64decode(img_data['b64_json'])
                Path(output_path).write_bytes(image_bytes)
                print(f"✅ Image saved to: {output_path}")
            elif 'url' in img_data:
                img_resp = requests.get(img_data['url'])
                Path(output_path).write_bytes(img_resp.content)
                print(f"✅ Image saved to: {output_path} (from URL)")
            return
        else:
            print(f"❌ No image data in response: {result}")
            sys.exit(1)

    result = resp.json()
    if result.get('choices'):
        msg = result['choices'][0]['message']
        images = []
        if msg.get('images'):
            images = msg['images']
        elif msg.get('content'):
            content = msg['content']
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'image':
                        images.append(part)

        if images:
            img = images[0]
            url = img.get('image_url', {}).get('url') or img.get('url')
            if url:
                if ',' in url:
                    _, b64 = url.split(',', 1)
                    Path(output_path).write_bytes(base64.b64decode(b64))
                else:
                    img_resp = requests.get(url)
                    Path(output_path).write_bytes(img_resp.content)
                print(f"✅ Image saved to: {output_path}")
            else:
                print(f"⚠️ Unexpected image format: {img}")
        else:
            print(f"⚠️ No image in response, got: {msg.get('content', '')[:200]}")
    else:
        print(f"❌ Unexpected response: {json.dumps(result, indent=2)[:500]}")

if __name__ == '__main__':
    main()
