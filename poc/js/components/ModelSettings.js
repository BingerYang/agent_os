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

                    <!-- Add Model Modal -->
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