let _w;
const _h = new Array(128).fill(undefined);
_h.push(undefined, null, true, false);
function _go(idx) {
  return _h[idx];
}
let _hn = _h.length;
function _do(idx) {
  if (idx < 132) return;
  _h[idx] = _hn;
  _hn = idx;
}
function _to(idx) {
  const ret = _go(idx);
  _do(idx);
  return ret;
}
function _aho(obj) {
  if (_hn === _h.length) _h.push(_h.length + 1);
  const idx = _hn;
  _hn = _h[idx];
  _h[idx] = obj;
  return idx;
}
const _td =
  typeof TextDecoder !== "undefined"
    ? new TextDecoder("utf-8", { ignoreBOM: true, fatal: true })
    : {
        decode: () => {
          throw Error("TextDecoder not available");
        },
      };
if (typeof TextDecoder !== "undefined") {
  _td.decode();
}
let _u8 = null;
function _gu8() {
  if (_u8 === null || _u8.byteLength === 0) {
    _u8 = new Uint8Array(_w.memory.buffer);
  }
  return _u8;
}
function _gsw(ptr, len) {
  ptr = ptr >>> 0;
  return _td.decode(_gu8().subarray(ptr, ptr + len));
}
let _vl = 0;
const _te =
  typeof TextEncoder !== "undefined"
    ? new TextEncoder("utf-8")
    : {
        encode: () => {
          throw Error("TextEncoder not available");
        },
      };
const _es =
  typeof _te.encodeInto === "function"
    ? function (arg, view) {
        return _te.encodeInto(arg, view);
      }
    : function (arg, view) {
        const buf = _te.encode(arg);
        view.set(buf);
        return { read: arg.length, written: buf.length };
      };
