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

                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">其他设置（PRD 5.9）</span>
                        </div>
                        <div class="card-body">
                            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">占位：默认运营场景、全局请求超时、审计保留天数等，后续对接配置中心。</p>
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