import json
import requests
import os
import sys
from pathlib import Path
from datetime import datetime

def fetch_remote_json(url):
    """获取远程JSON数据"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"成功获取远程数据")
        
        # 打印数据基本信息
        if isinstance(data, list):
            print(f"数据格式: 数组，包含 {len(data)} 个元素")
        elif isinstance(data, dict):
            print(f"数据格式: 字典，包含 {len(data)} 个键")
        else:
            print(f"数据格式: {type(data)}")
            
        return data
    except Exception as e:
        print(f"获取远程数据失败: {e}")
        sys.exit(1)

def filter_premium(data):
    """过滤掉group为premium的数据"""
    print("正在过滤group为'premium'的数据...")
    
    if isinstance(data, list):
        # 如果是数组，过滤掉group为premium的元素
        original_count = len(data)
        filtered = []
        removed_count = 0
        
        for item in data:
            if isinstance(item, dict):
                # 检查是否有group字段且值为premium
                if item.get('group') == 'premium':
                    print(f"过滤掉元素: {item.get('name', '无名')} (group: premium)")
                    removed_count += 1
                    continue
            filtered.append(item)
        
        print(f"数组过滤: 原始 {original_count} 条，过滤后 {len(filtered)} 条，移除了 {removed_count} 条")
        return filtered
        
    elif isinstance(data, dict):
        # 如果是字典，可能有不同的结构
        if 'items' in data and isinstance(data['items'], list):
            # 处理items数组
            original_items = data['items']
            filtered_items = []
            removed_count = 0
            
            for item in original_items:
                if isinstance(item, dict) and item.get('group') == 'premium':
                    print(f"过滤掉item: {item.get('name', '无名')} (group: premium)")
                    removed_count += 1
                    continue
                filtered_items.append(item)
            
            print(f"字典items过滤: 原始 {len(original_items)} 条，过滤后 {len(filtered_items)} 条，移除了 {removed_count} 条")
            return {**data, 'items': filtered_items}
            
        else:
            # 普通字典，尝试过滤掉group为premium的项
            filtered = {}
            removed_count = 0
            
            for key, value in data.items():
                if isinstance(value, dict) and value.get('group') == 'premium':
                    print(f"过滤掉键: {key} (group: premium)")
                    removed_count += 1
                    continue
                filtered[key] = value
            
            print(f"字典过滤: 原始 {len(data)} 个键，过滤后 {len(filtered)} 个键，移除了 {removed_count} 个")
            return filtered
            
    print(f"警告: 未知数据类型 {type(data)}，返回原数据")
    return data

def main():
    remote_url = "https://raw.githubusercontent.com/rapier15sapper/ew/refs/heads/main/test.json"
    kv_path = Path("kv.json")
    
    print("开始处理JSON数据...")
    
    # 获取并处理数据
    remote_data = fetch_remote_json(remote_url)
    filtered_data = filter_premium(remote_data)
    
    # 检查本地文件
    has_changes = True
    if kv_path.exists():
        print(f"找到现有文件: {kv_path}")
        try:
            with open(kv_path, 'r', encoding='utf-8') as f:
                local_data = json.load(f)
            
            # 序列化比较
            filtered_str = json.dumps(filtered_data, sort_keys=True, ensure_ascii=False)
            local_str = json.dumps(local_data, sort_keys=True, ensure_ascii=False)
            
            if filtered_str == local_str:
                print("数据无变化，跳过写入")
                has_changes = False
            else:
                print("发现数据变化，将更新文件")
        except Exception as e:
            print(f"读取现有文件失败，将创建新文件: {e}")
    else:
        print(f"未找到 {kv_path}，将创建新文件")
    
    # 写入数据
    if has_changes:
        try:
            with open(kv_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, indent=2, ensure_ascii=False)
            print(f"成功写入文件: {kv_path}")
            
            # 确保文件存在
            if kv_path.exists():
                file_size = kv_path.stat().st_size
                print(f"文件大小: {file_size} 字节")
                
                # 记录更新时间
                timestamp = datetime.now().isoformat()
                with open('last_update.txt', 'w', encoding='utf-8') as f:
                    f.write(f"最后更新时间: {timestamp}\n")
                    f.write(f"原始数据源: {remote_url}\n")
                print("已创建更新时间记录")
            else:
                print(f"错误: 文件 {kv_path} 写入后不存在")
                
        except Exception as e:
            print(f"写入文件失败: {e}")
            sys.exit(1)
    else:
        print("没有变化，不写入文件")
    
    # 输出是否变化的标志，供后续步骤使用
    print(f"::set-output name=has_changes::{str(has_changes).lower()}")
    return has_changes

if __name__ == "__main__":
    main()
