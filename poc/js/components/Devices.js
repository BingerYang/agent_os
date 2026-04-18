const DevicesPage = {
            setup() {
                const devices = ref([
                    { id: 'FG-001-A', model: '财神灯 Pro', vendor: '福光科技', batch: 'B-2025-Q4-01', firmware: 'v2.3.1', status: 'online', lastHeartbeat: '2分钟前', scene: '祈福祝寿' },
                    { id: 'FG-002-B', model: '祈福灯', vendor: '福光科技', batch: 'B-2025-Q4-01', firmware: 'v1.8.0', status: 'online', lastHeartbeat: '5分钟前', scene: '财神唱诵' },
                    { id: 'FG-003-C', model: '智慧灯', vendor: '慧联电子', batch: 'B-2025-Q3-02', firmware: 'v1.5.2', status: 'offline', lastHeartbeat: '2小时前', scene: '周公解梦' },
                    { id: 'FG-004-D', model: '财神灯 Pro', vendor: '福光科技', batch: 'B-2025-Q4-01', firmware: 'v2.3.0', status: 'online', lastHeartbeat: '1分钟前', scene: '祈福祝寿' },
                    { id: 'FG-005-E', model: '祈福灯', vendor: '福光科技', batch: 'B-2025-Q3-02', firmware: 'v1.8.0', status: 'online', lastHeartbeat: '10分钟前', scene: '反诈守财' }
                ]);

                const showProvisionModal = ref(false);
                const showImportModal = ref(false);

                return { devices, showProvisionModal, showImportModal };
            },
            template: `
                <div>
                    <div class="page-header">
                        <h1 class="page-title">设备资产管理</h1>
                        <p class="page-desc">端侧设备运维：列表含供应商、批次；支持批量导入（CSV）与 Provision（PRD 5.6，已去除 OTA 模块）。</p>
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
                            <option>全部供应商</option>
                            <option>福光科技</option>
                            <option>慧联电子</option>
                        </select>
                        <select class="filter-select">
                            <option>全部批次</option>
                            <option>B-2025-Q4-01</option>
                            <option>B-2025-Q3-02</option>
                        </select>
                        <select class="filter-select">
                            <option>全部状态</option>
                            <option>在线</option>
                            <option>离线</option>
                        </select>
                        <button type="button" class="btn btn-secondary" @click="showImportModal = true">批量导入</button>
                        <button type="button" class="btn btn-secondary">批量操作</button>
                        <button type="button" class="btn btn-primary" @click="showProvisionModal = true">+ 新增设备配置 (Provision)</button>
                    </div>

                    <div class="card">
                        <div class="table-container">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>设备详情</th>
                                        <th>供应商 / 批次</th>
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
                                        <td>
                                            <div>{{ device.vendor }}</div>
                                            <div style="font-size: 12px; color: var(--text-secondary);">{{ device.batch }}</div>
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

                    <!-- Provision Modal -->
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

                    <div class="modal-overlay" v-if="showImportModal" @click.self="showImportModal = false">
                        <div class="modal">
                            <div class="modal-header">
                                <span class="modal-title">批量导入设备</span>
                                <button class="modal-close" @click="showImportModal = false">×</button>
                            </div>
                            <div class="modal-body">
                                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">上传 CSV 或粘贴内容，预览后调用批量导入接口（原型占位）。</p>
                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label class="form-label">CSV 内容预览</label>
                                    <textarea class="form-textarea" rows="5" placeholder="device_id,vendor,batch,scene,model_version&#10;FG-001-A,福光科技,B-2025-Q4-01,祈福祝寿,M-1.4">device_id,vendor,batch,scene,model_version
FG-099-X,福光科技,B-2025-Q4-01,祈福祝寿,M-1.4</textarea>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button class="btn btn-secondary" @click="showImportModal = false">取消</button>
                                <button class="btn btn-primary" @click="showImportModal = false">解析并导入</button>
                            </div>
                        </div>
                    </div>
                </div>
            `
        };