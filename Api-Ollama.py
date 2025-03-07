import argparse
import requests
import random
import json
import os
import time
from tabulate import tabulate
from datetime import datetime, timedelta
from requests.exceptions import RequestException, Timeout, SSLError, ConnectionError
import pyfiglet
from termcolor import colored
from colorama import init, Fore, Style

# 初始化 colorama
init(autoreset=True)

def print_banner():
    """打印彩色艺术字，并在右下角显示作者和项目地址"""
    ascii_art = pyfiglet.figlet_format("API-Ollama")  # 生成艺术字

    # 颜色列表，随机选择颜色
    colors = ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    colored_art = "\n".join([colored(line, random.choice(colors)) for line in ascii_art.split("\n")])

    author_info = f"{Fore.CYAN}{' ' * 50}-- Author: Pstar{Style.RESET_ALL}"
    project_url = f"{Fore.CYAN}{' ' * 50}https://github.com/PstarSec{Style.RESET_ALL}"

    print(colored_art)  # 彩色艺术字
    print(author_info)  # 右下角作者信息
    print(project_url)  # 右下角项目地址

def set_proxy(proxy_url):
    # 判断是否是 SOCKS 代理
    if proxy_url:
        if proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://"):
            return {
                "http": proxy_url,
                "https": proxy_url
            }
        else:
            return {
                "http": proxy_url,
                "https": proxy_url
            }
    return None

def random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36"
    ]
    return random.choice(user_agents)

def bytes_to_gb(size):
    return f"{size / (1024 ** 3):.2f} GB"

def convert_to_beijing_time(iso_time):
    # 处理时间字符串的时区部分，例如 +08:00
    try:
        # 去掉末尾的 'Z'
        iso_time = iso_time.rstrip('Z')
        
        # 如果包含毫秒部分，则裁剪到秒
        if '.' in iso_time:
            iso_time = iso_time.split('.')[0]
        
        # 如果有时区偏移部分，去除并处理
        if '+' in iso_time or '-' in iso_time:
            iso_time = iso_time[:19]
        
        # 将时间字符串转换为 UTC 时间
        utc_time = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S")
        
        # 北京时间比 UTC 时间多 8 小时
        beijing_time = utc_time + timedelta(hours=8)
        
        return beijing_time.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return f"时间解析错误: {str(e)}"

def test_url(target_url, proxies=None, timeout=6):
    url = f"{target_url.rstrip('/')}/api/tags"
    headers = {"User-Agent": random_user_agent()}
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            if models:
                model_info = [[
                    model['model'],
                    convert_to_beijing_time(model['modified_at']),
                    bytes_to_gb(model['size']),
                    model['details']['parameter_size'],
                    model['details']['quantization_level']
                ] for model in models]
                return target_url, model_info, len(models), True
            else:
                return target_url, "返回值为空，不存在", 0, False
        else:
            return target_url, f"状态码: {response.status_code}，不存在", 0, False
    except SSLError as ssl_error:
        return target_url, f"请求失败: SSL 错误 - {ssl_error}", 0, False
    except Timeout as timeout_error:
        return target_url, f"请求失败: 超时错误 - {timeout_error}", 0, False
    except ConnectionError as conn_error:
        return target_url, f"请求失败: 连接错误 - {conn_error}", 0, False
    except RequestException as req_error:
        return target_url, f"请求失败: 网络错误 - {req_error}", 0, False
    except Exception as e:
        return target_url, f"请求失败: 未知错误 - {str(e)}", 0, False

def handle_single_url(target_url, proxies, timeout):
    result = test_url(target_url, proxies, timeout)
    color = "\033[92m" if result[3] else "\033[91m"
    print(f"{color}{result[0]}\033[0m")
    if isinstance(result[1], list):
        print(tabulate(result[1], headers=["模型", "修改时间", "大小", "参数大小", "量化级别"], tablefmt="fancy_grid"))
        print(f"模型数量: {result[2]}")
    else:
        print(result[1])

def handle_bulk_urls(file_path, output_path, proxies, timeout):
    if not os.path.exists(file_path):
        print(f"文件 {file_path} 不存在")
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    exists, not_exists = [], []
    for url in urls:
        result = test_url(url, proxies, timeout)
        color = "\033[92m" if result[3] else "\033[91m"
        print(f"{color}{result[0]}\033[0m")
        if isinstance(result[1], list):
            print(tabulate(result[1], headers=["模型", "修改时间", "大小", "参数大小", "量化级别"], tablefmt="fancy_grid"))
            print(f"模型数量: {result[2]}")
        else:
            print(result[1])
        if result[3]:
            exists.append(result[0])
        else:
            not_exists.append(result[0])
    
    print(f"\n\033[92m存在的 URL ({len(exists)})\033[0m")
    for url in exists:
        print(f"\033[92m{url}\033[0m")
    
    print(f"\n\033[91m不存在的 URL ({len(not_exists)})\033[0m")
    for url in not_exists:
        print(f"\033[91m{url}\033[0m")
    
    stats_table = [["类别", "数量"], ["存在的 URL", len(exists)], ["不存在的 URL", len(not_exists)]]
    print("\n统计结果：")
    print(tabulate(stats_table, headers="firstrow", tablefmt="fancy_grid"))
    
    timestamp = time.strftime('%Y%m%d%H%M%S')
    output_file = output_path if output_path else f"out_{timestamp}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("存在的 URL:\n" + "\n".join(exists) + "\n\n不存在的 URL:\n" + "\n".join(not_exists) + "\n")
        f.write("\n统计结果：\n")
        f.write(tabulate(stats_table, headers=["类别", "数量"], tablefmt="fancy_grid"))

if __name__ == "__main__":
    print_banner()  # 先打印艺术字
    
    parser = argparse.ArgumentParser(description="Ollama 批量扫描工具")
    parser.add_argument("-u", help="测试单个地址")
    parser.add_argument("-ul", help="批量测试文件路径")
    parser.add_argument("-o", help="输出文件路径")
    parser.add_argument("-proxy", help="使用代理，例如 -proxy=http://127.0.0.1:8080 或 socks5://127.0.0.1:1080")
    parser.add_argument("-t", type=int, default=6, help="设置请求超时时间，单位：秒，默认 6 秒")
    
    args = parser.parse_args()
    proxies = set_proxy(args.proxy)
    
    if args.u:
        handle_single_url(args.u, proxies, args.t)
    if args.ul:
        handle_bulk_urls(args.ul, args.o, proxies, args.t)
