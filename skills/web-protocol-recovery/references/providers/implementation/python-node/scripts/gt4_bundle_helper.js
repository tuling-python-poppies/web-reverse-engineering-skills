const fs = require('fs');
const vm = require('vm');

function loadBundle(bundlePath) {
  let code = fs.readFileSync(bundlePath, 'utf8');
  code = code.replace(
    /i\(i\[[^\]]+\]\s*=\s*16\)/,
    '(globalThis.__webpack_require__ = i, {})'
  );
  const context = { console, setTimeout, clearTimeout };
  Object.assign(context, {
    globalThis: context,
    global: context,
    self: context,
    window: context,
    navigator: {},
    document: {},
  });
  vm.createContext(context);
  vm.runInContext(code, context, { timeout: 10000, filename: bundlePath });
  if (typeof context.__webpack_require__ !== 'function') {
    throw new Error('Could not expose webpack require from bundle');
  }
  return {
    require: context.__webpack_require__,
    fixedFields: context._lib || {},
    lotRules: (context.lib && context.lib._abo) || {},
  };
}

function resolveExpression(expression, lotNumber) {
  return expression
    .replace(/n\[(\d+):(\d+)\]/g, (_, start, end) =>
      lotNumber.slice(Number(start), Number(end) + 1)
    )
    .replace(/\+/g, '');
}

function resolveLotFields(lotNumber, rules) {
  const result = {};
  for (const [keyExpression, valueExpression] of Object.entries(rules)) {
    const path = resolveExpression(keyExpression, lotNumber).split('.');
    const value = resolveExpression(valueExpression, lotNumber);
    let target = result;
    path.forEach((key, index) => {
      if (index === path.length - 1) target[key] = value;
      else target = target[key] || (target[key] = {});
    });
  }
  return result;
}

async function getBiht(input) {
  if (input.biht) {
    if (!/^\d+$/.test(String(input.biht))) throw new Error('Input biht must be digits');
    return String(input.biht);
  }
  const source = input.gctSource;
  if (typeof source !== 'string' || !source.trim()) {
    throw new Error('gctSource or biht is required; Python delivery owns GCT download');
  }
  const context = {};
  context.globalThis = context;
  context.self = context;
  vm.createContext(context);
  vm.runInContext(source, context, { timeout: 5000, filename: 'gct-source.js' });
  if (typeof context._gct !== 'function') throw new Error('GCT did not export _gct');
  const payload = { geetest: 'captcha', lang: 'zh', ep: '123' };
  context._gct(payload);
  if (!/^\d+$/.test(String(payload.biht))) throw new Error('GCT did not generate biht');
  return payload.biht;
}

async function build(input) {
  const bundle = loadBundle(input.bundle);
  const data = input.loadData;
  const detail = data.pow_detail;
  const pow = bundle.require(25).default(
    data.lot_number,
    input.captchaId,
    detail.hashfunc,
    detail.version,
    Number(detail.bits),
    detail.datetime,
    ''
  );
  const biht = await getBiht(input);
  const lotFields = resolveLotFields(data.lot_number, bundle.lotRules);
  // Re-check these version-specific environment outputs after a bundle upgrade.
  const geeGuard = {
    roe: { aup: '3', sep: '3', egp: '3', auh: '3', rew: '3', snh: '3', res: '3', cdc: '3' },
  };
  const em = { ph: 0, cp: 0, ek: '11', wd: 1, nt: 0, si: 0, sc: 0 };
  const wPayload = {
    setLeft: input.setLeft,
    passtime: input.passtime,
    userresponse: input.userresponse,
    device_id: '',
    lot_number: data.lot_number,
    pow_msg: pow.pow_msg,
    pow_sign: pow.pow_sign,
    geetest: 'captcha',
    lang: 'zh',
    ep: '123',
    biht,
    gee_guard: geeGuard,
    ...bundle.fixedFields,
    ...lotFields,
    em,
  };
  const compact = JSON.stringify(wPayload);
  const w = bundle.require(31).default(compact, { options: { pt: String(data.pt) } });
  return {
    w,
    wPayload,
    compact,
    fixedFields: bundle.fixedFields,
    lotRules: bundle.lotRules,
    lotFields,
  };
}

async function main() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  process.stdout.write(JSON.stringify(await build(input)));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
