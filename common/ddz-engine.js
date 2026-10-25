// 牌友斗地主 · 游戏引擎（无 DOM 依赖，可运行于 H5 / App / Node）
//
// 相对原版 game.js 的修复：
//  1. startGame 后若起叫者是 AI，立即调度 AI 行动（原版会永久卡在"叫分中"）
//  2. "重新发牌"由 UI 常驻提供（引擎侧不再有按钮被清除的问题）
//  3. 加倍轮从地主开始转满三家才进入出牌（原版 p===2 判断会跳过玩家）
//  4. 流局计数保存在实例上，重发不清零，三次流局后随机指定地主（原版永远到不了 3）
//  5. AI 领出会打对子/三带/顺子，不再只会甩最小单张
//  6. 炸弹/王炸倍数按次数叠加（bombCount，每炸 ×2）
//  7. 明牌模式只影响展示，叫分逻辑恢复正常
//  8. 提示在领出时给出合理牌组（bestLead），不再只选最小单张

export const SUITS = ['♠', '♥', '♣', '♦'];
export const SUIT_NAME = { '♠': '黑桃', '♥': '红桃', '♣': '梅花', '♦': '方块' };
export const RANK_LABEL = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A', 15: '2', 16: '小王', 17: '大王' };
export const NAMES = ['你', '竹影客', '梅子青'];

// AI 等级配置：速度(ms) / 是否配合队友 / 是否留牌后出（保留炸弹与强牌）
export const AI_LEVELS = {
  low: { label: '初级', badge: '初', speed: [400, 400], cooperate: false, retention: false },
  mid: { label: '中级', badge: '中', speed: [750, 850], cooperate: true, retention: false },
  high: { label: '高级', badge: '高', speed: [1500, 900], cooperate: true, retention: true },
};
// 每局随机 AI 名字与头像池（原创通用词，无版权）
export const AI_NAME_POOL = ['竹影客', '梅子青', '听雨楼主', '寒山远客', '青衫剑客', '白鹿先生', '夜航星子', '半盏清茶', '南山樵夫', '一苇渡江', '云中仙鹤', '观棋不语'];
export const AI_AVATAR_POOL = ['🎋', '🌿', '🌸', '🍁', '🌙', '⭐', '🏔', '🍵', '🎭', '🐉', '🕊', '🐺'];
export const AI_COLOR_POOL = ['#1f7a5c', '#a04a56', '#3a6ea5', '#8a5fb0', '#b07d3a'];

export function label(c) { return c.joker ? (c.rank === 17 ? '大王' : '小王') : (RANK_LABEL[c.rank] || String(c.rank)); }
export function rankShort(r) { return RANK_LABEL[r] || String(r); }
export function cardSort(a, b) { return a.rank - b.rank || SUITS.indexOf(a.suit) - SUITS.indexOf(b.suit); }

