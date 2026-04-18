const { createApp, ref, reactive, computed, onMounted } = Vue;
const { createRouter, createWebHashHistory } = VueRouter;

// 组件定义（内联在单文件中，避免模块导入问题）

// Login Component
const LoginPage = {
    setup() {
        const form = reactive({
            username: 'admin123',
            password: 'admin123'
        });

        const login = () => {
            if (form.username && form.password) {
                localStorage.setItem('isLoggedIn', 'true');
                localStorage.setItem('user', JSON.stringify({
                    name: form.username,
                    role: '超级管理员',
                    isAdmin: true
                }));
                router.push('/');
            }
        };

        return { form, login };
    },
    template: `
        <div class="login-page">
            <div class="login-box">
                <div class="login-header">
                    <div class="login-logo">🤖</div>
                    <h1 class="login-title">AI 智能体调度平台</h1>
                    <p class="login-subtitle">端云协同运营系统</p>
                </div>
                <form class="login-form" @submit.prevent="login">
                    <div class="form-group">
                        <label class="form-label">账号</label>
                        <input type="text" class="form-input" v-model="form.username" placeholder="请输入账号">
                    </div>
                    <div class="form-group">
                        <label class="form-label">密码</label>
                        <input type="password" class="form-input" v-model="form.password" placeholder="请输入密码">
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">登录</button>
                </form>
                <div class="login-hint">
                    默认超管账号：admin123 / admin123
                </div>
            </div>
        </div>
    `
};

// Layout Component
const AppLayout = {
    setup() {
        const user = reactive({
            name: 'admin123',
            role: '超级管理员',
            isAdmin: true
        });

        const currentRoute = computed(() => router.currentRoute.value.path);

        const logout = () => {
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('user');
            router.push('/login');
        };

        onMounted(() => {
            const savedUser = localStorage.getItem('user');
            if (savedUser) {
                Object.assign(user, JSON.parse(savedUser));
            }
        });

        return { user, currentRoute, logout };
    },
    template: `
        <div class="app-layout">
            <aside class="sidebar">
                <div class="sidebar-header">
                    <div class="sidebar-logo">🤖</div>
                    <span class="sidebar-title">AI 调度平台</span>
                </div>
                <nav class="sidebar-nav">
                    <div class="nav-section">
                        <div class="nav-section-title">模型运营</div>
                        <router-link to="/" class="nav-item" :class="{ active: currentRoute === '/' }">
                            <span class="icon">📊</span>
                            <span>业务概览</span>
                        </router-link>
                        <router-link to="/workflow" class="nav-item" :class="{ active: currentRoute === '/workflow' }">
                            <span class="icon">🤖</span>
                            <span>Agent 工作流</span>
                        </router-link>
                        <router-link to="/mcp" class="nav-item" :class="{ active: currentRoute === '/mcp' }">
                            <span class="icon">🧩</span>
                            <span>MCP 管理</span>
                        </router-link>
                        <router-link to="/skills" class="nav-item" :class="{ active: currentRoute === '/skills' }">
                            <span class="icon">⚡</span>
                            <span>Skill 技能管理</span>
                        </router-link>
                        <router-link to="/hooks" class="nav-item" :class="{ active: currentRoute === '/hooks' }">
                            <span class="icon">🔍</span>
                            <span>前后置检测</span>
                        </router-link>
                        <router-link to="/digital-human" class="nav-item" :class="{ active: currentRoute === '/digital-human' }">
                            <span class="icon">👤</span>
                            <span>数字人配置</span>
                        </router-link>
                    </div>
                    <div class="nav-section">
                        <div class="nav-section-title">硬件运维</div>
                        <router-link to="/devices" class="nav-item" :class="{ active: currentRoute === '/devices' }">
                            <span class="icon">🔌</span>
                            <span>设备资产管理</span>
                        </router-link>
                        <router-link to="/security" class="nav-item" :class="{ active: currentRoute === '/security' }">
                            <span class="icon">🛡️</span>
                            <span>反诈与安全审计</span>
                        </router-link>
                    </div>
                </nav>
                <div class="sidebar-footer">
                    <router-link to="/settings" class="nav-item" :class="{ active: currentRoute === '/settings' }">
                        <span class="icon">⚙️</span>
                        <span>全局运营设置</span>
                    </router-link>
                    <router-link to="/model-settings" class="nav-item" :class="{ active: currentRoute === '/model-settings' }">
                        <span class="icon">🧠</span>
                        <span>模型配置</span>
                    </router-link>
                </div>
            </aside>
            <main class="main-content">
                <header class="header">
                    <div class="breadcrumb">
                        <span>控制台</span>
                        <span>/</span>
                        <span class="breadcrumb-current">
                            <slot name="breadcrumb">{{ $route.meta.title || '业务概览' }}</slot>
                        </span>
                    </div>
                    <div class="header-actions">
                        <button class="header-btn">
                            <span>🔍</span>
                        </button>
                        <button class="header-btn">
                            <span>🔔</span>
                            <span class="badge">3</span>
                        </button>
                        <div class="user-menu" @click="logout">
                            <div class="user-avatar">{{ user.name[0].toUpperCase() }}</div>
                            <div class="user-info">
                                <span class="user-name">{{ user.name }}</span>
                                <span class="user-role">{{ user.role }}</span>
                            </div>
                        </div>
                    </div>
                </header>
                <div class="page-content">
                    <router-view></router-view>
                </div>
            </main>
        </div>
    `
};

