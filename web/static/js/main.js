// 会话切换 - 直接给session-info添加点击事件，避免与按钮事件冲突
document.addEventListener('click', function(e) {
    if (e.target.closest('.session-info') && !e.target.closest('.session-actions')) {
        const sessionInfo = e.target.closest('.session-info');
        const sessionId = sessionInfo.querySelector('.session-id').textContent;
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/switch_session';
        form.style.display = 'none';
        
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'session_id';
        input.value = sessionId;
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
});

// 创建自定义模态对话框元素
function createRenameDialog() {
    const dialogHTML = `
    <div id="rename-dialog" class="custom-dialog" style="display:none;">
        <div class="dialog-overlay"></div>
        <div class="dialog-content">
            <div class="dialog-header">
                <h3>重命名会话</h3>
            </div>
            <div class="dialog-body">
                <input type="text" id="new-session-name" class="dialog-input" placeholder="请输入新的会话名称">
            </div>
            <div class="dialog-footer">
                <button id="dialog-cancel" class="dialog-btn cancel">取消</button>
                <button id="dialog-confirm" class="dialog-btn confirm">确认</button>
            </div>
        </div>
    </div>
    `;
    
    // 添加样式
    const styleHTML = `
    <style>
    .custom-dialog {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: flex-start;
        overflow-y: auto;
        padding: 20px;
        box-sizing: border-box;
    }
    .dialog-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
    }
    .dialog-content {
        position: relative;
        background-color: white;
        border-radius: 8px;
        padding: 0;
        width: 100%;
        max-width: 400px;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        margin: auto;
        top: 20vh;
        box-sizing: border-box;
    }
    .dialog-header {
        padding: 15px 20px;
        border-bottom: 1px solid #eee;
    }
    .dialog-header h3 {
        margin: 0;
        font-size: 16px;
        color: #333;
    }
    .dialog-body {
        padding: 20px;
    }
    .dialog-input {
        width: 100%;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
        outline: none;
        box-sizing: border-box;
    }
    .dialog-input:focus {
        border-color: #3498db;
    }
    .dialog-footer {
        padding: 15px 20px;
        border-top: 1px solid #eee;
        display: flex;
        justify-content: flex-end;
        gap: 10px;
    }
    .dialog-btn {
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        font-size: 14px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .dialog-btn.cancel {
        background-color: #f5f5f5;
        color: #333;
    }
    .dialog-btn.cancel:hover {
        background-color: #e0e0e0;
    }
    .dialog-btn.confirm {
        background-color: #3498db;
        color: white;
    }
    .dialog-btn.confirm:hover {
        background-color: #2980b9;
    }
    </style>
    `;
    
    // 添加到文档
    document.head.insertAdjacentHTML('beforeend', styleHTML);
    document.body.insertAdjacentHTML('beforeend', dialogHTML);
}

// 初始化自定义对话框
if (!document.getElementById('rename-dialog')) {
    createRenameDialog();
}

// 会话重命名
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('rename-btn')) {
        e.stopPropagation(); // 阻止事件冒泡，避免触发会话切换
        const sessionId = e.target.getAttribute('data-id');
        const sessionElement = e.target.closest('.session-item');
        
        // 显示自定义对话框
        const dialog = document.getElementById('rename-dialog');
        const input = document.getElementById('new-session-name');
        const confirmBtn = document.getElementById('dialog-confirm');
        const cancelBtn = document.getElementById('dialog-cancel');
        
        // 移除可能存在的旧事件监听器（避免连续点击时的问题）
        const newConfirmBtn = confirmBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
        
        // 更新引用
        const updatedConfirmBtn = document.getElementById('dialog-confirm');
        const updatedCancelBtn = document.getElementById('dialog-cancel');
        
        // 设置初始值
        input.value = sessionId;
        
        // 确保对话框在可视区域内
        updateDialogPosition();
        
        // 显示对话框
        dialog.style.display = 'flex';
        // 聚焦输入框
        setTimeout(() => {
            input.focus();
            input.select();
        }, 100);
        
        // 确认按钮点击事件
        const handleConfirm = function() {
            const newName = input.value.trim();
            
            if (newName && newName !== sessionId) {
                fetch('/rename_session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: `old_name=${encodeURIComponent(sessionId)}&new_name=${encodeURIComponent(newName)}`
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // 更新界面上的会话名称
                        if (sessionElement) {
                            const sessionIdElement = sessionElement.querySelector('.session-id');
                            if (sessionIdElement) {
                                sessionIdElement.textContent = newName;
                            }
                        }
                    } else {
                        // 显示错误信息
                        alert(data.message || '重命名失败');
                    }
                })
                .catch(error => {
                    alert('重命名失败');
                })
                .finally(() => {
                    closeDialog();
                });
            } else {
                closeDialog();
            }
        };
        
        // 取消按钮点击事件
        const handleCancel = function() {
            closeDialog();
        };
        
        // 关闭对话框并清理事件监听器
        const closeDialog = function() {
            dialog.style.display = 'none';
            document.removeEventListener('keydown', handleEsc);
        };
        
        // ESC键关闭对话框
        const handleEsc = function(event) {
            if (event.key === 'Escape') {
                closeDialog();
            }
        };
        
        // 添加事件监听器
        updatedConfirmBtn.addEventListener('click', handleConfirm);
        updatedCancelBtn.addEventListener('click', handleCancel);
        document.addEventListener('keydown', handleEsc);
        
        // 确保对话框在窗口大小改变时仍然可见
        window.addEventListener('resize', updateDialogPosition);
        
        // 确保对话框在可视区域内
        function updateDialogPosition() {
            const dialogContent = dialog.querySelector('.dialog-content');
            const windowHeight = window.innerHeight;
            const dialogHeight = dialogContent.offsetHeight;
            
            // 确保对话框不超出视口
            if (dialogHeight > windowHeight - 40) {
                dialogContent.style.maxHeight = (windowHeight - 40) + 'px';
                dialogContent.style.overflowY = 'auto';
            } else {
                dialogContent.style.maxHeight = 'none';
                dialogContent.style.overflowY = 'visible';
            }
            
            // 设置顶部位置，确保在可视区域内
            const topPosition = Math.max(20, (windowHeight - dialogHeight) / 2);
            dialogContent.style.top = topPosition + 'px';
        }
    }
});

