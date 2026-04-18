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
                        <p class="page-desc">人物与硬件、音色与克隆、模型配置（与场景工作流同款选择器）、系统调试（PRD 5.5）。</p>
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