# Requirements Document

## Introduction

OmniGridX is a Massachusetts commercial-site solar-and-storage screening product hypothesis. The immediate delivery target is the **Fast_Judge_MVP**: a deterministic, public, sample-only demonstration that compares exactly three alternatives—existing operation, documented rule-based dispatch, and cost-minimized optimized dispatch—and reports screening cost, deterministic outage service, purchased-electricity emissions, and clean-energy metrics. The Fast_Judge_MVP accepts only bundled non-customer inputs and makes no customer, tariff-verification, reliability, forecasting, or commercial-validation claim.

**Commercial status:** Unvalidated: no paid pilot, signed order, repeat purchase, customer data commitment, or measured workflow improvement has been supplied.

The **Public_Data_Business_Dashboard** is a distinct **Post_MVP_Capability** for Massachusetts business users. The dashboard uses approved public federal, Massachusetts, and ISO-NE data only; provides aggregate demand, supply, storage, policy, and maintenance-planning views; accepts no customer uploads; and does not alter the completed Fast_Judge_MVP routes, dependency boundary, outputs, or claims. The **First_Commercial_Release** remains a separate proposed customer-authorized workflow. Neither post-MVP surface changes Fast_Judge_MVP completion or judging history.

### Scope and applicability

| Scope | Requirements that gate the scope |
|---|---|
| Fast_Judge_MVP | Bundled sample ingestion and provenance already implemented under Requirements 1 and 10.1–10.2; interval accounting and independent checking under Requirement 2; optimization under Requirement 3; exactly three alternatives under Requirement 4; sample Screening_Estimate cost under Requirements 5.1–5.3; deterministic outage metrics under Requirement 6; emissions under Requirement 8; release labels under Requirement 11; sample-only public safety under Requirements 13.1, 13.12, and 13.13; and judge delivery under Requirement 14. |
| Public_Data_Business_Dashboard | Public-only navigation and access under Requirement 15; policy snapshots under Requirement 16; aggregate demand and supply intelligence under Requirement 17; checked storage presentation under Requirement 18; maintenance-window planning under Requirement 19; and bounded public-data refresh and deployment isolation under Requirement 20. |
| First_Commercial_Release / other Post_MVP_Capability | Historical tariff verification and reconciliation under Requirements 5.4–5.14; customer-authorized forecasting under Requirement 7 where applicable; additional state-pack activation and isolation under Requirements 10.3–10.11; commercial-validation evidence under Requirement 12; and real customer-data, private, production, tenant, retention, backup, and incident operations under Requirements 13.2–13.11. |

All Fast_Judge_MVP outputs are advisory sample Screening_Estimates, not autonomous dispatch instructions, probabilistic reliability studies, feeder or interconnection feasibility findings, legal advice, investment-grade projections, verified tariff calculations, or future-savings validation. No ML, weather, or demand forecasting code or claim is part of the Fast_Judge_MVP. Optimization may be described as grid intelligence, but OmniGridX does not describe the Fast_Judge_MVP as AI forecasting. Forecasting, policy refresh, and approved remote adapters introduced for Public_Business_Mode remain absent from Fast_Judge_MVP routes and runtime dependencies.

## Glossary

- **OmniGridX**: The complete platform described by this document.
- **Fast_Judge_MVP**: The immediate sample-only judge release containing one deterministic bundled scenario, exactly three alternatives, independent constraint checking, sample Screening_Estimate cost, outage, emissions, clean-energy metrics, one comparison/report page, and minimal JSON/HTML endpoints.
- **Post_MVP_Capability**: A capability that is absent from the Fast_Judge_MVP public routes and runtime dependency graph and does not block judge delivery; a Post_MVP_Capability may be implemented in a separately isolated deployment mode.
- **Public_Data_Business_Dashboard**: A post-MVP, no-upload dashboard for Massachusetts business users that presents approved public federal, Massachusetts, and ISO-NE demand, supply, policy, storage, and maintenance-planning information.
- **Public_Business_Mode**: The deployment mode that serves the Public_Data_Business_Dashboard, uses only approved public sources and derived public-data results, and remains isolated from Public_Judge_Demo_Mode and customer-data operations.
- **Approved_Remote_Adapter**: A bounded, allowlisted connector for one documented canonical public federal, Massachusetts, or ISO-NE source, with fixed request limits, timeouts, retry limits, schema validation, and provenance capture.
- **Refresh_Run**: One scheduled or operator-triggered attempt to retrieve, validate, snapshot, and atomically publish approved public Dataset versions for Public_Business_Mode.
- **Aggregate_Scope**: A declared combination of geography, interval, time period, and measurement basis used to determine whether demand and supply values are comparable.
- **Official_Published_Demand_Forecast**: A demand forecast published by an approved federal, Massachusetts, or ISO-NE canonical source with declared issue time, horizon, geography, interval, and source methodology.
- **Validated_Baseline_Forecast**: A transparent demand forecast produced from approved historical public data, evaluated on time-ordered holdout observations against a declared simple comparator, and reported with error by horizon.
- **Supply_Context**: Public generation, capacity, production, imports, or fuel-mix information whose source, Aggregate_Scope, freshness, and limitations are declared.
- **Maintenance_Window_Plan**: An optimization result that identifies feasible asset-unavailability windows from declared duration, availability, operating constraints, and demand and Supply_Context inputs; the result is planning guidance rather than asset-health or failure prediction.
- **Sample_Screening_Rate_Configuration**: A dated, versioned sample-only energy-import rate, optional export credit, currency, units, source or assumption label, effective period, and exclusions used only to compare bundled alternatives; the configuration is not a tariff or account-verification claim.
- **First_Commercial_Release**: The proposed release limited to repeated Massachusetts commercial-site solar-and-storage screening for the Buyer_Hypothesis using Authorized_Customer_Data.
- **Buyer_Hypothesis**: A principal or practice leader at an independent energy consultancy who controls or influences budget for repeated commercial-site screening.
- **Authorized_Customer_Data**: Customer interval meter data, bills, and site inputs supplied under recorded authorization and data-use terms.
- **Hackathon_Demo**: A sample-data-only demonstration that supplies no evidence of buyer demand or production fitness.
- **Public_Judge_Demo_Mode**: A public, no-login Hackathon_Demo deployment that serves only bundled non-customer samples through a restricted judge-facing surface and provides no customer-data or mutable commercial-validation capability.
- **Future_Capability**: Functionality excluded from the First_Commercial_Release pending separate technical and commercial validation.
- **Commercial_Validation_Record**: Evidence record containing buyer role and budget authority, current workflow, annual project frequency, analyst and reviewer hours, current spend, urgency, accepted deliverable, order and payment evidence, measured outcomes, and stop-or-narrow decisions.
- **Data_Ingestion_Service**: The subsystem that retrieves, validates, and normalizes external data.
- **Dataset**: A versioned collection of time-series or static records from one source.
- **Climate_Dataset**: Historical climate records used for screening.
- **Weather_Forecast**: Weather values available at a declared forecast issue time.
- **Demand_Dataset**: Historical electricity-demand records for a declared geography.
- **Source_Record**: Metadata for an approved source comprising publisher, canonical URL, dataset ID, retrieval time, version or as-of date, geography, units, cadence, coverage, access terms, quality status, and allowed and prohibited uses.
- **Raw_Dataset**: An immutable byte-for-byte copy of received source data linked to a Source_Record.
- **Freshness_Threshold**: The maximum configured age permitted for a Dataset for a declared use.
- **Simulation_Engine**: The subsystem that performs interval energy accounting for a Scenario.
- **Scenario**: A named configuration of site loads, assets, constraints, Dataset versions, tariff, assumptions, and Simulation_Horizon.
- **Simulation_Horizon**: The declared time span and fixed interval duration for a Scenario.
- **Microgrid**: The modeled site generation, Battery_Storage, and electrical loads.
- **Utility_Grid**: The modeled external grid connection, represented only by declared availability and import and export constraints.
- **Battery_Storage**: A modeled storage asset with energy capacity, power limits, efficiencies, initial and terminal state-of-charge treatment, and reserve behavior.
- **State_of_Charge**: Energy stored in Battery_Storage, measured in kilowatt-hours.
- **Unserved_Load**: Demand not served during an interval, measured in kilowatt-hours and separated into critical and noncritical load.
- **Interruption_Duration**: Sum of interval durations in which critical Unserved_Load is greater than zero.
- **Outage_Service_Screening**: Deterministic evaluation under a declared outage start, duration, grid availability, load, asset, and reserve assumptions; not probabilistic reliability analysis.
- **Optimizer**: The subsystem that computes a feasible dispatch schedule under Scenario constraints.
- **Operating_Cost**: Modeled supported tariff charges minus modeled export credits over the Simulation_Horizon, excluding optimization penalties and degradation costs unless those items are tariff charges.
- **Optimization_Objective**: Operating_Cost plus configured Battery_Storage degradation cost and configured critical and noncritical Unserved_Load penalties.
- **Clean_Energy_Share**: Served load supplied directly by qualifying on-site zero-emission generation or by Battery_Storage energy whose qualifying origin is tracked, divided by total served load.
- **Recommendation_Service**: The subsystem that compares three defined alternatives and applies buyer-supplied mandatory constraints and a decision rule.
- **Screening_Estimate**: The default label for modeled cost and savings results.
- **Historically_Reconciled_Tariff_Calculation**: A historical tariff-calculation status for one independently verified account and tariff configuration, based on held-out billing periods, tariff version and effective period, modeled line items, exclusions, and pilot-agreed line-item and total error tolerances; the status does not validate future savings.
- **Verified_Tariff_Configuration**: One account-specific tariff configuration independently checked against the controlling tariff and account applicability; no tariff, including National Grid Massachusetts G-3, is considered verified before this check.
- **Customer_Interval_Data**: Authorized meter readings for one customer account at the resolution required by the applicable tariff calculation.
- **Purchased_Electricity_Emissions_Estimate**: Operational CO2-equivalent from gross nonnegative imported electricity using a declared Emissions_Factor; exports do not reduce the estimate.
- **Emissions_Factor**: A factor with value, units, geography, data year, version, included gases, intended purpose, source, and average-or-marginal classification.
- **Operational_ML_Forecast**: A near-term demand forecast limited to a validated horizon and evaluated using time-based holdout data and weather available at issue time.
- **Long_Range_Scenario_Projection**: A demand projection beyond the validated Operational_ML_Forecast horizon, based on declared growth assumptions and not labeled as a forecast.
- **Aggregate_Demand_Threshold_Comparison**: A territory-level comparison of aggregate demand with a declared threshold that makes no feeder, service-connection, or interconnection-feasibility claim.
- **Utility_Planner**: A user evaluating territory-level aggregate demand.
- **Data_Center_Load**: A declared large-load profile; bespoke thermal modeling is a Future_Capability.
- **Policy_Snapshot**: An immutable, dated, versioned set of policy records pinned to a result.
- **Policy_Record**: Policy metadata containing issuer, canonical source, legal-or-advisory status, publication date, effective period, jurisdiction, customer and asset applicability, last review date, supersession status, named owner, review status, and informational-or-calculation use.
- **MA_Regional_Context**: Massachusetts-specific geography, tariff, emissions, policy, calendar, and source configuration supplied by the Massachusetts_Data_Pack.
- **State_Data_Pack**: Versioned configuration and adapters for one state containing approved datasets, utility territories, tariffs, emissions factors, policy snapshots, geography mappings, and source metadata without changes to core simulation or optimization code.
- **Massachusetts_Data_Pack**: The first State_Data_Pack, built from the Hackachusetts 2026 climate catalog, Massachusetts official sources, federal sources, ISO-NE, and customer-authorized files.
- **Security_Baseline**: Controls required before OmniGridX receives real customer data or provides private-pilot, production, or publicly accessible customer-data operations; Public_Judge_Demo_Mode remains governed by its stricter sample-only route and startup restrictions.
- **Submission_Metadata**: Versioned Hackachusetts entry data containing the declared track, team members, authorized representative, project description, public judge-demo URL, local judge fallback, demonstration-video link, and Final_Submission_Commit.
- **Judge_Delivery_Package**: The public repository contents and instructions that let a judge install, run, and test the bundled sample-only OmniGridX demonstration without real customer data or authentication.
- **Submission_Writeup**: The evidence-based description of OmniGridX features, Kiro usage, development workflow, public data sources, and third-party tools supplied with the submission.
- **Third_Party_Notices**: The inventory of third-party and open-source code, assets, data, marks, music, copyrighted material, licenses, and attribution obligations used by submission artifacts.
- **Submission_Validator**: A deterministic local check of machine-verifiable Judge_Delivery_Package and Submission_Metadata requirements.
- **Final_Submission_Commit**: The recorded Git commit identifier whose repository contents constitute the submitted project materials.

