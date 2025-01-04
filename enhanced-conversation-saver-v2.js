// ==UserScript==
// @name         增强版三合一会话记录保存
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  集成JSON下载、Markdown转换和Unicode字符清理的增强版会话记录保存工具
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
        markdownContent: null
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

    // JSON到Markdown转换相关函数
    function processCitations(text, citations, contentReferences) {
        if (!citations || !contentReferences) {
            return text;
        }

        const citationMap = {};
        for (const ref of contentReferences) {
            if (ref.type === 'webpage' || ref.url) {
                const startIdx = ref.start_idx;
                const endIdx = ref.end_idx;
                const url = ref.url;
                const title = ref.title || url;
                if (startIdx !== null && endIdx !== null && url) {
                    citationMap[`${startIdx},${endIdx}`] = [url, title];
                }
            }
        }

        const sortedCitations = Object.entries(citationMap)
            .map(([key, value]) => {
                const [start, end] = key.split(',').map(Number);
                return [start, end, ...value];
            })
            .sort((a, b) => b[0] - a[0]);

        for (const [start, end, url, title] of sortedCitations) {
            if (start < text.length && end <= text.length) {
                const link = `[${title}](${url})`;
                text = text.slice(0, start) + link + text.slice(end);
            }
        }

        return text;
    }

    function adjustHeaderLevels(text, increaseBy = 2) {
        return text.replace(/^(#+)(.*?)$/gm, (match, hashes, rest) => {
            return '#'.repeat(hashes.length + increaseBy) + rest;
        });
    }

    function extractMessageParts(message) {
        if (!message?.message) return null;

        const author = message.message?.author;
        if (!author) return null;

        if (author.name?.startsWith('canmore.') || author.name?.startsWith('dalle.')) {
            return null;
        }

        const content = message.message.content;
        if (!content) return null;

        let text = '';
        if (content.content_type === 'multimodal_text') {
            const parts = [];
            for (const part of content.parts || []) {
                if (typeof part === 'string') {
                    parts.push(part);
                }
            }
            text = parts.join(' ');
        } else {
            const parts = content.parts || [];
            text = parts.filter(part => part != null).join(' ');
        }

        if (!text) return null;

        const metadata = message.message.metadata || {};
        text = processCitations(text, metadata.citations, metadata.content_references);

        if (text.trim().startsWith('{') && text.trim().endsWith('}')) {
            try {
                const jsonContent = JSON.parse(text);
                if (['name', 'type', 'content', 'updates'].some(key => key in jsonContent)) {
                    return null;
                }
            } catch {
                // 解析失败，继续处理
            }
        }

        return text;
    }

    function buildConversationTree(mapping, nodeId, indent = 0) {
        if (!mapping[nodeId]) return [];

        const node = mapping[nodeId];
        const conversation = [];

        const messageContent = extractMessageParts(node);
        if (messageContent) {
            const role = node.message?.author?.role;
            if (role === 'user' || role === 'assistant') {
                const prefix = role === 'user' ? '## Human\n\n' : '## Assistant\n\n';
                const adjustedContent = adjustHeaderLevels(messageContent);
                conversation.push(`${prefix}${adjustedContent}`);
            }
        }

        for (const childId of node.children || []) {
            conversation.push(...buildConversationTree(mapping, childId, indent + 1));
        }

        return conversation;
    }

    function convertToMarkdown(jsonData) {
        try {
            const title = jsonData.title || 'Conversation';
            const mapping = jsonData.mapping;
            const rootId = Object.keys(mapping).find(nodeId => !mapping[nodeId].parent);
            
            if (!rootId) return '';

            const conversation = buildConversationTree(mapping, rootId);
            let markdownContent = `# ${title}\n\n`;
            markdownContent += conversation.join('\n\n').replace(/\n{3,}/g, '\n\n');

            state.markdownContent = markdownContent;
            return markdownContent;
        } catch (e) {
            log.error('转换Markdown时出错:', e);
            return null;
        }
    }

    // 响应处理函数
    function processResponse(text, url) {
        try {
            const responseSize = text.length;
            if (responseSize > state.largestResponseSize) {
                state.largestResponse = text;
                state.largestResponseSize = responseSize;
                state.largestResponseUrl = url;
                state.lastUpdateTime = new Date().toLocaleTimeString();

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
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await originalFetch.apply(this, args);
        const url = args[0];

        if (url.includes('conversation/')) {
            try {
                const clonedResponse = response.clone();
                clonedResponse.text().then(text => {
                    processResponse(text, url);
                }).catch(e => {
                    log.error('解析fetch响应时出错:', e);
                });
            } catch (e) {
                log.error('克隆fetch响应时出错:', e);
            }
        }
        return response;
    };

    // 监听传统的 XHR 请求
    const originalXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        if (url.includes('conversation/')) {
            this.addEventListener('load', function() {
                try {
                    processResponse(this.responseText, url);
                } catch (e) {
                    log.error('处理XHR响应时出错:', e);
                }
            });
        }
        return originalXhrOpen.apply(this, arguments);
    };

    // 更新按钮状态
    function updateButtonsStatus() {
        const commonStatus = state.largestResponse 
            ? `最后更新: ${state.lastUpdateTime}\n来源: ${state.largestResponseUrl}\n大小: ${(state.largestResponseSize / 1024).toFixed(2)}KB`
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
                const fileName = `${chatName}_${timestamp}.json`;

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
                const fileName = `${chatName}_${timestamp}.md`;

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