// Overview Page
const OverviewPage = {
    setup() {
        const stats = ref([
            { label: '全球在线硬件数', value: '12,842', change: '+12.5%', up: true },
            { label: '意图识别吞吐量', value: '1.2M/日', change: '+8.3%', up: true },
            { label: '离线感知比例', value: '34.2%', change: '-2.1%', up: false },
            { label: '活跃运营场景数', value: '8', change: '+1', up: true }
        ]);

        const healthScore = ref(98.4);

        const intents = ref([
            { name: '祈福祝寿', value: 35 },
            { name: '财神唱诵', value: 28 },
            { name: '周公解梦', value: 20 },
            { name: '反诈守财', value: 12 },
            { name: '其他', value: 5 }
        ]);

        onMounted(() => {
            const ctx = document.getElementById('interactionChart');
            if (ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['02-01', '02-02', '02-03', '02-04', '02-05', '02-06', '02-07'],
                        datasets: [{
                            label: '云端大脑',
                            data: [1200, 1350, 1280, 1420, 1500, 1380, 1450],
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            fill: true,
                            tension: 0.4
                        }, {
                            label: '端侧感知',
                            data: [800, 920, 850, 980, 1050, 920, 1000],
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'top',
                                align: 'end'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: '#f3f4f6'
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                }
                            }
                        }
                    }
                });
            }
        });

        return { stats, healthScore, intents };
    },
    template: `
        <div>
            <div class="page-header" style="display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px;">
                <div>
                    <h1 class="page-title">业务概览</h1>
                    <p class="page-desc">实时监控业务指标与健康度</p>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
                    <input type="datetime-local" class="filter-input" style="min-width: 180px;" value="2026-02-01T00:00">
                    <span style="color: var(--text-tertiary);">～</span>
                    <input type="datetime-local" class="filter-input" style="min-width: 180px;" value="2026-02-07T00:00">
                    <button type="button" class="btn btn-secondary btn-sm">生成深度运营报告</button>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card" v-for="(stat, index) in stats" :key="index">
                    <div class="stat-label">{{ stat.label }}</div>
                    <div class="stat-value">{{ stat.value }}</div>
                    <div class="stat-change" :class="stat.up ? 'up' : 'down'">
                        <span>{{ stat.up ? '↑' : '↓' }}</span>
                        <span>{{ stat.change }}</span>
                    </div>
                </div>
            </div>

            <div class="charts-grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">端云互动频次分布</span>
                        <select class="filter-select">
                            <option>最近7天</option>
                            <option>最近30天</option>
                        </select>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="interactionChart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">健康度指数</span>
                    </div>
                    <div class="card-body">
                        <div class="health-score">
                            <div class="health-circle">
                                <span class="health-value">{{ healthScore }}</span>
                            </div>
                            <div class="health-info">
                                <div class="health-label">系统健康度</div>
                                <div class="health-desc">进意图有效交互用户 UV 占日活 15%，健康度 100 分，按比例计算</div>
                            </div>
                        </div>
                        <div style="margin-top: 24px;">
                            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">最新意图用户分布</div>
                            <div class="intent-bar" v-for="intent in intents" :key="intent.name">
                                <span class="intent-label">{{ intent.name }}</span>
                                <div class="intent-progress">
                                    <div class="intent-fill" :style="{ width: intent.value + '%' }">{{ intent.value }}%</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Workflow Page (Agent Workflow Management)
const WorkflowPage = {
    setup() {
        // Agent 列表数据 - 支持单Agent和多Agent编排
        const agents = ref([
            {
                id: 'agent-001',
                name: '财神助手 Agent',
                type: 'single',
                typeLabel: '单 Agent',
                desc: '处理财运、投资、祈福等相关咨询的单Agent服务',
                status: 'published',
                model: 'AI财神专业模型',
                // 意图识别 & 实体提取配置
                intentRecognition: {
                    enabled: true,
                    model: 'qwen-turbo',
                    shortcutThreshold: 0.85,
                    systemPrompt: '你是一个意图识别助手。请分析用户输入，识别用户意图并提取关键实体。\n\n输出JSON格式：\n{\n  "intent": "意图名称",\n  "confidence": 0.95,\n  "entities": {\n    "时间": "",\n    "地点": "",\n    "对象": ""\n  },\n  "directTool": "可直接调用的工具名（如确定）"\n}',
                    entitySchema: [
                        { name: '时间', type: 'string', required: false, desc: '用户提到的时间' },
                        { name: '地点', type: 'string', required: false, desc: '用户提到的地点' },
                        { name: '对象', type: 'string', required: false, desc: '操作对象' }
                    ]
                },
                tools: [
                    { id: 'tool-1', name: '实时黄金价格抓取', enabled: true, desc: '获取实时黄金价格数据' },
                    { id: 'tool-2', name: '股票行情查询', enabled: true, desc: 'A股、港股、美股实时行情' }
                ],
                skills: [
                    { id: 'skill-1', name: '财神对话技能', enabled: true, desc: '财神角色对话技能包' },
                    { id: 'skill-2', name: '祈福话术生成', enabled: true, desc: '根据场景生成祈福话术' }
                ],
                hooks: {
                    pre: [{ id: 'hook-1', name: '安全检测', enabled: true, desc: '检测输入是否包含敏感内容' }],
                    post: [{ id: 'hook-2', name: '内容审核', enabled: true, desc: '审核输出内容合规性' }]
                },
                apiEndpoint: '/api/v1/agent/schedule',
                updatedAt: '2024-01-15',
                icon: '🧧'
            },
            {
                id: 'agent-002',
                name: '寺庙综合咨询 Agent',
                type: 'multi',
                typeLabel: '多 Agent 编排',
                desc: '智能路由分发到多个子Agent的综合咨询服务',
                status: 'published',
                // 编排 Agent（大 Agent）配置
                orchestrator: {
                    model: '通义千问 Plus',
                    systemPrompt: '你是一个智能编排助手。根据用户输入，将请求路由到合适的子 Agent，并在多子 Agent 场景下归纳汇总各子 Agent 的回复生成最终回复。',
                    maxTokens: 2048,
                    temperature: 0.7
                },
                // 智能路由配置
                routing: {
                    strategy: '智能路由',
                    model: 'qwen-turbo',
                    threshold: 0.8,
                    // 路由系统提示词
                    systemPrompt: '你是一个智能路由助手。分析用户输入，决定应该调用哪些子 Agent。输出 JSON 格式：{\n  "selectedAgents": ["agent-id-1", "agent-id-2"],\n  "confidence": 0.95,\n  "reason": "选择理由",\n  "singleAgent": false\n}',
                    // 候选子 Agent 池（用于路由选择）
                    candidatePool: ['sub-1', 'sub-2', 'sub-3'],
                    // 意图规则（意图路由模式下使用）
                    intentRules: [
                        { id: 'rule-1', intent: '财运咨询', keywords: ['财', '钱', '投资', '股票'], targetAgents: ['sub-1'], priority: 1 },
                        { id: 'rule-2', intent: '解梦咨询', keywords: ['梦', '梦见', '解梦'], targetAgents: ['sub-2'], priority: 1 },
                        { id: 'rule-3', intent: '节气查询', keywords: ['节气', '农历', '节日'], targetAgents: ['sub-3'], priority: 1 }
                    ]
                },
                // 子 Agent 列表 - 完整配置（与单 Agent 同一套模型）
                subAgents: [
                    {
                        id: 'sub-1',
                        name: '财神子Agent',
                        enabled: true,
                        desc: '处理财运、投资、祈福等相关咨询',
                        model: 'AI财神专业模型',
                        systemPrompt: '你是财神助手，专门处理用户的财运、投资、祈福等相关咨询。请用吉祥、专业的语气回复。',
                        temperature: 0.7,
                        maxTokens: 1024,
                        tools: [
                            { id: 'tool-1', name: '实时黄金价格抓取', enabled: true },
                            { id: 'tool-2', name: '股票行情查询', enabled: true }
                        ],
                        skills: [
                            { id: 'skill-1', name: '财神对话技能', enabled: true },
                            { id: 'skill-2', name: '祈福话术生成', enabled: true }
                        ],
                        hooks: { pre: [], post: [] }
                    },
                    {
                        id: 'sub-2',
                        name: '解梦子Agent',
                        enabled: true,
                        desc: '周公解梦、梦境解析相关咨询',
                        model: 'qwen-turbo',
                        systemPrompt: '你是解梦专家，精通周公解梦。请根据用户的梦境描述，给出传统解梦解释和心理分析。',
                        temperature: 0.8,
                        maxTokens: 1024,
                        tools: [{ id: 'tool-6', name: '周公解梦', enabled: true }],
                        skills: [],
                        hooks: { pre: [], post: [] }
                    },
                    {
                        id: 'sub-3',
                        name: '节气子Agent',
                        enabled: false,
                        desc: '农历节气、传统节日查询',
                        model: 'qwen-turbo',
                        systemPrompt: '你是节气助手，熟悉农历二十四节气、传统节日。请为用户提供节气知识和节日习俗介绍。',
                        temperature: 0.6,
                        maxTokens: 512,
                        tools: [{ id: 'tool-3', name: '农历节气查询', enabled: true }],
                        skills: [],
                        hooks: { pre: [], post: [] }
                    }
                ],
                hooks: {
                    pre: [{ id: 'hook-3', name: '意图识别', enabled: true, desc: '识别用户意图进行路由' }],
                    post: [{ id: 'hook-4', name: '结果汇总', enabled: true, desc: '汇总各子Agent结果' }]
                },
                apiEndpoint: '/api/v1/agent/schedule',
                updatedAt: '2024-01-14',
                icon: '🏮'
            },
            {
                id: 'agent-003',
                name: '反诈安全 Agent',
                type: 'single',
                typeLabel: '单 Agent',
                desc: '识别诈骗话术，提供安全预警服务',
                status: 'draft',
                model: 'DeepSeek Chat',
                intentRecognition: {
                    enabled: false,
                    model: 'qwen-turbo',
                    shortcutThreshold: 0.8,
                    systemPrompt: '你是一个意图识别助手。请分析用户输入，识别是否存在诈骗风险意图。',
                    entitySchema: [
                        { name: '风险等级', type: 'string', required: false, desc: 'high/medium/low' }
                    ]
                },
                tools: [{ id: 'tool-3', name: '风险知识库查询', enabled: true, desc: '查询风险案例库' }],
                skills: [{ id: 'skill-3', name: '反诈识别技能', enabled: true, desc: '识别诈骗话术模式' }],
                hooks: { pre: [], post: [] },
                apiEndpoint: '/api/v1/agent/schedule',
                updatedAt: '2024-01-13',
                icon: '🛡️'
            },
            {
                id: 'agent-004',
                name: '生活助手 Agent',
                type: 'multi',
                typeLabel: '多 Agent 编排',
                desc: '天气、农历、日常咨询的生活服务编排',
                status: 'published',
                orchestrator: {
                    model: 'qwen-turbo',
                    systemPrompt: '你是一个生活助手编排器。根据用户咨询内容，路由到天气或农历子 Agent。',
                    maxTokens: 1024,
                    temperature: 0.5
                },
                routing: {
                    strategy: '意图路由',
                    model: 'qwen-turbo',
                    threshold: 0.75,
                    systemPrompt: '分析用户意图，选择天气或农历子 Agent。',
                    candidatePool: ['sub-4', 'sub-5'],
                    intentRules: [
                        { id: 'rule-4', intent: '天气查询', keywords: ['天气', '温度', '下雨', '晴'], targetAgents: ['sub-4'], priority: 1 },
                        { id: 'rule-5', intent: '农历查询', keywords: ['农历', '节气', '节日', '黄历'], targetAgents: ['sub-5'], priority: 1 }
                    ]
                },
                subAgents: [
                    {
                        id: 'sub-4',
                        name: '天气子Agent',
                        enabled: true,
                        desc: '天气查询服务',
                        model: 'qwen-turbo',
                        systemPrompt: '你是天气助手，提供实时天气查询服务。请简洁明了地回复天气信息。',
                        temperature: 0.5,
                        maxTokens: 512,
                        tools: [{ id: 'tool-4', name: '天气查询服务', enabled: true }],
                        skills: [],
                        hooks: { pre: [], post: [] }
                    },
                    {
                        id: 'sub-5',
                        name: '农历子Agent',
                        enabled: true,
                        desc: '农历节气查询',
                        model: 'qwen-turbo',
                        systemPrompt: '你是农历助手，提供农历日期、节气、传统节日查询服务。',
                        temperature: 0.5,
                        maxTokens: 512,
                        tools: [{ id: 'tool-3', name: '农历节气查询', enabled: true }],
                        skills: [],
                        hooks: { pre: [], post: [] }
                    }
                ],
                hooks: { pre: [], post: [] },
                apiEndpoint: '/api/v1/agent/schedule',
                updatedAt: '2024-01-12',
                icon: '🌤️'
            }
        ]);

        // 可用的 Tools、Skills、Hooks 库
        const availableTools = ref([
            { id: 't1', name: '实时黄金价格抓取', desc: '获取实时黄金价格数据，支持多币种转换', category: '金融' },
            { id: 't2', name: '股票行情查询', desc: 'A股、港股、美股实时行情数据', category: '金融' },
            { id: 't3', name: '农历节气查询', desc: '查询农历日期、二十四节气', category: '生活' },
            { id: 't4', name: '天气查询服务', desc: '实时天气查询，支持全球城市', category: '生活' },
            { id: 't5', name: '风险知识库查询', desc: '查询诈骗风险案例库', category: '安全' },
            { id: 't6', name: '周公解梦', desc: '传统解梦知识库查询', category: '文化' }
        ]);

        const availableSkills = ref([
            { id: 's1', name: '财神对话技能', desc: '财神角色对话技能包', category: '角色' },
            { id: 's2', name: '祈福话术生成', desc: '根据场景生成祈福话术', category: '场景' },
            { id: 's3', name: '反诈识别技能', desc: '识别诈骗话术模式', category: '安全' },
            { id: 's4', name: '多轮对话管理', desc: '管理多轮对话上下文', category: '基础' },
            { id: 's5', name: '意图识别增强', desc: '增强意图识别准确率', category: '基础' }
        ]);

        const availableHooks = ref([
            { id: 'h1', name: '安全检测', desc: '检测输入是否包含敏感内容', type: 'pre' },
            { id: 'h2', name: '内容审核', desc: '审核输出内容合规性', type: 'post' },
            { id: 'h3', name: '意图识别', desc: '识别用户意图进行路由', type: 'pre' },
            { id: 'h4', name: '结果汇总', desc: '汇总多Agent结果生成回复', type: 'post' },
            { id: 'h5', name: '参数校验', desc: '校验输入参数合法性', type: 'pre' },
            { id: 'h6', name: '格式标准化', desc: '标准化输出格式', type: 'post' }
        ]);

        const availableModels = ref([
            { id: 'm1', name: 'AI财神专业模型', desc: '针对财神场景优化的模型' },
            { id: 'm2', name: '通义千问 Plus', desc: '阿里云大模型增强版' },
            { id: 'm3', name: 'DeepSeek Chat', desc: 'DeepSeek对话模型' },
            { id: 'm4', name: 'qwen-turbo', desc: '通义千问轻量版' },
            { id: 'm5', name: 'gpt-4', desc: 'OpenAI GPT-4' }
        ]);

        const filterType = ref('全部');
        const filterStatus = ref('全部');
        const searchQuery = ref('');
        const showAddModal = ref(false);
        const showDetailModal = ref(false);
        const showConfigModal = ref(false);
        const selectedAgent = ref(null);
        const activeConfigTab = ref('basic');

        // 子配置弹窗状态
        const showToolModal = ref(false);
        const showSkillModal = ref(false);
        const showSubAgentModal = ref(false);
        const showHookModal = ref(false);
        const hookModalType = ref('pre');
        const editingSubAgent = ref(null);
        const editingHook = ref(null);
        const expandedSubAgents = ref({});

        const agentTypes = ['全部', '单 Agent', '多 Agent 编排'];
        const statuses = ['全部', '已发布', '草稿'];

        const filteredAgents = computed(() => {
            return agents.value.filter(agent => {
                const matchType = filterType.value === '全部' || agent.typeLabel === filterType.value;
                const matchStatus = filterStatus.value === '全部' ||
                    (filterStatus.value === '已发布' && agent.status === 'published') ||
                    (filterStatus.value === '草稿' && agent.status === 'draft');
                const matchSearch = !searchQuery.value ||
                    agent.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                    agent.desc.toLowerCase().includes(searchQuery.value.toLowerCase());
                return matchType && matchStatus && matchSearch;
            });
        });

        const viewAgentDetail = (agent) => {
            selectedAgent.value = agent;
            showDetailModal.value = true;
        };

        const configAgent = (agent) => {
            selectedAgent.value = agent;
            activeConfigTab.value = 'basic';
            showConfigModal.value = true;
        };

        const deleteAgent = (id) => {
            if (confirm('确定要删除这个 Agent 吗？')) {
                agents.value = agents.value.filter(a => a.id !== id);
            }
        };

        const toggleStatus = (agent) => {
            agent.status = agent.status === 'published' ? 'draft' : 'published';
        };

        const copyEndpoint = (endpoint) => {
            navigator.clipboard.writeText(endpoint);
            alert('API 端点已复制到剪贴板');
        };

        // ========== 意图识别 & 实体提取管理 ==========
        const addEntityField = () => {
            if (!selectedAgent.value.intentRecognition.entitySchema) {
                selectedAgent.value.intentRecognition.entitySchema = [];
            }
            selectedAgent.value.intentRecognition.entitySchema.push({
                name: '',
                type: 'string',
                required: false,
                desc: ''
            });
        };

        const removeEntityField = (index) => {
            selectedAgent.value.intentRecognition.entitySchema.splice(index, 1);
        };

        // ========== 意图规则管理 ==========
        const addIntentRule = () => {
            if (!selectedAgent.value.routing.intentRules) {
                selectedAgent.value.routing.intentRules = [];
            }
            selectedAgent.value.routing.intentRules.push({
                id: 'rule-' + Date.now(),
                intent: '',
                keywords: '',
                targetAgents: [],
                priority: 1
            });
        };

        const removeIntentRule = (index) => {
            selectedAgent.value.routing.intentRules.splice(index, 1);
        };

        // ========== Tools 管理 ==========
        const openToolModal = () => {
            showToolModal.value = true;
        };

        const addTool = (tool) => {
            if (!selectedAgent.value.tools.find(t => t.id === tool.id)) {
                selectedAgent.value.tools.push({
                    id: tool.id,
                    name: tool.name,
                    desc: tool.desc,
                    enabled: true
                });
            }
        };

        const removeTool = (toolId) => {
            selectedAgent.value.tools = selectedAgent.value.tools.filter(t => t.id !== toolId);
        };

        const toggleTool = (tool) => {
            tool.enabled = !tool.enabled;
        };

        // ========== Skills 管理 ==========
        const openSkillModal = () => {
            showSkillModal.value = true;
        };

        const addSkill = (skill) => {
            if (!selectedAgent.value.skills.find(s => s.id === skill.id)) {
                selectedAgent.value.skills.push({
                    id: skill.id,
                    name: skill.name,
                    desc: skill.desc,
                    enabled: true
                });
            }
        };

        const removeSkill = (skillId) => {
            selectedAgent.value.skills = selectedAgent.value.skills.filter(s => s.id !== skillId);
        };

        const toggleSkill = (skill) => {
            skill.enabled = !skill.enabled;
        };

        // ========== 子 Agent 管理 ==========
        const openSubAgentModal = () => {
            editingSubAgent.value = null;
            showSubAgentModal.value = true;
        };

        const editSubAgent = (subAgent) => {
            editingSubAgent.value = { ...subAgent };
            showSubAgentModal.value = true;
        };

        const saveSubAgent = (subAgentData) => {
            if (editingSubAgent.value) {
                // 编辑模式
                const index = selectedAgent.value.subAgents.findIndex(s => s.id === editingSubAgent.value.id);
                if (index !== -1) {
                    selectedAgent.value.subAgents[index] = { ...subAgentData, id: editingSubAgent.value.id };
                }
            } else {
                // 新增模式
                selectedAgent.value.subAgents.push({
                    ...subAgentData,
                    id: 'sub-' + Date.now(),
                    enabled: true
                });
            }
            showSubAgentModal.value = false;
            editingSubAgent.value = null;
        };

        const removeSubAgent = (subAgentId) => {
            if (confirm('确定要移除这个子 Agent 吗？')) {
                selectedAgent.value.subAgents = selectedAgent.value.subAgents.filter(s => s.id !== subAgentId);
            }
        };

        const toggleSubAgent = (subAgent) => {
            subAgent.enabled = !subAgent.enabled;
        };

        const toggleSubAgentExpand = (subAgent) => {
            expandedSubAgents.value[subAgent.id] = !expandedSubAgents.value[subAgent.id];
        };

        // ========== Hooks 管理 ==========
        const openHookModal = (type) => {
            hookModalType.value = type;
            editingHook.value = null;
            showHookModal.value = true;
        };

        const editHook = (hook, type) => {
            hookModalType.value = type;
            editingHook.value = { ...hook, type };
            showHookModal.value = true;
        };

        const addHook = (hook) => {
            const type = hookModalType.value;
            if (!selectedAgent.value.hooks[type].find(h => h.id === hook.id)) {
                selectedAgent.value.hooks[type].push({
                    id: hook.id,
                    name: hook.name,
                    desc: hook.desc,
                    enabled: true
                });
            }
            showHookModal.value = false;
        };

        const removeHook = (hookId, type) => {
            selectedAgent.value.hooks[type] = selectedAgent.value.hooks[type].filter(h => h.id !== hookId);
        };

        const toggleHook = (hook) => {
            hook.enabled = !hook.enabled;
        };

        return {
            agents, filterType, filterStatus, searchQuery,
            agentTypes, statuses, filteredAgents,
            showAddModal, showDetailModal, showConfigModal,
            selectedAgent, activeConfigTab,
            availableTools, availableSkills, availableHooks, availableModels,
            showToolModal, showSkillModal, showSubAgentModal, showHookModal,
            hookModalType, editingSubAgent, editingHook, expandedSubAgents,
            viewAgentDetail, configAgent, deleteAgent, toggleStatus, copyEndpoint,
            addEntityField, removeEntityField,
            addIntentRule, removeIntentRule,
            openToolModal, addTool, removeTool, toggleTool,
            openSkillModal, addSkill, removeSkill, toggleSkill,
            openSubAgentModal, editSubAgent, saveSubAgent, removeSubAgent, toggleSubAgent, toggleSubAgentExpand,
            openHookModal, editHook, addHook, removeHook, toggleHook
        };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">Agent 工作流</h1>
                <p class="page-desc">管理对外提供服务的 Agent 工作流，支持单 Agent 和多 Agent 编排模式</p>
            </div>

            <div class="filters-bar">
                <select class="filter-select" v-model="filterType">
                    <option v-for="type in agentTypes" :key="type" :value="type">{{ type }}</option>
                </select>
                <select class="filter-select" v-model="filterStatus">
                    <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
                </select>
                <input type="text" class="filter-input" v-model="searchQuery" placeholder="搜索 Agent 名称或描述...">
                <button class="btn btn-primary" @click="showAddModal = true">+ 新建 Agent</button>
            </div>

            <div class="agent-grid">
                <div class="agent-card" v-for="agent in filteredAgents" :key="agent.id">
                    <div class="agent-card-header">
                        <div class="agent-icon">{{ agent.icon }}</div>
                        <div class="agent-info">
                            <div class="agent-name">{{ agent.name }}</div>
                            <div class="agent-meta">
                                <span class="agent-type" :class="agent.type">{{ agent.typeLabel }}</span>
                                <span class="agent-status" :class="agent.status">
                                    {{ agent.status === 'published' ? '已发布' : '草稿' }}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="agent-desc">{{ agent.desc }}</div>
                    <div class="agent-config">
                        <div class="config-item">
                            <span class="config-label">模型</span>
                            <span class="config-value">{{ agent.model }}</span>
                        </div>
                        <div class="config-item" v-if="agent.type === 'single'">
                            <span class="config-label">Tools</span>
                            <span class="config-value">{{ agent.tools?.length || 0 }} 个</span>
                        </div>
                        <div class="config-item" v-if="agent.type === 'single'">
                            <span class="config-label">Skills</span>
                            <span class="config-value">{{ agent.skills?.length || 0 }} 个</span>
                        </div>
                        <div class="config-item" v-if="agent.type === 'multi'">
                            <span class="config-label">子 Agent</span>
                            <span class="config-value">{{ agent.subAgents?.length || 0 }} 个</span>
                        </div>
                        <div class="config-item" v-if="agent.type === 'multi'">
                            <span class="config-label">路由策略</span>
                            <span class="config-value">{{ agent.routingStrategy }}</span>
                        </div>
                    </div>
                    <div class="agent-endpoint">
                        <code class="endpoint-code">{{ agent.apiEndpoint }}</code>
                        <button class="btn btn-sm btn-secondary" @click="copyEndpoint(agent.apiEndpoint)">复制</button>
                    </div>
                    <div class="agent-actions">
                        <button class="btn btn-sm btn-secondary" @click="viewAgentDetail(agent)">详情</button>
                        <button class="btn btn-sm btn-primary" @click="configAgent(agent)">配置</button>
                        <button class="btn btn-sm" :class="agent.status === 'published' ? 'btn-secondary' : 'btn-primary'" @click="toggleStatus(agent)">
                            {{ agent.status === 'published' ? '下架' : '发布' }}
                        </button>
                        <button class="btn btn-sm btn-secondary" @click="deleteAgent(agent.id)">删除</button>
                    </div>
                </div>
            </div>

            <!-- 新建 Agent Modal -->
            <div class="modal-overlay" v-if="showAddModal" @click.self="showAddModal = false">
                <div class="modal" style="max-width: 720px;">
                    <div class="modal-header">
                        <span class="modal-title">新建 Agent 工作流</span>
                        <button class="modal-close" @click="showAddModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 20px;">
                            <label class="form-label">Agent 类型</label>
                            <div class="agent-type-selector">
                                <div class="type-option">
                                    <input type="radio" name="agentType" value="single" id="type-single" checked>
                                    <label for="type-single">
                                        <div class="type-icon">🤖</div>
                                        <div class="type-name">单 Agent</div>
                                        <div class="type-desc">单一 Agent 处理所有请求，适合简单场景</div>
                                    </label>
                                </div>
                                <div class="type-option">
                                    <input type="radio" name="agentType" value="multi" id="type-multi">
                                    <label for="type-multi">
                                        <div class="type-icon">🎭</div>
                                        <div class="type-name">多 Agent 编排</div>
                                        <div class="type-desc">智能路由分发到多个子 Agent，适合复杂场景</div>
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">Agent 名称</label>
                            <input type="text" class="form-input" placeholder="如: 财神助手 Agent">
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">功能描述</label>
                            <textarea class="form-textarea" rows="3" placeholder="描述 Agent 的主要功能和应用场景..."></textarea>
                        </div>
                        <div class="form-row" style="margin-bottom: 16px;">
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label">选择模型</label>
                                <select class="form-input">
                                    <option>AI财神专业模型</option>
                                    <option>通义千问 Plus</option>
                                    <option>DeepSeek Chat</option>
                                    <option>qwen-turbo</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label">图标</label>
                                <select class="form-input">
                                    <option>🧧</option>
                                    <option>🏮</option>
                                    <option>🛡️</option>
                                    <option>🌤️</option>
                                    <option>🤖</option>
                                    <option>🎭</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showAddModal = false">取消</button>
                        <button class="btn btn-primary" @click="showAddModal = false">创建并配置</button>
                    </div>
                </div>
            </div>

            <!-- Agent 详情 Modal -->
            <div class="modal-overlay" v-if="showDetailModal" @click.self="showDetailModal = false">
                <div class="modal" style="max-width: 640px;" v-if="selectedAgent">
                    <div class="modal-header">
                        <span class="modal-title">Agent 详情</span>
                        <button class="modal-close" @click="showDetailModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
                            <span style="font-size: 48px;">{{ selectedAgent.icon }}</span>
                            <div>
                                <div style="font-size: 20px; font-weight: 600;">{{ selectedAgent.name }}</div>
                                <div style="display: flex; gap: 8px; margin-top: 4px;">
                                    <span class="tag" :class="selectedAgent.type === 'single' ? 'tag-primary' : 'tag-success'">{{ selectedAgent.typeLabel }}</span>
                                    <span class="tag" :class="selectedAgent.status === 'published' ? 'tag-success' : 'tag-info'">{{ selectedAgent.status === 'published' ? '已发布' : '草稿' }}</span>
                                </div>
                            </div>
                        </div>
                        <div class="card" style="background: var(--bg-secondary); margin-bottom: 16px;">
                            <div class="card-body">
                                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">功能描述</div>
                                <div>{{ selectedAgent.desc }}</div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px;">
                            <div class="info-item">
                                <div class="info-label">模型</div>
                                <div class="info-value">{{ selectedAgent.model }}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">更新时间</div>
                                <div class="info-value">{{ selectedAgent.updatedAt }}</div>
                            </div>
                            <div class="info-item" v-if="selectedAgent.type === 'single'">
                                <div class="info-label">Tools</div>
                                <div class="info-value">{{ selectedAgent.tools?.length || 0 }} 个</div>
                            </div>
                            <div class="info-item" v-if="selectedAgent.type === 'single'">
                                <div class="info-label">Skills</div>
                                <div class="info-value">{{ selectedAgent.skills?.length || 0 }} 个</div>
                            </div>
                            <div class="info-item" v-if="selectedAgent.type === 'multi'">
                                <div class="info-label">子 Agent</div>
                                <div class="info-value">{{ selectedAgent.subAgents?.length || 0 }} 个</div>
                            </div>
                            <div class="info-item" v-if="selectedAgent.type === 'multi'">
                                <div class="info-label">路由策略</div>
                                <div class="info-value">{{ selectedAgent.routingStrategy }}</div>
                            </div>
                        </div>
                        <div class="card" style="background: var(--bg-secondary);">
                            <div class="card-header">
                                <span class="card-title">API 端点</span>
                            </div>
                            <div class="card-body">
                                <code style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px; display: block; font-size: 13px;">
                                    POST {{ selectedAgent.apiEndpoint }}<br>
                                    Content-Type: application/json<br><br>
                                    {<br>
                                    &nbsp;&nbsp;"agent_id": "{{ selectedAgent.id }}",<br>
                                    &nbsp;&nbsp;"query": "用户输入",<br>
                                    &nbsp;&nbsp;"stream": false<br>
                                    }
                                </code>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showDetailModal = false">关闭</button>
                        <button class="btn btn-primary" @click="showDetailModal = false; configAgent(selectedAgent)">编辑配置</button>
                    </div>
                </div>
            </div>

            <!-- Agent 配置 Modal -->
            <div class="modal-overlay" v-if="showConfigModal" @click.self="showConfigModal = false">
                <div class="modal" style="max-width: 900px; height: 80vh; display: flex; flex-direction: column;" v-if="selectedAgent">
                    <div class="modal-header">
                        <span class="modal-title">配置 Agent: {{ selectedAgent.name }}</span>
                        <button class="modal-close" @click="showConfigModal = false">×</button>
                    </div>
                    <div class="agent-tabs" style="padding: 0 24px; border-bottom: 1px solid var(--border); margin: 0;">
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'basic' }" @click="activeConfigTab = 'basic'">基础配置</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'model' }" @click="activeConfigTab = 'model'">模型参数</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'intent' }" @click="activeConfigTab = 'intent'" v-if="selectedAgent.type === 'single'">🎯 意图识别</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'tools' }" @click="activeConfigTab = 'tools'" v-if="selectedAgent.type === 'single'">Tools ({{ selectedAgent.tools?.length || 0 }})</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'skills' }" @click="activeConfigTab = 'skills'" v-if="selectedAgent.type === 'single'">Skills ({{ selectedAgent.skills?.length || 0 }})</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'orchestrator' }" @click="activeConfigTab = 'orchestrator'" v-if="selectedAgent.type === 'multi'">🎭 编排器</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'routing' }" @click="activeConfigTab = 'routing'" v-if="selectedAgent.type === 'multi'">🚦 智能路由</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'subagents' }" @click="activeConfigTab = 'subagents'" v-if="selectedAgent.type === 'multi'">子 Agent ({{ selectedAgent.subAgents?.length || 0 }})</button>
                        <button class="agent-tab" :class="{ active: activeConfigTab === 'hooks' }" @click="activeConfigTab = 'hooks'">前置/后置检测</button>
                    </div>
                    <div class="modal-body" style="flex: 1; overflow-y: auto;">
                        <!-- 基础配置 -->
                        <div v-if="activeConfigTab === 'basic'">
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">Agent 名称</label>
                                <input type="text" class="form-input" v-model="selectedAgent.name">
                            </div>
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">功能描述</label>
                                <textarea class="form-textarea" rows="3" v-model="selectedAgent.desc"></textarea>
                            </div>
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">系统 Prompt (System Prompt)</label>
                                <textarea class="form-textarea" rows="6" placeholder="定义 Agent 的角色、风格和边界..."></textarea>
                            </div>
                            <div class="form-group">
                                <label class="form-label">欢迎语</label>
                                <textarea class="form-textarea" rows="2" placeholder="用户首次进入时的欢迎语..."></textarea>
                            </div>
                        </div>

                        <!-- 模型参数 -->
                        <div v-if="activeConfigTab === 'model'">
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">选择模型</label>
                                <select class="form-input" v-model="selectedAgent.model">
                                    <option v-for="model in availableModels" :key="model.id" :value="model.name">{{ model.name }}</option>
                                </select>
                            </div>
                            <div class="slider-container" style="margin-bottom: 20px;">
                                <div class="slider-header">
                                    <span class="slider-label">多样性 (Temperature)</span>
                                    <span class="slider-value">0.7</span>
                                </div>
                                <input type="range" class="slider" min="0" max="1" step="0.05" value="0.7">
                            </div>
                            <div class="slider-container" style="margin-bottom: 20px;">
                                <div class="slider-header">
                                    <span class="slider-label">核采样 (Top-P)</span>
                                    <span class="slider-value">0.9</span>
                                </div>
                                <input type="range" class="slider" min="0" max="1" step="0.05" value="0.9">
                            </div>
                            <div class="slider-container" style="margin-bottom: 20px;">
                                <div class="slider-header">
                                    <span class="slider-label">最大输出 Tokens</span>
                                    <span class="slider-value">2048</span>
                                </div>
                                <input type="range" class="slider" min="256" max="8192" step="256" value="2048">
                            </div>
                            <div class="form-group" style="margin: 16px 0;">
                                <div style="display: flex; align-items: center; justify-content: space-between;">
                                    <span class="form-label" style="margin: 0;">启用流式输出 (SSE)</span>
                                    <div class="toggle active"></div>
                                </div>
                            </div>
                        </div>

                        <!-- 意图识别 & 实体提取配置 (单 Agent) -->
                        <div v-if="activeConfigTab === 'intent'">
                            <div class="card" style="background: var(--primary-light); border: 1px solid var(--primary); margin-bottom: 20px;">
                                <div class="card-body">
                                    <div style="display: flex; align-items: center; justify-content: space-between;">
                                        <div>
                                            <div style="font-weight: 600; color: var(--primary); margin-bottom: 4px;">🎯 意图识别短路优化</div>
                                            <div style="font-size: 13px; color: var(--text-secondary);">启用后，当意图识别置信度高且参数完整时，可直接调用 Tool 跳过完整 Plan 调度，降低延迟</div>
                                        </div>
                                        <div class="toggle" :class="{ active: selectedAgent.intentRecognition?.enabled }" @click="selectedAgent.intentRecognition.enabled = !selectedAgent.intentRecognition.enabled"></div>
                                    </div>
                                </div>
                            </div>

                            <template v-if="selectedAgent.intentRecognition?.enabled">
                                <div class="form-row" style="margin-bottom: 16px;">
                                    <div class="form-group" style="flex: 1;">
                                        <label class="form-label">意图识别模型</label>
                                        <select class="form-input" v-model="selectedAgent.intentRecognition.model">
                                            <option v-for="model in availableModels" :key="model.id" :value="model.name">{{ model.name }}</option>
                                        </select>
                                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">可选择轻量模型专门做意图识别，降低成本</div>
                                    </div>
                                    <div class="form-group" style="flex: 1;">
                                        <label class="form-label">短路阈值</label>
                                        <div class="slider-container" style="margin: 0;">
                                            <div class="slider-header">
                                                <span class="slider-label">置信度 ≥ {{ selectedAgent.intentRecognition.shortcutThreshold }} 且参数完整时直接执行</span>
                                                <span class="slider-value">{{ selectedAgent.intentRecognition.shortcutThreshold }}</span>
                                            </div>
                                            <input type="range" class="slider" min="0.5" max="0.99" step="0.01" v-model="selectedAgent.intentRecognition.shortcutThreshold">
                                        </div>
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label class="form-label">系统提示词 (System Prompt)</label>
                                    <textarea class="form-textarea" rows="8" v-model="selectedAgent.intentRecognition.systemPrompt" placeholder="定义意图识别的角色、输出格式和实体提取要求..."></textarea>
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">提示词中应说明输出 JSON 格式，包含 intent、confidence、entities、directTool 字段</div>
                                </div>

                                <div class="card" style="margin-bottom: 16px;">
                                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                        <span class="card-title">实体 Schema 定义 ({{ selectedAgent.intentRecognition.entitySchema?.length || 0 }})</span>
                                        <button class="btn btn-sm btn-primary" @click="addEntityField">+ 添加字段</button>
                                    </div>
                                    <div class="card-body">
                                        <div v-if="selectedAgent.intentRecognition.entitySchema?.length === 0" style="text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px;">
                                            暂无实体字段定义，点击上方按钮添加
                                        </div>
                                        <div v-else class="entity-schema-list">
                                            <div v-for="(field, index) in selectedAgent.intentRecognition.entitySchema" :key="index" class="entity-field-item">
                                                <div style="display: grid; grid-template-columns: 1.5fr 1fr 0.8fr 2fr 0.5fr; gap: 12px; align-items: center;">
                                                    <input type="text" class="form-input" v-model="field.name" placeholder="字段名">
                                                    <select class="form-input" v-model="field.type">
                                                        <option value="string">字符串</option>
                                                        <option value="number">数字</option>
                                                        <option value="boolean">布尔</option>
                                                        <option value="array">数组</option>
                                                        <option value="object">对象</option>
                                                    </select>
                                                    <div style="display: flex; align-items: center; gap: 6px;">
                                                        <input type="checkbox" :id="'required-' + index" v-model="field.required">
                                                        <label :for="'required-' + index" style="font-size: 12px; cursor: pointer;">必填</label>
                                                    </div>
                                                    <input type="text" class="form-input" v-model="field.desc" placeholder="字段描述">
                                                    <button class="btn btn-sm btn-secondary" @click="removeEntityField(index)">删除</button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="card" style="background: var(--bg-secondary);">
                                    <div class="card-header">
                                        <span class="card-title">输出示例</span>
                                    </div>
                                    <div class="card-body">
                                        <pre style="margin: 0; font-size: 12px; overflow-x: auto;"><code>{\n  "intent": "查询黄金价格",\n  "confidence": 0.95,\n  "entities": {\n    <template v-for="(field, idx) in selectedAgent.intentRecognition.entitySchema" :key="idx">"{{ field.name }}": <span v-if="field.type === 'string'">""</span><span v-else-if="field.type === 'number'">0</span><span v-else-if="field.type === 'boolean'">false</span><span v-else>[]</span><span v-if="idx < selectedAgent.intentRecognition.entitySchema.length - 1">,\n    </span></template>\n  },\n  "directTool": "实时黄金价格抓取"\n}</code></pre>
                                    </div>
                                </div>
                            </template>

                            <div v-else style="text-align: center; padding: 60px 40px; color: var(--text-secondary);">
                                <div style="font-size: 64px; margin-bottom: 20px;">🎯</div>
                                <div style="font-size: 16px; font-weight: 500; margin-bottom: 8px;">意图识别未启用</div>
                                <div style="font-size: 13px;">开启后可配置意图识别模型、短路阈值和实体提取规则</div>
                            </div>
                        </div>

                        <!-- Tools 配置 (单 Agent) -->
                        <div v-if="activeConfigTab === 'tools'">
                            <div style="margin-bottom: 16px;">
                                <button class="btn btn-primary btn-sm" @click="openToolModal">+ 添加 Tool</button>
                            </div>
                            <div class="tool-list">
                                <div class="tool-item" v-for="tool in selectedAgent.tools" :key="tool.id">
                                    <div class="tool-info">
                                        <div class="tool-icon">🔧</div>
                                        <div class="tool-details">
                                            <div class="tool-name">{{ tool.name }}</div>
                                            <div class="tool-desc">{{ tool.desc }}</div>
                                        </div>
                                    </div>
                                    <div class="tool-actions">
                                        <div class="toggle" :class="{ active: tool.enabled }" @click="toggleTool(tool)"></div>
                                        <button class="btn btn-sm btn-secondary" @click="removeTool(tool.id)">移除</button>
                                    </div>
                                </div>
                            </div>
                            <div v-if="selectedAgent.tools.length === 0" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                <div style="font-size: 48px; margin-bottom: 16px;">🔧</div>
                                <div>暂无 Tools，点击上方按钮添加</div>
                            </div>
                        </div>

                        <!-- Skills 配置 (单 Agent) -->
                        <div v-if="activeConfigTab === 'skills'">
                            <div style="margin-bottom: 16px;">
                                <button class="btn btn-primary btn-sm" @click="openSkillModal">+ 添加 Skill</button>
                            </div>
                            <div class="tool-list">
                                <div class="tool-item" v-for="skill in selectedAgent.skills" :key="skill.id">
                                    <div class="tool-info">
                                        <div class="tool-icon">⚡</div>
                                        <div class="tool-details">
                                            <div class="tool-name">{{ skill.name }}</div>
                                            <div class="tool-desc">{{ skill.desc }}</div>
                                        </div>
                                    </div>
                                    <div class="tool-actions">
                                        <div class="toggle" :class="{ active: skill.enabled }" @click="toggleSkill(skill)"></div>
                                        <button class="btn btn-sm btn-secondary" @click="removeSkill(skill.id)">移除</button>
                                    </div>
                                </div>
                            </div>
                            <div v-if="selectedAgent.skills.length === 0" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                <div style="font-size: 48px; margin-bottom: 16px;">⚡</div>
                                <div>暂无 Skills，点击上方按钮添加</div>
                            </div>
                        </div>

                        <!-- 编排器配置 (多 Agent) -->
                        <div v-if="activeConfigTab === 'orchestrator'">
                            <div class="card" style="background: var(--primary-light); border: 1px solid var(--primary); margin-bottom: 20px;">
                                <div class="card-body">
                                    <div style="font-weight: 600; color: var(--primary); margin-bottom: 8px;">🎭 编排 Agent（大 Agent）</div>
                                    <div style="font-size: 13px; color: var(--text-secondary);">多 Agent 模式下的统一编排实例，承载智能路由、分支决策、多子场景下的规划式调用与归纳回复</div>
                                </div>
                            </div>

                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">编排模型</label>
                                <select class="form-input" v-model="selectedAgent.orchestrator.model">
                                    <option v-for="model in availableModels" :key="model.id" :value="model.name">{{ model.name }}</option>
                                </select>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">用于多子 Agent 场景下的规划调度与结果归纳</div>
                            </div>

                            <div class="form-row" style="margin-bottom: 16px;">
                                <div class="form-group" style="flex: 1;">
                                    <label class="form-label">Temperature</label>
                                    <div class="slider-container" style="margin: 0;">
                                        <div class="slider-header">
                                            <span class="slider-value">{{ selectedAgent.orchestrator.temperature || 0.7 }}</span>
                                        </div>
                                        <input type="range" class="slider" min="0" max="1" step="0.05" v-model="selectedAgent.orchestrator.temperature">
                                    </div>
                                </div>
                                <div class="form-group" style="flex: 1;">
                                    <label class="form-label">Max Tokens</label>
                                    <input type="number" class="form-input" v-model="selectedAgent.orchestrator.maxTokens" placeholder="2048">
                                </div>
                            </div>

                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">系统提示词 (System Prompt)</label>
                                <textarea class="form-textarea" rows="6" v-model="selectedAgent.orchestrator.systemPrompt" placeholder="定义编排 Agent 的角色、调度策略和归纳回复风格..."></textarea>
                            </div>

                            <div class="card" style="background: var(--bg-secondary);">
                                <div class="card-header">
                                    <span class="card-title">编排流程说明</span>
                                </div>
                                <div class="card-body" style="font-size: 13px; color: var(--text-secondary);">
                                    <p><strong>单子 Agent 路径：</strong>智能路由识别为单一子 Agent 时，直接调用该子 Agent，不启动编排规划 LLM</p>
                                    <p><strong>多子 Agent 路径：</strong>编排 LLM 仅挂载路由命中的子 Agent，像调用工具一样调用各子 Agent，归纳汇总生成回复</p>
                                    <p><strong>后置检测：</strong>两种分支的输出均须经过后置检测后才返回给用户</p>
                                </div>
                            </div>
                        </div>

                        <!-- 路由配置 (多 Agent) -->
                        <div v-if="activeConfigTab === 'routing'">
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">路由策略</label>
                                <select class="form-input" v-model="selectedAgent.routing.strategy">
                                    <option>智能路由</option>
                                    <option>意图路由</option>
                                    <option>混合路由</option>
                                </select>
                            </div>

                            <div class="form-row" style="margin-bottom: 16px;">
                                <div class="form-group" style="flex: 1;">
                                    <label class="form-label">路由模型</label>
                                    <select class="form-input" v-model="selectedAgent.routing.model">
                                        <option v-for="model in availableModels" :key="model.id" :value="model.name">{{ model.name }}</option>
                                    </select>
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">可选择轻量模型降低路由成本</div>
                                </div>
                                <div class="form-group" style="flex: 1;">
                                    <label class="form-label">置信度阈值</label>
                                    <div class="slider-container" style="margin: 0;">
                                        <div class="slider-header">
                                            <span class="slider-label">低于此值视为低置信度</span>
                                            <span class="slider-value">{{ selectedAgent.routing.threshold || 0.8 }}</span>
                                        </div>
                                        <input type="range" class="slider" min="0.5" max="0.95" step="0.05" v-model="selectedAgent.routing.threshold">
                                    </div>
                                </div>
                            </div>

                            <div class="form-group" style="margin-bottom: 16px;">
                                <label class="form-label">路由系统提示词</label>
                                <textarea class="form-textarea" rows="6" v-model="selectedAgent.routing.systemPrompt" placeholder="定义路由助手的角色和输出格式要求..."></textarea>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">提示词中应说明输出 JSON 格式：selectedAgents, confidence, reason, singleAgent</div>
                            </div>

                            <div class="card" style="margin-bottom: 16px;">
                                <div class="card-header">
                                    <span class="card-title">候选子 Agent 池 ({{ selectedAgent.routing.candidatePool?.length || 0 }})</span>
                                </div>
                                <div class="card-body">
                                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                        <span v-for="subId in selectedAgent.routing.candidatePool" :key="subId" class="tag tag-primary">
                                            {{ selectedAgent.subAgents.find(s => s.id === subId)?.name || subId }}
                                        </span>
                                    </div>
                                    <div style="margin-top: 12px; font-size: 12px; color: var(--text-secondary);">
                                        路由将从此池中选择子 Agent，未在池中的子 Agent 不会被路由选中
                                    </div>
                                </div>
                            </div>

                            <div class="card" v-if="selectedAgent.routing.strategy === '意图路由' || selectedAgent.routing.strategy === '混合路由'">
                                <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                    <span class="card-title">意图规则 ({{ selectedAgent.routing.intentRules?.length || 0 }})</span>
                                    <button class="btn btn-sm btn-primary" @click="addIntentRule">+ 添加规则</button>
                                </div>
                                <div class="card-body">
                                    <div v-if="selectedAgent.routing.intentRules?.length === 0" style="text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px;">
                                        暂无意图规则，点击上方按钮添加
                                    </div>
                                    <div v-else class="intent-rules-list">
                                        <div v-for="(rule, index) in selectedAgent.routing.intentRules" :key="rule.id" class="intent-rule-item" style="padding: 12px; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 12px;">
                                            <div style="display: grid; grid-template-columns: 1fr 1fr 2fr 0.5fr; gap: 12px; align-items: center;">
                                                <input type="text" class="form-input" v-model="rule.intent" placeholder="意图名称">
                                                <input type="text" class="form-input" v-model="rule.keywords" placeholder="关键词（逗号分隔）">
                                                <div>
                                                    <select class="form-input" v-model="rule.targetAgents" multiple style="height: 60px;">
                                                        <option v-for="sub in selectedAgent.subAgents" :key="sub.id" :value="sub.id">{{ sub.name }}</option>
                                                    </select>
                                                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">按住 Ctrl 多选</div>
                                                </div>
                                                <button class="btn btn-sm btn-secondary" @click="removeIntentRule(index)">删除</button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="card" style="background: var(--bg-secondary); margin-top: 16px;">
                                <div class="card-header">
                                    <span class="card-title">路由输出示例</span>
                                </div>
                                <div class="card-body">
                                    <pre style="margin: 0; font-size: 12px; overflow-x: auto;"><code>{\n  "selectedAgents": ["sub-1", "sub-2"],\n  "confidence": 0.95,\n  "reason": "用户询问财运和投资，需要财神子Agent和理财子Agent共同回答",\n  "singleAgent": false\n}</code></pre>
                                </div>
                            </div>
                        </div>

                        <!-- 子 Agent 配置 (多 Agent) -->
                        <div v-if="activeConfigTab === 'subagents'">
                            <div style="margin-bottom: 16px;">
                                <button class="btn btn-primary btn-sm" @click="openSubAgentModal">+ 添加子 Agent</button>
                            </div>

                            <div class="subagent-list">
                                <div v-for="subAgent in selectedAgent.subAgents" :key="subAgent.id" class="subagent-card" :class="{ disabled: !subAgent.enabled }">
                                    <div class="subagent-header">
                                        <div class="subagent-info">
                                            <div class="tool-icon">🤖</div>
                                            <div>
                                                <div style="font-weight: 600; font-size: 15px;">{{ subAgent.name }}</div>
                                                <div style="font-size: 12px; color: var(--text-secondary);">{{ subAgent.desc }}</div>
                                            </div>
                                        </div>
                                        <div class="subagent-actions">
                                            <div class="toggle" :class="{ active: subAgent.enabled }" @click="toggleSubAgent(subAgent)"></div>
                                            <button class="btn btn-sm btn-secondary" @click="toggleSubAgentExpand(subAgent)">{{ expandedSubAgents[subAgent.id] ? '收起' : '展开' }}</button>
                                            <button class="btn btn-sm btn-secondary" @click="editSubAgent(subAgent)">编辑</button>
                                            <button class="btn btn-sm btn-secondary" @click="removeSubAgent(subAgent.id)">移除</button>
                                        </div>
                                    </div>

                                    <div v-if="expandedSubAgents[subAgent.id]" class="subagent-detail">
                                        <div class="subagent-config-grid">
                                            <div class="config-item">
                                                <span class="config-label">模型</span>
                                                <span class="config-value">{{ subAgent.model }}</span>
                                            </div>
                                            <div class="config-item">
                                                <span class="config-label">Temperature</span>
                                                <span class="config-value">{{ subAgent.temperature || 0.7 }}</span>
                                            </div>
                                            <div class="config-item">
                                                <span class="config-label">Max Tokens</span>
                                                <span class="config-value">{{ subAgent.maxTokens || 1024 }}</span>
                                            </div>
                                            <div class="config-item">
                                                <span class="config-label">Tools</span>
                                                <span class="config-value">{{ subAgent.tools?.length || 0 }} 个</span>
                                            </div>
                                            <div class="config-item">
                                                <span class="config-label">Skills</span>
                                                <span class="config-value">{{ subAgent.skills?.length || 0 }} 个</span>
                                            </div>
                                            <div class="config-item">
                                                <span class="config-label">Hooks</span>
                                                <span class="config-value">{{ (subAgent.hooks?.pre?.length || 0) + (subAgent.hooks?.post?.length || 0) }} 个</span>
                                            </div>
                                        </div>

                                        <div class="card" style="margin-top: 12px; background: var(--bg-secondary);">
                                            <div class="card-header">
                                                <span class="card-title" style="font-size: 13px;">系统提示词</span>
                                            </div>
                                            <div class="card-body" style="font-size: 12px; color: var(--text-secondary); padding: 12px;">
                                                {{ subAgent.systemPrompt || '未配置' }}
                                            </div>
                                        </div>

                                        <div class="subagent-tools-skills" v-if="subAgent.tools?.length > 0 || subAgent.skills?.length > 0">
                                            <div v-if="subAgent.tools?.length > 0" class="tag-list">
                                                <span class="tag tag-small" v-for="tool in subAgent.tools" :key="tool.id">🔧 {{ tool.name }}</span>
                                            </div>
                                            <div v-if="subAgent.skills?.length > 0" class="tag-list">
                                                <span class="tag tag-small tag-success" v-for="skill in subAgent.skills" :key="skill.id">⚡ {{ skill.name }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div v-if="selectedAgent.subAgents.length === 0" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
                                <div>暂无子 Agent，点击上方按钮添加</div>
                            </div>

                            <div style="margin-top: 20px; padding: 16px; background: var(--bg-secondary); border-radius: 8px; font-size: 13px; color: var(--text-secondary);">
                                <strong>编排说明</strong><br>
                                多 Agent 模式下，编排 Agent 会先将 query 路由到命中的子 Agent，然后归纳汇总各子 Agent 的回复生成最终输出。<br>
                                子 Agent 配置与单 Agent 使用同一套模型，支持 Tools、Skills、Hooks 等完整配置。
                            </div>
                        </div>

                        <!-- 前置/后置检测 -->
                        <div v-if="activeConfigTab === 'hooks'">
                            <div class="card" style="margin-bottom: 16px;">
                                <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                    <span class="card-title">前置检测 ({{ selectedAgent.hooks.pre?.length || 0 }})</span>
                                    <button class="btn btn-sm btn-primary" @click="openHookModal('pre')">+ 添加</button>
                                </div>
                                <div class="card-body">
                                    <div class="tool-list">
                                        <div class="tool-item" v-for="hook in selectedAgent.hooks.pre" :key="hook.id">
                                            <div class="tool-info">
                                                <div class="tool-icon">🔍</div>
                                                <div class="tool-details">
                                                    <div class="tool-name">{{ hook.name }}</div>
                                                    <div class="tool-desc">{{ hook.desc }}</div>
                                                </div>
                                            </div>
                                            <div class="tool-actions">
                                                <div class="toggle" :class="{ active: hook.enabled }" @click="toggleHook(hook)"></div>
                                                <button class="btn btn-sm btn-secondary" @click="removeHook(hook.id, 'pre')">移除</button>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-if="!selectedAgent.hooks.pre || selectedAgent.hooks.pre.length === 0" style="text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px;">
                                        暂无前置检测，点击上方按钮添加
                                    </div>
                                </div>
                            </div>
                            <div class="card">
                                <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                    <span class="card-title">后置检测 ({{ selectedAgent.hooks.post?.length || 0 }})</span>
                                    <button class="btn btn-sm btn-primary" @click="openHookModal('post')">+ 添加</button>
                                </div>
                                <div class="card-body">
                                    <div class="tool-list">
                                        <div class="tool-item" v-for="hook in selectedAgent.hooks.post" :key="hook.id">
                                            <div class="tool-info">
                                                <div class="tool-icon">✅</div>
                                                <div class="tool-details">
                                                    <div class="tool-name">{{ hook.name }}</div>
                                                    <div class="tool-desc">{{ hook.desc }}</div>
                                                </div>
                                            </div>
                                            <div class="tool-actions">
                                                <div class="toggle" :class="{ active: hook.enabled }" @click="toggleHook(hook)"></div>
                                                <button class="btn btn-sm btn-secondary" @click="removeHook(hook.id, 'post')">移除</button>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-if="!selectedAgent.hooks.post || selectedAgent.hooks.post.length === 0" style="text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px;">
                                        暂无后置检测，点击上方按钮添加
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showConfigModal = false">取消</button>
                        <button class="btn btn-primary" @click="showConfigModal = false">保存配置</button>
                    </div>
                </div>
            </div>

            <!-- 添加 Tool Modal -->
            <div class="modal-overlay" v-if="showToolModal" @click.self="showToolModal = false">
                <div class="modal" style="max-width: 600px; max-height: 80vh;">
                    <div class="modal-header">
                        <span class="modal-title">添加 Tool</span>
                        <button class="modal-close" @click="showToolModal = false">×</button>
                    </div>
                    <div class="modal-body" style="overflow-y: auto; max-height: 60vh;">
                        <div v-for="tool in availableTools" :key="tool.id" class="tool-select-item">
                            <div class="tool-select-info">
                                <div class="tool-select-name">{{ tool.name }}</div>
                                <div class="tool-select-desc">{{ tool.desc }}</div>
                                <div class="tool-select-category">{{ tool.category }}</div>
                            </div>
                            <button class="btn btn-primary btn-sm" @click="addTool(tool)" :disabled="selectedAgent.tools.find(t => t.id === tool.id)">
                                {{ selectedAgent.tools.find(t => t.id === tool.id) ? '已添加' : '添加' }}
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showToolModal = false">关闭</button>
                    </div>
                </div>
            </div>

            <!-- 添加 Skill Modal -->
            <div class="modal-overlay" v-if="showSkillModal" @click.self="showSkillModal = false">
                <div class="modal" style="max-width: 600px; max-height: 80vh;">
                    <div class="modal-header">
                        <span class="modal-title">添加 Skill</span>
                        <button class="modal-close" @click="showSkillModal = false">×</button>
                    </div>
                    <div class="modal-body" style="overflow-y: auto; max-height: 60vh;">
                        <div v-for="skill in availableSkills" :key="skill.id" class="tool-select-item">
                            <div class="tool-select-info">
                                <div class="tool-select-name">{{ skill.name }}</div>
                                <div class="tool-select-desc">{{ skill.desc }}</div>
                                <div class="tool-select-category">{{ skill.category }}</div>
                            </div>
                            <button class="btn btn-primary btn-sm" @click="addSkill(skill)" :disabled="selectedAgent.skills.find(s => s.id === skill.id)">
                                {{ selectedAgent.skills.find(s => s.id === skill.id) ? '已添加' : '添加' }}
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showSkillModal = false">关闭</button>
                    </div>
                </div>
            </div>

            <!-- 添加/编辑 子 Agent Modal -->
            <div class="modal-overlay" v-if="showSubAgentModal" @click.self="showSubAgentModal = false">
                <div class="modal" style="max-width: 600px;">
                    <div class="modal-header">
                        <span class="modal-title">{{ editingSubAgent ? '编辑子 Agent' : '添加子 Agent' }}</span>
                        <button class="modal-close" @click="showSubAgentModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">子 Agent 名称</label>
                            <input type="text" class="form-input" :value="editingSubAgent?.name" id="subAgentName" placeholder="如: 财神子Agent">
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">功能描述</label>
                            <textarea class="form-textarea" rows="2" id="subAgentDesc" placeholder="描述子 Agent 的功能...">{{ editingSubAgent?.desc }}</textarea>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">选择模型</label>
                            <select class="form-input" id="subAgentModel">
                                <option v-for="model in availableModels" :key="model.id" :value="model.name" :selected="editingSubAgent?.model === model.name">{{ model.name }}</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">系统 Prompt</label>
                            <textarea class="form-textarea" rows="4" placeholder="定义子 Agent 的角色和边界..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showSubAgentModal = false">取消</button>
                        <button class="btn btn-primary" @click="saveSubAgent({
                            name: document.getElementById('subAgentName').value,
                            desc: document.getElementById('subAgentDesc').value,
                            model: document.getElementById('subAgentModel').value
                        })">保存</button>
                    </div>
                </div>
            </div>

            <!-- 添加 Hook Modal -->
            <div class="modal-overlay" v-if="showHookModal" @click.self="showHookModal = false">
                <div class="modal" style="max-width: 600px; max-height: 80vh;">
                    <div class="modal-header">
                        <span class="modal-title">添加 {{ hookModalType === 'pre' ? '前置' : '后置' }}检测</span>
                        <button class="modal-close" @click="showHookModal = false">×</button>
                    </div>
                    <div class="modal-body" style="overflow-y: auto; max-height: 60vh;">
                        <div v-for="hook in availableHooks.filter(h => h.type === hookModalType)" :key="hook.id" class="tool-select-item">
                            <div class="tool-select-info">
                                <div class="tool-select-name">{{ hook.name }}</div>
                                <div class="tool-select-desc">{{ hook.desc }}</div>
                            </div>
                            <button class="btn btn-primary btn-sm" @click="addHook(hook)" :disabled="selectedAgent.hooks[hookModalType].find(h => h.id === hook.id)">
                                {{ selectedAgent.hooks[hookModalType].find(h => h.id === hook.id) ? '已添加' : '添加' }}
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showHookModal = false">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Agents Page
const AgentsPage = {
    setup() {
        const plugins = ref([
            { id: 1, name: '实时黄金价格抓取', desc: '获取实时黄金价格数据，支持多币种转换', prdKind: '自主规划', tags: ['官方预置', '金融服务'], version: 'v1.2.0', enabled: true, icon: '🪙' },
            { id: 2, name: '农历节气查询', desc: '查询农历日期、二十四节气、传统节日', prdKind: '工作流', tags: ['官方预置', '生活服务'], version: 'v2.0.1', enabled: true, icon: '📅' },
            { id: 3, name: '天气查询服务', desc: '实时天气查询，支持全球城市', prdKind: '多智能体协同', tags: ['第三方集成'], version: 'v1.0.5', enabled: false, icon: '🌤️' },
            { id: 4, name: '股票行情查询', desc: 'A股、港股、美股实时行情数据', prdKind: '自主规划', tags: ['金融服务'], version: 'v1.1.0', enabled: true, icon: '📈' },
            { id: 5, name: '周公解梦', desc: '传统解梦知识库查询', prdKind: '工作流', tags: ['官方预置', '文化'], version: 'v1.0.0', enabled: true, icon: '🌙' },
            { id: 6, name: '祈福话术生成', desc: '根据场景生成传统祈福祝寿话术', prdKind: '多智能体协同', tags: ['官方预置'], version: 'v1.3.0', enabled: true, icon: '🙏' }
        ]);

        const filterTag = ref('全部');
        const tags = ['全部', '自主规划', '工作流', '多智能体协同'];

        const filteredPlugins = computed(() => {
            if (filterTag.value === '全部') return plugins.value;
            return plugins.value.filter(p => p.prdKind === filterTag.value);
        });

        return { plugins, filterTag, tags, filteredPlugins };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">MCP 插件广场</h1>
                <p class="page-desc">为 AI 模型挂载原子化插件，赋予其联网与执行能力</p>
            </div>

            <div class="filters-bar">
                <button
                    v-for="tag in tags"
                    :key="tag"
                    class="btn btn-sm"
                    :class="filterTag === tag ? 'btn-primary' : 'btn-secondary'"
                    @click="filterTag = tag"
                >
                    {{ tag }}
                </button>
                <input type="text" class="filter-input" placeholder="搜索插件名称或描述...">
                <router-link to="/agents/add" class="btn btn-primary" style="text-decoration: none;">+ 新增插件服务</router-link>
            </div>

            <div class="grid-cards">
                <div class="plugin-card" v-for="plugin in filteredPlugins" :key="plugin.id">
                    <div class="plugin-header">
                        <div class="plugin-icon">{{ plugin.icon }}</div>
                        <div class="plugin-info">
                            <div class="plugin-name">{{ plugin.name }}</div>
                            <div class="plugin-tags">
                                <span class="plugin-tag">{{ plugin.prdKind }}</span>
                                <span class="plugin-tag" v-for="t in plugin.tags" :key="t">{{ t }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="plugin-desc">{{ plugin.desc }}</div>
                    <div style="margin-bottom: 12px;">
                        <a href="#" style="font-size: 12px; color: var(--primary);">开发文档 →</a>
                    </div>
                    <div class="plugin-footer">
                        <span class="plugin-version">{{ plugin.version }}</span>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <button class="header-btn" style="width: 32px; height: 32px;">✏️</button>
                            <div class="toggle" :class="{ active: plugin.enabled }" @click="plugin.enabled = !plugin.enabled"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Agent Add Page
const AgentAddPage = {
    methods: {
        cancel() { this.$router.push('/agents'); },
        save() { this.$router.push('/agents'); }
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">新增 AI Agent 插件</h1>
                <p class="page-desc">配置插件基础信息与服务接入参数</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">基础配置</span>
                </div>
                <div class="card-body">
                    <div class="form-group" style="margin-bottom: 16px;">
                        <label class="form-label">插件名称</label>
                        <input type="text" class="form-input" placeholder="如: 实时黄金价格抓取">
                    </div>
                    <div class="form-group" style="margin-bottom: 16px;">
                        <label class="form-label">功能描述</label>
                        <textarea class="form-textarea" rows="3" placeholder="描述作用及返回数据结构..."></textarea>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">分类标签</label>
                            <select class="form-input">
                                <option>第三方集成</option>
                                <option>官方预置</option>
                                <option>金融服务</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">版本号</label>
                            <input type="text" class="form-input" placeholder="v1.0.0">
                        </div>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-top: 20px;">
                <div class="card-header">
                    <span class="card-title">服务接入</span>
                </div>
                <div class="card-body">
                    <div class="form-group" style="margin-bottom: 16px;">
                        <label class="form-label">API 终端地址</label>
                        <input type="text" class="form-input" placeholder="https://api.example.com/mcp/v1">
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">认证方式</label>
                            <select class="form-input">
                                <option>无认证 (Public)</option>
                                <option>API Key</option>
                                <option>OAuth 2.0</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">响应超时 (ms)</label>
                            <input type="number" class="form-input" value="3000">
                        </div>
                    </div>
                </div>
            </div>

            <div style="margin-top: 24px; display: flex; gap: 12px; justify-content: flex-end;">
                <button class="btn btn-secondary" @click="cancel">取消</button>
                <button class="btn btn-primary" @click="save">保存设置</button>
            </div>
        </div>
    `
};

