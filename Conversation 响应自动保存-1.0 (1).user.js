// ==UserScript==
// @name         Conversation 响应自动保存
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  监听多个网站的网络请求并保存最大的 conversation 响应为JSON文件，支持自动命名和更好的按钮位置
// @author       You
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

    let largestResponse = null;
    let largestResponseUrl = null;

    // 监听 fetch 请求
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await originalFetch.apply(this, args);
        const url = args[0];

        // 检查URL是否包含"conversation/"
        if (url.includes('conversation/')) {
            const clonedResponse = response.clone();
            clonedResponse.text().then((text) => {
                if (!largestResponse || text.length > largestResponse.length) {
                    largestResponse = text;
                    largestResponseUrl = url;
                }
            });
        }
        return response;
    };

    // 监听传统的 XHR 请求
    const originalXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.addEventListener('load', function() {
            if (url.includes('conversation/')) {
                if (!largestResponse || this.responseText.length > largestResponse.length) {
                    largestResponse = this.responseText;
                    largestResponseUrl = url;
                }
            }
        });
        return originalXhrOpen.apply(this, arguments);
    };

    // 创建一个按钮来下载 JSON 响应
    function createDownloadButton() {
        const button = document.createElement('button');
        button.innerText = '下载最大 conversation 响应';
        button.style.position = 'fixed';
        button.style.top = '45%';  // 向上移动一点
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
                // 获取浏览器的标签页标题，设置为文件名
                let chatName = document.title.trim().replace(/[/\\?%*:|"<>]/g, '-'); // 替换非法字符

                const blob = new Blob([largestResponse], { type: 'application/json' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = chatName + '.json';
                link.click();
            } else {
                alert('还没有找到 conversation 响应。');
            }
        };

        document.body.appendChild(button);
    }

    // 页面加载完成后添加按钮
    window.addEventListener('load', createDownloadButton);

})();
