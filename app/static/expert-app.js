let state = {projects:[], chemicals:[], project:null, chemical:null, projectChemicalIds:new Set(), profile:null, evidence:[], selection:null, emissionRuns:[], activityRuns:[], latestEmission:null, frameworks:[], groups:[], scenarios:[], models:[], contracts:{}, externalIntegrations:[], modelWorkflows:[], selectedWorkflow:null, orchestrationManifest:null, semanticContracts:null, orchestratedAssessments:[], orchestrationPreview:null};
const el = id => document.getElementById(id);
const fmt = (v,d=4) => v === null || v === undefined ? "—" : Number(v).toPrecision(d);

function showToast(message, kind="info", timeout=6000){
  const stack=el("toast-stack");
  if(!stack)return;
  const node=document.createElement("div");
  node.className=`expert-toast ${kind}`;
  node.setAttribute("role",kind==="error"?"alert":"status");
  node.innerHTML=`<span>${kind==="error"?"!":"✓"}</span><div>${escapeHtml(message)}</div><button aria-label="Dismiss notification" type="button">×</button>`;
  node.querySelector("button").onclick=()=>node.remove();
  stack.appendChild(node);
  window.setTimeout(()=>node.remove(),timeout);
}

window.addEventListener("unhandledrejection",event=>{
  event.preventDefault();
  showToast(event.reason?.message||"The operation could not be completed.","error");
});

function page(name){
  document.querySelectorAll(".page").forEach(x=>x.classList.remove("active"));
  document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));
  el(`page-${name}`).classList.add("active");
  document.querySelector(`[data-page="${name}"]`).classList.add("active");
  el("title").textContent = {project:"Dashboard",planner:"Assessment Planner",orchestration:"Tier Orchestration",evidence:"Evidence",selection:"Selection",sorption:"Sorption / Koc",emission:"Emission & Metabolism",wwtp:"Activity SimpleTreat & Risk",irrigation:"Irrigation EU ↔ US",models:"Model Library",homeapp:"Home App",labsafety:"Lab Safety",reach:"REACH Review Bundle",audit:"Audit Trail"}[name];
  if(name==="audit") loadAudit();
  if(name==="models") loadModelWorkflows();
  if(name==="reach") loadReachWorkspace().catch(error=>showToast(error.message,"error"));
  if(name==="orchestration") loadOrchestratedAssessments().catch(error=>showToast(error.message,"error"));
}
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>page(b.dataset.page));

async function api(url, opts={}){
  const r = await fetch(url, opts);
  const data = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

async function init(){
  [state.projects, state.chemicals, state.frameworks, state.groups, state.scenarios, state.models, state.contracts, state.externalIntegrations, state.orchestrationManifest, state.semanticContracts] = await Promise.all([
    api("/api/projects"), api("/api/chemicals"), api("/api/frameworks"),
    api("/api/contaminant-groups"), api("/api/scenarios"), api("/api/model-registry"), api("/api/model-adapter-contracts"), api("/api/external-model-integrations"), api("/api/orchestration/manifest"), api("/api/orchestration/model-contracts")
  ]);
  initialisePlanner();
  initialiseOrchestration();
  initialiseModelWorkflow();
  renderModelLibrary();
  renderExternalIntegrations();
  renderProjects();
  if(state.projects.length) selectProject(state.projects[0]);
}

function renderProjects(){
  el("project-list").innerHTML = state.projects.map(p=>`
    <button class="${state.project?.id===p.id?"active":""}" onclick="selectProjectById(${p.id})">
      <span><strong>${p.name}</strong><br><small>${p.jurisdiction}</small></span><span>›</span>
    </button>`).join("");
}
window.selectProjectById = id => selectProject(state.projects.find(p=>p.id===id));

async function selectProject(p){
  state.project = p;
  setHomeProfileBinding(false);
  renderProjects();
  el("project-empty").classList.add("hidden");
  el("project-details").classList.remove("hidden");
  el("active-project-name").textContent = p.name;
  const pcs = await api(`/api/projects/${p.id}/chemicals`);
  state.projectChemicalIds = new Set(pcs.map(c=>c.id));
  state.chemical = state.chemicals.find(c=>c.id===pcs[0]?.id) || state.chemicals[0];
  renderChemicalSelector();
  renderChemical(state.projectChemicalIds.has(state.chemical.id));
  await loadAssessmentProfileIntoExpert();
  if(state.projectChemicalIds.has(state.chemical.id)) await loadEvidence();
  else el("evidence-table").innerHTML='<div class="empty">Add the selected chemical to this project before reviewing evidence.</div>';
  renderChemical(state.projectChemicalIds.has(state.chemical.id));
  updateHomeProfileBinding();
  await loadEmissionRuns();
  await loadActivityRuns();
  await loadModelWorkflows();
  await loadOrchestratedAssessments();
}

function renderChemicalSelector(){
  const select=el("project-chemical-select");
  select.innerHTML=state.chemicals.map(c=>`<option value="${c.id}" ${c.id===state.chemical?.id?'selected':''}>${escapeHtml(c.preferred_name)}${state.projectChemicalIds.has(c.id)?'':' · not in project'}</option>`).join("");
}

el("project-chemical-select").onchange=async()=>{
  setHomeProfileBinding(false);
  state.chemical=state.chemicals.find(c=>c.id===Number(el("project-chemical-select").value));
  state.evidence=[];
  renderOrchestrationEvidenceOptions();
  renderChemical(state.projectChemicalIds.has(state.chemical.id));
  await loadAssessmentProfileIntoExpert();
  if(state.projectChemicalIds.has(state.chemical.id)) await loadEvidence();
  else el("evidence-table").innerHTML='<div class="empty">Add the selected chemical to this project before reviewing evidence.</div>';
  renderChemical(state.projectChemicalIds.has(state.chemical.id));
  updateHomeProfileBinding();
  await loadOrchestratedAssessments();
};

async function loadAssessmentProfileIntoExpert(){
  state.profile=null;
  if(!state.project||!state.chemical||!state.projectChemicalIds.has(state.chemical.id))return;
  state.profile=await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/assessment-profile`);
  const benchmark=state.profile.profile_origin==="protected_carbamazepine_benchmark";
  el("w-model-mode").value=benchmark?"supplied_workbook_9box_preset":"custom_screening";
  el("custom-wwtp-fields").classList.toggle("hidden",benchmark);
  if(!benchmark){
    [["w-bio","wwtp_biodegradation_fraction"],["w-primary","wwtp_primary_sludge_fraction"],["w-secondary","wwtp_secondary_sludge_fraction"],["w-vol","wwtp_volatilisation_fraction"]].forEach(([id,key])=>{el(id).value=state.profile[key]??"";});
  }
  if(el("ir-solubility"))el("ir-solubility").value=state.profile.water_solubility_mg_l??"";
  if(el("ir-dt50"))el("ir-dt50").value=state.profile.soil_dt50_days??"";
}

function renderChemical(inProject){
  const c = state.chemical;
  const profile=state.profile;
  const identityConfirmed=Boolean(c.identity_snapshot);
  const profileReviewed=Boolean(profile&&profile.review_status==="reviewed"&&profile.reviewer_confirmation);
  const structureSrc=c.cas_number==="298-46-4"?"/static/carbamazepine.svg":"/static/chemical-placeholder.svg";
  const metric=(field,label,unit)=>{
    const value=profile?.[field];
    return `<div class="profile-metric"><small>${label}</small><strong>${value==null?"Not set":`${fmt(value)} ${unit}`}</strong><button type="button" class="why-button" data-profile-field="${field}">Why this number?</button></div>`;
  };
  el("chemical-card").innerHTML = `
    <div class="chemical chemical-profile-head"><div class="structure"><img src="${structureSrc}" alt="Structure preview for ${escapeHtml(c.preferred_name)}"></div><div><small>${escapeHtml(c.review_status)}</small><h2>${escapeHtml(c.preferred_name)}</h2><p>${escapeHtml(c.cas_number||"No CAS")} · ${escapeHtml(c.molecular_formula||"Formula unavailable")}</p><div class="identity-chips"><span class="${identityConfirmed?"ready":"pending"}">${identityConfirmed?"Confirmed identity":"Identity review required"}</span><span class="${profileReviewed?"ready":"pending"}">${profileReviewed?"Reviewed profile":"Draft profile"}</span></div></div></div>
    <div class="readiness-ladder" aria-label="Assessment readiness">
      <button type="button" data-go-page="project" class="${identityConfirmed?"ready":"pending"}"><span>1</span><strong>Identity</strong><small>${identityConfirmed?"Confirmed snapshot":"Confirm before modelling"}</small></button>
      <button type="button" data-go-page="project" class="${profileReviewed?"ready":"pending"}"><span>2</span><strong>Profile</strong><small>${profileReviewed?"Reviewed and bound":"Review properties"}</small></button>
      <button type="button" data-go-page="evidence" class="${state.evidence.length?"ready":"pending"}"><span>3</span><strong>Evidence</strong><small>${state.evidence.length?`${state.evidence.length} stored record(s)`:"No stored records"}</small></button>
    </div>
    <div class="profile-metrics">
      ${metric("log_kow","log Kow","")}
      ${metric("soil_dt50_days","Soil DT50","days")}
      ${metric("water_solubility_mg_l","Water solubility","mg/L")}
    </div>
    <div class="facts">
      <div><small>Molecular weight</small><strong>${escapeHtml(c.molecular_weight_g_mol)} g/mol</strong></div>
      <div><small>Substance form</small><strong>${escapeHtml(c.substance_form || "parent")}</strong></div>
      <div><small>Project status</small><strong>${inProject?"Added":"Not added"}</strong></div>
    </div>`;
  el("chemical-card").querySelectorAll("[data-go-page]").forEach(button=>button.onclick=()=>page(button.dataset.goPage));
  el("chemical-card").querySelectorAll("[data-profile-field]").forEach(button=>button.onclick=()=>openProfileProvenance(button.dataset.profileField));
  el("add-chemical").textContent = inProject ? `${c.preferred_name} added` : `Add ${c.preferred_name} to project`;
  el("add-chemical").disabled = inProject;
}

el("project-form").onsubmit = async e=>{
  e.preventDefault();
  const p = await api("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    name:el("project-name").value,jurisdiction:el("project-jurisdiction").value,purpose:"Environmental fate and risk screening"
  })});
  state.projects = await api("/api/projects");
  selectProject(state.projects.find(x=>x.id===p.id));
};

el("add-chemical").onclick = async ()=>{
  await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}`,{method:"POST"});
  state.projectChemicalIds.add(state.chemical.id);
  renderChemicalSelector();
  renderChemical(true);
  await loadAssessmentProfileIntoExpert();
  await loadEvidence();
};

