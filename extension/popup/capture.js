/**
 * Capture flow: start, stop, send, and status polling.
 */

import { state, showError, updateUI, formatDuration } from './ui.js';

let statusPollInterval = null;

/**
 * Start capture on current tab.
 */
export async function startCapture() {
  const btnStart = document.getElementById('btn-start');
  try {
    btnStart.disabled = true;
    state.lastStats = null;

    const response = await chrome.runtime.sendMessage({
      type: 'START_CAPTURE',
      tabId: state.currentTabId,
    });

    if (response.error) {
      throw new Error(response.error);
    }

    startStatusPolling();
    updateUI('capturing');
  } catch (error) {
    showError(`Failed to start: ${error.message}`);
    updateUI('idle');
  } finally {
    btnStart.disabled = false;
  }
}

/**
 * Stop capture.
 */
export async function stopCapture() {
  const btnStop = document.getElementById('btn-stop');
  try {
    btnStop.disabled = true;
    stopStatusPolling();

    const response = await chrome.runtime.sendMessage({
      type: 'STOP_CAPTURE',
    });

    if (response.error) {
      throw new Error(response.error);
    }

    state.lastStats = response.stats;
    updateUI('idle');
  } catch (error) {
    showError(`Failed to stop: ${error.message}`);
  } finally {
    btnStop.disabled = false;
  }
}

/**
 * Send capture to spectral CLI via native messaging.
 */
export async function sendCapture() {
  const btnExport = document.getElementById('btn-export');
  try {
    btnExport.disabled = true;
    updateUI('sending');

    const response = await chrome.runtime.sendMessage({
      type: 'SEND_CAPTURE',
    });

    if (response.error) {
      if (chrome.runtime.lastError &&
          chrome.runtime.lastError.message &&
          chrome.runtime.lastError.message.includes('native messaging host not found')) {
        throw new Error(`Native host not found. Run: spectral extension install --extension-id ${chrome.runtime.id}`);
      }
      throw new Error(response.error);
    }

    state.lastStats = null;
    updateUI('idle');
  } catch (error) {
    if (error.message && error.message.includes('native messaging host not found')) {
      showError(`Native host not found. Run: spectral extension install --extension-id ${chrome.runtime.id}`);
    } else {
      showError(`Failed to send: ${error.message}`);
    }
    updateUI('idle');
  } finally {
    btnExport.disabled = false;
  }
}

// -- Status polling ----------------------------------------------------------

export function startStatusPolling() {
  stopStatusPolling();
  statusPollInterval = setInterval(pollStatus, 1000);
}

export function stopStatusPolling() {
  if (statusPollInterval) {
    clearInterval(statusPollInterval);
    statusPollInterval = null;
  }
}

async function pollStatus() {
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GET_STATUS',
    });

    if (response.state === 'capturing' && response.stats) {
      updateUI('capturing', response.stats);
    } else if (response.state === 'idle') {
      stopStatusPolling();
      if (response.stats) {
        state.lastStats = response.stats;
      }
      updateUI('idle');
    }
  } catch (error) {
    // Ignore polling errors
  }
}
