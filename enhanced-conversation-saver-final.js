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
        modelName: null        // 新增：模型名称
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

    // 新增：提取模型名称
    function extractModelName(text) {
        try {
            const data = JSON.parse(text);
            const mapping = data.mapping || {};
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

    // JSON到Markdown转换相关函数
    [... 保持原有的Markdown转换相关函数不变 ...]

    // 响应处理函数
    function processResponse(text, url) {
        try {
            const responseSize = text.length;
            if (responseSize > state.largestResponseSize) {
                state.largestResponse = text;
                state.largestResponseSize = responseSize;
                state.largestResponseUrl = url;
                state.lastUpdateTime = new Date().toLocaleTimeString();
                state.modelName = extractModelName(text);  // 新增：提取模型名称

                // 预处理Markdown内容
                try {
                    const cleanedJson = removeSpecificUnicode(text);
                    const jsonData = JSON.parse(cleanedJson);
                    convertToMarkdown(jsonData);
                } catch (e) {
                    log.error('预处理Markdown内容时出错:', e);
                }

                updateButtonsStatus();
                log.info(`发现更大的响应 (${responseSize} bytes) 来自: ${url}`);
            }
        } catch (e) {
            log.error('处理响应时出错:', e);
        }
    }

    // 监听 fetch 请求
    [... 保持原有的请求监听代码不变 ...]

    // 更新按钮状态
    function updateButtonsStatus() {
        const modelInfo = state.modelName ? `\n模型: ${state.modelName}` : '';  // 新增：模型信息
        const commonStatus = state.largestResponse 
            ? `最后更新: ${state.lastUpdateTime}\n来源: ${state.largestResponseUrl}\n大小: ${(state.largestResponseSize / 1024).toFixed(2)}KB${modelInfo}`
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
        const containerStyles = {
            position: 'fixed',
            top: '45%',
            right: '0px',
            transform: 'translateY(-50%)',
            zIndex: '9999',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px',
            padding: '5px',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            borderRadius: '5px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
        };

        const buttonStyles = {
            padding: '10px',
            backgroundColor: '#007bff',
            color: '#ffffff',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            fontFamily: 'Arial, sans-serif',
            whiteSpace: 'nowrap',
            width: '120px',
            textAlign: 'center',
        };

        const container = document.createElement('div');
        Object.assign(container.style, containerStyles);

        // JSON下载按钮
        const jsonButton = document.createElement('button');
        jsonButton.id = 'jsonDownloadButton';
        jsonButton.innerText = '下载JSON';
        Object.assign(jsonButton.style, buttonStyles);

        // Markdown下载按钮
        const mdButton = document.createElement('button');
        mdButton.id = 'mdDownloadButton';
        mdButton.innerText = '下载MD';
        Object.assign(mdButton.style, buttonStyles);

        // 添加悬停效果
        [jsonButton, mdButton].forEach(button => {
            button.onmouseover = () => {
                button.style.transform = 'scale(1.05)';
                button.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
            };
            button.onmouseout = () => {
                button.style.transform = 'scale(1)';
                button.style.boxShadow = 'none';
            };
        });

        // 下载功能
        jsonButton.onclick = function() {
            if (!state.largestResponse) {
                alert('还没有发现有效的会话记录。\n请等待页面加载完成或进行一些对话。');
                return;
            }

            try {
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
                const chatName = document.title.trim().replace(/[/\\?%*:|"<>]/g, '-');
                const modelSuffix = state.modelName ? `_${state.modelName}` : '';  // 新增：模型后缀
                const fileName = `${chatName}${modelSuffix}_${timestamp}.json`;

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

        mdButton.onclick = function() {
            if (!state.markdownContent) {
                alert('Markdown内容未就绪。\n请确保已有有效的会话记录。');
                return;
            }

            try {
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
                const chatName = document.title.trim().replace(/[/\\?%*:|"<>]/g, '-');
                const modelSuffix = state.modelName ? `_${state.modelName}` : '';  // 新增：模型后缀
                const fileName = `${chatName}${modelSuffix}_${timestamp}.md`;

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

        container.appendChild(jsonButton);
        container.appendChild(mdButton);
        document.body.appendChild(container);
        updateButtonsStatus();
    }

    // 页面加载完成后初始化
    window.addEventListener('load', function() {
        createButtons();

        // 使用 MutationObserver 确保按钮始终存在
        const observer = new MutationObserver(() => {
            if (!document.getElementById('jsonDownloadButton') || !document.getElementById('mdDownloadButton')) {
                log.info('检测到按钮丢失，正在重新创建...');
                createButtons();
            }
        });
        
        observer.observe(document.body, { 
            childList: true, 
            subtree: true 
        });

        log.info('增强版三合一会话保存脚本已启动');
    });
})();