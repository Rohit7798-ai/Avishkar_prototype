import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Alert } from '../components/ui/Alert';
import { Modal } from '../components/ui/Modal';
import { cropService } from '../services/cropService';
import { farmService } from '../services/farmService';
import { cropObservationService } from '../services/cropObservationService';
import { indicatorService } from '../services/indicatorService';
import { decisionService } from '../services/decisionService';
import { explanationService } from '../services/explanationService';
import { recommendationService } from '../services/recommendationService';
import { reminderService } from '../services/reminderService';

const WEEKDAYS = [
  { value: 'sunday', label: 'Sunday' },
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
];

const GROWTH_STAGES = [
  { value: 'early', label: 'Early Stage' },
  { value: 'vegetative', label: 'Vegetative Growth' },
  { value: 'flowering', label: 'Flowering' },
  { value: 'fruiting', label: 'Fruiting / Bulb Dev' },
  { value: 'maturity', label: 'Maturity' },
  { value: 'post_maturity', label: 'Post-Maturity' },
];

const HEALTH_STATUSES = [
  { value: 'healthy', label: 'Healthy', variant: 'success' },
  { value: 'moderate', label: 'Moderate', variant: 'neutral' },
  { value: 'stressed', label: 'Stressed', variant: 'warning' },
  { value: 'damaged', label: 'Damaged', variant: 'warning' },
];

