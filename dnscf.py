import requests
import time
import os
import json
import re
import ipaddress

# ====================== 【配置区 - 可以直接修改参数】 ======================
# 优选接口地址（电信）
IP_SOURCE_URL = "https://cf.vvhan.com/api/ip"
MAX_IP_COUNT = 6               # 需要维护多少条DNS A记录
UPDATE_SLEEP_SEC = 1          # CF每次更新之间间隔秒数
FETCH_TIMEOUT = 10             # http请求超时
RETRY_TIMES = 3                # 请求重试次数
RETRY_DELAY = 3                # 重试间隔

NOTIFY_WHEN_NO_CHANGE = True   # True:即使没有DNS变更也推送消息；False：只有发生变更才推送
ENABLE_PUSH = True             # 推送总开关

# ====================== 环境变量（青龙面板设置） ======================
CF_API_TOKEN = os.environ["CF_API_TOKEN"]
CF_ZONE_ID = os.environ["CF_ZONE_ID"]
CF_DNS_NAME = os.environ["CF_DNS_NAME"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]

HEADERS_CF = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}


def send_pushplus(content: str):
    """
    使用PushPlus发送微信推送通知，并检测推送是否成功
    :param content: 需要推送的文本消息内容
    :return bool: True推送成功 / False推送失败
    """
    if not ENABLE_PUSH:
        print("推送已关闭，跳过pushplus")
        return False
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "IP优选DNSCF推送",
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }
    try:
        resp = requests.post(url,
                             data=json.dumps(data).encode("utf-8"),
                             headers={'Content-Type': 'application/json'},
                             timeout=15)
        resp.raise_for_status()
        print("Pushplus推送发送完成")
        return True
    except Exception as e:
        print(f"Pushplus推送失败！e:{str(e)}")
        return False


def fetch_with_retries(url, timeout=10, retries=3, delay=3):
    """
    HTTP GET请求封装，自带重试机制，网络失败自动重试指定次数
    :param url: 需要访问的目标网址
    :param timeout: 请求超时时间，单位秒
    :param retries: 最大重试次数
    :param delay: 每次重试之间的等待间隔，单位秒
    :return: 成功返回网页文本内容；全部失败后返回 None
    """
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout, headers=req_headers)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            print(f"[{attempt+1}/{retries}] 请求失败 {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None


def is_valid_ipv4(ip_str: str) -> bool:
    """
    校验字符串是否是合法IPv4地址
    :param ip_str: ip字符串
    :return True合法IPv4 / False非法
    """
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def get_ip_list(ip_source_url: str, max_num: int):
    """
    从优选IP网页接口获取ip列表，正则提取 + ip合法性校验 + 去重
    :param ip_source_url: IP优选接口地址
    :param max_num: 返回最多多少个ip
    :return: list[str] 清洗之后的ip数组；失败返回空列表[]
    """
    html = fetch_with_retries(ip_source_url, timeout=FETCH_TIMEOUT, retries=RETRY_TIMES, delay=RETRY_DELAY)
    if not html:
        print("优选IP接口请求失败！")
        return []
    raw_matches = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", html)
    valid_ips = []
    seen = set()
    for item in raw_matches:
        if is_valid_ipv4(item) and item not in seen:
            seen.add(item)
            valid_ips.append(item)
        if len(valid_ips) >= max_num:
            break
    print(f"清洗之后有效优选IP列表: {valid_ips}")
    return valid_ips


def get_dns_records(name: str):
    """
    调用Cloudflare API，读取指定域名现有的全部DNS A记录信息
    :param name: 查询的域名
    :return: dict, key = dns记录ID，value = 当前解析的IP地址；API失败返回空字典 {}
    """
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records'
    try:
        resp = requests.get(url, headers=HEADERS_CF, timeout=15)
        if resp.status_code == 429:
            print("⚠️Cloudflare API触发限流(429)！")
            return {}
        if resp.status_code != 200:
            print('Error fetching DNS records:', resp.text)
            return {}
        record_map = {}
        for r in resp.json()["result"]:
            if r["name"] == name and r["type"] == "A":
                record_map[r["id"]] = r["content"]
        return record_map
    except Exception as e:
        print(f"获取DNS记录发生异常：{str(e)}")
        return {}


def update_dns_record(record_id: str, name: str, cf_ip: str):
    """
    更新单条Cloudflare的DNS A记录（仅修改已存在记录，不会新建）
    :param record_id: 需要修改的DNS记录唯一ID
    :param name: 域名名称
    :param cf_ip: 设置新优选IP地址
    :return: str 返回本次更新结果消息；None=更新异常
    """
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record_id}'
    payload = {"type": "A", "name": name, "content": cf_ip}
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        resp = requests.put(url, headers=HEADERS_CF, json=payload, timeout=15)
        if resp.status_code == 429:
            msg = f"[{t}] ip:{cf_ip} 更新失败，CF接口限流429！"
            print(msg)
            return msg
        if resp.status_code == 200:
            msg = f"[{t}] ip:{cf_ip} 解析 {name} 成功"
            print(msg)
            return msg
        else:
            msg = f"[{t}] ip:{cf_ip} 解析 {name} 失败，resp:{resp.text}"
            print(msg)
            return msg
    except Exception as e:
        msg = f"[{t}] ip:{cf_ip} 更新DNS异常，e:{str(e)}"
        print(msg)
        return msg


