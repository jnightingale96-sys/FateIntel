/* Contaminated land / conceptual site model screen.
   Structure only: it maps potential linkages and data gaps and calculates no exposure or risk.
   Uses app.js globals: api(), escapeHtml(), toast(), state. */
(() => {
  "use strict";
  const $id = (id) => document.getElementById(id);
  const esc = (value) => escapeHtml(value);
  const label = (text) => String(text ?? "").replace(/_/g, " ");
  const post = (body) => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const STORE_KEY = "fateintel.contaminatedLand.projectId";

  const CL = {
    ref: null, frameworks: [], sources: [], receptors: new Set(), links: [], measurements: [], saved: [],
    extraMeasured: {}, projectId: null, projectName: null, blobUrl: null,
    activeId: null, editingMeasurement: null, refreshSeq: 0,
  };

  const PROP_KEYS = ["vapour_pressure_mm_hg", "henry_law_constant_atm_m3_mol", "bcf_or_baf_aquatic", "log_kow", "log_koc"];

  function blankContaminant() {
    return { name: "", group: CL.ref.contaminant_groups[0].key, cas: "", props: { vapour_pressure_mm_hg: "", henry_law_constant_atm_m3_mol: "", bcf_or_baf_aquatic: "", log_kow: "", log_koc: "", source: "" } };
  }

  function propsFromPayload(properties) {
    const props = { vapour_pressure_mm_hg: "", henry_law_constant_atm_m3_mol: "", bcf_or_baf_aquatic: "", log_kow: "", log_koc: "", source: "" };
    const sources = [];
    for (const [key, entry] of Object.entries(properties || {})) {
      if (key in props) { props[key] = String(entry.value); if (entry.source && !sources.includes(entry.source)) sources.push(entry.source); }
    }
    props.source = sources.join("; ");
    return props;
  }

  function propertiesPayload(c) {
    const out = {};
    for (const key of PROP_KEYS) {
      const raw = String(c.props[key] ?? "").trim();
      if (raw === "") continue;
      const value = Number(raw);
      if (!Number.isFinite(value)) throw new Error(`${c.name || "A contaminant"}: ${CL.ref.property_specs[key]} must be a number.`);
      if (!c.props.source.trim()) throw new Error(`${c.name || "A contaminant"}: give the source of the property values. None are assumed.`);
      out[key] = { value, source: c.props.source.trim() };
    }
    return out;
  }

  function setStatus(title, detail, kind) {
    const node = $id("cl-status");
    if (!node) return;
    node.classList.toggle("cl-error", kind === "error");
    node.innerHTML = `<strong>${esc(title)}</strong>${detail ? `<small>${esc(detail)}</small>` : ""}`;
  }

  /* ---------- project handling ---------- */
  function appProject() {
    return typeof state !== "undefined" && state && state.project ? state.project : null;
  }

  function storedProjectId() {
    try { return Number(localStorage.getItem(STORE_KEY)) || null; } catch { return null; }
  }

  function rememberProject(id) {
    try { id ? localStorage.setItem(STORE_KEY, String(id)) : localStorage.removeItem(STORE_KEY); } catch { /* storage unavailable */ }
  }

  function resolveProject() {
    const project = appProject();
    if (project) { CL.projectId = project.id; CL.projectName = project.name; }
    else if (!CL.projectId) { CL.projectId = storedProjectId(); CL.projectName = CL.projectId ? `Site project #${CL.projectId}` : null; }
    else if (CL.projectName === null) { CL.projectName = `Site project #${CL.projectId}`; }
  }

  function renderProjectLine() {
    const node = $id("cl-project-line");
    if (!node) return;
    node.innerHTML = CL.projectId
      ? `<span>Project: <strong>${esc(CL.projectName)}</strong> (#${esc(CL.projectId)})</span>`
      : `<span>No project selected. Saving a measurement or site model will create a project named &ldquo;Site: &lt;model name&gt;&rdquo;.</span>`;
  }

  async function ensureProject() {
    resolveProject();
    if (CL.projectId) return CL.projectId;
    const name = ($id("cl-name").value || "").trim() || "Untitled site";
    const project = await api("/api/projects", post({
      name: `Site: ${name}`, jurisdiction: $id("cl-jurisdiction").value,
      purpose: "Contaminated land conceptual site model",
    }));
    CL.projectId = project.id; CL.projectName = project.name;
    rememberProject(project.id);
    renderProjectLine();
    return project.id;
  }

  async function refreshLists() {
    resolveProject();
    renderProjectLine();
    if (!CL.projectId) { CL.measurements = []; CL.saved = []; CL.activeId = null; renderMeasurements(); renderSaved(); updateSaveUi(); return; }
    // Two refreshes can overlap (the section scrolling into view, a save finishing). Only the latest call may
    // apply its result, otherwise an older response arriving late would overwrite newer data.
    const seq = ++CL.refreshSeq;
    try {
      const [measurements, saved] = await Promise.all([
        api(`/api/projects/${CL.projectId}/metal-measurements`),
        api(`/api/projects/${CL.projectId}/site-models`),
      ]);
      if (seq !== CL.refreshSeq) return;
      CL.measurements = measurements; CL.saved = saved;
    } catch (error) {
      if (seq !== CL.refreshSeq) return;
      if (error.status === 404) { CL.projectId = null; CL.projectName = null; rememberProject(null); renderProjectLine(); }
      else setStatus("Saved data could not be loaded for this project.", `${error.message} Scroll away and back, or reload the page, to try again.`, "error");
      CL.measurements = []; CL.saved = [];
    }
    if (CL.activeId && !CL.saved.some((m) => m.id === CL.activeId)) CL.activeId = null;
    if (CL.editingMeasurement && !CL.measurements.some((m) => m.id === CL.editingMeasurement.id)) resetMeasurementForm();
    renderMeasurements(); renderSaved(); updateSaveUi();
  }

  function updateSaveUi() {
    const active = CL.saved.find((m) => m.id === CL.activeId);
    $id("cl-save").textContent = active ? "Update saved model" : "Save site model";
    $id("cl-save-new").hidden = !active;
    const note = $id("cl-editing");
    note.hidden = !active;
    note.textContent = active ? `Editing saved model “${active.name}”. Update replaces it (the previous version is kept in the audit trail); Save as new copy keeps it and adds another.` : "";
  }

  /* ---------- builder state ---------- */
  function blankSource() {
    const groups = CL.ref.contaminant_groups;
    return { kind: CL.ref.source_kinds[0], media: ["soil"], contaminants: [blankContaminant()] };
  }

  function buildModel() {
    return {
      sources: CL.sources.map((s, i) => ({
        id: `S${i + 1}`, kind: s.kind, release_media: s.media,
        contaminants: s.contaminants.filter((c) => c.name.trim()).map((c) => {
          const properties = propertiesPayload(c);
          return {
            name: c.name.trim(), contaminant_group: c.group, ...(c.cas.trim() ? { cas_number: c.cas.trim() } : {}),
            ...(Object.keys(properties).length ? { properties } : {}),
          };
        }),
      })),
      receptors: [...CL.receptors],
      links: CL.links.map((l) => ({ pathway: l.pathway, from: l.from, to: l.to })),
      measured: CL.extraMeasured,
    };
  }

  function loadModel(model, name, jurisdiction) {
    CL.sources = model.sources.map((s) => ({
      kind: s.kind, media: [...s.release_media],
      contaminants: s.contaminants.map((c) => ({ name: c.name, group: c.contaminant_group, cas: c.cas_number || "", props: propsFromPayload(c.properties) })),
    }));
    CL.receptors = new Set(model.receptors || []);
    CL.links = (model.links || []).map((l) => ({ pathway: l.pathway, from: l.from, to: l.to }));
    CL.extraMeasured = model.measured || {};
    $id("cl-name").value = name || "";
    if (jurisdiction && [...$id("cl-jurisdiction").options].some((o) => o.value === jurisdiction)) $id("cl-jurisdiction").value = jurisdiction;
    renderSources(); renderReceptors(); renderLinks();
  }

  /* ---------- rendering: builder ---------- */
  function renderSources() {
    const { source_kinds: kinds, media, contaminant_groups: groups } = CL.ref;
    $id("cl-sources").innerHTML = CL.sources.map((s, i) => `
      <div class="cl-source" data-i="${i}">
        <div class="cl-source-head">
          <span class="cl-source-title">S${i + 1}</span>
          <label><span>Kind</span><select data-f="kind">${kinds.map((k) => `<option value="${esc(k)}"${k === s.kind ? " selected" : ""}>${esc(label(k))}</option>`).join("")}</select></label>
          <button class="cl-icon-btn" data-act="rm-source" type="button" aria-label="Remove source S${i + 1}">✕</button>
        </div>
        <div><span class="cl-sub" style="margin:0 0 6px;display:block">Releases to</span>
          <div class="cl-chips" role="group" aria-label="Release media for S${i + 1}">${media.map((m) => `<label class="cl-chip"><input type="checkbox" data-f="media" value="${esc(m)}"${s.media.includes(m) ? " checked" : ""}>${esc(label(m))}</label>`).join("")}</div>
        </div>
        <div class="cl-stack">${s.contaminants.map((c, j) => `
          <div class="cl-contaminant" data-j="${j}">
            <label><span>Contaminant</span><input data-f="name" value="${esc(c.name)}" placeholder="e.g. lead, PCB-153" autocomplete="off"></label>
            <label><span>Group</span><select data-f="group">${groups.map((g) => `<option value="${esc(g.key)}"${g.key === c.group ? " selected" : ""}>${esc(label(g.key))} (${esc(g.letter)})</option>`).join("")}</select></label>
            <label><span>CAS (optional)</span><input data-f="cas" value="${esc(c.cas)}" placeholder="e.g. 1336-36-3" autocomplete="off"></label>
            <button class="cl-icon-btn" data-act="rm-cont" type="button" aria-label="Remove contaminant">✕</button>
            <details class="cl-props"${PROP_KEYS.some((k) => String(c.props[k] ?? "").trim()) ? " open" : ""}>
              <summary>Properties for plausibility checks (optional)</summary>
              <p class="cl-hint">Enter only values you have from a cited source: nothing is assumed, and units are fixed. They let the volatility, bioaccumulation and mobility screening definitions be applied as prompts for review.</p>
              <div class="cl-row3">
                <label><span>Vapour pressure (mm Hg)</span><input data-f="p:vapour_pressure_mm_hg" inputmode="decimal" value="${esc(c.props.vapour_pressure_mm_hg)}"></label>
                <label><span>Henry's law constant (atm-m3/mol)</span><input data-f="p:henry_law_constant_atm_m3_mol" inputmode="decimal" value="${esc(c.props.henry_law_constant_atm_m3_mol)}"></label>
                <label><span>BCF/BAF, aquatic (L/kg)</span><input data-f="p:bcf_or_baf_aquatic" inputmode="decimal" value="${esc(c.props.bcf_or_baf_aquatic)}"></label>
              </div>
              <div class="cl-row3">
                <label><span>log Kow</span><input data-f="p:log_kow" inputmode="decimal" value="${esc(c.props.log_kow)}"></label>
                <label><span>log Koc (Koc in L/kg)</span><input data-f="p:log_koc" inputmode="decimal" value="${esc(c.props.log_koc)}"></label>
              </div>
              <label><span>Source of these values (required if any are entered)</span><input data-f="p:source" value="${esc(c.props.source)}" placeholder="e.g. supplier datasheet rev 3" autocomplete="off"></label>
            </details>
          </div>`).join("")}</div>
        <button class="ghost-button" data-act="add-cont" type="button">+ Add contaminant</button>
      </div>`).join("") || `<p class="cl-empty">No sources yet.</p>`;
  }

  function renderReceptors() {
    $id("cl-receptors").innerHTML = CL.ref.receptors.map((r) =>
      `<label class="cl-chip"><input type="checkbox" value="${esc(r)}"${CL.receptors.has(r) ? " checked" : ""}>${esc(label(r))}</label>`).join("");
  }

  function fillLinkSelects(keepPathway) {
    const pathways = CL.ref.pathways;
    const pSel = $id("cl-link-pathway");
    if (!keepPathway) pSel.innerHTML = Object.keys(pathways).map((p) => `<option value="${esc(p)}">${esc(label(p))}</option>`).join("");
    const rule = pathways[pSel.value];
    $id("cl-link-from").innerHTML = rule.from.map((n) => `<option value="${esc(n)}">${esc(label(n))}</option>`).join("");
    $id("cl-link-to").innerHTML = rule.to.map((n) => `<option value="${esc(n)}">${esc(label(n))}</option>`).join("");
  }

  function renderLinks() {
    $id("cl-links").innerHTML = CL.links.map((l, i) =>
      `<li><span>${esc(label(l.from))} <strong>→</strong> ${esc(label(l.to))} <small>(${esc(label(l.pathway))})</small></span>
       <button class="cl-icon-btn" data-i="${i}" type="button" aria-label="Remove pathway ${esc(label(l.pathway))}">✕</button></li>`).join("")
      || `<li><small>No pathways yet. Add at least one to connect a source to a receptor.</small></li>`;
  }

  /* ---------- rendering: measurements and saved models ---------- */
  function renderMeasurementForm() {
    const ref = CL.ref;
    $id("cl-m-element").innerHTML = Object.entries(ref.metal_elements).map(([sym, name]) => `<option value="${esc(sym)}">${esc(sym)} · ${esc(name)}</option>`).join("");
    $id("cl-m-medium").innerHTML = ref.measurement.media.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("");
    $id("cl-m-basis").innerHTML = ref.measurement.bases.map((b) => `<option value="${esc(b)}"${b === "total" ? " selected" : ""}>${esc(label(b))}</option>`).join("");
    $id("cl-m-origin").innerHTML = ref.measurement.origins.map((o) => `<option value="${esc(o)}">${esc(o)}</option>`).join("");
    $id("cl-m-site").innerHTML = `<option value="">not set (will not link)</option>` + ref.media.map((m) => `<option value="${esc(m)}">${esc(label(m))}</option>`).join("");
    syncMeasurementUnits();
  }

  function syncMeasurementUnits() {
    const water = $id("cl-m-medium").value === "water";
    const units = water ? CL.ref.measurement.water_units : CL.ref.measurement.solid_units;
    $id("cl-m-unit").innerHTML = units.map((u) => `<option value="${esc(u)}">${esc(u)}</option>`).join("");
    $id("cl-m-weight-wrap").hidden = water;
  }

  function renderMeasurements() {
    const node = $id("cl-measurements");
    if (!node) return;
    node.innerHTML = CL.measurements.map((m) => `
      <div class="cl-measurement${CL.editingMeasurement && CL.editingMeasurement.id === m.id ? " editing" : ""}">
        <span><strong>${esc(m.element)}</strong> ${esc(m.value)} ${esc(m.unit)}${m.weight_basis ? ` ${esc(m.weight_basis)} weight` : ""} · ${esc(label(m.basis))} · ${esc(m.medium)}
          <small>${esc(m.source)} · ${m.site_medium ? `represents ${esc(label(m.site_medium))}` : "site medium not set (will not link)"}</small></span>
        <span class="cl-measurement-actions">
          <button class="cl-icon-btn cl-edit-btn" data-edit="${esc(m.id)}" type="button" aria-label="Edit measurement">Edit</button>
          <button class="cl-icon-btn" data-id="${esc(m.id)}" type="button" aria-label="Delete measurement">✕</button>
        </span>
      </div>`).join("") || `<p class="cl-empty">No measurements saved for this project.</p>`;
  }

  function renderSaved() {
    const select = $id("cl-saved");
    select.innerHTML = CL.saved.length
      ? CL.saved.map((m) => `<option value="${esc(m.id)}">${esc(m.name)} · ${esc(m.jurisdiction)}</option>`).join("")
      : `<option value="">none saved</option>`;
    $id("cl-open").disabled = $id("cl-delete").disabled = !CL.saved.length;
  }

  /* ---------- rendering: results ---------- */
  function renderDiagram(svg) {
    if (CL.blobUrl) URL.revokeObjectURL(CL.blobUrl);
    CL.blobUrl = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    $id("cl-diagram").innerHTML =
      `<img alt="Conceptual site model diagram: sources, environmental media and receptors joined by pathways" src="${CL.blobUrl}">`;
    let link = $id("cl-diagram-download");
    if (!link) {
      link = document.createElement("a");
      link.id = "cl-diagram-download"; link.className = "cl-note"; link.style.display = "inline-block";
      $id("cl-diagram").after(link);
    }
    link.href = CL.blobUrl; link.download = "conceptual-site-model.svg"; link.textContent = "Download diagram (SVG)";
  }

  function badge(kind, text) { return `<span class="cl-badge ${kind}">${esc(text)}</span>`; }

  function popBadge(status) {
    if (status === "POPS_REGULATORY_STATUS_DETECTED") return badge("pop", "POPs status detected");
    if (status === "IDENTITY_CONFLICT") return badge("gap", "identity conflict");
    return "";
  }

  const PLAUS = {
    SUPPORTS_RELEVANCE: ["ok", "supported"], QUESTIONS_RELEVANCE: ["gap", "review: questioned"],
    INCONCLUSIVE: ["ext", "inconclusive"], PROPERTY_MISSING: ["mute", "property missing"],
  };

  function plausibilityBadges(items) {
    if (!items || !items.length) return "";
    return `<div class="cl-plaus">${items.map((r) => {
      const [kind, text] = PLAUS[r.outcome] || ["mute", r.outcome];
      return `${badge(kind, text)} <small>${esc(r.rule)} · ${esc(label(r.pathway))}</small>`;
    }).join(" ")}</div>`;
  }

  function quoteHtml(q) {
    const where = q.page ? `PDF page ${q.page}` : (q.locator || "");
    const parts = [q.document, where, q.section ? `section ${q.section}` : ""].filter(Boolean).join("; ");
    const link = q.url && /^https?:\/\//.test(q.url)
      ? ` <a href="${esc(q.url)}" target="_blank" rel="noopener noreferrer">source</a>` : "";
    return `<blockquote>${esc(q.text)} <small>(${esc(parts)})</small>${link}</blockquote>`;
  }

  function safeUrl(url) { return /^https?:\/\//.test(url) ? url : "#"; }

  function plausibilityNotes(result) {
    const seen = new Map();
    for (const l of result.linkages) {
      for (const r of l.plausibility || []) {
        const key = `${l.contaminant}|${r.rule}|${r.outcome}`;
        if (!seen.has(key)) seen.set(key, { contaminant: l.contaminant, ...r });
      }
    }
    const items = [...seen.values()];
    const out = [];
    const missing = items.filter((r) => r.outcome === "PROPERTY_MISSING");
    const others = items.filter((r) => r.outcome !== "PROPERTY_MISSING");
    if (others.length) {
      const questioned = others.some((r) => r.outcome === "QUESTIONS_RELEVANCE");
      out.push(`<div class="cl-note${questioned ? " warn" : ""}"><strong>Plausibility prompts.</strong> Published screening definitions applied to the properties you supplied, as prompts for review only. A linkage is never removed.<ul>${others.map((r) => {
        const [kind, text] = PLAUS[r.outcome];
        return `<li><strong>${esc(r.contaminant)}</strong> · ${esc(label(r.pathway))} · ${badge(kind, text)} ${esc(r.message)}${r.basis.length ? ` <small>Basis: ${esc(r.basis.join("; "))}.</small>` : ""} <small>Rule ${esc(r.rule)}: ${esc(r.source)}. ${r.in_regime ? "In this jurisdiction" : "Not formal in this jurisdiction"}: ${esc(r.regime_note)}.</small></li>`;
      }).join("")}</ul></div>`);
    }
    if (missing.length) {
      const byContaminant = new Map();
      for (const r of missing) byContaminant.set(r.contaminant, [...(byContaminant.get(r.contaminant) || []), r]);
      out.push(`<div class="cl-note"><strong>Properties needed to apply the screening definitions</strong> (nothing is assumed):<ul>${[...byContaminant].map(([name, rs]) => `<li><strong>${esc(name)}</strong>: ${esc(rs.map((r) => `${r.rule} (${label(r.pathway)})`).join(", "))}. ${esc(rs[0].message)}</li>`).join("")}</ul></div>`);
    }
    const meta = result.plausibility_rules;
    if (meta) {
      out.push(`<details class="cl-rules"><summary>Rules used, their sources, and what is not encoded</summary>
        ${Object.entries(meta.rules).map(([id, rule]) => `<h5>${esc(id)} · ${esc(rule.title)}</h5>
          <div>${esc(rule.criterion)}. Applies to: ${esc(rule.applies_to)}.</div>
          <div><a href="${esc(safeUrl(rule.url))}" target="_blank" rel="noopener noreferrer">${esc(rule.source)}</a> (retrieved ${esc(rule.retrieved)})</div>
          ${rule.quotes.map(quoteHtml).join("")}
          <div><strong>Position by jurisdiction:</strong></div>
          <ul>${Object.entries(rule.regimes || {}).map(([k, v]) => `<li>${esc(k === "*" ? "All jurisdictions" : k)}: ${esc(v)}</li>`).join("")}</ul>
          <div><strong>Limits:</strong></div>
          <ul>${rule.caveats.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>`).join("")}
        <h5>Not encoded</h5><ul>${meta.not_encoded.map((g) => `<li>${esc(g)}</li>`).join("")}</ul>
      </details>`);
    }
    return out.join("");
  }

  function renderAssessment(result) {
    const s = result.summary;
    const groupLabel = Object.fromEntries(CL.ref.contaminant_groups.map((g) => [g.key, g.label]));
    const rows = result.linkages.map((l) => {
      const steps = l.path.map((p) => ` → <em>${esc(label(p.pathway))}</em> → ${esc(label(p.to))}`).join("");
      const data = l.status === "POTENTIAL_LINKAGE_DATA_PRESENT";
      const external = /EXTERNAL MODEL REQUIRED/.test(l.native_assessment) ? badge("ext", "external model required") : "";
      return `<tr>
        <td>${esc(l.source_id)}<br><small>${esc(label(l.source_kind))}</small></td>
        <td><strong>${esc(l.contaminant)}</strong> ${popBadge(l.pops_status)}<br><small>${esc(groupLabel[l.contaminant_group] || label(l.contaminant_group))} (${esc(l.taxonomy_letter)})</small></td>
        <td>${esc(label(l.release_medium))}${steps}${plausibilityBadges(l.plausibility)}</td>
        <td>${esc(label(l.receptor))}<br><small>${esc(label(l.receptor_class))}</small></td>
        <td>${data ? badge("ok", "measured data present") : badge("gap", "measurement missing")}<br>${esc(l.missing_data.join("; "))}</td>
        <td>${esc(l.external_route.route)} ${external}${l.external_route.source ? `<br><small>${esc(l.external_route.source)}</small>` : ""}</td>
      </tr>`;
    }).join("");

    const notes = [];
    if (result.receptors_without_linkage.length) {
      notes.push(`<div class="cl-note warn"><strong>Receptors with no linkage identified.</strong> This is not a finding of no risk: the model or the site investigation may be incomplete.<ul>${result.receptors_without_linkage.map((r) => `<li>${esc(label(r.receptor))}</li>`).join("")}</ul></div>`);
    }
    if (result.sources_without_linkage.length) {
      notes.push(`<div class="cl-note warn"><strong>Sources not connected to any receptor:</strong> ${esc(result.sources_without_linkage.join(", "))}</div>`);
    }
    if (result.unsupported_pathway_links.length) {
      notes.push(`<div class="cl-note warn"><strong>Pathways not connected to a source and receptor:</strong><ul>${result.unsupported_pathway_links.map((u) => `<li>${esc(label(u.pathway))}: ${esc(label(u.from))} → ${esc(label(u.to))}</li>`).join("")}</ul></div>`);
    }
    const link = result.measurement_linkage;
    if (link) {
      const unlinked = link.unlinked_measurements;
      if (link.linked_measurements.length || unlinked.length) {
        notes.push(`<div class="cl-note"><strong>Saved measurements:</strong> ${esc(link.linked_measurements.length)} linked to the model.${unlinked.length ? `<ul>${unlinked.map((u) => `<li>Measurement #${esc(u.measurement_id)} (${esc(u.element)}) not linked: ${esc(u.reason)}</li>`).join("")}</ul>` : ""}</div>`);
      }
    }
    const flags = result.contaminant_pops_flags || [];
    const detected = flags.filter((f) => f.status === "POPS_REGULATORY_STATUS_DETECTED");
    const conflicts = flags.filter((f) => f.status === "IDENTITY_CONFLICT");
    if (detected.length) {
      notes.push(`<div class="cl-note warn"><strong>POPs regulatory status detected</strong> (Stockholm Convention and EU Regulation 2019/1021 seed list; ${esc(detected[0].reference_retrieved || "")}).<ul>${detected.map((f) => {
        const m = f.matches[0];
        const eu = m.eu_pops_regulation_2019_1021;
        return `<li><strong>${esc(f.contaminant)}</strong> matches ${esc(m.name)} on ${esc(f.match_basis)}. Stockholm Convention Annex ${esc(m.stockholm_convention.annexes.join(", ") || "n/a")}; EU: ${esc(eu.annex || "listing not confirmed")} (${esc(label(eu.status))}). ${esc(f.confidence_note || "")}</li>`;
      }).join("")}</ul></div>`);
    }
    if (conflicts.length) {
      notes.push(`<div class="cl-note warn"><strong>POPs identity conflict:</strong><ul>${conflicts.map((f) => `<li>${esc(f.contaminant)}: ${esc(f.reason)}</li>`).join("")}</ul></div>`);
    }
    const undetermined = flags.filter((f) => f.status === "NOT_DETERMINED").length;
    if (undetermined) {
      notes.push(`<div class="cl-note">${esc(undetermined)} contaminant(s) not determined against the POPs seed list. The list is non-exhaustive and covers only the Stockholm Convention and EU: not being listed is not evidence that a substance is not a POP.</div>`);
    }

    $id("cl-assessment").innerHTML = `
      <div class="cl-summary">
        <div class="cl-stat"><strong>${esc(s.potential_linkages)}</strong><span>potential linkages</span></div>
        <div class="cl-stat"><strong>${esc(s.with_measured_data)}</strong><span>with measured data</span></div>
        <div class="cl-stat"><strong>${esc(s.measurement_gaps)}</strong><span>measurement gaps</span></div>
        <div class="cl-stat"><strong>${esc(s.receptors_without_linkage)}</strong><span>receptors, no linkage</span></div>
      </div>
      ${rows ? `<div class="cl-table-wrap"><table class="cl-table"><thead><tr><th>Source</th><th>Contaminant</th><th>Route</th><th>Receptor</th><th>Data</th><th>External assessment route (${esc(result.jurisdiction)})</th></tr></thead><tbody>${rows}</tbody></table></div>`
              : `<p class="cl-empty">No source-to-receptor linkage was found. Add pathways that connect the release media to receptors.</p>`}
      ${notes.join("")}
      ${plausibilityNotes(result)}
      <p class="cl-disclaimer">${esc(result.disclaimer)}</p>`;
  }

  /* ---------- actions ---------- */
  async function analyse() {
    const jurisdiction = $id("cl-jurisdiction").value;
    setStatus("Analysing…", "");
    try {
      const model = { ...buildModel(), jurisdiction };
      resolveProject();
      let result, svg;
      if (CL.projectId) {
        try {
          result = await api(`/api/projects/${CL.projectId}/site-models/analyse`, post(model));
        } catch (error) {
          if (error.status !== 404) throw error;
          CL.projectId = null; rememberProject(null); renderProjectLine();
        }
        if (result) svg = result.diagram_svg;
      }
      if (!result) {
        result = await api("/api/conceptual-site-model/assess", post(model));
        const response = await fetch("/api/conceptual-site-model/diagram", post(model));
        if (!response.ok) throw new Error(`Diagram request failed: ${response.status}`);
        svg = await response.text();
      }
      renderDiagram(svg);
      renderAssessment(result);
      setStatus("Analysis complete.", `${result.summary.potential_linkages} potential linkage(s), ${result.summary.measurement_gaps} with a measurement gap. Structure only: no risk is calculated.`);
    } catch (error) {
      setStatus("The model could not be analysed.", error.message, "error");
    }
  }

  async function saveModel(asNew = false) {
    const name = $id("cl-name").value.trim();
    if (!name) { setStatus("Give the site model a name before saving.", "", "error"); $id("cl-name").focus(); return; }
    try {
      const body = { ...buildModel(), name, jurisdiction: $id("cl-jurisdiction").value };
      const projectId = await ensureProject();
      let saved, verb;
      if (CL.activeId && !asNew) {
        saved = await api(`/api/projects/${projectId}/site-models/${CL.activeId}`, { ...post(body), method: "PUT" });
        verb = "updated";
      } else {
        saved = await api(`/api/projects/${projectId}/site-models`, post(body));
        CL.activeId = saved.id;
        verb = "saved";
      }
      await refreshLists();
      $id("cl-saved").value = String(saved.id);
      setStatus(`Site model ${verb}.`, `“${saved.name}” is stored in ${CL.projectName}.`);
      toast(`Site model ${verb}.`);
    } catch (error) {
      setStatus("The site model was not saved.", error.message, "error");
    }
  }

  function newModel() {
    CL.activeId = null;
    CL.sources = [blankSource()]; CL.receptors = new Set(); CL.links = []; CL.extraMeasured = {};
    $id("cl-name").value = "";
    renderSources(); renderReceptors(); renderLinks(); updateSaveUi();
    setStatus("New site model.", "The saved models are unchanged.");
  }

  async function openModel() {
    const id = $id("cl-saved").value;
    if (!id || !CL.projectId) { setStatus("Choose a saved site model to open.", CL.projectId ? "" : "No project is selected, so there are no saved models to open.", "error"); return; }
    try {
      const row = await api(`/api/projects/${CL.projectId}/site-models/${id}`);
      loadModel(row.model, row.name, row.jurisdiction);
      CL.activeId = row.id;
      updateSaveUi();
      setStatus("Site model opened for editing.", "Change it and choose Update saved model, or Save as new copy. Analyse refreshes the diagram with the current measurements of the project.");
    } catch (error) {
      setStatus("Could not open the site model.", error.message, "error");
    }
  }

  async function deleteModel() {
    const id = $id("cl-saved").value;
    if (!id || !CL.projectId) { setStatus("Choose a saved site model to delete.", "", "error"); return; }
    const name = CL.saved.find((m) => String(m.id) === String(id))?.name || "this site model";
    if (!window.confirm(`Delete the saved site model “${name}”? Measurements are kept.`)) return;
    try {
      await api(`/api/projects/${CL.projectId}/site-models/${id}`, { method: "DELETE" });
      if (String(CL.activeId) === String(id)) CL.activeId = null;
      await refreshLists();
      setStatus("Saved site model deleted.", "");
    } catch (error) {
      setStatus("Could not delete the site model.", error.message, "error");
    }
  }

  async function saveMeasurement() {
    const value = $id("cl-m-value").value;
    const source = $id("cl-m-source").value.trim();
    if (value === "" || Number.isNaN(Number(value))) { setStatus("Enter the measured concentration.", "", "error"); $id("cl-m-value").focus(); return; }
    if (!source) { setStatus("Every measurement needs a source.", "Cite the lab report, sample or dataset.", "error"); $id("cl-m-source").focus(); return; }
    const water = $id("cl-m-medium").value === "water";
    const body = {
      element: $id("cl-m-element").value, value: Number(value), unit: $id("cl-m-unit").value,
      basis: $id("cl-m-basis").value, medium: $id("cl-m-medium").value, source,
      origin: $id("cl-m-origin").value, ...(water ? {} : { weight_basis: $id("cl-m-weight").value }),
      ...($id("cl-m-method").value.trim() ? { method: $id("cl-m-method").value.trim() } : {}),
      ...($id("cl-m-site").value ? { site_medium: $id("cl-m-site").value } : {}),
    };
    try {
      const projectId = await ensureProject();
      if (CL.editingMeasurement) {
        // keep provenance fields this form does not show (species, date, assumptions, ...)
        const kept = {};
        for (const key of ["oxidation_state", "species", "date", "jurisdiction", "confidence", "applicability"]) {
          if (CL.editingMeasurement[key] != null) kept[key] = CL.editingMeasurement[key];
        }
        if ((CL.editingMeasurement.assumptions || []).length) kept.assumptions = CL.editingMeasurement.assumptions;
        await api(`/api/projects/${projectId}/metal-measurements/${CL.editingMeasurement.id}`, { ...post({ ...kept, ...body }), method: "PUT" });
        resetMeasurementForm();
        await refreshLists();
        setStatus("Measurement updated.", "The previous values are kept in the audit trail. Choose Analyse to refresh the linkages.");
      } else {
        await api(`/api/projects/${projectId}/metal-measurements`, post(body));
        $id("cl-m-value").value = "";
        await refreshLists();
        setStatus("Measurement saved.", "Choose Analyse to see it clear the matching data gap.");
      }
    } catch (error) {
      setStatus("The measurement was not saved.", error.message, "error");
    }
  }

  function resetMeasurementForm() {
    CL.editingMeasurement = null;
    $id("cl-add-measurement").textContent = "Save measurement";
    $id("cl-m-cancel").hidden = true;
    $id("cl-m-value").value = ""; $id("cl-m-source").value = ""; $id("cl-m-method").value = "";
    renderMeasurements();
  }

  function startEditMeasurement(id) {
    const m = CL.measurements.find((x) => String(x.id) === String(id));
    if (!m) return;
    CL.editingMeasurement = m;
    $id("cl-m-element").value = m.element;
    $id("cl-m-value").value = m.value;
    $id("cl-m-medium").value = m.medium;
    syncMeasurementUnits();
    $id("cl-m-unit").value = m.unit;
    $id("cl-m-basis").value = m.basis;
    if (m.weight_basis) $id("cl-m-weight").value = m.weight_basis;
    $id("cl-m-site").value = m.site_medium || "";
    $id("cl-m-origin").value = m.origin;
    $id("cl-m-method").value = m.method || "";
    $id("cl-m-source").value = m.source;
    $id("cl-add-measurement").textContent = "Update measurement";
    $id("cl-m-cancel").hidden = false;
    renderMeasurements();
    setStatus(`Editing measurement #${m.id}.`, "Change the values and choose Update measurement. The previous values are kept in the audit trail.");
    $id("cl-m-value").focus();
  }

  async function deleteMeasurement(id) {
    try {
      await api(`/api/projects/${CL.projectId}/metal-measurements/${id}`, { method: "DELETE" });
      if (CL.editingMeasurement && String(CL.editingMeasurement.id) === String(id)) resetMeasurementForm();
      await refreshLists();
    } catch (error) {
      setStatus("Could not delete the measurement.", error.message, "error");
    }
  }

  async function loadExample() {
    try {
      const example = await api("/api/conceptual-site-model/example");
      loadModel(example, "Fictional example site", example.jurisdiction);
      CL.activeId = null; updateSaveUi();
      setStatus("Fictional example loaded.", "Entirely invented, for demonstration. Choose Analyse.");
    } catch (error) {
      setStatus("Could not load the example.", error.message, "error");
    }
  }

  /* ---------- wiring ---------- */
  function wire() {
    const sources = $id("cl-sources");
    sources.addEventListener("input", (event) => {
      const field = event.target.dataset.f; if (!field) return;
      const i = Number(event.target.closest(".cl-source").dataset.i);
      const j = event.target.closest(".cl-contaminant")?.dataset.j;
      if (j !== undefined && (field === "name" || field === "cas")) CL.sources[i].contaminants[Number(j)][field] = event.target.value;
      else if (j !== undefined && field.startsWith("p:")) CL.sources[i].contaminants[Number(j)].props[field.slice(2)] = event.target.value;
    });
    sources.addEventListener("change", (event) => {
      const field = event.target.dataset.f; if (!field) return;
      const i = Number(event.target.closest(".cl-source").dataset.i);
      const j = event.target.closest(".cl-contaminant")?.dataset.j;
      if (field === "kind") CL.sources[i].kind = event.target.value;
      else if (field === "group" && j !== undefined) CL.sources[i].contaminants[Number(j)].group = event.target.value;
      else if (field === "media") {
        const media = new Set(CL.sources[i].media);
        event.target.checked ? media.add(event.target.value) : media.delete(event.target.value);
        CL.sources[i].media = CL.ref.media.filter((m) => media.has(m));
      }
    });
    sources.addEventListener("click", (event) => {
      const button = event.target.closest("[data-act]"); if (!button) return;
      const i = Number(button.closest(".cl-source").dataset.i);
      if (button.dataset.act === "rm-source") CL.sources.splice(i, 1);
      else if (button.dataset.act === "add-cont") CL.sources[i].contaminants.push(blankContaminant());
      else if (button.dataset.act === "rm-cont") {
        const j = Number(button.closest(".cl-contaminant").dataset.j);
        CL.sources[i].contaminants.splice(j, 1);
        if (!CL.sources[i].contaminants.length) CL.sources[i].contaminants.push(blankContaminant());
      }
      renderSources();
    });
    $id("cl-add-source").addEventListener("click", () => { CL.sources.push(blankSource()); renderSources(); });

    $id("cl-receptors").addEventListener("change", (event) => {
      event.target.checked ? CL.receptors.add(event.target.value) : CL.receptors.delete(event.target.value);
    });

    $id("cl-link-pathway").addEventListener("change", () => fillLinkSelects(true));
    $id("cl-add-link").addEventListener("click", () => {
      const link = { pathway: $id("cl-link-pathway").value, from: $id("cl-link-from").value, to: $id("cl-link-to").value };
      if (CL.links.some((l) => l.pathway === link.pathway && l.from === link.from && l.to === link.to)) {
        setStatus("That pathway is already in the model.", "", "error"); return;
      }
      CL.links.push(link); renderLinks();
    });
    $id("cl-links").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-i]"); if (!button) return;
      CL.links.splice(Number(button.dataset.i), 1); renderLinks();
    });

    $id("cl-m-medium").addEventListener("change", syncMeasurementUnits);
    $id("cl-add-measurement").addEventListener("click", saveMeasurement);
    $id("cl-measurements").addEventListener("click", (event) => {
      const edit = event.target.closest("button[data-edit]");
      if (edit) { startEditMeasurement(edit.dataset.edit); return; }
      const del = event.target.closest("button[data-id]"); if (del) deleteMeasurement(del.dataset.id);
    });
    $id("cl-m-cancel").addEventListener("click", () => { resetMeasurementForm(); setStatus("Measurement edit cancelled.", ""); });

    $id("cl-fit").addEventListener("click", (event) => {
      const actual = $id("cl-diagram").classList.toggle("actual");
      event.currentTarget.setAttribute("aria-pressed", String(actual));
      event.currentTarget.textContent = actual ? "Fit to width" : "Actual size";
    });
    $id("cl-analyse").addEventListener("click", analyse);
    $id("cl-save").addEventListener("click", () => saveModel(false));
    $id("cl-save-new").addEventListener("click", () => saveModel(true));
    $id("cl-new").addEventListener("click", newModel);
    $id("cl-open").addEventListener("click", openModel);
    $id("cl-delete").addEventListener("click", deleteModel);
    $id("cl-load-example").addEventListener("click", loadExample);

    if ("IntersectionObserver" in window) {
      new IntersectionObserver((entries) => { if (entries.some((e) => e.isIntersecting)) refreshLists(); }, { threshold: 0.05 })
        .observe($id("contaminated-land"));
    }
  }

  async function init() {
    if (!$id("contaminated-land")) return;
    try {
      [CL.ref, CL.frameworks] = await Promise.all([api("/api/conceptual-site-model/reference"), api("/api/frameworks")]);
    } catch (error) {
      setStatus("The contaminated-land screen could not load its reference data.", error.message, "error");
      return;
    }
    const frameworks = CL.frameworks;
    $id("cl-jurisdiction").innerHTML = frameworks.map((f) => `<option value="${esc(f.key)}">${esc(f.name)} (${esc(f.key)})</option>`).join("");
    const preferred = typeof state !== "undefined" && state && state.modelSystem;
    if (preferred && frameworks.some((f) => f.key === preferred)) $id("cl-jurisdiction").value = preferred;
    CL.sources = [blankSource()];
    renderSources(); renderReceptors(); fillLinkSelects(false); renderLinks(); renderMeasurementForm();
    wire();
    resolveProject(); renderProjectLine(); renderMeasurements(); renderSaved();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
