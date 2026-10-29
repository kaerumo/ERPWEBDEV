// ============================================================
// ITPC ERP — js/auth.js
// Load this file BEFORE js/main.js on every page.
//
// Everything here is front-end only (no server). It covers:
//   1. Accounts stored as salted PBKDF2 hashes (no plain-text passwords)
//   2. Login with a failed-attempt lockout
//   3. Signed sessions that expire (idle + maximum age). The ROLE always
//      comes from ACCOUNTS below, never from anything stored in the browser
//   4. "Sealed" storage: saved data carries an HMAC seal, so hand-editing
//      Local Storage in DevTools is detected and repaired
//   5. Backup signing with a passphrase
//
// HONEST LIMIT: with no server, the code and its keys live in the visitor's
// browser. These measures stop casual tampering (DevTools one-liners and
// hand-edited storage). They cannot stop someone who rewrites the JavaScript
// itself. Real protection against that needs a server.
// ============================================================
const Auth = (() => {
  "use strict";

  // ---------- SETTINGS ----------
  // Create each account's salt + hash with the console snippet in the
  // instructions, then paste the values here. Never type a password here.
  const ACCOUNTS = [
    {
      username: "admin",
      displayName: "Admin",
      role: "admin",
      salt: "PASTE_SALT_HERE",
      hash: "PASTE_HASH_HERE",
      iterations: 600000,
    },
    {
      username: "member",
      displayName: "Member",
      role: "member",
      salt: "PASTE_SALT_HERE",
      hash: "PASTE_HASH_HERE",
      iterations: 600000,
    },
  ];

  const IDLE_LIMIT_MS = 15 * 60 * 1000; // auto log-out after 15 min of no activity
  const SESSION_MAX_MS = 8 * 60 * 60 * 1000; // ...and never stay logged in past 8 h
  const WARN_BEFORE_MS = 60 * 1000; // warn 1 min before the idle log-out
  const FREE_ATTEMPTS = 5; // wrong passwords allowed before a lock starts
  const LOCK_BASE_MS = 30 * 1000; // first lock = 30 s, then it doubles
  const LOCK_MAX_MS = 15 * 60 * 1000; // longest lock = 15 min
  const ALLOW_UNSIGNED_BACKUPS = true; // set to false once everyone has re-exported a signed backup

  const STORE = {
    devKey: "itpc_devkey",
    seals: "itpc_seals",
    session: "itpc_session",
    lockout: "itpc_lockout",
    notice: "itpc_notice",
  };

  // ---------- SMALL HELPERS ----------
  const encoder = new TextEncoder();

  function toHex(bytes) {
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function fromHex(hex) {
    const out = new Uint8Array(hex.length / 2);
    for (let i = 0; i < out.length; i++) {
      out[i] = parseInt(hex.substr(i * 2, 2), 16);
    }
    return out;
  }

  const isHex = (text, minLength) =>
    typeof text === "string" &&
    text.length >= minLength &&
    text.length % 2 === 0 &&
    /^[0-9a-f]+$/.test(text);

  // Compares two strings without stopping at the first difference
  function safeEqual(a, b) {
    if (typeof a !== "string" || typeof b !== "string") return false;
    if (a.length !== b.length) return false;
    let diff = 0;
    for (let i = 0; i < a.length; i++)
      diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return diff === 0;
  }

  function readJSON(storage, key, fallback) {
    try {
      const value = JSON.parse(storage.getItem(key));
      return value === null ? fallback : value;
    } catch (error) {
      return fallback;
    }
  }

  // ---------- SHA-256 + HMAC (plain JavaScript, so sealing can be instant) ----------
  const SHA_K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function sha256(bytes) {
    const H = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c,
      0x1f83d9ab, 0x5be0cd19,
    ]);
    const bitLength = bytes.length * 8;
    const padded = new Uint8Array(Math.ceil((bytes.length + 9) / 64) * 64);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(padded.length - 8, Math.floor(bitLength / 0x100000000));
    view.setUint32(padded.length - 4, bitLength >>> 0);

    const w = new Uint32Array(64);
    for (let offset = 0; offset < padded.length; offset += 64) {
      for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4);
      for (let i = 16; i < 64; i++) {
        const a = w[i - 15];
        const b = w[i - 2];
        const s0 =
          ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
        const s1 =
          ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
      }

      let a = H[0],
        b = H[1],
        c = H[2],
        d = H[3];
      let e = H[4],
        f = H[5],
        g = H[6],
        h = H[7];
      for (let i = 0; i < 64; i++) {
        const S1 =
          ((e >>> 6) | (e << 26)) ^
          ((e >>> 11) | (e << 21)) ^
          ((e >>> 25) | (e << 7));
        const ch = (e & f) ^ (~e & g);
        const t1 = (h + S1 + ch + SHA_K[i] + w[i]) | 0;
        const S0 =
          ((a >>> 2) | (a << 30)) ^
          ((a >>> 13) | (a << 19)) ^
          ((a >>> 22) | (a << 10));
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + maj) | 0;
        h = g;
        g = f;
        f = e;
        e = (d + t1) | 0;
        d = c;
        c = b;
        b = a;
        a = (t1 + t2) | 0;
      }
      H[0] += a;
      H[1] += b;
      H[2] += c;
      H[3] += d;
      H[4] += e;
      H[5] += f;
      H[6] += g;
      H[7] += h;
    }

    const out = new Uint8Array(32);
    const outView = new DataView(out.buffer);
    H.forEach((word, i) => outView.setUint32(i * 4, word));
    return out;
  }

  function concatBytes(a, b) {
    const out = new Uint8Array(a.length + b.length);
    out.set(a);
    out.set(b, a.length);
    return out;
  }

  function hmacHex(keyText, message) {
    let key = encoder.encode(keyText);
    if (key.length > 64) key = sha256(key);
    const inner = new Uint8Array(64);
    const outer = new Uint8Array(64);
    for (let i = 0; i < 64; i++) {
      const k = i < key.length ? key[i] : 0;
      inner[i] = k ^ 0x36;
      outer[i] = k ^ 0x5c;
    }
    const innerHash = sha256(concatBytes(inner, encoder.encode(message)));
    return toHex(sha256(concatBytes(outer, innerHash)));
  }

  // Password -> hex hash (PBKDF2, slow on purpose so guessing is expensive)
  async function pbkdf2Hex(password, saltHex, iterations) {
    const material = await crypto.subtle.importKey(
      "raw",
      encoder.encode(password),
      "PBKDF2",
      false,
      ["deriveBits"],
    );
    const bits = await crypto.subtle.deriveBits(
      {
        name: "PBKDF2",
        hash: "SHA-256",
        salt: fromHex(saltHex),
        iterations: iterations,
      },
      material,
      256,
    );
    return toHex(new Uint8Array(bits));
  }

  // ---------- DEVICE KEY + SEALED STORAGE ----------
  // A random key made once per browser. Every saved list gets an HMAC "seal"
  // made with it. Edit a value by hand in DevTools and the seal no longer
  // matches, so the app knows. A mirror copy of each list is kept so a
  // tampered list can be restored to the last verified version.
  let firstRun = false; // true only on the very first page load in this browser
  let devKey = localStorage.getItem(STORE.devKey);
  if (!isHex(devKey, 64)) {
    devKey = toHex(crypto.getRandomValues(new Uint8Array(32)));
    localStorage.setItem(STORE.devKey, devKey);
    firstRun = true; // existing pre-update data is accepted once and sealed
  }

  let seals = readJSON(localStorage, STORE.seals, {});
  if (typeof seals !== "object" || Array.isArray(seals)) seals = {};
  const issues = [];

  const sealOf = (text) => hmacHex(devKey, text);
  const mirrorKey = (key) => key + "_mirror";
  const quarantineKey = (key) => "itpc_quarantine_" + key.replace(/^itpc_/, "");
  const saveSeals = () =>
    localStorage.setItem(STORE.seals, JSON.stringify(seals));

  function writeSealed(key, data) {
    const text = JSON.stringify(data);
    localStorage.setItem(key, text);
    localStorage.setItem(mirrorKey(key), text);
    seals[key] = sealOf(text);
    saveSeals();
  }

  function clearSealed(key) {
    localStorage.removeItem(key);
    localStorage.removeItem(mirrorKey(key));
    delete seals[key];
    saveSeals();
  }

  // Returns the verified data, or null when there is nothing (valid) saved.
  // `validate(data)` must return true for acceptable data.
  function readSealed(key, validate) {
    const raw = localStorage.getItem(key);
    const mirror = localStorage.getItem(mirrorKey(key));
    const expected = seals[key];

    if (raw === null && mirror === null && expected === undefined) return null; // never saved

    function verified(text) {
      if (text === null) return null;
      let data;
      try {
        data = JSON.parse(text);
      } catch (error) {
        return null;
      }
      if (!validate(data)) return null;
      if (expected === undefined) return firstRun ? data : null; // one-time migration
      return safeEqual(sealOf(text), expected) ? data : null;
    }

    let data = verified(raw);
    if (data !== null) {
      if (expected === undefined) writeSealed(key, data); // migrate: seal it now
      return data;
    }

    data = verified(mirror);
    if (data !== null) {
      issues.push({ key: key, kind: "restored" });
      writeSealed(key, data);
      return data;
    }

    // Nothing trustworthy left: keep the modified copy aside and start clean
    if (raw !== null) localStorage.setItem(quarantineKey(key), raw);
    clearSealed(key);
    issues.push({
      key: key,
      kind: "reset",
      quarantine: raw !== null ? quarantineKey(key) : null,
    });
    return null;
  }

  // ---------- LOGIN LOCKOUT ----------
  const isLockoutShape = (v) =>
    v && Number.isInteger(v.fails) && v.fails >= 0 && Number.isFinite(v.until);

  function loadLockout() {
    const hadRecord = seals[STORE.lockout] !== undefined;
    const value = readSealed(STORE.lockout, isLockoutShape);
    if (value) return value;
    if (hadRecord) {
      // The record was edited or deleted: assume the worst
      const penalty = {
        fails: FREE_ATTEMPTS + 4,
        until: Date.now() + LOCK_MAX_MS,
      };
      writeSealed(STORE.lockout, penalty);
      return penalty;
    }
    return { fails: 0, until: 0 };
  }

  function lockoutState() {
    return { until: loadLockout().until };
  }

  // ---------- SESSION ----------
  // Stored in sessionStorage as { d: {u, iat, last}, s: seal }. It holds NO
  // role: the role is looked up from ACCOUNTS, so a stored value can't grant it.
  let session = null;

  function readSession() {
    const raw = sessionStorage.getItem(STORE.session);
    if (!raw) return null;
    try {
      const pack = JSON.parse(raw);
      if (!safeEqual(sealOf(JSON.stringify(pack.d)), pack.s)) return null;
      const account = ACCOUNTS.find((a) => a.username === pack.d.u);
      if (!account) return null;
      const now = Date.now();
      if (
        now - pack.d.last > IDLE_LIMIT_MS ||
        now - pack.d.iat > SESSION_MAX_MS
      ) {
        sessionStorage.setItem(STORE.notice, "timeout");
        return null;
      }
      return {
        username: account.username,
        name: account.displayName,
        role: account.role,
        iat: pack.d.iat,
        last: pack.d.last,
      };
    } catch (error) {
      return null;
    }
  }

  function saveSession() {
    const d = { u: session.username, iat: session.iat, last: session.last };
    sessionStorage.setItem(
      STORE.session,
      JSON.stringify({ d: d, s: sealOf(JSON.stringify(d)) }),
    );
  }

  session = readSession();
  if (!session) sessionStorage.removeItem(STORE.session);

  const isLoggedIn = () => session !== null;
  const isAdmin = () => session !== null && session.role === "admin";

  function user() {
    if (!session) return { username: null, name: "Guest", role: "none" };
    return {
      username: session.username,
      name: session.name,
      role: session.role,
    };
  }

  function logout(reason) {
    session = null;
    sessionStorage.removeItem(STORE.session);
    if (reason) sessionStorage.setItem(STORE.notice, reason);
  }

  // Message to show on the login page ("timeout"), shown once
  function takeNotice() {
    const notice = sessionStorage.getItem(STORE.notice);
    sessionStorage.removeItem(STORE.notice);
    return notice;
  }

  // Logs out after inactivity. `onWarn(message)` is called ~1 min before.
  function startIdleWatch(onWarn) {
    if (!session) return;
    let lastWrite = 0;
    let warned = false;

    function check() {
      const now = Date.now();
      if (
        now - session.last >= IDLE_LIMIT_MS ||
        now - session.iat >= SESSION_MAX_MS
      ) {
        logout("timeout");
        window.location.replace("index.html");
        return;
      }
      if (!warned && IDLE_LIMIT_MS - (now - session.last) <= WARN_BEFORE_MS) {
        warned = true;
        if (onWarn)
          onWarn("You will be logged out in about a minute due to inactivity.");
      }
    }

    function activity() {
      const now = Date.now();
      if (now - session.last >= IDLE_LIMIT_MS) return check(); // already expired
      session.last = now;
      warned = false;
      if (now - lastWrite > 15000) {
        saveSession();
        lastWrite = now;
      }
    }

    ["click", "keydown", "touchstart", "scroll", "mousemove"].forEach((name) =>
      document.addEventListener(name, activity, { passive: true }),
    );
    document.addEventListener("visibilitychange", check);
    setInterval(check, 5000);
    check();
  }

  // ---------- LOGIN ----------
  const FAKE_SALT = "00".repeat(16); // used so unknown usernames cost the same time

  async function login(username, password) {
    if (!(window.crypto && crypto.subtle)) {
      return {
        ok: false,
        message: "Sign-in needs a secure connection (HTTPS).",
      };
    }

    const lock = loadLockout();
    if (lock.until > Date.now()) {
      return {
        ok: false,
        locked: true,
        until: lock.until,
        message: "Too many failed attempts.",
      };
    }

    const account = ACCOUNTS.find(
      (a) => a.username === String(username).trim().toLowerCase(),
    );
    const usable =
      account && isHex(account.salt, 32) && isHex(account.hash, 64);
    const salt = usable ? account.salt : FAKE_SALT;
    const iterations = usable ? account.iterations : 600000;
    const hash = await pbkdf2Hex(String(password), salt, iterations);

    if (!usable || !safeEqual(hash, account.hash)) {
      lock.fails += 1;
      if (lock.fails >= FREE_ATTEMPTS) {
        const wait = Math.min(
          LOCK_BASE_MS * 2 ** (lock.fails - FREE_ATTEMPTS),
          LOCK_MAX_MS,
        );
        lock.until = Date.now() + wait;
      }
      writeSealed(STORE.lockout, lock);

      const locked = lock.until > Date.now();
      const left = FREE_ATTEMPTS - lock.fails;
      let message = "Invalid username or password.";
      if (!locked && left > 0 && lock.fails >= 2) {
        message +=
          " " +
          left +
          " attempt" +
          (left === 1 ? "" : "s") +
          " left before a temporary lock.";
      }
      return { ok: false, locked: locked, until: lock.until, message: message };
    }

    writeSealed(STORE.lockout, { fails: 0, until: 0 });
    const now = Date.now();
    session = {
      username: account.username,
      name: account.displayName,
      role: account.role,
      iat: now,
      last: now,
    };
    saveSession();
    return { ok: true };
  }

  // ---------- BACKUP SIGNING ----------
  // The passphrase never leaves the browser. It is stretched with PBKDF2 and
  // used as an HMAC key over the backup's contents. Change one character of
  // the file afterwards and verification fails.
  const backupText = (backup) =>
    backup.exportedAt + "|" + JSON.stringify(backup.data);

  async function signBackup(backup, passphrase) {
    const salt = toHex(crypto.getRandomValues(new Uint8Array(16)));
    const iterations = 250000;
    const key = await pbkdf2Hex(passphrase, salt, iterations);
    return {
      ...backup,
      version: 2,
      signature: {
        alg: "PBKDF2-SHA256+HMAC-SHA256",
        salt: salt,
        iterations: iterations,
        mac: hmacHex(key, backupText(backup)),
      },
    };
  }

  async function verifyBackup(backup, passphrase) {
    const sig = backup && backup.signature;
    if (
      !sig ||
      !isHex(sig.salt, 32) ||
      !isHex(sig.mac, 64) ||
      !Number.isInteger(sig.iterations) ||
      sig.iterations < 100000 ||
      sig.iterations > 1000000 ||
      typeof backup.exportedAt !== "string"
    ) {
      return false;
    }
    const key = await pbkdf2Hex(passphrase, sig.salt, sig.iterations);
    return safeEqual(hmacHex(key, backupText(backup)), sig.mac);
  }

  // Integrity problems found since the last call (main.js logs and shows them)
  function takeIssues() {
    return issues.splice(0, issues.length);
  }

  return Object.freeze({
    isLoggedIn: isLoggedIn,
    isAdmin: isAdmin,
    user: user,
    login: login,
    logout: logout,
    takeNotice: takeNotice,
    startIdleWatch: startIdleWatch,
    lockoutState: lockoutState,
    readSealed: readSealed,
    writeSealed: writeSealed,
    clearSealed: clearSealed,
    takeIssues: takeIssues,
    signBackup: signBackup,
    verifyBackup: verifyBackup,
    allowUnsignedBackups: ALLOW_UNSIGNED_BACKUPS,
  });
})();
