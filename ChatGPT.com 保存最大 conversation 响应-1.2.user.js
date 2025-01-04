// ==UserScript==
// @name         ChatGPT.com 保存最大 conversation 响应
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  监听 chatgpt.com 的网络请求并保存最大的 conversation 响应为JSON文件，支持手动下载和自动命名功能。
// @author       You
// @match        https://chatgpt.com/c/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    let largestResponse = null;
    let largestResponseSize = 0;

    // 监听 fetch 请求
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await originalFetch.apply(this, args);
        const url = args[0];

        // 检查URL是否包含"conversation/"
        if (url.includes('conversation/')) {
            const clonedResponse = response.clone();
            clonedResponse.text().then((text) => {
                const responseSize = text.length;
                if (responseSize > largestResponseSize) {
                    largestResponseSize = responseSize;
                    largestResponse = text;
                }
            }).catch((e) => {
                console.error('无法解析响应:', e);
            });
        }
        return response;
    };

    // 监听传统的 XHR 请求
    const originalXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.addEventListener('load', function() {
            if (url.includes('conversation/')) {
                try {
                    const responseSize = this.responseText.length;
                    if (responseSize > largestResponseSize) {
                        largestResponseSize = responseSize;
                        largestResponse = this.responseText;
                    }
                } catch (e) {
                    console.error('无法解析响应:', e);
                }
            }
        });
        return originalXhrOpen.apply(this, arguments);
    };

    // 创建一个按钮来下载最大的 JSON 响应
    function createDownloadButton() {
        const button = document.createElement('button');
        button.innerText = '下载最大 conversation 响应';
        button.id = 'downloadButton';
        button.style.position = 'fixed';
        button.style.top = '45%';
        button.style.right = '0px';
        button.style.transform = 'translateY(-50%)';
        button.style.zIndex = 9999;
        button.style.padding = '10px';
        button.style.backgroundColor = '#007bff';
        button.style.color = '#ffffff';
        button.style.border = 'none';
        button.style.cursor = 'pointer';
        button.style.borderRadius = '5px';

        button.onclick = function() {
            if (largestResponse) {
                const chatName = document.title.trim().replace(/[/\\?%*:|"<>]/g, '-'); // 替换非法字符

                const blob = new Blob([largestResponse], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = chatName + '.json';
                link.click();
            } else {
                alert('还没有找到有效的 conversation 响应。请稍等页面加载完成。');
            }
        };

        document.body.appendChild(button);
    }

    // 页面加载完成后添加按钮
    window.addEventListener('load', function() {
        createDownloadButton();

        // 观察页面变化，确保按钮不会被移除
        const observer = new MutationObserver(() => {
            if (!document.getElementById('downloadButton')) {
                createDownloadButton();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    });

})();