def get_dns_list(ip_list: list, dns_records: dict):
    """
    对比优选ip列表和当前CF上已有的DNS记录，筛选哪些ip需要更新，哪些旧记录ID可以复用
    :param ip_list: 新一批优选IP数组
    :param dns_records: 当前域名DNS字典 {dns_id: ip}
    :return new_ip_need: list 需要写入的新ip列表；unused_record_ids: list 可复用旧DNS记录ID
    """
    unused_record_ids = [k for k, v in dns_records.items() if v not in ip_list]
    new_ip_need = [ip for ip in ip_list if ip not in dns_records.values()]
    return new_ip_need, unused_record_ids


def main():
    """
    主函数执行一次完整优选DNS更新流程
    """
    start_time = time.time()
    push_content = []
    # 获取优选IP
    ip_list = get_ip_list(IP_SOURCE_URL, MAX_IP_COUNT)
    if len(ip_list) == 0:
        push_content.append("❌错误：优选IP接口返回为空，本次脚本结束")
        report_text = "\n".join(push_content)
        send_pushplus(report_text)
        print(report_text)
        return

    # 获取当前CF dns记录
    dns_map = get_dns_records(CF_DNS_NAME)
    if not dns_map:
        push_content.append("❌错误：读取Cloudflare DNS记录失败！检查token/zid权限")
        report_text = "\n".join(push_content)
        send_pushplus(report_text)
        print(report_text)
        return
    print("当前CF DNS记录：", dns_map)

    ip_need_update, rec_id_list = get_dns_list(ip_list, dns_map)
    print(f"待更新IP:{ip_need_update},可复用DNSID:{rec_id_list}")

    if len(ip_need_update) == 0:
        info_msg = "✅本次检测：优选IP和现有DNS完全一致，无需任何更新"
        push_content.append(info_msg)
    else:
        for idx, ip in enumerate(ip_need_update):
            if idx >= len(rec_id_list):
                push_content.append(f"⚠️DNS记录数量不足，剩余{len(ip_need_update)-idx}个IP跳过更新，请预先多创建A记录！")
                break
            res = update_dns_record(rec_id_list[idx], CF_DNS_NAME, ip)
            push_content.append(res)
            time.sleep(UPDATE_SLEEP_SEC)

    # 统计运行耗时
    cost = round(time.time() - start_time,2)
    push_content.append(f"\n脚本运行耗时 {cost} s")
    report_text = "\n".join(push_content)
    print("====运行报告====")
    print(report_text)
    if NOTIFY_WHEN_NO_CHANGE or len(ip_need_update) > 0:
        send_pushplus(report_text)


if __name__ == '__main__':
    main()
