/**
  * @env-module worker-messaging
 * @description Worker, SharedWorker, BroadcastChannel and MessageChannel stubs with local dispatch.
 */

(function() {
    'use strict';

    const profile = window.__ProfileManager__ ? window.__ProfileManager__.getSection('worker') : {};
    const Monitor = window.__EnvMonitor__ || window.__envMonitor__ || {
        log: function() {},
        logCall: function() {},
        logCreate: function() {}
    };

    function EventTargetLite() {
        this._listeners = {};
    }

    EventTargetLite.prototype.addEventListener = function(type, listener) {
        if (!this._listeners[type]) this._listeners[type] = [];
        this._listeners[type].push(listener);
    };

    EventTargetLite.prototype.removeEventListener = function(type, listener) {
        if (!this._listeners[type]) return;
        this._listeners[type] = this._listeners[type].filter(function(item) { return item !== listener; });
    };

    EventTargetLite.prototype.dispatchEvent = function(event) {
        event = event || {};
        event.target = event.target || this;
        const type = event.type;
        if (typeof this['on' + type] === 'function') this['on' + type](event);
        (this._listeners[type] || []).slice().forEach(function(listener) { listener.call(this, event); }, this);
        return true;
    };

    function makeMessageEvent(data, origin, source) {
        return {
            type: 'message',
            data: data,
            origin: origin || (window.location && window.location.origin) || '',
            lastEventId: '',
            source: source || null,
            ports: []
        };
    }

    function MessagePort() {
        EventTargetLite.call(this);
        this.onmessage = null;
        this.onmessageerror = null;
        this._started = false;
        this._peer = null;
        this._closed = false;
    }
    MessagePort.prototype = Object.create(EventTargetLite.prototype);
    MessagePort.prototype.constructor = MessagePort;
    MessagePort.prototype.postMessage = function(message) {
        if (this._closed || !this._peer || this._peer._closed) return;
        this._peer.dispatchEvent(makeMessageEvent(message, '', this));
    };
    MessagePort.prototype.start = function() { this._started = true; };
    MessagePort.prototype.close = function() { this._closed = true; };

    function MessageChannel() {
        this.port1 = new MessagePort();
        this.port2 = new MessagePort();
        this.port1._peer = this.port2;
        this.port2._peer = this.port1;
    }

    function Worker(scriptURL, options) {
        EventTargetLite.call(this);
        Monitor.logCreate && Monitor.logCreate('Worker', { scriptURL: String(scriptURL), options: options || {} });
        this.scriptURL = String(scriptURL || '');
        this.options = options || {};
        this.onmessage = null;
        this.onerror = null;
        this.onmessageerror = null;
        this._terminated = false;
    }
    Worker.prototype = Object.create(EventTargetLite.prototype);
    Worker.prototype.constructor = Worker;
    Worker.prototype.postMessage = function(message) {
        Monitor.log('Worker', 'postMessage', { scriptURL: this.scriptURL, type: typeof message });
        if (this._terminated) return;
        const inlineScripts = profile.inlineScripts || {};
        if (typeof inlineScripts[this.scriptURL] === 'function') {
            try {
                const result = inlineScripts[this.scriptURL](message);
                if (result !== undefined) this.dispatchEvent(makeMessageEvent(result, '', this));
            } catch (error) {
                this.dispatchEvent({ type: 'error', error: error, message: error.message || String(error) });
            }
        } else if (inlineScripts[this.scriptURL] !== undefined) {
            this.dispatchEvent(makeMessageEvent(inlineScripts[this.scriptURL], '', this));
        }
    };
    Worker.prototype.terminate = function() {
        this._terminated = true;
        Monitor.log('Worker', 'terminate', { scriptURL: this.scriptURL });
    };

    function SharedWorker(scriptURL, options) {
        EventTargetLite.call(this);
        Monitor.logCreate && Monitor.logCreate('SharedWorker', { scriptURL: String(scriptURL), options: options || {} });
        this.scriptURL = String(scriptURL || '');
        this.name = typeof options === 'string' ? options : (options && options.name) || profile.sharedWorkerName || '';
        this.port = new MessagePort();
        this.onerror = null;
    }
    SharedWorker.prototype = Object.create(EventTargetLite.prototype);
    SharedWorker.prototype.constructor = SharedWorker;

    const broadcastRegistry = new Map();

    function BroadcastChannel(name) {
        EventTargetLite.call(this);
        this.name = String(name || '');
        this.onmessage = null;
        this.onmessageerror = null;
        this._closed = false;
        if (!broadcastRegistry.has(this.name)) broadcastRegistry.set(this.name, []);
        broadcastRegistry.get(this.name).push(this);
    }
    BroadcastChannel.prototype = Object.create(EventTargetLite.prototype);
    BroadcastChannel.prototype.constructor = BroadcastChannel;
    BroadcastChannel.prototype.postMessage = function(message) {
        Monitor.log('BroadcastChannel', 'postMessage', { name: this.name, type: typeof message });
        if (this._closed) return;
        (broadcastRegistry.get(this.name) || []).forEach(function(channel) {
            if (channel !== this && !channel._closed) channel.dispatchEvent(makeMessageEvent(message, '', this));
        }, this);
    };
    BroadcastChannel.prototype.close = function() {
        this._closed = true;
        const channels = broadcastRegistry.get(this.name) || [];
        broadcastRegistry.set(this.name, channels.filter(function(channel) { return channel !== this; }, this));
    };

    window.MessagePort = MessagePort;
    window.MessageChannel = MessageChannel;
    window.Worker = Worker;
    window.SharedWorker = SharedWorker;
    window.BroadcastChannel = BroadcastChannel;
})();
