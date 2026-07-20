"""
iv8 完整配置示例

列出所有 environment 和 config 支持的配置路径及默认值。

environment: 浏览器/设备画像（"浏览器长什么样"）— 直接映射到 JS 可观测属性
config:      框架行为配置（"iv8 引擎怎么跑"）— 控制引擎内部行为

path 映射规则:
  environment={"navigator": {"userAgent": "X"}}  →  JS navigator.userAgent == "X"
  config={"time": {"mode": "system"}}            →  内部路径 config.time.mode = "system"

所有配置路径和默认值可通过 iv8.JSContext.get_defaults() 动态获取。

---

iv8 Full Configuration Reference

Lists all supported environment and config paths with default values.

environment: Browser/device profile — maps directly to JS-observable properties
config:      Engine behavior config — controls internal engine behavior

Path mapping:
  environment={"navigator": {"userAgent": "X"}}  →  JS navigator.userAgent == "X"
  config={"time": {"mode": "system"}}            →  internal path config.time.mode = "system"

All paths and defaults can be retrieved via iv8.JSContext.get_defaults().
"""

import iv8


# ============================================================
#  environment 参数 — 浏览器环境值
# ============================================================
#
#  Python dict → 转为 V8 Object → EnvironmentAccessor 按 dot-path 读取
#  未指定的字段使用内置默认值

