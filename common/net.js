// 联机网络层：REST + 轮询（uni.request；浏览器垫片下由 fetch 实现）
// 服务器地址保存在本机存储；token 会话隔离。

const NET_STORE = 'ddz-net-v1';

export function netConfig() {
  try { return uni.getStorageSync(NET_STORE) || { server: '', token: '', username: '' }; }
  catch (e) { return { server: '', token: '', username: '' }; }
}
export function setNet(cfg) {
  uni.setStorageSync(NET_STORE, { ...netConfig(), ...cfg });
}
export function installId() {
  const cfg = netConfig();
  if (!cfg.installId) {
    cfg.installId = 'i' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    setNet(cfg);
  }
  return cfg.installId;
}
export function isOnline() {
  return !!netConfig().token;
}

export function request(path, { method = 'GET', body = null, auth = true } = {}) {
  const cfg = netConfig();
  const base = (cfg.server || '').replace(/\/$/, '');
  return new Promise((resolve) => {
    if (!base) { resolve({ ok: false, error: '未配置服务器地址', offline: true }); return; }
    const header = { 'Content-Type': 'application/json', 'X-Install': installId() };
    if (auth && cfg.token) header['X-Token'] = cfg.token;
    uni.request({
      url: base + path,
      method,
      data: body || undefined,
      header,
      timeout: 8000,
      success: res => resolve(res.data && typeof res.data === 'object' ? res.data : { ok: false, error: '响应异常' }),
      fail: e => resolve({ ok: false, error: (e && e.errMsg) || '网络错误', offline: true }),
    });
  });
}

// ---------- 账户 ----------
export function serverRegister(username, password, server) {
  if (server !== undefined) setNet({ server });
  return request('/api/register', { method: 'POST', body: { username, password }, auth: false }).then(r => {
    if (r.ok) setNet({ token: r.token, username });
    return r;
  });
}
export function serverLogin(username, password, server) {
  if (server !== undefined) setNet({ server });
  return request('/api/login', { method: 'POST', body: { username, password }, auth: false }).then(r => {
    if (r.ok) setNet({ token: r.token, username });
    return r;
  });
}
export function serverProfile() {
  return request('/api/profile');
}
export function serverLogout() {
  setNet({ token: '' });
}
// 每次启动上报安装量
export function reportInstall(username) {
  return request('/api/install/report', { method: 'POST', body: { installId: installId(), username: username || netConfig().username || '' }, auth: false });
}

// ---------- 签到 / 充值 ----------
export function serverCheckin() { return request('/api/checkin', { method: 'POST' }); }
export function rechargeCreate(yuan, channel) { return request('/api/recharge/create', { method: 'POST', body: { yuan, channel } }); }
export function rechargeConfirm(order) { return request('/api/recharge/confirm', { method: 'POST', body: { order } }); }

// ---------- 记录 / FAQ ----------
export function serverRecords() { return request('/api/records'); }
export function serverFaq() { return request('/api/faq', { auth: false }); }

// ---------- 匹配 / 房间 ----------
export function matchJoin() { return request('/api/match/join', { method: 'POST' }); }
export function matchStatus() { return request('/api/match/status'); }
export function matchCancel() { return request('/api/match/cancel', { method: 'POST' }); }
export function roomCreate() { return request('/api/room/create', { method: 'POST' }); }
export function roomJoin(roomId) { return request('/api/room/join', { method: 'POST', body: { roomId } }); }
export function roomSpectate(roomId) { return request('/api/room/spectate', { method: 'POST', body: { roomId } }); }
export function roomState(roomId) { return request('/api/room/state?roomId=' + roomId); }
export function roomStart(roomId) { return request('/api/room/start', { method: 'POST', body: { roomId } }); }
export function roomLeave(roomId) { return request('/api/room/leave', { method: 'POST', body: { roomId } }); }

// ---------- 对局 ----------
export function gameState(gameId) { return request('/api/game/state?gameId=' + gameId); }
export function gameAction(gameId, action, value, cards) {
  return request('/api/game/action', { method: 'POST', body: { gameId, action, value, cards } });
}
export function gameQuit(gameId) { return request('/api/game/quit', { method: 'POST', body: { gameId } }); }
export function gameOpen(gameId) { return request('/api/game/open', { method: 'POST', body: { gameId } }); }

// 默认导出（便于页面统一调用）
export default {
  netConfig, setNet, installId, isOnline, request,
  serverRegister, serverLogin, serverProfile, serverLogout, reportInstall,
  serverCheckin, rechargeCreate, rechargeConfirm, serverRecords, serverFaq,
  matchJoin, matchStatus, matchCancel,
  roomCreate, roomJoin, roomSpectate, roomState, roomStart, roomLeave,
  gameState, gameAction, gameQuit, gameOpen,
};
