import { API_BASE } from '../config.js';

export async function get(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `${API_BASE}/${path}?${qs}` : `${API_BASE}/${path}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function post(path, body) {
    const res = await fetch(`${API_BASE}/${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function del(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `${API_BASE}/${path}?${qs}` : `${API_BASE}/${path}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}
