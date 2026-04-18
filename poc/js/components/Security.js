const SecurityPage = {
            setup() {
                const scenes = ref([
                    { name: '虚假投资诈骗', category: '金融诈骗', risk: 'high', desc: '诱导用户进行虚假投资，承诺高额回报' },
                    { name: '冒充公检法', category: '身份冒充', risk: 'high', desc: '冒充公安机关要求转账或提供个人信息' },
                    { name: '虚假中奖', category: '利诱诈骗', risk: 'medium', desc: '以中奖为由要求支付手续费或税费' },
                    { name: '钓鱼链接', category: '网络诈骗', risk: 'medium', desc: '发送虚假链接窃取用户账户信息' }
                ]);

                const logs = ref([
                    { time: '2026-02-07 14:32:15', device: 'FG-001-A', scene: '虚假投资诈骗', risk: 'high', summary: '检测到可疑投资话术' },
                    { time: '2026-02-07 13:28:42', device: 'FG-003-C', scene: '虚假中奖', risk: 'medium', summary: '用户询问中奖信息' },
                    { time: '2026-02-07 11:15:33', device: 'FG-002-B', scene: '钓鱼链接', risk: 'medium', summary: '提及外部链接' }
                ]);

                const messages = ref([
                    { role: 'ai', content: '您好！我是反诈参谋，可以为您提供诈骗识别建议和风险处置方案。' }
                ]);
                const inputMessage = ref('');

                const sendMessage = () => {
                    if (!inputMessage.value.trim()) return;
                    messages.value.push({ role: 'user', content: inputMessage.value });
                    inputMessage.value = '';
                    setTimeout(() => {
                        messages.value.push({
                            role: 'ai',
                            content: '根据您描述的情况，这很可能是虚假投资诈骗。建议：1. 不要转账；2. 挂断电话；3. 拨打 96110 咨询。'
                        });
                    }, 1000);
                };

                return { scenes, logs, messages, inputMessage, sendMessage };
            },
            template: `
                <div>
                    <div class="page-header">
                        <h1 class="page-title">反诈与安全审计</h1>
                        <p class="page-desc">识别诈骗场景、查看审计日志，获取反诈话术与处置建议</p>
                    </div>

                    <div class="security-grid">
                        <!-- Scene Library -->
                        <div class="security-panel">
                            <div class="security-panel-header">诈骗场景库</div>
                            <div class="security-panel-body">
                                <div class="scene-card" v-for="scene in scenes" :key="scene.name">
                                    <div class="scene-header">
                                        <span class="scene-name">{{ scene.name }}</span>
                                        <span class="scene-risk" :class="scene.risk">{{ scene.risk === 'high' ? '高风险' : '中风险' }}</span>
                                    </div>
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">{{ scene.category }}</div>
                                    <div class="scene-desc">{{ scene.desc }}</div>
                                </div>
                            </div>
                        </div>

                        <!-- Audit Logs -->
                        <div class="security-panel">
                            <div class="security-panel-header">审计日志</div>
                            <div class="security-panel-body">
                                <div v-for="log in logs" :key="log.time" style="padding: 12px; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 12px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                        <span style="font-size: 12px; color: var(--text-tertiary);">{{ log.time }}</span>
                                        <span class="tag" :class="log.risk === 'high' ? 'tag-error' : 'tag-warning'" style="font-size: 11px;">
                                            {{ log.risk === 'high' ? '高风险' : '中风险' }}
                                        </span>
                                    </div>
                                    <div style="font-size: 13px; font-weight: 500; margin-bottom: 4px;">{{ log.scene }}</div>
                                    <div style="font-size: 12px; color: var(--text-secondary);">{{ log.device }} · {{ log.summary }}</div>
                                </div>
                            </div>
                        </div>

                        <!-- Anti-fraud Assistant -->
                        <div class="security-panel">
                            <div class="security-panel-header">反诈参谋</div>
                            <div class="chat-container" style="height: 500px;">
                                <div class="chat-messages" style="flex: 1; max-height: 380px;">
                                    <div v-for="(msg, index) in messages" :key="index" class="chat-message" :class="msg.role">
                                        <div class="chat-avatar" :class="msg.role">
                                            {{ msg.role === 'user' ? 'U' : '🛡️' }}
                                        </div>
                                        <div class="chat-bubble">{{ msg.content }}</div>
                                    </div>
                                </div>
                                <div class="chat-input-area">
                                    <div class="chat-input-wrapper">
                                        <textarea class="chat-input" v-model="inputMessage" placeholder="描述可疑情况..." rows="1"></textarea>
                                        <button class="chat-send-btn" @click="sendMessage">➤</button>
                                    </div>
                                    <div style="margin-top: 8px; font-size: 12px; color: var(--text-tertiary); text-align: center;">
                                        支持语音输入与 TTS 播报
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `
        };