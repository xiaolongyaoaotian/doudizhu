<template>
  <view class="page">
    <view class="hero">
      <text class="logo">♠</text>
      <text class="title">牌友斗地主</text>
      <text class="sub">离线单机 · 本地账户 · 数据互相隔离</text>
    </view>

    <view class="card">
      <view class="tabs">
        <button class="tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">登 录</button>
        <button class="tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">注 册</button>
      </view>
      <input class="input" v-model="username" maxlength="16" placeholder="用户名（2-16 位中文/字母/数字）" />
      <input class="input" v-model="password" password maxlength="32" placeholder="密码（至少 4 位）" />
      <button class="btn primary" @click="submit">{{ mode === 'login' ? '登录' : '注册并登录' }}</button>
      <button class="btn guest" @click="guest">游客试玩（数据独立保存）</button>
      <text v-if="errMsg" class="err">{{ errMsg }}</text>
      <text class="note">密码仅在本机加盐哈希后保存，不上传不联网；每个账户的积分、战绩、钱包互相隔离。</text>
      <text v-if="userCount" class="note">本机已有 {{ userCount }} 个账户：{{ users.join('、') }}</text>
    </view>
  </view>
</template>

<script>
import { register, login, loginGuest, listUsers } from '@/common/account.js';

export default {
  data() {
    return { mode: 'login', username: '', password: '', errMsg: '', users: [] };
  },
  computed: {
    userCount() { return this.users.length; },
  },
  onShow() {
    this.users = listUsers();
  },
  methods: {
    submit() {
      this.errMsg = '';
      try {
        const name = this.mode === 'login' ? login(this.username, this.password) : register(this.username, this.password);
        uni.showToast({ title: `欢迎，${name}`, icon: 'none' });
        this.enter();
      } catch (e) {
        this.errMsg = e.message || '操作失败';
      }
    },
    guest() {
      loginGuest();
      this.enter();
    },
    enter() {
      uni.reLaunch({ url: '/pages/index/index' });
    },
  },
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #0d3b2e;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
  gap: 30rpx;
}
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}
.logo {
  font-size: 80rpx;
  color: #e7c766;
}
.title {
  font-size: 48rpx;
  font-weight: 800;
  color: #f3efe2;
  letter-spacing: 4rpx;
}
.sub {
  font-size: 22rpx;
  color: #9db8a8;
}
.card {
  width: 100%;
  max-width: 640rpx;
  background: #124535;
  border: 2rpx solid #1e5c48;
  border-radius: 24rpx;
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.tabs {
  display: flex;
  gap: 12rpx;
}
.tab {
  flex: 1;
  font-size: 28rpx;
  color: #9db8a8;
  background: #0d3b2e;
  border-radius: 14rpx;
  padding: 14rpx 0;
  font-weight: 700;
}
.tab.active {
  background: #e7c766;
  color: #3a2c07;
}
.input {
  background: #0d3b2e;
  border: 2rpx solid #1e5c48;
  border-radius: 12rpx;
  padding: 18rpx 20rpx;
  color: #f3efe2;
  font-size: 26rpx;
}
.btn {
  border-radius: 40rpx;
  padding: 18rpx 0;
  font-size: 30rpx;
  font-weight: 700;
  text-align: center;
}
.btn.primary {
  background: #e7c766;
  color: #3a2c07;
  border: 2rpx solid #d9b76e;
}
.btn.guest {
  background: #1f7a5c;
  color: #f3efe2;
  border: 2rpx solid #2a8f6d;
}
.err {
  font-size: 24rpx;
  color: #f3b8b8;
}
.note {
  font-size: 20rpx;
  color: #7ea391;
  line-height: 1.6;
}
</style>