async function loadEvidence(){
  if(!state.project||!state.chemical) return;
  const rows = await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/evidence`);
  state.evidence=rows;
  const endpointFilter=el("evidence-endpoint-filter");
  const previous=endpointFilter.value;
  const endpoints=[...new Set(rows.map(row=>row.property_code))].sort();
  endpointFilter.innerHTML=`<option value="">All endpoints</option>${endpoints.map(code=>`<option value="${escapeHtml(code)}">${escapeHtml(code)}</option>`).join("")}`;
  if(endpoints.includes(previous))endpointFilter.value=previous;
  renderEvidenceTable();
  renderOrchestrationEvidenceOptions();
  renderChemical(state.projectChemicalIds.has(state.chemical.id));
}

function renderOrchestrationEvidenceOptions(){
  const select=el("orch-benchmark-evidence");
  if(!select)return;
  const previous=select.value;
  const supported=new Set(["ECOTOX.AQUATIC.LC50","ECOTOX.AQUATIC.EC50","ECOTOX.AQUATIC.NOEC","ECOTOX.AQUATIC.EC10"]);
  const rows=state.evidence.filter(row=>supported.has(row.property_code));
  select.innerHTML=`<option value="">No evidence bound — exploratory only</option>${rows.map(row=>`<option value="${row.id}">#${row.id} · ${escapeHtml(row.property_code)} · ${row.original_value} ${escapeHtml(row.original_unit)} · ${escapeHtml(row.source.title)}</option>`).join("")}`;
  if(rows.some(row=>String(row.id)===previous))select.value=previous;
}

function renderEvidenceTable(){
  const query=(el("evidence-filter").value||"").trim().toLowerCase();
  const endpoint=el("evidence-endpoint-filter").value;
  const rows=state.evidence.filter(row=>{
    if(endpoint&&row.property_code!==endpoint)return false;
    if(!query)return true;
    return [row.property_code,row.evidence_type,row.source.title,row.source.identifier,row.source.organisation,row.representative_group_key,row.soil_type,row.notes,row.test_guideline]
      .some(value=>String(value||"").toLowerCase().includes(query));
  });
  el("evidence-filter-count").textContent=`Showing ${rows.length} of ${state.evidence.length} record(s)`;
  el("evidence-table").innerHTML = rows.length ? `
    <table><thead><tr><th>ID</th><th>Endpoint</th><th>Source</th><th>Group</th><th>Matrix</th><th>Reported value</th><th>Reliability</th><th>Provenance</th></tr></thead>
    <tbody>${rows.map(r=>`<tr><td>${r.id}</td><td><strong>${escapeHtml(r.property_code)}</strong><br><small>${escapeHtml(r.evidence_type||"evidence")}</small></td><td><strong>${escapeHtml(r.source.title)}</strong><br><small>${escapeHtml(r.source.identifier||"No identifier")}</small></td><td>${escapeHtml(r.representative_group_key)}</td><td>${escapeHtml(r.soil_type||"—")}</td><td>${r.original_value} ${escapeHtml(r.original_unit)}</td><td>${r.reliability_score??"—"}</td><td><button class="table-action" type="button" data-evidence-id="${r.id}">Inspect</button></td></tr>`).join("")}</tbody></table>`
    : `<div class="empty">${state.evidence.length?"No evidence matches these filters.":"No evidence records yet."}</div>`;
  el("evidence-table").querySelectorAll("[data-evidence-id]").forEach(button=>button.onclick=()=>openEvidenceProvenance(Number(button.dataset.evidenceId)));
}

el("evidence-filter").oninput=renderEvidenceTable;
el("evidence-endpoint-filter").onchange=renderEvidenceTable;

function openProvenanceDialog(title,body){
  el("provenance-title").textContent=title;
  el("provenance-dialog-body").innerHTML=body;
  const dialog=el("provenance-dialog");
  if(typeof dialog.showModal==="function")dialog.showModal();
  else dialog.setAttribute("open","");
}

function openEvidenceProvenance(id){
  const record=state.evidence.find(row=>row.id===id);
  if(!record)return;
  const sourceUrl=safeExternalUrl(record.source.url);
  openProvenanceDialog(`Evidence #${record.id} · ${record.property_code}`,`
    <dl class="provenance-list">
      <div><dt>Reported result</dt><dd>${record.original_value} ${escapeHtml(record.original_unit)}</dd></div>
      <div><dt>Endpoint context</dt><dd>${escapeHtml(record.endpoint_kind||"Not recorded")} · ${escapeHtml(record.test_guideline||"No guideline recorded")}</dd></div>
      <div><dt>Source</dt><dd>${escapeHtml(record.source.title)}${record.source.identifier?` · ${escapeHtml(record.source.identifier)}`:""}${sourceUrl?` · <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer">Open source</a>`:""}</dd></div>
      <div><dt>Organisation / year</dt><dd>${escapeHtml(record.source.organisation||"Not recorded")} · ${escapeHtml(record.source.publication_year||"Not recorded")}</dd></div>
      <div><dt>Representativeness group</dt><dd>${escapeHtml(record.representative_group_key)}</dd></div>
      <div><dt>Reliability</dt><dd>${record.reliability_score??"Not scored"}</dd></div>
      <div><dt>Notes</dt><dd>${escapeHtml(record.notes||"No notes recorded")}</dd></div>
      <div><dt>Canonical record hash</dt><dd><code>${escapeHtml(record.provenance_hash)}</code></dd></div>
    </dl><div class="warning">This hash identifies the returned source-and-endpoint snapshot. It does not prove that the underlying study is correct or suitable.</div>`);
}

function openProfileProvenance(field){
  const labels={log_kow:["log Kow",""],soil_dt50_days:["Soil DT50","days"],water_solubility_mg_l:["Water solubility","mg/L"]};
  const [label,unit]=labels[field];
  const value=state.profile?.[field];
  const profile=state.profile;
  openProvenanceDialog(label,`
    <dl class="provenance-list">
      <div><dt>Selected value</dt><dd>${value==null?"Not set":`${fmt(value)} ${unit}`}</dd></div>
      <div><dt>Profile status</dt><dd>${escapeHtml(profile?.review_status||"No project profile")}${profile?.reviewer_confirmation?" · reviewer confirmed":""}</dd></div>
      <div><dt>Profile origin</dt><dd>${escapeHtml(profile?.profile_origin||"Not available")}</dd></div>
      <div><dt>Source summary</dt><dd>${escapeHtml(profile?.source_summary||"No source summary supplied")}</dd></div>
      <div><dt>Updated</dt><dd>${escapeHtml(profile?.updated_at||"Not available")}</dd></div>
    </dl><div class="warning">Profile-level provenance does not replace endpoint-level evidence review. Inspect the Evidence workspace before regulatory use.</div>`);
}

el("add-demo").onclick = async ()=>{
  requireProject();
  const r=await api(`/api/evidence/demo/${state.project.id}/${state.chemical.id}`,{method:"POST"});
  showToast(r.message||`Created ${r.created} records`,"success");
  loadEvidence();
};

el("evidence-form").onsubmit = async e=>{
  e.preventDefault(); requireProject();
  await api("/api/evidence",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    project_id:state.project.id,chemical_id:state.chemical.id,
    source:{title:el("source-title").value,identifier:el("source-identifier").value||null,organisation:el("source-organisation").value||null,publication_year:el("source-year").value?Number(el("source-year").value):null},
    original_value:Number(el("ev-value").value),representative_group_key:el("ev-group").value,
    soil_type:el("ev-soil").value||null,soil_texture:el("ev-soil").value||null,
    temperature_c:Number(el("ev-temp").value),reliability_score:Number(el("ev-rel").value),
    test_guideline:el("ev-guideline").value||null,kinetic_model:el("ev-kinetic").value||null
  })});
  e.target.reset(); el("ev-guideline").value="OECD 307"; el("ev-kinetic").value="SFO";
  await loadEvidence();
  await loadEmissionRuns();
};

el("selection-form").onsubmit = async e=>{
  e.preventDefault(); requireProject();
  const r=await api("/api/selections/calculate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    project_id:state.project.id,chemical_id:state.chemical.id,target_temperature_c:Number(el("sel-temp").value),
    activation_energy_kj_mol:Number(el("sel-ea").value),max_reliability_score:Number(el("sel-rel").value)
  })});
  state.selection=r; renderSelection(r);
};

function renderSelection(r){
  const box=el("selection-result"); box.classList.remove("hidden");
  if(r.selected_value_days==null){box.innerHTML=`<h3>No selected value</h3><p>${r.reason}</p>`;return}
  const s=r.statistics;
  box.innerHTML=`
    <div class="selection-hero"><div><small>SELECTED MODELLING VALUE</small><strong>${fmt(r.selected_value_days)} days</strong><span>${r.reason}</span></div><div>GM</div></div>
    <div class="stats">
      <div class="stat"><small>Independent groups</small><strong>${s.n_independent_groups}</strong></div>
      <div class="stat"><small>Minimum</small><strong>${fmt(s.minimum_days)} d</strong></div>
      <div class="stat"><small>Median</small><strong>${fmt(s.median_days)} d</strong></div>
      <div class="stat"><small>Maximum</small><strong>${fmt(s.maximum_days)} d</strong></div>
    </div>
    <div class="table-wrap"><table><thead><tr><th>Evidence</th><th>Decision</th><th>Reason</th><th>Normalised</th><th>Group representative</th></tr></thead>
    <tbody>${r.members.map(m=>`<tr><td>${m.evidence_id}</td><td>${m.decision}</td><td>${m.reason}</td><td>${fmt(m.normalised_value_days)} d</td><td>${fmt(m.representative_value_days)} d</td></tr>`).join("")}</tbody></table></div>
    <label>Lock rationale</label><input id="lock-rationale" value="Representative multi-soil geometric mean under pilot ruleset.">
    <button id="lock-button">Lock selected value</button><div id="lock-output"></div>`;
  el("lock-button").onclick=lockSelection;
}

async function lockSelection(){
  const r=await api("/api/selections/lock",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    selection_set_id:state.selection.selection_set_id,rationale:el("lock-rationale").value
  })});
  el("lock-output").innerHTML=`<h3>Locked</h3><div class="hash">${r.evidence_hash}</div>`;
}


el("sorption-form").onsubmit = async e=>{
  e.preventDefault(); requireProject();
  const maybe = id => el(id).value === "" ? null : Number(el(id).value);
  const payload = {
    project_id: state.project.id,
    chemical_id: state.chemical.id,
    scenario_name: "Ionisation-aware soil sorption screening",
    mode: el("s-mode").value,
    neutral_variant: el("s-neutral-variant").value,
    base_variant: el("s-base-variant").value,
    log_kow: Number(el("s-logkow").value),
    pkaa: maybe("s-pkaa"),
    pkab: maybe("s-pkab"),
    soil_ph: Number(el("s-ph").value),
    organic_carbon_fraction: Number(el("s-foc").value),
    ionic_strength_mol_l: Number(el("s-ionic").value),
    molecular_formula: el("s-formula").value||null,
    cec_total_mol_c_kg: maybe("s-cec"),
    electrolyte_system: el("s-electrolyte").value,
    mcgowan_volume_vx: maybe("s-vx"),
    ring_count: Number(el("s-rings").value||0),
    bond_count: maybe("s-bonds"),
    atom_c: maybe("s-atom-c"), atom_h: maybe("s-atom-h"), atom_n: maybe("s-atom-n"), atom_o: maybe("s-atom-o"),
    atom_cl: maybe("s-atom-cl"), atom_f: maybe("s-atom-f"), atom_s: maybe("s-atom-s"), atom_i: maybe("s-atom-i"), atom_b: maybe("s-atom-b"),
    n_h_attached_to_cationic_n: Number(el("s-nai").value||0),
    oh_groups: Number(el("s-oh").value||0), nh2_groups: Number(el("s-nh2").value||0),
    ether_groups: Number(el("s-ether").value||0), ester_groups: Number(el("s-ester").value||0),
    ketone_groups: Number(el("s-ketone").value||0), amide_groups: Number(el("s-amide").value||0),
    single_ring_charged_pyridines: Number(el("s-pyridine").value||0), chloro_groups: Number(el("s-chloro").value||0),
    carboxamide_groups: Number(el("s-carboxamide").value||0), multi_ring_charged_n: Number(el("s-multiring-n").value||0)
  };
  const r = await api("/api/model-runs/sorption", {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)
  });
  renderSorption(r.outputs);
};

function methodCard(m, selected=false){
  const warns = (m.warnings||[]).map(x=>`<li>${x}</li>`).join("");
  const dg = m.cation_sorption ? `<div class="stats"><div class="stat"><small>Kd organic matter</small><strong>${fmt(m.cation_sorption.organic_matter_kd_contribution_l_kg)} L/kg</strong></div><div class="stat"><small>Kd clay CEC</small><strong>${fmt(m.cation_sorption.clay_kd_contribution_l_kg)} L/kg</strong></div><div class="stat"><small>Clay share</small><strong>${(m.cation_sorption.clay_fraction_of_total_kd*100).toFixed(2)}%</strong></div><div class="stat"><small>McGowan Vx</small><strong>${fmt(m.cation_sorption.mcgowan_volume_vx)}</strong></div></div>` : "";
  return `<div class="sorption-method ${selected?"selected-method":""}">
    <div class="method-top"><div><small>${selected?"SELECTED METHOD":"COMPARISON"}</small><h3>${m.model_name}</h3></div><span>${m.model_key}</span></div>
    <div class="stats">
      <div class="stat"><small>Koc</small><strong>${fmt(m.koc_l_kg)} L/kg</strong></div>
      <div class="stat"><small>Kd</small><strong>${fmt(m.kd_l_kg)} L/kg</strong></div>
      <div class="stat"><small>log Koc</small><strong>${fmt(m.log_koc)}</strong></div>
      <div class="stat"><small>log Kd</small><strong>${fmt(m.log_kd)}</strong></div>
    </div>
    ${dg}
    <details><summary>Equation trace</summary><ol>${m.formula_trace.map(x=>`<li>${x}</li>`).join("")}</ol></details>
    ${warns?`<div class="warning"><strong>Method warnings</strong><ul>${warns}</ul></div>`:""}
  </div>`;
}

function renderSorption(o){
  const box=el("sorption-result"); box.classList.remove("hidden");
  box.innerHTML=`
    <div class="selection-hero"><div><small>${o.selected.model_key.includes("DROGE_GOSS")?"SELECTED CATION Kd":"SELECTED APPARENT Koc"}</small><strong>${fmt(o.selected.model_key.includes("DROGE_GOSS")?o.selected.kd_l_kg:o.selected.koc_l_kg)} L/kg</strong>
    <span>${o.ionisation_class.toUpperCase()} · Koc compatibility ${fmt(o.selected.koc_l_kg)} L/kg · Kd ${fmt(o.selected.kd_l_kg)} L/kg</span></div><div>${o.selected.model_key.includes("DROGE_GOSS")?"Kd":"Koc"}</div></div>
    <div class="dependency-map"><h3>Workbook dependency map</h3><ul>${o.workbook_dependency_map.map(x=>`<li>${x}</li>`).join("")}</ul></div>
    ${methodCard(o.selected,true)}
    ${o.comparisons.map(x=>methodCard(x,false)).join("")}
    <details><summary>Global scientific warnings</summary><ul>${o.global_warnings.map(x=>`<li>${x}</li>`).join("")}</ul></details>`;
}


let metaboliteCounter = 0;

function addMetaboliteRow(values={}){
  metaboliteCounter += 1;
  const row=document.createElement("div");
  row.className="metabolite-row";
  row.dataset.index=metaboliteCounter;
  row.innerHTML=`
    <div><label>Metabolite name</label><input class="m-name" value="${values.name||""}" placeholder="e.g. carbamazepine-10,11-epoxide"></div>
    <div><label>Molecular weight (g/mol)</label><input class="m-mw" type="number" step="any" value="${values.mw||""}"></div>
    <div><label>Molar fraction of systemic parent</label><input class="m-fraction" type="number" step="0.01" value="${values.fraction||""}"></div>
    <div><label>Evidence type</label><select class="m-evidence"><option value="measured">Measured</option><option value="modelled">Modelled</option><option value="estimated">Estimated</option><option value="read_across">Read-across</option></select></div>
    <div><label>Source title</label><input class="m-source" value="${values.source||""}"></div>
    <div><label>Source identifier</label><input class="m-id" value="${values.identifier||""}"></div>
    <button type="button" class="remove-metabolite secondary">Remove</button>`;
  row.querySelector(".remove-metabolite").onclick=()=>row.remove();
  el("metabolite-rows").appendChild(row);
}

el("add-metabolite").onclick=()=>addMetaboliteRow();

el("e-mode").onchange=()=>{
  const screening=el("e-mode").value==="screening_spc";
  document.querySelectorAll(".screening-field").forEach(x=>x.classList.toggle("hidden",!screening));
  document.querySelectorAll(".refined-field").forEach(x=>x.classList.toggle("hidden",screening));
};

function emissionMetabolites(){
  return [...document.querySelectorAll(".metabolite-row")].filter(row=>row.querySelector(".m-name").value.trim()).map((row,i)=>({
    species_key:`metabolite-${i+1}`,
    name:row.querySelector(".m-name").value.trim(),
    molecular_weight_g_mol:Number(row.querySelector(".m-mw").value),
    molar_fraction:Number(row.querySelector(".m-fraction").value),
    evidence_type:row.querySelector(".m-evidence").value,
    source_title:row.querySelector(".m-source").value||null,
    source_identifier:row.querySelector(".m-id").value||null
  }));
}

el("emission-form").onsubmit=async e=>{
  e.preventDefault(); requireProject();
  const payload={
    project_id:state.project.id, chemical_id:state.chemical.id,
    scenario_name:`${state.chemical.preferred_name} pharmaceutical emission and metabolism`,
    emission_mode:el("e-mode").value,
    parent_name:state.chemical.preferred_name,
    parent_molecular_weight_g_mol:state.chemical.molecular_weight_g_mol,
    product_name:el("e-product").value||null,
    formulation:el("e-formulation").value,
    administration_route:el("e-route").value,
    spc_title:el("e-spc-title").value||null,
    spc_identifier:el("e-spc-id").value||null,
    spc_url:el("e-spc-url").value||null,
    spc_access_date:el("e-spc-date").value||null,
    spc_source_type:el("e-spc-type").value,
    consumption_source_title:el("e-consumption-title").value||null,
    consumption_source_identifier:el("e-consumption-id").value||null,
    therapeutic_class_ddd_per_1000_day:Number(el("e-ddd").value),
    dose_per_administration:Number(el("e-dose").value),
    dose_unit:el("e-dose-unit").value,
    administrations_per_day:Number(el("e-admins").value),
    refined_annual_active_kg:el("e-mode").value==="refined_annual_use"?Number(el("e-annual-active").value):null,
    emitting_days_per_year:Number(el("e-days").value),
    population:Number(el("e-population").value),
    wastewater_l_person_day:Number(el("e-water").value),
    direct_to_sewer_fraction:Number(el("e-direct").value),
    systemic_fraction:Number(el("e-systemic").value),
    parent_urine_fraction:Number(el("e-parent-urine").value),
    parent_faeces_fraction:Number(el("e-parent-faeces").value),
    metabolites:emissionMetabolites()
  };
  const r=await api("/api/model-runs/emission",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  state.latestEmission={model_run_id:r.model_run_id,outputs:r.outputs,scenario_name:payload.scenario_name};
  renderEmission(r);
  await loadEmissionRuns();
};

function renderEmission(r){
  const o=r.outputs, box=el("emission-result"); box.classList.remove("hidden");
  const rows=o.species.map(x=>`<tr><td><strong>${x.name}</strong><br><small>${x.species_type}</small></td><td>${fmt(x.moles_day)} mol/day</td><td>${fmt(x.mass_g_day)} g/day</td><td>${fmt(x.influent_concentration_ug_l)} µg/L</td><td>${x.evidence_type}</td></tr>`).join("");
  box.innerHTML=`
    <div class="selection-hero"><div><small>PARENT WWTP INFLUENT</small><strong>${fmt(o.species[0].influent_concentration_ug_l)} µg/L</strong><span>${fmt(o.species[0].mass_g_day)} g/day entering ${fmt(o.wastewater_flow_m3_day)} m³/day</span></div><div>PECin</div></div>
    <div class="stats">
      <div class="stat"><small>Administered mass</small><strong>${fmt(o.administered.mass_g_day)} g/day</strong></div>
      <div class="stat"><small>Population</small><strong>${o.population}</strong></div>
      <div class="stat"><small>Flow</small><strong>${fmt(o.wastewater_flow_m3_day)} m³/day</strong></div>
      <div class="stat"><small>Recovered parent equivalents</small><strong>${(o.recovered_parent_equivalent_fraction*100).toFixed(2)}%</strong></div>
    </div>
    <div class="table-wrap"><table><thead><tr><th>Species</th><th>Moles/day</th><th>Mass/day</th><th>Influent</th><th>Evidence</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${o.warnings.length?`<div class="warning"><strong>Scientific warnings</strong><ul>${o.warnings.map(x=>`<li>${x}</li>`).join("")}</ul></div>`:""}
    <details><summary>Assumptions and calculation order</summary><ol>${o.assumptions.map(x=>`<li>${x}</li>`).join("")}</ol></details>
    <button id="open-wwtp-from-emission">Continue to Activity SimpleTreat</button>`;
  el("open-wwtp-from-emission").onclick=()=>page("wwtp");
}

async function loadEmissionRuns(){
  if(!state.project) return;
  state.emissionRuns=await api(`/api/projects/${state.project.id}/emission-runs`);
  if(state.emissionRuns.length) state.latestEmission=state.emissionRuns[0];
  const select=el("w-emission-run");
  if(!select) return;
  select.innerHTML=state.emissionRuns.length?state.emissionRuns.map(r=>`<option value="${r.model_run_id}">Run ${r.model_run_id} · ${r.scenario_name}</option>`).join(""):`<option value="">Create an emission run first</option>`;
  loadSpeciesForSelectedEmission();
}

function selectedEmissionRun(){
  const id=Number(el("w-emission-run").value);
  return state.emissionRuns.find(x=>x.model_run_id===id);
}

function loadSpeciesForSelectedEmission(){
  const run=selectedEmissionRun();
  el("w-species").innerHTML=run?run.outputs.species.map(x=>`<option value="${x.species_key}">${x.name} · ${fmt(x.influent_concentration_ug_l)} µg/L</option>`).join(""):`<option value="">No species</option>`;
}
el("w-emission-run").onchange=loadSpeciesForSelectedEmission;

el("w-model-mode").onchange=()=>{
  el("custom-wwtp-fields").classList.toggle("hidden",el("w-model-mode").value!=="custom_screening");
};

el("wwtp-form").onsubmit=async e=>{
  e.preventDefault(); requireProject();
  if(!el("w-emission-run").value) throw new Error("Create an Emission & Metabolism run first");
  if(el("w-model-mode").value==="custom_screening"&&state.profile?.review_status!=="reviewed") throw new Error("Save a reviewed chemical-specific calculation profile in the guided workspace before running custom WWTP fractions");
  if(el("w-model-mode").value==="custom_screening"&&["w-bio","w-primary","w-secondary","w-vol"].some(id=>el(id).value==="")) throw new Error("All four reviewed custom WWTP fractions are required");
  const val=id=>el(id).value;
  const payload={
    project_id:state.project.id, chemical_id:state.chemical.id,
    assessment_profile_id:state.profile?.id||null,
    emission_model_run_id:Number(val("w-emission-run")), species_key:val("w-species"),
    scenario_name:"Activity SimpleTreat and receiving-water screening",
    model_mode:val("w-model-mode"),
    biodegradation_fraction:Number(val("w-bio")),
    primary_sludge_fraction:Number(val("w-primary")),
    secondary_sludge_fraction:Number(val("w-secondary")),
    volatilisation_fraction:Number(val("w-vol")),
    post_wwtp_biodegradation_fraction:Number(val("w-post-bio")),
    receiving_water_dilution_factor:Number(val("w-dil")),
    sludge_to_soil_fraction:Number(val("w-sludge")), mixed_soil_mass_kg:Number(val("w-soil-mass")),
    aquatic_pnec_ug_l:val("w-aq-pnec")?Number(val("w-aq-pnec")):null,
    soil_pnec_ug_kg:val("w-soil-pnec")?Number(val("w-soil-pnec")):null
  };
  const r=await api("/api/model-runs/activity-simpletreat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  renderWWTP(r);
  await loadActivityRuns();
};

function renderWWTP(r){
  const o=r.outputs, box=el("wwtp-result"); box.classList.remove("hidden");
  const pathways=Object.entries(o.pathway_fractions).map(([k,v])=>`<tr><td>${k.replaceAll("_"," ")}</td><td>${(v*100).toFixed(6)}%</td><td>${fmt(o.mass_flows_kg_day[k])} kg/day</td></tr>`).join("");
  box.innerHTML=`
    <div class="selection-hero"><div><small>SURFACE-WATER PEC</small><strong>${fmt(o.surface_water_pec_ug_l)} µg/L</strong><span>${o.species_name} · ${o.model_label}</span></div><div>WWTP</div></div>
    <div class="stats">
      <div class="stat"><small>Influent</small><strong>${fmt(o.influent_concentration_ug_l)} µg/L</strong></div>
      <div class="stat"><small>Effluent</small><strong>${fmt(o.effluent_concentration_ug_l)} µg/L</strong></div>
      <div class="stat"><small>Soil PEC</small><strong>${fmt(o.soil_pec_ug_kg)} µg/kg</strong></div>
      <div class="stat"><small>Mass closure</small><strong>${(o.mass_balance_closure_fraction*100).toFixed(6)}%</strong></div>
    </div>
    <div class="table-wrap"><table><thead><tr><th>Pathway</th><th>Fraction</th><th>Mass flow</th></tr></thead><tbody>${pathways}</tbody></table></div>
    <div class="risk-badges"><div class="risk">Aquatic RQ: ${fmt(o.aquatic_rq)} · ${o.aquatic_risk_band}</div><div class="risk">Soil RQ: ${fmt(o.soil_rq)} · ${o.soil_risk_band}</div></div>
    <h3>Conclusion</h3><p>${r.conclusion}</p>
    ${r.limitations.length?`<div class="warning"><strong>Model limitations</strong><ul>${r.limitations.map(x=>`<li>${x}</li>`).join("")}</ul></div>`:""}
    <details><summary>Assumptions</summary><ul>${r.assumptions.map(a=>`<li>${a}</li>`).join("")}</ul></details>`;
}


async function loadActivityRuns(){
  if(!state.project) return;
  state.activityRuns=await api(`/api/projects/${state.project.id}/activity-simpletreat-runs`);
  const select=el("ir-activity-run");
  if(!select) return;
  select.innerHTML=state.activityRuns.length?state.activityRuns.map(r=>`<option value="${r.model_run_id}">Run ${r.model_run_id} · ${r.scenario_name} · ${fmt(r.outputs.effluent_concentration_ug_l)} µg/L</option>`).join(""):`<option value="">Run Activity SimpleTreat first</option>`;
}

el("ir-source").onchange=()=>{
  const linked=el("ir-source").value==="linked";
  document.querySelectorAll(".ir-linked").forEach(x=>x.classList.toggle("hidden",!linked));
  document.querySelectorAll(".ir-direct").forEach(x=>x.classList.toggle("hidden",linked));
};

el("irrigation-form").onsubmit=async e=>{
  e.preventDefault(); requireProject();
  const optional=id=>el(id).value===""?null:Number(el(id).value);
  const linked=el("ir-source").value==="linked";
  const payload={
    project_id:state.project.id, chemical_id:state.chemical.id,
    activity_simpletreat_model_run_id:linked?Number(el("ir-activity-run").value):null,
    effluent_concentration_ug_l:linked?null:Number(el("ir-effluent").value),
    scenario_name:`${state.chemical.preferred_name} EU–US wastewater irrigation comparison`,
    chemical_name:state.chemical.preferred_name, cas_number:state.chemical.cas_number, smiles:state.chemical.smiles,
    irrigation_rate_l_m2_day:Number(el("ir-rate").value), irrigated_area_m2:Number(el("ir-area").value),
    total_irrigation_flow_l_day:optional("ir-flow"), soil_depth_m:Number(el("ir-depth").value),
    bulk_density_kg_m3:Number(el("ir-density").value), kd_l_kg:Number(el("ir-kd").value),
    organic_carbon_fraction:optional("ir-foc"), soil_dt50_days:optional("ir-dt50"), degradation_rate_per_day:null,
    duration_years:Number(el("ir-years").value), receiving_water_dilution_factor:Number(el("ir-dilution").value),
    aquatic_pnec_ug_l:optional("ir-pnec"), crop:el("ir-crop").value,
    water_solubility_mg_l:optional("ir-solubility"), vapour_pressure_pa:optional("ir-vp")
  };
  if(linked&&!payload.activity_simpletreat_model_run_id) throw new Error("Select an Activity SimpleTreat run or use a direct effluent concentration");
  const r=await api("/api/model-runs/wastewater-irrigation-comparison",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  renderIrrigation(r);
  await loadModelWorkflows();
};

function renderIrrigation(r){
  const o=r.outputs, n=o.native_screen, box=el("irrigation-result"); box.classList.remove("hidden");
  const workflowRows=[...r.workflow_ids.EU.map(id=>({region:"EU",id})),...r.workflow_ids.US.map(id=>({region:"US",id}))];
  box.innerHTML=`
    <div class="selection-hero"><div><small>SOIL CONCENTRATION AT ${o.shared_inputs.duration_years} YEAR(S)</small><strong>${fmt(n.soil_concentration_at_duration_ug_kg)} µg/kg</strong><span>Effluent ${fmt(n.effluent_concentration_ug_l)} µg/L · ${fmt(n.application_mass_kg_ha_year)} kg/ha/year</span></div><div>EU↔US</div></div>
    <div class="stats"><div class="stat"><small>Annual soil input</small><strong>${fmt(n.annual_input_mg_kg_soil)} mg/kg/y</strong></div><div class="stat"><small>Plateau with degradation</small><strong>${fmt(n.soil_plateau_with_degradation_mg_kg)} mg/kg</strong></div><div class="stat"><small>Plateau without degradation</small><strong>${fmt(n.soil_plateau_without_degradation_mg_kg)} mg/kg</strong></div><div class="stat"><small>Surface water screen</small><strong>${fmt(n.surface_water_screen_ug_l)} µg/L</strong></div></div>
    <div class="grid two framework-compare"><div><h3>European Union toolchain</h3><ol>${o.frameworks.EU.toolchain.map(x=>`<li>${x}</li>`).join("")}</ol><p><strong>Comparison endpoints:</strong> ${o.frameworks.EU.primary_comparison_outputs.join(", ")}</p></div><div><h3>United States toolchain</h3><ol>${o.frameworks.US.toolchain.map(x=>`<li>${x}</li>`).join("")}</ol><p><strong>Comparison endpoints:</strong> ${o.frameworks.US.primary_comparison_outputs.join(", ")}</p></div></div>
    <h3>Framework differences</h3><div class="table-wrap"><table><thead><tr><th>Topic</th><th>EU</th><th>US</th></tr></thead><tbody>${o.framework_differences.map(x=>`<tr><td><strong>${x.topic}</strong></td><td>${x.EU}</td><td>${x.US}</td></tr>`).join("")}</tbody></table></div>
    <h3>Prepared external-model workflows</h3><div class="table-wrap"><table><thead><tr><th>Region</th><th>Workflow</th></tr></thead><tbody>${workflowRows.map(x=>`<tr><td>${x.region}</td><td><button class="secondary" onclick="page('models');selectModelWorkflow(${x.id})">Open workflow #${x.id}</button></td></tr>`).join("")}</tbody></table></div>
    <div class="warning"><strong>Workbook corrections and scientific boundaries</strong><ul>${[...o.source_workbook_checks,...o.warnings].map(x=>`<li>${x}</li>`).join("")}</ul></div>`;
}

async function loadReachWorkspace(){
  const capabilities=await api("/api/reach/review-bundles/capabilities");
  const signing=capabilities.signing;
  el("reach-capabilities").className="";
  el("reach-capabilities").innerHTML=`
    <div class="stats"><div class="stat"><small>Format</small><strong>${escapeHtml(capabilities.format_version)}</strong></div><div class="stat"><small>Boundary</small><strong>Review only</strong></div></div>
    <p><strong>RSA-PSS:</strong> ${signing.cryptography_available?"dependency available":"dependency unavailable"} · ${signing.private_key_configured?"private key configured":"no private key configured"}</p>
    <div class="warning">Signing never falls back silently. If RSA is selected and unavailable, export stops.</div>`;
  const rsaOption=el("reach-signing").querySelector('option[value="rsa"]');
  rsaOption.disabled=!(signing.cryptography_available&&signing.private_key_configured);
  if(rsaOption.disabled&&el("reach-signing").value==="rsa")el("reach-signing").value="unsigned";
  if(!state.project||!state.chemical||!state.projectChemicalIds.has(state.chemical.id)){
    el("reach-readiness").className="warning";
    el("reach-readiness").textContent="Select a project and add a confirmed chemical before preparing a bundle.";
    el("reach-critical-evidence").innerHTML="";
    el("reach-evidence-list").innerHTML='<div class="empty">No project chemical selected.</div>';
    return;
  }
  state.profile=await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/assessment-profile`);
  state.evidence=await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/evidence`);
  const aquatic=state.evidence.filter(row=>["ECOTOX.AQUATIC.LC50","ECOTOX.AQUATIC.EC50","ECOTOX.AQUATIC.NOEC","ECOTOX.AQUATIC.EC10"].includes(row.property_code));
  el("reach-critical-evidence").innerHTML=aquatic.length?aquatic.map(row=>`<option value="${row.id}">#${row.id} · ${escapeHtml(row.property_code)} · ${row.original_value} ${escapeHtml(row.original_unit)}</option>`).join(""):'<option value="">No stored aquatic ecotoxicity evidence</option>';
  el("reach-evidence-list").innerHTML=state.evidence.length?state.evidence.map(row=>`<label><input class="reach-evidence-check" type="checkbox" value="${row.id}" ${aquatic.some(item=>item.id===row.id)?"checked":""}><span><strong>#${row.id} · ${escapeHtml(row.property_code)}</strong><br><small>${escapeHtml(row.source.title)} · ${row.original_value} ${escapeHtml(row.original_unit)}</small></span></label>`).join(""):'<div class="empty">No evidence records. Import and review evidence first.</div>';
  const ready=state.profile.review_status==="reviewed"&&state.profile.reviewer_confirmation&&aquatic.length>0&&Boolean(state.chemical.identity_snapshot);
  el("reach-readiness").className=ready?"reach-ready":"warning";
  el("reach-readiness").textContent=ready?`${state.chemical.preferred_name} is bound to confirmed identity, reviewed profile and ${aquatic.length} aquatic endpoint(s).`:`Not ready: confirmed identity, reviewed profile and at least one stored aquatic ecotoxicity endpoint are required.`;
  el("reach-critical-evidence").onchange=()=>{
    const selected=document.querySelector(`.reach-evidence-check[value="${el("reach-critical-evidence").value}"]`);
    if(selected)selected.checked=true;
  };
}

