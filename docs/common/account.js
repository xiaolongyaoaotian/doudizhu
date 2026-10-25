// 账户系统：本地多账户（离线演示），密码 SHA-256 + 盐，不联网
// 存储：ddz-accounts-v1 = { users: { name: { passHash, salt, createdAt, profile } }, last: name|null }
// profile 结构与页面使用的 DEFAULT_PROFILE 一致，实现积分/战绩/钱包/偏好按账户隔离。

const ACCOUNT_STORE = 'ddz-accounts-v1';
const LEGACY_PROFILE = 'ddz-profile-v1';   // 旧版单用户数据（首次注册时迁移）

export const DEFAULT_PROFILE = {
  name: '林间听竹', games: 0, wins: 0, points: 0, coins: 12000,
  open: false, sound: true, counter: true, style: 'bamboo', bg: 'green',
  backEmoji: '🐉', backColor: '#8a5fb0', avatarEmoji: '', avatarColor: '#1f7a5c',
  transactions: [],
};

// ---------- 纯 JS SHA-256（同步、跨端） ----------
function sha256(ascii) {
  function rightRotate(v, a) { return (v >>> a) | (v << (32 - a)); }
  const mathPow = Math.pow;
  const maxWord = mathPow(2, 32);
  let result = '';
  const words = [];
  const asciiBitLength = ascii.length * 8;
  let hash = [];
  let k = [];
  let primeCounter = 0;
  const isComposite = {};
  for (let candidate = 2; primeCounter < 64; candidate++) {
    if (!isComposite[candidate]) {
      for (let i = 0; i < 313; i += candidate) isComposite[i] = candidate;
      hash[primeCounter] = (mathPow(candidate, 0.5) * maxWord) | 0;
      k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
    }
  }
  ascii += '\x80';
  while (ascii.length % 64 - 56) ascii += '\x00';
  for (let i = 0; i < ascii.length; i++) {
    const j = ascii.charCodeAt(i);
    if (j >> 8) return '';   // 仅支持 ASCII：先做 UTF-8 编码再传入
    words[i >> 2] |= j << ((3 - i) % 4) * 8;
  }
  words[words.length] = ((asciiBitLength / maxWord) | 0);
  words[words.length] = (asciiBitLength);
  for (let j = 0; j < words.length;) {
    const w = words.slice(j, j += 16);
    const oldHash = hash;
    hash = hash.slice(0, 8);
    for (let i = 0; i < 64; i++) {
      const w15 = w[i - 15], w2 = w[i - 2];
      const a = hash[0], e = hash[4];
      const temp1 = hash[7]
        + (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25))
        + ((e & hash[5]) ^ ((~e) & hash[6]))
        + k[i]
        + (w[i] = (i < 16) ? w[i] : (
          w[i - 16]
          + (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3))
          + w[i - 7]
          + (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10))
        )) | 0;
      const temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22))
        + ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]));
      hash = [(temp1 + temp2) | 0].concat(hash);
      hash[4] = (hash[4] + temp1) | 0;
    }
    for (let i = 0; i < 8; i++) hash[i] = (hash[i] + oldHash[i]) | 0;
  }
  for (let i = 0; i < 8; i++) {
    for (let j = 3; j + 1; j--) {
      const b = (hash[i] >> (j * 8)) & 255;
      result += ((b < 16) ? 0 : '') + b.toString(16);
    }
  }
  return result;
}
function utf8(str) {
  // 简易 UTF-8 编码（供 sha256 使用）
  return unescape(encodeURIComponent(str));
}
function hashPassword(password, salt) {
  return sha256(utf8(salt + '::' + password));
}
function randomSalt() {
  let s = '';
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 16; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

// ---------- 存取 ----------
function loadAll() {
  try { return uni.getStorageSync(ACCOUNT_STORE) || { users: {}, last: null }; }
  catch (e) { return { users: {}, last: null }; }
}
function saveAll(all) {
  uni.setStorageSync(ACCOUNT_STORE, all);
}

export function listUsers() {
  return Object.keys(loadAll().users);
}

// 注册：成功返回用户名；失败抛 Error(message)
export function register(username, password) {
  const name = (username || '').trim();
  if (!name || name.length < 2 || name.length > 16) throw new Error('用户名需 2-16 个字符');
  if (!/^[A-Za-z0-9_\u4e00-\u9fa5]+$/.test(name)) throw new Error('用户名只能包含中文、字母、数字、下划线');
  if (!password || password.length < 4) throw new Error('密码至少 4 位');
  const all = loadAll();
  if (all.users[name]) throw new Error('该用户名已被注册');
  const salt = randomSalt();
  const profile = { ...DEFAULT_PROFILE, name, transactions: [] };
  // 首个注册账户：迁移旧版单机数据（若有）
  try {
    const legacy = uni.getStorageSync(LEGACY_PROFILE);
    if (legacy && typeof legacy === 'object') {
      Object.assign(profile, legacy, { name, transactions: legacy.transactions || [] });
      uni.removeStorageSync(LEGACY_PROFILE);
    }
  } catch (e) { /* 迁移失败不阻塞注册 */ }
  all.users[name] = { salt, passHash: hashPassword(password, salt), createdAt: Date.now(), profile };
  all.last = name;
  saveAll(all);
  return name;
}

// 登录：成功返回用户名；失败抛 Error(message)
export function login(username, password) {
  const all = loadAll();
  const u = all.users[(username || '').trim()];
  if (!u) throw new Error('账户不存在，请先注册');
  if (u.passHash !== hashPassword(password || '', u.salt)) throw new Error('密码错误');
  all.last = username.trim();
  saveAll(all);
  return username.trim();
}

// 游客账户（固定内置，隔离数据，无密码）
export function loginGuest() {
  const all = loadAll();
  if (!all.users['游客']) {
    all.users['游客'] = { salt: 'guest', passHash: 'guest', createdAt: Date.now(), profile: { ...DEFAULT_PROFILE, name: '游客' } };
  }
  all.last = '游客';
  saveAll(all);
  return '游客';
}

export function currentUser() {
  const all = loadAll();
  return all.last && all.users[all.last] ? all.last : null;
}

export function logout() {
  const all = loadAll();
  all.last = null;
  saveAll(all);
}

// 当前账户的 profile（未登录返回 null，由页面引导去登录）
export function getProfile() {
  const all = loadAll();
  const u = all.last && all.users[all.last];
  if (!u) return null;
  if (!u.profile) u.profile = { ...DEFAULT_PROFILE };
  return { ...DEFAULT_PROFILE, ...u.profile, transactions: u.profile.transactions || [] };
}

export function saveProfile(profile) {
  const all = loadAll();
  const u = all.last && all.users[all.last];
  if (!u) return false;
  u.profile = { ...profile };
  saveAll(all);
  return true;
}

export default { register, login, loginGuest, logout, currentUser, getProfile, saveProfile, listUsers };
