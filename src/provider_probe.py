"""One-shot API diagnostic, no retries and no credential/body logging."""
import json
import os
import sys
import time
import urllib.error
import urllib.request

PROVIDERS = {
    "nvidia": ("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1/chat/completions",
               os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")),
    "zai": ("ZAI_API_KEY", "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            os.getenv("ZAI_MODEL", "glm-4.7-flash")),
}

def main():
    provider = sys.argv[1]
    key_name, endpoint, model = PROVIDERS[provider]
    key = os.getenv(key_name)
    if not key:
        print(f"RESULT {provider}: MISSING_SECRET {key_name}")
        return 2
    use_stream = provider == "nvidia"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly OK."}],
        "max_tokens": 128,
        "stream": use_stream,
    }
    if provider == "nvidia":
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(endpoint,
         data=json.dumps(payload).encode(),
         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                  "Accept": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=100) as resp:
            if use_stream:
                pieces = []
                finish_reason = None
                first = None
                for raw in resp:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data: "):
                        continue
                    if line == "data: [DONE]":
                        break
                    try:
                        event = json.loads(line[6:])
                    except ValueError:
                        continue
                    choice = (event.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        if first is None:
                            first = time.monotonic() - started
                        pieces.append(delta["content"])
                    finish_reason = choice.get("finish_reason") or finish_reason
                content = "".join(pieces)
                print(f"RESULT {provider}: HTTP_200 model={model} total_s={time.monotonic()-started:.1f} first_content_s={first}")
                print(f"FINISH_REASON: {finish_reason}; OUTPUT: {content[:100]!r}")
            else:
                obj = json.load(resp)
                choice = (obj.get("choices") or [{}])[0]
                content = (choice.get("message") or {}).get("content") or ""
                print(f"RESULT {provider}: HTTP_200 model={model} total_s={time.monotonic()-started:.1f}")
                print(f"FINISH_REASON: {choice.get('finish_reason')}; OUTPUT: {str(content)[:100]!r}")
                print(f"USAGE: {obj.get('usage')}")
            return 0 if str(content).strip() else 3
    except urllib.error.HTTPError as exc:
        # Never log full response bodies or headers; these can contain sensitive data.
        code = exc.code
        try:
            detail = json.loads(exc.read(4096))
            error = detail.get("error", {})
            provider_code = error.get("code") if isinstance(error, dict) else None
        except Exception:
            provider_code = None
        print(f"RESULT {provider}: HTTP_{code} provider_error_code={provider_code!r} elapsed_s={time.monotonic()-started:.1f}")
        return 1
    except Exception as exc:
        print(f"RESULT {provider}: {type(exc).__name__} elapsed_s={time.monotonic()-started:.1f}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
