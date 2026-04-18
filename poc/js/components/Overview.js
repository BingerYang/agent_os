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
                    // Initialize chart
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
                            <p class="page-desc">实时监控业务指标与健康度（PRD 5.2：支持按时间段查询与运营报告入口）</p>
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