function _psw(arg, malloc, realloc) {
  if (realloc === undefined) {
    const buf = _te.encode(arg);
    const ptr = malloc(buf.length, 1) >>> 0;
    _gu8()
      .subarray(ptr, ptr + buf.length)
      .set(buf);
    _vl = buf.length;
    return ptr;
  }
  let len = arg.length;
  let ptr = malloc(len, 1) >>> 0;
  const mem = _gu8();
  let offset = 0;
  for (; offset < len; offset++) {
    const code = arg.charCodeAt(offset);
    if (code > 0x7f) break;
    mem[ptr + offset] = code;
  }
  if (offset !== len) {
    if (offset !== 0) {
      arg = arg.slice(offset);
    }
    ptr = realloc(ptr, len, (len = offset + arg.length * 3), 1) >>> 0;
    const view = _gu8().subarray(ptr + offset, ptr + len);
    const ret = _es(arg, view);
    offset += ret.written;
    ptr = realloc(ptr, len, offset, 1) >>> 0;
  }
  _vl = offset;
  return ptr;
}
let _i32 = null;
function _gi32() {
  if (_i32 === null || _i32.byteLength === 0) {
    _i32 = new Int32Array(_w.memory.buffer);
  }
  return _i32;
}
export function generate_sign(data_json, method, timestamp, random) {
  let deferred5_0;
  let deferred5_1;
  try {
    const retptr = _w.__wbindgen_add_to_stack_pointer(-16);
    const ptr0 = _psw(data_json, _w.__wbindgen_malloc, _w.__wbindgen_realloc);
    const len0 = _vl;
    const ptr1 = _psw(method, _w.__wbindgen_malloc, _w.__wbindgen_realloc);
    const len1 = _vl;
    const ptr2 = _psw(timestamp, _w.__wbindgen_malloc, _w.__wbindgen_realloc);
    const len2 = _vl;
    const ptr3 = _psw(random, _w.__wbindgen_malloc, _w.__wbindgen_realloc);
    const len3 = _vl;
    _w.generate_sign(retptr, ptr0, len0, ptr1, len1, ptr2, len2, ptr3, len3);
    var r0 = _gi32()[retptr / 4 + 0];
    var r1 = _gi32()[retptr / 4 + 1];
    deferred5_0 = r0;
    deferred5_1 = r1;
    return _gsw(r0, r1);
  } finally {
    _w.__wbindgen_add_to_stack_pointer(16);
    _w.__wbindgen_free(deferred5_0, deferred5_1, 1);
  }
}
function _he(f, args) {
  try {
    return f.apply(this, args);
  } catch (e) {
    _w.__wbindgen_exn_store(_aho(e));
  }
}
async function __wbg_load(module, imports) {
  if (module && typeof module === "object" && typeof module.arrayBuffer === "function") {
    if (typeof WebAssembly.instantiateStreaming === "function") {
      try {
        return await WebAssembly.instantiateStreaming(module, imports);
      } catch (e) {
        if (module.headers.get("Content-Type") != "application/wasm") {
          console.warn(
            "`WebAssembly.instantiateStreaming` failed because your server does not serve wasm with `application/wasm` MIME type. Falling back to `WebAssembly.instantiate` which is slower. Original error:\n",
            e,
          );
        } else {
        }
      }
    }
    const bytes = await module.arrayBuffer();
    return await WebAssembly.instantiate(bytes, imports);
  } else {
    if (module && typeof module === "object" && module.arrayBuffer) {
      const bytes = await module.arrayBuffer();
      return await WebAssembly.instantiate(bytes, imports);
    }
    const instance = await WebAssembly.instantiate(module, imports);
    if (instance instanceof WebAssembly.Instance) {
      return { instance, module };
    } else {
      return instance;
    }
  }
}
function __wbg_get_imports() {
  const imports = {};
  imports.wbg = {};
  imports.wbg.__wbindgen_object_drop_ref = function (arg0) {
    _to(arg0);
  };
  imports.wbg.__wbg_instanceof_Window_f401953a2cf86220 = function (arg0) {
    let result;
    try {
      result = Object.prototype.toString.call(_go(arg0)) === "[object Window]";
    } catch (_) {
      result = false;
    }
    const ret = result;
    return ret;
  };
  imports.wbg.__wbg_location_2951b5ee34f19221 = function (arg0) {
    const ret = _go(arg0).location;
    return _aho(ret);
  };
  imports.wbg.__wbg_href_706b235ecfe6848c = function () {
    return _he(function (arg0, arg1) {
      const ret = _go(arg1).href;
      const ptr1 = _psw(ret, _w.__wbindgen_malloc, _w.__wbindgen_realloc);
      const len1 = _vl;
      _gi32()[arg0 / 4 + 1] = len1;
      _gi32()[arg0 / 4 + 0] = ptr1;
    }, arguments);
  };
  imports.wbg.__wbg_hostname_3d9f22c60dc5bec6 = function () {
    return _he(function (arg0, arg1) {
      const ret = _go(arg1).hostname;
      const ptr1 = _psw(ret, _w.__wbindgen_malloc, _w.__wbindgen_realloc);
      const len1 = _vl;
      _gi32()[arg0 / 4 + 1] = len1;
      _gi32()[arg0 / 4 + 0] = ptr1;
    }, arguments);
  };
  imports.wbg.__wbg_newnoargs_e258087cd0daa0ea = function (arg0, arg1) {
    const ret = new Function(_gsw(arg0, arg1));
    return _aho(ret);
  };
  imports.wbg.__wbg_self_ce0dbfc45cf2f5be = function () {
    return _he(function () {
      const ret = self.self;
      return _aho(ret);
    }, arguments);
  };
  imports.wbg.__wbg_window_c6fb939a7f436783 = function () {
    return _he(function () {
      const ret = window.window;
      return _aho(ret);
    }, arguments);
  };
  imports.wbg.__wbg_globalThis_d1e6af4856ba331b = function () {
    return _he(function () {
      const ret = globalThis.globalThis;
      return _aho(ret);
    }, arguments);
  };
  imports.wbg.__wbg_global_207b558942527489 = function () {
    return _he(function () {
      const ret = global.global;
      return _aho(ret);
    }, arguments);
  };
  imports.wbg.__wbindgen_is_undefined = function (arg0) {
    const ret = _go(arg0) === undefined;
    return ret;
  };
  imports.wbg.__wbg_call_27c0f87801dedf93 = function () {
    return _he(function (arg0, arg1) {
      const ret = _go(arg0).call(_go(arg1));
      return _aho(ret);
    }, arguments);
  };
  imports.wbg.__wbindgen_object_clone_ref = function (arg0) {
    const ret = _go(arg0);
    return _aho(ret);
  };
  imports.wbg.__wbindgen_throw = function (arg0, arg1) {
    throw new Error(_gsw(arg0, arg1));
  };
  return imports;
}
function __wbg_init_memory(imports, maybe_memory) {}
function __wbg_finalize_init(instance, module) {
  _w = instance.exports;
  __wbg_init.__wbindgen_wasm_module = module;
  _i32 = null;
  _u8 = null;
  return _w;
}
function initSync(module) {
  if (_w !== undefined) return _w;
  const imports = __wbg_get_imports();
  __wbg_init_memory(imports);
  if (!(module instanceof WebAssembly.Module)) {
    module = new WebAssembly.Module(module);
  }
  const instance = new WebAssembly.Instance(module, imports);
  return __wbg_finalize_init(instance, module);
}
async function __wbg_init(input) {
  if (_w !== undefined) return _w;
  if (typeof WebAssembly === "undefined") {
    throw new Error("WebAssembly is not supported in this browser");
  }
  if (typeof input === "undefined") {
    input = new URL("ad96acb6.wasm", import.meta.url);
  }
  const imports = __wbg_get_imports();
  if (
    typeof input === "string" ||
    (input && typeof input === "object" && typeof input.url === "string") ||
    (input && typeof input === "object" && typeof input.href === "string")
  ) {
    input = _fetchWasm(input);
  }
  __wbg_init_memory(imports);
  const { instance, module } = await __wbg_load(await input, imports);
  return __wbg_finalize_init(instance, module);
}
export { initSync };
export default __wbg_init;
async function _fetchWasm(url) {
  if (typeof fetch === "function") {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
    } catch (e) {}
  }
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", typeof url === "string" ? url : url.href || url.url || url.toString(), true);
    xhr.responseType = "arraybuffer";
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve(xhr.response)
        : reject(new Error("Failed to load WASM: " + xhr.status));
    xhr.onerror = () => reject(new Error("Failed to load WASM"));
    xhr.send();
  });
}
