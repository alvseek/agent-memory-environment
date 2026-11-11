// Disposable instrumentation only. No watcher, power requests or user config writes.
import { appendFileSync } from "node:fs";

export default {
  id: "joro-lifecycle-probe",
  async setup(ctx) {
    const file = process.env.JORO_QA_EVENT_FILE;
    if (!file) throw new Error("Probe requires an explicitly injected event path");
    const record = (event, fields = {}) =>
      appendFileSync(file, JSON.stringify({ event, at: Date.now(), ...fields }) + "\n");
    record("plugin_setup", { version: ctx.app.version });
    // This transform affects this private test server only, not saved configuration.
    await ctx.mcp.transform((editor) => {
      for (const [name] of editor.list()) editor.update(name, (server) => { server.disabled = true; });
    });
    await ctx.tool.transform((editor) => {
      editor.add({
        name: "joro_probe",
        description: "Run the harmless two-second Joro lifecycle specimen exactly once.",
        input: { type: "object", properties: {}, additionalProperties: false },
        options: { codemode: false },
        async execute(_input, context) {
          record("controlled_tool_started", { sessionID: context.sessionID });
          await new Promise((resolve) => setTimeout(resolve, 2000));
          record("controlled_tool_finished", { sessionID: context.sessionID });
          return { content: "JORO_CONTROLLED_PROBE" };
        },
      });
    });
    const waits = new Set();
    const contextHook = await ctx.session.hook("context", (request) => {
      if (request.agent !== "joro-lifecycle-probe") return;
      record("context_dispatch", { sessionID: request.sessionID, tools: Object.keys(request.tools) });
      request.system.splice(0, request.system.length, {
        type: "text", text: "Controlled QA only: call joro_probe exactly once, then reply PROBE_DONE. Do not repeat it.",
      });
      for (const name of Object.keys(request.tools)) if (name !== "joro_probe") delete request.tools[name];
      if (!waits.has(request.sessionID)) {
        waits.add(request.sessionID);
        void ctx.session.wait({ sessionID: request.sessionID })
          .then(() => record("session_wait_returned", { sessionID: request.sessionID }))
          .catch(() => record("session_wait_rejected", { sessionID: request.sessionID }));
      }
    });
    const controller = new AbortController();
    const observer = (async () => {
      try {
        for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
          if (/^(session\.(execution\.|idle|created)|permission\.|form\.|shell\.)/.test(event.type)) {
            const data = event.data ?? {};
            record(event.type, {
              sessionID: data.sessionID ?? data.form?.sessionID ?? (event.type === "session.created" ? data.info?.id : undefined),
              requestID: data.requestID ?? data.id ?? data.form?.id,
              shellID: data.info?.id,
            });
          }
        }
      } catch {
        if (!controller.signal.aborted) record("event_subscription_failed");
      }
    })();
    return async () => {
      controller.abort();
      await observer;
      await contextHook.dispose();
      record("plugin_cleanup");
    };
  },
};
