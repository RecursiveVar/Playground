#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""videotool 的本地网页界面（只用 Python 标准库，不需要装任何东西）。

启动：
    python webui.py                 # 打开 http://127.0.0.1:8765
    python webui.py --port 9000
    python webui.py --no-browser    # 只起服务，不自动开浏览器

它把 videotool.py 的三个能力包成点击操作：
    分析  -> 读 MP4 结构，告诉你码率花在哪
    提取  -> 无损重封装（-c copy，画质不变，体积基本不变）
    压缩  -> 目标体积 / CRF 两种模式重新编码

所有任务都在本机跑，文件不出网。服务只监听 127.0.0.1。
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(BASE, "videotool.py")
OUT_DIR = os.path.join(BASE, "out")
UPLOAD_DIR = os.path.join(OUT_DIR, "_uploads")
UI_FILE = os.path.join(BASE, "ui.html")
PYTHON = sys.executable or "python"

if BASE not in sys.path:
    sys.path.insert(0, BASE)

try:
    import videotool as vt
except Exception as exc:  # pragma: no cover - 只在文件缺失时发生
    sys.exit("找不到同目录的 videotool.py：%s" % exc)

# Windows 控制台编码兜底
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 任务
# ---------------------------------------------------------------------------

RE_TIME = re.compile(r"time=\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
RE_TIME_SHORT = re.compile(r"time=\s*(\d+):(\d+(?:\.\d+)?)")
RE_SPEED = re.compile(r"speed=\s*([\d.]+)\s*x")
RE_FPS = re.compile(r"fps=\s*([\d.]+)")
RE_SIZE = re.compile(r"size=\s*(\d+)\s*KiB")
RE_FF_OUTPUT = re.compile(r"^\s*输出：\s*(.+?)\s*$")

JOBS = {}
JOBS_LOCK = threading.Lock()


def _hidden_flags():
    if os.name == "nt":
        return 0x08000000  # CREATE_NO_WINDOW，避免每次弹黑框
    return 0


def kill_tree(proc):
    """终止任务及其子进程。videotool.py 是中间层，真正的 ffmpeg 是它的子进程，
    只 terminate 父进程会留下孤儿 ffmpeg 继续跑（还占着输出文件）。"""
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=0x08000000)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def new_job(kind, title, argv, src, out_path, duration):
    jid = uuid.uuid4().hex[:12]
    job = {
        "id": jid,
        "kind": kind,
        "title": title,
        "argv": argv,
        "src": src,
        "out_path": out_path,
        "duration": duration,
        "status": "running",
        "progress": 0.0,
        "done_seconds": 0.0,
        "speed": None,
        "fps": None,
        "log": deque(maxlen=400),
        "error": None,
        "started": time.time(),
        "elapsed": 0.0,
        "cancelled": False,
        "proc": None,
    }
    with JOBS_LOCK:
        JOBS[jid] = job
    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return job


