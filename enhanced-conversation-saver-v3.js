// ==UserScript==
// @name         增强版三合一会话记录保存
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  集成JSON下载、Markdown转换和Unicode字符清理的增强版会话记录保存工具，支持多种模型
// @author       You
// @match        https://chatgpt.com/c/*
// @match        https://abcd.dwai.world/c/*
// @match        https://ed.dawuai.buzz/c/*
// @match        https://node.dawuai.buzz/c/*
// @match        https://newnode.dawuai.buzz/c/*
// @match        https://france.dwai.work/c/*
// @match        https://dw.dwai.world/c/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 状态追踪
    let state = {
        largestResponse: null,
        largestResponseSize: 0,
        largestResponseUrl: null,
        lastUpdateTime: null,
        markdownContent: null,
        modelName: null
    };

    // 日志函数
    const log = {
        info: (msg) => console.log(`[Conversation Saver] ${msg}`),
        error: (msg, e) => console.error(`[Conversation Saver] ${msg}`, e)
    };

    // Unicode清理函数
    function removeSpecificUnicode(text) {
        const regex = /[\uE203\uE204]/gu;
        return text.replace(regex, '');
    }

    // 获取模型名称
    function extractModelName(jsonData) {
        try {
            // 遍历消息记录查找模型名称
            const mapping = jsonData.mapping || {};
            for (const key in mapping) {
                const message = mapping[key].message;
                if (message?.metadata?.model_slug) {
                    return message.metadata.model_slug;
                }
            }
            return null;
        } catch (e) {
            log.error('提取模型名称时出错:', e);
            return null;
        }
    }

    // 生成文件名
    function generateFileName(baseName, modelName, type) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const cleanBaseName = baseName.trim().replace(/[/\\?%*:|"<>]/g, '-');
        const modelSuffix = modelName ? `_${modelName}` : '';
        return `${cleanBaseName}${modelSuffix}_${timestamp}.${type}`;
    }

    [... 其他函数代码保持不变 ...]

    // 响应处理函数
    function processResponse(text, url) {
        try {
            const responseSize = text.length;
            if (responseSize > state.largestResponseSize) {
                state.largestResponse = text;
                state.largestResponseSize = responseSize;
                state.largestResponseUrl = url;
                state.lastUpdateTime = new Date().toLocaleTimeString();

                // 预处理JSON和提取模型名称
                try {
                    const cleanedJson = removeSpecificUnicode(text);
                    const jsonData = JSON.parse(cleanedJson);
                    state.modelName = extractModelName(jsonData);
                    convertToMarkdown(jsonData);
                } catch (e) {
                    log.error('预处理内容时出错:', e);
                }

                updateButtonsStatus();
                log.info(`发现更大的响应 (${responseSize} bytes) 来自: ${url}${state.modelName ? `, 模型: ${state.modelName}` : ''}`);
            }
        } catch (e) {
            log.error('处理响应时出错:', e);
        }
    }

    // 更新按钮状态
    function updateButtonsStatus() {
        const commonStatus = state.largestResponse 
            ? `最后更新: ${state.lastUpdateTime}\n来源: ${state.largestResponseUrl}\n大小: ${(state.largestResponseSize / 1024).toFixed(2)}KB${state.modelName ? `\n模型: ${state.modelName}` : ''}`
            : '等待响应中...';

        const jsonButton = document.getElementById('jsonDownloadButton');
        const mdButton = document.getElementById('mdDownloadButton');

        if (jsonButton) {
            jsonButton.style.backgroundColor = state.largestResponse ? '#28a745' : '#007bff';
            jsonButton.title = commonStatus;
        }

        if (mdButton) {
            mdButton.style.backgroundColor = state.markdownContent ? '#28a745' : '#007bff';
            mdButton.title = state.markdownContent 
                ? commonStatus + '\nMarkdown转换已就绪'
                : commonStatus + '\nMarkdown转换未就绪';
        }
    }

    // 创建按钮容器和按钮
    function createButtons() {
        [... 按钮样式代码保持不变 ...]

        // JSON下载按钮点击事件
        jsonButton.onclick = function() {
            if (!state.largestResponse) {
                alert('还没有发现有效的会话记录。\n请等待页面加载完成或进行一些对话。');
                return;
            }

            try {
                const fileName = generateFileName(document.title, state.modelName, 'json');
                const cleanedJson = removeSpecificUnicode(state.largestResponse);
                const blob = new Blob([cleanedJson], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = fileName;
                link.click();
                
                log.info(`成功下载JSON文件: ${fileName}`);
            } catch (e) {
                log.error('下载JSON过程中出错:', e);
                alert('下载过程中发生错误，请查看控制台了解详情。');
            }
        };

        // Markdown下载按钮点击事件
        mdButton.onclick = function() {
            if (!state.markdownContent) {
                alert('Markdown内容未就绪。\n请确保已有有效的会话记录。');
                return;
            }

            try {
                const fileName = generateFileName(document.title, state.modelName, 'md');
                const blob = new Blob([state.markdownContent], { type: 'text/markdown' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = fileName;
                link.click();
                
                log.info(`成功下载Markdown文件: ${fileName}`);
            } catch (e) {
                log.error('下载Markdown过程中出错:', e);
                alert('下载过程中发生错误，请查看控制台了解详情。');
            }
        };

        [... 其余代码保持不变 ...]
    }

    [... 初始化代码保持不变 ...]

})();