#!/usr/bin/env node
/**
 * Darwin Skill - 高清截图脚本
 *
 * 用法: node scripts/screenshot.mjs [html文件路径] [输出png路径] [--open]
 *
 * 特性:
 * - 2x deviceScaleFactor，输出高清图
 * - 只截 .card 元素，无多余背景
 * - 等待字体加载完成
 * - 传入 --open 时自动打开图片
 */

import { execFile } from 'child_process';
import { createRequire } from 'module';
import { dirname, resolve } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { promisify } from 'util';

const require = createRequire(import.meta.url);
const execFileAsync = promisify(execFile);

function loadPlaywright() {
  const candidates = ['playwright', 'playwright-core'];
  const errors = [];
  for (const name of candidates) {
    try {
      return require(name);
    } catch (error) {
      errors.push(`${name}: ${error.message}`);
    }
  }
  throw new Error(`Cannot load playwright. Tried ${candidates.join(', ')}. ${errors.join(' | ')}`);
}

async function openFile(filePath) {
  if (process.platform === 'win32') {
    await execFileAsync('cmd', ['/c', 'start', '', filePath], { windowsHide: true });
    return;
  }
  if (process.platform === 'darwin') {
    await execFileAsync('open', [filePath]);
    return;
  }
  await execFileAsync('xdg-open', [filePath]);
}

const pw = loadPlaywright();
const scriptDir = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const openAfter = args.includes('--open');
const positionalArgs = args.filter(arg => arg !== '--open');

const htmlPath = resolve(positionalArgs[0] || resolve(scriptDir, '../templates/result-card.html'));
const outputPath = resolve(positionalArgs[1] || resolve(scriptDir, '../templates/result-card.png'));

async function screenshot() {
  const browser = await pw.chromium.launch();

  try {
    const context = await browser.newContext({
      viewport: { width: 920, height: 1600 },
      deviceScaleFactor: 2,
    });

    const page = await context.newPage();

    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle' });

    // 等待字体加载
    await page.evaluate(() => document.fonts.ready);
    // 额外等待确保渲染完成
    await page.waitForTimeout(2000);

    // 只截 .card 元素
    const card = await page.locator('.card');
    const box = await card.boundingBox();
    if (!box) {
      throw new Error('Cannot find .card element to screenshot');
    }
    await card.screenshot({
      path: outputPath,
      type: 'png',
    });

    console.log(`截图完成: ${outputPath}`);

    console.log(`卡片尺寸: ${Math.round(box.width)}x${Math.round(box.height)}px (CSS)`);
    console.log(`输出尺寸: ${Math.round(box.width * 2)}x${Math.round(box.height * 2)}px (2x高清)`);

  } finally {
    await browser.close();
  }

  if (openAfter) {
    await openFile(outputPath);
  }
}

screenshot().catch(err => {
  console.error('截图失败:', err.message);
  process.exit(1);
});