export function makeDeck() {
  const deck = [];
  for (let r = 3; r <= 15; r++) for (const suit of SUITS) deck.push({ rank: r, suit, id: `${suit}${r}` });
  deck.push({ rank: 16, suit: '★', joker: true, id: 'joker-s' });
  deck.push({ rank: 17, suit: '★', joker: true, id: 'joker-b' });
  return deck;
}
export function shuffle(a, rng = Math.random) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---------- 牌型 ----------
export function getCombo(cards) {
  if (!cards || !cards.length) return null;
  const cs = [...cards].sort(cardSort), n = cs.length, freq = {};
  cs.forEach(c => (freq[c.rank] = (freq[c.rank] || 0) + 1));
  const distinct = Object.keys(freq).map(Number).sort((a, b) => a - b);
  const counts = Object.values(freq).sort((a, b) => b - a);
  const isRun = rs => rs.every(r => r <= 14) && rs.every((r, i) => i === 0 || r === rs[i - 1] + 1);
  if (n === 1) return { type: 'single', high: cs[0].rank, len: 1, text: label(cs[0]) };
  if (n === 2 && distinct.length === 2 && distinct[0] === 16 && distinct[1] === 17) return { type: 'rocket', high: 18, len: 1, text: '王炸' };
  if (n === 2 && distinct.length === 1) return { type: 'pair', high: distinct[0], len: 1, text: `${label(cs[0])} 对` };
  if (n === 3 && distinct.length === 1) return { type: 'triple', high: distinct[0], len: 1, text: `${label(cs[0])} 三张` };
  if (n === 4 && distinct.length === 1) return { type: 'bomb', high: distinct[0], len: 1, text: `${label(cs[0])} 炸弹` };
  if (n === 4 && counts[0] === 3) return { type: 'triple1', high: Number(Object.keys(freq).find(r => freq[r] === 3)), len: 1, text: '三带一' };
  if (n === 5 && counts[0] === 3 && counts[1] === 2) return { type: 'triple2', high: Number(Object.keys(freq).find(r => freq[r] === 3)), len: 1, text: '三带二' };
  if (n >= 5 && distinct.length === n && isRun(distinct)) return { type: 'straight', high: distinct[n - 1], len: n, text: `${n} 张顺子` };
  if (n >= 6 && n % 2 === 0 && distinct.length === n / 2 && counts.every(c => c === 2) && isRun(distinct))
    return { type: 'pairrun', high: distinct[distinct.length - 1], len: distinct.length, text: `${distinct.length} 连对` };
  if (n >= 6) {
    const trs = distinct.filter(r => freq[r] >= 3 && r <= 14);
    if (trs.length >= 2 && trs.every((r, i) => i === 0 || r === trs[i - 1] + 1)) {
      const high = trs[trs.length - 1], len = trs.length;
      const rest = n - 3 * len;
      if (rest === 0) return { type: 'plane', high, len, text: `${len} 连三` };
      if (rest === len) return { type: 'plane1', high, len, text: `${len} 连三带${len}单` };
      if (rest === 2 * len) {
        const rem = distinct.filter(r => freq[r] < 3);
        if (rem.every(r => freq[r] % 2 === 0)) return { type: 'plane2', high, len, text: `${len} 连三带对` };
      }
    }
  }
  return null; // 含 4 带 2 等未支持的边缘牌型
}

export function beats(a, b) {
  if (!b) return true;
  if (a.type === 'rocket') return true;
  if (b.type === 'rocket') return false;
  if (a.type === 'bomb' && b.type === 'bomb') return a.high > b.high;
  if (a.type === 'bomb') return true;
  if (b.type === 'bomb') return false;
  return a.type === b.type && a.len === b.len && a.high > b.high;
}

function groupBy(hand) {
  const by = {};
  [...hand].sort(cardSort).forEach(c => (by[c.rank] = by[c.rank] || []).push(c));
  return by;
}
function anyBomb(by) {
  for (let r = 3; r <= 17; r++) if (by[r]?.length >= 4) return by[r].slice(0, 4);
  if (by[16]?.length && by[17]?.length) return [by[16][0], by[17][0]];
  return null;
}
// 选一张不拆牌的单张翅膀：优先散牌，其次最小的对子/三张里拆
function pickKicker(by, excludeRank, need = 1) {
  const singles = Object.keys(by).map(Number).filter(r => r !== excludeRank && by[r].length === 1).sort((a, b) => a - b);
  if (singles.length >= need) return singles.slice(0, need).map(r => by[r][0]);
  const others = Object.keys(by).map(Number).filter(r => r !== excludeRank && by[r].length >= 1).sort((a, b) => a - b);
  const out = [];
  for (const r of others) { for (const c of by[r]) { if (out.length < need) out.push(c); } }
  return out.length >= need ? out : null;
}

