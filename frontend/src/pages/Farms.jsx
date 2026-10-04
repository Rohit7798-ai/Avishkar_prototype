import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Alert } from '../components/ui/Alert';
import { Modal } from '../components/ui/Modal';
import { farmService } from '../services/farmService';
import { farmerService } from '../services/farmerService';
import { cropService } from '../services/cropService';
import { weatherObservationService } from '../services/weatherObservationService';
import { indicatorService } from '../services/indicatorService';
import { syncService } from '../services/syncService';

export function Farms() {
  const navigate = useNavigate();

  const [farms, setFarms] = useState([]);
  const [farmers, setFarmers] = useState([]);
  const [crops, setCrops] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Weather Indicators state map (farm_id -> indicators)
  const [farmWeatherIndicatorsMap, setFarmWeatherIndicatorsMap] = useState({});

  // Search & filter
  const [searchQuery, setSearchQuery] = useState('');

  // Modal states
  const [isAddFarmOpen, setIsAddFarmOpen] = useState(false);
  const [isFarmerModalOpen, setIsFarmerModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null); // farm to delete
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Weather Observation state
  const [activeFarmForWeather, setActiveFarmForWeather] = useState(null);
  const [weatherObservations, setWeatherObservations] = useState([]);
  const [isLoadingWeather, setIsLoadingWeather] = useState(false);
  const [weatherErrorMessage, setWeatherErrorMessage] = useState(null);
  const [deleteWeatherTarget, setDeleteWeatherTarget] = useState(null);

  // Weather Sync State (Open-Meteo)
  const [syncTargetFarm, setSyncTargetFarm] = useState(null);
  const [syncCoords, setSyncCoords] = useState({ latitude: '', longitude: '', days: 1 });
  const [isSyncingWeather, setIsSyncingWeather] = useState(false);
  const [syncErrorMessage, setSyncErrorMessage] = useState(null);

  // Geolocation detection state
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);
  const [locationDetectionStatus, setLocationDetectionStatus] = useState(null); // 'success' | 'error' | null
  const [locationDetectionMessage, setLocationDetectionMessage] = useState(null);
  const [showManualLocationInput, setShowManualLocationInput] = useState(false);

  // New Farm form state
  const [farmForm, setFarmForm] = useState({
    farmer_id: '',
    name: '',
    location: '',
    area: '',
    area_unit: 'acre',
  });

  // Quick Farmer form state
  const [farmerForm, setFarmerForm] = useState({
    name: '',
    phone: '',
  });

  // Helper to get formatted current local datetime for datetime-local input
  const getCurrentLocalDatetime = () => {
    const now = new Date();
    const offset = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offset).toISOString().slice(0, 16);
  };

  // Weather form state
  const [weatherForm, setWeatherForm] = useState({
    observed_at: getCurrentLocalDatetime(),
    temperature: '',
    humidity: '',
    rainfall: '0.0',
    wind_speed: '0.0',
  });

  // Load farms, farmers, crops, and weather indicators
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [fetchedFarms, fetchedFarmers, fetchedCrops] = await Promise.all([
        farmService.getFarms(),
        farmerService.getFarmers(),
        cropService.getCrops().catch(() => []),
      ]);
      setFarms(fetchedFarms);
      setFarmers(fetchedFarmers);
      setCrops(fetchedCrops);

      // Load deterministic weather indicators for all farms
      const indicatorsList = await Promise.all(
        fetchedFarms.map(async (f) => {
          try {
            const ind = await indicatorService.getFarmWeatherIndicators(f.id);
            return { id: f.id, ind };
          } catch {
            return { id: f.id, ind: null };
          }
        })
      );
      const indMap = {};
      indicatorsList.forEach((item) => {
        if (item.ind) indMap[item.id] = item.ind;
      });
      setFarmWeatherIndicatorsMap(indMap);
    } catch (err) {
      setErrorMessage(err.message || 'Unable to load farm records. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load weather observations and indicators for a farm
  const loadWeather = useCallback(async (farmId) => {
    setIsLoadingWeather(true);
    setWeatherErrorMessage(null);
    try {
      const [data, indicators] = await Promise.all([
        weatherObservationService.getWeatherObservations(farmId),
        indicatorService.getFarmWeatherIndicators(farmId).catch(() => null),
      ]);
      setWeatherObservations(data);
      if (indicators) {
        setFarmWeatherIndicatorsMap((prev) => ({ ...prev, [farmId]: indicators }));
      }
    } catch (err) {
      setWeatherErrorMessage(err.message || 'Failed to load weather observations.');
    } finally {
      setIsLoadingWeather(false);
    }
  }, []);

  const handleOpenWeather = (farm) => {
    setActiveFarmForWeather(farm);
    setWeatherForm({
      observed_at: getCurrentLocalDatetime(),
      temperature: '',
      humidity: '',
      rainfall: '0.0',
      wind_speed: '0.0',
    });
    loadWeather(farm.id);
  };

  // Open Add Farm modal
  const handleOpenAddFarm = () => {
    setFarmForm({
      farmer_id: farmers.length > 0 ? String(farmers[0].id) : '',
      name: '',
      location: '',
      area: '',
      area_unit: 'acre',
    });
    setIsDetectingLocation(false);
    setLocationDetectionStatus(null);
    setLocationDetectionMessage(null);
    setShowManualLocationInput(false);
    setErrorMessage(null);
    setIsAddFarmOpen(true);
  };

  // Browser Geolocation Detection
  const handleDetectLocation = () => {
    if (typeof window === 'undefined' || !navigator || !navigator.geolocation) {
      setLocationDetectionStatus('error');
      setLocationDetectionMessage('Unable to detect your location. Browser geolocation not supported.');
      return;
    }

    setIsDetectingLocation(true);
    setLocationDetectionStatus(null);
    setLocationDetectionMessage(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const formatted = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;

        setFarmForm((prev) => ({
          ...prev,
          location: formatted,
        }));
        setLocationDetectionStatus('success');
        setLocationDetectionMessage('Location detected successfully');
        setIsDetectingLocation(false);
      },
      (error) => {
        setIsDetectingLocation(false);
        setLocationDetectionStatus('error');
        if (error.code === error.PERMISSION_DENIED) {
          setLocationDetectionMessage('Location permission was denied. Please allow location access and try again.');
        } else if (error.code === error.TIMEOUT) {
          setLocationDetectionMessage('Location detection timed out. Please try again.');
        } else {
          setLocationDetectionMessage('Unable to detect your location. Please try again or enter location manually.');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    );
  };

  // Submit Farm Form
  const handleCreateFarm = async (e) => {
    e.preventDefault();
    if (!farmForm.farmer_id) {
      setErrorMessage('Please select or register a farmer first.');
      return;
    }
    if (!farmForm.name.trim()) {
      setErrorMessage('Farm name is required.');
      return;
    }
    if (!farmForm.location.trim()) {
      setErrorMessage('Please click "Detect My Location" to set your farm coordinates.');
      return;
    }
    const numericArea = parseFloat(farmForm.area);
    if (isNaN(numericArea) || numericArea <= 0) {
      setErrorMessage('Farm area must be a positive number.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await farmService.createFarm({
        farmer_id: parseInt(farmForm.farmer_id, 10),
        name: farmForm.name.trim(),
        location: farmForm.location.trim(),
        area: numericArea,
        area_unit: farmForm.area_unit,
      });
      setIsAddFarmOpen(false);
      setSuccessMessage(`Farm parcel "${farmForm.name}" created successfully.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      await loadData();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create farm. Please verify inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Farmer Form
  const handleCreateFarmer = async (e) => {
    e.preventDefault();
    if (!farmerForm.name.trim()) {
      setErrorMessage('Farmer name is required.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const newFarmer = await farmerService.createFarmer({
        name: farmerForm.name.trim(),
        phone: farmerForm.phone.trim() || null,
      });
      setFarmers((prev) => [...prev, newFarmer]);
      setFarmForm((prev) => ({ ...prev, farmer_id: String(newFarmer.id) }));
      setFarmerForm({ name: '', phone: '' });
      setIsFarmerModalOpen(false);
      setSuccessMessage(`Farmer "${newFarmer.name}" registered successfully.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to register farmer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Farm
  const handleConfirmDeleteFarm = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await farmService.deleteFarm(deleteTarget.id);
      setSuccessMessage(`Farm "${deleteTarget.name}" deleted successfully.`);
      setDeleteTarget(null);
      setTimeout(() => setSuccessMessage(null), 4000);
      await loadData();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete farm.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Weather Observation
  const handleCreateWeather = async (e) => {
    e.preventDefault();
    if (!activeFarmForWeather) return;

    const temp = parseFloat(weatherForm.temperature);
    const hum = parseFloat(weatherForm.humidity);
    const rain = parseFloat(weatherForm.rainfall);
    const wind = parseFloat(weatherForm.wind_speed);

    if (isNaN(temp) || temp < -50 || temp > 60) {
      setWeatherErrorMessage('Temperature must be between -50°C and 60°C.');
      return;
    }
    if (isNaN(hum) || hum < 0 || hum > 100) {
      setWeatherErrorMessage('Humidity must be between 0% and 100%.');
      return;
    }
    if (isNaN(rain) || rain < 0) {
      setWeatherErrorMessage('Rainfall cannot be negative.');
      return;
    }
    if (isNaN(wind) || wind < 0) {
      setWeatherErrorMessage('Wind speed cannot be negative.');
      return;
    }

    setIsSubmitting(true);
    setWeatherErrorMessage(null);
    try {
      await weatherObservationService.createWeatherObservation(activeFarmForWeather.id, {
        observed_at: new Date(weatherForm.observed_at).toISOString(),
        temperature: temp,
        humidity: hum,
        rainfall: rain,
        wind_speed: wind,
      });
      setWeatherForm({
        observed_at: getCurrentLocalDatetime(),
        temperature: '',
        humidity: '',
        rainfall: '0.0',
        wind_speed: '0.0',
      });
      await loadWeather(activeFarmForWeather.id);
    } catch (err) {
      setWeatherErrorMessage(err.message || 'Failed to record weather observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Weather Observation
  const handleConfirmDeleteWeather = async () => {
    if (!deleteWeatherTarget || !activeFarmForWeather) return;
    setIsSubmitting(true);
    setWeatherErrorMessage(null);
    try {
      await weatherObservationService.deleteWeatherObservation(deleteWeatherTarget.id);
      setDeleteWeatherTarget(null);
      await loadWeather(activeFarmForWeather.id);
    } catch (err) {
      setWeatherErrorMessage(err.message || 'Failed to delete weather observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Parse coordinates helper
  const parseCoords = (locStr) => {
    if (!locStr || typeof locStr !== 'string') return null;
    const parts = locStr.split(',').map((p) => p.trim());
    if (parts.length === 2) {
      const lat = parseFloat(parts[0]);
      const lon = parseFloat(parts[1]);
      if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        return { lat, lon };
      }
    }
    return null;
  };

  // Farmer-friendly location display formatter (coordinates hidden)
  const formatLocationDisplay = (locStr) => {
    if (!locStr) return 'No location specified';
    const coords = parseCoords(locStr);
    if (coords) {
      return 'Current location detected';
    }
    return locStr;
  };

  // Open Weather Sync modal
  const handleInitiateSyncWeather = (farm) => {
    const coords = parseCoords(farm.location);
    setSyncCoords({
      latitude: coords ? String(coords.lat) : '19.9975',
      longitude: coords ? String(coords.lon) : '73.7898',
      days: 1,
    });
    setSyncErrorMessage(null);
    setSyncTargetFarm(farm);
  };

  // Execute Weather Sync via Open-Meteo
  const handleExecuteSyncWeather = async (e) => {
    e.preventDefault();
    if (!syncTargetFarm) return;

    const lat = parseFloat(syncCoords.latitude);
    const lon = parseFloat(syncCoords.longitude);
    if (isNaN(lat) || lat < -90 || lat > 90) {
      setSyncErrorMessage('Valid Latitude between -90 and 90 is required.');
      return;
    }
    if (isNaN(lon) || lon < -180 || lon > 180) {
      setSyncErrorMessage('Valid Longitude between -180 and 180 is required.');
      return;
    }

    setIsSyncingWeather(true);
    setSyncErrorMessage(null);
    try {
      const res = await syncService.syncFarmWeather(syncTargetFarm.id, {
        latitude: lat,
        longitude: lon,
        days: parseInt(syncCoords.days, 10) || 1,
      });
      setSuccessMessage(
        `Weather synced from Open-Meteo: ${res.records_received} received, ${res.records_accepted} accepted, ${res.records_rejected} rejected.`
      );
      setSyncTargetFarm(null);
      setTimeout(() => setSuccessMessage(null), 5000);
      await loadData();
      if (activeFarmForWeather && activeFarmForWeather.id === syncTargetFarm.id) {
        await loadWeather(activeFarmForWeather.id);
      }
    } catch (err) {
      setSyncErrorMessage(err.message || 'Failed to sync weather from Open-Meteo.');
    } finally {
      setIsSyncingWeather(false);
    }
  };

  const getFarmer = (farmerId) => {
    return farmers.find((item) => item.id === farmerId);
  };

  // Total acreage sum
  const totalAcreage = useMemo(() => {
    return farms.reduce((sum, f) => sum + (parseFloat(f.area) || 0), 0);
  }, [farms]);

  // Total weather readings count across all farms
  const totalWeatherCount = useMemo(() => {
    return Object.values(farmWeatherIndicatorsMap).reduce(
      (sum, ind) => sum + (ind?.observation_count || 0),
      0
    );
  }, [farmWeatherIndicatorsMap]);

  // Filtered farms based on search
  const filteredFarms = useMemo(() => {
    if (!searchQuery.trim()) return farms;
    const q = searchQuery.toLowerCase();
    return farms.filter((f) => {
      const owner = getFarmer(f.farmer_id)?.name?.toLowerCase() || '';
      return (
        f.name.toLowerCase().includes(q) ||
        f.location?.toLowerCase().includes(q) ||
        owner.includes(q)
      );
    });
  }, [farms, searchQuery, farmers]);

  return (
    <PageContainer
      title="Farm Parcels"
      subtitle="Manage land boundaries, GPS coordinates, farmer ownership, and local weather stations"
      action={
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setFarmerForm({ name: '', phone: '' });
              setIsFarmerModalOpen(true);
            }}
            className="flex items-center gap-1.5 text-slate-700"
          >
            <span>👨‍🌾</span> + Register Farmer
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleOpenAddFarm}
            className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 shadow-xs"
          >
            <span>📍</span> + Add Farm Parcel
          </Button>
        </div>
      }
    >
      {/* Notifications */}
      {successMessage && (
        <Alert variant="success" onDismiss={() => setSuccessMessage(null)} className="mb-6">
          {successMessage}
        </Alert>
      )}

      {errorMessage && (
        <Alert variant="error" onDismiss={() => setErrorMessage(null)} className="mb-6">
          {errorMessage}
        </Alert>
      )}

      {/* Top 4 KPI Metrics Bento Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* KPI 1: Total Parcels */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Total Land Parcels
              </span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-sm border border-emerald-100/80">
                📍
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading ? '...' : farms.length}
              </span>
              <span className="text-xs font-medium text-slate-500">
                parcel{farms.length === 1 ? '' : 's'}
              </span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>GPS Mapped</span>
              <span className="font-semibold text-slate-700">100% Detected</span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 2: Total Mapped Acreage */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Mapped Land Area
              </span>
              <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center text-sm border border-sky-100/80">
                🚜
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading ? '...' : totalAcreage.toFixed(1)}
              </span>
              <span className="text-xs font-medium text-slate-400">Total Acres</span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Active Plantings</span>
              <span className="font-semibold text-slate-700 font-mono">
                {crops.length} crop cycle{crops.length === 1 ? '' : 's'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 3: Registered Farmers */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Farmer Registry
              </span>
              <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center text-sm border border-violet-100/80">
                👨‍🌾
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading ? '...' : farmers.length}
              </span>
              <span className="text-xs font-medium text-slate-400">
                owner{farmers.length === 1 ? '' : 's'}
              </span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Ownership</span>
              <button
                type="button"
                onClick={() => {
                  setFarmerForm({ name: '', phone: '' });
                  setIsFarmerModalOpen(true);
                }}
                className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800"
              >
                + Add Farmer
              </button>
            </div>
          </CardContent>
        </Card>

        {/* KPI 4: Microclimate Telemetry */}
        <Card className="hover:border-slate-300 transition-all hover:shadow-md bg-white">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Weather Telemetry
              </span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center text-sm border border-amber-100/80">
                ⚡
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {isLoading ? '...' : totalWeatherCount}
              </span>
              <span className="text-xs font-medium text-slate-400">recorded readings</span>
            </div>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Weather Sync</span>
              <Badge variant="success" dot className="text-[10px] px-1.5 py-0">
                Active
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border border-slate-200">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-sm text-slate-500 font-medium">Loading farm parcels & weather telemetry...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && farms.length === 0 && (
        <EmptyState
          icon="📍"
          title="No farm parcels registered yet"
          description={
            farmers.length === 0
              ? 'Register your farmer profile first, then add your farm parcel with one-click GPS detection to automatically unlock weather risk tracking.'
              : 'Add your first farm parcel with one-click location detection to start monitoring local curing conditions and nearby mandi rates.'
          }
          action={
            farmers.length === 0 ? (
              <Button
                variant="primary"
                onClick={() => {
                  setFarmerForm({ name: '', phone: '' });
                  setIsFarmerModalOpen(true);
                }}
              >
                + Register Farmer First
              </Button>
            ) : (
              <Button variant="primary" onClick={handleOpenAddFarm}>
                + Add First Farm Parcel
              </Button>
            )
          }
        />
      )}

      {/* Main Content & Farms Grid */}
      {!isLoading && farms.length > 0 && (
        <div className="space-y-6">
          {/* Controls Bar: Search & Action Header */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-4 bg-white border border-slate-200/90 rounded-xl shadow-xs">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-3 top-2.5 text-slate-400 text-sm">🔍</span>
              <input
                type="text"
                placeholder="Search by parcel name, owner, or location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-slate-50/50"
              />
            </div>
            <div className="flex items-center justify-between sm:justify-end gap-3 text-xs text-slate-500">
              <span>
                Showing <strong className="text-slate-800 font-semibold">{filteredFarms.length}</strong> of {farms.length} parcels
              </span>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={() => {
                  setFarmerForm({ name: '', phone: '' });
                  setIsFarmerModalOpen(true);
                }}
                className="text-emerald-700 hover:text-emerald-800 font-medium hover:underline"
              >
                + New Farmer
              </button>
            </div>
          </div>

          {/* Farms Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredFarms.map((farm) => {
              const owner = getFarmer(farm.farmer_id);
              const ind = farmWeatherIndicatorsMap[farm.id];
              const farmCrops = crops.filter((c) => c.farm_id === farm.id);

              return (
                <Card
                  key={farm.id}
                  className="flex flex-col justify-between hover:border-slate-300 hover:shadow-md transition-all bg-white overflow-hidden"
                >
                  <CardHeader className="bg-slate-50/50 border-b border-slate-100 p-5">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base font-bold text-slate-900">{farm.name}</CardTitle>
                      </div>
                      <CardDescription className="flex items-center gap-1.5 text-emerald-800 mt-1 font-medium text-xs">
                        <span className="flex h-2 w-2 relative">
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                        <span>{formatLocationDisplay(farm.location)}</span>
                      </CardDescription>
                    </div>
                    <Badge variant="neutral" className="text-xs font-semibold px-2 py-0.5">
                      {farm.area} {farm.area_unit}{farm.area > 1 ? 's' : ''}
                    </Badge>
                  </CardHeader>

                  <CardContent className="p-5 space-y-3.5 text-xs text-slate-600">
                    {/* Owner & Identification */}
                    <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs shrink-0">
                          {owner?.name ? owner.name.charAt(0).toUpperCase() : 'F'}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-800">
                            {owner?.name || `Farmer #${farm.farmer_id}`}
                          </div>
                          {owner?.phone && (
                            <div className="text-[11px] text-slate-400 font-mono">{owner.phone}</div>
                          )}
                        </div>
                      </div>
                      <span className="font-mono text-[11px] text-slate-400 bg-white px-2 py-0.5 rounded border border-slate-200/60">
                        #{farm.id}
                      </span>
                    </div>

                    {/* Planted Crops Summary */}
                    <div className="pt-1 flex items-center justify-between text-xs border-b border-slate-100 pb-2.5">
                      <span className="text-slate-400">Active Cultivations:</span>
                      {farmCrops.length > 0 ? (
                        <div className="flex items-center gap-1.5">
                          <Badge variant="info" className="text-[10px] font-semibold">
                            {farmCrops.map((c) => c.crop_name).join(', ')} ({farmCrops.reduce((acc, c) => acc + (parseFloat(c.area) || 0), 0)} ac)
                          </Badge>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => navigate('/crops')}
                          className="text-[11px] text-emerald-700 hover:text-emerald-800 font-medium hover:underline"
                        >
                          + Plant Crop
                        </button>
                      )}
                    </div>

                    {/* Microclimate Telemetry Section */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                          <span>🌤️</span> Microclimate Telemetry
                        </span>
                        {ind && ind.observation_count > 0 && (
                          <Badge variant="success" dot className="text-[9px] px-1.5 py-0">
                            {ind.observation_count} obs
                          </Badge>
                        )}
                      </div>

                      {ind && ind.observation_count > 0 ? (
                        <div className="space-y-2 p-3 bg-slate-50/80 rounded-xl border border-slate-200/70">
                          {/* 4-quadrant readings */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="p-2 bg-white rounded-lg border border-slate-200/60 flex items-center justify-between">
                              <span className="text-slate-400 text-[11px]">Temp</span>
                              <span className="font-bold text-slate-800 font-mono">
                                {ind.latest_temperature}°C
                              </span>
                            </div>
                            <div className="p-2 bg-white rounded-lg border border-slate-200/60 flex items-center justify-between">
                              <span className="text-slate-400 text-[11px]">Humidity</span>
                              <span className="font-bold text-slate-800 font-mono">
                                {ind.latest_humidity}%
                              </span>
                            </div>
                            <div className="p-2 bg-white rounded-lg border border-slate-200/60 flex items-center justify-between">
                              <span className="text-slate-400 text-[11px]">Rainfall</span>
                              <span className="font-bold text-slate-800 font-mono">
                                {ind.latest_rainfall} mm
                              </span>
                            </div>
                            <div className="p-2 bg-white rounded-lg border border-slate-200/60 flex items-center justify-between">
                              <span className="text-slate-400 text-[11px]">Wind</span>
                              <span className="font-bold text-slate-800 font-mono">
                                {ind.latest_wind_speed} km/h
                              </span>
                            </div>
                          </div>

                          {/* Calculated aggregate bar */}
                          <div className="pt-1.5 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                            <span>48h Avg Temp: <strong className="text-slate-700">{ind.average_temperature}°C</strong></span>
                            <span>Total Rain: <strong className="text-slate-700">{ind.total_rainfall} mm</strong></span>
                          </div>
                        </div>
                      ) : (
                        <div className="p-3 bg-slate-50 rounded-xl text-center text-xs text-slate-400 border border-dashed border-slate-200 flex flex-col items-center gap-1.5">
                          <span>No weather telemetry recorded yet.</span>
                          <button
                            type="button"
                            onClick={() => handleInitiateSyncWeather(farm)}
                            className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
                          >
                            ⚡ Sync Open-Meteo Weather Now
                          </button>
                        </div>
                      )}
                    </div>
                  </CardContent>

                  <CardFooter className="bg-slate-50/50 p-4 border-t border-slate-100 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs h-8"
                        onClick={() => handleOpenWeather(farm)}
                      >
                        🌤️ Measurements
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        className="text-xs h-8 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200"
                        onClick={() => handleInitiateSyncWeather(farm)}
                      >
                        ⚡ Sync Weather
                      </Button>
                    </div>
                    <Button
                      variant="subtle"
                      size="sm"
                      className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 text-xs h-8"
                      onClick={() => setDeleteTarget(farm)}
                    >
                      Delete
                    </Button>
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: ADD FARM */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isAddFarmOpen}
        onClose={() => !isSubmitting && setIsAddFarmOpen(false)}
        title="Register Farm Parcel"
        subtitle="Specify land parcel details with one-click GPS detection for weather sync."
      >
        <form onSubmit={handleCreateFarm} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-slate-700">
                Farmer Owner <span className="text-rose-500">*</span>
              </label>
              <button
                type="button"
                onClick={() => {
                  setIsFarmerModalOpen(true);
                }}
                className="text-xs text-emerald-600 hover:text-emerald-700 font-medium"
              >
                + Register New Farmer
              </button>
            </div>
            {farmers.length === 0 ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                No registered farmers found. Please click <strong>+ Register New Farmer</strong> above.
              </div>
            ) : (
              <select
                required
                value={farmForm.farmer_id}
                onChange={(e) => setFarmForm({ ...farmForm, farmer_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="">Select a farmer...</option>
                {farmers.map((farmer) => (
                  <option key={farmer.id} value={farmer.id}>
                    {farmer.name} {farmer.phone ? `(${farmer.phone})` : ''}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Farm Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Shiva Mala Shivar"
              value={farmForm.name}
              onChange={(e) => setFarmForm({ ...farmForm, name: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Farm Location <span className="text-rose-500">*</span>
            </label>

            {locationDetectionStatus === 'success' || (farmForm.location && parseCoords(farmForm.location)) ? (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-semibold text-emerald-900 text-sm">
                    <span className="text-base">📍</span>
                    <span>Location detected successfully</span>
                  </div>
                  <Button
                    type="button"
                    variant="subtle"
                    size="sm"
                    onClick={handleDetectLocation}
                    disabled={isDetectingLocation}
                    className="text-emerald-700 hover:text-emerald-900 text-xs px-2 py-1 h-auto"
                  >
                    {isDetectingLocation ? 'Detecting...' : 'Re-detect'}
                  </Button>
                </div>

                <div className="text-sm font-medium text-slate-800 pl-6">
                  Current location detected
                </div>

              </div>
            ) : (
              <div className="space-y-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleDetectLocation}
                  disabled={isDetectingLocation}
                  className="w-full flex items-center justify-center gap-2 py-3 border-2 border-emerald-600 bg-emerald-50/50 text-emerald-800 hover:bg-emerald-100 font-semibold text-sm rounded-xl transition-all shadow-xs cursor-pointer"
                >
                  <span className="text-lg">📍</span>
                  <span>{isDetectingLocation ? 'Detecting your GPS location...' : 'Detect My Location'}</span>
                </Button>

                {locationDetectionStatus === 'error' && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-start gap-2">
                    <span className="text-sm">⚠️</span>
                    <span>{locationDetectionMessage}</span>
                  </div>
                )}

                <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
                  <span>Click to automatically detect GPS coordinates for weather sync.</span>
                  {!showManualLocationInput && (
                    <button
                      type="button"
                      onClick={() => setShowManualLocationInput(true)}
                      className="text-slate-500 underline hover:text-slate-700 cursor-pointer"
                    >
                      Enter manually
                    </button>
                  )}
                </div>
              </div>
            )}

            {showManualLocationInput && locationDetectionStatus !== 'success' && !(farmForm.location && parseCoords(farmForm.location)) && (
              <div className="mt-2 pt-2 border-t border-slate-100 space-y-1">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[11px] font-medium text-slate-600">Manual Coordinates or Location:</span>
                  <button
                    type="button"
                    onClick={() => setShowManualLocationInput(false)}
                    className="text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer"
                  >
                    Hide
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="e.g. 19.9975, 73.7898"
                  value={farmForm.location}
                  onChange={(e) => setFarmForm({ ...farmForm, location: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            )}

            {/* Hidden field storing coordinates internally */}
            <input
              type="hidden"
              name="location"
              value={farmForm.location}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Area <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="e.g. 3.5"
                value={farmForm.area}
                onChange={(e) => setFarmForm({ ...farmForm, area: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Unit <span className="text-rose-500">*</span>
              </label>
              <select
                value={farmForm.area_unit}
                onChange={(e) => setFarmForm({ ...farmForm, area_unit: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="acre">Acres</option>
                <option value="hectare">Hectares</option>
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setIsAddFarmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isSubmitting || farmers.length === 0}
            >
              {isSubmitting ? 'Registering Farm...' : 'Save Farm'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: REGISTER FARMER */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isFarmerModalOpen}
        onClose={() => !isSubmitting && setIsFarmerModalOpen(false)}
        title="Register Farmer Profile"
        subtitle="Establish farmer identity before creating land parcels."
      >
        <form onSubmit={handleCreateFarmer} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Farmer Full Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Dnyaneshwar Bhor"
              value={farmerForm.name}
              onChange={(e) => setFarmerForm({ ...farmerForm, name: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Phone Number <span className="text-slate-400 font-normal">(Optional)</span>
            </label>
            <input
              type="tel"
              placeholder="e.g. +91 98220 12345"
              value={farmerForm.phone}
              onChange={(e) => setFarmerForm({ ...farmerForm, phone: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setIsFarmerModalOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Registering...' : 'Save Farmer'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: WEATHER OBSERVATIONS */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!activeFarmForWeather}
        onClose={() => !isSubmitting && setActiveFarmForWeather(null)}
        title={`Weather Measurements: ${activeFarmForWeather?.name}`}
        subtitle={`Location: ${formatLocationDisplay(activeFarmForWeather?.location)}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-6">
          {weatherErrorMessage && (
            <Alert variant="error" onDismiss={() => setWeatherErrorMessage(null)}>
              {weatherErrorMessage}
            </Alert>
          )}

          {/* Decision-Ready Farm Weather Indicators in Modal */}
          {activeFarmForWeather && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                  Farm Weather Indicators
                </h4>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleInitiateSyncWeather(activeFarmForWeather)}
                >
                  ⚡ Sync from Open-Meteo
                </Button>
              </div>
              {farmWeatherIndicatorsMap[activeFarmForWeather.id] && farmWeatherIndicatorsMap[activeFarmForWeather.id].observation_count > 0 ? (
                <div className="space-y-3 text-xs">
                  {/* Latest Observed */}
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="flex items-center gap-1.5 text-slate-500 font-medium">
                        <Badge variant="info" className="text-[9px] px-1.5 py-0">Observed</Badge> Latest Condition
                      </span>
                      <span className="font-mono text-slate-400 text-[10px]">
                        {farmWeatherIndicatorsMap[activeFarmForWeather.id].latest_observed_at ? new Date(farmWeatherIndicatorsMap[activeFarmForWeather.id].latest_observed_at).toLocaleString() : ''}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Temperature</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].latest_temperature}°C</div>
                      </div>
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Humidity</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].latest_humidity}%</div>
                      </div>
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Rainfall</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].latest_rainfall} mm</div>
                      </div>
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Wind Speed</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].latest_wind_speed} km/h</div>
                      </div>
                    </div>
                  </div>

                  {/* Calculated Aggregates */}
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Badge variant="neutral" className="text-[9px] px-1.5 py-0">Calculated</Badge>
                      <span className="text-slate-500 font-medium">Aggregated Metrics ({farmWeatherIndicatorsMap[activeFarmForWeather.id].observation_count} observations)</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Avg Temperature</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].average_temperature}°C</div>
                      </div>
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Total Rainfall</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].total_rainfall} mm</div>
                      </div>
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Avg Humidity</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].average_humidity}%</div>
                      </div>
                      <div className="p-2 bg-white rounded border border-slate-200/60">
                        <div className="text-[10px] text-slate-400">Avg Wind Speed</div>
                        <div className="font-semibold text-slate-800">{farmWeatherIndicatorsMap[activeFarmForWeather.id].average_wind_speed} km/h</div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-slate-50 rounded-lg text-center text-xs text-slate-400 border border-dashed border-slate-200">
                  No weather observations available.
                </div>
              )}
            </div>
          )}

          {/* New Weather Observation Form */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-3">
              + Log Ambient Weather Measurement
            </h4>
            <form onSubmit={handleCreateWeather} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Observed Date & Time <span className="text-rose-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  required
                  value={weatherForm.observed_at}
                  onChange={(e) => setWeatherForm({ ...weatherForm, observed_at: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Temp (°C) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="-50"
                    max="60"
                    required
                    placeholder="e.g. 28.5"
                    value={weatherForm.temperature}
                    onChange={(e) => setWeatherForm({ ...weatherForm, temperature: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Humidity (%) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    required
                    placeholder="e.g. 65"
                    value={weatherForm.humidity}
                    onChange={(e) => setWeatherForm({ ...weatherForm, humidity: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Rainfall (mm) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    required
                    placeholder="e.g. 0.0"
                    value={weatherForm.rainfall}
                    onChange={(e) => setWeatherForm({ ...weatherForm, rainfall: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Wind (km/h) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    required
                    placeholder="e.g. 12"
                    value={weatherForm.wind_speed}
                    onChange={(e) => setWeatherForm({ ...weatherForm, wind_speed: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-1">
                <Button variant="primary" size="sm" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Recording...' : 'Record Weather'}
                </Button>
              </div>
            </form>
          </div>

          {/* Weather History List */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                Weather Measurement History ({weatherObservations.length})
              </h4>
            </div>

            {isLoadingWeather && (
              <div className="p-6 text-center text-xs text-slate-400">Loading measurements...</div>
            )}

            {!isLoadingWeather && weatherObservations.length === 0 && (
              <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                No weather observations recorded yet for this farm.
              </div>
            )}

            {!isLoadingWeather && weatherObservations.length > 0 && (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {weatherObservations.map((obs) => (
                  <div
                    key={obs.id}
                    className="p-3 bg-white border border-slate-200 rounded-xl flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-mono font-medium text-slate-800">
                        {new Date(obs.observed_at).toLocaleString()}
                      </div>
                      <div className="flex items-center gap-3 text-slate-600">
                        <span>🌡️ <strong>{obs.temperature}°C</strong></span>
                        <span>💧 <strong>{obs.humidity}%</strong> RH</span>
                        <span>🌧️ <strong>{obs.rainfall} mm</strong></span>
                        <span>💨 <strong>{obs.wind_speed} km/h</strong></span>
                      </div>
                    </div>
                    <Button
                      variant="subtle"
                      size="sm"
                      className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 shrink-0"
                      onClick={() => setDeleteWeatherTarget(obs)}
                    >
                      Delete
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: CONFIRM DELETE FARM */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => !isSubmitting && setDeleteTarget(null)}
        title="Confirm Farm Deletion"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to delete farm <strong className="text-slate-900">"{deleteTarget?.name}"</strong>?
          </p>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <strong>Warning:</strong> Deleting this farm will permanently delete all associated crop plantings and weather observations through cascade deletion.
          </div>
          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setDeleteTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="button"
              disabled={isSubmitting}
              className="bg-rose-600 hover:bg-rose-700 text-white focus:ring-rose-500"
              onClick={handleConfirmDeleteFarm}
            >
              {isSubmitting ? 'Deleting...' : 'Confirm Delete'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: CONFIRM DELETE WEATHER */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!deleteWeatherTarget}
        onClose={() => !isSubmitting && setDeleteWeatherTarget(null)}
        title="Confirm Weather Observation Deletion"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete weather record from <strong className="text-slate-900">{deleteWeatherTarget && new Date(deleteWeatherTarget.observed_at).toLocaleString()}</strong>?
          </p>
          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setDeleteWeatherTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="button"
              disabled={isSubmitting}
              className="bg-rose-600 hover:bg-rose-700 text-white focus:ring-rose-500"
              onClick={handleConfirmDeleteWeather}
            >
              {isSubmitting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: SYNC WEATHER FROM OPEN-METEO */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!syncTargetFarm}
        onClose={() => !isSyncingWeather && setSyncTargetFarm(null)}
        title={`Sync Weather: ${syncTargetFarm?.name}`}
        subtitle="Pull real atmospheric observations from Open-Meteo into farm records."
      >
        <form onSubmit={handleExecuteSyncWeather} className="space-y-4">
          {syncErrorMessage && (
            <Alert variant="error" onDismiss={() => setSyncErrorMessage(null)}>
              {syncErrorMessage}
            </Alert>
          )}

          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 leading-relaxed">
            <strong>Provider:</strong> Open-Meteo (Free for non-commercial use, no API key required).
            <div className="mt-1 text-blue-800">
              Per system safety rules, automatic geocoding is disabled. Specify numeric coordinates for this parcel.
            </div>
          </div>

          {parseCoords(syncTargetFarm?.location) ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-900">
                <span>📍</span>
                <span>Using Farm's Detected Location</span>
              </div>
              <div className="text-slate-600">
                Weather coordinates are pre-populated automatically from the farm's saved GPS location.
              </div>
              <div className="flex gap-4 text-[11px] text-slate-500 pt-1 font-mono border-t border-emerald-200/60">
                <span>Latitude: internally stored</span>
                <span>Longitude: internally stored</span>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Latitude (°N) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="-90"
                  max="90"
                  required
                  placeholder="e.g. 19.9975"
                  value={syncCoords.latitude}
                  onChange={(e) => setSyncCoords({ ...syncCoords, latitude: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Longitude (°E) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="-180"
                  max="180"
                  required
                  placeholder="e.g. 73.7898"
                  value={syncCoords.longitude}
                  onChange={(e) => setSyncCoords({ ...syncCoords, longitude: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Time Range (Observations)
            </label>
            <select
              value={syncCoords.days}
              onChange={(e) => setSyncCoords({ ...syncCoords, days: parseInt(e.target.value, 10) })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value={1}>Past 24 Hours (24 hourly measurements)</option>
              <option value={2}>Past 48 Hours (48 hourly measurements)</option>
              <option value={3}>Past 3 Days (72 hourly measurements)</option>
            </select>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSyncingWeather}
              onClick={() => setSyncTargetFarm(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isSyncingWeather}
            >
              {isSyncingWeather ? 'Syncing Weather...' : 'Start Weather Sync'}
            </Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
}

export default Farms;
