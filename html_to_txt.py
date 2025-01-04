import os
import sys
from bs4 import BeautifulSoup

def html_to_txt(file_path):
    # 确保文件是HTML文件
    if not file_path.endswith(".html"):
        print("输入的文件不是HTML文件，请提供一个以 .html 结尾的文件。")
        return
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件 {file_path} 不存在，请检查路径。")
        return
    
    # 读取HTML文件内容
    with open(file_path, 'r', encoding='utf-8') as html_file:
        soup = BeautifulSoup(html_file, 'html.parser')
        text = soup.get_text()  # 获取所有的文本内容
    
    # 创建输出文件路径，后缀改为.txt
    base_name = os.path.splitext(file_path)[0]
    txt_file_path = base_name + ".txt"
    
    # 写入到TXT文件
    with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write(text)
    
    print(f"文件已成功转换为：{txt_file_path}")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python script.py <html_file_path>")
        sys.exit(1)
    
    # 获取文件路径参数
    html_file_path = sys.argv[1]
    html_to_txt(html_file_path)
