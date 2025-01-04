#!/usr/bin/env python3
import sys

def wrap_long_lines(input_file, max_width=85):
    """
    简单地处理长行，超过指定宽度就换行
    """
    output_file = input_file.rsplit('.', 1)[0] + '.txt'
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        with open(output_file, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                # 去掉行尾的换行符
                line = line.rstrip()
                
                # 如果行长度超过最大宽度，进行分割
                while len(line) > max_width:
                    f_out.write(line[:max_width] + '\n')
                    line = line[max_width:]
                
                # 写入剩余部分
                if line:
                    f_out.write(line + '\n')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python script.py <输入文件> [最大宽度]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    max_width = int(sys.argv[2]) if len(sys.argv) > 2 else 85
    
    wrap_long_lines(input_file, max_width)
    print(f"已处理完成，输出文件为: {input_file.rsplit('.', 1)[0]}.txt")
