/*
 * Chronos front-end helpers.
 *
 *   Chronos.renderQuestionnaire(el)        builds the full optional questionnaire
 *   Chronos.collectAnswers(el)             returns only the answered, visible fields
 *   Chronos.mountCorrection(el, options)   "Correct reading" button and form
 *   Chronos.mountExpertPage(el)            the /expert review screen
 *
 * Everything user- or model-written is inserted as text, never as HTML.
 */
(function () {
  "use strict";

  const SECTIONS = ["personal", "heart", "medical", "nutrition", "psychological", "security"];
  const SECTION_LABELS = {
    personal: "Personal", heart: "Heart", medical: "Medical",
    nutrition: "Nutrition", psychological: "Psychological", security: "Safety",
  };
  const MAIN_FIELDS = [
    { key: "biological_age", label: "Biological age", unit: "years" },
    { key: "life_expectancy", label: "Life expectancy", unit: "years" },
    { key: "health_score", label: "Health score", unit: "out of 100" },
  ];
  const CODE_KEY = "chronos-expert-code";

  // ------------------------------------------------------------ helpers

  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const child of children.flat(Infinity)) {
      if (child == null || child === false) continue;
      node.append(child instanceof Node ? child : String(child));
    }
    return node;
  }

  function num(v) {
    if (v == null || v === "") return "";
    return String(Math.round(Number(v) * 10) / 10);
  }

  function signed(v) {
    if (v == null || v === "") return "";
    const n = Math.round(Number(v) * 10) / 10;
    return (n > 0 ? "+" : "") + n;
  }

  function getCode() {
    try { return sessionStorage.getItem(CODE_KEY) || ""; } catch (e) { return ""; }
  }

  function setCode(code) {
    try { sessionStorage.setItem(CODE_KEY, code); } catch (e) { /* storage blocked */ }
  }

  async function api(path, { method = "GET", body, code } = {}) {
    const headers = { "X-Expert-Code": code ?? getCode() };
    if (body) headers["Content-Type"] = "application/json";
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    let data = {};
    try { data = await res.json(); } catch (e) { /* non-JSON error page */ }
    if (!res.ok || !data.success) {
      throw new Error(data.error || `The server answered with status ${res.status}.`);
    }
    return data;
  }

  function paragraphs(text) {
    return String(text || "").split(/\n\s*\n/).filter(Boolean).map((p) => h("p", {}, p.trim()));
  }

  // ------------------------------------------------------------ green number arrows

  const ARROW_UP = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 2 9.5 7.5H.5z" fill="currentColor"/></svg>';
  const ARROW_DOWN = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 8 .5 2.5h9z" fill="currentColor"/></svg>';

  /**
   * Give every number box inside root a pair of green up/down buttons.
   * Optional data attributes on the input: data-step (default 1), data-start (value used
   * when the box is empty), data-floor (lowest value the arrows go to).
   * Safe to call repeatedly; boxes that already have arrows are skipped.
   */
  function addSteppers(root) {
    (root || document).querySelectorAll('input[type="number"]:not([data-stepper])').forEach((input) => {
      input.dataset.stepper = "1";
      const wrap = h("div", { class: "chr-num" });
      input.parentNode.insertBefore(wrap, input);
      wrap.append(input);

      const nudge = (dir) => {
        const step = Number(input.dataset.step) || 1;
        const raw = input.value.trim();
        let next;
        if (raw === "" || isNaN(Number(raw))) {
          next = input.dataset.start != null ? Number(input.dataset.start)
            : input.min !== "" ? Number(input.min) : 0;
        } else {
          next = Number(raw) + dir * step;
        }
        const floor = input.dataset.floor != null ? Number(input.dataset.floor)
          : input.min !== "" ? Number(input.min) : -Infinity;
        const ceil = input.max !== "" ? Number(input.max) : Infinity;
        next = Math.min(ceil, Math.max(floor, next));
        const decimals = Math.max(
          (String(step).split(".")[1] || "").length,
          (raw.split(".")[1] || "").length);
        input.value = String(Number(next.toFixed(Math.min(decimals, 4))));
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      };

      const up = h("button", { type: "button", tabindex: "-1", "aria-label": "Increase", title: "Increase" });
      const down = h("button", { type: "button", tabindex: "-1", "aria-label": "Decrease", title: "Decrease" });
      up.innerHTML = ARROW_UP;
      down.innerHTML = ARROW_DOWN;
      up.addEventListener("click", () => nudge(1));
      down.addEventListener("click", () => nudge(-1));
      // Keep focus in the box so typing carries on naturally after a click.
      [up, down].forEach((b) => b.addEventListener("mousedown", (e) => e.preventDefault()));
      wrap.append(h("div", { class: "chr-num-btns" }, up, down));
    });
  }

  // ------------------------------------------------------------ questionnaire

  function renderField(field) {
    const id = "chr-q-" + field.key;
    let control;
    if (field.type === "select") {
      control = h("select", { id, name: field.key },
        h("option", { value: "" }, "Not answered"),
        field.options.map((o) => h("option", { value: o }, o)));
    } else if (field.type === "number") {
      control = h("input", { id, name: field.key, type: "number", step: "any", inputmode: "decimal" });
    } else {
      control = h("input", { id, name: field.key, type: "text", maxlength: 500, autocomplete: "off" });
    }

    const wrap = h("div", { class: "chr-field" },
      h("label", { for: id }, field.label, field.unit ? h("span", { class: "chr-unit" }, field.unit) : null),
      control,
      field.help ? h("small", { class: "chr-help" }, field.help) : null,
      field.type === "number"
        ? h("small", { class: "chr-warn" }, "That looks unusual. Check the number and the unit.")
        : null);

    wrap.dataset.key = field.key;
    if (field.min != null) wrap.dataset.min = field.min;
    if (field.max != null) wrap.dataset.max = field.max;
    if (field.show_if) wrap.dataset.showIf = JSON.stringify(field.show_if);
    return wrap;
  }

  function refreshQuestionnaire(container) {
    container.querySelectorAll("[data-show-if]").forEach((wrap) => {
      const rule = JSON.parse(wrap.dataset.showIf);
      wrap.hidden = !Object.entries(rule).every(([key, allowed]) => {
        const ctl = container.querySelector(`[name="${key}"]`);
        return ctl && allowed.includes(ctl.value);
      });
    });

    container.querySelectorAll('.chr-field input[type="number"]').forEach((input) => {
      const wrap = input.closest(".chr-field");
      const v = input.value === "" ? null : Number(input.value);
      const low = wrap.dataset.min != null ? Number(wrap.dataset.min) : -Infinity;
      const high = wrap.dataset.max != null ? Number(wrap.dataset.max) : Infinity;
      wrap.classList.toggle("chr-unusual", v != null && (v < low || v > high));
    });

    container.querySelectorAll(".chr-section").forEach((section) => {
      const fields = [...section.querySelectorAll(".chr-field")].filter((f) => !f.hidden);
      const answered = fields.filter((f) => f.querySelector("input, select").value.trim() !== "").length;
      section.querySelector(".chr-count").textContent = `${answered} of ${fields.length} answered`;
    });
  }

  async function renderQuestionnaire(container) {
    const res = await fetch("/api/questions");
    const data = await res.json();

    container.replaceChildren();
    container.classList.add("chr", "chr-form");
    container.append(h("p", { class: "chr-note" },
      "Every question is optional. Answer what you know: the more you fill in, the more reliable the reading."));

    data.sections.forEach((section, i) => {
      container.append(h("details", { class: "chr-section", open: i === 0 },
        h("summary", {}, h("span", { class: "chr-section-title" }, section.title), h("span", { class: "chr-count" })),
        section.intro ? h("p", { class: "chr-intro" }, section.intro) : null,
        h("div", { class: "chr-grid" }, section.fields.map(renderField))));
    });

    addSteppers(container);
    const refresh = () => refreshQuestionnaire(container);
    container.addEventListener("input", refresh);
    container.addEventListener("change", refresh);
    refresh();
  }

  function collectAnswers(container) {
    const answers = {};
    container.querySelectorAll(".chr-field").forEach((wrap) => {
      if (wrap.hidden) return;
      const ctl = wrap.querySelector("input, select");
      const value = ctl.value.trim();
      if (value === "") return;
      answers[ctl.name] = ctl.type === "number" ? Number(value) : value;
    });
    return answers;
  }

  // ------------------------------------------------------------ correction panel

  /**
   * options:
   *   assessmentId       from the /api/manual or /api/pdf response
   *   reading            the model's reading (response.reading)
   *   start              values to prefill, defaults to reading (the expert page passes
   *                      the latest corrected values so a second expert builds on them)
   *   chronologicalAge   for the consistency hint, optional
   *   onSaved(result)    called after a successful save
   */
  function mountCorrection(container, options) {
    const { assessmentId, reading = {}, chronologicalAge = null, onSaved } = options;
    const start = options.start || reading;
    container.replaceChildren();
    container.classList.add("chr", "chr-correction");

    if (!assessmentId) {
      container.append(h("p", { class: "chr-muted" },
        "This reading wasn't saved, so it can't be corrected."));
      return;
    }

    const mainInputs = {};
    const scoreInputs = {};

    function numberInput(name, baseline, prefill, label, unit, isScore) {
      const id = `chr-c-${assessmentId}-${name}`;
      const input = h("input", { id, type: "number", step: "any", inputmode: "decimal", value: num(prefill) });
      input.dataset.baseline = baseline == null ? "" : String(baseline);
      const modelNote = h("span", { class: "chr-model-value" },
        baseline == null ? "Model gave no value" : `Model: ${isScore ? signed(baseline) : num(baseline)}`);
      const wrap = h("div", { class: "chr-cfield" },
        h("label", { for: id }, label, unit ? h("span", { class: "chr-unit" }, unit) : null),
        input, modelNote);
      input.addEventListener("input", () => {
        wrap.classList.toggle("chr-changed", isChanged(input));
        updateSum();
      });
      wrap.classList.toggle("chr-changed", isChanged(input));
      return { wrap, input };
    }

    function isChanged(input) {
      const v = input.value.trim();
      if (v === "") return false;
      const base = input.dataset.baseline;
      return base === "" || Math.abs(Number(v) - Number(base)) > 1e-9;
    }

    const codeInput = h("input", { id: `chr-c-${assessmentId}-code`, type: "password", autocomplete: "off", value: getCode() });
    const nameInput = h("input", { id: `chr-c-${assessmentId}-name`, type: "text", maxlength: 120, autocomplete: "name" });
    const reasonInput = h("textarea", { id: `chr-c-${assessmentId}-reason`, rows: 5, maxlength: 4000 });
    const sumLine = h("p", { class: "chr-sum", "aria-live": "polite" });
    const status = h("p", { class: "chr-status", role: "status" });

    const mainGrid = h("div", { class: "chr-cgrid" }, MAIN_FIELDS.map((f) => {
      const field = numberInput(f.key, reading[f.key], start[f.key], f.label, f.unit, false);
      mainInputs[f.key] = field.input;
      return field.wrap;
    }));

    const scoreGrid = h("div", { class: "chr-cgrid chr-cgrid-scores" }, SECTIONS.map((s) => {
      const field = numberInput(s, (reading.scores || {})[s], (start.scores || {})[s],
        SECTION_LABELS[s], "years", true);
      scoreInputs[s] = field.input;
      return field.wrap;
    }));

    function updateSum() {
      const total = SECTIONS.reduce((sum, s) => sum + (Number(scoreInputs[s].value) || 0), 0);
      let text = `Section scores add up to ${signed(total) || "0"} years.`;
      let mismatch = false;
      const bio = mainInputs.biological_age.value.trim();
      if (chronologicalAge != null && bio !== "") {
        const diff = Number(bio) - Number(chronologicalAge);
        text += ` Biological age minus actual age is ${signed(diff) || "0"}.`;
        mismatch = Math.abs(diff - total) > 0.15;
        if (mismatch) text += " These usually match.";
      }
      sumLine.textContent = text;
      sumLine.classList.toggle("chr-mismatch", mismatch);
    }

    const saveBtn = h("button", { type: "submit", class: "chr-btn" }, "Save correction");
    const cancelBtn = h("button", { type: "button", class: "chr-btn chr-btn-quiet" }, "Cancel");

    const form = h("form", { class: "chr-cform", hidden: true, novalidate: true },
      h("p", { class: "chr-intro" },
        "For doctors and medical experts. Change any value you disagree with and explain why. " +
        "Future readings for similar cases will take your correction into account."),
      h("div", { class: "chr-cgrid chr-cgrid-who" },
        h("div", { class: "chr-cfield" }, h("label", { for: codeInput.id }, "Expert access code"), codeInput),
        h("div", { class: "chr-cfield" }, h("label", { for: nameInput.id }, "Your name"), nameInput)),
      h("fieldset", {}, h("legend", {}, "Reading"), mainGrid),
      h("fieldset", {}, h("legend", {}, "Years added or removed by each section"), scoreGrid, sumLine),
      h("div", { class: "chr-cfield chr-reason" },
        h("label", { for: reasonInput.id }, "Why was the model's reading wrong?"),
        reasonInput,
        h("small", { class: "chr-help" },
          "Name the findings it over- or under-weighted. This is what future readings learn from.")),
      h("div", { class: "chr-actions" }, saveBtn, cancelBtn),
      status);

    const openBtn = h("button", { type: "button", class: "chr-btn chr-btn-quiet" }, "Correct reading");

    openBtn.addEventListener("click", () => {
      openBtn.hidden = true;
      form.hidden = false;
      (codeInput.value ? nameInput : codeInput).focus();
    });
    cancelBtn.addEventListener("click", () => {
      form.hidden = true;
      openBtn.hidden = false;
      status.textContent = "";
      openBtn.focus();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      status.className = "chr-status";

      const payload = { expert_name: nameInput.value.trim(), reason: reasonInput.value.trim(), scores: {} };
      for (const [key, input] of Object.entries(mainInputs)) {
        if (isChanged(input)) payload[key] = Number(input.value);
      }
      for (const [key, input] of Object.entries(scoreInputs)) {
        if (isChanged(input)) payload.scores[key] = Number(input.value);
      }

      const problems = [];
      if (!codeInput.value.trim()) problems.push("Enter the expert access code.");
      if (!payload.expert_name) problems.push("Enter your name.");
      if (payload.reason.length < 15) problems.push("Explain why the reading was wrong, in at least a sentence.");
      const anyChange = MAIN_FIELDS.some((f) => f.key in payload) || Object.keys(payload.scores).length > 0;
      if (!anyChange) problems.push("Change at least one value before saving.");
      if (problems.length) {
        status.textContent = problems.join(" ");
        status.classList.add("chr-error");
        return;
      }

      saveBtn.disabled = true;
      saveBtn.textContent = "Saving…";
      try {
        const code = codeInput.value.trim();
        const result = await api(`/api/assessments/${assessmentId}/corrections`, { method: "POST", body: payload, code });
        setCode(code);
        container.replaceChildren(h("div", { class: "chr-saved", role: "status" },
          h("p", {}, `Correction saved by ${payload.expert_name}.`),
          h("p", { class: "chr-muted" }, result.indexed
            ? "Future readings for similar cases will take it into account."
            : "It's stored, but couldn't be added to the learning index just now. Saving it again later will add it.")));
        if (onSaved) onSaved(result);
      } catch (err) {
        status.textContent = err.message;
        status.classList.add("chr-error");
        saveBtn.disabled = false;
        saveBtn.textContent = "Save correction";
      }
    });

    updateSum();
    container.append(openBtn, form);
    form.querySelectorAll('input[type="number"]').forEach((i) => {
      i.dataset.step = /life_expectancy|health_score/.test(i.id) ? "1" : "0.5";
    });
    addSteppers(form);
  }

  // ------------------------------------------------------------ expert page

  function effectiveReading(assessment) {
    const base = assessment.reading;
    const active = assessment.corrections.filter((c) => c.active);
    const latest = active[active.length - 1];
    if (!latest) return { reading: base, latest: null };
    const merged = { ...base, scores: { ...(base.scores || {}) } };
    for (const f of MAIN_FIELDS) {
      if (latest.reading[f.key] != null) merged[f.key] = latest.reading[f.key];
    }
    Object.assign(merged.scores, latest.reading.scores || {});
    return { reading: merged, latest };
  }

  function comparisonTable(assessment) {
    const { latest } = effectiveReading(assessment);
    const rows = [
      ...MAIN_FIELDS.map((f) => [f.label, assessment.reading[f.key], latest && latest.reading[f.key], false]),
      ...SECTIONS.map((s) => [SECTION_LABELS[s] + " section",
        (assessment.reading.scores || {})[s], latest && (latest.reading.scores || {})[s], true]),
    ];
    return h("table", { class: "chr-table chr-compare" },
      h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Value"), h("th", { scope: "col" }, "Reading"))),
      h("tbody", {}, rows.map(([label, model, fixed, isScore]) => {
        const show = (v) => (isScore ? signed(v) : num(v)) || "none";
        const cell = fixed != null
          ? h("td", {}, h("s", { class: "chr-was" }, show(model)), " ", h("span", { class: "chr-pen" }, show(fixed)))
          : h("td", {}, show(model));
        return h("tr", {}, h("th", { scope: "row" }, label), cell);
      })));
  }

  function mountExpertPage(root) {
    root.classList.add("chr", "chr-expert");

    function showGate(message) {
      const input = h("input", { id: "chr-gate-code", type: "password", autocomplete: "off" });
      const status = h("p", { class: "chr-status chr-error", role: "status" }, message || "");
      const form = h("form", { class: "chr-gate" },
        h("h1", {}, "Expert review"),
        h("p", { class: "chr-muted" }, "Readings contain personal health data. Enter the expert access code to see them."),
        h("label", { for: input.id }, "Expert access code"),
        input,
        h("button", { type: "submit", class: "chr-btn" }, "Open readings"),
        status);
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await api("/api/expert/check", { method: "POST", code: input.value.trim() });
          setCode(input.value.trim());
          showList();
        } catch (err) {
          status.textContent = err.message;
        }
      });
      root.replaceChildren(form);
      input.focus();
    }

    async function showList() {
      root.replaceChildren(h("p", { class: "chr-muted" }, "Loading readings…"));
      let data;
      try {
        data = await api("/api/assessments?limit=100");
      } catch (err) {
        return showGate(err.message);
      }

      const list = data.assessments;
      const header = h("header", { class: "chr-pagehead" },
        h("h1", {}, "Expert review"),
        h("p", { class: "chr-muted" },
          "Open a reading to check it. Values you correct are struck through in red, and similar future cases learn from them."));

      if (!list.length) {
        root.replaceChildren(header, h("p", {}, "No readings yet. They appear here as soon as someone runs an assessment."));
        return;
      }

      const table = h("table", { class: "chr-table chr-list" },
        h("thead", {}, h("tr", {},
          ["Reading", "Date", "Source", "Age", "Biological age", "Health score", "Corrections"]
            .map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, list.map((a) => {
          const open = h("button", { type: "button", class: "chr-link", onclick: () => showDetail(a.id) }, `#${a.id}`);
          return h("tr", { class: a.correction_count ? "chr-row-fixed" : null },
            h("td", {}, open),
            h("td", {}, new Date(a.created_at).toLocaleString()),
            h("td", {}, a.source === "pdf" ? `Lab report${a.filename ? ": " + a.filename : ""}` : "Questionnaire"),
            h("td", {}, num(a.chronological_age) || "not given"),
            h("td", {}, num(a.biological_age) || "none"),
            h("td", {}, num(a.health_score) || "none"),
            h("td", {}, a.correction_count ? String(a.correction_count) : ""));
        })));

      root.replaceChildren(header, h("div", { class: "chr-scroll" }, table));
    }

    async function showDetail(id) {
      root.replaceChildren(h("p", { class: "chr-muted" }, "Loading reading…"));
      let assessment;
      try {
        assessment = (await api(`/api/assessments/${id}`)).assessment;
      } catch (err) {
        return showGate(err.message);
      }

      const { reading: current } = effectiveReading(assessment);
      const back = h("button", { type: "button", class: "chr-link", onclick: showList }, "All readings");

      const history = assessment.corrections.length
        ? h("section", { class: "chr-block" },
            h("h2", {}, "Correction history"),
            h("ol", { class: "chr-history" }, assessment.corrections.map((c) =>
              h("li", { class: c.active ? null : "chr-inactive" },
                h("p", { class: "chr-who" }, `${c.expert_name}, ${new Date(c.created_at).toLocaleString()}`),
                h("p", {}, c.reason)))))
        : null;

      const panel = h("div");
      root.replaceChildren(
        h("nav", {}, back),
        h("header", { class: "chr-pagehead" },
          h("h1", {}, `Reading #${assessment.id}`),
          h("p", { class: "chr-muted" },
            `${assessment.source === "pdf" ? "Lab report" : "Questionnaire"}, ${new Date(assessment.created_at).toLocaleString()}. ` +
            `Actual age ${num(assessment.chronological_age) || "not given"}.`)),
        h("div", { class: "chr-columns" },
          h("section", { class: "chr-block" }, h("h2", {}, "Reading"), comparisonTable(assessment)),
          h("section", { class: "chr-block" }, h("h2", {}, "Model's explanation"), paragraphs(assessment.reading.explanation))),
        h("details", { class: "chr-block chr-input" },
          h("summary", {}, "What the model was shown"),
          h("pre", {}, assessment.input_text)),
        history,
        h("section", { class: "chr-block" }, panel));

      mountCorrection(panel, {
        assessmentId: assessment.id,
        reading: assessment.reading,
        start: current,
        chronologicalAge: assessment.chronological_age,
        onSaved: () => setTimeout(() => showDetail(assessment.id), 1200),
      });
    }

    getCode() ? showList() : showGate();
  }

  window.Chronos = { renderQuestionnaire, collectAnswers, mountCorrection, mountExpertPage, addSteppers };
})();