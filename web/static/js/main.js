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

// 会话重命名
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('rename-btn')) {
        e.stopPropagation(); // 阻止事件冒泡，避免触发会话切换
        const sessionId = e.target.getAttribute('data-id');
        const newName = prompt('请输入新的会话名称:', sessionId);
        
        if (newName && newName.trim() && newName !== sessionId) {
            fetch('/rename_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `old_name=${encodeURIComponent(sessionId)}&new_name=${encodeURIComponent(newName.trim())}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 更新界面上的会话名称
                    const sessionItem = e.target.closest('.session-item');
                    if (sessionItem) {
                        const sessionIdElement = sessionItem.querySelector('.session-id');
                        if (sessionIdElement) {
                            sessionIdElement.textContent = newName.trim();
                        }
                    }
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                alert('重命名失败');
            });
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