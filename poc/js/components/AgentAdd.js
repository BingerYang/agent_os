const AgentAddPage = {
            methods: {
                cancel() { this.$router.push('/agents'); },
                save() { this.$router.push('/agents'); }
            },
            template: `
                <div>
                    <div class="page-header">
                        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                            <router-link to="/agents" class="btn btn-secondary btn-sm" style="text-decoration: none;">← 返回广场</router-link>
                            <h1 class="page-title" style="margin: 0;">新增 AI Agent 插件</h1>
                        </div>
                        <p class="page-desc">基础配置 + 服务接入；右侧为版本保存记录（PRD 5.4）。</p>
                    </div>

                    <div class="workflow-layout" style="grid-template-columns: 1fr 320px; height: auto; min-height: 520px;">
                        <div class="workflow-panel" style="min-height: 480px;">
                            <div class="workflow-panel-header">基础配置与服务接入</div>
                            <div class="workflow-panel-body">
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
                                        <label class="form-label">当前版本号</label>
                                        <input type="text" class="form-input" placeholder="v1.0.0">
                                    </div>
                                </div>
                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label class="form-label">API 终端地址 (HTTPS)</label>
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
                                <div class="btn-group" style="margin-top: 24px;">
                                    <button type="button" class="btn btn-secondary" @click="cancel">取消</button>
                                    <button type="button" class="btn btn-primary" @click="save">保存设置</button>
                                </div>
                            </div>
                        </div>
                        <div class="workflow-panel" style="min-height: 480px;">
                            <div class="workflow-panel-header">版本保存记录</div>
                            <div class="workflow-panel-body">
                                <div class="empty-state" style="padding: 24px;">
                                    <div class="empty-icon">📋</div>
                                    <p style="font-size: 13px; color: var(--text-secondary);">暂无历史发布记录</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `
        };