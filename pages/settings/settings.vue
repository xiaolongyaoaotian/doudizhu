<template>
  <view class="page">
    <view class="card account-card">
      <view class="account-row">
        <view class="avatar-preview" :style="{ background: profile.avatarColor || '#1f7a5c' }">
          <text>{{ profile.avatarEmoji || '你' }}</text>
        </view>
        <view class="col">
          <text class="label">当前账户：{{ accountName || '未登录' }}</text>
          <text class="hint">积分、战绩、钱包均按账户隔离保存</text>
        </view>
      </view>
      <view class="join-row">
        <input class="input" v-model="serverAddr" placeholder="服务器地址 http://host:8080" />
        <button class="btn slim" @click="saveServer">保存</button>
      </view>
      <button class="btn primary" @click="goOnline">🌐 联机对战（匹配 / 好友房）</button>
      <button class="btn danger" @click="logout">退出登录 / 切换账户</button>
    </view>

    <view class="card">
      <text class="card-title">我的资料</text>
      <view class="row">
        <text class="label">昵称</text>
        <input class="input" v-model="profile.name" maxlength="16" placeholder="给自己起个名字" />
      </view>
      <button class="btn primary" @click="saveProfile">保存资料</button>
    </view>

    <view class="card">
      <text class="card-title">桌面个性化</text>
      <view class="row between">
        <view class="col">
          <text class="label">桌面背景</text>
          <text class="hint">长时间游戏推荐冷色调</text>
        </view>
        <view class="style-opts">
          <button class="style-opt" :class="{ active: profile.bg === 'green' }" @click="setBg('green')">青竹绿</button>
          <button class="style-opt" :class="{ active: profile.bg === 'blue' }" @click="setBg('blue')">深海蓝</button>
          <button class="style-opt" :class="{ active: profile.bg === 'purple' }" @click="setBg('purple')">暗夜紫</button>
        </view>
      </view>
      <view class="row between">
        <view class="col">
          <text class="label">牌背款式</text>
          <text class="hint">对手手牌与底牌的背面</text>
        </view>
        <view class="style-opts">
          <button class="style-opt" :class="{ active: profile.style === 'bamboo' }" @click="setStyle('bamboo')">青竹</button>
          <button class="style-opt" :class="{ active: profile.style === 'phoenix' }" @click="setStyle('phoenix')">朱雀</button>
          <button class="style-opt" :class="{ active: profile.style === 'custom' }" @click="setStyle('custom')">自定义</button>
        </view>
      </view>
      <view v-if="profile.style === 'custom'" class="custom-block">
        <text class="label">牌背图案 + 底色</text>
        <view class="emoji-grid">
          <button v-for="e in EMOJIS" :key="'b' + e" class="emoji-opt" :class="{ active: profile.backEmoji === e }" @click="profile.backEmoji = e; save()">{{ e }}</button>
        </view>
        <view class="color-row">
          <view v-for="c in COLORS" :key="'bc' + c" class="color-dot" :class="{ active: profile.backColor === c }" :style="{ background: c }" @click="profile.backColor = c; save()"></view>
        </view>
        <view class="back-preview" :style="{ background: profile.backColor }">
          <text>{{ profile.backEmoji || '🐉' }}</text>
        </view>
      </view>
      <view class="row between">
        <view class="col">
          <text class="label">我的头像</text>
          <text class="hint">emoji 图案 + 底色</text>
        </view>
        <view class="avatar-preview" :style="{ background: profile.avatarColor || '#1f7a5c' }">
          <text>{{ profile.avatarEmoji || '你' }}</text>
        </view>
      </view>
      <view class="custom-block">
        <view class="emoji-grid">
          <button v-for="e in EMOJIS" :key="'a' + e" class="emoji-opt" :class="{ active: profile.avatarEmoji === e }" @click="profile.avatarEmoji = e; save()">{{ e }}</button>
        </view>
        <view class="color-row">
          <view v-for="c in COLORS" :key="'ac' + c" class="color-dot" :class="{ active: profile.avatarColor === c }" :style="{ background: c }" @click="profile.avatarColor = c; save()"></view>
        </view>
        <button v-if="profile.avatarEmoji" class="text-btn" @click="profile.avatarEmoji = ''; save()">恢复默认头像</button>
      </view>
      <view class="row between">
        <view class="col">
          <text class="label">记牌器</text>
          <text class="hint">在牌桌中央显示各点数剩余张数</text>
        </view>
        <switch :checked="profile.counter !== false" color="#e7c766" @change="onCounterChange" />
      </view>
      <view class="row between">
        <view class="col">
          <text class="label">音效</text>
          <text class="hint">发牌 / 出牌 / 炸弹 / 结算提示音</text>
        </view>
        <switch :checked="profile.sound !== false" color="#e7c766" @change="onSoundChange" />
      </view>
      <view class="row between">
        <view class="col">
          <text class="label">明牌模式</text>
          <text class="hint">开启后 AI 手牌正面展示（练习用）</text>
        </view>
        <switch :checked="profile.open" color="#e7c766" @change="onOpenChange" />
      </view>
    </view>

    <view class="card">
      <text class="card-title">本机战绩</text>
      <view class="stats">
        <view class="stat"><text class="num">{{ profile.games }}</text><text class="hint">累计局数</text></view>
        <view class="stat"><text class="num">{{ profile.wins }}</text><text class="hint">获胜局数</text></view>
        <view class="stat"><text class="num">{{ profile.points }}</text><text class="hint">累计积分</text></view>
        <view class="stat"><text class="num">{{ fmtCoins }}</text><text class="hint">演示积分</text></view>
      </view>
      <text class="hint">战绩与积分仅保存在本机，不联网上传。</text>
    </view>

    <view class="card">
      <text class="card-title">客服中心（常见问题）</text>
      <view v-for="(f, i) in faq" :key="i" class="faq-item" @click="toggleFaq(i)">
        <view class="faq-q"><text class="faq-mark">Q</text><text>{{ f.q }}</text></view>
        <text v-if="faqOpen === i" class="faq-a">{{ f.a }}</text>
      </view>
      <text v-if="!faq.length" class="hint">需要联网获取客服问题；也可将账户名发给管理员处理充值补单、账号申诉。</text>
    </view>

    <view class="card">
      <text class="card-title">演示说明</text>
      <text class="hint">本应用为离线单机演示：无支付、无广告、无联网对战，不收集任何信息。「充值」仅在本机模拟，积分不可提现兑换。</text>
      <button class="btn danger" @click="resetData">重置本机数据</button>
    </view>
  </view>
