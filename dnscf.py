import requests
import traceback
import time
import os
import json
import re


# API 密钥
CF_API_TOKEN    =   os.environ["CF_API_TOKEN"]
CF_ZONE_ID      =   os.environ["CF_ZONE_ID"]
CF_DNS_NAME     =   os.environ["CF_DNS_NAME"]

# pushplus_token
PUSHPLUS_TOKEN  =   os.environ["PUSHPLUS_TOKEN"]

headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_cf_speed_test_ip(timeout=10, max_retries=5):
    for attempt in range(max_retries):
        try:
            # 发送 GET 请求，设置超时
            response = requests.get('https://ip.164746.xyz/ipTop.html', timeout=timeout)
            # 检查响应状态码
            if response.status_code == 200:
                return response.text
        except Exception as e:
            traceback.print_exc()
            print(f"get_cf_speed_test_ip Request failed (attempt {attempt + 1}/{max_retries}): {e}")
    # 如果所有尝试都失败，返回 None 或者抛出异常，根据需要进行处理
    return None

# 获取 DNS 记录
def get_dns_records(name):
    def_info = []
    cfdns = {}
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records'
    response = requests.get(url, headers=headers)
    #print(response.text)
    if response.status_code == 200:
        records = response.json()['result']
        #print(records)
        for record in records:
            if record['name'] == name:
                cfdns[record['id']] = record['content']
                #def_info.append(record['id'])
        #return def_info
        #print(cfdns)
        return cfdns
    else:
        print('Error fetching DNS records:', response.text)

# 更新 DNS 记录
def update_dns_record(record_id, name, cf_ip):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record_id}'
    data = {
        'type': 'A',
        'name': name,
        'content': cf_ip
    }

    response = requests.put(url, headers=headers, json=data)
    #print(response.text)
    if response.status_code == 200:
        print(f"cf_dns_change success: ---- Time: " + str(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + " ---- ip：" + str(cf_ip))
        return "ip:" + str(cf_ip) + "解析" + str(name) + "成功"
    else:
        traceback.print_exc()
        print(f"cf_dns_change ERROR: ---- Time: " + str(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + " ---- MESSAGE: ")# + str(e))
        return "ip:" + str(cf_ip) + "解析" + str(name) + "失败"

# 消息推送
def push_plus(content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "IP优选DNSCF推送",
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }
    body = json.dumps(data).encode(encoding='utf-8')
    headers = {'Content-Type': 'application/json'}
    requests.post(url, data=body, headers=headers)

# 获取网页内容并带有重试机制
def fetch_with_retries(url, timeout=10, retries=3, delay=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)#, headers=headers)
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
    return ip_all[:1]  # 只取前 10 个

# 筛选最终更新的ip
def get_dns_list(ip_list, dns_records):
    #ip_list = ['104.16.148.17', '104.16.237.246']
    #dns = dns_records
    d = []
    for k, v in dns_records.items():
        #print(k,v)
        if v not in ip_list:
            #d[k] = v
            d.append(k)
        else:
            ip_list.remove(v)
    print("最终更新内容",ip_list,d)
    #if len(ip_list) > 0 and len(d) > 0:
    return ip_list,d
    
    
# 主函数
def main():
    ip_source_url = "https://cf.090227.xyz/"
    ip_list = get_ip_list(ip_source_url)
    #ip_list = ""
    print("获取的优选ip",ip_list)
    # 获取最新优选IP
    #ip_addresses_str = get_cf_speed_test_ip()
    #print(ip_addresses_str)
    #ip_addresses = ip_addresses_str.split(',')
    #print(ip_addresses)
    dns_records = get_dns_records(CF_DNS_NAME)
    print("当前cf上的dns记录",dns_records)
    ip_addresses,dns_records = get_dns_list(ip_list,dns_records)
    push_plus_content = []
    # 遍历 IP 地址列表
    for index, ip_address in enumerate(ip_addresses):
        # 执行 DNS 变更
        dns = update_dns_record(dns_records[index], CF_DNS_NAME, ip_address)
        push_plus_content.append(dns)

    push_plus('\n'.join(push_plus_content))

if __name__ == '__main__':
    main()
