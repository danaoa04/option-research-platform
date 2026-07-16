export type MetricKind="observed"|"calculated"|"model_derived"|"fixture";export type ScenarioState="ready"|"ready_with_warnings"|"invalid"|"running"|"completed";
export interface PortfolioMetric{label:string;value:string;kind:MetricKind}
export interface PositionRow{id:string;strategy:string;symbol:string;instrument:string;expiration:string;strike:number|null;quantity:number;marketValue:number;unrealizedPnl:number;delta:number|null;gamma:number|null;theta:number|null;vega:number|null;margin:number;liquidity:"strong"|"acceptable"|"weak";quoteAge:string;assignmentRisk:string;eventRisk:string;quality:string;checksum:string}
export interface ExposureRow{group:string;delta:number;gamma:number;theta:number;vega:number;margin:number;concentration:number;kind:MetricKind}
export interface ScenarioPreset{id:string;name:string;family:string;severity:string;horizon:string;factors:string[];limitations:string[];synthetic:boolean}
export interface ScenarioDraft{portfolioId:string;presetId:string;spotShock:number;ivShock:number;timeDays:number;spreadMultiplier:number;marginShock:number;limitPolicy:string;acknowledged:boolean}
export interface MatrixCell{spot:number;volatility:number;pnl:number;returnPct:number;breaches:number;quality:string}
export interface RiskLimit{id:string;name:string;current:string;scenario:string;threshold:string;breach:string;severity:"info"|"warning"|"critical";affected:string[]}
export interface RemediationCandidate{id:string;action:string;cost:number;scenarioPnl:number;delta:number;margin:number;tailRisk:string;assignmentRisk:string;liquidity:string;complexity:string;confidence:string;warnings:string[];backendRank:number}
export interface ReplayEvent{id:string;sequence:number;at:string;type:string;severity:"info"|"warning"|"critical";symbol:string;strategy:string;branch:string;message:string;checksum:string}
export interface ReportRecord{id:string;type:string;source:string;version:number;format:"JSON"|"HTML";generatedAt:string;checksum:string;status:string;warnings:string[]}
export interface RiskFixture{metrics:PortfolioMetric[];positions:PositionRow[];exposures:ExposureRow[];scenarios:ScenarioPreset[];matrix:MatrixCell[];limits:RiskLimit[];remediation:RemediationCandidate[];events:ReplayEvent[];reports:ReportRecord[]}
