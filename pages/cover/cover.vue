<template>
  <view class="cover" :class="'bg-' + (profile.bg || 'green')">
    <!-- 右上角：语言 / 设置 -->
    <view class="top-actions">
      <button class="round-btn" @click="toggleLang">{{ t('lang') }}</button>
      <button class="round-btn" @click="goSettings" v-if="loggedIn">⚙︎</button>
    </view>

    <!-- 中央 LOGO -->
    <view class="logo-wrap">
      <view class="logo-cards">
        <text class="lc c1">♠</text>
        <text class="lc c2">♥</text>
        <text class="lc c3">♦</text>
        <text class="lc c4">♣</text>
      </view>
      <text class="logo-title">{{ t('brand') }}</text>
      <text class="logo-sub">{{ onlineReady ? t('server_note') : t('offline_note') }}</text>
    </view>

    <!-- 下方：进入游戏 -->
    <view class="bottom">
      <button class="enter-btn" @click="enterGame">
        {{ loggedIn ? (profile.name || t('welcome')) + ' · ' + t('enter') : t('enter') }}
      </button>
      <view class="sub-row">
        <button class="text-link" @click="goRecords">{{ t('记录') === '记录' ? '对战记录' : 'Records' }}</button>
        <button class="text-link" v-if="loggedIn" @click="doLogout">{{ t('logout') }}</button>
      </view>
    </view>

    <!-- 登录弹窗（未登录点进入游戏时弹出） -->
    <view v-if="showLogin" class="login-mask" @click="showLogin = false">
      <view class="login-panel" @click.stop>
        <view class="tabs">
          <button class="tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">{{ t('login') }}</button>
          <button class="tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">{{ t('register') }}</button>
        </view>
        <input class="input" v-model="username" maxlength="16" :placeholder="t('username') + '（2-16）'" />
        <input class="input" v-model="password" password maxlength="32" :placeholder="t('password') + '（4+）'" />
        <button class="btn primary" @click="submit">{{ mode === 'login' ? t('login') : t('register') }}</button>
        <view class="row-links">
          <button class="text-link" @click="guest">{{ t('guest') }}</button>
          <button class="text-link warn" @click="forgot">{{ t('forgot') }}</button>
        </view>
        <text v-if="errMsg" class="err">{{ errMsg }}</text>
        <text class="note">{{ onlineReady ? t('server_note') : t('offline_note') }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import account from '@/common/account.js';
import i18n, { t as tr } from '@/common/i18n.js';
import net from '@/common/net.js';

export default {
  data() {
    return {
      t: tr,
      loggedIn: false,
      showLogin: false,
      mode: 'login',
      username: '',
      password: '',
      errMsg: '',
      profile: { bg: 'green', name: '' },
      onlineReady: false,
    };
  },
  onShow() {
    this.loggedIn = !!account.currentUser();
    try {
      const p = account.getProfile();
      if (p) this.profile = { ...this.profile, ...p };
    } catch (e) { /* ignore */ }
    this.onlineReady = !!net.netConfig().server;
  },
  methods: {
    toggleLang() {
      i18n.setLang(i18n.getLang() === 'zh' ? 'en' : 'zh');
      this.$forceUpdate();
    },
    goSettings() {
      if (!this.loggedIn) { this.showLogin = true; return; }
      uni.navigateTo({ url: '/pages/settings/settings' });
    },
    goRecords() {
      if (!this.loggedIn) { this.showLogin = true; return; }
      uni.navigateTo({ url: '/pages/records/records' });
    },
    enterGame() {
      if (this.loggedIn) {
        uni.reLaunch({ url: '/pages/index/index' });
        return;
      }
      this.showLogin = true;
    },
    submit() {
      this.errMsg = '';
      const name = (this.username || '').trim();
      const pwd = this.password || '';
      if (this.onlineReady) {
        // 服务器账户
        const p = this.mode === 'login' ? net.serverLogin(name, pwd) : net.serverRegister(name, pwd);
        p.then(r => {
          if (r.ok) {
            this.afterAuth(name);
          } else {
            this.errMsg = r.error || '操作失败';
          }
        });
      } else {
        try {
          if (this.mode === 'login') account.login(name, pwd);
          else account.register(name, pwd);
          this.afterAuth(name);
        } catch (e) {
          this.errMsg = e.message || '操作失败';
        }
      }
    },
    afterAuth(name) {
      this.showLogin = false;
      this.loggedIn = true;
      uni.showToast({ title: `${tr('welcome')}，${name}`, icon: 'none' });
      setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 600);
    },
    guest() {
      account.loginGuest();
      this.afterAuth('游客');
    },
    forgot() {
      uni.showModal({ title: tr('forgot'), content: tr('forgot_msg'), showCancel: false });
    },
    doLogout() {
      account.logout();
      net.serverLogout();
      this.loggedIn = false;
      this.showLogin = true;
    },
  },
};
</script>

