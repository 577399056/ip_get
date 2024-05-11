import requests

# 获取网页内容
url = 'https://ip.164746.xyz/'
timeout=10
response = requests.get(url,timeout=timeout)
# 获取网页内容
html_content = response.text
print(html_content)
# 将内容保存到输出文件中
with open('output.txt', 'w') as f:
    f.write(html_content)