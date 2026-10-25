<template>
  <view class="page" :class="{ 'win-mode': viewMode === 'win' && !isFullscreen }">
    <!-- 顶栏 -->
    <view class="topbar" :style="{ paddingTop: statusBarPx + 'px' }">
      <view class="topbar-l">
        <text class="title">牌友斗地主</text>
        <text class="sub">{{ accountName ? accountName + ' · 离线单机' : '离线单机' }}</text>
      </view>
      <view class="topbar-r">
        <button class="coin-pill" @click="goWallet"><text class="coin-ico">◈</text><text>{{ fmtCoins }}</text></button>
        <text class="points-pill">⚔ {{ profile.points }}</text>
        <button class="mini-btn emoji-btn" @click="toggleEmotePanel">😉</button>
        <button class="mini-btn" :class="{ gold: onlineMode ? (snap && snap.openSeats && snap.openSeats.includes(0)) : profile.open }" @click="toggleOpen">{{ onlineMode ? (snap && snap.openSeats && snap.openSeats.includes(0) ? '已明牌' : '明牌') : (profile.open ? '已明牌' : '明牌') }}</button>
        <view class="robot-wrap">
          <text v-if="robotShow" class="robot-anim">🤖</text>
          <button v-if="!onlineMode" class="mini-btn" :class="{ gold: snap && snap.trust }" @click="toggleTrust">{{ snap && snap.trust ? '托管中' : '托管' }}</button>
          <button v-else class="mini-btn disabled" disabled>联机中</button>
        </view>
        <button class="mini-btn wide-only" @click="toggleViewMode">{{ viewMode === 'win' ? '窗口' : '全屏' }}</button>
        <button class="mini-btn wide-only" @click="toggleFullscreen">{{ isFullscreen ? '⤢' : '⛶' }}</button>
        <button class="mini-btn" @click="confirmRestart">重开</button>
        <button class="mini-btn" @click="goSettings">设置</button>
      </view>
    </view>

    <text class="rotate-tip">↻ 横屏体验更佳</text>

    <!-- 记牌器（收起时的小按钮） -->
    <button v-if="showCounter && snap && snap.started && !counterOpen" class="counter-collapsed" @click="counterOpen = true">记牌器</button>

    <!-- 牌桌（对局结束后进入冻结态） -->
    <view class="table" :class="['bg-' + (profile.bg || 'green'), 'back-' + (profile.style || 'bamboo'), snap && snap.finished ? 'table-over' : '']" :style="isCustomBack ? { '--back-color': profile.backColor } : {}">
      <view class="table-glow"></view>

      <!-- 对手：左上 -->
      <view class="opp opp-a">
        <view class="opp-info">
          <view class="avatar" @click.stop="openSeatProfile(1)" :style="{ background: seat(1) ? seat(1).color : '' }"><text>{{ seat(1) ? seat(1).avatar : '竹' }}</text></view>
          <text class="opp-name">{{ seat(1) ? seat(1).name : '竹影客' }}</text>
          <text v-if="seat(1)" class="level-tag" :class="seat(1).level">{{ levelBadge(seat(1).level) }}</text>
          <text v-if="showRole(1)" class="role-tag">地主</text>
          <text class="opp-count">{{ snap ? snap.handCounts[1] : 17 }}张</text>
          <text v-if="snap && snap.thinking === 1" class="thinking">…</text>
        </view>
        <text v-if="emotes[1]" class="emote-bubble seat-a">{{ emotes[1] }}</text>
        <view class="opp-cards" :style="{ '--step': stackStep(Math.min(snap ? snap.handCounts[1] : 17, 6)) + 'rpx' }">
          <template v-if="revealOpp(1)">
            <view v-for="(c, i) in snap.hands[1]" :key="dealId + '-o1-' + c.id" class="stack-card deal flipped" :class="{ red: isRed(c) }" :style="{ animationDelay: (i * 30) + 'ms', zIndex: i + 1 }">
              <view class="sc-face"><text class="sc-rank">{{ faceLabel(c) }}</text><text v-if="!c.joker" class="sc-suit">{{ c.suit }}</text></view>
            </view>
          </template>
          <template v-else>
            <view v-for="i in Math.min(snap ? snap.handCounts[1] : 17, 6)" :key="dealId + '-b1-' + i" class="stack-card deal back" :style="{ zIndex: i }">
              <view class="sc-back"><text v-if="isCustomBack" class="back-face">{{ profile.backEmoji }}</text></view>
            </view>
          </template>
        </view>
      </view>

      <!-- 对手：右上 -->
      <view class="opp opp-b">
        <view class="opp-info">
          <view class="avatar rose" @click.stop="openSeatProfile(2)" :style="{ background: seat(2) ? seat(2).color : '' }"><text>{{ seat(2) ? seat(2).avatar : '梅' }}</text></view>
          <text class="opp-name">{{ seat(2) ? seat(2).name : '梅子青' }}</text>
          <text v-if="seat(2)" class="level-tag" :class="seat(2).level">{{ levelBadge(seat(2).level) }}</text>
          <text v-if="showRole(2)" class="role-tag">地主</text>
          <text class="opp-count">{{ snap ? snap.handCounts[2] : 17 }}张</text>
          <text v-if="snap && snap.thinking === 2" class="thinking">…</text>
        </view>
        <text v-if="emotes[2]" class="emote-bubble seat-b">{{ emotes[2] }}</text>
        <view class="opp-cards right" :style="{ '--step': stackStep(Math.min(snap ? snap.handCounts[2] : 17, 6)) + 'rpx' }">
          <template v-if="revealOpp(2)">
            <view v-for="(c, i) in snap.hands[2]" :key="dealId + '-o2-' + c.id" class="stack-card deal flipped" :class="{ red: isRed(c) }" :style="{ animationDelay: (i * 30) + 'ms', zIndex: i + 1 }">
              <view class="sc-face"><text class="sc-rank">{{ faceLabel(c) }}</text><text v-if="!c.joker" class="sc-suit">{{ c.suit }}</text></view>
            </view>
          </template>
          <template v-else>
            <view v-for="i in Math.min(snap ? snap.handCounts[2] : 17, 6)" :key="dealId + '-b2-' + i" class="stack-card deal back" :style="{ zIndex: i }">
              <view class="sc-back"><text v-if="isCustomBack" class="back-face">{{ profile.backEmoji }}</text></view>
            </view>
          </template>
        </view>
      </view>

      <!-- 对手出牌区：各自手牌前方（朝中央），竞品布局 -->
      <view class="play-zone play-l">
        <template v-if="snap && snap.shown && snap.shown[1]">
          <template v-if="!snap.shown[1].pass">
            <view v-for="c in snap.shown[1].cards" :key="'s1' + c.id" class="shown-card side" :class="isRed(c) ? 'red' : ''">
              <view class="sc-rot"><text class="sc-rank">{{ faceLabel(c) }}</text><text v-if="!c.joker" class="sc-suit">{{ c.suit }}</text></view>
            </view>
          </template>
          <text v-else class="pass-pill">不出</text>
        </template>
      </view>
      <view class="play-zone play-r">
        <template v-if="snap && snap.shown && snap.shown[2]">
          <template v-if="!snap.shown[2].pass">
            <view v-for="c in snap.shown[2].cards" :key="'s2' + c.id" class="shown-card side" :class="isRed(c) ? 'red' : ''">
              <view class="sc-rot"><text class="sc-rank">{{ faceLabel(c) }}</text><text v-if="!c.joker" class="sc-suit">{{ c.suit }}</text></view>
            </view>
          </template>
          <text v-else class="pass-pill">不出</text>
        </template>
      </view>

      <!-- 中央：记牌器 + 底牌 + 我的出牌 + 轮次 -->
      <view class="center">
        <view v-if="showCounter && counterOpen && snap && snap.started" class="counter" @click="counterOpen = false">
          <text class="counter-title">记</text>
          <view v-for="c in cardCounter" :key="c.rank" class="counter-cell" :class="{ zero: c.left === 0 }">
            <text class="cc-label">{{ c.label }}</text>
            <text class="cc-num">{{ c.left }}</text>
          </view>
        </view>
        <button v-else-if="showCounter && snap && snap.started" class="counter-mini" @click="counterOpen = true">记牌器 ▾</button>

        <view class="kitty">
          <template v-if="snap && snap.started && snap.phase !== 'bid'">
            <view v-for="c in snap.kitty" :key="dealId + '-k-' + c.id" class="kitty-card" :class="isRed(c) ? 'red' : ''">
              <text class="kc-rank">{{ faceLabel(c) }}</text>
              <text v-if="!c.joker" class="kc-suit">{{ c.suit }}</text>
            </view>
          </template>
          <template v-else>
            <view v-for="i in 3" :key="dealId + '-kb-' + i" class="kitty-card back deal" :class="{ custom: isCustomBack }" :style="{ animationDelay: (600 + i * 90) + 'ms' }">
              <text v-if="isCustomBack" class="back-face">{{ profile.backEmoji }}</text>
            </view>
          </template>
          <text class="kitty-label">底牌</text>
        </view>

        <text class="round">{{ snap ? snap.roundText : '准备好了吗？' }}</text>
        <text v-if="snap && snap.started && snap.phase !== 'bid'" class="mult">底分 {{ snap.base }} · 倍数 ×{{ snap.points / snap.base }}<text v-if="snap.trust"> · 托管中</text></text>
        <view class="my-shown">
          <template v-if="snap && snap.shown && snap.shown[0]">
            <template v-if="!snap.shown[0].pass">
              <view v-for="c in snap.shown[0].cards" :key="'s0' + c.id" class="shown-card mine" :class="isRed(c) ? 'red' : ''">
                <text class="sc-rank">{{ faceLabel(c) }}</text>
                <text v-if="!c.joker" class="sc-suit">{{ c.suit }}</text>
              </view>
            </template>
            <text v-else class="pass-pill">你不出</text>
          </template>
          <text v-else-if="snap && snap.started" class="placeholder">等待出牌</text>
          <text v-else class="placeholder">点「开始游戏」发牌</text>
        </view>
      </view>
      <view class="room-bar" v-if="!onlineMode && (!snap || snap.phase === 'idle' || snap.phase === 'over')">
        <button v-for="r in ROOMS" :key="r.id" class="room-chip" :class="{ on: roomId === r.id, locked: roomLocked(r) }" @click="pickRoom(r)">
          <b>{{ r.name }}</b><small>{{ fmt(r.base) }}底</small><small v-if="roomLocked(r)" class="lock">🔒</small>
        </button>
      </view>
      <view class="actions in-table">
        <text v-if="hintMsg" class="hint-msg">{{ hintMsg }}</text>
        <template v-if="dealing">
          <button class="btn disabled" disabled>发牌中…</button>
        </template>
        <template v-else-if="!snap || snap.phase === 'idle' || snap.phase === 'over'">
          <button class="btn primary" @click="startGame">开始游戏</button>
        </template>
        <template v-else-if="snap.phase === 'bid'">
          <template v-if="snap.current === 0 && !snap.trust">
            <button v-for="v in bidOptions" :key="v" class="btn" @click="bid(v)">{{ v }} 分</button>
            <button class="btn primary" @click="bid(0)">不抢</button>
          </template>
          <button v-else class="btn disabled" disabled>{{ snap.trust && snap.current === 0 ? '托管叫分中…' : '好友叫分中…' }}</button>
        </template>
        <template v-else-if="snap.phase === 'double'">
          <template v-if="snap.current === 0 && !snap.trust">
            <button class="btn" @click="doubling(1)">不加倍</button>
            <button class="btn" @click="doubling(2)">加倍 ×2</button>
            <button v-if="snap.landlord === 0" class="btn primary" @click="doubling(4)">加倍 ×4</button>
          </template>
          <button v-else class="btn disabled" disabled>{{ snap.trust && snap.current === 0 ? '托管加倍中…' : '好友加倍中…' }}</button>
        </template>
        <template v-else-if="snap.phase === 'play'">
          <template v-if="snap.current === 0 && !snap.trust">
            <button v-if="canPass" class="btn" @click="pass">不出</button>
            <button class="btn" @click="hint">提示</button>
            <button class="btn primary" :disabled="!selected.length" :class="{ disabled: !selected.length }" @click="play">出牌</button>
          </template>
          <button v-else class="btn disabled" disabled>{{ snap.trust && snap.current === 0 ? '托管出牌中…' : '好友出牌中…' }}</button>
        </template>
      </view>

      <view class="hand">
        <view
          v-for="(c, i) in myHand"
          :key="dealId + '-' + c.id"
          class="hand-card deal"
          :class="[isRed(c) ? 'red' : '', isSelected(c) ? 'sel' : '']"
          :style="{ animationDelay: (i * 40) + 'ms' }"
          @click="toggleCard(c)"
        >
          <text class="hc-rank">{{ faceLabel(c) }}</text>
          <text v-if="!c.joker" class="hc-suit">{{ c.suit }}</text>
          <text v-else class="hc-suit joker">JOKER</text>
        </view>
        <text v-if="!myHand.length" class="placeholder">暂无手牌</text>
      </view>
    </view>

    <view class="me-head" @click="openProfile">
        <view class="avatar me-avatar" :style="{ background: profile.avatarColor || '#1f7a5c' }"><text>{{ profile.avatarEmoji || '你' }}</text></view>
        <view class="me-col">
          <text v-if="showRole(0)" class="role-tag">地主</text>
          <text class="opp-count">{{ snap ? snap.handCounts[0] : 0 }}张<text v-if="snap && snap.thinking === 0 && !snap.trust"> · 轮到你</text></text>
        </view>
        <text v-if="emotes[0]" class="emote-bubble seat-me">{{ emotes[0] }}</text>
      </view>

    <!-- 对手简介弹窗 -->
    <view v-if="seatInfo" class="profile-mask" @click="seatInfo = null">
      <view class="profile-panel" @click.stop>
        <view class="pf-head">
          <view class="avatar pf-avatar" :style="{ background: seatInfo.color }"><text>{{ seatInfo.avatar }}</text></view>
          <view class="pf-info">
            <text class="pf-name">{{ seatInfo.name }}</text>
            <text class="pf-sub">{{ seatInfo.isHuman ? '在线玩家' : 'AI · ' + (levelLabel(seatInfo.level)) }}</text>
          </view>
        </view>
        <view class="pf-stats">
          <view class="pf-stat"><text class="pf-num">{{ seatStat(seatInfo.seat).games }}</text><text class="pf-label">对局数</text></view>
          <view class="pf-stat"><text class="pf-num">{{ seatStat(seatInfo.seat).rate }}%</text><text class="pf-label">胜率</text></view>
          <view class="pf-stat"><text class="pf-num">{{ seatStat(seatInfo.seat).points }}</text><text class="pf-label">积分</text></view>
          <view class="pf-stat"><text class="pf-num">{{ snap ? snap.handCounts[seatInfo.seat] : '-' }}</text><text class="pf-label">剩余</text></view>
        </view>
        <button class="btn ghost" @click="seatInfo = null">关闭</button>
      </view>
    </view>

    <!-- 个人简介弹窗 -->
    <view v-if="profileOpen" class="profile-mask" @click="profileOpen = false">
      <view class="profile-panel" @click.stop>
        <view class="pf-head">
          <view class="avatar pf-avatar" :style="{ background: profile.avatarColor || '#1f7a5c' }"><text>{{ profile.avatarEmoji || '你' }}</text></view>
          <view class="pf-info">
            <text class="pf-name">{{ profile.name || '你' }}</text>
            <text class="pf-sub">{{ accountName ? '账户：' + accountName : '本地游客' }}</text>
          </view>
        </view>
        <view class="pf-stats">
          <view class="pf-stat"><text class="pf-num">{{ profile.games }}</text><text class="pf-label">对局数</text></view>
          <view class="pf-stat"><text class="pf-num">{{ winRate }}%</text><text class="pf-label">胜率</text></view>
          <view class="pf-stat"><text class="pf-num">{{ profile.points }}</text><text class="pf-label">积分</text></view>
          <view class="pf-stat"><text class="pf-num">{{ fmtCoins }}</text><text class="pf-label">积分</text></view>
        </view>
        <view v-if="profile.coins < 200" class="pf-recharge">
          <text class="pf-warn">余额已输光，是否充值？</text>
          <button class="btn primary" @click="goWallet">去充值</button>
        </view>
        <button class="btn ghost" @click="profileOpen = false">关闭</button>
      </view>
    </view>

    <!-- 表情面板 -->
    <view v-if="emoteOpen" class="emote-mask" @click="emoteOpen = false">
      <view class="emote-panel" @click.stop>
        <view v-for="e in EMOTE_SET" :key="e" class="emote-item" @click="sendEmote(e)">{{ e }}</view>
      </view>
    </view>

    <!-- 结算界面 -->
    <view v-if="finishInfo" class="settle-mask">
      <view class="settle-panel" :class="finishInfo.userWon ? 'win' : 'lose'">
        <view class="settle-banner">
          <text class="sb-title">{{ finishInfo.title }}</text>
          <text v-if="finishInfo.spring" class="sb-tag">春天 ×2</text>
          <text v-else-if="finishInfo.antiSpring" class="sb-tag">反春 ×2</text>
        </view>
        <view class="settle-formula">
          <text>底分 {{ snap.base }} × 加倍 {{ snap.multTotal }} × 炸弹 ×{{ Math.pow(2, snap.bombCount) }}{{ finishInfo.springMult > 1 ? ' × 春天 ×2' : '' }} = <b>{{ finishInfo.pts }}</b> 分</text>
        </view>
        <view class="settle-rows">
          <view v-for="p in [0, 1, 2]" :key="p" class="settle-row" :class="{ me: p === 0 }">
            <view class="sr-left">
              <view class="avatar" :class="{ rose: p === 2 }">{{ ['你', '竹', '梅'][p] }}</view>
              <view class="sr-info">
                <text class="sr-name">{{ playerName(p) }}</text>
                <text class="sr-role">{{ snap.landlord === p ? '地主' : '农民' }} · 剩 {{ snap.handCounts[p] }} 张</text>
              </view>
            </view>
            <text class="sr-delta" :class="finishInfo.delta[p] >= 0 ? 'plus' : 'minus'">{{ finishInfo.delta[p] >= 0 ? '+' : '' }}{{ finishInfo.delta[p] }}</text>
          </view>
        </view>
        <view class="settle-actions">
          <button class="btn" @click="finishInfo = null">看牌桌</button>
          <button class="btn primary" @click="startSettleNext">再来一局</button>
        </view>
      </view>
    </view>

    <text class="foot-note">单机演示 · 输赢只计本机积分 · 无支付无联网</text>
  </view>
