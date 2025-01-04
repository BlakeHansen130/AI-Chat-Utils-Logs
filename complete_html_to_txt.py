import os
import sys
import shutil

def copy_html_to_txt(file_path):
    # 确保文件是HTML文件
    if not file_path.endswith(".html"):
        print("输入的文件不是HTML文件，请提供一个以 .html 结尾的文件。")
        return
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件 {file_path} 不存在，请检查路径。")
        return
    
    # 创建输出文件路径，后缀改为 .txt
    base_name = os.path.splitext(file_path)[0]
    txt_file_path = base_name + ".txt"
    
    # 复制原文件内容到新文件
    shutil.copyfile(file_path, txt_file_path)
    
    print(f"文件已成功复制为：{txt_file_path}")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python script.py <html_file_path>")
        sys.exit(1)
    
    # 获取文件路径参数
    html_file_path = sys.argv[1]
    copy_html_to_txt(html_file_path)