environment = {

    # --- Location ---
    "location": {
        "protocol": "https:",
        "hostname": "localhost",
        "port": "",
        "pathname": "/",
        "href": "about:blank",
        "search": "",
        "hash": "",
        "origin": "",
    },

    # --- Navigator ---
    "navigator": {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "platform": "Win32",
        "vendor": "Google Inc.",
        "vendorSub": "",
        "productSub": "20030107",
        "appName": "Netscape",
        "appCodeName": "Mozilla",
        "product": "Gecko",
        "language": "en-US",
        "languages": ["en-US", "en"],  # 数组类型（不在标量默认表中，由 BrowserConstants 提供默认）
        "doNotTrack": "",              # "" → JS null; "1" → JS "1"
        "onLine": True,
        "cookieEnabled": True,
        "webdriver": False,
        "pdfViewerEnabled": True,
        "hardwareConcurrency": 8,
        "maxTouchPoints": 0,
        "deviceMemory": 8.0,
        "deprecatedRunAdAuctionEnforcesKAnonymity": False,

        # NavigatorUAData (User-Agent Client Hints)
        "userAgentData": {
            "platform": "Windows",
            "architecture": "x86",
            "bitness": "64",
            "model": "",
            "platformVersion": "10.0.0",
            "mobile": False,
            "wow64": False,
        },

        # NetworkInformation (navigator.connection.*)
        "connection": {
            "type": "wifi",
            "effectiveType": "4g",
            "downlinkMax": 10.0,
            "rtt": 50.0,
            "downlink": 10.0,
            "saveData": False,
        },

        "plugins": {
            "enabled": True,
        },
    },

    # --- Window ---
    "window": {
        "name": "",
        "status": "",
        "origin": "",
        "innerWidth": 1920,
        "innerHeight": 969,
        "outerWidth": 1920,
        "outerHeight": 1040,
        "screenLeft": 0,
        "screenTop": 0,
        "screenX": 0,
        "screenY": 0,
        "length": 0,
        "devicePixelRatio": 1.0,
        "scrollX": 0.0,
        "scrollY": 0.0,
        "closed": False,
        "hasOpener": False,
        "isSecureContext": True,
        "crossOriginIsolated": False,
        "originAgentCluster": False,
        "credentialless": False,
    },

    # --- Screen ---
    "screen": {
        "width": 1920,
        "height": 1080,
        "availWidth": 1920,
        "availHeight": 1040,
        "availLeft": 0,
        "availTop": 0,
        "colorDepth": 24,
        "pixelDepth": 24,
        "isExtended": False,
        "orientation": {
            "type": "landscape-primary",
            "angle": 0,
        },
    },

    # --- Document ---
    "document": {
        "domain": "",
        "referrer": "",
        "readyState": "complete",
        "visibilityState": "visible",
        "lastModified": "01/01/1970 00:00:00",
        "dir": "",
        "designMode": "off",
        "wasDiscarded": False,
        "prerendering": False,
    },

    # --- Media Queries (matchMedia / @media) ---
    "media": {
        "displayMode": "browser",
        "displayState": "normal",
        "prefersColorScheme": "light",
        "prefersContrast": "no-preference",
        "prefersReducedMotion": "no-preference",
        "prefersReducedData": "no-preference",
        "forcedColors": "none",
        "colorGamut": "srgb",
        "scripting": "enabled",
        "update": "fast",
        "pointer": "fine",
        "hover": "hover",
        "anyPointer": "fine",
        "anyHover": "hover",
        "resizable": True,
        "invertedColors": False,
        "deviceSupportsHDR": False,
    },

    # --- WebGL ---
    "webgl": {
        # 基础厂商/渲染器信息
        "VENDOR": "WebKit",
        "RENDERER": "WebKit WebGL",
        "VERSION": "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
        "SHADING_LANGUAGE_VERSION": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
        "UNMASKED_VENDOR_WEBGL": "Google Inc. (NVIDIA)",
        "UNMASKED_RENDERER_WEBGL": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 (0x00001F82) "
                                   "Direct3D11 vs_5_0 ps_5_0, D3D11)",
        # 按 WebGL 版本区分的版本/着色器语言字符串
        "version": {
            "webgl1": "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
            "webgl2": "WebGL 2.0 (OpenGL ES 3.0 Chromium)",
        },
        "shadingLanguageVersion": {
            "webgl1": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
            "webgl2": "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
        },

        # 纹理参数
        "MAX_TEXTURE_SIZE": 16384,
        "MAX_CUBE_MAP_TEXTURE_SIZE": 16384,
        "MAX_TEXTURE_IMAGE_UNITS": 16,
        "MAX_COMBINED_TEXTURE_IMAGE_UNITS": 32,
        "MAX_VERTEX_TEXTURE_IMAGE_UNITS": 16,

        # 顶点着色器参数
        "MAX_VERTEX_ATTRIBS": 16,
        "MAX_VERTEX_UNIFORM_VECTORS": 4095,
        "MAX_VARYING_VECTORS": 30,

        # 片段着色器参数
        "MAX_FRAGMENT_UNIFORM_VECTORS": 1024,

        # 渲染缓冲区参数
        "MAX_RENDERBUFFER_SIZE": 16384,
        "MAX_VIEWPORT_DIMS": {"0": 32767, "1": 32767},

        # 颜色位深度
        "RED_BITS": 8,
        "GREEN_BITS": 8,
        "BLUE_BITS": 8,
        "ALPHA_BITS": 8,
        "DEPTH_BITS": 24,
        "STENCIL_BITS": 0,
        "SUBPIXEL_BITS": 4,

        # 精度范围
        "ALIASED_LINE_WIDTH_RANGE": {"0": 1.0, "1": 1.0},
        "ALIASED_POINT_SIZE_RANGE": {"0": 1.0, "1": 1024.0},

        # 扩展参数
        "MAX_TEXTURE_MAX_ANISOTROPY_EXT": 16.0,
        "POLYGON_OFFSET_CLAMP_EXT": 0.0,

        # getShaderPrecisionFormat — 着色器精度格式
        # 路径: webgl.SHADER_PRECISION.<shader>.<precision_type>.<field>
        "SHADER_PRECISION": {
            "VERTEX_SHADER": {
                "LOW_FLOAT":    {"rangeMin": 127, "rangeMax": 127, "precision": 23},
                "MEDIUM_FLOAT": {"rangeMin": 127, "rangeMax": 127, "precision": 23},
                "HIGH_FLOAT":   {"rangeMin": 127, "rangeMax": 127, "precision": 23},
                "LOW_INT":      {"rangeMin": 31, "rangeMax": 30, "precision": 0},
                "MEDIUM_INT":   {"rangeMin": 31, "rangeMax": 30, "precision": 0},
                "HIGH_INT":     {"rangeMin": 31, "rangeMax": 30, "precision": 0},
            },
            "FRAGMENT_SHADER": {
                "LOW_FLOAT":    {"rangeMin": 127, "rangeMax": 127, "precision": 23},
                "MEDIUM_FLOAT": {"rangeMin": 127, "rangeMax": 127, "precision": 23},
                "HIGH_FLOAT":   {"rangeMin": 127, "rangeMax": 127, "precision": 23},
                "LOW_INT":      {"rangeMin": 31, "rangeMax": 30, "precision": 0},
                "MEDIUM_INT":   {"rangeMin": 31, "rangeMax": 30, "precision": 0},
                "HIGH_INT":     {"rangeMin": 31, "rangeMax": 30, "precision": 0},
            },
        },
    },

    # --- WebGL2 关键指纹参数 ---
    "webgl2": {
        "MAX_COMBINED_UNIFORM_BLOCKS": 24,
        "MAX_UNIFORM_BUFFER_BINDINGS": 24,
        "MAX_UNIFORM_BLOCK_SIZE": 65536,
        "MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS": 212988,
        "MAX_COMBINED_FRAGMENT_UNIFORM_COMPONENTS": 200704,
        "UNIFORM_BUFFER_OFFSET_ALIGNMENT": 256,
        "MAX_VERTEX_UNIFORM_COMPONENTS": 16380,
        "MAX_VERTEX_UNIFORM_BLOCKS": 12,
        "MAX_VERTEX_OUTPUT_COMPONENTS": 120,
        "MAX_VARYING_COMPONENTS": 120,
        "MAX_FRAGMENT_UNIFORM_COMPONENTS": 4096,
        "MAX_FRAGMENT_UNIFORM_BLOCKS": 12,
        "MAX_FRAGMENT_INPUT_COMPONENTS": 120,
        "MIN_PROGRAM_TEXEL_OFFSET": -8,
        "MAX_PROGRAM_TEXEL_OFFSET": 7,
        "MAX_DRAW_BUFFERS": 8,
        "MAX_COLOR_ATTACHMENTS": 8,
        "MAX_SAMPLES": 8,
        "MAX_3D_TEXTURE_SIZE": 2048,
        "MAX_ARRAY_TEXTURE_LAYERS": 2048,
        "MAX_TRANSFORM_FEEDBACK_INTERLEAVED_COMPONENTS": 120,
        "MAX_TRANSFORM_FEEDBACK_SEPARATE_ATTRIBS": 4,
        "MAX_TRANSFORM_FEEDBACK_SEPARATE_COMPONENTS": 4,
        "MAX_TEXTURE_LOD_BIAS": 2.0,
    },

    # --- WebGPU ---
    "webgpu": {
        "preferredCanvasFormat": "bgra8unorm",
        # CSV 字符串，逗号分隔（内部按逗号 split 为 Set）
        "wgslLanguageFeatures": {
            "csv": "readonly_and_readwrite_storage_textures,"
                   "packed_4x8_integer_dot_product,"
                   "unrestricted_pointer_parameters,"
                   "pointer_composite_access",
        },
        "adapterFeatures": {
            "csv": "indirect-first-instance,"
                   "depth32float-stencil8,"
                   "depth-clip-control,"
                   "shader-f16,"
                   "timestamp-query,"
                   "float32-filterable,"
                   "texture-compression-bc,"
                   "rg11b10ufloat-renderable,"
                   "bgra8unorm-storage",
        },
        "adapterInfo": {
            "vendor": "nvidia",
            "architecture": "",
            "device": "",
            "description": "",
        },
        "adapter": {
            "isFallbackAdapter": False,
            "isCompatibilityMode": False,
        },
        # adapter.limits — 基线值
        "adapterLimits": {
            "maxTextureDimension1D": 8192,
            "maxTextureDimension2D": 8192,
            "maxTextureDimension3D": 2048,
            "maxTextureArrayLayers": 256,
            "maxBindGroups": 4,
            "maxBindGroupsPlusVertexBuffers": 24,
            "maxBindingsPerBindGroup": 1000,
            "maxDynamicUniformBuffersPerPipelineLayout": 8,
            "maxDynamicStorageBuffersPerPipelineLayout": 4,
            "maxSampledTexturesPerShaderStage": 16,
            "maxSamplersPerShaderStage": 16,
            "maxStorageBuffersPerShaderStage": 8,
            "maxStorageTexturesPerShaderStage": 4,
            "maxUniformBuffersPerShaderStage": 12,
            "maxUniformBufferBindingSize": 65536,
            "maxStorageBufferBindingSize": 134217728,
            "minUniformBufferOffsetAlignment": 256,
            "minStorageBufferOffsetAlignment": 256,
            "maxVertexBuffers": 8,
            "maxBufferSize": 268435456,
            "maxVertexAttributes": 16,
            "maxVertexBufferArrayStride": 2048,
            "maxInterStageShaderComponents": 60,
            "maxInterStageShaderVariables": 16,
            "maxColorAttachments": 8,
            "maxColorAttachmentBytesPerSample": 32,
            "maxComputeWorkgroupStorageSize": 16384,
            "maxComputeInvocationsPerWorkgroup": 256,
            "maxComputeWorkgroupSizeX": 256,
            "maxComputeWorkgroupSizeY": 256,
            "maxComputeWorkgroupSizeZ": 64,
            "maxComputeWorkgroupsPerDimension": 65535,
            "minSubgroupSize": 0,
            "maxSubgroupSize": 0,
        },
    },

    # --- Chrome ---
    "chrome": {
        "loadTimes": {
            "navigationType": "Other",
            "npnNegotiatedProtocol": "h2",
            "connectionInfo": "h2",
            "wasFetchedViaSpdy": True,
            "wasNpnNegotiated": True,
            "wasAlternateProtocolAvailable": False,
        },
    },

    # --- AudioContext ---
    "audioContext": {
        "baseLatency": 0.01,
        "outputLatency": 0.02,
    },

    # --- VisualViewport ---
    "visualViewport": {
        "scale": 1.0,
        "offsetLeft": 0.0,
        "offsetTop": 0.0,
        "pageLeft": 0.0,
        "pageTop": 0.0,
    },

    # --- Storage ---
    "storage": {
        "usage": 0.0,
        "quota": 2400014910258.0,
        "persisted": False,
        "usageDetails": {
            "indexedDB": 0.0,
            "caches": 0.0,
            "serviceWorkerRegistrations": 0.0,
            "fileSystem": 0.0,
        },
    },

    # --- Geolocation ---
    "geolocation": {
        "coords": {
            "latitude": 0.0,
            "longitude": 0.0,
            "accuracy": 1.0,
        },
    },

    # --- Performance ---
    "performance": {
        "navigation": {
            "type": 0.0,
            "redirectCount": 0.0,
        },
        "memory": {
            "usedJSHeapSize": 5765120.0,
            "totalJSHeapSize": 6991872.0,
            "jsHeapSizeLimit": 4294705152.0,
        },
    },

    # --- BatteryManager ---
    "batteryManager": {
        "charging": True,
        "chargingTime": 0.0,
        "dischargingTime": float("inf"),
        "level": 1.0,
    },

    # --- History ---
    "history": {
        "length": 1,
        "scrollRestoration": "auto",
    },

    # --- Credentials ---
    "credentials": {
        "id": "",
        "type": "",
    },

    # --- Clipboard ---
    "clipboard": {
        "text": "",
    },

    # --- WebRTC ---
    "webrtc": {
        "ice": {
            "defaultHostIPv4": "192.168.0.100",
            "defaultMdnsHostname": "",
        },
    },

    # --- Video ---
    "video": {
        "defaultVideoWidth": 0,
        "defaultVideoHeight": 0,
        "webkitDecodedFrameCount": 0,
        "webkitDroppedFrameCount": 0,
    },

    # --- HTMLImageElement 默认尺寸/位置 ---
    "html": {
        "img": {
            "defaultNaturalWidth": 0.0,
            "defaultNaturalHeight": 0.0,
            "defaultX": 0.0,
            "defaultY": 0.0,
        },
    },

    # --- Canvas 环境级配置 ---
    # （canvas.fingerprint.toDataURL.* 可为不同格式设定固定指纹输出）
    "canvas": {
        "blob": {"size": 0.0},
        "fingerprint": {
            "toDataURL": {
                "png": "",
                "jpeg": "",
                "webp": "",
            },
        },
    },

    # --- Managed Device (企业管理) ---
    "managed": {
        "deviceId": "",
        "organizationName": "",
        "annotatedAssetId": "",
        "annotatedLocation": "",
        "directoryId": "",
        "hostname": "",
        "serialNumber": "",
    },
}


