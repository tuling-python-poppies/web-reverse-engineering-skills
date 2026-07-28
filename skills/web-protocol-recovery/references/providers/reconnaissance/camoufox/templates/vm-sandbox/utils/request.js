/**
 * 请求封装模块（VM沙箱版本）
 * 支持两阶段请求：先获取动态JS生成Cookie，再携带Cookie请求数据
 */

function assertOfflineTemplateRun() {
    throw new Error(
        'Camoufox request helper is offline-only in the skill tree. Python delivery must own live egress; ' +
        'copy/adapt this template into an approved project and inject captured fixture data instead of calling HTTP here.'
    );
}

const DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'X-Requested-With': 'XMLHttpRequest',
};

class TwoPhaseClient {
    constructor(options = {}) {
        this.baseURL = options.baseURL || '';
        this.cookies = options.cookies || {};
        this.headers = { ...DEFAULT_HEADERS, ...options.headers };
        this.delay = options.delay || 1500;

        this.fixtures = options.fixtures || {};
    }

    getCookieString() {
        return Object.entries(this.cookies).map(([k, v]) => `${k}=${v}`).join('; ');
    }

    setCookies(cookieObj) {
        Object.assign(this.cookies, cookieObj);
    }

    /**
     * 第一阶段：获取动态JS代码
     * @param {string} url - 返回JS代码的接口
     * @returns {string} JS 代码字符串
     */
    async fetchDynamicJS(url, params = {}) {
        const key = `${url}?${new URLSearchParams(params).toString()}`;
        if (Object.prototype.hasOwnProperty.call(this.fixtures, key)) return this.fixtures[key];
        if (Object.prototype.hasOwnProperty.call(this.fixtures, url)) return this.fixtures[url];
        assertOfflineTemplateRun();
    }

    /**
     * 第二阶段：携带Cookie请求数据
     */
    async fetchData(url, params = {}) {
        return this.fetchDynamicJS(url, params);
    }

    async post(url, data = {}) {
        const key = `POST ${url}`;
        if (Object.prototype.hasOwnProperty.call(this.fixtures, key)) return this.fixtures[key];
        assertOfflineTemplateRun();
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async fetchWithDelay(url, params = {}) {
        const data = await this.fetchData(url, params);
        const jitter = Math.random() * this.delay * 0.3;
        await this.sleep(this.delay + jitter);
        return data;
    }
}

module.exports = { TwoPhaseClient, DEFAULT_HEADERS, assertOfflineTemplateRun };
