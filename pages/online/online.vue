<template>
  <view class="page">
    <view class="head">
      <text class="title">联机对战</text>
      <text class="sub">{{ server || '未配置服务器' }}</text>
    </view>

    <view class="card" v-if="!matched">
      <text class="card-title">随机匹配</text>
      <text class="hint">与在线玩家匹配；30 秒内没有其他玩家，自动分配 AI 补位。</text>
      <button class="btn primary" :disabled="matching" :class="{ disabled: matching }" @click="startMatch">
        {{ matching ? `匹配中… ${wait}s（取消）` : '开始匹配' }}
      </button>
    </view>

    <view class="card" v-if="!matched">
      <text class="card-title">好友对战（房间）</text>
      <text class="hint">创建房间给好友输入房号加入；最多 3 人，未满员可由房主开始（补 AI），支持观战。</text>
      <button class="btn" @click="createRoom">创建房间</button>
      <view class="join-row">
        <input class="input" v-model="joinId" type="number" maxlength="6" placeholder="输入 6 位房号" />
        <button class="btn" @click="joinRoom">加入</button>
        <button class="btn ghost" @click="spectateRoom">观战</button>
      </view>
      <text v-if="roomInfo" class="hint">房间 {{ roomInfo.id }}：{{ (roomInfo.players || []).map(p => p.name).join('、') || '等待玩家…' }}{{ roomInfo.spectators && roomInfo.spectators.length ? '（观战 ' + roomInfo.spectators.length + '）' : '' }}</text>
      <button v-if="isHost && roomInfo" class="btn primary" @click="startRoom">开始对局（缺位补 AI）</button>
    </view>

    <view class="card" v-if="matched">
      <text class="card-title">对局进行中</text>
      <text class="hint">{{ onlineGameId ? '已连接对局：' + onlineGameId : '等待分配…' }}</text>
      <button class="btn primary" @click="enterGame">进入牌桌</button>
      <button class="btn ghost" @click="leave">离开</button>
    </view>

    <text v-if="errMsg" class="err">{{ errMsg }}</text>
    <button class="link" @click="back">返回大厅</button>
  </view>
</template>

<script>
import net from '@/common/net.js';

