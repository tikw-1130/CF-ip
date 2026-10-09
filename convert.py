#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BestCF ipv4.txt -> "REGION IP" 排序列表

输入(源)每行形如:
    2.27.109.35:443#Mia优选 | HK TG:@MiaChatChannel | 2.27.109.35:443
    ^^^^^^^^^^^^^^^^  ip:port          ^^ 地区(可能夹着零宽字符)
输出:
    HK 2.27.109.35
    ...
按 (地区, IP) 排序。

用法:
    python convert.py                      # 用内置源地址
    python convert.py -i local.txt         # 读本地文件
    python convert.py -u https://... -o ipv4.txt
    python convert.py --with-port         # 输出 "HK 2.27.109.35:443"
    python convert.py --src-env SRC_URL   # 从环境变量取源地址
"""
import argparse
import os
import re
import sys
import urllib.request

DEFAULT_SRC = "https://bestcf.pages.dev/xinyitang3/ipv4.txt"

# 零宽 / 不可见字符，源站用来防止抓取，必须清掉
INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"

IPV4_RE = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
REGION_RE = re.compile(r"\|\s*([A-Z]{2})\b")


def clean(s: str) -> str:
    for ch in INVISIBLE:
        s = s.replace(ch, "")
    return s


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (bestcf-auto)"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse(text: str):
    """返回 {ip: region}，按出现顺序记录，重复 IP 保留第一次的地区。"""
    result = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "#" not in line:
            continue
        host, comment = line.split("#", 1)

        m_ip = IPV4_RE.search(host)
        if not m_ip:
            continue
        ip = m_ip.group(0)

        comment = clean(comment)
        m_rg = REGION_RE.search(comment)
        if not m_rg:
            # 没有地区信息(源站的头/尾行)，跳过
            continue
        region = m_rg.group(1)

        if ip not in result:
            result[ip] = region
    return result


def ip_key(ip: str):
    return tuple(int(x) for x in ip.split("."))


def build(pairs, with_port=False, ports=None):
    lines = []
    for ip, region in sorted(pairs.items(), key=lambda kv: (kv[1], ip_key(kv[0]))):
        if with_port and ports:
            lines.append("%s %s:%s" % (region, ip, ports.get(ip, "443")))
        else:
            lines.append("%s %s" % (region, ip))
    return "\n".join(lines) + "\n"


def collect_ports(text: str):
    ports = {}
    for raw in text.splitlines():
        line = raw.strip()
        if "#" not in line:
            continue
        host = line.split("#", 1)[0].strip()
        m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d+)", host)
        if m:
            ports[m.group(1)] = m.group(2)
    return ports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-u", "--url", default=None, help="源地址")
    ap.add_argument("-i", "--input", default=None, help="本地输入文件")
    ap.add_argument("-o", "--output", default="ipv4.txt", help="输出文件")
    ap.add_argument("--with-port", action="store_true", help="输出带端口")
    ap.add_argument("--src-env", default=None, help="从该环境变量读取源地址")
    args = ap.parse_args()

    url = args.url
    if args.src_env and os.environ.get(args.src_env):
        url = os.environ[args.src_env]
    if not url:
        url = DEFAULT_SRC

    if args.input:
        with open(args.input, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        src_desc = args.input
    else:
        text = fetch(url)
        src_desc = url

    pairs = parse(text)
    if not pairs:
        print("ERROR: 没有解析到任何条目，源格式可能变了: %s" % src_desc, file=sys.stderr)
        sys.exit(1)

    ports = collect_ports(text) if args.with_port else None
    out = build(pairs, with_port=args.with_port, ports=ports)

    if args.output == "-":
        sys.stdout.write(out)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)

    regions = {}
    for r in pairs.values():
        regions[r] = regions.get(r, 0) + 1
    summary = " ".join("%s=%d" % (k, regions[k]) for k in sorted(regions))
    print("OK  %d 条  <- %s" % (len(pairs), src_desc), file=sys.stderr)
    print("地区: %s" % summary, file=sys.stderr)


if __name__ == "__main__":
    main()
