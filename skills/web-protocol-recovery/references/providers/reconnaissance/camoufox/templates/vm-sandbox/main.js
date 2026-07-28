/**
 * 主脚本模板 - VM 沙箱执行
 * 
 * Evidence-only template: copy into an approved project and adapt before use.
 * Do not run from the skill tree and do not use this as final live egress.
 * Python delivery must own live egress after web-protocol-recovery accepts it.
 *
 * 适用场景：服务端返回混淆JS用于生成Cookie/Token
 * 流程：
 *   1. 请求接口 → 返回混淆 JS
 *   2. VM 沙箱执行 JS → 提取 Cookie
 *   3. 携带 Cookie 请求数据接口
 * 
 * TODO: 根据逆向分析结果修改配置和逻辑
 */

const { executeAndExtractCookie } = require('./utils/sandbox');
const { TwoPhaseClient } = require('./utils/request');

function assertOfflineTemplateRun() {
    // offline-only template: live HTTP belongs to python-collector delivery.
    return true;
}

// ============ 配置区域 ============

const CONFIG = {
    name: '示例项目 - 动态Cookie',
    description: 'single approved artifact probe',
    
    baseURL: 'https://target.com',
    
    // 第一阶段：获取动态JS的接口
    jsEndpoint: '/api/init',
    
    // 第二阶段：数据接口
    dataEndpoint: '/api/data',
    
    referer: 'https://target.com/page',
    totalPages: 1,
    delay: 2000,

    // 仅在确认动态 JS 来源可信并完成审查后改为 true；node:vm 不是安全隔离。
    trustedCodeAcknowledged: false,
    
    cookies: {
        // sessionid: 'your_session_id',
    },
};

// ============ 主逻辑 ============

async function getDynamicCookie(client) {
    assertOfflineTemplateRun();
    console.log('[*] 获取动态Cookie...');
    
    const jsCode = 'document.cookie = "dynamic_token=offline_fixture; path=/";';
    
    // 在VM沙箱中执行，提取Cookie
    const result = executeAndExtractCookie(jsCode, {
        url: CONFIG.baseURL + CONFIG.referer,
        initialCookie: client.getCookieString(),
        trustedCode: CONFIG.trustedCodeAcknowledged,
    });
    
    if (result.success && Object.keys(result.cookies).length > 0) {
        console.log(`[+] Cookie 提取成功: ${result.cookieString.substring(0, 100)}...`);
        client.setCookies(result.cookies);
        return true;
    } else {
        console.error('[-] Cookie 提取失败:', result.error || '未生成Cookie');
        return false;
    }
}

async function fetchPage(client, page) {
    assertOfflineTemplateRun();
    return { data: [{ page, value: page, cookie: client.getCookieString() }] };
}

async function main() {
    assertOfflineTemplateRun();
    console.log(`[*] 项目：${CONFIG.name}`);
    console.log(`[*] 目标：${CONFIG.description}`);
    console.log('');
    
    const client = new TwoPhaseClient({
        baseURL: CONFIG.baseURL,
        cookies: CONFIG.cookies,
        delay: CONFIG.delay,
    });
    
    // 获取动态Cookie
    const cookieOk = await getDynamicCookie(client);
    if (!cookieOk) {
        console.error('[!] 无法获取动态Cookie，退出');
        process.exit(1);
    }
    
    // 采集数据
    const allData = [];
    
    for (let page = 1; page <= CONFIG.totalPages; page++) {
        try {
            // 某些网站每次请求都需要刷新Cookie
            // await getDynamicCookie(client);
            
            const responseData = await fetchPage(client, page);
            const pageData = responseData.data || [];
            allData.push(...pageData);
            console.log(`[+] 正在采集第 ${page}/${CONFIG.totalPages} 页... ✓ 获取 ${pageData.length} 条数据`);
        } catch (error) {
            console.error(`[-] 第 ${page} 页采集失败: ${error.message}`);
        }
    }
    
    console.log(`\n[+] 采集完成，共 ${allData.length} 条数据`);
    
    // TODO: 根据需求计算结果
    const result = allData.reduce((sum, item) => sum + (item.value || 0), 0);
    
    console.log('\n' + '='.repeat(30) + ' 计算结果 ' + '='.repeat(30));
    console.log(`答案：${result}`);
    console.log('='.repeat(70));
}

main().catch(error => {
    console.error('\n[!] 运行错误:', error.message);
    process.exit(1);
});