</template>

<script>
import { DDZGame, label, getCombo, rankShort } from '@/common/ddz-engine.js';
import { sfx, setSoundEnabled } from '@/common/sound.js';
import account, { DEFAULT_PROFILE } from '@/common/account.js';
import net from '@/common/net.js';
import { findResponse, bestLead } from '@/common/ddz-engine.js';

export default {
  data() {
    return {
      snap: null,
      selected: [],
      profile: { ...DEFAULT_PROFILE, transactions: [] },
      game: null,
      statusBarPx: 24,
      dealing: false,
      dealId: 0,
      dealTimer: null,
      hintMsg: '',
      hintTimer: null,
      finishInfo: null,   // 结算面板数据
      accountName: '',
      countdown: 0,       // 轮到玩家的倒计时（秒）
      cdTimer: null,
      counterOpen: true,  // 记牌器展开
      emoteOpen: false,   // 表情面板
      emotes: { 0: '', 1: '', 2: '' },  // 各座位当前表情气泡
      emoteTimer: null,
      lastPlayKey: '',    // 检测 AI 出牌以随机回应表情
      onlineMode: false,
      onlineGameId: '',
      onlineTimer: null,
      robotShow: false,
      profileOpen: false,
      seatInfo: null,
      aiStats: { 1: { games: 0, wins: 0, points: 0 }, 2: { games: 0, wins: 0, points: 0 } },
      ROOMS: [
        { id: 100, name: '小白场', base: 100 },
        { id: 1000, name: '初级场', base: 1000 },
        { id: 10000, name: '中级场', base: 10000 },
        { id: 100000, name: '高级场', base: 100000 },
      ],
      roomId: 100,
      viewMode: 'full',     // 桌面端：full 全屏铺满 / win 窗口模式
      isFullscreen: false,
      winW: 750,
      EMOTE_SET: ['👍', '😂', '😅', '😡', '😭', '🙏', '🎉', '🤔', '💪', '👋'],
    };
  },
  computed: {
    myHand() {
      return this.snap ? this.snap.hands[0] : [];
    },
    bidOptions() {
      if (!this.snap) return [];
      return [1, 2, 3].filter(v => v > this.snap.maxBid);
    },
    canPass() {
      return !!(this.snap && this.snap.last && this.snap.last.player !== 0);
    },
    fmtCoins() {
      return String(this.profile.coins || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },
    winRate() {
      return this.profile.games ? Math.round(this.profile.wins / this.profile.games * 100) : 0;
    },
    showCounter() {
      return this.profile.counter !== false;
    },
    // 选中牌的牌型实时识别
    selComboText() {
      if (!this.selected.length || !this.snap || this.snap.phase !== 'play') return '';
      const picked = this.myHand.filter(c => this.selected.includes(c.id));
      const combo = getCombo(picked);
      return combo ? combo.text : '不成牌型';
    },
    // 记牌器：场上未知的牌（总 54 − 我的手牌 − 已打出 − 已亮底牌）
    isCustomBack() {
      return this.profile.style === 'custom';
    },
    cardCounter() {
      if (!this.snap || !this.snap.started) return [];
      const mine = {};
      this.snap.hands[0].forEach(c => { mine[c.rank] = (mine[c.rank] || 0) + 1; });
      const played = {};
      (this.snap.played || []).forEach(c => { played[c.rank] = (played[c.rank] || 0) + 1; });
      const kittyShown = ['double', 'play', 'over'].includes(this.snap.phase) && this.snap.started;
      const kitty = {};
      if (kittyShown) this.snap.kitty.forEach(c => { kitty[c.rank] = (kitty[c.rank] || 0) + 1; });
      const out = [];
      for (let r = 3; r <= 15; r++) {
        out.push({ rank: r, label: rankShort(r), left: Math.max(0, 4 - (mine[r] || 0) - (played[r] || 0) - (kitty[r] || 0)) });
      }
      out.push({ rank: 16, label: '王', left: Math.max(0, 2 - (mine[16] || 0) - (played[16] || 0) - (kitty[16] || 0)) });
      return out;
    },
  },
  watch: {
    snap(s) {
      this.tickTurn(s);
      this.aiEmoteReact(s);
    },
  },
  onLoad(opts) {
    const info = uni.getSystemInfoSync();
    this.winW = info.windowWidth || 750;
    this.statusBarPx = info.platform === 'app' ? (info.statusBarHeight || 0) : 0;
    if (!this.loadProfile()) return;   // 未登录：跳账户页，不初始化对局
    setSoundEnabled(this.profile.sound !== false);
    net.reportInstall(this.accountName);   // 安装量统计
    // 联机模式：从联机大厅进入
    if (opts && opts.online) {
      const saved = uni.getStorageSync('ddz-online-game');
      this.onlineMode = true;
      this.onlineGameId = saved && saved.gameId;
      this.startOnlinePolling();
      return;
    }
    this.game = new DDZGame({
      onChange: snap => { this.snap = snap; },
      onEvent: e => this.handleEvent(e),
      persistStats: inc => this.applyStats(inc),
    });
    this.snap = this.game.snapshot();
  },
  onShow() {
    this.loadProfile();
    setSoundEnabled(this.profile.sound !== false);
    this.viewMode = this.profile.viewMode || 'full';
  },
  mounted() {
    // 全屏状态监听（Esc 退出时同步按钮）
    if (typeof document !== 'undefined') {
      document.addEventListener('fullscreenchange', () => { this.isFullscreen = !!document.fullscreenElement; });
    }
  },
  onUnload() {
    if (this.dealTimer) clearTimeout(this.dealTimer);
    if (this.hintTimer) clearTimeout(this.hintTimer);
    if (this.cdTimer) clearInterval(this.cdTimer);
    if (this.game) this.game.destroy();
  },
  methods: {
    loadProfile() {
      const saved = account.getProfile();
      if (!saved) {  // 未登录 → 去账户页
        uni.reLaunch({ url: '/pages/auth/auth' });
        return false;
      }
      this.profile = saved;
      this.accountName = account.currentUser() || '';
      return true;
    },
    saveProfile() {
      account.saveProfile(this.profile);
    },
    applyStats(inc) {
      this.profile.games += inc.games;
      this.profile.wins += inc.win;
      this.profile.points += inc.points;   // 历史总积分（成长值）
      this.profile.coins += inc.points;    // 钱包余额 = 对局筹码，直接结算
      // 本地对战记录：最多 30 条 / 1 个月
      if (!this.profile.records) this.profile.records = [];
      const s = this.snap;
      const cutoff = Date.now() - 30 * 86400 * 1000;
      this.profile.records.unshift({
        time: Date.now(), kind: 'local', base: s.base, mult: s.mults.reduce((a, b) => a * b, 1),
        bombs: s.bombCount, spring: !!(s.springTag), landlord: s.landlord, you: 0,
        delta: inc.points, winner: inc.win ? s.landlord : (s.landlord + 1) % 3,
        players: ['你', this.seat(1) ? this.seat(1).name : '竹影客', this.seat(2) ? this.seat(2).name : '梅子青'],
      });
      this.profile.records = this.profile.records
        .filter(r => r.time >= cutoff)
        .slice(0, 30);
      this.saveProfile();
    },
    handleEvent(e) {
      if (e.type === 'info') {
        this.flashHint(`${e.title}：${e.message}`);
        uni.showToast({ title: `${e.title}：${e.message}`, icon: 'none', duration: 1800 });
      } else if (e.type === 'finish') {
        this.finishInfo = e;   // 结算面板（替代小弹窗）
        this.aiStats[1].games++; this.aiStats[1].wins += e.delta[1] > 0 ? 1 : 0; this.aiStats[1].points += e.delta[1];
        this.aiStats[2].games++; this.aiStats[2].wins += e.delta[2] > 0 ? 1 : 0; this.aiStats[2].points += e.delta[2];
        if (this.profile.coins < 200) {
          setTimeout(() => {
            if (!this.snap.finished && this.snap.phase !== 'idle' && this.snap.phase !== 'over') return;
            uni.showModal({
              title: '余额已输光',
              content: '是否前往充值？',
              confirmText: '去充值',
              cancelText: '暂不',
              success: res => { if (res.confirm) uni.navigateTo({ url: '/pages/wallet/wallet' }); },
            });
          }, 600);
        }
        try { uni.vibrateShort(); } catch (err) {}
      } else if (e.type === 'sound') {
        sfx(e.name);   // 音效（可在设置关闭）
        if (e.name === 'bomb' || e.name === 'win' || e.name === 'lose') {
          try { uni.vibrateShort(); } catch (err) {}
        }
      }
    },
    // 轮到玩家时启动倒计时，超时自动行动（竞品防挂机行为）
    tickTurn(s) {
      if (this.cdTimer) { clearInterval(this.cdTimer); this.cdTimer = null; }
      this.countdown = 0;
      if (!s || !s.started || s.finished || s.trust || s.current !== 0) return;
      if (!['bid', 'double', 'play'].includes(s.phase)) return;
      this.countdown = 20;
      this.cdTimer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(this.cdTimer);
          this.cdTimer = null;
          this.autoAct();
        }
      }, 1000);
    },
    autoAct() {
      const s = this.snap;
      if (!s || s.finished || s.current !== 0 || s.trust) return;
      if (s.phase === 'bid') { this.flashHint('超时，自动不抢'); return this.bid(0); }
      if (s.phase === 'double') { this.flashHint('超时，自动不加倍'); return this.doubling(1); }
      if (s.phase === 'play') {
        const h = this.game.hint();
        if (h && h.length) { this.selected = h.map(c => c.id); this.flashHint('超时，自动出牌'); this.play(); }
        else if (this.canPass) { this.flashHint('超时，自动不出'); this.pass(); }
      }
    },
    flashHint(msg) {
      this.hintMsg = msg;
      if (this.hintTimer) clearTimeout(this.hintTimer);
      this.hintTimer = setTimeout(() => { this.hintMsg = ''; }, 2200);
    },
    roomLocked(r) {
      return this.profile.coins < r.base * 2;   // 入场门槛：2 倍底数（钱包余额即对局筹码）
    },
    pickRoom(r) {
      if (this.roomLocked(r)) {
        uni.showModal({ title: '余额不足', content: `进入${r.name}需要至少 ${this.fmt(r.base * 2)} 积分（当前 ${this.fmt(this.profile.coins)}）。是否前往充值？`, confirmText: '去充值', success: res => { if (res.confirm) uni.navigateTo({ url: '/pages/wallet/wallet' }); } });
        return;
      }
      this.roomId = r.id;
    },
    fmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); },
    refreshAIRoster() {
      // AI 输光（低于门槛）→ 换一个新 AI（新名字/头像/等级，带匹配积分入场）
      const base = this.ROOMS.find(r => r.id === this.roomId).base;
      for (const p of [1, 2]) {
        if (this.aiStats[p].points < base * 2) {
          this.aiStats[p] = { games: 0, wins: 0, points: Math.round(base * (0.8 + Math.random() * 0.4)) };
          // 下一局 _rollSeats 会生成新身份；这里先记录换人
          this.aiSwapped = true;
        }
      }
    },
    startGame() {
      const room = this.ROOMS.find(r => r.id === this.roomId);
      if (this.profile.coins < room.base * 2) {
        uni.showModal({ title: '余额不足', content: `当前余额 ${this.fmt(this.profile.coins)} 积分，进入${room.name}至少需要 ${this.fmt(room.base * 2)}。是否前往充值？`, confirmText: '去充值', success: res => { if (res.confirm) uni.navigateTo({ url: '/pages/wallet/wallet' }); } });
        return;
      }
      this.refreshAIRoster();
      this.selected = [];
      this.hintMsg = '';
      this.finishInfo = null;
      this.dealId++;
      this.dealing = true;
      if (this.dealTimer) clearTimeout(this.dealTimer);
      this.dealTimer = setTimeout(() => { this.dealing = false; }, 1100);
      this.game.roomBase = room.base;
      this.game.startGame();
    },
    startSettleNext() {
      this.finishInfo = null;
      if (this.onlineMode) { uni.redirectTo({ url: '/pages/online/online' }); return; }
      this.startGame();
    },
    backToOnline() {
      uni.redirectTo({ url: '/pages/online/online' });
    },
    confirmRestart() {
      uni.showModal({
        title: '重新发牌？',
        content: '当前牌局将作废（不计积分）。',
        success: res => { if (res.confirm) this.startGame(); },
      });
    },
    goSettings() {
      uni.navigateTo({ url: '/pages/settings/settings' });
    },
    goWallet() {
      uni.navigateTo({ url: '/pages/wallet/wallet' });
    },
    stackStep(n) {
      if (!n || n <= 1) return 0;
      const maxH = this.winW >= 700 ? 250 : 210;
      const step = Math.floor((maxH - 90) / (n - 1));
      return Math.min(40, Math.max(8, step));
    },
    toggleViewMode() {
      this.viewMode = this.viewMode === 'win' ? 'full' : 'win';
      this.profile.viewMode = this.viewMode;
      this.saveProfile();
    },
    toggleFullscreen() {
      try {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen();
        } else {
          document.exitFullscreen();
        }
      } catch (e) { /* 平台不支持时忽略 */ }
    },
    openProfile() {
      this.profileOpen = true;
    },
    openSeatProfile(p) {
      const m = this.seat(p);
      if (!m) return;
      this.seatInfo = { seat: p, name: m.name, avatar: m.avatar, color: m.color, level: m.level, isHuman: this.onlineMode && !m.bot && m.user };
      // 联机真人：拉取服务器公开战绩
      if (this.seatInfo.isHuman && m.user) {
        net.request('/api/player/' + encodeURIComponent(m.user)).then(r => {
          if (r.ok) this.seatInfo.remote = r.player;
        });
      }
    },
    levelLabel(lv) {
      return { low: '初级', mid: '中级', high: '高级' }[lv] || '中级';
    },
    seatStat(p) {
      if (this.seatInfo && this.seatInfo.remote && this.seatInfo.seat === p) {
        const r = this.seatInfo.remote;
        return { games: r.games, rate: r.rate, points: r.points };
      }
      const s = this.aiStats[p] || { games: 0, wins: 0, points: 0 };
      return { games: s.games, rate: s.games ? Math.round(s.wins * 100 / s.games) : 0, points: s.points };
    },
    goWallet() {
      this.profileOpen = false;
      uni.navigateTo({ url: '/pages/wallet/wallet' });
    },
    toggleOpen() {
      if (this.onlineMode) {
        net.gameOpen(this.onlineGameId).then(r => {
          if (r.ok) uni.showToast({ title: '已公开你的手牌给对面', icon: 'none' });
          else uni.showToast({ title: r.error || '明牌失败', icon: 'none' });
        });
        return;
      }
      this.profile.open = !this.profile.open;
      this.saveProfile();
      uni.showToast({ title: this.profile.open ? '明牌已开启' : '明牌已关闭', icon: 'none' });
    },
    toggleTrust() {
      const on = !(this.snap && this.snap.trust);
      this.game.setTrust(on);
      if (on) this.robotToggle();   // 按钮上方机器人动画
      uni.showToast({ title: on ? '已托管，AI 替你出牌' : '已取消托管', icon: 'none' });
    },
    playerName(i) {
      if (i === 0) return this.profile.name || '你';
      const m = this.seat(i);
      return (m && m.name) || ['你', '竹影客', '梅子青'][i];
    },
    seat(p) {
      return this.snap && this.snap.seatMeta ? this.snap.seatMeta[p] : null;
    },
    levelBadge(lv) {
      return { low: '初', mid: '中', high: '高' }[lv] || '中';
    },
    // ---------- 联机模式 ----------
    startOnlinePolling() {
      if (this.onlineTimer) clearInterval(this.onlineTimer);
      this.onlineTimer = setInterval(() => this.pollOnline(), 1000);
      this.pollOnline();
    },
    pollOnline() {
      net.gameState(this.onlineGameId).then(r => {
        if (!r.ok) { return; }
        this.applyServerState(r.state);
      });
    },
    applyServerState(st) {
      const seats = st.players;
      const names = seats.map(p => p.name);
      const mapped = {
        phase: st.phase, current: st.current, started: st.phase !== 'deal', finished: st.over,
        hands: [st.myHand, st.openHands ? (st.openHands['1'] || []) : [], st.openHands ? (st.openHands['2'] || []) : []],
        openSeats: st.openSeats || [],
        kitty: st.kitty || [],
        landlord: st.landlord, bids: st.bids, maxBid: st.maxBid,
        base: st.base, mults: st.mults, doubled: st.doubled,
        bombCount: st.bombCount, redraws: 0,
        handCounts: st.handCounts,
        multTotal: st.multTotal,
        points: st.base * st.multTotal * Math.pow(2, st.bombCount),
        roundText: st.roundText, thinking: st.current !== 0 ? st.current : -1,
        trust: false, shown: st.shown, played: [],
        seatMeta: [null, seats[1] ? { name: seats[1].name, avatar: seats[1].avatar, color: seats[1].color, level: 'mid' } : null,
                          seats[2] ? { name: seats[2].name, avatar: seats[2].avatar, color: seats[2].color, level: 'mid' } : null],
        onlinePlayers: seats.map(p => ({ ...p, online: p.online })),
      };
      const key = st.roundText + st.phase + st.current;
      if (key !== this._lastOnlineKey) {
        this._lastOnlineKey = key;
        if (st.last && st.last.player !== 0) {
          this.playsLog.push({ player: st.last.player, cards: st.last.cards, combo: st.last.combo });
          this.aiEmoteReact({ last: st.last });
        }
      }
      this.snap = mapped;
      if (st.over && !this.finishInfo) {
        const fin = st.finish || { delta: [0, 0, 0], pts: 0, spring: false, antiSpring: false };
        this.finishInfo = {
          title: fin.delta[0] > 0 ? '农民/你方获胜！' : '对方获胜',
          userWon: fin.delta[0] > 0, pts: fin.pts, spring: fin.spring, antiSpring: fin.antiSpring, springMult: fin.spring || fin.antiSpring ? 2 : 1,
          delta: fin.delta, winner: st.landlord,
        };
        sfx(fin.delta[0] > 0 ? 'win' : 'lose');
        if (this.onlineTimer) clearInterval(this.onlineTimer);   // 结束后停止高频轮询
        // 刷新账户积分（服务端已入账）
        net.serverProfile().then(r => {
          if (r.ok) { this.profile.points = r.user.points; this.profile.games = r.user.games; this.profile.wins = r.user.wins; this.saveProfile(); }
        });
      }
    },
    robotToggle() {
      this.robotShow = true;
      setTimeout(() => { this.robotShow = false; }, 2200);
    },

    // ---------- 表情 ----------
    toggleEmotePanel() {
      this.emoteOpen = !this.emoteOpen;
    },
    sendEmote(e) {
      this.emoteOpen = false;
      this.showEmote(0, e);
    },
    showEmote(p, e) {
      this.emotes[p] = e;
      setTimeout(() => { this.emotes[p] = ''; }, 2500);
    },
    // AI 出牌后小概率回应表情（竞品行为）
    aiEmoteReact(s) {
      if (!s || !s.last) return;
      const key = s.last.player + ':' + s.last.cards.map(c => c.id).join(',');
      if (key === this.lastPlayKey) return;
      this.lastPlayKey = key;
      const p = s.last.player;
      if (p === 0 || Math.random() > 0.25) return;
      this.showEmote(p, this.EMOTE_SET[Math.floor(Math.random() * this.EMOTE_SET.length)]);
    },
    isRed(c) {
      return c.suit === '♥' || c.suit === '♦' || (c.joker && c.rank === 17);
    },
    faceLabel(c) {
      return label(c);
    },
    isSelected(c) {
      return this.selected.includes(c.id);
    },
    showRole(p) {
      return !!(this.snap && this.snap.started && this.snap.phase !== 'bid' && this.snap.landlord === p);
    },
    revealOpp(p) {
      if (!this.snap || !this.snap.started) return false;
      if (this.onlineMode) return !!(this.snap.openSeats && this.snap.openSeats.includes(p));
      return !!(this.profile.open && ['bid', 'double', 'play', 'over'].includes(this.snap.phase));
    },
    toggleCard(c) {
      if (!this.snap || this.snap.phase !== 'play' || this.snap.current !== 0 || this.snap.trust) return;
      const i = this.selected.indexOf(c.id);
      if (i >= 0) this.selected.splice(i, 1);
      else this.selected.push(c.id);
    },
    bid(v) {
      if (this.onlineMode) { net.gameAction(this.onlineGameId, 'bid', v); return; }
      this.game.humanBid(v);
    },
    doubling(m) {
      if (this.onlineMode) { net.gameAction(this.onlineGameId, 'double', m); return; }
      this.game.humanDouble(m);
    },
    pass() {
      this.selected = [];
      if (this.onlineMode) { net.gameAction(this.onlineGameId, 'pass'); return; }
      this.game.humanPass();
    },
    hint() {
      if (this.onlineMode) {
        const s = this.snap;
        if (!s || s.phase !== 'play') return;
        const last = s.last && s.last.player !== 0 ? s.last.combo : null;
        const h = last ? findResponse(this.myHand, last, { bombs: true }) : bestLead(this.myHand);
        if (h && h.length) { this.selected = h.map(c => c.id); this.flashHint('已为你选牌，点「出牌」确认'); }
        else this.flashHint(this.canPass ? '没有能压过的牌，点「不出」过牌' : '轮到你领出');
        return;
      }
      const h = this.game.hint();
      if (h && h.length) {
        this.selected = h.map(c => c.id);
        this.flashHint('已为你选牌，点「出牌」确认');
      } else {
        this.selected = [];
        this.flashHint(this.canPass ? '没有能压过的牌，点「不出」过牌' : '轮到你领出，已选中建议牌型');
      }
    },
    play() {
      if (!this.selected.length) return;
      const picked = this.myHand.filter(c => this.selected.includes(c.id));
      if (this.onlineMode) {
        net.gameAction(this.onlineGameId, 'play', 0, picked);
        this.selected = [];
        this.hintMsg = '';
        return;
      }
      this.game.humanPlay(picked);
      this.selected = [];
      this.hintMsg = '';
    },
  },
};
</script>

