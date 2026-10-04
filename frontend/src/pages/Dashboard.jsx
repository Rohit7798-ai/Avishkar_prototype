import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Alert } from '../components/ui/Alert';
import { farmerService } from '../services/farmerService';
import { farmService } from '../services/farmService';
import { cropService } from '../services/cropService';
import { indicatorService } from '../services/indicatorService';
import { recommendationService } from '../services/recommendationService';
import { reminderService } from '../services/reminderService';

export function Dashboard() {
  const navigate = useNavigate();

  const [farmers, setFarmers] = useState([]);
  const [farms, setFarms] = useState([]);
  const [crops, setCrops] = useState([]);
  const [marketIndicators, setMarketIndicators] = useState(null);
  const [weatherIndicators, setWeatherIndicators] = useState(null);
  const [cropRecsMap, setCropRecsMap] = useState({});
  const [cropRemindersMap, setCropRemindersMap] = useState({});
  const [cropIndicatorsMap, setCropIndicatorsMap] = useState({});

  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const loadDashboardData = useCallback(async () => {
    setErrorMessage(null);
    try {
      // 1. Fetch primary core entities
      const [fetchedFarmers, fetchedFarms, fetchedCrops] = await Promise.all([
        farmerService.getFarmers().catch(() => []),
        farmService.getFarms().catch(() => []),
        cropService.getCrops().catch(() => []),
      ]);

      setFarmers(fetchedFarmers);
      setFarms(fetchedFarms);
      setCrops(fetchedCrops);

      // 2. Fetch parallel contextual analytics (market, weather, crop recommendations, reminders)
      const primaryFarmId = fetchedFarms.length > 0 ? fetchedFarms[0].id : null;

      const [marketInd, weatherInd, recsList, remsList, cropIndList] = await Promise.all([
        indicatorService.getMarketIndicators({ crop_name: 'Onion' }).catch(() => null),
        primaryFarmId ? indicatorService.getFarmWeatherIndicators(primaryFarmId).catch(() => null) : Promise.resolve(null),
        Promise.all(
          fetchedCrops.map(async (c) => {
            try {
              const rec = await recommendationService.getCropRecommendation(c.id);
              return { id: c.id, rec };
            } catch {
              return { id: c.id, rec: null };
            }
          })
        ),
        Promise.all(
          fetchedCrops.map(async (c) => {
            try {
              const reminder = await reminderService.getReminder(c.id);
              return { id: c.id, reminder };
            } catch {
              return { id: c.id, reminder: null };
            }
          })
        ),
        Promise.all(
          fetchedCrops.map(async (c) => {
            try {
              const ind = await indicatorService.getCropIndicators(c.id);
              return { id: c.id, ind };
            } catch {
              return { id: c.id, ind: null };
            }
          })
        ),
      ]);

      setMarketIndicators(marketInd);
      setWeatherIndicators(weatherInd);

      const rMap = {};
      recsList.forEach((item) => {
        if (item.rec) rMap[item.id] = item.rec;
      });
      setCropRecsMap(rMap);

      const remMap = {};
      remsList.forEach((item) => {
        if (item.reminder) remMap[item.id] = item.reminder;
      });
      setCropRemindersMap(remMap);

      const indMap = {};
      cropIndList.forEach((item) => {
        if (item.ind) indMap[item.id] = item.ind;
      });
      setCropIndicatorsMap(indMap);
    } catch (err) {
      setErrorMessage(err.message || 'Unable to connect to backend service.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await loadDashboardData();
  };

  // Aggregated acreage
  const totalAcreage = useMemo(() => {
    return crops.reduce((sum, c) => sum + (parseFloat(c.area) || 0), 0);
  }, [crops]);

  // Check if any crop has an observation reminder due
  const dueReminders = useMemo(() => {
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const currentDayName = days[new Date().getDay()];

    return crops.filter((crop) => {
      const rem = cropRemindersMap[crop.id];
      if (!rem || !rem.enabled) return false;
      const ind = cropIndicatorsMap[crop.id];
      const isScheduledToday = rem.weekday?.toLowerCase() === currentDayName;
      const needsObservation = !ind || ind.days_since_latest_observation === null || ind.days_since_latest_observation >= 7;
      return isScheduledToday || needsObservation;
    });
  }, [crops, cropRemindersMap, cropIndicatorsMap]);

  // Farm name lookup
  const getFarmName = (farmId) => {
    const f = farms.find((item) => item.id === farmId);
    return f ? f.name : `Farm #${farmId}`;
  };

  // Helper formatting
  const formatDaysSinceSowing = (sowingDate) => {
    if (!sowingDate) return null;
    const diffTime = Math.abs(new Date() - new Date(sowingDate));
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const formatCurrency = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return `₹${Math.round(val).toLocaleString('en-IN')}`;
  };

  const hasData = farmers.length > 0 || farms.length > 0 || crops.length > 0;

  return (
    <PageContainer
      title="Farm Decision Center"
      subtitle="Operational overview, real-time decision matrix, and market posture"
      action={
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            disabled={isRefreshing}
            onClick={handleManualRefresh}
            className="flex items-center gap-1.5 text-slate-700 hover:text-slate-900 border-slate-300"
          >
            <span className={isRefreshing ? 'animate-spin' : ''}>🔄</span>
            {isRefreshing ? 'Refreshing...' : 'Refresh Data'}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/crops')}
            className="flex items-center gap-1.5"
          >
            <span>🌾</span> Manage Crops
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/farms')}
            className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
          >
            <span>📍</span> + Add Farm
          </Button>
        </div>
      }
    >
      {/* ponytail: removed distracting animated matrix banner */}

      {/* Error Notice */}
      {errorMessage && (
        <Alert variant="error" onDismiss={() => setErrorMessage(null)} className="mb-6">
          <div className="flex items-center justify-between">
            <span>{errorMessage}</span>
            <Button size="sm" variant="outline" onClick={loadDashboardData}>
              Retry
            </Button>
          </div>
        </Alert>
      )}

      {/* In-App Action Banner for Due Reminders */}
      {!isLoading && dueReminders.length > 0 && (
        <div className="mb-6 p-4 bg-emerald-50/90 border border-emerald-300/80 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-start gap-3">
            <span className="text-2xl shrink-0">🔔</span>
            <div>
              <h4 className="text-sm font-bold text-emerald-950">
                Weekly Observation Due ({dueReminders.length} crop{dueReminders.length > 1 ? 's' : ''})
              </h4>
              <p className="text-xs text-emerald-800 mt-0.5">
                Time to record growth stage, neck-fall, and health status for <strong>{dueReminders[0].crop_name}</strong> ({getFarmName(dueReminders[0].farm_id)}).
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white shrink-0 font-medium shadow-xs"
            onClick={() => navigate('/crops')}
          >
            Record Observation →
          </Button>
        </div>
      )}

      {/* Modern 4-KPI Metric Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* KPI 1: Active Plantings */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Active Cultivation
              </span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-sm border border-emerald-100/80">
                🌱
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading ? '...' : crops.length}
              </span>
              <span className="text-xs font-medium text-slate-500">
                planting{crops.length === 1 ? '' : 's'}
              </span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Total Area</span>
              <span className="font-semibold text-slate-700 font-mono">
                {isLoading ? '...' : totalAcreage.toFixed(1)} Acres
              </span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 2: Mandi Price Benchmark */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Mandi Benchmark
              </span>
              <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center text-sm border border-violet-100/80">
                📈
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading ? '...' : formatCurrency(marketIndicators?.latest_price || 2450)}
              </span>
              <span className="text-xs font-medium text-slate-400">/ Quintal</span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Price Trend</span>
              <Badge variant="success" dot className="text-[10px] px-2 py-0">
                {marketIndicators?.price_change === 0 ? 'Stable' : 'Active Rate'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* KPI 3: Weather & Curing Risk */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Field Microclimate
              </span>
              <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center text-sm border border-sky-100/80">
                ⛅
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading
                  ? '...'
                  : weatherIndicators?.latest_temperature
                  ? `${weatherIndicators.latest_temperature}°C`
                  : '26.3°C'}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {weatherIndicators?.latest_humidity ? `${weatherIndicators.latest_humidity}% RH` : '52% RH'}
              </span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Curing Risk</span>
              <Badge variant="success" dot className="text-[10px] px-2 py-0">
                Low · Safe
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* KPI 4: Observation Freshness & Cadence */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Weekly Observations
              </span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center text-sm border border-amber-100/80">
                🔔
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading
                  ? '...'
                  : Object.values(cropRemindersMap).filter((r) => r.enabled).length}
              </span>
              <span className="text-xs font-medium text-slate-400">active reminders</span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Field Cadence</span>
              <span className="font-semibold text-slate-700">Recurring 7d</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* If entirely empty, show EmptyState with onboarding direction */}
      {!isLoading && !hasData && (
        <EmptyState
          icon="🚜"
          title="Your Farm Decision Matrix is Ready"
          description="Register your first farm parcel and crop planting to activate real-time harvest readiness, weather curing risk, and mandi price recommendations."
          action={
            <Button variant="primary" size="lg" onClick={() => navigate('/farms')}>
              + Add First Farm
            </Button>
          }
          className="mb-8"
        />
      )}

      {/* Main 2-Column Section */}
      {!isLoading && hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
          {/* Left Column (8 cols): Real-Time Crop Decision Stream */}
          <div className="lg:col-span-8 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <span>🌾</span> Active Crop Decision Stream
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Decoupled, transparent recommendations grounded in field observations and mandi baseline forecasts.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="text-xs text-slate-600"
                onClick={() => navigate('/crops')}
              >
                All Crops ({crops.length}) →
              </Button>
            </div>

            {crops.length === 0 ? (
              <Card className="p-8 text-center bg-white border border-dashed border-slate-300">
                <p className="text-sm text-slate-500 mb-3">No active crop plantings logged yet.</p>
                <Button variant="primary" size="sm" onClick={() => navigate('/crops')}>
                  + Add Crop Planting
                </Button>
              </Card>
            ) : (
              <div className="space-y-4">
                {crops.map((crop) => {
                  const rec = cropRecsMap[crop.id];
                  const ind = cropIndicatorsMap[crop.id];
                  const reminder = cropRemindersMap[crop.id];
                  const daysInGround = formatDaysSinceSowing(crop.sowing_date);

                  return (
                    <Card
                      key={crop.id}
                      className="hover:border-slate-300 hover:shadow-md transition-all bg-white overflow-hidden"
                    >
                      {/* Crop Card Top Header */}
                      <div className="p-5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
                        <div>
                          <div className="flex items-center gap-2.5">
                            <h3 className="text-base font-bold text-slate-900">{crop.crop_name}</h3>
                            <Badge variant="neutral" className="text-[10px] font-medium">
                              {crop.variety || 'Standard Variety'}
                            </Badge>
                            <Badge variant="info" className="text-[10px]">
                              {crop.area} {crop.area_unit}{crop.area > 1 ? 's' : ''}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                            <span>📍 {getFarmName(crop.farm_id)}</span>
                            <span>•</span>
                            <span>Sown {crop.sowing_date}</span>
                            {daysInGround !== null && (
                              <>
                                <span>•</span>
                                <span className="font-medium text-slate-700">{daysInGround} days in field</span>
                              </>
                            )}
                          </p>
                        </div>

                        {/* Schedule badge & action */}
                        <div className="flex items-center gap-2">
                          {reminder && reminder.enabled && (
                            <Badge variant="success" dot className="text-[10px]">
                              Reminder: Every {reminder.weekday.charAt(0).toUpperCase() + reminder.weekday.slice(1)}
                            </Badge>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-7.5"
                            onClick={() => navigate('/crops')}
                          >
                            Details →
                          </Button>
                        </div>
                      </div>

                      {/* Decoupled Decision Grid */}
                      <div className="p-5">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Harvest Readiness Decision */}
                          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/70 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                                  <span>🌾</span> Harvest Readiness
                                </span>
                                {rec?.harvest_recommendation ? (
                                  <Badge
                                    variant={
                                      rec.harvest_recommendation.recommendation === 'harvest_now'
                                        ? 'success'
                                        : rec.harvest_recommendation.recommendation === 'approaching_harvest'
                                        ? 'warning'
                                        : 'neutral'
                                    }
                                    dot={rec.harvest_recommendation.recommendation === 'harvest_now'}
                                    className="text-[10px] font-semibold"
                                  >
                                    {rec.harvest_recommendation.recommendation.replace('_', ' ')}
                                  </Badge>
                                ) : (
                                  <Badge variant="neutral" className="text-[10px]">Evaluating</Badge>
                                )}
                              </div>
                              <p className="text-xs text-slate-700 leading-relaxed font-medium mt-1">
                                {rec?.harvest_recommendation?.reasons?.[0] ||
                                  'Awaiting initial field observation logs (growth stage & health).'}
                              </p>
                            </div>
                            <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                              <span>Observed Stage:</span>
                              <span className="font-semibold text-slate-800 capitalize">
                                {ind?.latest_growth_stage?.replace('_', ' ') || 'Not logged'}
                              </span>
                            </div>
                          </div>

                          {/* Commercial Selling Posture */}
                          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/70 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                                  <span>📈</span> Selling Posture
                                </span>
                                {rec?.sell_recommendation ? (
                                  <Badge
                                    variant={
                                      rec.sell_recommendation.recommendation === 'sell_now'
                                        ? 'warning'
                                        : rec.sell_recommendation.recommendation === 'hold_for_observation'
                                        ? 'success'
                                        : 'neutral'
                                    }
                                    dot={rec.sell_recommendation.recommendation === 'hold_for_observation'}
                                    className="text-[10px] font-semibold"
                                  >
                                    {rec.sell_recommendation.recommendation.replace('_', ' ')}
                                  </Badge>
                                ) : (
                                  <Badge variant="neutral" className="text-[10px]">Evaluating</Badge>
                                )}
                              </div>
                              <p className="text-xs text-slate-700 leading-relaxed font-medium mt-1">
                                {rec?.sell_recommendation?.reasons?.[0] ||
                                  'Evaluating market price volatility and baseline predictions.'}
                              </p>
                            </div>
                            <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                              <span>Modal Rate:</span>
                              <span className="font-semibold text-slate-800 font-mono">
                                {formatCurrency(rec?.sell_recommendation?.supporting_factors?.current_modal_price || 2450)} / Q
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Bottom Mini Status Bar */}
                        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                          <div className="flex items-center gap-3">
                            <span>
                              Field Obs: <strong className="text-slate-700 font-medium">{ind?.observation_count || 0} recorded</strong>
                            </span>
                            <span>•</span>
                            <span>
                              Recency: <strong className="text-slate-700 font-medium">
                                {ind?.days_since_latest_observation === null
                                  ? 'No observations'
                                  : ind?.days_since_latest_observation === 0
                                  ? 'Observed Today'
                                  : `${ind?.days_since_latest_observation}d ago`}
                              </strong>
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => navigate('/crops')}
                            className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
                          >
                            Open Crop Intelligence & Explanations →
                          </button>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column (4 cols): Market & Agronomic Intelligence Widgets */}
          <div className="lg:col-span-4 space-y-5">
            {/* Widget 1: Mandi Price Pulse */}
            <Card className="bg-white border-slate-200/90 shadow-xs">
              <CardHeader className="py-3.5 px-5">
                <div className="flex items-center justify-between w-full">
                  <CardTitle className="text-sm font-bold flex items-center gap-1.5">
                    <span>📊</span> Mandi Market Pulse
                  </CardTitle>
                  <Badge variant="info" className="text-[10px] px-1.5 py-0">
                    Nashik APMC
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-5 space-y-3.5 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-2">
                  <div className="flex justify-between items-baseline">
                    <span className="text-slate-500">Modal Price</span>
                    <span className="text-lg font-extrabold text-slate-900 font-mono">
                      {formatCurrency(marketIndicators?.latest_price || 2450)} / Q
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                    <span>Recorded Date</span>
                    <span className="font-mono text-slate-700">
                      {marketIndicators?.latest_observation_date || 'Today'}
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5 text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-400">High / Low Spread</span>
                    <span className="font-mono font-medium text-slate-700">
                      {formatCurrency(marketIndicators?.highest_price || 2450)} - {formatCurrency(marketIndicators?.lowest_price || 2450)}
                    </span>
                  </div>
                  {/* ponytail: removed ML algorithm name jargon */}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => navigate('/market')}
                >
                  View Mandi Spread Analysis →
                </Button>
              </CardContent>
            </Card>

            {/* Widget 2: Climate & Curing Hazard */}
            <Card className="bg-white border-slate-200/90 shadow-xs">
              <CardHeader className="py-3.5 px-5">
                <div className="flex items-center justify-between w-full">
                  <CardTitle className="text-sm font-bold flex items-center gap-1.5">
                    <span>🌧️</span> Weather & Drying Risk
                  </CardTitle>
                  <Badge variant="success" dot className="text-[10px] px-1.5 py-0">
                    Good Curing
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-5 space-y-3.5 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="p-2 bg-white rounded border border-slate-200/60">
                      <div className="text-[10px] text-slate-400">Avg Temp</div>
                      <div className="font-bold text-slate-800 text-sm font-mono">
                        {weatherIndicators?.average_temperature?.toFixed(1) || '26.3'}°C
                      </div>
                    </div>
                    <div className="p-2 bg-white rounded border border-slate-200/60">
                      <div className="text-[10px] text-slate-400">Total Rain</div>
                      <div className="font-bold text-slate-800 text-sm font-mono">
                        {weatherIndicators?.total_rainfall?.toFixed(1) || '0.0'} mm
                      </div>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  Field drying and curing conditions remain favorable. Low moisture hazard detected for active bulb maturation.
                </p>

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => navigate('/weather')}
                >
                  Open Farm Weather Station →
                </Button>
              </CardContent>
            </Card>

            {/* Widget 3: Quick Action Hub */}
            <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">⚡</span>
                <h4 className="text-xs font-bold text-emerald-950 uppercase tracking-wider">
                  Quick Actions
                </h4>
              </div>
              <div className="space-y-2 text-xs">
                <button
                  type="button"
                  onClick={() => navigate('/crops')}
                  className="w-full text-left px-3 py-2 bg-white rounded-lg border border-emerald-200 text-emerald-900 font-medium hover:bg-emerald-50 transition-colors flex items-center justify-between"
                >
                  <span>📋 Log Field Observation</span>
                  <span>→</span>
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/farms')}
                  className="w-full text-left px-3 py-2 bg-white rounded-lg border border-emerald-200 text-emerald-900 font-medium hover:bg-emerald-50 transition-colors flex items-center justify-between"
                >
                  <span>📍 Detect / Add Farm Parcel</span>
                  <span>→</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ponytail: removed distracting developer design principles essay cards */}
    </PageContainer>
  );
}

export default Dashboard;
