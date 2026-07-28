type ProviderTokenUsage = {
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
};

type ProviderStageTelemetry = {
  stage: string;
  requested: boolean;
  outcome: string;
  status_code: string;
  model: string | null;
  prompt_version: string;
  schema_version: string;
  latency_ms: number;
  usage: ProviderTokenUsage | null;
  estimated_cost_usd: number | null;
  cost_estimate_status: string;
};

type ProviderTelemetrySummary = {
  telemetry_version: string;
  pricing_catalog_version: string;
  pricing_currency: string;
  pricing_basis: string;
  extraction: ProviderStageTelemetry;
  coaching: ProviderStageTelemetry;
  total_provider_latency_ms: number;
  total_input_tokens: number;
  total_cached_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_estimated_cost_usd: number | null;
  cost_estimate_status: string;
};

type AnalysisWithTelemetry = {
  analysis_engine: string;
  provider_telemetry?: ProviderTelemetrySummary | null;
};

function formatCost(value: number | null): string {
  if (value === null) {
    return "Unavailable";
  }
  const digits = value < 0.01 ? 6 : 4;
  return `$${value.toFixed(digits)} estimated`;
}

function formatStage(label: string, stage: ProviderStageTelemetry): string {
  const model = stage.model ?? "No provider model";
  const usage = stage.usage
    ? `${stage.usage.input_tokens.toLocaleString()} input / ${stage.usage.output_tokens.toLocaleString()} output tokens`
    : "Token usage unavailable";
  return `${label}: ${stage.status_code} · ${model} · ${stage.latency_ms.toFixed(1)} ms · ${usage} · ${formatCost(stage.estimated_cost_usd)}`;
}

export function ProviderTelemetryPanel({
  analysis,
}: {
  analysis: AnalysisWithTelemetry;
}) {
  const telemetry = analysis.provider_telemetry;
  if (!telemetry) {
    return null;
  }

  return (
    <details>
      <summary>Operational details</summary>
      <div className="evidence-stack">
        <p>{formatStage("Semantic extraction", telemetry.extraction)}</p>
        <p>{formatStage("Personalized coaching", telemetry.coaching)}</p>
        <p>
          <strong>Total:</strong> {telemetry.total_provider_latency_ms.toFixed(1)} ms · {telemetry.total_tokens.toLocaleString()} tokens · {formatCost(telemetry.total_estimated_cost_usd)}
        </p>
        <p className="helper-text">
          Extraction prompt/schema {telemetry.extraction.prompt_version}/{telemetry.extraction.schema_version}; coaching prompt/schema {telemetry.coaching.prompt_version}/{telemetry.coaching.schema_version}; telemetry {telemetry.telemetry_version}.
        </p>
        <p className="helper-text">
          Pricing catalog {telemetry.pricing_catalog_version}: {telemetry.pricing_basis}
        </p>
      </div>
    </details>
  );
}
