import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse
import subprocess
import time
import os

def extract_video_urls(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://cn.pornhub.com/'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for script in soup.find_all('script'):
        script_content = script.string
        if not script_content:
            continue
        
        pattern = r'var\s+flashvars_\d+\s*=\s*({.*?})\s*;'
        match = re.search(pattern, script_content, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                json_str = json_str.replace('\t', ' ')
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                data = json.loads(json_str)
                media_definitions = data.get('mediaDefinitions', [])
                
                video_urls = []
                for md in media_definitions:
                    video_url = md.get('videoUrl')
                    if video_url:
                        parsed = urlparse(video_url)
                        if parsed.netloc != 'cn.pornhub.com':
                            video_urls.append(video_url)
                
                return video_urls
                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                continue
                
    return []

def download_video(m3u8_url, output_file):
    command = [
        "streamlink",
        m3u8_url,
        "best",
        "-o",
        output_file,
        "--force",  # 强制覆盖已存在文件
        "--retry-streams", "3",  # 重试次数
        "--retry-max", "5"  # 最大重试次数
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"下载失败: {result.stderr}")
        raise RuntimeError("视频下载失败")
    else:
        print(f"下载成功: {output_file}")

def process_downloads_from_file(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split(',')
            if len(parts) < 2:
                print(f"第 {line_num} 行格式错误，跳过: {line}")
                continue
            
            target_url = parts[0].strip()
            video_param = parts[1].strip()
            output_file = parts[2].strip() if len(parts) > 2 else None
            
            print(f"正在处理: {target_url}")
            try:
                video_urls = extract_video_urls(target_url)
                if not video_urls:
                    print("未提取到有效视频链接")
                    continue
                
                filtered_urls = [url for url in video_urls if video_param in url]
                if not filtered_urls:
                    print(f"未找到包含参数 '{video_param}' 的视频链接")
                    continue
                
                selected_url = filtered_urls[0]
                
                if not output_file:
                    timestamp = int(time.time())
                    output_file = f"downloads/video_{video_param}_{timestamp}.mp4"
                
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                print(f"开始下载: {selected_url}")
                download_video(selected_url, output_file)
                
            except Exception as e:
                print(f"处理失败: {str(e)}")
                continue

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    process_downloads_from_file("download_list.txt")