function reachModelRunIds(){
  const raw=el("reach-model-runs").value.trim();
  if(!raw)return [];
  const ids=[...new Set(raw.split(",").map(value=>Number(value.trim())))];
  if(ids.some(value=>!Number.isInteger(value)||value<=0))throw new Error("Model-run IDs must be positive integers separated by commas");
  return ids;
}

el("reach-bundle-form").onsubmit=async event=>{
  event.preventDefault();
  requireProject();
  if(!state.profile)throw new Error("Load a reviewed assessment profile first");
  const selectedEvidence=[...document.querySelectorAll(".reach-evidence-check:checked")].map(node=>Number(node.value));
  const criticalEvidence=Number(el("reach-critical-evidence").value);
  if(!criticalEvidence)throw new Error("Select a stored aquatic ecotoxicity endpoint");
  if(!selectedEvidence.includes(criticalEvidence))selectedEvidence.push(criticalEvidence);
  const payload={
    project_id:state.project.id,
    chemical_id:state.chemical.id,
    assessment_profile_id:state.profile.id,
    selected_evidence_ids:selectedEvidence,
    selected_model_run_ids:reachModelRunIds(),
    pnec:{
      critical_evidence_id:criticalEvidence,
      assessment_factor:Number(el("reach-af").value),
      assessment_factor_rationale:el("reach-af-rationale").value,
      guidance_reference:el("reach-guidance").value,
      target_compartment:"freshwater"
    },
    reviewer_name:el("reach-reviewer").value,
    reviewer_role:el("reach-reviewer-role").value,
    reviewer_confirmation:el("reach-confirm").checked,
    signing_mode:el("reach-signing").value
  };
  const response=await fetch("/api/reach/review-bundles",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  if(!response.ok){
    const problem=await response.json().catch(()=>({}));
    throw new Error(problem.detail||"REACH review bundle export failed");
  }
  const blob=await response.blob();
  const disposition=response.headers.get("Content-Disposition")||"";
  const filename=disposition.match(/filename="([^"]+)"/)?.[1]||"fateintel-reach-review.zip";
  const url=URL.createObjectURL(blob), link=document.createElement("a");
  link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  const manifestHash=response.headers.get("X-FateIntel-Manifest-SHA256")||response.headers.get("X-EnviroChem-Manifest-SHA256");
  const bundleHash=response.headers.get("X-FateIntel-Bundle-SHA256")||response.headers.get("X-EnviroChem-Bundle-SHA256");
  el("reach-export-result").className="reach-export-result";
  el("reach-export-result").innerHTML=`<strong>Downloaded ${escapeHtml(filename)}</strong><p>${escapeHtml(response.headers.get("X-FateIntel-Signing-Mode")||response.headers.get("X-EnviroChem-Signing-Mode")||"unknown")} · NOT IUCLID / NOT SUBMISSION-READY</p><small>Manifest SHA-256</small><code>${escapeHtml(manifestHash)}</code><small>Bundle SHA-256</small><code>${escapeHtml(bundleHash)}</code>`;
  showToast("REACH review bundle prepared and recorded in the audit trail","success");
  await loadAudit();
};

