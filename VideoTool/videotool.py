#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
videotool.py —— 视频体积审计 / 无损提取 / 重编码压缩

为什么需要它：剪映（CapCut）等剪辑软件导出的 MP4 一定是"重新编码"的产物，
文件里并不存在一个"原始视频"可供还原。真正能做的三件事：
  1. analyze  拆开 MP4 的 box 结构，看清字节到底花在哪儿（纯 Python，不需要 ffmpeg）
  2. extract  把音视频流原样复制出来（remux，画质零损失，只能省掉容器开销）
  3. shrink   按目标体积 / 质量重新编码，这才是真正能大幅减小体积的手段

用法:
  python videotool.py analyze 导出.mp4
  python videotool.py analyze 导出.mp4 --compare 原素材.mp4
  python videotool.py analyze 导出.mp4 --json
  python videotool.py extract 导出.mp4 -o 提取.mp4
  python videotool.py extract 导出.mp4 -o 静音.mp4 --no-audio
  python videotool.py shrink  导出.mp4 -o 压缩.mp4 --target-mb 25
  python videotool.py shrink  导出.mp4 -o 压缩.mp4 --crf 26 --codec hevc
  python videotool.py get-ffmpeg          # 下载便携版 ffmpeg 到 ./tools/ffmpeg

extract / shrink 需要 ffmpeg；脚本会自动在 PATH、环境变量 FFMPEG、
脚本目录下的 tools/ffmpeg/bin 以及常见安装位置里查找。
"""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import unicodedata
import urllib.request
import zipfile

# 统一用 UTF-8 输出，避免 Windows 控制台默认 GBK 代码页把中文写成乱码
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------

FFMPEG_ZIP = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def fmt_bytes(n):
    if n is None:
        return "-"
    v = float(n)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    if i == 0:
        return "%d B" % int(v)
    return "%.2f %s" % (v, units[i])


def fmt_bps(bps):
    if not bps:
        return "-"
    if bps >= 1_000_000:
        return "%.2f Mbps" % (bps / 1_000_000.0)
    return "%.0f kbps" % (bps / 1000.0)


def fmt_dur(seconds):
    if seconds is None:
        return "-"
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    if h:
        return "%d:%02d:%02d.%03d" % (h, m, s, ms)
    return "%02d:%02d.%03d" % (m, s, ms)


def dwidth(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def pad(s, width, align="left"):
    gap = max(0, width - dwidth(s))
    if align == "right":
        return " " * gap + s
    return s + " " * gap


def pct(part, whole):
    if not whole:
        return "0.0%"
    return "%.1f%%" % (100.0 * part / whole)


# --------------------------------------------------------------------------
# MP4 / MOV 容器解析（纯标准库）
# --------------------------------------------------------------------------

CONTAINER_BOXES = {
    b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf", b"mvex",
    b"moof", b"traf", b"mfra", b"udta", b"ilst", b"sinf", b"schi", b"gmhd",
}

TOP_LEVEL_NAMES = {
    b"ftyp": "ftyp 文件类型",
    b"moov": "moov 元数据(索引)",
    b"mdat": "mdat 音视频数据",
    b"free": "free 填充",
    b"skip": "skip 填充",
    b"wide": "wide 占位",
    b"udta": "udta 用户数据",
    b"moof": "moof 分片索引",
    b"mfra": "mfra 分片随机访问",
    b"styp": "styp 分片类型",
    b"uuid": "uuid 扩展",
}

VIDEO_ENTRIES = {b"avc1", b"avc3", b"hvc1", b"hev1", b"av01", b"vp09", b"vp08", b"mp4v", b"ap4h", b"prores", b"dnxhd"}
AUDIO_ENTRIES = {b"mp4a", b"ac-3", b"ec-3", b"Opus", b"alac", b"fl32", b"fLaC", b"mp3 ", b"sowt", b"twos", b"lpcm"}

CODEC_NAMES = {
    b"avc1": "H.264", b"avc3": "H.264", b"hvc1": "H.265/HEVC", b"hev1": "H.265/HEVC",
    b"av01": "AV1", b"vp09": "VP9", b"vp08": "VP8", b"mp4v": "MPEG-4",
    b"ap4h": "ProRes 4444", b"ap4x": "ProRes 4444 XQ", b"apch": "ProRes 422 HQ",
    b"apcn": "ProRes 422", b"apcs": "ProRes 422 LT", b"apco": "ProRes 422 Proxy",
    b"mp4a": "AAC", b"ac-3": "AC-3", b"ec-3": "E-AC-3", b"Opus": "Opus",
    b"alac": "ALAC", b"fLaC": "FLAC", b"mp3 ": "MP3", b"twos": "PCM", b"lpcm": "PCM",
}

AVC_PROFILES = {66: "Baseline", 77: "Main", 88: "Extended", 100: "High",
                110: "High10", 122: "High422", 244: "High444"}


def iter_boxes(fh, start, end):
    """遍历 [start, end) 区间内的 box。"""
    pos = start
    while pos + 8 <= end:
        fh.seek(pos)
        head = fh.read(8)
        if len(head) < 8:
            return
        size = int.from_bytes(head[0:4], "big")
        btype = head[4:8]
        hsize = 8
        if size == 1:
            ext = fh.read(8)
            if len(ext) < 8:
                return
            size = int.from_bytes(ext, "big")
            hsize = 16
        elif size == 0:
            size = end - pos
        if size < hsize or pos + size > end + 1:
            return
        yield pos, size, btype, hsize
        pos += size


def read_tree(fh, start, end, depth=0):
    boxes = []
    if depth > 10:
        return boxes
    try:
        for pos, size, btype, hsize in iter_boxes(fh, start, end):
            box = {"type": btype, "start": pos, "size": size, "hsize": hsize, "children": []}
            if btype in CONTAINER_BOXES:
                box["children"] = read_tree(fh, pos + hsize, pos + size, depth + 1)
            elif btype == b"meta":
                box["children"] = read_tree(fh, pos + hsize + 4, pos + size, depth + 1)
            boxes.append(box)
    except Exception:
        pass
    return boxes


def kids(box_list, btype):
    return [b for b in box_list if b["type"] == btype]


def kid(box_list, btype):
    for b in box_list:
        if b["type"] == btype:
            return b
    return None


def payload(fh, box):
    fh.seek(box["start"] + box["hsize"])
    return fh.read(max(0, box["size"] - box["hsize"]))


def u32(buf, off):
    if off + 4 > len(buf):
        return None
    return struct.unpack_from(">I", buf, off)[0]


def u16(buf, off):
    if off + 2 > len(buf):
        return None
    return struct.unpack_from(">H", buf, off)[0]


def parse_avcc(buf):
    """avcC -> (profile, level)"""
    if len(buf) < 4:
        return None, None
    prof = buf[1]
    level = buf[3]
    name = AVC_PROFILES.get(prof, "profile %d" % prof)
    return name, level / 10.0


def parse_hvcc(buf):
    if len(buf) < 2:
        return None
    b1 = buf[1]
    space = (b1 >> 6) & 0x03
    tier = (b1 >> 5) & 0x01
    prof = b1 & 0x1F
    name = {1: "Main", 2: "Main10", 3: "Main Still", 4: "Rext"}.get(prof, "profile %d" % prof)
    return "%s%s" % (name, "/High tier" if tier else "")


def printable_strings(data, minlen=6):
    out, cur = [], bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii", "replace"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii", "replace"))
    return out


def parse_track(fh, trak, movie_timescale):
    t = {"kind": "other"}
    tkhd = kid(trak["children"], b"tkhd")
    mdia = kid(trak["children"], b"mdia")
    if mdia is None:
        return t
    mdhd = kid(mdia["children"], b"mdhd")
    hdlr = kid(mdia["children"], b"hdlr")
    minf = kid(mdia["children"], b"minf")
    stbl = kid(minf["children"], b"stbl") if minf else None

    handler = payload(fh, hdlr)[8:12] if hdlr else b""
    t["kind"] = {b"vide": "video", b"soun": "audio", b"text": "text", b"sbtl": "subtitle"}.get(handler, "other")

    timescale = duration = None
    if mdhd:
        p = payload(fh, mdhd)
        if p[:1] == b"\x01":
            timescale = u32(p, 20)
            duration = (u32(p, 24) or 0) << 32 | (u32(p, 28) or 0)
        else:
            timescale = u32(p, 12)
            duration = u32(p, 16)
    t["timescale"] = timescale
    t["duration"] = (duration / float(timescale)) if timescale and duration else None

    if tkhd:
        p = payload(fh, tkhd)
        if len(p) >= 8:
            t["track_id"] = u32(p, (20 if p[:1] == b"\x01" else 12))
        if len(p) >= 8:
            w = u32(p, len(p) - 8)
            h = u32(p, len(p) - 4)
            if w and h:
                t["width"], t["height"] = w / 65536.0, h / 65536.0

    if stbl:
        stsd = kid(stbl["children"], b"stsd")
        stsz = kid(stbl["children"], b"stsz")
        stts = kid(stbl["children"], b"stts")
        stss = kid(stbl["children"], b"stss")

        if stsd:
            sp = payload(fh, stsd)
            entry_off = stsd["start"] + stsd["hsize"] + 8
            ent = sp[8:]                      # 第一个 sample entry，偏移以条目自身为基准
            entry_size = u32(ent, 0)
            entry_type = ent[4:8]
            t["sample_entry"] = entry_type.decode("latin-1")
            t["codec"] = CODEC_NAMES.get(entry_type, t["sample_entry"])
            if entry_type in VIDEO_ENTRIES:
                t["kind"] = "video"
                if not t.get("width"):
                    t["width"] = u16(ent, 32)
                    t["height"] = u16(ent, 34)
                if entry_size and entry_size >= 86:
                    conf = read_tree(fh, entry_off + 86, entry_off + entry_size)
                    avcc = kid(conf, b"avcC")
                    if avcc:
                        prof, lev = parse_avcc(payload(fh, avcc))
                        if prof:
                            t["profile"] = prof + ("@%.1f" % lev if lev else "")
                    hvcc = kid(conf, b"hvcC")
                    if hvcc:
                        t["profile"] = parse_hvcc(payload(fh, hvcc))
            elif entry_type in AUDIO_ENTRIES:
                t["kind"] = "audio"
                t["channels"] = u16(ent, 24)
                sr = u32(ent, 32)
                if sr:
                    t["sample_rate"] = sr >> 16

        if stsz:
            p = payload(fh, stsz)
            sample_size = u32(p, 4)
            count = u32(p, 8) or 0
            t["sample_count"] = count
            if sample_size:
                t["bytes"] = sample_size * count
            elif 12 + 4 * count <= len(p) + 4:
                table = p[12:12 + 4 * count]
                t["bytes"] = sum(struct.unpack(">%dI" % (len(table) // 4), table)) if table else 0
            else:
                t["bytes"] = None

        if stts:
            p = payload(fh, stts)
            n = u32(p, 4) or 0
            total_delta = 0
            total_cnt = 0
            for i in range(n):
                c = u32(p, 8 + i * 8)
                d = u32(p, 12 + i * 8)
                if c is None or d is None:
                    break
                total_cnt += c
                total_delta += c * d
            if timescale and total_delta:
                t["stts_duration"] = total_delta / float(timescale)
                if t["kind"] == "video" and total_cnt:
                    t["fps"] = total_cnt / t["stts_duration"]
        if stss:
            p = payload(fh, stss)
            t["keyframes"] = u32(p, 4)

    if not t.get("duration") and t.get("stts_duration"):
        t["duration"] = t["stts_duration"]
    if t.get("bytes") and t.get("duration"):
        t["bps"] = t["bytes"] * 8.0 / t["duration"]
    return t


def analyze_mp4(path):
    total = os.path.getsize(path)
    with open(path, "rb") as fh:
        top = read_tree(fh, 0, total)
        if not top:
            raise ValueError("不是有效的 MP4/MOV 文件（找不到任何 box）")
        ftyp = kid(top, b"ftyp")
        brand = payload(fh, ftyp)[:4].decode("latin-1") if ftyp else "?"
        moov = kid(top, b"moov")
        if moov is None:
            raise ValueError("找不到 moov，可能是分片 MP4（fMP4）或不完整文件")

        mvhd = kid(moov["children"], b"mvhd")
        movie_timescale = movie_duration = None
        if mvhd:
            p = payload(fh, mvhd)
            if p[:1] == b"\x01":
                movie_timescale = u32(p, 20)
                movie_duration = ((u32(p, 24) or 0) << 32) | (u32(p, 28) or 0)
            else:
                movie_timescale = u32(p, 12)
                movie_duration = u32(p, 16)
        duration = (movie_duration / float(movie_timescale)) if movie_timescale and movie_duration else None

        tracks = []
        for trak in kids(moov["children"], b"trak"):
            tr = parse_track(fh, trak, movie_timescale)
            if tr.get("kind") != "other" or tr.get("bytes"):
                tracks.append(tr)

        # 容器开销
        tops = []
        covered = 0
        for b in top:
            tops.append({"type": b["type"].decode("latin-1"), "size": b["size"]})
            covered += b["size"]
        gaps = total - covered

        # 编码器字符串
        enc = []
        try:
            moov_bytes = payload(fh, moov)
            if len(moov_bytes) < 64 * 1024 * 1024:
                marks = ("Lavf", "Lavc", "encoder", "CapCut", "Jianying", "VideoToolbox",
                         "x264", "x265", "Apple", "isom")
                for s in printable_strings(moov_bytes, 8):
                    if any(m in s for m in marks) and s not in enc:
                        enc.append(s)
                    if len(enc) >= 6:
                        break
        except Exception:
            pass

    stream_bytes = sum((t.get("bytes") or 0) for t in tracks)
    result = {
        "path": os.path.abspath(path),
        "size": total,
        "brand": brand,
        "duration": duration,
        "tracks": tracks,
        "top_level": tops,
        "gaps": gaps,
        "stream_bytes": stream_bytes,
        "overhead": total - stream_bytes,
        "encoder_strings": enc,
        "moov_before_mdat": _moov_first(top, fh, path),
    }
    return result


def _moov_first(top, fh, path):
    order = [b["type"] for b in top]
    if b"moov" in order and b"mdat" in order:
        return order.index(b"moov") < order.index(b"mdat")
    return None


# --------------------------------------------------------------------------
# 报告输出
# --------------------------------------------------------------------------

def print_report(info, compare=None):
    W = 78
    line = "=" * W
    print(line)
    print("文件    %s" % info["path"])
    print("大小    %s (%s 字节)" % (fmt_bytes(info["size"]), format(info["size"], ",")))
    print("时长    %s" % fmt_dur(info["duration"]))
    layout = "MP4/%s" % info["brand"]
    if info.get("moov_before_mdat") is not None:
        layout += "  moov 在前" if info["moov_before_mdat"] else "  moov 在后（未做 faststart）"
    print("容器    %s" % layout)
    print(line)

    idx = 0
    for t in info["tracks"]:
        idx += 1
        if t["kind"] == "video":
            desc = "视频  %s %s  %dx%d  %.2f fps" % (
                t.get("codec", "?"), t.get("profile", ""),
                int(t.get("width") or 0), int(t.get("height") or 0), t.get("fps") or 0)
        elif t["kind"] == "audio":
            desc = "音频  %s  %dch  %s Hz" % (
                t.get("codec", "?"), t.get("channels") or 0,
                format(int(t.get("sample_rate") or 0), ","))
        else:
            desc = "其他  %s" % t.get("codec", "?")
        print("  #%d  %s" % (idx, pad(desc, 52)) + "%12s  %10s" % (
            fmt_bytes(t.get("bytes")), fmt_bps(t.get("bps"))))
        extra = []
        if t.get("sample_count"):
            extra.append("样本 %s" % format(t["sample_count"], ","))
        if t.get("keyframes"):
            extra.append("关键帧 %s" % format(t["keyframes"], ","))
        if t.get("track_id"):
            extra.append("track_id %s" % t["track_id"])
        if extra:
            print("      " + " · ".join(extra))

    print("-" * W)
    print("  %s%s%s" % (pad("容器结构", 24), pad("大小", 14, "right"), pad("占比", 10, "right")))
    for b in info["top_level"]:
        name = TOP_LEVEL_NAMES.get(b["type"].encode("latin-1"), b["type"])
        print("  %s%s%s" % (pad(name, 24), pad(fmt_bytes(b["size"]), 14, "right"),
                            pad(pct(b["size"], info["size"]), 10, "right")))
    if info["gaps"]:
        print("  %s%s%s" % (pad("未被 box 覆盖的间隙", 24), pad(fmt_bytes(info["gaps"]), 14, "right"),
                            pad(pct(info["gaps"], info["size"]), 10, "right")))

    print("-" * W)
    vb = sum(t.get("bytes") or 0 for t in info["tracks"] if t["kind"] == "video")
    ab = sum(t.get("bytes") or 0 for t in info["tracks"] if t["kind"] == "audio")
    print("  视频数据 %s（%s）  音频数据 %s（%s）  容器及其他 %s（%s）" % (
        fmt_bytes(vb), pct(vb, info["size"]), fmt_bytes(ab), pct(ab, info["size"]),
        fmt_bytes(info["size"] - vb - ab), pct(info["size"] - vb - ab, info["size"])))

    if info["encoder_strings"]:
        print("  编码器标记: " + " | ".join(info["encoder_strings"][:4]))

    # 结论
    print("-" * W)
    print("结论")
    vtrack = next((t for t in info["tracks"] if t["kind"] == "video"), None)
    if vtrack and vtrack.get("bps") and info.get("duration"):
        w = vtrack.get("width") or 0
        h = vtrack.get("height") or 0
        fps = vtrack.get("fps") or 0
        if w and h and fps:
            bpp = vtrack["bps"] / (w * h * fps)
            print("  视频码率 %s，约 %.3f bit/像素/帧（0.05~0.12 属常见区间，越高越「厚」）"
                  % (fmt_bps(vtrack["bps"]), bpp))
        print("  容器本身只占 %s，也就是说：文件大不是封装浪费，而是码流本身就大。"
              % pct(info["size"] - vb - ab, info["size"]))
    if compare:
        print_compare(info, compare)
    print(line)


def print_compare(info, cmp):
    a = next((t for t in info["tracks"] if t["kind"] == "video"), None)
    b = next((t for t in cmp["tracks"] if t["kind"] == "video"), None)
    if not a or not b:
        return
    print()
    print("  与对照文件对比")
    print("    对照    %s  %s  %s" % (os.path.basename(cmp["path"]), fmt_bytes(cmp["size"]),
                                    fmt_dur(cmp["duration"])))
    print("    体积    %s → %s  (×%.1f)" % (fmt_bytes(cmp["size"]), fmt_bytes(info["size"]),
                                          info["size"] / float(cmp["size"] or 1)))
    if a.get("bps") and b.get("bps"):
        print("    视频码率 %s → %s  (×%.1f)" % (fmt_bps(b["bps"]), fmt_bps(a["bps"]),
                                               a["bps"] / b["bps"]))
    if cmp.get("duration") and info.get("duration"):
        print("    时长    %s → %s  (×%.2f)" % (fmt_dur(cmp["duration"]), fmt_dur(info["duration"]),
                                             info["duration"] / cmp["duration"]))


# --------------------------------------------------------------------------
# ffmpeg 定位
# --------------------------------------------------------------------------

class ToolMissing(Exception):
    pass


def find_tool(name):
    exe = name + (".exe" if os.name == "nt" else "")
    env = os.environ.get(name.upper())
    cands = []
    if env:
        cands.append(env)
    here = os.path.dirname(os.path.abspath(__file__))
    cands += [
        os.path.join(here, "tools", "ffmpeg", "bin", exe),
        os.path.join(here, "tools", "ffmpeg", exe),
    ]
    found = shutil.which(name)
    if found:
        cands.append(found)
    cands += [
        r"C:\ffmpeg\bin\%s" % exe,
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ffmpeg", "bin", exe),
        os.path.join(os.environ.get("ProgramFiles", ""), "ffmpeg", "bin", exe),
    ]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def need_ffmpeg():
    p = find_tool("ffmpeg")
    if not p:
        raise ToolMissing(
            "找不到 ffmpeg。三种解决方式：\n"
            "  1) python videotool.py get-ffmpeg     （下载便携版到 ./tools/ffmpeg）\n"
            "  2) winget install Gyan.FFmpeg         （装到系统后本脚本会自动找到）\n"
            "  3) 设置环境变量 FFMPEG=<ffmpeg.exe 的完整路径>")
    return p


def run_live(cmd, ok_codes=(0,)):
    """运行命令并实时回显 ffmpeg 的进度行。"""
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    tail = []
    buf = b""
    last = 0.0
    while True:
        # read1：有多少读多少，不等凑满 4096 字节；否则进度要攒够一整块才刷新
        chunk = proc.stderr.read1(4096)
        if not chunk:
            break
        buf += chunk
        parts = buf.replace(b"\r", b"\n").split(b"\n")
        buf = parts.pop()
        for raw in parts:
            s = raw.decode("utf-8", "replace").strip()
            if not s:
                continue
            tail.append(s)
            tail = tail[-40:]
            if s.startswith("frame=") or "time=" in s or s.startswith("size="):
                now = time.time()
                if now - last > 0.25:
                    sys.stdout.write("\r  " + s[:100])
                    sys.stdout.flush()
                    last = now
    proc.wait()
    sys.stdout.write("\r" + " " * 102 + "\r")
    if proc.returncode not in ok_codes:
        raise RuntimeError("ffmpeg 失败（exit %d）:\n%s" % (proc.returncode, "\n".join(tail[-20:])))


# --------------------------------------------------------------------------
# 各子命令
# --------------------------------------------------------------------------

def cmd_analyze(args):
    info = analyze_mp4(args.file)
    compare = None
    if args.compare:
        compare = analyze_mp4(args.compare)
    if args.json:
        data = dict(info)
        data["tracks"] = [
            {k: v for k, v in t.items() if isinstance(v, (int, float, str, bool)) or v is None}
            for t in info["tracks"]
        ]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_report(info, compare)
    return 0


def _safe_out(src, out, suffix):
    if out:
        path = out
    else:
        stem, _ = os.path.splitext(src)
        path = stem + suffix
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    return path


def cmd_extract(args):
    info = analyze_mp4(args.file)
    ff = need_ffmpeg()
    out = _safe_out(args.file, args.output, ".extract.mp4")
    if os.path.abspath(out) == os.path.abspath(args.file):
        raise SystemExit("输出文件不能和输入相同")

    cmd = [ff, "-hide_banner", "-nostdin", "-y", "-i", args.file, "-map", "0:v:0"]
    if not args.no_audio:
        cmd += ["-map", "0:a?"]
    cmd += ["-c", "copy", "-map_metadata", "0"]
    v = next((t for t in info["tracks"] if t["kind"] == "video"), None)
    if v and (v.get("codec") or "").startswith("H.265"):
        cmd += ["-tag:v", "hvc1"]
    cmd += ["-movflags", "+faststart", out]

    print("提取视频流（-c copy，无重编码，画质零损失）…")
    print("  " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    t0 = time.time()
    run_live(cmd)
    el = time.time() - t0

    new = analyze_mp4(out)
    print("完成，用时 %.1fs" % el)
    print("  输入 %s  →  输出 %s  (%.1f%%)" % (
        fmt_bytes(info["size"]), fmt_bytes(new["size"]), 100.0 * new["size"] / info["size"]))
    dt = (new["duration"] or 0) - (info["duration"] or 0)
    print("  时长校验：%s vs 原 %s  (差 %+.3fs)" % (
        fmt_dur(new["duration"]), fmt_dur(info["duration"]), dt))
    if abs(dt) > 0.2:
        print("  !! 时长有偏差，检查是否有 edit list / 变速元数据，建议直接重新导出")
    print("  输出：%s" % os.path.abspath(out))
    print("  说明：remux 只重组容器，不会降低码率；体积几乎不变是正常的。")
    return 0


def cmd_shrink(args):
    info = analyze_mp4(args.file)
    dur = info.get("duration")
    if not dur:
        raise SystemExit("无法读取时长，不能自动计算码率；请改用 --crf 模式")
    ff = need_ffmpeg()
    out = _safe_out(args.file, args.output, ".small.mp4")

    v = next((t for t in info["tracks"] if t["kind"] == "video"), None)
    encoder = "libx265" if args.codec == "hevc" else "libx264"
    cmd = [ff, "-hide_banner", "-nostdin", "-y", "-i", args.file,
           "-map", "0:v:0", "-map", "0:a?", "-c:v", encoder, "-preset", args.preset]

    if args.target_mb:
        # 预留 ~4% 给封装开销和编码器过冲
        budget = args.target_mb * 0.96 * 1024 * 1024 * 8 / dur    # bits per second
        audio_bps = args.audio_kbps * 1000
        vbps = max(int(budget - audio_bps), 150_000)
        cmd += ["-b:v", "%dk" % (vbps // 1000),
                "-maxrate", "%dk" % (int(vbps * 1.45) // 1000),
                "-bufsize", "%dk" % (int(vbps * 2.0) // 1000)]
        print("目标体积 %s，总码率预算 %s，视频码率 %s" % (
            fmt_bytes(args.target_mb * 1024 * 1024), fmt_bps(budget), fmt_bps(vbps)))
    else:
        cmd += ["-crf", str(args.crf)]
        print("CRF=%s（数字越小越清晰；x264 建议 20~28，x265 建议 24~32）" % args.crf)

    if args.height:
        cmd += ["-vf", "scale=-2:%d" % args.height]
    if args.codec == "hevc":
        cmd += ["-tag:v", "hvc1"]
    cmd += ["-pix_fmt", "yuv420p"]
    if args.no_audio:
        cmd += ["-an"]
    else:
        cmd += ["-c:a", "aac", "-b:a", "%dk" % args.audio_kbps]
    cmd += ["-movflags", "+faststart", out]

    print("  " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    t0 = time.time()
    run_live(cmd)
    el = time.time() - t0

    new = analyze_mp4(out)
    print("完成，用时 %.1fs" % el)
    print("  %s → %s  (%.1f%%，压掉 %.1f%%)" % (
        fmt_bytes(info["size"]), fmt_bytes(new["size"]),
        100.0 * new["size"] / info["size"], 100.0 * (1 - new["size"] / info["size"])))
    nv = next((t for t in new["tracks"] if t["kind"] == "video"), None)
    if nv and nv.get("bps"):
        print("  新视频码率 %s，%dx%d" % (fmt_bps(nv["bps"]), int(nv.get("width") or 0),
                                      int(nv.get("height") or 0)))
    print("  输出：%s" % os.path.abspath(out))
    return 0


def _download(url, dest):
    start = time.time()
    state = {"t": 0.0}

    def hook(count, block, total):
        now = time.time()
        if now - state["t"] < 0.25 and count * block < total:
            return
        state["t"] = now
        if total > 0:
            done = min(100.0, count * block * 100.0 / total)
            sys.stdout.write("\r  %.1f%%  %s / %s" % (
                done, fmt_bytes(count * block), fmt_bytes(total)))
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, hook)
    sys.stdout.write("\r" + " " * 60 + "\r")
    return time.time() - start


def _wheel_platform_tag():
    if sys.platform == "win32":
        return "win_amd64" if sys.maxsize > 2 ** 32 else "win32"
    if sys.platform == "darwin":
        return "macosx"
    return "manylinux"


def cmd_get_ffmpeg(args):
    here = os.path.dirname(os.path.abspath(__file__))
    bin_dest = os.path.join(here, "tools", "ffmpeg", "bin")
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    target = os.path.join(bin_dest, exe)
    if os.path.isfile(target) and not args.force:
        print("已存在：%s\n如需重新下载请加 --force" % target)
        return 0
    os.makedirs(bin_dest, exist_ok=True)
    tmpdir = os.path.join(here, "tools", "ffmpeg")
    tmp = os.path.join(tmpdir, "download.zip")

    # 优先从 PyPI 的 imageio-ffmpeg wheel 里取二进制：国内下载通常比 gyan.dev 快得多
    ok = False
    try:
        print("从 PyPI 获取 ffmpeg 二进制…")
        meta_url = "https://pypi.org/pypi/imageio-ffmpeg/json"
        meta = json.loads(urllib.request.urlopen(meta_url, timeout=30).read().decode("utf-8"))
        tag = _wheel_platform_tag()
        cands = [u for u in meta.get("urls", [])
                 if u.get("packagetype") == "bdist_wheel" and tag in u["filename"]]
        if not cands:
            raise RuntimeError("PyPI 上没有匹配当前平台的 wheel（%s）" % tag)
        el = _download(cands[0]["url"], tmp)
        with zipfile.ZipFile(tmp) as zf:
            names = [n for n in zf.namelist()
                     if "/binaries/" in n and not n.endswith("/")
                     and os.path.basename(n).startswith("ffmpeg")]
            if not names:
                raise RuntimeError("wheel 里没有找到 ffmpeg 可执行文件")
            with zf.open(names[0]) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
        os.remove(tmp)
        if os.name != "nt":
            os.chmod(target, 0o755)
        print("完成，用时 %.1fs" % el)
        ok = True
    except Exception as ex:
        print("PyPI 方式失败：%s" % ex)

    if not ok:
        print("改用官方静态构建：%s" % FFMPEG_ZIP)
        el = _download(FFMPEG_ZIP, tmp)
        print("\n解压…")
        with zipfile.ZipFile(tmp) as zf:
            for name in zf.namelist():
                base = os.path.basename(name)
                if base in ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"):
                    with zf.open(name) as src, open(os.path.join(bin_dest, base), "wb") as dst:
                        shutil.copyfileobj(src, dst)
        os.remove(tmp)
        print("完成，用时 %.1fs" % el)

    print("  %s" % bin_dest)
    print("  现在可以直接运行 extract / shrink 了。")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        prog="videotool.py",
        description="视频体积审计 / 无损提取 / 重编码压缩",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="分析 MP4 体积构成（不需要 ffmpeg）")
    a.add_argument("file")
    a.add_argument("--compare", help="对照文件（如原素材），比较码率与体积")
    a.add_argument("--json", action="store_true", help="输出 JSON")
    a.set_defaults(func=cmd_analyze)

    e = sub.add_parser("extract", help="无损提取视频流（remux，需 ffmpeg）")
    e.add_argument("file")
    e.add_argument("-o", "--output")
    e.add_argument("--no-audio", action="store_true")
    e.set_defaults(func=cmd_extract)

    s = sub.add_parser("shrink", help="重编码压缩到目标体积或质量（需 ffmpeg）")
    s.add_argument("file")
    s.add_argument("-o", "--output")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--target-mb", type=float, help="目标体积（MB）")
    g.add_argument("--crf", type=float, default=23, help="质量优先模式，默认 23")
    s.add_argument("--codec", choices=["h264", "hevc"], default="h264")
    s.add_argument("--preset", default="medium")
    s.add_argument("--height", type=int, help="缩放到指定高度（宽度自动）")
    s.add_argument("--audio-kbps", type=int, default=128)
    s.add_argument("--no-audio", action="store_true")
    s.set_defaults(func=cmd_shrink)

    gf = sub.add_parser("get-ffmpeg", help="下载便携版 ffmpeg 到 ./tools/ffmpeg")
    gf.add_argument("--force", action="store_true", help="已存在也重新下载")
    gf.set_defaults(func=cmd_get_ffmpeg)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except ToolMissing as ex:
        print(str(ex), file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as ex:
        print("错误：%s" % ex, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
