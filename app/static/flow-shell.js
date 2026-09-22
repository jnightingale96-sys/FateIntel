/* Assessment setup shell: chemical group and track choosers, the stage rail, and per-region / per-group screen visibility.
 * All rules come from /api/workflow (app/services/workflow_registry.py). If that call fails, nothing is hidden and the
 * page behaves as it did before, so a registry problem can never remove a screen a user needs. */
(function () {
  "use strict";
  const $id = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // The group a chosen chemical group is filed under on the existing use cards. Only used to keep the older use cards
  // (which drive the pharma and veterinary panels) consistent with the group; the group itself is what is sent to the plan.
  const USE_FOR_GROUP = {
    human_pharmaceutical: "pharmaceutical", veterinary_pharmaceutical: "veterinary", industrial_organic: "industrial",
    pesticide: "agriculture", biocide: "industrial", personal_care_cosmetic: "consumer", detergent_cleaner: "consumer",
    emerging_contaminant: "waste", pfas_persistent_mobile: "industrial", hydrocarbon_solvent: "industrial",
    metal_inorganic: "industrial", pah: "industrial", legacy_pop_organic: "industrial", organotin: "industrial",
    polymer_microplastic: "industrial", nanomaterial: "industrial", uvcb_complex_substance: "industrial",
    mixture_formulation: "consumer", radionuclide: "industrial", contaminated_mixture: "industrial",
  };
  const STATUS = {
    available: ["Ready", "ok"], managed_external: ["External model, managed", "ext"],
    external_required: ["External model required", "ext"], partial: ["Partly mapped", "warn"],
    not_built: ["Not built", "gap"], not_established: ["Not established", "gap"],
  };
  const RECEPTOR = { human: "human health", ecological: "ecological", groundwater: "groundwater", surface_water: "surface water" };

  const FS = { ref: null, group: null, track: null, workflow: null, seq: 0, syncing: false };

  const regionKey = () => state.modelSystem;
  const familyOf = (group) => FS.ref?.families.find((f) => f.groups.some((g) => g.key === group)) || null;
  const activeTrack = () => FS.workflow?.tracks.find((t) => t.id === FS.track) || null;

  async function getJson(url) {
    const response = await fetch(url);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed: ${response.status}`);
    return body;
  }

  function showEverything() {
    document.querySelectorAll(".flow-hidden").forEach((el) => el.classList.remove("flow-hidden"));
    $id("assessment-flow")?.classList.remove("flow-blocked");
  }

  function applyModules() {
    const wf = FS.workflow;
    if (!wf || !FS.ref) return showEverything();
    const track = activeTrack();
    const shown = new Set(wf.blocked ? wf.modules : track ? track.modules : wf.modules);
    for (const [id, module] of Object.entries(FS.ref.modules)) {
      const show = shown.has(id);
      $id(module.section)?.classList.toggle("flow-hidden", !show);
      document.querySelectorAll(`.nav-item[data-scroll="${module.section}"]`).forEach((n) => n.classList.toggle("flow-hidden", !show));
    }
    // The regulatory route card sits inside the assessment flow: a blocked group keeps the flow but only that card.
    if (wf.blocked) {
      $id("assessment-flow")?.classList.remove("flow-hidden");
      document.querySelectorAll('.nav-item[data-scroll="assessment-flow"], .nav-item[data-scroll="regulatory-pathway"]').forEach((n) => n.classList.remove("flow-hidden"));
    }
    $id("assessment-flow")?.classList.toggle("flow-blocked", Boolean(wf.blocked));
    // The refinement heading only makes sense while at least one refinement screen is in the flow.
    $id("advanced-refinement")?.classList.toggle("flow-hidden", !["water_sediment", "pearl", "us_models"].some((m) => shown.has(m)));
    // Keep the contaminated-land jurisdiction inside the chosen region.
    const jurisdiction = $id("cl-jurisdiction");
    if (jurisdiction && shown.has("contaminated_land") && !wf.jurisdictions.includes(jurisdiction.value)) {
      const target = wf.jurisdictions[0];
      if ([...jurisdiction.options].some((o) => o.value === target)) jurisdiction.value = target;
    }
  }

  function choice(label, selected, onClick, extra = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "flow-choice";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", selected ? "true" : "false");
    button.textContent = label;
    if (extra) button.title = extra;
    button.addEventListener("click", onClick);
    return button;
  }

  function renderChoosers() {
    const family = familyOf(FS.group);
    const families = $id("flow-families");
    families.replaceChildren(...FS.ref.families.map((f) =>
      choice(f.label, family?.id === f.id, () => setGroup(f.groups[0].key))));
    const groups = $id("flow-groups");
    const many = family && family.groups.length > 1;
    groups.classList.toggle("hidden", !many);
    groups.replaceChildren(...(many ? family.groups.map((g) => choice(g.label, g.key === FS.group, () => setGroup(g.key), g.taxonomy)) : []));
    const tracks = $id("flow-tracks");
    const wf = FS.workflow;
    const list = wf && !wf.blocked ? wf.tracks : [];
    tracks.classList.toggle("hidden", list.length < 2);
    tracks.replaceChildren(...(list.length > 1 ? list.map((t) => choice(t.label, t.id === FS.track, () => setTrack(t.id))) : []));
  }

  function stageItem(stage, visibleModules) {
    const [text, tone] = STATUS[stage.status] || [stage.status, "gap"];
    const li = document.createElement("li");
    li.className = "flow-stage";
    const section = stage.module && visibleModules.has(stage.module) ? FS.ref.modules[stage.module]?.section : null;
    const inner = `<span class="flow-pill ${tone}">${esc(text)}</span><strong>${esc(stage.label)}</strong>`
      + (stage.detail ? `<small>${esc(stage.detail)}</small>` : "")
      + (stage.note ? `<small class="flow-stage-note">${esc(stage.note)}</small>` : "");
    if (section) {
      li.innerHTML = `<button type="button" class="flow-stage-link" data-target="${esc(section)}">${inner}</button>`;
      li.querySelector("button").addEventListener("click", () => $id(section)?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } else {
      li.innerHTML = inner;
    }
    return li;
  }

  function methodsBlock(track) {
    if (!track.methods) return "";
    const named = track.methods.filter((m) => m.named).length;
    const rows = track.methods.map((m) => `<li class="${m.named ? "" : "none"}"><strong>${esc(m.jurisdiction)}</strong> · ${esc(RECEPTOR[m.receptor] || m.receptor)}: ${esc(m.route)}</li>`).join("");
    return `<details class="flow-methods"><summary>Regional methods (${named} of ${track.methods.length} named)</summary><ul>${rows}</ul></details>`;
  }

  function renderRail() {
    const wf = FS.workflow;
    const rail = $id("flow-rail");
    const note = $id("flow-note");
    note.classList.toggle("blocked", Boolean(wf?.blocked));
    if (!wf) { rail.replaceChildren(); note.textContent = ""; return; }
    if (wf.blocked) {
      rail.replaceChildren();
      note.innerHTML = `<strong>${esc(wf.group_label)}.</strong> ${esc(wf.reason)}`;
      return;
    }
    const track = activeTrack();
    const shown = new Set(track ? track.modules : wf.modules);
    rail.replaceChildren(...(track ? track.stages.map((s) => stageItem(s, shown)) : []));
    const site = track?.id === "site";
    note.innerHTML = `<strong>${esc(wf.region_label)} · ${esc(wf.group_label)}.</strong> `
      + (site ? "Site assessment: potential linkages only, with no exposure or risk calculated. " : "")
      + `Screens for other groups and regions are hidden.` + (track ? methodsBlock(track) : "");
  }

  function render() {
    if (!FS.ref) return;
    renderChoosers();
    renderRail();
    applyModules();
  }

  async function refresh() {
    if (!FS.ref) return;
    const ticket = ++FS.seq;
    try {
      const wf = await getJson(`/api/workflow?region=${encodeURIComponent(regionKey())}&group=${encodeURIComponent(FS.group)}`);
      if (ticket !== FS.seq) return;
      FS.workflow = wf;
      if (!wf.tracks.some((t) => t.id === FS.track)) FS.track = wf.default_track;
      render();
    } catch (error) {
      if (ticket !== FS.seq) return;
      FS.workflow = null;
      showEverything();
      $id("flow-rail")?.replaceChildren();
      const note = $id("flow-note");
      if (note) { note.classList.remove("blocked"); note.textContent = `The workflow could not be loaded (${error.message}). All screens are shown.`; }
    }
  }

  function setTrack(track) {
    FS.track = track;
    render();
  }

  function setGroup(group) {
    FS.group = group;
    state.flowGroup = group;
    FS.track = null;
    // Keep the older use cards consistent (they drive the pharma and veterinary panels). Clicking one re-plans the route.
    const use = USE_FOR_GROUP[group];
    const card = use ? document.querySelector(`#use-cards [data-use="${use}"]`) : null;
    if (card && !card.classList.contains("active")) {
      FS.syncing = true;
      try { card.click(); } finally { FS.syncing = false; }
    } else {
      try { updateSummaries(); updateModels(); refreshRegulatoryPathway(); } catch (error) { /* the plan panel reports its own errors */ }
    }
    refresh();
  }

  function onUseCardClicked(use) {
    if (FS.syncing || !FS.ref) return;
    const group = (typeof USE_PRODUCT_CLASS !== "undefined" && USE_PRODUCT_CLASS[use]) || null;
    if (!group) return;
    FS.group = group;
    state.flowGroup = group;
    FS.track = null;
    refresh();
  }

  async function init() {
    try {
      FS.ref = await getJson("/api/workflow/reference");
    } catch (error) {
      const note = $id("flow-note");
      if (note) note.textContent = `The workflow could not be loaded (${error.message}). All screens are shown.`;
      return;
    }
    FS.group = state.flowGroup || (typeof USE_PRODUCT_CLASS !== "undefined" && USE_PRODUCT_CLASS[state.use]) || "human_pharmaceutical";
    await refresh();
  }

  window.flowShell = { refresh, setGroup, setTrack, onUseCardClicked, _state: FS };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
