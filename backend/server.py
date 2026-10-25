#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""牌友斗地主 · 后端服务（Python 标准库，零依赖）
    python3 backend/server.py [port]
功能：账号/签到/模拟充值/对战记录/客服FAQ/管理员(账号管理·代充值·销号)/联机(匹配·房间·观战·断线重连AI接管)
数据：backend/data/db.json（JSON 持久化）
"""
import json, os, sys, time, uuid, random, hashlib, threading, re, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import db as dbmod
DATA_DIR = DATA_DIR_ = os.path.join(ROOT, 'data')
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
ADMIN_PWD = os.environ.get('DDZ_ADMIN_PWD', 'admin123')
CHECKIN_POINTS = 2000
MATCH_WAIT_SECONDS = 30
POLL_MISSED_FOR_AI = 3          # 连续 3 个周期无心跳 → AI 接管
HEARTBEAT_SECONDS = 5

# ---------------- 数据库 ----------------
_LOCK = threading.RLock()
_DB = None

def _default_db():
    return {'users': {}, 'tokens': {}, 'rooms': {}, 'queue': [],
            'announcements': [
                {'id': 'n1', 'cat': 'newest', 'title': '全体牌友 · 春天玩法火热上线，翻倍更刺激！', 'time': '2026-10-24'},
                {'id': 'n2', 'cat': 'news', 'title': '新版客户端发布：记牌器、托管机器人全面升级', 'time': '2026-10-21'},
                {'id': 'n3', 'cat': 'notice', 'title': '服务器维护公告：每周四 02:00-04:00', 'time': '2026-10-20'},
            ],
            'downloads': [
                {'platform': 'android', 'name': 'Android', 'desc': 'APK 安装包 · Android 8.0+', 'url': '/download/android.apk', 'icon': '🤖'},
                {'platform': 'ios', 'name': 'iOS', 'desc': 'App Store · iOS 12.0+', 'url': '/download/ios', 'icon': '🍎'},
                {'platform': 'windows', 'name': 'Windows', 'desc': '桌面版 · Win 10/11', 'url': '/download/android.apk', 'icon': '💻'},
                {'platform': 'web', 'name': '网页版', 'desc': '无需安装 · 打开即玩', 'url': '/h5/', 'icon': '🌐'},
            ]}

STORE = None

def _store():
    global STORE
    if STORE is None:
        STORE = dbmod.make_store()
    return STORE

def db():
    global _DB
    with _LOCK:
        if _DB is None:
            _DB = _store().load() or _default_db()
            for key, val in _default_db().items():
                _DB.setdefault(key, val)
        return _DB

def save_db():
    with _LOCK:
        _store().save(_DB)

# ---------------- 工具 ----------------
def now_ms():
    return int(time.time() * 1000)

def hash_pwd(pwd, salt):
    return hashlib.sha256((salt + '::' + pwd).encode('utf-8')).hexdigest()

def _touch_activity(u):
    now = now_ms()
    u['lastActive'] = now
    u.setdefault('activeDays', {})[time.strftime('%Y-%m-%d')] = now
    ad = u['activeDays']
    if len(ad) > 60:  # 只保留近 60 天
        for k in sorted(ad.keys())[:-60]:
            ad.pop(k)

def _touch_install(iid, user=None, platform='app'):
    installs = db().setdefault('installs', {})
    rec = installs.get(iid)
    if rec:
        rec['last'] = now_ms()
        rec['platform'] = platform
        if user:
            rec['user'] = user
    else:
        installs[iid] = {'first': now_ms(), 'last': now_ms(), 'user': user, 'platform': platform}
    if len(installs) > 5000:
        old = sorted(installs.items(), key=lambda kv: kv[1]['last'])[:500]
        for k, _ in old:
            installs.pop(k)

def new_user(name, password):
    salt = uuid.uuid4().hex[:16]
    return {'name': name, 'salt': salt, 'passHash': hash_pwd(password, salt),
            'createdAt': now_ms(), 'coins': 12000, 'points': 0, 'games': 0, 'wins': 0,
            'lastCheckin': '', 'records': [], 'banned': False, 'lastActive': now_ms(),
            'activeDays': {time.strftime('%Y-%m-%d'): now_ms()}}

# ---------------- 斗地主引擎（Python 移植：服务端权威） ----------------
SUITS = ['♠', '♥', '♣', '♦']
RANK_LABEL = {11: 'J', 12: 'Q', 13: 'K', 14: 'A', 15: '2', 16: '小王', 17: '大王'}

def card_label(c):
    return RANK_LABEL.get(c['rank'], str(c['rank'])) if not c.get('joker') else ('大王' if c['rank'] == 17 else '小王')

def card_sort(c):
    return (c['rank'], SUITS.index(c['suit']) if c['suit'] in SUITS else 9)

def make_deck():
    deck = [{'rank': r, 'suit': s, 'id': f'{s}{r}'} for r in range(3, 16) for s in SUITS]
    deck.append({'rank': 16, 'suit': '★', 'joker': True, 'id': 'joker-s'})
    deck.append({'rank': 17, 'suit': '★', 'joker': True, 'id': 'joker-b'})
    return deck

def get_combo(cards):
    if not cards:
        return None
    cs = sorted(cards, key=card_sort)
    n = len(cs)
    freq = {}
    for c in cs:
        freq[c['rank']] = freq.get(c['rank'], 0) + 1
    distinct = sorted(freq.keys())
    counts = sorted(freq.values(), reverse=True)
    def is_run(rs):
        return all(r <= 14 for r in rs) and all(rs[i] == rs[i - 1] + 1 for i in range(1, len(rs)))
    if n == 1:
        return {'type': 'single', 'high': cs[0]['rank'], 'len': 1, 'text': card_label(cs[0])}
    if n == 2 and distinct == [16, 17]:
        return {'type': 'rocket', 'high': 18, 'len': 1, 'text': '王炸'}
    if n == 2 and len(distinct) == 1:
        return {'type': 'pair', 'high': distinct[0], 'len': 1, 'text': f"{card_label(cs[0])} 对"}
    if n == 3 and len(distinct) == 1:
        return {'type': 'triple', 'high': distinct[0], 'len': 1, 'text': f"{card_label(cs[0])} 三张"}
    if n == 4 and len(distinct) == 1:
        return {'type': 'bomb', 'high': distinct[0], 'len': 1, 'text': f"{card_label(cs[0])} 炸弹"}
    if n == 4 and counts[0] == 3:
        t = next(r for r, c in freq.items() if c == 3)
        return {'type': 'triple1', 'high': t, 'len': 1, 'text': '三带一'}
    if n == 5 and counts[0] == 3 and counts[1] == 2:
        t = next(r for r, c in freq.items() if c == 3)
        return {'type': 'triple2', 'high': t, 'len': 1, 'text': '三带二'}
    if n >= 5 and len(distinct) == n and is_run(distinct):
        return {'type': 'straight', 'high': distinct[-1], 'len': n, 'text': f'{n} 张顺子'}
    if n >= 6 and n % 2 == 0 and len(distinct) == n // 2 and all(c == 2 for c in counts) and is_run(distinct):
        return {'type': 'pairrun', 'high': distinct[-1], 'len': len(distinct), 'text': f'{len(distinct)} 连对'}
    if n >= 6:
        trs = [r for r in distinct if freq[r] >= 3 and r <= 14]
        if len(trs) >= 2 and all(trs[i] == trs[i - 1] + 1 for i in range(1, len(trs))):
            high, ln = trs[-1], len(trs)
            rest = n - 3 * ln
            if rest == 0:
                return {'type': 'plane', 'high': high, 'len': ln, 'text': f'{ln} 连三'}
            if rest == ln:
                return {'type': 'plane1', 'high': high, 'len': ln, 'text': f'{ln} 连三带单'}
            if rest == 2 * ln:
                rem = [r for r in distinct if freq[r] < 3]
                if all(freq[r] % 2 == 0 for r in rem):
                    return {'type': 'plane2', 'high': high, 'len': ln, 'text': f'{ln} 连三带对'}
    return None

def beats(a, b):
    if not b:
        return True
    if a['type'] == 'rocket':
        return True
    if b['type'] == 'rocket':
        return False
    if a['type'] == 'bomb' and b['type'] == 'bomb':
        return a['high'] > b['high']
    if a['type'] == 'bomb':
        return True
    if b['type'] == 'bomb':
        return False
    return a['type'] == b['type'] and a['len'] == b['len'] and a['high'] > b['high']

def group_by(hand):
    by = {}
    for c in sorted(hand, key=card_sort):
        by.setdefault(c['rank'], []).append(c)
    return by

def any_bomb(by):
    for r in range(3, 18):
        if len(by.get(r, [])) >= 4:
            return by[r][:4]
    if by.get(16) and by.get(17):
        return [by[16][0], by[17][0]]
    return None

def find_response(hand, last, use_bombs=True):
    if not last:
        return None
    if last['type'] == 'rocket':
        return None
    by = group_by(hand)
    if last['type'] == 'bomb':
        if not use_bombs:
            return None
        for r in range(last['high'] + 1, 18):
            if len(by.get(r, [])) >= 4:
                return by[r][:4]
        return any_bomb(by)
    if last['type'] in ('single', 'pair', 'triple'):
        need = {'single': 1, 'pair': 2, 'triple': 3}[last['type']]
        for r in range(last['high'] + 1, 18):
            if len(by.get(r, [])) >= need:
                return by[r][:need]
        return any_bomb(by) if use_bombs else None
    if last['type'] in ('triple1', 'triple2'):
        need_pair = last['type'] == 'triple2'
        for r in range(last['high'] + 1, 16):
            if len(by.get(r, [])) < 3:
                continue
            group = by[r][:3]
            if need_pair:
                pair = None
                for rr in sorted(k for k in by if k != r and len(by[k]) >= 2):
                    pair = by[rr][:2]
                    break
                if not pair:
                    continue
                group += pair
            else:
                kick = next((by[x][0] for x in sorted(by) if x != r), None)
                if kick is None:
                    continue
                group.append(kick)
            if beats(get_combo(group), last):
                return group
        return any_bomb(by) if use_bombs else None
    if last['type'] in ('straight', 'pairrun'):
        per = 1 if last['type'] == 'straight' else 2
        need = last['len']
        ranks = sorted(r for r in by if r <= 14 and len(by[r]) >= per)
        for i in range(len(ranks)):
            run = [ranks[i]]
            j = i + 1
            while j < len(ranks) and ranks[j] == run[-1] + 1:
                run.append(ranks[j]); j += 1
            for k in range(0, len(run) - need + 1):
                seg = run[k:k + need]
                if seg[-1] <= last['high']:
                    continue
                cand = []
                for r in seg:
                    cand += by[r][:per]
                if beats(get_combo(cand), last):
                    return cand
        return any_bomb(by) if use_bombs else None
    if last['type'] in ('plane', 'plane1', 'plane2'):
        need = last['len']
        trs = sorted(r for r in by if r <= 14 and len(by[r]) >= 3)
        for i in range(len(trs)):
            run = [trs[i]]
            j = i + 1
            while j < len(trs) and trs[j] == run[-1] + 1:
                run.append(trs[j]); j += 1
            for k in range(0, len(run) - need + 1):
                win = run[k:k + need]
                if win[-1] <= last['high']:
                    continue
                wset = set(win)
                group = []
                for r in win:
                    group += by[r][:3]
                if last['type'] == 'plane1':
                    singles = [c for r in sorted(by) if r not in wset for c in by[r]]
                    if len(singles) < need:
                        continue
                    group += singles[:need]
                elif last['type'] == 'plane2':
                    pairs = []
                    for r in sorted(by):
                        if r not in wset and len(by[r]) >= 2:
                            pairs += by[r][:2]
                        if len(pairs) >= need * 2:
                            break
                    if len(pairs) < need * 2:
                        continue
                    group += pairs
                if beats(get_combo(group), last):
                    return group
        return any_bomb(by) if use_bombs else None
    return None

def best_lead(hand):
    whole = get_combo(hand)
    if whole:
        return list(hand)
    by = group_by(hand)
    ranks = sorted(by.keys())
    lones = [r for r in ranks if len(by[r]) == 1 and r <= 14]
    if lones:
        return [by[lones[0]][0]]
    for i in range(len(lones) - 4):
        seg = lones[i:i + 5]
        if all(seg[j] == seg[0] + j for j in range(5)):
            return [by[r][0] for r in seg]
    pairs = [r for r in ranks if len(by[r]) == 2 and r <= 14]
    if pairs:
        return by[pairs[0]][:2]
    triples = [r for r in ranks if len(by[r]) == 3 and r <= 14]
    if triples:
        t = triples[0]
        if len(hand) == 3:
            return by[t][:3]
        kick = next((by[x][0] for x in sorted(by) if x != t and len(by[x]) == 1), None)
        if kick:
            return by[t][:3] + [kick]
        return by[t][:3]
    loose = next((r for r in ranks if len(by[r]) == 1), None)
    if loose is not None:
        return [by[loose][0]]
    return [sorted(hand, key=card_sort)[0]]

def compute_points(base, mults, bombs, spring_mult=1):
    m = 1
    for x in mults:
        m *= x
    return base * m * (2 ** bombs) * spring_mult

AI_NAMES = ['半盏清茶', '夜航星子', '白鹿先生', '青衫剑客', '南山樵夫', '观棋不语']
AI_AVATARS = ['🎋', '🌿', '🌸', '🌙', '⭐', '🍵']

class Game:
    def __init__(self, game_id, players, kind, room_base=1):
        self.id = game_id
        self.kind = kind                    # 'match' | 'room'
        self.players = players              # [{seat, user|null, bot, name, avatar, color, token|null, lastSeen, missed}]
        for pl in self.players:
            pl.setdefault('open', False)    # 明牌声明：公开自己的手牌
        self.hands = [[], [], []]
        self.kitty = []
        self.phase = 'deal'                 # deal→bid→double→play→over
        self.current = 0
        self.last = None
        self.passes = 0
        self.landlord = -1
        self.bids = [None, None, None]
        self.maxBid = 0
        self.base = 1
        self.mults = [1, 1, 1]
        self.doubled = [False, False, False]
        self.bombCount = 0
        self.shown = [None, None, None]
        self.playsLog = []
        self.roundText = '发牌中'
        self.roomBase = room_base      # 场次底数（100/1000/…）
        self.startedAt = now_ms()
        self.finishedAt = None
        self.dealAt = now_ms()

    def seat_names(self):
        return [p['name'] for p in self.players]

    def deal(self):
        deck = make_deck()
        random.shuffle(deck)
        self.hands = [sorted(deck[0:17], key=card_sort), sorted(deck[17:34], key=card_sort), sorted(deck[34:51], key=card_sort)]
        self.kitty = deck[51:]
        self.phase = 'bid'
        self.current = random.randrange(3)
        self.roundText = '叫地主'

    def ai_bid(self, p):
        v = 0
        if self.maxBid == 0:
            v = 1 if random.random() < 0.55 else (2 if random.random() < 0.35 else (3 if random.random() < 0.4 else 0))
        elif self.maxBid < 3 and random.random() < 0.18:
            v = self.maxBid + 1
        self.commit_bid(p, v)

    def commit_bid(self, p, v):
        self.bids[p] = v
        if v > self.maxBid:
            self.maxBid = v
        self.roundText = f"{self.players[p]['name']} {'叫 %d 分' % v if v > 0 else '不抢'}"
        if all(b is not None for b in self.bids):
            self.resolve_landlord()
        else:
            self.current = (p + 1) % 3

    def resolve_landlord(self):
        if self.maxBid > 0:
            self.landlord = self.bids.index(self.maxBid)
            self.base = self.maxBid
        else:
            self.landlord = random.randrange(3)
            self.base = 1
        self.hands[self.landlord] += self.kitty
        self.hands[self.landlord].sort(key=card_sort)
        self.phase = 'double'
        self.current = self.landlord
        self.doubled = [False, False, False]
        self.roundText = f"地主：{self.players[self.landlord]['name']} · 底分 {self.base}"

    def commit_double(self, p, m):
        self.mults[p] = m
        self.doubled[p] = True
        self.roundText = f"{self.players[p]['name']} {'加倍 ×%d' % m if m > 1 else '不加倍'}"
        if all(self.doubled):
            self.phase = 'play'
            self.current = self.landlord
            self.last = None
            self.passes = 0
            self.roundText = f"地主 {self.players[self.landlord]['name']} 先出牌"
        else:
            self.current = (p + 1) % 3

    def commit_play(self, p, cards, combo):
        ids = {c['id'] for c in cards}
        self.hands[p] = [c for c in self.hands[p] if c['id'] not in ids]
        self.last = {'player': p, 'cards': cards, 'combo': combo}
        self.passes = 0
        self.shown[p] = {'cards': cards, 'text': combo['text']}
        self.playsLog.append({'player': p, 'cards': cards, 'combo': combo})
        if combo['type'] in ('bomb', 'rocket'):
            self.bombCount += 1
        self.roundText = f"{self.players[p]['name']} 出了 {combo['text']}"
        if not self.hands[p]:
            self.finish(p)
            return
        self.current = (p + 1) % 3

    def do_pass(self, p):
        self.passes += 1
        self.shown[p] = {'pass': True}
        self.roundText = f"{self.players[p]['name']} 不出"
        if self.passes >= 2:
            leader = self.last['player'] if self.last else 0
            self.last = None
            self.passes = 0
            self.shown = [None, None, None]
            self.current = leader
            self.roundText = f"新一轮 · {self.players[leader]['name']} 领出"
        else:
            self.current = (p + 1) % 3

    def finish(self, winner):
        self.phase = 'over'
        self.finishedAt = now_ms()
        lw = winner == self.landlord
        dl = self.landlord
        f1, f2 = (dl + 1) % 3, (dl + 2) % 3
        played_hands = [sum(1 for x in self.playsLog if x['player'] == i) for i in range(3)]
        spring = lw and played_hands[f1] == 0 and played_hands[f2] == 0
        anti = (not lw) and played_hands[dl] <= 1
        sm = 2 if (spring or anti) else 1
        pts = compute_points(self.base, self.mults, self.bombCount, sm) * self.roomBase
        delta = [0, 0, 0]
        if lw:
            delta[dl] = 2 * pts; delta[f1] = -pts; delta[f2] = -pts
        else:
            delta[dl] = -2 * pts; delta[f1] = pts; delta[f2] = pts
        self.delta = delta
        self.spring = spring
        self.antiSpring = anti
        self.finalPts = pts
        self.roundText = f"{'地主' if lw else '农民'}获胜{' · 春天 ×2' if spring else ' · 反春 ×2' if anti else ''}"
        # 记录入账（人类玩家）
        with _LOCK:
            st = db().setdefault('stats', {}).setdefault('gamesByDay', {})
            day = time.strftime('%Y-%m-%d')
            st[day] = st.get(day, 0) + 1
            for p, pl in enumerate(self.players):
                if pl['user']:
                    u = db()['users'].get(pl['user'])
                    if u:
                        u['games'] += 1
                        u['wins'] += 1 if delta[p] > 0 else 0
                        u['points'] += delta[p]
                        u['records'].insert(0, {
                            'time': now_ms(), 'kind': self.kind, 'base': self.base,
                            'mult': self.mults[0] * self.mults[1] * self.mults[2],
                            'bombs': self.bombCount, 'spring': spring or anti,
                            'landlord': dl, 'you': p, 'delta': delta[p], 'winner': winner,
                            'players': self.seat_names(),
                        })
                        del u['records'][100:]
            save_db()

    def is_bot_seat(self, p):
        return self.players[p]['bot'] or (self.players[p]['user'] and self._missed(p) >= POLL_MISSED_FOR_AI)

    def _missed(self, p):
        pl = self.players[p]
        if not pl['user']:
            return 0
        if now_ms() - pl['lastSeen'] > HEARTBEAT_SECONDS * 1000 * POLL_MISSED_FOR_AI:
            return POLL_MISSED_FOR_AI
        return 0

    def tick(self):
        """推进 AI/超时行动（由后台线程周期调用）"""
        if self.phase == 'over':
            # 30 分钟后回收
            if self.finishedAt and now_ms() - self.finishedAt > 30 * 60 * 1000:
                _GAMES.pop(self.id, None)
            return
        if self.phase == 'deal' and now_ms() - self.dealAt > 800:
            self.deal()
            return
        if self.phase in ('bid', 'double', 'play') and self.is_bot_seat(self.current):
            self._ai_act(self.current)

    def _ai_act(self, p):
        if self.phase == 'bid':
            self.ai_bid(p)
        elif self.phase == 'double':
            self.commit_double(p, 2 if (p == self.landlord and random.random() < 0.4) else 1)
        elif self.phase == 'play':
            hand = self.hands[p]
            if not self.last or self.last['player'] == p:
                play = best_lead(hand)
            else:
                play = find_response(hand, self.last['combo'], use_bombs=True)
                if play and get_combo(play) is None:
                    play = None
            if play and get_combo(play):
                self.commit_play(p, play, get_combo(play))
            else:
                self.do_pass(p)

    def state_for(self, seat):
        """seat=None 为观战视角"""
        s = {
            'gameId': self.id, 'kind': self.kind, 'phase': self.phase,
            'current': self.current, 'landlord': self.landlord, 'maxBid': self.maxBid,
            'bids': self.bids, 'base': self.base, 'mults': self.mults, 'doubled': self.doubled,
            'bombCount': self.bombCount, 'roundText': self.roundText,
            'shown': self.shown, 'handCounts': [len(h) for h in self.hands],
            'multTotal': self.mults[0] * self.mults[1] * self.mults[2],
            'roomBase': self.roomBase,
            'players': [{'seat': p['seat'], 'name': p['name'], 'avatar': p['avatar'],
                         'color': p['color'], 'bot': p['bot'], 'user': p['user'],
                         'open': bool(p.get('open')),
                         'online': (not p['user']) or (now_ms() - p['lastSeen'] < HEARTBEAT_SECONDS * 1000 * POLL_MISSED_FOR_AI)}
                        for p in self.players],
            'kitty': self.kitty if self.phase not in ('bid', 'deal') else [],
            'last': self.last,
            'over': self.phase == 'over',
        }
        if self.phase == 'over':
            s['finish'] = {'delta': getattr(self, 'delta', [0, 0, 0]), 'pts': getattr(self, 'finalPts', 0),
                           'spring': getattr(self, 'spring', False), 'antiSpring': getattr(self, 'antiSpring', False),
                           'winner': getattr(self, '_winner_seat', None)}
        open_seats = [p['seat'] for p in self.players if p.get('open')]
        s['openSeats'] = open_seats
        s['openHands'] = {str(p['seat']): self.hands[p['seat']] for p in self.players if p.get('open')}
        if seat is not None:
            s['you'] = seat
            s['myHand'] = self.hands[seat]
        else:
            s['you'] = -1
            s['myHand'] = []
        return s

# ---------------- 房间 / 匹配 ----------------
_GAMES = {}   # 对局仅存内存（进程重启即结束，不持久化）

def get_game(gid):
    return _GAMES.get(gid)

def touch_seat(game, seat):
    for p in game.players:
        if p['seat'] == seat and p['user']:
            p['lastSeen'] = now_ms()
            p['missed'] = 0

def create_game(players, kind, room_base=1):
    gid = uuid.uuid4().hex[:12]
    g = Game(gid, players, kind, room_base)
    _GAMES[gid] = g
    return g

# ---------------- HTTP 服务 ----------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        pass  # 安静模式

    # ---- 基础 ----
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Token, X-Admin, X-Install')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode('utf-8'))
        except Exception:
            return {}

    def _user(self):
        token = self.headers.get('X-Token', '')
        name = db()['tokens'].get(token)
        if not name:
            return None, None
        u = db()['users'].get(name)
        if not u or u.get('banned'):
            return None, None
        _touch_activity(u)
        iid = self.headers.get('X-Install', '')
        if iid:
            _touch_install(iid, name)
        return name, u

    def _admin(self):
        return self.headers.get('X-Admin', '') == ADMIN_PWD

    def do_OPTIONS(self):
        self._json(200, {'ok': True})

    # ---- 路由 ----
    def do_GET(self):
        from urllib.parse import unquote
        path = unquote(self.path.split('?')[0])
        try:
            if path == '/admin':
                return self._serve_file(os.path.join(ROOT, 'admin.html'), 'text/html; charset=utf-8')
            if path == '/' or path == '/web':
                return self._serve_file(os.path.join(ROOT, 'web', 'index.html'), 'text/html; charset=utf-8')
            if path == '/download/android.apk':
                body = '牌友斗地主 Android 安装包占位文件 —— 部署时替换为真实 APK。'.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="paiyou-ddz.apk.txt"')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == '/download/ios':
                self.send_response(302)
                self.send_header('Location', 'https://apps.apple.com/')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if path.startswith('/uploads/'):
                fp = os.path.join(UPLOAD_DIR, os.path.basename(path))
                if os.path.exists(fp):
                    ext = fp.rsplit('.', 1)[-1].lower()
                    ctype = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif'}.get(ext, 'application/octet-stream')
                    return self._serve_file(fp, ctype)
                return self._json(404, {'ok': False, 'error': 'file not found'})
            if path == '/h5/':
                fp = os.path.join(ROOT, 'web', 'h5', 'index.html')
                if os.path.exists(fp):
                    return self._serve_file(fp, 'text/html; charset=utf-8')
                return self._serve_file(os.path.join(ROOT, 'web', 'h5-coming.html'), 'text/html; charset=utf-8')
            if path == '/api/faq':
                return self._json(200, {'ok': True, 'faq': FAQ})
            if path.startswith('/api/player/'):
                name = path.rsplit('/', 1)[-1]
                u = db()['users'].get(name)
                if not u:
                    return self._json(404, {'ok': False, 'error': '玩家不存在'})
                return self._json(200, {'ok': True, 'player': {
                    'name': name, 'games': u['games'], 'wins': u['wins'], 'points': u['points'],
                    'rate': round(u['wins'] * 100 / u['games']) if u['games'] else 0}})
            if path == '/api/announcements':
                return self._json(200, {'ok': True, 'announcements': db().get('announcements', [])})
            if path == '/api/downloads':
                return self._json(200, {'ok': True, 'downloads': db().get('downloads', [])})
            if path == '/api/admin/announcements':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._json(200, {'ok': True, 'announcements': db().get('announcements', [])})
            if path == '/api/admin/downloads':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._json(200, {'ok': True, 'downloads': db().get('downloads', [])})
            if path == '/api/admin/uploads':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                files = []
                if os.path.isdir(UPLOAD_DIR):
                    for f in sorted(os.listdir(UPLOAD_DIR)):
                        fp = os.path.join(UPLOAD_DIR, f)
                        files.append({'file': f, 'url': '/uploads/' + f, 'size': os.path.getsize(fp), 'at': int(os.path.getmtime(fp) * 1000)})
                return self._json(200, {'ok': True, 'uploads': files})
            if path == '/api/stats':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._api_admin_stats()
            if path == '/api/admin/export':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                fmt = self.path.split('format=')[-1].split('&')[0] if 'format=' in self.path else 'json'
                if fmt == 'sql':
                    return self._json(200, {'ok': True, 'format': 'sql', 'sql': dbmod.state_to_sql(db())})
                return self._json(200, {'ok': True, 'format': 'json', 'state': db()})
            if path == '/api/profile':
                name, u = self._user()
                if not name:
                    return self._json(401, {'ok': False, 'error': '未登录'})
                return self._json(200, {'ok': True, 'user': self._user_public(u)})
            if path == '/api/records':
                name, u = self._user()
                if not name:
                    return self._json(401, {'ok': False, 'error': '未登录'})
                return self._json(200, {'ok': True, 'records': u['records'][:30]})
            if path == '/api/game/state':
                return self._api_game_state()
            if path == '/api/match/status':
                return self._api_match_status()
            if path == '/api/room/state':
                return self._api_room_state()
            if path == '/api/admin/accounts':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                users = [self._user_admin_view(u) for u in db()['users'].values()]
                return self._json(200, {'ok': True, 'users': users})
            if path.startswith('/api/admin/records/'):
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                name = path.rsplit('/', 1)[-1]
                u = db()['users'].get(name)
                if not u:
                    return self._json(404, {'ok': False, 'error': '用户不存在'})
                return self._json(200, {'ok': True, 'user': name, 'records': u['records'][:30],
                                        'points': u['points'], 'coins': u['coins'], 'games': u['games'], 'wins': u['wins']})
            return self._json(404, {'ok': False, 'error': 'not found'})
        except Exception as e:
            return self._json(500, {'ok': False, 'error': f'服务器错误: {e}'})

    def do_POST(self):
        from urllib.parse import unquote
        path = unquote(self.path.split('?')[0])
        body = self._body()
        try:
            if path == '/api/install/report':
                iid = body.get('installId') or ''
                if iid:
                    with _LOCK:
                        _touch_install(iid, body.get('username'), body.get('platform') or 'app')
                        save_db()
                return self._json(200, {'ok': True})
            if path == '/api/register':
                return self._api_register(body)
            if path == '/api/login':
                return self._api_login(body)
            if path == '/api/checkin':
                return self._api_checkin()
            if path == '/api/recharge/create':
                return self._api_recharge_create(body)
            if path == '/api/recharge/confirm':
                return self._api_recharge_confirm(body)
            if path == '/api/game/action':
                return self._api_game_action(body)
            if path == '/api/game/quit':
                return self._api_game_quit(body)
            if path == '/api/game/open':
                return self._api_game_open(body)
            if path == '/api/match/join':
                return self._api_match_join()
            if path == '/api/match/cancel':
                return self._api_match_cancel()
            if path == '/api/room/create':
                return self._api_room_create()
            if path == '/api/room/join':
                return self._api_room_join(body)
            if path == '/api/room/spectate':
                return self._api_room_spectate(body)
            if path == '/api/room/start':
                return self._api_room_start(body)
            if path == '/api/room/leave':
                return self._api_room_leave(body)
            if path == '/api/admin/announcements':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                op = body.get('op')
                anns = db().setdefault('announcements', [])
                if op == 'create':
                    anns.insert(0, {'id': uuid.uuid4().hex[:8], 'cat': body.get('cat') or 'newest',
                                    'title': (body.get('title') or '').strip()[:60], 'time': time.strftime('%Y-%m-%d')})
                elif op == 'update':
                    for a in anns:
                        if a['id'] == body.get('id'):
                            a['title'] = (body.get('title') or a['title'])[:60]
                            a['cat'] = body.get('cat') or a['cat']
                elif op == 'delete':
                    db()['announcements'] = [a for a in anns if a['id'] != body.get('id')]
                else:
                    return self._json(400, {'ok': False, 'error': '未知操作'})
                save_db()
                return self._json(200, {'ok': True, 'announcements': db()['announcements']})
            if path == '/api/admin/downloads':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                items = body.get('downloads')
                if not isinstance(items, list):
                    return self._json(400, {'ok': False, 'error': '需要 downloads 数组'})
                clean = [{'platform': d.get('platform') or 'android', 'name': (d.get('name') or '').strip()[:20],
                          'desc': (d.get('desc') or '').strip()[:40], 'url': (d.get('url') or '').strip()[:200],
                          'icon': (d.get('icon') or '').strip()[:8]} for d in items]
                db()['downloads'] = clean
                save_db()
                return self._json(200, {'ok': True, 'downloads': clean})
            if path == '/api/admin/uploads/delete':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                f = os.path.basename(body.get('file') or '')
                fp = os.path.join(UPLOAD_DIR, f)
                if os.path.exists(fp):
                    os.remove(fp)
                save_db()
                return self._json(200, {'ok': True})
            if path == '/api/upload':
                name, u = self._user()
                if not name:
                    return self._json(401, {'ok': False, 'error': '未登录'})
                data_url = body.get('dataUrl') or ''
                m = re.match(r'data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)$', data_url)
                if not m:
                    return self._json(400, {'ok': False, 'error': '仅支持 png/jpeg/webp/gif 的 base64 图片'})
                ext = 'jpg' if m.group(1) in ('jpeg', 'jpg') else m.group(1)
                raw = base64.b64decode(m.group(2))
                if len(raw) > 512 * 1024:
                    return self._json(400, {'ok': False, 'error': '图片不能超过 512KB'})
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                fid = uuid.uuid4().hex[:12] + '.' + ext
                with open(os.path.join(UPLOAD_DIR, fid), 'wb') as f:
                    f.write(raw)
                db()['users'][name].setdefault('uploads', []).append({'file': fid, 'type': body.get('type') or 'avatar', 'at': now_ms()})
                save_db()
                return self._json(200, {'ok': True, 'url': '/uploads/' + fid})
            if path == '/api/admin/recharge':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._api_admin_recharge(body)
            if path == '/api/admin/delete':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._api_admin_delete(body)
            if path == '/api/admin/import':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._api_admin_import(body)
            if path == '/api/admin/sql':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                try:
                    rows = _store().execute(body.get('sql') or '')
                    return self._json(200, {'ok': True, 'rows': rows})
                except NotImplementedError as e:
                    return self._json(400, {'ok': False, 'error': str(e)})
                except Exception as e:
                    return self._json(400, {'ok': False, 'error': f'SQL 执行失败: {e}'})
            if path == '/api/admin/points':
                if not self._admin():
                    return self._json(403, {'ok': False, 'error': '管理员密码错误'})
                return self._api_admin_points(body)
            return self._json(404, {'ok': False, 'error': 'not found'})
        except Exception as e:
            return self._json(500, {'ok': False, 'error': f'服务器错误: {e}'})

    # ---- 实现片段 ----
    def _user_public(self, u):
        return {'name': u['name'], 'coins': u['coins'], 'points': u['points'],
                'games': u['games'], 'wins': u['wins'], 'lastCheckin': u['lastCheckin'],
                'records': u['records'][:30]}

    def _user_admin_view(self, u):
        return {'name': u['name'], 'coins': u['coins'], 'points': u['points'],
                'games': u['games'], 'wins': u['wins'], 'createdAt': u['createdAt'],
                'lastCheckin': u['lastCheckin'], 'banned': u.get('banned', False),
                'records': len(u['records'])}

    def _api_register(self, body):
        name = (body.get('username') or '').strip()
        pwd = body.get('password') or ''
        if not name or len(name) < 2 or len(name) > 16 or not re.fullmatch(r'[A-Za-z0-9_\u4e00-\u9fa5]+', name):
            return self._json(400, {'ok': False, 'error': '用户名需 2-16 位中文/字母/数字/下划线'})
        if len(pwd) < 4:
            return self._json(400, {'ok': False, 'error': '密码至少 4 位'})
        with _LOCK:
            if name in db()['users']:
                return self._json(400, {'ok': False, 'error': '该用户名已被注册'})
            db()['users'][name] = new_user(name, pwd)
            save_db()
        return self._api_login({'username': name, 'password': pwd})

    def _api_login(self, body):
        name = (body.get('username') or '').strip()
        u = db()['users'].get(name)
        if not u or u.get('banned'):
            return self._json(401, {'ok': False, 'error': '账户不存在或已被封禁'})
        if u['passHash'] != hash_pwd(body.get('password') or '', u['salt']):
            return self._json(401, {'ok': False, 'error': '密码错误'})
        token = uuid.uuid4().hex
        db()['tokens'][token] = name
        save_db()
        return self._json(200, {'ok': True, 'token': token, 'user': self._user_public(u)})

    def _api_checkin(self):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        today = time.strftime('%Y-%m-%d')
        if u['lastCheckin'] == today:
            return self._json(200, {'ok': True, 'checked': False, 'points': u['points'], 'message': '今天已签到'})
        u['lastCheckin'] = today
        u['points'] += CHECKIN_POINTS
        save_db()
        return self._json(200, {'ok': True, 'checked': True, 'points': u['points'],
                                'message': f'签到成功 +{CHECKIN_POINTS} 积分'})

    def _api_recharge_create(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        yuan = int(body.get('yuan') or 0)
        channel = body.get('channel') or 'alipay'
        if yuan not in (1, 6, 30, 68, 128) or channel not in ('alipay', 'wechat'):
            return self._json(400, {'ok': False, 'error': '参数无效'})
        bonus = RECHARGE_BONUS.get(yuan, 0)
        coins = int(yuan * 100 * (1 + bonus))
        order = uuid.uuid4().hex[:16]
        db()['users'][name].setdefault('orders', {})[order] = {'yuan': yuan, 'channel': channel, 'at': now_ms(), 'done': False, 'coins': coins}
        save_db()
        return self._json(200, {'ok': True, 'order': order, 'yuan': yuan, 'channel': channel,
                                'coins': coins, 'bonus': bonus,
                                'qrSeed': f'DDZPAY:{order}:{channel}:{yuan}'})

    def _api_recharge_confirm(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        order = body.get('order') or ''
        o = u.get('orders', {}).get(order)
        if not o:
            return self._json(404, {'ok': False, 'error': '订单不存在'})
        if o['done']:
            return self._json(200, {'ok': True, 'already': True, 'coins': u['coins']})
        o['done'] = True
        coins = o.get('coins') or o['yuan'] * 100
        u['coins'] += coins
        u['points'] += coins   # 充值同步获得等额积分（可继续对局）
        u.setdefault('records_tx', []).insert(0, {'title': f"充值 ¥{o['yuan']}（{o['channel']}）", 'coins': coins, 'time': now_ms()})
        save_db()
        return self._json(200, {'ok': True, 'added': coins, 'coins': u['coins']})

    def _seat_of(self, game, name):
        for p in game.players:
            if p['user'] == name:
                return p['seat']
        return None

    def _api_game_state(self):
        name, u = self._user()
        gid = self.path.split('gameId=')[-1].split('&')[0]
        g = get_game(gid)
        if not g:
            return self._json(404, {'ok': False, 'error': '对局不存在或已结束'})
        seat = self._seat_of(g, name)
        if seat is not None:
            touch_seat(g, seat)
        return self._json(200, {'ok': True, 'state': g.state_for(seat)})

    def _api_game_action(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        g = get_game(body.get('gameId') or '')
        if not g or g.phase == 'over':
            return self._json(404, {'ok': False, 'error': '对局不存在或已结束'})
        seat = self._seat_of(g, name)
        if seat is None or seat != g.current:
            return self._json(400, {'ok': False, 'error': '还没轮到你'})
        touch_seat(g, seat)
        act = body.get('action')
        if act == 'bid':
            v = int(body.get('value') or 0)
            if g.bids[seat] is not None or (v > 0 and v <= g.maxBid):
                return self._json(400, {'ok': False, 'error': '叫分无效'})
            g.commit_bid(seat, v)
        elif act == 'double':
            m = int(body.get('value') or 1)
            g.commit_double(seat, min(4, max(1, m)))
        elif act == 'pass':
            if not g.last or g.last['player'] == seat:
                return self._json(400, {'ok': False, 'error': '轮到你先出，不能不出'})
            g.do_pass(seat)
        elif act == 'play':
            ids = {c['id'] for c in body.get('cards', [])}
            cards = [c for c in g.hands[seat] if c['id'] in ids]
            combo = get_combo(cards)
            if not combo:
                return self._json(400, {'ok': False, 'error': '这组牌不成立'})
            if g.last and g.last['player'] != seat and not beats(combo, g.last['combo']):
                return self._json(400, {'ok': False, 'error': '这手牌压不过'})
            g.commit_play(seat, cards, combo)
        else:
            return self._json(400, {'ok': False, 'error': '未知操作'})
        save_db()
        return self._json(200, {'ok': True, 'state': g.state_for(seat)})

    def _api_game_open(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        g = get_game(body.get('gameId') or '')
        if not g or g.phase == 'over':
            return self._json(404, {'ok': False, 'error': '对局不存在或已结束'})
        seat = self._seat_of(g, name)
        if seat is None:
            return self._json(400, {'ok': False, 'error': '你不在此对局中'})
        g.players[seat]['open'] = True
        save_db()
        return self._json(200, {'ok': True, 'seat': seat})

    def _api_game_quit(self, body):
        name, u = self._user()
        g = get_game(body.get('gameId') or '')
        if g and name:
            seat = self._seat_of(g, name)
            if seat is not None:
                g.players[seat]['lastSeen'] = 0   # 触发 AI 接管
        save_db()
        return self._json(200, {'ok': True})

    # ---- 匹配 ----
    def _api_match_join(self):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        with _LOCK:
            q = db()['queue']
            if any(e['user'] == name for e in q):
                pass
            else:
                q.append({'user': name, 'at': now_ms(), 'token': self.headers.get('X-Token', '')})
            # 已有可开的局？
            game = self._try_make_match()
            save_db()
        if game:
            seat = self._seat_of(game, name)
            return self._json(200, {'ok': True, 'matched': True, 'gameId': game.id, 'seat': seat})
        wait = 0
        me = next((e for e in db()['queue'] if e['user'] == name), None)
        if me:
            wait = int((now_ms() - me['at']) / 1000)
        return self._json(200, {'ok': True, 'matched': False, 'wait': wait})

    def _try_make_match(self):
        q = [e for e in db()['queue'] if e['user'] in db()['users']]
        humans = []
        for e in q:
            if e['user'] not in [h['user'] for h in humans]:
                humans.append({'user': e['user'], 'token': e['token']})
        if not humans:
            return None
        waited = (now_ms() - min(e['at'] for e in q)) / 1000
        if len(humans) < 3 and waited < MATCH_WAIT_SECONDS:
            return None
        humans = humans[:3]
        db()['queue'][:] = [e for e in db()['queue'] if e['user'] not in [h['user'] for h in humans]]
        players = []
        for i, h in enumerate(humans):
            u = db()['users'][h['user']]
            players.append({'seat': i, 'user': h['user'], 'bot': False, 'name': h['user'],
                            'avatar': '🙂', 'color': '#1f7a5c', 'token': h['token'],
                            'lastSeen': now_ms(), 'missed': 0})
        for i in range(len(players), 3):
            nm = random.choice([n for n in AI_NAMES if n not in [p['name'] for p in players]])
            players.append({'seat': i, 'user': None, 'bot': True, 'name': nm,
                            'avatar': random.choice(AI_AVATARS), 'color': '#6d7f8f',
                            'token': None, 'lastSeen': 0, 'missed': 0})
        return create_game(players, 'match')

    def _api_match_status(self):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        # 是否已被分进对局
        for g in list(_GAMES.values()):
            seat = self._seat_of(g, name)
            if seat is not None and g.phase != 'over':
                return self._json(200, {'ok': True, 'matched': True, 'gameId': g.id, 'seat': seat, 'kind': g.kind})
        return self._json(200, {'ok': True, 'matched': False})

    def _api_match_cancel(self):
        name, _ = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        db()['queue'][:] = [e for e in db()['queue'] if e['user'] != name]
        save_db()
        return self._json(200, {'ok': True})

    # ---- 房间 ----
    def _api_room_create(self):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        rb = int(self._body().get('base') or 1)
        if rb not in (1, 100, 1000, 10000, 100000):
            rb = 1
        rid = str(random.randint(100000, 999999))
        players = [{'seat': 0, 'user': name, 'bot': False, 'name': name, 'avatar': '🙂',
                    'color': '#1f7a5c', 'token': self.headers.get('X-Token', ''),
                    'lastSeen': now_ms(), 'missed': 0}]
        room = {'id': rid, 'host': name, 'players': players, 'spectators': [],
                'gameId': None, 'createdAt': now_ms(), 'started': False, 'base': rb}
        db()['rooms'][rid] = room
        save_db()
        return self._json(200, {'ok': True, 'roomId': rid, 'seat': 0})

    def _api_room_join(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        room = db()['rooms'].get(str(body.get('roomId') or ''))
        if not room:
            return self._json(404, {'ok': False, 'error': '房间不存在'})
        if any(p['user'] == name for p in room['players']):
            seat = next(p['seat'] for p in room['players'] if p['user'] == name)
            return self._json(200, {'ok': True, 'roomId': room['id'], 'seat': seat, 'rejoin': True})
        if len(room['players']) >= 3:
            return self._json(400, {'ok': False, 'error': '房间已满（3 人）'})
        if room['started']:
            return self._json(400, {'ok': False, 'error': '对局已开始，请观战'})
        seat = len(room['players'])
        room['players'].append({'seat': seat, 'user': name, 'bot': False, 'name': name,
                                'avatar': '🙂', 'color': '#3a6ea5', 'token': self.headers.get('X-Token', ''),
                                'lastSeen': now_ms(), 'missed': 0})
        save_db()
        return self._json(200, {'ok': True, 'roomId': room['id'], 'seat': seat})

    def _api_room_spectate(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        room = db()['rooms'].get(str(body.get('roomId') or ''))
        if not room:
            return self._json(404, {'ok': False, 'error': '房间不存在'})
        if name not in room['spectators'] and not any(p['user'] == name for p in room['players']):
            room['spectators'].append(name)
            save_db()
        return self._json(200, {'ok': True, 'roomId': room['id'], 'spectators': room['spectators']})

    def _api_room_state(self):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        rid = self.path.split('roomId=')[-1].split('&')[0]
        room = db()['rooms'].get(rid)
        if not room:
            return self._json(404, {'ok': False, 'error': '房间不存在'})
        if room['gameId'] and get_game(room['gameId']):
            g = get_game(room['gameId'])
            seat = self._seat_of(g, name)
            if seat is not None:
                touch_seat(g, seat)
            return self._json(200, {'ok': True, 'room': {'id': rid, 'started': room['started']},
                                    'game': g.state_for(seat)})
        return self._json(200, {'ok': True,
                                'room': {'id': rid, 'host': room['host'], 'started': False,
                                         'players': [{'seat': p['seat'], 'name': p['name'], 'user': p['user']} for p in room['players']],
                                         'spectators': room['spectators'], 'you': name}})

    def _api_room_start(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        room = db()['rooms'].get(str(body.get('roomId') or ''))
        if not room:
            return self._json(404, {'ok': False, 'error': '房间不存在'})
        if room['host'] != name:
            return self._json(403, {'ok': False, 'error': '只有房主能开始'})
        if room['started'] and room['gameId'] and get_game(room['gameId']):
            return self._json(200, {'ok': True, 'gameId': room['gameId']})
        players = []
        for i, p in enumerate(room['players']):
            players.append({'seat': i, 'user': p['user'], 'bot': False, 'name': p['name'],
                            'avatar': '🙂', 'color': '#1f7a5c', 'token': p['token'],
                            'lastSeen': now_ms(), 'missed': 0})
        for i in range(len(players), 3):
            nm = random.choice([n for n in AI_NAMES if n not in [p['name'] for p in players]])
            players.append({'seat': i, 'user': None, 'bot': True, 'name': nm,
                            'avatar': random.choice(AI_AVATARS), 'color': '#6d7f8f',
                            'token': None, 'lastSeen': 0, 'missed': 0})
        g = create_game(players, 'room', room.get('base', 1))
        room['gameId'] = g.id
        room['started'] = True
        save_db()
        return self._json(200, {'ok': True, 'gameId': g.id})

    def _api_room_leave(self, body):
        name, u = self._user()
        if not name:
            return self._json(401, {'ok': False, 'error': '未登录'})
        room = db()['rooms'].get(str(body.get('roomId') or ''))
        if room:
            room['players'] = [p for p in room['players'] if p['user'] != name]
            room['spectators'] = [s for s in room['spectators'] if s != name]
            if not room['players']:
                db()['rooms'].pop(room['id'], None)
            save_db()
        return self._json(200, {'ok': True})

    # ---- 管理员 ----
    def _api_admin_recharge(self, body):
        name = body.get('username') or ''
        u = db()['users'].get(name)
        if not u:
            return self._json(404, {'ok': False, 'error': '用户不存在'})
        coins = int(body.get('coins') or 0)
        if coins <= 0:
            return self._json(400, {'ok': False, 'error': '积分数无效'})
        u['coins'] += coins
        u.setdefault('records_tx', []).insert(0, {'title': f'管理员充值', 'coins': coins, 'time': now_ms()})
        save_db()
        return self._json(200, {'ok': True, 'coins': u['coins']})

    def _api_admin_points(self, body):
        name = body.get('username') or ''
        u = db()['users'].get(name)
        if not u:
            return self._json(404, {'ok': False, 'error': '用户不存在'})
        pts = int(body.get('points') or 0)
        u['points'] += pts
        save_db()
        return self._json(200, {'ok': True, 'points': u['points']})

    def _api_admin_import(self, body):
        global _DB
        fmt = body.get('format') or ('sql' if body.get('sql') else 'json')
        if fmt == 'json':
            state = body.get('state')
            if not state or 'users' not in state:
                return self._json(400, {'ok': False, 'error': '需要 state 字段（JSON 状态）'})
            with _LOCK:
                _DB = {**_default_db(), **state}
                save_db()
            return self._json(200, {'ok': True, 'users': len(_DB['users'])})
        # SQL：逐条执行（需要 sqlite/mysql/postgres 后端）
        sql = body.get('sql') or ''
        if not sql:
            return self._json(400, {'ok': False, 'error': '需要 sql 字段'})
        ok_n, errs = 0, []
        try:
            for stmt in sql.split(';'):
                if stmt.strip():
                    _store().execute(stmt)
                    ok_n += 1
        except NotImplementedError as e:
            return self._json(400, {'ok': False, 'error': str(e)})
        except Exception as e:
            errs.append(str(e))
        # 重新加载状态
        with _LOCK:
            _DB = None
            _DB = db()
        return self._json(200, {'ok': len(errs) == 0, 'statements': ok_n, 'errors': errs, 'users': len(_DB['users'])})

    def _api_admin_stats(self):
        users = db()['users']
        today = time.strftime('%Y-%m-%d')
        now = now_ms()
        day_ms = 86400 * 1000
        active_today = sum(1 for u in users.values() if now - u.get('lastActive', 0) < day_ms)
        active_week = sum(1 for u in users.values() if now - u.get('lastActive', 0) < 7 * day_ms)
        installs = db().get('installs', {})
        installs_today = sum(1 for r in installs.values() if now - r['first'] < day_ms)
        by_platform = {'app': 0, 'web': 0}
        for r in installs.values():
            pf = r.get('platform', 'app')
            by_platform[pf] = by_platform.get(pf, 0) + 1
        online = sum(1 for g in _GAMES.values() for p in g.players if p['user'] and now - p['lastSeen'] < 15 * 1000)
        # 近 7 天序列
        reg_series, act_series, install_series = [], [], []
        for i in range(6, -1, -1):
            day = time.strftime('%Y-%m-%d', time.localtime((now - i * day_ms) / 1000))
            reg_series.append(sum(1 for u in users.values() if time.strftime('%Y-%m-%d', time.localtime(u['createdAt'] / 1000)) == day))
            act_series.append(sum(1 for u in users.values() if u.get('activeDays', {}).get(day)))
            install_series.append(sum(1 for r in installs.values() if time.strftime('%Y-%m-%d', time.localtime(r['first'] / 1000)) == day))
        games_by_day = db().get('stats', {}).get('gamesByDay', {})
        game_series = [games_by_day.get(time.strftime('%Y-%m-%d', time.localtime((now - i * day_ms) / 1000)), 0) for i in range(6, -1, -1)]
        return self._json(200, {'ok': True, 'stats': {
            'registered': len(users), 'registeredToday': reg_series[-1],
            'activeToday': active_today, 'activeWeek': active_week, 'onlineNow': online,
            'installs': len(installs), 'installsToday': installs_today,
            'installsByPlatform': by_platform,
            'webVisits': by_platform.get('web', 0),
            'gamesTotal': sum(games_by_day.values()),
            'series': {'days': [time.strftime('%m-%d', time.localtime((now - i * day_ms) / 1000)) for i in range(6, -1, -1)],
                       'registered': reg_series, 'active': act_series, 'installs': install_series, 'games': game_series}}})

    def _api_admin_delete(self, body):
        name = body.get('username') or ''
        if name not in db()['users']:
            return self._json(404, {'ok': False, 'error': '用户不存在'})
        db()['users'].pop(name, None)
        db()['tokens'] = {t: n for t, n in db()['tokens'].items() if n != name}
        save_db()
        return self._json(200, {'ok': True})

    # ---- 静态文件 ----
    def _serve_file(self, fp, ctype):
        try:
            with open(fp, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self._json(404, {'ok': False, 'error': 'file not found'})

RECHARGE_BONUS = {1: 0, 6: 0.05, 30: 0.10, 68: 0.20, 128: 0.30}

FAQ = [
    {'q': '如何快速获得积分？', 'a': '每天登录点击「签到」领取 2000 积分；对局获胜也可以获得积分（底分×加倍×炸弹×春天倍数）。'},
    {'q': '积分和积分有什么区别？', 'a': '积分是对战成绩，随胜负增减；积分用于对局消耗与活动，通过充值或管理员发放获得，两者互相独立。'},
    {'q': '充值后积分没有到账？', 'a': '点击「已完成充值」后立刻到账；若未到账请稍后在「积分钱包」查看记录，或联系管理员人工补单。'},
    {'q': '断线了怎么办？', 'a': '重新登录后进入「联机对战」会自动重连进行中的对局；超过 3 个心跳周期未重连，系统会托管 AI 代打。'},
    {'q': '托管是什么？', 'a': '点击「托管」后由 AI 代你叫分/加倍/出牌，随时可取消。'},
    {'q': '怎么联系人工客服？', 'a': '本页面为常见问题自助服务；如需人工处理（如充值补单、账号申诉），请将账户名发给管理员。'},
]

FAQJS = json.dumps(FAQ, ensure_ascii=False)

# ---------------- 后台线程：AI 推进 + 匹配兜底 ----------------
def game_loop():
    while True:
        time.sleep(0.5)
        try:
            with _LOCK:
                for g in list(_GAMES.values()):
                    g.tick()
        except Exception as e:
            print('[game_loop]', e, file=sys.stderr)

def start_background():
    t = threading.Thread(target=game_loop, daemon=True)
    t.start()

# ---------------- 启动 ----------------
def _cli(argv):
    # python3 server.py --export-sql dump.sql / --import-sql dump.sql / --export-json f / --import-json f
    if len(argv) >= 2 and argv[0].startswith('--export'):
        st = db(); save_db()
        if argv[0] == '--export-sql':
            out = dbmod.state_to_sql(st)
        else:
            out = json.dumps(st, ensure_ascii=False, indent=2)
        with open(argv[1], 'w', encoding='utf-8') as f:
            f.write(out)
        print(f'已导出 {len(st["users"])} 个账户 → {argv[1]}')
        return True
    if len(argv) >= 2 and argv[0].startswith('--import'):
        with open(argv[1], 'r', encoding='utf-8') as f:
            content = f.read()
        if argv[0] == '--import-sql':
            for stmt in content.split(';'):
                if stmt.strip():
                    _store().execute(stmt)
        else:
            global _DB
            _DB = {**_default_db(), **json.loads(content)}
            save_db()
        print(f'已导入 → 当前账户数 {len(db()["users"])}')
        return True
    return False

if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    if args and args[0].startswith('--'):
        db(); save_db()
        if _cli(args):
            sys.exit(0)
    port = int(args[0]) if args and args[0].isdigit() else 8080
    db()
    save_db()
    start_background()
    print(f'牌友斗地主后端已启动: http://0.0.0.0:{port}  管理面板: http://localhost:{port}/admin  (管理员密码: {ADMIN_PWD})')
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