async function loadAudit(){
  if(!state.project){el("audit-list").innerHTML=`<div class="empty">Select a project.</div>`;return}
  const rows=await api(`/api/projects/${state.project.id}/audit`);
  el("audit-list").innerHTML=rows.length?rows.map(r=>`<div class="event"><strong>${r.action} · ${r.entity_type} ${r.entity_id}</strong><small>${new Date(r.created_at).toLocaleString()}</small></div>`).join(""):`<div class="empty">No events.</div>`;
}
el("refresh-audit").onclick=loadAudit;

function requireProject(){
  if(!state.project||!state.chemical) throw new Error("Select a project first");
  if(!state.projectChemicalIds.has(state.chemical.id)) throw new Error("Add the selected chemical to this project first");
}


function pretty(value){
  return String(value).replaceAll("_"," ").replace(/\b\w/g, c=>c.toUpperCase());
}

function initialisePlanner(){
  el("p-jurisdiction").innerHTML=state.frameworks.map(x=>`<option value="${x.key}">${x.name}</option>`).join("");
  el("p-group").innerHTML=state.groups.map(x=>`<option value="${x}">${pretty(x)}</option>`).join("");
  el("p-scenario").innerHTML=state.scenarios.map(x=>`<option value="${x}">${pretty(x)}</option>`).join("");
  el("p-jurisdiction").value="UK";
  el("p-group").value="human_pharmaceutical";
  el("p-scenario").value="municipal_wastewater";
}

