/**
 * Auth extraction: grab cookies and storage tokens from the current page.
 */

/**
 * Grab auth data from the current tab.
 *
 * Returns { cookies: "name=val; ...", tokens: [{source, key, value}] }
 * or null if nothing found.
 */
export async function grabAuth(tabUrl, tabId) {
  const results = { cookies: null, tokens: [] };

  // 1. Get cookies for this URL
  try {
    const cookies = await chrome.cookies.getAll({ url: tabUrl });
    if (cookies.length > 0) {
      results.cookies = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
    }
  } catch (e) {
    console.warn('Failed to read cookies:', e);
  }

  // 2. Scan localStorage/sessionStorage for token-like keys
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        const pattern = /token|auth|jwt|api_key|apikey|session/i;
        const found = [];
        for (const [storeName, storage] of [['localStorage', localStorage], ['sessionStorage', sessionStorage]]) {
          for (let i = 0; i < storage.length; i++) {
            const key = storage.key(i);
            if (pattern.test(key)) {
              found.push({ source: storeName, key, value: storage.getItem(key) });
            }
          }
        }
        return found;
      },
    });
    if (result && result.length > 0) {
      results.tokens = result;
    }
  } catch (e) {
    console.warn('Failed to scan storage:', e);
  }

  if (!results.cookies && results.tokens.length === 0) {
    return null;
  }

  return results;
}