# ============================================================
#  config 参数 — 框架行为配置
# ============================================================
#
#  Python dict → 递归展平为 "config.X.Y" → 写入 RuntimeConfigStore
#  与 environment 独立通道，不可嵌套在 environment 中。
#
#  注意：config 只支持标量类型（str / int / float / bool），不支持数组。
#  需要传数组的配置（如 navigator.languages）请使用 environment。

config = {

    # --- 时间系统 ---
    "time": {
        "mode": "logical",  # "logical" | "system"
    },

    # --- 指纹噪声种子 ---
    # 整数，用于所有可观测噪声（timing、canvas 等）的确定性复现。
    # 不设置或省略此字段 → 使用 isolate-local 随机 seed（默认行为）。
    "fingerprint": {
        "seed": 0,  # int，0 = 固定 seed；省略此键 = 随机模式
    },

    # --- 安全策略 ---
    # "csp" 和 "csp.reportOnly" 并列在同一个 dict 中：
    # Python key 中的 "." 会被拼入 dot-path，生成正确的 config.security.csp.reportOnly 路径
    "security": {
        "csp": "",
        "csp.reportOnly": "",
        "csp.upgradeInsecureRequests": False,
        "csp.blockAllMixedContent": False,
    },

    # --- Cookie ---
    "cookies": {
        "blockThirdParty": False,
    },

    # --- WebAssembly ---
    "wasm": {
        "streaming": {
            "strictMime": True,
        },
    },

    # --- WebGL 指纹 ---
    "webgl": {
        "fingerprint": {
            "mode": "clear",  # "clear" | "seeded"
            "seed": "",
            "data": "",
        },
        "GPU_DISJOINT_EXT": False,
        "contextLost": False,
    },

    # --- Canvas 行为控制 ---
    "canvas": {
        "toDataURL": "",
        "context": {
            "2d": {"enabled": True},
            "webgl": {"enabled": True},
            "webgl2": {"enabled": True},
            "bitmaprenderer": {"enabled": True},
        },
        "toBlob": {"enabled": True},
        "transferControlToOffscreen": {"enabled": True},
        "captureStream": {
            "enabled": True,
            "id": {"format": "canvas-stream-{random}"},
        },
    },

    # --- WebGPU ---
    "webgpu": {
        "requestAdapter": {"available": True},
    },

    # --- Streams ---
    "streams": {
        "readable": {"defaultChunkSize": 65536},
    },

    # --- 媒体编解码器 ---
    "media": {
        "canPlayType": {"proprietaryCodecsEnabled": True},
    },

    # --- 权限状态 ---
    # 值域: "granted" | "denied" | "prompt"
    # 影响 navigator.permissions.query() 返回值
    "permissions": {
        # A) 自动授予类
        "accelerometer": "granted",
        "gyroscope": "granted",
        "magnetometer": "granted",
        "ambient-light-sensor": "granted",
        "background-sync": "granted",
        "midi": "granted",
        "clipboard-write": "granted",
        "screen-wake-lock": "granted",

        # B) 需用户决策类
        "geolocation": "prompt",
        "notifications": "prompt",
        "push": "prompt",
        "camera": "prompt",
        "microphone": "prompt",
        "bluetooth": "prompt",
        "persistent-storage": "prompt",
        "clipboard-read": "prompt",
        "idle-detection": "prompt",
        "nfc": "prompt",
        "storage-access": "prompt",
        "window-management": "prompt",
        "local-fonts": "prompt",
        "payment-handler": "prompt",
        "periodic-background-sync": "prompt",

        # C) 已废弃/非标准（对这些名称会 reject TypeError，
        #    框架以 "prompt" 兜底避免异常）
        "speaker": "prompt",
        "device-info": "prompt",
        "clipboard": "prompt",
        "accessibility-events": "prompt",
    },

    # --- IFrame ---
    "iframe": {
        "parentOrigin": "",
    },

    # --- 功能特征集 ---
    "features": {
        "profile": "chrome124_win",

        # Chromium Feature Flags — 默认行为
        "FencedFrames": True,
        "FencedFramesAPIChanges": False,
        "FencedFramesDefaultMode": False,
        "FencedFramesLocalUnpartitionedDataAccess": False,
        "SharedArrayBufferEnabled": False,
        "ModelExecutionAPI": True,
        "TrustedTypeBeforePolicyCreationEvent": False,
        "AdInterestGroupAPI": True,
        "Fledge": True,
        "AllowURNsInIframes": True,
        "AllowURNsInIframe": False,  # 旧拼写兼容
        "FledgeNegativeTargeting": True,
        "FledgeClearOriginJoinedAdInterestGroups": True,
        "FledgeFeatureDetection": True,
        "EnforceAnonymityExposure": True,
        "InstalledApp": True,
        "CookieDeprecationFacilitatedTesting": False,
        "AttributionReportingInterface": True,
        "SharedStorageAPIM118": True,
        "NavigationId": False,
        "CrossFramePerformanceTimeline": False,
        "CSSKeyframesRuleLength": True,
        "ManagedConfiguration": True,
        "DeviceAttributes": False,
        "Focusgroup": True,
        "FetchLaterAPI": False,
        "UACHOverrideBlank": False,
        "HTMLElementScrollParent": False,
        "LateWindowProperties": False,
        "WebGPUExperimentalFeatures": False,
        "WebGPUDeveloperFeatures": False,
    },

    # --- Model Execution ---
    "modelExecution": {
        "genericSession": {
            "availability": "no",
            "responseMode": "empty",
            "fixedResponse": "",
            "defaultTopK": 1,
            "defaultTemperature": 0.0,
        },
    },
}