el("planner-form").onsubmit=async e=>{
  e.preventDefault();
  const plan=await api("/api/assessment-plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    jurisdiction:el("p-jurisdiction").value,
    contaminant_group:el("p-group").value,
    scenario:el("p-scenario").value,
    tier:Number(el("p-tier").value)
  })});
  renderPlan(plan);
};

function renderPlan(plan){
  const models=plan.models.map(m=>`<div class="plan-model ${m.applicable?"":"not-applicable"}"><div><small>${m.implementation}</small><h3>${m.name}</h3><p>${m.domain}</p></div><span>${m.status}</span></div>`).join("");
  el("planner-result").innerHTML=`
    <div class="panel-head"><div><small>${plan.jurisdiction.name.toUpperCase()} · TIER ${plan.tier}</small><h3>Assessment workflow</h3></div></div>
    <p>${plan.plan_summary}</p>
    <div class="plan-stack">${models||'<div class="empty">No model is required at this tier; complete identity and evidence checks first.</div>'}</div>
    <h3>Required inputs</h3><ul>${plan.required_inputs.map(x=>`<li>${x}</li>`).join("")}</ul>
    ${plan.warnings.length?`<div class="warning"><strong>Applicability warnings</strong><ul>${plan.warnings.map(x=>`<li>${x}</li>`).join("")}</ul></div>`:""}
    <details><summary>Framework packs</summary><ul>${plan.jurisdiction.packs.map(x=>`<li>${x}</li>`).join("")}</ul></details>`;
}

function initialiseOrchestration(){
  el("orch-jurisdiction").innerHTML=state.frameworks.map(x=>`<option value="${x.key}">${escapeHtml(x.name)}</option>`).join("");
  el("orch-group").innerHTML=state.groups.map(x=>`<option value="${x}">${pretty(x)}</option>`).join("");
  el("orch-scenario").innerHTML=state.scenarios.map(x=>`<option value="${x}">${pretty(x)}</option>`).join("");
  el("orch-risk-model").innerHTML=state.models.map(x=>`<option value="${x.key}">${escapeHtml(x.name)}</option>`).join("");
  el("orch-jurisdiction").value="EU";
  el("orch-group").value="human_pharmaceutical";
  el("orch-scenario").value="municipal_wastewater";
  el("orch-risk-model").value="ENVIROCHEM_CATCHMENT_RIVER_NETWORK";
  initialiseCompatibilityInspector();
  syncOrchestrationCompartment();
}

function semanticContractRows(){
  return state.semanticContracts?.contracts||[];
}

function contractRow(modelKey){
  return semanticContractRows().find(row=>row.model_key===modelKey);
}

function initialiseCompatibilityInspector(){
  const sources=semanticContractRows().filter(row=>row.outputs.length);
  const targets=semanticContractRows().filter(row=>row.inputs.length);
  el("compat-source-model").innerHTML=sources.map(row=>`<option value="${row.model_key}">${escapeHtml(row.model_name)} · ${pretty(row.semantic_status)}</option>`).join("");
  el("compat-target-model").innerHTML=targets.map(row=>`<option value="${row.model_key}">${escapeHtml(row.model_name)} · ${pretty(row.semantic_status)}</option>`).join("");
  if(sources.some(row=>row.model_key==="ACTIVITY_SIMPLETREAT"))el("compat-source-model").value="ACTIVITY_SIMPLETREAT";
  if(targets.some(row=>row.model_key==="ENVIROCHEM_CATCHMENT_RIVER_NETWORK"))el("compat-target-model").value="ENVIROCHEM_CATCHMENT_RIVER_NETWORK";
  updateCompatibilityPorts();
}

function updateCompatibilityPorts(){
  const source=contractRow(el("compat-source-model").value);
  const target=contractRow(el("compat-target-model").value);
  el("compat-source-port").innerHTML=(source?.outputs||[]).map(port=>`<option value="${port.port_key}">${pretty(port.port_key)} · ${escapeHtml(port.unit)}</option>`).join("");
  el("compat-target-port").innerHTML=(target?.inputs||[]).map(port=>`<option value="${port.port_key}">${pretty(port.port_key)} · ${escapeHtml(port.unit)}</option>`).join("");
}

el("compat-source-model").onchange=updateCompatibilityPorts;
el("compat-target-model").onchange=updateCompatibilityPorts;

function syncOrchestrationCompartment(){
  const solid=["soil","sediment"].includes(el("orch-compartment").value);
  el("orch-unit").value=solid?"µg/kg":"µg/L";
  el("orch-phase").value=solid?"bulk":"total";
  el("orch-basis").value=solid?"dry_weight":"volume";
}
el("orch-compartment").onchange=syncOrchestrationCompartment;

function orchestrationPayload(){
  requireProject();
  const currentTier=Number(el("orch-current-tier").value);
  const maximumTier=Number(el("orch-maximum-tier").value);
  if(currentTier>maximumTier)throw new Error("Current tier cannot exceed maximum tier");
  const dataGaps=el("orch-data-gaps").value.split(/\r?\n/).map(value=>value.trim()).filter(Boolean).map((description,index)=>({
    code:`USER_GAP_${index+1}`,
    description,
    blocks_conclusion:true,
    required_by_tier:currentTier
  }));
  const pecText=el("orch-pec").value.trim();
  const benchmarkText=el("orch-benchmark").value.trim();
  const risks=[];
  const modelResults=[];
  if(pecText||benchmarkText){
    if(!pecText||!benchmarkText)throw new Error("Provide both PEC and PNEC, or leave both blank");
    if(Number(benchmarkText)<=0)throw new Error("PNEC / benchmark must be greater than zero");
    const benchmarkSource=el("orch-benchmark-source").value.trim();
    const guidance=el("orch-guidance").value.trim();
    if(!benchmarkSource||!guidance)throw new Error("Benchmark source and guidance reference are required for an RQ");
    const runId=el("orch-run-id").value?Number(el("orch-run-id").value):null;
    const evidenceId=el("orch-benchmark-evidence").value?Number(el("orch-benchmark-evidence").value):null;
    const assessmentFactor=el("orch-assessment-factor").value?Number(el("orch-assessment-factor").value):null;
    const evidenceReviewed=el("orch-evidence-reviewed").checked;
    const afRationale=el("orch-af-rationale").value.trim();
    if(evidenceId&&(!assessmentFactor||!evidenceReviewed||afRationale.length<10))throw new Error("Reviewed evidence requires an assessment factor and a rationale of at least 10 characters");
    const modelKey=el("orch-risk-model").value;
    const metadata={
      unit:el("orch-unit").value,
      endpoint_kind:"concentration",
      compartment:el("orch-compartment").value,
      phase:el("orch-phase").value,
      basis:el("orch-basis").value,
      temporal_statistic:el("orch-temporal").value,
      averaging_period_days:Number(el("orch-period").value),
      spatial_scale:el("orch-scale").value,
      substance_basis:el("orch-substance-basis").value
    };
    risks.push({
      name:`${pretty(metadata.compartment)} PEC/PNEC risk quotient`,
      metric:"pec_pnec_rq",
      exposure:{...metadata,value:Number(pecText),label:"Predicted exposure concentration"},
      benchmark:{...metadata,value:Number(benchmarkText),label:"Reviewed effect benchmark"},
      threshold:1,
      benchmark_type:`PNEC ${pretty(metadata.compartment)}`,
      benchmark_source:benchmarkSource,
      guidance_reference:guidance,
      model_key:modelKey,
      exposure_run_id:runId,
      exposure_endpoint_key:el("orch-endpoint-key").value.trim()||null,
      benchmark_evidence_ids:evidenceId?[evidenceId]:[],
      critical_benchmark_evidence_id:evidenceId,
      benchmark_evidence_review_confirmed:evidenceId?evidenceReviewed:false,
      assessment_factor:evidenceId?assessmentFactor:null,
      assessment_factor_rationale:evidenceId?afRationale:null
    });
    if(runId){
      modelResults.push({
        model_key:modelKey,
        jurisdiction:el("orch-jurisdiction").value,
        tier:currentTier,
        execution_status:"not_started",
        alignment_claim:el("orch-alignment").value,
        guidance_reference:guidance,
        run_id:runId,
        outputs:[]
      });
    }
  }
  return {
    project_id:state.project.id,
    chemical_id:state.chemical.id,
    jurisdiction:el("orch-jurisdiction").value,
    contaminant_group:el("orch-group").value,
    scenario:el("orch-scenario").value,
    current_tier:currentTier,
    maximum_tier:maximumTier,
    assessment_mode:el("orch-mode").value,
    uncertainty:el("orch-uncertainty").value,
    application_method:el("orch-application").value||null,
    use_site_category:el("orch-use-site").value||null,
    bee_attractive:el("orch-bee-attractive").checked,
    data_gaps:dataGaps,
    model_results:modelResults,
    risk_characterisations:risks,
    model_connections:[]
  };
}

