import { execFile } from "node:child_process";
import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";

export default {
  id: "joro-keep-awake",
  async setup(ctx) {
    const config = JSON.parse(readFileSync(new URL("./config.json", import.meta.url), "utf8"));
    const producer = randomUUID();
    const owned = new Set();
    const sessions = new Map();
    const pending = new Map();
    let stopped = false;
    let writes = Promise.resolve();
    const emit = (work, active) => {
      const job = writes.catch(() => {}).then(() => new Promise((resolve, reject) => {
        const child = execFile(config.python, [config.helper, "event"], { windowsHide: true }, (error, _out, err) => {
          if (error) reject(new Error(err || "Joro activity update failed")); else resolve();
        });
        child.stdin.on("error", reject);
        child.stdin.end(JSON.stringify({ client: "opencode", producer, work, pid: process.pid, active }));
      }));
      writes = job;
      return job;
    };
    const set = async (work, active) => {
      if (stopped && active) return;
      await emit(work, active);
      if (stopped && active) { await emit(work, false); return; }
      if (active) owned.add(work); else owned.delete(work);
    };
    const done = async (id) => {
      sessions.delete(id);
      pending.delete(id);
      await set("session:" + id, false);
    };
    const started = async (request) => {
      if (stopped) return;
      const id = request.sessionID;
      if (!pending.get(id)?.size) await set("session:" + id, true);
      if (stopped) return;
      if (!sessions.has(id)) {
        const token = {};
        sessions.set(id, token);
        void ctx.session.wait({ sessionID: id }).finally(async () => {
          if (sessions.get(id) === token) await done(id);
        }).catch((error) => console.warn("Joro:", error.message));
      }
    };
    const guardedStart = async (request) => {
      try { await started(request); }
      catch (error) { console.warn("Joro monitoring failed:", error.message); }
    };
    const contextHook = await ctx.session.hook("context", guardedStart);
    const compactionHook = await ctx.session.hook("compaction", guardedStart);
    const controller = new AbortController();
    const observer = (async () => {
      try {
        for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
          const d = event.data ?? {};
          if (event.type === "shell.created") await set("shell:" + d.info.id, true);
          else if (["shell.exited", "shell.deleted"].includes(event.type)) await set("shell:" + d.id, false);
          else if (["permission.asked", "form.created", "question.asked"].includes(event.type)) {
            const id = d.sessionID ?? d.form?.sessionID;
            if (sessions.has(id)) {
              const waiting = pending.get(id) ?? new Set();
              waiting.add(d.id ?? d.form?.id);
              pending.set(id, waiting);
              await set("session:" + id, false);
            }
          } else if (["permission.replied", "form.replied", "form.cancelled", "question.replied", "question.rejected"].includes(event.type)) {
            const id = d.sessionID ?? d.form?.sessionID;
            const waiting = pending.get(id);
            waiting?.delete(d.requestID ?? d.id ?? d.form?.id);
            if (waiting?.size === 0) {
              pending.delete(id);
              if (sessions.has(id)) await set("session:" + id, true);
            }
          }
        }
      } catch (error) {
        if (!controller.signal.aborted) console.warn("Joro monitoring failed:", error.message);
      }
    })();
    return async () => {
      stopped = true;
      controller.abort();
      await observer;
      await contextHook.dispose();
      await compactionHook.dispose();
      sessions.clear();
      await Promise.all([...owned].map((work) => emit(work, false)));
    };
  },
};
