/**
  * @env-module navigator-fingerprint
 * @description 浏览器navigator对象模拟
 * @compatibility Chrome 80+, Firefox 75+, Edge 79+
 */

(function() {
    const profile = window.__ProfileManager__ ? window.__ProfileManager__.getSection('navigator') : {};
    const navigator = {};

    // 基础属性
    navigator.userAgent = profile.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
    navigator.appCodeName = profile.appCodeName || 'Mozilla';
    navigator.appName = profile.appName || 'Netscape';
    navigator.appVersion = profile.appVersion || '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
    navigator.platform = profile.platform || 'Win32';
    navigator.product = profile.product || 'Gecko';
    navigator.productSub = profile.productSub || '20030107';
    navigator.vendor = profile.vendor || 'Google Inc.';
    navigator.vendorSub = profile.vendorSub || '';
    navigator.buildID = profile.buildID;

    // 语言相关
    navigator.language = profile.language || 'zh-CN';
    navigator.languages = profile.languages || ['zh-CN', 'zh', 'en'];

    // 在线状态
    navigator.onLine = profile.onLine !== undefined ? profile.onLine : true;

    // Cookie
    navigator.cookieEnabled = profile.cookieEnabled !== undefined ? profile.cookieEnabled : true;

    // Do Not Track
    navigator.doNotTrack = profile.doNotTrack !== undefined ? profile.doNotTrack : null;

    // 硬件相关
    navigator.hardwareConcurrency = profile.hardwareConcurrency || 8;
    navigator.maxTouchPoints = profile.maxTouchPoints !== undefined ? profile.maxTouchPoints : 0;
    navigator.deviceMemory = profile.deviceMemory || 8;

    // 反爬虫检测关键属性
    navigator.webdriver = profile.webdriver !== undefined ? profile.webdriver : false;

    // plugins
    const pluginArray = [];
    (profile.plugins || []).forEach(function(def) {
        const plugin = {
            name: def.name,
            description: def.description,
            filename: def.filename,
            length: def.length || (def.mimeTypes ? def.mimeTypes.length : 0)
        };
        (def.mimeTypes || []).forEach(function(mimeType, index) {
            plugin[index] = {
                type: mimeType.type,
                suffixes: mimeType.suffixes || '',
                description: mimeType.description || '',
                enabledPlugin: plugin
            };
        });
        pluginArray.push(plugin);
    });
    pluginArray.item = function(index) { return pluginArray[index] || null; };
    pluginArray.namedItem = function(name) {
        for (let i = 0; i < pluginArray.length; i++) {
            if (pluginArray[i].name === name) return pluginArray[i];
        }
        return null;
    };
    pluginArray.refresh = function() {};
    navigator.plugins = pluginArray;

    // mimeTypes
    const mimeTypeArray = [];
    (profile.plugins || []).forEach(function(def) {
        (def.mimeTypes || []).forEach(function(mimeType) {
            mimeTypeArray.push({
                type: mimeType.type,
                suffixes: mimeType.suffixes || '',
                description: mimeType.description || ''
            });
        });
    });
    mimeTypeArray.item = function(index) { return mimeTypeArray[index] || null; };
    mimeTypeArray.namedItem = function(name) {
        for (let i = 0; i < mimeTypeArray.length; i++) {
            if (mimeTypeArray[i].type === name) return mimeTypeArray[i];
        }
        return null;
    };
    navigator.mimeTypes = mimeTypeArray;

    // connection
    const connection = profile.connection || {};
    navigator.connection = {
        downlink: connection.downlink !== undefined ? connection.downlink : 10,
        effectiveType: connection.effectiveType || '4g',
        onchange: null,
        rtt: connection.rtt !== undefined ? connection.rtt : 50,
        saveData: connection.saveData !== undefined ? connection.saveData : false,
        addEventListener: function() {},
        removeEventListener: function() {},
        dispatchEvent: function() { return true; }
    };

    // geolocation
    navigator.geolocation = {
        getCurrentPosition: function(success, error, options) {
            if (error) {
                error({
                    code: 1,
                    message: 'User denied Geolocation'
                });
            }
        },
        watchPosition: function(success, error, options) {
            return 0;
        },
        clearWatch: function(id) {}
    };

    // permissions
    navigator.permissions = {
        query: function(descriptor) {
            return Promise.resolve({
                name: descriptor.name,
                state: 'prompt',
                onchange: null,
                addEventListener: function() {},
                removeEventListener: function() {},
                dispatchEvent: function() { return true; }
            });
        }
    };

    // mediaDevices
    navigator.mediaDevices = {
        enumerateDevices: function() {
            return Promise.resolve([]);
        },
        getUserMedia: function(constraints) {
            return Promise.reject(new Error('NotAllowedError'));
        },
        getDisplayMedia: function(constraints) {
            return Promise.reject(new Error('NotAllowedError'));
        },
        getSupportedConstraints: function() {
            return {
                aspectRatio: true,
                deviceId: true,
                echoCancellation: true,
                facingMode: true,
                frameRate: true,
                height: true,
                width: true,
                volume: true
            };
        },
        ondevicechange: null,
        addEventListener: function() {},
        removeEventListener: function() {}
    };

    // serviceWorker
    navigator.serviceWorker = {
        controller: null,
        ready: Promise.resolve(),
        oncontrollerchange: null,
        onmessage: null,
        register: function(scriptURL, options) {
            return Promise.resolve({
                scope: '/',
                installing: null,
                waiting: null,
                active: null
            });
        },
        getRegistration: function(clientURL) {
            return Promise.resolve(undefined);
        },
        getRegistrations: function() {
            return Promise.resolve([]);
        },
        addEventListener: function() {},
        removeEventListener: function() {}
    };

    // 方法实现
    navigator.javaEnabled = function() {
        return false;
    };

    navigator.vibrate = function(pattern) {
        return true;
    };

    navigator.sendBeacon = function(url, data) {
        console.log('[sendBeacon]', url);
        return true;
    };

    navigator.registerProtocolHandler = function(scheme, url, title) {};

    navigator.unregisterProtocolHandler = function(scheme, url) {};

    // getBattery
    navigator.getBattery = function() {
        return Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1,
            onchargingchange: null,
            onchargingtimechange: null,
            ondischargingtimechange: null,
            onlevelchange: null,
            addEventListener: function() {},
            removeEventListener: function() {}
        });
    };

    // clipboard
    navigator.clipboard = {
        read: function() {
            return Promise.reject(new Error('NotAllowedError'));
        },
        readText: function() {
            return Promise.reject(new Error('NotAllowedError'));
        },
        write: function(data) {
            return Promise.reject(new Error('NotAllowedError'));
        },
        writeText: function(text) {
            return Promise.reject(new Error('NotAllowedError'));
        }
    };

    // credentials
    navigator.credentials = {
        create: function(options) {
            return Promise.resolve(null);
        },
        get: function(options) {
            return Promise.resolve(null);
        },
        preventSilentAccess: function() {
            return Promise.resolve();
        },
        store: function(credential) {
            return Promise.resolve(credential);
        }
    };

    // storage
    navigator.storage = {
        estimate: function() {
            return Promise.resolve({
                quota: 1073741824,
                usage: 0
            });
        },
        persist: function() {
            return Promise.resolve(false);
        },
        persisted: function() {
            return Promise.resolve(false);
        }
    };

    // userAgentData (新API)
    const userAgentData = profile.userAgentData || {};
    navigator.userAgentData = {
        brands: userAgentData.brands || [
            { brand: 'Not_A Brand', version: '8' },
            { brand: 'Chromium', version: '120' },
            { brand: 'Google Chrome', version: '120' }
        ],
        mobile: userAgentData.mobile !== undefined ? userAgentData.mobile : false,
        platform: userAgentData.platform || 'Windows',
        getHighEntropyValues: function(hints) {
            return Promise.resolve({
                architecture: userAgentData.architecture || 'x86',
                bitness: userAgentData.bitness || '64',
                brands: this.brands,
                fullVersionList: userAgentData.fullVersionList || [
                    { brand: 'Not_A Brand', version: '8.0.0.0' },
                    { brand: 'Chromium', version: '120.0.0.0' },
                    { brand: 'Google Chrome', version: '120.0.0.0' }
                ],
                mobile: userAgentData.mobile !== undefined ? userAgentData.mobile : false,
                model: userAgentData.model || '',
                platform: userAgentData.platform || 'Windows',
                platformVersion: userAgentData.platformVersion || '10.0.0',
                uaFullVersion: userAgentData.uaFullVersion || (userAgentData.fullVersionList && userAgentData.fullVersionList[2] ? userAgentData.fullVersionList[2].version : '120.0.0.0')
            });
        },
        toJSON: function() {
            return {
                brands: this.brands,
                mobile: this.mobile,
                platform: this.platform
            };
        }
    };

    // 挂载到window
    window.navigator = navigator;
})();
