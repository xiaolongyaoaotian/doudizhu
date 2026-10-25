#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后端 API 端到端冒烟测试（不需要浏览器）
覆盖：注册/签到/充值/联机房间(AI推进)/出牌/结算记录/管理员(销号·代充值·导出导入)/SQLite后端
"""
import json, os, sys, time, urllib.request, urllib.parse

BASE = 'http://localhost:8080'
import time as _t
SUF = str(int(_t.time()))[-6:]   # 每次运行唯一后缀，避免历史重名
ok_n = 0
fail = []

def api(path, body=None, token=None, admin=None, method=None):
    m = method or ('POST' if body is not None else 'GET')
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=m)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('X-Token', token)
    if admin:
        req.add_header('X-Admin', admin)
    try:
        res = urllib.request.urlopen(req, timeout=10)
        return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

def ok(cond, name):
    global ok_n
    print(('PASS ' if cond else 'FAIL ') + name)
    if cond:
        ok_n += 1
    else:
        fail.append(name)

# ---------- 账号 ----------
r = api('/api/register', {'username': '压测A' + SUF + SUF, 'password': '1234'})
ok(r.get('ok'), 'register A')
TA = r['token']
r = api('/api/register', {'username': '压测B' + SUF, 'password': '1234'})
TB = r['token']
ok(r.get('ok'), 'register B')
r = api('/api/login', {'username': '压测A' + SUF + SUF, 'password': 'wrong'})
ok(not r.get('ok') and r.get('error') == '密码错误', 'wrong password rejected')
r = api('/api/checkin', token=TA, method='POST')
ok(r.get('checked') and r.get('points') == 2000, 'checkin +2000')
r = api('/api/checkin', token=TA, method='POST')
ok(not r.get('checked'), 'second checkin same day blocked')

# ---------- 充值 ----------
r = api('/api/recharge/create', {'yuan': 68, 'channel': 'wechat'}, token=TA)
ok(r.get('ok') and r.get('qrSeed'), 'recharge order + qrSeed')
r = api('/api/recharge/confirm', {'order': r['order']}, token=TA)
ok(r.get('added') == 8160 and r.get('coins') == 20160, 'recharge confirm +8160 (12000+68*100*1.2)')

# ---------- 房间联机 ----------
r = api('/api/room/create', token=TA, method='POST')
ok(r.get('ok'), 'room create')
rid = r['roomId']
r = api('/api/room/join', {'roomId': rid}, token=TB)
ok(r.get('ok') and r.get('seat') == 1, 'room B join seat 1')
r = api('/api/room/spectate', {'roomId': rid}, token=TB)
ok(r.get('ok'), 'spectate no-op for player')
r = api('/api/room/start', {'roomId': rid}, token=TA)
ok(r.get('ok'), 'room start with 2 humans + 1 AI')
gid = r['gameId']
# 像玩家一样驱动自己的回合：AI 座位由后台线程推进；B 不轮询 → 断线由 AI 接管
phase, over_state = None, None
saw_progress = False
last_counts = None
for _ in range(120):
    st = api('/api/game/state?gameId=' + gid, token=TA)['state']
    phase = st['phase']
    counts = tuple(st['handCounts'])
    if last_counts is not None and counts != last_counts:
        saw_progress = True
    last_counts = counts
    if phase == 'over':
        over_state = st
        break
    if st['current'] == st['you']:
        if phase == 'bid':
            api('/api/game/action', {'gameId': gid, 'action': 'bid', 'value': 0}, token=TA)
        elif phase == 'double':
            api('/api/game/action', {'gameId': gid, 'action': 'double', 'value': 1}, token=TA)
        elif phase == 'play':
            last = st.get('last')
            if last and last['player'] != st['you']:
                r = api('/api/game/action', {'gameId': gid, 'action': 'pass'}, token=TA)
                if not r.get('ok'):  # 我领出 → 出最小单张
                    st2 = api('/api/game/state?gameId=' + gid, token=TA)['state']
                    api('/api/game/action', {'gameId': gid, 'action': 'play', 'cards': [st2['myHand'][0]]}, token=TA)
            else:
                st2 = api('/api/game/state?gameId=' + gid, token=TA)['state']
                if st2['myHand']:
                    api('/api/game/action', {'gameId': gid, 'action': 'play', 'cards': [st2['myHand'][0]]}, token=TA)
    time.sleep(0.3)

ok(phase == 'play' or phase == 'over', f'game reached play/over (phase={phase})')
ok(saw_progress, 'turns progress (hand counts changed)')
ok(over_state is not None, 'game finished')
if over_state:
    fin = over_state.get('finish', {})
    ok('delta' in fin, f'finish payload has delta ({fin})')
r = api('/api/records', token=TA)
ok(len(r.get('records', [])) >= 1, 'settlement recorded for human player')
r = api('/api/records', token=TB)
ok(len(r.get('records', [])) >= 1, 'disconnected B AI-settled record exists')

# ---------- 管理员 ----------
r = api('/api/admin/accounts', admin='wrong')
ok(not r.get('ok'), 'admin wrong password rejected')
r = api('/api/admin/accounts', admin='admin123')
ok(r.get('ok') and len(r.get('users', [])) >= 2, 'admin list accounts')
r = api('/api/admin/recharge', {'username': '压测B' + SUF, 'coins': 5000}, admin='admin123')
ok(r.get('ok'), 'admin recharge coins')
r = api('/api/admin/records/' + urllib.parse.quote('压测B' + SUF), admin='admin123')
ok(r.get('ok'), 'admin view records')
r = api('/api/admin/delete', {'username': '压测B' + SUF}, admin='admin123')
ok(r.get('ok'), 'admin delete account')
r = api('/api/login', {'username': '压测B' + SUF, 'password': '1234'})
ok(not r.get('ok'), 'deleted account cannot login')

# ---------- SQL 导出/导入 ----------
r = api('/api/admin/export?format=sql', admin='admin123')
ok(r.get('ok') and 'INSERT INTO ddz_users' in r.get('sql', ''), 'export SQL dump')
sql = r['sql']
r = api('/api/admin/import', {'format': 'json', 'state': json.loads(json.dumps(api('/api/admin/export?format=json', admin='admin123').get('state', {})))}, admin='admin123')
ok(r.get('ok'), 'import JSON state')
print(f'\n{ok_n} passed, {len(fail)} failed')
if fail:
    print('FAILED:', fail)
    sys.exit(1)
