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