// 跟牌：找出能压住 last 的最小合法应手（不含领出场景）
export function findResponse(hand, last, opts = {}) {
  if (!last) return null;
  if (last.type === 'rocket') return null;
  const by = groupBy(hand);
  const useBombs = opts.bombs !== false;
  if (last.type === 'bomb') {
    if (!useBombs) return null;
    for (let r = last.high + 1; r <= 17; r++) if (by[r]?.length >= 4) return by[r].slice(0, 4);
    if (by[16]?.length && by[17]?.length) return [by[16][0], by[17][0]];
    return null;
  }
  if (last.type === 'single' || last.type === 'pair' || last.type === 'triple') {
    const need = { single: 1, pair: 2, triple: 3 }[last.type];
    for (let r = last.high + 1; r <= 17; r++) if (by[r]?.length >= need) return by[r].slice(0, need);
    return useBombs ? anyBomb(by) : null;
  }
  if (last.type === 'triple1' || last.type === 'triple2') {
    const needPair = last.type === 'triple2';
    for (let r = last.high + 1; r <= 15; r++) {
      if (!by[r] || by[r].length < 3) continue;
      const group = by[r].slice(0, 3);
      if (needPair) {
        let pair = null;
        for (const rr of Object.keys(by).map(Number).filter(x => x !== r && by[x].length >= 2).sort((a, b) => a - b)) { pair = by[rr].slice(0, 2); break; }
        if (!pair) continue;
        group.push(...pair);
      } else {
        const kickers = pickKicker(by, r, 1);
        if (!kickers) continue;
        group.push(...kickers);
      }
      if (beats(getCombo(group), last)) return group;
    }
    return useBombs ? anyBomb(by) : null;
  }
  if (last.type === 'straight' || last.type === 'pairrun') {
    const per = last.type === 'straight' ? 1 : 2;
    const need = last.len;
    const ranks = Object.keys(by).map(Number).filter(r => r <= 14 && by[r].length >= per).sort((a, b) => a - b);
    for (let i = 0; i < ranks.length; i++) {
      const run = [ranks[i]];
      for (let j = i + 1; j < ranks.length && ranks[j] === run[run.length - 1] + 1; j++) run.push(ranks[j]);
      for (let k = 0; k + need <= run.length; k++) {
        const slice = run.slice(k, k + need);
        if (slice[slice.length - 1] <= last.high) continue;
        const candidate = slice.flatMap(r => by[r].slice(0, per));
        if (beats(getCombo(candidate), last)) return candidate;
      }
    }
    return useBombs ? anyBomb(by) : null;
  }
  if (last.type === 'plane' || last.type === 'plane1' || last.type === 'plane2') {
    const need = last.len;
    const trRanks = Object.keys(by).map(Number).filter(r => r <= 14 && by[r].length >= 3).sort((a, b) => a - b);
    for (let i = 0; i < trRanks.length; i++) {
      const run = [trRanks[i]];
      for (let j = i + 1; j < trRanks.length && trRanks[j] === run[run.length - 1] + 1; j++) run.push(trRanks[j]);
      for (let k = 0; k + need <= run.length; k++) {
        const win = run.slice(k, k + need);
        if (win[win.length - 1] <= last.high) continue;
        const set = new Set(win);
        const group = win.flatMap(r => by[r].slice(0, 3));
        if (last.type === 'plane1') {
          const singles = Object.keys(by).map(Number).sort((a, b) => a - b).filter(r => !set.has(r)).flatMap(r => by[r]);
          if (singles.length < need) continue;
          group.push(...singles.slice(0, need));
        } else if (last.type === 'plane2') {
          const pairs = [];
          for (const r of Object.keys(by).map(Number).sort((a, b) => a - b)) if (!set.has(r) && by[r].length >= 2) { pairs.push(by[r][0], by[r][1]); if (pairs.length >= need * 2) break; }
          if (pairs.length < need * 2) continue;
          group.push(...pairs);
        }
        if (beats(getCombo(group), last)) return group;
      }
    }
    return useBombs ? anyBomb(by) : null;
  }
  return null;
}