// Skill Management Page
const SkillPage = {
    setup() {
        const skills = ref([
            { id: 1, name: '祈福话术生成', category: '场景技能', desc: '根据场景生成传统祈福祝寿话术', version: 'v1.3.0', status: 'published', author: '系统官方', updatedAt: '2024-01-15', icon: '🙏' },
            { id: 2, name: '财神对话技能', category: '角色技能', desc: '财神角色对话技能包，包含财运、投资等话题', version: 'v2.1.0', status: 'published', author: '系统官方', updatedAt: '2024-01-14', icon: '🧧' },
            { id: 3, name: '反诈识别技能', category: '安全技能', desc: '识别诈骗话术并预警用户', version: 'v1.0.5', status: 'published', author: '安全团队', updatedAt: '2024-01-13', icon: '🛡️' },
            { id: 4, name: '多轮对话管理', category: '基础技能', desc: '支持复杂多轮对话上下文管理', version: 'v1.2.0', status: 'draft', author: '系统官方', updatedAt: '2024-01-12', icon: '💬' },
            { id: 5, name: '意图识别增强', category: '基础技能', desc: '增强意图识别准确率，支持模糊匹配', version: 'v1.1.0', status: 'published', author: 'AI实验室', updatedAt: '2024-01-11', icon: '🎯' },
            { id: 6, name: '周公解梦技能', category: '场景技能', desc: '传统解梦知识库查询与解读', version: 'v1.0.0', status: 'published', author: '内容团队', updatedAt: '2024-01-10', icon: '🌙' }
        ]);

        const showAddModal = ref(false);
        const showDetailModal = ref(false);
        const selectedSkill = ref(null);
        const filterCategory = ref('全部');
        const filterStatus = ref('全部');
        const searchQuery = ref('');

        const categories = ['全部', '场景技能', '角色技能', '安全技能', '基础技能'];
        const statuses = ['全部', '已发布', '草稿'];

        const filteredSkills = computed(() => {
            return skills.value.filter(skill => {
                const matchCategory = filterCategory.value === '全部' || skill.category === filterCategory.value;
                const matchStatus = filterStatus.value === '全部' || 
                    (filterStatus.value === '已发布' && skill.status === 'published') ||
                    (filterStatus.value === '草稿' && skill.status === 'draft');
                const matchSearch = !searchQuery.value || 
                    skill.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                    skill.desc.toLowerCase().includes(searchQuery.value.toLowerCase());
                return matchCategory && matchStatus && matchSearch;
            });
        });

        const viewSkillDetail = (skill) => {
            selectedSkill.value = skill;
            showDetailModal.value = true;
        };

        const deleteSkill = (id) => {
            if (confirm('确定要删除这个技能吗？')) {
                skills.value = skills.value.filter(s => s.id !== id);
            }
        };

        const toggleStatus = (skill) => {
            skill.status = skill.status === 'published' ? 'draft' : 'published';
        };

        return {
            skills, showAddModal, showDetailModal, selectedSkill,
            filterCategory, filterStatus, searchQuery,
            categories, statuses, filteredSkills,
            viewSkillDetail, deleteSkill, toggleStatus
        };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">Skill 技能管理</h1>
                <p class="page-desc">管理 AI Agent 的技能库，支持技能的创建、编辑与版本控制</p>
            </div>

            <div class="filters-bar">
                <select class="filter-select" v-model="filterCategory">
                    <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
                <select class="filter-select" v-model="filterStatus">
                    <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
                </select>
                <input type="text" class="filter-input" v-model="searchQuery" placeholder="搜索技能名称或描述...">
                <button class="btn btn-primary" @click="showAddModal = true">+ 新建 Skill 技能</button>
            </div>

            <div class="card">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>技能信息</th>
                                <th>分类</th>
                                <th>版本</th>
                                <th>状态</th>
                                <th>作者</th>
                                <th>更新时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="skill in filteredSkills" :key="skill.id">
                                <td>
                                    <div style="display: flex; align-items: center; gap: 12px;">
                                        <span style="font-size: 24px;">{{ skill.icon }}</span>
                                        <div>
                                            <div style="font-weight: 500;">{{ skill.name }}</div>
                                            <div style="font-size: 12px; color: var(--text-secondary);">{{ skill.desc }}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <span class="tag" :class="{
                                        'tag-primary': skill.category === '场景技能',
                                        'tag-success': skill.category === '角色技能',
                                        'tag-warning': skill.category === '安全技能',
                                        'tag-info': skill.category === '基础技能'
                                    }">{{ skill.category }}</span>
                                </td>
                                <td>{{ skill.version }}</td>
                                <td>
                                    <span class="tag" :class="skill.status === 'published' ? 'tag-success' : 'tag-info'">
                                        {{ skill.status === 'published' ? '已发布' : '草稿' }}
                                    </span>
                                </td>
                                <td>{{ skill.author }}</td>
                                <td>{{ skill.updatedAt }}</td>
                                <td>
                                    <div style="display: flex; gap: 8px;">
                                        <button class="btn btn-sm btn-secondary" @click="viewSkillDetail(skill)">详情</button>
                                        <button class="btn btn-sm" :class="skill.status === 'published' ? 'btn-secondary' : 'btn-primary'" @click="toggleStatus(skill)">
                                            {{ skill.status === 'published' ? '下架' : '发布' }}
                                        </button>
                                        <button class="btn btn-sm btn-secondary" @click="deleteSkill(skill.id)">删除</button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="modal-overlay" v-if="showAddModal" @click.self="showAddModal = false">
                <div class="modal" style="max-width: 640px;">
                    <div class="modal-header">
                        <span class="modal-title">新建 Skill 技能</span>
                        <button class="modal-close" @click="showAddModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">技能名称</label>
                            <input type="text" class="form-input" placeholder="如: 祈福话术生成">
                        </div>
                        <div class="form-row" style="margin-bottom: 16px;">
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label">技能分类</label>
                                <select class="form-input">
                                    <option>场景技能</option>
                                    <option>角色技能</option>
                                    <option>安全技能</option>
                                    <option>基础技能</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label">版本号</label>
                                <input type="text" class="form-input" placeholder="v1.0.0">
                            </div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">技能描述</label>
                            <textarea class="form-textarea" rows="3" placeholder="描述技能的功能和用途..."></textarea>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">技能定义 (JSON)</label>
                            <textarea class="form-textarea" rows="8" placeholder='{
  "name": "skill_name",
  "description": "技能描述",
  "parameters": {
    "type": "object",
    "properties": {}
  }
}'></textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Prompt 模板</label>
                            <textarea class="form-textarea" rows="4" placeholder="输入技能的 Prompt 模板..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showAddModal = false">取消</button>
                        <button class="btn btn-primary" @click="showAddModal = false">保存为草稿</button>
                        <button class="btn btn-primary" @click="showAddModal = false">发布</button>
                    </div>
                </div>
            </div>

            <div class="modal-overlay" v-if="showDetailModal" @click.self="showDetailModal = false">
                <div class="modal" style="max-width: 640px;" v-if="selectedSkill">
                    <div class="modal-header">
                        <span class="modal-title">Skill 详情</span>
                        <button class="modal-close" @click="showDetailModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
                            <span style="font-size: 48px;">{{ selectedSkill.icon }}</span>
                            <div>
                                <div style="font-size: 20px; font-weight: 600;">{{ selectedSkill.name }}</div>
                                <div style="color: var(--text-secondary);">{{ selectedSkill.desc }}</div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px;">
                            <div class="info-item">
                                <div class="info-label">分类</div>
                                <div class="info-value">{{ selectedSkill.category }}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">版本</div>
                                <div class="info-value">{{ selectedSkill.version }}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">状态</div>
                                <div class="info-value">
                                    <span class="tag" :class="selectedSkill.status === 'published' ? 'tag-success' : 'tag-info'">
                                        {{ selectedSkill.status === 'published' ? '已发布' : '草稿' }}
                                    </span>
                                </div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">作者</div>
                                <div class="info-value">{{ selectedSkill.author }}</div>
                            </div>
                        </div>
                        <div class="card" style="background: var(--bg-secondary);">
                            <div class="card-header">
                                <span class="card-title">技能定义</span>
                            </div>
                            <div class="card-body">
                                <pre style="margin: 0; font-size: 12px; overflow-x: auto;"><code>{
  "name": "{{ selectedSkill.name }}",
  "description": "{{ selectedSkill.desc }}",
  "version": "{{ selectedSkill.version }}",
  "type": "skill"
}</code></pre>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showDetailModal = false">关闭</button>
                        <button class="btn btn-primary">编辑</button>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Hooks Management Page