export default {
  data() {
    return { matching: false, wait: 0, joinId: '', errMsg: '', matched: false, onlineGameId: '', roomInfo: null, isHost: false, pollTimer: null, server: '' };
  },
  onLoad() {
    this.server = net.netConfig().server || '';
    // 断线重连：启动时检查是否有进行中的对局
    net.matchStatus().then(r => {
      if (r.ok && r.matched) {
        this.matched = true;
        this.onlineGameId = r.gameId;
        uni.showToast({ title: '检测到进行中的对局，已重连', icon: 'none', duration: 2500 });
      }
    });
  },
  onUnload() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },
  methods: {
    back() { uni.navigateBack(); },
    fail(e) { this.errMsg = e.error || e.message || '网络错误'; },
    // ---- 匹配 ----
    startMatch() {
      if (this.matching) {  // 点击正在匹配 = 取消
        clearInterval(this.pollTimer);
        this.matching = false;
        net.matchCancel();
        return;
      }
      this.errMsg = '';
      this.matching = true;
      this.wait = 0;
      net.matchJoin().then(r => {
        if (!r.ok) { this.fail(r); this.matching = false; return; }
        if (r.matched) { this.onMatched(r); return; }
        this.pollTimer = setInterval(() => {
          this.wait++;
          net.matchStatus().then(s => {
            if (s.ok && s.matched) { clearInterval(this.pollTimer); this.matching = true; this.onMatched(s); }
          });
        }, 1000);
        // 30 秒后由服务端自动补 AI（matchJoin 会返回 matched），这里再触发一次 join 查询结果
        setTimeout(() => {
          if (this.matching) net.matchJoin().then(r2 => { if (r2.ok && r2.matched) { clearInterval(this.pollTimer); this.onMatched(r2); } });
        }, (30 - this.wait) * 1000 + 500);
      });
    },
    onMatched(r) {
      this.matching = false;
      this.matched = true;
      this.onlineGameId = r.gameId;
      uni.showToast({ title: '匹配成功！', icon: 'success' });
    },
    // ---- 房间 ----
    createRoom() {
      this.errMsg = '';
      net.roomCreate().then(r => {
        if (!r.ok) { this.fail(r); return; }
        this.isHost = true;
        this.pollRoom(r.roomId);
      });
    },
    joinRoom() {
      if (!this.joinId || this.joinId.length !== 6) { this.errMsg = '请输入 6 位房号'; return; }
      this.errMsg = '';
      net.roomJoin(this.joinId).then(r => {
        if (!r.ok) { this.fail(r); return; }
        this.isHost = false;
        this.pollRoom(this.joinId);
        uni.showToast({ title: r.rejoin ? '已回到房间' : '加入成功', icon: 'none' });
      });
    },
    spectateRoom() {
      if (!this.joinId || this.joinId.length !== 6) { this.errMsg = '请输入 6 位房号'; return; }
      net.roomSpectate(this.joinId).then(r => {
        if (!r.ok) { this.fail(r); return; }
        uni.showToast({ title: '进入观战', icon: 'none' });
        this.pollRoom(this.joinId);
      });
    },
    pollRoom(roomId) {
      if (this.pollTimer) clearInterval(this.pollTimer);
      this.pollTimer = setInterval(() => {
        net.roomState(roomId).then(r => {
          if (!r.ok) { this.fail(r); return; }
          if (r.game) {
            this.matched = true;
            this.onlineGameId = r.game.gameId;
            clearInterval(this.pollTimer);
            uni.showToast({ title: '对局开始！', icon: 'success' });
          } else {
            this.roomInfo = r.room;
          }
        });
      }, 1500);
    },
    startRoom() {
      net.roomStart(this.roomInfo.id).then(r => {
        if (!r.ok) { this.fail(r); return; }
        this.matched = true;
        this.onlineGameId = r.gameId;
      });
    },
    // ---- 进入对局（牌桌页通过存储的 gameId 轮询） ----
    enterGame() {
      uni.setStorageSync('ddz-online-game', { gameId: this.onlineGameId });
      uni.redirectTo({ url: '/pages/index/index?online=1' });
    },
    leave() {
      if (this.pollTimer) clearInterval(this.pollTimer);
      if (this.onlineGameId) net.gameQuit(this.onlineGameId);
      if (this.roomInfo) net.roomLeave(this.roomInfo.id);
      this.matched = false;
      this.onlineGameId = '';
      this.roomInfo = null;
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
  gap: 20rpx;
}
.head { display: flex; flex-direction: column; gap: 6rpx; }
.title { font-size: 40rpx; font-weight: 800; color: #f3efe2; }
.sub { font-size: 22rpx; color: #9db8a8; }
.card {
  background: #124535;
  border: 2rpx solid #1e5c48;
  border-radius: 20rpx;
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}
.card-title { font-size: 30rpx; font-weight: 700; color: #f3efe2; }
.hint { font-size: 20rpx; color: #9db8a8; line-height: 1.5; }
.btn {
  border-radius: 40rpx;
  padding: 16rpx 0;
  font-size: 28rpx;
  font-weight: 700;
  text-align: center;
  color: #f3efe2;
  background: #1f7a5c;
  border: 2rpx solid #2a8f6d;
}
.btn.primary { background: #e7c766; color: #3a2c07; border-color: #d9b76e; }
.btn.ghost { background: transparent; }
.btn.disabled { opacity: 0.6; }
.join-row { display: flex; gap: 12rpx; align-items: center; }
.join-row .btn { padding: 12rpx 28rpx; }
.input {
  flex: 1;
  background: #0d3b2e;
  border: 2rpx solid #1e5c48;
  border-radius: 12rpx;
  padding: 14rpx 18rpx;
  color: #f3efe2;
  font-size: 26rpx;
}
.err { font-size: 24rpx; color: #f3b8b8; }
.link { font-size: 24rpx; color: #9db8a8; padding: 10rpx; }
</style>
