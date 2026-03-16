import { useState, useEffect } from "react";
import {
  Play,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Activity,
} from "lucide-react";
import { assetsAPI, scanningAPI } from "../services/api";

const SCAN_TYPES = [
  { value: "all", label: "All Passive Scans", color: "primary", passive: true },
  { value: "dns", label: "DNS Records", color: "info", passive: true },
  { value: "whois", label: "WHOIS Lookup", color: "success", passive: true },
  {
    value: "subdomain",
    label: "Subdomain Enumeration",
    color: "warning",
    passive: true,
  },
  {
    value: "cert_trans",
    label: "Certificate Transparency",
    color: "info",
    passive: true,
  },
  { value: "asn", label: "ASN Lookup", color: "primary", passive: true },
  { value: "ip", label: "IP Information", color: "primary", passive: true },
  { value: "tech", label: "Technology Stack", color: "info", passive: true },
  {
    value: "port",
    label: "⚠️ Port Scan (Active)",
    color: "danger",
    passive: false,
  },
  {
    value: "ssl",
    label: "⚠️ SSL/TLS Probe (Active)",
    color: "danger",
    passive: false,
  },
];

function Scanning() {
  const [assets, setAssets] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState("");
  const [selectedScanType, setSelectedScanType] = useState("dns");
  const [scanJobs, setScanJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    loadAssets();
  }, []);

  useEffect(() => {
    if (selectedAsset) {
      loadScanJobs();
      const interval = setInterval(loadScanJobs, 5000); // Poll every 5 seconds
      return () => clearInterval(interval);
    }
  }, [selectedAsset]);

  const loadAssets = async () => {
    try {
      const data = await assetsAPI.list({ status: "active", page_size: 100 });
      setAssets(data.data || []);
      if (data.data && data.data.length > 0) {
        setSelectedAsset(data.data[0].id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const loadScanJobs = async () => {
    if (!selectedAsset) return;
    try {
      setLoading(true);
      const data = await scanningAPI.listJobs(selectedAsset, {
        page: 1,
        page_size: 20,
      });
      setScanJobs(data.data || []);
    } catch (err) {
      console.error("Failed to load scan jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartScan = async () => {
    if (!selectedAsset || !selectedScanType) return;

    const scanType = SCAN_TYPES.find((t) => t.value === selectedScanType);
    if (!scanType.passive) {
      const confirmed = window.confirm(
        "⚠️ WARNING: You are about to start an ACTIVE scan.\n\n" +
          "Active scans directly probe target systems and may be illegal without authorization.\n\n" +
          "Only proceed if you own the target or have written permission.\n\n" +
          "Continue?",
      );
      if (!confirmed) return;
    }

    try {
      setScanning(true);
      setError("");
      setSuccess("");
      await scanningAPI.startScan(selectedAsset, selectedScanType);
      setSuccess(`Scan started successfully! Refreshing...`);
      setTimeout(() => {
        loadScanJobs();
        setSuccess("");
      }, 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setScanning(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "pending":
        return <Clock size={16} className="status-pending" />;
      case "running":
        return <RefreshCw size={16} className="status-running" />;
      case "completed":
        return <CheckCircle size={16} className="status-completed" />;
      case "failed":
        return <XCircle size={16} className="status-failed" />;
      case "partial":
        return <AlertCircle size={16} className="status-warning" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: "badge-warning",
      running: "badge-info",
      completed: "badge-success",
      failed: "badge-danger",
      partial: "badge-warning",
    };
    return badges[status] || "badge-secondary";
  };

  const selectedAssetData = assets.find((a) => a.id === selectedAsset);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Scanning Operations</h1>
        <p className="page-description">
          Execute reconnaissance scans on your assets
        </p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {success && <div className="alert alert-success mb-4">{success}</div>}

      <div className="grid grid-2">
        {/* Scan Configuration */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Start New Scan</h3>
          </div>

          {assets.length === 0 ? (
            <div className="empty-state">
              <p className="text-muted">
                No active assets found. Please add assets first.
              </p>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Select Asset</label>
                <select
                  className="form-select"
                  value={selectedAsset}
                  onChange={(e) => setSelectedAsset(e.target.value)}
                >
                  {assets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.name} ({asset.type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Scan Type</label>
                <select
                  className="form-select"
                  value={selectedScanType}
                  onChange={(e) => setSelectedScanType(e.target.value)}
                >
                  {SCAN_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label} {type.passive ? "🟢" : "🔴"}
                    </option>
                  ))}
                </select>
              </div>

              {selectedScanType &&
                !SCAN_TYPES.find((t) => t.value === selectedScanType)
                  ?.passive && (
                  <div className="alert alert-warning mb-4">
                    <strong>⚠️ Active Scan Warning:</strong> This scan type
                    directly probes the target and requires explicit
                    authorization. Only proceed if you own the target or have
                    written permission.
                  </div>
                )}

              <button
                className="btn btn-primary w-full"
                onClick={handleStartScan}
                disabled={scanning || !selectedAsset}
              >
                {scanning ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    Start Scan
                  </>
                )}
              </button>

              {selectedAssetData && (
                <div className="mt-4 p-4 bg-gray-50 rounded-md">
                  <h4 className="font-semibold text-sm mb-2">
                    Target Details:
                  </h4>
                  <div className="text-sm text-muted space-y-1">
                    <p>
                      <strong>Name:</strong> {selectedAssetData.name}
                    </p>
                    <p>
                      <strong>Type:</strong> {selectedAssetData.type}
                    </p>
                    <p>
                      <strong>Status:</strong> {selectedAssetData.status}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Scan Types Info */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Available Scan Types</h3>
          </div>

          <div className="space-y-3">
            <div>
              <h4 className="font-semibold text-sm mb-2">
                🟢 Passive Scans (Safe)
              </h4>
              <ul
                className="text-sm text-muted space-y-1"
                style={{ listStyle: "disc", paddingLeft: "1.5rem" }}
              >
                <li>
                  <strong>All:</strong> Run all passive scans
                </li>
                <li>
                  <strong>DNS:</strong> Query public DNS records
                </li>
                <li>
                  <strong>WHOIS:</strong> Lookup domain registration
                </li>
                <li>
                  <strong>Subdomain:</strong> Enumerate subdomains
                </li>
                <li>
                  <strong>Cert Trans:</strong> Certificate Transparency logs
                </li>
                <li>
                  <strong>ASN:</strong> Autonomous System lookup
                </li>
              </ul>
            </div>

            <div className="pt-3 border-t">
              <h4 className="font-semibold text-sm mb-2">
                🔴 Active Scans (Requires Permission)
              </h4>
              <ul
                className="text-sm text-muted space-y-1"
                style={{ listStyle: "disc", paddingLeft: "1.5rem" }}
              >
                <li>
                  <strong>Port:</strong> TCP/UDP port scanning
                </li>
                <li>
                  <strong>SSL:</strong> SSL/TLS certificate probing
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Scan Jobs */}
      <div className="card mt-4">
        <div className="card-header flex items-center justify-between">
          <h3 className="card-title">Recent Scan Jobs</h3>
          {selectedAsset && (
            <button
              className="btn btn-sm btn-secondary"
              onClick={loadScanJobs}
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          )}
        </div>

        {loading && scanJobs.length === 0 ? (
          <div className="loading">
            <div className="spinner"></div>
            <span>Loading scan jobs...</span>
          </div>
        ) : scanJobs.length === 0 ? (
          <div className="empty-state">
            <Activity className="empty-state-icon" size={64} />
            <h3 className="empty-state-title">No scans yet</h3>
            <p className="empty-state-description">
              Start your first scan to see results here
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Scan Type</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Results</th>
                </tr>
              </thead>
              <tbody>
                {scanJobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(job.status)}
                        <span className="font-medium">{job.scan_type}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadge(job.status)}`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="text-sm text-muted">
                      {new Date(job.started_at).toLocaleString()}
                    </td>
                    <td className="text-sm text-muted">
                      {job.ended_at
                        ? `${Math.round(
                            (new Date(job.ended_at) -
                              new Date(job.started_at)) /
                              1000,
                          )}s`
                        : "-"}
                    </td>
                    <td>
                      <span className="font-semibold">{job.results}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Scanning;
