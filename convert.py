#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IP 列表生成器：源列表 -> "ip:端口#地区 丨ip"

源文件每行形如:
    1.2.3.4:443#备注 | HK ... | 1.2.3.4:443
    └─ ip:端口 ─┘      └ 地区(可能夹零宽字符)

输出:
    1.2.3.4:443#HK 丨 1.2.3.4

用法:
    python3 convert.py                    # 抓默认源 -> ipv4.txt
    python3 convert.py -u <url> -o out.txt
    python3 convert.py -i local.txt       # 读本地文件
    python3 convert.py -o -               # 输出到 stdout
    python3 convert.py --src-env SRC_URL  # 源地址从环境变量取
    python3 convert.py --sep "|"          # 自定义分隔符(默认 " 丨 ")
"""
import argparse
import os
import re
import sys
import urllib.request

SRC = "https://bestcf.pages.dev/xinyitang3/ipv4.txt"
SEP = " \u4e28 "                        # " 丨 "
ZW = "\u200b\u200c\u200d\u2060\ufeff"   # 零宽/不可见字符，源站用来防抓取

ROW = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d+)#(.*)")
REGION = re.compile(r"\|\s*([A-Z]{2})\b")


def rows(text):
    """产出 (ip, port, region)；没有地区信息的行(头/尾行)自动跳过。"""
    for raw in text.splitlines():
        m = ROW.search(raw)
        if not m:
            continue
        ip, port, comment = m.group(1), m.group(2), m.group(3)
        for ch in ZW:
            comment = comment.replace(ch, "")
        r = REGION.search(comment)
        if r:
            yield ip, port, r.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-u", "--url", help="源地址")
    ap.add_argument("-i", "--input", help="本地输入文件")
    ap.add_argument("-o", "--output", default="ipv4.txt", help="输出文件，- 为 stdout")
    ap.add_argument("--sep", default=SEP, help='ip 与 地区 之间的分隔符')
    ap.add_argument("--src-env", help="从该环境变量读取源地址")
    a = ap.parse_args()

    url = (os.environ.get(a.src_env) if a.src_env else None) or a.url or SRC
    if a.input:
        text = open(a.input, encoding="utf-8", errors="replace").read()
        src = a.input
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        src = url

    seen, data = set(), []
    for ip, port, region in rows(text):
        if ip not in seen:
            seen.add(ip)
            data.append((region, tuple(int(x) for x in ip.split(".")), ip, port))
    if not data:
        sys.exit("ERROR: 未解析到任何条目，源格式可能变了: %s" % src)

    data.sort()
    out = "".join("%s:%s#%s%s%s\n" % (ip, port, rg, a.sep, ip)
                  for rg, _, ip, port in data)

    if a.output == "-":
        sys.stdout.write(out)
    else:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(out)
    print("OK  %d 条  <- %s" % (len(data), src), file=sys.stderr)


if __name__ == "__main__":
    main()