function orchestrationStatusClass(code){
  if(["stop_screening","below_trigger_at_current_tier","regulatory_aligned_workflow"].includes(code))return "orch-good";
  if(["potential_concern","resolve_incompatibility","expert_review"].includes(code))return "orch-alert";
  return "orch-review";
}

function renderOrchestrationRecord(record, persisted=null){
  state.orchestrationPreview=record;
  const gate=record.current_tier_decision;
  const regulatory=record.regulatory_status;
  const conclusion=record.overall_conclusion;
  const riskRows=record.risk_characterisations.map(result=>`<div class="orchestration-risk-row"><div><small>${pretty(result.metric)}</small><strong>${result.value==null?"Not calculated":fmt(result.value,5)}</strong></div><span class="${orchestrationStatusClass(result.status)}">${pretty(result.status)}</span><p>${escapeHtml(result.conclusion)}</p><small>${result.decision_eligible?"PEC endpoint and benchmark evidence verified":"Exploratory result — verified PEC endpoint and reviewed benchmark evidence are both required to control the tier gate"}</small></div>`).join("");
  const stages=record.tier_sequence.map(stage=>`<div class="orchestration-tier ${stage.tier===record.context.current_tier?"current":""}"><div class="orchestration-tier-number">${stage.tier}</div><div><small>${escapeHtml(stage.title)}</small><strong>${stage.regulatory_programme?escapeHtml(stage.regulatory_programme.name):"Identity and evidence foundation"}</strong><p>${stage.models.length?stage.models.map(model=>escapeHtml(model.name)).join(" · "):"No simulator execution at this stage"}</p>${stage.introduced_models.length?`<span>${stage.introduced_models.length} newly introduced model(s)</span>`:""}</div></div>`).join("");
  el("orchestration-result").innerHTML=`
    <div class="panel-head"><div><small>${escapeHtml(record.context.jurisdiction)} · ${pretty(record.context.assessment_mode)} · ${persisted?`SAVED #${persisted.id}`:"PREVIEW"}</small><h3>${escapeHtml(record.identity.preferred_name||state.chemical?.preferred_name||"Assessment")} tier route</h3></div></div>
    <div class="orchestration-decision ${orchestrationStatusClass(gate.action)}"><small>CURRENT GATE</small><strong>${pretty(gate.action)}</strong><p>${gate.reasons.map(escapeHtml).join(" ")}</p>${gate.next_tier!==null?`<span>Next: Tier ${gate.next_tier}</span>`:""}</div>
    <div class="orchestration-regulatory"><small>REGULATORY STATUS</small><strong>${escapeHtml(regulatory.label)}</strong><p>${escapeHtml(regulatory.reason)}</p></div>
    <div class="orchestration-conclusion"><small>PROVISIONAL CONCLUSION</small><strong>${pretty(conclusion.code)}</strong><p>${escapeHtml(conclusion.text)}</p></div>
    <h3>Tier sequence</h3><div class="orchestration-tier-stack">${stages}</div>
    ${riskRows?`<h3>Risk characterisation</h3>${riskRows}`:"<div class=\"warning\">No PEC/PNEC risk characterisation was supplied. The route can be planned, but the current tier cannot close.</div>"}
    <details><summary>Record integrity and graph</summary><dl class="provenance-list"><div><dt>Identity hash</dt><dd><code>${escapeHtml(record.identity.identity_hash)}</code></dd></div><div><dt>Record hash</dt><dd><code>${escapeHtml(record.record_hash)}</code></dd></div><div><dt>Graph</dt><dd>${record.graph.nodes.length} nodes · ${record.graph.edges.length} edges</dd></div><div><dt>Ruleset</dt><dd>${escapeHtml(record.risk_ruleset_version)}</dd></div></dl></details>
    <div class="scope-boundary"><strong>Competent review required</strong><span>FateIntel has not issued a final regulatory decision.</span></div>`;
}

el("orchestration-form").onsubmit=async event=>{
  event.preventDefault();
  const record=await api("/api/orchestration/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(orchestrationPayload())});
  renderOrchestrationRecord(record);
  showToast("Tier route previewed; no assessment record was saved","success");
};

el("orch-save").onclick=async()=>{
  const saved=await api("/api/orchestration/assessments",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(orchestrationPayload())});
  renderOrchestrationRecord(saved.record,saved);
  await loadOrchestratedAssessments();
  await loadAudit();
  showToast(`Immutable assessment #${saved.id} saved`,"success");
};

async function loadOrchestratedAssessments(){
  const box=el("orchestration-history");
  if(!box)return;
  if(!state.project){box.className="empty";box.innerHTML="Select a project.";return;}
  const chemicalQuery=state.chemical?`?chemical_id=${state.chemical.id}`:"";
  state.orchestratedAssessments=await api(`/api/projects/${state.project.id}/orchestrated-assessments${chemicalQuery}`);
  box.className="orchestration-history";
  box.innerHTML=state.orchestratedAssessments.length?state.orchestratedAssessments.map(row=>`<div class="orchestration-history-row"><button type="button" data-orchestration-id="${row.id}"><span><small>${escapeHtml(row.jurisdiction)} · Tier ${row.current_tier} · ${pretty(row.status)}</small><strong>#${row.id} · ${pretty(row.scenario)}</strong></span><span>${new Date(row.created_at).toLocaleString()}</span></button><a href="/api/orchestration/assessments/${row.id}/export" download>JSON</a></div>`).join(""):'<div class="empty">No immutable assessment records yet.</div>';
  box.querySelectorAll("[data-orchestration-id]").forEach(button=>button.onclick=()=>{
    const row=state.orchestratedAssessments.find(item=>item.id===Number(button.dataset.orchestrationId));
    if(row)renderOrchestrationRecord(row.record,row);
  });
}

el("refresh-orchestrated-assessments").onclick=()=>loadOrchestratedAssessments().catch(error=>showToast(error.message,"error"));

el("compatibility-form").onsubmit=async event=>{
  event.preventDefault();
  const result=await api("/api/orchestration/model-compatibility",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    source_model_key:el("compat-source-model").value,
    source_port_key:el("compat-source-port").value,
    target_model_key:el("compat-target-model").value,
    target_port_key:el("compat-target-port").value,
    value:Number(el("compat-value").value),
    allow_draft_contracts:el("compat-allow-draft").checked
  })});
  const reasons=(result.reasons||[]).map(reason=>`<li><strong>${pretty(reason.code)}</strong> — ${escapeHtml(reason.message)}</li>`).join("");
  const converted=result.harmonised_source;
  el("compatibility-result").innerHTML=`<div class="compatibility-answer ${result.compatible?"orch-good":"orch-alert"}"><small>CONNECTION ${result.compatible?"COMPATIBLE":"BLOCKED"}</small><strong>${escapeHtml(result.source_model_key||el("compat-source-model").value)} → ${escapeHtml(result.target_model_key||el("compat-target-model").value)}</strong>${converted?`<p>${fmt(converted.value,6)} ${escapeHtml(converted.unit)} on the target basis</p>`:""}${reasons?`<ul>${reasons}</ul>`:"<p>Units and all declared scientific bases match.</p>"}<span>${el("compat-allow-draft").checked?"Draft-contract result requires manual review":"Only verified semantic contracts can pass automatically"}</span></div>`;
};

function renderModelLibrary(){
  const region=el("model-filter-region")?.value||"all";
  const tier=el("model-filter-tier")?.value||"all";
  const implementation=el("model-filter-implementation")?.value||"all";
  const filtered=state.models.filter(m=>(region==="all"||m.regions.includes(region))&&(tier==="all"||m.tiers.includes(Number(tier)))&&(implementation==="all"||m.implementation===implementation));
  el("model-library").innerHTML=filtered.map(m=>{
    const contract=state.contracts[m.key]||{};
    return `<div class="model-card"><div class="model-card-top"><div><small>${m.implementation}</small><h3>${m.name}</h3></div><span class="status ${m.status.includes('working')?'working':'planned'}">${pretty(m.status)}</span></div><p>${m.domain}</p><div class="chips">${m.regions.map(x=>`<span>${x}</span>`).join("")}</div><details><summary>Outputs and scope</summary><p><strong>Outputs:</strong> ${m.outputs.map(pretty).join(", ")}</p><p><strong>Tiers:</strong> ${m.tiers.join(", ")}</p><p><strong>Required inputs:</strong> ${(contract.required_inputs||[]).map(pretty).join(", ")}</p><p><strong>Execution:</strong> ${contract.redistribution_note||"Workflow contract pending"}</p></details><button class="secondary model-prepare" onclick="prepareModelKey('${m.key}')">Prepare workflow</button></div>`;
  }).join("")||'<div class="empty">No models match the selected filters.</div>';
}

function renderExternalIntegrations(){
  const box=el("external-model-integrations");
  if(!box)return;
  box.innerHTML=state.externalIntegrations.map(profile=>{
    const bridge=profile.execution_bridge||{};
    const bridgeLabel=bridge.execution_ready?'Execution ready':bridge.path_exists?'Installation detected · handoff':'Manual handoff';
    const bridgeClass=bridge.execution_ready?'working':'planned';
    return `
    <article class="external-model-card">
      <div class="external-model-top"><div><small>${profile.is_simulation_model?'EXTERNAL SIMULATOR':'SHARED FOCUS DEPENDENCY'}</small><h3>${profile.name}</h3></div><span class="status ${bridgeClass}">${bridge.supported?bridgeLabel:(profile.path_exists?'Path found':'Path required')}</span></div>
      <p>${profile.role}</p>
      <dl><div><dt>Version</dt><dd>${profile.official_version}</dd></div><div><dt>Path setting</dt><dd>${profile.path_environment_variable}</dd></div><div><dt>Run route</dt><dd>${pretty(bridge.default_route||'managed handoff')}</dd></div><div><dt>Prerequisites</dt><dd>${profile.prerequisites.join(', ')||'None'}</dd></div></dl>
      <div class="external-model-actions"><a href="${profile.official_page}" target="_blank" rel="noopener">Official source</a><button class="secondary" onclick="prepareModelKey('${profile.key}')">Prepare ${profile.key}</button></div>
    </article>`;
  }).join("");
}

function parseJsonInput(id, label){
  try{return JSON.parse(el(id).value);}
  catch(error){throw new Error(`${label} must be valid JSON`);}
}

el("multimedia-form").onsubmit=async event=>{
  event.preventDefault();
  requireProject();
  const response=await api("/api/model-runs/multimedia-fate",{
    method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      project_id:state.project.id,
      chemical_id:state.chemical.id,
      scenario_name:"Expert multimedia environmental fate screen",
      emissions_kg_day:parseJsonInput("mm-emissions","Emissions"),
      compartments:parseJsonInput("mm-compartments","Compartments"),
      transfers:parseJsonInput("mm-transfers","Transfer rates")
    })
  });
  const output=response.outputs;
  el("multimedia-result").innerHTML=`
    <div class="selection-hero"><div><small>MASS BALANCE</small><strong>${fmt(output.mass_balance.emission_input_kg_day)} kg/day</strong><span>Closure ${fmt(output.mass_balance.relative_closure_error,3)}</span></div><div>Run #${response.model_run_id}</div></div>
    <div class="table-wrap"><table><thead><tr><th>Compartment</th><th>Mass (kg)</th><th>Concentration</th><th>Degraded (kg/day)</th><th>Advected (kg/day)</th></tr></thead><tbody>${output.compartments.map(row=>`<tr><td><strong>${pretty(row.key)}</strong></td><td>${fmt(row.mass_kg)}</td><td>${fmt(row.concentration)} ${row.concentration_unit}</td><td>${fmt(row.degradation_loss_kg_day)}</td><td>${fmt(row.advective_loss_kg_day)}</td></tr>`).join("")}</tbody></table></div>
    <div class="warning"><strong>Scientific boundary</strong><ul>${output.warnings.map(item=>`<li>${item}</li>`).join("")}</ul></div>`;
  await loadAudit();
};

