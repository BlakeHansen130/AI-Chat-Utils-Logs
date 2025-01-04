// ==UserScript==
// @name         增强版 Conversation 响应保存
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  监听多个网站的网络请求并保存最大的 conversation 响应为JSON文件，结合了错误处理、自动命名、URL追踪等多个增强功能
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
        lastUpdateTime: null
    };

    // 日志函数
    const log = {
        info: (msg) => console.log(`[Conversation Saver] ${msg}`),
        error: (msg, e) => console.error(`[Conversation Saver] ${msg}`, e)
    };

    // 响应处理函数
    function processResponse(text, url) {
        try {
            const responseSize = text.length;
            if (responseSize > state.largestResponseSize) {
                state.largestResponse = text;
                state.largestResponseSize = responseSize;
                state.largestResponseUrl = url;
                state.lastUpdateTime = new Date().toLocaleTimeString();
                updateButtonStatus();
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
    function updateButtonStatus() {
        const button = document.getElementById('downloadButton');
        if (button) {
            button.style.backgroundColor = state.largestResponse ? '#28a745' : '#007bff';
            button.title = state.largestResponse
                ? `最后更新: ${state.lastUpdateTime}\n来源: ${state.largestResponseUrl}\n大小: ${(state.largestResponseSize / 1024).toFixed(2)}KB`
                : '等待响应中...';
        }
    }

    // 创建下载按钮
    function createDownloadButton() {
        const button = document.createElement('button');
        const buttonStyles = {
            position: 'fixed',
            top: '45%',
            right: '0px',
            transform: 'translateY(-50%)',
            zIndex: '9999',
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

        button.id = 'downloadButton';
        button.innerText = '下载会话记录';
        Object.assign(button.style, buttonStyles);

        // 鼠标悬停效果
        button.onmouseover = () => {
            button.style.transform = 'translateY(-50%) scale(1.05)';
            button.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
        };
        button.onmouseout = () => {
            button.style.transform = 'translateY(-50%)';
            button.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        };

        // 下载功能
        button.onclick = function() {
            if (!state.largestResponse) {
                alert('还没有发现有效的会话记录。\n请等待页面加载完成或进行一些对话。');
                return;
            }

            try {
                // 获取文件名（使用标题+时间戳）
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
                const chatName = document.title.trim().replace(/[/\\?%*:|"<>]/g, '-');
                const fileName = `${chatName}_${timestamp}.json`;

                // 创建下载
                const blob = new Blob([state.largestResponse], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = fileName;
                link.click();

                log.info(`成功下载文件: ${fileName}`);
            } catch (e) {
                log.error('下载过程中出错:', e);
                alert('下载过程中发生错误，请查看控制台了解详情。');
            }
        };

        document.body.appendChild(button);
        updateButtonStatus();
    }

    // 页面加载完成后初始化
    window.addEventListener('load', function() {
        createDownloadButton();

        // 使用 MutationObserver 确保按钮始终存在
        const observer = new MutationObserver(() => {
            if (!document.getElementById('downloadButton')) {
                log.info('检测到按钮丢失，正在重新创建...');
                createDownloadButton();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        log.info('增强版会话保存脚本已启动');
    });
})();