// 领出建议：整手成牌 > 低顺子 > 低对子 > 低三带 > 最小单张（AI 领出与玩家提示共用）
// level: 'low' 基本乱出 / 'mid' 默认策略 / 'high' 留牌后出（保留对子/三张/炸弹/大牌，先甩散牌）
export function bestLead(hand, level = 'mid', rng = Math.random) {
  if (!hand || !hand.length) return null;
  const whole = getCombo(hand);
  if (whole) return [...hand];
  const by = groupBy(hand);
  const ranks = Object.keys(by).map(Number).sort((a, b) => a - b);
  const lone = r => by[r].length === 1;

  if (level === 'low') {
    // 初级：多数时候甩最小单张（可能拆对），偶尔出对子
    if (ranks.length && by[ranks[0]].length >= 2 && rng() < 0.3) return by[ranks[0]].slice(0, 2);
    return [[...hand].sort(cardSort)[0]];
  }

  if (level === 'high') {
    // 高级留牌后出：优先甩非王/非2 的散牌，其次小对子，绝不主动拆炸弹、不先甩王炸/2
    const safeLones = ranks.filter(r => lone(r) && r <= 14);
    if (safeLones.length) return [by[safeLones[0]][0]];
    const pairs = ranks.filter(r => by[r].length === 2 && r <= 14);
    if (pairs.length) return by[pairs[0]].slice(0, 2);
    const lones = ranks.filter(r => lone(r) && r <= 14);
    for (let i = 0; i + 5 <= lones.length; i++) {
      let ok = true;
      for (let j = i; j < i + 5; j++) if (lones[j] !== lones[i] + (j - i)) { ok = false; break; }
      if (ok) return lones.slice(i, i + 5).map(r => by[r][0]);
    }
    const triples = ranks.filter(r => by[r].length === 3 && r <= 14);
    if (triples.length) {
      const t = triples[0];
      if (hand.length === 3) return by[t].slice(0, 3);
      const kickers = pickKicker(by, t, 1);
      if (kickers) return [...by[t].slice(0, 3), ...kickers];
      return by[t].slice(0, 3);
    }
    // 只剩对2/王/炸弹：出最小的那组（王炸和炸弹留最后）
    const two = ranks.filter(r => by[r].length >= 2 && r <= 14);
    if (two.length) return by[two[0]].slice(0, 2);
    return [[...hand].sort(cardSort)[0]];
  }

  // mid：原默认策略
  const singles = ranks.filter(r => lone(r) && r <= 14);
  for (let i = 0; i + 5 <= singles.length; i++) {
    let ok = true;
    for (let j = i; j < i + 5; j++) if (singles[j] !== singles[i] + (j - i)) { ok = false; break; }
    if (ok) return singles.slice(i, i + 5).map(r => by[r][0]);
  }
  const pair = ranks.find(r => by[r].length === 2 && r <= 14);
  if (pair !== undefined) return by[pair].slice(0, 2);
  const triple = ranks.find(r => by[r].length === 3 && r <= 14);
  if (triple !== undefined) {
    if (hand.length === 3) return by[triple].slice(0, 3);
    const kickers = pickKicker(by, triple, 1);
    if (kickers) return [...by[triple].slice(0, 3), ...kickers];
    return by[triple].slice(0, 3);
  }
  const loose = ranks.find(r => by[r].length === 1);
  if (loose !== undefined) return [by[loose][0]];
  const twoOfPair = ranks.find(r => by[r].length === 2);
  if (twoOfPair !== undefined) return [by[twoOfPair][0]];
  return [[...hand].sort(cardSort)[0]];
}

export function computePoints(base, mults, bombCount) {
  const m = mults.reduce((a, b) => a * b, 1);
  return base * m * Math.pow(2, bombCount);
}

// ---------- 对局状态机 ----------
function freshState() {
  return {
    hands: [[], [], []], kitty: [], phase: 'idle', current: 0,
    last: null, passes: 0, landlord: -1, bids: [null, null, null],
    maxBid: 0, bidStart: 0, base: 1, mults: [1, 1, 1], doubled: [false, false, false],
    bombCount: 0, started: false, finished: false,
    shown: [null, null, null],  // 每个座位最近一次动作：{cards, text} 或 {pass:true}
  };
}

export class DDZGame {
  constructor(opts = {}) {
    this.rng = opts.rng || Math.random;
    this.speed = opts.speed || [750, 850];
    this.schedule = opts.schedule || ((fn, ms) => setTimeout(fn, ms));
    this.cancel = opts.cancel || (id => clearTimeout(id));
    this.onChange = opts.onChange || (() => {});
    this.onEvent = opts.onEvent || (() => {});
    this.persistStats = opts.persistStats || (() => {});
    this.roomBase = opts.roomBase || 1;   // 场次底数（100/1000/10000/100000）
    this.redraws = 0;          // 修复4：流局计数跨重发保留（仅用户主动开局时清零）
    this.roundText = '点「开始游戏」发牌';
    this.thinking = -1;
    this.trust = false;        // 托管：轮到玩家时由 AI 代打
    this._autoPending = false; // 托管定时器防重入
    this.playsLog = [];        // 每手 {player, cards, combo}
    this.aiLevel = ['mid', 'mid', 'mid'];       // 各座位 AI 等级（0 为人类）
    this.seatMeta = [null, null, null];         // 每局随机的 AI 名字/头像/等级
    this._timers = new Set();
    this.state = freshState();
  }
  _name(p) {
    if (p === 0) return '你';
    return (this.seatMeta[p] && this.seatMeta[p].name) || NAMES[p];
  }
  // 每局随机分配 AI 名字、头像与等级（等级两两不同，保证对局风格有变化）
  _rollSeats(rng) {
    const pick = arr => arr[Math.floor(rng() * arr.length)];
    const names = [...AI_NAME_POOL];
    const n1 = names.splice(Math.floor(rng() * names.length), 1)[0];
    const n2 = names.splice(Math.floor(rng() * names.length), 1)[0];
    const lv = ['low', 'mid', 'high'];
    const l1 = lv.splice(Math.floor(rng() * lv.length), 1)[0];
    const l2 = lv[Math.floor(rng() * lv.length)];
    this.seatMeta = [
      null,
      { name: n1, avatar: pick(AI_AVATAR_POOL), color: pick(AI_COLOR_POOL), level: l1 },
      { name: n2, avatar: pick(AI_AVATAR_POOL), color: pick(AI_COLOR_POOL), level: l2 },
    ];
    this.aiLevel = ['mid', l1, l2];
  }