el("river-network-form").onsubmit=async event=>{
  event.preventDefault();
  requireProject();
  const response=await api("/api/model-runs/catchment-river",{
    method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      project_id:state.project.id,
      chemical_id:state.chemical.id,
      scenario_name:"Expert catchment river-network exposure screen",
      default_water_dt50_days:Number(el("river-dt50").value),
      aquatic_pnec_ug_l:el("river-pnec").value===""?null:Number(el("river-pnec").value),
      segments:parseJsonInput("river-segments","River segments")
    })
  });
  const output=response.outputs, summary=output.network_summary;
  el("river-network-result").innerHTML=`
    <div class="selection-hero"><div><small>PEAK MEAN PEC</small><strong>${fmt(summary.peak_mean_concentration_ug_l)} µg/L</strong><span>${summary.peak_segment_id} · ${summary.segment_count} segment(s)</span></div><div>Run #${response.model_run_id}</div></div>
    <div class="table-wrap"><table><thead><tr><th>Segment</th><th>Local load</th><th>Inlet PEC</th><th>Mean PEC</th><th>Outlet PEC</th><th>RQ</th></tr></thead><tbody>${output.segments.map(row=>`<tr><td><strong>${row.segment_id}</strong></td><td>${fmt(row.local_direct_load_kg_day+row.local_effluent_load_kg_day)} kg/day</td><td>${fmt(row.inlet_concentration_ug_l)} µg/L</td><td>${fmt(row.mean_concentration_ug_l)} µg/L</td><td>${fmt(row.outlet_concentration_ug_l)} µg/L</td><td>${fmt(row.risk_quotient_mean)}</td></tr>`).join("")}</tbody></table></div>
    <div class="warning"><strong>Scientific boundary</strong><ul>${output.warnings.map(item=>`<li>${item}</li>`).join("")}</ul></div>`;
  await loadAudit();
};

function setHomeProfileBinding(bound){
  const hidden=el("h-profile-bound");
  if(!hidden)return;
  hidden.value=bound?"true":"false";
  ["h-chemical","h-logkow","h-dt50"].forEach(id=>{el(id).disabled=bound;});
  updateHomeProfileBinding();
}

function updateHomeProfileBinding(){
  const button=el("h-use-selected"), status=el("home-link-state");
  if(!button||!status)return;
  const inProject=Boolean(state.project&&state.chemical&&state.projectChemicalIds.has(state.chemical.id));
  const reviewed=Boolean(state.profile&&state.profile.review_status==="reviewed"&&state.profile.reviewer_confirmation);
  const confirmed=Boolean(state.chemical?.identity_snapshot);
  const ready=inProject&&reviewed&&confirmed;
  const bound=el("h-profile-bound").value==="true";
  if(bound&&!ready){
    el("h-profile-bound").value="false";
    ["h-chemical","h-logkow","h-dt50"].forEach(id=>{el(id).disabled=false;});
  }
  button.disabled=!ready;
  button.textContent=bound?"Release profile binding":"Use selected reviewed profile";
  status.textContent=ready
    ? `${state.chemical.preferred_name} · ${bound?"profile bound to this summary":"reviewed profile available"}`
    : "Select a confirmed chemical with a reviewed profile to enable binding.";
}

el("h-use-selected").onclick=()=>{
  const bound=el("h-profile-bound").value==="true";
  if(bound){
    setHomeProfileBinding(false);
    showToast("Reviewed-profile binding released; visible values can now be edited.");
    return;
  }
  if(!state.project||!state.chemical||!state.profile)return;
  el("h-chemical").value=state.chemical.preferred_name;
  el("h-logkow").value=state.profile.log_kow??"";
  el("h-dt50").value=state.profile.soil_dt50_days??"";
  el("h-koc").value="";
  setHomeProfileBinding(true);
  showToast(`Bound ${state.chemical.preferred_name} identity and reviewed profile. Koc remains unbound because it is not stored in this profile.`,"success");
};

el("home-form").onsubmit=async e=>{
  e.preventDefault();
  const optional=id=>el(id).value===""?null:Number(el(id).value);
  const bound=el("h-profile-bound").value==="true";
  const r=await api("/api/home-use-summary",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    project_id:bound?state.project.id:null,
    chemical_id:bound?state.chemical.id:null,
    assessment_profile_id:bound?state.profile.id:null,
    bind_to_reviewed_profile:bound,
    product_identifier:el("h-identifier").value||null,
    product_name:el("h-product").value||null,
    chemical_name:el("h-chemical").value||null,
    amount_value:Number(el("h-amount").value),amount_unit:el("h-unit").value,
    frequency_value:Number(el("h-frequency").value),frequency_unit:el("h-frequency-unit").value,
    release_route:el("h-route").value,log_kow:optional("h-logkow"),koc_l_kg:optional("h-koc"),soil_dt50_days:optional("h-dt50")
  })});
  renderHomeSummary(r);
};

function renderHomeSummary(r){
  const flagClass=level=>["high","moderate","lower"].includes(level)?level:"unknown";
  const reviewed=r.input_basis.filter(item=>item.status==="reviewed"||item.status==="confirmed");
  el("home-result").innerHTML=`<div class="home-summary-head"><small>QUALITATIVE ENVIRONMENTAL FATE</small><h2>${escapeHtml(r.product_name)}</h2><p>${escapeHtml(r.chemical_name)}</p></div><div class="home-route"><small>MAIN ROUTE</small><strong>${escapeHtml(r.primary_environmental_path)}</strong></div><div class="flag-list">${r.fate_flags.map(x=>`<div class="fate-flag ${flagClass(x.level)}"><span>${escapeHtml(x.topic)}</span><strong>${pretty(x.level)}</strong><p>${escapeHtml(x.text)}</p></div>`).join("")}</div><h3>What to do</h3><ul>${r.advice.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul><div class="confidence">Confidence: <strong>${pretty(r.confidence)}</strong><br><small>${r.confidence_basis.map(escapeHtml).join(" · ")}</small></div><div class="scope-boundary"><strong>No quantitative risk result</strong><span>PEC: not calculated · PNEC: not used · RQ: not calculated</span></div><details><summary>Input provenance (${reviewed.length} confirmed/reviewed field(s))</summary><dl class="provenance-list">${r.input_basis.map(item=>`<div><dt>${escapeHtml(pretty(item.field))}</dt><dd>${escapeHtml(pretty(item.source))} · ${escapeHtml(pretty(item.status))}</dd></div>`).join("")}</dl></details><div class="warning"><strong>Important boundaries</strong><ul>${r.warnings.map(item=>`<li>${escapeHtml(item)}</li>`).join("")}</ul></div><p>${escapeHtml(r.plain_language_summary)}</p>`;
}

el("coshh-form").onsubmit=async e=>{
  e.preventDefault();
  const file=el("c-file").files[0];
  if(!file){showToast("Select an SDS file","error");return;}
  const data=new FormData();
  data.append("sds_file",file);
  data.append("substance_name",el("c-substance").value);
  data.append("task_description",el("c-task").value);
  data.append("quantity",el("c-quantity").value);
  data.append("frequency",el("c-frequency").value);
  data.append("persons_at_risk",el("c-persons").value);
  data.append("open_handling",el("c-open").checked);
  data.append("heating_or_aerosol",el("c-aerosol").checked);
  const r=await api("/api/lab/coshh-draft",{method:"POST",body:data});
  renderCoshh(r);
};

function renderCoshh(r){
  const c=r.coshh_draft;
  el("coshh-result").innerHTML=`<div class="draft-badge">DRAFT · COMPETENT PERSON REVIEW REQUIRED</div><h2>${c.title}</h2><p><strong>Task:</strong> ${c.task}</p><div class="stats"><div class="stat"><small>Initial risk</small><strong>${pretty(c.initial_risk)}</strong></div><div class="stat"><small>Residual risk</small><strong>${pretty(c.residual_risk)}</strong></div><div class="stat"><small>H statements</small><strong>${c.hazards.h_statements.length}</strong></div><div class="stat"><small>SDS sections</small><strong>${r.sds.sections_found.length}</strong></div></div><h3>Extracted hazards</h3><p>${c.hazards.signal_word||"No signal word extracted"} · ${c.hazards.h_statements.join(", ")||"No H codes extracted"}</p><h3>Controls for this task</h3><ol>${c.recommended_controls.map(x=>`<li>${x}</li>`).join("")}</ol><h3>Emergency and disposal</h3><p><strong>First aid:</strong> ${c.emergency_information.first_aid||"Manual review required"}</p><p><strong>Spill:</strong> ${c.emergency_information.spill||"Manual review required"}</p><p><strong>Waste:</strong> ${c.waste_disposal||"Manual review required"}</p>${c.manual_review_items.length?`<div class="warning"><strong>Manual checks</strong><ul>${c.manual_review_items.map(x=>`<li>${x}</li>`).join("")}</ul></div>`:""}<div class="approval-box">${c.approval_statement}<div class="signature-lines"><span>Assessor</span><span>Reviewer</span><span>Date</span></div></div>`;
}


function initialiseModelWorkflow(){
  if(!el("mw-model")) return;
  el("mw-model").innerHTML=state.models.map(m=>`<option value="${m.key}">${m.name} · ${pretty(m.implementation)}</option>`).join("");
  ["model-filter-region","model-filter-tier","model-filter-implementation"].forEach(id=>el(id).onchange=renderModelLibrary);
  el("mw-model").onchange=syncWorkflowModelOptions;
  syncWorkflowModelOptions();
}

function syncWorkflowModelOptions(){
  const model=state.models.find(m=>m.key===el("mw-model").value);
  if(!model) return;
  el("mw-region").innerHTML=model.regions.map(x=>`<option>${x}</option>`).join("");
  el("mw-tier").innerHTML=model.tiers.map(x=>`<option value="${x}">${x}</option>`).join("");
  const contract=state.contracts[model.key];
  if(contract){
    const example=contract.input_template ? structuredClone(contract.input_template) : {};
    if(!contract.input_template) contract.required_inputs.slice(0,5).forEach(key=>example[key]={value:null,unit:null,evidence_status:"required"});
    el("mw-inputs").value=JSON.stringify(example,null,2);
  }
}

window.prepareModelKey=key=>{
  page("models");
  el("mw-model").value=key;
  syncWorkflowModelOptions();
  el("model-workflow-form").scrollIntoView({behavior:"smooth",block:"start"});
};

el("model-workflow-form").onsubmit=async e=>{
  e.preventDefault();
  requireProject();
  let inputData={};
  try{inputData=JSON.parse(el("mw-inputs").value||"{}");}
  catch(err){throw new Error("Reviewed inputs must be valid JSON");}
  const workflow=await api("/api/model-workflows",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    project_id:state.project.id,
    chemical_id:state.chemical.id,
    model_key:el("mw-model").value,
    jurisdiction:el("mw-region").value,
    tier:Number(el("mw-tier").value),
    scenario_name:el("mw-scenario").value,
    input_data:inputData,
    executable_path:el("mw-executable").value||null
  })});
  state.selectedWorkflow=workflow;
  await loadModelWorkflows();
  renderModelWorkflowDetail(workflow);
};

async function loadModelWorkflows(){
  if(!el("model-workflow-list")) return;
  if(!state.project){el("model-workflow-list").innerHTML='<div class="empty">Select a project.</div>';return;}
  state.modelWorkflows=await api(`/api/projects/${state.project.id}/model-workflows`);
  renderModelWorkflowList();
}

