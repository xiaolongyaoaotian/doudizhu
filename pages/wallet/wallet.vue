<template>
  <view class="page">
    <view class="balance-card">
      <text class="bc-label">积分余额</text>
      <text class="bc-num">◈ {{ fmt(profile.coins) }}</text>
      <text class="bc-note">仅保存在本机 · 不可提现、不可兑换</text>
      <button class="checkin-btn" :disabled="checkedToday" :class="{ done: checkedToday }" @click="doCheckin">{{ checkedToday ? '今日已签到' : '📅 每日签到 +2000 积分' }}</button>
    </view>

    <view class="card">
      <view class="card-head">
        <text class="card-title">补充积分</text>
        <text class="rate">¥1 = 100 积分</text>
      </view>
      <view class="amounts">
        <button
          v-for="opt in amounts"
          :key="opt.yuan"
          class="amount"
          :class="{ active: rechargeYuan === opt.yuan }"
          @click="rechargeYuan = opt.yuan"
        >
          <text v-if="opt.bonus > 0" class="a-bonus">赠{{ Math.round(opt.bonus * 100) }}%</text>
          <text class="a-yuan">¥{{ opt.yuan }}</text>
          <text class="a-coins">{{ fmt(totalCoins(opt)) }} 积分</text>
          <text v-if="opt.tag" class="a-tag">{{ opt.tag }}</text>
        </button>
      </view>
      <view class="channel-row">
        <button class="channel-btn alipay" @click="qrRecharge('alipay')"><text class="ch-badge">支</text><text class="ch-text">支付宝充值</text></button>
        <button class="channel-btn wechat" @click="qrRecharge('wechat')"><text class="ch-badge">微</text><text class="ch-text">微信充值</text></button>
      </view>
      <text class="tiny-note">弹出二维码，完成支付后点击下方小字确认到账（演示流程，不会产生真实扣款）。</text>
    </view>

    <view class="card records-hero">
      <view class="rh-left">
        <view class="rh-icon">🏆</view>
        <view class="rh-info">
          <text class="card-title">对战记录</text>
          <text class="hint">最近 30 条 · 1 个月内</text>
        </view>
      </view>
      <view class="rh-stats">
        <view class="rh-stat"><text class="rs-num">{{ profile.games }}</text><text class="rs-label">总局</text></view>
        <view class="rh-stat"><text class="rs-num win">{{ winRate }}%</text><text class="rs-label">胜率</text></view>
      </view>
      <button class="pill-btn gold" @click="goRecords">全部记录 <text class="pill-arrow">›</text></button>
    </view>

    <view class="card">
      <view class="card-head">
        <text class="card-title">最近记录</text>
        <button class="pill-btn danger" @click="clearHistory"><text class="pill-x">×</text>清空记录</button>
      </view>
      <view v-if="!profile.transactions || !profile.transactions.length" class="empty">
        <text>还没有记录，充值后会显示在这里。</text>
      </view>
      <view v-for="(tx, i) in profile.transactions" :key="i" class="tx-row">
        <view class="tx-icon" :class="tx.coins >= 0 ? 'gain' : 'cost'"><text>{{ tx.coins >= 0 ? '↑' : '↓' }}</text></view>
        <view class="tx-info">
          <text class="tx-title">{{ tx.title }}</text>
          <text class="tx-date">{{ tx.date }}</text>
        </view>
        <view class="tx-right">
          <text class="tx-amount" :class="{ neg: tx.coins < 0 }">{{ tx.coins >= 0 ? '+' : '−' }}{{ fmt(Math.abs(tx.coins)) }}</text>
          <text class="tx-unit">积分</text>
        </view>
      </view>
    </view>

    <!-- 二维码充值弹窗 -->
    <view v-if="qrInfo" class="qr-mask">
      <view class="qr-panel">
        <view class="qr-head">
          <view class="qr-brand" :class="qrInfo.channel">{{ qrInfo.channel === 'alipay' ? '支付宝' : '微信支付' }}</view>
          <text class="qr-pay">扫码支付 <b>¥{{ qrInfo.yuan }}</b></text>
        </view>
        <view class="qr-frame">
          <view class="qr-corner c1"></view><view class="qr-corner c2"></view>
          <view class="qr-corner c3"></view><view class="qr-corner c4"></view>
          <view class="qr-grid">
            <view v-for="(cell, i) in qrCells" :key="i" class="qr-cell" :class="{ dark: cell }"></view>
          </view>
        </view>
        <view class="qr-breakdown">
          <text class="qb-row">到账积分 <b>{{ fmt(qrBase) }}</b></text>
          <text v-if="qrBonus > 0" class="qb-row gift">赠送 {{ Math.round(qrInfo.bonus * 100) }}% <b>+{{ fmt(qrBonus) }}</b></text>
          <text class="qb-row total">实际到账 <b>{{ fmt(qrInfo.coins) }} 积分</b></text>
        </view>
        <button class="btn primary pay-confirm" @click="confirmQr"><text class="pc-check">✓</text>支付完成 · 确认到账</button>
        <text class="qr-note">* 演示环境不会产生真实扣款，点击上方按钮即视为支付成功</text>
        <button class="text-btn" @click="qrInfo = null">取消</button>
      </view>
    </view>

    <view class="safety">
      <text class="safety-title">ⓘ 关于演示充值</text>
      <text class="safety-body">本应用没有接入任何收款渠道，所有订单仅在本机模拟成功。不存在真实支付、银行绑定或资金账户，积分仅用于练习体验。</text>
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
      rechargeYuan: 30,
      checkedToday: false,
      qrInfo: null,
      online: false,
      qrCells: [],
      qrBase: 0,
      qrBonus: 0,
      amounts: [
        { yuan: 1, bonus: 0 },
        { yuan: 6, bonus: 0.05 },
        { yuan: 30, bonus: 0.10, tag: '推荐' },
        { yuan: 68, bonus: 0.20 },
        { yuan: 128, bonus: 0.30 },
      ],
    };
  },
  computed: {
    winRate() {
      return this.profile.games ? Math.round(this.profile.wins / this.profile.games * 100) : 0;
    },
  },
  onShow() {
    this.load();
    this.online = net.isOnline();
    // 今日是否已签到（离线：profile.checkinDate；在线：服务器返回）
    this.checkedToday = this.profile.checkinDate === this.today();
  },
  methods: {
    load() {
      const saved = account.getProfile();
      if (!saved) { uni.reLaunch({ url: '/pages/auth/auth' }); return; }
      this.profile = saved;
      this.accountName = account.currentUser() || '';
    },
    save() {
      account.saveProfile(this.profile);
    },
    fmt(n) {
      return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },
    totalCoins(opt) {
      return Math.round(opt.yuan * 100 * (1 + opt.bonus));
    },
    recharge() {
      const coins = this.rechargeYuan * 100;
      this.profile.coins += coins;
      this.profile.transactions.unshift({
        title: `演示充值 ¥${this.rechargeYuan}（模拟）`,
        coins,
        date: this.now(),
      });
      this.profile.transactions = this.profile.transactions.slice(0, 30);
      this.save();
      uni.showToast({ title: `模拟成功 +${this.fmt(coins)} 积分，不会真实扣款`, icon: 'none', duration: 2200 });
    },
    clearHistory() {
      this.profile.transactions = [];
      this.save();
      uni.showToast({ title: '记录已清空', icon: 'none' });
    },
    today() {
      const d = new Date();
      const p = n => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
    },
    goRecords() {
      uni.navigateTo({ url: '/pages/records/records' });
    },
    doCheckin() {
      if (this.checkedToday) return;
      if (this.online) {
        net.serverCheckin().then(r => {
          if (r.ok && r.checked) {
            this.checkedToday = true;
            this.profile.points = r.points;
            this.save();
            uni.showToast({ title: '签到成功 +2000 积分', icon: 'none' });
          } else if (r.ok) {
            this.checkedToday = true;
            uni.showToast({ title: '今天已签到', icon: 'none' });
          } else {
            uni.showToast({ title: r.error || '签到失败', icon: 'none' });
          }
        });
      } else {
        this.profile.checkinDate = this.today();
        this.profile.points += 2000;
        this.save();
        this.checkedToday = true;
        uni.showToast({ title: '签到成功 +2000 积分', icon: 'none' });
      }
    },
    // ---- 二维码充值 ----
    qrRecharge(channel) {
      const yuan = this.rechargeYuan;
      if (this.online) {
        net.rechargeCreate(yuan, channel).then(r => {
          if (!r.ok) { uni.showToast({ title: r.error || '下单失败', icon: 'none' }); return; }
          this.showQr({ order: r.order, yuan, channel, coins: r.coins, bonus: r.bonus || 0, seed: r.qrSeed });
        });
      } else {
        const opt = this.amounts.find(a => a.yuan === yuan) || { bonus: 0 };
        const base = yuan * 100;
        const coins = Math.round(base * (1 + opt.bonus));
        this.showQr({ order: 'local-' + Date.now(), yuan, channel, coins, bonus: opt.bonus, seed: 'local:' + yuan + ':' + channel + ':' + Date.now() });
      }
    },
    showQr(info) {
      this.qrInfo = info;
      this.qrBase = Math.round(info.yuan * 100);
      this.qrBonus = info.coins - this.qrBase;
      // 由 seed 生成伪二维码网格（21×21，含三个定位角，确定性哈希分布）
      let h = 0;
      for (const ch of info.seed) h = (h * 131 + ch.charCodeAt(0)) >>> 0;
      const cells = [];
      const N = 21;
      for (let y = 0; y < N; y++) {
        for (let x = 0; x < N; x++) {
          const finder = (x < 7 && y < 7) || (x >= N - 7 && y < 7) || (x < 7 && y >= N - 7);
          let dark;
          if (finder) {
            const lx = x >= N - 7 ? x - (N - 7) : x;
            const ly = y >= N - 7 ? y - (N - 7) : y;
            dark = lx === 0 || lx === 6 || ly === 0 || ly === 6 || (lx >= 2 && lx <= 4 && ly >= 2 && ly <= 4);
          } else {
            h = (h * 1103515245 + 12345) >>> 0;
            dark = (h >>> 16) % 100 < 45;
          }
          cells.push(dark);
        }
      }
      this.qrCells = cells;
    },
    confirmQr() {
      const info = this.qrInfo;
      if (!info) return;
      if (this.online) {
        net.rechargeConfirm(info.order).then(r => {
          if (r.ok) {
            this.profile.points += (r.added || info.coins);   // 充值同步加积分
            this.save();
            this.load();
            uni.showToast({ title: `充值成功 +${this.fmt(r.added || info.coins)} 积分`, icon: 'none', duration: 2500 });
          } else {
            uni.showToast({ title: r.error || '确认失败', icon: 'none' });
          }
          this.qrInfo = null;
        });
      } else {
        this.profile.coins += info.coins;
        this.profile.points += info.coins;   // 充值同步加积分
        this.profile.transactions.unshift({ title: `演示充值 ¥${info.yuan}（${info.channel === 'alipay' ? '支付宝' : '微信'}扫码）`, coins: info.coins, date: this.now() });
        this.profile.transactions = this.profile.transactions.slice(0, 30);
        this.save();
        uni.showToast({ title: `充值成功 +${this.fmt(info.coins)} 积分`, icon: 'none', duration: 2500 });
        this.qrInfo = null;
      }
    },
    now() {
      const d = new Date();
      const p = n => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
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
.balance-card {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 85% 15%, rgba(231, 199, 102, 0.16), transparent 45%),
    radial-gradient(circle at 10% 90%, rgba(42, 143, 109, 0.35), transparent 50%),
    linear-gradient(135deg, #1d6a4f, #124535 70%);
  border: 2rpx solid #e7c76677;
  border-radius: 28rpx;
  padding: 40rpx 32rpx 34rpx;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  align-items: center;
  box-shadow: 0 14rpx 40rpx rgba(0, 0, 0, 0.35);
}
.bc-glow {
  position: absolute;
  top: -40rpx;
  right: -30rpx;
  width: 220rpx;
  height: 220rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 233, 168, 0.25), transparent 65%);
}
.bc-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.bc-tag {
  font-size: 18rpx;
  color: #0d3529;
  background: #e7c766;
  border-radius: 14rpx;
  padding: 2rpx 14rpx;
  font-weight: 700;
}
.bc-label {
  font-size: 24rpx;
  color: #c8d8c0;
}
.bc-num {
  font-size: 76rpx;
  font-weight: 900;
  color: #ffe9a8;
  letter-spacing: 2rpx;
  text-shadow: 0 4rpx 16rpx rgba(255, 215, 110, 0.35);
}
.bc-note {
  font-size: 20rpx;
  color: #9db8a8;
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
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #f3efe2;
}
.rate {
  font-size: 22rpx;
  color: #e7c766;
}
.amounts {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}
.amount {
  position: relative;
  width: 30%;
  flex-grow: 1;
  background: linear-gradient(180deg, #103f31, #0d3b2e);
  border: 2rpx solid #1e5c48;
  border-radius: 18rpx;
  padding: 20rpx 0 16rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  overflow: hidden;
  transition: transform 0.12s, border-color 0.12s;
}
.amount:active { transform: scale(0.96); }
.amount.active {
  border-color: #ffd76e;
  background: linear-gradient(180deg, #1b5a44, #14493a);
  box-shadow: 0 0 0 2rpx rgba(255, 215, 110, 0.25), 0 8rpx 24rpx rgba(0, 0, 0, 0.35);
}
.amount.active .a-yuan { color: #ffe9a8; }
.a-bonus {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 16rpx;
  font-weight: 800;
  color: #3a2c07;
  background: linear-gradient(135deg, #ffe9a8, #f0a93c);
  border-radius: 0 14rpx 0 14rpx;
  padding: 3rpx 12rpx;
}
.a-yuan {
  font-size: 38rpx;
  font-weight: 900;
  color: #f3efe2;
  letter-spacing: 1rpx;
}
.amount.active .a-yuan {
  color: #ffe9a8;
}
.a-coins {
  font-size: 20rpx;
  color: #9db8a8;
}
.a-tag {
  position: absolute;
  top: -14rpx;
  right: -6rpx;
  font-size: 18rpx;
  color: #3a2c07;
  background: #e7c766;
  border-radius: 12rpx;
  padding: 2rpx 12rpx;
  font-weight: 700;
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
.tiny-note {
  font-size: 20rpx;
  color: #9db8a8;
  line-height: 1.5;
}
.pill-btn {
  display: flex;
  align-items: center;
  gap: 6rpx;
  font-size: 22rpx;
  font-weight: 700;
  border-radius: 26rpx;
  padding: 8rpx 22rpx;
  letter-spacing: 1rpx;
}
.pill-btn.gold {
  color: #ffe9a8;
  background: rgba(231, 199, 102, 0.14);
  border: 2rpx solid #e7c76688;
}
.pill-arrow { font-size: 30rpx; font-weight: 900; margin-left: 2rpx; }
.pill-btn.danger {
  color: #f3b8b8;
  background: rgba(125, 55, 66, 0.28);
  border: 2rpx solid #a04a5688;
}
.pill-x { font-size: 28rpx; font-weight: 900; }

.text-btn {
  font-size: 24rpx;
  color: #e7c766;
}
.empty {
  padding: 20rpx 0;
}
.empty text {
  font-size: 24rpx;
  color: #7ea391;
}
.tx-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 14rpx;
  margin-bottom: 10rpx;
  background: rgba(13, 59, 46, 0.45);
  border: 1rpx solid #1e5c4888;
  border-radius: 16rpx;
}
.tx-icon {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: 900;
  flex-shrink: 0;
}
.tx-icon.gain { background: rgba(126, 214, 162, 0.18); color: #7ed6a2; border: 1rpx solid #7ed6a255; }
.tx-icon.cost { background: rgba(224, 140, 140, 0.15); color: #e08c8c; border: 1rpx solid #e08c8c55; }
.tx-info { flex: 1; display: flex; flex-direction: column; gap: 4rpx; min-width: 0; }
.tx-title { font-size: 24rpx; color: #f0ead5; font-weight: 600; }
.tx-date { font-size: 18rpx; color: #7ea391; }
.tx-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2rpx; flex-shrink: 0; }
.tx-amount { font-size: 30rpx; font-weight: 900; color: #7ed6a2; letter-spacing: 1rpx; }
.tx-amount.neg { color: #e08c8c; }
.tx-unit { font-size: 16rpx; color: #7ea391; }

/* 对战记录摘要卡 */
.records-hero {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12rpx;
  border-color: #e7c76644;
}
.rh-left { display: flex; align-items: center; gap: 16rpx; }
.rh-icon {
  width: 72rpx;
  height: 72rpx;
  border-radius: 20rpx;
  background: linear-gradient(160deg, #1d6a4f, #124535);
  border: 1rpx solid #e7c76655;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
}
.rh-info { display: flex; flex-direction: column; gap: 4rpx; }
.rh-stats { display: flex; gap: 24rpx; }
.rh-stat { display: flex; flex-direction: column; align-items: center; gap: 2rpx; }
.rs-num { font-size: 34rpx; font-weight: 900; color: #ffe9a8; }
.rs-num.win { color: #7ed6a2; }
.rs-label { font-size: 18rpx; color: #9db8a8; }
/* 已由卡片化样式取代 */
.checkin-btn {
  background: #e7c766;
  color: #3a2c07;
  border: 2rpx solid #d9b76e;
  border-radius: 32rpx;
  padding: 12rpx 28rpx;
  font-size: 24rpx;
  font-weight: 700;
}
.checkin-btn.done {
  background: #2a5c4a;
  color: #9db8a8;
  border-color: #1e5c48;
}
.channel-row { display: flex; gap: 14rpx; }
.channel-btn {
  flex: 1;
  border-radius: 14rpx;
  padding: 18rpx 0;
  font-size: 26rpx;
  font-weight: 700;
  color: #fff;
}
.channel-btn.alipay {
  background: linear-gradient(180deg, #3b8dff, #1569e6);
  box-shadow: 0 6rpx 18rpx rgba(22, 120, 255, 0.35), inset 0 2rpx 0 rgba(255, 255, 255, 0.25);
}
.channel-btn.wechat {
  background: linear-gradient(180deg, #2ed573, #06ad56);
  box-shadow: 0 6rpx 18rpx rgba(7, 193, 96, 0.35), inset 0 2rpx 0 rgba(255, 255, 255, 0.25);
}
.channel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
}
.ch-badge {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 900;
}
.channel-btn.alipay .ch-badge { color: #1678ff; }
.channel-btn.wechat .ch-badge { color: #07c160; }
.ch-text {
  font-size: 30rpx;
  font-weight: 900;
  letter-spacing: 2rpx;
}
.qr-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 18, 13, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 120;
}
.qr-panel {
  width: 560rpx;
  max-width: 94%;
  background: #fffef8;
  border-radius: 28rpx;
  padding: 34rpx 30rpx 26rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18rpx;
  box-shadow: 0 30rpx 80rpx rgba(0, 0, 0, 0.5);
}
.qr-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}
.qr-brand {
  font-size: 22rpx;
  font-weight: 800;
  color: #fff;
  border-radius: 20rpx;
  padding: 6rpx 24rpx;
}
.qr-brand.alipay { background: #1678ff; box-shadow: 0 6rpx 16rpx rgba(22, 120, 255, 0.35); }
.qr-brand.wechat { background: #07c160; box-shadow: 0 6rpx 16rpx rgba(7, 193, 96, 0.35); }
.qr-pay { font-size: 30rpx; color: #23252b; }
.qr-pay b { font-size: 40rpx; font-weight: 900; color: #b3372e; }
.qr-frame {
  position: relative;
  padding: 18rpx;
}
.qr-corner {
  position: absolute;
  width: 36rpx;
  height: 36rpx;
  border-color: #e7c766;
  border-style: solid;
  border-width: 0;
}
.qr-corner.c1 { top: 0; left: 0; border-top-width: 6rpx; border-left-width: 6rpx; border-top-left-radius: 12rpx; }
.qr-corner.c2 { top: 0; right: 0; border-top-width: 6rpx; border-right-width: 6rpx; border-top-right-radius: 12rpx; }
.qr-corner.c3 { bottom: 0; left: 0; border-bottom-width: 6rpx; border-left-width: 6rpx; border-bottom-left-radius: 12rpx; }
.qr-corner.c4 { bottom: 0; right: 0; border-bottom-width: 6rpx; border-right-width: 6rpx; border-bottom-right-radius: 12rpx; }
.qr-grid {
  display: flex;
  flex-wrap: wrap;
  width: 320rpx;
  overflow: hidden;
}
.qr-breakdown {
  width: 100%;
  background: #f3eeda;
  border-radius: 14rpx;
  padding: 14rpx 20rpx;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.qb-row {
  display: flex;
  justify-content: space-between;
  font-size: 22rpx;
  color: #6b6452;
}
.qb-row b { color: #23252b; }
.qb-row.gift { color: #b06a1d; }
.qb-row.gift b { color: #d97b1e; }
.qb-row.total { font-size: 24rpx; font-weight: 700; color: #23252b; border-top: 1rpx dashed #d8d2b8; padding-top: 8rpx; margin-top: 4rpx; }
.qr-cell { width: 4.762%; padding-top: 4.762%; }
.qr-cell.dark { background: #23252b; }
.qr-cell:not(.dark) { background: #fff; }
.qr-amount { display: none; }
.qr-note { font-size: 18rpx; color: #999; text-align: center; line-height: 1.5; }
.qr-panel .btn.primary {
  background: linear-gradient(180deg, #33dd7a, #06ad56);
  color: #fff;
  border: none;
  width: 100%;
  box-shadow: 0 10rpx 24rpx rgba(7, 193, 96, 0.4), inset 0 2rpx 0 rgba(255, 255, 255, 0.3);
  font-size: 32rpx;
  font-weight: 900;
  letter-spacing: 3rpx;
  padding: 22rpx 0;
  border-radius: 44rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
}
.pc-check {
  font-size: 34rpx;
  font-weight: 900;
}
.qr-panel .text-btn { color: #999; font-size: 24rpx; }
.safety {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  background: #0a2f24;
  border-radius: 16rpx;
  padding: 20rpx;
}
.safety-title {
  font-size: 24rpx;
  font-weight: 700;
  color: #c8d8c0;
}
.safety-body {
  font-size: 20rpx;
  color: #7ea391;
  line-height: 1.6;
}
</style>