  _later(fn, ms) {
    // 同步调度器（测试/回放）会在赋值前执行回调，故用 let 声明兜底
    let id;
    id = this.schedule(() => { this._timers.delete(id); fn(); }, ms);
    this._timers.add(id);
    return id;
  }
  _clearTimers() { for (const id of this._timers) this.cancel(id); this._timers.clear(); this._autoPending = false; }

  snapshot() {
    const s = this.state;
    return {
      phase: s.phase, current: s.current, started: s.started, finished: s.finished,
      hands: s.hands.map(h => [...h]), kitty: [...s.kitty],
      last: s.last ? { player: s.last.player, cards: [...s.last.cards], combo: s.last.combo } : null,
      landlord: s.landlord, bids: [...s.bids], maxBid: s.maxBid,
      base: s.base, mults: [...s.mults], doubled: [...s.doubled],
      bombCount: s.bombCount, redraws: this.redraws,
      shown: s.shown.map(x => x ? { cards: x.cards ? [...x.cards] : null, text: x.text || '', pass: !!x.pass } : null),
      handCounts: s.hands.map(h => h.length),
      multTotal: s.mults.reduce((a, b) => a * b, 1),
      points: computePoints(s.base, s.mults, s.bombCount) * this.roomBase,
      roomBase: this.roomBase,
      roundText: this.roundText, thinking: this.thinking,
      trust: !!this.trust,
      springTag: !!this._springTag,
      played: this.playsLog.flatMap(p => p.cards),   // 已打出的全部牌（记牌器用）
      seatMeta: this.seatMeta.map(m => m ? { ...m } : null),  // AI 名字/头像/等级
      aiLevel: [...this.aiLevel],
    };
  }
  _emit() { this.onChange(this.snapshot()); this._maybeAuto(); }
  _sound(name) { this.onEvent({ type: 'sound', name }); }
  _info(title, message) { this.onEvent({ type: 'info', title, message }); }
  _round(t) { this.roundText = t; }

  // 用户主动开局（清空流局计数）；opts.bidStart 仅供测试注入
  startGame(opts = {}) {
    this.redraws = 0;
    this._beginRound(opts.bidStart);
  }
  _beginRound(forcedBidStart) {
    this._clearTimers();
    this.playsLog = [];
    this._rollSeats(this.rng);   // 每局随机 AI 名字/头像/等级
    this.state = freshState();
    const deck = shuffle(makeDeck(), this.rng);
    this.state.hands = [deck.slice(0, 17), deck.slice(17, 34), deck.slice(34, 51)].map(h => h.sort(cardSort));
    this.state.kitty = deck.slice(51);
    this.state.bidStart = forcedBidStart !== undefined ? forcedBidStart : Math.floor(this.rng() * 3);
    this.state.current = this.state.bidStart;
    this.state.phase = 'bid';
    this.state.started = true;
    this.thinking = -1;
    this._round(`叫地主 · 第 ${this.redraws + 1} 轮`);
    this._sound('deal');
    this._emit();
    // 修复1：起叫者是 AI 时立即调度，避免永久卡死
    if (this.state.current !== 0) this._scheduleAI();
  }

