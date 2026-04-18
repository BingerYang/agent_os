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
                        <p class="page-desc">为 AI 模型挂载原子化插件；按 PRD 5.4 使用类型筛选，搜寻可用能力；新增跳转独立表单页。</p>
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
                        <input type="text" class="filter-input" placeholder="按插件名称或描述搜寻可用能力…">
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
                                <a href="#" @click.prevent style="font-size: 12px; color: var(--primary);">开发文档 →</a>
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