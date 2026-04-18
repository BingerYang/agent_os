const WorkflowPage = {
            setup() {
                const scenarios = ref(['祈福祝寿', '财神唱诵', '周公解梦', '反诈守财']);
                const currentScenario = ref('祈福祝寿');
                const defaultWelcome = { role: 'ai', content: '您好！我是您的智能助手，请问有什么可以帮助您的？' };
                const messages = ref([{ ...defaultWelcome }]);
                const inputMessage = ref('');
                const temperature = ref(0.7);
                const topP = ref(0.9);
                const enableSearch = ref(false);
                const thinkingBudget = ref(4096);
                const deepThinking = ref(false);

                const intents = ref([
                    { name: '求财祈福', action: 'LED_MODE_GOLD_PULSE', enabled: true },
                    { name: '健康长寿', action: 'LED_MODE_GREEN_FLOW', enabled: true },
                    { name: '反诈预警', action: 'LED_MODE_ALERT_RED', enabled: true }
                ]);

                // Model Selection Modal
                const showModelModal = ref(false);
                const selectedModelCategory = ref('自定义模型');
                const selectedModel = ref('AI财神专业模型');
                const filterAuthor = ref('全部作者');
                const filterSupplier = ref('全部供应商');
                const filterType = ref('全部类型');
                const filterCapability = ref('全部能力');
                const filterLength = ref('全部长度');

                const modelCategories = ref([
                    { id: 'tongyi', name: '通义千问' },
                    { id: 'custom', name: '自定义模型' },
                    { id: 'gpt', name: 'GPT系列' },
                    { id: 'deepseek', name: 'DeepSeek' },
                    { id: 'doubao', name: '豆包' },
                    { id: 'grok', name: 'Grok' }
                ]);

                const modelsByCategory = ref({
                    '通义千问': [
                        { name: 'qwen-turbo', desc: '通义千问超大规模语言模型，支持中文英文对话' },
                        { name: 'qwen-plus', desc: '通义千问增强版，更好的推理能力' },
                        { name: 'qwen-max', desc: '通义千问最强版本，复杂任务处理' }
                    ],
                    '自定义模型': [
                        { name: 'AI财神专业模型', desc: '针对AI财神场景训练的专业模型' },
                        { name: '寺庙场景模型', desc: '寺庙场景专用模型' }
                    ],
                    'GPT系列': [
                        { name: 'gpt-3.5-turbo', desc: 'OpenAI GPT-3.5 模型' },
                        { name: 'gpt-4', desc: 'OpenAI GPT-4 模型' },
                        { name: 'gpt-4-turbo', desc: 'OpenAI GPT-4 Turbo 模型' }
                    ],
                    'DeepSeek': [
                        { name: 'deepseek-chat', desc: 'DeepSeek 对话模型' },
                        { name: 'deepseek-coder', desc: 'DeepSeek 代码模型' }
                    ],
                    '豆包': [
                        { name: 'doubao-pro', desc: '字节跳动豆包Pro模型' },
                        { name: 'doubao-lite', desc: '字节跳动豆包Lite模型' }
                    ],
                    'Grok': [
                        { name: 'grok-beta', desc: 'X AI Grok Beta模型' }
                    ]
                });

                const confirmModelSelection = () => {
                    showModelModal.value = false;
                };

                const sendMessage = () => {
                    if (!inputMessage.value.trim()) return;
                    messages.value.push({ role: 'user', content: inputMessage.value });
                    inputMessage.value = '';
                    setTimeout(() => {
                        const suffix = deepThinking.value ? '（已开启深度思考 · 模拟）' : '';
                        messages.value.push({
                            role: 'ai',
                            content: '收到您的请求，正在为您处理...（模拟回复，对接 POST /api/chat）' + suffix
                        });
                    }, 1000);
                };

                const newConversation = () => {
                    messages.value = [{ ...defaultWelcome }];
                };

                const clearConversation = () => {
                    messages.value = [];
                };

                const exportSnapshot = () => {
                    alert('导出场景快照（原型占位）：将包含当前场景、模型参数与意图映射配置。');
                };

                return {
                    scenarios, currentScenario, messages, inputMessage,
                    temperature, topP, enableSearch, thinkingBudget, deepThinking,
                    intents, sendMessage, newConversation, clearConversation, exportSnapshot,
                    showModelModal, selectedModelCategory, selectedModel,
                    filterAuthor, filterSupplier, filterType, filterCapability, filterLength,
                    modelCategories, modelsByCategory, confirmModelSelection
                };
            },
            template: `
                <div>
                    <div class="page-header">
                        <h1 class="page-title">场景工作流编排</h1>
                        <p class="page-desc">三栏布局：场景与模型参数、端云沙盒、意图映射（PRD 5.3）。沙盒调用 POST /api/chat。</p>
                    </div>

                    <div class="workflow-layout">
                        <!-- Left Panel: Configuration -->
                        <div class="workflow-panel">
                            <div class="workflow-panel-header">场景配置与模型参数</div>
                            <div class="workflow-panel-body">
                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label class="form-label">运营场景</label>
                                    <select class="form-input" v-model="currentScenario">
                                        <option v-for="s in scenarios" :key="s" :value="s">{{ s }}</option>
                                    </select>
                                </div>

                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label class="form-label">选择模型</label>
                                    <button class="btn btn-secondary btn-sm" style="width: 100%;">
                                        🔍 选择模型
                                    </button>
                                </div>

                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label class="form-label">角色设定 (System Prompt)</label>
                                    <textarea class="form-textarea" rows="4" placeholder="自定义 AI 回复风格与话术要求..."></textarea>
                                </div>

                                <div class="slider-container">
                                    <div class="slider-header">
                                        <span class="slider-label">多样性 (Temperature)</span>
                                        <span class="slider-value">{{ temperature }}</span>
                                    </div>
                                    <input type="range" class="slider" min="0" max="1" step="0.05" v-model="temperature">
                                </div>

                                <div class="slider-container">
                                    <div class="slider-header">
                                        <span class="slider-label">核采样 (Top-P)</span>
                                        <span class="slider-value">{{ topP }}</span>
                                    </div>
                                    <input type="range" class="slider" min="0" max="1" step="0.05" v-model="topP">
                                </div>

                                <div class="form-group" style="margin: 16px 0;">
                                    <div style="display: flex; align-items: center; justify-content: space-between;">
                                        <span class="form-label" style="margin: 0;">联网搜索</span>
                                        <div class="toggle" :class="{ active: enableSearch }" @click="enableSearch = !enableSearch"></div>
                                    </div>
                                </div>

                                <div class="slider-container">
                                    <div class="slider-header">
                                        <span class="slider-label">思维链最大输出 tokens（thinking_budget）</span>
                                        <span class="slider-value">{{ thinkingBudget }}</span>
                                    </div>
                                    <input type="range" class="slider" min="1" max="32768" step="1" v-model.number="thinkingBudget">
                                </div>

                                <div class="btn-group" style="margin-top: 20px;">
                                    <button class="btn btn-primary btn-sm">💾 保存</button>
                                    <button class="btn btn-secondary btn-sm">📤 发布到端侧</button>
                                    <button type="button" class="btn btn-secondary btn-sm" @click="exportSnapshot">📎 导出场景快照</button>
                                </div>
                            </div>
                        </div>

                        <!-- Middle Panel: Sandbox -->
                        <div class="workflow-panel">
                            <div class="workflow-panel-header" style="flex-wrap: wrap; gap: 8px;">
                                <span>端云交互实时沙盒</span>
                                <span style="font-size: 12px; color: var(--text-tertiary);">{{ currentScenario }}</span>
                                <span style="flex: 1;"></span>
                                <button type="button" class="btn btn-secondary btn-sm" @click="newConversation">新建对话</button>
                                <button type="button" class="btn btn-secondary btn-sm" @click="clearConversation">清空对话</button>
                                <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary);">
                                    <span>深度思考</span>
                                    <div class="toggle" :class="{ active: deepThinking }" @click="deepThinking = !deepThinking"></div>
                                </div>
                            </div>
                            <div class="chat-container">
                                <div class="chat-messages">
                                    <div v-for="(msg, index) in messages" :key="index" class="chat-message" :class="msg.role">
                                        <div class="chat-avatar" :class="msg.role">
                                            {{ msg.role === 'user' ? 'U' : '🤖' }}
                                        </div>
                                        <div class="chat-bubble">{{ msg.content }}</div>
                                    </div>
                                </div>
                                <div class="chat-input-area">
                                    <div class="chat-input-wrapper">
                                        <textarea class="chat-input" v-model="inputMessage" placeholder="输入消息..." rows="1"></textarea>
                                        <button class="chat-send-btn" @click="sendMessage">➤</button>
                                    </div>
                                    <div style="margin-top: 8px; font-size: 12px; color: var(--text-tertiary);">
                                        💡 当前为模型实验场，对话用于模型调优和场景复现
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Right Panel: Intent Mapping -->
                        <div class="workflow-panel">
                            <div class="workflow-panel-header">意图触发与映射 (Actions)</div>
                            <div class="workflow-panel-body">
                                <div style="margin-bottom: 16px;">
                                    <button class="btn btn-primary btn-sm" style="width: 100%;">+ 新增语义映射</button>
                                </div>

                                <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 12px;">
                                    已配置映射 ({{ intents.length }})
                                </div>

                                <div class="intent-item" v-for="intent in intents" :key="intent.name">
                                    <div class="intent-info">
                                        <span class="intent-name">{{ intent.name }}</span>
                                        <span class="intent-action">{{ intent.action }}</span>
                                    </div>
                                    <div class="toggle" :class="{ active: intent.enabled }" @click="intent.enabled = !intent.enabled"></div>
                                </div>

                                <div style="margin-top: 20px; padding: 12px; background: var(--bg-secondary); border-radius: 8px; font-size: 12px; color: var(--text-secondary);">
                                    <strong>端云协同机制</strong><br>
                                    映射在设备下次同步心跳时生效；核心意图将直接挂载在端侧离线模型中。
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Model Selection Modal -->
                    <div class="modal-overlay" v-if="showModelModal" @click.self="showModelModal = false">
                        <div class="modal" style="max-width: 720px; height: 600px;">
                            <div class="modal-header">
                                <span class="modal-title">选择模型</span>
                                <button class="modal-close" @click="showModelModal = false">×</button>
                            </div>
                            <div style="padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; gap: 12px; flex-wrap: wrap;">
                                <select class="filter-select" v-model="filterAuthor">
                                    <option>全部作者</option>
                                    <option>阿里云</option>
                                    <option>OpenAI</option>
                                    <option>DeepSeek</option>
                                </select>
                                <select class="filter-select" v-model="filterSupplier">
                                    <option>全部供应商</option>
                                    <option>阿里云百炼</option>
                                    <option>硅基流动</option>
                                    <option>OpenAI</option>
                                </select>
                                <select class="filter-select" v-model="filterType">
                                    <option>全部类型</option>
                                    <option>深度思考</option>
                                    <option>文本生成</option>
                                </select>
                                <select class="filter-select" v-model="filterCapability">
                                    <option>全部能力</option>
                                    <option>Function Calling</option>
                                    <option>结构化输出</option>
                                </select>
                                <select class="filter-select" v-model="filterLength">
                                    <option>全部长度</option>
                                    <option>0-32K</option>
                                    <option>32K-128K</option>
                                </select>
                            </div>
                            <div class="modal-body" style="display: flex; padding: 0; overflow: hidden;">
                                <!-- Left: Categories -->
                                <div style="width: 180px; border-right: 1px solid var(--border); overflow-y: auto; background: var(--bg-secondary);">
                                    <div
                                        v-for="cat in modelCategories"
                                        :key="cat.id"
                                        style="padding: 12px 16px; cursor: pointer; font-size: 14px;"
                                        :style="selectedModelCategory === cat.name ? 'background: var(--primary-light); color: var(--primary); font-weight: 500;' : 'color: var(--text-secondary);'"
                                        @click="selectedModelCategory = cat.name"
                                    >
                                        {{ cat.name }}
                                    </div>
                                </div>
                                <!-- Right: Models -->
                                <div style="flex: 1; overflow-y: auto; padding: 16px;">
                                    <div
                                        v-for="model in modelsByCategory[selectedModelCategory]"
                                        :key="model.name"
                                        style="display: flex; align-items: flex-start; gap: 12px; padding: 12px; border-radius: 8px; cursor: pointer; margin-bottom: 8px;"
                                        :style="selectedModel === model.name ? 'background: var(--primary-light);' : 'background: var(--bg-secondary);'"
                                        @click="selectedModel = model.name"
                                    >
                                        <input type="radio" :value="model.name" v-model="selectedModel" style="margin-top: 2px;">
                                        <div>
                                            <div style="font-weight: 500; margin-bottom: 4px;">{{ model.name }}</div>
                                            <div style="font-size: 13px; color: var(--text-secondary);">{{ model.desc }}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <span style="font-size: 13px; color: var(--text-secondary);">已选 1/1</span>
                                <div style="flex: 1;"></div>
                                <button class="btn btn-secondary" @click="showModelModal = false">取消</button>
                                <button class="btn btn-primary" @click="confirmModelSelection">确定</button>
                            </div>
                        </div>
                    </div>
                </div>
            `
        };