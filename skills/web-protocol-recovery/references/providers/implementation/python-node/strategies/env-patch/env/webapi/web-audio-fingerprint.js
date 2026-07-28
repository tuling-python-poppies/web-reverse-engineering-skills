/**
  * @env-module web-audio-fingerprint
 * @description Web Audio API lightweight stubs for fingerprint and feature probes.
 */

(function() {
    'use strict';

    const profile = window.__ProfileManager__ ? window.__ProfileManager__.getSection('audio') : {};
    const Monitor = window.__EnvMonitor__ || window.__envMonitor__ || {
        log: function() {},
        logCall: function() {},
        logCreate: function() {}
    };

    let nodeId = 0;

    function makeAudioParam(value) {
        return {
            value: value,
            defaultValue: value,
            minValue: -3.4028234663852886e38,
            maxValue: 3.4028234663852886e38,
            automationRate: 'a-rate',
            setValueAtTime: function(nextValue) { this.value = nextValue; return this; },
            linearRampToValueAtTime: function(nextValue) { this.value = nextValue; return this; },
            exponentialRampToValueAtTime: function(nextValue) { this.value = nextValue; return this; },
            setTargetAtTime: function(nextValue) { this.value = nextValue; return this; },
            setValueCurveAtTime: function(values) { if (values && values.length) this.value = values[values.length - 1]; return this; },
            cancelScheduledValues: function() { return this; },
            cancelAndHoldAtTime: function() { return this; }
        };
    }

    function AudioNode(context, type) {
        this.context = context;
        this.channelCount = 2;
        this.channelCountMode = 'max';
        this.channelInterpretation = 'speakers';
        this.numberOfInputs = type === 'destination' ? 1 : 1;
        this.numberOfOutputs = type === 'destination' ? 0 : 1;
        this._id = 'audio_node_' + (++nodeId);
        this._type = type;
    }

    AudioNode.prototype.connect = function(destination) {
        Monitor.log('AudioNode', 'connect', { from: this._type, to: destination && destination._type });
        return destination || this;
    };

    AudioNode.prototype.disconnect = function() {
        Monitor.log('AudioNode', 'disconnect', { type: this._type });
    };

    function AudioBuffer(numberOfChannels, length, sampleRate) {
        this.length = length;
        this.duration = length / sampleRate;
        this.sampleRate = sampleRate;
        this.numberOfChannels = numberOfChannels;
        this._channels = [];
        for (let i = 0; i < numberOfChannels; i++) {
            this._channels.push(new Float32Array(length));
        }
    }

    AudioBuffer.prototype.getChannelData = function(channel) {
        return this._channels[channel] || new Float32Array(this.length);
    };

    AudioBuffer.prototype.copyFromChannel = function(destination, channelNumber, startInChannel) {
        destination.set(this.getChannelData(channelNumber).subarray(startInChannel || 0, (startInChannel || 0) + destination.length));
    };

    AudioBuffer.prototype.copyToChannel = function(source, channelNumber, startInChannel) {
        this.getChannelData(channelNumber).set(source, startInChannel || 0);
    };

    function BaseAudioContext(options) {
        options = options || {};
        this.sampleRate = options.sampleRate || profile.sampleRate || 44100;
        this.currentTime = 0;
        this.state = profile.state || 'suspended';
        this.baseLatency = profile.baseLatency !== undefined ? profile.baseLatency : 0.005333;
        this.outputLatency = profile.outputLatency !== undefined ? profile.outputLatency : 0.016;
        this.destination = new AudioNode(this, 'destination');
        this.listener = {
            positionX: makeAudioParam(0),
            positionY: makeAudioParam(0),
            positionZ: makeAudioParam(0),
            forwardX: makeAudioParam(0),
            forwardY: makeAudioParam(0),
            forwardZ: makeAudioParam(-1),
            upX: makeAudioParam(0),
            upY: makeAudioParam(1),
            upZ: makeAudioParam(0)
        };
    }

    BaseAudioContext.prototype.createBuffer = function(channels, length, sampleRate) {
        return new AudioBuffer(channels, length, sampleRate || this.sampleRate);
    };

    BaseAudioContext.prototype.createBufferSource = function() {
        const node = new AudioNode(this, 'bufferSource');
        node.buffer = null;
        node.loop = false;
        node.loopStart = 0;
        node.loopEnd = 0;
        node.playbackRate = makeAudioParam(1);
        node.detune = makeAudioParam(0);
        node.start = function() {};
        node.stop = function() {};
        return node;
    };

    BaseAudioContext.prototype.createOscillator = function() {
        const node = new AudioNode(this, 'oscillator');
        node.type = 'sine';
        node.frequency = makeAudioParam(440);
        node.detune = makeAudioParam(0);
        node.start = function() {};
        node.stop = function() {};
        return node;
    };

    BaseAudioContext.prototype.createGain = function() {
        const node = new AudioNode(this, 'gain');
        node.gain = makeAudioParam(1);
        return node;
    };

    BaseAudioContext.prototype.createAnalyser = function() {
        const node = new AudioNode(this, 'analyser');
        node.fftSize = 2048;
        node.frequencyBinCount = 1024;
        node.minDecibels = -100;
        node.maxDecibels = -30;
        node.smoothingTimeConstant = 0.8;
        node.getFloatFrequencyData = function(array) { array.fill(-100); };
        node.getByteFrequencyData = function(array) { array.fill(0); };
        node.getFloatTimeDomainData = function(array) { array.fill(0); };
        node.getByteTimeDomainData = function(array) { array.fill(128); };
        return node;
    };

    BaseAudioContext.prototype.createDynamicsCompressor = function() {
        const node = new AudioNode(this, 'dynamicsCompressor');
        node.threshold = makeAudioParam(-24);
        node.knee = makeAudioParam(30);
        node.ratio = makeAudioParam(12);
        node.attack = makeAudioParam(0.003);
        node.release = makeAudioParam(0.25);
        node.reduction = -20;
        return node;
    };

    BaseAudioContext.prototype.decodeAudioData = function(data, successCallback, errorCallback) {
        const buffer = this.createBuffer(1, Math.max(1, data && data.byteLength || 1), this.sampleRate);
        if (successCallback) successCallback(buffer);
        return Promise.resolve(buffer).catch(function(error) {
            if (errorCallback) errorCallback(error);
            throw error;
        });
    };

    BaseAudioContext.prototype.resume = function() { this.state = 'running'; return Promise.resolve(); };
    BaseAudioContext.prototype.suspend = function() { this.state = 'suspended'; return Promise.resolve(); };
    BaseAudioContext.prototype.close = function() { this.state = 'closed'; return Promise.resolve(); };

    function AudioContext(options) {
        Monitor.logCreate && Monitor.logCreate('AudioContext', options || {});
        BaseAudioContext.call(this, options);
    }
    AudioContext.prototype = Object.create(BaseAudioContext.prototype);
    AudioContext.prototype.constructor = AudioContext;

    function OfflineAudioContext(numberOfChannels, length, sampleRate) {
        if (typeof numberOfChannels === 'object') {
            sampleRate = numberOfChannels.sampleRate;
            length = numberOfChannels.length;
            numberOfChannels = numberOfChannels.numberOfChannels;
        }
        BaseAudioContext.call(this, { sampleRate: sampleRate || profile.sampleRate || 44100 });
        this.length = length || 44100;
        this._numberOfChannels = numberOfChannels || 2;
        this.oncomplete = null;
    }
    OfflineAudioContext.prototype = Object.create(BaseAudioContext.prototype);
    OfflineAudioContext.prototype.constructor = OfflineAudioContext;
    OfflineAudioContext.prototype.startRendering = function() {
        const buffer = this.createBuffer(this._numberOfChannels, this.length, this.sampleRate);
        const fingerprint = profile.fingerprint || {};
        const channel = buffer.getChannelData(0);
        if (channel.length) channel[0] = fingerprint.sum || 124.04347527516074;
        const event = { renderedBuffer: buffer };
        if (typeof this.oncomplete === 'function') this.oncomplete(event);
        return Promise.resolve(buffer);
    };

    window.AudioNode = window.AudioNode || AudioNode;
    window.AudioBuffer = window.AudioBuffer || AudioBuffer;
    window.AudioParam = window.AudioParam || function AudioParam() {};
    window.BaseAudioContext = window.BaseAudioContext || BaseAudioContext;
    window.AudioContext = window.AudioContext || AudioContext;
    window.webkitAudioContext = window.webkitAudioContext || AudioContext;
    window.OfflineAudioContext = window.OfflineAudioContext || OfflineAudioContext;
    window.webkitOfflineAudioContext = window.webkitOfflineAudioContext || OfflineAudioContext;
})();
