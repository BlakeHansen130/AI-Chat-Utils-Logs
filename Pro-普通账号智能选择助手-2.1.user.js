// ==UserScript==
// @name         Pro/普通账号智能选择助手
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  智能查找最佳可用账号（优先Pro账号,无可用Pro账号时自动切换到普通账号）
// @author       Gao
// @match        https://cn.claudesvip.top/list/list.html
// @icon         https://cn.claudesvip.top/favicon.ico
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 创建浮动按钮
    function createFloatingButton() {
        const button = document.createElement('button');
        button.textContent = '查找最佳账号';
        button.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            padding: 10px 20px;
            background-color: #4a90e2;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;
        button.addEventListener('click', () => {
            button.disabled = true;
            button.textContent = '更新中...';
            refreshAndFind().finally(() => {
                button.disabled = false;
                button.textContent = '查找最佳账号';
            });
        });
        document.body.appendChild(button);
    }

    // 获取所有Pro账号元素（带皇冠图标的）
    function getProAccounts() {
        const allAccounts = document.querySelectorAll('.account-item');
        return Array.from(allAccounts).filter(account => {
            // 检查是否有皇冠图标且账号没有显示隐藏，且不是被禁用状态
            return account.querySelector('.fa-crown') !== null &&
                   account.style.display !== 'none' &&
                   !account.classList.contains('disabled');
        });
    }

    // 获取所有普通账号元素（带人像图标的）
    function getNormalAccounts() {
        const allAccounts = document.querySelectorAll('.account-item');
        return Array.from(allAccounts).filter(account => {
            // 检查是否有用户图标且账号没有显示隐藏，且不是被禁用状态
            return account.querySelector('.fa-user') !== null &&
                   account.style.display !== 'none' &&
                   !account.classList.contains('disabled');
        });
    }

    // 解析使用次数
    function parseUsageCount(account) {
        const usageInfo = account.querySelector('.usage-info')?.textContent || '';
        const usageMatch = usageInfo.match(/使用次数: (\d+) 次/);
        return usageMatch ? parseInt(usageMatch[1]) : Infinity;
    }

    // 刷新账号状态并查找最佳账号
    async function refreshAndFind() {
        // 获取所有账号数量统计
        const allAccountItems = document.querySelectorAll('.account-item');
        // 统计实际显示的账号总数（排除 display:none 的账号）
        const visibleAccounts = Array.from(allAccountItems).filter(account => {
            return window.getComputedStyle(account).display !== 'none';
        });

        const totalProAccounts = visibleAccounts.filter(account =>
            account.querySelector('.fa-crown') !== null
        ).length;

        const totalNormalAccounts = visibleAccounts.filter(account =>
            account.querySelector('.fa-user') !== null
        ).length;

        // 获取可用的账号（未被禁用的账号）
        const proAccounts = getProAccounts();
        const normalAccounts = getNormalAccounts();

        // 显示账号统计信息
        showToast(`账号统计:\nPro账号: ${proAccounts.length}/${totalProAccounts} 个\n普通账号: ${normalAccounts.length}/${totalNormalAccounts} 个`);

        // 等待2秒让用户看清统计信息
        await new Promise(resolve => setTimeout(resolve, 2000));

        // 先尝试查找Pro账号
        if (proAccounts.length > 0) {
            showToast(`正在更新 ${proAccounts.length} 个可用Pro账号状态...`);

            // 更新所有Pro账号状态
            const proResults = await Promise.all(proAccounts.map(async (account) => {
                const carID = account.querySelector('.account-route')?.textContent;
                if (!carID) return null;

                try {
                    const response = await fetch(`https://cn.claudesvip.top/status?carid=${carID}`);
                    const data = await response.json();
                    updateAccountStatus(account, data);
                    return { account, data };
                } catch (error) {
                    console.error(`更新账号 ${carID} 状态失败:`, error);
                    return null;
                }
            }));

            // 查找最佳Pro账号
            let bestProAccount = null;
            let minProUsage = Infinity;

            proResults.forEach(result => {
                if (!result) return;
                const { account, data } = result;

                if (data.accountReady && !data.clears_in && data.count < minProUsage) {
                    minProUsage = data.count;
                    bestProAccount = account;
                }
            });

            if (bestProAccount) {
                highlightAccount(bestProAccount);
                const accountId = bestProAccount.querySelector('.account-route').textContent;
                showToast(`找到最佳Pro账号:\n${accountId}\n使用次数: ${minProUsage}次`);
                return;
            }
        }

        // 如果没有可用的Pro账号，查找普通账号
        if (normalAccounts.length === 0) {
            showToast('未找到任何可用账号');
            return;
        }

        showToast('Pro账号均不可用，正在查找最佳普通账号...');

        // 查找使用次数最少的普通账号
        let bestNormalAccount = null;
        let minNormalUsage = Infinity;

        normalAccounts.forEach(account => {
            const usageCount = parseUsageCount(account);
            if (usageCount < minNormalUsage) {
                minNormalUsage = usageCount;
                bestNormalAccount = account;
            }
        });

        if (bestNormalAccount) {
            highlightAccount(bestNormalAccount);
            const accountId = bestNormalAccount.querySelector('.account-route').textContent;
            showToast(`找到最佳普通账号:\n${accountId}\n使用次数: ${minNormalUsage}次`);
        } else {
            showToast('没有找到任何可用账号');
        }
    }

    // 更新单个账号状态显示
    function updateAccountStatus(accountElement, statusData) {
        const usageInfo = accountElement.querySelector('.usage-info');
        if (!usageInfo) return;

        if (statusData.accountReady) {
            if (statusData.clears_in > 0) {
                accountElement.classList.add('disabled');
                usageInfo.textContent = `冷却时间: ${statusData.clears_in} 秒`;
            } else {
                accountElement.classList.remove('disabled');
                usageInfo.textContent = `使用次数: ${statusData.count} 次`;
            }
        } else {
            accountElement.classList.add('disabled');
        }
    }

    // 高亮显示选中的账号
    function highlightAccount(accountElement) {
        // 移除之前的高亮
        document.querySelectorAll('.account-item-highlight').forEach(item => {
            item.classList.remove('account-item-highlight');
        });

        // 添加高亮样式
        const style = document.createElement('style');
        style.textContent = `
            .account-item-highlight {
                transform: scale(1.05);
                box-shadow: 0 0 20px rgba(74, 144, 226, 0.6) !important;
                border: 2px solid #4a90e2 !important;
                transition: all 0.3s ease;
            }
        `;
        document.head.appendChild(style);

        accountElement.classList.add('account-item-highlight');
        accountElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // 显示提示信息
    function showToast(message) {
        // 移除现有的提示
        const existingToast = document.querySelector('.status-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = 'status-toast';
        toast.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 10001;
            font-size: 14px;
            white-space: pre-line;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);

        // 根据消息类型设置显示时间
        if (message.includes('账号统计')) {
            // 统计信息显示4秒
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s ease';
                setTimeout(() => toast.remove(), 500);
            }, 4000);
        } else {
            // 其他提示信息显示3秒
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s ease';
                setTimeout(() => toast.remove(), 500);
            }, 3000);
        }
    }

    // 初始化
    function init() {
        createFloatingButton();
    }

    // 当页面加载完成后运行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();