const HooksPage = {
    setup() {
        // 前置检测 Hooks
        const preHooks = ref([
            {
                id: 'pre-001',
                name: '安全检测',
                type: 'pre',
                typeLabel: '前置检测',
                desc: '检测输入是否包含敏感词、恶意内容或违规信息',
                category: '安全',
                status: 'published',
                priority: 1,
                config: {
                    sensitiveWords: ['暴力', '色情', '赌博', '毒品'],
                    blockLevel: 'high',
                    action: 'block'
                },
                usageCount: 15234,
                updatedAt: '2024-01-15',
                icon: '🛡️'
            },
            {
                id: 'pre-002',
                name: '意图识别',
                type: 'pre',
                typeLabel: '前置检测',
                desc: '识别用户意图，用于多Agent路由决策',
                category: '路由',
                status: 'published',
                priority: 2,
                config: {
                    model: 'qwen-turbo',
                    confidence: 0.8,
                    timeout: 500
                },
                usageCount: 28956,
                updatedAt: '2024-01-14',
                icon: '🎯'
            },
            {
                id: 'pre-003',
                name: '参数校验',
                type: 'pre',
                typeLabel: '前置检测',
                desc: '校验输入参数格式、必填项和合法性',
                category: '校验',
                status: 'published',
                priority: 0,
                config: {
                    schema: 'standard',
                    strictMode: true
                },
                usageCount: 45678,
                updatedAt: '2024-01-13',
                icon: '✅'
            },
            {
                id: 'pre-004',
                name: '权限校验',
                type: 'pre',
                typeLabel: '前置检测',
                desc: '验证用户身份、调用权限和频次限制',
                category: '安全',
                status: 'draft',
                priority: 0,
                config: {
                    authType: 'token',
                    rateLimit: 100
                },
                usageCount: 0,
                updatedAt: '2024-01-12',
                icon: '🔐'
            },
            {
                id: 'pre-005',
                name: '上下文预处理',
                type: 'pre',
                typeLabel: '前置检测',
                desc: '初始化会话上下文，加载用户历史记录',
                category: '上下文',
                status: 'published',
                priority: 3,
                config: {
                    sessionTimeout: 3600,
                    maxHistory: 10
                },
                usageCount: 32145,
                updatedAt: '2024-01-11',
                icon: '📝'
            }
        ]);

        // 后置检测 Hooks
        const postHooks = ref([
            {
                id: 'post-001',
                name: '内容审核',
                type: 'post',
                typeLabel: '后置检测',
                desc: '审核输出内容合规性，过滤敏感信息',
                category: '安全',
                status: 'published',
                priority: 0,
                config: {
                    checkLevel: 'strict',
                    maskSensitive: true
                },
                usageCount: 45231,
                updatedAt: '2024-01-15',
                icon: '🔍'
            },
            {
                id: 'post-002',
                name: '结果汇总',
                type: 'post',
                typeLabel: '后置检测',
                desc: '多Agent场景下汇总各子Agent结果并生成回复',
                category: '处理',
                status: 'published',
                priority: 1,
                config: {
                    model: 'qwen-plus',
                    maxTokens: 2048
                },
                usageCount: 12345,
                updatedAt: '2024-01-14',
                icon: '📊'
            },
            {
                id: 'post-003',
                name: '格式标准化',
                type: 'post',
                typeLabel: '后置检测',
                desc: '统一输出格式，处理Markdown、JSON等格式',
                category: '处理',
                status: 'published',
                priority: 2,
                config: {
                    format: 'markdown',
                    autoFix: true
                },
                usageCount: 28934,
                updatedAt: '2024-01-13',
                icon: '📐'
            },
            {
                id: 'post-004',
                name: '敏感信息脱敏',
                type: 'post',
                typeLabel: '后置检测',
                desc: '自动识别并脱敏手机号、身份证等敏感信息',
                category: '安全',
                status: 'published',
                priority: 0,
                config: {
                    rules: ['phone', 'idcard', 'email'],
                    maskChar: '*'
                },
                usageCount: 19876,
                updatedAt: '2024-01-12',
                icon: '🎭'
            },
            {
                id: 'post-005',
                name: '日志记录',
                type: 'post',
                typeLabel: '后置检测',
                desc: '记录请求日志、响应结果用于审计和分析',
                category: '监控',
                status: 'draft',
                priority: 99,
                config: {
                    logLevel: 'info',
                    retention: 30
                },
                usageCount: 0,
                updatedAt: '2024-01-10',
                icon: '📋'
            }
        ]);

        const activeTab = ref('pre');
        const filterCategory = ref('全部');
        const filterStatus = ref('全部');
        const searchQuery = ref('');
        const showAddModal = ref(false);
        const showDetailModal = ref(false);
        const showConfigModal = ref(false);
        const selectedHook = ref(null);
        const editingHook = ref(null);

        const categories = ['全部', '安全', '路由', '校验', '上下文', '处理', '监控'];
        const statuses = ['全部', '已发布', '草稿'];

        const allHooks = computed(() => {
            return activeTab.value === 'pre' ? preHooks.value : postHooks.value;
        });

        const filteredHooks = computed(() => {
            const hooks = allHooks.value;
            return hooks.filter(hook => {
                const matchCategory = filterCategory.value === '全部' || hook.category === filterCategory.value;
                const matchStatus = filterStatus.value === '全部' ||
                    (filterStatus.value === '已发布' && hook.status === 'published') ||
                    (filterStatus.value === '草稿' && hook.status === 'draft');
                const matchSearch = !searchQuery.value ||
                    hook.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                    hook.desc.toLowerCase().includes(searchQuery.value.toLowerCase());
                return matchCategory && matchStatus && matchSearch;
            }).sort((a, b) => a.priority - b.priority);
        });

        const viewHookDetail = (hook) => {
            selectedHook.value = hook;
            showDetailModal.value = true;
        };

        const openAddModal = () => {
            editingHook.value = null;
            showAddModal.value = true;
        };

        const editHook = (hook) => {
            editingHook.value = { ...hook };
            showAddModal.value = true;
        };

        const saveHook = (hookData) => {
            const hooks = activeTab.value === 'pre' ? preHooks : postHooks;
            if (editingHook.value) {
                const index = hooks.value.findIndex(h => h.id === editingHook.value.id);
                if (index !== -1) {
                    hooks.value[index] = { ...hookData, id: editingHook.value.id };
                }
            } else {
                const newId = `${activeTab.value}-${Date.now()}`;
                hooks.value.push({
                    ...hookData,
                    id: newId,
                    type: activeTab.value,
                    typeLabel: activeTab.value === 'pre' ? '前置检测' : '后置检测',
                    status: 'draft',
                    usageCount: 0,
                    updatedAt: new Date().toISOString().split('T')[0]
                });
            }
            showAddModal.value = false;
            editingHook.value = null;
        };

        const deleteHook = (id) => {
            if (confirm('确定要删除这个检测 Hook 吗？')) {
                const hooks = activeTab.value === 'pre' ? preHooks : postHooks;
                hooks.value = hooks.value.filter(h => h.id !== id);
            }
        };

        const toggleStatus = (hook) => {
            hook.status = hook.status === 'published' ? 'draft' : 'published';
        };

        const toggleHook = (hook) => {
            hook.enabled = !hook.enabled;
        };

        const movePriority = (hook, direction) => {
            const hooks = allHooks.value;
            const index = hooks.findIndex(h => h.id === hook.id);
            if (direction === 'up' && index > 0) {
                const temp = hooks[index].priority;
                hooks[index].priority = hooks[index - 1].priority;
                hooks[index - 1].priority = temp;
            } else if (direction === 'down' && index < hooks.length - 1) {
                const temp = hooks[index].priority;
                hooks[index].priority = hooks[index + 1].priority;
                hooks[index + 1].priority = temp;
            }
        };

        return {
            preHooks, postHooks, activeTab,
            filterCategory, filterStatus, searchQuery,
            categories, statuses, filteredHooks,
            showAddModal, showDetailModal, showConfigModal,
            selectedHook, editingHook,
            viewHookDetail, openAddModal, editHook, saveHook, deleteHook, toggleStatus,
            movePriority
        };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">前后置检测管理</h1>
                <p class="page-desc">管理 Agent 工作流的前置检测（Pre-hooks）和后置检测（Post-hooks），控制请求处理流程</p>
            </div>

            <div class="agent-tabs" style="margin-bottom: 24px;">
                <button class="agent-tab" :class="{ active: activeTab === 'pre' }" @click="activeTab = 'pre'">
                    🔍 前置检测 ({{ preHooks.length }})
                </button>
                <button class="agent-tab" :class="{ active: activeTab === 'post' }" @click="activeTab = 'post'">
                    ✅ 后置检测 ({{ postHooks.length }})
                </button>
            </div>

            <div class="filters-bar">
                <select class="filter-select" v-model="filterCategory">
                    <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
                <select class="filter-select" v-model="filterStatus">
                    <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
                </select>
                <input type="text" class="filter-input" v-model="searchQuery" placeholder="搜索检测名称或描述...">
                <button class="btn btn-primary" @click="openAddModal">+ 新建 {{ activeTab === 'pre' ? '前置' : '后置' }}检测</button>
            </div>

            <div class="card">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width: 60px;">优先级</th>
                                <th>检测信息</th>
                                <th>分类</th>
                                <th>状态</th>
                                <th>调用次数</th>
                                <th>更新时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="hook in filteredHooks" :key="hook.id">
                                <td>
                                    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
                                        <button class="btn btn-xs btn-secondary" @click="movePriority(hook, 'up')" style="padding: 2px 6px; font-size: 10px;">▲</button>
                                        <span style="font-weight: 600; font-size: 14px;">{{ hook.priority }}</span>
                                        <button class="btn btn-xs btn-secondary" @click="movePriority(hook, 'down')" style="padding: 2px 6px; font-size: 10px;">▼</button>
                                    </div>
                                </td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 12px;">
                                        <span style="font-size: 24px;">{{ hook.icon }}</span>
                                        <div>
                                            <div style="font-weight: 500;">{{ hook.name }}</div>
                                            <div style="font-size: 12px; color: var(--text-secondary);">{{ hook.desc }}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <span class="tag" :class="{
                                        'tag-warning': hook.category === '安全',
                                        'tag-primary': hook.category === '路由',
                                        'tag-info': hook.category === '校验',
                                        'tag-success': hook.category === '上下文',
                                        'tag-secondary': hook.category === '处理',
                                        'tag-default': hook.category === '监控'
                                    }">{{ hook.category }}</span>
                                </td>
                                <td>
                                    <span class="tag" :class="hook.status === 'published' ? 'tag-success' : 'tag-info'">
                                        {{ hook.status === 'published' ? '已发布' : '草稿' }}
                                    </span>
                                </td>
                                <td>{{ hook.usageCount.toLocaleString() }}</td>
                                <td>{{ hook.updatedAt }}</td>
                                <td>
                                    <div style="display: flex; gap: 8px;">
                                        <button class="btn btn-sm btn-secondary" @click="viewHookDetail(hook)">详情</button>
                                        <button class="btn btn-sm btn-secondary" @click="editHook(hook)">编辑</button>
                                        <button class="btn btn-sm" :class="hook.status === 'published' ? 'btn-secondary' : 'btn-primary'" @click="toggleStatus(hook)">
                                            {{ hook.status === 'published' ? '下架' : '发布' }}
                                        </button>
                                        <button class="btn btn-sm btn-secondary" @click="deleteHook(hook.id)">删除</button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 新建/编辑 Hook Modal -->
            <div class="modal-overlay" v-if="showAddModal" @click.self="showAddModal = false">
                <div class="modal" style="max-width: 640px;">
                    <div class="modal-header">
                        <span class="modal-title">{{ editingHook ? '编辑' : '新建' }} {{ activeTab === 'pre' ? '前置' : '后置' }}检测</span>
                        <button class="modal-close" @click="showAddModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">检测名称</label>
                            <input type="text" class="form-input" :value="editingHook?.name" id="hookName" placeholder="如: 安全检测">
                        </div>
                        <div class="form-row" style="margin-bottom: 16px;">
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label">分类</label>
                                <select class="form-input" id="hookCategory">
                                    <option v-for="cat in categories.slice(1)" :key="cat" :value="cat" :selected="editingHook?.category === cat">{{ cat }}</option>
                                </select>
                            </div>
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label">优先级</label>
                                <input type="number" class="form-input" :value="editingHook?.priority || 0" id="hookPriority" placeholder="数字越小优先级越高">
                            </div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">功能描述</label>
                            <textarea class="form-textarea" rows="3" id="hookDesc" placeholder="描述检测的功能和作用...">{{ editingHook?.desc }}</textarea>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">图标</label>
                            <select class="form-input" id="hookIcon">
                                <option :selected="editingHook?.icon === '🛡️'">🛡️</option>
                                <option :selected="editingHook?.icon === '🎯'">🎯</option>
                                <option :selected="editingHook?.icon === '✅'">✅</option>
                                <option :selected="editingHook?.icon === '🔐'">🔐</option>
                                <option :selected="editingHook?.icon === '📝'">📝</option>
                                <option :selected="editingHook?.icon === '🔍'">🔍</option>
                                <option :selected="editingHook?.icon === '📊'">📊</option>
                                <option :selected="editingHook?.icon === '📐'">📐</option>
                                <option :selected="editingHook?.icon === '🎭'">🎭</option>
                                <option :selected="editingHook?.icon === '📋'">📋</option>
                            </select>
                        </div>
                        <div class="card" style="background: var(--bg-secondary); margin-bottom: 16px;">
                            <div class="card-header">
                                <span class="card-title">配置参数 (JSON)</span>
                            </div>
                            <div class="card-body">
                                <textarea class="form-textarea" rows="6" id="hookConfig" placeholder='{"key": "value"}'>{{ editingHook ? JSON.stringify(editingHook.config, null, 2) : '{}' }}</textarea>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showAddModal = false">取消</button>
                        <button class="btn btn-primary" @click="saveHook({
                            name: document.getElementById('hookName').value,
                            category: document.getElementById('hookCategory').value,
                            priority: parseInt(document.getElementById('hookPriority').value) || 0,
                            desc: document.getElementById('hookDesc').value,
                            icon: document.getElementById('hookIcon').value,
                            config: JSON.parse(document.getElementById('hookConfig').value || '{}')
                        })">保存</button>
                    </div>
                </div>
            </div>

            <!-- Hook 详情 Modal -->
            <div class="modal-overlay" v-if="showDetailModal" @click.self="showDetailModal = false">
                <div class="modal" style="max-width: 640px;" v-if="selectedHook">
                    <div class="modal-header">
                        <span class="modal-title">检测详情</span>
                        <button class="modal-close" @click="showDetailModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
                            <span style="font-size: 48px;">{{ selectedHook.icon }}</span>
                            <div>
                                <div style="font-size: 20px; font-weight: 600;">{{ selectedHook.name }}</div>
                                <div style="display: flex; gap: 8px; margin-top: 4px;">
                                    <span class="tag" :class="selectedHook.type === 'pre' ? 'tag-primary' : 'tag-success'">{{ selectedHook.typeLabel }}</span>
                                    <span class="tag" :class="{
                                        'tag-warning': selectedHook.category === '安全',
                                        'tag-primary': selectedHook.category === '路由',
                                        'tag-info': selectedHook.category === '校验',
                                        'tag-success': selectedHook.category === '上下文',
                                        'tag-secondary': selectedHook.category === '处理',
                                        'tag-default': selectedHook.category === '监控'
                                    }">{{ selectedHook.category }}</span>
                                    <span class="tag" :class="selectedHook.status === 'published' ? 'tag-success' : 'tag-info'">{{ selectedHook.status === 'published' ? '已发布' : '草稿' }}</span>
                                </div>
                            </div>
                        </div>
                        <div class="card" style="background: var(--bg-secondary); margin-bottom: 16px;">
                            <div class="card-body">
                                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">功能描述</div>
                                <div>{{ selectedHook.desc }}</div>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px;">
                            <div class="info-item">
                                <div class="info-label">优先级</div>
                                <div class="info-value">{{ selectedHook.priority }}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">调用次数</div>
                                <div class="info-value">{{ selectedHook.usageCount.toLocaleString() }}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">更新时间</div>
                                <div class="info-value">{{ selectedHook.updatedAt }}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Hook ID</div>
                                <div class="info-value" style="font-size: 12px;">{{ selectedHook.id }}</div>
                            </div>
                        </div>
                        <div class="card" style="background: var(--bg-secondary);">
                            <div class="card-header">
                                <span class="card-title">配置参数</span>
                            </div>
                            <div class="card-body">
                                <pre style="margin: 0; font-size: 12px; overflow-x: auto;"><code>{{ JSON.stringify(selectedHook.config, null, 2) }}</code></pre>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showDetailModal = false">关闭</button>
                        <button class="btn btn-primary" @click="showDetailModal = false; editHook(selectedHook)">编辑</button>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Digital Human Page