## Approved Massachusetts Data Sources

The [Hackachusetts 2026 climate catalog](https://hackachusetts2026.vercel.app/#/climate) is a discovery catalog and is not necessarily the authoritative publisher. Each Source_Record must identify the underlying publisher through the canonical publisher URL rather than relying on the discovery URL alone.

### Core Sources for OmniGridX

1. **Boston BERDO 2021 building energy and emissions** — [City of Boston dataset API](https://data.boston.gov/api/3/action/datastore_search?resource_id=43e4abc9-1fae-40d9-a02e-ff950bd0e732&fields=Property_Type,Zip,Year_Built,Gross_Area_sf,Site_EUI_kBtuft2,ENERGY_STAR_Score,GHG_Emissions_MTCO2e,GHG_Intensity_kgCO2sf,per_Electricity,per_Gas&limit=100). Approved as a building-screening benchmark; the dataset is not customer interval demand and does not prove site load.
2. **Massachusetts electric utility by town** — [Massachusetts ArcGIS query](https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/ElectricityProviders/MapServer/0/query?where=1%3D1&outFields=TOWN,ELEC,ELEC_LABEL&returnGeometry=false&f=json). Approved for utility-territory lookup; the dataset is not proof of tariff or account applicability.
3. **Renewables at Massachusetts landfills** — [Massachusetts DEP ArcGIS query](https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/DEP/RenewablesAtMaLandfills/MapServer/0/query?where=1%3D1&outFields=MUNICIPALITY,FACILITY,TYPE_,MW_PERMITTED,MW_OPERATING,STATUS_1,OPERATING_SINCE&returnGeometry=false&f=json). Approved for existing-project context; the dataset is not a site generation profile.
4. **HIFLD transmission lines** — [HIFLD ArcGIS query](https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0/query?geometry=-73.5081%2C41.1870%2C-69.9284%2C42.8868&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=OWNER,VOLTAGE,VOLT_CLASS,TYPE,STATUS&returnGeometry=false&resultRecordCount=100&f=json). Approved for infrastructure context only; the dataset does not establish feeder headroom or electrical-connection feasibility.
5. **ISO-NE ISO Express** — [ISO Express](https://www.iso-ne.com/isoexpress/) and [load and demand reports](https://www.iso-ne.com/isoexpress/web/reports/load-and-demand). Approved as a regional or zonal demand, price, generation-mix, and forecast benchmark; the reports are not site load or feeder capacity.
6. **Massachusetts energy data** — [Massachusetts energy data](https://www.mass.gov/massachusetts-energy-data). Approved for state consumption, generation, and emissions context and source links; the page is a guidance portal rather than a single normalized dataset.
7. **Massachusetts Climate Change Assessment** — [assessment information](https://www.mass.gov/info-details/massachusetts-climate-change-assessment). Approved for hazard and policy context; the assessment is guidance rather than a load forecast.
8. **ResilientMass** — [ResilientMass](https://resilient.mass.gov/). Approved for municipal adaptation-plan guidance and context.
9. **Massachusetts electric rates and tariffs** — [rates and tariffs information](https://www.mass.gov/info-details/massachusetts-electric-rates-and-tariffs). Approved for tariff discovery; customer-facing tariff application still requires the controlling utility filing and confirmation of account eligibility.
10. **National Weather Service API** — [NWS API documentation](https://www.weather.gov/documentation/services-web-api). Approved for short-range weather forecasts; forecasts do not establish long-term climate conditions, site load, or generation output.
11. **NREL/NLR National Solar Radiation Database** — [NSRDB](https://nsrdb.nlr.gov/). Approved for historical solar and weather-resource data; modeled or gridded values require site-specific qualification and do not constitute a generation guarantee.
12. **EPA eGRID** — [eGRID summary data](https://www.epa.gov/egrid/summary-data). Approved for inventory emissions factors; eGRID factors are retrospective aggregate factors and do not represent real-time marginal emissions.
13. **EIA Massachusetts electricity profile** — [Massachusetts profile](https://www.eia.gov/electricity/state/massachusetts/). Approved as a state-level benchmark; aggregated annual statistics do not establish site demand, tariff applicability, or local grid capacity.

### Supplementary and Optional Sources

The [eMOLT bottom-temperature dataset](https://erddap.ondeckdata.com/erddap/tabledap/emolt_data.csv), [NOAA buoy 44013](https://www.ndbc.noaa.gov/data/realtime2/44013.txt), NOAA Boston tide data, USGS Charles River discharge data, MassGIS environmental-justice blocks, and fish-monitoring data are approved only as climate, equity, or resilience context unless an explicit use case requires a listed source. These sources are supplementary and are not required by the energy model.

Customer_Interval_Data, actual customer bills, the applicable rate, account classification, supply contract, asset specifications, and operating limits are required for customer-specific conclusions. Public datasets cannot substitute for those customer-authorized inputs. No approved source by itself proves buyer demand, site load, tariff applicability, or electrical-connection feasibility.

## Requirements

### Requirement 1: Ingest and Qualify Data

**User Story:** As an energy consultant, I want traceable and validated customer and public data, so that screening results disclose data quality and provenance.

#### Acceptance Criteria

1. WHEN Data_Ingestion_Service receives a record timestamp, THE Data_Ingestion_Service SHALL require an explicit UTC offset or named time zone and store the instant and the America/New_York representation without collapsing repeated daylight-saving wall-clock times.
2. WHEN Data_Ingestion_Service receives a numeric field, THE Data_Ingestion_Service SHALL accept the field only when the value is numeric and finite and the unit is declared.
3. WHEN Data_Ingestion_Service receives a source, THE Data_Ingestion_Service SHALL create a Source_Record and store a Raw_Dataset unchanged with provenance linking every normalized record to the Raw_Dataset and Source_Record.
4. WHEN Data_Ingestion_Service validates a Dataset, THE Data_Ingestion_Service SHALL check required fields, timestamps, units, cadence, geography, duplicates, temporal and geographic coverage, and configured plausible ranges.
5. IF a validation rule has record scope, THEN THE Data_Ingestion_Service SHALL reject each affected record, retain valid records, and identify the record, field, and failed rule.
6. IF a validation rule has Dataset scope or every record fails validation, THEN THE Data_Ingestion_Service SHALL reject the Dataset version, preserve prior versions unchanged, and identify every failed Dataset-scope rule.
7. IF publisher, canonical URL, dataset ID, retrieval time, version or as-of date, geography, units, cadence, coverage, access terms, quality status, or allowed and prohibited uses is unavailable, THEN THE Data_Ingestion_Service SHALL reject the source for analysis and report the missing Source_Record metadata.
8. WHEN Data_Ingestion_Service downloads a remote source, THE Data_Ingestion_Service SHALL report remote-download duration separately from validation and normalization processing duration.
9. WHEN Data_Ingestion_Service processes a local snapshot of up to 1,000,000 records, THE Data_Ingestion_Service SHALL report record count and measured processing duration without including remote-download latency.
10. IF Dataset age exceeds the Freshness_Threshold for a use that requires current data, THEN THE Data_Ingestion_Service SHALL block that use and report the Dataset as-of date and threshold.
11. IF Dataset age exceeds the Freshness_Threshold for a use that permits historical data, THEN THE Data_Ingestion_Service SHALL qualify the result with source condition, as-of date, and resulting limitation.
12. IF a remote source remains unavailable after the configured attempts, THEN THE Data_Ingestion_Service SHALL return a source-specific error and preserve all stored Dataset versions unchanged.
13. WHEN the Hackachusetts climate catalog identifies a source, THE Data_Ingestion_Service SHALL treat the catalog as discovery metadata and the underlying publisher canonical URL as the authority.
14. THE First_Commercial_Release SHALL require Authorized_Customer_Data for site load and tariff conclusions.
15. THE First_Commercial_Release SHALL treat public and zonal data as contextual data that does not establish customer site load, tariff applicability, feeder capacity, electrical-connection feasibility, or buyer demand.

### Requirement 2: Perform Interval Energy-Balance Screening

**User Story:** As an energy consultant, I want complete interval energy accounting, so that I can detect physically inconsistent screening results.

#### Acceptance Criteria

1. WHEN a user submits a valid Scenario, THE Simulation_Engine SHALL produce exactly one record for every interval in the Simulation_Horizon.
2. THE Simulation_Engine SHALL report dispatched on-site generation, curtailed generation, gross grid imports, gross grid exports, Battery_Storage charge, Battery_Storage discharge, served critical load, served noncritical load, critical Unserved_Load, and noncritical Unserved_Load in kilowatt-hours for every interval.
3. THE Simulation_Engine SHALL enforce interval conservation such that dispatched generation plus gross imports plus Battery_Storage discharge equals served load plus Battery_Storage charge plus gross exports plus conversion losses for every interval.
4. THE Simulation_Engine SHALL constrain gross imports and gross exports by declared Utility_Grid availability, power limits converted using interval duration, and import and export permissions.
5. THE Simulation_Engine SHALL constrain each asset dispatch by declared asset availability and operating bounds for every interval.
6. IF a Scenario does not explicitly support simultaneous grid import and export, THEN THE Simulation_Engine SHALL return records with at most one positive grid-flow direction per interval.
7. IF a Scenario does not explicitly support simultaneous Battery_Storage charge and discharge, THEN THE Simulation_Engine SHALL return records with at most one positive storage-flow direction per interval.
8. IF a Scenario references a missing Dataset or required parameter, THEN THE Simulation_Engine SHALL reject the Scenario before simulation and identify each missing item.
9. IF the Simulation_Engine cannot satisfy conservation or a hard constraint, THEN THE Simulation_Engine SHALL return a diagnostic and no partial time series.
10. WHEN the Simulation_Engine returns an optimized schedule, THE Simulation_Engine SHALL run an independent constraint check over every interval and reject the schedule if any conservation, grid, asset, storage, reserve, or service constraint fails.
11. WHEN the Simulation_Engine returns a result, THE Simulation_Engine SHALL label the result as economic and energy-balance screening that does not evaluate voltage, thermal, protection, switching, islanding, feeder headroom, service connection, or interconnection approval.

### Requirement 3: Optimize Dispatch

**User Story:** As an energy consultant, I want constrained cost-minimizing dispatch, so that I can compare an optimized case with existing and rule-based operation.

#### Acceptance Criteria

1. WHEN optimization is requested for a completed Scenario, THE Optimizer SHALL minimize the Optimization_Objective subject to every Scenario hard constraint.
2. THE Optimizer SHALL include supported financial costs, configured Battery_Storage degradation cost, configured critical Unserved_Load penalty, and configured noncritical Unserved_Load penalty in the Optimization_Objective, with every component stated in currency units over the Simulation_Horizon.
3. THE Optimizer SHALL enforce the configured minimum critical-load service quantity or fraction in every applicable interval.
4. THE Optimizer SHALL constrain State_of_Charge in kilowatt-hours between declared usable-capacity and reserve bounds and constrain charge and discharge power in kilowatts after conversion to interval energy using interval duration in hours.
5. THE Optimizer SHALL update State_of_Charge using separately configured charge and discharge efficiencies and shall report storage conversion losses in kilowatt-hours.
6. THE Optimizer SHALL start from the configured initial State_of_Charge and enforce either a configured terminal State_of_Charge constraint or a configured terminal energy value in the Optimization_Objective.
7. WHEN reserve energy is configured, THE Optimizer SHALL identify whether reserve is unavailable for normal dispatch, available during a declared outage, or valued through a configured terminal constraint.
8. WHEN the Optimizer returns a solution, THE Optimizer SHALL report solution status, runtime, relative or absolute optimality gap, best bound when available, Optimization_Objective value, and independent constraint-check outcome.
9. IF optimization reaches the runtime limit with a feasible incumbent, THEN THE Optimizer SHALL return the incumbent as feasible-at-timeout with the reported gap and bound.
10. IF optimization reaches the runtime limit without a feasible incumbent, THEN THE Optimizer SHALL return timeout-without-solution and no Optimization_Objective value or schedule.
11. IF optimization encounters numerical failure, THEN THE Optimizer SHALL return numerical-failure diagnostics and no Optimization_Objective value or schedule.
12. IF the Optimizer proves the hard constraints infeasible, THEN THE Optimizer SHALL return proven-infeasible status with identified conflicting constraints and no Optimization_Objective value or schedule.
13. IF optimization is requested without a completed simulation, THEN THE Optimizer SHALL reject the request and preserve existing results.

### Requirement 4: Compare First-Release Alternatives

**User Story:** As an energy consultant, I want three transparent alternatives, so that I can deliver a reviewable client screening recommendation.

#### Acceptance Criteria

1. THE First_Commercial_Release SHALL compare exactly three operationally documented alternatives: existing-operation baseline, documented rule-based dispatch, and cost-minimized optimized dispatch.
2. WHEN the Recommendation_Service compares alternatives, THE Recommendation_Service SHALL use identical Authorized_Customer_Data, Simulation_Horizon, tariff configuration, outage assumptions, and asset assumptions for all three alternatives.
3. THE Recommendation_Service SHALL report absolute Operating_Cost, peak imported demand, critical Unserved_Load energy, Interruption_Duration, Clean_Energy_Share, Purchased_Electricity_Emissions_Estimate, and assumptions and exclusions for each alternative.
4. IF total served load is zero, THEN THE Recommendation_Service SHALL report Clean_Energy_Share as not applicable.
5. IF total critical demand is zero, THEN THE Recommendation_Service SHALL report critical-service fractions and outage critical-service metrics as not applicable.
6. WHEN a buyer supplies mandatory constraints and a deterministic decision rule, THE Recommendation_Service SHALL exclude alternatives that fail a mandatory constraint and recommend the remaining alternative selected by the rule.
7. IF buyer mandatory constraints or a deterministic decision rule are absent, THEN THE Recommendation_Service SHALL present the comparison without a recommendation.
8. THE First_Commercial_Release SHALL exclude composite weighted ranking, min-max scoring, and additional strategy-ranking interfaces.
9. WHERE composite ranking or additional strategies are shown in the Hackathon_Demo, THE OmniGridX SHALL label the functionality as Demo or Future_Capability and exclude the functionality from first-release claims.

### Requirement 5: Calculate Sample Screening Cost and Defer Tariff Reconciliation

**User Story:** As a judge, I want a transparent sample cost comparison, so that I can compare the three bundled alternatives without mistaking the result for a verified tariff calculation.

#### Acceptance Criteria

1. WHEN Fast_Judge_MVP calculates Operating_Cost, THE Recommendation_Service SHALL apply the dated Sample_Screening_Rate_Configuration to gross imports and gross exports for the bundled scenario.
2. WHEN Fast_Judge_MVP reports cost or savings, THE Recommendation_Service SHALL label every value Screening_Estimate and display the Sample_Screening_Rate_Configuration version, currency, units, effective period, source or assumption label, and exclusions.
3. THE Fast_Judge_MVP SHALL state that the Sample_Screening_Rate_Configuration is not a verified tariff, historical bill reconciliation, account-applicability determination, or future-savings validation.
4. WHERE historical tariff verification is enabled as a Post_MVP_Capability, THE First_Commercial_Release SHALL support at most one Verified_Tariff_Configuration for one independently verified account before broader support is claimed.
5. WHERE historical tariff verification is enabled as a Post_MVP_Capability, IF independent verification of a tariff and account applicability is incomplete, THEN THE Recommendation_Service SHALL label every associated cost and savings result Screening_Estimate and identify the missing verification.
6. WHERE historical reconciliation is enabled as a Post_MVP_Capability, WHEN historical reconciliation is run, THE Recommendation_Service SHALL use held-out billing periods not used to configure the tariff calculation.
7. WHERE historical reconciliation is enabled as a Post_MVP_Capability, WHEN historical reconciliation is run, THE Recommendation_Service SHALL compare every supported modeled line item and modeled bill total with corresponding actual-bill values using pilot-agreed configured absolute or percentage tolerances.
8. WHERE historical reconciliation is enabled as a Post_MVP_Capability, IF any supported line item or bill total exceeds the configured tolerance, THEN THE Recommendation_Service SHALL label the calculation Screening_Estimate and report each failed item.
9. WHERE historical reconciliation is enabled as a Post_MVP_Capability, WHEN every supported line item and total for every held-out billing period meets configured tolerances, THE Recommendation_Service SHALL label the historical calculation Historically_Reconciled_Tariff_Calculation and report account identifier, held-out periods, tariff version and effective period, modeled line items, exclusions, tolerance, and error for each line item and total.
10. WHERE historical reconciliation is enabled as a Post_MVP_Capability, THE Recommendation_Service SHALL exclude prior balances, late fees, account credits, payments, and nonmodeled items from reconciliation and list each exclusion.
11. WHERE verified tariff calculation is enabled as a Post_MVP_Capability, WHEN a tariff changes within a billing or scenario period, THE Recommendation_Service SHALL apply each verified tariff version only to the effective dates and report the allocation method.
12. WHERE verified tariff calculation is enabled as a Post_MVP_Capability, WHILE tariff demand measurement is finer than Customer_Interval_Data, THE Recommendation_Service SHALL label affected demand charges Screening_Estimate and report that the billing determinant cannot be reconstructed.
13. WHERE verified tariff calculation is enabled as a Post_MVP_Capability, THE Recommendation_Service SHALL label every future scenario cost and savings result as a modeled Screening_Estimate even when the historical calculation has Historically_Reconciled_Tariff_Calculation status.
14. WHERE verified tariff calculation is enabled as a Post_MVP_Capability, THE Recommendation_Service SHALL state that Historically_Reconciled_Tariff_Calculation status validates neither future savings nor tariff applicability to another account or period.

### Requirement 6: Screen Outage Service

**User Story:** As an energy consultant, I want deterministic outage-service screening, so that I can communicate critical-load outcomes under explicit assumptions.

#### Acceptance Criteria

1. WHEN a Scenario evaluates outage service, THE Simulation_Engine SHALL require outage start, outage duration, interval grid availability, critical-load profile, starting State_of_Charge, equipment availability, reserve behavior, and interval import bounds.
2. WHILE the Utility_Grid is unavailable, THE Simulation_Engine SHALL set the permitted grid import and export bounds to zero.
3. WHEN outage service is evaluated, THE Simulation_Engine SHALL report critical Unserved_Load in kilowatt-hours and Interruption_Duration in hours.
4. WHEN outage service is evaluated, THE Simulation_Engine SHALL label the result Outage_Service_Screening and state that the result is deterministic rather than probabilistic reliability analysis.
5. IF no outage is declared and grid import is unbounded for every interval, THEN THE Simulation_Engine SHALL report outage service as not evaluated.
6. IF an outage-service input is missing, THEN THE Simulation_Engine SHALL reject outage-service evaluation and identify each missing input.

### Requirement 7: Defer Aggregate Territory Forecasting

**User Story:** As a utility planner, I want territory-level demand analysis labeled by evidence and horizon, so that I do not confuse aggregate thresholds with local grid feasibility.

#### Acceptance Criteria

1. WHERE an Operational_ML_Forecast is enabled as a Future_Capability, THE OmniGridX SHALL declare the forecast issue time, maximum validated horizon, geography, interval, target variable, training period, and input versions.
2. WHEN an Operational_ML_Forecast is evaluated, THE OmniGridX SHALL use a time-based holdout and only weather and other inputs available at each simulated issue time.
3. WHEN an Operational_ML_Forecast is evaluated, THE OmniGridX SHALL compare forecast error by horizon with a declared simple baseline using the same holdout observations.
4. WHEN an Operational_ML_Forecast reports a quantile or prediction interval, THE OmniGridX SHALL declare nominal coverage and report observed holdout coverage by horizon.
5. IF a requested horizon exceeds the validated Operational_ML_Forecast horizon, THEN THE OmniGridX SHALL label the result Long_Range_Scenario_Projection and report the growth and weather assumptions.
6. WHEN aggregate demand is compared with a territory threshold, THE OmniGridX SHALL label the result Aggregate_Demand_Threshold_Comparison and report threshold source, units, geography, effective period, and projected exceedance.
7. THE Aggregate_Demand_Threshold_Comparison SHALL state that the comparison does not establish feeder capacity, substation capacity, service-connection feasibility, or interconnection feasibility.
8. WHERE projected Data_Center_Load is included, THE OmniGridX SHALL identify the load as a declared scenario assumption and prevent double counting with baseline growth.
9. WHERE the deployment stage is the Hackathon_Demo or MVP, THE OmniGridX SHALL accept versioned source snapshots and identify live ingestion and forecast operations as a production milestone.
10. IF historical demand data is absent for the requested geography, THEN THE OmniGridX SHALL reject the Operational_ML_Forecast and identify the missing Dataset.
11. THE First_Commercial_Release SHALL exclude Operational_ML_Forecast, Long_Range_Scenario_Projection, and Aggregate_Demand_Threshold_Comparison unless separate commercial validation is completed.

### Requirement 8: Report Purchased-Electricity Emissions

**User Story:** As an energy consultant, I want emissions calculations with explicit scope and factors, so that clients can interpret the estimate correctly.

#### Acceptance Criteria

1. WHEN a Scenario is evaluated, THE OmniGridX SHALL compute Purchased_Electricity_Emissions_Estimate as gross nonnegative imported electricity multiplied by the applicable declared Emissions_Factor for every interval.
2. THE OmniGridX SHALL report gross exports separately and exclude exports from reduction or cancellation of Purchased_Electricity_Emissions_Estimate.
3. WHEN Purchased_Electricity_Emissions_Estimate is reported, THE OmniGridX SHALL report Emissions_Factor value, units, geography, data year, version, included gases, intended purpose, source, and average-or-marginal classification.
4. IF an avoided-emissions estimate is reported, THEN THE OmniGridX SHALL report the estimate separately with the counterfactual baseline, method, temporal resolution, and limitations.
5. WHERE on-site fuel consumption and applicable fuel factors are modeled, THE OmniGridX SHALL report on-site fuel emissions separately and report combined operational emissions.
6. IF on-site fuel emissions are omitted, THEN THE OmniGridX SHALL name the grid-only result Purchased_Electricity_Emissions_Estimate and list on-site fuel emissions as excluded.
7. WHEN Battery_Storage charges from the Utility_Grid, THE OmniGridX SHALL attribute imported electricity emissions at charging time and avoid assigning negative emissions to discharge.

### Requirement 9: Defer Policy Intelligence

**User Story:** As an energy consultant, I want traceable policy context, so that informational content is not mistaken for legal applicability or generated policy values.

#### Acceptance Criteria

1. WHEN a Policy_Record is stored, THE OmniGridX SHALL record issuer, canonical source, legal-or-advisory status, publication date, effective period, jurisdiction, customer and asset applicability, last review date, supersession status, named owner, review status, and informational-or-calculation use.
2. WHEN policy context is attached to a result, THE OmniGridX SHALL pin the Policy_Snapshot name, version, date, and Policy_Record identifiers to that result.
3. WHEN a historical result is reopened, THE OmniGridX SHALL retain and display the originally pinned Policy_Snapshot rather than substituting a newer snapshot.
4. WHEN applicability is assessed, THE OmniGridX SHALL report exactly one status for each Policy_Record: applicable, inapplicable, unknown, or not-evaluated.
5. IF evidence is insufficient to determine applicability, THEN THE OmniGridX SHALL report unknown or not-evaluated and identify the missing evidence.
6. WHEN a Policy_Record affects a calculation, THE OmniGridX SHALL require named-owner review approval and review date for the applicable snapshot version.
7. THE OmniGridX SHALL source displayed and calculated policy values only from reviewed Policy_Records and exclude language-model-generated or language-model-paraphrased policy figures.
8. THE OmniGridX SHALL label policy presentation as informational and not legal advice.
9. THE First_Commercial_Release SHALL limit policy content to records required by the supported screening calculation and treat broad policy intelligence as a Future_Capability.

### Requirement 10: Retain the Massachusetts Reference and Defer Multi-State Activation

**User Story:** As a deployment operator, I want to activate a State_Data_Pack without changing core calculations, so that OmniGridX can expand beyond Massachusetts consistently.

#### Acceptance Criteria

1. THE OmniGridX SHALL provide the Massachusetts_Data_Pack as the reference implementation for State_Data_Pack structure, validation, and activation.
2. THE State_Data_Pack SHALL provide an official utility-territory map, an approved demand or market source or a documented absence, weather and climate sources, an Emissions_Factor, tariff and policy sources, a local time zone and billing calendar, and provenance and access terms for every source.
3. THE OmniGridX SHALL resolve every state-specific simulation, optimization, and recommendation value through the active State_Data_Pack rather than embedding state-specific constants in core simulation, optimization, or recommendation code.
4. WHEN a State_Data_Pack is activated, THE OmniGridX SHALL run automated validation of schema, units, time zone, geographic coverage, and source access before making the State_Data_Pack available for analysis.
5. IF a State_Data_Pack lacks a required capability, THEN THE OmniGridX SHALL report the capability as unsupported instead of applying a value from the Massachusetts_Data_Pack.
6. WHEN OmniGridX produces a result, THE OmniGridX SHALL identify the active State_Data_Pack name and version and every Source_Record used by the result.
7. WHEN state-specific tariff or policy information is approved for customer-facing use, THE OmniGridX SHALL record the named reviewer and review date before producing a customer-facing result that uses the information.
8. WHEN a State_Data_Pack is added or changed, THE OmniGridX SHALL run the same canonical scenario against the Massachusetts_Data_Pack and the changed State_Data_Pack and verify unit and conservation invariants while permitting differences caused by rates, emissions factors, and policies.
9. WHERE the deployment stage is the MVP, THE OmniGridX SHALL accept versioned source snapshots in place of live data adapters and identify live data adapters as a production milestone.
10. IF State_Data_Pack validation fails or a required value, Source_Record, geography mapping, tariff applicability rule, unit conversion, or policy review is missing, THEN THE OmniGridX SHALL keep the State_Data_Pack inactive and identify every failed check.
11. IF the active State_Data_Pack cannot supply a capability required by a request, THEN THE OmniGridX SHALL reject that capability for the request without falling back to the Massachusetts_Data_Pack or another State_Data_Pack.

### Requirement 11: Enforce Fast Judge and Release Capability Boundaries

**User Story:** As a judge or buyer, I want release claims tied to implemented scope, so that demonstration breadth is not represented as commercial evidence or forecasting.

#### Acceptance Criteria

1. THE Fast_Judge_MVP SHALL accept only bundled non-customer sample inputs and produce one deterministic comparison of exactly three alternatives.
2. THE Fast_Judge_MVP SHALL include independent constraint-check status, Screening_Estimate cost, deterministic Outage_Service_Screening, Purchased_Electricity_Emissions_Estimate, and Clean_Energy_Share in the comparison report.
3. THE Fast_Judge_MVP SHALL exclude ML, weather, and demand forecasting from public routes, runtime dependencies, reports, and submission claims.
4. WHEN the Fast_Judge_MVP describes cost-minimized optimization as grid intelligence, THE OmniGridX SHALL identify the capability as constrained optimization and not AI forecasting.
5. THE First_Commercial_Release SHALL limit the primary workflow to repeated Massachusetts commercial-site solar-and-storage screening from Authorized_Customer_Data and bills for the Buyer_Hypothesis.
6. WHERE a Hackathon_Demo includes utility forecasting, broad policy intelligence, or Data_Center_Load examples as a Post_MVP_Capability, THE OmniGridX SHALL label each capability Future_Capability and exclude each capability from Fast_Judge_MVP routes and claims.
7. THE First_Commercial_Release SHALL exclude bespoke Data_Center_Load thermal modeling.
8. WHERE a future demonstration includes a Data_Center_Load, THE OmniGridX SHALL use a declared sample load profile and identify the profile as an assumption rather than measured facility demand.
9. IF a capability lacks its own paid validation and required customer data, THEN THE OmniGridX SHALL exclude the capability from first-commercial-release claims.

### Requirement 12: Defer Commercial-Demand Evidence Operations

**User Story:** As a founder or investor, I want auditable commercial gates, so that buyer demand and repeatability claims rely on paid evidence.

#### Acceptance Criteria

1. THE Commercial_Validation_Record SHALL identify each prospective buyer's role, budget ownership or influence, current workflow, annual project frequency, analyst hours, reviewer hours, current spend, urgency, and accepted deliverable definition.
2. BEFORE OmniGridX claims initial paid validation, THE Commercial_Validation_Record SHALL contain two independent paid pilots or orders from separate buyers in the Buyer_Hypothesis.
3. WHEN a paid pilot or order is recorded, THE Commercial_Validation_Record SHALL contain buyer identity, amount, scope, order evidence, and payment evidence.
4. BEFORE OmniGridX claims repeat demand, THE Commercial_Validation_Record SHALL contain one additional paid project from each of the two independently validated buyers.
5. WHEN a paid project is delivered, THE Commercial_Validation_Record SHALL measure delivery elapsed time, rework or defects, buyer acceptance, founder hours, third-party cost, gross margin, and delivered report type.
6. WHEN commercial validation begins, THE Commercial_Validation_Record SHALL identify the proposed gates as future decision gates rather than evidence already obtained.
7. IF a target buyer declines payment, declines required data access, rejects the agreed deliverable, declines a repeat paid project, or requires bespoke labor that makes gross margin uneconomic under the recorded target, THEN THE Commercial_Validation_Record SHALL record a stop-or-narrow decision and the triggering evidence.
8. THE OmniGridX SHALL retain the statement "Unvalidated: no paid pilot, signed order, repeat purchase, customer data commitment, or measured workflow improvement has been supplied." until supplied evidence disproves every applicable clause.
9. THE Commercial_Validation_Record SHALL distinguish product-generated delivery effort from founder services and third-party work when calculating gross margin.

### Requirement 13: Protect the Public Sample Demo and Defer Customer-Data Operations

**User Story:** As a customer data owner, I want enforceable access and lifecycle controls, so that interval data and bills are protected.

#### Acceptance Criteria

1. WHERE OmniGridX operates in unauthenticated local Hackathon_Demo mode, THE OmniGridX SHALL accept bundled sample data only and bind only to a loopback network interface.
2. BEFORE OmniGridX accepts real customer data, THE Security_Baseline SHALL require recorded customer authorization and data-use terms.
3. BEFORE OmniGridX accepts real customer data or provides a publicly accessible customer-data operation, THE Security_Baseline SHALL require authenticated identities and role-based authorization for every customer-data operation.
4. BEFORE OmniGridX accepts real customer data, THE Security_Baseline SHALL require encrypted transfer and encrypted storage using organization-approved configurations.
5. BEFORE OmniGridX accepts real customer data or provides a publicly accessible customer-data operation, THE Security_Baseline SHALL require managed secrets that are excluded from source code, client output, and logs.
6. BEFORE OmniGridX accepts data from multiple customers, THE Security_Baseline SHALL require tested tenant isolation across storage, processing, logs, exports, and backups.
7. WHEN customer data is accessed, changed, exported, or deleted, THE Security_Baseline SHALL record an audit event containing actor, action, customer scope, timestamp, and outcome.
8. BEFORE OmniGridX accepts real customer data, THE Security_Baseline SHALL define and enforce retention and deletion periods for source data, derived data, logs, and backups.
9. BEFORE OmniGridX accepts real customer data, THE Security_Baseline SHALL define backup scope, restoration testing, access restrictions, and deletion propagation.
10. BEFORE OmniGridX accepts real customer data or provides a publicly accessible customer-data operation, THE Security_Baseline SHALL assign a named incident owner and document detection, containment, notification, recovery, and post-incident responsibilities.
11. IF the Security_Baseline is incomplete for a customer-data, private-pilot, or production operation, THEN THE OmniGridX SHALL reject the operation and keep customer-data paths unavailable.
12. WHERE OmniGridX operates in Public_Judge_Demo_Mode, THE OmniGridX SHALL serve only bundled non-customer samples and disable uploads, arbitrary source registration, remote adapters, customer-data operations, commercial-validation mutation, and every real-data path.
13. WHEN OmniGridX starts in Public_Judge_Demo_Mode, THE OmniGridX SHALL reject startup if a secret is exposed to the application response surface or any disabled operation or real-data path is enabled.

### Requirement 14: Deliver a Compliant Hackachusetts Submission

**User Story:** As a Hackachusetts judge, I want a complete, attributable, and reproducible submission package, so that I can evaluate OmniGridX through an unrestricted sample-only path and verify the team's use of Kiro.

#### Acceptance Criteria

1. THE Submission_Metadata SHALL declare the Climate Tech & Clean Energy track and contain a project feature and function description.
2. THE Judge_Delivery_Package SHALL use a public GitHub repository containing all project source, assets, setup instructions, run instructions, test instructions, Third_Party_Notices, demo assets, and tracked root `.kiro/specs/omnigridx`, `.kiro/steering`, and `.kiro/hooks` content.
3. WHEN the Submission_Validator inspects repository ignore and tracked-file state, THE Submission_Validator SHALL confirm that neither `.kiro` nor any `.kiro` subfolder is ignored and that the required root `.kiro` content is tracked by Git.
4. THE Judge_Delivery_Package SHALL provide a pinned local setup path, one command that runs the bundled sample-only demonstration, and one command that runs the automated tests from a fresh clone.
5. WHEN a judge uses the local test path, THE OmniGridX SHALL provide unrestricted access without login, real customer data, customer-data upload, enabled remote adapters, or public network binding.
6. THE Submission_Metadata SHALL provide a public no-login HTTPS URL for Public_Judge_Demo_Mode while preserving the customer-data Security_Baseline for every private-pilot and production path.
7. THE Submission_Writeup SHALL accurately identify the Kiro surfaces used, spec-driven workflow, implemented agent hooks and measured workflow effect, steering documents, MCP use or non-use, property-based tests and mapped requirements, Kiro powers, and third-party tools or integrations without claiming unused tools.
8. THE Submission_Writeup SHALL describe OmniGridX potential value, accessibility and adoption path, original contribution, intentional product design, and useful public data sources using evidence present in the Judge_Delivery_Package.
9. THE Third_Party_Notices SHALL identify every included third-party and open-source component and asset with source, owner or publisher, applicable license or permission, required attribution, and intended use.
10. WHEN the Submission_Validator inspects tracked submission artifacts, THE Submission_Validator SHALL reject known secret patterns, real-customer-data fixtures, undeclared executable artifacts, and third-party components or assets missing from Third_Party_Notices.
11. WHEN submission artifacts are finalized, THE Submission_Validator SHALL confirm that Submission_Metadata contains the public repository URL, project description, judge test path, demonstration-video URL, team list, authorized representative, Kiro-use evidence references, Third_Party_Notices reference, and Final_Submission_Commit.
12. WHEN the Submission_Validator inspects team metadata, THE Submission_Validator SHALL accept one to four unique team members and exactly one authorized representative who is included in the team list.
13. WHEN the Submission_Validator inspects demonstration-video metadata, THE Submission_Validator SHALL require a public HTTPS URL on the configured approved-host list and a declared duration greater than zero and less than 180 seconds.
14. WHEN a Final_Submission_Commit is recorded, THE Submission_Validator SHALL confirm that the checked-out commit equals the recorded identifier and that the required submission files are unchanged relative to that commit.
15. WHEN Public_Judge_Demo_Mode is deployed, THE Judge_Delivery_Package SHALL provide a health check that reports readiness only after bundled sample initialization and startup security checks succeed.
16. WHEN a judge opens the Public_Judge_Demo_Mode URL, THE OmniGridX SHALL provide a deterministic bundled-sample screening flow and report without accepting user-supplied data.
17. WHERE Public_Judge_Demo_Mode uses a free hosting tier, THE Judge_Delivery_Package SHALL disclose expected cold-start delay, ephemeral-storage and no-persistence behavior, free-tier limit volatility, and the `make demo` local fallback.

#### Manual Submission Checklist

The following obligations require human review or action and are not represented as automatable coding tasks:

- [ ] Register no more than four team members and identify every member in Submission_Metadata.
- [ ] Identify the authorized team representative in Submission_Metadata and confirm authorization to submit for the team.
- [ ] Confirm that the project is original or owned by the team and that licenses, intellectual property, privacy obligations, and third-party permissions are satisfied.
- [ ] Record and manually review a demonstration video shorter than 3 minutes that shows OmniGridX functioning on the device or platform where built and contains no unlicensed third-party marks, music, or copyrighted material.
- [ ] Upload the video to an approved public video host, verify public accessibility, and enter the working link in Submission_Metadata and the submission form.
- [ ] Enter the Climate Tech & Clean Energy track, project feature and function description, public GitHub URL, judge test path, team data, representative, Kiro write-up, and required links in the official submission form.
- [ ] Record the Final_Submission_Commit at submission time and make no post-deadline change to submitted materials unless Hackachusetts organizers permit the change.

### Requirement 15: Provide the Public-Data Business Dashboard

**User Story:** As a Massachusetts business user, I want a navigable public-data dashboard, so that I can review energy context and planning results without supplying customer data.

#### Acceptance Criteria

1. WHERE Public_Business_Mode is active, THE Public_Data_Business_Dashboard SHALL provide Overview, Demand & Supply, Storage & Dispatch, Policy & Regulation, and Maintenance Planning pages.
2. WHEN a user opens any Public_Data_Business_Dashboard page, THE Public_Data_Business_Dashboard SHALL display navigation links to all five pages and identify the current page.
3. WHEN a user operates dashboard navigation by keyboard, THE Public_Data_Business_Dashboard SHALL expose a visible focus indicator and an accessible name for every interactive control.
4. WHEN the Public_Data_Business_Dashboard presents a graph, status, or comparison, THE Public_Data_Business_Dashboard SHALL provide the same material values and status in text or tabular form.
5. THE Public_Data_Business_Dashboard SHALL accept only approved public federal, Massachusetts, and ISO-NE data and derived results from those data.
6. THE Public_Data_Business_Dashboard SHALL provide no customer upload, arbitrary URL, arbitrary source registration, customer-data, private-tenant, or mutable commercial-validation operation.
7. WHEN the Public_Data_Business_Dashboard displays a Dataset-derived value, THE Public_Data_Business_Dashboard SHALL display the publisher, canonical source link, Dataset version or as-of date, retrieval time, geography, units, interval or cadence, and freshness status.
8. IF required page data is invalid, missing, or stale beyond the configured Freshness_Threshold, THEN THE Public_Data_Business_Dashboard SHALL display the affected section as unavailable and identify each blocking Dataset and reason.
9. THE Public_Data_Business_Dashboard SHALL label outputs as public-data planning context that does not establish customer-specific load, tariff applicability, future savings, probabilistic reliability, feeder capacity, service-connection feasibility, or interconnection feasibility.

### Requirement 16: Present Current, Traceable Policy Information

**User Story:** As a Massachusetts business user, I want current policy records from official sources, so that I can identify potentially relevant requirements without mistaking the dashboard for legal advice.

#### Acceptance Criteria

1. WHEN Public_Business_Mode stores a Policy_Record, THE OmniGridX SHALL accept the Policy_Record only from an official federal or Massachusetts canonical source.
2. WHEN Public_Business_Mode stores a Policy_Record, THE OmniGridX SHALL record issuer, title, canonical source link, publication date, effective period, retrieval time, last review date, jurisdiction, customer and asset applicability, supersession status, named reviewer, review status, and informational-or-calculation use.
3. WHEN Public_Business_Mode publishes policy information, THE OmniGridX SHALL pin the immutable Policy_Snapshot name, version, snapshot date, and Policy_Record identifiers to the dashboard result.
4. WHEN a Policy_Snapshot is evaluated for freshness, THE OmniGridX SHALL compare retrieval time and last review date with configured Freshness_Thresholds and report current or stale with the threshold dates.
5. IF a Policy_Record is superseded, THEN THE OmniGridX SHALL display superseded status and the succeeding Policy_Record canonical source link when the official source identifies a successor.
6. WHEN policy applicability is displayed, THE OmniGridX SHALL report exactly one status for each Policy_Record: applicable, inapplicable, unknown, or not-evaluated.
7. IF evidence required for policy applicability is absent from approved public data, THEN THE OmniGridX SHALL report unknown or not-evaluated and identify the missing evidence.
8. IF a Policy_Record lacks a canonical source, required date, named reviewer, or review status, THEN THE OmniGridX SHALL exclude the Policy_Record from current policy results and report the failed checks.
9. THE Public_Data_Business_Dashboard SHALL reproduce reviewed policy values from Policy_Records without substituting language-model-generated or language-model-paraphrased policy values.
10. WHEN the Public_Data_Business_Dashboard displays policy information, THE Public_Data_Business_Dashboard SHALL label the information as informational and not legal advice and provide the official canonical source link.
11. WHEN a historical dashboard result is reopened, THE Public_Data_Business_Dashboard SHALL display the originally pinned Policy_Snapshot and identify whether a newer reviewed Policy_Snapshot exists.

### Requirement 17: Present Aggregate Demand and Supply Intelligence

**User Story:** As a Massachusetts business user, I want traceable aggregate demand and supply context, so that I can understand public energy conditions without inferring site or feeder capability.

#### Acceptance Criteria

1. WHEN the Demand & Supply page displays historical demand, THE Public_Data_Business_Dashboard SHALL display an aggregate time-series graph and equivalent table with Aggregate_Scope, source metadata, units, interval, coverage period, retrieval time, and freshness status.
2. WHEN a current Official_Published_Demand_Forecast is available for the selected Aggregate_Scope, THE Public_Data_Business_Dashboard SHALL display the Official_Published_Demand_Forecast rather than a generated forecast.
3. IF no current Official_Published_Demand_Forecast is available for the selected Aggregate_Scope, THEN THE Public_Data_Business_Dashboard SHALL display a Validated_Baseline_Forecast or mark forecast data unavailable.
4. WHEN an Official_Published_Demand_Forecast is displayed, THE Public_Data_Business_Dashboard SHALL report publisher, canonical source link, issue time, maximum horizon, geography, interval, target variable, input or methodology reference, published error or coverage when supplied by the publisher, and unavailable published quality fields.
5. WHEN a Validated_Baseline_Forecast is displayed, THE Public_Data_Business_Dashboard SHALL report issue time, maximum validated horizon, geography, interval, target variable, training period, input Dataset versions, method, time-based holdout period, comparator, error by horizon, and prediction-interval nominal and observed coverage when intervals are produced.
6. WHEN a Validated_Baseline_Forecast is evaluated, THE OmniGridX SHALL use time-ordered holdout observations and only input records whose publication or availability time is no later than each simulated forecast issue time.
7. IF a requested demand horizon exceeds the published or validated maximum horizon, THEN THE Public_Data_Business_Dashboard SHALL label the result Long_Range_Scenario_Projection and report each growth, weather, and supply assumption.
8. WHEN the Demand & Supply page displays Supply_Context, THE Public_Data_Business_Dashboard SHALL report geography, interval or cadence, measurement basis, source, canonical link, coverage period, retrieval time, freshness status, and limitations.
9. WHEN the Public_Data_Business_Dashboard compares demand with Supply_Context, THE Public_Data_Business_Dashboard SHALL compare values only when geography, interval, time period, and measurement basis satisfy the declared Aggregate_Scope matching rules.
10. IF demand and Supply_Context do not share a matching Aggregate_Scope, THEN THE Public_Data_Business_Dashboard SHALL omit the numeric comparison and identify every scope mismatch.
11. THE Public_Data_Business_Dashboard SHALL identify historical observations, Official_Published_Demand_Forecast values, Validated_Baseline_Forecast values, and Long_Range_Scenario_Projection values as separate series and statuses.
12. WHEN the Public_Data_Business_Dashboard displays demand or Supply_Context, THE Public_Data_Business_Dashboard SHALL state that aggregate public data does not establish customer site load, feeder capacity, service-connection feasibility, or interconnection feasibility.
13. IF a demand, forecast, or Supply_Context Dataset fails schema, provenance, geography, unit, interval, coverage, or freshness validation, THEN THE Public_Data_Business_Dashboard SHALL mark the affected series unavailable and preserve the last valid immutable Dataset version without presenting the failed version as current.

### Requirement 18: Explain Checked Storage and Dispatch Results

**User Story:** As a Massachusetts business user, I want business-facing storage and dispatch explanations, so that I can understand modeled battery behavior without duplicating or weakening the checked calculations.

#### Acceptance Criteria

1. WHEN the Storage & Dispatch page presents a scenario, THE Public_Data_Business_Dashboard SHALL use the existing independently checked Battery_Storage, State_of_Charge, and exactly-three dispatch results without recomputing dispatch or metric values in the presentation layer.
2. WHEN storage results are displayed, THE Public_Data_Business_Dashboard SHALL report usable capacity in kilowatt-hours, charge and discharge limits in kilowatts, reserve quantity and treatment, initial and terminal State_of_Charge, charge and discharge energy, conversion losses, and the source Scenario version.
3. WHEN dispatch results are displayed, THE Public_Data_Business_Dashboard SHALL present existing operation, documented rule-based dispatch, and cost-minimized optimized dispatch exactly once each.
4. WHEN peak impact is displayed, THE Public_Data_Business_Dashboard SHALL report peak imported demand for each alternative, the interval of each peak, and the arithmetic difference from existing operation using the checked report values.
5. WHEN a storage or dispatch constraint affects an interval, THE Public_Data_Business_Dashboard SHALL identify the constraint name, configured bound, unit, interval, and whether the bound is active or violated.
6. IF the independent ConstraintChecker rejects a schedule, THEN THE Public_Data_Business_Dashboard SHALL withhold metrics for the rejected schedule and display the checker status and sanitized diagnostics.
7. WHEN the Storage & Dispatch page presents cost, outage, emissions, or clean-energy values, THE Public_Data_Business_Dashboard SHALL preserve the labels, assumptions, exclusions, and limitations attached by the existing calculation core.

### Requirement 19: Plan Maintenance Windows

**User Story:** As a Massachusetts business operator, I want optimized maintenance-window planning, so that I can identify lower-impact asset-unavailability periods using declared public-data assumptions.

#### Acceptance Criteria

1. WHEN maintenance planning is requested, THE OmniGridX SHALL require the asset identifier, planning horizon, allowed start intervals, maintenance duration, declared asset availability, operating constraints, demand forecast version, Supply_Context version, objective components, and constraint-check tolerance.
2. WHEN OmniGridX creates a Maintenance_Window_Plan, THE OmniGridX SHALL select a contiguous window of the declared duration from the allowed start intervals and enforce declared asset, reserve, service, and operating constraints for every affected interval.
3. WHEN OmniGridX evaluates candidate maintenance windows, THE OmniGridX SHALL use the pinned demand forecast and Supply_Context versions without retrieving or substituting newer data during optimization.
4. WHEN OmniGridX returns a Maintenance_Window_Plan, THE OmniGridX SHALL report selected start and end, duration, affected asset, objective value and components, expected peak impact, expected unserved-load impact, binding constraints, input versions, solution status, and independent constraint-check outcome.
5. IF no candidate window satisfies every hard constraint, THEN THE OmniGridX SHALL return no recommended window and identify the conflicting constraints.
6. IF required maintenance, demand, supply, asset, or constraint input is missing, invalid, or stale, THEN THE OmniGridX SHALL reject maintenance planning and identify every blocking input.
7. THE Public_Data_Business_Dashboard SHALL label Maintenance_Window_Plan results as planning estimates and not predictive maintenance.
8. THE Public_Data_Business_Dashboard SHALL state that asset-health and failure prediction are unavailable without asset telemetry and validated failure data.
9. THE Public_Data_Business_Dashboard SHALL provide no asset-telemetry upload, asset-health score, remaining-useful-life estimate, or failure prediction in Public_Business_Mode.

### Requirement 20: Refresh Approved Public Data Without Changing Judge Mode

**User Story:** As a dashboard operator, I want bounded and traceable public-data refresh, so that business users receive current validated information without exposing arbitrary ingestion or changing the judge demo.

#### Acceptance Criteria

1. WHERE Public_Business_Mode is active, THE Data_Ingestion_Service SHALL enable only Approved_Remote_Adapters for configured official federal, Massachusetts, and ISO-NE canonical sources.
2. THE Approved_Remote_Adapter SHALL enforce configured canonical hosts, HTTPS, response-size limits, connection and read timeouts, retry limits, content types, and Dataset schemas.
3. WHEN a Refresh_Run retrieves source bytes, THE Data_Ingestion_Service SHALL create a complete Source_Record, store the Raw_Dataset unchanged by content hash, and link every normalized record to the Raw_Dataset and Source_Record.
4. WHEN a scheduled Refresh_Run begins, THE Data_Ingestion_Service SHALL record adapter, scheduled time, start time, completion time, outcome, retrieved content hash, validation result, and published Dataset version.
5. WHEN a Refresh_Run produces a valid Dataset version, THE Data_Ingestion_Service SHALL atomically make the new immutable version current only after provenance, schema, unit, geography, interval, coverage, and freshness checks pass.
6. IF a Refresh_Run fails retrieval or validation, THEN THE Data_Ingestion_Service SHALL preserve prior Dataset versions unchanged, mark the new version unavailable, and report every failed check without partially publishing records.
7. IF the latest valid Dataset version exceeds the Freshness_Threshold for a dashboard use, THEN THE Public_Data_Business_Dashboard SHALL fail closed for the affected section and report the last valid as-of date, threshold, and refresh outcome.
8. WHEN Public_Business_Mode starts, THE OmniGridX SHALL reject startup if an enabled adapter lacks an allowlisted canonical host, bounds, schema, provenance configuration, Freshness_Threshold, or scheduled refresh definition.
9. WHILE Public_Judge_Demo_Mode or demo-local mode is active, THE OmniGridX SHALL keep Approved_Remote_Adapters, scheduled refresh, dashboard routes, policy refresh, and forecasting runtime dependencies disabled.
10. WHEN Fast_Judge_MVP routes are requested after Public_Business_Mode is introduced, THE OmniGridX SHALL preserve the existing route behavior, bundled-sample inputs, deterministic fingerprints, labels, and denied-operation behavior.
11. THE Public_Business_Mode SHALL use a route and runtime dependency boundary distinct from Public_Judge_Demo_Mode and customer/private/production operations.
12. IF a request attempts an upload, arbitrary URL retrieval, arbitrary source registration, customer-data operation, predictive-maintenance operation, or non-allowlisted adapter invocation in Public_Business_Mode, THEN THE OmniGridX SHALL reject the request without retrieving or storing request-supplied data.