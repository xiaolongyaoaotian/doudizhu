<template>
  <view class="page">
    <view class="head">
      <text class="title">对战记录</text>
      <text class="sub">{{ online ? '服务器最近 30 条' : '本机最近 30 局 · 仅保留 1 个月内' }}</text>
    </view>

    <view v-if="!records.length" class="card"><text class="hint">暂无对战记录，打完一局后这里会显示结果。</text></view>

    <view v-for="(r, i) in records" :key="i" class="card record">
      <view class="row1">
        <text class="result" :class="r.delta >= 0 ? 'win' : 'lose'">{{ r.delta >= 0 ? '胜' : '负' }} {{ r.delta >= 0 ? '+' : '' }}{{ r.delta }}</text>
        <text class="time">{{ fmtTime(r.time) }}</text>
      </view>
      <view class="row2">
        <text class="tag">{{ r.kind === 'room' ? '房间局' : r.kind === 'match' ? '匹配局' : '单机' }}</text>
        <text class="tag">{{ r.landlord === r.you ? '地主' : '农民' }}</text>
        <text class="detail">底分 {{ r.base }} × 加倍 {{ r.mult }}<text v-if="r.bombs"> × 炸弹×{{ r.bombs }}</text><text v-if="r.spring"> × 春天</text></text>
      </view>
      <text class="players">{{ (r.players || []).join(' vs ') }}</text>
    </view>
  </view>
</template>

<script>
import net from '@/common/net.js';

export default {
  data() {
    return { records: [], online: false };
  },
  onShow() {
    this.online = net.isOnline();
    if (this.online) {
      net.serverRecords().then(r => {
        if (r.ok) this.records = r.records || [];
      });
    } else {
      try {
        const p = uni.getStorageSync('ddz-accounts-v1');
        // 离线模式：取当前账户 profile 里的本地记录
        const all = typeof p === 'object' ? p : {};
        const last = all.last;
        const prof = last && all.users && all.users[last] ? all.users[last].profile : null;
        this.records = (prof && prof.records) || [];
      } catch (e) {
        this.records = [];
      }
    }
  },
  methods: {
    fmtTime(t) {
      const d = new Date(t);
      const p = n => String(n).padStart(2, '0');
      return `${d.getMonth() + 1}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },
  },
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #0d3b2e;
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.head { display: flex; flex-direction: column; gap: 6rpx; margin-bottom: 6rpx; }
.title { font-size: 40rpx; font-weight: 800; color: #f3efe2; }
.sub { font-size: 22rpx; color: #9db8a8; }
.card {
  background: #124535;
  border: 2rpx solid #1e5c48;
  border-radius: 16rpx;
  padding: 20rpx;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.row1 { display: flex; justify-content: space-between; align-items: center; }
.result { font-size: 32rpx; font-weight: 800; }
.result.win { color: #7ed6a2; }
.result.lose { color: #e08c8c; }
.time { font-size: 20rpx; color: #9db8a8; }
.row2 { display: flex; align-items: center; gap: 10rpx; flex-wrap: wrap; }
.tag {
  font-size: 18rpx;
  color: #c8d8c0;
  border: 1rpx solid #2a8f6d;
  border-radius: 10rpx;
  padding: 2rpx 12rpx;
}
.detail { font-size: 22rpx; color: #c8d8c0; }
.players { font-size: 20rpx; color: #7ea391; }
.hint { font-size: 22rpx; color: #9db8a8; line-height: 1.6; }
</style>
