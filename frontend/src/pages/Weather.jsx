import React from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

export function Weather() {
  return (
    <PageContainer
      title="Weather"
      subtitle="Field-drying safety scores, rainfall forecasts, and rot hazard analysis"
    >
      <div className="space-y-6">
        <EmptyState
          icon="⛅"
          title="Weather information will appear here."
          description="Localized 7-day meteorological forecasts and field curing safety scores will be calculated automatically based on your farm's geographic coordinates."
        />

        {/* Informational Parameter Seam */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Field Drying Index</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-500">
              Evaluates post-harvest curing conditions to prevent neck rot and bulb decay during field laying.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">7-Day Rainfall Radar</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-500">
              Monitors precipitation probability and millimeters to recommend dry harvesting windows.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Humidity & Wind</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-500">
              Tracks ambient humidity and wind speed for optimal onion curing and skin coloring.
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}

export default Weather;
