/**
 * @env-module web-crypto
 * @description VM-realm Web Crypto facade backed by the host implementation
 */

(() => {
    'use strict';

    const host = globalThis.__WPR_HOST_WEBCRYPTO__;
    if (!host || !host.subtle || typeof host.getRandomValues !== 'function') {
        throw new Error('web-crypto requires a trusted host WebCrypto adapter');
    }

    const hostToLocalKeys = new WeakMap();
    const localToHostKeys = new WeakMap();
    const keyMetadata = new WeakMap();
    const legacyDomExceptionCodes = {
        IndexSizeError: 1, DOMStringSizeError: 2, HierarchyRequestError: 3,
        WrongDocumentError: 4, InvalidCharacterError: 5, NoDataAllowedError: 6,
        NoModificationAllowedError: 7, NotFoundError: 8, NotSupportedError: 9,
        InUseAttributeError: 10, InvalidStateError: 11, SyntaxError: 12,
        InvalidModificationError: 13, NamespaceError: 14, InvalidAccessError: 15,
        ValidationError: 16, TypeMismatchError: 17, SecurityError: 18,
        NetworkError: 19, AbortError: 20, URLMismatchError: 21,
        QuotaExceededError: 22, TimeoutError: 23, InvalidNodeTypeError: 24,
        DataCloneError: 25
    };
    const legacyDomExceptionConstants = {
        INDEX_SIZE_ERR: 1, DOMSTRING_SIZE_ERR: 2, HIERARCHY_REQUEST_ERR: 3,
        WRONG_DOCUMENT_ERR: 4, INVALID_CHARACTER_ERR: 5, NO_DATA_ALLOWED_ERR: 6,
        NO_MODIFICATION_ALLOWED_ERR: 7, NOT_FOUND_ERR: 8, NOT_SUPPORTED_ERR: 9,
        INUSE_ATTRIBUTE_ERR: 10, INVALID_STATE_ERR: 11, SYNTAX_ERR: 12,
        INVALID_MODIFICATION_ERR: 13, NAMESPACE_ERR: 14, INVALID_ACCESS_ERR: 15,
        VALIDATION_ERR: 16, TYPE_MISMATCH_ERR: 17, SECURITY_ERR: 18,
        NETWORK_ERR: 19, ABORT_ERR: 20, URL_MISMATCH_ERR: 21,
        QUOTA_EXCEEDED_ERR: 22, TIMEOUT_ERR: 23, INVALID_NODE_TYPE_ERR: 24,
        DATA_CLONE_ERR: 25
    };
    const domExceptionState = new WeakMap();

    function requireDomException(value) {
        const state = domExceptionState.get(value);
        if (!state) throw new TypeError('Value of this must be of type DOMException');
        return state;
    }

    function DOMException(message = '', name = 'Error') {
        if (!new.target) throw new TypeError("Class constructor DOMException cannot be invoked without 'new'");
        const instance = Object.create(new.target.prototype);
        domExceptionState.set(instance, { message: String(message), name: String(name) });
        if (typeof Error.captureStackTrace === 'function') Error.captureStackTrace(instance, new.target);
        return instance;
    }
    DOMException.prototype = Object.create(Error.prototype);
    Object.defineProperties(DOMException.prototype, {
        constructor: { value: DOMException, configurable: true, writable: true },
        name: { get() { return requireDomException(this).name; }, enumerable: true, configurable: true },
        message: { get() { return requireDomException(this).message; }, enumerable: true, configurable: true },
        code: {
            get() { return legacyDomExceptionCodes[requireDomException(this).name] || 0; },
            enumerable: true,
            configurable: true
        },
        [Symbol.toStringTag]: { value: 'DOMException', configurable: true }
    });
    for (const [constant, code] of Object.entries(legacyDomExceptionConstants)) {
        Object.defineProperty(DOMException, constant, { value: code, enumerable: true });
        Object.defineProperty(DOMException.prototype, constant, { value: code, enumerable: true });
    }

    function toLocalError(error) {
        const message = error && typeof error.message === 'string' ? error.message : String(error);
        const name = error && typeof error.name === 'string' ? error.name : 'Error';
        if (Object.prototype.toString.call(error) === '[object DOMException]') {
            const Constructor = typeof globalThis.DOMException === 'function' ? globalThis.DOMException : DOMException;
            let local;
            try {
                local = new Constructor(message, name);
            } catch (_) {
                local = new DOMException(message, name);
            }
            const code = Number.isInteger(error.code) ? error.code : (legacyDomExceptionCodes[name] || 0);
            if (local.code !== code) {
                try { Object.defineProperty(local, 'code', { value: code, configurable: true }); } catch (_) {}
            }
            return local;
        }
        const constructors = { Error, EvalError, RangeError, ReferenceError, SyntaxError, TypeError, URIError };
        const Constructor = constructors[name] || Error;
        const local = new Constructor(message);
        if (Constructor === Error) local.name = name;
        return local;
    }

    function requireKey(value) {
        const metadata = keyMetadata.get(value);
        if (!metadata) throw new TypeError('Value of this must be of type CryptoKey');
        return metadata;
    }

    function CryptoKey() {
        throw new TypeError('Illegal constructor');
    }
    Object.defineProperties(CryptoKey.prototype, {
        type: {
            get() { return requireKey(this).type; },
            enumerable: true,
            configurable: true
        },
        extractable: {
            get() { return requireKey(this).extractable; },
            enumerable: true,
            configurable: true
        },
        algorithm: {
            get() { return requireKey(this).algorithm; },
            enumerable: true,
            configurable: true
        },
        usages: {
            get() { return requireKey(this).usages.slice(); },
            enumerable: true,
            configurable: true
        },
        [Symbol.toStringTag]: {
            value: 'CryptoKey',
            configurable: true
        }
    });

    function isHostCryptoKey(value) {
        return value !== null && typeof value === 'object' &&
            Object.prototype.toString.call(value) === '[object CryptoKey]';
    }

    function wrapCryptoKey(hostKey) {
        if (hostToLocalKeys.has(hostKey)) return hostToLocalKeys.get(hostKey);
        const localKey = Object.create(CryptoKey.prototype);
        hostToLocalKeys.set(hostKey, localKey);
        localToHostKeys.set(localKey, hostKey);
        keyMetadata.set(localKey, {
            type: hostKey.type,
            extractable: hostKey.extractable,
            algorithm: toLocal(hostKey.algorithm),
            usages: Array.from(hostKey.usages, toLocal)
        });
        return localKey;
    }

    function toLocal(value) {
        const tag = Object.prototype.toString.call(value);
        if (tag === '[object ArrayBuffer]') {
            const source = new Uint8Array(value);
            const copy = new Uint8Array(source.byteLength);
            copy.set(source);
            return copy.buffer;
        }
        if (isHostCryptoKey(value)) return wrapCryptoKey(value);
        if (Array.isArray(value)) return value.map(toLocal);
        if (tag === '[object Object]') {
            const copy = {};
            for (const key of Object.keys(value)) copy[key] = toLocal(value[key]);
            return copy;
        }
        return value;
    }

    function toHost(value) {
        if (localToHostKeys.has(value)) return localToHostKeys.get(value);
        if (Array.isArray(value)) return value.map(toHost);
        if (value && Object.prototype.toString.call(value) === '[object Object]') {
            const copy = {};
            for (const key of Object.keys(value)) copy[key] = toHost(value[key]);
            return copy;
        }
        return value;
    }

    const subtleInstances = new WeakSet();
    function SubtleCrypto() {
        throw new TypeError('Illegal constructor');
    }
    Object.defineProperty(SubtleCrypto.prototype, Symbol.toStringTag, {
        value: 'SubtleCrypto',
        configurable: true
    });

    const methodLengths = {
        decrypt: 3, deriveBits: 2, deriveKey: 5, digest: 2, encrypt: 3,
        exportKey: 2, generateKey: 3, importKey: 5, sign: 3,
        unwrapKey: 7, verify: 4, wrapKey: 4
    };

    function shapeFunction(func, name, length) {
        Object.defineProperties(func, {
            name: { value: name, configurable: true },
            length: { value: length, configurable: true }
        });
        if (typeof globalThis.safefunction === 'function') globalThis.safefunction(func);
        return func;
    }
    if (typeof globalThis.safefunction === 'function') {
        for (const key of ['name', 'message', 'code']) {
            globalThis.safefunction(Object.getOwnPropertyDescriptor(DOMException.prototype, key).get);
        }
    }

    for (const name of [
        'decrypt', 'deriveBits', 'deriveKey', 'digest', 'encrypt', 'exportKey',
        'generateKey', 'importKey', 'sign', 'unwrapKey', 'verify', 'wrapKey'
    ]) {
        if (typeof host.subtle[name] !== 'function') continue;
        const method = function(...args) {
            if (!subtleInstances.has(this)) {
                throw new TypeError(`Value of this must be of type SubtleCrypto for ${name}`);
            }
            let operation;
            try {
                operation = host.subtle[name](...args.map(toHost));
            } catch (error) {
                throw toLocalError(error);
            }
            return Promise.resolve(operation).then(
                toLocal,
                error => { throw toLocalError(error); }
            );
        };
        shapeFunction(method, name, methodLengths[name]);
        Object.defineProperty(SubtleCrypto.prototype, name, {
            value: method,
            enumerable: true,
            configurable: true,
            writable: true
        });
    }

    const subtle = Object.create(SubtleCrypto.prototype);
    subtleInstances.add(subtle);

    const cryptoInstances = new WeakSet();
    function requireCrypto(value) {
        const monitor = globalThis.__ProxyMonitor__;
        const unwrapped = monitor && typeof monitor.unwrap === 'function' ? monitor.unwrap(value) : value;
        if (!cryptoInstances.has(unwrapped)) throw new TypeError('Value of this must be of type Crypto');
    }

    function Crypto() {
        throw new TypeError('Illegal constructor');
    }
    const subtleGetter = shapeFunction(function() {
        requireCrypto(this);
        return subtle;
    }, 'get subtle', 0);
    const getRandomValues = shapeFunction(function(array) {
        requireCrypto(this);
        try {
            return host.getRandomValues(array);
        } catch (error) {
            throw toLocalError(error);
        }
    }, 'getRandomValues', 1);
    const randomUUID = shapeFunction(function() {
        requireCrypto(this);
        try {
            return host.randomUUID();
        } catch (error) {
            throw toLocalError(error);
        }
    }, 'randomUUID', 0);
    for (const constructor of [Crypto, SubtleCrypto, CryptoKey, DOMException]) {
        if (typeof globalThis.safefunction === 'function') globalThis.safefunction(constructor);
    }
    Object.defineProperties(Crypto.prototype, {
        subtle: {
            get: subtleGetter,
            enumerable: true,
            configurable: true
        },
        getRandomValues: {
            value: getRandomValues,
            enumerable: true,
            configurable: true,
            writable: true
        },
        randomUUID: {
            value: randomUUID,
            enumerable: true,
            configurable: true,
            writable: true
        },
        [Symbol.toStringTag]: {
            value: 'Crypto',
            configurable: true
        }
    });

    const crypto = Object.create(Crypto.prototype);
    cryptoInstances.add(crypto);
    Object.defineProperties(window, {
        crypto: {
            value: crypto,
            enumerable: true,
            configurable: true,
            writable: true
        },
        Crypto: {
            value: Crypto,
            configurable: true,
            writable: true
        },
        SubtleCrypto: {
            value: SubtleCrypto,
            configurable: true,
            writable: true
        },
        CryptoKey: {
            value: CryptoKey,
            configurable: true,
            writable: true
        },
        DOMException: {
            value: typeof globalThis.DOMException === 'function' ? globalThis.DOMException : DOMException,
            configurable: true,
            writable: true
        }
    });
})();
