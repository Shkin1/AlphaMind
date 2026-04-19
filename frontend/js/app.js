/**
 * AlphaMind 投研会 - SSE版本前端
 * 支持全屏、Markdown渲染、选择题弹框
 */

const API_BASE = window.location.origin;

// State
let currentMeetingId = null;
let currentPhase = 0;
let advisorsData = [];
let isFullscreen = false;
let quizAnswers = {};

// DOM Elements
let topicInput, startBtn, meetingSection, meetingIdSpan, phaseName;
let discussionStream, selectedAdvisors, tensionPairs;
let qaSection, qaList, submitAnswersBtn;
let reportSection, generateReportBtn, reportModal, reportContent;
let advisorsGrid, progressFill, fullscreenBtn;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    loadAdvisors();
    setupMarkdown();
});

function initElements() {
    topicInput = document.getElementById('topicInput');
    startBtn = document.getElementById('startBtn');
    meetingSection = document.getElementById('meetingSection');
    meetingIdSpan = document.getElementById('meetingId');
    phaseName = document.getElementById('phaseName');
    discussionStream = document.getElementById('discussionStream');
    selectedAdvisors = document.getElementById('selectedAdvisors');
    tensionPairs = document.getElementById('tensionPairs');
    qaSection = document.getElementById('qaSection');
    qaList = document.getElementById('qaList');
    submitAnswersBtn = document.getElementById('submitAnswersBtn');
    reportSection = document.getElementById('reportSection');
    generateReportBtn = document.getElementById('generateReportBtn');
    reportModal = document.getElementById('reportModal');
    reportContent = document.getElementById('reportContent');
    advisorsGrid = document.getElementById('advisorsGrid');
    progressFill = document.getElementById('progressFill');
    fullscreenBtn = document.getElementById('fullscreenBtn');

    // Event listeners
    if (startBtn) startBtn.addEventListener('click', startMeeting);
    if (submitAnswersBtn) submitAnswersBtn.addEventListener('click', submitAnswers);
    if (generateReportBtn) generateReportBtn.addEventListener('click', generateReport);
    if (fullscreenBtn) fullscreenBtn.addEventListener('click', toggleFullscreen);
}

// Markdown配置
function setupMarkdown() {
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false
        });
    }
}

