/**
  * @env-module screen-fingerprint
 * @description 浏览器screen对象模拟
 * @compatibility Chrome 80+, Firefox 75+, Edge 79+
 */

(function() {
    const profile = window.__ProfileManager__ ? window.__ProfileManager__.getSection('screen') : {};
    const screen = {
        // 屏幕尺寸
        width: profile.width || 1920,
        height: profile.height || 1080,
        availWidth: profile.availWidth || 1920,
        availHeight: profile.availHeight || 1040,
        availLeft: profile.availLeft !== undefined ? profile.availLeft : 0,
        availTop: profile.availTop !== undefined ? profile.availTop : 0,

        // 颜色深度
        colorDepth: profile.colorDepth || 24,
        pixelDepth: profile.pixelDepth || 24,

        // 方向
        orientation: {
            angle: profile.orientation && profile.orientation.angle !== undefined ? profile.orientation.angle : 0,
            type: profile.orientation && profile.orientation.type || 'landscape-primary',
            onchange: null,
            lock: function(orientation) {
                return Promise.resolve();
            },
            unlock: function() {}
        },

        // 是否为扩展显示器
        isExtended: profile.isExtended !== undefined ? profile.isExtended : false
    };

    // 挂载到window
    window.screen = screen;
})();
