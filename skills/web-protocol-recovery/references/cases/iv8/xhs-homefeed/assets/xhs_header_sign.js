function encodeUtf8(text) {
  var encoded = encodeURIComponent(text);
  var out = [];
  for (var i = 0; i < encoded.length; i++) {
    var ch = encoded.charAt(i);
    if (ch === "%") {
      out.push(parseInt(encoded.charAt(i + 1) + encoded.charAt(i + 2), 16));
      i += 2;
    } else {
      out.push(ch.charCodeAt(0));
    }
  }
  return out;
}

var b64chars = "ZmserbBoHQtNP+wOcza/LpngG8yJq42KWYj0DSfdikx3VT16IlUAFM97hECvuRX5".split("");
function tripletToBase64(num) {
  return b64chars[(num >> 18) & 63] + b64chars[(num >> 12) & 63] + b64chars[(num >> 6) & 63] + b64chars[num & 63];
}
function encodeChunk(bytes, start, end) {
  var chunks = [];
  for (var i = start; i < end; i += 3) {
    var tmp = ((bytes[i] << 16) & 0xff0000) + ((bytes[i + 1] << 8) & 65280) + (bytes[i + 2] & 255);
    chunks.push(tripletToBase64(tmp));
  }
  return chunks.join("");
}
function b64Encode(bytes) {
  var len = bytes.length;
  var extra = len % 3;
  var parts = [];
  var maxChunk = 16383;
  var end = len - extra;
  for (var i = 0; i < end; i += maxChunk) {
    parts.push(encodeChunk(bytes, i, i + maxChunk > end ? end : i + maxChunk));
  }
  var tmp;
  if (extra === 1) {
    tmp = bytes[len - 1];
    parts.push(b64chars[tmp >> 2] + b64chars[(tmp << 4) & 63] + "==");
  } else if (extra === 2) {
    tmp = (bytes[len - 2] << 8) + bytes[len - 1];
    parts.push(b64chars[tmp >> 10] + b64chars[(tmp >> 4) & 63] + b64chars[(tmp << 2) & 63] + "=");
  }
  return parts.join("");
}

function crc32Like(input) {
  var table = [];
  var poly = 0xedb88320;
  for (var n = 255, c; n >= 0; n--) {
    c = n;
    for (var k = 8; k--;) c = c & 1 ? (c >>> 1) ^ poly : c >>> 1;
    table[n] = c >>> 0;
  }
  var crc = -1;
  if (typeof input === "string") {
    for (var i = 0; i < input.length; i++) crc = table[(crc & 255) ^ input.charCodeAt(i)] ^ (crc >>> 8);
  } else {
    for (var j = 0; j < input.length; j++) crc = table[(crc & 255) ^ input[j]] ^ (crc >>> 8);
  }
  return (-1 ^ crc ^ poly);
}