export function Crops() {
  const navigate = useNavigate();
  const [crops, setCrops] = useState([]);
  const [farms, setFarms] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Indicators state map (crop_id -> indicators)
  const [cropIndicatorsMap, setCropIndicatorsMap] = useState({});
  // Decision assessment state map (crop_id -> assessment)
  const [cropAssessmentsMap, setCropAssessmentsMap] = useState({});
  // Observation reminders state map (crop_id -> reminder)
  const [cropRemindersMap, setCropRemindersMap] = useState({});

  // Observation Reminder modal states
  const [activeCropForReminder, setActiveCropForReminder] = useState(null);
  const [isReminderModalOpen, setIsReminderModalOpen] = useState(false);
  const [reminderForm, setReminderForm] = useState({
    enabled: true,
    weekday: 'sunday',
    reminder_time: '08:00',
  });
  const [isSubmittingReminder, setIsSubmittingReminder] = useState(false);
  const [reminderErrorMessage, setReminderErrorMessage] = useState(null);
  const [notificationPermissionStatus, setNotificationPermissionStatus] = useState(
    typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default'
  );

  // Crop Creation & Deletion modal states
  const [isAddCropOpen, setIsAddCropOpen] = useState(false);
  const [deleteCropTarget, setDeleteCropTarget] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Observation state
  const [activeCropForObs, setActiveCropForObs] = useState(null);
  const [observations, setObservations] = useState([]);
  const [isLoadingObs, setIsLoadingObs] = useState(false);
  const [obsErrorMessage, setObsErrorMessage] = useState(null);
  const [deleteObsTarget, setDeleteObsTarget] = useState(null);

  // Explanation state
  const [activeCropForExplanation, setActiveCropForExplanation] = useState(null);
  const [explanationData, setExplanationData] = useState(null);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false);
  const [explanationError, setExplanationError] = useState(null);

  // Recommendation state
  const [activeCropForRecommendation, setActiveCropForRecommendation] = useState(null);
  const [recommendationData, setRecommendationData] = useState(null);
  const [isLoadingRecommendation, setIsLoadingRecommendation] = useState(false);
  const [recommendationError, setRecommendationError] = useState(null);

  // New Crop form state
  const [cropForm, setCropForm] = useState({
    farm_id: '',
    crop_name: '',
    variety: '',
    sowing_date: '',
    expected_harvest_date: '',
    area: '',
    area_unit: 'acre',
  });

  // New Observation form state
  const [obsForm, setObsForm] = useState({
    observation_date: new Date().toISOString().split('T')[0],
    growth_stage: 'vegetative',
    health_status: 'healthy',
    notes: '',
  });

  // Load crops, available farms, and crop indicators
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [fetchedCrops, fetchedFarms] = await Promise.all([
        cropService.getCrops(),
        farmService.getFarms(),
      ]);
      setCrops(fetchedCrops);
      setFarms(fetchedFarms);

      // Load deterministic indicators, decision assessments, and reminders for all crops
      const [indicatorsList, assessmentsList, remindersList] = await Promise.all([
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
        Promise.all(
          fetchedCrops.map(async (c) => {
            try {
              const assessment = await decisionService.getCropDecisionAssessment(c.id);
              return { id: c.id, assessment };
            } catch {
              return { id: c.id, assessment: null };
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
      ]);

      const indMap = {};
      indicatorsList.forEach((item) => {
        if (item.ind) indMap[item.id] = item.ind;
      });
      setCropIndicatorsMap(indMap);

      const assessMap = {};
      assessmentsList.forEach((item) => {
        if (item.assessment) assessMap[item.id] = item.assessment;
      });
      setCropAssessmentsMap(assessMap);

      const remMap = {};
      remindersList.forEach((item) => {
        if (item.reminder) remMap[item.id] = item.reminder;
      });
      setCropRemindersMap(remMap);
    } catch (err) {
      setErrorMessage(err.message || 'Unable to load crop records. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load observations, indicators, and decision assessment when active crop modal opens
  const loadObservations = useCallback(async (cropId) => {
    setIsLoadingObs(true);
    setObsErrorMessage(null);
    try {
      const [data, indicators, assessment] = await Promise.all([
        cropObservationService.getCropObservations(cropId),
        indicatorService.getCropIndicators(cropId).catch(() => null),
        decisionService.getCropDecisionAssessment(cropId).catch(() => null),
      ]);
      setObservations(data);
      if (indicators) {
        setCropIndicatorsMap((prev) => ({ ...prev, [cropId]: indicators }));
      }
      if (assessment) {
        setCropAssessmentsMap((prev) => ({ ...prev, [cropId]: assessment }));
      }
    } catch (err) {
      setObsErrorMessage(err.message || 'Failed to load observations for this crop.');
    } finally {
      setIsLoadingObs(false);
    }
  }, []);

  const handleOpenObservations = (crop) => {
    setActiveCropForObs(crop);
    setObsForm({
      observation_date: new Date().toISOString().split('T')[0],
      growth_stage: 'vegetative',
      health_status: 'healthy',
      notes: '',
    });
    loadObservations(crop.id);
  };

  const handleOpenExplanation = async (crop) => {
    setActiveCropForExplanation(crop);
    setExplanationData(null);
    setExplanationError(null);
    setIsLoadingExplanation(true);
    try {
      const data = await explanationService.getCropExplanation(crop.id);
      setExplanationData(data);
    } catch (err) {
      setExplanationError(err.message || 'Failed to load explanation for this crop.');
    } finally {
      setIsLoadingExplanation(false);
    }
  };

  const handleOpenRecommendation = async (crop) => {
    setActiveCropForRecommendation(crop);
    setRecommendationData(null);
    setRecommendationError(null);
    setIsLoadingRecommendation(true);
    try {
      const data = await recommendationService.getCropRecommendation(crop.id);
      setRecommendationData(data);
    } catch (err) {
      setRecommendationError(err.message || 'Failed to load recommendations for this crop.');
    } finally {
      setIsLoadingRecommendation(false);
    }
  };

  // Helper formatting for reminder schedules
  const formatWeekdayDisplay = (weekday) => {
    if (!weekday) return '';
    return weekday.charAt(0).toUpperCase() + weekday.slice(1).toLowerCase();
  };

  const formatTimeDisplay = (timeStr) => {
    if (!timeStr) return '';
    const [hours, minutes] = timeStr.split(':').map((num) => parseInt(num, 10));
    if (isNaN(hours) || isNaN(minutes)) return timeStr;
    const period = hours >= 12 ? 'PM' : 'AM';
    const h12 = hours % 12 || 12;
    return `${String(h12).padStart(2, '0')}:${String(minutes).padStart(2, '0')} ${period}`;
  };

  const getNextReminderDate = (weekday, reminderTime) => {
    if (!weekday || !reminderTime) return null;
    const dayIndices = {
      sunday: 0,
      monday: 1,
      tuesday: 2,
      wednesday: 3,
      thursday: 4,
      friday: 5,
      saturday: 6,
    };
    const targetDay = dayIndices[weekday.toLowerCase()];
    if (targetDay === undefined) return null;

    const [hours, minutes] = reminderTime.split(':').map((num) => parseInt(num, 10));
    const now = new Date();
    const result = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hours || 0, minutes || 0, 0, 0);

    const currentDay = now.getDay();
    let daysUntil = (targetDay - currentDay + 7) % 7;
    if (daysUntil === 0 && now.getTime() > result.getTime()) {
      daysUntil = 7;
    }
    result.setDate(result.getDate() + daysUntil);
    return result;
  };

  const formatNextReminder = (weekday, reminderTime) => {
    const nextDate = getNextReminderDate(weekday, reminderTime);
    if (!nextDate) return 'Not scheduled';
    return (
      nextDate.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      }) + `, ${formatTimeDisplay(reminderTime)}`
    );
  };

  // Determine crops with active weekly reminders due
  const dueCropsForReminder = React.useMemo(() => {
    if (!crops || crops.length === 0) return [];
    const now = new Date();
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const currentDayName = days[now.getDay()];

    return crops.filter((crop) => {
      const rem = cropRemindersMap[crop.id];
      if (!rem || !rem.enabled) return false;
      const ind = cropIndicatorsMap[crop.id];
      const isScheduledToday = rem.weekday.toLowerCase() === currentDayName;
      const needsObservation = !ind || ind.days_since_latest_observation === null || ind.days_since_latest_observation >= 7;
      return isScheduledToday || needsObservation;
    });
  }, [crops, cropRemindersMap, cropIndicatorsMap]);

  // Trigger browser notification at most once per week per crop
  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;

    const now = new Date();
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const currentDayName = days[now.getDay()];

    // Generate ISO week key (e.g. 2026-W40)
    const d = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    const weekKey = `${d.getUTCFullYear()}-W${weekNo}`;

    crops.forEach((crop) => {
      const rem = cropRemindersMap[crop.id];
      if (!rem || !rem.enabled) return;
      if (rem.weekday.toLowerCase() !== currentDayName) return;

      const storageKey = `fdss_reminder_notified_${crop.id}_${weekKey}`;
      if (localStorage.getItem(storageKey)) return;

      try {
        const notif = new Notification('🔔 Weekly Observation Reminder', {
          body: `Time to record growth stage and health for ${crop.crop_name}.`,
        });
        notif.onclick = () => {
          window.focus();
          handleOpenObservations(crop);
        };
        localStorage.setItem(storageKey, 'true');
      } catch {
        // Notification permission or creation failed
      }
    });
  }, [crops, cropRemindersMap]);

  // Open Observation Reminder Schedule Modal
  const handleOpenReminderModal = (crop) => {
    setActiveCropForReminder(crop);
    const existing = cropRemindersMap[crop.id];
    if (existing) {
      setReminderForm({
        enabled: existing.enabled,
        weekday: existing.weekday,
        reminder_time: existing.reminder_time,
      });
    } else {
      setReminderForm({
        enabled: true,
        weekday: 'sunday',
        reminder_time: '08:00',
      });
    }
    setReminderErrorMessage(null);
    setIsReminderModalOpen(true);
  };

  // Save Observation Reminder Schedule
  const handleSaveReminderSchedule = async (e) => {
    e.preventDefault();
    if (!activeCropForReminder) return;

    setIsSubmittingReminder(true);
    setReminderErrorMessage(null);

    // Request notification permission if farmer enables reminder
    if (reminderForm.enabled && typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'default') {
        try {
          const perm = await Notification.requestPermission();
          setNotificationPermissionStatus(perm);
        } catch {
          // ignore
        }
      } else {
        setNotificationPermissionStatus(Notification.permission);
      }
    }

    try {
      const saved = await reminderService.createReminder(activeCropForReminder.id, {
        enabled: reminderForm.enabled,
        weekday: reminderForm.weekday,
        reminder_time: reminderForm.reminder_time,
      });

      setCropRemindersMap((prev) => ({
        ...prev,
        [activeCropForReminder.id]: saved,
      }));

      setIsReminderModalOpen(false);
      setSuccessMessage(`Observation schedule for "${activeCropForReminder.crop_name}" saved.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      setReminderErrorMessage(err.message || 'Failed to save observation reminder schedule.');
    } finally {
      setIsSubmittingReminder(false);
    }
  };

  // Toggle Reminder Enabled/Disabled
  const handleToggleReminder = async (crop, reminder) => {
    if (!reminder) return;
    try {
      const newEnabled = !reminder.enabled;
      if (newEnabled && typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
        try {
          const perm = await Notification.requestPermission();
          setNotificationPermissionStatus(perm);
        } catch {
          // ignore
        }
      }

      const updated = await reminderService.updateReminder(crop.id, {
        enabled: newEnabled,
      });

      setCropRemindersMap((prev) => ({
        ...prev,
        [crop.id]: updated,
      }));
      setSuccessMessage(
        `Reminder for "${crop.crop_name}" ${newEnabled ? 'enabled' : 'disabled'}.`
      );
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to update reminder status.');
    }
  };

  // Delete Reminder Schedule
  const handleDeleteReminder = async () => {
    if (!activeCropForReminder) return;
    setIsSubmittingReminder(true);
    setReminderErrorMessage(null);
    try {
      await reminderService.deleteReminder(activeCropForReminder.id);
      setCropRemindersMap((prev) => {
        const copy = { ...prev };
        delete copy[activeCropForReminder.id];
        return copy;
      });
      setIsReminderModalOpen(false);
      setSuccessMessage(`Reminder schedule for "${activeCropForReminder.crop_name}" removed.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      setReminderErrorMessage(err.message || 'Failed to remove reminder schedule.');
    } finally {
      setIsSubmittingReminder(false);
    }
  };

  // Open Add Crop modal
  const handleOpenAddCrop = () => {
    setCropForm({
      farm_id: farms.length > 0 ? String(farms[0].id) : '',
      crop_name: 'Onion',
      variety: '',
      sowing_date: new Date().toISOString().split('T')[0],
      expected_harvest_date: '',
      area: '',
      area_unit: 'acre',
    });
    setErrorMessage(null);
    setIsAddCropOpen(true);
  };

  // Submit Crop Form with validation
  const handleCreateCrop = async (e) => {
    e.preventDefault();

    if (!cropForm.farm_id) {
      setErrorMessage('Please select a farm parcel.');
      return;
    }
    if (!cropForm.crop_name.trim()) {
      setErrorMessage('Crop name is required.');
      return;
    }
    if (!cropForm.sowing_date) {
      setErrorMessage('Sowing date is required.');
      return;
    }
    if (cropForm.expected_harvest_date && cropForm.expected_harvest_date < cropForm.sowing_date) {
      setErrorMessage('Expected harvest date cannot be before sowing date.');
      return;
    }
    const numericArea = parseFloat(cropForm.area);
    if (isNaN(numericArea) || numericArea <= 0) {
      setErrorMessage('Planted area must be a positive number.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await cropService.createCrop({
        farm_id: parseInt(cropForm.farm_id, 10),
        crop_name: cropForm.crop_name.trim(),
        variety: cropForm.variety.trim() || null,
        sowing_date: cropForm.sowing_date,
        expected_harvest_date: cropForm.expected_harvest_date || null,
        area: numericArea,
        area_unit: cropForm.area_unit,
      });

      setIsAddCropOpen(false);
      setSuccessMessage(`Crop planting "${cropForm.crop_name}" added successfully.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      await loadData();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to add crop planting. Please verify inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Crop
  const handleConfirmDeleteCrop = async () => {
    if (!deleteCropTarget) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await cropService.deleteCrop(deleteCropTarget.id);
      setSuccessMessage(`Crop planting "${deleteCropTarget.crop_name}" deleted.`);
      setDeleteCropTarget(null);
      setTimeout(() => setSuccessMessage(null), 4000);
      await loadData();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete crop.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Crop Observation
  const handleCreateObservation = async (e) => {
    e.preventDefault();
    if (!activeCropForObs) return;

    setIsSubmitting(true);
    setObsErrorMessage(null);
    try {
      await cropObservationService.createCropObservation(activeCropForObs.id, {
        observation_date: obsForm.observation_date,
        growth_stage: obsForm.growth_stage,
        health_status: obsForm.health_status,
        notes: obsForm.notes.trim() || null,
      });
      setObsForm({
        observation_date: new Date().toISOString().split('T')[0],
        growth_stage: 'vegetative',
        health_status: 'healthy',
        notes: '',
      });
      await loadObservations(activeCropForObs.id);
    } catch (err) {
      setObsErrorMessage(err.message || 'Failed to record crop observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Crop Observation
  const handleConfirmDeleteObservation = async () => {
    if (!deleteObsTarget || !activeCropForObs) return;
    setIsSubmitting(true);
    setObsErrorMessage(null);
    try {
      await cropObservationService.deleteCropObservation(deleteObsTarget.id);
      setDeleteObsTarget(null);
      await loadObservations(activeCropForObs.id);
    } catch (err) {
      setObsErrorMessage(err.message || 'Failed to delete observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFarmName = (farmId) => {
    const f = farms.find((item) => item.id === farmId);
    return f ? f.name : `Farm #${farmId}`;
  };

  const formatFarmLocation = (loc) => {
    if (!loc) return '';
    const parts = loc.split(',').map((p) => p.trim());
    if (parts.length === 2 && !isNaN(parseFloat(parts[0])) && !isNaN(parseFloat(parts[1]))) {
      return 'Current location detected';
    }
    return loc;
  };

  return (
    <PageContainer
      title="Crops"
      subtitle="Track active crop cycles, sowing dates, and field observations"
      action={
        <Button variant="primary" onClick={handleOpenAddCrop}>
          + Add Crop
        </Button>
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

      {/* In-App Reminder Banner for Due Crops */}
      {!isLoading && dueCropsForReminder.length > 0 && (
        <div className="mb-6 space-y-3">
          {dueCropsForReminder.map((crop) => (
            <div
              key={`banner-${crop.id}`}
              className="p-4 bg-emerald-50/90 border border-emerald-300 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl shrink-0">🔔</span>
                <div>
                  <h4 className="text-sm font-bold text-emerald-950">
                    Weekly Observation Reminder
                  </h4>
                  <p className="text-xs text-emerald-800 mt-0.5">
                    Time to record growth stage and health for <strong>{crop.crop_name}</strong> ({getFarmName(crop.farm_id)}).
                  </p>
                </div>
              </div>
              <Button
                variant="primary"
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white shrink-0 self-end sm:self-center font-medium"
                onClick={() => handleOpenObservations(crop)}
              >
                [ Record Observation ]
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border border-slate-200">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-sm text-slate-500 font-medium">Loading crops...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && crops.length === 0 && (
        <EmptyState
          icon="🧅"
          title="No crops added yet."
          description={
            farms.length === 0
              ? 'You need to create a farm parcel before logging crop cycles. Start by registering your first farm.'
              : 'Register crop plantings (e.g. Kharif, Rangda, or Rabi onions) with their sowing dates to track crop age and harvest timing.'
          }
          action={
            farms.length === 0 ? (
              <Button variant="primary" onClick={() => navigate('/farms')}>
                Go to Farms
              </Button>
            ) : (
              <Button variant="primary" onClick={handleOpenAddCrop}>
                + Add Crop
              </Button>
            )
          }
        />
      )}

      {/* Crop Cards List */}
      {!isLoading && crops.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {crops.map((crop) => (
            <Card key={crop.id} className="flex flex-col justify-between">
              <CardHeader>
                <div>
                  <CardTitle>{crop.crop_name}</CardTitle>
                  <CardDescription>{crop.variety || 'Standard Variety'}</CardDescription>
                </div>
                <Badge variant="success" dot>
                  {crop.area} {crop.area_unit}{crop.area > 1 ? 's' : ''}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-slate-600">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-400">Farm Parcel</span>
                  <span className="font-medium text-slate-800">{getFarmName(crop.farm_id)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-400">Sowing Date</span>
                  <span className="font-mono text-slate-700">{crop.sowing_date}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-400">Expected Harvest</span>
                  <span className="font-mono text-slate-700">
                    {crop.expected_harvest_date || 'Not specified'}
                  </span>
                </div>

                {/* Decision-Ready Crop Indicators */}
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Crop Indicators</span>
                  </div>
                  {cropIndicatorsMap[crop.id] && cropIndicatorsMap[crop.id].observation_count > 0 ? (
                    <div className="space-y-1.5 bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Growth Stage</span>
                        <span className="font-semibold text-slate-800 capitalize">
                          {cropIndicatorsMap[crop.id].latest_growth_stage.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Health Status</span>
                        <span className="font-semibold text-slate-800 capitalize">
                          {cropIndicatorsMap[crop.id].latest_health_status}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Observations</span>
                        <span className="font-mono font-medium text-slate-700">
                          {cropIndicatorsMap[crop.id].observation_count} recorded
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Last Observation</span>
                        <span className="font-mono font-medium text-slate-700">
                          {cropIndicatorsMap[crop.id].days_since_latest_observation === null
                            ? '—'
                            : cropIndicatorsMap[crop.id].days_since_latest_observation === 0
                            ? 'Today'
                            : `${cropIndicatorsMap[crop.id].days_since_latest_observation} days ago`}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 bg-slate-50 rounded-lg text-center text-xs text-slate-400 border border-dashed border-slate-200">
                      No crop observations available.
                    </div>
                  )}
                </div>

                {/* Decision-Ready Harvest Assessment */}
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Harvest Assessment</span>
                  </div>
                  {cropAssessmentsMap[crop.id] ? (
                    <div className="space-y-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
                      <div className="flex items-center justify-between gap-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] text-slate-500 font-medium">Status:</span>
                          {cropAssessmentsMap[crop.id].status === 'maturity_observed' && (
                            <Badge variant="success" dot className="text-[10px]">Maturity Observed</Badge>
                          )}
                          {cropAssessmentsMap[crop.id].status === 'approaching' && (
                            <Badge variant="warning" dot className="text-[10px]">Approaching</Badge>
                          )}
                          {cropAssessmentsMap[crop.id].status === 'not_ready' && (
                            <Badge variant="neutral" className="text-[10px]">Not Ready</Badge>
                          )}
                          {cropAssessmentsMap[crop.id].status === 'insufficient_data' && (
                            <Badge variant="neutral" className="text-[10px]">Insufficient Data</Badge>
                          )}
                        </div>
                      </div>

                      {/* Key Factors */}
                      <div className="pt-1.5 border-t border-slate-200/60 space-y-1">
                        <div className="text-[10px] font-semibold text-slate-400 uppercase">Key Factors</div>
                        {cropAssessmentsMap[crop.id].factors.map((f, idx) => (
                          <div key={idx} className="text-[11px] text-slate-600 flex items-start gap-1">
                            <span className="text-slate-400 shrink-0">•</span>
                            <span>{f.observation}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 bg-slate-50 rounded-lg text-center text-xs text-slate-400 border border-dashed border-slate-200">
                      No assessment available.
                    </div>
                  )}
                </div>

                {/* Weekly Observation Reminder Schedule */}
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      🔔 Observation Schedule
                    </span>
                    {cropRemindersMap[crop.id] && (
                      <Badge
                        variant={cropRemindersMap[crop.id].enabled ? 'success' : 'neutral'}
                        dot={cropRemindersMap[crop.id].enabled}
                        className="text-[9px] px-1.5 py-0"
                      >
                        {cropRemindersMap[crop.id].enabled ? 'Active' : 'Disabled'}
                      </Badge>
                    )}
                  </div>
                  {cropRemindersMap[crop.id] ? (
                    <div className="space-y-1.5 bg-slate-50 p-2.5 rounded-lg border border-slate-200/60 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Frequency</span>
                        <span className="font-semibold text-slate-800">
                          Every {formatWeekdayDisplay(cropRemindersMap[crop.id].weekday)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Reminder Time</span>
                        <span className="font-mono text-slate-700">
                          {formatTimeDisplay(cropRemindersMap[crop.id].reminder_time)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Next Reminder</span>
                        <span className="font-mono font-medium text-slate-700 text-[11px]">
                          {cropRemindersMap[crop.id].enabled
                            ? formatNextReminder(
                                cropRemindersMap[crop.id].weekday,
                                cropRemindersMap[crop.id].reminder_time
                              )
                            : 'Paused'}
                        </span>
                      </div>
                      <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => handleToggleReminder(crop, cropRemindersMap[crop.id])}
                          className="text-[11px] font-medium text-slate-600 hover:text-slate-900 underline"
                        >
                          {cropRemindersMap[crop.id].enabled ? 'Turn Off' : 'Turn On'}
                        </button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-[11px] px-2 py-0"
                          onClick={() => handleOpenReminderModal(crop)}
                        >
                          ⚙️ Configure
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 bg-slate-50 rounded-lg text-center text-xs border border-dashed border-slate-200 flex flex-col items-center gap-1.5">
                      <span className="text-slate-400">No reminder configured.</span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px] px-2.5 py-0 text-emerald-700 hover:text-emerald-800 border-emerald-300 hover:bg-emerald-50"
                        onClick={() => handleOpenReminderModal(crop)}
                      >
                        + Set Schedule
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="flex flex-wrap justify-between items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenObservations(crop)}
                  >
                    📋 Observations
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleOpenExplanation(crop)}
                  >
                    💡 Explanation
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => handleOpenRecommendation(crop)}
                  >
                    🎯 Recommendations
                  </Button>
                </div>
                <Button
                  variant="subtle"
                  size="sm"
                  className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                  onClick={() => setDeleteCropTarget(crop)}
                >
                  Delete
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: ADD CROP */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isAddCropOpen}
        onClose={() => !isSubmitting && setIsAddCropOpen(false)}
        title="Add Crop Planting"
        subtitle="Record a new planting cycle on one of your registered farms."
      >
        <form onSubmit={handleCreateCrop} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Farm Parcel <span className="text-rose-500">*</span>
            </label>
            {farms.length === 0 ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
                <span>No farms available. Please create a farm first.</span>
                <Button size="sm" variant="outline" onClick={() => navigate('/farms')}>
                  Create Farm
                </Button>
              </div>
            ) : (
              <select
                required
                value={cropForm.farm_id}
                onChange={(e) => setCropForm({ ...cropForm, farm_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="">Select a farm...</option>
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.name} ({formatFarmLocation(farm.location)} - {farm.area} {farm.area_unit})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Crop Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Onion"
                value={cropForm.crop_name}
                onChange={(e) => setCropForm({ ...cropForm, crop_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Variety / Cultivar <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Bhima Super"
                value={cropForm.variety}
                onChange={(e) => setCropForm({ ...cropForm, variety: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Sowing Date <span className="text-rose-500">*</span>
              </label>
              <input
                type="date"
                required
                value={cropForm.sowing_date}
                onChange={(e) => setCropForm({ ...cropForm, sowing_date: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Expected Harvest <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="date"
                min={cropForm.sowing_date || undefined}
                value={cropForm.expected_harvest_date}
                onChange={(e) => setCropForm({ ...cropForm, expected_harvest_date: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Planted Area <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="e.g. 2.0"
                value={cropForm.area}
                onChange={(e) => setCropForm({ ...cropForm, area: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Unit <span className="text-rose-500">*</span>
              </label>
              <select
                value={cropForm.area_unit}
                onChange={(e) => setCropForm({ ...cropForm, area_unit: e.target.value })}
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
              onClick={() => setIsAddCropOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isSubmitting || farms.length === 0}
            >
              {isSubmitting ? 'Saving Crop...' : 'Save Crop'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: CROP OBSERVATIONS HISTORY & ENTRY */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!activeCropForObs}
        onClose={() => !isSubmitting && setActiveCropForObs(null)}
        title={`Field Observations: ${activeCropForObs?.crop_name}`}
        subtitle={`Planted on ${getFarmName(activeCropForObs?.farm_id)} (Sown ${activeCropForObs?.sowing_date})`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-6">
          {obsErrorMessage && (
            <Alert variant="error" onDismiss={() => setObsErrorMessage(null)}>
              {obsErrorMessage}
            </Alert>
          )}

          {/* Decision-Ready Crop Indicators in Modal */}
          {activeCropForObs && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                  Crop Indicators
                </h4>
              </div>
              {cropIndicatorsMap[activeCropForObs.id] && cropIndicatorsMap[activeCropForObs.id].observation_count > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-slate-400 text-[11px] block mb-1">Growth Stage</span>
                    <div className="font-semibold text-slate-800 capitalize truncate">
                      {cropIndicatorsMap[activeCropForObs.id].latest_growth_stage.replace('_', ' ')}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-slate-400 text-[11px] block mb-1">Health Status</span>
                    <div className="font-semibold text-slate-800 capitalize truncate">
                      {cropIndicatorsMap[activeCropForObs.id].latest_health_status}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-slate-400 text-[11px] block mb-1">Total Entries</span>
                    <div className="font-semibold text-slate-800 font-mono">
                      {cropIndicatorsMap[activeCropForObs.id].observation_count}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-slate-400 text-[11px] block mb-1">Last Recorded</span>
                    <div className="font-semibold text-slate-800 font-mono">
                      {cropIndicatorsMap[activeCropForObs.id].days_since_latest_observation === null
                        ? '—'
                        : cropIndicatorsMap[activeCropForObs.id].days_since_latest_observation === 0
                        ? 'Today'
                        : `${cropIndicatorsMap[activeCropForObs.id].days_since_latest_observation}d ago`}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-slate-50 rounded-lg text-center text-xs text-slate-400 border border-dashed border-slate-200">
                  No crop observations available.
                </div>
              )}
            </div>
          )}

          {/* Decision-Ready Harvest Assessment in Modal */}
          {activeCropForObs && cropAssessmentsMap[activeCropForObs.id] && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                  Harvest Assessment
                </h4>
              </div>

              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200/60">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-600">Condition Status:</span>
                  {cropAssessmentsMap[activeCropForObs.id].status === 'maturity_observed' && (
                    <Badge variant="success" dot>Maturity Observed</Badge>
                  )}
                  {cropAssessmentsMap[activeCropForObs.id].status === 'approaching' && (
                    <Badge variant="warning" dot>Approaching Maturity</Badge>
                  )}
                  {cropAssessmentsMap[activeCropForObs.id].status === 'not_ready' && (
                    <Badge variant="neutral">Not Ready</Badge>
                  )}
                  {cropAssessmentsMap[activeCropForObs.id].status === 'insufficient_data' && (
                    <Badge variant="neutral">Insufficient Data</Badge>
                  )}
                </div>
              </div>

              <div className="space-y-1.5 pt-1">
                <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Evaluation Factors</div>
                {cropAssessmentsMap[activeCropForObs.id].factors.map((f, idx) => (
                  <div key={idx} className="p-2 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-700 flex items-start gap-2">
                    <span className="font-semibold text-slate-800 capitalize min-w-[120px] shrink-0">
                      {f.name.replace('_', ' ')}:
                    </span>
                    <span className="text-slate-600">{f.observation}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* New Observation Form */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-3">
              + Log New Field Observation
            </h4>
            <form onSubmit={handleCreateObservation} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Date <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={obsForm.observation_date}
                    onChange={(e) => setObsForm({ ...obsForm, observation_date: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Growth Stage <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={obsForm.growth_stage}
                    onChange={(e) => setObsForm({ ...obsForm, growth_stage: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {GROWTH_STAGES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Health Status <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={obsForm.health_status}
                    onChange={(e) => setObsForm({ ...obsForm, health_status: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {HEALTH_STATUSES.map((h) => (
                      <option key={h.value} value={h.value}>{h.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Field Notes / Symptoms <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. 50% neck-fall observed, uniform bulb size, dry leaf tips"
                  value={obsForm.notes}
                  onChange={(e) => setObsForm({ ...obsForm, notes: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end pt-1">
                <Button variant="primary" size="sm" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Recording...' : 'Record Observation'}
                </Button>
              </div>
            </form>
          </div>

          {/* Observation History List */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                Observation Journal ({observations.length})
              </h4>
            </div>

            {isLoadingObs && (
              <div className="p-6 text-center text-xs text-slate-400">Loading observations...</div>
            )}

            {!isLoadingObs && observations.length === 0 && (
              <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                No observations recorded yet. Enter your first field observation above.
              </div>
            )}

            {!isLoadingObs && observations.length > 0 && (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {observations.map((obs) => {
                  const healthObj = HEALTH_STATUSES.find((h) => h.value === obs.health_status) || { variant: 'neutral' };
                  return (
                    <div
                      key={obs.id}
                      className="p-3 bg-white border border-slate-200 rounded-xl flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-medium text-slate-800">{obs.observation_date}</span>
                          <span className="text-slate-300">•</span>
                          <span className="font-semibold text-slate-700 capitalize">{obs.growth_stage.replace('_', ' ')}</span>
                          <Badge variant={healthObj.variant} size="sm">{obs.health_status}</Badge>
                        </div>
                        {obs.notes && (
                          <p className="text-slate-500 text-xs">{obs.notes}</p>
                        )}
                      </div>
                      <Button
                        variant="subtle"
                        size="sm"
                        className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 shrink-0"
                        onClick={() => setDeleteObsTarget(obs)}
                      >
                        Delete
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: CONFIRM DELETE CROP */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!deleteCropTarget}
        onClose={() => !isSubmitting && setDeleteCropTarget(null)}
        title="Confirm Crop Deletion"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to delete crop planting <strong className="text-slate-900">"{deleteCropTarget?.crop_name}"</strong> on farm <em>{getFarmName(deleteCropTarget?.farm_id)}</em>?
          </p>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <strong>Warning:</strong> Deleting this crop will permanently delete all associated field observations through cascade deletion.
          </div>
          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setDeleteCropTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="button"
              disabled={isSubmitting}
              className="bg-rose-600 hover:bg-rose-700 text-white focus:ring-rose-500"
              onClick={handleConfirmDeleteCrop}
            >
              {isSubmitting ? 'Deleting...' : 'Confirm Delete'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: CONFIRM DELETE OBSERVATION */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!deleteObsTarget}
        onClose={() => !isSubmitting && setDeleteObsTarget(null)}
        title="Confirm Observation Deletion"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Delete observation from <strong className="text-slate-900">{deleteObsTarget?.observation_date}</strong> ({deleteObsTarget?.growth_stage})?
          </p>
          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setDeleteObsTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="button"
              disabled={isSubmitting}
              className="bg-rose-600 hover:bg-rose-700 text-white focus:ring-rose-500"
              onClick={handleConfirmDeleteObservation}
            >
              {isSubmitting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
      {/* ========================================================================= */}
      {/* MODAL: EXPLANATION LAYER */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!activeCropForExplanation}
        onClose={() => setActiveCropForExplanation(null)}
        title={`Farmer Explanation: ${activeCropForExplanation?.crop_name}`}
        subtitle={`Planted on ${getFarmName(activeCropForExplanation?.farm_id)} (Sown ${activeCropForExplanation?.sowing_date})`}
        maxWidth="max-w-3xl"
      >
        {isLoadingExplanation && (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-medium text-slate-600">Generating transparent farmer explanation...</p>
          </div>
        )}

        {explanationError && (
          <Alert variant="error" onDismiss={() => setExplanationError(null)}>
            {explanationError}
          </Alert>
        )}

        {explanationData && !isLoadingExplanation && (
          <div className="space-y-6">
            {/* Farmer-Friendly Summary Banner */}
            <div className="bg-emerald-50/80 border border-emerald-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
                  💡 Crop Status Summary
                </span>
              </div>
              <p className="text-sm text-emerald-950 font-medium leading-relaxed">
                {explanationData.summary}
              </p>
            </div>

            {/* Strict 4-Category Data Breakdown Grid */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                Grounded Data Foundation
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {/* 1. OBSERVED */}
                <div className="p-3.5 bg-sky-50/50 border border-sky-200/80 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="info" className="text-[10px]">1. Observed</Badge>
                    <span className="text-[10px] text-slate-400 font-medium">Recorded Facts</span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Crop Stage:</span>
                      <span className="font-semibold text-slate-800 capitalize">
                        {explanationData.observations.crop_stage?.replace('_', ' ') || 'None'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Crop Health:</span>
                      <span className="font-semibold text-slate-800 capitalize">
                        {explanationData.observations.crop_health || 'None'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Field Obs Count:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.observations.crop_observations_count} entries
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Weather Obs:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.observations.weather_observations_count} readings
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Latest Mandi Price:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.observations.latest_market_price !== null
                          ? `Rs. ${explanationData.observations.latest_market_price} / Q`
                          : 'None'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 2. CALCULATED */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="neutral" className="text-[10px]">2. Calculated</Badge>
                    <span className="text-[10px] text-slate-400 font-medium">Derived Indicators</span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Observation Age:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.calculated.days_since_latest_crop_observation !== null
                          ? `${explanationData.calculated.days_since_latest_crop_observation}d ago`
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Avg Temperature:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.calculated.average_temperature_c !== null
                          ? `${explanationData.calculated.average_temperature_c}°C`
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Total Rainfall:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.calculated.total_rainfall_mm !== null
                          ? `${explanationData.calculated.total_rainfall_mm} mm`
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Avg Humidity / Wind:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.calculated.average_humidity_percent !== null
                          ? `${explanationData.calculated.average_humidity_percent}% / ${explanationData.calculated.average_wind_speed_kmh} km/h`
                          : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Mandi Price Change:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {explanationData.calculated.market_price_change !== null
                          ? `Rs. ${explanationData.calculated.market_price_change} (${explanationData.calculated.market_price_change_percentage}%)`
                          : '—'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 3. PREDICTED */}
                <div className="p-3.5 bg-violet-50/50 border border-violet-200/80 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="info" className="text-[10px] bg-violet-100 text-violet-800 border-violet-200">3. Predicted</Badge>
                    <span className="text-[10px] text-slate-400 font-medium">Statistical Baseline</span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    {explanationData.predicted ? (
                      <>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Forecast Price:</span>
                          <span className="font-semibold text-violet-900 font-mono">
                            Rs. {explanationData.predicted.predicted_next_modal_price} / Q
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Direction:</span>
                          <span className="font-semibold text-slate-800 capitalize">
                            {explanationData.predicted.direction} ({explanationData.predicted.price_difference_from_current > 0 ? '+' : ''}{explanationData.predicted.price_difference_from_current} Rs/Q)
                          </span>
                        </div>
                        {/* ponytail: removed ML model name/version internal detail */}
                        <p className="text-[10px] text-violet-700 pt-1 border-t border-violet-100">
                          Automated statistical projection from historical mandi data.
                        </p>
                      </>
                    ) : (
                      <div className="py-2 text-slate-400 text-center">
                        No prediction available (requires mandi observations).
                      </div>
                    )}
                  </div>
                </div>

                {/* 4. ASSESSMENT */}
                <div className="p-3.5 bg-amber-50/50 border border-amber-200/80 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="warning" className="text-[10px]">4. Assessment</Badge>
                    <span className="text-[10px] text-slate-400 font-medium">Deterministic Engine</span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Harvest Readiness:</span>
                      <span className="font-semibold text-slate-800 capitalize">
                        {explanationData.assessment.harvest_status.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Harvest Data:</span>
                      <span className="font-medium text-slate-700 capitalize">
                        {explanationData.assessment.harvest_data_sufficiency}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Market Trend:</span>
                      <span className="font-semibold text-slate-800 capitalize">
                        {explanationData.assessment.market_trend_status.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Market Data:</span>
                      <span className="font-medium text-slate-700 capitalize">
                        {explanationData.assessment.market_data_sufficiency}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* In-Depth Farmer-Friendly Explanations */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Detailed Explanatory Breakdowns
              </h4>

              <div className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-1">
                <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <span>🌾 Harvest Readiness Factors</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {explanationData.decision_explanation}
                </p>
              </div>

              <div className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-1">
                <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <span>🌦️ Ambient Farm Weather Context</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {explanationData.weather_explanation}
                </p>
              </div>

              <div className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-1">
                <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <span>📈 Mandi Market Context</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {explanationData.market_explanation}
                </p>
              </div>

              {explanationData.prediction_explanation && (
                <div className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-1">
                  <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                    <span>🔮 Baseline Price Forecast Details</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {explanationData.prediction_explanation}
                  </p>
                </div>
              )}
            </div>

            {/* System Limitations & Non-Directive Guardrail */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <span>⚠️ System Boundaries & Limitations</span>
              </div>
              <ul className="space-y-1.5 text-xs text-slate-600 list-disc list-inside">
                {explanationData.limitations.map((limit, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {limit}
                  </li>
                ))}
              </ul>
              <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 italic">
                Notice: The system provides explainable evaluations based strictly on recorded field and market observations. It does not provide directive harvest or selling recommendations; all management decisions remain with the farmer.
              </div>
            </div>

            {/* Close Button */}
            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <Button
                variant="outline"
                onClick={() => setActiveCropForExplanation(null)}
              >
                Close Explanation
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: RECOMMENDATIONS */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!activeCropForRecommendation}
        onClose={() => setActiveCropForRecommendation(null)}
        title={`Harvest & Selling Decisions: ${activeCropForRecommendation?.crop_name}`}
        subtitle={`Field planting on ${getFarmName(activeCropForRecommendation?.farm_id)} (Sown ${activeCropForRecommendation?.sowing_date})`}
        maxWidth="max-w-3xl"
      >
        {isLoadingRecommendation && (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-medium text-slate-600">Evaluating transparent harvest and sell recommendations...</p>
          </div>
        )}

        {recommendationError && (
          <Alert variant="error" onDismiss={() => setRecommendationError(null)}>
            {recommendationError}
          </Alert>
        )}

        {recommendationData && !isLoadingRecommendation && (
          <div className="space-y-6">
            {/* Decoupled Principle Banner */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-600 flex items-start gap-2">
              <span className="text-emerald-700 font-bold shrink-0">ℹ️ Decoupled Decisions:</span>
              <span>
                Harvest Readiness and Selling Posture are evaluated as separate, independent decisions. A mature crop ready for harvest may be held or sold based on mandi price momentum.
              </span>
            </div>

            {/* HARVEST DECISION SECTION */}
            <div className="bg-white border border-slate-200 rounded-xl p-4.5 shadow-sm space-y-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-800">🌾 Harvest Decision</span>
                  {recommendationData.harvest_recommendation.recommendation === 'harvest_now' && (
                    <Badge variant="success" dot className="font-semibold text-xs">Harvest Now</Badge>
                  )}
                  {recommendationData.harvest_recommendation.recommendation === 'approaching_harvest' && (
                    <Badge variant="warning" dot className="font-semibold text-xs">Approaching Harvest</Badge>
                  )}
                  {recommendationData.harvest_recommendation.recommendation === 'not_ready' && (
                    <Badge variant="neutral" className="font-semibold text-xs">Not Ready</Badge>
                  )}
                  {recommendationData.harvest_recommendation.recommendation === 'insufficient_data' && (
                    <Badge variant="neutral" className="font-semibold text-xs">Insufficient Data</Badge>
                  )}
                </div>
                <div className="flex items-center gap-1.5 text-[11px]">
                  <Badge variant="info" className="px-1.5 py-0 text-[10px]">
                    Confidence: {recommendationData.harvest_recommendation.confidence}
                  </Badge>
                  <Badge variant="neutral" className="px-1.5 py-0 text-[10px]">
                    Data: {recommendationData.harvest_recommendation.data_sufficiency}
                  </Badge>
                </div>
              </div>

              {/* Reasons */}
              <div>
                <h5 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                  Why this recommendation:
                </h5>
                <ul className="space-y-1 text-xs text-slate-700 list-disc list-inside">
                  {recommendationData.harvest_recommendation.reasons.map((reason, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Supporting Factors */}
              <div className="p-3 bg-slate-50/70 border border-slate-100 rounded-lg">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Supporting Factors
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div>
                    <div className="text-[10px] text-slate-400">Observed Stage</div>
                    <div className="font-semibold text-slate-800 capitalize">
                      {recommendationData.harvest_recommendation.supporting_factors.growth_stage?.replace('_', ' ') || 'None'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Observed Health</div>
                    <div className="font-semibold text-slate-800 capitalize">
                      {recommendationData.harvest_recommendation.supporting_factors.health_status || 'None'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Calculated Recency</div>
                    <div className="font-semibold text-slate-800 font-mono">
                      {recommendationData.harvest_recommendation.supporting_factors.days_since_observation !== null
                        ? `${recommendationData.harvest_recommendation.supporting_factors.days_since_observation}d ago`
                        : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Weather Records</div>
                    <div className="font-semibold text-slate-800 font-mono">
                      {recommendationData.harvest_recommendation.supporting_factors.weather_observations_count} readings
                    </div>
                  </div>
                </div>
              </div>

              {/* Agricultural Risks */}
              {recommendationData.harvest_recommendation.risks.length > 0 && (
                <div className="p-2.5 bg-amber-50/60 border border-amber-200/70 rounded-lg text-xs">
                  <div className="font-semibold text-amber-800 text-[11px] mb-1">Harvest Risk Factors:</div>
                  <ul className="space-y-0.5 text-amber-900 list-disc list-inside">
                    {recommendationData.harvest_recommendation.risks.map((risk, idx) => (
                      <li key={idx}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* SELLING DECISION SECTION */}
            <div className="bg-white border border-slate-200 rounded-xl p-4.5 shadow-sm space-y-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-800">📈 Selling Decision</span>
                  {recommendationData.sell_recommendation.recommendation === 'sell_now' && (
                    <Badge variant="warning" dot className="font-semibold text-xs">Sell Now</Badge>
                  )}
                  {recommendationData.sell_recommendation.recommendation === 'hold_for_observation' && (
                    <Badge variant="success" dot className="font-semibold text-xs">Hold For Observation</Badge>
                  )}
                  {recommendationData.sell_recommendation.recommendation === 'price_stable' && (
                    <Badge variant="neutral" className="font-semibold text-xs">Price Stable</Badge>
                  )}
                  {recommendationData.sell_recommendation.recommendation === 'insufficient_data' && (
                    <Badge variant="neutral" className="font-semibold text-xs">Insufficient Data</Badge>
                  )}
                </div>
                <div className="flex items-center gap-1.5 text-[11px]">
                  <Badge variant="info" className="px-1.5 py-0 text-[10px]">
                    Confidence: {recommendationData.sell_recommendation.confidence}
                  </Badge>
                  <Badge variant="neutral" className="px-1.5 py-0 text-[10px]">
                    Data: {recommendationData.sell_recommendation.data_sufficiency}
                  </Badge>
                </div>
              </div>

              {/* Reasons */}
              <div>
                <h5 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                  Why this recommendation:
                </h5>
                <ul className="space-y-1 text-xs text-slate-700 list-disc list-inside">
                  {recommendationData.sell_recommendation.reasons.map((reason, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Supporting Factors */}
              <div className="p-3 bg-slate-50/70 border border-slate-100 rounded-lg">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Market Factors & Model Baseline
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div>
                    <div className="text-[10px] text-slate-400">Current Modal Price</div>
                    <div className="font-semibold text-slate-800 font-mono">
                      {recommendationData.sell_recommendation.supporting_factors.current_modal_price !== null
                        ? `Rs. ${recommendationData.sell_recommendation.supporting_factors.current_modal_price} / Q`
                        : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Calculated Change</div>
                    <div className="font-semibold text-slate-800 font-mono">
                      {recommendationData.sell_recommendation.supporting_factors.price_change !== null
                        ? `Rs. ${recommendationData.sell_recommendation.supporting_factors.price_change} (${recommendationData.sell_recommendation.supporting_factors.price_change_percentage}%)`
                        : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Assessment Trend</div>
                    <div className="font-semibold text-slate-800 capitalize">
                      {recommendationData.sell_recommendation.supporting_factors.trend_status?.replace('_', ' ') || 'None'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Predicted Price (Estimate)</div>
                    <div className="font-semibold text-violet-800 font-mono">
                      {recommendationData.sell_recommendation.supporting_factors.predicted_next_modal_price !== null
                        ? `Rs. ${recommendationData.sell_recommendation.supporting_factors.predicted_next_modal_price} / Q`
                        : 'Unavailable'}
                    </div>
                  </div>
                </div>
                <div className="text-[10px] text-slate-400 mt-2 italic">
                  Note: Predicted prices are statistical baseline model estimates from historical mandi data; they do not guarantee future market prices.
                </div>
              </div>

              {/* Commercial Risks */}
              {recommendationData.sell_recommendation.risks.length > 0 && (
                <div className="p-2.5 bg-amber-50/60 border border-amber-200/70 rounded-lg text-xs">
                  <div className="font-semibold text-amber-800 text-[11px] mb-1">Market Risk Factors:</div>
                  <ul className="space-y-0.5 text-amber-900 list-disc list-inside">
                    {recommendationData.sell_recommendation.risks.map((risk, idx) => (
                      <li key={idx}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* DATA QUALITY & TRACEABILITY */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Data Quality & Grounding
                </span>
                <span className="text-[10px] text-slate-400">
                  Generated {new Date(recommendationData.generated_at).toLocaleTimeString()}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="p-2 bg-white rounded-lg border border-slate-200/60">
                  <div className="text-[10px] text-slate-400 mb-0.5">Field Obs Freshness</div>
                  <div className="font-semibold text-slate-800 font-mono">
                    {recommendationData.data_quality.observation_freshness_days !== null
                      ? `${recommendationData.data_quality.observation_freshness_days}d ago (${recommendationData.data_quality.crop_observation_count} entries)`
                      : 'No records'}
                  </div>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200/60">
                  <div className="text-[10px] text-slate-400 mb-0.5">Weather Freshness</div>
                  <div className="font-semibold text-slate-800 font-mono">
                    {recommendationData.data_quality.weather_observation_count} records
                  </div>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200/60">
                  <div className="text-[10px] text-slate-400 mb-0.5">Market History</div>
                  <div className="font-semibold text-slate-800 font-mono">
                    {recommendationData.data_quality.market_observation_count} mandi records
                  </div>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200/60">
                  <div className="text-[10px] text-slate-400 mb-0.5">Prediction Model</div>
                  <div className="font-semibold text-slate-800">
                    {recommendationData.data_quality.prediction_available ? 'Available (Baseline)' : 'Unavailable'}
                  </div>
                </div>
              </div>

              {/* Data Grounding Categories Badges */}
              <div className="pt-2 border-t border-slate-200/60 flex flex-wrap items-center gap-1.5 text-[10px]">
                <span className="text-slate-400 font-medium">Data Traceability:</span>
                <span className="px-1.5 py-0.5 bg-sky-100 text-sky-800 rounded font-medium">Observed: Field & Mandi inputs</span>
                <span className="px-1.5 py-0.5 bg-slate-200 text-slate-800 rounded font-medium">Calculated: Recency & Change %</span>
                <span className="px-1.5 py-0.5 bg-violet-100 text-violet-800 rounded font-medium">Predicted: Baseline estimate</span>
                <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded font-medium">Assessment: Decision rules</span>
                <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded font-medium">Recommendation: Actionable advice</span>
              </div>
            </div>

            {/* Non-Directive Safety Disclaimer */}
            <div className="p-3 bg-amber-50/50 border border-amber-200/60 rounded-xl text-[11px] text-amber-900 italic">
              <strong>Notice:</strong> Recommendations are deterministic decision-support suggestions grounded in historical data and manual observations. They do not constitute financial guarantees or autonomous instructions; all final harvesting and commercial decisions remain with the farmer.
            </div>

            {/* Close Button */}
            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <Button
                variant="outline"
                onClick={() => setActiveCropForRecommendation(null)}
              >
                Close Recommendations
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: OBSERVATION REMINDER SCHEDULE */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isReminderModalOpen}
        onClose={() => !isSubmittingReminder && setIsReminderModalOpen(false)}
        title={
          activeCropForReminder
            ? `Observation Schedule: ${activeCropForReminder.crop_name}`
            : 'Observation Schedule'
        }
        subtitle="Configure a recurring weekly reminder to record crop growth stage and health."
      >
        <form onSubmit={handleSaveReminderSchedule} className="space-y-4">
          {reminderErrorMessage && (
            <Alert variant="error" onDismiss={() => setReminderErrorMessage(null)}>
              {reminderErrorMessage}
            </Alert>
          )}

          {/* Enabled Checkbox */}
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={reminderForm.enabled}
                onChange={(e) =>
                  setReminderForm({ ...reminderForm, enabled: e.target.checked })
                }
                className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
              />
              <span className="text-sm font-semibold text-slate-800">
                ☑ Every week (Enable recurring reminder)
              </span>
            </label>
            <p className="text-xs text-slate-500 mt-1 pl-6">
              When enabled, you will receive a weekly reminder to update observations for this crop.
            </p>
          </div>

          {/* Weekday Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Day of week <span className="text-rose-500">*</span>
            </label>
            <select
              disabled={!reminderForm.enabled}
              value={reminderForm.weekday}
              onChange={(e) =>
                setReminderForm({ ...reminderForm, weekday: e.target.value })
              }
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white disabled:bg-slate-100 disabled:text-slate-400"
            >
              {WEEKDAYS.map((day) => (
                <option key={day.value} value={day.value}>
                  {day.label}
                </option>
              ))}
            </select>
          </div>

          {/* Time Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Time <span className="text-rose-500">*</span>
            </label>
            <input
              type="time"
              required
              disabled={!reminderForm.enabled}
              value={reminderForm.reminder_time}
              onChange={(e) =>
                setReminderForm({ ...reminderForm, reminder_time: e.target.value })
              }
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-100 disabled:text-slate-400"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Currently set to: {formatTimeDisplay(reminderForm.reminder_time)}
            </p>
          </div>

          {/* Browser Notification Status Info */}
          <div className="p-3 bg-slate-50/80 border border-slate-200/80 rounded-lg text-xs text-slate-600 space-y-1">
            <div className="font-semibold text-slate-700">Browser Notification Support</div>
            {notificationPermissionStatus === 'granted' && (
              <div className="text-emerald-700 flex items-center gap-1.5">
                <span>✅</span>
                <span>Browser notifications are enabled. You will receive an alert on schedule.</span>
              </div>
            )}
            {notificationPermissionStatus === 'denied' && (
              <div className="text-amber-700 flex items-center gap-1.5">
                <span>⚠️</span>
                <span>
                  Browser notifications are blocked in your browser. An in-app reminder banner will be shown on the Crops page instead.
                </span>
              </div>
            )}
            {notificationPermissionStatus === 'default' && (
              <div className="text-slate-600 flex items-center gap-1.5">
                <span>🔔</span>
                <span>
                  We will request browser notification permission when you save this schedule. In-app reminders will also be shown.
                </span>
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
            {activeCropForReminder && cropRemindersMap[activeCropForReminder.id] ? (
              <Button
                variant="subtle"
                type="button"
                className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 text-xs"
                disabled={isSubmittingReminder}
                onClick={handleDeleteReminder}
              >
                Delete Schedule
              </Button>
            ) : (
              <div />
            )}

            <div className="flex gap-2">
              <Button
                variant="outline"
                type="button"
                disabled={isSubmittingReminder}
                onClick={() => setIsReminderModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                type="submit"
                disabled={isSubmittingReminder}
              >
                {isSubmittingReminder ? 'Saving...' : 'Save Schedule'}
              </Button>
            </div>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
}

export default Crops;
