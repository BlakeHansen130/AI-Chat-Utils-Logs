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
        markdownContent: null,
        modelName: null // 新增：模型名称
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

    // 新增：提取模型名称函数
    function extractModelName(jsonData) {
        try {
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

                // 预处理Markdown内容和提取模型名称
                try {
                    const cleanedJson = removeSpecificUnicode(text);
                    const jsonData = JSON.parse(cleanedJson);
                    state.modelName = extractModelName(jsonData); // 新增：提取模型名称
                    convertToMarkdown(jsonData);
                } catch (e) {
                    log.error('预处理Markdown内容时出错:', e);
                }

                updateButtonsStatus();
                log.info(`发现更大的响应 (${responseSize} bytes) 来自: ${url}${state.modelName ? `, 模型: ${state.modelName}` : ''}`);
            }
        } catch (e) {
            log.error('处理响应时出错:', e);
        }
    }