/**
  * @env-module profile-seed-manager
 * @description Profile seed manager for env-patch modules.
 */

(function() {
    'use strict';

    const profile = window.__profile__ || {};

    function getByPath(source, keyPath, fallback) {
        const parts = String(keyPath || '').split('.').filter(Boolean);
        let current = source;
        for (let i = 0; i < parts.length; i++) {
            if (current === undefined || current === null) return fallback;
            current = current[parts[i]];
        }
        return current === undefined ? fallback : current;
    }

    function setByPath(source, keyPath, value) {
        const parts = String(keyPath || '').split('.').filter(Boolean);
        if (!parts.length) return;
        let current = source;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!current[parts[i]] || typeof current[parts[i]] !== 'object') {
                current[parts[i]] = {};
            }
            current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;
    }

    window.__ProfileManager__ = {
        _profile: profile,
        hasProfile: function() {
            return !!(this._profile && Object.keys(this._profile).length);
        },
        getProfileName: function() {
            return getByPath(this._profile, 'meta.name', 'none');
        },
        getSection: function(section) {
            return this._profile[section] || {};
        },
        get: function(keyPath, fallback) {
            return getByPath(this._profile, keyPath, fallback);
        },
        set: function(keyPath, value) {
            setByPath(this._profile, keyPath, value);
        },
        merge: function(section, data) {
            if (!this._profile[section] || typeof this._profile[section] !== 'object') {
                this._profile[section] = {};
            }
            Object.assign(this._profile[section], data || {});
        },
        toJSON: function() {
            return JSON.parse(JSON.stringify(this._profile));
        }
    };

    window.__profile__ = profile;
})();
