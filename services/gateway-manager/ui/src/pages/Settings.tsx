import { useState, useEffect } from 'react';
import { PageLayout } from '../components/layout';
import { Card, CardBody, Button } from '../components/common';
import { useBranding } from '../hooks/useBranding';
import { useBrandingConfig, type BrandingConfig } from '../hooks/useBrandingConfig';

type TabType = 'branding' | 'gateway' | 'integrations';

export const Settings = () => {
  const branding = useBranding();
  const [activeTab, setActiveTab] = useState<TabType>('branding');
  const { getBranding, updateBranding } = useBrandingConfig();

  // Form state for branding config
  const [brandingConfig, setBrandingConfig] = useState<BrandingConfig | null>(null);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Load branding config on mount
  useEffect(() => {
    const loadBranding = async () => {
      const config = await getBranding();
      if (config) {
        setBrandingConfig(config);
      }
    };
    loadBranding();
  }, []);

  // Handle input changes
  const handleInputChange = (field: string, value: string) => {
    if (!brandingConfig) return;

    setBrandingConfig({
      ...brandingConfig,
      [field]: value,
    });
  };

  // Handle color changes
  const handleColorChange = (colorKey: string, value: string) => {
    if (!brandingConfig) return;

    setBrandingConfig({
      ...brandingConfig,
      colors: {
        ...brandingConfig.colors,
        [colorKey]: value,
      },
    });
  };

  // Handle terminology changes
  const handleTerminologyChange = (termKey: string, value: string) => {
    if (!brandingConfig) return;

    setBrandingConfig({
      ...brandingConfig,
      terminology: {
        ...brandingConfig.terminology,
        [termKey]: value,
      },
    });
  };

  // Handle save
  const handleSave = async () => {
    if (!brandingConfig) return;

    setIsSaving(true);
    setSaveMessage(null);

    const result = await updateBranding(brandingConfig);

    if (result.success) {
      setSaveMessage({
        type: 'success',
        text: result.message || 'Branding updated successfully! Please refresh the page to see changes.'
      });
      // Optionally reload the page after a delay
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } else {
      setSaveMessage({
        type: 'error',
        text: result.message || 'Failed to update branding'
      });
    }

    setIsSaving(false);
  };

  // Handle reset
  const handleReset = async () => {
    const config = await getBranding();
    if (config) {
      setBrandingConfig(config);
      setSaveMessage(null);
    }
  };

  const tabs = [
    { id: 'branding' as TabType, name: 'Branding' },
    { id: 'gateway' as TabType, name: branding.terminology.gateway },
    { id: 'integrations' as TabType, name: 'Integrations' },
  ];

  return (
    <PageLayout title="Settings">
      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Branding Tab */}
      {activeTab === 'branding' && (
        <Card>
          <CardBody className="space-y-6">
            {/* Info message */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> Changes to branding may require a page refresh to take full effect.
                Logo uploads are not yet supported - please update the logoUrl field manually.
              </p>
            </div>

            {/* Success/Error message */}
            {saveMessage && (
              <div className={`rounded-lg p-4 ${
                saveMessage.type === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-800'
                  : 'bg-red-50 border border-red-200 text-red-800'
              }`}>
                <p className="text-sm">{saveMessage.text}</p>
              </div>
            )}

            {!brandingConfig ? (
              <p className="text-sm text-gray-500">Loading branding configuration...</p>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={brandingConfig.companyName}
                    onChange={(e) => handleInputChange('companyName', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Product Name
                  </label>
                  <input
                    type="text"
                    value={brandingConfig.productName}
                    onChange={(e) => handleInputChange('productName', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Logo URL
                  </label>
                  <input
                    type="text"
                    value={brandingConfig.logoUrl}
                    onChange={(e) => handleInputChange('logoUrl', e.target.value)}
                    placeholder="/assets/logo.png"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Favicon URL
                  </label>
                  <input
                    type="text"
                    value={brandingConfig.faviconUrl}
                    onChange={(e) => handleInputChange('faviconUrl', e.target.value)}
                    placeholder="/assets/favicon.ico"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Color Theme
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(brandingConfig.colors).map(([key, value]) => (
                      <div key={key}>
                        <label className="block text-xs text-gray-600 mb-1 capitalize">
                          {key.replace(/([A-Z])/g, ' $1').trim()}
                        </label>
                        <div className="flex items-center space-x-2">
                          <input
                            type="color"
                            value={value}
                            onChange={(e) => handleColorChange(key, e.target.value)}
                            className="h-10 w-20 border border-gray-300 rounded cursor-pointer"
                          />
                          <input
                            type="text"
                            value={value}
                            onChange={(e) => handleColorChange(key, e.target.value)}
                            pattern="^#[0-9A-Fa-f]{6}$"
                            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Preview
                  </label>
                  <div className="p-4 border border-gray-200 rounded-lg space-y-3">
                    <div className="flex space-x-2">
                      <Button size="sm">Primary Button</Button>
                      <Button variant="secondary" size="sm">
                        Secondary Button
                      </Button>
                      <Button variant="danger" size="sm">
                        Danger Button
                      </Button>
                    </div>
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                      ⚠️ Warning message with accent color
                    </div>
                    <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                      ❌ Error message with danger color
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Terminology
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(brandingConfig.terminology).map(([key, value]) => (
                      <div key={key}>
                        <label className="block text-xs text-gray-600 mb-1 capitalize">
                          {key.replace(/([A-Z])/g, ' $1').trim()}
                        </label>
                        <input
                          type="text"
                          value={value}
                          onChange={(e) => handleTerminologyChange(key, e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end space-x-3">
                  <Button variant="secondary" onClick={handleReset} disabled={isSaving}>
                    Reset to Current
                  </Button>
                  <Button onClick={handleSave} disabled={isSaving}>
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </>
            )}
          </CardBody>
        </Card>
      )}

      {/* Gateway Tab */}
      {activeTab === 'gateway' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Gateway configuration is managed via Kubernetes resources.
              The information below is for reference only.
            </p>
          </div>

          {/* Supported Gateways */}
          <Card>
            <CardBody>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Supported API Gateways
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="border-2 border-green-500 rounded-lg p-4 bg-green-50">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-900">KrakenD</h4>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      ✓ Active
                    </span>
                  </div>
                  <p className="text-xs text-gray-600">
                    High-performance API Gateway with stateless architecture
                  </p>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-500">Kong</h4>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      Planned
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    Plugin-based gateway with extensive ecosystem
                  </p>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-500">Apigee</h4>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      Planned
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    Google Cloud's full lifecycle API management
                  </p>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-500">NGINX</h4>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      Planned
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    Lightweight reverse proxy and load balancer
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* KrakenD Configuration */}
          <Card>
            <CardBody>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  KrakenD Configuration
                </h3>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  ✓ Running
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Namespace
                  </label>
                  <code className="block px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                    default
                  </code>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Deployment Name
                  </label>
                  <code className="block px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                    krakend
                  </code>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    ConfigMap
                  </label>
                  <code className="block px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                    krakend-config
                  </code>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Metrics Endpoint
                  </label>
                  <div className="flex items-center space-x-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                      http://krakend.default.svc.cluster.local:9091/metrics
                    </code>
                    <a
                      href="http://krakend.default.svc.cluster.local:9091/metrics"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-hover text-sm font-medium"
                    >
                      View ↗
                    </a>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Health Check
                  </label>
                  <div className="flex items-center space-x-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                      http://krakend.default.svc.cluster.local:8080/__health
                    </code>
                    <a
                      href="http://krakend.default.svc.cluster.local:8080/__health"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-hover text-sm font-medium"
                    >
                      Check ↗
                    </a>
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Integration settings are configured via Kubernetes Secrets.
              The information below is for reference only.
            </p>
          </div>

          <Card>
            <CardBody>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {branding.terminology.orchestrator} (Apache Airflow)
                  </h3>
                  <p className="text-sm text-gray-600">
                    Workflow discovery and DAG synchronization
                  </p>
                </div>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  ✓ Active
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    API Endpoint
                  </label>
                  <div className="flex items-center space-x-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                      http://airflow-api-server.airflow.svc.cluster.local:8080
                    </code>
                    <a
                      href="http://airflow-api-server.airflow.svc.cluster.local:8080/api/v2/ui"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-hover text-sm font-medium"
                    >
                      API Docs ↗
                    </a>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Web UI (External)
                  </label>
                  <div className="flex items-center space-x-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                      http://34.170.165.185:8080
                    </code>
                    <a
                      href="http://34.170.165.185:8080"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-hover text-sm font-medium"
                    >
                      Open ↗
                    </a>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Authentication
                  </label>
                  <p className="text-sm text-gray-700">
                    JWT Token (configured via <code className="bg-gray-100 px-1 rounded">airflow-credentials</code> Secret)
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Configuration
                  </label>
                  <p className="text-sm text-gray-700">
                    Kubernetes Secret: <code className="bg-gray-100 px-1 rounded">airflow-credentials</code> in namespace <code className="bg-gray-100 px-1 rounded">es-core-gw</code>
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Langflow
                  </h3>
                  <p className="text-sm text-gray-600">
                    LLM workflow platform integration (future enhancement)
                  </p>
                </div>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-600">
                  Not Configured
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Typical API Endpoint
                  </label>
                  <code className="block px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                    http://langflow.default.svc.cluster.local:7860
                  </code>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Status
                  </label>
                  <p className="text-sm text-gray-700">
                    Integration not yet implemented. Contact your administrator for details.
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </PageLayout>
  );
};
