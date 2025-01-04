// ==UserScript==
// @name         超级增强版 Conversation 响应保存
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  监听多个网站的网络请求，保存对话内容，支持JSON和Markdown格式，自动清理特殊字符
// @author       Gao Jiaxuan + GPT-4 + Claude
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
        cleanedResponse: null,
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

    // Markdown转换相关函数
    function formatTimestamp(timestamp) {
        if (timestamp) {
            const dt = new Date(timestamp * 1000);
            return dt.toISOString().replace('T', ' ').replace('Z', ' UTC');
        }
        return null;
    }

    function getModelInfo(message) {
        if (!message || !message.metadata) {
            return null;
        }

        const metadata = message.metadata;
        const modelSlug = metadata.model_slug;
        const defaultModelSlug = metadata.default_model_slug;

        if (modelSlug && defaultModelSlug && modelSlug !== defaultModelSlug) {
            return ` [使用模型: ${modelSlug}]`;
        }
        return "";
    }

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

        const citationsSorted = Object.entries(citationMap)
            .map(([key, value]) => {
                const [start, end] = key.split(',').map(Number);
                return [start, end, ...value];
            })
            .sort((a, b) => b[0] - a[0]);

        for (const [start, end, url, title] of citationsSorted) {
            if (start < text.length && end <= text.length) {
                const link = `[${title}](${url})`;
                text = text.slice(0, start) + link + text.slice(end);
            }
        }

        return text;
    }

    function extractMessageParts(message) {
        if (!message || !message.message) {
            return [null, null];
        }

        const msg = message.message;
        const timestamp = formatTimestamp(msg.create_time);

        const author = msg.author || {};
        const authorName = author.name;
        if (authorName && typeof authorName === 'string' && (
            authorName.startsWith('canmore.') ||
            authorName.startsWith('dalle.')
        )) {
            return [null, null];
        }

        const content = msg.content || {};
        if (!content) {
            return [null, null];
        }

        let parts = content.parts || [];
        if (parts[0] && typeof parts[0] === 'string' && parts[0].includes("DALL-E displayed")) {
            return [null, null];
        }

        let text;
        if (content.content_type === 'multimodal_text') {
            text = parts
                .filter(part => typeof part === 'string')
                .join(' ');
        } else {
            text = parts
                .filter(part => part !== null)
                .map(String)
                .join(' ');
        }

        if (!text) {
            return [null, null];
        }

        const metadata = msg.metadata || {};
        const citations = metadata.citations || [];
        const contentReferences = metadata.content_references || [];

        text = processCitations(text, citations, contentReferences);

        return [text, timestamp];
    }

    function isCanvasRelated(node) {
        if (!node || !node.message) {
            return false;
        }

        const author = node.message.author || {};
        const authorName = author.name;
        if (authorName && typeof authorName === 'string' && authorName.startsWith('canmore.')) {
            return true;
        }

        const content = node.message.content || {};
        const parts = content.parts || [];
        if (!parts.length) {
            return false;
        }

        const text = parts
            .filter(part => part !== null)
            .map(String)
            .join(' ');

        if (!text) {
            return false;
        }

        if (text.trim().startsWith('{') && text.trim().endsWith('}')) {
            try {
                const jsonContent = JSON.parse(text);
                return ['name', 'type', 'content', 'updates'].some(key => key in jsonContent);
            } catch (e) {
                return false;
            }
        }

        return false;
    }

    function adjustHeaderLevels(text, increaseBy = 2) {
        return text.replace(/^(#+)(.*?)$/gm, (match, hashes, rest) => {
            return '#'.repeat(hashes.length + increaseBy) + rest;
        });
    }

    function buildConversationTree(mapping, nodeId, indent = 0) {
        if (!mapping[nodeId]) {
            return [];
        }

        const node = mapping[nodeId];
        const conversation = [];

        if (!isCanvasRelated(node)) {
            const [messageContent, timestamp] = extractMessageParts(node);
            if (messageContent) {
                const role = node.message?.author?.role;
                if (role === 'user' || role === 'assistant') {
                    const modelInfo = getModelInfo(node.message);
                    const timestampInfo = timestamp ? `\n\n*${timestamp}*` : "";
                    const prefix = role === 'user'
                        ? `## Human${timestampInfo}\n\n`
                        : `## Assistant${modelInfo}${timestampInfo}\n\n`;
                    const adjustedContent = adjustHeaderLevels(messageContent);
                    conversation.push(`${prefix}${adjustedContent}`);
                }
            }
        }

        for (const childId of (node.children || [])) {
            conversation.push(...buildConversationTree(mapping, childId, indent + 1));
        }

        return conversation;
    }

    function getDefaultModel(data) {
        if (!data || !data.mapping) {
            return null;
        }

        for (const node of Object.values(data.mapping)) {
            if (!node.message) continue;
            const msg = node.message;
            if (msg.author?.role === 'assistant') {
                return msg.metadata?.default_model_slug;
            }
        }

        return 'unknown';
    }

    function convertToMarkdown(jsonData) {
        try {
            const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;

            const title = data.title || 'Conversation';
            const defaultModel = getDefaultModel(data);

            const mapping = data.mapping;
            const rootId = Object.keys(mapping).find(nodeId => !mapping[nodeId].parent);

            const conversation = buildConversationTree(mapping, rootId);

            let markdownContent = `# ${title}-${defaultModel}\n\n`;
            markdownContent += conversation.join('\n\n').replace(/\n{3,}/g, '\n\n');

            return markdownContent;

        } catch (e) {
            log.error('转换Markdown时出错:', e);
            throw e;
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

                // 清理Unicode字符并转换为Markdown
                try {
                    state.cleanedResponse = removeSpecificUnicode(text);
                    const jsonData = JSON.parse(state.cleanedResponse);
                    state.markdownContent = convertToMarkdown(jsonData);
                } catch (e) {
                    log.error('处理cleaned response或转换Markdown时出错:', e);
                    state.cleanedResponse = null;
                    state.markdownContent = null;
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
        const jsonButton = document.getElementById('downloadJsonButton');
        const mdButton = document.getElementById('downloadMdButton');

        if (jsonButton) {
            jsonButton.style.backgroundColor = state.cleanedResponse ? '#28a745' : '#007bff';
            jsonButton.title = state.cleanedResponse
                ? `最后更新: ${state.lastUpdateTime}\n来源: ${state.largestResponseUrl}\n大小: ${(state.largestResponseSize / 1024).toFixed(2)}KB`
                : '等待响应中...';
        }

        if (mdButton) {
            mdButton.style.backgroundColor = state.markdownContent ? '#28a745' : '#007bff';
            mdButton.title = state.markdownContent
                ? `最后更新: ${state.lastUpdateTime}\n来源: ${state.largestResponseUrl}`
                : '等待响应中...';
        }
    }

    // 创建下载按钮
    function createDownloadButtons() {
        const buttonContainer = document.createElement('div');
        Object.assign(buttonContainer.style, {
            position: 'fixed',
            top: '45%',
            right: '0px',
            transform: 'translateY(-50%)',
            zIndex: '9999',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
        });

        // 通用按钮样式
        const commonButtonStyles = {
            padding: '10px',
            backgroundColor: '#007bff',
            color: '#ffffff',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            fontFamily: 'Arial, sans-serif',
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
            whiteSpace: 'nowrap'
        };

        // JSON下载按钮
        const jsonButton = document.createElement('button');
        jsonButton.id = 'downloadJsonButton';
        jsonButton.innerText = '下载JSON';
        Object.assign(jsonButton.style, commonButtonStyles);

        // Markdown下载按钮
        const mdButton = document.createElement('button');
        mdButton.id = 'downloadMdButton';
        mdButton.innerText = '下载MD';
        Object.assign(mdButton.style, commonButtonStyles);

        // 鼠标悬停效果
        [jsonButton, mdButton].forEach(button => {
            button.onmouseover = () => {
                button.style.transform = 'scale(1.05)';
                button.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
            };
            button.onmouseout = () => {
                button.style.transform = 'scale(1)';
                button.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
            };
        });

        // JSON下载功能
        jsonButton.onclick = function() {
            if (!state.cleanedResponse) {
                alert('还没有发现有效的会话记录。\n请等待页面加载完成或进行一些对话。');
                return;
            }

            try {
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
                const chatName = document.title.trim().replace(/[/\\?%*:|"<>]/g, '-');
                const fileName = `${chatName}_${timestamp}.json`;

                const blob = new Blob([state.cleanedResponse], { type: 'application/json' });
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

        // Markdown下载功能
        mdButton.onclick = function() {
            if (!state.markdownContent) {
                alert('还没有可用的Markdown内容。\n请等待页面加载完成或进行一些对话。');
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

        buttonContainer.appendChild(jsonButton);
        buttonContainer.appendChild(mdButton);
        document.body.appendChild(buttonContainer);
        updateButtonsStatus();
    }

    // 页面加载完成后初始化
    window.addEventListener('load', function() {
        createDownloadButtons();

        // 使用 MutationObserver 确保按钮始终存在
        const observer = new MutationObserver(() => {
            if (!document.getElementById('downloadJsonButton') || !document.getElementById('downloadMdButton')) {
                log.info('检测到按钮丢失，正在重新创建...');
                createDownloadButtons();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        log.info('增强版会话保存脚本已启动');
    });
})();