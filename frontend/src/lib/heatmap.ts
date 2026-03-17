export interface HeatmapAdapter {
  identifyStep: (_step: string) => void;
  trackFeatureUsage: (_feature: string) => void;
}

const noopHeatmapAdapter: HeatmapAdapter = {
  identifyStep: () => undefined,
  trackFeatureUsage: () => undefined,
};

export function getHeatmapAdapter(): HeatmapAdapter {
  if (process.env.NEXT_PUBLIC_HEATMAP_ENABLED === "true") {
    return noopHeatmapAdapter;
  }

  return noopHeatmapAdapter;
}