def _handle_line(job, raw):
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return
    m = RE_TIME.search(text)
    if m:
        job["done_seconds"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        job["progress"] = _progress(job)
        sp = RE_SPEED.search(text)
        if sp:
            try:
                job["speed"] = float(sp.group(1))
            except ValueError:
                pass
        fp = RE_FPS.search(text)
        if fp:
            try:
                job["fps"] = float(fp.group(1))
            except ValueError:
                pass
        return
    m = RE_TIME_SHORT.search(text)
    if m and text.startswith("frame="):
        job["done_seconds"] = int(m.group(1)) * 60 + float(m.group(2))
        job["progress"] = _progress(job)
        return
    # 普通输出行：去掉 ffmpeg 进度行的残渣
    if text.startswith("frame=") or text.startswith("size=") or text.startswith("  "):
        if "time=" in text:
            return
    job["log"].append(text)


def _progress(job):
    dur = job.get("duration") or 0
    if dur <= 0:
        return None
    return max(0.0, min(0.995, job["done_seconds"] / dur))


def _run_job(job):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    try:
        proc = subprocess.Popen(
            job["argv"],
            cwd=BASE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=_hidden_flags(),
        )
        job["proc"] = proc
        buf = b""
        while True:
            # 用 read1：有数据就返回，不等到凑满 1024 字节（否则进度会卡在 0%）
            chunk = proc.stdout.read1(4096)
            if not chunk:
                break
            buf += chunk
            parts = re.split(rb"[\r\n]", buf)
            buf = parts.pop()
            if len(buf) > 16384:
                parts.append(buf)
                buf = b""
            for raw in parts:
                _handle_line(job, raw)
        if buf:
            _handle_line(job, buf)
        rc = proc.wait()
        job["elapsed"] = time.time() - job["started"]
        if job["cancelled"]:
            job["status"] = "cancelled"
            _discard(job["out_path"])
        elif rc == 0:
            job["status"] = "done"
            job["progress"] = 1.0
        else:
            job["status"] = "error"
            job["error"] = "处理失败（退出码 %d），看下面日志的最后几行。" % rc
            _discard(job["out_path"])
    except Exception as exc:  # pragma: no cover
        job["status"] = "error"
        job["error"] = "%s: %s" % (type(exc).__name__, exc)
        job["elapsed"] = time.time() - job["started"]
    finally:
        job["proc"] = None


def _discard(path, attempts=6):
    """删除未完成的输出文件；Windows 上刚被 ffmpeg 关掉的文件可能短暂被占用，重试几次。"""
    if not path:
        return
    for _ in range(attempts):
        try:
            if not os.path.exists(path):
                return
            os.remove(path)
            return
        except OSError:
            time.sleep(0.2)


def job_public(job):
    out_size = None
    if job["status"] == "done" and os.path.isfile(job["out_path"]):
        try:
            out_size = os.path.getsize(job["out_path"])
        except OSError:
            out_size = None
    return {
        "id": job["id"],
        "kind": job["kind"],
        "title": job["title"],
        "status": job["status"],
        "progress": job["progress"],
        "speed": job["speed"],
        "fps": job["fps"],
        "done_seconds": job["done_seconds"],
        "duration": job["duration"],
        "elapsed": round(job["elapsed"] or (time.time() - job["started"]), 1),
        "src": job["src"],
        "out_path": job["out_path"],
        "out_size": out_size,
        "error": job["error"],
        "log": list(job["log"])[-60:],
    }


# ---------------------------------------------------------------------------
# 分析
# ---------------------------------------------------------------------------

_SCALARS = (int, float, str, bool)


def analyze_path(path):
    info = vt.analyze_mp4(path)
    tracks = []
    for t in info["tracks"]:
        clean = {}
        for k, v in t.items():
            if isinstance(v, _SCALARS) or v is None:
                clean[k] = v
        if "bytes" not in clean:
            clean["bytes"] = None
        tracks.append(clean)
    dur = info.get("duration") or 0
    size = info.get("size") or 0
    v = next((t for t in tracks if t["kind"] == "video"), None)
    a = next((t for t in tracks if t["kind"] == "audio"), None)
    bpp = None
    if v and v.get("bps") and v.get("width") and v.get("height") and v.get("fps"):
        bpp = v["bps"] / (v["width"] * v["height"] * v["fps"])
    return {
        "path": info["path"],
        "name": os.path.basename(info["path"]),
        "size": size,
        "duration": dur,
        "brand": info.get("brand"),
        "moov_first": info.get("moov_before_mdat"),
        "overhead": info.get("overhead"),
        "encoder_strings": info.get("encoder_strings") or [],
        "tracks": tracks,
        "bpp": bpp,
        "video": v,
        "audio": a,
    }


# ---------------------------------------------------------------------------
# 输出路径
# ---------------------------------------------------------------------------

def _resolve_out_dir(raw_dir):
    text = (raw_dir or "").strip().strip('"')
    if not text:
        return OUT_DIR
    resolved = os.path.abspath(os.path.join(BASE, text))
    if os.path.isfile(resolved):
        raise ValueError("输出目录不能是已存在的文件：%s" % resolved)
    return resolved


def _unique_out(src, tag, out_dir=None):
    target_dir = _resolve_out_dir(out_dir)
    stem = os.path.splitext(os.path.basename(src))[0]
    safe = re.sub(r'[\\/:*?"<>|]+', "_", stem)[:60] or "output"
    base = os.path.join(target_dir, "%s_%s" % (safe, tag))
    candidate = base + ".mp4"
    n = 2
    while os.path.exists(candidate):
        candidate = "%s_%d.mp4" % (base, n)
        n += 1
    os.makedirs(target_dir, exist_ok=True)
    return candidate


def _num(payload, key, default=None, lo=None, hi=None, cast=float):
    raw = payload.get(key, default)
    if raw in (None, ""):
        raw = default
    try:
        val = cast(raw)
    except (TypeError, ValueError):
        raise ValueError("参数 %s 不是数字" % key)
    if lo is not None and val < lo:
        raise ValueError("参数 %s 太小（最小 %s）" % (key, lo))
    if hi is not None and val > hi:
        raise ValueError("参数 %s 太大（最大 %s）" % (key, hi))
    return val


def build_job(payload):
    op = payload.get("op")
    src = payload.get("path") or payload.get("src")
    if not src:
        raise ValueError("缺少文件路径")
    src = os.path.abspath(src)
    if not os.path.isfile(src):
        raise ValueError("文件不存在：%s" % src)

    duration = None
    try:
        duration = vt.analyze_mp4(src).get("duration")
    except Exception:
        duration = None

    out_dir = payload.get("out_dir")
    if op == "extract":
        out = _unique_out(src, "提取", out_dir)
        argv = [PYTHON, "-u", TOOL, "extract", src, "-o", out]
        if payload.get("no_audio"):
            argv.append("--no-audio")
        return new_job("extract", "无损提取", argv, src, out, duration)

    if op != "shrink":
        raise ValueError("未知操作：%s" % op)

    mode = payload.get("mode") or "size"
    codec = payload.get("codec") or "h264"
    if codec not in ("h264", "hevc"):
        raise ValueError("编码器只能是 h264 或 hevc")
    preset = payload.get("preset") or "veryfast"
    if preset not in ("ultrafast", "veryfast", "faster", "fast", "medium", "slow"):
        raise ValueError("preset 不合法")

    if mode == "size":
        mb = _num(payload, "target_mb", 20, lo=0.5, hi=4096)
        tag = "%dMB" % round(mb) if abs(mb - round(mb)) < 0.05 else "%.1fMB" % mb
    else:
        mb = None
        tag = "CRF%d" % round(_num(payload, "crf", 23, lo=10, hi=40))

    out = _unique_out(src, "压缩_" + tag, out_dir)
    argv = [PYTHON, "-u", TOOL, "shrink", src, "-o", out,
            "--codec", codec, "--preset", preset]
    if mode == "size":
        argv += ["--target-mb", ("%g" % mb)]
    else:
        crf = _num(payload, "crf", 23, lo=10, hi=40)
        argv += ["--crf", ("%g" % crf)]
    height = payload.get("height")
    if height not in (None, "", 0, "0"):
        argv += ["--height", str(int(_num(payload, "height", 1080, lo=144, hi=4320, cast=int)))]
    if payload.get("no_audio"):
        argv.append("--no-audio")
    else:
        argv += ["--audio-kbps", str(int(_num(payload, "audio_kbps", 128, lo=8, hi=512, cast=int)))]
    label = "压缩到 %s" % tag if mode == "size" else "压缩（%s）" % tag
    return new_job("shrink", label, argv, src, out, duration)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _ffmpeg_state():
    try:
        path = vt.need_ffmpeg()
        try:
            ver = subprocess.run([path, "-version"], capture_output=True, text=True,
                                 timeout=10, creationflags=_hidden_flags()).stdout.splitlines()[0]
        except Exception:
            ver = os.path.basename(path)
        return {"ok": True, "path": path, "version": ver}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class Handler(BaseHTTPRequestHandler):
    server_version = "videotool-ui/1.0"
    protocol_version = "HTTP/1.1"

    # ---- 基础响应工具 -------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str))

    def _err(self, message, code=400):
        self._json({"ok": False, "error": str(message)}, code)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("请求体不是合法 JSON")

    def log_message(self, fmt, *args):
        return  # 安静模式

    # ---- 路由 ---------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                return self._serve_ui()
            if u.path == "/api/state":
                return self._json({
                    "ok": True,
                    "ffmpeg": _ffmpeg_state(),
                    "out_dir": OUT_DIR,
                    "tool": TOOL,
                    "python": PYTHON,
                })
            if u.path == "/api/job":
                job = JOBS.get((q.get("id") or [""])[0])
                if not job:
                    return self._err("任务不存在", 404)
                return self._json({"ok": True, "job": job_public(job)})
            if u.path == "/api/download":
                return self._download((q.get("path") or [""])[0])
            if u.path == "/api/log":
                job = JOBS.get((q.get("id") or [""])[0])
                if not job:
                    return self._err("任务不存在", 404)
                return self._json({"ok": True, "log": list(job["log"])})
            return self._err("未知接口：%s" % u.path, 404)
        except Exception as exc:
            return self._err(exc, 500)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/api/upload":
                name = (q.get("name") or ["upload.mp4"])[0]
                return self._upload(name)
            if u.path == "/api/analyze":
                data = self._body()
                path = (data.get("path") or "").strip().strip('"')
                if not path:
                    return self._err("请先选择文件")
                if not os.path.isfile(path):
                    return self._err("文件不存在：%s" % path)
                return self._json({"ok": True, "info": analyze_path(path)})
            if u.path == "/api/job":
                return self._json({"ok": True, "job": job_public(build_job(self._body()))})
            if u.path == "/api/cancel":
                job = JOBS.get(self._body().get("id") or "")
                if not job:
                    return self._err("任务不存在", 404)
                job["cancelled"] = True
                kill_tree(job.get("proc"))
                return self._json({"ok": True})
            if u.path == "/api/reveal":
                path = self._body().get("path") or ""
                if not os.path.exists(path):
                    return self._err("路径不存在")
                target = path if os.path.isdir(path) else os.path.dirname(path)
                if os.name == "nt":
                    os.startfile(target)  # noqa: S606 - 本地工具，打开资源管理器
                else:
                    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", target])
                return self._json({"ok": True})
            return self._err("未知接口：%s" % u.path, 404)
        except ValueError as exc:
            return self._err(exc, 400)
        except Exception as exc:
            return self._err(exc, 500)

    # ---- 具体实现 -----------------------------------------------------
    def _serve_ui(self):
        try:
            with open(UI_FILE, "rb") as fh:
                body = fh.read()
        except OSError:
            return self._send(500, "找不到 ui.html，请确认它和 webui.py 在同一目录。",
                              "text/plain; charset=utf-8")
        self._send(200, body, "text/html; charset=utf-8")

    def _upload(self, raw_name):
        name = os.path.basename(unquote(raw_name)).strip() or "upload.mp4"
        safe = re.sub(r'[\\/:*?"<>|]+', "_", name)
        stem, ext = os.path.splitext(safe)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        target = os.path.join(UPLOAD_DIR, safe)
        n = 2
        while os.path.exists(target):
            target = os.path.join(UPLOAD_DIR, "%s_%d%s" % (stem, n, ext))
            n += 1
        length = int(self.headers.get("Content-Length") or 0)
        remaining = length
        t0 = time.time()
        with open(target, "wb") as fh:
            while remaining > 0:
                chunk = self.rfile.read(min(4 * 1024 * 1024, remaining))
                if not chunk:
                    break
                fh.write(chunk)
                remaining -= len(chunk)
        if remaining > 0:
            _discard(target)
            return self._err("上传中断，只收到 %d/%d 字节" % (length - remaining, length))
        return self._json({"ok": True, "path": os.path.abspath(target),
                           "size": length, "seconds": round(time.time() - t0, 2)})

    def _download(self, path):
        path = unquote(path)
        if not path or not os.path.isfile(path):
            return self._send(404, "文件不存在", "text/plain; charset=utf-8")
        size = os.path.getsize(path)
        name = os.path.basename(path)
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition",
                         "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (
                             re.sub(r"[^\x20-\x7e]", "_", name), quote(name)))
        self.end_headers()
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return


def main(argv=None):
    global OUT_DIR, UPLOAD_DIR
    import argparse

    ap = argparse.ArgumentParser(description="videotool 网页面板")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--out-dir", help="默认输出目录（默认为 ./out）")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    if args.out_dir:
        OUT_DIR = _resolve_out_dir(args.out_dir)
        UPLOAD_DIR = os.path.join(OUT_DIR, "_uploads")

    httpd = None
    port = args.port
    for _ in range(20):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            port += 1
    if httpd is None:
        sys.exit("端口 %d~%d 都被占用了" % (args.port, port))
    httpd.daemon_threads = True
    url = "http://127.0.0.1:%d" % port
    state = _ffmpeg_state()
    print("videotool 网页面板：%s" % url)
    print("ffmpeg：%s" % (state.get("version") if state.get("ok") else "未找到 —— " + state["error"]))
    print("输出目录：%s" % OUT_DIR)
    print("按 Ctrl+C 停止。")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
