// 轻量 i18n：覆盖启动页/登录弹窗/官网等入口文案；牌桌内部文案保持中文
const DICT = {
  zh: {
    brand: '牌友斗地主', enter: '进入游戏', login: '登录', register: '注册', logout: '退出登录',
    guest: '游客试玩', username: '用户名', password: '密码', forgot: '忘记密码？',
    forgot_msg: '请携带账户名联系管理员重置密码（演示环境不支持自助找回）。',
    settings: '设置', welcome: '欢迎', login_first: '请先登录', lang: 'EN',
    offline_note: '本地账户 · 数据保存在本机', server_note: '服务器账户 · 数据云端保存',
  },
  en: {
    brand: 'PaiYou DDZ', enter: 'Enter Game', login: 'Sign In', register: 'Sign Up', logout: 'Sign Out',
    guest: 'Play as Guest', username: 'Username', password: 'Password', forgot: 'Forgot password?',
    forgot_msg: 'Please contact the administrator to reset your password (demo build).',
    settings: 'Settings', welcome: 'Welcome', login_first: 'Please sign in first', lang: '中文',
    offline_note: 'Local account · data stays on this device', server_note: 'Server account · data in cloud',
  },
};
let lang = 'zh';
try { lang = uni.getStorageSync('ddz-lang') || 'zh'; } catch (e) { /* 默认中文 */ }

export function getLang() { return lang; }
export function setLang(l) {
  lang = l === 'en' ? 'en' : 'zh';
  try { uni.setStorageSync('ddz-lang', lang); } catch (e) { /* ignore */ }
}
export function t(key) {
  return (DICT[lang] && DICT[lang][key]) || (DICT.zh && DICT.zh[key]) || key;
}
export default { t, getLang, setLang };
