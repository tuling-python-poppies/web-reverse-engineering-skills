'use strict';

function installEnv(profile) {
  const root = globalThis;
  root.window = root;
  root.self = root;
  root.globalThis = root;
  root.__profile__ = profile || root.__profile__ || {};

  if (!root.console) root.console = console;
  if (!root.atob) root.atob = (value) => Buffer.from(String(value), 'base64').toString('binary');
  if (!root.btoa) root.btoa = (value) => Buffer.from(String(value), 'binary').toString('base64');

  // Paste verified env-patch module bodies below, preserving the accepted load order.
}

installEnv();

module.exports = { installEnv };