  // ---------- 叫地主 ----------
  humanBid(v) {
    const s = this.state;
    if (s.phase !== 'bid' || s.current !== 0) return;
    if (v > 0 && v <= s.maxBid) { this._info('叫分无效', `要压过 ${s.maxBid} 分才行。`); return; }
    this._commitBid(0, v);
  }
  _aiBid(p) {
    const s = this.state;
    let v = 0;
    if (s.maxBid === 0) { const r = this.rng(); v = r < 0.55 ? 1 : r < 0.7 ? 2 : r < 0.75 ? 3 : 0; }
    else if (s.maxBid < 3 && this.rng() < 0.18) v = s.maxBid + 1;
    this._commitBid(p, v);
  }
  _commitBid(p, v) {
    const s = this.state;
    s.bids[p] = v;
    if (v > s.maxBid) s.maxBid = v;
    this._round(`${this._name(p)} ${v > 0 ? `叫 ${v} 分` : '不抢'}`);
    this._sound('pass');
    if (s.bids.every(b => b !== null)) { this._resolveLandlord(); return; }
    s.current = (p + 1) % 3;
    this._emit();
    if (s.current !== 0) this._scheduleAI();
  }
  _resolveLandlord() {
    const s = this.state;
    if (s.maxBid > 0) {
      s.landlord = s.bids.indexOf(s.maxBid);
      s.base = s.maxBid;
    } else {
      this.redraws++;
      if (this.redraws < 3) {
        this._round('没人叫地主，重新发牌');
        this.onEvent({ type: 'info', title: '流局', message: `没人叫地主（${this.redraws}/3），重新发牌。` });
        this._emit();
        this._later(() => this._beginRound(), 1400);
        return;
      }
      s.landlord = Math.floor(this.rng() * 3);
      s.base = 1;
      this.onEvent({ type: 'info', title: '随机地主', message: '三轮流局，本局随机指定地主（底分 1）。' });
    }
    s.hands[s.landlord].push(...s.kitty);
    s.hands[s.landlord].sort(cardSort);
    s.phase = 'double';
    s.current = s.landlord;
    s.doubled = [false, false, false];
    this._round(`地主：${this._name(s.landlord)} · 底分 ${s.base}，开始加倍`);
    this._emit();
    if (s.current !== 0) this._scheduleAI();
  }

  // ---------- 加倍 ----------
  humanDouble(m) {
    const s = this.state;
    if (s.phase !== 'double' || s.current !== 0) return;
    this._commitDouble(0, m);
  }
  _aiDouble(p) {
    let m = 1;
    if (p === this.state.landlord) { const r = this.rng(); m = r < 0.4 ? 2 : r < 0.55 ? 4 : 1; }
    else if (this.rng() < 0.35) m = 2;
    this._commitDouble(p, m);
  }
  _commitDouble(p, m) {
    const s = this.state;
    s.mults[p] = m;
    s.doubled[p] = true;
    this._round(`${this._name(p)} ${m > 1 ? `加倍 ×${m}` : '不加倍'}（本局 ×${s.mults.reduce((a, b) => a * b, 1)}）`);
    this._sound('pass');
    // 修复3：三家都表态过后才进入出牌（原版 p===2 会漏掉玩家）
    if (s.doubled.every(Boolean)) {
      s.phase = 'play';
      s.current = s.landlord;
      s.last = null;
      s.passes = 0;
      this._round(`地主 ${this._name(s.landlord)} 先出牌`);
      this._emit();
      if (s.current !== 0) this._scheduleAI();
      return;
    }
    s.current = (p + 1) % 3;
    this._emit();
    if (s.current !== 0) this._scheduleAI();
  }

  // ---------- 出牌 ----------
  humanPlay(cards) {
    const s = this.state;
    if (s.phase !== 'play' || s.current !== 0 || s.finished) return;
    if (!cards || !cards.length) { this._info('还没有选牌', '先点选要出的牌，或用「提示」。'); return; }
    const combo = getCombo(cards);
    if (!combo) { this._info('这组牌不成立', '试试单张、对子、三张、顺子、连对、飞机或炸弹。'); return; }
    if (s.last && s.last.player !== 0 && !beats(combo, s.last.combo)) { this._info('这手牌压不过', '需要同类型更大的牌，或使用炸弹。'); return; }
    this._commitPlay(0, cards, combo);
  }
  humanPass() {
    const s = this.state;
    if (s.phase !== 'play' || s.current !== 0 || s.finished) return;
    if (!s.last || s.last.player === 0) { this._info('轮到你先出', '新一圈由你领出，不能不出。'); return; }
    this._pass(0);
  }
  // 提示：领出给 bestLead；跟牌给最小应手（含炸弹选项）
  hint() {
    const s = this.state;
    if (s.phase !== 'play' || s.current !== 0 || s.finished) return null;
    if (!s.last || s.last.player === 0) return bestLead(s.hands[0]);
    return findResponse(s.hands[0], s.last.combo, { bombs: true });
  }