<style scoped>
.page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0d3b2e;
  overflow: hidden;
}

/* ---------- 视图模式（桌面窗口/全屏） ---------- */
.page.win-mode {
  max-width: 1020px;
  min-height: 0;
  height: calc(100vh - 28px);
  margin: 14px auto;
  border-radius: 26px;
  border: 2px solid #e7c76644;
  box-shadow: 0 24px 80px rgba(0,0,0,.6), 0 0 0 8px rgba(0,0,0,.35);
  overflow: hidden;
}
body:has(.page.win-mode) { background: #060f0b; }
.wide-only { display: none; }
@media (min-width: 900px) {
  .wide-only { display: block; }
  .page.win-mode .actions { min-height: 84rpx; }
}
@media (max-width: 380px) {
  .hand-card { width: 72rpx; height: 100rpx; margin-left: -50rpx; padding: 8rpx 0 0 9rpx; }
  .hc-rank { font-size: 28rpx; }
  .hc-suit { font-size: 22rpx; }
  .hand { padding-left: 50rpx; min-height: 118rpx; }
  .btn { font-size: 26rpx; padding: 14rpx 36rpx; }
  .card-back-mini, .open-card, .shown-card { width: 68rpx; height: 94rpx; margin-top: -70rpx; }
  .card-back-mini:first-child, .open-card:first-child, .shown-card:first-child { margin-top: 0; }
  .shown-card:nth-child(even) { margin-left: 8rpx; }
  .oc-rank, .sc-rank { font-size: 22rpx; }
  .oc-suit, .sc-suit { font-size: 18rpx; }
  .opp-cards { padding-top: 70rpx; }
  .opp-shown { min-height: 110rpx; }
}

/* ---------- 顶栏 ---------- */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12rpx 20rpx 8rpx;
}
.topbar-l .title {
  font-size: 32rpx;
  font-weight: 700;
  color: #f3efe2;
}
.topbar-l .sub {
  margin-left: 10rpx;
  font-size: 20rpx;
  color: #9db8a8;
}
.topbar-r {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.coin-pill {
  display: flex;
  align-items: center;
  gap: 6rpx;
  font-size: 22rpx;
  color: #ffe9a8;
  background: #0a2f24;
  border: 2rpx solid #e7c76666;
  border-radius: 26rpx;
  padding: 8rpx 18rpx;
  font-weight: 700;
}
.coin-ico {
  color: #e7c766;
}
.points-pill {
  font-size: 22rpx;
  color: #bfe3d0;
  background: #0a2f24;
  border: 2rpx solid #2a8f6d;
  border-radius: 26rpx;
  padding: 8rpx 18rpx;
  font-weight: 700;
}
.mini-btn {
  font-size: 22rpx;
  color: #f3efe2;
  background: #1f7a5c;
  border: 2rpx solid #2a8f6d;
  padding: 8rpx 18rpx;
  border-radius: 24rpx;
}
.mini-btn.gold {
  background: #e7c766;
  color: #3a2c07;
  border-color: #d9b76e;
  font-weight: 700;
}
.rotate-tip {
  display: none;
  text-align: center;
  font-size: 20rpx;
  color: #7ea391;
  padding: 0 0 4rpx;
}
@media (orientation: portrait) and (max-width: 700px) {
  .rotate-tip { display: block; }
}

/* ---------- 牌桌主题 ---------- */
.table {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  margin: 6rpx 16rpx;
  border-radius: 24rpx;
  padding: 16rpx 20rpx;
  border: 3rpx solid #1e5c48;
}
.table.bg-green {
  background: radial-gradient(ellipse at 50% 30%, #14614a 0%, #0f4d3a 55%, #0a382b 100%);
}
.table.bg-blue {
  background: radial-gradient(ellipse at 50% 30%, #173a6b 0%, #122c54 55%, #0b1f3d 100%);
  border-color: #24507e;
}
.table.bg-purple {
  background: radial-gradient(ellipse at 50% 30%, #45245e 0%, #371c4b 55%, #251234 100%);
  border-color: #5c3480;
}
.table-over {
  filter: saturate(0.72) brightness(0.9);
}
.table-over .deal { animation: none !important; }
.table-over .thinking { display: none; }

.table-glow {
  position: absolute;
  top: -60rpx;
  left: 50%;
  width: 400rpx;
  height: 200rpx;
  margin-left: -200rpx;
  background: radial-gradient(ellipse, rgba(255, 236, 180, 0.16), transparent 70%);
}

/* 对手座位：竖向牌堆（与手牌同尺寸，纵向层叠） */
.opp {
  position: absolute;
  top: 16rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  width: 240rpx;
}
.opp-info { flex-wrap: nowrap; }
.opp-name { max-width: 110rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.opp-a { left: 16rpx; align-items: flex-start; }
.opp-b { right: 16rpx; align-items: flex-end; }
.opp-body {
  display: flex;
  flex-direction: row;
  gap: 16rpx;
  align-items: flex-start;
}
.opp-b .opp-body { flex-direction: row-reverse; }
.opp-info {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.opp-name {
  font-size: 24rpx;
  color: #f0ead5;
  font-weight: 600;
}
.opp-count {
  font-size: 20rpx;
  color: #9db8a8;
}
.role-tag {
  font-size: 18rpx;
  color: #3a2c07;
  background: #e7c766;
  border-radius: 10rpx;
  padding: 2rpx 10rpx;
  font-weight: 700;
}
.thinking {
  font-size: 20rpx;
  color: #ffe9a8;
}
.avatar {
  display: flex;
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  background: #1f7a5c;
  color: #fff;
  font-size: 26rpx;
  font-weight: 700;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #e7c766;
}
.avatar.rose { background: #a04a56; }
/* 手牌堆：横放卡翻转（背/面双图层，明牌原地翻开） */
.opp-cards {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 120rpx;
  overflow: hidden;
}
.opp-cards.right { align-items: flex-end; }
.stack-card {
  position: relative;
  display: block;
  width: 128rpx;
  height: 88rpx;
  margin-top: -62rpx;   /* 每张露出 26rpx 边缘 */
  border-radius: 8rpx;
}
.stack-card:first-child { margin-top: 0; }
.stack-card .sc-back,
.stack-card .sc-face {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  backface-visibility: hidden;
}
.stack-card .sc-back {
  border: 1rpx solid rgba(231, 199, 102, 0.5);
}
.back-bamboo .sc-back {
  background: repeating-linear-gradient(45deg, #1f7a5c 0 14rpx, #175d46 14rpx 28rpx);
}
.back-phoenix .sc-back {
  background: repeating-linear-gradient(45deg, #a04a56 0 14rpx, #7d3742 14rpx 28rpx);
}
.stack-card .sc-face {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2rpx;
  padding: 8rpx 0 0 10rpx;
  background: #fffef8;
  border: 2rpx solid #d8d5c6;
  color: #23252b;
  transform: rotate(90deg);   /* 顺时针 90°：角标落在横卡右上 */
}
.stack-card .sc-face .sc-rank { font-size: 26rpx; font-weight: 800; line-height: 1; }
.stack-card .sc-face .sc-suit { font-size: 20rpx; line-height: 1.1; }
.stack-card.flipped .sc-face { gap: 4rpx; }

/* 座位出牌展示：竖排层开（同手牌尺寸，每张向下错位） */
/* 左右出牌区：与下方同款竖立卡牌，层叠只露字母角 */
.play-zone {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 150rpx;
  height: 380rpx;
  padding: 4rpx 0 0 2rpx;
  overflow: hidden;
}
.play-l { left: 140rpx; top: 118rpx; }
.play-r { right: 140rpx; top: 118rpx; align-items: flex-end; padding: 4rpx 2rpx 0 0; }
/* 出牌区：横放卡，数字花色直立在左上角（与下方手牌一致） */
.play-zone .shown-card {
  position: relative;
  display: block;
  width: 120rpx;
  height: 84rpx;
  margin-top: -54rpx;
  border-radius: 8rpx;
  background: #fffef8;
  border: 2rpx solid #d8d5c6;
  color: #23252b;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.3);
  overflow: hidden;
}
.play-zone .shown-card:first-child { margin-top: 0; }
.play-zone .shown-card.red { color: #b3372e; }
.play-zone .sc-rot {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 84rpx;
  height: 120rpx;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 8rpx 0 0 10rpx;
  transform: translate(-50%, -50%) rotate(90deg);
}
.play-zone .sc-rank { font-size: 26rpx; font-weight: 800; line-height: 1; }
.play-zone .sc-suit { font-size: 20rpx; line-height: 1.1; margin-top: 2rpx; }
.play-zone .pass-pill { align-self: center; }
.shown-card.mine {
  width: 60rpx;
  height: 84rpx;
  margin-left: -16rpx;
  align-items: center;
  padding: 5rpx 0 0 0;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.25);
}
.shown-card.mine:first-child { margin-left: 0; }
.shown-card.mine .sc-rank { font-size: 22rpx; }
.shown-card.mine .sc-suit { font-size: 16rpx; }
.pass-pill {
  font-size: 20rpx;
  color: #bfe3d0;
  border: 1rpx solid #2a8f6d;
  border-radius: 18rpx;
  padding: 4rpx 18rpx;
  background: rgba(15, 77, 58, 0.5);
}

/* 中央 */
.center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 8rpx;
  padding: 4rpx 0 2rpx;
  min-height: 0;
}
.kitty {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.kitty-label {
  font-size: 20rpx;
  color: #9db8a8;
  margin-left: 6rpx;
}
.kitty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 48rpx;
  height: 64rpx;
  border-radius: 8rpx;
  background: #fffef8;
  color: #23252b;
  border: 2rpx solid #d8d5c6;
  overflow: hidden;
}
.kitty-card.red { color: #b3372e; }
.kc-rank { font-size: 22rpx; font-weight: 800; line-height: 1.1; }
.kc-suit { font-size: 18rpx; line-height: 1; }
.kitty-card.back {
  background: repeating-linear-gradient(45deg, #1f7a5c 0 8rpx, #175d46 8rpx 16rpx);
  border-color: rgba(231, 199, 102, 0.45);
}
.back-phoenix .kitty-card.back {
  background: repeating-linear-gradient(45deg, #a04a56 0 8rpx, #7d3742 8rpx 16rpx);
}
.my-shown {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  width: 640rpx;
  max-width: 96%;
  min-height: 96rpx;
  margin-top: 6rpx;
  border: 2rpx dashed rgba(231, 199, 102, 0.3);
  border-radius: 16rpx;
  background: rgba(10, 47, 36, 0.3);
  padding: 10rpx 14rpx;
  overflow: hidden;
}
.placeholder {
  font-size: 22rpx;
  color: #9db8a8;
}
.round {
  display: block;
  font-size: 24rpx;
  color: #ffe9a8;
  text-align: center;
}
.mult {
  display: block;
  font-size: 20rpx;
  color: #c8d8c0;
  text-align: center;
}

/* 我的座位：左下角长方形框体 */
.me-head {
  position: fixed;
  left: 76px;
  bottom: 6px;   /* 直接锚定视口底部 */
  display: flex;
  align-items: center;
  gap: 12rpx;
  background: rgba(10, 47, 36, 0.88);
  border: 2rpx solid #2a8f6d;
  border-radius: 14rpx;
  padding: 10rpx 16rpx;
  z-index: 30;
  cursor: pointer;
}
.me-avatar {
  width: 56rpx;
  height: 56rpx;
  font-size: 26rpx;
}
.me-col {
  display: flex;
  flex-direction: column;
  gap: 2rpx;
}
.me-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.hand {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  row-gap: 12rpx;
  min-height: 118rpx;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 4rpx;
  padding-left: 230rpx;   /* 左下角让位给头像框体 */
}
.hand-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 80rpx;
  height: 112rpx;
  margin-left: -50rpx;
  padding: 8rpx 0 0 10rpx;
  border-radius: 10rpx;
  background: #fffef8;
  border: 2rpx solid #d8d5c6;
  color: #23252b;
  position: relative;
  transition: transform 0.08s;
}
.hand-card.red { color: #b3372e; }
.hand-card.sel {
  transform: translateY(-26rpx);
  border-color: #e7c766;
  box-shadow: 0 0 14rpx rgba(231, 199, 102, 0.65);
}
.hc-rank {
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1;
}
.hc-suit {
  font-size: 22rpx;
  line-height: 1.2;
  margin-top: 2rpx;
}
.hc-suit.joker {
  font-size: 12rpx;
  font-weight: 700;
  letter-spacing: 1rpx;
}

/* ---------- 发牌动画 ---------- */
.deal {
  animation: deal-in 0.32s ease-out backwards;
}
@keyframes deal-in {
  0% {
    opacity: 0;
    transform: translate(20rpx, -160rpx) rotate(14deg) scale(0.6);
  }
  70% { opacity: 1; }
  100% {
    opacity: 1;
    transform: translate(0, 0) rotate(0) scale(1);
  }
}
.hand-card.deal.sel {
  animation: none;
  transform: translateY(-26rpx);
}

/* ---------- 横屏布局 ---------- */
@media (orientation: landscape) {
  .hand {
    margin-top: auto;
    min-height: 130rpx;
  }
}

/* ---------- 结算界面 ---------- */
.settle-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 18, 13, 0.78);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.settle-panel {
  width: 560rpx;
  max-width: 92%;
  background: linear-gradient(180deg, #14493a, #0d3529);
  border: 2rpx solid #e7c76666;
  border-radius: 24rpx;
  padding: 28rpx 28rpx 24rpx;
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  box-shadow: 0 10rpx 50rpx rgba(0, 0, 0, 0.5);
}
.settle-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
}
.settle-panel.win .sb-title { color: #ffe9a8; }
.settle-panel.lose .sb-title { color: #f3b8b8; }
.sb-title {
  font-size: 44rpx;
  font-weight: 800;
  letter-spacing: 4rpx;
}
.sb-tag {
  font-size: 22rpx;
  color: #3a2c07;
  background: #e7c766;
  border-radius: 14rpx;
  padding: 4rpx 16rpx;
  font-weight: 700;
}
.settle-formula {
  text-align: center;
  font-size: 22rpx;
  color: #c8d8c0;
  border-top: 1rpx solid #1e5c48;
  border-bottom: 1rpx solid #1e5c48;
  padding: 10rpx 0;
}
.settle-formula b {
  color: #ffe9a8;
  font-size: 28rpx;
}
.settle-rows {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.settle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(10, 47, 36, 0.5);
  border-radius: 14rpx;
  padding: 12rpx 18rpx;
}
.settle-row.me {
  border: 1rpx solid #e7c76688;
}
.sr-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.settle-row .avatar {
  width: 52rpx;
  height: 52rpx;
  font-size: 24rpx;
}
.sr-info {
  display: flex;
  flex-direction: column;
}
.sr-name {
  font-size: 26rpx;
  color: #f0ead5;
  font-weight: 600;
}
.sr-role {
  font-size: 20rpx;
  color: #9db8a8;
}
.sr-delta {
  font-size: 34rpx;
  font-weight: 800;
}
.sr-delta.plus { color: #7ed6a2; }
.sr-delta.minus { color: #e08c8c; }
.settle-actions {
  display: flex;
  gap: 16rpx;
}
.settle-actions .btn {
  flex: 1;
}

/* ---------- AI 等级徽章 ---------- */
.level-tag {
  font-size: 18rpx;
  border-radius: 10rpx;
  padding: 2rpx 10rpx;
  font-weight: 700;
  color: #fff;
}
.level-tag.low { background: #b07d3a; }
.level-tag.mid { background: #6d7f8f; }
.level-tag.high { background: #c9a13b; color: #3a2c07; }

/* ---------- 表情 ---------- */
.emote-bubble {
  position: absolute;
  font-size: 44rpx;
  background: rgba(255, 254, 248, 0.95);
  border-radius: 28rpx;
  padding: 6rpx 18rpx;
  z-index: 20;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.3);
}
.emote-bubble.seat-a { top: 100rpx; left: 60rpx; }
.emote-bubble.seat-b { top: 100rpx; right: 60rpx; }
.emote-bubble.seat-me { position: static; display: inline-block; margin-left: 8rpx; }
.emote-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 18, 13, 0.35);
  z-index: 90;
}
.emote-panel {
  position: absolute;
  bottom: 140rpx;
  left: 50%;
  transform: translateX(-50%);
  background: #124535;
  border: 2rpx solid #e7c76666;
  border-radius: 20rpx;
  padding: 18rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  width: 560rpx;
  max-width: 90%;
  justify-content: center;
}
.emote-item {
  font-size: 52rpx;
  width: 96rpx;
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0d3b2e;
  border-radius: 14rpx;
}
.emoji-btn {
  font-size: 26rpx;
}

/* ---------- 自定义牌背 ---------- */
.card-back-mini.custom {
  background: var(--back-color, #8a5fb0);
  border-color: rgba(255, 255, 255, 0.35);
}
.kitty-card.back.custom {
  background: var(--back-color, #8a5fb0);
  border-color: rgba(255, 255, 255, 0.35);
}
.back-face {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  transform: rotate(90deg);
}
.kitty-card .back-face {
  font-size: 28rpx;
}

.robot-wrap { position: relative; }
.robot-anim {
  position: absolute;
  bottom: 44rpx;
  left: 50%;
  transform: translateX(-50%);
  font-size: 44rpx;
  animation: robot-float 2.2s ease-out forwards;
  z-index: 50;
  filter: drop-shadow(0 4rpx 10rpx rgba(0,0,0,0.4));
}
@keyframes robot-float {
  0% { opacity: 0; transform: translate(-50%, 16rpx) scale(0.6); }
  20% { opacity: 1; transform: translate(-50%, 0) scale(1.1); }
  80% { opacity: 1; transform: translate(-50%, -8rpx) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -30rpx) scale(0.8); }
}

/* ---------- 个人简介弹窗 ---------- */
.profile-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 18, 13, 0.78);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 110;
}
.profile-panel {
  width: 520rpx;
  max-width: 92%;
  background: linear-gradient(180deg, #14493a, #0d3529);
  border: 2rpx solid #e7c76666;
  border-radius: 20rpx;
  padding: 26rpx;
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.pf-head {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.pf-avatar {
  width: 88rpx;
  height: 88rpx;
  font-size: 40rpx;
}
.pf-info { display: flex; flex-direction: column; gap: 4rpx; }
.pf-name { font-size: 32rpx; font-weight: 800; color: #f3efe2; }
.pf-sub { font-size: 20rpx; color: #9db8a8; }
.pf-stats {
  display: flex;
  justify-content: space-around;
  background: rgba(10, 47, 36, 0.5);
  border-radius: 14rpx;
  padding: 14rpx 8rpx;
}
.pf-stat { display: flex; flex-direction: column; align-items: center; gap: 4rpx; }
.pf-num { font-size: 30rpx; font-weight: 800; color: #ffe9a8; }
.pf-label { font-size: 20rpx; color: #9db8a8; }
.pf-recharge {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  background: rgba(125, 55, 66, 0.35);
  border: 1rpx solid #a04a56aa;
  border-radius: 12rpx;
  padding: 14rpx;
}
.pf-warn { font-size: 24rpx; color: #f3b8b8; }
.profile-panel .btn.primary { width: 100%; }
.profile-panel .btn.ghost {
  background: transparent;
  color: #9db8a8;
  border: 2rpx solid #1e5c48;
}

/* ---------- 记牌器（底牌上方） ---------- */
.counter {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3rpx;
  background: rgba(10, 47, 36, 0.72);
  border: 1rpx solid #2a8f6d88;
  border-radius: 12rpx;
  padding: 6rpx 14rpx;
  margin-bottom: 26rpx;   /* 上移：靠近标题框 */
}
.counter-title {
  font-size: 18rpx;
  color: #e7c766;
  font-weight: 700;
  margin-right: 4rpx;
}
.counter-mini {
  font-size: 20rpx;
  color: #9db8a8;
  background: rgba(10, 47, 36, 0.72);
  border: 1rpx solid #2a8f6d88;
  border-radius: 12rpx;
  padding: 4rpx 16rpx;
}
.counter-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 34rpx;
  border-radius: 8rpx;
  background: rgba(10, 47, 36, 0.55);
  padding: 2rpx 4rpx;
}
.counter-cell.zero { opacity: 0.3; }
.cc-label {
  font-size: 18rpx;
  color: #c8d8c0;
  line-height: 1.2;
}
.cc-num {
  font-size: 20rpx;
  color: #ffe9a8;
  font-weight: 700;
  line-height: 1.2;
}
.counter-collapsed {
  font-size: 20rpx;
  color: #9db8a8;
  background: transparent;
  border: 1rpx solid #1e5c48;
  border-radius: 18rpx;
  padding: 2rpx 16rpx;
  margin: 0 auto 4rpx;
}

/* ---------- 牌型标签 / 倒计时 ---------- */
.combo-tag {
  position: absolute;
  top: -30rpx;
  left: 50%;
  transform: translateX(-50%);
  font-size: 22rpx;
  color: #0d3529;
  background: #e7c766;
  border-radius: 18rpx;
  padding: 4rpx 22rpx;
  white-space: nowrap;
  font-weight: 700;
}
.combo-tag.bad {
  color: #f3b8b8;
  background: #7d3742;
}
.count-pill {
  position: absolute;
  top: -30rpx;
  right: 24rpx;
  font-size: 22rpx;
  color: #bfe3d0;
  background: rgba(10, 47, 36, 0.9);
  border: 1rpx solid #2a8f6d;
  border-radius: 18rpx;
  padding: 4rpx 16rpx;
}
.count-pill.urgent {
  color: #ffb4b4;
  border-color: #a04a56;
}

.room-bar {
  display: flex;
  justify-content: center;
  gap: 10rpx;
  padding: 4rpx 0;
}
.room-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #0d3b2e;
  border: 2rpx solid #1e5c48;
  border-radius: 12rpx;
  padding: 6rpx 18rpx;
}
.room-chip b { font-size: 22rpx; color: #f0ead5; }
.room-chip small { font-size: 18rpx; color: #9db8a8; }
.room-chip.on { border-color: #e7c766; background: #17493a; }
.room-chip.on b { color: #ffe9a8; }
.room-chip.locked { opacity: 0.45; }

/* ---------- 操作区 ---------- */
.actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14rpx;
  padding: 4rpx 16rpx 2rpx;
  flex-wrap: wrap;
  position: relative;
}
.actions.in-table { min-height: 60rpx; }
.hint-msg {
  position: absolute;
  top: -30rpx;
  left: 50%;
  transform: translateX(-50%);
  font-size: 22rpx;
  color: #ffe9a8;
  background: rgba(10, 47, 36, 0.9);
  border: 1rpx solid #e7c76666;
  border-radius: 18rpx;
  padding: 4rpx 22rpx;
  white-space: nowrap;
}
.btn {
  font-size: 24rpx;
  font-weight: 700;
  color: #f3efe2;
  background: #1f7a5c;
  border: 2rpx solid #2a8f6d;
  border-radius: 30rpx;
  padding: 10rpx 34rpx;
  text-align: center;
}
.btn.primary {
  background: #e7c766;
  color: #3a2c07;
  border-color: #d9b76e;
}
.btn.disabled {
  opacity: 0.5;
}
.foot-note {
  display: none;
}
</style>