function md5(text) {
  function rotateLeft(n, s) { return (n << s) | (n >>> (32 - s)); }
  function add(x, y) { var l = (x & 0xffff) + (y & 0xffff); var m = (x >> 16) + (y >> 16) + (l >> 16); return (m << 16) | (l & 0xffff); }
  function cmn(q, a, b, x, s, t) { return add(rotateLeft(add(add(a, q), add(x, t)), s), b); }
  function ff(a, b, c, d, x, s, t) { return cmn((b & c) | ((~b) & d), a, b, x, s, t); }
  function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & (~d)), a, b, x, s, t); }
  function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
  function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | (~d)), a, b, x, s, t); }
  function toWords(str) {
    var bytes = unescape(encodeURIComponent(str));
    var words = [];
    for (var i = 0; i < bytes.length; i++) words[i >> 2] |= bytes.charCodeAt(i) << ((i % 4) * 8);
    words[bytes.length >> 2] |= 0x80 << ((bytes.length % 4) * 8);
    words[(((bytes.length + 8) >> 6) * 16) + 14] = bytes.length * 8;
    return words;
  }
  function hex(num) {
    var out = "";
    for (var i = 0; i < 4; i++) out += ("0" + ((num >> (i * 8)) & 255).toString(16)).slice(-2);
    return out;
  }
  var x = toWords(text);
  var a = 1732584193, b = -271733879, c = -1732584194, d = 271733878;
  for (var i = 0; i < x.length; i += 16) {
    var olda = a, oldb = b, oldc = c, oldd = d;
    a = ff(a,b,c,d,x[i+0],7,-680876936); d = ff(d,a,b,c,x[i+1],12,-389564586); c = ff(c,d,a,b,x[i+2],17,606105819); b = ff(b,c,d,a,x[i+3],22,-1044525330);
    a = ff(a,b,c,d,x[i+4],7,-176418897); d = ff(d,a,b,c,x[i+5],12,1200080426); c = ff(c,d,a,b,x[i+6],17,-1473231341); b = ff(b,c,d,a,x[i+7],22,-45705983);
    a = ff(a,b,c,d,x[i+8],7,1770035416); d = ff(d,a,b,c,x[i+9],12,-1958414417); c = ff(c,d,a,b,x[i+10],17,-42063); b = ff(b,c,d,a,x[i+11],22,-1990404162);
    a = ff(a,b,c,d,x[i+12],7,1804603682); d = ff(d,a,b,c,x[i+13],12,-40341101); c = ff(c,d,a,b,x[i+14],17,-1502002290); b = ff(b,c,d,a,x[i+15],22,1236535329);
    a = gg(a,b,c,d,x[i+1],5,-165796510); d = gg(d,a,b,c,x[i+6],9,-1069501632); c = gg(c,d,a,b,x[i+11],14,643717713); b = gg(b,c,d,a,x[i+0],20,-373897302);
    a = gg(a,b,c,d,x[i+5],5,-701558691); d = gg(d,a,b,c,x[i+10],9,38016083); c = gg(c,d,a,b,x[i+15],14,-660478335); b = gg(b,c,d,a,x[i+4],20,-405537848);
    a = gg(a,b,c,d,x[i+9],5,568446438); d = gg(d,a,b,c,x[i+14],9,-1019803690); c = gg(c,d,a,b,x[i+3],14,-187363961); b = gg(b,c,d,a,x[i+8],20,1163531501);
    a = gg(a,b,c,d,x[i+13],5,-1444681467); d = gg(d,a,b,c,x[i+2],9,-51403784); c = gg(c,d,a,b,x[i+7],14,1735328473); b = gg(b,c,d,a,x[i+12],20,-1926607734);
    a = hh(a,b,c,d,x[i+5],4,-378558); d = hh(d,a,b,c,x[i+8],11,-2022574463); c = hh(c,d,a,b,x[i+11],16,1839030562); b = hh(b,c,d,a,x[i+14],23,-35309556);
    a = hh(a,b,c,d,x[i+1],4,-1530992060); d = hh(d,a,b,c,x[i+4],11,1272893353); c = hh(c,d,a,b,x[i+7],16,-155497632); b = hh(b,c,d,a,x[i+10],23,-1094730640);
    a = hh(a,b,c,d,x[i+13],4,681279174); d = hh(d,a,b,c,x[i+0],11,-358537222); c = hh(c,d,a,b,x[i+3],16,-722521979); b = hh(b,c,d,a,x[i+6],23,76029189);
    a = hh(a,b,c,d,x[i+9],4,-640364487); d = hh(d,a,b,c,x[i+12],11,-421815835); c = hh(c,d,a,b,x[i+15],16,530742520); b = hh(b,c,d,a,x[i+2],23,-995338651);
    a = ii(a,b,c,d,x[i+0],6,-198630844); d = ii(d,a,b,c,x[i+7],10,1126891415); c = ii(c,d,a,b,x[i+14],15,-1416354905); b = ii(b,c,d,a,x[i+5],21,-57434055);
    a = ii(a,b,c,d,x[i+12],6,1700485571); d = ii(d,a,b,c,x[i+3],10,-1894986606); c = ii(c,d,a,b,x[i+10],15,-1051523); b = ii(b,c,d,a,x[i+1],21,-2054922799);
    a = ii(a,b,c,d,x[i+8],6,1873313359); d = ii(d,a,b,c,x[i+15],10,-30611744); c = ii(c,d,a,b,x[i+6],15,-1560198380); b = ii(b,c,d,a,x[i+13],21,1309151649);
    a = ii(a,b,c,d,x[i+4],6,-145523070); d = ii(d,a,b,c,x[i+11],10,-1120210379); c = ii(c,d,a,b,x[i+2],15,718787259); b = ii(b,c,d,a,x[i+9],21,-343485551);
    a = add(a, olda); b = add(b, oldb); c = add(c, oldc); d = add(d, oldd);
  }
  return hex(a) + hex(b) + hex(c) + hex(d);
}

function seccoreSignV2(url, data) {
  var raw = url;
  if (Object.prototype.toString.call(data) === "[object Object]" || Object.prototype.toString.call(data) === "[object Array]") raw += JSON.stringify(data);
  else if (typeof data === "string") raw += data;
  var m = md5(raw);
  var w = md5(url);
  var x3 = window.mnsv2(raw, m, w);
  var p = {x0: "4.3.5", x1: "xhs-pc-web", x2: window.xsecplatform || "PC", x3: x3, x4: data ? (data === undefined ? "undefined" : typeof data) : ""};
  return "XYS_" + b64Encode(encodeUtf8(JSON.stringify(p)));
}

function xsCommon(seed) {
  var b1 = seed.b1;
  var en = {
    s0: 5,
    s1: "",
    x0: seed.b1b1 || "1",
    x1: "4.3.5",
    x2: seed.platform || "Windows",
    x3: "xhs-pc-web",
    x4: "6.12.1",
    x5: seed.a1,
    x6: "",
    x7: "",
    x8: b1,
    x9: crc32Like(b1),
    x10: Number(seed.sc || 0),
    x11: "normal",
    x12: String(seed.dsllt) + ";" + String(seed.dsl)
  };
  return {object: en, value: b64Encode(encodeUtf8(JSON.stringify(en)))};
}

function generateHeaders(payload, seed) {
  var xs = seccoreSignV2(seed.apiPath, payload);
  var common = xsCommon(seed);
  return {"X-s": xs, "X-t": String(Date.now()), "X-S-Common": common.value, "X-S-Common-Object": common.object};
}
