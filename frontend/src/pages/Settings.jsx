import React from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';

export function Settings() {
  return (
    <PageContainer
      title="Settings"
      subtitle="Application configuration, language localization, and system preferences"
    >
      <div className="space-y-6">
        <EmptyState
          icon="⚙️"
          title="Settings & Preferences"
          description="Customization options including UI language (Marathi, Hindi, English), default regional mandis, and notification preferences."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Language & Localization</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-500 space-y-1">
              <div>• Marathi (मराठी)</div>
              <div>• Hindi (हिंदी)</div>
              <div>• English</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Notifications & Alerts</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-slate-500 space-y-1">
              <div>• Weekly Observation Reminders</div>
              <div>• Severe Weather Alerts</div>
              <div>• APMC Price Movement Alerts</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}

export default Settings;
