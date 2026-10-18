# 抖音 a_bogus 签名复现 - iv8 + bdms SDK
#
# 使用方法:
#   python abogus.py --aweme_id=7682671884655596901 --cursor=0 --count=10
#   python abogus.py --aweme_id=7682671884655596901 --cookie_file=cookies.json

import requests
from urllib.parse import urlencode, urlparse, parse_qs
import iv8
import argparse
import os
import json
from loguru import logger
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BDMS_JS_PATH = os.path.join(SCRIPT_DIR, "bdms_1.0.1.19_fix.js")

with open(BDMS_JS_PATH, 'r', encoding='utf-8') as f:
    BDMS_JS = f.read()

DEFAULT_ENVIRONMENT = {
    "location": {
        "href": "https://www.douyin.com/video/7682671884655596901",
        "origin": "https://www.douyin.com",
        "protocol": "https:", "host": "www.douyin.com",
        "hostname": "www.douyin.com", "port": "",
        "pathname": "/video/7682671884655596901",
        "search": "", "hash": ""
    },
    "navigator": {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "language": "zh-CN", "languages": ["zh-CN", "zh", "en"],
    },
}


def generate_abogus(base_url, params, environment=None):
    """使用 iv8 + bdms SDK 生成带 a_bogus 的完整 URL"""
    if environment is None:
        environment = DEFAULT_ENVIRONMENT

    with iv8.JSContext(environment=environment) as ctx:
        ctx.eval('''window.MessageChannel = __iv8__.wrapNative(function() {
            const port1 = { onmessage: null };
            const port2 = { onmessage: null };
            port1.postMessage = function(data) {
                if (port2.onmessage) setTimeout(() => port2.onmessage({data}), 0);
            };
            port2.postMessage = function(data) {
                if (port1.onmessage) setTimeout(() => port1.onmessage({data}), 0);
            };
            return { port1, port2 };
        }, "MessageChannel");''')
        ctx.eval(BDMS_JS)
        ctx.eval('''window.bdms.init({"aid": 6383, "pageId": 6241, "paths": ["^/webcast/", "^/aweme/v1/", "^/aweme/v2/", "/douplus/", "/v1/message/send", "^/live/", "^/captcha/", "^/ecom/", "^/luna/pc"], "boe": false, "ddrt": 8.5, "ic": 8.5});''')

        query_string = urlencode(params, safe='*')
        request_url = f"{base_url}?{query_string}"

        result = ctx.eval(f'''
            var xhr = new XMLHttpRequest();
            xhr.open('GET', "{request_url}", true);
            xhr.send(null);
            window.__iv8__.netLog.entries;
        ''', to_py=True)

        if result and len(result) > 0:
            # logger.info("abogus:%s"%result[0]["url"])
            return result[0]["url"]
        else:
            raise RuntimeError("iv8 未能捕获请求")


def fetch_comment_list(aweme_id, cursor=0, count=10, cookies=None, environment=None):
    """获取抖音视频评论列表"""
    base_url = "https://www.douyin.com/aweme/v1/web/comment/list/"
    params = {
        "device_platform": "webapp", "aid": "6383",
        "channel": "channel_pc_web", "aweme_id": aweme_id,
        "cursor": str(cursor), "count": str(count),
        "item_type": "0", "insert_ids": "",
        "whale_cut_token": "", "cut_version": "1",
        "rcFT": "", "update_version_code": "170400",
        "pc_client_type": "1", "pc_libra_divert": "Windows",
        "support_h265": "1", "support_dash": "1",
        "cpu_core_num": "16", "version_code": "170400",
        "version_name": "17.4.0", "cookie_enabled": "true",
        "screen_width": "1707", "screen_height": "960",
        "browser_language": "zh-CN", "browser_platform": "Win32",
        "browser_name": "Chrome", "browser_version": "145.0.0.0",
        "browser_online": "true", "engine_name": "Blink",
        "engine_version": "145.0.0.0", "os_name": "Windows",
        "os_version": "10", "device_memory": "8", "platform": "PC",
        "downlink": "2.7", "effective_type": "4g",
        "round_trip_time": "100",
    }

    full_url = generate_abogus(base_url, params, environment)
    a_bogus = parse_qs(urlparse(full_url).query).get("a_bogus", [""])[0]
    print(f"[a_bogus] {a_bogus[::]}")

    headers = {
        "authority": "www.douyin.com",
        "accept": "application/json, text/plain, */*",
        "referer": f"https://www.douyin.com/video/{aweme_id}",
        "user-agent": DEFAULT_ENVIRONMENT["navigator"]["userAgent"],
    }
    resp = requests.get(full_url, headers=headers, cookies=cookies, timeout=15)
    data = resp.json()
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抖音 a_bogus 签名复现")
    parser.add_argument("--aweme_id", default="7682671884655596901")
    parser.add_argument("--cursor", type=int, default=0)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--cookie_file", default=None, help="cookies.json 文件路径")
    args = parser.parse_args()

    # 加载 cookies
    cookies = None
    cookie_file = args.cookie_file or os.path.join(SCRIPT_DIR, "cookies.json")
    if os.path.exists(cookie_file):
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        print(f"[cookies] loaded from {cookie_file}, keys: {list(cookies.keys())[:5]}...")

    print(f"=== 视频 {args.aweme_id} 评论列表 (cursor={args.cursor}, count={args.count}) ===")
    data = fetch_comment_list(args.aweme_id, args.cursor, args.count, cookies)

    status_code = data.get("status_code")
    print(f"\n[API status_code] {status_code}")

    comments = data.get("comments", [])
    print(f"[comments count] {len(comments)}")
    print(f"[has_more] {data.get('has_more')}")
    print(f"[cursor] {data.get('cursor')}")
    print(f"[extra] {data.get('extra', {})}")
    print()

    for i, c in enumerate(comments):
        user = c.get("user", {})
        nickname = user.get("nickname", "unknown")
        uid = user.get("uid", "")
        text = c.get("text", "")
        digg_count = c.get("digg_count", 0)
        reply_count = c.get("reply_comment_total", 0)
        create_time = c.get("create_time", 0)
        print(f"  [{i}] @{nickname} (uid={uid})")
        print(f"      {text[:80]}")
        print(f"      点赞:{digg_count} 回复:{reply_count} 时间:{create_time}")
        print()

    # 保存原始响应
    out_file = os.path.join(SCRIPT_DIR, "comment_response.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[saved] {out_file}")