const DigitalHumanPage = {
    setup() {
        const humans = ref([
            { id: 1, name: '财神形象 A', product: '财神灯 Pro', voice: '男声-醇厚', version: 'v2.1', status: 'active', icon: '🧧' },
            { id: 2, name: '观音形象 B', product: '祈福灯', voice: '女声-温柔', version: 'v1.5', status: 'active', icon: '☸️' },
            { id: 3, name: '童子形象 C', product: '智慧灯', voice: '童声-活泼', version: 'v1.0', status: 'draft', icon: '👶' }
        ]);

        return { humans };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">数字人配置管理</h1>
                <p class="page-desc">管理硬件人物形象、音色版本与克隆素材</p>
            </div>

            <div class="filters-bar">
                <input type="text" class="filter-input" placeholder="搜索数字人...">
                <button class="btn btn-primary">+ 新建数字人</button>
            </div>

            <div class="device-grid">
                <div class="device-card" v-for="human in humans" :key="human.id">
                    <div class="device-header">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 32px;">{{ human.icon }}</span>
                            <div>
                                <div style="font-weight: 600;">{{ human.name }}</div>
                                <div style="font-size: 12px; color: var(--text-secondary);">{{ human.product }}</div>
                            </div>
                        </div>
                        <span class="tag" :class="human.status === 'active' ? 'tag-success' : 'tag-info'">
                            {{ human.status === 'active' ? '已发布' : '草稿' }}
                        </span>
                    </div>
                    <div class="device-info">
                        <div class="device-info-row">
                            <span class="device-info-label">音色版本</span>
                            <span class="device-info-value">{{ human.voice }}</span>
                        </div>
                        <div class="device-info-row">
                            <span class="device-info-label">模型版本</span>
                            <span class="device-info-value">{{ human.version }}</span>
                        </div>
                        <div class="device-info-row">
                            <span class="device-info-label">部署类型</span>
                            <span class="device-info-value">云端</span>
                        </div>
                    </div>
                    <div style="margin-top: 16px; display: flex; gap: 8px;">
                        <button class="btn btn-secondary btn-sm" style="flex: 1;">编辑</button>
                        <button class="btn btn-primary btn-sm" style="flex: 1;">系统调试</button>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Devices Page
const DevicesPage = {
    setup() {
        const devices = ref([
            { id: 'FG-001-A', model: '财神灯 Pro', firmware: 'v2.3.1', status: 'online', lastHeartbeat: '2分钟前', scene: '祈福祝寿' },
            { id: 'FG-002-B', model: '祈福灯', firmware: 'v1.8.0', status: 'online', lastHeartbeat: '5分钟前', scene: '财神唱诵' },
            { id: 'FG-003-C', model: '智慧灯', firmware: 'v1.5.2', status: 'offline', lastHeartbeat: '2小时前', scene: '周公解梦' },
            { id: 'FG-004-D', model: '财神灯 Pro', firmware: 'v2.3.0', status: 'online', lastHeartbeat: '1分钟前', scene: '祈福祝寿' },
            { id: 'FG-005-E', model: '祈福灯', firmware: 'v1.8.0', status: 'online', lastHeartbeat: '10分钟前', scene: '反诈守财' }
        ]);

        const showProvisionModal = ref(false);

        return { devices, showProvisionModal };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">设备资产管理</h1>
                <p class="page-desc">管理硬件设备群及其搭载的端侧模型版本</p>
            </div>

            <div class="filters-bar">
                <input type="text" class="filter-input" placeholder="搜索设备 ID...">
                <select class="filter-select">
                    <option>全部场景</option>
                    <option>祈福祝寿</option>
                    <option>财神唱诵</option>
                    <option>周公解梦</option>
                </select>
                <select class="filter-select">
                    <option>全部状态</option>
                    <option>在线</option>
                    <option>离线</option>
                </select>
                <button class="btn btn-secondary">批量操作</button>
                <button class="btn btn-primary" @click="showProvisionModal = true">+ 新增设备配置 (Provision)</button>
            </div>

            <div class="card">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>设备详情</th>
                                <th>运营场景</th>
                                <th>型号与固件</th>
                                <th>连接状态</th>
                                <th>最后心跳</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="device in devices" :key="device.id">
                                <td>
                                    <div style="font-weight: 500;">{{ device.id }}</div>
                                    <div style="font-size: 12px; color: var(--text-secondary);">{{ device.model }}</div>
                                </td>
                                <td>{{ device.scene }}</td>
                                <td>
                                    <div>{{ device.model }}</div>
                                    <div style="font-size: 12px; color: var(--text-secondary);">{{ device.firmware }}</div>
                                </td>
                                <td>
                                    <span class="tag" :class="device.status === 'online' ? 'tag-success' : 'tag-error'">
                                        <span class="status-dot" :class="device.status"></span>
                                        {{ device.status === 'online' ? '在线' : '离线' }}
                                    </span>
                                </td>
                                <td>{{ device.lastHeartbeat }}</td>
                                <td>
                                    <button class="header-btn">⋮</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div style="margin-top: 16px; font-size: 13px; color: var(--text-secondary);">
                正在查看 {{ devices.length }} 台设备，共 12,842 台分布于 14 个区域
            </div>

            <div class="modal-overlay" v-if="showProvisionModal" @click.self="showProvisionModal = false">
                <div class="modal">
                    <div class="modal-header">
                        <span class="modal-title">新增设备配置 (Provision)</span>
                        <button class="modal-close" @click="showProvisionModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">设备 ID / 批次</label>
                            <input type="text" class="form-input" placeholder="如: FG-001-A 或 FG-001-*">
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">运营场景</label>
                            <select class="form-input">
                                <option>祈福祝寿</option>
                                <option>财神唱诵</option>
                                <option>周公解梦</option>
                                <option>反诈守财</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">端侧模型版本</label>
                            <input type="text" class="form-input" placeholder="如: M-1.4">
                        </div>
                        <div style="padding: 12px; background: var(--bg-secondary); border-radius: 8px; font-size: 13px; color: var(--text-secondary);">
                            配置同步后将在设备下次心跳时生效；若设备当前离线，将在上线后拉取。
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showProvisionModal = false">取消</button>
                        <button class="btn btn-primary" @click="showProvisionModal = false">保存并下发</button>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Security Page
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

// Settings Page
const SettingsPage = {
    setup() {
        const user = ref({
            name: 'admin123',
            role: '超级管理员',
            isAdmin: true,
            permissions: ['业务概览', '场景工作流编排', 'AI Agent 中心', '数字人配置', '设备资产管理', '反诈与安全审计', '全局运营设置', '模型配置', '权限配置']
        });

        return { user };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">全局运营设置</h1>
                <p class="page-desc">管理账号权限与系统配置</p>
            </div>

            <div class="card" style="margin-bottom: 20px;">
                <div class="card-header">
                    <span class="card-title">当前账号权限</span>
                </div>
                <div class="card-body">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">当前角色</div>
                            <div style="font-weight: 600;">{{ user.role }}</div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">是否超管</div>
                            <div style="font-weight: 600;">{{ user.isAdmin ? '是' : '否' }}</div>
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">功能权限列表</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            <span v-for="perm in user.permissions" :key="perm" class="tag tag-info">
                                {{ perm }}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card" v-if="user.isAdmin">
                <div class="card-header">
                    <span class="card-title">权限配置（仅超管可见）</span>
                </div>
                <div class="card-body">
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>角色名称</th>
                                    <th>说明</th>
                                    <th>是否全局</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>超级管理员</td>
                                    <td>全局权限，包含权限配置</td>
                                    <td><span class="tag tag-success">是</span></td>
                                    <td><button class="btn btn-secondary btn-sm">编辑</button></td>
                                </tr>
                                <tr>
                                    <td>运营人员</td>
                                    <td>全系统功能权限，无权限配置</td>
                                    <td><span class="tag tag-success">是</span></td>
                                    <td><button class="btn btn-secondary btn-sm">编辑</button></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-top: 20px;">
                <div class="card-header">
                    <span class="card-title">其他设置</span>
                </div>
                <div class="card-body">
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">默认运营场景、全局请求超时、审计保留天数等配置。</p>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">默认场景</label>
                            <select class="form-input">
                                <option>祈福祝寿</option>
                                <option>财神唱诵</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">全局超时 (秒)</label>
                            <input type="number" class="form-input" value="120">
                        </div>
                    </div>
                    <button type="button" class="btn btn-secondary btn-sm">保存其他设置</button>
                </div>
            </div>
        </div>
    `
};

// Model Settings Page
const ModelSettingsPage = {
    setup() {
        const models = ref([
            { id: 1, name: 'Qwen-Turbo', provider: '阿里云 / 通义千问', category: '通义千问', status: '未配置', selected: false },
            { id: 2, name: 'Qwen-Plus', provider: '阿里云 / 通义千问', category: '通义千问', status: '未配置', selected: false },
            { id: 3, name: 'Qwen-Max', provider: '阿里云 / 通义千问', category: '通义千问', status: '已配置', selected: false },
            { id: 4, name: 'AI财神专业模型', provider: '阿里云 / 自定义模型', category: '自定义模型', status: '未配置', selected: false },
            { id: 5, name: '市场情报模型', provider: '阿里云 / 自定义模型', category: '自定义模型', status: '未配置', selected: false },
            { id: 6, name: 'GPT-3.5-Turbo', provider: 'OpenAI / GPT系列', category: 'GPT系列', status: '未配置', selected: false },
            { id: 7, name: 'GPT-4', provider: 'OpenAI / GPT系列', category: 'GPT系列', status: '未配置', selected: false },
            { id: 8, name: 'GPT-4 Turbo', provider: 'OpenAI / GPT系列', category: 'GPT系列', status: '未配置', selected: false },
            { id: 9, name: 'DeepSeek Chat', provider: 'DeepSeek / DeepSeek', category: 'DeepSeek', status: '未配置', selected: false },
            { id: 10, name: 'DeepSeek Coder', provider: 'DeepSeek / DeepSeek', category: 'DeepSeek', status: '未配置', selected: false },
            { id: 11, name: '豆包 Pro', provider: '字节跳动 / 豆包', category: '豆包', status: '未配置', selected: false },
            { id: 12, name: '豆包 Lite', provider: '字节跳动 / 豆包', category: '豆包', status: '未配置', selected: false },
            { id: 13, name: 'Grok Beta', provider: 'X(Twitter) / Grok', category: 'Grok', status: '未配置', selected: false }
        ]);

        const showAddModal = ref(false);
        const filterSupplier = ref('全部供应商');
        const filterStatus = ref('全部状态');
        const searchQuery = ref('');

        const filteredModels = computed(() => {
            let result = models.value;
            if (filterSupplier.value !== '全部供应商') {
                result = result.filter(m => m.provider.includes(filterSupplier.value));
            }
            if (filterStatus.value !== '全部状态') {
                result = result.filter(m => m.status === filterStatus.value);
            }
            if (searchQuery.value) {
                result = result.filter(m => m.name.toLowerCase().includes(searchQuery.value.toLowerCase()));
            }
            return result;
        });

        const selectedCount = computed(() => models.value.filter(m => m.selected).length);

        const toggleAll = (e) => {
            const checked = e.target.checked;
            filteredModels.value.forEach(m => m.selected = checked);
        };

        const newModel = reactive({
            name: '',
            modelId: '',
            supplier: '阿里云',
            category: '自定义模型',
            endpoint: '',
            apiKey: '',
            apiVersion: '',
            description: ''
        });

        const saveModel = () => {
            models.value.push({
                id: models.value.length + 1,
                name: newModel.name,
                provider: `${newModel.supplier} / ${newModel.category}`,
                category: newModel.category,
                status: '已配置',
                selected: false
            });
            showAddModal.value = false;
        };

        return {
            models, showAddModal, filterSupplier, filterStatus, searchQuery,
            filteredModels, selectedCount, toggleAll, newModel, saveModel
        };
    },
    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">模型配置</h1>
                <p class="page-desc">编排和调用模型所需的模型 API Key，并为模型配置所需的模型在场景编排与工作流中可用</p>
            </div>

            <div class="filters-bar">
                <input type="text" class="filter-input" v-model="searchQuery" placeholder="搜索模型名称、供应商...">
                <select class="filter-select" v-model="filterSupplier">
                    <option>全部供应商</option>
                    <option>阿里云</option>
                    <option>OpenAI</option>
                    <option>DeepSeek</option>
                    <option>字节跳动</option>
                </select>
                <select class="filter-select" v-model="filterStatus">
                    <option>全部状态</option>
                    <option>已配置</option>
                    <option>未配置</option>
                </select>
                <div style="flex: 1;"></div>
                <button class="btn btn-secondary">保存修改</button>
                <button class="btn btn-primary" @click="showAddModal = true">+ 新建配置</button>
            </div>

            <div class="card">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width: 40px;">
                                    <input type="checkbox" @change="toggleAll">
                                </th>
                                <th>模型名称</th>
                                <th>供应商 / 类别</th>
                                <th>API 状态</th>
                                <th>操作</th>
                                <th>获取 Key 参考</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="model in filteredModels" :key="model.id">
                                <td>
                                    <input type="checkbox" v-model="model.selected">
                                </td>
                                <td>
                                    <div style="font-weight: 500;">{{ model.name }}</div>
                                </td>
                                <td>
                                    <div style="font-size: 13px; color: var(--text-secondary);">{{ model.provider }}</div>
                                </td>
                                <td>
                                    <span class="tag" :class="model.status === '已配置' ? 'tag-success' : 'tag-info'">
                                        {{ model.status }}
                                    </span>
                                </td>
                                <td>
                                    <button class="btn btn-sm" :class="model.status === '已配置' ? 'btn-secondary' : 'btn-primary'">
                                        {{ model.status === '已配置' ? '配置 API' : '配置 API' }}
                                    </button>
                                </td>
                                <td>
                                    <a href="#" style="color: var(--primary); font-size: 13px;">{{ model.provider.split(' / ')[0] }} 控制台 ></a>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div style="padding: 16px 24px; border-top: 1px solid var(--border-light); font-size: 13px; color: var(--text-secondary);">
                    当前已选 {{ selectedCount }} 个模型
                </div>
            </div>

            <div class="modal-overlay" v-if="showAddModal" @click.self="showAddModal = false">
                <div class="modal" style="max-width: 560px;">
                    <div class="modal-header">
                        <span class="modal-title">新建配置</span>
                        <button class="modal-close" @click="showAddModal = false">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">模型名称 <span style="color: var(--error);">*</span></label>
                            <input type="text" class="form-input" v-model="newModel.name" placeholder="如：业务专属模型">
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">API 标识 <span style="color: var(--error);">*</span></label>
                            <input type="text" class="form-input" v-model="newModel.modelId" placeholder="英文唯一标识，如：gpt-4-turbo">
                            <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">格式要求：仅支持英文、数字、-、_、.、: 等字符</div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label">供应商 <span style="color: var(--error);">*</span></label>
                                <select class="form-input" v-model="newModel.supplier">
                                    <option>阿里云</option>
                                    <option>OpenAI</option>
                                    <option>DeepSeek</option>
                                    <option>字节跳动</option>
                                    <option>百度</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">模型类别 <span style="color: var(--error);">*</span></label>
                                <select class="form-input" v-model="newModel.category">
                                    <option>自定义模型</option>
                                    <option>通义千问</option>
                                    <option>GPT系列</option>
                                    <option>DeepSeek</option>
                                    <option>豆包</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">API Endpoint</label>
                            <input type="text" class="form-input" v-model="newModel.endpoint" placeholder="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation">
                            <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">请填写该模型的 API 终端节点地址 URL</div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">API Key <span style="color: var(--error);">*</span></label>
                            <div style="display: flex; gap: 8px;">
                                <input type="password" class="form-input" v-model="newModel.apiKey" placeholder="请输入 API Key" style="flex: 1;">
                                <button class="btn btn-secondary btn-sm">👁</button>
                            </div>
                            <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">配置后加密存储，在列表中显示为 智谱-***-末尾</div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">API 模型标识</label>
                            <input type="text" class="form-input" v-model="newModel.apiVersion" placeholder="如：qwen-turbo、gpt-4-turbo">
                            <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">部分供应商需要填写模型版本标识，用于 API 调用时识别</div>
                        </div>
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label class="form-label">描述</label>
                            <textarea class="form-textarea" v-model="newModel.description" rows="2" placeholder="模型用途说明（可选）"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="showAddModal = false">取消</button>
                        <button class="btn btn-primary" @click="saveModel">确定</button>
                    </div>
                </div>
            </div>
        </div>
    `
};

// Router
const routes = [
    { path: '/login', component: LoginPage, meta: { public: true } },
    {
        path: '/',
        component: AppLayout,
        children: [
            { path: '', component: OverviewPage, meta: { title: '业务概览' } },
            { path: 'workflow', component: WorkflowPage, meta: { title: 'Agent 工作流' } },
            { path: 'mcp', component: AgentsPage, meta: { title: 'MCP 管理' } },
            { path: 'agents/add', component: AgentAddPage, meta: { title: '新增 MCP 插件' } },
            { path: 'skills', component: SkillPage, meta: { title: 'Skill 技能管理' } },
            { path: 'hooks', component: HooksPage, meta: { title: '前后置检测管理' } },
            { path: 'digital-human', component: DigitalHumanPage, meta: { title: '数字人配置' } },
            { path: 'devices', component: DevicesPage, meta: { title: '设备资产管理' } },
            { path: 'security', component: SecurityPage, meta: { title: '反诈与安全审计' } },
            { path: 'settings', component: SettingsPage, meta: { title: '全局运营设置' } },
            { path: 'model-settings', component: ModelSettingsPage, meta: { title: '模型配置' } }
        ]
    }
];

const router = createRouter({
    history: createWebHashHistory(),
    routes
});

router.beforeEach((to, from, next) => {
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    if (!to.meta.public && !isLoggedIn) {
        next('/login');
    } else if (to.path === '/login' && isLoggedIn) {
        next('/');
    } else {
        next();
    }
});

// App
const app = createApp({});
app.use(router);
app.mount('#app');