</template>

<script>
import account, { DEFAULT_PROFILE } from '@/common/account.js';
import net from '@/common/net.js';

export default {
  data() {
    return {
      profile: { ...DEFAULT_PROFILE, transactions: [] },
      accountName: '',
      serverAddr: '',
      faq: [],
      faqOpen: -1,
      EMOJIS: ['🐉', '🎋', '🌸', '🍁', '🌙', '⭐', '🏔', '🍵', '🎭', '🕊', '🐺', '♠', '♥', '♦', '♣'],
      COLORS: ['#1f7a5c', '#a04a56', '#3a6ea5', '#8a5fb0', '#b07d3a', '#444a55'],
    };
  },
  computed: {
    fmtCoins() {
      return String(this.profile.coins || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },
  },
  onShow() {
    this.load();
  },
  methods: {
    load() {
      const saved = account.getProfile();
      if (!saved) { uni.reLaunch({ url: '/pages/auth/auth' }); return; }
      this.profile = saved;
      this.accountName = account.currentUser() || '';
      this.serverAddr = net.netConfig().server || '';
      net.serverFaq().then(r => { if (r.ok) this.faq = r.faq; });
    },
    saveServer() {
      net.setNet({ server: (this.serverAddr || '').trim().replace(/\/$/, '') });
      uni.showToast({ title: '服务器地址已保存', icon: 'none' });
    },
    goOnline() {
      if (!net.netConfig().server) { uni.showToast({ title: '请先填写服务器地址', icon: 'none' }); return; }
      uni.navigateTo({ url: '/pages/online/online' });
    },
    toggleFaq(i) {
      this.faqOpen = this.faqOpen === i ? -1 : i;
    },
    save() {
      account.saveProfile(this.profile);
    },
    saveProfile() {
      this.profile.name = (this.profile.name || '').trim() || '牌友';
      this.save();
      uni.showToast({ title: '已保存在本机', icon: 'success' });
    },
    onOpenChange(e) {
      this.profile.open = !!e.detail.value;
      this.save();
    },
    onCounterChange(e) {
      this.profile.counter = !!e.detail.value;
      this.save();
    },
    onSoundChange(e) {
      this.profile.sound = !!e.detail.value;
      this.save();
    },
    setStyle(s) {
      this.profile.style = s;
      this.save();
      uni.showToast({ title: { bamboo: '青竹牌背', phoenix: '朱雀牌背', custom: '自定义牌背' }[s] || '已更换', icon: 'none' });
    },
    setBg(b) {
      this.profile.bg = b;
      this.save();
      uni.showToast({ title: { green: '青竹绿', blue: '深海蓝', purple: '暗夜紫' }[b] || '已更换', icon: 'none' });
    },
    resetData() {
      uni.showModal({
        title: '重置本账户数据？',
        content: '当前账户的战绩、积分（恢复 12,000）、昵称与偏好将全部清空，其他账户不受影响，此操作不可撤销。',
        success: res => {
          if (res.confirm) {
            this.profile = { ...DEFAULT_PROFILE, transactions: [] };
            account.saveProfile(this.profile);
            uni.showToast({ title: '已重置', icon: 'success' });
          }
        },
      });
    },
    logout() {
      uni.showModal({
        title: '退出登录？',
        content: '本账户数据已保存在本机，下次登录可继续。',
        success: res => {
          if (res.confirm) {
            account.saveProfile(this.profile);
            account.logout();
            uni.reLaunch({ url: '/pages/auth/auth' });
          }
        },
      });
    },
  },
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx;
  background: #0d3b2e;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.account-card {
  border-color: #e7c76666;
}
.account-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.avatar-preview {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  border: 2rpx solid #e7c766;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34rpx;
}
.card {
  background: #124535;
  border: 2rpx solid #1e5c48;
  border-radius: 20rpx;
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.card-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #f3efe2;
}
.row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.row.between {
  justify-content: space-between;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  flex-shrink: 0;
}
.label {
  font-size: 26rpx;
  color: #f0ead5;
}
.hint {
  font-size: 20rpx;
  color: #9db8a8;
}
.input {
  flex: 1;
  background: #0d3b2e;
  border: 2rpx solid #1e5c48;
  border-radius: 12rpx;
  padding: 14rpx 18rpx;
  color: #f3efe2;
  font-size: 26rpx;
}
.btn {
  border-radius: 36rpx;
  padding: 16rpx 0;
  font-size: 28rpx;
  font-weight: 700;
  text-align: center;
  color: #f3efe2;
  background: #1f7a5c;
  border: 2rpx solid #2a8f6d;
}
.btn.primary {
  background: #e7c766;
  color: #3a2c07;
  border-color: #d9b76e;
}
.btn.danger {
  background: #7d3742;
  border-color: #a04a56;
  color: #ffe4e4;
}
.style-opts {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.style-opt {
  font-size: 24rpx;
  padding: 10rpx 24rpx;
  border-radius: 28rpx;
  color: #f0ead5;
  background: #0d3b2e;
  border: 2rpx solid #1e5c48;
}
.style-opt.active {
  background: #e7c766;
  color: #3a2c07;
  border-color: #d9b76e;
  font-weight: 700;
}
.custom-block {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
  background: #0d3b2e;
  border-radius: 14rpx;
  padding: 18rpx;
}
.emoji-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}
.emoji-opt {
  width: 72rpx;
  height: 72rpx;
  font-size: 38rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #124535;
  border: 2rpx solid #1e5c48;
  border-radius: 12rpx;
}
.emoji-opt.active {
  border-color: #e7c766;
  background: #17493a;
}
.color-row {
  display: flex;
  gap: 14rpx;
  flex-wrap: wrap;
}
.color-dot {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  border: 3rpx solid transparent;
}
.color-dot.active {
  border-color: #e7c766;
  box-shadow: 0 0 10rpx rgba(231, 199, 102, 0.6);
}
.back-preview {
  width: 72rpx;
  height: 100rpx;
  border-radius: 10rpx;
  border: 2rpx solid rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34rpx;
  align-self: center;
}
.avatar-preview {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  border: 2rpx solid #e7c766;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30rpx;
}
.join-row { display: flex; gap: 12rpx; align-items: center; }
.btn.slim { padding: 14rpx 28rpx; }
.faq-item { display: flex; flex-direction: column; gap: 8rpx; border-bottom: 1rpx solid #1e5c48; padding: 12rpx 0; }
.faq-q { display: flex; align-items: center; gap: 12rpx; font-size: 26rpx; color: #f0ead5; }
.faq-mark { color: #e7c766; font-weight: 800; }
.faq-a { font-size: 22rpx; color: #9db8a8; line-height: 1.6; padding-left: 44rpx; }
.stats {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 12rpx;
}
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  min-width: 140rpx;
}
.num {
  font-size: 40rpx;
  font-weight: 800;
  color: #ffe9a8;
}
</style>