  _pass(p) {
    const s = this.state;
    this._sound('pass');
    s.passes++;
    s.shown[p] = { pass: true };
    this._round(`${this._name(p)} 不出`);
    if (s.passes >= 2) {
      const leader = s.last ? s.last.player : 0;
      s.last = null;
      s.passes = 0;
      s.shown = [null, null, null];   // 新一圈：清空各座位展示
      s.current = leader;
      this._round(`新一轮 · ${this._name(leader)} 领出`);
      this._emit();
      if (leader !== 0) this._scheduleAI();
      return;
    }
    this._next();
  }
  _next() {
    const s = this.state;
    s.current = (s.current + 1) % 3;
    this._emit();
    if (s.current !== 0) this._scheduleAI();
  }
  _commitPlay(p, cards, combo) {
    const s = this.state;
    const ids = new Set(cards.map(c => c.id));
    s.hands[p] = s.hands[p].filter(c => !ids.has(c.id));
    s.hands[p].sort(cardSort);
    s.last = { player: p, cards: [...cards], combo };
    s.passes = 0;
    s.shown[p] = { cards: [...cards], text: combo.text };
    this.playsLog.push({ player: p, cards: [...cards], combo });
    if (combo.type === 'bomb' || combo.type === 'rocket') {
      s.bombCount++;   // 修复6：按次叠加
      this._sound('bomb');
    } else {
      this._sound('play');
    }
    this._round(`${this._name(p)} 出了 ${combo.text} · 倍数 ×${computePoints(s.base, s.mults, s.bombCount) / s.base / s.mults.reduce((a, b) => a * b, 1)}`);
    if (s.hands[p].length === 0) { this._emit(); this._finish(p); return; }
    this._emit();
    this._next();
  }

  // ---------- AI ----------
  _farmerMinHand() {
    return Math.min(...this.state.hands.map((h, i) => (i === this.state.landlord ? 99 : h.length)));
  }
  // 应手是否会拆炸弹（高级 AI 留牌判断）
  _breaksBomb(hand, resp) {
    const by = groupBy(hand);
    const ranks = [...new Set(resp.map(c => c.rank))];
    return ranks.some(r => by[r].length >= 4);
  }
  // 出牌决策（AI 与托管共用），返回要出的牌数组或 null（不出）
  _decidePlay(p) {
    const s = this.state;
    const hand = s.hands[p];
    if (!hand.length) return null;
    const lv = p === 0 ? 'mid' : (this.aiLevel[p] || 'mid');
    const cfg = AI_LEVELS[lv];
    const iAmLandlord = p === s.landlord;
    const threat = iAmLandlord ? this._farmerMinHand() : s.hands[s.landlord].length;
    if (!s.last || s.last.player === p) {
      return bestLead(hand, lv, this.rng);   // 分级领出：高级留牌后出
    }
    let resp = findResponse(hand, s.last.combo, { bombs: false });
    if (resp && resp.length === hand.length) return resp; // 打完即胜
    const allyOnTop = !iAmLandlord && s.last.player !== s.landlord;
    if (allyOnTop) {
      if (!cfg.cooperate) return resp && this.rng() < 0.5 ? resp : null;  // 初级不认队友
      return resp && threat <= 1 ? resp : null;
    }
    if (resp) {
      // 高级留牌：应手会拆炸弹且局势不紧 → 忍住不出
      if (cfg.retention && this._breaksBomb(hand, resp) && threat > 2 && hand.length > 4) return null;
      return resp;
    }
    resp = findResponse(hand, s.last.combo, { bombs: true });
    const bombOk = lv === 'low' ? hand.length <= 2 : (threat <= 2 || hand.length <= 6);
    return resp && bombOk ? resp : null;
  }
  _aiPlay(p) {
    const hand = this.state.hands[p];
    const play = this._decidePlay(p);
    if (play && play.length) {
      const combo = getCombo(play);
      if (combo) return this._commitPlay(p, play, combo);
    }
    this._pass(p);
  }
  _scheduleAI() {
    const p = this.state.current;
    if (p === 0) return;
    this.thinking = p;
    this._emit();
    // 高级 AI 思考更久（用于"分析"），初级快速出牌
    const lv = p === 0 ? 'mid' : (this.aiLevel[p] || 'mid');
    const spd = AI_LEVELS[lv].speed;
    this._later(() => {
      this.thinking = -1;
      const s = this.state;
      if (s.finished || s.current !== p) { this._emit(); return; }
      if (s.phase === 'bid') return this._aiBid(p);
      if (s.phase === 'double') return this._aiDouble(p);
      if (s.phase !== 'play') return;
      this._aiPlay(p);
    }, spd[0] + this.rng() * spd[1]);
  }

