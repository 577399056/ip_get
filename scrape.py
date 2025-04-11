import requests
import re
import time
import json

# 获取网页内容并带有重试机制
def fetch_with_retries(url, timeout=10, retries=3, delay=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()  # 确保状态码为 200
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"[{attempt+1}/{retries}] 请求失败：{url}，错误：{e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print("多次重试失败，跳过该请求。")
    return None

# 提取前 10 个 IP 列表
def get_ip_list(ip_source_url):
    html = fetch_with_retries(ip_source_url)
    if not html:
        return []
    ip_all = re.findall(r">(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})<", html)
    return ip_all[:10]  # 只取前 10 个

# 获取每个 IP 的归属地
def get_ip_address(ip):
    #detail_url = f"https://www.ip.cn/ip/{ip}.html"
    detail_url = f"https://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true"
    html = fetch_with_retries(detail_url)
    if not html:
        return "未知地址"
    data = json.loads(text)
    addr = data.get("addr", "")  
    return addr
    #match = re.search(r'<div id="tab0_address">(.*?)</div>', html, re.DOTALL)
    #if match:
        #return match.group(1).strip()
    #return "未知地址"

# 主逻辑封装
def main():
    ip_source_url = "https://cf.090227.xyz/"
    ip_list = get_ip_list(ip_source_url)

    if not ip_list:
        print("未获取到任何 IP。")
        return

    print(f"共获取到 {len(ip_list)} 个 IP，开始查询归属地...")

    results = []
    for ip in ip_list:
        address = get_ip_address(ip)
        results.append(f"{ip}:443#{address}")
        #results.append(f"{ip}:443#weizhi")
        print(f"{ip} → {address}")
        #print(f"{ip}")
        time.sleep(0.5)  # 避免访问过快被封

    # 写入文件
    with open("ip.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print("\n✅ 查询完成，已保存到 ip.txt")

if __name__ == "__main__":
    main()
