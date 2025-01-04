// ==UserScript==
// @name         Enhanced DWAI Card Button for React
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Add quick-open buttons to DWAI cards in React app
// @author       Your name
// @match        *://node.dawuai.buzz/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 创建样式
    function addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .dwai-quick-open {
                position: absolute !important;
                top: 5px;
                right: 5px;
                background: rgba(255, 255, 255, 0.9) !important;
                border: 1px solid #ccc !important;
                border-radius: 4px !important;
                padding: 2px 6px !important;
                cursor: pointer;
                font-size: 12px !important;
                z-index: 100;
                opacity: 0;
                transition: opacity 0.2s;
                color: #666 !important;
            }

            .dwai-card-wrapper {
                position: relative !important;
            }

            .dwai-card-wrapper:hover .dwai-quick-open {
                opacity: 1;
            }

            .dwai-quick-open:hover {
                background: rgba(255, 255, 255, 1) !important;
                color: #333 !important;
            }
        `;
        document.head.appendChild(style);
    }

    // 创建按钮
    function createButton(url) {
        const button = document.createElement('button');
        button.className = 'dwai-quick-open';
        button.innerHTML = '↗️';
        button.title = '在新标签页打开';

        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            window.open(url, '_blank');
        });

        return button;
    }

    // 获取链接URL
    function getCardUrl(element) {
        // 检查data属性
        const dataUrl = element.dataset.url;
        if (dataUrl) return dataUrl;

        // 检查href属性
        const href = element.getAttribute('href');
        if (href) return href;

        // 检查子元素中的链接
        const link = element.querySelector('a');
        if (link && link.href) return link.href;

        // 检查onclick事件
        const onclick = element.getAttribute('onclick');
        const match = onclick?.match(/window\.location=['"]([^'"]+)['"]/);
        if (match) return match[1];

        // 检查父元素
        const parentLink = element.closest('a');
        if (parentLink && parentLink.href) return parentLink.href;

        return null;
    }

    // 处理卡片
    function processCard(card) {
        // 如果已经处理过，跳过
        if (card.querySelector('.dwai-quick-open')) {
            return;
        }

        // 获取URL
        const url = getCardUrl(card);
        if (!url) {
            return;
        }

        // 添加包装器类名
        card.classList.add('dwai-card-wrapper');

        // 创建并添加按钮
        const button = createButton(url);
        card.appendChild(button);
    }

    // 初始化函数
    function init() {
        // 添加样式
        addStyles();

        // 查找可能的卡片选择器
        const selectors = [
            '[class*="card"]',
            '[class*="TEAM"]',
            '[class*="PLUS"]',
            'a[href*="/detail/"]',
            'div[onclick*="window.location"]'
        ];

        // 创建观察器
        const observer = new MutationObserver((mutations) => {
            // 等待React渲染完成
            setTimeout(() => {
                document.querySelectorAll(selectors.join(',')).forEach(processCard);
            }, 100);
        });

        // 开始观察
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // 初始处理
        setTimeout(() => {
            document.querySelectorAll(selectors.join(',')).forEach(processCard);
        }, 1000);
    }

    // 当DOM加载完成时初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();