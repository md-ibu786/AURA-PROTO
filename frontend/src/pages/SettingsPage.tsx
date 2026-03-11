// SettingsPage.tsx
// Admin-only page for provider configuration, default models, and API key management

// Renders a settings interface with card-style layout matching AURA-CHAT styling.
// Features three sections: Provider Configuration, Default Models, and API Credentials.
// Each section is wrapped in a card container with responsive padding and icons.

// @see: features/settings/components/ - ProviderSettingsSection, DefaultModelSection, ApiKeyManager
// @note: Includes back navigation button (AURA-NOTES-MANAGER specific feature)

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Shield, Cpu, Key } from 'lucide-react';
import { ProviderSettingsSection } from '../features/settings/components/ProviderSettingsSection';
import { DefaultModelSection } from '../features/settings/components/DefaultModelSection';
import { ApiKeyManager } from '../features/settings/components/ApiKeyManager';
import '../styles/index.css';

export function SettingsPage() {
    const navigate = useNavigate();

    return (
        <div className="flex flex-col h-full bg-[#0A0A0A]">
            {/* Header */}
            <header className="px-4 md:px-6 py-3 md:py-4 border-b border-border">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => navigate(-1)}
                        className="p-2 hover:bg-white/10 rounded-full transition-colors -ml-2"
                        title="Back"
                    >
                        <ArrowLeft className="w-5 h-5 text-muted-foreground" />
                    </button>
                    <div>
                        <h1 className="text-xl font-semibold text-white">Settings</h1>
                        <p className="text-sm text-muted-foreground">
                            Configure AI providers, default models, and API credentials
                        </p>
                    </div>
                </div>
            </header>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <div className="max-w-4xl mx-auto space-y-6">
                    {/* Provider Configuration */}
                    <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                        <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2 mb-4">
                            <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                            Provider Configuration
                        </h2>
                        <ProviderSettingsSection />
                    </section>

                    {/* Default Models */}
                    <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                        <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2 mb-4">
                            <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                            Default Models
                        </h2>
                        <DefaultModelSection />
                    </section>

                    {/* API Credentials */}
                    <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                        <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2 mb-4">
                            <Key className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                            API Credentials
                        </h2>
                        <ApiKeyManager />
                    </section>
                </div>
            </div>
        </div>
    );
}