# ============================================================
#  使用示例
# ============================================================

if __name__ == "__main__":
    # 1. 查看所有支持的配置路径和默认值
    defaults = iv8.JSContext.get_defaults()
    print(f"共 {len(defaults)} 个配置路径")
    for path, value in sorted(defaults.items()):
        print(f"  {path} = {value!r}")

    print("\n" + "=" * 60)

    # 2. 使用完整配置创建上下文
    with iv8.JSContext(environment=environment, config=config) as ctx:
        print("navigator.userAgent:", ctx.eval("navigator.userAgent"))
        print("screen.width:", ctx.eval("screen.width"))
        print("navigator.hardwareConcurrency:", ctx.eval("navigator.hardwareConcurrency"))
        print("navigator.webdriver:", ctx.eval("navigator.webdriver"))
        print("window.innerWidth:", ctx.eval("window.innerWidth"))

    print("\n" + "=" * 60)

    # 3. 只覆盖需要的部分（未指定的字段使用默认值）
    with iv8.JSContext(
        environment={
            "navigator": {"userAgent": "CustomBot/1.0"},
            "screen": {"width": 1440, "height": 900},
        },
        config={
            "permissions": {"geolocation": "granted"},
            "time": {"mode": "system"},
        },
    ) as ctx:
        print("自定义 UA:", ctx.eval("navigator.userAgent"))
        print("自定义屏幕:", ctx.eval("screen.width"), "x", ctx.eval("screen.height"))