  // ---------- 托管（玩家由 AI 代打） ----------
  setTrust(on) {
    this.trust = !!on;
    this._emit();
  }
  _maybeAuto() {
    const s = this.state;
    if (!this.trust || this._autoPending || s.finished || s.current !== 0) return;
    if (s.phase !== 'bid' && s.phase !== 'double' && s.phase !== 'play') return;
    this._autoPending = true;
    this.thinking = 0;
    this._emit();
    this._later(() => {
      this._autoPending = false;
      this.thinking = -1;
      const s = this.state;
      if (!this.trust || s.finished || s.current !== 0) { this._emit(); return; }
      if (s.phase === 'bid') return this._aiBid(0);
      if (s.phase === 'double') return this._aiDouble(0);
      if (s.phase !== 'play') return;
      this._aiPlay(0);
    }, this.speed[0] + this.rng() * this.speed[1]);
  }

  // ---------- 结算 ----------
  _finish(winner) {
    const s = this.state;
    s.finished = true;
    s.phase = 'over';
    this._clearTimers();
    this.thinking = -1;
    const landlordWin = winner === s.landlord;
    // 春天：地主赢且两农民一张未出；反春：地主只出过一手（首局域）即输。均 ×2（与主流规则一致）
    const playedHands = [0, 1, 2].map(i => this.playsLog.filter(x => x.player === i).length);
    const dl = s.landlord, f1 = (dl + 1) % 3, f2 = (dl + 2) % 3;
    const spring = landlordWin && playedHands[f1] === 0 && playedHands[f2] === 0;
    const antiSpring = !landlordWin && playedHands[dl] <= 1;
    const springMult = spring || antiSpring ? 2 : 1;
    const pts = computePoints(s.base, s.mults, s.bombCount) * springMult * this.roomBase;
    const delta = { [dl]: 0, [f1]: 0, [f2]: 0 };
    if (landlordWin) { delta[dl] = 2 * pts; delta[f1] = -pts; delta[f2] = -pts; }
    else { delta[dl] = -2 * pts; delta[f1] = pts; delta[f2] = pts; }
    const userWon = delta[0] > 0;
    this.persistStats({ games: 1, win: userWon ? 1 : 0, points: delta[0] });
    this._sound(userWon ? 'win' : 'lose');
    const springText = spring ? ' · 春天 ×2' : antiSpring ? ' · 反春 ×2' : '';
    this._springTag = spring || antiSpring;
    this._round(`${landlordWin ? '地主' : '农民'}获胜${springText} · 底分 ${s.base} × 加倍 ${s.mults.reduce((a, b) => a * b, 1)} × 炸弹 ×${Math.pow(2, s.bombCount)} = ${pts} 分`);
    this.onEvent({
      type: 'finish',
      landlordWin, winner, pts, delta: [delta[0], delta[1], delta[2]], userWon,
      spring, antiSpring, springMult,
      title: landlordWin ? '地主获胜！' : '农民获胜！',
      message: `你 ${delta[0] >= 0 ? '+' : ''}${delta[0]} 分${springText}（${this._name(winner)} 先出完）。`,
    });
    this._emit();
  }

  // 页面卸载时调用：清理全部定时器
  destroy() {
    this._clearTimers();
    this.onChange = () => {};
    this.onEvent = () => {};
  }

  // 测试钩子：直接装载一局状态（仅自动化测试使用）
  loadScenario(partial, opts = {}) {
    this._clearTimers();
    this.state = { ...freshState(), ...partial };
    this.playsLog = [];
    this._emit();
    if (opts.runAI && this.state.current !== 0 && ['bid', 'double', 'play'].includes(this.state.phase)) this._scheduleAI();
  }
}
