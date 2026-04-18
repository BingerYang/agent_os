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
                                    <span class="icon">🔄</span>
                                    <span>场景工作流编排</span>
                                </router-link>
                                <router-link to="/agents" class="nav-item" :class="{ active: currentRoute === '/agents' }">
                                    <span class="icon">🧩</span>
                                    <span>AI Agent 中心</span>
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