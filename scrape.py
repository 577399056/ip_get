import requests
import re
import os
# 获取网页内容
url = 'https://ip.164746.xyz/'
timeout=10
response = requests.get(url,timeout=timeout)
# 获取网页内容
html_content = response.text
ip_addresses = re.findall(r">(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})<", html_content)
#ip_addresses_joined = "\n".join(ip_addresses)
#print(str(ip_addresses_joined))

ip_all = ""
for ip in ip_addresses:
    url = "https://www.ip.cn/ip/"+ip+".html"
    response = requests.get(url, timeout=10)
    html_content = response.text
    #print(html_content)
    pattern = re.compile(r'<div id="tab0_address">(.*?)</div>', re.DOTALL)
    match = pattern.search(html_content)
    if match:
        address = match.group(1)
        ip_all += str(ip)+":443#"+str(address)+"\n"

print(ip_all)
# 将内容保存到输出文件中
with open('ip.txt', 'w') as f:
    f.write(ip_all)