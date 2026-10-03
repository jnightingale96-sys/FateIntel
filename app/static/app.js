const $ = (id) => document.getElementById(id);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const fmt = (value, digits = 3) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  if (n === 0) return "0";
  const sigDigits = Math.max(1, Math.min(21, digits)); // maximumSignificantDigits/maximumFractionDigits must be 1-21
  if (Math.abs(n) >= 1000) return n.toLocaleString(undefined,{maximumFractionDigits:sigDigits});
  if (Math.abs(n) < 0.001) return n.toExponential(2);
  return n.toLocaleString(undefined,{maximumSignificantDigits:sigDigits});
};

const state = {
  identityMode: "cas",
  chemical: null,
  project: null,
  projects: [],
  use: "pharmaceutical",
  release: "wastewater",
  tier: 2,
  results: null,
  plans: {},
  regulatory: null,
  running: false,
  veterinaryProfiles: [],
  veterinaryPhaseI: null,
  envirodesign: null,
  pearl: null,
  pearlTimer: null,
  toxswa: null,
  toxswaManifest: null,
  focusScenarios: [],
  modelSystem: "EU",
  evidenceCandidates: [],
  evidenceSearch: null,
  oecdPharmaRegistry: null,
  identityCandidate: null,
  profile: null,
  profileReadiness: null,
  profileDraftProvenance: {},
  transformationPathway: null,
  usExposureManifest: null,
  usExposureScenarios: [],
  usExposureResult: null,
  assessmentPlan: null,
  externalWorkflow: null,
  assessmentStage: null,
  flowGroup: null,
};



const REGION_SETS = {
  EU_US: ["EU","US"],
  EU: ["EU"],
  UK: ["UK"],
  CH: ["CH"],
  US: ["US"],
  US_CA: ["US","CA"],
  AU_NZ: ["AU","NZ"],
  JP_CN_KR: ["JP","CN","KR"],
  BR_MX: ["BR","MX"],
  CA: ["CA"],
  AU: ["AU"],
  NZ: ["NZ"],
  JP: ["JP"],
  CN: ["CN"],
  KR: ["KR"],
  IN: ["IN"],
  NO: ["NO"],
  AE: ["AE"],
  SA: ["SA"],
  BR: ["BR"],
  MX: ["MX"],
  SG: ["SG"],
  TW: ["TW"],
  ZA: ["ZA"],
  GLOBAL: ["EU","UK","CH","US","CA","AU","NZ","JP","CN","KR","TW","IN","SG","MY","TH","ID","PH","VN","BR","MX","CO","CL","PE","ZA","NG","KE","GH","MA","EG","SA","AE","IL","TR","EAEU","ANDEAN","GCC","CILSS","CEMAC"],
};
const REGION_LABELS = {
  EU_US:"EU + US", EU:"European Union", UK:"United Kingdom", CH:"Switzerland", US:"United States", US_CA:"United States + Canada",
  AU_NZ:"Australia + New Zealand", JP_CN_KR:"Japan + China + South Korea",
  BR_MX:"Brazil + Mexico", CA:"Canada", AU:"Australia", NZ:"New Zealand",
  JP:"Japan", CN:"China", KR:"South Korea", IN:"India", GLOBAL:"Global navigator",
  NO:"Norway", AE:"United Arab Emirates", SA:"Saudi Arabia", BR:"Brazil", MX:"Mexico",
  SG:"Singapore", TW:"Taiwan", ZA:"South Africa",
};
const MODEL_SYSTEM_JURISDICTIONS = {
  // Kept as "EU + UK + Switzerland" deliberately, even though UK and Switzerland now have their own tab: this is
  // the jurisdiction label every EU-tab project was saved with before that split (build_assessment_plan's
  // jurisdiction was always "EU" for the whole combined tab). Changing it would silently stop matching existing
  // saved projects and demo lookups (see confirmIdentityCandidate/loadCarbamazepineDemo, which look a project up
  // by exact jurisdiction string).
  EU: "EU + UK + Switzerland",
  UK: "United Kingdom",
  CH: "Switzerland",
  US: "United States",
  CA: "Canada",
  AU: "Australia",
  NZ: "New Zealand",
  JP: "Japan",
  CN: "China",
  KR: "South Korea",
  IN: "India",
  NO: "Norway",
  AE: "United Arab Emirates",
  SA: "Saudi Arabia",
  BR: "Brazil",
  MX: "Mexico",
  SG: "Singapore",
  TW: "Taiwan",
  ZA: "South Africa",
};
// Regions that share FateIntel's native FOCUS/water-sediment refinement screens (workflow_registry.py's
// refinement:"eu"). Only the regulatory-programme text differs per region within this set. "NO" (Norway) was
// added 2026-09-23 -- confirmed, not assumed: Mattilsynet mandates FOCUS MACRO 5.5.4 and its own surface-water
// scenario selection is drawn from FOCUS's own standard set (see registry._regulatory_programme's "NO" branch).
const FOCUS_REGIONS = new Set(["EU", "UK", "CH", "NO"]);
function regionName(system = state.modelSystem) {
  return MODEL_SYSTEM_JURISDICTIONS[system] || system;
}

function activeJurisdictionLabel() {
  return MODEL_SYSTEM_JURISDICTIONS[state.modelSystem];
}

function projectModelSystem(project) {
  const jurisdiction = String(project?.jurisdiction || "").toLowerCase();
  if (jurisdiction.includes("canada")) return "CA";
  if (jurisdiction.includes("australia")) return "AU";
  if (jurisdiction.includes("new zealand")) return "NZ";
  if (jurisdiction.includes("japan")) return "JP";
  if (jurisdiction.includes("china")) return "CN";
  if (jurisdiction.includes("south korea") || jurisdiction.includes("korea")) return "KR";
  if (jurisdiction.includes("india")) return "IN";
  if (jurisdiction.includes("norway")) return "NO";
  if (jurisdiction.includes("united arab emirates")) return "AE";
  if (jurisdiction.includes("saudi arabia")) return "SA";
  if (jurisdiction.includes("brazil")) return "BR";
  if (jurisdiction.includes("mexico")) return "MX";
  if (jurisdiction.includes("singapore")) return "SG";
  if (jurisdiction.includes("taiwan")) return "TW";
  if (jurisdiction.includes("south africa")) return "ZA";
  if (jurisdiction.includes("united states") || /(^|\W)us(\W|$)/.test(jurisdiction)) return "US";
  // The combined legacy phrasing is checked before the individual UK/Switzerland checks below, or it would
  // wrongly match "uk" or "switzerland" (the combined string contains both of those too).
  if (jurisdiction.includes("eu + uk")) return "EU";
  if (jurisdiction.includes("united kingdom") || jurisdiction === "uk") return "UK";
  if (jurisdiction.includes("switzerland")) return "CH";
  if (jurisdiction.includes("eu") || jurisdiction.includes("europe")) return "EU";
  return null;
}

function projectMatchesModelSystem(project = state.project) {
  const projectSystem = projectModelSystem(project);
  return !project || projectSystem === null || projectSystem === state.modelSystem;
}

function projectJurisdictionMessage() {
  return `The selected project is labelled ${state.project?.jurisdiction || "with an unspecified jurisdiction"}. Select or confirm a ${activeJurisdictionLabel()} project before preparing or running this pathway.`;
}
const USE_PRODUCT_CLASS = {
  pharmaceutical:"human_pharmaceutical", veterinary:"veterinary_pharmaceutical", industrial:"industrial_organic",
  // AssessmentPlanCreate expects a chemical/contaminant group, not an exposure
  // setting.  "workplace" was never a valid registry group and caused the
  // laboratory pathway to fail validation before a plan could be rendered.
  laboratory:"industrial_organic", agriculture:"pesticide", consumer:"mixture_formulation",
  waste:"emerging_contaminant",
};
const RELEASE_SCENARIO = {
  wastewater:"municipal_wastewater", surface_water:"surface_water_discharge",
  soil:"soil_incorporation", biosolids:"biosolids_to_soil",
  irrigation:"wastewater_irrigation", manufacturing:"industrial_effluent",
  household_use:"household_use", product_disposal:"product_disposal", agricultural_spray:"agricultural_spray",
};

const LIVE_RELEASES = new Set(["wastewater","biosolids","irrigation"]);
// These exposure scenarios exist in both jurisdictions.  They do not enter the
// three-pathway native guided calculator; instead the selected jurisdiction is
// passed to /api/assessment-plan and the applicable native/managed/external
// workflows are shown without fabricating a model result.
const PROGRAMME_ROUTED_RELEASES = new Set([
  "surface_water", "soil", "manufacturing",
  "household_use", "product_disposal", "agricultural_spray",
]);
const SCENARIO_JURISDICTION_COPY = {
  household_use: {
    EU: ["Household / consumer use", "Consumer lifecycle release → EU REACH exposure plan"],
    US: ["Household / consumer use", "Product/article exposure → CEM / E-FAST"],
  },
  product_disposal: {
    EU: ["Product disposal", "Waste stage → EU lifecycle release and fate plan"],
    US: ["Product disposal", "Landfill / incineration / treatment → E-FAST"],
  },
  agricultural_spray: {
    EU: ["Agricultural spray", "Plant-protection use → FOCUS groundwater and surface water"],
    US: ["Agricultural spray", "Pesticide use → PWC / PRZM"],
  },
  manufacturing: {
    EU: ["Manufacturing / processing", "Industrial release → EU REACH exposure plan"],
    US: ["Manufacturing / processing", "Industrial release + worker exposure → native screen / ChemSTEER"],
  },
};
const STRUCTURE_REGION_META = {
  benzene_like_aromatic_ring:{role:"persistence-associated",tone:"persistent",title:"Benzene-like aromatic ring",explanation:"An aromatic six-membered carbon ring is present. Aromaticity can be associated with slower biodegradation, but the exact fitted BIOWIN aromatic term is only counted when its own SMARTS pattern matches."},
  polycyclic_aromatic_scaffold:{role:"persistence-associated",tone:"persistent",title:"Multi-ring aromatic scaffold",explanation:"Multiple aromatic rings form a rigid scaffold. Treat this as a persistence hypothesis until matched analogues or transformation products support it."},
  aromatic_halogen:{role:"persistence-associated",tone:"persistent",title:"Aromatic halogen",explanation:"A halogen attached to an aromatic carbon is present. The supplied BIOWIN reconstruction contains attachment-specific halogen terms; exact fitted matches are reported separately."},
  halogenated_structure:{role:"persistence-associated",tone:"persistent",title:"Halogenated region",explanation:"A halogen is present. Attachment context determines whether it contributes to the fitted model."},
  ester:{role:"transformation-sensitive",tone:"labile",title:"Ester linkage",explanation:"An ester is a plausible hydrolysis or enzymatic-cleavage handle. Rate and products remain matrix- and condition-dependent."},
  hydrolysable_carbamate:{role:"transformation-sensitive",tone:"labile",title:"Carbamate linkage",explanation:"A carbamate can provide a hydrolytic or enzymatic transformation route, but environmental rate cannot be inferred from structure alone."},
  alcohol:{role:"transformation-sensitive",tone:"labile",title:"Alcohol group",explanation:"An alcohol may provide an oxidation or conjugation handle. This is a transformation hypothesis, not an assumed loss rate."},
  aldehyde:{role:"transformation-sensitive",tone:"labile",title:"Aldehyde group",explanation:"An aldehyde can be susceptible to oxidation or reduction. Transformation products should be tracked."},
  aliphatic_alkene:{role:"transformation-sensitive",tone:"labile",title:"Non-aromatic C=C bond",explanation:"A non-aromatic double bond can be a plausible oxidative transformation site; actual environmental kinetics require evidence."},
  beta_lactam:{role:"transformation-sensitive",tone:"labile",title:"β-lactam ring",explanation:"The strained cyclic amide is a ring-opening alert. Parent disappearance and ultimate mineralisation must remain separate endpoints."},
  carboxamide:{role:"functional region",tone:"neutral",title:"Carboxamide",explanation:"A carboxamide is present. It may be functionally important; this screen does not label it persistent or labile unless a fitted term or pathway supports that conclusion."},
  ether:{role:"functional region",tone:"neutral",title:"Ether linkage",explanation:"An ether is present. Oxidative cleavage is possible in some systems, but no generic environmental rate is assumed."},
  tertiary_amine:{role:"persistence / sorption review",tone:"persistent",title:"Tertiary amine",explanation:"A tertiary amine can influence biodegradation, ionisation and sorption. Exact BIOWIN contribution and pKa-dependent fate should be considered together."},
  nitro:{role:"structural alert",tone:"neutral",title:"Nitro group",explanation:"A nitro group is present. Redox conditions can strongly influence transformation."},
  nitrile:{role:"structural alert",tone:"neutral",title:"Nitrile",explanation:"A nitrile is present. Transformation depends on biological and chemical context."},
  azo:{role:"transformation-sensitive",tone:"labile",title:"Azo linkage",explanation:"An azo bond may undergo reductive cleavage under suitable conditions; aerobic and anaerobic behaviour should be separated."},
  sulfonamide:{role:"structural alert",tone:"neutral",title:"Sulfonamide",explanation:"A sulfonamide is present. Persistence varies widely with substitution and matrix."},
  quaternary_carbon:{role:"persistence-associated",tone:"persistent",title:"Highly substituted carbon",explanation:"A fully substituted carbon centre can reduce accessibility at nearby transformation sites; exact model evidence is reported separately."},
};

function selectedJurisdictions() {
  return REGION_SETS[$("regions")?.value || "EU"] || ["EU"];
}
function regulatoryProductClass() {
  if (state.release === "agricultural_spray") return "pesticide";
  // The chemical group chosen in the assessment setup wins over the group implied by the use card.
  if (state.flowGroup) return state.flowGroup;
  return USE_PRODUCT_CLASS[state.use] || "cross_cutting";
}
function isUSIndustrialSelection(release = state.release) {
  return state.modelSystem === "US" && release === "manufacturing" && state.use === "industrial";
}
function waterSedimentWorkbenchEligible() {
  const group = regulatoryProductClass();
  const eligibleGroup = !new Set(["pfas_persistent_mobile", "metal_inorganic", "polymer_microplastic", "nanomaterial", "uvcb_complex_substance", "mixture_formulation", "radionuclide", "contaminated_mixture"]).has(group);
  return FOCUS_REGIONS.has(state.modelSystem) && currentTier() >= 2 && eligibleGroup && state.use !== "veterinary" &&
    new Set(["wastewater", "surface_water", "manufacturing", "agricultural_spray"]).has(state.release);
}
function officialFocusToxswaEligible() {
  return waterSedimentWorkbenchEligible() && regulatoryProductClass() === "pesticide" && currentTier() >= 3 &&
    new Set(["agricultural_spray", "soil"]).has(state.release);
}
function updateAdvancedModelVisibility() {
  const processEligible = waterSedimentWorkbenchEligible();
  const officialEligible = officialFocusToxswaEligible();
  $("toxswa-surface-water")?.classList.toggle("hidden", !processEligible);
  $$('[data-water-sediment-nav]').forEach(node => node.classList.toggle("hidden", !processEligible));
  $$('[data-focus-official]').forEach(node => node.classList.toggle("hidden", !officialEligible));
  $("continue-toxswa")?.classList.toggle("hidden", !processEligible);
}
function regulatoryScenario() {
  return RELEASE_SCENARIO[state.release] || "municipal_wastewater";
}

async function api(url, options = {}) {
  const method = String(options.method || "GET").toUpperCase();
  const mutation = !["GET", "HEAD", "OPTIONS"].includes(method);
  const persistedRoutes = [
    "/api/projects", "/api/model-runs/", "/api/evidence", "/api/selections/",
    "/api/model-workflows", "/api/chemicals/from-resolved-identity",
    "/api/envirodesign/analyse", "/api/transformation-pathways/predict", "/api/toxswa/import-official-summary",
  ];
  const tracksSave = mutation && persistedRoutes.some(route => url === route || url.startsWith(route));
  if (tracksSave) setSaveState("saving", "Saving…");
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    if (tracksSave) setSaveState("error", "Save failed");
    throw error;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (tracksSave) setSaveState("error", "Save failed");
    const rawDetail = data.detail ?? data.message;
    const detail = Array.isArray(rawDetail)
      ? rawDetail.map(item => {
          const location = Array.isArray(item?.loc) ? item.loc.filter(part => part !== "body").join(" ") : "";
          return `${location ? `${location}: ` : ""}${item?.msg || JSON.stringify(item)}`;
        }).join("; ")
      : (rawDetail && typeof rawDetail === "object" ? (rawDetail.message || JSON.stringify(rawDetail)) : rawDetail);
    const error = new Error(detail || `Request failed: ${response.status}`);
    error.status = response.status;
    error.requestId = response.headers.get("X-Request-ID");
    error.endpoint = url;
    throw error;
  }
  if (tracksSave) setSaveState("saved", "Saved locally");
  return data;
}

function setSaveState(kind, message) {
  const node = $("save-state");
  if (!node) return;
  const icons = {ready:"•", saving:"…", saved:"✓", error:"!"};
  node.className = `save-state ${kind}`;
  node.innerHTML = `<span>${icons[kind] || "•"}</span> ${message}`;
}

function toast(message, timeout = 3400) {
  const node = $("toast");
  node.textContent = message;
  node.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.add("hidden"), timeout);
}

function updateSummaries() {
  const chemicalName = state.chemical?.preferred_name || "No chemical selected";
  const amount = `${$("amount-value").value || 0} ${$("amount-unit").value}`;
  const useNames = {pharmaceutical:"Human pharmaceutical",veterinary:"Veterinary medicine",industrial:"Industrial use",laboratory:"Laboratory use",agriculture:"Agricultural use",consumer:"Consumer product",waste:"Waste / disposal"};
  const releaseNames = {wastewater:"Municipal wastewater",surface_water:"Direct to surface water",soil:"Direct to soil",biosolids:"Biosolids to soil",irrigation:"Wastewater irrigation",manufacturing:"Manufacturing catchment",household_use:"Household / consumer use",product_disposal:"Product disposal",agricultural_spray:"Agricultural spray (pesticide)"};
  $("use-summary").textContent = `${useNames[state.use]} · ${amount}`;
  $("release-summary").textContent = releaseNames[state.release];
  $("tier-summary").textContent = `Tier ${state.tier} · ${["","Worst case","Standard","Refined","Monitoring-informed"][state.tier]}`;
  const region = REGION_LABELS[$("regions").value] || $("regions").value;
  $("run-description").textContent = `${chemicalName} · ${releaseNames[state.release].toLowerCase()} · ${region} · Tier ${state.tier}`;
}

function setupFlowCards() {
  $$(".flow-card-head").forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".flow-card");
      card.classList.toggle("open");
      button.setAttribute("aria-expanded", card.classList.contains("open") ? "true" : "false");
    });
  });
}

function setupIdentity() {
  const placeholders = {
    cas: ["CAS or chemical name", "298-46-4"],
    smiles: ["SMILES", "NC(=O)N1c2ccccc2C=Cc2ccccc21"],
    barcode: ["Barcode / GTIN", "Scan or enter a product barcode"],
    iupac: ["IUPAC or preferred name", "Carbamazepine"],
    product: ["Product name or SDS title", "Tegretol / product formulation"],
  };
  $$("#identity-modes button").forEach((button) => {
    button.addEventListener("click", () => {
      $$("#identity-modes button").forEach((x) => x.classList.remove("active"));
      button.classList.add("active");
      state.identityMode = button.dataset.mode;
      $("identity-input-label").textContent = placeholders[state.identityMode][0];
      $("identity-input").placeholder = placeholders[state.identityMode][1];
      $("identity-input").value = state.identityMode === "smiles" && state.chemical?.smiles ? state.chemical.smiles : "";
    });
  });
  $("resolve-identity").addEventListener("click", resolveIdentity);
  $("confirm-identity")?.addEventListener("click", confirmIdentityCandidate);
  $("cancel-identity")?.addEventListener("click", clearIdentityCandidate);
  $("save-profile")?.addEventListener("click", saveAssessmentProfile);
  $("profile-ionisation")?.addEventListener("change", updateProfilePkaLabel);
  $("identity-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); resolveIdentity(); }
  });
}

async function resolveIdentity() {
  const value = $("identity-input").value.trim();
  if (!value) { toast("Enter a chemical name, CAS number or structure first."); return; }
  if (["barcode","product"].includes(state.identityMode)) {
    toast("Product and barcode resolution require formulation/SDS confirmation. Use the active substance name, CAS or SMILES for this assessment.", 6000);
    return;
  }
  const button = $("resolve-identity");
  button.disabled = true; button.textContent = "Resolving…";
  try {
    const result = await api("/api/identities/resolve", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({query:value,query_mode:state.identityMode}),
    });
    state.identityCandidate = result.candidate;
    const candidate = result.candidate;
    $("identity-candidate-name").textContent = candidate.preferred_name;
    $("identity-candidate-detail").textContent = `CAS ${candidate.cas_number || "not resolved"} · ${candidate.molecular_formula} · ${fmt(candidate.molecular_weight_g_mol,7)} g/mol · ${candidate.source_record_id}`;
    $("identity-candidate-warning").textContent = (candidate.warnings || []).join(" ");
    $("identity-candidate").classList.remove("hidden");
    toast("Identity candidate resolved. Confirm the parent/salt form before it is stored.", 5200);
  } catch (error) {
    clearIdentityCandidate();
    toast(`Identity resolution stopped: ${error.message}`, 6500);
  } finally { button.disabled = false; button.textContent = "Resolve"; }
}

function clearIdentityCandidate() {
  state.identityCandidate = null;
  $("identity-candidate")?.classList.add("hidden");
}

async function confirmIdentityCandidate() {
  const candidate = state.identityCandidate;
  if (!candidate) return;
  const name = candidate.preferred_name;
  try {
    const projects = await api("/api/projects");
    const jurisdiction = activeJurisdictionLabel();
    const projectName = `${name} — ${state.modelSystem} guided fate assessment`;
    const legacyProjectName = `${name} guided fate assessment`;
    let project = projects.find(row =>
      row.jurisdiction === jurisdiction &&
      [projectName, legacyProjectName].some(candidateName => row.name.toLowerCase() === candidateName.toLowerCase())
    );
    if (!project) {
      project = await api("/api/projects", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
        name:projectName,
        jurisdiction,
        purpose:`${state.modelSystem} guided environmental fate assessment for ${name}`,
      })});
    }
    const result = await api("/api/chemicals/from-resolved-identity", {
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({project_id:project.id,candidate,user_confirmed:true}),
    });
    state.project = project;
    state.projects = [project, ...projects.filter(row => row.id !== project.id)];
    state.chemical = {...result.chemical, structure_image_url:candidate.structure_image_url || null};
    state.profile = result.profile;
    state.results = null;
    state.profileDraftProvenance = candidate.xlogp_candidate == null ? {} : {identity_xlogp_candidate:{value:candidate.xlogp_candidate,source:candidate.source_record_id,status:"unselected_candidate"}};
    clearIdentityCandidate();
    renderProjectSwitcher();
    renderChemicalIdentity();
    renderAssessmentProfile(state.profile);
    setWorkspaceUrl();
    if (state.profile?.log_kow == null && candidate.xlogp_candidate != null) {
      $("profile-logkow").value = candidate.xlogp_candidate;
      $("profile-reviewed").checked = false;
      $("profile-source").value = `PHYS.LOGKOW: PubChem ${candidate.source_record_id} computed XLogP candidate; original record review required.`;
      $("profile-status").textContent = "Draft · PubChem XLogP candidate copied for review";
    }
    await refreshGuidedReadiness();
    toast(`${name} is now the confirmed assessment chemical. Review and save its chemical-specific calculation profile before running.`, 6500);
  } catch (error) { toast(`Identity confirmation stopped: ${error.message}`, 6500); }
}

function renderChemicalIdentity() {
  const chemical = state.chemical;
  if (!chemical) { renderNeutralWorkspace(); return; }
  const name = chemical.preferred_name;
  setProfileControlsEnabled(true);
  $("identity-summary").textContent = `${name} · CAS ${chemical.cas_number || "not assigned"}`;
  $("identity-confidence").textContent = "Confirmed identity";
  $("identity-name").textContent = name;
  $("identity-cas").textContent = chemical.cas_number || "Not assigned";
  $("identity-formula").textContent = chemical.molecular_formula || "—";
  $("identity-mw").textContent = `${fmt(chemical.molecular_weight_g_mol,8)} g/mol`;
  $("identity-form-badge").textContent = `${chemical.substance_form || "parent"} substance`;
  const image = $("identity-structure");
  if (image) {
    image.alt = `Two-dimensional structure of ${name}`;
    image.src = chemical.cas_number === "298-46-4" ? "/static/carbamazepine.svg" : (chemical.structure_image_url || "/static/chemical-placeholder.svg");
    image.onerror = () => { image.onerror = null; image.src = "/static/chemical-placeholder.svg"; };
  }
  $("evidence-chemical").value = name;
  $("evidence-cas").value = chemical.cas_number || "";
  $("identity-input").value = chemical.cas_number || name;
  if ($("results-title")) $("results-title").textContent = `Here is what happens to ${name}.`;
  if ($("assessment-story-title")) $("assessment-story-title").textContent = `What happens to ${name}?`;
  if ($("ai-summary") && !state.results) $("ai-summary").textContent = `${name} is the confirmed assessment substance. Complete its reviewed calculation profile and release scenario before running.`;
  if ($("use-ai-copy") && state.use !== "veterinary") $("use-ai-copy").innerHTML = `<strong>Grounded suggestion:</strong> Confirm whether ${escapeHtml(name)} is being assessed as a human pharmaceutical; the chemical identity alone does not prove the use or release route.`;
  if ($("pearl-mw")) $("pearl-mw").value = chemical.molecular_weight_g_mol || "";
  $("step-identity")?.classList.add("complete");
  const status = $("step-identity")?.querySelector(".step-status");
  if (status) status.textContent = "✓";
  updateSummaries();
  refreshIdentificationProfile();
}

function setProfileControlsEnabled(enabled) {
  $$('#chemical-profile-panel input, #chemical-profile-panel select, #chemical-profile-panel textarea, #chemical-profile-panel button').forEach(node => {
    node.disabled = !enabled;
  });
}

function renderNeutralWorkspace() {
  state.project = null;
  state.chemical = null;
  state.profile = null;
  state.profileReadiness = null;
  state.results = null;
  $("identity-summary").textContent = "No chemical selected";
  $("identity-confidence").textContent = "Awaiting confirmation";
  $("identity-name").textContent = "No chemical selected";
  $("identity-cas").textContent = "—";
  $("identity-formula").textContent = "—";
  $("identity-mw").textContent = "—";
  $("identity-ionisation-badge").textContent = "Not assessed";
  $("identity-form-badge").textContent = "Confirm parent or salt form";
  const image = $("identity-structure");
  if (image) {
    image.alt = "Chemical structure appears after identity confirmation";
    image.src = "/static/chemical-placeholder.svg";
  }
  $("step-identity")?.classList.remove("complete");
  const status = $("step-identity")?.querySelector(".step-status");
  if (status) status.textContent = "1";
  renderAssessmentProfile(null);
  setProfileControlsEnabled(false);
  renderProjectSwitcher();
  updateSummaries();
  resetIdentificationPanels();
}

function resetIdentificationPanels() {
  if (!$("identification-status")) return;
  $("identification-status").innerHTML = "<strong>Select a chemical to load its identification profile.</strong><small>Looks up the selected chemical's stored InChIKey against NORMAN SusDat, NORMAN EAWAGTPS and MassBank Europe.</small>";
  ["identification-ionisation","identification-product-ions","identification-transformation-products","identification-oasis-soil-dt50","identification-nite-mineralization"].forEach(id => {
    if ($(id)) $(id).innerHTML = "<p>No chemical selected.</p>";
  });
}

async function refreshIdentificationProfile() {
  if (!$("identification-status")) return;
  const chemical = state.chemical;
  if (!chemical) { resetIdentificationPanels(); return; }
  if (!chemical.inchikey) {
    $("identification-status").innerHTML = `<strong>No InChIKey on record.</strong><small>${escapeHtml(chemical.preferred_name)} has no stored InChIKey, so an identification profile cannot be looked up.</small>`;
    ["identification-ionisation","identification-product-ions","identification-transformation-products","identification-oasis-soil-dt50","identification-nite-mineralization"].forEach(id => {
      if ($(id)) $(id).innerHTML = "<p>Not available.</p>";
    });
    return;
  }
  await loadIdentificationProfile(`/api/chemicals/${chemical.id}/identification`, chemical.preferred_name, chemical.inchikey);
}

async function lookupIdentificationByInchikey(inchikey, name) {
  await loadIdentificationProfile(`/api/analytical-identification/${encodeURIComponent(inchikey)}`, name || inchikey, inchikey);
}

async function loadIdentificationProfile(url, displayName, inchikey) {
  $("identification-status").innerHTML = `<strong>Looking up ${escapeHtml(displayName)}…</strong><small>Querying NORMAN SusDat, NORMAN EAWAGTPS and MassBank Europe.</small>`;
  ["identification-ionisation","identification-product-ions","identification-transformation-products","identification-oasis-soil-dt50","identification-nite-mineralization"].forEach(id => {
    if ($(id)) $(id).innerHTML = "<p>Loading…</p>";
  });
  try {
    const profile = await api(url);
    renderIdentificationProfile(profile, displayName);
  } catch (error) {
    $("identification-status").innerHTML = `<strong>Identification lookup failed.</strong><small>${escapeHtml(error.message)}</small>`;
    ["identification-ionisation","identification-product-ions","identification-transformation-products","identification-oasis-soil-dt50","identification-nite-mineralization"].forEach(id => {
      if ($(id)) $(id).innerHTML = "<p>Lookup failed.</p>";
    });
  }
}

function renderIdentificationProfile(profile, displayName) {
  state.identificationProfile = profile;
  const generated = profile.generated_at ? new Date(profile.generated_at).toLocaleString() : "";
  $("identification-status").innerHTML = `<strong>${escapeHtml(displayName)} · ${escapeHtml(profile.inchikey || "")}</strong><small>Generated ${escapeHtml(generated)}</small>`;

  const ip = profile.ionisation_and_platform || {};
  $("identification-ionisation").innerHTML = ip.found ? `
      <p><strong>Predicted ESI mode</strong> ${escapeHtml(ip.predicted_esi_mode || "—")} <em>(+ESI p=${fmt(ip.probability_positive_esi,2)}, −ESI p=${fmt(ip.probability_negative_esi,2)})</em></p>
      <p><strong>Precursor ions</strong> [M+H]⁺ ${fmt(ip.precursor_m_plus_h_da,7)} · [M−H]⁻ ${fmt(ip.precursor_m_minus_h_da,7)}</p>
      <p><strong>Platform recommendation</strong> ${escapeHtml(ip.preferable_platform || "—")} <em>(${escapeHtml(ip.predicted_chromatography || "—")}: RPLC p=${fmt(ip.probability_rplc,2)}, GC p=${fmt(ip.probability_gc,2)})</em></p>
      <p class="identification-source">Source: <a href="${escapeHtml(ip.source_url || "#")}" rel="noopener" target="_blank">${escapeHtml(ip.citation || "NORMAN SusDat")}</a> · model-predicted, not a confirmed method.</p>`
    : `<p>${escapeHtml(ip.message || "Not in the NORMAN SusDat reference set.")}</p>`;

  const pi = profile.known_product_ions || {};
  if (pi.found && Array.isArray(pi.spectra) && pi.spectra.length) {
    const extra = (pi.match_count || 0) > (pi.returned_count || pi.spectra.length)
      ? `<p><em>${pi.match_count - pi.returned_count} additional MassBank spectra not shown.</em></p>` : "";
    $("identification-product-ions").innerHTML = pi.spectra.map(s => `
      <div class="identification-spectrum-card">
        <p><strong>${escapeHtml(s.ion_mode || "—")}</strong> · ${escapeHtml(s.precursor_type || "")} m/z ${fmt(s.precursor_mz,7)} · ${s.product_ion_count ?? 0} product ions</p>
        <p>${escapeHtml(s.instrument_type || "")}${s.instrument ? ` · ${escapeHtml(s.instrument)}` : ""}${s.collision_energy ? ` · CE ${escapeHtml(s.collision_energy)}` : ""}</p>
        ${s.retention_time_min != null ? `<p>RT ${fmt(s.retention_time_min,4)} min${s.column ? ` on ${escapeHtml(s.column)}` : ""}</p>` : ""}
        ${Array.isArray(s.mobile_phase_solvents) && s.mobile_phase_solvents.length ? `<p>Mobile phase: ${s.mobile_phase_solvents.map(v => escapeHtml(v)).join("; ")}</p>` : ""}
        ${Array.isArray(s.product_ions) && s.product_ions.length ? `<p>Top product ions (m/z): ${s.product_ions.slice(0,8).map(ion => fmt(ion.mz,6)).join(", ")}</p>` : ""}
        <p class="identification-source">Source: <a href="${escapeHtml(s.source_url || "#")}" rel="noopener" target="_blank">MassBank ${escapeHtml(s.accession || "")}</a> · real, measured spectrum.</p>
      </div>`).join("") + extra;
  } else {
    $("identification-product-ions").innerHTML = `<p>${escapeHtml(pi.message || "No reference spectrum found in MassBank Europe.")}</p>`;
  }

  const tp = profile.known_transformation_products || {};
  if (tp.found && Array.isArray(tp.known_transformation_products) && tp.known_transformation_products.length) {
    $("identification-transformation-products").innerHTML = tp.known_transformation_products.map((row, index) => `
      <div class="identification-tp-card">
        <p><strong>${escapeHtml(row.tp_name || "Unnamed transformation product")}</strong> <em>${escapeHtml(row.transformation_type || "")}</em></p>
        <p>${escapeHtml(row.tp_formula || "—")} · mass diff ${fmt(row.mass_diff_da,4)} Da (${escapeHtml(row.formula_diff || "—")}) · ionisation ${escapeHtml(row.ionization || "—")}</p>
        <p class="identification-source">Source: <a href="${escapeHtml(row.source_url || "#")}" rel="noopener" target="_blank">${escapeHtml(row.source_name || "curated reference")} ${row.source_record_id ? "record " + escapeHtml(String(row.source_record_id)).slice(0, 60) : ""}</a> · curated pair, not predicted.${row.quantity_percent != null ? ` Reported quantity: ${fmt(row.quantity_percent, 3)}%.` : ""}</p>
        ${row.tp_inchikey ? `<button class="text-button" data-identification-index="${index}" type="button">View this TP's own identification profile</button>` : ""}
      </div>`).join("");
    $$('#identification-transformation-products [data-identification-index]').forEach(button => {
      const row = tp.known_transformation_products[Number(button.dataset.identificationIndex)];
      button.addEventListener("click", () => lookupIdentificationByInchikey(row.tp_inchikey, row.tp_name));
    });
    $("identification-transformation-products").insertAdjacentHTML("beforeend", '<p><button class="ghost-button" id="identification-to-soil" type="button">Model these transformation products in soil</button></p>');
    $("identification-to-soil")?.addEventListener("click", () => tpLoadFromAssessment({ knownTps: true }));
  } else {
    $("identification-transformation-products").innerHTML = `<p>${escapeHtml(tp.message || "No known transformation products recorded.")}</p>`;
  }

  const soilDt50 = profile.oasis_soil_dt50 || {};
  if (soilDt50.found) {
    const rec = soilDt50.records[0];
    $("identification-oasis-soil-dt50").innerHTML = `<p><strong>${fmt(soilDt50.dt50_mean_days)} days</strong> (mean across ${soilDt50.n} record(s))</p>
      <p><small>${escapeHtml(rec.names || "")}${rec.names ? " · " : ""}CAS ${escapeHtml(rec.cas_number || "not reported")}</small></p>
      <p class="identification-source">Source: Biodegradation in soil OASIS (LMC Bourgas) · exact-structure match · licence unconfirmed, review before external use.</p>`;
  } else {
    $("identification-oasis-soil-dt50").innerHTML = `<p>${escapeHtml(soilDt50.reason || "No exact-structure match in this reference set.")}</p>`;
  }

  const mineralization = profile.nite_mineralization || {};
  if (mineralization.found) {
    const rec = mineralization.records[0];
    $("identification-nite-mineralization").innerHTML = `<p><strong>${fmt(mineralization.biodeg_percent_mean)}%</strong> of theoretical oxygen demand (mean across ${mineralization.n} record(s))${rec.duration_days != null ? ` over ${fmt(rec.duration_days)} d` : ""}</p>
      <p>${readyBiodegradabilityBadge(rec.readily_biodegradable)}</p>
      <p><small>${escapeHtml(rec.test_guideline || "")}</small></p>
      <p class="identification-source">Source: Biodegradation NITE (METI Japan) · a ready-biodegradability screening result, not a soil DT50 · licence unconfirmed.</p>`;
  } else {
    $("identification-nite-mineralization").innerHTML = `<p>${escapeHtml(mineralization.reason || "No exact-structure match in this reference set.")}</p>`;
  }
}

function nullableNumber(id) {
  const value = $(id)?.value?.trim();
  if (value === "" || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function updateProfilePkaLabel() {
  const ionisation = $("profile-ionisation")?.value || "";
  $("profile-pka-label").textContent = ionisation === "acid" ? "Acid pKa" : ionisation === "base" ? "Base pKa / conjugate-acid pKa" : "pKa (not used in neutral screen)";
  if ($("identity-ionisation-badge")) $("identity-ionisation-badge").textContent = ionisation
    ? `${ionisation[0].toUpperCase()}${ionisation.slice(1)} screen`
    : "Not assessed";
}

function renderAssessmentProfile(profile) {
  state.profile = profile;
  const set = (id, value) => { if ($(id)) $(id).value = value ?? ""; };
  set("profile-ionisation", profile?.ionisation_class || "");
  set("profile-logkow", profile?.log_kow);
  set("profile-pka", profile?.ionisation_class === "base" ? profile?.pkab : profile?.pkaa);
  set("profile-solubility", profile?.water_solubility_mg_l);
  set("profile-vapour", profile?.vapour_pressure_pa);
  set("profile-soil-dt50", profile?.soil_dt50_days);
  set("profile-wwtp-bio", profile?.wwtp_biodegradation_fraction);
  set("profile-wwtp-primary", profile?.wwtp_primary_sludge_fraction);
  set("profile-wwtp-secondary", profile?.wwtp_secondary_sludge_fraction);
  set("profile-wwtp-air", profile?.wwtp_volatilisation_fraction);
  set("profile-source", profile?.source_summary);
  if ($("profile-reviewed")) $("profile-reviewed").checked = Boolean(profile?.reviewer_confirmation);
  if ($("profile-status")) $("profile-status").textContent = !state.chemical
    ? "Confirm a chemical before entering properties"
    : profile?.profile_origin === "protected_carbamazepine_benchmark"
    ? "Protected Carbamazepine benchmark loaded"
    : profile?.review_status === "reviewed" ? "Reviewed chemical-specific profile" : "Draft · review required";
  if ($("pearl-solubility")) $("pearl-solubility").value = profile?.water_solubility_mg_l || "";
  updateProfilePkaLabel();
}

function buildAssessmentProfilePayload() {
  const ionisation = $("profile-ionisation").value;
  const pka = nullableNumber("profile-pka");
  return {
    ionisation_class:ionisation,
    log_kow:nullableNumber("profile-logkow"),
    pkaa:ionisation === "acid" ? pka : (ionisation === "neutral" ? state.profile?.pkaa ?? null : null),
    pkab:ionisation === "base" ? pka : null,
    water_solubility_mg_l:nullableNumber("profile-solubility"),
    vapour_pressure_pa:nullableNumber("profile-vapour"),
    soil_dt50_days:nullableNumber("profile-soil-dt50"),
    wwtp_biodegradation_fraction:nullableNumber("profile-wwtp-bio"),
    wwtp_primary_sludge_fraction:nullableNumber("profile-wwtp-primary"),
    wwtp_secondary_sludge_fraction:nullableNumber("profile-wwtp-secondary"),
    wwtp_volatilisation_fraction:nullableNumber("profile-wwtp-air"),
    source_summary:$("profile-source").value.trim() || null,
    provenance:{...(state.profile?.provenance || {}), ...state.profileDraftProvenance},
    reviewer_confirmation:Boolean($("profile-reviewed").checked),
  };
}

async function saveAssessmentProfile() {
  if (!state.project || !state.chemical) { toast("Confirm a chemical identity first."); return; }
  const button = $("save-profile");
  button.disabled = true; button.textContent = "Saving…";
  try {
    const profile = await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/assessment-profile`, {
      method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(buildAssessmentProfilePayload()),
    });
    state.profileDraftProvenance = {};
    renderAssessmentProfile(profile);
    await refreshGuidedReadiness();
    toast(profile.review_status === "reviewed" ? `${state.chemical.preferred_name} profile saved and reviewed.` : "Draft profile saved; it cannot drive calculations until review is confirmed.", 5200);
  } catch (error) { toast(`Profile save stopped: ${error.message}`, 6500); }
  finally { button.disabled = false; button.textContent = "Save reviewed profile"; }
}

async function refreshGuidedReadiness() {
  if (!state.project || !state.chemical) return null;
  try {
    const readiness = await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/guided-readiness?release=${encodeURIComponent(state.release)}`);
    state.profileReadiness = readiness;
    state.profile = readiness.profile;
    const box = $("profile-readiness");
    if (box) {
      box.classList.toggle("not-ready", !readiness.ready);
      box.innerHTML = readiness.ready
        ? `<strong>Ready for ${escapeHtml(state.chemical.preferred_name)}.</strong><small>${readiness.wwtp_model_mode === "supplied_workbook_9box_preset" ? "Protected Carbamazepine benchmark." : "Chemical-specific custom WWTP mass balance."}</small>`
        : `<strong>Calculation blocked pending review.</strong><small>Missing: ${escapeHtml(readiness.missing.join(", ").replaceAll("_", " "))}</small>`;
    }
    return readiness;
  } catch (error) { toast(`Readiness check stopped: ${error.message}`, 6000); return null; }
}

function activateModelSystem(modelSystem, {reset = true} = {}) {
  const previous = state.modelSystem;
  state.modelSystem = modelSystem;
  $$('[data-model-system]').forEach(node => {
    const active = node.dataset.modelSystem === state.modelSystem;
    node.classList.toggle('active', active);
    node.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  if ($('regions')) $('regions').value = state.modelSystem;
  if (reset && previous !== state.modelSystem) resetForJurisdictionSwitch();
  updateModelSystemUI();
  updateSummaries();
  refreshRegulatoryPathway();
  if (window.flowShell) window.flowShell.refresh();
  if (previous !== state.modelSystem && state.project && !projectMatchesModelSystem()) {
    toast(projectJurisdictionMessage(), 7600);
  }
}

function setupModelSystem() {
  $$('[data-model-system]').forEach(button => button.addEventListener('click', () => {
    if (state.running) {
      toast("The current calculation must finish before changing jurisdiction.", 5200);
      return;
    }
    activateModelSystem(button.dataset.modelSystem);
  }));
  activateModelSystem(state.modelSystem, {reset: false});
}

// Clears any results, advanced-refinement sync state and release selection that
// belonged to the jurisdiction being left, so switching EU<->US can never show a
// stale result (or a hidden-but-still-populated EU panel) as if it applied here.
function resetForJurisdictionSwitch() {
  state.results = null;
  state.assessmentPlan = null;
  state.externalWorkflow = null;
  state.pearl = null;
  state.toxswa = null;
  state.usExposureResult = null;
  $('results')?.classList.add('hidden');
  $('run-progress')?.classList.add('hidden');
  clearAssessmentFailure();
  if ($('toxswa-route-note')) $('toxswa-route-note').innerHTML = '';
  if ($('regulatory-plan')) $('regulatory-plan').innerHTML = '<p>Refreshing the jurisdiction-specific model plan…</p>';
  if ($('regulatory-requirements')) $('regulatory-requirements').innerHTML = '';
  if ($('regulatory-warnings')) $('regulatory-warnings').innerHTML = '';
  if ($('regulatory-workflows')) $('regulatory-workflows').innerHTML = '';
  if ($('fifra-application-method')) $('fifra-application-method').value = '';
  if ($('fifra-use-site')) $('fifra-use-site').value = 'field_crop';
  if ($('fifra-bee-attractive')) $('fifra-bee-attractive').checked = false;
  // Exposure scenarios are jurisdiction-neutral. Keep the scientist's selected
  // scenario and replace only its regulatory plan and result state.
  updateReleaseContext();
  updateCompartments();
  updateModels();
}

function updateScenarioJurisdictionCopy() {
  Object.entries(SCENARIO_JURISDICTION_COPY).forEach(([release, copy]) => {
    const card = document.querySelector(`#release-cards [data-release="${release}"]`);
    if (!card) return;
    const [title, description] = copy[state.modelSystem]
      || [copy.EU[0], `Exposure scenario → ${regionName()} regulatory route (see the plan below)`];
    if (card.querySelector('strong')) card.querySelector('strong').textContent = title;
    if (card.querySelector('small')) card.querySelector('small').textContent = description;
  });
}

function updateModelSystemUI() {
  // EU, UK and Switzerland share FateIntel's native FOCUS/water-sediment refinement screens (workflow_registry.py's
  // refinement:"eu"); only the regulatory-programme text differs per region (registry.py's _regulatory_programme).
  const eu = FOCUS_REGIONS.has(state.modelSystem);
  const us = state.modelSystem === 'US';
  $('pearl-groundwater')?.classList.toggle('hidden', !eu);
  $('us-models-placeholder')?.classList.toggle('hidden', !isUSIndustrialSelection());
  // Only regulatory tools are jurisdiction-gated. Exposure scenarios remain
  // visible in both systems and are re-planned against the selected registry.
  $$('[data-eu-only]').forEach(node => node.classList.toggle('hidden', !eu));
  $$('[data-us-only-model]').forEach(node => node.classList.toggle('hidden', !us));
  if ($('model-system-status')) $('model-system-status').innerHTML = eu
    ? `<strong>${escapeHtml(regionName())} modelling selected.</strong> Shared process screens remain labelled as native; chemicals-regulation and plant-protection scenarios route to ${escapeHtml(regionName())}-specific model plans and FOCUS refinements.`
    : us
      ? '<strong>US modelling selected.</strong> Shared process screens remain labelled as native; TSCA and FIFRA scenarios route to US-specific plans, while EPA tools remain managed external workflows.'
      : `<strong>${escapeHtml(regionName())} selected.</strong> Shared process screens remain labelled as native; scenarios route to this region's own regulatory route in the plan. No dedicated refinement screen is built for ${escapeHtml(regionName())} yet.`;
  if ($('next-stage-region')) $('next-stage-region').textContent = eu ? `${regionName()} models` : us ? 'US models' : regionName();
  if ($('next-stage-model')) $('next-stage-model').textContent = eu ? 'FOCUS PEARL' : us ? 'PWC / PRZM' : 'Regulatory route';
  if ($('next-stage-model-copy')) $('next-stage-model-copy').textContent = eu
    ? 'Use the selected soil PEC as the starting exposure for groundwater refinement.'
    : us
      ? 'Use the native US foundation to structure inputs, then execute and review the applicable external EPA model.'
      : `No dedicated refinement screen is built for ${regionName()}. Review the regulatory route plan for the applicable method.`;
  const soilReady = Boolean(currentScreeningSoilEndpoint());
  $('continue-pearl')?.classList.toggle('hidden', !(eu && soilReady));
  if ($('toxswa-nav-label')) $('toxswa-nav-label').textContent = 'Water–sediment';
  updateScenarioJurisdictionCopy();
  updateScenarioAvailability();
  updateReleaseContext();
  updateCompartments();
  updateModels();
  updateAdvancedModelVisibility();
}

function usNumber(id) {
  const raw = $(id)?.value;
  return raw === "" || raw === null || raw === undefined ? null : Number(raw);
}

async function loadUSExposureCatalogue() {
  const includeReference = Boolean($("us-include-draft")?.checked);
  const [manifest, scenarios] = await Promise.all([
    api("/api/us-exposure/manifest"),
    api(`/api/us-exposure/scenarios?include_reference_only=${includeReference ? "true" : "false"}`),
  ]);
  state.usExposureManifest = manifest;
  state.usExposureScenarios = scenarios;
  const select = $("us-exposure-scenario");
  if (select) {
    const current = select.value;
    select.innerHTML = '<option value="">Select a scenario basis…</option>' + scenarios.map(row =>
      `<option value="${escapeHtml(row.key)}">${row.publication_status === "draft" ? "DRAFT · " : ""}${escapeHtml(row.title)}</option>`
    ).join("");
    if (scenarios.some(row => row.key === current)) select.value = current;
  }
  const status = $("us-foundation-status");
  if (status) status.innerHTML = `
    <span><strong>Native transparent screen</strong><small>Mass balance + worker routes · not EPA-equivalent</small></span>
    <span><strong>${manifest.scenario_status_counts.published} published ESDs</strong><small>Enabled for normal selection</small></span>
    <span><strong>${manifest.scenario_status_counts.draft} draft records</strong><small>Reference-only · explicit opt-in</small></span>
    <span><strong>ChemSTEER · CEM · E-FAST</strong><small>External execution and reviewed import</small></span>`;
  await renderUsRoadmapStatus();
}

// Single honest status convention for the four external EPA contracts: the real
// per-instance ModelWorkflow lifecycle (prepared/output_imported/reviewed/...)
// rather than the static "external reviewed execution" catalog copy, which
// implied a workflow existed even when none had been prepared.
async function renderUsRoadmapStatus() {
  const grid = $('us-roadmap-grid');
  if (!grid || !state.project) return;
  let workflows = [];
  try { workflows = await api(`/api/projects/${state.project.id}/model-workflows`); } catch { return; }
  $$('#us-roadmap-grid [data-model-key]').forEach(article => {
    const key = article.dataset.modelKey;
    const latest = workflows.find(w => w.model_key === key && w.jurisdiction === 'US');
    const status = article.querySelector('.workflow-status');
    if (status) status.textContent = latest ? latest.status.replaceAll('_',' ') : 'not yet prepared';
  });
}

function updateUSWorkerFields() {
  const enabled = Boolean($("us-worker-enabled")?.checked);
  $("us-worker-fields")?.classList.toggle("muted-fields", !enabled);
  $$("#us-worker-fields input, #us-worker-fields select").forEach(node => { node.disabled = !enabled; });
  const modelled = $("us-worker-mode")?.value === "well_mixed_screen";
  $$(".us-modelled-field").forEach(node => node.classList.toggle("hidden", !modelled));
  $$(".us-measured-field").forEach(node => node.classList.toggle("hidden", modelled));
}

function updateUSGroundwaterFields() {
  const enabled = Boolean($("us-groundwater-enabled")?.checked);
  $("us-groundwater-fields")?.classList.toggle("muted-fields", !enabled);
  $$("#us-groundwater-fields input").forEach(node => { node.disabled = !enabled; });
}

function renderUSExposureResult(result) {
  const output = result.outputs;
  state.usExposureResult = output;
  const daily = output.releases.daily_kg;
  const worker = output.worker_exposure[0];
  const groundwater = output.groundwater_leaching || {status:"not_assessed"};
  $("us-result-summary").textContent = `Model run ${result.model_run_id} · ${output.review_status.replaceAll("_", " ")} · native research screen`;
  $("us-result-metrics").innerHTML = `
    <article><small>Air release</small><strong>${fmt(daily.air,5)}</strong><em>kg/day</em></article>
    <article><small>Water release</small><strong>${fmt(daily.water,5)}</strong><em>kg/day</em></article>
    <article><small>Managed waste</small><strong>${fmt(output.releases.managed_waste_transfer_kg_day,5)}</strong><em>kg/day · transfer</em></article>
    <article><small>Worker dose</small><strong>${worker ? fmt(worker.acute_absorbed_dose_mg_kg_shift,5) : "not assessed"}</strong><em>mg/kg-shift</em></article>
    <article><small>Groundwater screen</small><strong>${groundwater.status === "screened" ? fmt(groundwater.screened_groundwater_concentration_ug_l,5) : "not assessed"}</strong><em>µg/L · native screen</em></article>
    <article><small>Mass closure error</small><strong>${fmt(output.mass_balance.closure_error_kg_day,4)}</strong><em>kg/day</em></article>`;
  const missing = output.completeness.missing;
  $("us-completeness").innerHTML = missing.length
    ? `<p><strong>${output.completeness.complete_count}/${output.completeness.total_count} domains addressed.</strong></p><ul>${missing.map(row => `<li>${escapeHtml(row.label)}</li>`).join("")}</ul>`
    : "<p><strong>All catalogue domains addressed.</strong> Regulatory adequacy still requires expert review.</p>";
  $("us-warnings").innerHTML = `<ul>${output.warnings.map(row => `<li>${escapeHtml(row)}</li>`).join("")}</ul>`;
}

async function runUSExposure() {
  if (!isUSIndustrialSelection()) {
    toast("The industrial source-term screen is available only when US + Industrial + Manufacturing / processing are selected.", 7000);
    return;
  }
  if (!state.project?.id || !state.chemical?.id) {
    toast("Confirm and attach a chemical identity before running the US exposure screen.", 6500);
    return;
  }
  if (!projectMatchesModelSystem()) {
    toast(projectJurisdictionMessage(), 7600);
    return;
  }
  const scenarioKey = $("us-exposure-scenario")?.value;
  const scenario = state.usExposureScenarios.find(row => row.key === scenarioKey);
  const throughput = usNumber("us-throughput");
  const operatingDays = usNumber("us-operating-days");
  const loss = usNumber("us-loss-percent");
  const control = usNumber("us-control-percent") ?? 0;
  const air = usNumber("us-air-percent") ?? 0;
  const water = usNumber("us-water-percent") ?? 0;
  const soil = usNumber("us-soil-percent") ?? 0;
  const eventName = $("us-event-name")?.value.trim();
  if (!scenario || !(throughput > 0) || !(operatingDays > 0 && operatingDays <= 365) || !(loss > 0) || !eventName) {
    toast("Select a scenario and complete throughput, operating days, event name and event loss.", 6500);
    return;
  }
  if (Math.abs(air + water + soil - 100) > 1e-7) {
    toast("The post-control air, water and soil percentages must sum to 100%.", 6500);
    return;
  }
  const sourceReference = $("us-source-reference")?.value.trim();
  let groundwaterScreen = null;
  if ($("us-groundwater-enabled")?.checked) {
    groundwaterScreen = {
      soil_release_area_ha: usNumber("us-gw-area"),
      source_zone_depth_m: usNumber("us-gw-source-depth"),
      assessment_depth_m: usNumber("us-gw-depth"),
      soil_bulk_density_kg_m3: usNumber("us-gw-density"),
      volumetric_water_content: usNumber("us-gw-water"),
      annual_recharge_mm: usNumber("us-gw-recharge"),
      koc_l_kg: usNumber("us-gw-koc"),
      soil_organic_carbon_fraction: usNumber("us-gw-foc"),
      soil_dt50_days: usNumber("us-gw-dt50"),
      additional_attenuation_fraction: usNumber("us-gw-attenuation"),
      parameter_source: $("us-gw-source")?.value.trim(),
    };
    if (!(groundwaterScreen.soil_release_area_ha > 0) || !(groundwaterScreen.source_zone_depth_m > 0) ||
        !(groundwaterScreen.assessment_depth_m >= groundwaterScreen.source_zone_depth_m) ||
        !(groundwaterScreen.soil_bulk_density_kg_m3 > 0) || !(groundwaterScreen.volumetric_water_content > 0) ||
        !(groundwaterScreen.annual_recharge_mm > 0) || !(groundwaterScreen.koc_l_kg >= 0) ||
        !(groundwaterScreen.soil_organic_carbon_fraction > 0) || !(groundwaterScreen.soil_dt50_days > 0) ||
        !(groundwaterScreen.additional_attenuation_fraction >= 0 && groundwaterScreen.additional_attenuation_fraction <= 1) ||
        !groundwaterScreen.parameter_source) {
      toast("Complete the groundwater area, depths, soil, recharge, Koc, DT50, attenuation and source fields.", 7000);
      return;
    }
  }
  const workerTasks = [];
  if ($("us-worker-enabled")?.checked) {
    const mode = $("us-worker-mode").value;
    const task = {
      task_name: $("us-task-name").value.trim(),
      inhalation_mode: mode,
      task_duration_hours: usNumber("us-task-hours"),
      exposure_days_year: usNumber("us-worker-days"),
      body_weight_kg: usNumber("us-body-weight"),
      inhalation_rate_m3_hour: usNumber("us-inhalation-rate"),
      respirator_apf: usNumber("us-respirator-apf"),
      inhalation_absorption_fraction: 1,
      dermal_contact_mg_shift: usNumber("us-dermal-contact") ?? 0,
      glove_protection_factor: usNumber("us-glove-factor"),
      dermal_absorption_fraction: (usNumber("us-dermal-absorption") ?? 0) / 100,
      local_exhaust_control_fraction: 0,
      source_reference: sourceReference || null,
    };
    if (!task.task_name || !(task.task_duration_hours > 0) || !(task.exposure_days_year > 0) ||
        !(task.body_weight_kg > 0) || !(task.inhalation_rate_m3_hour > 0) ||
        !(task.respirator_apf >= 1) || !(task.glove_protection_factor >= 1)) {
      toast("Complete the enabled worker task, including duration, days, body weight, inhalation rate and PPE factors.", 6500);
      return;
    }
    if (mode === "measured_air") {
      task.measured_air_concentration_mg_m3 = usNumber("us-air-concentration");
      if (!(task.measured_air_concentration_mg_m3 >= 0)) {
        toast("Measured-air mode requires an air concentration.", 6500); return;
      }
    } else {
      task.chemical_handled_kg_per_shift = usNumber("us-handled-kg");
      task.airborne_release_fraction = (usNumber("us-airborne-percent") ?? -1) / 100;
      task.room_volume_m3 = usNumber("us-room-volume");
      task.air_exchange_rate_per_hour = usNumber("us-ach");
      if (!(task.chemical_handled_kg_per_shift > 0) || !(task.airborne_release_fraction >= 0) ||
          !(task.room_volume_m3 > 0) || !(task.air_exchange_rate_per_hour > 0)) {
        toast("Complete chemical handled, airborne fraction, room volume and air changes for the well-mixed screen.", 6500); return;
      }
    }
    workerTasks.push(task);
  }
  const request = {
    project_id: state.project.id,
    chemical_id: state.chemical.id,
    contaminant_group: "industrial_organic",
    scenario_name: `US industrial exposure · ${scenario.title}`,
    source_scenario_key: scenario.key,
    chemical_throughput_kg_day: throughput,
    operating_days_year: operatingDays,
    release_events: [{
      event_key: "screening_event_1",
      name: eventName,
      loss_fraction: loss / 100,
      control_efficiency_fraction: control / 100,
      media_fractions: {air: air / 100, water: water / 100, soil: soil / 100},
      control_destination: control > 0 ? $("us-control-destination").value : null,
      evidence_status: scenario.publication_status === "published" ? "scenario_default" : "expert_judgement",
      source_reference: sourceReference || scenario.title,
    }],
    worker_tasks: workerTasks,
    groundwater_screen: groundwaterScreen,
    citations: [{
      source_key: "epa_screening_scenario_catalogue",
      reference: sourceReference || scenario.title,
      evidence_status: scenario.publication_status === "published" ? "scenario_default" : "expert_judgement",
    }],
    uncertainty_notes: $("us-uncertainty")?.value.trim() || null,
    scientist_review_confirmed: Boolean($("us-scientist-review")?.checked),
  };
  const button = $("run-us-exposure");
  try {
    button.disabled = true;
    button.textContent = "Calculating and checking closure…";
    const result = await api("/api/model-runs/us-industrial-exposure", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request),
    });
    renderUSExposureResult(result);
    toast("US exposure screen completed and identity-bound.");
  } catch (error) {
    console.error(error);
    toast(`US exposure screen stopped: ${error.message}`, 7000);
  } finally {
    button.disabled = false;
    button.textContent = "Run transparent US screen";
  }
}

function setupUSExposure() {
  $("us-include-draft")?.addEventListener("change", () => loadUSExposureCatalogue().catch(error => toast(error.message, 6500)));
  $("us-worker-enabled")?.addEventListener("change", updateUSWorkerFields);
  $("us-worker-mode")?.addEventListener("change", updateUSWorkerFields);
  $("us-groundwater-enabled")?.addEventListener("change", updateUSGroundwaterFields);
  $("run-us-exposure")?.addEventListener("click", runUSExposure);
  updateUSWorkerFields();
  updateUSGroundwaterFields();
  loadUSExposureCatalogue().catch(error => {
    const status = $("us-foundation-status");
    if (status) status.innerHTML = `<span><strong>Source register unavailable</strong><small>${escapeHtml(error.message)}</small></span>`;
  });
}

function updateScenarioAvailability() {
  const vet = state.use === 'veterinary';
  $$('#release-cards .scenario-card').forEach(button => {
    const rel = button.dataset.release;
    const badge = button.querySelector('.scenario-availability');
    const usIndustrial = isUSIndustrialSelection(rel);
    const programme = PROGRAMME_ROUTED_RELEASES.has(rel);
    const veterinaryBranch = vet && ['soil','surface_water'].includes(rel);
    const live = LIVE_RELEASES.has(rel) || programme || veterinaryBranch;
    button.classList.toggle('unavailable', !live);
    button.setAttribute('aria-disabled', live ? 'false' : 'true');
    if (badge) {
      badge.textContent = live
        ? (veterinaryBranch ? 'VICH' : usIndustrial ? 'Native + EPA' : programme ? `${state.modelSystem} workflow` : 'Live')
        : 'Planned';
      badge.className = `scenario-availability ${live ? 'ready' : 'roadmap'}`;
    }
  });
}

function updateReleaseContext() {
  const linkedWastewater = ['wastewater','biosolids','irrigation'].includes(state.release);
  const veterinary = state.use === 'veterinary';
  $('wastewater-context')?.classList.toggle('hidden', !linkedWastewater || veterinary);
  $('pharma-influent-panel')?.classList.toggle('hidden', !linkedWastewater || state.use !== 'pharmaceutical');
  $('biosolids-context')?.classList.toggle('hidden', state.release !== 'biosolids');
  $('irrigation-context')?.classList.toggle('hidden', state.release !== 'irrigation');
  $('plant-context')?.classList.toggle('hidden', state.release !== 'irrigation');
  const programme = routesThroughRegulatoryProgramme();
  $('regulatory-programme')?.classList.toggle('hidden', !programme);
  $('us-models-placeholder')?.classList.toggle('hidden', !isUSIndustrialSelection());
  if (programme) loadRegulatoryProgrammePanel();
  updatePharmaInfluentUI();
  updateAdvancedModelVisibility();
}

function currentTier() {
  return Number($('tier-select')?.value) || state.tier || 2;
}

function routesThroughRegulatoryProgramme() {
  const veterinaryBranch = state.use === 'veterinary' && ['soil','surface_water'].includes(state.release);
  return PROGRAMME_ROUTED_RELEASES.has(state.release) && !veterinaryBranch;
}

function currentPlanContext() {
  const context = {
    jurisdiction: state.modelSystem,
    contaminant_group: regulatoryProductClass(),
    scenario: regulatoryScenario(),
    tier: currentTier(),
  };
  // FIFRA companion-model routing triggers: which of AgDRIFT/TerrPlant/T-REX/
  // BeeREX actually apply depends on application method, use site and
  // bee-attractiveness, not just "this is a pesticide" -- see
  // build_assessment_plan's US pesticide branch. Only meaningful for
  // US + agricultural_spray; the trigger controls are hidden otherwise.
  if (context.jurisdiction === 'US' && context.scenario === 'agricultural_spray') {
    context.application_method = $('fifra-application-method')?.value || null;
    context.use_site_category = $('fifra-use-site')?.value || null;
    context.bee_attractive = Boolean($('fifra-bee-attractive')?.checked);
  }
  return context;
}

// A transient "Loading …" label shown while the real plan is fetched (the plan itself, once it arrives, carries
// its own name/scope from registry._regulatory_programme -- this table is a cosmetic preview of that, kept in
// step with it for the regions that have their own scenario-specific routing).
const PROGRAMME_LABELS = {
  EU: {
    agricultural_spray: 'EU plant-protection product pathway', household_use: 'EU REACH consumer lifecycle pathway',
    product_disposal: 'EU REACH waste-stage pathway', industrial_effluent: 'EU REACH industrial pathway',
    default: 'EU environmental exposure pathway',
  },
  UK: {
    agricultural_spray: 'UK plant-protection product pathway', household_use: 'UK REACH consumer lifecycle pathway',
    product_disposal: 'UK REACH waste-stage pathway', industrial_effluent: 'UK REACH industrial pathway',
    default: 'UK environmental exposure pathway',
  },
  CH: {
    agricultural_spray: 'Swiss plant-protection product pathway', household_use: 'Swiss ChemO consumer lifecycle pathway',
    product_disposal: 'Swiss ChemO waste-stage pathway', industrial_effluent: 'Swiss ChemO/ORRChem industrial pathway',
    default: 'Swiss environmental exposure pathway',
  },
  US: {
    agricultural_spray: 'US FIFRA pesticide pathway', household_use: 'US TSCA consumer pathway',
    product_disposal: 'US TSCA waste-stage pathway', industrial_effluent: 'US TSCA industrial pathway',
    default: 'US environmental exposure pathway',
  },
};
function programmeLabel(context = currentPlanContext()) {
  const table = PROGRAMME_LABELS[context.jurisdiction];
  if (!table) return `${regionName(context.jurisdiction)} regulatory pathway`;
  return table[context.scenario] || table.default;
}

// The scenarios handled here exist in both jurisdictions. The same exposure
// scenario is retained while /api/assessment-plan replaces its jurisdictional
// model route. Native models are described but never represented as official
// regulatory executions; external models use the prepare/import/review control
// plane and keep their jurisdiction and scenario in the manifest.
async function loadRegulatoryProgrammePanel() {
  const planBox = $('regulatory-plan');
  if (!planBox) return;
  if (!state.chemical || !state.project) {
    planBox.innerHTML = '<p>Resolve and confirm a chemical identity first.</p>';
    $('regulatory-requirements').innerHTML = '';
    $('regulatory-warnings').innerHTML = '';
    $('regulatory-workflows').innerHTML = '';
    return;
  }
  if (!projectMatchesModelSystem()) {
    planBox.innerHTML = `<p><strong>Project jurisdiction does not match this tab.</strong> ${escapeHtml(projectJurisdictionMessage())}</p>`;
    $('regulatory-requirements').innerHTML = '';
    $('regulatory-warnings').innerHTML = '';
    $('regulatory-workflows').innerHTML = '';
    return;
  }
  const context = currentPlanContext();
  $('fifra-triggers')?.classList.toggle('hidden', !(context.jurisdiction === 'US' && context.scenario === 'agricultural_spray'));
  planBox.innerHTML = `<p>Loading ${escapeHtml(programmeLabel(context))}…</p>`;
  try {
    const plan = await api('/api/assessment-plan', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(context),
    });
    state.assessmentPlan = plan;
    const applicable = plan.models.filter(m => m.applicable);
    const [workflows, integrations] = await Promise.all([
      api(`/api/projects/${state.project.id}/model-workflows`).catch(() => []),
      api('/api/external-model-integrations').catch(() => []),
    ]);
    const executionModes = Object.fromEntries(integrations.map(row => [row.key, row.execution_bridge]));
    renderRegulatoryProgrammePanel(plan, applicable, workflows, context, executionModes);
  } catch (error) {
    planBox.innerHTML = `<p>Assessment-plan lookup stopped: ${escapeHtml(error.message)}</p>`;
  }
}

function workflowMatchesPlanContext(workflow, context) {
  if (workflow.jurisdiction !== context.jurisdiction) return false;
  const recordedScenario = workflow.manifest?.inputs?.regulatory_scenario;
  if (recordedScenario) return recordedScenario === context.scenario;
  return String(workflow.scenario_name || '').includes(`[${context.scenario}]`);
}

function renderRegulatoryProgrammePanel(plan, applicable, workflows, context = currentPlanContext(), executionModes = {}) {
  const planBox = $('regulatory-plan');
  const programme = plan.regulatory_programme || {name: programmeLabel(context), scope: ''};
  const external = applicable.filter(m => !String(m.implementation || '').startsWith('native'));
  const native = applicable.filter(m => String(m.implementation || '').startsWith('native'));
  const modelCard = (model, prepareable) => {
    const latest = workflows.find(w => w.model_key === model.key && workflowMatchesPlanContext(w, context));
    const nativeAvailable = model.key === 'ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN' && context.jurisdiction === 'US'
      ? 'native FateIntel screen · available in the industrial workbench below'
      : 'native FateIntel screen · calculation not run by this planning panel';
    const status = latest ? latest.status.replaceAll('_',' ') : (prepareable ? 'not yet prepared' : nativeAvailable);
    const button = prepareable ? `<button class="text-button" data-open-workflow-form="${escapeHtml(model.key)}" type="button">Enter inputs &amp; prepare</button>` : '';
    // Distinguish "FateIntel can run this executable locally, once configured"
    // from "manual official handoff -- a hashed original-file import is
    // required before this can ever be marked reviewed". Both are honest;
    // neither claims a result exists until one actually does.
    const bridge = prepareable ? executionModes[model.key] : null;
    const executionNote = bridge
      ? (bridge.execution_ready
          ? '<em class="model-note-inline">Controlled local execution configured.</em>'
          : bridge.supported
            ? '<em class="model-note-inline">Controlled local execution supported, not yet configured.</em>'
            : '<em class="model-note-inline">Manual official handoff -- hashed file import required for review.</em>')
      : '';
    return `<article class="model-tile selected" data-model="${escapeHtml(model.key)}"><span><strong>${escapeHtml(model.name || model.key)}</strong><small>${escapeHtml(status)}</small></span>${executionNote}${button}<div class="external-model-form hidden" id="external-model-form-${escapeHtml(model.key)}"></div></article>`;
  };
  planBox.innerHTML = applicable.length
    ? `<p><strong>${escapeHtml(programme.name)} · Tier ${plan.tier}.</strong> ${escapeHtml(context.scenario.replaceAll('_',' '))} remains the selected exposure scenario; the models below are specific to ${escapeHtml(context.jurisdiction)}.${programme.scope ? ` ${escapeHtml(programme.scope)}.` : ''}</p><div class="model-grid">${external.map(m => modelCard(m, true)).join('')}${native.map(m => modelCard(m, false)).join('')}</div>`
    : `<p>No ${escapeHtml(context.jurisdiction)} model in the registry is applicable to this contaminant group / scenario / tier combination. Adjust the use, release scenario or tier above.</p>`;
  $('regulatory-requirements').innerHTML = (plan.required_inputs || []).map(row => `<li>${escapeHtml(row)}</li>`).join('') || '<li>None recorded.</li>';
  $('regulatory-warnings').innerHTML = (plan.warnings || []).map(row => `<li>${escapeHtml(row)}</li>`).join('') || '<li>None.</li>';
  const relevant = workflows.filter(w => applicable.some(model => model.key === w.model_key) && workflowMatchesPlanContext(w, context));
  $('regulatory-workflows').innerHTML = relevant.length
    ? `<div class="mini-heading"><span>Prepared workflows</span></div><ul>${relevant.map(w => `<li>${escapeHtml(w.model_key)} · ${escapeHtml(w.status.replaceAll('_',' '))} · created ${escapeHtml(String(w.created_at || '').slice(0,10))}</li>`).join('')}</ul>`
    : '';
}

function fieldLabel(key) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Generic, data-driven form: works for any model with a MODEL_PROFILES
// input_template (PWC/PRZM/AGDRIFT/TERRPLANT/TREX/BEEREX/SPIN/MACRO/GREATER/
// CHEMSTEER/CEM/EFAST) without a bespoke form per model. Each top-level key
// is a section; every sub-key except "status" becomes a labeled input. The
// literal "contaminant_group": "pesticide" entry some templates carry is a
// plain string, not a section, and is skipped here -- it's merged back in by
// prepareRegulatoryWorkflow() from currentPlanContext() instead.
// fieldTypes (from MODEL_PROFILES[key]["field_types"], "section.field" -> {type,
// unit, min, max, step, options}) drives real input types instead of a blanket
// <input type="text"> -- a number input cannot hold non-numeric text, and a
// select cannot hold a value outside its options, so this closes the
// "supplied not-a-number for every field, reached prepared anyway" gap at the
// browser level, with backend require_numeric()/enum checks as defense in depth.
function renderModelInputForm(modelKey, template, fieldTypes = {}) {
  const sections = Object.entries(template).filter(([, fields]) => typeof fields === 'object' && fields !== null).map(([sectionKey, fields]) => {
    const inputs = Object.keys(fields).filter(k => k !== 'status').map(fieldKey => {
      const path = `${sectionKey}.${fieldKey}`;
      const meta = fieldTypes[path] || {type: 'text'};
      const label = `${fieldLabel(fieldKey)}${meta.unit ? ` (${meta.unit})` : ''}`;
      let control;
      const requiredAttr = meta.required ? ' required' : '';
      if (meta.type === 'select' && Array.isArray(meta.options)) {
        control = `<select data-field="${escapeHtml(path)}"${requiredAttr}><option value="">Select…</option>${meta.options.map(o => `<option value="${escapeHtml(o)}">${escapeHtml(fieldLabel(o))}</option>`).join('')}</select>`;
      } else if (meta.type === 'number') {
        const attrs = [
          meta.min !== undefined ? `min="${escapeHtml(String(meta.min))}"` : '',
          meta.max !== undefined ? `max="${escapeHtml(String(meta.max))}"` : '',
          `step="${escapeHtml(String(meta.step ?? 'any'))}"`,
        ].filter(Boolean).join(' ');
        control = `<input data-field="${escapeHtml(path)}" type="number" ${attrs}${requiredAttr}>`;
      } else {
        control = `<input data-field="${escapeHtml(path)}" type="text">`;
      }
      return `<label><span>${escapeHtml(label)}</span>${control}</label>`;
    }).join('');
    return `<fieldset><legend>${escapeHtml(fieldLabel(sectionKey))}</legend>${inputs}</fieldset>`;
  }).join('');
  return `<form class="external-model-form-body" data-model-key="${escapeHtml(modelKey)}">
    ${sections}
    <div class="external-model-form-actions">
      <button class="text-button" data-cancel-workflow-form="${escapeHtml(modelKey)}" type="button">Cancel</button>
      <button class="primary-button" data-submit-workflow="${escapeHtml(modelKey)}" type="button">Prepare workflow</button>
    </div>
  </form>`;
}

async function openWorkflowForm(modelKey) {
  const container = $(`external-model-form-${modelKey}`);
  if (!container) return;
  const opening = container.classList.contains('hidden');
  $$('.external-model-form').forEach(node => node.classList.add('hidden'));
  if (!opening) return;
  container.innerHTML = '<p>Loading input fields…</p>';
  container.classList.remove('hidden');
  try {
    const profile = await api(`/api/external-model-integrations/${modelKey}`);
    container.innerHTML = renderModelInputForm(modelKey, profile.input_template, profile.field_types || {});
  } catch (error) {
    container.innerHTML = `<p>Could not load ${escapeHtml(modelKey)}'s input fields: ${escapeHtml(error.message)}</p>`;
  }
}

// Builds {section: {status:"resolved", ...fields}} from whatever the user
// actually filled in; a section with no filled fields is simply omitted, so
// the backend's unresolved()/missing_inputs check reports it as missing --
// exactly as if the user had left it at "status":"required".
function collectWorkflowFormInputData(form) {
  const bySection = {};
  $$('[data-field]', form).forEach(input => {
    const [section, field] = input.dataset.field.split('.');
    const value = input.value.trim();
    if (!value) return;
    (bySection[section] ||= {status: 'resolved'})[field] = value;
  });
  return bySection;
}

async function prepareRegulatoryWorkflow(modelKey, formInputData = {}) {
  if (!state.chemical || !state.project) return;
  if (!projectMatchesModelSystem()) {
    toast(projectJurisdictionMessage(), 7600);
    return;
  }
  const context = currentPlanContext();
  try {
    const workflow = await api('/api/model-workflows', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        project_id: state.project.id, chemical_id: state.chemical.id, model_key: modelKey,
        jurisdiction: context.jurisdiction, tier: context.tier,
        scenario_name: `Guided ${context.jurisdiction} [${context.scenario}] ${modelKey} workflow for ${state.chemical.preferred_name}`,
        input_data: {
          // Preserved verbatim: main.py's pesticide-only gate reads
          // input_data.contaminant_group directly, and workflowMatchesPlanContext()
          // reads input_data.regulatory_scenario -- both must keep working.
          regulatory_scenario: context.scenario,
          contaminant_group: context.contaminant_group,
          assessment_tier: context.tier,
          source: 'guided_assessment_plan',
          ...formInputData,
        },
      }),
    });
    const missing = workflow.manifest?.missing_inputs || [];
    toast(missing.length
      ? `${modelKey} workflow saved as "${workflow.status.replaceAll('_',' ')}" -- still missing: ${missing.join(', ').replaceAll('_',' ')}.`
      : `${modelKey} workflow prepared with all required inputs. Import and review its official output from the Expert workspace when available.`, 7000);
    await loadRegulatoryProgrammePanel();
  } catch (error) { toast(`Could not prepare the ${modelKey} workflow: ${error.message}`, 6500); }
}

function setupRegulatoryProgramme() {
  document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-open-workflow-form]');
    if (opener) { openWorkflowForm(opener.dataset.openWorkflowForm); return; }
    const canceller = event.target.closest('[data-cancel-workflow-form]');
    if (canceller) { $(`external-model-form-${canceller.dataset.cancelWorkflowForm}`)?.classList.add('hidden'); return; }
    const submitter = event.target.closest('[data-submit-workflow]');
    if (submitter) {
      const modelKey = submitter.dataset.submitWorkflow;
      const form = submitter.closest('form');
      if (form && !form.checkValidity()) { form.reportValidity(); return; }
      prepareRegulatoryWorkflow(modelKey, collectWorkflowFormInputData(form));
    }
  });
  ['fifra-application-method', 'fifra-use-site'].forEach(id => $(id)?.addEventListener('change', loadRegulatoryProgrammePanel));
  $('fifra-bee-attractive')?.addEventListener('change', loadRegulatoryProgrammePanel);
}

function setupScenarioCards() {
  $$('#use-cards .scenario-card').forEach((button) => button.addEventListener('click', () => {
    if (state.running) { toast('The current calculation must finish before changing use.'); return; }
    $$('#use-cards .scenario-card').forEach((x) => x.classList.remove('active'));
    button.classList.add('active'); state.use = button.dataset.use;
    const isVet=state.use==='veterinary';
    $('veterinary-workflow')?.classList.toggle('hidden',!isVet);
    if($('use-ai-copy')) $('use-ai-copy').innerHTML=isVet?'<strong>Grounded suggestion:</strong> FateIntel will first run VICH Phase I, then open the applicable aquaculture, intensive, pasture or tailored companion-animal branch.':`<strong>Grounded suggestion:</strong> Confirm whether ${escapeHtml(state.chemical?.preferred_name || 'the selected substance')} is used as a human pharmaceutical. Identity alone does not establish the release scenario.`;
    if(isVet) updateVeterinaryProfile();
    if (window.flowShell) window.flowShell.onUseCardClicked(state.use);
    updateScenarioAvailability(); updateReleaseContext(); updateCompartments(); updateModels();
    updateSummaries(); refreshRegulatoryPathway();
  }));
  $$('#release-cards .scenario-card').forEach((button) => button.addEventListener('click', () => {
    if (state.running) { toast('The current calculation must finish before changing release scenario.'); return; }
    const rel = button.dataset.release;
    const usIndustrial = isUSIndustrialSelection(rel);
    const programme = PROGRAMME_ROUTED_RELEASES.has(rel) && !(state.use === 'veterinary' && ['soil','surface_water'].includes(rel));
    const allowed = LIVE_RELEASES.has(rel) || programme || (state.use === 'veterinary' && ['soil','surface_water'].includes(rel));
    if (!allowed) {
      toast('This emission scenario is visible in the roadmap but is not yet wired into the executable guided assessment. No result will be fabricated.',5600);
      return;
    }
    $$('#release-cards .scenario-card').forEach((x) => x.classList.remove('active'));
    button.classList.add('active'); state.release = rel;
    updateReleaseContext(); updateCompartments(); updateModels(); updateSummaries(); refreshRegulatoryPathway(); refreshGuidedReadiness();
    if (usIndustrial) $("us-models-placeholder")?.scrollIntoView({behavior:"smooth",block:"start"});
    if (programme) $("regulatory-programme")?.scrollIntoView({behavior:"smooth",block:"start"});
  }));
  ['amount-value','amount-unit','frequency','regions','tier-select','population','water-per-person','parent-fraction','dilution','irrigation-rate','irrigation-area','irrigation-depth','irrigation-years','biosolids-area','biosolids-depth','biosolids-storage','biosolids-years'].forEach((id) => {
    $(id)?.addEventListener('change', () => {
      if (id === 'tier-select') selectTier(Number($(id).value));
      updateSummaries();
      updateInfluentPreview();
      updateAdvancedModelVisibility();
      if (['regions','tier-select'].includes(id)) refreshRegulatoryPathway();
    });
  });
  updateScenarioAvailability();
  updateReleaseContext();
}

function updateCompartments() {
  const active = new Set(['source']);
  const planned = new Set();
  if (state.release === 'wastewater') ['wwtp','river','sediment','air'].forEach(x=>active.add(x));
  if (state.release === 'biosolids') { ['wwtp','soil','air'].forEach(x=>active.add(x)); planned.add('groundwater'); }
  if (state.release === 'irrigation') { ['wwtp','soil','crop','air'].forEach(x=>active.add(x)); planned.add('groundwater'); }
  if (state.release === 'surface_water') ['river','sediment'].forEach(x=>active.add(x));
  if (state.release === 'soil') { active.add('soil'); planned.add('groundwater'); }
  if (state.release === 'manufacturing') ['air','river','soil'].forEach(x=>active.add(x));
  if (state.release === 'household_use') ['air','wwtp','river'].forEach(x=>active.add(x));
  if (state.release === 'product_disposal') { ['air','river','soil'].forEach(x=>active.add(x)); planned.add('groundwater'); }
  if (state.release === 'agricultural_spray') { ['air','river','soil','crop'].forEach(x=>active.add(x)); planned.add('groundwater'); }
  $$('.compartment-node').forEach((node) => {
    const key=node.dataset.compartment;
    node.classList.toggle('active', active.has(key));
    node.classList.toggle('planned', planned.has(key));
    node.classList.toggle('muted', !active.has(key) && !planned.has(key));
  });
  const count=active.size+planned.size;
  const summary=document.querySelector('#step-compartments .step-summary'); if(summary) summary.textContent=`${count} relevant compartment${count===1?'':'s'}`;
}

function updateModels() {
  const relevant = new Set();
  if (['wastewater','biosolids','irrigation'].includes(state.release)) ['SIMPLETREAT','ACTIVITY_SIMPLETREAT'].forEach(x=>relevant.add(x));
  if (state.release === 'biosolids') relevant.add('BIOSOLIDS');
  if (state.release === 'irrigation') { relevant.add('SOIL_ACCUMULATION'); relevant.add('PLANT_UPTAKE'); }
  if (isUSIndustrialSelection()) {
    relevant.add('US_INDUSTRIAL_SCREEN'); relevant.add('CHEMSTEER');
  }
  if (state.modelSystem === 'US' && state.release === 'household_use') { relevant.add('CEM'); relevant.add('EFAST'); }
  if (state.modelSystem === 'US' && state.release === 'product_disposal') relevant.add('EFAST');
  if (state.modelSystem === 'US' && state.release === 'agricultural_spray') relevant.add('PWC');
  $$('.model-tile').forEach((tile) => tile.classList.toggle('selected', relevant.has(tile.dataset.model)));
  $('model-summary').textContent = routesThroughRegulatoryProgramme()
    ? `${state.modelSystem} jurisdiction plan · review applicable models below`
    : `${relevant.size} screening model${relevant.size===1?'':'s'} · advanced models later`;
}


function frameworkChip(row) {
  const tier=(row.verification_tier || "?").toLowerCase();
  const title=(row.framework || row.id).replace(/"/g,"&quot;");
  return `<a class="framework-chip" href="${row.official_url}" target="_blank" rel="noopener" title="${title}">
    <em class="${tier}">${row.verification_tier}</em><strong>${row.id}</strong><span>${row.framework}</span>
  </a>`;
}

function renderRegulatoryPathway(data) {
  state.regulatory=data;
  const rows=data.selected_frameworks || [];
  const globalRows=rows.filter(row=>["INT","XCT"].includes(row.region_group)).slice(0,9);
  const regionalRows=rows.filter(row=>!["INT","XCT"].includes(row.region_group)).slice(0,12);
  $("global-framework-chips").innerHTML=globalRows.length?globalRows.map(frameworkChip).join(""):`<span class="framework-chip">No international source selected</span>`;
  $("regional-framework-chips").innerHTML=regionalRows.length?regionalRows.map(frameworkChip).join(""):`<span class="framework-chip">No regional framework matched</span>`;
  $("tier-a-count").textContent=data.verification_summary?.A ?? 0;
  $("tier-bc-count").textContent=(data.verification_summary?.B ?? 0)+(data.verification_summary?.C ?? 0);
  $("watch-count").textContent=(data.change_watch || []).length;
  const regionLabel=(data.jurisdiction_labels || []).slice(0,3).join(" + ")+(data.jurisdiction_labels?.length>3?` + ${data.jurisdiction_labels.length-3} more`:"");
  $("regulatory-summary").textContent=`International baseline · ${regionLabel}`;
  const watch=$("change-watch-box");
  if((data.change_watch || []).length){
    watch.classList.remove("hidden");
    $("change-watch-text").textContent=(data.change_watch || []).slice(0,2).map(x=>x.item).join(" · ")+(data.change_watch.length>2?` · ${data.change_watch.length-2} more`:"");
  }else watch.classList.add("hidden");
}

async function refreshRegulatoryPathway() {
  if(!$("regulatory-pathway")) return;
  try{
    const payload={
      jurisdictions:selectedJurisdictions(),
      product_class:regulatoryProductClass(),
      scenario:regulatoryScenario(),
      tier:state.tier,
      include_international:true,
    };
    const data=await api("/api/global-regulatory/pathway",{
      method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)
    });
    renderRegulatoryPathway(data);
  }catch(error){
    console.error(error);
    $("global-framework-chips").innerHTML=`<span class="framework-chip">Framework service unavailable</span>`;
    $("regional-framework-chips").innerHTML=`<span class="framework-chip">Review required</span>`;
  }
}

function frameworkRowHtml(row){
  return `<article class="framework-row" data-framework-search="${[
    row.id,row.jurisdiction,row.authority,row.chemical_domain,row.framework,row.implementation_note
  ].join(" ").toLowerCase().replace(/"/g,"&quot;")}">
    <div class="framework-row-head">
      <span class="framework-id">${row.id}</span>
      <div><h3>${row.framework}</h3><p>${row.jurisdiction} · ${row.authority}</p></div>
      <span class="framework-chip"><em class="${row.verification_tier.toLowerCase()}">${row.verification_tier}</em></span>
    </div>
    <div class="framework-row-meta"><span>${row.chemical_domain}</span><span>${row.version_effective_date}</span><span>${row.source_review_status.replaceAll("_"," ")}</span></div>
    <div class="framework-note">${row.implementation_note}</div>
    <a class="framework-link" href="${row.official_url}" target="_blank" rel="noopener">Open official source ↗</a>
  </article>`;
}

async function openFrameworkNavigator(){
  $("drawer-content").innerHTML=`<span class="drawer-kicker">GLOBAL FRAMEWORK NAVIGATOR</span><h2>Loading 139 official-source pathways…</h2>`;
  $("drawer-backdrop").classList.remove("hidden");
  $("detail-drawer").classList.add("open");
  $("detail-drawer").setAttribute("aria-hidden","false");
  try{
    const [rows,status]=await Promise.all([
      api("/api/global-regulatory/frameworks"),
      api("/api/global-regulatory/research-status"),
    ]);
    $("drawer-content").innerHTML=`<span class="drawer-kicker">GLOBAL FRAMEWORK NAVIGATOR</span>
      <h2>Official-source regulatory register</h2>
      <p>This register routes assessments by product class and jurisdiction. Tier A is a verified official guidance source or portal; Tier B and C require additional local confirmation.</p>
      <div class="research-status-grid">
        <span><strong>${status.framework_entries}</strong><small>Framework entries</small></span>
        <span><strong>${status.official_urls}</strong><small>Official URLs</small></span>
        <span><strong>${status.verification_tiers.A}</strong><small>Tier A</small></span>
        <span><strong>${status.change_watch_items}</strong><small>Change watch</small></span>
      </div>
      <div class="framework-navigator">
        <div class="framework-filter-grid">
          <input id="framework-search" placeholder="Search framework, authority or domain">
          <select id="framework-tier-filter"><option value="">All verification tiers</option><option>A</option><option>B</option><option>C</option></select>
          <select id="framework-region-filter"><option value="">All regions</option><option>INT</option><option>EUR</option><option>NAM</option><option>OCE</option><option>ASI</option><option>LAT</option><option>AFR</option><option>MEA</option><option>XCT</option></select>
        </div>
        <div class="framework-list" id="framework-list">${rows.map(frameworkRowHtml).join("")}</div>
      </div>
      <div class="drawer-block"><h3>Implementation rule</h3><p>${status.implementation_rule}</p></div>`;
    const filter=()=>{
      const q=$("framework-search").value.toLowerCase();
      const tier=$("framework-tier-filter").value;
      const region=$("framework-region-filter").value;
      $$("#framework-list .framework-row").forEach(node=>{
        const row=rows.find(x=>node.querySelector(".framework-id").textContent===x.id);
        const show=(!q||node.dataset.frameworkSearch.includes(q))&&(!tier||row.verification_tier===tier)&&(!region||row.region_group===region);
        node.classList.toggle("hidden",!show);
      });
    };
    ["framework-search","framework-tier-filter","framework-region-filter"].forEach(id=>$(id).addEventListener(id==="framework-search"?"input":"change",filter));
  }catch(error){
    $("drawer-content").innerHTML=`<h2>Framework navigator unavailable</h2><p>${error.message}</p>`;
  }
}



async function loadVeterinaryProfiles(){
  try{
    state.veterinaryProfiles=await api("/api/veterinary/animal-profiles");
    const select=$("vet-animal-profile");
    const groups={};
    state.veterinaryProfiles.forEach(row=>{(groups[row.group]??=[]).push(row)});
    select.innerHTML=Object.entries(groups).map(([group,rows])=>`<optgroup label="${group}">${rows.map(row=>`<option value="${row.key}" ${row.key==="fattening_pig"?"selected":""}>${row.name}</option>`).join("")}</optgroup>`).join("");
    select.addEventListener("change",updateVeterinaryProfile);
    $("run-vet-phase-i")?.addEventListener("click",runVeterinaryPhaseI);
    updateVeterinaryProfile();
  }catch(error){
    console.error(error);toast(`Veterinary profile library unavailable: ${error.message}`,6000);
  }
}

function currentVeterinaryProfile(){
  return state.veterinaryProfiles.find(row=>row.key===$("vet-animal-profile")?.value);
}

function updateVeterinaryProfile(){
  const profile=currentVeterinaryProfile(); if(!profile)return;
  $("vet-branch").value=profile.branch;
  if(profile.body_weight_kg!=null) $("vet-body-weight").value=profile.body_weight_kg;
  if(profile.turnover_per_year!=null) $("vet-turnover").value=profile.turnover_per_year;
  if(profile.nitrogen_kg_place_year!=null) $("vet-nitrogen").value=profile.nitrogen_kg_place_year;
  const status=profile.official_default?"Registered EMA/VICH-support numeric default":"Custom values required — no official default asserted";
  $("vet-profile-source").textContent=`${status} · ${profile.group}`;
  const releaseByBranch={intensive:"biosolids",pasture:"soil",aquaculture:"surface_water",companion:"wastewater",special:"soil",custom:"soil"};
  state.release=releaseByBranch[profile.branch]||"soil";
  $$("#release-cards .scenario-card").forEach(x=>x.classList.toggle("active",x.dataset.release===state.release));
  updateCompartments();updateModels();updateSummaries();refreshRegulatoryPathway();
}

function veterinaryPhaseIPayload(){
  const profile=currentVeterinaryProfile();
  return {
    animal_profile_key:profile.key,jurisdiction:selectedJurisdictions().join(" + "),
    legally_exempt:false,natural_substance_no_distribution_change:false,minor_species_equivalent:false,
    small_number_treated:$("vet-small-number").checked,extensively_metabolized:$("vet-extensive-metabolism").checked,
    parasiticide:$("vet-parasiticide").checked,specific_environmental_concern:$("vet-custom-concern").checked,
    waste_entry_prevented:false,aquatic_confined:["raceway","pond","pond_or_tank"].includes(profile.facility_type),
    eic_aquatic_ug_l:null,pec_soil_ug_kg:null
  };
}

async function runVeterinaryPhaseI(){
  try{
    const result=await api("/api/veterinary/phase-i",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(veterinaryPhaseIPayload())});
    state.veterinaryPhaseI=result;
    const labels={phase_i_stop:"Phase I stop",phase_ii:"Phase II required",tailored_assessment:"Tailored assessment"};
    $("vet-phase-i-result").innerHTML=`<strong>${labels[result.outcome]||result.outcome}</strong><small>${result.reason}</small>`;
    toast(`${labels[result.outcome]||result.outcome}: ${result.reason}`,5200);
    return result;
  }catch(error){toast(`Phase I check stopped: ${error.message}`,6000);throw error;}
}

function veterinaryAssessmentPayload(){
  const profile=currentVeterinaryProfile();
  const branch=profile.branch;
  const valueOrNull=id=>{const v=Number($(id).value);return Number.isFinite(v)&&v>0?v:null};
  return {
    chemical_name:state.chemical?.preferred_name||"Selected chemical",animal_profile_key:profile.key,branch_override:null,
    dose_value:Number($("vet-dose").value),dose_unit:$("vet-dose-unit").value,treatment_duration_days:Number($("vet-duration").value),
    fraction_treated:Number($("vet-fraction-treated").value),treatment_events_per_year:1,
    excreted_fraction:Number($("vet-excreted-fraction").value),faecal_excretion_fraction:Number($("vet-excreted-fraction").value),excretion_duration_days:Number($("vet-duration").value),
    parasiticide:$("vet-parasiticide").checked,body_weight_kg:valueOrNull("vet-body-weight"),turnover_per_year:valueOrNull("vet-turnover"),
    nitrogen_kg_place_year:valueOrNull("vet-nitrogen"),housing_factor:1,nitrogen_spreading_limit_kg_ha:170,soil_bulk_density_kg_m3:1500,soil_depth_m:0.05,
    stocking_density_animals_ha:branch==="pasture"?valueOrNull("vet-stocking"):null,dung_output_kg_animal_day:branch==="pasture"?valueOrNull("vet-dung-output"):null,
    manure_storage_days:branch==="intensive"?Number($("vet-storage").value):0,storage_time_basis:"mean_age_half_duration",manure_dt50_value:null,manure_dt50_unit:"days",
    biowin4_value:branch==="intensive"?Number($("vet-biowin").value):null,source_temperature_c:25,target_temperature_c:10,temperature_factor_theta:1.047,
    soil_dt50_days:branch==="intensive"||branch==="pasture"?valueOrNull("vet-soil-dt50"):null,soil_dt90_days:null,soil_accumulation_years:Number($("vet-soil-years").value||10),
    treated_biomass_kg:branch==="aquaculture"?valueOrNull("vet-biomass"):null,facility_water_volume_l:branch==="aquaculture"?valueOrNull("vet-water-volume"):null,
    direct_water_release_fraction:branch==="aquaculture"?0.1:0,uneaten_feed_fraction:branch==="aquaculture"?0.05:0,receiving_water_dilution_factor:Number($("dilution").value||10),
    sediment_area_m2:branch==="aquaculture"?1000:null,sediment_depth_m:branch==="aquaculture"?0.05:null,sediment_density_kg_m3:branch==="aquaculture"?1300:null,
    log_kow:state.profile?.log_kow??null,soil_pnec_ug_kg:null,aquatic_pnec_ug_l:null,sediment_pnec_ug_kg:null,dung_pnec_ug_kg:null,earthworm_ld50_ug_kg:null
  };
}

async function runVeterinaryAssessment(){
  const button=$("run-assessment");
  stage("identity",10,"Resolving animal profile and VICH Phase I…");
  const phaseI=await runVeterinaryPhaseI();
  stage("emission",35,"Calculating dose, total residue and excretion…");
  const veterinary=await api("/api/veterinary/assessment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(veterinaryAssessmentPayload())});
  stage("irrigation",75,"Routing veterinary compartments and Tier A/B triggers…");
  state.results={veterinary,phaseI};
  renderVeterinaryResults();
  stage("summary",100,"Veterinary assessment complete");
  return {veterinary,phaseI};
}

function renderVeterinaryResults(){
  const {veterinary,phaseI}=state.results;
  const pec=veterinary.calculations.pecs||{};
  const profile=veterinary.animal_profile;
  $("results").classList.remove("hidden");
  document.querySelector("#results .results-heading h2").textContent=`Veterinary fate story: ${profile.name}`;
  $("results-subtitle").textContent=`${phaseI.reason} · ${veterinary.calculations.method}`;
  $("metric-effluent").textContent=phaseI.outcome.replaceAll("_"," ");
  $("metric-surface").textContent=pec.surface_water_refined_ug_l!=null?`${fmt(pec.surface_water_refined_ug_l)} µg/L`:"Not calculated";
  $("metric-dilution").textContent=profile.branch==="aquaculture"?"Aquaculture release":"Branch-specific pathway";
  const accumulation=veterinary.calculations.soil_accumulation;
  $("metric-soil").textContent=accumulation?`${fmt(accumulation.final_post_application_ug_kg)} µg/kg (${accumulation.years} y)`:pec.soil_refined_ug_kg!=null?`${fmt(pec.soil_refined_ug_kg)} µg/kg`:"Not calculated";
  $("metric-groundwater").textContent=profile.branch;
  $("metric-confidence").textContent=profile.official_default?"Moderate":"Review required";
  $("confidence-basis").textContent=profile.official_default?"Registered animal defaults; chemical inputs remain reviewable":"Custom husbandry values must be verified";
  $("donut-primary").textContent=`${fmt(veterinary.normalised_inputs.excreted_fraction*100)}%`;
  $("mass-donut").style.background=`conic-gradient(#2aa7c4 0 ${veterinary.normalised_inputs.excreted_fraction*100}%,#29b978 ${veterinary.normalised_inputs.excreted_fraction*100}% 100%)`;
  $("mass-legend").innerHTML=`<div class="legend-item"><i style="background:#2aa7c4"></i><span>Excreted parent fraction</span><strong>${fmt(veterinary.normalised_inputs.excreted_fraction*100)}%</strong></div><div class="legend-item"><i style="background:#29b978"></i><span>Other/metabolised fraction</span><strong>${fmt((1-veterinary.normalised_inputs.excreted_fraction)*100)}%</strong></div>`;
  $("comparison-insight").textContent="VICH GL6/GL38 harmonise the decision logic across regions, while animal husbandry, climate, soil, water and accepted refinements remain jurisdiction-specific.";
  $("ai-summary").textContent=`${profile.name} follows the ${profile.branch} branch. ${phaseI.reason}. ${veterinary.decision.message}`;
  $("ai-pathways").innerHTML=(profile.branch==="intensive"?["Animal dose → excretion into manure","Storage degradation and manure spreading","Agricultural soil → runoff and groundwater"]:profile.branch==="pasture"?["Direct urine and faecal excretion to pasture","Soil and dung-fauna exposure","Runoff/direct access to surface water"]:profile.branch==="aquaculture"?["Dose to feed or water","Facility effluent and receiving water","Uneaten feed/faeces → sediment"]:["Use-specific tailored release scenario required"]).map(x=>`<li>${x}</li>`).join("");
  $("data-gaps").querySelector("small").textContent=veterinary.warnings.join(" ");
  $("soil-chart").querySelector(".chart-line").setAttribute("d","");
  $("soil-chart").querySelector(".chart-area").setAttribute("d","");
}

function setupTiers() {
  $$("#tier-track button").forEach((button) => button.addEventListener("click", () => selectTier(Number(button.dataset.tier))));
}
function selectTier(tier) {
  state.tier = tier;
  $("tier-select").value = String(tier);
  $$("#tier-track button").forEach((x) => x.classList.toggle("active", Number(x.dataset.tier) === tier));
  updateSummaries();
  if ($("regulatory-pathway")) refreshRegulatoryPathway();
  if (routesThroughRegulatoryProgramme()) loadRegulatoryProgrammePanel();
}

function showWorkspaceTab(name) {
  $$(".workspace-tab").forEach(btn => btn.classList.toggle("active", btn.dataset.workspaceTab === name));
  $("tab-panel-assessment")?.classList.toggle("hidden", name !== "assessment");
  $("tab-panel-saved")?.classList.toggle("hidden", name !== "saved");
}

function setupWorkspaceTabs() {
  $$(".workspace-tab").forEach(button => button.addEventListener("click", () => showWorkspaceTab(button.dataset.workspaceTab)));
}

async function runSavedAssessmentsSearch() {
  const q = $("saved-search-input").value.trim();
  const results = $("saved-assessments-results");
  if (!q) { results.innerHTML = "<p>Search above to find a saved assessment.</p>"; return; }
  results.innerHTML = "<p>Searching…</p>";
  try {
    const rows = await api(`/api/projects?${new URLSearchParams({ q, limit: "50" })}`);
    if (!rows.length) { results.innerHTML = `<p>No saved assessment matches “${escapeHtml(q)}”.</p>`; return; }
    results.innerHTML = rows.map(row => `
      <button class="saved-result" data-saved-project-id="${row.id}" type="button">
        <span style="text-align:left"><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.jurisdiction || "Unspecified jurisdiction")} · ${escapeHtml(row.purpose || "")}</small></span>
        <span>${new Date(row.created_at).toLocaleDateString()}</span>
      </button>`).join("");
    $$("#saved-assessments-results [data-saved-project-id]").forEach(button => button.addEventListener("click", async () => {
      try {
        await selectProject(Number(button.dataset.savedProjectId));
        showWorkspaceTab("assessment");
        $("step-identity")?.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (error) {
        console.error(error);
        toast(`Could not open that project: ${error.message}. It may contain more than one chemical — open it from a link with an explicit chemical id.`, 7000);
      }
    }));
  } catch (error) {
    console.error(error);
    results.innerHTML = `<p>Search failed: ${escapeHtml(error.message)}</p>`;
  }
}

function setupSavedAssessmentsSearch() {
  if (!$("saved-search-run")) return;
  $("saved-search-run").addEventListener("click", runSavedAssessmentsSearch);
  $("saved-search-input").addEventListener("keydown", (event) => { if (event.key === "Enter") runSavedAssessmentsSearch(); });
}

function setupNavigation() {
  $$("[data-scroll]").forEach((button) => button.addEventListener("click", () => {
    showWorkspaceTab("assessment");
    const node = $(button.dataset.scroll); if (node) node.scrollIntoView({behavior:"smooth",block:"start"});
  }));
  setupWorkspaceTabs();
  setupSavedAssessmentsSearch();
  setupExampleMenu();
  $("refine-assessment").addEventListener("click", () => $("step-use").scrollIntoView({behavior:"smooth",block:"start"}));
  $("copilot-launch").addEventListener("click", () => $("assistant-panel").scrollIntoView({behavior:"smooth",block:"start"}));
  $("project-pill")?.addEventListener("click", () => {
    const menu = $("project-menu");
    const opening = menu.classList.contains("hidden");
    menu.classList.toggle("hidden", !opening);
    $("project-pill").setAttribute("aria-expanded", opening ? "true" : "false");
  });
  document.addEventListener("click", event => {
    if (!event.target.closest(".project-switcher")) {
      $("project-menu")?.classList.add("hidden");
      $("project-pill")?.setAttribute("aria-expanded", "false");
    }
    if (!event.target.closest(".example-switcher")) {
      $("example-menu")?.classList.add("hidden");
      $("example-pill")?.setAttribute("aria-expanded", "false");
    }
  });
}

// Curated "Load example" entries: the real gold-standard validation cases (full multi-scenario runs, each
// checked against an independent primary source -- see the validation-cases artifact) plus one quick-start
// chemical per top-level group (identity confirmed via the real resolve/confirm flow, not a full validation --
// labelled as such so the two are never confused). Project IDs are real, created live in this app; this list
// is presentation-layer curation only, not stored in the database (Project has no "group"/"kind" column).
const EXAMPLE_PROJECTS = [
  { id: 2326, chemicalId: 1, name: "Carbamazepine", group: "Human pharmaceutical", kind: "validated", note: "3 scenarios, matches Japan MoE's own PNEC exactly" },
  { id: 2327, chemicalId: 2, name: "Diclofenac", group: "Human pharmaceutical", kind: "validated", note: "checked against SCHEER's EU EQS opinion" },
  { id: 2329, chemicalId: 1394, name: "Ibuprofen", group: "Human pharmaceutical", kind: "validated", note: "checked against real WWTP-removal + field data" },
  { id: 2332, chemicalId: 1397, name: "Bisphenol A", group: "Industrial, detergent & consumer", kind: "quickstart" },
  { id: 2333, chemicalId: 1396, name: "Atrazine", group: "Pesticides & biocides", kind: "quickstart" },
  { id: 2334, chemicalId: 1395, name: "PFOS", group: "PFAS", kind: "quickstart" },
  { id: 2335, chemicalId: 1398, name: "Copper", group: "Metals & metalloids", kind: "quickstart" },
  { id: 2336, chemicalId: 1399, name: "PCB-153", group: "Legacy persistent organics", kind: "quickstart" },
  { id: 2337, chemicalId: 1400, name: "Benzene", group: "Petroleum hydrocarbons & solvents", kind: "quickstart" },
];

function renderExampleMenu() {
  const menu = $("example-menu");
  if (!menu) return;
  const validated = EXAMPLE_PROJECTS.filter(e => e.kind === "validated");
  const quickstart = EXAMPLE_PROJECTS.filter(e => e.kind === "quickstart");
  const item = (e) => `<button data-example-id="${e.id}" data-example-chemical="${e.chemicalId}" role="menuitem" type="button">
    <strong>${escapeHtml(e.name)}</strong><small>${escapeHtml(e.group)}${e.note ? ` — ${escapeHtml(e.note)}` : ""}</small>
  </button>`;
  menu.innerHTML = `
    <div class="menu-group-label">Validated gold-standard cases</div>
    ${validated.map(item).join("")}
    <div class="menu-group-label">Quick start — one chemical per group</div>
    ${quickstart.map(item).join("")}
    <div class="menu-group-label">Polymers, mixtures and radionuclides have no single-substance identity to screen this way yet.</div>
  `;
  $$("#example-menu [data-example-id]").forEach(button => button.addEventListener("click", async () => {
    menu.classList.add("hidden");
    $("example-pill")?.setAttribute("aria-expanded", "false");
    try {
      await selectProject(Number(button.dataset.exampleId), Number(button.dataset.exampleChemical));
      $("step-identity")?.scrollIntoView({ behavior: "smooth", block: "start" });
      toast(`${button.querySelector("strong").textContent} example loaded.`);
    } catch (error) {
      console.error(error);
      toast(`Could not load that example: ${error.message}`, 6000);
    }
  }));
}

function setupExampleMenu() {
  if (!$("example-pill")) return;
  renderExampleMenu();
  $("example-pill").addEventListener("click", () => {
    const menu = $("example-menu");
    const opening = menu.classList.contains("hidden");
    menu.classList.toggle("hidden", !opening);
    $("example-pill").setAttribute("aria-expanded", opening ? "true" : "false");
  });
}

function annualKg() {
  const value = Number($("amount-value").value);
  const unit = $("amount-unit").value;
  if (unit === "kg/year") return value;
  if (unit === "tonnes/year") return value * 1000;
  if (unit === "kg/day") return value * 365;
  if (unit === "g/day") return value * 365 / 1000;
  if (unit === "mg/day") return value * 365 / 1_000_000;
  return value;
}

function dailyUseKg() {
  const value = Number($('amount-value')?.value || 0);
  const unit = $('amount-unit')?.value || 'kg/year';
  if (unit === 'kg/year') return value / 365;
  if (unit === 'tonnes/year') return value * 1000 / 365;
  if (unit === 'kg/day') return value;
  if (unit === 'g/day') return value / 1000;
  if (unit === 'mg/day') return value / 1_000_000;
  return value / 365;
}

function selectedFpen() {
  const mode = $('pharma-fpen-mode')?.value || 'default';
  if (mode === 'default') return 0.01;
  if (mode === 'user') return Number($('pharma-fpen')?.value || 0);
  const prevalence = Number($('pharma-prevalence')?.value || 0);
  const days = Number($('pharma-treatment-days')?.value || 0);
  const repetitions = Number($('pharma-treatments-year')?.value || 0);
  return prevalence * days * repetitions / 365;
}

function currentOecdClassValue() {
  const registry = state.oecdPharmaRegistry;
  const classKey = $('pharma-oecd-class')?.value;
  const country = $('pharma-oecd-country')?.value;
  const row = registry?.classes?.[classKey];
  if (!row || !country) return null;
  const values = row.values_2023_or_nearest || {};
  if (country === 'highest_available') {
    const entries = Object.entries(values).filter(([name]) => name !== 'OECD32');
    if (!entries.length) return null;
    const [name, value] = entries.reduce((best, item) => Number(item[1]) > Number(best[1]) ? item : best, entries[0]);
    return {country:name, value:Number(value), row};
  }
  if (values[country] == null) return null;
  return {country, value:Number(values[country]), row};
}

function refreshOecdCountryOptions() {
  const select = $('pharma-oecd-country');
  const row = state.oecdPharmaRegistry?.classes?.[$('pharma-oecd-class')?.value];
  if (!select || !row) return;
  const previous = select.value || 'OECD32';
  const countries = Object.keys(row.values_2023_or_nearest || {}).filter(name => name !== 'OECD32').sort((a,b)=>a.localeCompare(b));
  select.innerHTML = `<option value="OECD32">OECD32 average</option><option value="highest_available">Highest available country</option>${countries.map(name=>`<option value="${name}">${name}</option>`).join('')}`;
  if ([...select.options].some(option => option.value === previous)) select.value = previous;
  else select.value = 'OECD32';
  updateOecdDddDisplay();
}

function updateOecdDddDisplay() {
  const lookup = currentOecdClassValue();
  if ($('pharma-oecd-ddd')) $('pharma-oecd-ddd').value = lookup ? fmt(lookup.value, 6) : '—';
  updateInfluentPreview();
}

async function loadOecdPharmaRegistry() {
  try {
    state.oecdPharmaRegistry = await api('/api/pharmaceutical-consumption/oecd-2025');
    refreshOecdCountryOptions();
  } catch (error) {
    console.error(error);
    if ($('pharma-oecd-ddd')) $('pharma-oecd-ddd').value = 'source unavailable';
  }
}

function updatePharmaInfluentUI() {
  const panel = $('pharma-influent-panel');
  if (!panel || panel.classList.contains('hidden')) return;
  const mode = $('pharma-emission-mode')?.value || 'entered_use';
  const ema = mode === 'ema_phase_i' || mode === 'ema_phase_ii';
  const oecd = mode === 'oecd_class_screen';
  $$('.ema-field').forEach(node => node.classList.toggle('hidden', !ema));
  $$('.oecd-field').forEach(node => node.classList.toggle('hidden', !oecd));
  $$('.site-flow-field').forEach(node => node.classList.toggle('hidden', mode !== 'entered_use'));
  const fpenMode = $('pharma-fpen-mode')?.value || 'default';
  $$('.ema-fpen-user').forEach(node => node.classList.toggle('hidden', !ema || fpenMode !== 'user'));
  $$('.ema-fpen-refined').forEach(node => node.classList.toggle('hidden', !ema || fpenMode !== 'prevalence_treatment'));
  const notes = {
    entered_use:'The amount entered above is the total active substance used in this catchment. Daily and annual units are accepted; the matched sewer flow determines ClocalINF.',
    ema_phase_i:'EMA Phase I uses the maximum daily dose, FPEN, 200 L/inhabitant/day and 10× dilution. It deliberately assumes no patient metabolism and no STP removal.',
    ema_phase_ii:'EMA Phase II can apply the excreted parent fraction before SimpleTreat. Local release mass depends on the reference STP capacity; ClocalINF is the untreated-wastewater concentration.',
    oecd_class_screen:'OECD Figure 9.6 provides regional therapeutic-class DDD rates for four selected classes. Assigning the whole class rate to one active is a deliberately conservative prioritisation screen, not measured compound use.'
  };
  if ($('pharma-mode-note')) $('pharma-mode-note').textContent = notes[mode] || notes.entered_use;
  updateInfluentPreview();
}

function updateInfluentPreview() {
  if (!$('influent-preview') || state.use !== 'pharmaceutical') return;
  const mode = $('pharma-emission-mode')?.value || 'entered_use';
  const parentFraction = Math.max(0, Math.min(1, Number($('parent-fraction')?.value || 0)));
  const waterL = Math.max(0, Number($('water-per-person')?.value || 0));
  const population = Math.max(1, Number($('population')?.value || 1));
  let administeredKgDay = 0, sewerKgDay = 0, flowM3Day = 0, useLabel = '', note = '';
  if (mode === 'entered_use') {
    administeredKgDay = dailyUseKg();
    sewerKgDay = administeredKgDay * parentFraction;
    const override = Number($('wwtp-flow-override')?.value || 0);
    flowM3Day = override > 0 ? override : population * waterL / 1000;
    useLabel = `${$('amount-value')?.value || 0} ${$('amount-unit')?.value || ''}`;
    note = override > 0 ? 'Using the measured WWTP flow entered above.' : 'WWTP flow is derived from population × wastewater per person.';
  } else if (mode === 'ema_phase_i' || mode === 'ema_phase_ii') {
    const doseMg = Number($('pharma-dose-mg')?.value || 0);
    const fpen = selectedFpen();
    const capacity = Math.max(1, Number($('pharma-stp-capacity')?.value || 10000));
    administeredKgDay = doseMg * fpen * capacity / 1_000_000;
    sewerKgDay = mode === 'ema_phase_i' ? administeredKgDay : administeredKgDay * parentFraction;
    flowM3Day = capacity * waterL / 1000;
    useLabel = `${fmt(doseMg,6)} mg/patient/day × FPEN ${fmt(fpen,6)}`;
    note = mode === 'ema_phase_i' ? 'EMA Phase I total-residue screen: 100% parent, no patient metabolism or STP removal.' : 'EMA Phase II local release: the selected parent excretion fraction is applied before treatment.';
  } else if (mode === 'oecd_class_screen') {
    const lookup = currentOecdClassValue();
    const ddd = lookup?.value || 0;
    const doseMg = Number($('pharma-oecd-dose-mg')?.value || 0);
    administeredKgDay = ddd * doseMg * population / 1000 / 1_000_000;
    sewerKgDay = administeredKgDay * parentFraction;
    flowM3Day = population * waterL / 1000;
    useLabel = lookup ? `${fmt(ddd,6)} DDD/1,000/day · ${lookup.country}` : 'Select OECD class/region';
    note = 'Class-level prioritisation only; this is not compound-specific measured consumption.';
  }
  const influentUgL = flowM3Day > 0 ? sewerKgDay * 1_000_000 / flowM3Day : NaN;
  if ($('preview-use-mass')) $('preview-use-mass').textContent = useLabel || `${fmt(administeredKgDay,6)} kg/day used`;
  if ($('preview-sewer-mass')) $('preview-sewer-mass').textContent = `${fmt(sewerKgDay,7)} kg/day parent to sewer`;
  if ($('preview-wwtp-flow')) $('preview-wwtp-flow').textContent = `${fmt(flowM3Day,7)} m³/day WWTP flow`;
  if ($('preview-influent')) $('preview-influent').textContent = Number.isFinite(influentUgL) ? `${fmt(influentUgL,7)} µg/L` : '—';
  if ($('preview-influent-note')) $('preview-influent-note').textContent = `${note} Preview only; the saved run repeats the unit-normalised calculation and records the selected evidence mode.`;
}

function buildEmissionPayload() {
  const pharma = state.use === 'pharmaceutical';
  const selectedMode = pharma ? ($('pharma-emission-mode')?.value || 'entered_use') : 'entered_use';
  const amountUnit = $('amount-unit')?.value || 'kg/year';
  let emissionMode = selectedMode;
  if (selectedMode === 'entered_use') emissionMode = amountUnit.includes('/day') ? 'direct_daily_use' : 'refined_annual_use';
  const dailyUnit = amountUnit === 'kg/day' ? 'kg' : amountUnit === 'g/day' ? 'g' : 'mg';
  const payload = {
    project_id:state.project.id, chemical_id:state.chemical.id,
    scenario_name: pharma ? `Guided ${state.modelSystem} human-pharmaceutical ${selectedMode.replaceAll('_',' ')} emission` : `Guided ${state.modelSystem} direct-use wastewater emission`,
    emission_mode:emissionMode, parent_name:state.chemical.preferred_name, parent_molecular_weight_g_mol:state.chemical.molecular_weight_g_mol,
    product_name:pharma?'Guided human-pharmaceutical scenario':'Guided direct-use scenario', formulation:pharma?'tablet':'industrial active', administration_route:pharma?'oral':'other',
    spc_title:pharma && ['ema_phase_i','ema_phase_ii','oecd_class_screen'].includes(selectedMode)?'User-entered maximum daily dose; current SmPC review required':'Not supplied',
    spc_identifier:null, spc_url:null, spc_access_date:null,
    spc_source_type:'other',
    consumption_source_title:selectedMode==='oecd_class_screen'?'OECD (2025), Health at a Glance 2025, Figure 9.6':selectedMode==='entered_use'?'User-entered catchment active quantity':'EMA human medicinal-product ERA use assumptions',
    consumption_source_identifier:selectedMode==='oecd_class_screen'?'Figure 9.6':null,
    therapeutic_class_ddd_per_1000_day:0, dose_per_administration:1, dose_unit:'mg', administrations_per_day:1,
    oecd_class_key:selectedMode==='oecd_class_screen'?$('pharma-oecd-class')?.value:null,
    oecd_country:selectedMode==='oecd_class_screen'?$('pharma-oecd-country')?.value:null,
    refined_annual_active_kg:emissionMode==='refined_annual_use'?annualKg():null,
    daily_active_amount:emissionMode==='direct_daily_use'?Number($('amount-value')?.value || 0):null,
    daily_active_unit:dailyUnit, emitting_days_per_year:365,
    maximum_daily_dose_mg:['ema_phase_i','ema_phase_ii'].includes(selectedMode)?Number($('pharma-dose-mg')?.value || 0):null,
    ema_fpen_mode:$('pharma-fpen-mode')?.value || 'default', market_penetration_fraction:Number($('pharma-fpen')?.value || 0.01),
    prevalence_fraction:$('pharma-prevalence')?.value?Number($('pharma-prevalence').value):null,
    treatment_days:$('pharma-treatment-days')?.value?Number($('pharma-treatment-days').value):null,
    treatments_per_year:$('pharma-treatments-year')?.value?Number($('pharma-treatments-year').value):null,
    regulatory_stp_capacity_inhabitants:Number($('pharma-stp-capacity')?.value || 10000), dilution_factor:Number($('dilution')?.value || 10),
    population:Number($('population')?.value || 100000), wastewater_l_person_day:Number($('water-per-person')?.value || 200),
    wastewater_flow_m3_day_override:selectedMode==='entered_use' && Number($('wwtp-flow-override')?.value || 0)>0?Number($('wwtp-flow-override').value):null,
    direct_to_sewer_fraction:pharma?0:1, systemic_fraction:pharma?1:0,
    parent_urine_fraction:pharma?Number($('parent-fraction')?.value || 0):0, parent_faeces_fraction:0, metabolites:[]
  };
  if (selectedMode === 'oecd_class_screen') {
    payload.dose_per_administration = Number($('pharma-oecd-dose-mg')?.value || 0);
    payload.dose_unit = 'mg';
    payload.administrations_per_day = 1;
  }
  return payload;
}

async function ensureWorkspace() {
  if (!state.project?.id || !state.chemical?.id) {
    throw new Error("Confirm a chemical identity and assessment project before running a model")
  }
  const [projects, chemicals, projectChemicals] = await Promise.all([
    api("/api/projects"), api("/api/chemicals"),
    api(`/api/projects/${state.project.id}/chemicals`),
  ]);
  state.projects = projects;
  const exactProject = projects.find((x) => x.id === state.project.id);
  const exactChemical = chemicals.find((x) => x.id === state.chemical.id);
  const membership = projectChemicals.find((x) => x.id === state.chemical.id);
  if (!exactProject || !exactChemical || !membership) {
    renderNeutralWorkspace();
    throw new Error("The selected project/chemical binding is no longer available; confirm the identity again")
  }
  if (!projectMatchesModelSystem(exactProject)) {
    throw new Error(projectJurisdictionMessage())
  }
  state.project = exactProject;
  state.chemical = exactChemical;
  state.profile = await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}/assessment-profile`);
  renderProjectSwitcher();
  renderChemicalIdentity();
  renderAssessmentProfile(state.profile);
}

function setWorkspaceUrl() {
  const url = new URL(window.location.href);
  if (state.project?.id && state.chemical?.id) {
    url.searchParams.set("project_id", String(state.project.id));
    url.searchParams.set("chemical_id", String(state.chemical.id));
  } else {
    url.searchParams.delete("project_id");
    url.searchParams.delete("chemical_id");
  }
  history.replaceState({}, "", url);
}

async function selectProject(projectId, chemicalId = null) {
  const project = state.projects.find(row => row.id === Number(projectId));
  if (!project) return;
  const [projectChemicals, allChemicals] = await Promise.all([
    api(`/api/projects/${project.id}/chemicals`), api("/api/chemicals"),
  ]);
  if (!projectChemicals.length) { toast("This project has no chemical identity attached."); return; }
  if (projectChemicals.length > 1 && chemicalId == null) {
    toast("This project contains multiple chemicals. Open it with an exact project and chemical link to avoid selecting the wrong identity.", 6500);
    return;
  }
  const selected = chemicalId == null
    ? projectChemicals[0]
    : projectChemicals.find(row => row.id === Number(chemicalId));
  if (!selected) { toast("The requested chemical is not attached to this project."); return; }
  state.project = project;
  state.chemical = allChemicals.find(row => row.id === selected.id) || selected;
  const projectSystem = projectModelSystem(project);
  if (projectSystem && projectSystem !== state.modelSystem) activateModelSystem(projectSystem);
  state.profile = await api(`/api/projects/${project.id}/chemicals/${state.chemical.id}/assessment-profile`);
  state.results = null;
  renderProjectSwitcher();
  renderChemicalIdentity();
  renderAssessmentProfile(state.profile);
  await refreshGuidedReadiness();
  setWorkspaceUrl();
  setSaveState("ready", "Project selected");
}

async function loadCarbamazepineDemo() {
  const [projects, chemicals] = await Promise.all([api("/api/projects"), api("/api/chemicals")]);
  state.chemical = chemicals.find(row => row.cas_number === "298-46-4");
  if (!state.chemical) throw new Error("Protected Carbamazepine record is unavailable");
  const jurisdiction = activeJurisdictionLabel();
  const projectName = state.modelSystem === "EU"
    ? "Carbamazepine guided fate assessment"
    : `Carbamazepine — ${state.modelSystem} guided fate assessment`;
  state.project = projects.find(row => row.name === projectName && row.jurisdiction === jurisdiction) || null;
  if (!state.project) {
    state.project = await api("/api/projects", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name:projectName,jurisdiction,purpose:`Protected Carbamazepine ${state.modelSystem} verification example`}),
    });
  }
  await api(`/api/projects/${state.project.id}/chemicals/${state.chemical.id}`, {method:"POST"}).catch(error => {
    if (!String(error.message).toLowerCase().includes("already")) throw error;
  });
  await ensureWorkspace();
  setWorkspaceUrl();
}

function renderProjectSwitcher() {
  if (!$("project-pill") || !$("project-menu")) return;
  $("project-pill").innerHTML = `${escapeHtml(state.project?.name || "No assessment selected")} <span>⌄</span>`;
  $("project-menu").innerHTML = state.projects.map(project => `
    <button class="${project.id === state.project?.id ? "active" : ""}" data-project-id="${project.id}" role="menuitem" type="button">
      <strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.jurisdiction || "Unspecified jurisdiction")}</small>
    </button>`).join("");
  $$('#project-menu [data-project-id]').forEach(button => button.addEventListener('click', async () => {
    await selectProject(Number(button.dataset.projectId));
    $("project-menu").classList.add("hidden");
    $("project-pill").setAttribute("aria-expanded", "false");
  }));
}

async function loadInitialWorkspace() {
  state.projects = await api("/api/projects");
  const params = new URL(window.location.href).searchParams;
  const projectId = Number(params.get("project_id"));
  const chemicalId = Number(params.get("chemical_id"));
  if (Number.isInteger(projectId) && projectId > 0 && Number.isInteger(chemicalId) && chemicalId > 0) {
    await selectProject(projectId, chemicalId);
    if (state.project && state.chemical) return;
  }
  renderNeutralWorkspace();
}

function stage(name, percent, title) {
  state.assessmentStage = name;
  $("progress-title").textContent = title;
  $("progress-percent").textContent = `${percent}%`;
  $("progress-bar").style.width = `${percent}%`;
  const order = ["identity","sorption","emission","wwtp","biosolids","irrigation","plant","summary"];
  const current = order.indexOf(name);
  $$("#progress-stages span").forEach((node) => {
    const index = order.indexOf(node.dataset.stage);
    node.classList.toggle("done", index < current);
    node.classList.toggle("active", index === current);
  });
}

function clearAssessmentFailure() {
  $('run-error')?.classList.add('hidden');
  if ($('run-error-message')) $('run-error-message').textContent = '';
  if ($('run-error-detail')) $('run-error-detail').textContent = '';
}

function renderAssessmentFailure(error) {
  const labels = {
    identity: 'Identity and reviewed-profile confirmation',
    sorption: 'Sorption calculation',
    emission: 'Source and emission calculation',
    wwtp: 'Wastewater-treatment calculation',
    biosolids: 'Biosolids-to-soil calculation',
    irrigation: 'Wastewater-irrigation calculation',
    plant: 'Crop-uptake calculation',
    summary: 'Result rendering',
  };
  const stageLabel = labels[state.assessmentStage] || 'Assessment preparation';
  const message = String(error?.message || 'An unexpected error stopped the assessment.');
  const metadata = [
    error?.status ? `HTTP ${error.status}` : null,
    error?.requestId ? `request ${error.requestId}` : null,
    error?.endpoint ? `endpoint ${error.endpoint}` : null,
  ].filter(Boolean).join(' · ');
  $('run-progress')?.classList.add('hidden');
  $('results')?.classList.add('hidden');
  if ($('run-error-title')) $('run-error-title').textContent = `Stopped at: ${stageLabel}`;
  if ($('run-error-message')) $('run-error-message').textContent = message;
  if ($('run-error-detail')) $('run-error-detail').textContent = metadata || 'No HTTP request identifier was available.';
  $('run-error')?.classList.remove('hidden');
  $('run-error')?.scrollIntoView({behavior:'smooth', block:'center'});
}

async function runAssessment() {
  if (state.running) return;
  $('run-progress')?.classList.add('hidden');
  clearAssessmentFailure();
  state.assessmentStage = null;
  if (isUSIndustrialSelection()) {
    $("us-models-placeholder")?.scrollIntoView({behavior:"smooth",block:"start"});
    toast("Complete the source-term and worker-task fields, then run the transparent US screen.", 5600);
    return;
  }
  if (routesThroughRegulatoryProgramme()) {
    $("regulatory-programme")?.scrollIntoView({behavior:"smooth",block:"start"});
    toast(`This scenario uses the ${programmeLabel()}. Review or prepare the applicable ${state.modelSystem} workflow below; no result will be fabricated.`, 6500);
    return;
  }
  if (state.use!=='veterinary' && !LIVE_RELEASES.has(state.release)) {
    toast('This guided release scenario is not executable yet. Choose Wastewater, Biosolids or Wastewater irrigation; no placeholder result will be generated.',5600);
    return;
  }
  let readiness = null;
  try {
    await ensureWorkspace();
    if (state.use !== 'veterinary') {
      readiness = await refreshGuidedReadiness();
      if (!readiness?.ready) {
        toast(`Assessment blocked. Review and save the ${state.chemical.preferred_name} profile; missing: ${(readiness?.missing || ["profile review"]).join(", ").replaceAll("_", " ")}.`, 7000);
        $("chemical-profile-panel")?.scrollIntoView({behavior:"smooth",block:"center"});
        return;
      }
    }
  } catch (error) { toast(`Assessment preparation stopped: ${error.message}`,6500); return; }
  state.running = true;
  const button = $('run-assessment'); button.disabled = true; button.innerHTML = '<span>✦</span> Running Tier 1–2 assessment…';
  $('run-progress').classList.remove('hidden'); $('results').classList.add('hidden');
  try {
    if(state.use==='veterinary'){
      await runVeterinaryAssessment();
      await new Promise(resolve=>setTimeout(resolve,300));
      $('run-progress').classList.add('hidden');
      $('results').classList.remove('hidden');
      $('results').scrollIntoView({behavior:'smooth',block:'start'});
      toast('Veterinary VICH assessment created with explicit animal-profile provenance.');
      return;
    }
    stage('identity',5,'Confirming project, identity and reviewed parameter profile…');
    const profile = readiness.profile;
    state.assessmentPlan = await api('/api/assessment-plan', {
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jurisdiction:state.modelSystem, contaminant_group:regulatoryProductClass(), scenario:regulatoryScenario(), tier:currentTier()}),
    }).catch(() => null);

    stage('sorption',18,'Running ionisation-aware sorption model…');
    const sorption = await api('/api/model-runs/sorption', {
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        project_id:state.project.id,chemical_id:state.chemical.id,assessment_profile_id:profile.id,scenario_name:`Guided ${state.modelSystem} ${profile.ionisation_class} sorption assessment for ${state.chemical.preferred_name}`,
        mode:profile.ionisation_class,neutral_variant:profile.profile_origin==='protected_carbamazepine_benchmark'?'workbook_literal':'publication',base_variant:'franco_trapp',log_kow:profile.log_kow,pkaa:profile.pkaa,pkab:profile.pkab,
        soil_ph:7.0,organic_carbon_fraction:0.02,ionic_strength_mol_l:0.01,
        molecular_formula:state.chemical.molecular_formula,ring_count:0,n_h_attached_to_cationic_n:0,oh_groups:0,nh2_groups:0,ether_groups:0,ester_groups:0,ketone_groups:0,amide_groups:0,single_ring_charged_pyridines:0,chloro_groups:0,carboxamide_groups:0,multi_ring_charged_n:0,electrolyte_system:'5 mM CaCl2'
      })
    });

    stage('emission',35,'Calculating daily use, sewer mass and WWTP influent concentration…');
    const selectedHumanMode = state.use === 'pharmaceutical' ? ($('pharma-emission-mode')?.value || 'entered_use') : 'entered_use';
    if (state.use === 'pharmaceutical' && selectedHumanMode === 'ema_phase_i' && state.release !== 'wastewater') {
      throw new Error('EMA Phase I is a surface-water screening calculation with no STP removal. Select Wastewater, or use actual/Phase II inputs before modelling biosolids or wastewater irrigation.');
    }
    const emission = await api('/api/model-runs/emission', {
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(buildEmissionPayload())
    });

    stage('wwtp',55,readiness.wwtp_model_mode==='supplied_workbook_9box_preset'?'Running protected Carbamazepine Activity SimpleTreat benchmark…':'Running reviewed custom WWTP mass balance…');
    const wwtp = await api('/api/model-runs/activity-simpletreat', {
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        project_id:state.project.id,chemical_id:state.chemical.id,assessment_profile_id:profile.id,emission_model_run_id:emission.model_run_id,species_key:'parent',
        scenario_name:`Guided ${state.modelSystem} WWTP assessment for ${state.chemical.preferred_name}`,model_mode:readiness.wwtp_model_mode,
        biodegradation_fraction:profile.wwtp_biodegradation_fraction,primary_sludge_fraction:profile.wwtp_primary_sludge_fraction,
        secondary_sludge_fraction:profile.wwtp_secondary_sludge_fraction,volatilisation_fraction:profile.wwtp_volatilisation_fraction,
        post_wwtp_biodegradation_fraction:0,receiving_water_dilution_factor:Number($('dilution').value),
        sludge_to_soil_fraction:0.1,mixed_soil_mass_kg:2_000_000,aquatic_pnec_ug_l:null,soil_pnec_ug_kg:null
      })
    });

    const kd = sorption.outputs.selected.kd_l_kg;
    let biosolids=null, irrigation=null, plant=null;

    if (state.release === 'biosolids') {
      stage('biosolids',74,'Calculating the selected biosolids-to-soil pathway…');
      biosolids = await api('/api/model-runs/biosolids', {
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          project_id:state.project.id,chemical_id:state.chemical.id,scenario_name:`Selected ${state.modelSystem} WWTP biosolids land application`,
          assessment_profile_id:profile.id,activity_simpletreat_model_run_id:wwtp.model_run_id,
          source_mode:'wwtp_chemical_mass',chemical_mass_to_sludge_kg_day:wwtp.outputs.sludge_mass_kg_day,
          biosolids_dry_solids_kg_day:null,biosolids_concentration_mg_kg_dw:null,biosolids_application_t_dw_ha_year:null,
          operating_days_per_year:365,fraction_sludge_land_applied:1,land_application_area_ha:Number($('biosolids-area')?.value||100),
          storage_days:Number($('biosolids-storage')?.value||30),storage_dt50_days:null,
          soil_mixing_depth_m:Number($('biosolids-depth')?.value||0.2),soil_bulk_density_kg_m3:1500,soil_dt50_days:profile.soil_dt50_days,
          assessment_years:Number($('biosolids-years')?.value||10),runoff_fraction:0,leaching_fraction:0
        })
      });
    }

    if (state.release === 'irrigation') {
      stage('irrigation',74,'Calculating the selected wastewater-irrigation soil pathway…');
      irrigation = await api('/api/model-runs/wastewater-irrigation-comparison', {
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          project_id:state.project.id,chemical_id:state.chemical.id,assessment_profile_id:profile.id,sorption_model_run_id:sorption.model_run_id,activity_simpletreat_model_run_id:wwtp.model_run_id,
          effluent_concentration_ug_l:null,scenario_name:`Selected ${state.modelSystem} wastewater-irrigation soil exposure for ${state.chemical.preferred_name}`,chemical_name:state.chemical.preferred_name,
          cas_number:state.chemical.cas_number,smiles:state.chemical.smiles,irrigation_rate_l_m2_day:Number($('irrigation-rate')?.value||0.5),
          irrigated_area_m2:Number($('irrigation-area')?.value||3_680_000),total_irrigation_flow_l_day:null,soil_depth_m:Number($('irrigation-depth')?.value||0.4),bulk_density_kg_m3:1350,
          kd_l_kg:kd,organic_carbon_fraction:0.02,soil_dt50_days:profile.soil_dt50_days,degradation_rate_per_day:null,duration_years:Number($('irrigation-years')?.value||10),
          receiving_water_dilution_factor:Number($('dilution').value),aquatic_pnec_ug_l:null,crop:'maize',
          freundlich_exponent:null,water_solubility_mg_l:profile.water_solubility_mg_l,vapour_pressure_pa:profile.vapour_pressure_pa,
          eu_weather_scenario:null,eu_macro_scenario:null,drainage_boundary_conditions:null,eu_surface_water_scenario:null,
          eu_loading_time_series:null,us_pwc_scenario:null,us_weather_series:null,us_runoff_erosion_parameters:null
        })
      });
      if (profile.ionisation_class === 'neutral') {
        stage('plant',88,'Running the optional neutral-organic crop-uptake research screen…');
        plant = await api('/api/model-runs/plant-uptake', {
          method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
            project_id:state.project.id,chemical_id:state.chemical.id,scenario_name:`Selected ${state.modelSystem} irrigation maize uptake screen for ${state.chemical.preferred_name}`,
            assessment_profile_id:profile.id,sorption_model_run_id:sorption.model_run_id,
            model_mode:'briggs_neutral',ionisation_class:'neutral',
            soil_concentration_mg_kg_dw:irrigation.outputs.native_screen.soil_concentration_at_duration_ug_kg/1000,
            kd_l_kg:kd,volumetric_water_content_l_l:Number($('plant-water')?.value||0.25),soil_bulk_density_kg_m3:1350,
            log_kow:profile.log_kow,user_tscf:null,transpiration_l_plant_day:Number($('plant-transpiration')?.value||1.5),
            harvest_interval_days:Number($('plant-harvest')?.value||90),plant_loss_dt50_days:null,
            root_allocation_fraction:0.2,shoot_allocation_fraction:0.5,edible_allocation_fraction:0.3,
            root_fresh_mass_kg:0.5,shoot_fresh_mass_kg:3.0,edible_fresh_mass_kg:0.5,
            root_bcf_kg_kg:null,shoot_bcf_kg_kg:null,edible_bcf_kg_kg:null
          })
        });
      } else {
        stage('plant',88,`Skipping neutral-only crop screen for ${profile.ionisation_class} substance…`);
      }
    }

    stage('summary',96,'Building scenario-specific Tier 1–2 interpretation…');
    state.results = {sorption,emission,wwtp,biosolids,irrigation,pearl:null,plant,release:state.release,modelSystem:state.modelSystem,profile};
    renderResults();
    syncToxswaFromScreening();
    syncPearlFromScreening();
    stage('summary',100,'Tier 1–2 assessment complete');
    await new Promise((resolve)=>setTimeout(resolve,320));
    $('run-progress').classList.add('hidden');
    $('results').classList.remove('hidden');
    $('results').scrollIntoView({behavior:'smooth',block:'start'});
    toast('Tier 1–2 assessment complete. Advanced refinement is now available below where scientifically applicable.');
  } catch (error) {
    console.error(error);
    renderAssessmentFailure(error);
    toast(`Assessment stopped: ${error.message}`,8500);
  } finally {
    state.running = false; button.disabled = false; button.innerHTML = '<span>✦</span> Run Tier 1–2 assessment';
  }
}

function setMetricVisible(id, visible) {
  $(id)?.classList.toggle('hidden', !visible);
}

function currentScreeningSoilEndpoint() {
  if (!state.results) return null;
  if (state.results.release === 'biosolids' && state.results.biosolids) return {
    concentration_ug_kg: state.results.biosolids.outputs.final_post_application_mg_kg * 1000,
    mixing_depth_m: Number($('biosolids-depth')?.value || 0.2),
    label: 'biosolids repeated-application soil PEC',
  };
  if (state.results.release === 'irrigation' && state.results.irrigation) return {
    concentration_ug_kg: state.results.irrigation.outputs.native_screen.soil_concentration_at_duration_ug_kg,
    mixing_depth_m: Number($('irrigation-depth')?.value || 0.4),
    label: 'wastewater-irrigation soil PEC',
  };
  return null;
}

function syncPearlFromScreening() {
  const soil = currentScreeningSoilEndpoint();
  if (!soil) { $('continue-pearl')?.classList.add('hidden'); updateModelSystemUI(); return; }
  if ($('pearl-input-mode')) $('pearl-input-mode').value='pecsoil';
  if ($('pearl-initial-conc')) $('pearl-initial-conc').value=soil.concentration_ug_kg;
  if ($('pearl-mixing-depth')) $('pearl-mixing-depth').value=soil.mixing_depth_m;
  updatePearlModeUI(); updatePearlTierPreview(); updateModelSystemUI();
  if ($('pearl-status')) $('pearl-status').textContent=`Ready from ${soil.label} · ${fmt(soil.concentration_ug_kg,5)} µg/kg`;
}

function renderResults() {
  const {sorption,emission,wwtp,biosolids,irrigation,plant,release,modelSystem} = state.results;
  const chemicalName = state.chemical?.preferred_name || "the selected chemical";
  if ($("results-title")) $("results-title").textContent = `Here is what happens to ${chemicalName}.`;
  if ($("assessment-story-title")) $("assessment-story-title").textContent = `What happens to ${chemicalName}?`;
  if ($("results-jurisdiction-banner")) $("results-jurisdiction-banner").innerHTML = FOCUS_REGIONS.has(modelSystem)
    ? `<strong>${escapeHtml(regionName(modelSystem))} screening result.</strong> This is a FateIntel native process calculation, not a regulatory submission result. FOCUS and other official refinements remain separate, versioned EU/UK/CH workflows.`
    : modelSystem === 'US'
      ? '<strong>US screening result.</strong> This is a FateIntel native process calculation, not an EPA model result. PWC/CEM/E-FAST/ChemSTEER outputs appear only after real external execution, import and review.'
      : `<strong>${escapeHtml(regionName(modelSystem))} screening result.</strong> This is a FateIntel native process calculation, not a regulatory submission result. The regulator's own method is named in the regulatory route plan.`;
  const provenance = [
    ['Sorption', sorption], ['Emission', emission], ['WWTP', wwtp], ['Biosolids', biosolids], ['Irrigation', irrigation], ['Plant uptake', plant],
  ].filter(([, run]) => run);
  if ($("results-provenance")) $("results-provenance").innerHTML = provenance.map(([label, run]) =>
    `<li>${escapeHtml(label)} · model run #${escapeHtml(String(run.model_run_id ?? '—'))}</li>`
  ).join('');
  const e = emission.outputs.species[0];
  const w = wwtp.outputs;
  const fractions = w.pathway_fractions;
  const eff = fractions.effluent * 100, deg = fractions.biodegraded * 100, sludge = (fractions.primary_sludge + fractions.secondary_sludge) * 100, air = fractions.air * 100;

  ['metric-card-influent','metric-card-effluent','metric-card-surface','metric-card-soil','metric-card-biosolids','metric-card-groundwater','metric-card-crop'].forEach(id=>setMetricVisible(id,false));
  setMetricVisible('metric-card-confidence',true);
  setMetricVisible('metric-card-influent',true);
  setMetricVisible('metric-card-effluent',true);
  const influent = emission.outputs.influent || {parent_concentration_ug_l:e.influent_concentration_ug_l,parent_mass_kg_day:e.mass_kg_day};
  $('metric-influent').textContent = `${fmt(influent.parent_concentration_ug_l,7)} µg/L`;
  $('metric-influent-mass').textContent = `${fmt(influent.parent_mass_kg_day,7)} kg/day parent · ${fmt(emission.outputs.wastewater_flow_m3_day,7)} m³/day flow`;
  $('metric-effluent').textContent = `${fmt(w.effluent_concentration_ug_l)} µg/L`;
  $('metric-confidence').textContent = 'Moderate';
  $('confidence-basis').textContent = state.profile?.profile_origin === 'protected_carbamazepine_benchmark'
    ? 'Protected benchmark mass balance and reviewed pilot inputs'
    : 'Reviewed chemical-specific profile; source uncertainty retained';

  const soilEndpoint=currentScreeningSoilEndpoint();
  if (release === 'wastewater') {
    setMetricVisible('metric-card-surface',true);
    const regulatory = emission.outputs.regulatory;
    const emaPhaseI = emission.outputs.emission_mode === 'ema_phase_i' && regulatory?.pec_surface_water_ug_l != null;
    $('metric-surface').textContent=`${fmt(emaPhaseI ? regulatory.pec_surface_water_ug_l : w.surface_water_pec_ug_l,7)} µg/L`;
    $('metric-dilution').textContent=emaPhaseI?`EMA Phase I · ${fmt(regulatory.dilution_factor,2)}× dilution · no STP removal`:`${fmt(Number($('dilution').value),2)}× receiving-water dilution after treatment`;
    $('results-subtitle').textContent=emaPhaseI
      ? `EMA Phase I · untreated wastewater ${fmt(influent.parent_concentration_ug_l,7)} µg/L · regulatory PECSW ${fmt(regulatory.pec_surface_water_ug_l,7)} µg/L. The treatment mass balance below is supplementary and is not part of the Phase I PEC equation.`
      : `Municipal wastewater selected · parent influent ${fmt(influent.parent_concentration_ug_l,7)} µg/L from ${fmt(influent.parent_mass_kg_day,7)} kg/day at ${fmt(emission.outputs.wastewater_flow_m3_day,7)} m³/day · no soil pathway is reported unless Biosolids or Wastewater irrigation is selected.`;
  } else if (release === 'biosolids') {
    setMetricVisible('metric-card-biosolids',true); setMetricVisible('metric-card-groundwater',true);
    $('metric-biosolids').textContent=`${fmt(biosolids.outputs.final_post_application_mg_kg*1000)} µg/kg`;
    $('metric-groundwater').textContent=FOCUS_REGIONS.has(state.modelSystem)?'Ready for PEARL':state.modelSystem==='US'?'PWC/PRZM not yet prepared':'Groundwater refinement not built for this region';
    $('results-subtitle').textContent=`Biosolids selected · ${fmt(biosolids.outputs.annual_chemical_loading_kg_ha,5)} kg/ha/year reaches land · ${biosolids.outputs.annual_series.length}-year soil series shown below.`;
  } else if (release === 'irrigation') {
    const i=irrigation.outputs.native_screen;
    setMetricVisible('metric-card-soil',true); setMetricVisible('metric-card-groundwater',true); setMetricVisible('metric-card-crop',Boolean(plant));
    $('metric-soil').textContent=`${fmt(i.soil_concentration_at_duration_ug_kg)} µg/kg`;
    $('metric-groundwater').textContent=FOCUS_REGIONS.has(state.modelSystem)?'Ready for PEARL':state.modelSystem==='US'?'PWC/PRZM not yet prepared':'Groundwater refinement not built for this region';
    if(plant) $('metric-crop').textContent=`${fmt(plant.outputs.edible_tissue_concentration_mg_kg_fw*1000)} µg/kg`;
    $('results-subtitle').textContent=`Wastewater irrigation selected · ${fmt(i.application_mass_kg_ha_year,5)} kg/ha/year applied in reclaimed water · ${i.annual_series.length}-year soil series shown below.`;
  }

  const legend = [
    ['#2aa7c4','Treated effluent',eff],['#29b978','Degraded',deg],['#c99a51','Primary + secondary sludge',sludge],['#c8d4d2','Air',air]
  ];
  $('donut-primary').textContent = `${fmt(eff,3)}%`;
  $('mass-donut').style.background = `conic-gradient(#2aa7c4 0 ${eff}%,#29b978 ${eff}% ${eff+deg}%,#c99a51 ${eff+deg}% ${eff+deg+sludge}%,#c8d4d2 ${eff+deg+sludge}% 100%)`;
  $('mass-legend').innerHTML = legend.map(([color,label,value])=>`<div class="legend-item"><i style="background:${color}"></i><span>${label}</span><strong>${fmt(value,3)}%</strong></div>`).join('');

  $('ai-pathways').innerHTML='';
  if (release === 'wastewater') {
    const regulatory=emission.outputs.regulatory;
    const emaPhaseI=emission.outputs.emission_mode==='ema_phase_i' && regulatory?.pec_surface_water_ug_l!=null;
    $('ai-summary').textContent=emaPhaseI
      ? `The EMA Phase I use screen gives ${fmt(influent.parent_mass_kg_day,7)} kg/day at the 10,000-inhabitant reference STP, ${fmt(influent.parent_concentration_ug_l,7)} µg/L in untreated wastewater, and ${fmt(regulatory.pec_surface_water_ug_l,7)} µg/L PECSW after the regulatory dilution. Phase I deliberately assumes no patient metabolism and no STP removal.`
      : `The selected pathway converts use to ${fmt(influent.parent_mass_kg_day,7)} kg/day of parent reaching the sewer and ${fmt(influent.parent_concentration_ug_l,7)} µg/L at the WWTP influent. Activity SimpleTreat then predicts ${fmt(eff,3)}% in treated effluent and ${fmt(w.surface_water_pec_ug_l,7)} µg/L in receiving water after dilution.`;
    $('ai-pathways').innerHTML=(emaPhaseI
      ? [`Reference STP release → ${fmt(influent.parent_mass_kg_day,7)} kg/day`,`Untreated wastewater → ${fmt(influent.parent_concentration_ug_l,7)} µg/L`,`EMA Phase I receiving water → ${fmt(regulatory.pec_surface_water_ug_l,7)} µg/L PECSW`]
      : [`Parent to sewer → ${fmt(influent.parent_mass_kg_day,7)} kg/day`,`WWTP influent → ${fmt(influent.parent_concentration_ug_l,7)} µg/L`,`Treated effluent → ${fmt(w.effluent_concentration_ug_l,7)} µg/L`,`Receiving water → ${fmt(w.surface_water_pec_ug_l,7)} µg/L screening PEC`]).map(x=>`<li>${x}</li>`).join('');
  } else if (release === 'biosolids') {
    $('ai-summary').textContent=`The selected pathway follows WWTP sludge to agricultural soil. The model predicts ${fmt(sludge,3)}% of influent mass to primary + secondary sludge. Repeated land application gives ${fmt(biosolids.outputs.final_post_application_mg_kg*1000)} µg/kg after ${biosolids.outputs.annual_series.length} years. Groundwater is a later refinement and has not been calculated automatically.`;
    $('ai-pathways').innerHTML=[`WWTP sludge transfer → ${fmt(sludge,3)}% of influent mass`,`Land loading → ${fmt(biosolids.outputs.annual_chemical_loading_kg_ha,5)} kg/ha/year`,`Soil → ${fmt(biosolids.outputs.final_post_application_mg_kg*1000)} µg/kg after ${biosolids.outputs.annual_series.length} years`,`Groundwater → available as later EU FOCUS refinement`].map(x=>`<li>${x}</li>`).join('');
  } else if (release === 'irrigation') {
    const i=irrigation.outputs.native_screen;
    $('ai-summary').textContent=`The selected pathway uses treated WWTP effluent for irrigation. The effluent concentration is ${fmt(w.effluent_concentration_ug_l)} µg/L and the ${i.annual_series.length}-year soil screen reaches ${fmt(i.soil_concentration_at_duration_ug_kg)} µg/kg. ${plant ? 'A neutral-organic crop-uptake research screen is shown.' : `The neutral-only crop model was not run for this ${state.profile?.ionisation_class || 'ionisable'} substance.`} Groundwater remains a later FOCUS PEARL refinement rather than an automatic Tier 1–2 output.`;
    $('ai-pathways').innerHTML=[`Treated effluent → ${fmt(w.effluent_concentration_ug_l)} µg/L`,`Reclaimed-water loading → ${fmt(i.application_mass_kg_ha_year,5)} kg/ha/year`,`Soil → ${fmt(i.soil_concentration_at_duration_ug_kg)} µg/kg after ${i.annual_series.length} years`,plant?`Crop screen → ${fmt(plant.outputs.edible_tissue_concentration_mg_kg_fw*1000)} µg/kg fresh weight`:null,`Groundwater → available as later EU FOCUS refinement`].filter(Boolean).map(x=>`<li>${x}</li>`).join('');
  }

  $('data-gaps').innerHTML=`<span>!</span><div><strong>Data gaps detected</strong><small>Measured fate values and PNECs remain review items.${release === 'irrigation' && !plant ? ' Ionisable-chemical crop uptake requires a suitable model or reviewed BCF and was not fabricated.' : ''} Advanced external models run only after the exposure screen supplies a relevant PEC and their model-specific inputs are reviewed.</small></div>`;
  $('comparison-insight').textContent = FOCUS_REGIONS.has(state.modelSystem)
    ? (soilEndpoint ? `A soil PEC is ready. Continue to FOCUS PEARL below using ${fmt(soilEndpoint.concentration_ug_kg,5)} µg/kg as the starting exposure.` : 'No soil pathway was selected, so FOCUS PEARL is not automatically invoked.')
    : state.modelSystem === 'US'
      ? 'US modelling is selected. PWC/PRZM remain external EPA models managed through the model-workflow lifecycle; no groundwater concentration is shown here until a real workflow is prepared, its output imported and reviewed.'
      : `${regionName()} is selected. No dedicated groundwater refinement is built for this region, so no groundwater concentration is shown.`;
  updateModelSystemUI();

  const timeline=document.querySelector('.timeline-panel');
  if (release === 'biosolids') {
    timeline?.classList.remove('hidden');
    $('soil-timeline-kicker').textContent='BIOSOLIDS · REPEATED APPLICATION';
    $('soil-timeline-title').textContent=`Soil concentration over ${biosolids.outputs.annual_series.length} years`;
    drawSoilSeries(biosolids.outputs.annual_series.map(x=>({year:x.year,value_ug_kg:x.post_application_mg_kg*1000})), 'Biosolids soil PEC');
  } else if (release === 'irrigation') {
    timeline?.classList.remove('hidden');
    $('soil-timeline-kicker').textContent='WASTEWATER IRRIGATION · CONTINUOUS LOADING';
    $('soil-timeline-title').textContent=`Soil concentration over ${irrigation.outputs.native_screen.annual_series.length} years`;
    drawSoilSeries(irrigation.outputs.native_screen.annual_series.map(x=>({year:x.year,value_ug_kg:x.soil_concentration_mg_kg*1000})), 'Irrigated-soil PEC');
  } else {
    timeline?.classList.add('hidden');
  }
}

function drawSoilSeries(series, label='Soil PEC') {
  const svg = $('soil-chart');
  if (!svg || !series?.length) return;
  const points=[{year:0,value_ug_kg:0},...series];
  const maxY=Math.max(...points.map(x=>Number(x.value_ug_kg)||0),1e-12);
  const maxX=Math.max(...points.map(x=>Number(x.year)||0),1);
  const x=t=>42+(t/maxX)*555;
  const y=c=>184-(c/maxY)*135;
  const path=points.map((pt,index)=>`${index?'L':'M'}${x(pt.year).toFixed(1)} ${y(pt.value_ug_kg).toFixed(1)}`).join(' ');
  svg.querySelector('.chart-line').setAttribute('d',path);
  svg.querySelector('.chart-area').setAttribute('d',`${path} L597 184 L42 184 Z`);
  svg.querySelector('.chart-points').innerHTML=points.slice(1).map(pt=>`<circle cx="${x(pt.year)}" cy="${y(pt.value_ug_kg)}" r="2.6"></circle>`).join('');
  svg.querySelector('.grid-lines').innerHTML=[0,1,2,3].map(n=>`<line x1="42" y1="${49+n*45}" x2="597" y2="${49+n*45}"></line>`).join('');
  const texts=svg.querySelectorAll('text');
  if(texts[0]) texts[0].textContent='0';
  if(texts[1]) texts[1].textContent=`${maxX} years · ${label}`;
}

const drawerTemplates = {
  "us-exposure-method": () => `<span class="drawer-kicker">US EXPOSURE SCIENCE BOUNDARIES</span><h2>A transparent foundation, not an EPA clone</h2><p>The native calculation tracks one chemical throughput through non-overlapping loss events, controls, environmental media and managed waste. Captured material remains a transfer until downstream fate is assessed.</p><div class="drawer-block"><h3>Occupational screen</h3><p>Measured-air mode calculates route-specific shift dose. Well-mixed mode uses a time-averaged room build-up equation and omits near-field peaks; it is a screening bound, not ChemSTEER.</p></div><div class="drawer-block"><h3>Source governance</h3><p>Only 12 published EPA ESDs are enabled by default. Forty-eight draft records require explicit opt-in and remain labelled draft. ChemSTEER, CEM and E-FAST execute externally and are never bundled or rebranded.</p></div><div class="equation">throughput = retained process mass + direct release + managed-waste transfer</div>`,
  "envirodesign-method": () => `<span class="drawer-kicker">ENVIRODESIGN SCIENCE BOUNDARIES</span><h2>What this module can and cannot claim</h2><p>The fitted layer reproduces the supplied open BIOWIN 3/4 SMARTS reconstruction. It is not EPA source code and has not yet been validated as regulatory-equivalent output.</p><div class="drawer-block"><h3>Attribution</h3><p>A matched fragment explains part of the model score. It does not prove that the fragment is the experimental cause of persistence.</p></div><div class="drawer-block"><h3>Pathways</h3><p>Observed and predicted products retain their matrix, conditions, status and provenance. Direct commercial embedding of enviPath data remains licence-gated; this build supports manual import and an adapter contract.</p></div><div class="drawer-block"><h3>Design</h3><p>Candidate changes are hypotheses. Efficacy, metabolites, toxicity, mobility, bioaccumulation and synthetic feasibility must be reassessed before a structure can be described as safer or more sustainable.</p></div>`,
  "tp-soil-fate-method": () => `<span class="drawer-kicker">SOIL TRANSFORMATION PRODUCTS · SCIENCE BOUNDARIES</span><h2>A theoretical screen, not a fate study</h2><p>Single first-order kinetics on a molar basis: each product forms from ONE source (the parent or another product) with a formation fraction and declines with its own DT50, so chains and branches are allowed but reversible steps are not. Mass follows from the molar-mass ratio (EFSA 2017 soil PEC guidance, section 2.8). The 10 % line follows OECD TG 307 (2025) paragraph 51: a major transformation product is any product at 10 % or more of the applied dose at any time; here it is applied to the molar percentage of the parent dose.</p><div class="drawer-block"><h3>Formation fractions</h3><p>If you give none, 1.0 is used for each product on its own — the conservative first step of the EFSA 2017 stepped approach (section 3.2.3). Those defaults are not additive and can sum above 1. Supplied fractions must sum to 1 or less.</p></div><div class="drawer-block"><h3>Temperature</h3><p>DT50s are moved with the FOCUS/EFSA Arrhenius factor (Ea 65.4 kJ/mol; no degradation at or below 0 °C). EU is set to 10 °C; other regions need a temperature you enter, and none is guessed.</p></div><div class="drawer-block"><h3>Prediction quality</h3><p>Predicted DT50s and log P are proxies and most such tools were built on one chemical class. The BIOWIN screen is an unsourced project relation. Prefer measured values, and treat every result as a hypothesis for review.</p></div><div class="drawer-block"><h3>Uncertainty band</h3><p>Each DT50 that has a stated uncertainty (a PEPPER interval, or a 90 % range you enter) is sampled log-normally and independently, the kinetics are rerun, and the 5th, 50th and 95th percentiles of concentration are drawn at each time. It is seeded, so it reproduces. Formation fractions with a 90 % range you enter are sampled too (logit-normal around your value, taken as the median; sibling fractions from one source are scaled down together in any draw that would sum above 1). Anything without a stated uncertainty is held at its central value, so the band understates the full uncertainty; the tab names what was held fixed. No default range is assumed for formation fractions: it has to come from your data, for example the spread across soils in a study. Percentiles at neighbouring times do not belong to one curve. The single-soil basis adds PEPPER's between-soil spread; the typical-soil basis is the model uncertainty of the mean only.</p></div><div class="drawer-block"><h3>Microbial mineralization (context only)</h3><p>When a substance's SMILES matches the NITE ready-biodegradability set (Japan METI, OECD TG 301C/301D/302C/302D), its measured % of theoretical oxygen demand consumed is shown for context. It is a screening-test percentage, not a soil DT50, and it is never used in the kinetics above. A pass/fail badge follows OECD TG 301 (1992) para 10 (60% ThOD) but ONLY for 301C (Modified MITI I) records, where the guideline itself waives the usual 10-day-window requirement; 301D is labelled indicative only, 302C (a different, inherent-biodegradability test) is labelled not applicable, and unrecognised guidelines are labelled not classified.</p></div><div class="drawer-block"><h3>Not modelled</h3><p>Reversible steps, products with two sources, biphasic kinetics, leaching, plant uptake, volatilisation and run-off. Animal, wastewater and manure only set the starting soil concentration. The 0.1 µg/L groundwater relevance trigger for metabolites is not applied because it was not confirmed in primary text.</p></div>`,
  "degradation-kinetics-method": () => `<span class="drawer-kicker">DEGRADATION KINETICS SCIENCE BOUNDARIES</span><h2>Two different "10%" rules, on purpose</h2><p>FOCUS Kinetics Section 8.5.1 (verbatim): metabolites below 10% of applied parent throughout the study are "minor" — a full formation/decline fit is not required to the same reliability standard. This is a kinetic-modelling-reliability distinction, not a toxicological or ecotoxicological relevance decision; that is governed by a separate document (the Guidance Document on Relevant Metabolites), which this module does not evaluate.</p><p>VICH GL38 (verbatim): excreted metabolites representing 10% or more of the administered dose <em>and which do not form part of biochemical pathways</em> should be added to the active substance for PEC recalculation. Whether a metabolite "forms part of biochemical pathways" is a reviewer judgement this module cannot determine automatically — it only applies the rule once you tell it.</p><div class="drawer-block"><h3>Model selection</h3><p>Every candidate model (SFO, FOMC, HS, DFOP) is fitted; the chi-square error percentage against day-level means (FOCUS Kinetics Eq. 6-1) is reported for all four, and the simplest model that passes the 15% guidance figure is pre-selected — FOCUS Kinetics' own words: "this value should only be considered as guidance and not absolute cut-off criterion." A model that passes narrowly can still be visibly worse than a bi-phasic alternative; review every model's error, not just the selected one.</p></div><div class="drawer-block"><h3>DT50/DT90</h3><p>Found by numerically solving the fitted M(t) curve rather than a hand-transcribed closed form for every model — FOCUS Kinetics itself states DFOP has no analytical solution and recommends an iterative search.</p></div><div class="equation">SFO: M(t) = M0·e^(−kt) · FOMC: M(t) = M0·(1+t/β)^(−α) · HS: piecewise first-order with a breakpoint · DFOP: M(t) = M0·(g·e^(−k1t) + (1−g)·e^(−k2t))</div><p>Source documents: FOCUS (2014) Generic guidance for Estimating Persistence and Degradation Kinetics, Version 1.1; VICH GL38 (EMA/CVMP).</p>`,
  "identity-evidence": () => state.chemical ? `<span class="drawer-kicker">IDENTITY RESOLUTION</span><h2>Why this identity was selected</h2><p>${escapeHtml(state.chemical.preferred_name)} is stored as a confirmed identity snapshot: CAS ${escapeHtml(state.chemical.cas_number || 'not assigned')}, formula ${escapeHtml(state.chemical.molecular_formula || 'not supplied')}, molecular weight ${fmt(state.chemical.molecular_weight_g_mol,8)} g/mol and InChIKey ${escapeHtml(state.chemical.inchikey || 'not supplied')}.</p><div class="drawer-block"><h3>Trust boundary</h3><p>Resolution creates a candidate first. User confirmation creates or reuses the chemical record and attaches it to a separate project-specific calculation profile. Evidence searched for another identity cannot be staged against this record.</p></div><div class="equation">Input → candidate identity → user confirmation → immutable identity snapshot → reviewed parameter profile</div>` : `<h2>No chemical selected</h2>`,
  "use-suggestion": () => `<span class="drawer-kicker">RULE-BASED USE PROMPT</span><h2>Why use still requires confirmation</h2><p>A chemical identity does not prove whether the substance is used as a human medicine, veterinary medicine, pesticide, industrial chemical or consumer ingredient. The selected use controls emission assumptions and model applicability.</p><div class="drawer-block"><h3>User control</h3><p>You can switch among the supported use categories. Veterinary mode opens VICH Phase I and the relevant animal branch.</p></div>`,
  "compartment-logic": () => `<span class="drawer-kicker">PATHWAY ENGINE</span><h2>Only the selected release pathway is activated</h2><p><strong>Wastewater</strong> ends at WWTP effluent and receiving water in the Tier 1–2 screen. <strong>Biosolids</strong> follows sludge to repeated soil application. <strong>Wastewater irrigation</strong> follows treated effluent to repeated soil loading and an optional crop screen. Groundwater is shown as a planned refinement only when a soil PEC exists.</p><div class="drawer-block"><h3>Not a blind “run everything” button</h3><p>Unselected compartments are not assigned concentrations. Roadmap scenarios remain visibly disabled until their equations and evidence requirements are implemented.</p></div>`,
  "model-applicability": () => `<span class="drawer-kicker">MODEL ORCHESTRATION</span><h2>Native calculations and managed adapters</h2><p>Tier 1–2 screening runs only models required by the emission pathway. Native multimedia and river-network screens are explicit FateIntel calculations. SimpleBox, GREAT-ER, ePiE, EPI Suite, FOCUS and PWC3 remain separate managed workflows.</p><div class="drawer-block"><h3>Scientific rule</h3><p>No external model concentration is fabricated. Prepared input is not presented as a completed model result.</p></div>`,
  "eu-us": () => `<span class="drawer-kicker">REGULATORY MODEL SYSTEMS</span><h2>EU and US workflows are versioned independently</h2><p><strong>EU:</strong> FOCUS PEARL follows a relevant soil PEC; SWASH/TOXSWA remains the official pesticide surface-water chain. GREAT-ER and ePiE provide higher-tier point-source river options.</p><p><strong>US:</strong> PWC3 is the current managed pesticide-water workflow; standalone PRZM and EXAMS remain legacy or specialist records.</p><div class="drawer-block"><h3>Scientific rule</h3><p>Switching region changes model eligibility, but an external result appears only after actual execution, import and scientific review.</p></div>`,
  "global-baseline": () => `<span class="drawer-kicker">INTERNATIONAL BASELINE</span><h2>Why global sources come first</h2><p>FateIntel starts with GHS classification, OECD test methods, GLP/MAD evidence quality, eChemPortal discovery and QSAR/read-across support. National and sector rules then determine what is legally required and accepted.</p><div class="equation">Product class → international methods → national framework → scenario/model guidance → decision and risk management</div>`,
  "framework-selection": () => state.regulatory ? `<span class="drawer-kicker">FRAMEWORK SELECTION</span><h2>How this pathway was assembled</h2><p>The platform selected ${state.regulatory.selected_frameworks.length} sources for ${state.regulatory.product_class.replaceAll("_"," ")} across ${state.regulatory.jurisdiction_labels.join(", ")}.</p><div class="drawer-block"><h3>Verification summary</h3><p>Tier A: ${state.regulatory.verification_summary.A}; Tier B: ${state.regulatory.verification_summary.B}; Tier C: ${state.regulatory.verification_summary.C}.</p></div><p>Sources are selected by product class, jurisdiction, exposure scenario and specialist triggers. Registration in the source library is not the same as completed ruleset implementation.</p>` : `<h2>Regulatory pathway loading</h2>`,
  "change-watch": () => state.regulatory ? `<span class="drawer-kicker">CHANGE WATCH</span><h2>Rules that must be rechecked</h2>${state.regulatory.change_watch.map(x=>`<div class="drawer-block"><h3>${x.item}</h3><p>${x.change_trigger}</p><p><strong>Action:</strong> ${x.required_action}</p><a class="framework-link" href="${x.official_url}" target="_blank" rel="noopener">Open official source ↗</a></div>`).join("")}<p>${state.regulatory.legal_notice}</p>` : `<h2>No pathway loaded</h2>`,
  "mass-balance": () => state.results ? `<span class="drawer-kicker">WWTP MASS BALANCE</span><h2>Wastewater mass balance</h2><p>${state.results.wwtp.outputs.model_mode === 'supplied_workbook_9box_preset' ? 'The protected Carbamazepine verification fractions were used.' : 'The reviewed custom fractions stored for this chemical and project were used; this is not an official SimpleTreat execution.'} Their sum closes to ${fmt(state.results.wwtp.outputs.mass_balance_closure_fraction*100,5)}%.</p><div class="equation">Influent mass = effluent + degraded + primary sludge + secondary sludge + air</div><div class="drawer-block"><h3>Transfer rule</h3><p>The Carbamazepine fixture is identity-locked. Custom fractions remain user-reviewed screening inputs and are not inferred from overall WWTP removal alone.</p></div>` : `<h2>Run the assessment first</h2>`,
  "soil-timeline": () => state.results?.release === "biosolids" ? `<span class="drawer-kicker">BIOSOLIDS SOIL SERIES</span><h2>Repeated land application over time</h2><p>The chart shows the post-application soil concentration for each assessment year from the selected biosolids pathway. Storage loss, annual loading and soil degradation are retained in the calculation trace.</p><div class="drawer-block"><h3>Selected pathway only</h3><p>Wastewater-irrigation accumulation is not mixed into this chart.</p></div>` : `<span class="drawer-kicker">WASTEWATER-IRRIGATION SOIL SERIES</span><h2>Continuous reclaimed-water loading</h2><p>The chart shows the selected irrigation pathway only. First-order degradation and Kd-controlled leaching are applied within the native screen.</p><div class="equation">C(t) = Input / (kdeg + kleach) × [1 − exp{−(kdeg + kleach)t}]</div><p>Biosolids accumulation is not mixed into this chart.</p>`,
};

function openDrawer(key) {
  const template = drawerTemplates[key];
  if (!template) return;
  $("drawer-content").innerHTML = template();
  $("drawer-backdrop").classList.remove("hidden");
  $("detail-drawer").classList.add("open");
  $("detail-drawer").setAttribute("aria-hidden","false");
}
function closeDrawer() {
  $("drawer-backdrop").classList.add("hidden");
  $("detail-drawer").classList.remove("open");
  $("detail-drawer").setAttribute("aria-hidden","true");
}
function setupDrawers() {
  $$('[data-drawer]').forEach((node)=>node.addEventListener("click",()=>openDrawer(node.dataset.drawer)));
  $("identity-evidence").addEventListener("click",()=>openDrawer("identity-evidence"));
  $("open-framework-navigator")?.addEventListener("click",openFrameworkNavigator);
  $("refresh-regulatory-pathway")?.addEventListener("click",()=>{refreshRegulatoryPathway();toast("Regulatory pathway refreshed from the 139-source register.");});
  $$(".compartment-node").forEach((node)=>node.addEventListener("click",()=>openDrawer("compartment-logic")));
  $("drawer-close").addEventListener("click",closeDrawer); $("drawer-backdrop").addEventListener("click",closeDrawer);
  document.addEventListener("keydown",(event)=>{if(event.key==="Escape")closeDrawer();});
}

function setupCopilot() {
  $("copilot-form").addEventListener("submit",(event)=>{
    event.preventDefault();
    const q=$("copilot-input").value.trim().toLowerCase(); if(!q)return;
    let answer;
    if(q.includes("koc")||q.includes("sorption")) answer=state.results?`The ${state.results.sorption.outputs.selected.model_name} route selected Koc ${fmt(state.results.sorption.outputs.selected.koc_l_kg)} L/kg and Kd ${fmt(state.results.sorption.outputs.selected.kd_l_kg)} L/kg at fOC 0.02 for the reviewed ${state.results.sorption.outputs.ionisation_class} profile. Open the scientific workspace to inspect the equation trace.`:"Run the assessment first so I can explain the stored sorption output.";
    else if(q.includes("framework")||q.includes("regulation")||q.includes("jurisdiction")||q.includes("eu")||q.includes("us")) answer=state.regulatory?`The current pathway uses ${state.regulatory.selected_frameworks.length} official-source entries across ${state.regulatory.jurisdiction_labels.join(", ")}. Verification tiers are A ${state.regulatory.verification_summary.A}, B ${state.regulatory.verification_summary.B}, C ${state.regulatory.verification_summary.C}. Open Frameworks to inspect the sources and change-watch flags.`:"The regulatory pathway is still loading.";
    else if(q.includes("risk")||q.includes("pnec")) answer="Risk is not yet characterised because no reviewed PNEC was supplied. FateIntel will not invent one. Add an evidence-backed PNEC in the scientific workspace, then the RQ can be calculated.";
    else if(q.includes("metabol")) answer="This run quantifies unchanged parent only. Named metabolite fractions are a flagged data gap and must be entered on a molar basis before treatment.";
    else if(q.includes("dilution")) answer=`The current receiving-water dilution factor is ${$("dilution").value}×. Change it in the wastewater context and rerun to update the surface-water PEC.`;
    else answer="This is a rule-based assessment explainer. Ask about risk, PNEC, sorption, frameworks, metabolites or dilution. It reads stored results and does not invent scientific endpoints.";
    $("copilot-answer").textContent=answer; $("copilot-answer").classList.remove("hidden");
  });
}




const ENVIRODESIGN_RDKIT_JS_URL = "https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js";
const ENVIRODESIGN_RDKIT_WASM_URL = "https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.wasm";
let enviroDesignRDKitPromise = null;
let enviroDesignBrowserConfigPromise = null;

function pickDescriptor(descriptors, names, fallback = 0) {
  for (const name of names) {
    const value = descriptors?.[name];
    if (value !== undefined && value !== null && Number.isFinite(Number(value))) return Number(value);
  }
  return fallback;
}

function safeJson(value, fallback) {
  try { return JSON.parse(value); } catch (_) { return fallback; }
}

async function getEnviroDesignBrowserConfig() {
  if (!enviroDesignBrowserConfigPromise) enviroDesignBrowserConfigPromise = api("/api/envirodesign/browser-config");
  return enviroDesignBrowserConfigPromise;
}

async function loadEnviroDesignRDKit() {
  if (window.RDKit) return window.RDKit;
  if (enviroDesignRDKitPromise) return enviroDesignRDKitPromise;
  enviroDesignRDKitPromise = new Promise((resolve, reject) => {
    const finish = () => {
      if (typeof window.initRDKitModule !== "function") {
        reject(new Error("RDKit.js loader did not initialise."));
        return;
      }
      window.initRDKitModule({
        locateFile: (path) => path.endsWith(".wasm") ? ENVIRODESIGN_RDKIT_WASM_URL : path,
      }).then((module) => {
        window.RDKit = module;
        resolve(module);
      }).catch((error) => reject(new Error(`RDKit WebAssembly could not initialise: ${error?.message || error}`)));
    };
    if (typeof window.initRDKitModule === "function") { finish(); return; }
    const script = document.createElement("script");
    script.src = ENVIRODESIGN_RDKIT_JS_URL;
    script.async = true;
    script.crossOrigin = "anonymous";
    script.onload = finish;
    script.onerror = () => reject(new Error("The browser could not load the RDKit.js WebAssembly distribution. Check internet/network access."));
    document.head.appendChild(script);
  });
  return enviroDesignRDKitPromise;
}

function browserSubstructureMatches(RDKit, mol, smarts) {
  let qmol = null;
  try {
    qmol = RDKit.get_qmol(smarts);
    if (!qmol) return [];
    const raw = mol.get_substruct_matches(qmol);
    const parsed = safeJson(raw, []);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) { return []; }
  finally { try { qmol?.delete(); } catch (_) {} }
}

function formulaFromInchi(inchi) {
  if (!inchi || !inchi.startsWith("InChI=")) return null;
  const parts = inchi.split("/");
  return parts.length > 1 ? parts[1] : null;
}

function featureFittedEvidence(feature, components) {
  const atoms=new Set(feature.atom_indices||[]);
  const matches=(components||[]).filter(row=>row.smarts && (row.atom_indices||[]).some(idx=>atoms.has(idx)));
  if(!matches.length) return null;
  return {
    b3:matches.reduce((sum,row)=>sum+Number(row.biowin3_contribution||0),0),
    b4:matches.reduce((sum,row)=>sum+Number(row.biowin4_contribution||0),0),
    labels:[...new Set(matches.map(row=>row.description))],
  };
}

function plainContribution(value) {
  const v=Number(value||0);
  if(v < -0.02) return 'lowers the biodegradation score';
  if(v > 0.02) return 'raises the biodegradation score';
  return 'has little effect on the score';
}

function browserDesignHypotheses(inventory, attribution) {
  const suggestions=[];
  const exactNegatives=attribution.components.filter(x=>x.smarts && (Number(x.biowin3_contribution)<0 || Number(x.biowin4_contribution)<0));
  const keys=new Set((inventory.features||[]).map(x=>x.key));
  if(keys.has('benzene_like_aromatic_ring') || keys.has('polycyclic_aromatic_scaffold')) suggestions.push({
    feature:'Aromatic ring system',
    hypothesis:'Test whether the aromatic scaffold is retained in transformation products and compare matched analogues with reduced aromaticity only where the required function allows.',
    why:'Aromatic rings are clearly present. The exact reconstructed BIOWIN aromatic coefficient is reported only if its own fitted SMARTS matched this substituted structure.',
    tradeoffs:['target or product function','logD and sorption','photochemistry','new transformation products'],
    confidence:'structural hypothesis; strengthen with pathway or analogue evidence',
  });
  const labile=(inventory.features||[]).filter(x=>['ester','hydrolysable_carbamate','alcohol','aldehyde','aliphatic_alkene','beta_lactam','azo'].includes(x.key));
  if(labile.length) suggestions.push({
    feature:'Potential transformation handle',
    hypothesis:`Prioritise experiments around ${labile.map(x=>(STRUCTURE_REGION_META[x.key]?.title||x.label).toLowerCase()).join(', ')} and identify the products formed rather than assuming complete biodegradation.`,
    why:'These motifs provide plausible chemical or biological transformation sites, but structure alone does not establish the environmental rate.',
    tradeoffs:['parent disappearance versus mineralisation','product persistence','matrix and pH dependence'],
    confidence:'structure-based screening',
  });
  for(const item of exactNegatives.slice(0,2)) suggestions.push({
    feature:`Fitted BIOWIN term · ${item.description}`,
    hypothesis:'Build a matched molecular pair that changes this exact fitted feature while preserving the required functional core, then rerun the complete fate assessment.',
    why:`This term directly contributes ${Number(item.biowin3_contribution)>=0?'+':''}${Number(item.biowin3_contribution).toFixed(3)} to B3 and ${Number(item.biowin4_contribution)>=0?'+':''}${Number(item.biowin4_contribution).toFixed(3)} to B4.`,
    tradeoffs:['efficacy or product function','Koc / mobility','toxicity','transformation products'],
    confidence:'direct model attribution; causal environmental persistence still unproven',
  });
  if(!suggestions.length) suggestions.push({
    feature:'No decisive fitted hotspot',
    hypothesis:'Use matched analogues and observed transformation products before proposing a structural substitution.',
    why:'No strong negative structure-specific term was found in the current reconstructed fragment set.',
    tradeoffs:['additional evidence generation','analogue selection'],
    confidence:'high that more evidence is needed',
  });
  return suggestions;
}


async function browserAnalyseStructure(smiles, name = "Unlabelled structure") {
  const [RDKit, config] = await Promise.all([loadEnviroDesignRDKit(), getEnviroDesignBrowserConfig()]);
  let mol = null;
  try {
    mol = RDKit.get_mol(smiles);
    if (!mol) throw new Error("SMILES could not be parsed by the browser RDKit engine.");
    const descriptors = safeJson(mol.get_descriptors(), {});
    const canonical = mol.get_smiles();
    const inchi = typeof mol.get_inchi === "function" ? mol.get_inchi() : null;
    const formula = formulaFromInchi(inchi) || "—";
    const mw = pickDescriptor(descriptors,["MolWt","amw","MW","MolecularWeight"],0);
    const exactMass = pickDescriptor(descriptors,["ExactMolWt","exactmw","ExactMW"],0);
    const logp = pickDescriptor(descriptors,["CrippenClogP","MolLogP","logP","LogP"],0);
    const tpsa = pickDescriptor(descriptors,["TPSA","tpsa"],0);
    const hbd = pickDescriptor(descriptors,["NumHBD","NumHDonors","HBD"],0);
    const hba = pickDescriptor(descriptors,["NumHBA","NumHAcceptors","HBA"],0);
    const rot = pickDescriptor(descriptors,["NumRotatableBonds","NumRotBonds"],0);
    const ringCount = pickDescriptor(descriptors,["RingCount","NumRings"],0);
    const aromaticRingCount = pickDescriptor(descriptors,["NumAromaticRings","AromaticRings"],0);
    const heavyCount = pickDescriptor(descriptors,["HeavyAtomCount","NumHeavyAtoms"],0);

    const terms = config.biowin.terms;
    const mw3 = mw * Number(terms.MW.biowin3);
    const mw4 = mw * Number(terms.MW.biowin4);
    let b3 = Number(terms.intercept.biowin3) + mw3;
    let b4 = Number(terms.intercept.biowin4) + mw4;
    const components = [
      {description:"Equation intercept",count:1,biowin3_contribution:Number(terms.intercept.biowin3),biowin4_contribution:Number(terms.intercept.biowin4),atom_indices:[]},
      {description:"Molecular-weight term",count:1,biowin3_contribution:mw3,biowin4_contribution:mw4,atom_indices:[]},
    ];
    const negativeAtoms = new Set();
    for (const fragment of config.biowin.fragments) {
      const matches = browserSubstructureMatches(RDKit,mol,fragment.smarts);
      if (!matches.length) continue;
      const c3 = matches.length * Number(fragment.biowin3_coefficient);
      const c4 = matches.length * Number(fragment.biowin4_coefficient);
      b3 += c3; b4 += c4;
      const atoms = [...new Set(matches.flatMap(x => x.atoms || []))];
      if (c3 < 0 || c4 < 0) atoms.forEach(x => negativeAtoms.add(x));
      components.push({
        fragment_id:fragment.id,description:fragment.description,smarts:fragment.smarts,count:matches.length,
        biowin3_contribution:c3,biowin4_contribution:c4,atom_indices:atoms,source_status:fragment.source_status,
      });
    }

    const features = [];
    for (const [key,smarts] of Object.entries(config.feature_smarts || {})) {
      const matches = browserSubstructureMatches(RDKit,mol,smarts);
      if (!matches.length) continue;
      features.push({key,label:key.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase()),count:matches.length,
        atom_indices:[...new Set(matches.flatMap(x=>x.atoms||[]))],basis:"transparent RDKit.js structure alert; no fitted BIOWIN coefficient"});
    }
    const aromaticAtoms = browserSubstructureMatches(RDKit,mol,"[a]").flatMap(x=>x.atoms||[]);
    const halogenAtoms = browserSubstructureMatches(RDKit,mol,"[F,Cl,Br,I]").flatMap(x=>x.atoms||[]);
    if (aromaticRingCount >= 2) features.push({key:"polycyclic_aromatic_scaffold",label:"Polycyclic Aromatic Scaffold",count:aromaticRingCount,atom_indices:[...new Set(aromaticAtoms)],basis:"structure-inventory alert; requires analogue/pathway evidence before causal interpretation"});
    if (halogenAtoms.length) features.push({key:"halogenated_structure",label:"Halogenated Structure",count:halogenAtoms.length,atom_indices:[...new Set(halogenAtoms)],basis:"elemental structure alert; attachment context determines interpretation"});
    const inventory = {
      molecular_formula:formula,molecular_weight_g_mol:mw,exact_mass:exactMass,logp_rdkit:logp,tpsa_a2:tpsa,
      h_bond_donors:hbd,h_bond_acceptors:hba,rotatable_bonds:rot,ring_count:ringCount,aromatic_ring_count:aromaticRingCount,
      heavy_atom_count:heavyCount,features,
    };
    const attribution = {
      biowin3_ultimate_score:b3,biowin4_primary_score:b4,matched_fragment_count:components.filter(x=>x.smarts).length,
      components,
      interpretation:{biowin3:"Reconstructed ultimate biodegradation timeframe score",biowin4:"Reconstructed primary biodegradation timeframe score"},
    };
    let structureSvg;
    try { structureSvg = mol.get_svg(620,350); } catch (_) { structureSvg = mol.get_svg(); }
    let inchiKey = null;
    try { if (inchi && typeof RDKit.get_inchikey_for_inchi === "function") inchiKey = RDKit.get_inchikey_for_inchi(inchi); } catch (_) {}
    return {
      model_version:config.model_version,name,input_smiles:smiles,canonical_smiles:canonical,inchi_key:inchiKey,
      structure:inventory,biowin_screen:attribution,design_hypotheses:browserDesignHypotheses(inventory,attribution),structure_svg:structureSvg,
      engine:{key:"rdkit-js-wasm-browser",version:typeof RDKit.version === "function" ? RDKit.version() : "unknown",delivery:"remote official RDKit.js distribution"},
      confidence:{identity:"high after successful RDKit parsing; stereochemistry depends on supplied SMILES",fragment_attribution:"screening",causal_persistence_assignment:"not established",regulatory_equivalence:"not established"},
      warnings:[...(config.biowin.limitations||[]),"Browser/WASM execution avoids the optional native Python RDKit DLL dependency.","Primary degradation, ultimate degradation, bioactivity loss and transformation-product persistence are separate endpoints."],
    };
  } finally { try { mol?.delete(); } catch (_) {} }
}

async function browserHasSubstructure(smiles, smarts) {
  const RDKit = await loadEnviroDesignRDKit();
  let mol=null,qmol=null;
  try { mol=RDKit.get_mol(smiles); qmol=RDKit.get_qmol(smarts); if(!mol||!qmol) return false; return String(mol.get_substruct_match(qmol)).length>2; }
  finally { try{mol?.delete();}catch(_){} try{qmol?.delete();}catch(_){} }
}

async function persistBrowserEnviroDesign(modelKey, scenarioName, inputs, outputs) {
  if (!state.project?.id || !state.chemical?.id) return {model_run_id:null,outputs};
  return api("/api/envirodesign/persist-browser",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    model_key:modelKey,scenario_name:scenarioName,project_id:state.project.id,chemical_id:state.chemical.id,inputs,outputs
  })});
}

async function browserCompareCandidates(originalSmiles,candidates,protectedSmarts=[]) {
  const original=await browserAnalyseStructure(originalSmiles,"Original");
  for (const smarts of protectedSmarts) if (!(await browserHasSubstructure(originalSmiles,smarts))) throw new Error(`Protected SMARTS is not present in the original structure: ${smarts}`);
  const rows=[];
  for (const candidate of candidates) {
    const analysed=await browserAnalyseStructure(candidate.smiles,candidate.name||"Candidate");
    const d3=analysed.biowin_screen.biowin3_ultimate_score-original.biowin_screen.biowin3_ultimate_score;
    const d4=analysed.biowin_screen.biowin4_primary_score-original.biowin_screen.biowin4_primary_score;
    const direction=d3>0&&d4>0?"higher_in_both_screening_models":d3<0&&d4<0?"lower_in_both_screening_models":"mixed_primary_vs_ultimate_direction";
    const preserved=[];
    for (const smarts of protectedSmarts) preserved.push({smarts,preserved:await browserHasSubstructure(candidate.smiles,smarts)});
    const dlogp=analysed.structure.logp_rdkit-original.structure.logp_rdkit;
    const dtpsa=analysed.structure.tpsa_a2-original.structure.tpsa_a2;
    const dmw=analysed.structure.molecular_weight_g_mol-original.structure.molecular_weight_g_mol;
    const tradeoffs=[];
    if(dlogp>0.3) tradeoffs.push("Calculated logP increased; bioaccumulation/sorption consequences require review");
    if(dlogp<-0.3) tradeoffs.push("Calculated logP decreased; groundwater mobility may increase");
    if(Math.abs(dtpsa)>20) tradeoffs.push("Polar surface area changed substantially; function and permeability may change");
    if(dmw>50) tradeoffs.push("Molecular weight increased substantially");
    if(preserved.some(x=>!x.preserved)) tradeoffs.push("At least one user-protected substructure was not preserved");
    rows.push({name:analysed.name,canonical_smiles:analysed.canonical_smiles,biowin3_delta:d3,biowin4_delta:d4,screening_direction:direction,logp_delta:dlogp,tpsa_delta_a2:dtpsa,molecular_weight_delta_g_mol:dmw,protected_substructures:preserved,tradeoffs:tradeoffs.length?tradeoffs:["No major descriptor trade-off detected by this limited comparison"],analysis:analysed});
  }
  return {model_version:original.model_version,original,candidates:rows,ranking_rule:"No single winner is asserted. Compare model direction, property trade-offs, protected structure and full fate evidence.",warnings:["Improved reconstructed BIOWIN scores do not demonstrate retained efficacy or experimental biodegradability."]};
}

async function browserPathwayRetention(parentSmiles,products) {
  const parent=await browserAnalyseStructure(parentSmiles,"Parent");
  const parentFragments=new Set(parent.biowin_screen.components.filter(x=>x.smarts).map(x=>x.description));
  const parentFeatures=new Set(parent.structure.features.map(x=>x.key));
  const counts={}; [...parentFragments,...parentFeatures].forEach(k=>counts[k]=0);
  const rows=[];
  for (const product of products) {
    const analysed=await browserAnalyseStructure(product.smiles,product.name||"Transformation product");
    const productFragments=new Set(analysed.biowin_screen.components.filter(x=>x.smarts).map(x=>x.description));
    const productFeatures=new Set(analysed.structure.features.map(x=>x.key));
    const retainedFragments=[...parentFragments].filter(x=>productFragments.has(x));
    const retainedAlerts=[...parentFeatures].filter(x=>productFeatures.has(x));
    [...retainedFragments,...retainedAlerts].forEach(k=>counts[k]=(counts[k]||0)+1);
    rows.push({name:analysed.name,canonical_smiles:analysed.canonical_smiles,status:product.status||"predicted",matrix:product.matrix,source:product.source,dt50_days:product.dt50_days,retained_biowin_fragments:retainedFragments,retained_structure_alerts:retainedAlerts,analysis:analysed});
  }
  const motif_retention_summary=Object.entries(counts).filter(([,count])=>count).map(([motif,count])=>({motif,products_retaining:count,product_count:rows.length,retention_fraction:rows.length?count/rows.length:0})).sort((a,b)=>b.products_retaining-a.products_retaining||a.motif.localeCompare(b.motif));
  return {model_version:parent.model_version,parent,products:rows,motif_retention_summary,interpretation_rule:"Repeated motif retention across observed or predicted products is a pathway-persistence hypothesis, not proof that the motif controls environmental persistence.",engine:{key:"rdkit-js-wasm-browser"}};
}

function contributionClass(value) {
  if (Number(value) < 0) return "negative";
  if (Number(value) > 0) return "positive";
  return "";
}

function renderEnviroDesign(result) {
  const out = result.outputs || result;
  state.envirodesign = out;
  $('design-b3').textContent = fmt(out.biowin_screen.biowin3_ultimate_score, 5);
  $('design-b4').textContent = fmt(out.biowin_screen.biowin4_primary_score, 5);
  $('design-formula').textContent = out.structure.molecular_formula;
  $('design-mw').textContent = `${fmt(out.structure.molecular_weight_g_mol, 5)} g/mol`;
  $('design-logp').textContent = fmt(out.structure.logp_rdkit, 4);
  $('envirodesign-structure').innerHTML = out.structure_svg || 'No structure image returned.';
  $('envirodesign-status').className = 'design-status';
  const structuralComponents=out.biowin_screen.components.filter(x=>x.smarts);
  $('envirodesign-status').innerHTML = `<strong>${out.structure.aromatic_ring_count} aromatic ring(s) · ${out.structure.features.length} structural region(s)</strong><small>${structuralComponents.length} fitted BIOWIN structural term(s) · browser RDKit depiction · model run ${result.model_run_id || 'not persisted'}</small>`;

  const fitted=structuralComponents;
  const equation=out.biowin_screen.components.filter(x=>!x.smarts);
  $('envirodesign-attribution').innerHTML = fitted.length
    ? fitted.map(row=>{
        const c3=Number(row.biowin3_contribution),c4=Number(row.biowin4_contribution);
        const overall=(c3+c4)/2;
        return `<div class="attribution-row"><div><strong>${row.description}</strong><small>${row.count||1} occurrence(s) · ${plainContribution(overall)}</small></div><div class="attribution-values"><span class="${contributionClass(c3)}">B3 ${c3>=0?'+':''}${fmt(c3,4)}</span><span class="${contributionClass(c4)}">B4 ${c4>=0?'+':''}${fmt(c4,4)}</span></div></div>`;
      }).join('') + `<details class="model-equation-details"><summary>Show intercept and molecular-weight terms</summary>${equation.map(row=>`<div><span>${row.description}</span><strong>B3 ${Number(row.biowin3_contribution)>=0?'+':''}${fmt(row.biowin3_contribution,4)} · B4 ${Number(row.biowin4_contribution)>=0?'+':''}${fmt(row.biowin4_contribution,4)}</strong></div>`).join('')}</details>`
    : `<div class="plain-model-note"><strong>No structure-specific fitted term matched.</strong><p>The whole-molecule intercept and molecular-weight terms still contribute to the score. Structural regions below remain visible because an exact BIOWIN SMARTS miss does not mean the chemistry is irrelevant.</p></div>`;

  const features=(out.structure.features||[]);
  $('envirodesign-features').innerHTML = features.length ? features.map(feature=>{
    const meta=STRUCTURE_REGION_META[feature.key]||{role:'structural alert',tone:'neutral',title:feature.label,explanation:feature.basis};
    const fittedEvidence=featureFittedEvidence(feature,out.biowin_screen.components);
    const fittedText=fittedEvidence
      ? `Overlapping fitted term(s): ${fittedEvidence.labels.join('; ')} · B3 ${fittedEvidence.b3>=0?'+':''}${fmt(fittedEvidence.b3,3)} · B4 ${fittedEvidence.b4>=0?'+':''}${fmt(fittedEvidence.b4,3)}`
      : (feature.key==='benzene_like_aromatic_ring' ? 'No exact fitted aromatic term was applied to this substituted ring pattern.' : 'No direct fitted BIOWIN term assigned to this region.');
    return `<article class="structure-region ${meta.tone}"><div class="region-head"><span>${meta.role}</span><strong>${meta.title}${feature.count>1?` × ${feature.count}`:''}</strong></div><p>${meta.explanation}</p><small>${fittedText}</small></article>`;
  }).join('') : '<span class="feature-chip muted">No additional structural regions detected</span>';

  $('envirodesign-hypotheses').innerHTML = out.design_hypotheses.map((item,index)=>`<article class="hypothesis-card"><span class="hypothesis-number">${String(index+1).padStart(2,'0')}</span><div><h4>${item.feature}</h4><p>${item.hypothesis}</p><details><summary>Evidence and trade-offs</summary><p>${item.why}</p><p><strong>Check:</strong> ${item.tradeoffs.join(', ')}</p><p><strong>Confidence:</strong> ${item.confidence}</p></details></div></article>`).join('');
}


async function runEnviroDesign(persist = true) {
  const button = $("run-envirodesign");
  const smiles = $("envirodesign-smiles").value.trim();
  if (!smiles) { toast("Enter a SMILES structure first."); return; }
  button.disabled = true;
  $("envirodesign-status").className = "design-status running";
  $("envirodesign-status").innerHTML = `<strong>Analysing structure…</strong><small>Loading the browser RDKit/WebAssembly engine and matching the reconstructed SMARTS inventory.</small>`;
  try {
    if (persist) await ensureWorkspace();
    let result;
    try {
      const outputs = await browserAnalyseStructure(smiles,state.chemical?.preferred_name || "Selected chemical");
      result = persist ? await persistBrowserEnviroDesign("ENVIRODESIGN_BROWSER_WASM","EnviroDesign browser/WASM structural attribution",{smiles},outputs) : {model_run_id:null,outputs};
    } catch (browserError) {
      console.warn("Browser RDKit/WASM unavailable; checking optional native backend",browserError);
      const manifest = await api("/api/envirodesign/manifest");
      if (!manifest.runtime?.rdkit_available) throw new Error(`Browser RDKit/WASM could not run: ${browserError.message}. The optional native Python RDKit backend is also unavailable. Core FateIntel remains available.`);
      result = await api("/api/envirodesign/analyse",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({smiles,name:state.chemical?.preferred_name||"Selected chemical",project_id:persist?state.project?.id:null,chemical_id:persist?state.chemical?.id:null,scenario_name:"EnviroDesign native structural attribution",include_svg:true})});
    }
    renderEnviroDesign(result);
    const engine=result.outputs?.engine?.key || "native-python-rdkit";
    $("envirodesign-status").querySelector("small").insertAdjacentText("beforeend",` · engine ${engine}`);
    if (persist) toast("EnviroDesign analysis stored with the project audit trail.");
  } catch (error) {
    console.error(error);
    $("envirodesign-status").className = "design-status error";
    $("envirodesign-status").innerHTML = `<strong>Analysis stopped</strong><small>${error.message}</small>`;
    toast(`EnviroDesign stopped: ${error.message}`,6000);
  } finally { button.disabled = false; }
}

function parseCandidateLines() {
  return $("candidate-smiles").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map((line,index)=>{
    const [name, ...rest] = line.split("|");
    const smiles = rest.join("|").trim();
    if (!smiles) throw new Error(`Candidate line ${index+1} must use Name|SMILES`);
    return {name:name.trim() || `Candidate ${index+1}`, smiles};
  });
}

async function compareEnviroDesignCandidates() {
  const node = $("candidate-results");
  node.innerHTML = `<small>Comparing candidates…</small>`;
  try {
    await ensureWorkspace();
    const candidates = parseCandidateLines();
    const protectedSmarts = $("protected-smarts").value.split(",").map(x=>x.trim()).filter(Boolean);
    const originalSmiles=$("envirodesign-smiles").value.trim();
    let result;
    try {
      const outputs=await browserCompareCandidates(originalSmiles,candidates,protectedSmarts);
      result=await persistBrowserEnviroDesign("ENVIRODESIGN_BROWSER_WASM_COMPARISON","EnviroDesign browser/WASM candidate comparison",{original_smiles:originalSmiles,candidates,protected_smarts:protectedSmarts},outputs);
    } catch(browserError) {
      const manifest=await api("/api/envirodesign/manifest");
      if(!manifest.runtime?.rdkit_available) throw browserError;
      result=await api("/api/envirodesign/compare",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({original_smiles:originalSmiles,candidates,protected_smarts:protectedSmarts,project_id:state.project.id,chemical_id:state.chemical.id,scenario_name:"EnviroDesign native candidate comparison"})});
    }    const rows = result.outputs.candidates;
    node.innerHTML = `<div class="candidate-comparison-grid">${rows.map(row=>{
      const protectedOk=(row.protected_substructures||[]).every(x=>x.preserved);
      const direction=row.screening_direction.startsWith("higher")?"improved biodegradation direction":row.screening_direction.startsWith("lower")?"poorer biodegradation direction":"mixed primary / ultimate direction";
      const mobility=Number(row.logp_delta)<-0.3?"Lower logP may reduce hydrophobic partitioning but could increase mobility; run the soil/groundwater workflow.":Number(row.logp_delta)>0.3?"Higher logP may increase sorption or bioaccumulation concern; rerun the full fate screen.":"No large logP shift detected.";
      return `<article class="candidate-card"><div class="candidate-card-head"><div><strong>${row.name}</strong><small>${row.canonical_smiles}</small></div><span class="${row.screening_direction.startsWith("higher")?"good":row.screening_direction.startsWith("lower")?"bad":"mixed"}">${direction}</span></div><div class="candidate-deltas"><span><small>Δ B3</small><strong>${row.biowin3_delta>=0?"+":""}${fmt(row.biowin3_delta,4)}</strong></span><span><small>Δ B4</small><strong>${row.biowin4_delta>=0?"+":""}${fmt(row.biowin4_delta,4)}</strong></span><span><small>Δ logP</small><strong>${row.logp_delta>=0?"+":""}${fmt(row.logp_delta,3)}</strong></span><span><small>Protected core</small><strong>${protectedOk?"preserved":"changed"}</strong></span></div><p><strong>Environmental readout:</strong> ${mobility}</p><p class="candidate-tradeoffs">${row.tradeoffs.join(" · ")}</p></article>`;
    }).join("")}</div><p class="design-rule"><strong>Rule:</strong> ${result.outputs.ranking_rule} Candidate structures still require complete fate, transformation-product, toxicity and performance assessment.</p>`;
    toast("Candidate comparison stored. Environmental trade-offs are shown without declaring a winner.");
  } catch (error) { node.innerHTML=`<strong>Comparison stopped</strong><br>${error.message}`; toast(error.message,6000); }
}

function parsePathwayLines() {
  return $("pathway-products").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map((line,index)=>{
    const parts=line.split("|").map(x=>x.trim());
    if (parts.length < 2) throw new Error(`Pathway line ${index+1} must use Name|SMILES|status|matrix|source`);
    return {name:parts[0] || `Product ${index+1}`, smiles:parts[1], status:parts[2] || "predicted", matrix:parts[3] || null, source:parts[4] || "User imported pathway"};
  });
}

function pathwayDisplayName(node, fallback = "Transformation product") {
  return node?.name || fallback;
}

function renderTransformationPathway(out) {
  const resultNode = $("pathway-results");
  const nodes = out.pathway?.nodes || [];
  const edges = out.pathway?.edges || [];
  const byId = new Map(nodes.map(node => [node.id,node]));
  const displayNodes = nodes.slice(0,80);
  const generations = [...new Set(displayNodes.map(node => Number(node.generation) || 0))].sort((a,b)=>a-b);
  const productCount = out.summary?.unique_product_count || 0;
  const providerLabel = (out.provider?.provider_name || "Provider").toUpperCase();
  const resultLabel = out.products?.[0]?.status === "database_curated" ? "curated" : "predicted";
  const generationMarkup = generations.map(generation => {
    const generationNodes = displayNodes.filter(node => Number(node.generation || 0) === generation);
    return `<section class="tp-generation"><header><span>${generation===0?"Parent":`Generation ${generation}`}</span><small>${generationNodes.length} structure${generationNodes.length===1?"":"s"}</small></header><div>${generationNodes.map(node=>`<article class="tp-node ${node.role==="parent"?"parent":"predicted"}"><strong>${escapeHtml(pathwayDisplayName(node))}</strong><code>${escapeHtml(node.smiles)}</code><small>${escapeHtml(node.formula || "Formula not returned")}${node.monoisotopic_mass_da!=null?` · ${fmt(node.monoisotopic_mass_da,7)} Da`:""}</small><em>${node.role==="parent"?"submitted parent":`${resultLabel === "curated" ? "database curated" : "model predicted"}`}</em></article>`).join("")}</div></section>`;
  }).join("");
  const edgeMarkup = edges.slice(0,16).map(edge => {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    return `<div class="tp-edge"><span>${escapeHtml(pathwayDisplayName(source,"Parent"))}</span><i>→</i><span>${escapeHtml(pathwayDisplayName(target))}</span><small>${escapeHtml(edge.reaction_type || "Environmental microbial transformation")}${edge.enzyme_or_biosystem?` · ${escapeHtml(edge.enzyme_or_biosystem)}`:""}</small></div>`;
  }).join("");
  resultNode.innerHTML = `<div class="tp-summary"><div><span>${escapeHtml(providerLabel)}</span><strong>${productCount} ${resultLabel} product${productCount===1?"":"s"}</strong></div><div><small>Provider query</small><strong>${escapeHtml(out.query?.provider_query_id || "—")}</strong></div><div><small>Reaction edges</small><strong>${edges.length}</strong></div><div><small>Maximum generation</small><strong>${out.summary?.maximum_generation || 0}</strong></div></div><div class="tp-network">${generationMarkup}</div>${nodes.length>80?`<p class="tp-display-limit">Interactive diagram shows the first 80 of ${nodes.length} nodes. The saved output retains the complete normalised graph.</p>`:""}${edges.length?`<details class="tp-reactions"><summary>Review ${edges.length} ${resultLabel} reaction edge${edges.length===1?"":"s"}</summary>${edgeMarkup}${edges.length>16?`<p>${edges.length-16} additional edges remain in the saved model output.</p>`:""}</details>`:""}<div class="tp-quantitative-boundary"><strong>Qualitative pathway only</strong><span>Formation fractions, rate constants and TP degradation must be fitted separately from reviewed time-series data.</span></div>`;
}

async function predictTransformationPathway() {
  const button = $("predict-transformation-pathway");
  const status = $("pathway-provider-status");
  const parentSmiles = $("envirodesign-smiles").value.trim();
  if (!parentSmiles) { toast("Enter a parent SMILES before predicting the pathway."); return; }
  const provider = $("pathway-provider")?.value || "biotransformer";
  const envipathPackageId = $("envipath-package-id")?.value.trim();
  if (provider === "envipath" && !envipathPackageId) {
    toast("Enter an enviPath package id before predicting with enviPath."); return;
  }
  const providerLabel = provider === "envipath" ? "enviPath" : "BioTransformer ENVMICRO";
  button.disabled = true;
  status.className = "pathway-provider-status running";
  status.innerHTML = `<span>RUNNING</span><p>Submitting one parent to ${escapeHtml(providerLabel)} and waiting for the predicted pathway…</p>`;
  $("pathway-results").innerHTML = `<small>Generating environmental microbial transformation products…</small>`;
  try {
    await ensureWorkspace();
    const result = await api("/api/transformation-pathways/predict",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        provider,
        parent_smiles:parentSmiles,
        parent_name:state.chemical?.preferred_name || "Selected parent",
        number_of_steps:Number($("pathway-generations").value || 1),
        ...(provider === "envipath" ? {envipath_package_id:envipathPackageId} : {}),
        project_id:state.project.id,
        chemical_id:state.chemical.id,
        scenario_name:`${providerLabel} environmental pathway prediction`,
      }),
    });
    const out = result.outputs;
    state.transformationPathway = out;
    const availableProducts = out.products || [];
    const editable = availableProducts.slice(0,100).map(product => [
      String(product.name || "Transformation product").replaceAll("|","/"),
      product.smiles,
      "predicted",
      product.matrix || "generic environmental microbial (soil/water)",
      product.source || `${providerLabel} query ${out.query?.provider_query_id || "unknown"}`,
    ].join("|"));
    $("pathway-products").value = editable.join("\n");
    renderTransformationPathway(out);
    status.className = "pathway-provider-status complete";
    const importNote = availableProducts.length > editable.length ? `${editable.length} of ${availableProducts.length}` : `${editable.length}`;
    status.innerHTML = `<span>REVIEW</span><p>${importNote} predicted product(s) imported into the editable scientist-review list. Confirm structures and evidence status before downstream use.</p>`;
    toast(`${providerLabel} pathway saved. Review the predicted products before motif or fate analysis.`,6000);
  } catch(error) {
    console.error(error);
    status.className = "pathway-provider-status error";
    status.innerHTML = `<span>STOPPED</span><p>${escapeHtml(error.message)}</p>`;
    $("pathway-results").innerHTML = `<strong>Prediction stopped</strong><br>${escapeHtml(error.message)}`;
    toast(error.message,6000);
  } finally {
    button.disabled = false;
  }
}

function renderCuratedPathwaySearchResults(result) {
  const resultNode = $("pathway-results");
  const pathways = result.pathways || [];
  if (!pathways.length) {
    resultNode.innerHTML = `<small>${escapeHtml((result.warnings || [])[0] || "No curated enviPath pathway matched this compound.")}</small>`;
    return;
  }
  const cards = pathways.map((pathway, index) => {
    const products = pathway.products || [];
    const productList = products.map(p => `<li><strong>${escapeHtml(p.name)}</strong> <code>${escapeHtml(p.smiles)}</code></li>`).join("");
    return `<article class="tp-node predicted" style="margin-bottom:12px">
      <strong>DATABASE CURATED · ${escapeHtml(pathway.query?.package_name || "enviPath package")}</strong>
      <small>${products.length} product${products.length===1?"":"s"} · ${pathway.summary?.reaction_edge_count || 0} reaction edge(s)</small>
      <ul>${productList}</ul>
      <button class="ghost-button" data-copy-curated-pathway="${index}" type="button">Copy into review list</button>
    </article>`;
  }).join("");
  resultNode.innerHTML = `<div class="tp-summary"><div><span>ENVIPATH CURATED</span><strong>${pathways.length} matching pathway${pathways.length===1?"":"s"}</strong></div></div>${cards}`;
  resultNode.querySelectorAll("[data-copy-curated-pathway]").forEach(button => {
    button.addEventListener("click", () => {
      const pathway = pathways[Number(button.dataset.copyCuratedPathway)];
      const existing = $("pathway-products").value.split("\n").filter(Boolean);
      const additions = (pathway.products || []).map(product => [
        String(product.name || "Transformation product").replaceAll("|","/"),
        product.smiles,
        "database_curated",
        product.matrix || "enviPath package",
        product.source || pathway.query?.package_name || "enviPath",
      ].join("|"));
      $("pathway-products").value = [...existing, ...additions].join("\n");
      toast(`${additions.length} curated product(s) copied into the review list.`,5000);
    });
  });
}

async function searchEnvipathCuratedPathways() {
  const button = $("search-envipath-curated");
  const status = $("pathway-provider-status");
  const parentSmiles = $("envirodesign-smiles").value.trim();
  if (!parentSmiles) { toast("Enter a parent SMILES before searching enviPath."); return; }
  button.disabled = true;
  status.className = "pathway-provider-status running";
  status.innerHTML = `<span>RUNNING</span><p>Searching enviPath's curated packages for this parent…</p>`;
  $("pathway-results").innerHTML = `<small>Searching curated pathways…</small>`;
  try {
    const params = new URLSearchParams({parent_smiles:parentSmiles});
    const result = await api(`/api/transformation-pathways/search-curated?${params}`);
    renderCuratedPathwaySearchResults(result);
    status.className = "pathway-provider-status complete";
    status.innerHTML = `<span>REVIEW</span><p>${result.pathway_count} curated pathway(s) found. Copy any relevant products into the review list before downstream use.</p>`;
  } catch(error) {
    console.error(error);
    status.className = "pathway-provider-status error";
    status.innerHTML = `<span>STOPPED</span><p>${escapeHtml(error.message)}</p>`;
    $("pathway-results").innerHTML = `<strong>Search stopped</strong><br>${escapeHtml(error.message)}`;
    toast(error.message,6000);
  } finally {
    button.disabled = false;
  }
}

async function analysePathwayRetention() {
  const node=$("pathway-results");
  node.innerHTML=`<small>Analysing motif retention…</small>`;
  try {
    const products=parsePathwayLines();
    if(!products.length) throw new Error("Add at least one observed or predicted transformation product.");
    await ensureWorkspace();
    const parentSmiles=$("envirodesign-smiles").value.trim();
    let result;
    try {
      const outputs=await browserPathwayRetention(parentSmiles,products);
      result=await persistBrowserEnviroDesign("ENVIRODESIGN_BROWSER_WASM_PATHWAY","EnviroDesign browser/WASM pathway retention",{parent_smiles:parentSmiles,products},outputs);
    } catch(browserError) {
      const manifest=await api("/api/envirodesign/manifest");
      if(!manifest.runtime?.rdkit_available) throw browserError;
      result=await api("/api/envirodesign/pathway-retention",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({parent_smiles:parentSmiles,products,project_id:state.project.id,chemical_id:state.chemical.id,scenario_name:"EnviroDesign native pathway retention"})});
    }
    const out=result.outputs;
    const motifs=out.motif_retention_summary.slice(0,10);
    node.innerHTML=`<strong>${out.products.length} product(s) analysed</strong>${motifs.length?motifs.map(m=>`<div class="motif-bar"><span>${m.motif.replaceAll("_"," ")}</span><i style="--retention:${Math.round(m.retention_fraction*100)}%"></i></div>`).join(""):`<p>No parent fitted fragment or structure alert was retained across the imported products.</p>`}<p>${out.interpretation_rule}</p>`;
    toast("Pathway-retention analysis stored with matrix and provenance fields.");
  } catch(error){node.innerHTML=`<strong>Pathway analysis stopped</strong><br>${error.message}`;toast(error.message,6000);}
}

function pearlNumber(id) {
  const node = $(id);
  const value = Number(node?.value);
  if (!Number.isFinite(value)) throw new Error(`Invalid value for ${id}`);
  return value;
}

function optionalPearlNumber(id) {
  const raw = $(id)?.value?.trim();
  if (raw === undefined || raw === null || raw === "") return null;
  const value = Number(raw);
  if (!Number.isFinite(value)) throw new Error(`Invalid value for ${id}`);
  return value;
}

function selectedPearlScenario() {
  const key = $("pearl-focus-scenario")?.value || "okehampton";
  return state.focusScenarios.find(row => row.key === key) || null;
}

function scenarioTopFoc(scenario) {
  if (!scenario) return optionalPearlNumber("pearl-foc");
  if (scenario.horizons?.length) return Number(scenario.horizons[0].organic_carbon_percent) / 100;
  if (scenario.topsoil_organic_matter_percent != null) return Number(scenario.topsoil_organic_matter_percent) / 1.724 / 100;
  return optionalPearlNumber("pearl-foc");
}

function updatePearlTierPreview() {
  const mode = $("pearl-input-mode")?.value || "application_rate";
  const scenario = selectedPearlScenario();
  const scenarioName = scenario?.name || "User profile";
  $("tier-scenario-value").textContent = scenarioName;
  if (mode === "application_rate") {
    const rate = Number($("pearl-app-rate")?.value || 0);
    const interception = Number($("pearl-interception")?.value || 0);
    const effective = rate * (1 - interception / 100);
    $("tier-application-value").textContent = `${fmt(rate,4)} kg/ha × ${fmt(100-interception,4)}%`;
    const depth = Number($("pearl-pecsoil-depth")?.value || 0.05);
    let bulk = Number($("pearl-bulk-density")?.value || 1350);
    if ($("pearl-profile-mode")?.value === "focus_scenario" && scenario?.horizons?.length) bulk = Number(scenario.horizons[0].bulk_density_kg_m3);
    const soilMass = bulk * depth * 10000;
    const pec = soilMass > 0 ? effective * 1e9 / soilMass : 0;
    $("tier-pecsoil-value").textContent = `${fmt(pec,5)} µg/kg initial`;
    $("pearl-surface-label").textContent = `${fmt(rate,4)} kg/ha · ${fmt(effective,4)} kg/ha reaches soil`;
  } else {
    const concentration = Number($("pearl-initial-conc")?.value || 0);
    $("tier-application-value").textContent = "Existing soil exposure";
    $("tier-pecsoil-value").textContent = `${fmt(concentration,5)} µg/kg`;
    $("pearl-surface-label").textContent = `Existing PECsoil · ${fmt(concentration,5)} µg/kg`;
  }
  $("tier-pecgw-value").textContent = state.pearl ? $("tier-pecgw-value").textContent : "PECgw pending";
}

function updatePearlModeUI() {
  const applicationMode = ($("pearl-input-mode")?.value || "application_rate") === "application_rate";
  $("pearl-existing-pecsoil")?.classList.toggle("hidden", applicationMode);
  ["pearl-app-rate","pearl-app-count","pearl-app-interval","pearl-interception","pearl-frequency","pearl-app-day","pearl-app-method","pearl-incorporation-depth","pearl-pecsoil-depth"].forEach(id => {
    if ($(id)) $(id).disabled = !applicationMode;
  });
  const useFocus = ($("pearl-profile-mode")?.value || "focus_scenario") === "focus_scenario";
  $("pearl-user-profile")?.classList.toggle("hidden", useFocus);
  if ($("pearl-focus-scenario")) $("pearl-focus-scenario").disabled = !useFocus;
  if ($("pearl-focus-crop")) $("pearl-focus-crop").disabled = !useFocus;
  updatePearlScenarioUI();
}

function updatePearlScenarioUI() {
  const scenario = selectedPearlScenario();
  const useFocus = ($("pearl-profile-mode")?.value || "focus_scenario") === "focus_scenario";
  const cropSelect = $("pearl-focus-crop");
  if (cropSelect && scenario) {
    const current = cropSelect.value;
    cropSelect.innerHTML = (scenario.crops || []).map(crop => `<option value="${crop}">${crop.replace(/\b\w/g,m=>m.toUpperCase())}</option>`).join("");
    cropSelect.value = (scenario.crops || []).includes(current) ? current : ((scenario.crops || []).includes("winter cereals") ? "winter cereals" : (scenario.crops || [""])[0]);
  }
  if (scenario && useFocus) {
    const profileNote = scenario.native_profile_status === "depth_profile_transcribed" ? "depth-resolved native profile" : "official choice; native profile uses editable screening soil";
    const gw = scenario.groundwater_depth_context_m ? ` · groundwater context ${fmt(scenario.groundwater_depth_context_m,3)} m` : "";
    $("pearl-scenario-summary").textContent = `${scenario.name} (${scenario.code}) · ${scenario.topsoil_texture} · ${fmt(scenario.annual_rainfall_mm,5)} mm/year · ${fmt(scenario.topsoil_organic_matter_percent,4)}% topsoil OM · ${scenario.lower_boundary}${gw} · ${profileNote}.`;
    if (scenario.focus_target_depth_m) $("pearl-target-depth").value = scenario.focus_target_depth_m;
    const depth = Number(scenario.profile_depth_m || $("pearl-profile-depth")?.value || 1.2);
    const layers = scenario.horizons?.length ? scenario.horizons.reduce((sum,h)=>{
      const step = Number(h.top_m) < 0.5 ? 0.025 : (Number(h.top_m) < 1 ? 0.05 : 0.10);
      return sum + Math.max(1,Math.round((Number(h.bottom_m)-Number(h.top_m))/step));
    },0) : Number($("pearl-layers")?.value || 12);
    pearlRenderStatic(depth,layers,Number($("pearl-target-depth")?.value||1),scenario);
    $("pearl-status").textContent = `Ready · ${scenario.name} ${$("pearl-horizon-mode")?.value === "focus_standard" ? "FOCUS-style horizon" : "quick screen"}`;
  } else {
    $("pearl-scenario-summary").textContent = "User-defined uniform profile. This is a native screening scenario, not an official locked FOCUS scenario.";
    pearlRenderStatic(Number($("pearl-profile-depth")?.value||1.2),Number($("pearl-layers")?.value||12),Number($("pearl-target-depth")?.value||1),null);
    $("pearl-status").textContent = "Ready · user-defined quick screen";
  }
  updatePearlTierPreview();
}

async function loadPearlScenarios() {
  try {
    state.focusScenarios = await api("/api/pearl/focus-scenarios");
    const select = $("pearl-focus-scenario");
    if (select) {
      const selected = select.value || "okehampton";
      select.innerHTML = state.focusScenarios.map(row => `<option value="${row.key}">${row.name} (${row.code})${row.native_profile_status === "depth_profile_transcribed" ? " · native profile" : ""}</option>`).join("");
      select.value = state.focusScenarios.some(row=>row.key===selected) ? selected : "okehampton";
    }
    updatePearlScenarioUI();
  } catch (error) {
    console.error(error);
    $("pearl-scenario-summary").textContent = `Scenario register unavailable: ${error.message}`;
  }
}

function pearlPayload() {
  const scenario = selectedPearlScenario();
  const profileMode = $("pearl-profile-mode")?.value || "focus_scenario";
  const inputMode = $("pearl-input-mode")?.value || "application_rate";
  const temperatureOverride = optionalPearlNumber("pearl-temperature");
  const rootDepth = scenario?.crop_parameters?.[$("pearl-focus-crop")?.value]?.root_depth_m || Math.min(Number($("pearl-mixing-depth")?.value||0.4),Number(scenario?.profile_depth_m||$("pearl-profile-depth")?.value||1.2));
  const foc = profileMode === "focus_scenario" ? scenarioTopFoc(scenario) : optionalPearlNumber("pearl-foc");
  return {
    project_id: state.project.id,
    chemical_id: state.chemical.id,
    scenario_name: `${scenario?.name || "User-defined"} tiered application → PECsoil → PECgw`,
    chemical_name: state.chemical?.preferred_name || "Selected chemical",
    input_mode: inputMode,
    profile_mode: profileMode,
    application_rate_kg_ha: inputMode === "application_rate" ? pearlNumber("pearl-app-rate") : null,
    number_applications: Math.round(pearlNumber("pearl-app-count")),
    application_interval_days: pearlNumber("pearl-app-interval"),
    crop_interception_percent: pearlNumber("pearl-interception"),
    application_frequency_years: Number($("pearl-frequency")?.value || 1),
    first_application_day_of_year: pearlNumber("pearl-app-day"),
    application_method: $("pearl-app-method")?.value || "surface",
    incorporation_depth_m: pearlNumber("pearl-incorporation-depth"),
    pecsoil_mixing_depth_m: pearlNumber("pearl-pecsoil-depth"),
    initial_soil_concentration_ug_kg: inputMode === "pecsoil" ? pearlNumber("pearl-initial-conc") : 0,
    layer_initial_concentrations_ug_kg: null,
    initial_mixing_depth_m: pearlNumber("pearl-mixing-depth"),
    focus_scenario: profileMode === "focus_scenario" ? (scenario?.key || "okehampton") : null,
    focus_crop: profileMode === "focus_scenario" ? ($("pearl-focus-crop")?.value || null) : null,
    focus_target_depth_m: pearlNumber("pearl-target-depth"),
    groundwater_threshold_ug_l: pearlNumber("pearl-gw-threshold"),
    assessment_horizon_mode: $("pearl-horizon-mode")?.value || "quick_screen",
    screening_recharge_fraction: 0.35,
    profile_depth_m: pearlNumber("pearl-profile-depth"),
    n_layers: Math.round(pearlNumber("pearl-layers")),
    bulk_density_kg_m3: pearlNumber("pearl-bulk-density"),
    volumetric_water_content: pearlNumber("pearl-theta"),
    organic_carbon_fraction: foc,
    kd_l_kg: optionalPearlNumber("pearl-kd"),
    koc_l_kg: optionalPearlNumber("pearl-koc"),
    freundlich_exponent: pearlNumber("pearl-freundlich"),
    reference_concentration_mg_l: 1,
    soil_dt50_days: pearlNumber("pearl-dt50"),
    temperature_c: temperatureOverride ?? Number(scenario?.mean_annual_temperature_c ?? 20),
    temperature_ref_c: 20,
    activation_energy_kj_mol: 65.4,
    moisture_exponent: 0,
    depth_transformation_half_depth_m: null,
    simulation_days: pearlNumber("pearl-duration"),
    time_step_days: 1,
    max_transport_substep_days: 0.25,
    percolation_mm_day: optionalPearlNumber("pearl-percolation"),
    dispersivity_m: pearlNumber("pearl-dispersivity"),
    molecular_diffusion_m2_d: 0.00001,
    root_water_uptake_mm_day: 0,
    root_depth_m: Number(rootDepth),
    root_uptake_factor: 0,
    molecular_weight_g_mol: optionalPearlNumber("pearl-mw"),
    water_solubility_mg_l: optionalPearlNumber("pearl-solubility"),
    vapour_pressure_pa: optionalPearlNumber("pearl-vapour"),
    pka: null,
    metabolite_scheme: null,
    swap_state_sampling: "end",
    swap_bottom_flux_sign: 1,
    swap_q_flux_sign: 1,
    swap_drop_initial_row: true,
  };
}

const PEARL_PLOT_GEOMETRY = Object.freeze({left:55, right:845, top:105, height:225, groundwaterTop:330});

function pearlRenderStatic(profileDepth, nLayers, targetDepth=1, scenario=null) {
  const lines = $("pearl-layer-lines");
  if (!lines) return;
  const {left, right, top, height} = PEARL_PLOT_GEOMETRY;
  const bottom = top + height;
  const layerHeight = height / Math.max(nLayers,1);
  const labelEvery = Math.max(1,Math.ceil(nLayers/10));
  let layerMarkup = Array.from({length:nLayers}, (_,i) => {
    const y = top + i * layerHeight;
    const depth = profileDepth * i / nLayers;
    const label = i % labelEvery === 0 ? `<text class="pearl-layer-label" x="796" y="${y+9}">${depth.toFixed(2)} m</text>` : "";
    return `<line class="pr-layer-line" x1="${left}" y1="${y}" x2="${right}" y2="${y}"/>${label}`;
  }).join("");
  if (scenario?.horizons?.length) {
    layerMarkup += scenario.horizons.slice(1).map(h=>{
      const y=top+(Number(h.top_m)/profileDepth)*height;
      return `<line class="pr-horizon-line" x1="${left}" y1="${y}" x2="${right}" y2="${y}"/><text class="pr-horizon-label" x="62" y="${y+12}">${h.name}</text>`;
    }).join("");
  }
  lines.innerHTML = layerMarkup + `<line class="pr-soil-base" x1="${left}" y1="${bottom}" x2="${right}" y2="${bottom}"/>`;
  $("pearl-depth-label").textContent = `${fmt(profileDepth,3)} m`;
  const targetY = top + Math.min(Math.max(targetDepth/profileDepth,0),1) * height;
  $("pearl-target-line").innerHTML = `<line class="pr-target" x1="${left}" y1="${targetY}" x2="${right}" y2="${targetY}"/><text class="pr-target-label" x="70" y="${Math.max(top+17,targetY-7)}">FOCUS PECgw assessment plane · ${fmt(targetDepth,3)} m</text>`;
  const arrowXs = [275,395,515,635];
  $("pearl-flow-arrows").innerHTML = arrowXs.map((x,i)=>{
    const y1=top+35+(i%2)*13, y2=Math.max(y1+36,targetY-8);
    return `<path class="pr-arrow percolation" d="M${x} ${y1} C${x-9} ${y1+36},${x+9} ${y2-36},${x} ${y2}"/>`;
  }).join("");
  if ($("pearl-profile-title")) $("pearl-profile-title").textContent = `${scenario?.name || "User-defined"} soil profile`;
  const context = scenario?.groundwater_depth_context_m ? `Scenario groundwater context: approximately ${fmt(scenario.groundwater_depth_context_m,3)} m; regulatory solute flux evaluated at ${fmt(targetDepth,3)} m.` : `Groundwater is the final assessment compartment; solute flux is evaluated at ${fmt(targetDepth,3)} m.`;
  $("pearl-groundwater-context").textContent = context;
}

function pearlRenderSnapshot(index) {
  if (!state.pearl) return;
  const out = state.pearl.outputs || state.pearl;
  const snapshots = out.profile_snapshots;
  const snapshot = snapshots[Math.max(0, Math.min(index, snapshots.length-1))];
  const profile = snapshot.profile;
  const depth = out.resolved_inputs.profile_depth_m;
  const targetDepth = out.resolved_inputs.focus_target_depth_m || 1;
  const scenario = out.resolved_inputs.focus_scenario;
  const maxAcross = Math.max(...snapshots.flatMap(s=>s.profile.map(r=>r.total_soil_concentration_ug_kg)), 1e-18);
  const maxLiquid = Math.max(...snapshots.flatMap(s=>s.profile.map(r=>r.liquid_concentration_ug_l)), 1e-18);
  pearlRenderStatic(depth, profile.length, targetDepth, scenario);

  const particles=[];
  profile.forEach((row, layerIndex)=>{
    const totalNorm = Math.log10(1 + 9 * row.total_soil_concentration_ug_kg / maxAcross);
    const liquidNorm = Math.log10(1 + 9 * row.liquid_concentration_ug_l / maxLiquid);
    const count = Math.max(0, Math.round(totalNorm * 7));
    for(let j=0;j<count;j++){
      const seed=(layerIndex+1)*97+(j+1)*53;
      const x=90+((seed*37)%700);
      const y=PEARL_PLOT_GEOMETRY.top+(row.centre_depth_m/depth)*PEARL_PLOT_GEOMETRY.height+(((seed*19)%15)-7);
      const dissolved=j < Math.round(liquidNorm*count);
      particles.push(`<circle cx="${x}" cy="${y}" r="${dissolved?3.5:4.5}" fill="${dissolved?'#2a7c88':'#8d724e'}" opacity="${0.35+0.5*totalNorm}"><title>${row.horizon} · layer ${row.layer}: ${fmt(row.total_soil_concentration_ug_kg,4)} µg/kg; liquid ${fmt(row.liquid_concentration_ug_l,4)} µg/L</title></circle>`);
    }
  });
  const ts = out.timeseries.reduce((best,row)=>Math.abs(row.time_d-snapshot.time_d)<Math.abs(best.time_d-snapshot.time_d)?row:best,out.timeseries[0]);
  const endpoint = out.summary.focus_style_80th_percentile_ug_l ?? out.summary.groundwater_flux_weighted_average_ug_l;
  const gwCount=Math.min(18,Math.round(Math.log10(1+9*Math.max(ts.cumulative_groundwater_concentration_ug_l,0)/Math.max(endpoint,1e-18))*12));
  for(let j=0;j<gwCount;j++){
    const x=90+((j*139)%700), y=342+((j*47)%32);
    particles.push(`<circle cx="${x}" cy="${y}" r="3.5" fill="#2a7c88" opacity=".68"><title>Groundwater endpoint concentration</title></circle>`);
  }
  $("pearl-particles").innerHTML=particles.join("");

  const maxProfile=Math.max(...profile.map(r=>r.total_soil_concentration_ug_kg),1e-18);
  const pts=profile.map(row=>{
    const x=735+88*Math.log10(1+9*row.total_soil_concentration_ug_kg/maxProfile);
    const y=PEARL_PLOT_GEOMETRY.top+(row.centre_depth_m/depth)*PEARL_PLOT_GEOMETRY.height;
    return {x,y};
  });
  $("pearl-profile-line").innerHTML=`<path class="pearl-profile-path" d="${pts.map((p,i)=>`${i?'L':'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')}"/>${pts.map(p=>`<circle class="pearl-profile-dot" cx="${p.x}" cy="${p.y}" r="2.8"/>`).join('')}`;

  $("pearl-time-label").textContent=`Day ${fmt(snapshot.time_d,6)}`;
  $("pearl-time-slider").value=String(index);
  $("pearl-layer-table").innerHTML=`<table class="pearl-table"><thead><tr><th>Horizon / layer / depth</th><th>Total µg/kg</th><th>Liquid µg/L</th><th>Sorbed µg/kg</th></tr></thead><tbody>${profile.map(row=>`<tr><td><strong>${row.horizon}</strong> · ${row.layer} · ${fmt(row.top_depth_m)}–${fmt(row.bottom_depth_m)} m</td><td>${fmt(row.total_soil_concentration_ug_kg,5)}</td><td>${fmt(row.liquid_concentration_ug_l,5)}</td><td>${fmt(row.sorbed_concentration_ug_kg,5)}</td></tr>`).join('')}</tbody></table>`;
}



const TOXSWA_USE_GROUP = {
  pharmaceutical: "human_pharmaceutical",
  veterinary: "veterinary_pharmaceutical",
  industrial: "industrial_organic",
  laboratory: "emerging_contaminant",
  agriculture: "pesticide",
  consumer: "mixture_formulation",
  waste: "emerging_contaminant",
};

function toxswaNumber(id, fallback = 0) {
  const node = $(id);
  const value = node ? Number(node.value) : Number(fallback);
  return Number.isFinite(value) ? value : Number(fallback);
}

function toxswaGroupForUse() {
  return TOXSWA_USE_GROUP[state.use] || "emerging_contaminant";
}

function setToxswaLoadMode(mode) {
  if ($("toxswa-loading-mode")) $("toxswa-loading-mode").value = mode;
  $$(".toxswa-load-fields").forEach((node) => {
    const modes = String(node.dataset.loadMode || "").split(/\s+/).filter(Boolean);
    node.classList.toggle("hidden", !modes.includes(mode));
  });
  const labels = {
    continuous_point_discharge: "continuous point source",
    spray_drift: "distributed pulse deposition",
    lateral_drainage: "distributed drainage loading",
    lateral_runoff: "distributed runoff loading",
    continuous_distributed: "continuous distributed mass input",
    pulse_mass: "one-off point / distributed pulse",
  };
  if ($("toxswa-loading-caption")) $("toxswa-loading-caption").textContent = labels[mode] || mode.replaceAll("_", " ");
}

function toxswaRouteRow(group) {
  return state.toxswaManifest?.routing?.[group] || null;
}

function renderToxswaRoute(group, row) {
  const route = row || toxswaRouteRow(group);
  if (!route || !$("toxswa-route-note")) return;
  const label = $("toxswa-group")?.selectedOptions?.[0]?.textContent || group.replaceAll("_", " ");
  const status = String(route.applicability || "adapted").replaceAll("_", " ");
  $("toxswa-route-note").innerHTML = `<strong>${label} · ${status}</strong><span>${route.regulatory_note}</span>`;
  $("toxswa-route-note").classList.toggle("limited", ["limited","not_quantitative","component_based"].includes(route.applicability));
}

async function updateToxswaRoute({applyDefault = false} = {}) {
  const group = $("toxswa-group")?.value || toxswaGroupForUse();
  let row = toxswaRouteRow(group);
  if (!row) {
    try { row = await api(`/api/toxswa/route/${group}`); }
    catch (error) { console.error(error); }
  }
  if (row && applyDefault) setToxswaLoadMode(row.default_loading_mode);
  else setToxswaLoadMode($("toxswa-loading-mode")?.value || row?.default_loading_mode || "continuous_point_discharge");
  renderToxswaRoute(group, row);
}

async function loadToxswaManifest() {
  try {
    state.toxswaManifest = await api("/api/toxswa/manifest");
    updateToxswaRoute();
    const install = state.toxswaManifest?.installation_status?.items || state.toxswaManifest?.installation_status?.models || [];
    const tox = Array.isArray(install) ? install.find(row => String(row.key || row.name || "").toLowerCase().includes("toxswa")) : null;
    if ($("toxswa-import-status") && tox?.detected) $("toxswa-import-status").textContent = "Official FOCUS_TOXSWA installation detected · no result imported yet.";
  } catch (error) {
    console.error(error);
    if ($("toxswa-import-status")) $("toxswa-import-status").textContent = `TOXSWA manifest unavailable · ${error.message}`;
  }
}

function syncToxswaFromScreening() {
  const group = toxswaGroupForUse();
  if ($("toxswa-group")) $("toxswa-group").value = group;
  const route = toxswaRouteRow(group);
  let mode = route?.default_loading_mode || "continuous_point_discharge";

  // The wastewater chain already has an auditable effluent concentration and flow.
  // Re-use those as TOXSWA loading inputs, then use receiving flow to represent the
  // selected dilution. This keeps application/use mass separate from waterbody fate.
  if (state.results?.wwtp && ["wastewater","irrigation","biosolids"].includes(state.release)) {
    mode = "continuous_point_discharge";
    const effluent = Number(state.results.wwtp.outputs.effluent_concentration_ug_l || 0);
    const population = toxswaNumber("population", 100000);
    const waterPerPerson = toxswaNumber("water-per-person", 200);
    const dischargeFlow = population * waterPerPerson / 1000;
    const dilution = Math.max(1, toxswaNumber("dilution", 10));
    if ($("toxswa-discharge-conc")) $("toxswa-discharge-conc").value = effluent;
    if ($("toxswa-discharge-flow")) $("toxswa-discharge-flow").value = dischargeFlow;
    if ($("toxswa-flow")) $("toxswa-flow").value = dischargeFlow * dilution;
    if ($("toxswa-waterbody")) $("toxswa-waterbody").value = "stream";
    // A 40,000 m³ modelled reach gives a transparent, numerically tractable
    // receiving-water residence time with the pilot 200,000 m³/day flow.
    if ($("toxswa-length")) $("toxswa-length").value = 1000;
    if ($("toxswa-width")) $("toxswa-width").value = 20;
    if ($("toxswa-depth")) $("toxswa-depth").value = 2;
  }
  if (group === "pesticide" && !state.results?.wwtp) mode = "spray_drift";

  const selectedKoc = Number(state.results?.sorption?.outputs?.selected?.koc_l_kg);
  if (Number.isFinite(selectedKoc) && $("toxswa-koc")) $("toxswa-koc").value = selectedKoc;
  setToxswaLoadMode(mode);
  renderToxswaRoute(group, route);
  if ($("toxswa-status") && state.results?.wwtp && mode === "continuous_point_discharge") {
    $("toxswa-status").textContent = `Ready from Tier 1–2 · ${fmt(state.results.wwtp.outputs.effluent_concentration_ug_l,5)} µg/L effluent`;
  }
}

function toxswaPayload() {
  const length = toxswaNumber("toxswa-length", 1000);
  const mode = $("toxswa-loading-mode")?.value || "continuous_point_discharge";
  return {
    project_id: state.project.id,
    chemical_id: state.chemical.id,
    chemical_name: state.chemical?.preferred_name || "Selected chemical",
    scenario_name: `${$("toxswa-group")?.selectedOptions?.[0]?.textContent || "Chemical"} · ${mode.replaceAll("_", " ")} surface-water screen`,
    contaminant_group: $("toxswa-group")?.value || "emerging_contaminant",
    regulatory_context: FOCUS_REGIONS.has(state.modelSystem) ? "EU/UK/CH adapted surface-water refinement" : "Adapted surface-water refinement",
    waterbody_type: $("toxswa-waterbody")?.value || "stream",
    waterbody_length_m: length,
    waterbody_width_m: toxswaNumber("toxswa-width", 20),
    water_depth_m: toxswaNumber("toxswa-depth", 2),
    receiving_flow_m3_day: toxswaNumber("toxswa-flow", 200000),
    n_segments: Math.round(toxswaNumber("toxswa-segments", 20)),
    sediment_active_depth_m: toxswaNumber("toxswa-sed-depth", 0.05),
    sediment_bulk_density_kg_m3: toxswaNumber("toxswa-sed-density", 800),
    sediment_porosity: 0.6,
    sediment_organic_carbon_fraction: toxswaNumber("toxswa-sed-foc", 0.0522),
    suspended_solids_mg_l: toxswaNumber("toxswa-ss", 15),
    suspended_solids_organic_carbon_fraction: 0.2,
    molecular_weight_g_mol: state.chemical?.molecular_weight_g_mol || null,
    koc_l_kg: toxswaNumber("toxswa-koc", 281.7),
    sediment_kd_l_kg: null,
    suspended_solids_kd_l_kg: null,
    freundlich_exponent: 1,
    reference_concentration_mg_l: 1,
    water_dt50_days: toxswaNumber("toxswa-water-dt50", 40),
    sediment_dt50_days: toxswaNumber("toxswa-sed-dt50", 80),
    transformation_reference_temperature_c: 20,
    water_temperature_c: 20,
    activation_energy_kj_mol: 65.4,
    water_transformation_mode: $("toxswa-transform-mode")?.value || "lumped",
    aqueous_diffusion_coefficient_m2_day: toxswaNumber("toxswa-diffusion", 0.000043),
    relative_sediment_diffusion: 0.3,
    interface_diffusion_path_m: 0.0005,
    volatilisation_half_life_days: null,
    water_solubility_mg_l: state.profile?.water_solubility_mg_l || null,
    vapour_pressure_pa: state.profile?.vapour_pressure_pa ?? null,
    loading_mode: mode,
    loaded_start_m: 0,
    loaded_end_m: length,
    application_rate_kg_ha: toxswaNumber("toxswa-app-rate", 1),
    drift_percent: toxswaNumber("toxswa-drift", 1),
    first_application_day: 1,
    number_applications: Math.max(1, Math.round(toxswaNumber("toxswa-app-count", 1))),
    application_interval_days: toxswaNumber("toxswa-app-interval", 7),
    discharge_concentration_ug_l: toxswaNumber("toxswa-discharge-conc", 0.640775),
    discharge_flow_m3_day: toxswaNumber("toxswa-discharge-flow", 20000),
    continuous_mass_mg_day: toxswaNumber("toxswa-continuous-mass", 0),
    pulse_mass_mg: toxswaNumber("toxswa-pulse-mass", 0),
    pulse_day: toxswaNumber("toxswa-pulse-day", 1),
    pulse_distributed: false,
    lateral_concentration_ug_l: toxswaNumber("toxswa-lateral-conc", 0),
    lateral_water_flux_m3_day: toxswaNumber("toxswa-lateral-flow", 0),
    initial_water_concentration_ug_l: 0,
    initial_sediment_concentration_ug_kg: 0,
    simulation_days: toxswaNumber("toxswa-duration", 120),
    output_interval_days: 1 / 24,
    max_transport_substep_days: 0.05,
    aquatic_pnec_ug_l: null,
    sediment_pnec_ug_kg: null,
  };
}

function drawToxswaChart(series = []) {
  const svg = $("toxswa-chart");
  if (!svg || !series.length) return;
  const water = svg.querySelector(".tx-chart-water");
  const sediment = svg.querySelector(".tx-chart-sed");
  const grid = svg.querySelector(".grid-lines");
  if (grid) grid.innerHTML = [0,1,2,3,4].map(i => `<line x1="35" x2="735" y1="${25+i*40}" y2="${25+i*40}"></line>`).join("");
  const maxT = Math.max(...series.map(row => Number(row.time_d || 0)), 1);
  const maxW = Math.max(...series.map(row => Number(row.water_dissolved_ug_l || 0)), 1e-12);
  const maxS = Math.max(...series.map(row => Number(row.sediment_ug_kg || 0)), 1e-12);
  const path = (key, maxV) => series.map((row, i) => {
    const x = 35 + 700 * Number(row.time_d || 0) / maxT;
    const y = 185 - 155 * Number(row[key] || 0) / maxV;
    return `${i ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
  if (water) water.setAttribute("d", path("water_dissolved_ug_l", maxW));
  if (sediment) sediment.setAttribute("d", path("sediment_ug_kg", maxS));
}

function renderToxswa(result) {
  state.toxswa = result;
  const out = result.outputs || result;
  const summary = out.summary || {};
  const mb = out.mass_balance || {};
  const totalInput = Number(mb.initial_mass_mg || 0) + Number(mb.external_input_mg || 0);
  const pct = value => totalInput > 0 ? Number(value || 0) / totalInput * 100 : 0;
  if ($("toxswa-pecsw")) $("toxswa-pecsw").textContent = fmt(summary.global_max_pecsw_dissolved_ug_l, 6);
  if ($("toxswa-twa3")) $("toxswa-twa3").textContent = fmt(summary.twaecsw_dissolved_ug_l?.["3"], 6);
  if ($("toxswa-pecsed")) $("toxswa-pecsed").textContent = fmt(summary.global_max_pecsed_ug_kg, 6);
  if ($("toxswa-outflow")) $("toxswa-outflow").textContent = fmt(pct(mb.outflow_mass_mg), 5);
  if ($("toxswa-transformed")) $("toxswa-transformed").textContent = fmt(pct(Number(mb.water_transformed_mg || 0) + Number(mb.sediment_transformed_mg || 0)), 5);
  if ($("toxswa-balance")) $("toxswa-balance").textContent = fmt(Math.abs(Number(mb.closure_error_fraction || 0)) * 100, 5);

  const wTwa = summary.twaecsw_dissolved_ug_l || {};
  const sTwa = summary.twaecsed_ug_kg || {};
  if ($("toxswa-twa-table")) $("toxswa-twa-table").innerHTML = `<table class="toxswa-table"><thead><tr><th>Window</th><th>Water µg/L</th><th>Sediment µg/kg</th></tr></thead><tbody>${[1,2,3,4,7,14,21,28,42,50,100].map(day => `<tr><td>${day} d</td><td>${fmt(wTwa[String(day)],6)}</td><td>${fmt(sTwa[String(day)],6)}</td></tr>`).join("")}</tbody></table>`;
  if ($("toxswa-readiness")) $("toxswa-readiness").innerHTML = (out.official_input_readiness || []).map(row => `<div class="readiness-row ${row.status === "ready" ? "ready" : "missing"}"><i class="readiness-dot"></i><div><strong>${row.label}</strong><small>${row.note}</small></div></div>`).join("");
  if ($("toxswa-warnings")) $("toxswa-warnings").innerHTML = (out.warnings || []).map(warning => `<div class="pearl-warning"><span>!</span><div><strong>Review point</strong><small>${warning}</small></div></div>`).join("");
  drawToxswaChart(out.time_series || []);
  if ($("toxswa-status")) {
    $("toxswa-status").className = "toxswa-status complete";
    $("toxswa-status").textContent = `Complete · adapted screen · run ${result.model_run_id || "not persisted"} · not official FOCUS`;
  }
}

async function runToxswa() {
  if (!waterSedimentWorkbenchEligible()) {
    toast("The water–sediment workbench is available for relevant EU organic-chemical pathways from Tier 2.", 6500);
    return;
  }
  const button = $("run-toxswa");
  if (button) button.disabled = true;
  if ($("toxswa-status")) { $("toxswa-status").className = "toxswa-status running"; $("toxswa-status").textContent = "Solving segmented water transport and water–sediment exchange…"; }
  try {
    await ensureWorkspace();
    const result = await api("/api/model-runs/toxswa-surface-water", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(toxswaPayload())});
    renderToxswa(result);
    toast("TOXSWA process screen completed. Official FOCUS remains a separate external workflow.");
  } catch (error) {
    console.error(error);
    if ($("toxswa-status")) { $("toxswa-status").className = "toxswa-status error"; $("toxswa-status").textContent = `Stopped · ${error.message}`; }
    toast(`TOXSWA screen stopped: ${error.message}`, 6500);
  } finally { if (button) button.disabled = false; }
}

async function prepareOfficialToxswaWorkflow() {
  if (!officialFocusToxswaEligible()) {
    toast("Official FOCUS_TOXSWA preparation is restricted to EU pesticide soil/spray pathways at Tier 3 or 4.", 7000);
    return;
  }
  const button = $("prepare-toxswa-workflow");
  if (button) button.disabled = true;
  try {
    await ensureWorkspace();
    const p = toxswaPayload();
    const driftMgM2 = p.loading_mode === "spray_drift" ? p.application_rate_kg_ha * p.drift_percent : null;
    const workflow = await api("/api/model-workflows", {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({
        project_id: state.project.id,
        chemical_id: state.chemical.id,
        model_key: "TOXSWA",
        jurisdiction: "EU",
        tier: 3,
        scenario_name: "FOCUS_TOXSWA Step 3 workflow shell",
        input_data: {
          contaminant_group: "pesticide",
          spin_substance_record: {chemical: p.chemical_name, koc_l_kg: p.koc_l_kg, water_dt50_days: p.water_dt50_days, sediment_dt50_days: p.sediment_dt50_days},
          swash_surface_water_scenario: null,
          application_pattern: {loading_mode:p.loading_mode, application_rate_kg_ha:p.application_rate_kg_ha, number_applications:p.number_applications, interval_days:p.application_interval_days},
          drift_deposition: driftMgM2 == null ? "not configured for the current loading route" : {mg_m2:driftMgM2, application_rate_kg_ha:p.application_rate_kg_ha, drift_percent:p.drift_percent},
          macro_m2t_or_przm_p2t_when_applicable: null,
          water_and_sediment_dt50: {water_days:p.water_dt50_days, sediment_days:p.sediment_dt50_days, reference_temperature_c:p.transformation_reference_temperature_c},
          freundlich_sorption_parameters: {koc_l_kg:p.koc_l_kg, exponent:p.freundlich_exponent, reference_concentration_mg_l:p.reference_concentration_mg_l},
          molar_mass_vapour_pressure_solubility_diffusion: {molar_mass_g_mol:p.molecular_weight_g_mol, vapour_pressure_pa:p.vapour_pressure_pa, solubility_mg_l:p.water_solubility_mg_l, diffusion_m2_day:p.aqueous_diffusion_coefficient_m2_day},
          metabolite_scheme_if_applicable: "not configured",
        }
      })
    });
    const missing = workflow.manifest?.missing_inputs || [];
    if ($("toxswa-import-status")) $("toxswa-import-status").textContent = `Official workflow ${workflow.id} prepared · ${missing.length ? `still requires ${missing.join(", ")}` : "input manifest complete"}.`;
    toast("Official FOCUS_TOXSWA workflow shell prepared in the audit trail.");
  } catch (error) {
    console.error(error);
    if ($("toxswa-import-status")) $("toxswa-import-status").textContent = `Workflow preparation stopped · ${error.message}`;
    toast(`TOXSWA workflow stopped: ${error.message}`, 6500);
  } finally { if (button) button.disabled = false; }
}

async function importOfficialToxswaSummary() {
  const file = $("toxswa-summary-file")?.files?.[0];
  if (!file) { toast("Choose a FOCUS_TOXSWA .sum, .txt or .out file first."); return; }
  const button = $("import-toxswa-summary");
  if (button) button.disabled = true;
  try {
    await ensureWorkspace();
    const form = new FormData();
    form.append("summary_file", file);
    form.append("project_id", String(state.project.id));
    form.append("chemical_id", String(state.chemical.id));
    form.append("scenario_name", `Imported FOCUS_TOXSWA · ${file.name}`);
    const result = await api("/api/toxswa/import-official-summary", {method:"POST", body:form});
    const parsed = result.parsed || {};
    if ($("toxswa-import-status")) $("toxswa-import-status").textContent = `Imported · SHA-256 ${String(parsed.raw_output_sha256 || "").slice(0,12)}… · run ${result.model_run_id || "not persisted"}`;
    const node = $("toxswa-official-result");
    if (node) {
      node.classList.remove("hidden");
      node.innerHTML = `
        <article><small>FOCUS_TOXSWA</small><strong>${parsed.focus_toxswa_version || "version not parsed"}</strong></article>
        <article><small>TOXSWA kernel</small><strong>${parsed.toxswa_kernel_version || "not parsed"}</strong></article>
        <article><small>Global max PECsw</small><strong>${fmt(parsed.global_max_pecsw_ug_l,6)} µg/L</strong></article>
        <article><small>3-day TWAECsw</small><strong>${fmt(parsed.twaecsw_ug_l?.["3"],6)} µg/L</strong></article>`;
    }
    toast("Official TOXSWA summary imported with provenance hash.");
  } catch (error) {
    console.error(error);
    if ($("toxswa-import-status")) $("toxswa-import-status").textContent = `Import stopped · ${error.message}`;
    toast(`TOXSWA import stopped: ${error.message}`, 6500);
  } finally { if (button) button.disabled = false; }
}

function setupToxswa() {
  $("toxswa-loading-mode")?.addEventListener("change", () => setToxswaLoadMode($("toxswa-loading-mode").value));
  $("toxswa-group")?.addEventListener("change", () => updateToxswaRoute({applyDefault:true}));
  $("run-toxswa")?.addEventListener("click", runToxswa);
  $("prepare-toxswa-workflow")?.addEventListener("click", prepareOfficialToxswaWorkflow);
  $("import-toxswa-summary")?.addEventListener("click", importOfficialToxswaSummary);
  setToxswaLoadMode($("toxswa-loading-mode")?.value || "continuous_point_discharge");
  loadToxswaManifest();
}

function renderPearl(result) {
  state.pearl=result;
  const out=result.outputs||result;
  const s=out.summary;
  const tiers=out.tiered_assessment||{};
  const pecsoil=tiers.tier_1_pecsoil;
  const application=tiers.tier_1_application;
  const gw=tiers.tier_3_groundwater||{};
  const comparison = s.focus_style_80th_percentile_ug_l ?? s.groundwater_flux_weighted_average_ug_l;
  const effective = pecsoil?.effective_soil_application_rate_kg_ha_per_application ?? (application?.dose_kg_m2_per_application != null ? application.dose_kg_m2_per_application*10000 : null);
  $("pearl-effective-dose").textContent=effective==null?"Existing PECsoil":fmt(effective,6);
  $("pearl-pecsoil-initial").textContent=fmt(s.pecsoil_initial_ug_kg ?? 0,6);
  $("pearl-pecsoil-max").textContent=fmt(s.pecsoil_max_ug_kg,6);
  $("pearl-gw-endpoint").textContent=fmt(comparison,6);
  $("pearl-gw-average").textContent=fmt(comparison,6);
  $("pearl-leached").textContent=fmt(s.target_leached_fraction*100,5);
  $("pearl-degraded").textContent=fmt(s.degraded_fraction*100,5);
  $("pearl-depth").textContent=fmt(s.deepest_detected_depth_m,4);
  $("pearl-risk").textContent=fmt(s.groundwater_risk_quotient,5);
  $("pearl-balance").textContent=fmt(s.mass_balance_error_mg_m2,4);
  $("tier-application-value").textContent=effective==null?"Existing PECsoil":`${fmt(effective,5)} kg/ha to soil`;
  $("tier-pecsoil-value").textContent=`${fmt(s.pecsoil_max_ug_kg,5)} µg/kg max`;
  $("tier-scenario-value").textContent=out.resolved_inputs.focus_scenario?.name || "User-defined";
  $("tier-pecgw-value").textContent=`${fmt(comparison,5)} µg/L · ${s.groundwater_risk_status.replaceAll('_',' ')}`;
  $("pearl-status").className="pearl-status complete";
  $("pearl-status").textContent=`Complete · ${out.resolved_inputs.focus_scenario?.name || "user profile"} · ${gw.endpoint_basis || "screening endpoint"} · run ${result.model_run_id||'not persisted'}`;
  $("pearl-time-slider").max=String(out.profile_snapshots.length-1);
  $("pearl-time-slider").disabled=false;
  $("pearl-conversions").innerHTML=out.conversions.map(row=>`<div class="pearl-conversion-row"><div><strong>${row.name}</strong><small>${row.equation}${row.basis?` · ${row.basis}`:''}</small></div><span>${fmt(row.value,6)} ${row.unit||''}</span></div>`).join('');
  $("pearl-readiness").innerHTML=out.official_input_readiness.map(row=>`<div class="readiness-row ${row.status==='ready'?'ready':'missing'}"><i class="readiness-dot"></i><div><strong>${row.label}</strong><small>${row.note}</small></div></div>`).join('');
  $("pearl-warnings").innerHTML=out.warnings.map(w=>`<div class="pearl-warning"><span>!</span><div><strong>${w.includes('not an official')?'Model boundary':'Review point'}</strong><small>${w}</small></div></div>`).join('');
  if(state.results && $("metric-groundwater")){ $("metric-groundwater").textContent=`${fmt(comparison,5)} µg/L`; $("metric-card-groundwater")?.classList.remove("hidden"); }
  pearlRenderSnapshot(0);
}

async function runPearl() {
  const button=$("run-pearl");
  button.disabled=true;
  $("pearl-status").className="pearl-status running";
  $("pearl-status").textContent="Calculating PECsoil, resolving the scenario and running downward transport…";
  try{
    await ensureWorkspace();
    const payload=pearlPayload();
    const file=$("pearl-swap-file")?.files?.[0];
    let result;
    if(file){
      const form=new FormData();
      form.append("payload_json",JSON.stringify(payload));
      form.append("swap_csv",file);
      result=await api("/api/model-runs/pearl-groundwater/swap",{method:"POST",body:form});
    }else{
      result=await api("/api/model-runs/pearl-groundwater",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    }
    renderPearl(result);
    toast("Tiered application → PECsoil → scenario → PECgw assessment completed.");
  }catch(error){
    console.error(error);
    $("pearl-status").className="pearl-status error";
    $("pearl-status").textContent=`Stopped · ${error.message}`;
    toast(`PEARL run stopped: ${error.message}`,6500);
  }finally{button.disabled=false;}
}

function setupPearl() {
  $("run-pearl")?.addEventListener("click",runPearl);
  $("pearl-time-slider")?.addEventListener("input",event=>pearlRenderSnapshot(Number(event.target.value)));
  $("pearl-play")?.addEventListener("click",()=>{
    if(!state.pearl) return;
    if(state.pearlTimer){clearInterval(state.pearlTimer);state.pearlTimer=null;$("pearl-play").textContent="▶";return;}
    $("pearl-play").textContent="Ⅱ";
    state.pearlTimer=setInterval(()=>{
      const slider=$("pearl-time-slider");
      let next=Number(slider.value)+1;
      if(next>Number(slider.max)) next=0;
      pearlRenderSnapshot(next);
    },750);
  });
  $("pearl-input-mode")?.addEventListener("change",updatePearlModeUI);
  $("pearl-profile-mode")?.addEventListener("change",updatePearlModeUI);
  $("pearl-focus-scenario")?.addEventListener("change",updatePearlScenarioUI);
  $("pearl-focus-crop")?.addEventListener("change",updatePearlTierPreview);
  $("pearl-horizon-mode")?.addEventListener("change",updatePearlScenarioUI);
  $("pearl-target-depth")?.addEventListener("change",updatePearlScenarioUI);
  ["pearl-app-rate","pearl-app-count","pearl-app-interval","pearl-interception","pearl-pecsoil-depth","pearl-initial-conc","pearl-profile-depth","pearl-layers","pearl-bulk-density"].forEach(id=>$(id)?.addEventListener("input",()=>{
    updatePearlTierPreview();
    if (["pearl-profile-depth","pearl-layers"].includes(id) && $("pearl-profile-mode")?.value === "user_defined") updatePearlScenarioUI();
  }));
  pearlRenderStatic(1.5,36,1,null);
  loadPearlScenarios();
  updatePearlModeUI();
}

function setupEnviroDesign() {
  $("run-envirodesign")?.addEventListener("click",()=>runEnviroDesign(true));
  $("compare-envirodesign")?.addEventListener("click",compareEnviroDesignCandidates);
  $("predict-transformation-pathway")?.addEventListener("click",predictTransformationPathway);
  $("analyse-pathway-retention")?.addEventListener("click",analysePathwayRetention);
  $("search-envipath-curated")?.addEventListener("click",searchEnvipathCuratedPathways);
  $("pathway-provider")?.addEventListener("change",(event)=>{
    $("envipath-package-field")?.classList.toggle("hidden", event.target.value !== "envipath");
  });
}

function setupIdentification() {
  $("refresh-identification")?.addEventListener("click", () => refreshIdentificationProfile());
}

let kineticsMetaboliteCounter = 0;

function setupDegradationKinetics() {
  $("run-degradation-kinetics")?.addEventListener("click", runDegradationKinetics);
  $("add-kinetics-metabolite")?.addEventListener("click", () => addKineticsMetaboliteBlock());
  $("kinetics-framework")?.addEventListener("change", updateKineticsFrameworkUI);
  updateKineticsFrameworkUI();
}

function addKineticsMetaboliteBlock() {
  kineticsMetaboliteCounter += 1;
  const id = kineticsMetaboliteCounter;
  const wrap = document.createElement("div");
  wrap.className = "kinetics-metabolite-block";
  wrap.innerHTML = `
    <div class="kinetics-metabolite-head">
      <input class="kinetics-met-name" placeholder="Transformation product name" value="Metabolite ${id}"/>
      <button class="text-button" type="button" data-remove-metabolite>Remove</button>
    </div>
    <input class="kinetics-met-smiles" placeholder="SMILES (optional)"/>
    <label class="kinetics-met-biochem-row hidden"><span>Forms part of a normal biochemical pathway?</span>
      <select class="kinetics-met-biochem">
        <option value="unknown" selected>Unknown — flag for reviewer</option>
        <option value="no">No</option>
        <option value="yes">Yes</option>
      </select>
    </label>
    <textarea class="kinetics-met-observations" rows="4" placeholder="day, replicate values as % of applied&#10;0, 0, 0, 0&#10;14, 3.1, 2.9, 3.4&#10;30, 8.0, 7.6, 8.4"></textarea>
  `;
  $("kinetics-metabolites").appendChild(wrap);
  wrap.querySelector("[data-remove-metabolite]").addEventListener("click", () => wrap.remove());
  updateKineticsFrameworkUI();
}

function updateKineticsFrameworkUI() {
  const isVich = $("kinetics-framework")?.value === "vich_gl38_veterinary";
  $$(".kinetics-met-biochem-row").forEach(row => row.classList.toggle("hidden", !isVich));
}

function parseKineticsObservations(text) {
  const lines = text.split("\n").map(line => line.trim()).filter(Boolean);
  if (!lines.length) throw new Error("Enter at least two sampling days, one per line: day, replicate values.");
  return lines.map(line => {
    const parts = line.split(",").map(part => part.trim()).filter(part => part !== "");
    const day = Number(parts[0]);
    const replicate_values_percent = parts.slice(1).map(Number);
    if (!Number.isFinite(day) || day < 0 || day > 120 || !replicate_values_percent.length || replicate_values_percent.some(value => !Number.isFinite(value))) {
      throw new Error(`Could not parse "${line}". Use: day, value1, value2, ... (day 0-120).`);
    }
    return { day, replicate_values_percent };
  });
}

function collectKineticsMetabolites() {
  return $$("#kinetics-metabolites .kinetics-metabolite-block").map(block => {
    const name = block.querySelector(".kinetics-met-name").value.trim() || "Unnamed transformation product";
    const smiles = block.querySelector(".kinetics-met-smiles").value.trim();
    const biochemValue = block.querySelector(".kinetics-met-biochem")?.value;
    const forms_part_of_biochemical_pathway = biochemValue === "yes" ? true : biochemValue === "no" ? false : null;
    const observations = parseKineticsObservations(block.querySelector(".kinetics-met-observations").value);
    return { name, smiles: smiles || null, forms_part_of_biochemical_pathway, observations };
  });
}

async function runDegradationKinetics() {
  const button = $("run-degradation-kinetics");
  const status = $("kinetics-status");
  let payload;
  try {
    payload = {
      regulatory_framework: $("kinetics-framework").value,
      matrix: $("kinetics-matrix").value.trim() || "soil",
      parent_name: $("kinetics-parent-name").value.trim() || "Parent",
      parent_observations: parseKineticsObservations($("kinetics-parent-observations").value),
      metabolites: collectKineticsMetabolites(),
    };
  } catch (error) {
    toast(error.message, 6000);
    return;
  }
  if (state.project?.id && state.chemical?.id) {
    payload.project_id = state.project.id;
    payload.chemical_id = state.chemical.id;
    payload.scenario_name = `${payload.regulatory_framework === "vich_gl38_veterinary" ? "VICH GL38" : "FOCUS Kinetics"} degradation kinetics for ${state.chemical.preferred_name}`;
  }
  if (button) button.disabled = true;
  if (status) { status.className = "design-status running"; status.innerHTML = "<strong>Fitting SFO, FOMC, HS and DFOP…</strong><small>Nonlinear least squares against every replicate point.</small>"; }
  try {
    const result = await api("/api/degradation-kinetics/assess", {
      method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload),
    });
    renderDegradationKineticsResult(result);
    if (status) { status.className = "design-status"; status.innerHTML = `<strong>Fit complete.</strong><small>${result.model_run_id ? `Saved as model run ${result.model_run_id}.` : "Not saved — select a project and chemical to persist a run."}</small>`; }
  } catch (error) {
    console.error(error);
    if (status) { status.className = "design-status error"; status.innerHTML = `<strong>Fit failed.</strong><small>${escapeHtml(error.message)}</small>`; }
  } finally {
    if (button) button.disabled = false;
  }
}

function kineticsModelLabel(key) {
  return {SFO:"SFO · single first-order", FOMC:"FOMC · Gustafson–Holden", HS:"HS · hockey-stick", DFOP:"DFOP · bi-exponential"}[key] || key;
}

function renderKineticsFitsTable(fits, selectedModel) {
  const rows = Object.values(fits).map(fit => {
    if (fit.error) return `<tr><td>${kineticsModelLabel(fit.model)}</td><td colspan="4">${escapeHtml(fit.error)}</td></tr>`;
    const cs = fit.chi_square || {};
    const isSelected = fit.model === selectedModel;
    return `<tr class="${isSelected ? "kinetics-selected-row" : ""}">
      <td>${isSelected ? "★ " : ""}${kineticsModelLabel(fit.model)}</td>
      <td>${cs.error_percent != null ? fmt(cs.error_percent,3) + "%" : "—"}</td>
      <td>${cs.passes_guidance_threshold ? "Passes" : "Fails"} guidance</td>
      <td>${fit.dt50_days != null ? fmt(fit.dt50_days,4) + " d" : "not reached"}</td>
      <td>${fit.dt90_days != null ? fmt(fit.dt90_days,4) + " d" : "not reached"}</td>
    </tr>`;
  }).join("");
  return `<table class="candidate-table"><thead><tr><th>Model</th><th>χ² error</th><th>Guidance (≤15%)</th><th>DT50</th><th>DT90</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderDegradationKineticsResult(result) {
  const out = result.outputs;
  const parentFit = out.parent.kinetics;
  $("kinetics-parent-results").innerHTML = `
    <p><strong>${escapeHtml(out.parent.name)}</strong> · ${escapeHtml(out.matrix)} · selected <strong>${kineticsModelLabel(parentFit.selected_model)}</strong></p>
    <p class="identification-source">${escapeHtml(parentFit.selection_reason)}</p>
    ${renderKineticsFitsTable(parentFit.fits, parentFit.selected_model)}
    ${(out.warnings||[]).map(w => `<p class="identification-source">${escapeHtml(w)}</p>`).join("")}
  `;

  const selectedFit = parentFit.fits[parentFit.selected_model];
  drawKineticsChart(parentFit.day_level_observations, selectedFit, out.parent.reference_amount_percent);

  if (!out.metabolites.length) {
    $("kinetics-metabolite-results").innerHTML = "<p>No transformation products entered.</p>";
  } else {
    $("kinetics-metabolite-results").innerHTML = out.metabolites.map(metabolite => {
      const sig = metabolite.significance;
      const badge = sig.classification === "major" || sig.include_in_pec_refinement ? "Included" : "Shown in pathway only";
      const basisNote = metabolite.kinetics?.fit_basis === "decline_from_observed_maximum"
        ? `<p class="identification-source">DT50/DT90 measured from this metabolite's own peak on day ${fmt(metabolite.kinetics.fit_basis_detail?.peak_day,1)} (re-based to day 0), not from time of parent application — ${escapeHtml(metabolite.kinetics.fit_basis_detail?.note || "")}</p>`
        : "";
      const kineticsBlock = metabolite.kinetics
        ? `<p>Selected <strong>${kineticsModelLabel(metabolite.kinetics.selected_model)}</strong> · DT50 ${fmt(metabolite.kinetics.fits[metabolite.kinetics.selected_model]?.dt50_days,4)} d${metabolite.kinetics.fit_basis === "decline_from_observed_maximum" ? " (from peak)" : ""}</p>${basisNote}`
        : `<p class="identification-source">${escapeHtml(metabolite.kinetics_note || metabolite.kinetics_error || "Not fitted.")}</p>`;
      return `<div class="identification-tp-card">
        <p><strong>${escapeHtml(metabolite.name)}</strong> <em>${badge}</em></p>
        <p>Max observed ${fmt(sig.max_observed_percent,3)}% · threshold ${fmt(sig.threshold_percent,1)}%</p>
        ${kineticsBlock}
        <p class="identification-source">${escapeHtml(sig.rule_text)}</p>
      </div>`;
    }).join("");
  }
}

function drawKineticsChart(dayLevelObservations, selectedFit, m0Reference) {
  const svg = $("kinetics-chart");
  if (!svg || !selectedFit) return;
  const pad = 40, width = 560, height = 280;
  const maxDay = Math.max(...dayLevelObservations.map(row => row.day), 1);
  const maxVal = Math.max(m0Reference, ...dayLevelObservations.map(row => row.mean_percent), 1);
  const x = day => pad + (width - 2*pad) * day / maxDay;
  const y = value => height - pad - (height - 2*pad) * Math.max(value, 0) / maxVal;

  const grid = svg.querySelector(".kinetics-grid-lines");
  if (grid) grid.innerHTML = [0,0.25,0.5,0.75,1].map(f => `<line x1="${pad}" x2="${width-pad}" y1="${pad+(height-2*pad)*f}" y2="${pad+(height-2*pad)*f}" stroke="#e2e8e5" stroke-width="1"/>`).join("");

  const paramOrder = {SFO:["m0","k"], FOMC:["m0","alpha","beta"], HS:["m0","k1","k2","tb"], DFOP:["m0","g","k1","k2"]}[selectedFit.model] || [];
  const params = selectedFit.parameters;
  const curveFn = t => {
    if (selectedFit.model === "SFO") return params.m0 * Math.exp(-params.k * t);
    if (selectedFit.model === "FOMC") return params.m0 * Math.pow(1 + t/params.beta, -params.alpha);
    if (selectedFit.model === "HS") return t <= params.tb ? params.m0*Math.exp(-params.k1*t) : params.m0*Math.exp(-params.k1*params.tb)*Math.exp(-params.k2*(t-params.tb));
    if (selectedFit.model === "DFOP") return params.m0*(params.g*Math.exp(-params.k1*t) + (1-params.g)*Math.exp(-params.k2*t));
    return 0;
  };
  const steps = 60;
  const linePath = Array.from({length: steps+1}, (_, i) => {
    const t = maxDay * i / steps;
    return `${i ? "L" : "M"}${x(t).toFixed(2)} ${y(curveFn(t)).toFixed(2)}`;
  }).join(" ");
  const line = svg.querySelector(".kinetics-fit-line");
  if (line) { line.setAttribute("d", linePath); line.setAttribute("stroke", "#2c9773"); }

  const points = svg.querySelector(".kinetics-points");
  if (points) points.innerHTML = dayLevelObservations.map(row => `<circle cx="${x(row.day).toFixed(2)}" cy="${y(row.mean_percent).toFixed(2)}" r="4" fill="#17382e"/>`).join("");
}


function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}

function evidenceSourceLabel(sourceKey) {
  const labels = {pubchem:"PubChem", europe_pmc:"Europe PMC", epa_comptox:"EPA CompTox", efsa_openfoodtox:"EFSA OpenFoodTox", epa_ecotox:"EPA ECOTOX", aeru_vsdb:"AERU VSDB", aeru_ppdb:"AERU PPDB", premier:"PREMIER", oasis_soil_dt50:"OASIS soil DT50", nite_ready_biodegradability:"NITE mineralization"};
  return labels[sourceKey] || sourceKey;
}

function evidenceValueText(candidate) {
  const qualifier = candidate.qualifier && candidate.qualifier !== "=" ? `${candidate.qualifier} ` : "";
  return candidate.value == null ? "Value not parsed" : `${qualifier}${fmt(candidate.value, 7)} ${candidate.unit || ""}`.trim();
}

function evidenceCandidateMatchesSelectedChemical(candidate) {
  if (!state.chemical) return false;
  if (candidate.cas_number) return Boolean(state.chemical.cas_number) && candidate.cas_number === state.chemical.cas_number;
  const norm = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  return norm(candidate.chemical_name) === norm(state.chemical.preferred_name);
}

function profileCandidateTarget(candidate) {
  return ({
    "PHYS.LOGKOW":"profile-logkow",
    "PHYS.PKA":"profile-pka",
    "PHYS.WATER_SOLUBILITY":"profile-solubility",
    "PHYS.VAPOUR_PRESSURE":"profile-vapour",
    "FATE.SOIL_DT50":"profile-soil-dt50",
  })[candidate.property_code] || null;
}

function convertedCandidateValue(candidate) {
  const value = Number(candidate.value);
  const unit = String(candidate.unit || "").toLowerCase().replaceAll(" ", "").replace("μ", "µ");
  if (!Number.isFinite(value)) return null;
  if (candidate.property_code === "PHYS.WATER_SOLUBILITY") {
    const factors = {"ng/l":1e-6,"µg/l":1e-3,"mg/l":1,"g/l":1000,"mg/ml":1000,"g/100ml":10000};
    return factors[unit] == null ? null : value * factors[unit];
  }
  if (candidate.property_code === "PHYS.VAPOUR_PRESSURE") {
    const factors = {"pa":1,"kpa":1000,"hpa":100,"mpa":0.001,"mmhg":133.322368,"torr":133.322368,"atm":101325};
    return factors[unit] == null ? null : value * factors[unit];
  }
  if (candidate.property_code === "FATE.SOIL_DT50") {
    const factors = {hours:1/24,days:1,weeks:7,months:30.4375,years:365.25};
    return factors[unit] == null ? null : value * factors[unit];
  }
  return value;
}

function copyEvidenceCandidateToProfile(index) {
  const candidate = state.evidenceCandidates[index];
  const target = candidate && profileCandidateTarget(candidate);
  if (!candidate || !target) return;
  if (!evidenceCandidateMatchesSelectedChemical(candidate)) {
    toast("This candidate belongs to a different chemical than the confirmed assessment identity. It was not copied.", 6500);
    return;
  }
  const value = convertedCandidateValue(candidate);
  if (value == null) { toast(`The ${candidate.unit || "unknown"} unit cannot be normalised into the profile field.`); return; }
  $(target).value = value;
  $("profile-reviewed").checked = false;
  const source = candidate.publication_title || candidate.original_source || candidate.source_record_id || evidenceSourceLabel(candidate.source_key);
  const sourceLine = `${candidate.property_code}: ${source} (${candidate.source_url || candidate.source_key}); copied candidate ${candidate.candidate_id || "unidentified"} for review.`;
  const existing = $("profile-source").value.trim();
  $("profile-source").value = existing ? `${existing}\n${sourceLine}` : sourceLine;
  state.profileDraftProvenance[candidate.property_code] = {
    candidate_id:candidate.candidate_id,source_key:candidate.source_key,source_record_id:candidate.source_record_id,
    source_url:candidate.source_url,original_value:candidate.value,original_unit:candidate.unit,
    normalised_value:value,status:"copied_unreviewed_candidate",
  };
  $("profile-status").textContent = "Draft changed · review and save required";
  toast("Candidate copied into the profile form only. Review the original source, confirm the profile, then save.", 6200);
}

function renderEvidenceCandidates(searchResult) {
  state.evidenceSearch = searchResult;
  state.evidenceCandidates = searchResult.candidates || [];
  const list = $("evidence-candidates");
  const count = state.evidenceCandidates.length;
  if ($("evidence-result-count")) $("evidence-result-count").textContent = `${count} candidate${count === 1 ? "" : "s"}`;
  const sourceResults = searchResult.source_results || [];
  const okSources = sourceResults.filter(row => row.status === "ok").map(row => evidenceSourceLabel(row.source_key));
  const errors = sourceResults.filter(row => row.status === "error");
  if ($("evidence-result-summary")) {
    $("evidence-result-summary").innerHTML = `<strong>${count ? `${count} candidate values found` : "No numeric endpoint candidates found"}</strong><span>${okSources.length ? `Searched ${escapeHtml(okSources.join(" + "))}. ` : ""}Every result is unselected until scientist review.${errors.length ? ` ${errors.length} source request(s) reported an error.` : ""}</span>`;
  }
  if (!list) return;
  if (!count) {
    const warnings = sourceResults.flatMap(row => row.warnings || []).slice(0,4);
    list.innerHTML = `<div class="empty-evidence"><strong>No endpoint candidate was extracted.</strong><span>${warnings.length ? warnings.map(escapeHtml).join(" · ") : "Try another endpoint, search all fate endpoints, or inspect the original source manually."}</span></div>`;
    return;
  }
  list.innerHTML = state.evidenceCandidates.map((candidate, index) => {
    const matrix = candidate.matrix ? candidate.matrix.replaceAll("_", " ") : "matrix not resolved";
    const conditions = [candidate.temperature_c != null ? `${candidate.temperature_c} °C` : null, candidate.ph != null ? `pH ${candidate.ph}` : null].filter(Boolean).join(" · ");
    const sourceId = candidate.doi ? `DOI ${candidate.doi}` : candidate.pmid ? `PMID ${candidate.pmid}` : candidate.source_record_id || "source record";
    const extraction = String(candidate.extraction_status || "candidate").replaceAll("_", " ");
    const importDisabled = candidate.import_allowed === false ? "disabled" : "";
    const copyTarget = profileCandidateTarget(candidate);
    return `<article class="evidence-candidate" data-evidence-index="${index}">
      <div class="candidate-main">
        <div class="candidate-source-line"><span class="candidate-source">${escapeHtml(evidenceSourceLabel(candidate.source_key))}</span><span>${escapeHtml(sourceId)}</span><span>${escapeHtml(extraction)}</span></div>
        <div class="candidate-endpoint-line"><div><strong>${escapeHtml(candidate.endpoint_label || candidate.property_code)}</strong><small>${escapeHtml(matrix)}${conditions ? ` · ${escapeHtml(conditions)}` : ""}</small></div><b>${escapeHtml(evidenceValueText(candidate))}</b></div>
        ${candidate.publication_title ? `<p class="candidate-publication">${escapeHtml(candidate.publication_title)}</p>` : ""}
        <p class="candidate-context">${escapeHtml(candidate.snippet || "No extraction context available.")}</p>
      </div>
      <div class="candidate-review">
        <span class="candidate-rights">${escapeHtml(String(candidate.rights_status || "source terms apply").replaceAll("_", " "))}</span>
        ${candidate.source_url ? `<a href="${escapeHtml(candidate.source_url)}" target="_blank" rel="noreferrer">Open source</a>` : ""}
        ${copyTarget ? `<button class="ghost-button evidence-copy-button" type="button" data-evidence-index="${index}">Copy to profile</button>` : ""}
        <button class="ghost-button evidence-stage-button" type="button" data-evidence-index="${index}" ${importDisabled}>${candidate.import_allowed === false ? "Import blocked" : "Stage for review"}</button>
      </div>
    </article>`;
  }).join("");
  $$(".evidence-stage-button").forEach(button => button.addEventListener("click", () => importEvidenceCandidate(Number(button.dataset.evidenceIndex), button)));
  $$(".evidence-copy-button").forEach(button => button.addEventListener("click", () => copyEvidenceCandidateToProfile(Number(button.dataset.evidenceIndex))));
}

async function searchEvidenceHub() {
  const button = $("search-evidence");
  const status = $("evidence-search-status");
  const chemicalName = $("evidence-chemical")?.value.trim();
  if (!chemicalName) { toast("Enter a chemical name before searching evidence."); return; }
  const sources = [];
  if ($("evidence-use-pubchem")?.checked) sources.push("pubchem");
  if ($("evidence-use-epmc")?.checked) sources.push("europe_pmc");
  if ($("evidence-use-oasis-soil-dt50")?.checked) sources.push("oasis_soil_dt50");
  if ($("evidence-use-nite-mineralization")?.checked) sources.push("nite_ready_biodegradability");
  if (!sources.length) { toast("Select at least one live evidence source."); return; }
  const endpoint = $("evidence-endpoint")?.value || "";
  const norm = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const structureMatch = state.chemical?.smiles && norm(chemicalName) === norm(state.chemical.preferred_name);
  const smiles = structureMatch ? state.chemical.smiles : null;
  if ((sources.includes("oasis_soil_dt50") || sources.includes("nite_ready_biodegradability")) && !smiles) {
    toast("OASIS soil DT50 / NITE mineralization match by exact structure: enter the confirmed chemical's own name (matching the reviewed profile) to search them.", 6500);
  }
  if (button) button.disabled = true;
  if (status) status.textContent = "Searching attributed databases and literature…";
  try {
    const result = await api("/api/evidence-sources/search", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        chemical_name: chemicalName,
        cas_number: $("evidence-cas")?.value.trim() || null,
        source_keys: sources,
        endpoint_codes: endpoint ? [endpoint] : [],
        limit_per_source: 24,
        include_open_access_full_text: Boolean($("evidence-fulltext")?.checked),
        smiles,
      })
    });
    renderEvidenceCandidates(result);
    if (status) status.textContent = `Complete · ${result.candidates?.length || 0} unselected candidate values`;
    toast(`Evidence search complete: ${result.candidates?.length || 0} candidate values found.`);
  } catch (error) {
    console.error(error);
    if (status) status.textContent = `Search stopped · ${error.message}`;
    toast(`Evidence search stopped: ${error.message}`, 6500);
  } finally { if (button) button.disabled = false; }
}

async function importEvidenceCandidate(index, button) {
  const candidate = state.evidenceCandidates[index];
  if (!candidate) return;
  if (!evidenceCandidateMatchesSelectedChemical(candidate)) {
    toast("Evidence staging blocked: the candidate does not match the confirmed chemical identity.", 6500);
    return;
  }
  try {
    await ensureWorkspace();
    if (button) { button.disabled = true; button.textContent = "Staging…"; }
    const result = await api("/api/evidence-sources/import-candidate", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        project_id: state.project.id, chemical_id: state.chemical.id, candidate,
        scientist_reviewed:false, rights_asserted:false, reliability_score:null,
        representative_group_key:null, review_notes:"Staged from Evidence Data Hub; original study review pending."
      })
    });
    if (button) { button.textContent = `Staged · evidence ${result.id}`; button.classList.add("staged"); }
    toast("Candidate staged in the evidence review queue. It has not been selected for modelling.");
  } catch (error) {
    console.error(error);
    if (button) { button.disabled = false; button.textContent = "Stage for review"; }
    toast(`Evidence staging stopped: ${error.message}`, 6500);
  }
}

function setupEvidenceHub() {
  $("search-evidence")?.addEventListener("click", searchEvidenceHub);
  ["evidence-chemical","evidence-cas"].forEach(id => $(id)?.addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); searchEvidenceHub(); } }));
}

function setupPharmaInfluent() {
  const ids = ['pharma-emission-mode','wwtp-flow-override','pharma-dose-mg','pharma-stp-capacity','pharma-fpen-mode','pharma-fpen','pharma-prevalence','pharma-treatment-days','pharma-treatments-year','pharma-oecd-class','pharma-oecd-country','pharma-oecd-dose-mg','population','water-per-person','parent-fraction','dilution','amount-value','amount-unit'];
  ids.forEach(id => $(id)?.addEventListener('input', () => {
    if (id === 'pharma-oecd-class') refreshOecdCountryOptions();
    if (id === 'pharma-oecd-country') updateOecdDddDisplay();
    updatePharmaInfluentUI();
  }));
  ids.forEach(id => $(id)?.addEventListener('change', () => {
    if (id === 'pharma-oecd-class') refreshOecdCountryOptions();
    if (id === 'pharma-oecd-country') updateOecdDddDisplay();
    updatePharmaInfluentUI();
  }));
  updatePharmaInfluentUI();
}


function setupQuickScreen() {
  const scenarioSelect = $("qs-scenario");
  const updateScenarioUI = () => {
    const isEma = scenarioSelect.value === "ema_phase_i_pharma";
    $("qs-release-wrap").classList.toggle("hidden", isEma);
    $("qs-dose-wrap").classList.toggle("hidden", !isEma);
  };
  scenarioSelect?.addEventListener("change", updateScenarioUI);
  updateScenarioUI();
  $("qs-run")?.addEventListener("click", runQuickScreen);
}

async function runQuickScreen() {
  const button = $("qs-run");
  const status = $("quick-screen-status");
  const query = $("qs-query").value.trim();
  const scenario = $("qs-scenario").value;
  if (!query) { toast("Enter a CAS number, SMILES or name to screen.", 5000); return; }
  const payload = {
    query, query_mode: $("qs-query-mode").value, scenario,
  };
  if (scenario === "generic_wwtp") {
    const release = Number($("qs-release").value);
    if (!Number.isFinite(release) || release <= 0) { toast("Enter a positive annual release (kg/year).", 5000); return; }
    payload.release_kg_year = release;
  } else {
    const dose = Number($("qs-dose").value);
    if (!Number.isFinite(dose) || dose <= 0) { toast("Enter a positive maximum daily dose (mg).", 5000); return; }
    payload.maximum_daily_dose_mg = dose;
  }
  if (button) button.disabled = true;
  if (status) { status.className = "design-status running"; status.innerHTML = "<strong>Screening…</strong><small>Querying US EPA ECOTOX and running the exposure engine.</small>"; }
  try {
    const result = await api("/api/quick-screen/risk", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
    renderQuickScreenResult(result);
    if (status) { status.className = "design-status"; status.innerHTML = "<strong>Screening estimate — not reviewed.</strong><small>A fast triage signal, not a substitute for a reviewed FateIntel assessment.</small>"; }
  } catch (error) {
    console.error(error);
    if (status) { status.className = "design-status error"; status.innerHTML = `<strong>Screen failed.</strong><small>${escapeHtml(error.message)}</small>`; }
  } finally {
    if (button) button.disabled = false;
  }
}

function renderQuickScreenResult(result) {
  const identity = result.identity || {};
  const unconfirmedBadge = identity.identity_confirmed === false
    ? `<p class="identification-source"><strong>Identity not confirmed by PubChem</strong> — screened by CAS number only. ${escapeHtml(identity.note || "")}</p>` : "";
  $("qs-identity").innerHTML = `
    <p><strong>${escapeHtml(identity.preferred_name || "Unknown")}</strong></p>
    <p class="identification-source">CAS ${escapeHtml(identity.cas_number || "—")}${identity.smiles ? ` · ${escapeHtml(identity.smiles)}` : ""}</p>
    ${unconfirmedBadge}
  `;

  const hazard = result.hazard || {};
  if (hazard.pnec_ug_l != null) {
    $("qs-hazard").innerHTML = `
      <p><strong>PNEC: ${fmt(hazard.pnec_ug_l, 4)} &micro;g/L</strong></p>
      <p class="identification-source">${escapeHtml(hazard.basis || "")}</p>
      <p class="identification-source">Critical value ${hazard.critical_value_ug_l != null ? fmt(hazard.critical_value_ug_l, 4) + " µg/L" : "—"} (${escapeHtml(hazard.critical_endpoint || "—")}) &divide; AF ${hazard.assessment_factor != null ? fmt(hazard.assessment_factor, 0) : "—"}</p>
      <p class="identification-source">${(hazard.species_considered || []).length} species considered, ${hazard.candidates_found ?? 0} candidate values used.</p>
    `;
  } else {
    $("qs-hazard").innerHTML = `<p>${escapeHtml(hazard.data_gap || "No real ecotoxicity data found for this chemical in US EPA ECOTOX.")}</p>`;
  }

  const sedimentSoil = hazard.sediment_soil || {};
  if (sedimentSoil.data_gap) {
    $("qs-sediment-soil").innerHTML = `<p>${escapeHtml(sedimentSoil.data_gap)}</p>`;
  } else if (sedimentSoil.pnec_soil_mg_per_kg != null) {
    $("qs-sediment-soil").innerHTML = `
      <p><strong>Sediment: ${fmt(sedimentSoil.pnec_sediment_dry_mg_per_kg, 4)} mg/kg dry</strong> &middot; <strong>Soil: ${fmt(sedimentSoil.pnec_soil_mg_per_kg, 4)} mg/kg</strong></p>
      <p class="identification-source">Koc used: ${fmt(sedimentSoil.koc_l_per_kg_used, 3)} L/kg (median of ${sedimentSoil.koc_candidates_found} candidate${sedimentSoil.koc_candidates_found === 1 ? "" : "s"}${sedimentSoil.koc_range_l_per_kg ? `, range ${fmt(sedimentSoil.koc_range_l_per_kg[0], 3)}–${fmt(sedimentSoil.koc_range_l_per_kg[1], 3)}` : ""})</p>
      <p class="identification-source">${escapeHtml(sedimentSoil.source || "")}</p>
    `;
  } else {
    $("qs-sediment-soil").innerHTML = `<p>Not derived.</p>`;
  }

  const flagsList = result.flags || [];
  $("qs-flags").innerHTML = flagsList.length
    ? flagsList.map(flag => `<p class="identification-source">${escapeHtml(flag.message || flag.pathway)}</p>`).join("")
    : `<p>No flagged pathways for this chemical.</p>`;

  const exposure = result.exposure || {};
  $("qs-exposure").innerHTML = `
    <p><strong>PEC<sub>SW</sub>: ${exposure.pec_surface_water_ug_l != null ? fmt(exposure.pec_surface_water_ug_l, 4) + " µg/L" : "—"}</strong></p>
    <p class="identification-source">Scenario: ${escapeHtml(exposure.scenario || "—")}</p>
  `;

  const risk = result.risk || {};
  const bandLabel = {cannot_be_characterised: "Cannot be characterised", risk_not_excluded: "Risk not excluded", low: "Low"}[risk.risk_band] || risk.risk_band || "—";
  $("qs-risk").innerHTML = `
    <p><strong>RQ: ${risk.risk_quotient != null ? fmt(risk.risk_quotient, 3) : "—"}</strong> &middot; ${escapeHtml(bandLabel)}</p>
    <p class="identification-source">${escapeHtml(risk.note || "")}</p>
    <p class="identification-source"><strong>Screening estimate — not reviewed.</strong> A fast triage signal, never a substitute for a reviewed FateIntel assessment.</p>
  `;
}

async function init() {
  setupFlowCards(); setupIdentity(); setupEvidenceHub(); setupScenarioCards(); setupPharmaInfluent(); setupModelSystem(); setupUSExposure(); setupRegulatoryProgramme(); setupTiers(); setupNavigation(); setupDrawers(); setupCopilot(); setupEnviroDesign(); setupToxswa(); setupPearl(); setupIdentification(); setupDegradationKinetics(); setupQuickScreen(); await Promise.all([loadVeterinaryProfiles(), loadOecdPharmaRegistry()]);
  $("run-assessment").addEventListener("click",runAssessment);
  $("retry-assessment")?.addEventListener("click",runAssessment);
  $("continue-toxswa")?.addEventListener("click",()=>{syncToxswaFromScreening(); $("toxswa-surface-water")?.scrollIntoView({behavior:"smooth",block:"start"});});
  $("continue-pearl")?.addEventListener("click",()=>{syncPearlFromScreening(); $("pearl-groundwater")?.scrollIntoView({behavior:"smooth",block:"start"});});
  $("continue-envirodesign")?.addEventListener("click",()=>$("envirodesign")?.scrollIntoView({behavior:"smooth",block:"start"}));
  updateCompartments(); updateModels(); updateSummaries(); await refreshRegulatoryPathway();
  try {
    const build = await api("/api/build");
    if (!String(build.build_id || "").includes("v2.24")) toast("Warning: this page is not connected to the v2.24 server build.",6000);
    await loadInitialWorkspace();
    if (state.project && state.chemical) await refreshGuidedReadiness();
    // EnviroDesign is an advanced, user-invoked screen. Do not load external RDKit.js/WASM during core startup.
  } catch (error) { toast(`Startup check failed: ${error.message}`,6000); }
}

document.addEventListener("DOMContentLoaded",()=>{
  init();
  if (navigator.serviceWorker?.register) navigator.serviceWorker.register("/static/sw.js").catch(()=>{});
});

/* ---- Transformation products in soil (theoretical screen) ---- */
const TP_COLORS = ["#2a6f97", "#c2571a", "#3a7d44", "#8e4585", "#b08900", "#5c6b73", "#a4243b", "#1b7f79", "#6a4c93"];
const TP_SOURCES = [["auto", "Best available: your DT50, else PEPPER, BIOWIN only as last resort"], ["measured", "Measured"], ["pepper_prediction", "PEPPER prediction"], ["opera_prediction", "OPERA prediction"], ["biowin_screen", "BIOWIN screen (via score)"], ["user_estimate", "Own estimate"], ["pepper_auto", "PEPPER prediction from SMILES (fills the DT50)"]];
const TP_EXAMPLE = {
  parent: { name: "Carbamazepine", smiles: "NC(=O)N1c2ccccc2C=Cc2ccccc21", mw: 236.27, log_p: 2.45, pka_a: "", pka_b: "", dt50: 100, temp: 20, source: "user_estimate", lo: 30, hi: 330 },
  products: [
    { name: "Carbamazepine-10,11-epoxide", smiles: "NC(=O)N1c2ccccc2C2OC2c2ccccc21", mw: 252.27, log_p: 1.1, pka_a: "", pka_b: "", dt50: 30, temp: 20, source: "user_estimate", ff: 0.2, from: "", lo: 10, hi: 90, ff_lo: 0.08, ff_hi: 0.45 },
    { name: "10,11-Dihydroxycarbamazepine", smiles: "NC(=O)N1c2ccccc2C(O)C(O)c2ccccc21", mw: 270.28, log_p: 0.3, pka_a: "", pka_b: "", dt50: 60, temp: 20, source: "user_estimate", ff: 0.5, from: "Carbamazepine-10,11-epoxide", ff_lo: 0.25, ff_hi: 0.8 },
  ],
};

function tpNumber(id) { const value = $(id)?.value; return value === "" || value == null ? null : Number(value); }

function tpSubstanceHtml(prefix, item, isProduct) {
  const sourceOptions = TP_SOURCES.map(([value, label]) => `<option value="${value}"${item.source === value ? " selected" : ""}>${label}</option>`).join("");
  const field = (name, label, value, attrs = "") => `<label><span>${label}</span><input data-tp="${name}" value="${escapeHtml(String(value ?? ""))}" ${attrs}/></label>`;
  return `<div class="tp-substance" data-tp-prefix="${prefix}">
    <div class="cl-row2">${field("name", "Name", item.name)}${field("mw", "Molecular weight (g/mol)", item.mw, 'type="number" step="any" min="0"')}</div>
    ${field("smiles", "SMILES (optional: fills a blank MW / log P and enables the PEPPER DT50)", item.smiles)}
    <div class="cl-row3">${field("log_p", "log P", item.log_p, 'type="number" step="any"')}${field("pka_a", "pKa (acid)", item.pka_a, 'type="number" step="any"')}${field("pka_b", "pKa (base)", item.pka_b, 'type="number" step="any"')}</div>
    <div class="cl-row3">${field("dt50", "Soil DT50 (days)", item.dt50, 'type="number" step="any" min="0"')}${field("temp", "DT50 measured at (°C)", item.temp, 'type="number" step="any"')}
      <label><span>DT50 source</span><select data-tp="source">${sourceOptions}</select></label></div>
    ${field("biowin4", "BIOWIN4 score from EPI Suite (last resort, used only if nothing better exists)", item.biowin4 ?? "", 'type="number" step="any"')}
    <div class="cl-row2">${field("dt50_lo", "DT50 90 % range: low (days, optional)", item.lo ?? "", 'type="number" step="any" min="0"')}${field("dt50_hi", "DT50 90 % range: high (days, optional)", item.hi ?? "", 'type="number" step="any" min="0"')}</div>
    ${isProduct ? `${field("pathway_source", "Pathway source (tool or reference that proposed it, optional)", item.pathway_source ?? "")}<label><span>Formed from</span><select data-tp="formed_from" data-tp-from="${escapeHtml(item.from || "")}"></select></label>
    <div class="cl-row2">${field("ff", "Formation fraction (molar, 0–1) of its source", item.ff ?? "", 'type="number" step="any" min="0" max="1" placeholder="blank = 1.0 worst case"')}
      <button class="ghost-button" type="button" data-tp-remove="1">Remove</button></div>
    <div class="cl-row2">${field("ff_lo", "Formation fraction 90 % range: low (optional)", item.ff_lo ?? "", 'type="number" step="any" min="0" max="1"')}${field("ff_hi", "Formation fraction 90 % range: high (optional)", item.ff_hi ?? "", 'type="number" step="any" min="0" max="1"')}</div>` : ""}
  </div>`;
}

function tpRenderInputs(example) {
  $("tp-parent").innerHTML = tpSubstanceHtml("parent", example.parent, false);
  $("tp-products").innerHTML = example.products.map((item, index) => tpSubstanceHtml(`product-${index}`, item, true)).join("");
  tpRefreshSources();
}

// "Formed from" lists the parent and every OTHER product by its current name; a stale choice falls back to the parent.
function tpRefreshSources() {
  const parentName = (document.querySelector('#tp-parent [data-tp="name"]')?.value || "").trim() || "parent";
  const nodes = [...document.querySelectorAll("#tp-products [data-tp-prefix]")];
  const names = nodes.map((node, index) => (node.querySelector('[data-tp="name"]')?.value || "").trim() || `product ${index + 1}`);
  nodes.forEach((node, index) => {
    const select = node.querySelector('[data-tp="formed_from"]');
    if (!select) return;
    const wanted = select.value || select.dataset.tpFrom || "";
    const options = [["", parentName], ...names.map((name, other) => [name, name]).filter((_, other) => other !== index)];
    select.innerHTML = options.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}${value === "" ? " (parent)" : ""}</option>`).join("");
    select.value = options.some(([value]) => value === wanted) ? wanted : "";
    select.dataset.tpFrom = "";
  });
}

function tpReadSubstance(node, isProduct) {
  const get = (name) => node.querySelector(`[data-tp="${name}"]`)?.value ?? "";
  const num = (name) => (get(name) === "" ? null : Number(get(name)));
  const entry = { name: get("name").trim() || undefined, molecular_weight_g_mol: num("mw"), log_p: num("log_p"), pka_a: num("pka_a"), pka_b: num("pka_b"),
    dt50_days: num("dt50"), dt50_temperature_c: num("temp") ?? 20, dt50_source: get("source"), smiles: get("smiles").trim() || null };
  if (num("dt50_lo") !== null && num("dt50_hi") !== null) entry.dt50_range_days = [num("dt50_lo"), num("dt50_hi")];
  if (num("biowin4") !== null) entry.biowin4_score = num("biowin4");
  if (get("source") === "auto") { entry.dt50_auto = true; delete entry.dt50_source; if (entry.dt50_days != null) entry.dt50_source = "user_estimate"; }
  if (get("source") === "pepper_auto") { entry.dt50_from_pepper = true; delete entry.dt50_days; delete entry.dt50_source; delete entry.dt50_temperature_c; delete entry.dt50_range_days; }
  if (isProduct && get("ff") !== "") entry.formation_fraction = Number(get("ff"));
  if (isProduct && get("formed_from") !== "") entry.formed_from = get("formed_from");
  if (isProduct && get("pathway_source").trim() !== "") entry.pathway_source = get("pathway_source").trim();
  if (isProduct && num("ff_lo") !== null && num("ff_hi") !== null) entry.formation_fraction_range = [num("ff_lo"), num("ff_hi")];
  Object.keys(entry).forEach((key) => { if (entry[key] === null || entry[key] === undefined) delete entry[key]; });
  return entry;
}

function tpPayload() {
  const parentNode = document.querySelector('#tp-parent [data-tp-prefix]');
  const productNodes = [...document.querySelectorAll('#tp-products [data-tp-prefix]')];
  const region = $("tp-region").value;
  const payload = {
    parent: tpReadSubstance(parentNode, false), products: productNodes.map((node) => tpReadSubstance(node, true)),
    initial_parent_mg_kg: tpNumber("tp-c0"), duration_days: tpNumber("tp-duration") ?? 365,
  };
  payload.uncertainty = $("tp-band")?.checked === false ? false : { basis: $("tp-band-basis")?.value || "single_soil" };
  const oc = tpNumber("tp-oc");
  if (oc !== null) payload.soil = { organic_carbon_fraction: oc / 100, soil_ph: tpNumber("tp-ph") ?? 7 };
  const temperature = tpNumber("tp-temperature");
  if (temperature !== null) payload.temperature_c = temperature; else if (region) payload.region = region;
  return payload;
}

function tpFmt(value, digits = 3) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (value !== 0 && (Math.abs(value) < 0.001 || Math.abs(value) >= 10000)) return value.toExponential(2);
  return Number(value.toPrecision(digits)).toString();
}

// Confirmed OECD TG 301 (1992) para 10 ready-biodegradability pass/fail (60% ThOD, 301C only — see
// nite_ready_biodegradability.py for the full basis). Shared between the soil TP tab and the Identification screen.
function readyBiodegradabilityBadge(rb) {
  if (!rb) return "";
  const label = { pass: "Readily biodegradable (pass)", fail: "Not readily biodegradable (fail)",
    indicative_only: "Indicative only — window requirement not verifiable", not_applicable: "Not applicable (inherent-biodegradability test)",
    unknown: "Not classified" }[rb.classification] || escapeHtml(rb.classification);
  return `<span class="feature-chip" title="${escapeHtml(rb.basis)}">${escapeHtml(label)}</span> `;
}

function tpDrawChart(result) {
  const svg = $("tp-chart");
  const W = 560, H = 300, L = 48, R = 16, T = 16, B = 40;
  const times = result.times_days, tMax = times[times.length - 1];
  const series = [{ name: result.parent.name, values: result.parent.series_mg_kg.map((v) => (v / result.initial_parent_mg_kg) * 100) },
    ...result.products.map((p) => ({ name: p.name, values: p.series_percent_of_applied_molar }))];
  const band = result.uncertainty_band?.available ? result.uncertainty_band : null;
  const bandSeries = band ? [band.parent.percent_of_applied_molar, ...band.products.map((p) => p.percent_of_applied_molar)] : [];
  const yMax = Math.max(100, ...series.flatMap((s) => s.values), ...bandSeries.flatMap((b) => b.p95));
  const niceMax = Math.ceil(yMax / 10) * 10;
  const x = (t) => L + (t / tMax) * (W - L - R);
  const y = (v) => T + (1 - v / niceMax) * (H - T - B);
  const grid = [];
  for (let i = 0; i <= 5; i += 1) {
    const v = (niceMax * i) / 5;
    grid.push(`<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" stroke-opacity=".12"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="currentColor">${tpFmt(v, 3)}</text>`);
    const t = (tMax * i) / 5;
    grid.push(`<text x="${x(t)}" y="${H - B + 16}" text-anchor="middle" font-size="11" fill="currentColor">${tpFmt(t, 3)}</text>`);
  }
  const major = `<line x1="${L}" x2="${W - R}" y1="${y(10)}" y2="${y(10)}" stroke="currentColor" stroke-opacity=".5" stroke-dasharray="5 4"/><text x="${W - R - 4}" y="${y(10) - 4}" text-anchor="end" font-size="11" fill="currentColor">10 %</text>`;
  const bandTimes = band ? band.times_days : [];
  const bands = bandSeries.map((b, index) => {
    const upper = b.p95.map((v, i) => `${x(bandTimes[i]).toFixed(1)},${y(v).toFixed(1)}`);
    const lower = b.p05.map((v, i) => `${x(bandTimes[i]).toFixed(1)},${y(v).toFixed(1)}`).reverse();
    return `<polygon points="${[...upper, ...lower].join(" ")}" fill="${TP_COLORS[index % TP_COLORS.length]}" fill-opacity=".16" stroke="none"/>`;
  });
  const lines = series.map((s, index) => `<polyline fill="none" stroke="${TP_COLORS[index % TP_COLORS.length]}" stroke-width="2" points="${s.values.map((v, i) => `${x(times[i]).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`);
  const peaks = result.products.map((p, index) => (p.peak.time_days === null ? "" :
    `<circle cx="${x(p.peak.time_days)}" cy="${y(p.peak.percent_of_applied_molar)}" r="4" fill="${TP_COLORS[(index + 1) % TP_COLORS.length]}"/>`)).join("");
  svg.innerHTML = `${grid.join("")}${bands.join("")}${major}${lines.join("")}${peaks}
    <text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" font-size="12" fill="currentColor">Days after application</text>
    <text transform="translate(12 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle" font-size="12" fill="currentColor">% of applied parent (molar)</text>`;
  $("tp-legend").innerHTML = (band ? `<span class="feature-chip">shaded = 5–95 % band (${band.basis === "single_soil" ? "single soil" : "typical soil"}, ${band.n_samples} draws)</span>` : "") + series.map((s, index) => `<span class="feature-chip"><i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${TP_COLORS[index % TP_COLORS.length]};margin-right:6px"></i>${escapeHtml(s.name)}</span>`).join("");
}

function tpSubstanceResult(item, isParent) {
  const sorption = item.sorption;
  let sorptionText = "not calculated (needs log P and soil organic carbon)";
  if (sorption?.available) {
    const mobility = sorption.very_mobile_clp ? "very mobile (CLP log Koc &lt; 2)" : sorption.mobile_clp ? "mobile (CLP log Koc &lt; 3)" : "not mobile by the CLP log Koc line";
    sorptionText = `log Koc ${tpFmt(sorption.log_koc)} · ${mobility} · ${escapeHtml(sorption.model)}`;
  } else if (sorption) sorptionText = escapeHtml(sorption.reason || "unavailable");
  const peak = item.peak;
  const peakText = isParent ? "" : `<p><strong>Peak:</strong> ${tpFmt(peak.concentration_mg_kg)} mg/kg (${tpFmt(peak.percent_of_applied_molar)} % of applied) ${peak.within_simulation_window ? `at day ${tpFmt(peak.time_days)}` : "— no peak inside the window (still rising); highest value in the window shown"}. ${item.major_transformation_product.flag ? (item.major_transformation_product.formation_fraction_defaulted ? '<span class="feature-chip">≥ 10 % only under the worst-case formation fraction of 1.0 — not evidence that it is a major product</span>' : '<span class="feature-chip">major transformation product (≥ 10 %)</span>') : "Below the 10 % major-product line."}</p>
    <p><small>Formation fraction ${tpFmt(item.formation_fraction)} — ${escapeHtml(item.formation_fraction_basis)}</small></p>`;
  const notes = (item.property_notes || []).map((n) => `<p><small>${escapeHtml(n)}</small></p>`).join("");
  const u = item.dt50_uncertainty;
  const uncertaintyText = u?.source === "user_range" ? `<p><small>Your 90 % range for the DT50: ${tpFmt(u.range_days[0])}–${tpFmt(u.range_days[1])} d (as stated, at the DT50's own temperature).</small></p>` : u ? `<p><small>PEPPER 90 % interval for the mean DT50 at 20 °C: ${u.mean_90CI_days ? `${tpFmt(u.mean_90CI_days[0])}–${tpFmt(u.mean_90CI_days[1])} d` : "n/a"} · single-soil 90 % interval ${u.single_soil_90PI_days ? `${tpFmt(u.single_soil_90PI_days[0])}–${tpFmt(u.single_soil_90PI_days[1])} d` : "n/a"} · confidence ${escapeHtml(String(u.confidence))}. Treat the number as a wide range, not a point.</small></p>` : "";
  const b = item._band;
  const bandText = b ? `<p><strong>Uncertainty (5–95 %):</strong> peak ${tpFmt(b.peak_percent_of_applied_molar.p05)}–${tpFmt(b.peak_percent_of_applied_molar.p95)} % of applied (median ${tpFmt(b.peak_percent_of_applied_molar.p50)} %), reached between day ${tpFmt(b.peak_time_days.p05)} and ${tpFmt(b.peak_time_days.p95)}. Probability of being a major product (≥ 10 %): <strong>${tpFmt(b.probability_major_transformation_product * 100, 2)} %</strong>.${b.drivers.length ? ` Main driver: ${escapeHtml(b.drivers[0].variable || b.drivers[0].substance)} (rank correlation ${tpFmt(b.drivers[0].spearman_rho, 2)}).` : ""}</p>` : "";
  const lineage = isParent ? "" : `<p><small>Generation ${item.generation} · formed from ${escapeHtml(item.formed_from)}${item.pathway_source ? ` · pathway source: ${escapeHtml(item.pathway_source)}` : ""}</small></p>`;
  const min = item.mineralization;
  const mineralizationText = min
    ? `<p><strong>Microbial mineralization (measured, context only):</strong> ${tpFmt(min.biodeg_percent)}% of theoretical oxygen demand${min.duration_days != null ? ` over ${tpFmt(min.duration_days)} d` : ""}${min.test_guideline ? ` (${escapeHtml(min.test_guideline)})` : ""} · NITE (Japan METI), n=${min.n}. ${readyBiodegradabilityBadge(min.readily_biodegradable)}<small>A ready-biodegradability screening result, not a soil DT50 — not used in the kinetics above.</small></p>`
    : "";
  return `<article class="hypothesis-card"><div><h4>${escapeHtml(item.name)}</h4>${lineage}
    <p><strong>DT50 at soil temperature:</strong> ${tpFmt(item.dt50_days)} d · ${escapeHtml(item.dt50_source.replace(/_/g, " "))}</p>
    <p><small>${escapeHtml(item.dt50_basis)}</small></p>${(item.dt50_ladder || []).map((step) => `<p><small>Ladder: ${escapeHtml(step)}</small></p>`).join("")}${uncertaintyText}${peakText}${bandText}
    <p><strong>Sorption:</strong> ${sorptionText}</p>${mineralizationText}${notes}</div></article>`;
}

async function tpRun() {
  const button = $("tp-run"), status = $("tp-status");
  let payload;
  try { payload = tpPayload(); } catch (error) { toast(error.message, 6000); return; }
  if (button) button.disabled = true;
  status.className = "design-status running";
  const usesPepper = [payload.parent, ...payload.products].some((entry) => entry.dt50_from_pepper);
  status.innerHTML = usesPepper ? "<strong>Calculating…</strong><small>PEPPER computes structure descriptors (Java) and can take up to a minute on the first run.</small>" : "<strong>Calculating…</strong>";
  try {
    const result = await api("/api/tp-soil-fate/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    state.tpSoilFate = result;
    const band = result.uncertainty_band;
    result.products.forEach((product) => { product._band = band?.available ? band.products.find((entry) => entry.name === product.name) : null; });
    tpDrawChart(result);
    $("tp-results").innerHTML = [tpSubstanceResult(result.parent, true), ...result.products.map((p) => tpSubstanceResult(p, false))].join("");
    const warnings = (result.warnings || []).map((w) => `<p><strong>Note:</strong> ${escapeHtml(w)}</p>`).join("");
    const bandNotes = !band ? "" : band.available
      ? `<p><strong>Uncertainty band:</strong> sampled ${band.sampled.map((s) => escapeHtml(s.name)).join(", ")}${band.fixed.length ? `; held fixed: ${band.fixed.map(escapeHtml).join(", ")}` : ""}.</p>${band.notes.map((n) => `<p>${escapeHtml(n)}</p>`).join("")}`
      : `<p><strong>No uncertainty band:</strong> ${escapeHtml(band.reason)}.</p>`;
    $("tp-notes").innerHTML = `${bandNotes}<p><strong>Soil temperature:</strong> ${tpFmt(result.target_temperature_c)} °C — ${escapeHtml(result.temperature_basis)}</p>${warnings}${result.limitations.map((l) => `<p>${escapeHtml(l)}</p>`).join("")}`;
    status.className = "design-status";
    status.innerHTML = `<strong>Calculated for ${escapeHtml(result.parent.name)} at ${tpFmt(result.target_temperature_c)} °C.</strong><small>${result.products.length} transformation product(s) · predictions are proxies; prefer measured DT50s.</small>`;
  } catch (error) {
    status.className = "design-status error";
    status.innerHTML = `<strong>Could not calculate.</strong><small>${escapeHtml(error.message)}</small>`;
  } finally {
    if (button) button.disabled = false;
  }
}

async function tpInit() {
  if (!$("tp-soil-fate")) return;
  tpRenderInputs(TP_EXAMPLE);
  try {
    const options = await api("/api/tp-soil-fate/options");
    const regions = Object.entries(options.region_temperature_c);
    $("tp-region").innerHTML = `<option value="">Reference (${options.reference_temperature_c} °C, no region)</option>` +
      regions.map(([code, temp]) => `<option value="${escapeHtml(code)}">${escapeHtml(code)} — ${temp} °C</option>`).join("");
    if (options.region_temperature_c[state.modelSystem] !== undefined) $("tp-region").value = state.modelSystem;
  } catch (error) {
    $("tp-region").innerHTML = '<option value="">Reference (20 °C, no region)</option>';
  }
  $("tp-run").addEventListener("click", tpRun);
  document.addEventListener("input", (event) => { if (event.target.matches?.('#tp-soil-fate [data-tp="name"]')) tpRefreshSources(); });
  $("tp-add-product").addEventListener("click", () => {
    const count = document.querySelectorAll("#tp-products [data-tp-prefix]").length;
    if (count >= 8) { toast("At most 8 main-stage transformation products.", 4000); return; }
    $("tp-products").insertAdjacentHTML("beforeend", tpSubstanceHtml(`product-${count}`, { name: "", mw: "", log_p: "", pka_a: "", pka_b: "", dt50: "", temp: 20, source: "measured", ff: "", from: "" }, true));
    tpRefreshSources();
  });
  $("tp-products").addEventListener("click", (event) => {
    if (event.target.closest("[data-tp-remove]")) { event.target.closest("[data-tp-prefix]").remove(); tpRefreshSources(); }
  });
  tpRun();
}
document.addEventListener("DOMContentLoaded", () => { tpInit(); });

/* ---- Hand-off: assessed chemical, its known transformation products and its soil PEC -> the soil TP screen ---- */
async function tpKnownProductsFor(chemical) {
  // Local reference data only (no live MassBank call), so a dead third-party service cannot block the hand-off.
  if (!chemical.inchikey) return { rows: [], message: "This chemical has no InChIKey, so its known transformation products cannot be looked up." };
  const block = await api(`/api/analytical-identification/${encodeURIComponent(chemical.inchikey)}/transformation-products`);
  return { rows: block.found && Array.isArray(block.known_transformation_products) ? block.known_transformation_products : [], message: block.message || null };
}

async function tpPredictedProductsFor(chemical, { numberOfSteps = 2 } = {}) {
  // BioTransformer's environmental-microbial module: real structure predictions, no formation fractions or rates.
  if (!chemical.smiles) return { rows: [], message: "This chemical has no SMILES, so predicted transformation products cannot be requested.", warnings: [] };
  const result = await api("/api/transformation-pathways/predict", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: "biotransformer", parent_smiles: chemical.smiles, parent_name: chemical.preferred_name, number_of_steps: numberOfSteps }),
  });
  const nodesById = new Map((result.pathway?.nodes || []).map((node) => [node.id, node]));
  const firstSourceByTarget = new Map();
  for (const edge of result.pathway?.edges || []) if (!firstSourceByTarget.has(edge.target)) firstSourceByTarget.set(edge.target, edge.source);
  const rows = (result.products || []).map((product) => {
    const sourceNode = nodesById.get(firstSourceByTarget.get(product.provider_node_id));
    return { ...product, formed_from_name: sourceNode ? sourceNode.name : null };
  });
  return { rows, message: result.warnings?.[0] || null, warnings: result.warnings || [] };
}

async function tpLoadFromAssessment({ knownTps, predictedTps } = {}) {
  const status = $("tp-status");
  const chemical = state.chemical;
  if (!chemical) { toast("Choose and confirm a chemical first.", 5000); return; }
  const profile = state.profile || {};
  const hasDt50 = profile.soil_dt50_days != null;
  const parent = {
    name: chemical.preferred_name, smiles: chemical.smiles || "", mw: chemical.molecular_weight_g_mol ?? "", log_p: profile.log_kow ?? "",
    pka_a: profile.pkaa ?? "", pka_b: profile.pkab ?? "", dt50: hasDt50 ? profile.soil_dt50_days : "", temp: 20,
    source: hasDt50 ? "user_estimate" : "auto", lo: "", hi: "",
  };
  let products = [];
  let productNote = "";
  if (knownTps || predictedTps) {
    status.className = "design-status running";
    status.innerHTML = "<strong>Looking up known transformation products…</strong>";
    try {
      let lookup;
      if (predictedTps) {
        status.innerHTML = "<strong>Predicting transformation products (BioTransformer)…</strong><small>This can take up to a minute.</small>";
        lookup = await tpPredictedProductsFor(chemical);
        products = lookup.rows.slice(0, 8).map((row) => ({
          name: row.name || "Unnamed product", smiles: row.smiles || "", mw: "", log_p: "", pka_a: "", pka_b: "", dt50: "", temp: 20,
          source: "auto", ff: "", from: row.formed_from_name || "", lo: "", hi: "", pathway_source: row.source || "BioTransformer (predicted)",
        }));
      } else {
        lookup = await tpKnownProductsFor(chemical);
        products = lookup.rows.slice(0, 8).map((row) => ({
          name: row.tp_name || "Unnamed product", smiles: row.tp_smiles || "", mw: "", log_p: "", pka_a: "", pka_b: "", dt50: "", temp: 20,
          source: "auto", ff: "", from: "", lo: "", hi: "",
        }));
      }
      productNote = products.length
        ? (predictedTps
            ? `${products.length} predicted transformation product(s) from BioTransformer's environmental-microbial module were added, with "Formed from" set from the predicted reaction. These are structure hypotheses, not confirmed products, and BioTransformer gives no formation fractions or rates: formation fractions are blank (worst case 1.0). Each DT50 uses the best-available ladder (measured OASIS data, then PEPPER, then BIOWIN only as a last resort). Review every structure before using it.`
            : `${products.length} curated parent–product pair(s) from NORMAN EAWAGTPS were added as direct products of the parent. They say the product is known, not that it forms in soil or in what yield: formation fractions are blank (worst case 1.0). Each DT50 uses the best-available ladder (measured OASIS data, then PEPPER, then BIOWIN only as a last resort). Rewire "Formed from" where a product comes from another product.`)
        : (lookup.message || (predictedTps ? "BioTransformer returned no transformation products for this structure." : "No known transformation products are recorded for this chemical."));
    } catch (error) {
      productNote = `The ${predictedTps ? "predicted-product" : "known-product"} lookup failed: ${error.message}`;
    }
  }
  if (!products.length) products = [{ name: "", smiles: "", mw: "", log_p: "", pka_a: "", pka_b: "", dt50: "", temp: 20, source: "measured", ff: "", from: "", lo: "", hi: "" }];
  tpRenderInputs({ parent, products });
  const soil = currentScreeningSoilEndpoint();
  if (soil && soil.concentration_ug_kg > 0) $("tp-c0").value = Number((soil.concentration_ug_kg / 1000).toPrecision(4));
  const options = state.modelSystem && [...$("tp-region").options].some((o) => o.value === state.modelSystem);
  if (options) $("tp-region").value = state.modelSystem;
  const parts = [
    `Parent: ${chemical.preferred_name}${hasDt50 ? " (soil DT50 from the reviewed profile — relabel it if it is measured)" : chemical.smiles ? " (no soil DT50 in the profile, so PEPPER will predict one)" : " (no soil DT50 and no SMILES: enter a DT50)"}.`,
    soil ? `Initial soil concentration: ${Number((soil.concentration_ug_kg / 1000).toPrecision(4))} mg/kg from the ${soil.label}.` : "No soil concentration from the assessment yet: set the initial parent concentration yourself.",
    productNote,
  ].filter(Boolean);
  status.className = "design-status";
  status.innerHTML = `<strong>Loaded from the assessed chemical.</strong><small>${parts.map(escapeHtml).join(" ")}</small>`;
  $("tp-soil-fate")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.addEventListener("DOMContentLoaded", () => {
  $("tp-use-assessed")?.addEventListener("click", () => tpLoadFromAssessment({ knownTps: false }));
  $("tp-use-known")?.addEventListener("click", () => tpLoadFromAssessment({ knownTps: true }));
  $("tp-use-predicted")?.addEventListener("click", () => tpLoadFromAssessment({ predictedTps: true }));
  $("continue-tp-soil")?.addEventListener("click", () => tpLoadFromAssessment({ knownTps: true }));
});

/* ---- Import products proposed by any pathway tool (QSAR Toolbox, CTS, CATALOGIC, a paper, a spreadsheet) ---- */
function tpSplitLine(line, delimiter) {
  const cells = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') { cell += '"'; i += 1; } else if (ch === '"') quoted = false; else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === delimiter) { cells.push(cell.trim()); cell = ""; } else cell += ch;
  }
  cells.push(cell.trim());
  return cells;
}

// Columns: name, SMILES, formation fraction (0-1, molar), formed from (parent or a product name), pathway source. Only the name is required.
function tpParseImport(text) {
  const rows = [];
  const issues = [];
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  lines.forEach((line, index) => {
    const delimiter = line.includes("\t") ? "\t" : line.includes(";") ? ";" : line.includes("|") ? "|" : ",";
    const cells = tpSplitLine(line, delimiter);
    if (index === 0 && /^(name|product|tp)\b/i.test(cells[0]) && /smiles/i.test(line)) return; // header row
    const [name, smiles = "", ffText = "", from = "", source = ""] = cells;
    if (!name) { issues.push(`Line ${index + 1}: no name, skipped.`); return; }
    let ff = "";
    if (ffText !== "") {
      const value = Number(ffText);
      if (!Number.isFinite(value) || value <= 0 || value > 1) { issues.push(`Line ${index + 1} (${name}): formation fraction "${ffText}" is not a number in (0, 1], so it was left blank (worst case 1.0).`); } else ff = value;
    }
    if (!smiles) issues.push(`Line ${index + 1} (${name}): no SMILES, so enter its molecular weight and DT50 yourself.`);
    rows.push({ name, smiles, ff, from, source });
  });
  return { rows, issues };
}

function tpImportProducts(text) {
  const { rows, issues } = tpParseImport(text);
  const existing = [...document.querySelectorAll("#tp-products [data-tp-prefix]")];
  const room = 8 - existing.length;
  if (!rows.length) return { added: 0, issues: issues.length ? issues : ["Nothing to import: paste one product per line."] };
  if (rows.length > room) issues.push(`Only ${Math.max(room, 0)} more product(s) fit (8 in total); the rest were not added.`);
  const names = new Set(existing.map((node) => (node.querySelector('[data-tp="name"]')?.value || "").trim()));
  const parentName = (document.querySelector('#tp-parent [data-tp="name"]')?.value || "").trim();
  const accepted = [];
  for (const row of rows.slice(0, Math.max(room, 0))) {
    if (names.has(row.name) || row.name === parentName) { issues.push(`${row.name}: a substance with that name is already listed, skipped.`); continue; }
    names.add(row.name);
    accepted.push(row);
  }
  const known = new Set([parentName, ...names]);
  accepted.forEach((row, offset) => {
    let from = row.from;
    if (from && from !== "parent" && !known.has(from)) { issues.push(`${row.name}: formed-from "${from}" is not the parent or a listed product, so it is set to the parent.`); from = ""; }
    if (from === "parent" || from === parentName) from = "";
    const count = document.querySelectorAll("#tp-products [data-tp-prefix]").length;
    $("tp-products").insertAdjacentHTML("beforeend", tpSubstanceHtml(`product-${count + offset}`, {
      name: row.name, smiles: row.smiles, mw: "", log_p: "", pka_a: "", pka_b: "", dt50: "", temp: 20,
      source: "auto", ff: row.ff, from, lo: "", hi: "", pathway_source: row.source,
    }, true));
  });
  tpRefreshSources();
  return { added: accepted.length, issues };
}

document.addEventListener("DOMContentLoaded", () => {
  $("tp-import-run")?.addEventListener("click", () => {
    const outcome = tpImportProducts($("tp-import-text").value);
    const status = $("tp-status");
    status.className = "design-status";
    status.innerHTML = `<strong>${outcome.added} product(s) imported.</strong><small>${outcome.issues.map(escapeHtml).join(" ") || "Set a DT50 (or keep PEPPER) and a formation fraction for each, then calculate. Blank formation fractions use the worst case of 1.0."}</small>`;
    if (outcome.added) $("tp-import-text").value = "";
  });
  $("tp-import-file")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (file) $("tp-import-text").value = await file.text();
    event.target.value = "";
  });
});
