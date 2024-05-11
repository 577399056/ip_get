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
ip_addresses_joined = "\n".join(ip_addresses)
print(str(ip_addresses_joined))
# 将内容保存到输出文件中
#with open('ip.txt', 'w') as f:
    #f.write(ip_addresses_joined)