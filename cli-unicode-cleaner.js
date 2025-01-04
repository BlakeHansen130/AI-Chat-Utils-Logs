#!/usr/bin/env node

const fs = require('fs').promises;
const path = require('path');

function removeSpecificUnicode(text) {
    // 精确匹配 U+E203 和 U+E204
    const regex = /[\uE203\uE204]/gu;
    return text.replace(regex, '');
}

function getStats(originalText, cleanedText) {
    const originalLength = originalText.length;
    const cleanedLength = cleanedText.length;
    const removedCount = originalLength - cleanedLength;
    
    // 统计每种字符的出现次数
    let e203Count = 0;
    let e204Count = 0;
    for (let char of originalText) {
        if (char === '\uE203') e203Count++;
        if (char === '\uE204') e204Count++;
    }
    
    return {
        originalLength,
        cleanedLength,
        removedCount,
        e203Count,
        e204Count
    };
}

async function main() {
    try {
        // 检查命令行参数
        if (process.argv.length !== 3) {
            console.error('Usage: node clean-unicode.js <filename.md>');
            process.exit(1);
        }

        const inputFile = process.argv[2];
        
        // 检查文件是否存在
        try {
            await fs.access(inputFile);
        } catch {
            console.error(`Error: File '${inputFile}' does not exist`);
            process.exit(1);
        }

        // 读取文件
        console.log(`Reading file: ${inputFile}`);
        const content = await fs.readFile(inputFile, 'utf8');

        // 清理文本
        const cleanedContent = removeSpecificUnicode(content);

        // 生成统计信息
        const stats = getStats(content, cleanedContent);

        // 如果没有发现需要清理的字符，直接退出
        if (stats.removedCount === 0) {
            console.log('\n文件分析完成：未发现 U+E203 或 U+E204 字符');
            return;
        }

        // 创建输出文件名
        const ext = path.extname(inputFile);
        const basename = path.basename(inputFile, ext);
        const outputFile = `${basename}-cleaned${ext}`;

        // 写入新文件
        await fs.writeFile(outputFile, cleanedContent, 'utf8');

        // 输出统计信息
        console.log('\n清理完成！统计信息：');
        console.log(`- 原始文件长度: ${stats.originalLength} 字符`);
        console.log(`- 清理后长度: ${stats.cleanedLength} 字符`);
        console.log(`- 总共移除: ${stats.removedCount} 个字符`);
        console.log(`  - U+E203: ${stats.e203Count} 个`);
        console.log(`  - U+E204: ${stats.e204Count} 个`);
        console.log(`\n清理后的文件已保存为: ${outputFile}`);

    } catch (error) {
        console.error('处理过程中出错：', error);
        process.exit(1);
    }
}

// 运行主函数
main();