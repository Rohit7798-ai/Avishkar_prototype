import React, { useState, useEffect, useCallback } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Alert } from '../components/ui/Alert';
import { Modal } from '../components/ui/Modal';
import { marketObservationService } from '../services/marketObservationService';
import { indicatorService } from '../services/indicatorService';
import { decisionService } from '../services/decisionService';
import { syncService } from '../services/syncService';

export function Market() {
  const [observations, setObservations] = useState([]);
  const [marketIndicators, setMarketIndicators] = useState(null);
  const [marketAssessment, setMarketAssessment] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Modal & form states
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSyncingMarket, setIsSyncingMarket] = useState(false);

  // Filter state
  const [commodityFilter, setCommodityFilter] = useState('');

  // New Market Observation form state
  const [form, setForm] = useState({
    crop_name: 'Onion',
    market_name: 'Lasalgaon APMC',
    observed_date: new Date().toISOString().split('T')[0],
    price: '',
    unit: 'Rs/Quintal',
  });

  const loadObservations = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const params = commodityFilter.trim() ? { crop_name: commodityFilter.trim() } : {};
      const [data, indicators, assessment] = await Promise.all([
        marketObservationService.getMarketObservations(params),
        indicatorService.getMarketIndicators(params).catch(() => null),
        decisionService.getMarketDecisionAssessment(params).catch(() => null),
      ]);
      setObservations(data);
      setMarketIndicators(indicators);
      setMarketAssessment(assessment);
    } catch (err) {
      setErrorMessage(err.message || 'Unable to load market observations.');
    } finally {
      setIsLoading(false);
    }
  }, [commodityFilter]);

  useEffect(() => {
    loadObservations();
  }, [loadObservations]);

  const handleOpenAdd = () => {
    setForm({
      crop_name: 'Onion',
      market_name: 'Lasalgaon APMC',
      observed_date: new Date().toISOString().split('T')[0],
      price: '',
      unit: 'Rs/Quintal',
    });
    setErrorMessage(null);
    setIsAddModalOpen(true);
  };

  const handleCreate = async (e) => {
    e.preventDefault();

    if (!form.crop_name.trim()) {
      setErrorMessage('Commodity / crop name is required.');
      return;
    }
    if (!form.market_name.trim()) {
      setErrorMessage('Market name is required.');
      return;
    }
    const numericPrice = parseFloat(form.price);
    if (isNaN(numericPrice) || numericPrice <= 0) {
      setErrorMessage('Observed price must be a strictly positive number.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await marketObservationService.createMarketObservation({
        crop_name: form.crop_name.trim(),
        market_name: form.market_name.trim(),
        observed_date: form.observed_date,
        price: numericPrice,
        unit: form.unit.trim() || 'Rs/Quintal',
      });
      setIsAddModalOpen(false);
      setSuccessMessage(`Market rate for ${form.crop_name} at ${form.market_name} recorded.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      await loadObservations();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to record market observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await marketObservationService.deleteMarketObservation(deleteTarget.id);
      setSuccessMessage(`Market observation #${deleteTarget.id} deleted.`);
      setDeleteTarget(null);
      setTimeout(() => setSuccessMessage(null), 4000);
      await loadObservations();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete market observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSyncMarket = async () => {
    setIsSyncingMarket(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const targetCrop = commodityFilter.trim() || 'Onion';
      const res = await syncService.syncMarketData({
        crop_name: targetCrop,
      });
      setSuccessMessage(
        `Market sync complete from ${res.provider}: ${res.records_received} received, ${res.records_accepted} accepted, ${res.records_rejected} rejected.`
      );
      setTimeout(() => setSuccessMessage(null), 5000);
      await loadObservations();
    } catch (err) {
      setErrorMessage(err.message || 'Market synchronization failed.');
    } finally {
      setIsSyncingMarket(false);
    }
  };

  return (
    <PageContainer
      title="Market"
      subtitle="Track recorded APMC mandi price quotes and trading observations"
      action={
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            disabled={isSyncingMarket}
            onClick={handleSyncMarket}
          >
            {isSyncingMarket ? '⚡ Syncing Mandi...' : '⚡ Sync Market Data'}
          </Button>
          <Button variant="primary" onClick={handleOpenAdd}>
            + Record Mandi Rate
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

      {/* Filter Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-slate-200 rounded-xl p-4 mb-6 shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Filter Commodity:
          </span>
          <input
            type="text"
            placeholder="e.g. Onion"
            value={commodityFilter}
            onChange={(e) => setCommodityFilter(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500 w-44"
          />
          {commodityFilter && (
            <button
              onClick={() => setCommodityFilter('')}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Clear
            </button>
          )}
        </div>
        <div className="text-xs text-slate-500">
          Showing <strong>{observations.length}</strong> recorded observation{observations.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Mandi Market Indicators */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div>
              <CardTitle className="text-sm font-semibold text-slate-800">Mandi Market Indicators</CardTitle>
              <CardDescription className="text-xs">
                Deterministic price metrics for {commodityFilter ? commodityFilter : 'All Commodities'}
              </CardDescription>
            </div>
            {marketIndicators && marketIndicators.observation_count > 0 && (
              <Badge variant="neutral" className="text-xs">
                {marketIndicators.observation_count} observation{marketIndicators.observation_count !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {marketIndicators && marketIndicators.observation_count > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Latest Price</span>
                <div className="text-base font-bold text-slate-800">
                  Rs. {marketIndicators.latest_price?.toLocaleString()}
                </div>
                <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                  {marketIndicators.latest_observation_date || 'Recent'}
                </div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Average Price</span>
                <div className="text-base font-bold text-slate-800">
                  Rs. {marketIndicators.average_price?.toLocaleString()}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Weighted avg</div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Minimum Price</span>
                <div className="text-base font-bold text-slate-800">
                  Rs. {marketIndicators.lowest_price?.toLocaleString()}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Recorded low</div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Maximum Price</span>
                <div className="text-base font-bold text-slate-800">
                  Rs. {marketIndicators.highest_price?.toLocaleString()}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Recorded high</div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Price Change</span>
                <div className="text-base font-bold text-slate-800">
                  {marketIndicators.price_change === null
                    ? '—'
                    : marketIndicators.price_change >= 0
                    ? `+Rs. ${marketIndicators.price_change}`
                    : `-Rs. ${Math.abs(marketIndicators.price_change)}`}
                </div>
                <div className="text-[10px] text-slate-400 font-medium mt-0.5">
                  {marketIndicators.price_change_percentage !== null
                    ? `${marketIndicators.price_change_percentage >= 0 ? '+' : ''}${marketIndicators.price_change_percentage}%`
                    : '1 observation'}
                </div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl">
                <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Observations</span>
                <div className="text-base font-bold text-slate-800 font-mono">
                  {marketIndicators.observation_count}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">Total records</div>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-slate-50 rounded-lg text-center text-xs text-slate-400 border border-dashed border-slate-200">
              No market observations available.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Market Decision Assessment */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div>
              <CardTitle className="text-sm font-semibold text-slate-800">Market Assessment</CardTitle>
              <CardDescription className="text-xs">
                Empirical price trend evaluation for {commodityFilter ? commodityFilter : 'All Commodities'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {marketAssessment ? (
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200/60">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-600">Price Trend Status:</span>
                  {marketAssessment.status === 'price_rising' && (
                    <Badge variant="success" dot className="text-xs">Price Rising (&gt; +2.0%)</Badge>
                  )}
                  {marketAssessment.status === 'price_falling' && (
                    <Badge variant="warning" dot className="text-xs">Price Falling (&lt; -2.0%)</Badge>
                  )}
                  {marketAssessment.status === 'price_stable' && (
                    <Badge variant="info" dot className="text-xs">Price Stable (within ±2.0%)</Badge>
                  )}
                  {marketAssessment.status === 'insufficient_data' && (
                    <Badge variant="neutral" className="text-xs">Insufficient Data</Badge>
                  )}
                </div>
              </div>

              <div className="space-y-1.5 pt-1">
                <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Evaluation Factors</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {marketAssessment.factors.map((f, idx) => (
                    <div key={idx} className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-700 flex items-start gap-2">
                      <span className="font-semibold text-slate-800 capitalize min-w-[110px] shrink-0">
                        {f.name.replace('_', ' ')}:
                      </span>
                      <span className="text-slate-600">{f.observation}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-slate-50 rounded-lg text-center text-xs text-slate-400 border border-dashed border-slate-200">
              No market assessment available.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border border-slate-200">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p className="text-sm text-slate-500 font-medium">Loading market observations...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && observations.length === 0 && (
        <EmptyState
          icon="📊"
          title="No market observations recorded yet."
          description="Record empirical modal prices from local APMC mandis (e.g. Lasalgaon, Pimpalgaon, Nashik) to monitor market trends."
          action={
            <Button variant="primary" onClick={handleOpenAdd}>
              + Record First Mandi Rate
            </Button>
          }
        />
      )}

      {/* Observations Grid / Table */}
      {!isLoading && observations.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {observations.map((obs) => (
            <Card key={obs.id} className="flex flex-col justify-between">
              <CardHeader>
                <div>
                  <CardTitle>{obs.crop_name}</CardTitle>
                  <CardDescription>{obs.market_name}</CardDescription>
                </div>
                <Badge variant="success">
                  ₹{obs.price.toLocaleString()} / {obs.unit.replace('Rs/', '')}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-slate-600">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-400">Observed Date</span>
                  <span className="font-mono text-slate-800">{obs.observed_date}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-400">Rate Unit</span>
                  <span className="text-slate-700">{obs.unit}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Logged On</span>
                  <span className="text-slate-500">{new Date(obs.created_at).toLocaleDateString()}</span>
                </div>
              </CardContent>
              <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400">Rate #{obs.id}</span>
                <Button
                  variant="subtle"
                  size="sm"
                  className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                  onClick={() => setDeleteTarget(obs)}
                >
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: RECORD MARKET OBSERVATION */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => !isSubmitting && setIsAddModalOpen(false)}
        title="Record Mandi Market Rate"
        subtitle="Log an empirical modal price quote for a commodity at a local APMC yard."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Commodity / Crop <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Onion"
                value={form.crop_name}
                onChange={(e) => setForm({ ...form, crop_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                APMC Market Yard <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Lasalgaon APMC"
                value={form.market_name}
                onChange={(e) => setForm({ ...form, market_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Quote Date <span className="text-rose-500">*</span>
              </label>
              <input
                type="date"
                required
                value={form.observed_date}
                onChange={(e) => setForm({ ...form, observed_date: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Price <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="e.g. 1950"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Unit <span className="text-rose-500">*</span>
              </label>
              <select
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="Rs/Quintal">Rs/Quintal</option>
                <option value="Rs/kg">Rs/kg</option>
                <option value="Rs/tonne">Rs/tonne</option>
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isSubmitting}
              onClick={() => setIsAddModalOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Recording...' : 'Record Rate'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL: CONFIRM DELETE */}
      {/* ========================================================================= */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => !isSubmitting && setDeleteTarget(null)}
        title="Confirm Observation Deletion"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            Are you sure you want to delete rate quote for <strong className="text-slate-900">{deleteTarget?.crop_name}</strong> at <strong className="text-slate-900">{deleteTarget?.market_name}</strong> (₹{deleteTarget?.price} on {deleteTarget?.observed_date})?
          </p>
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
              onClick={handleConfirmDelete}
            >
              {isSubmitting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
}

export default Market;
