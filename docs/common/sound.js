// 音效：WebAudio 合成（无外部资源），H5 与 App(webview) 均可用
let actx = null;
let enabled = true;

export function setSoundEnabled(v) { enabled = !!v; }
export function isSoundEnabled() { return enabled; }

function beep(freq, dur, type = 'sine', gain = 0.06, when = 0) {
  if (!enabled) return;
  try {
    actx = actx || new (typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext))();
    if (!actx) return;
    const o = actx.createOscillator();
    const g = actx.createGain();
    o.type = type;
    o.frequency.value = freq;
    const at = actx.currentTime + when;
    g.gain.setValueAtTime(gain, at);
    g.gain.exponentialRampToValueAtTime(0.001, at + dur);
    o.connect(g);
    g.connect(actx.destination);
    o.start(at);
    o.stop(at + dur + 0.03);
  } catch (e) { /* 音频不可用时静默 */ }
}

export function sfx(name) {
  switch (name) {
    case 'deal': beep(290, .06, 'triangle'); beep(350, .06, 'triangle', .05, .07); beep(420, .09, 'triangle', .05, .14); break;
    case 'play': beep(520, .07, 'square', .04); break;
    case 'pass': beep(220, .09, 'sine', .05); break;
    case 'bomb': beep(160, .16, 'sawtooth', .09); beep(120, .2, 'sawtooth', .07, .1); break;
    case 'win': [523, 659, 784, 1047].forEach((f, i) => beep(f, .13, 'triangle', .08, i * .13)); break;
    case 'lose': [392, 330, 262].forEach((f, i) => beep(f, .15, 'sine', .05, i * .16)); break;
    case 'coin': beep(880, .07, 'square', .04); beep(1175, .11, 'square', .04, .08); break;
    default: break;
  }
}
