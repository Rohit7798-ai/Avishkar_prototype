import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { Dashboard } from '../pages/Dashboard';
import { Farms } from '../pages/Farms';
import { Crops } from '../pages/Crops';
import { Market } from '../pages/Market';
import { Weather } from '../pages/Weather';
import { Settings } from '../pages/Settings';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="farms" element={<Farms />} />
        <Route path="crops" element={<Crops />} />
        <Route path="market" element={<Market />} />
        <Route path="weather" element={<Weather />} />
        <Route path="settings" element={<Settings />} />
        {/* Fallback wildcard to Dashboard */}
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}

export default AppRoutes;