// 会话删除
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('delete-btn')) {
        e.stopPropagation(); // 阻止事件冒泡，避免触发会话切换
        const sessionId = e.target.getAttribute('data-id');
        
        if (confirm(`确定要删除会话 "${sessionId}" 吗？`)) {
            fetch('/delete_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `session_id=${encodeURIComponent(sessionId)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 从界面上移除会话项
                    const sessionItem = e.target.closest('.session-item');
                    if (sessionItem && sessionItem.parentNode) {
                        sessionItem.parentNode.removeChild(sessionItem);
                    }
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                alert('删除失败');
            });
        }
    }
});

// 新建会话 - 添加临时会话ID
let tempSessionId = null;
document.getElementById('new-btn').addEventListener('click', function() {
    // 生成临时会话ID
    tempSessionId = '新会话_' + new Date().getTime();
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/new_session';
    form.style.display = 'none';
    
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'temp_session_id';
    input.value = tempSessionId;
    
    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
});

// 监听页面卸载，检查是否有未使用的临时会话
window.addEventListener('beforeunload', function() {
    // 这个功能会在switch_session路由中实现，自动删除未使用的空会话
});

// 保存会话
document.getElementById('save-btn').addEventListener('click', function() {
    fetch('/save_session', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            alert('保存失败');
        });
});

// 发送消息
document.getElementById('chat-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // 清空输入框
    messageInput.value = '';
    
    // 添加用户消息到界面
    const chatHistory = document.getElementById('chat-history');
    const userMessage = document.createElement('div');
    userMessage.className = 'message user';
    userMessage.innerHTML = `
        <div class="history-control">
            <button class="continue-button">从此处继续</button>
        </div>
        <div class="message-content">${escapeHtml(message)}</div>
    `;
    chatHistory.appendChild(userMessage);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // 显示加载状态
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'message assistant';
    loadingMessage.innerHTML = '<div class="message-content">思考中...</div>';
    chatHistory.appendChild(loadingMessage);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // 发送请求
    fetch('/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `message=${encodeURIComponent(message)}`
    })
    .then(response => response.json())
    .then(data => {
        // 移除加载消息
        chatHistory.removeChild(loadingMessage);
        
        // 添加回复消息
        const responseMessage = document.createElement('div');
        responseMessage.className = 'message assistant';
        
        // 渲染Markdown内容
        const markdownContent = marked.parse(data.response);
        
        responseMessage.innerHTML = `
            <div class="history-control">
                <button class="continue-button">从此处继续</button>
            </div>
            <div class="message-content markdown-content">${markdownContent}</div>
        `;
        
        chatHistory.appendChild(responseMessage);
        
        // 对代码块应用语法高亮
        hljs.highlightAll();
        
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
        // 更新递归日志
        updateRecursionLogs();
    })
    .catch(error => {
        chatHistory.removeChild(loadingMessage);
        const errorMessage = document.createElement('div');
        errorMessage.className = 'message system';
        errorMessage.innerHTML = '<div class="content">发生错误，请重试</div>';
        chatHistory.appendChild(errorMessage);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    });
});

// 从历史继续
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('continue-button')) {
        const index = e.target.getAttribute('data-index') || 
                    Array.from(document.querySelectorAll('.message')).indexOf(
                        e.target.closest('.message')
                    );
        
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/continue_from_history';
        form.style.display = 'none';
        
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'history_index';
        input.value = index;
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
});

// 清空日志
document.getElementById('clear-logs').addEventListener('click', function() {
    document.getElementById('recursion-logs').innerHTML = 
        '<div style="text-align: center; color: #999; padding: 20px;">暂无递归调用记录</div>';
});

// 更新递归日志
function updateRecursionLogs() {
    fetch('/get_recursion_logs')
        .then(response => response.json())
        .then(logs => {
            const logsContainer = document.getElementById('recursion-logs');
            if (logs.length > 0) {
                logsContainer.innerHTML = '';
                logs.forEach(log => {
                    const logElement = document.createElement('div');
                    logElement.className = `recursion-log ${log.level}`;
                    logElement.innerHTML = `
                        <div class="timestamp">${log.timestamp}</div>
                        <div class="function">${log.level} - ${log.function}</div>
                        ${log.params ? `<div class="params">参数: ${JSON.stringify(log.params)}</div>` : ''}
                        ${log.result ? `<div class="result">结果: ${JSON.stringify(log.result)}</div>` : ''}
                    `;
                    logsContainer.appendChild(logElement);
                });
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        });
}

// HTML转义函数
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>'"]/g, m => map[m]);
}

// 页面加载时处理现有的Markdown内容
document.addEventListener('DOMContentLoaded', function() {
    // 处理所有markdown-content元素
    document.querySelectorAll('.markdown-content').forEach(element => {
        const content = element.textContent;
        const html = marked.parse(content);
        element.innerHTML = html;
    });
    
    // 对代码块应用语法高亮
    if (typeof hljs !== 'undefined') {
        hljs.highlightAll();
    }
});

// 自动滚动到底部
window.addEventListener('load', function() {
    const chatHistory = document.getElementById('chat-history');
    chatHistory.scrollTop = chatHistory.scrollHeight;
});