function renderModelWorkflowList(){
  const box=el("model-workflow-list");
  if(!box) return;
  box.innerHTML=state.modelWorkflows.length?state.modelWorkflows.map(w=>`<button class="workflow-list-item ${state.selectedWorkflow?.id===w.id?'active':''}" onclick="selectModelWorkflow(${w.id})"><span><strong>${w.model_key}</strong><br><small>${w.jurisdiction} · Tier ${w.tier} · ${w.scenario_name}</small></span><span>${pretty(w.status)} ›</span></button>`).join(""):'<div class="empty">No model workflows prepared for this project.</div>';
}

window.selectModelWorkflow=id=>{
  state.selectedWorkflow=state.modelWorkflows.find(x=>x.id===id);
  renderModelWorkflowList();
  renderModelWorkflowDetail(state.selectedWorkflow);
};

function renderModelWorkflowDetail(w){
  const box=el("model-workflow-detail");
  if(!w){box.classList.add("hidden");return;}
  box.classList.remove("hidden");
  const missing=w.manifest.missing_inputs||[];
  const modelValidation=w.manifest.model_specific_validation;
  const output=w.output_record?.structured_outputs||{};
  const outputValidation=w.output_record?.model_specific_validation;
  const integration=state.externalIntegrations.find(row=>row.key===w.model_key);
  const bridge=integration?.execution_bridge||{};
  const officialEPA=Boolean(bridge.supported);
  const accepted=(state.contracts[w.model_key]?.accepted_output_formats||[]).map(x=>`.${x}`).join(',');
  const outputTemplate=Object.fromEntries((w.expected_outputs||[]).map(key=>[key,output[key]??null]));
  const bridgePanel=officialEPA?`
    <div class="external-validation official-bridge-status">
      <strong>Official-tool execution bridge · ${pretty(bridge.configuration_state)}</strong>
      <span>${bridge.execution_ready?'Pinned local process is ready':'Use the handoff ZIP for a GUI/manual run'}</span>
      ${bridge.executable_sha256?`<p>Configured executable SHA-256<br><code>${bridge.executable_sha256}</code></p>`:''}
      ${bridge.missing_requirements?.length?`<ul>${bridge.missing_requirements.map(item=>`<li>${escapeHtml(item)}</li>`).join('')}</ul>`:''}
      <p>FateIntel neither bundles nor modifies the EPA software. A prepared manifest is not an execution.</p>
    </div>
    ${bridge.execution_ready?`<form id="official-execute-form" class="official-execute-form">
      <h3>Execute pinned local installation</h3>
      <div class="grid two"><div><label>Operator</label><input id="mwe-operator" required></div><div><label>Installed version</label><input id="mwe-version" value="${escapeHtml(w.executable_version||'')}" required></div></div>
      <label class="check-label"><input id="mwe-authorised" type="checkbox" required> This is an authorised, separately installed official copy.</label>
      <label class="check-label"><input id="mwe-unmodified" type="checkbox" required> The configured executable is unmodified and its displayed SHA-256 is acknowledged.</label>
      <button ${missing.length?'disabled':''}>Execute and capture output files</button>
    </form>`:''}`:'';
  const importForm=officialEPA?`
      <form id="official-output-files-form" enctype="multipart/form-data">
        <h3>Import official output files</h3>
        <p class="field-note">For a manual/GUI run, retain original files and map every endpoint needed for review. Files are hashed on import.</p>
        <label>Original output files</label><input id="mwo-files" type="file" accept="${accepted}" multiple required>
        <div class="grid two"><div><label>Model version</label><input id="mwo-model-version" value="${escapeHtml(w.model_version||'')}" required></div><div><label>Executable version</label><input id="mwo-executable-version" value="${escapeHtml(w.executable_version||'')}" required></div></div>
        <label>Operator</label><input id="mwo-operator" required>
        <label>Execution notes</label><textarea id="mwo-notes" rows="3" required placeholder="Workstation, scenario/database version and how the run was checked"></textarea>
        <label>Reviewed structured outputs (JSON)</label><textarea id="mwo-structured" rows="10">${escapeHtml(JSON.stringify(outputTemplate,null,2))}</textarea>
        <label class="check-label"><input id="mwo-genuine" type="checkbox" required> These files came from a genuine execution of the official tool.</label>
        <label class="check-label"><input id="mwo-authorised" type="checkbox" required> The installation was obtained and used under the applicable terms.</label>
        <button ${missing.length?'disabled':''}>Import, hash and validate files</button>
      </form>`:`
      <form id="model-output-form">
        <h3>Import model output</h3>
        <label>Model version</label><input id="mwo-model-version" value="${escapeHtml(w.model_version||'')}">
        <label>Executable version</label><input id="mwo-executable-version" value="${escapeHtml(w.executable_version||'')}">
        <label>Raw or key=value output</label><textarea id="mwo-raw" rows="8" placeholder="groundwater_concentration=0.12\nleaching_flux=4.6">${escapeHtml(w.output_record?.raw_output_text||'')}</textarea>
        <button>Import and hash output</button>
      </form>`;
  box.innerHTML=`
    <div class="panel-head split"><div><small>${w.implementation} · ${w.jurisdiction} · TIER ${w.tier}</small><h3>${w.model_key} workflow #${w.id}</h3></div><span class="status ${w.status==='reviewed'?'working':'planned'}">${pretty(w.status)}</span></div>
    <div class="hash-grid"><div><small>INPUT HASH</small><code>${w.input_hash}</code></div><div><small>OUTPUT HASH</small><code>${w.output_hash||'Not imported'}</code></div></div>
    <p><strong>Scenario:</strong> ${w.scenario_name}</p>
    ${missing.length?`<div class="warning"><strong>Inputs still required</strong><ul>${missing.map(x=>`<li>${pretty(x)}</li>`).join("")}</ul></div>`:`<div class="success-note">All contract inputs are present in the manifest.</div>`}
    ${modelValidation?`<div class="external-validation"><strong>${modelValidation.official_name} · ${modelValidation.official_version}</strong><span>${modelValidation.is_simulation_model?'External simulation workflow':'Dependency record; no fate calculation'}</span><p>${modelValidation.role}</p><ul>${modelValidation.warnings.map(item=>`<li>${item}</li>`).join('')}</ul></div>`:''}
    <div class="grid two">
      <div><h3>Workflow steps</h3><ol>${w.manifest.workflow_steps.map(x=>`<li>${x}</li>`).join("")}</ol><p><a class="button-link" href="/api/model-workflows/${w.id}/manifest">Download input manifest</a>${integration?` · <a class="button-link" href="/api/model-workflows/${w.id}/handoff">Download official-run handoff ZIP</a>`:''}</p></div>
      <div><h3>Expected outputs</h3><ul>${w.expected_outputs.map(x=>`<li>${pretty(x)}</li>`).join("")}</ul><p><strong>Executable:</strong> ${w.executable_path||'Not configured / native execution'}</p></div>
    </div>
    ${bridgePanel}
    <details><summary>Full input manifest</summary><pre>${escapeHtml(JSON.stringify(w.manifest,null,2))}</pre></details>
    <div class="grid two model-output-grid">
      ${importForm}
      <form id="model-review-form">
        <h3>Scientific review</h3>
        <label>Reviewer</label><input id="mwr-reviewer" value="${w.reviewer||''}" required>
        <label>Decision</label><select id="mwr-decision"><option value="accepted">Accepted</option><option value="revision_required">Revision required</option><option value="rejected">Rejected</option></select>
        <label>Review notes</label><textarea id="mwr-notes" rows="8">${w.review_notes||''}</textarea>
        <button ${w.output_record?'':'disabled'}>Record review decision</button>
      </form>
    </div>
    ${Object.keys(output).length?`<h3>Imported structured outputs</h3><div class="table-wrap"><table><tbody>${Object.entries(output).map(([k,v])=>`<tr><th>${pretty(k)}</th><td>${escapeHtml(typeof v==='object'?JSON.stringify(v):v)}</td></tr>`).join("")}</tbody></table></div>`:''}
    ${outputValidation&&outputValidation.missing_recommended_outputs.length?`<div class="warning"><strong>Imported output review items</strong><p>Recommended structured fields not yet mapped: ${outputValidation.missing_recommended_outputs.map(pretty).join(', ')}. The raw record and output hash are retained.</p></div>`:''}`;
  if(el("official-execute-form")) el("official-execute-form").onsubmit=async e=>{
    e.preventDefault();
    const updated=await api(`/api/model-workflows/${w.id}/execute`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      operator:el("mwe-operator").value,
      installed_version:el("mwe-version").value,
      expected_executable_sha256:bridge.executable_sha256,
      confirm_authorised_installation:el("mwe-authorised").checked,
      confirm_unmodified_official_software:el("mwe-unmodified").checked
    })});
    state.selectedWorkflow=updated; await loadModelWorkflows(); renderModelWorkflowDetail(updated); await loadAudit();
  };
  if(el("official-output-files-form")) el("official-output-files-form").onsubmit=async e=>{
    e.preventDefault();
    let structured={};
    try{structured=JSON.parse(el("mwo-structured").value||"{}");}catch{throw new Error("Reviewed structured outputs must be valid JSON");}
    const data=new FormData();
    [...el("mwo-files").files].forEach(file=>data.append("files",file));
    data.append("model_version",el("mwo-model-version").value);
    data.append("executable_version",el("mwo-executable-version").value);
    data.append("operator",el("mwo-operator").value);
    data.append("execution_notes",el("mwo-notes").value);
    data.append("structured_outputs_json",JSON.stringify(structured));
    data.append("confirm_genuine_execution",String(el("mwo-genuine").checked));
    data.append("confirm_authorised_installation",String(el("mwo-authorised").checked));
    const updated=await api(`/api/model-workflows/${w.id}/import-output-files`,{method:"POST",body:data});
    state.selectedWorkflow=updated; await loadModelWorkflows(); renderModelWorkflowDetail(updated); await loadAudit();
  };
  if(el("model-output-form")) el("model-output-form").onsubmit=async e=>{
    e.preventDefault();
    const updated=await api(`/api/model-workflows/${w.id}/import-output`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      raw_output_text:el("mwo-raw").value,
      structured_outputs:{},
      model_version:el("mwo-model-version").value||null,
      executable_version:el("mwo-executable-version").value||null,
      execution_notes:"Imported through FateIntel model control plane"
    })});
    state.selectedWorkflow=updated; await loadModelWorkflows(); renderModelWorkflowDetail(updated);
  };
  el("model-review-form").onsubmit=async e=>{
    e.preventDefault();
    const updated=await api(`/api/model-workflows/${w.id}/review`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      reviewer:el("mwr-reviewer").value,
      decision:el("mwr-decision").value,
      notes:el("mwr-notes").value||null
    })});
    state.selectedWorkflow=updated; await loadModelWorkflows(); renderModelWorkflowDetail(updated); await loadAudit();
  };
}

function escapeHtml(value){return String(value).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));}
function safeExternalUrl(value){
  if(!value)return null;
  try{
    const parsed=new URL(value,window.location.origin);
    return ["http:","https:"].includes(parsed.protocol)?escapeHtml(parsed.href):null;
  }catch{return null;}
}

el("refresh-model-workflows").onclick=loadModelWorkflows;


let deferredInstallPrompt=null;
window.addEventListener("beforeinstallprompt",e=>{
  e.preventDefault();deferredInstallPrompt=e;el("install-app").classList.remove("hidden");
});
el("install-app").onclick=async()=>{
  if(!deferredInstallPrompt)return;
  deferredInstallPrompt.prompt();await deferredInstallPrompt.userChoice;deferredInstallPrompt=null;el("install-app").classList.add("hidden");
};
if("serviceWorker" in navigator){navigator.serviceWorker.register("/static/sw.js").catch(()=>{});}

init().catch(e=>showToast(e.message,"error",9000));
