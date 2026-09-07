# EPA execution bridge

Release: EnviroChem Studio v2.23.0 Alpha 3.1  
Bridge contract: `ENVIROCHEM_EXTERNAL_EXECUTION_BRIDGE_1.0`

## What this integration does

EnviroChem prepares, executes where a validated unattended contract exists,
captures, imports and reviews workflows for four separately installed US EPA
tools:

| Tool | EnviroChem route | Default state |
|---|---|---|
| PWC 3.003 | FIFRA pesticide surface water, sediment and simple groundwater | Manual handoff until an operator validates a batch contract |
| ChemSTEER 3.2 | TSCA industrial releases and occupational exposure | Manual handoff |
| CEM 3.2 | TSCA consumer product/article exposure | Manual handoff |
| E-FAST 2014 | Legacy release, landfill, consumer and general-population screening | Manual handoff; legacy label retained |

The official software is not included. EPA's current pages provide the official
downloads and documentation for [PWC](https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment),
[ChemSTEER](https://www.epa.gov/tsca-screening-tools/chemsteer-chemical-screening-tool-exposures-and-environmental-releases),
[consumer exposure/CEM](https://www.epa.gov/tsca-screening-tools/approaches-estimate-consumer-exposure-under-tsca)
and [E-FAST](https://www.epa.gov/tsca-screening-tools/e-fast-exposure-and-fate-assessment-screening-tool-version-2014).

## Manual or GUI execution

This is the default and safest route when the official application has no
validated unattended interface.

1. Prepare a complete `ModelWorkflow`.
2. Download **Official-run handoff ZIP** from the Expert Workspace.
3. Review every unresolved input and enter it in the separately installed tool.
4. Run the unmodified official software and retain its complete output set.
5. Upload the original files through **Import official output files**.
6. Record model version, executable version, operator and execution notes.
7. Map each required endpoint in the structured-output JSON.
8. An independent scientist records accepted, revision-required or rejected.

Files are never inferred from pasted results. Each original file receives a
SHA-256, and the set hash, versions, operator and confirmation are retained in
the workflow audit record.

## Optional controlled local execution

Local execution is off by default. It is suitable only where the operator has
verified that the separately installed tool or an authorised, non-modifying
launcher has a deterministic unattended contract.

Configure the exact executable and a fixed JSON argument/output contract in
`.env`, then restart EnviroChem:

```text
ENVIROCHEM_EXTERNAL_EXECUTION_ENABLED=true
ENVIROCHEM_EXTERNAL_EXECUTION_TIMEOUT_SECONDS=900
ENVIROCHEM_PWC_PATH=C:\exact\path\to\authorised-tool.exe
ENVIROCHEM_PWC_COMMAND_ARGS_JSON=["--input","{manifest}","--output","{output_dir}"]
ENVIROCHEM_PWC_OUTPUT_GLOBS_JSON=["output/**/*.txt","output/**/*.csv"]
```

The command shown is syntax documentation only; it is **not** a statement that
PWC supports those switches. Equivalent variables exist for `CHEMSTEER`, `CEM`
and `EFAST`. Supported placeholders are:

- `{manifest}` — immutable input-manifest JSON;
- `{output_dir}` — empty output directory inside the run workspace;
- `{workspace}` — isolated run workspace.

The browser cannot submit a command or executable path. Before each run, the
operator must acknowledge the currently calculated executable SHA-256. The
bridge invokes an argument array without a shell, applies a fixed timeout,
captures stdout/stderr and hashes files matching the configured relative globs.
A zero exit code without an output file is recorded as a failed execution.

## Scientific acceptance gate

For these four tools, **accepted** is blocked unless:

- the output record carries genuine-execution provenance;
- original output files or bridge-captured files are retained and hashed;
- every tool-specific required endpoint is mapped to a non-empty value; and
- a reviewer records the scientific decision and notes.

Preparation, launching and output capture are distinct states. None is silently
presented as regulatory acceptance.

## US industrial groundwater screen

The native industrial screen now considers a direct soil release through an
optional, transparent soil-to-groundwater calculation:

1. `Kd = Koc × fOC`;
2. annual soil loading is divided by source-zone water plus `Kd × soil mass`;
3. vertical water travel time is multiplied by
   `1 + bulk density × Kd / water content`;
4. first-order survival is applied using the reviewed soil DT50; and
5. an explicit additional-attenuation fraction is applied (default `1`, meaning
   no unsupported extra attenuation).

The output includes pore-water concentration, retardation, travel time,
survival, groundwater concentration, equations and all inputs. The screen omits
preferential flow, layered/transient weather, crop processes, runoff and
erosion. It is not PWC or PRZM and is a trigger for refinement, not a US EPA
regulatory endpoint.

## Routing corrections

- The industrial source-term workbench is displayed only when **US**,
  **Industrial** and **Manufacturing / processing** are all selected.
- The native European water–sediment process workbench is available only for a
  relevant organic-chemical pathway at Tier 2 or higher.
- The native workbench is not labelled TOXSWA.
- Official SWASH/FOCUS_TOXSWA preparation appears only for EU pesticide
  soil/spray pathways at Tier 3 or 4.
- PWC remains pesticide-only.

## Commercial and regulatory boundary

EnviroChem does not redistribute, modify, merge or create a derivative of the
EPA tools. The ChemSTEER, CEM and E-FAST pages state software-use terms that
must be reviewed before commercial deployment. Calling a separately installed
copy does not by itself resolve contractual, cybersecurity, validation or
regulatory-acceptance questions; obtain appropriate legal and quality-system
review for the intended deployment.

This bridge closes the execution/provenance gap for the named tools. It does not
make EnviroChem a complete US risk assessment platform. EPA describes TSCA
assessment as covering occupational, consumer, general-population and ecological
exposure, with measured information preferred and models used in a tiered
weight-of-evidence process; see [EPA's predictive-methods overview](https://www.epa.gov/tsca-screening-tools/using-predictive-methods-assess-exposure-and-fate-under-tsca).