// 渲染Markdown（简化版）
function renderMarkdown(text) {
    if (!text) return '';

    // 简单处理：换行、加粗、标题
    let html = text;

    // 换行转br
    html = html.replace(/\n/g, '<br>');

    // 加粗 **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 标题 ### text
    html = html.replace(/### (.+)/g, '<h3>$1</h3>');
    html = html.replace(/## (.+)/g, '<h2>$1</h2>');
    html = html.replace(/# (.+)/g, '<h1>$1</h1>');

    // 列表项 - text
    html = html.replace(/^- (.+)/g, '<li>$1</li>');

    // 数字列表 1. text
    html = html.replace(/^\d+\. (.+)/g, '<li>$1</li>');

    return html;
}

// 全屏切换
function toggleFullscreen() {
    isFullscreen = !isFullscreen;

    if (isFullscreen) {
        document.body.classList.add('fullscreen-mode');
        fullscreenBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M8 3v3a2 2 0 01-2 2H3m18 0h-3a2 2 0 01-2-2V3m0 18v-3a2 2 0 012-2h3M3 16h3a2 2 0 012 2v3"/>
            </svg>
        `;
        fullscreenBtn.title = '退出全屏';
    } else {
        document.body.classList.remove('fullscreen-mode');
        fullscreenBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/>
            </svg>
        `;
        fullscreenBtn.title = '全屏模式';
    }
}

// Load Advisors
async function loadAdvisors() {
    try {
        const response = await fetch(`${API_BASE}/api/advisors`);
        const data = await response.json();
        advisorsData = data.advisors;

        if (advisorsGrid) {
            advisorsGrid.innerHTML = advisorsData.map(a => `
                <div class="advisor-card">
                    <div class="advisor-avatar">${a.name[0]}</div>
                    <div class="advisor-name">${a.name}</div>
                    <div class="advisor-title">${a.title.split(',')[0]}</div>
                    <span class="advisor-type">${getTypeLabel(a.type)}</span>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('加载顾问失败:', error);
    }
}

function getTypeLabel(type) {
    const labels = {
        'value': '价值投资', 'growth': '成长投资',
        'technical': '技术分析', 'quant': '量化分析',
        'risk': '风险投资', 'trading': '交易',
        'pe': '私募视角'
    };
    return labels[type] || type;
}

function setExample(text) {
    if (topicInput) {
        topicInput.value = text;
        topicInput.focus();
    }
}

// Start Meeting - 在新标签页打开会议页面
async function startMeeting() {
    const topic = topicInput.value.trim();
    if (!topic) {
        showMessage('请输入投资议题', 'warning');
        return;
    }

    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="loading-spinner"></span><span>启动中...</span>';

    try {
        // 1. 创建会议
        const response = await fetch(`${API_BASE}/api/meeting/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const meetingId = data.meeting_id;

        // 2. 在新标签页打开会议页面，首页保留
        window.open(`/meeting.html?meeting_id=${meetingId}&topic=${encodeURIComponent(topic)}`, '_blank');

        // 3. 重置按钮，用户可以继续输入新议题
        resetStartBtn();
        showMessage('会议已在新窗口启动', 'success');

    } catch (error) {
        console.error('启动失败:', error);
        showMessage('启动失败: ' + error.message, 'error');
        resetStartBtn();
    }
}

// Connect SSE
function connectSSE(url) {
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('SSE消息:', data);
            handleSSEMessage(data);
        } catch (e) {
            console.error('解析消息失败:', e);
        }
    };

    eventSource.onerror = (error) => {
        console.error('SSE错误:', error);
        eventSource.close();
    };

    return eventSource;
}

// Handle SSE Message - 整块返回版本
function handleSSEMessage(data) {
    // 移除加载指示器
    removeTypingIndicator();

    if (data.type === 'error') {
        showMessage(data.message, 'error');
        return;
    }

    console.log('SSE消息:', data);

    if (data.phase) {
        updatePhase(data.phase);
    }

    switch (data.type) {
        case 'phase_update':
            handlePhaseUpdate(data);
            if (data.phase === 'PHASE_0') {
                addTypingIndicator('正在准备澄清问题...');
            } else if (data.phase === 'PHASE_2') {
                addTypingIndicator('顾问们正在入场...');
            }
            break;
        case 'waiting_for_quiz':
            // 等待用户提交选择题，显示弹框（只在这里调用一次）
            showQuizModal(QUIZ_QUESTIONS);
            break;
        case 'advisor_speaking':
            // 显示"正在发言"加载提示
            addTypingIndicator(`${data.advisor_name} 正在发言...`);
            break;
        case 'advisor_opinion':
            // 完整意见（整块返回）
            handleAdvisorOpinion(data);
            removeTypingIndicator();
            break;
        case 'crossfire':
            handleCrossfire(data);
            break;
        case 'resolution':
            handleResolution(data);
            break;
        case 'complete':
            removeTypingIndicator();
            handleComplete();
            break;
        case 'round_summary':
            handleRoundSummary(data);
            break;
    }
}

// 处理每轮总结
function handleRoundSummary(data) {
    if (!discussionStream) return;

    const summary = data.data;
    const html = `
        <div class="chat-message system round-summary">
            <div class="chat-avatar">📊</div>
            <div class="chat-content">
                <div class="chat-bubble summary-bubble">
                    <div class="summary-title">第 ${summary?.round || 0} 轮讨论</div>
                    <div class="summary-stats">
                        发言人数: ${summary?.speakers_count || 0} 位<br>
                        观点分布: ${summary?.sentiment_distribution || '分析中...'}
                    </div>
                </div>
            </div>
        </div>
    `;

    discussionStream.innerHTML += html;
    scrollToBottom();
}

// 添加打字指示器
function addTypingIndicator(text = '正在分析...') {
    if (!discussionStream) return;

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <span class="typing-text">${text}</span>
    `;
    discussionStream.appendChild(indicator);
    scrollToBottom();
}

// 移除打字指示器
function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

// Update Phase
function updatePhase(phase) {
    const phaseNum = parseInt(phase.replace('PHASE_', ''));
    currentPhase = phaseNum;

    const phaseNames = ['议题接收', '信息补全', '选席', '第一轮发言', '交锋', '决议'];
    if (phaseName) {
        phaseName.textContent = `Phase ${phaseNum}: ${phaseNames[phaseNum] || ''}`;
    }

    if (progressFill) {
        progressFill.style.width = `${(phaseNum / 5) * 100}%`;
    }

    document.querySelectorAll('.phase-step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index < phaseNum) step.classList.add('completed');
        else if (index === phaseNum) step.classList.add('active');
    });
}

// Handle Phase Update - 简洁的群聊风格
function handlePhaseUpdate(data) {
    if (!discussionStream) return;

    let html = '';
    switch (data.phase) {
        case 'PHASE_0':
            html = `
                <div class="chat-message system">
                    <div class="chat-avatar">主持人</div>
                    <div class="chat-content">
                        <div class="chat-bubble">
                            <div class="chat-text">议题已接收：<strong>${data.data?.restated_topic || ''}</strong></div>
                            <div class="chat-meta">类型: ${data.data?.topic_type || '综合分析'}</div>
                        </div>
                    </div>
                </div>
            `;
            break;

        case 'PHASE_1':
            // 跳过Phase 1，不显示
            if (data.data?.skip) return;
            break;

        case 'PHASE_2':
            html = `
                <div class="chat-message system">
                    <div class="chat-avatar">主持人</div>
                    <div class="chat-content">
                        <div class="chat-bubble">
                            <div class="chat-text">已邀请 ${data.data?.advisors?.length || 0} 位顾问参与讨论</div>
                            <div class="chat-advisors">${data.data?.advisors?.map(a => `<span class="advisor-tag">${a}</span>`).join('') || ''}</div>
                        </div>
                    </div>
                </div>
            `;
            break;
    }

    discussionStream.innerHTML += html;
    scrollToBottom();
}

// Show Questions
function showQuestions(questions) {
    if (!qaList || !qaSection) return;

    qaSection.style.display = 'block';
    qaList.innerHTML = questions.map((q, i) => `
        <div class="qa-item">
            <label class="qa-label">${i + 1}. ${q}</label>
            <input type="text" class="qa-input" id="answer_${i}" placeholder="请回答...">
        </div>
    `).join('');
}

// Submit Answers
async function submitAnswers() {
    if (!currentMeetingId) return;

    const answers = {};
    document.querySelectorAll('.qa-input').forEach((input, i) => {
        answers[`question_${i}`] = input.value || '暂无回答';
    });

    try {
        // 1. 提交答案
        const response = await fetch(`${API_BASE}/api/meeting/${currentMeetingId}/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        showMessage('回答已收到，继续分析...', 'success');
        if (qaSection) qaSection.style.display = 'none';

        // 2. 添加加载指示器
        addTypingIndicator('顾问们正在发言...');

        // 3. 连接SSE继续Phase 3-5
        connectSSE(`${API_BASE}/api/meeting/${currentMeetingId}/continue`);

    } catch (error) {
        console.error('提交失败:', error);
        showMessage('提交失败: ' + error.message, 'error');
    }
}

// Handle Advisor Opinion - 群聊风格 + Markdown渲染
function handleAdvisorOpinion(data) {
    if (!discussionStream) return;

    // 移除加载指示器
    removeTypingIndicator();

    const opinion = data.data;
    const opinionText = opinion?.opinion || '';

    // 使用Markdown渲染
    const renderedContent = renderMarkdown(opinionText);

    html = `
        <div class="chat-message advisor" data-advisor="${opinion?.advisor_name || ''}">
            <div class="chat-avatar advisor-avatar">${(opinion?.advisor_name || 'A')[0]}</div>
            <div class="chat-content">
                <div class="chat-name">${opinion?.advisor_name || '顾问'}</div>
                <div class="chat-bubble advisor-bubble">
                    <div class="chat-text">${renderedContent}</div>
                    <div class="chat-meta">置信度 ${((opinion?.confidence || 0.7) * 100).toFixed(0)}%</div>
                </div>
            </div>
        </div>
    `;

    discussionStream.innerHTML += html;
    scrollToBottom();
}

// Handle Crossfire
function handleCrossfire(data) {
    if (!discussionStream) return;

    const dialog = data.data;
    const html = `
        <div class="stream-item crossfire">
            <div class="stream-header-label">交锋: ${dialog?.topic || ''}</div>
            <div class="crossfire-dialog">
                <div class="dialog-bubble left">
                    <div class="dialog-advisor">${dialog?.advisor1 || ''}</div>
                    <div class="dialog-content">${(dialog?.response1 || '').substring(0, 200)}...</div>
                </div>
                <div class="dialog-bubble right">
                    <div class="dialog-advisor">${dialog?.advisor2 || ''}</div>
                    <div class="dialog-content">${(dialog?.response2 || '').substring(0, 200)}...</div>
                </div>
            </div>
        </div>
    `;

    discussionStream.innerHTML += html;
    scrollToBottom();
}

// Handle Resolution - 群聊风格总结
function handleResolution(data) {
    if (!discussionStream) return;

    const resolution = data.data;
    const consensusText = resolution?.consensus?.slice(0, 3).join('<br>') || '暂无共识';
    const overallText = resolution?.overall_judgment?.substring(0, 300) || '综合分析完成';

    html = `
        <div class="chat-message system">
            <div class="chat-avatar">主持人</div>
            <div class="chat-content">
                <div class="chat-name">投研会主持人</div>
                <div class="chat-bubble summary-bubble">
                    <div class="summary-title">📋 会议总结</div>
                    <div class="summary-section">
                        <strong>共识观点:</strong><br>
                        ${consensusText}
                    </div>
                    <div class="summary-section">
                        <strong>总体判断:</strong><br>
                        ${overallText}
                    </div>
                </div>
            </div>
        </div>
    `;

    discussionStream.innerHTML += html;
    scrollToBottom();
}

// Handle Complete
function handleComplete() {
    if (reportSection) reportSection.style.display = 'block';
    resetStartBtn();
    showMessage('投研会已完成！', 'success');
}

// Show Selected Advisors
function showSelectedAdvisors(advisors, tensionPairsList) {
    if (selectedAdvisors) {
        selectedAdvisors.innerHTML = advisors.map(name => `
            <div class="advisor-mini-card">
                <div class="mini-avatar">${name[0]}</div>
                <span class="mini-name">${name.split('(')[0]}</span>
            </div>
        `).join('');
    }

    if (tensionPairs) {
        tensionPairs.innerHTML = `
            <div class="tension-title">张力对</div>
            ${tensionPairsList.map(pair => `
                <div class="tension-item">
                    <span>${pair?.advisor1?.split('(')[0] || ''}</span>
                    <span class="tension-vs">VS</span>
                    <span>${pair?.advisor2?.split('(')[0] || ''}</span>
                </div>
            `).join('')}
        `;
    }
}

// Generate Report
async function generateReport() {
    if (!currentMeetingId) return;

    try {
        const response = await fetch(`${API_BASE}/api/meeting/${currentMeetingId}/report`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (reportContent) reportContent.innerHTML = data.report_html;
        if (reportModal) reportModal.classList.add('active');

    } catch (error) {
        console.error('生成报告失败:', error);
        showMessage('生成报告失败: ' + error.message, 'error');
    }
}

// Helper Functions
function resetStartBtn() {
    if (startBtn) {
        startBtn.disabled = false;
        startBtn.innerHTML = '<span class="btn-text">开始投研会</span><svg viewBox="0 0 24 24" width="20" height="20"><path d="M5 12h14M12 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
    }
}

function scrollToBottom() {
    if (discussionStream) {
        discussionStream.scrollTop = discussionStream.scrollHeight;
    }
}

function showMessage(text, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${text}</span>`;
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'error' ? '#ff4d4f' : type === 'success' ? '#52c41a' : type === 'warning' ? '#faad14' : '#1677ff'};
        color: #fff;
        border-radius: 8px;
        font-size: 14px;
        z-index: 1100;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function closeModal() {
    if (reportModal) reportModal.classList.remove('active');
}

function downloadReport() {
    if (!reportContent) return;
    const htmlContent = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>投研会报告</title><style>body{font-family:sans-serif;padding:40px;max-width:800px;margin:0 auto}</style></head><body>${reportContent.innerHTML}</body></html>`;
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `投研会报告_${currentMeetingId}.html`;
    a.click();
    URL.revokeObjectURL(url);
}

// Global
window.setExample = setExample;
window.closeModal = closeModal;
window.downloadReport = downloadReport;
window.toggleFullscreen = toggleFullscreen;

// ========== 澄清问题弹框 ==========

function showQuizModal(questions) {
    removeTypingIndicator();

    const modal = document.createElement('div');
    modal.className = 'quiz-modal';
    modal.id = 'quizModal';

    let selectedOptions = {};
    questions.forEach(q => {
        selectedOptions[q.id] = q.default;
    });

    modal.innerHTML = `
        <div class="quiz-content">
            <h3>📋 请选择你的投资偏好</h3>
            <div class="quiz-list">
                ${questions.map(q => `
                    <div class="quiz-item" data-question="${q.id}">
                        <div class="quiz-question">${q.question}</div>
                        <div class="quiz-options">
                            ${q.options.map(opt => `
                                <button class="quiz-option ${opt === q.default ? 'selected' : ''}"
                                        data-question="${q.id}"
                                        data-value="${opt}">
                                    ${opt}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
            <button class="quiz-submit" id="quizSubmitBtn">确认选择，开始讨论</button>
        </div>
    `;

    document.body.appendChild(modal);

    // 选项点击事件
    modal.querySelectorAll('.quiz-option').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const questionId = e.target.dataset.question;
            const value = e.target.dataset.value;

            // 取消同组其他选中
            modal.querySelectorAll(`[data-question="${questionId}"]`).forEach(b => {
                b.classList.remove('selected');
            });

            // 标记当前选中
            e.target.classList.add('selected');
            selectedOptions[questionId] = value;
        });
    });

    // 提交按钮
    const submitBtn = modal.querySelector('#quizSubmitBtn');
    submitBtn.addEventListener('click', () => {
        submitQuizAnswers(selectedOptions);
        modal.remove();
    });
}

async function submitQuizAnswers(answers) {
    if (!currentMeetingId) return;

    quizAnswers = answers;
    console.log('提交选择题答案:', answers);

    try {
        const response = await fetch(`${API_BASE}/api/meeting/${currentMeetingId}/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        showMessage('选择已提交，开始讨论...', 'success');
        addTypingIndicator('顾问们正在入场...');

        // 连接continue API继续讨论
        connectSSE(`${API_BASE}/api/meeting/${currentMeetingId}/continue`);

    } catch (error) {
        console.error('提交失败:', error);
        showMessage('提交失败: ' + error.message, 'error');
    }
}

// 预定义的选择题问题
const QUIZ_QUESTIONS = [
    {id: "time_horizon", question: "你的投资周期是？", options: ["短期(<1年)", "中期(1-3年)", "长期(>3年)"], default: "长期(>3年)"},
    {id: "position_intent", question: "你对这只股票的意向是？", options: ["考虑买入", "持有观察", "考虑卖出", "仅做分析"], default: "仅做分析"},
    {id: "risk_tolerance", question: "你的风险承受能力？", options: ["保守(厌恶亏损)", "均衡", "激进(追求高收益)"], default: "均衡"}
];

// ========== 全局导出 ==========

// 导出给HTML onclick使用的函数
window.setExample = setExample;
window.closeModal = closeModal;
window.downloadReport = downloadReport;
window.toggleFullscreen = toggleFullscreen;