<style scoped>
.cover {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}
.cover.bg-green { background: radial-gradient(ellipse at 50% 30%, #1a6b52 0%, #0d3b2e 70%); }
.cover.bg-blue { background: radial-gradient(ellipse at 50% 30%, #1c4a80 0%, #0b1f3d 70%); }
.cover.bg-purple { background: radial-gradient(ellipse at 50% 30%, #4d2a68 0%, #251234 70%); }
.top-actions {
  position: absolute;
  top: 24rpx;
  right: 24rpx;
  display: flex;
  gap: 12rpx;
  z-index: 10;
}
.round-btn {
  min-width: 72rpx;
  height: 60rpx;
  border-radius: 30rpx;
  background: rgba(18, 69, 53, 0.85);
  border: 2rpx solid #2a8f6d;
  color: #f3efe2;
  font-size: 24rpx;
  padding: 0 20rpx;
}
.logo-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 22vh;
}
.logo-cards { display: flex; gap: 8rpx; margin-bottom: 20rpx; }
.lc {
  font-size: 64rpx;
  color: #e7c766;
  text-shadow: 0 6rpx 30rpx rgba(231, 199, 102, 0.4);
  animation: float 3s ease-in-out infinite;
}
.lc.c2 { animation-delay: 0.3s; }
.lc.c3 { animation-delay: 0.6s; }
.lc.c4 { animation-delay: 0.9s; }
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-14rpx); }
}
.logo-title {
  font-size: 72rpx;
  font-weight: 800;
  color: #f3efe2;
  letter-spacing: 10rpx;
}
.logo-sub {
  margin-top: 14rpx;
  font-size: 22rpx;
  color: #9db8a8;
}
.bottom {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
  padding: 0 60rpx 12vh;
}
.enter-btn {
  width: 100%;
  max-width: 520rpx;
  background: #e7c766;
  color: #3a2c07;
  border: 2rpx solid #d9b76e;
  border-radius: 48rpx;
  padding: 26rpx 0;
  font-size: 36rpx;
  font-weight: 800;
  letter-spacing: 6rpx;
  box-shadow: 0 8rpx 30rpx rgba(231, 199, 102, 0.35);
}
.sub-row { display: flex; gap: 40rpx; }
.text-link {
  background: transparent;
  color: #9db8a8;
  font-size: 24rpx;
  padding: 6rpx;
}
.text-link.warn { color: #f3b8b8; }
.login-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 18, 13, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.login-panel {
  width: 560rpx;
  max-width: 90%;
  background: #124535;
  border: 2rpx solid #e7c76666;
  border-radius: 24rpx;
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.tabs { display: flex; gap: 12rpx; }
.tab {
  flex: 1;
  font-size: 28rpx;
  color: #9db8a8;
  background: #0d3b2e;
  border-radius: 14rpx;
  padding: 14rpx 0;
  font-weight: 700;
}
.tab.active { background: #e7c766; color: #3a2c07; }
.input {
  background: #0d3b2e;
  border: 2rpx solid #1e5c48;
  border-radius: 12rpx;
  padding: 18rpx 20rpx;
  color: #f3efe2;
  font-size: 26rpx;
}
.btn.primary {
  background: #e7c766;
  color: #3a2c07;
  border: 2rpx solid #d9b76e;
  border-radius: 40rpx;
  padding: 18rpx 0;
  font-size: 30rpx;
  font-weight: 700;
}
.row-links { display: flex; justify-content: space-between; }
.err { font-size: 24rpx; color: #f3b8b8; }
.note { font-size: 20rpx; color: #7ea391; text-align: center; }
</style>
