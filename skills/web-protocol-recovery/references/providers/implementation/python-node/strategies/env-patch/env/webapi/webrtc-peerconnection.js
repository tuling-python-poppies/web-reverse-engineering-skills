/**
  * @env-module webrtc-peerconnection
 * @description RTCPeerConnection and related WebRTC lightweight stubs.
 */

(function() {
    'use strict';

    const profile = window.__ProfileManager__ ? window.__ProfileManager__.getSection('webrtc') : {};
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

    function RTCSessionDescription(init) {
        init = init || {};
        this.type = init.type || 'offer';
        this.sdp = init.sdp || '';
    }

    function RTCIceCandidate(init) {
        init = init || {};
        this.candidate = init.candidate || '';
        this.sdpMid = init.sdpMid || null;
        this.sdpMLineIndex = init.sdpMLineIndex === undefined ? null : init.sdpMLineIndex;
        this.usernameFragment = init.usernameFragment || null;
    }

    function RTCDataChannel(label, options) {
        EventTargetLite.call(this);
        options = options || {};
        this.label = label || '';
        this.ordered = options.ordered !== undefined ? options.ordered : true;
        this.maxPacketLifeTime = options.maxPacketLifeTime || null;
        this.maxRetransmits = options.maxRetransmits || null;
        this.protocol = options.protocol || '';
        this.negotiated = !!options.negotiated;
        this.id = options.id === undefined ? null : options.id;
        this.readyState = 'open';
        this.bufferedAmount = 0;
        this.bufferedAmountLowThreshold = 0;
        this.binaryType = 'blob';
    }
    RTCDataChannel.prototype = Object.create(EventTargetLite.prototype);
    RTCDataChannel.prototype.constructor = RTCDataChannel;
    RTCDataChannel.prototype.send = function(data) {
        Monitor.log('RTCDataChannel', 'send', { label: this.label, type: typeof data });
    };
    RTCDataChannel.prototype.close = function() {
        this.readyState = 'closed';
        this.dispatchEvent({ type: 'close' });
    };

    function RTCPeerConnection(configuration) {
        EventTargetLite.call(this);
        Monitor.logCreate && Monitor.logCreate('RTCPeerConnection', configuration || {});
        this.localDescription = null;
        this.remoteDescription = null;
        this.currentLocalDescription = null;
        this.currentRemoteDescription = null;
        this.pendingLocalDescription = null;
        this.pendingRemoteDescription = null;
        this.signalingState = 'stable';
        this.iceGatheringState = 'new';
        this.iceConnectionState = 'new';
        this.connectionState = 'new';
        this.canTrickleIceCandidates = true;
        this._configuration = Object.assign({
            iceServers: [],
            iceTransportPolicy: profile.iceTransportPolicy || 'all',
            bundlePolicy: profile.bundlePolicy || 'balanced',
            rtcpMuxPolicy: profile.rtcpMuxPolicy || 'require'
        }, configuration || {});
        this._senders = [];
        this._receivers = [];
        this._transceivers = [];
    }
    RTCPeerConnection.prototype = Object.create(EventTargetLite.prototype);
    RTCPeerConnection.prototype.constructor = RTCPeerConnection;

    RTCPeerConnection.prototype.createOffer = function() {
        return Promise.resolve(new RTCSessionDescription({ type: 'offer', sdp: profile.defaultOfferSdp || 'v=0\r\n' }));
    };

    RTCPeerConnection.prototype.createAnswer = function() {
        return Promise.resolve(new RTCSessionDescription({ type: 'answer', sdp: profile.defaultAnswerSdp || 'v=0\r\n' }));
    };

    RTCPeerConnection.prototype.setLocalDescription = function(description) {
        this.localDescription = new RTCSessionDescription(description || { type: 'offer', sdp: profile.defaultOfferSdp || 'v=0\r\n' });
        this.currentLocalDescription = this.localDescription;
        this.signalingState = this.localDescription.type === 'offer' ? 'have-local-offer' : 'stable';
        this.iceGatheringState = 'complete';
        const candidates = profile.allowCandidateLeak ? (profile.iceCandidates || []) : [];
        candidates.forEach(function(candidate) {
            this.dispatchEvent({ type: 'icecandidate', candidate: new RTCIceCandidate(candidate) });
        }, this);
        this.dispatchEvent({ type: 'icecandidate', candidate: null });
        return Promise.resolve();
    };

    RTCPeerConnection.prototype.setRemoteDescription = function(description) {
        this.remoteDescription = new RTCSessionDescription(description || { type: 'answer', sdp: profile.defaultAnswerSdp || 'v=0\r\n' });
        this.currentRemoteDescription = this.remoteDescription;
        this.signalingState = 'stable';
        return Promise.resolve();
    };

    RTCPeerConnection.prototype.addIceCandidate = function(candidate) {
        return Promise.resolve(candidate ? new RTCIceCandidate(candidate) : null);
    };

    RTCPeerConnection.prototype.createDataChannel = function(label, options) {
        return new RTCDataChannel(label, options);
    };

    RTCPeerConnection.prototype.addTrack = function(track, stream) {
        const sender = { track: track || null, transport: null, getStats: function() { return Promise.resolve(new Map()); } };
        this._senders.push(sender);
        return sender;
    };
    RTCPeerConnection.prototype.removeTrack = function(sender) {
        this._senders = this._senders.filter(function(item) { return item !== sender; });
    };
    RTCPeerConnection.prototype.addTransceiver = function(trackOrKind, init) {
        const transceiver = { mid: null, sender: null, receiver: null, stopped: false, direction: init && init.direction || 'sendrecv', currentDirection: null };
        this._transceivers.push(transceiver);
        return transceiver;
    };
    RTCPeerConnection.prototype.getSenders = function() { return this._senders.slice(); };
    RTCPeerConnection.prototype.getReceivers = function() { return this._receivers.slice(); };
    RTCPeerConnection.prototype.getTransceivers = function() { return this._transceivers.slice(); };
    RTCPeerConnection.prototype.getConfiguration = function() { return Object.assign({}, this._configuration); };
    RTCPeerConnection.prototype.setConfiguration = function(configuration) { this._configuration = Object.assign(this._configuration, configuration || {}); };
    RTCPeerConnection.prototype.getStats = function() { return Promise.resolve(new Map()); };
    RTCPeerConnection.prototype.close = function() { this.signalingState = 'closed'; this.connectionState = 'closed'; this.iceConnectionState = 'closed'; };

    window.RTCPeerConnection = window.RTCPeerConnection || RTCPeerConnection;
    window.webkitRTCPeerConnection = window.webkitRTCPeerConnection || RTCPeerConnection;
    window.RTCSessionDescription = window.RTCSessionDescription || RTCSessionDescription;
    window.RTCIceCandidate = window.RTCIceCandidate || RTCIceCandidate;
    window.RTCDataChannel = window.RTCDataChannel || RTCDataChannel;
})();
