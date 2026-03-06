/**
 * Auth grab flow: discover cookies/tokens from the current page and save them.
 */

import { state, showError } from './ui.js';

function truncate(str, max = 40) {
  if (!str || str.length <= max) return str || '';
  return str.slice(0, max) + '...';
}

/**
 * Grab auth from the current page: read cookies and scan storage for tokens.
 */
export async function grabAuthFromPage() {
  const btnGrabAuth = document.getElementById('btn-grab-auth');
  const authPanel = document.getElementById('auth-panel');
  const authItems = document.getElementById('auth-items');
  const authEmpty = document.getElementById('auth-empty');
  const btnSaveAuth = document.getElementById('btn-save-auth');
  const authSuccess = document.getElementById('auth-success');

  try {
    btnGrabAuth.disabled = true;
    authPanel.classList.remove('hidden');
    authItems.innerHTML = '';
    authEmpty.classList.add('hidden');
    btnSaveAuth.classList.add('hidden');
    authSuccess.classList.add('hidden');

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const authData = await chrome.runtime.sendMessage({
      type: 'GRAB_AUTH',
      url: tab.url,
      tabId: tab.id,
    });

    if (!authData) {
      authEmpty.classList.remove('hidden');
      setTimeout(() => { authPanel.classList.add('hidden'); }, 3000);
      return;
    }

    if (authData.cookies) {
      const div = document.createElement('label');
      div.className = 'auth-item';
      div.innerHTML = `<input type="checkbox" checked data-type="cookie">
        <span class="auth-item-name">Cookie</span>
        <span class="auth-item-value">${truncate(authData.cookies)}</span>`;
      div.querySelector('input').dataset.value = authData.cookies;
      authItems.appendChild(div);
    }

    if (authData.tokens) {
      for (const token of authData.tokens) {
        const div = document.createElement('label');
        div.className = 'auth-item';
        div.innerHTML = `<input type="checkbox" checked data-type="token">
          <span class="auth-item-name">${token.source}:${token.key}</span>
          <span class="auth-item-value">${truncate(token.value)}</span>`;
        div.querySelector('input').dataset.value = token.value;
        div.querySelector('input').dataset.key = token.key;
        authItems.appendChild(div);
      }
    }

    btnSaveAuth.classList.remove('hidden');
  } catch (error) {
    showError(`Failed to grab auth: ${error.message}`);
    authPanel.classList.add('hidden');
  } finally {
    btnGrabAuth.disabled = false;
  }
}

/**
 * Save selected auth headers to spectral CLI.
 */
export async function saveAuth() {
  const authPanel = document.getElementById('auth-panel');
  const authItems = document.getElementById('auth-items');
  const btnSaveAuth = document.getElementById('btn-save-auth');
  const authSuccess = document.getElementById('auth-success');

  try {
    btnSaveAuth.disabled = true;
    const headers = {};

    const checkboxes = authItems.querySelectorAll('input[type="checkbox"]:checked');
    for (const cb of checkboxes) {
      if (cb.dataset.type === 'cookie') {
        headers['Cookie'] = cb.dataset.value;
      } else if (cb.dataset.type === 'token') {
        headers['Authorization'] = `Bearer ${cb.dataset.value}`;
      }
    }

    if (Object.keys(headers).length === 0) {
      showError('No auth items selected');
      return;
    }

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab.url);
    const domain = url.hostname.replace(/^(www\.|m\.|app\.)/, '');
    const appName = domain.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'app';

    const result = await chrome.runtime.sendMessage({
      type: 'SEND_AUTH',
      appName,
      displayName: domain,
      headers,
    });

    if (result && result.success === false) {
      throw new Error(result.message || 'Failed to save auth');
    }

    authItems.innerHTML = '';
    btnSaveAuth.classList.add('hidden');
    authSuccess.classList.remove('hidden');
    setTimeout(() => { authPanel.classList.add('hidden'); }, 2000);
  } catch (error) {
    showError(`Failed to save auth: ${error.message}`);
  } finally {
    btnSaveAuth.disabled = false;
  }
}
