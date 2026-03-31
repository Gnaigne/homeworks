import { useState, useEffect, useRef } from "react";
import {
  FileText,
  Globe,
  Server,
  Search,
  ChevronLeft,
  ChevronRight,
  Shield,
  Cpu,
  Network,
  Award,
} from "lucide-react";
import { assetsAPI, resultsAPI } from "../services/api";

function Results() {
  const [assets, setAssets] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState("");
  const [resultType, setResultType] = useState("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // State cho mỗi loại result
  const [whoisData, setWhoisData] = useState(null);
  const [dnsData, setDnsData] = useState([]);
  const [subdomainData, setSubdomainData] = useState([]);
  const [ipData, setIpData] = useState([]);
  const [sslData, setSslData] = useState([]);
  const [techData, setTechData] = useState([]);
  const [certTransData, setCertTransData] = useState([]);
  const [portData, setPortData] = useState([]);

  // Pagination state
  const [dnsPage, setDnsPage] = useState(1);
  const [subdomainPage, setSubdomainPage] = useState(1);
  const [certTransPage, setCertTransPage] = useState(1);
  const [portPage, setPortPage] = useState(1);

  // Filter state
  const [dnsSearch, setDnsSearch] = useState("");
  const [dnsTypeFilter, setDnsTypeFilter] = useState("");
  const [subdomainSearch, setSubdomainSearch] = useState("");
  const [subdomainActiveFilter, setSubdomainActiveFilter] = useState("");

  // Pagination metadata
  const [dnsPagination, setDnsPagination] = useState({});
  const [subdomainPagination, setSubdomainPagination] = useState({});
  const [certTransPagination, setCertTransPagination] = useState({});
  const [portPagination, setPortPagination] = useState({});

  const pageSize = 10;
  const isChangingAsset = useRef(false);

  useEffect(() => {
    loadAssets();
  }, []);

  useEffect(() => {
    if (selectedAsset) {
      isChangingAsset.current = true;
      setDnsPage(1); setSubdomainPage(1); setCertTransPage(1); setPortPage(1);
      setDnsSearch(""); setDnsTypeFilter("");
      setSubdomainSearch(""); setSubdomainActiveFilter("");

      if (resultType === "all") {
        loadAllResults(selectedAsset).finally(() => {
          setTimeout(() => { isChangingAsset.current = false; }, 100);
        });
      } else {
        loadSingleTypeResults().finally(() => {
          setTimeout(() => { isChangingAsset.current = false; }, 100);
        });
      }
    }
  }, [selectedAsset, resultType]);

  useEffect(() => {
    if (isChangingAsset.current) return;
    if (!selectedAsset || resultType !== "all") return;
    loadDNSResults();
  }, [dnsPage, dnsSearch, dnsTypeFilter]);

  useEffect(() => {
    if (isChangingAsset.current) return;
    if (!selectedAsset || resultType !== "all") return;
    loadSubdomainResults();
  }, [subdomainPage, subdomainSearch, subdomainActiveFilter]);

  useEffect(() => {
    if (selectedAsset && resultType === "dns") loadDNSResults();
  }, [selectedAsset, resultType, dnsPage, dnsSearch, dnsTypeFilter]);

  useEffect(() => {
    if (selectedAsset && resultType === "subdomains") loadSubdomainResults();
  }, [selectedAsset, resultType, subdomainPage, subdomainSearch, subdomainActiveFilter]);

  useEffect(() => {
    if (selectedAsset && resultType === "whois") loadWhoisResults();
  }, [selectedAsset, resultType]);

  useEffect(() => {
    if (selectedAsset && resultType === "cert_trans") loadCertTransResults();
  }, [selectedAsset, resultType, certTransPage]);

  useEffect(() => {
    if (selectedAsset && resultType === "port") loadPortResults();
  }, [selectedAsset, resultType, portPage]);

  const loadAssets = async () => {
    try {
      const data = await assetsAPI.list({ page_size: 100 });
      setAssets(data.data || []);
      if (data.data && data.data.length > 0) setSelectedAsset(data.data[0].id);
    } catch (err) {
      setError(err.message);
    }
  };

  const loadAllResults = async (assetId = selectedAsset) => {
    setLoading(true);
    setError("");
    try {
      await Promise.allSettled([
        loadWhoisResults(assetId),
        loadDNSResults(assetId, { page: 1, search: "", typeFilter: "" }),
        loadSubdomainResults(assetId, { page: 1, search: "", activeFilter: "" }),
        loadIPResults(assetId),
        loadSSLResults(assetId),
        loadTechResults(assetId),
        loadCertTransResults(assetId, { page: 1 }),
        loadPortResults(assetId, { page: 1 }),
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadWhoisResults = async (assetId = selectedAsset) => {
    try {
      const data = await resultsAPI.getWHOIS(assetId);
      setWhoisData(data.data || data);
    } catch { setWhoisData(null); }
  };

  const loadDNSResults = async (assetId = selectedAsset, options = {}) => {
    try {
      const { page = dnsPage, search = dnsSearch, typeFilter = dnsTypeFilter } = options;
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (typeFilter) params.type = typeFilter;
      const data = await resultsAPI.getDNS(assetId, params);
      setDnsData(data.data || []);
      setDnsPagination({ total: data.total || 0, page: data.page || page, page_size: data.page_size || pageSize, total_pages: data.total_pages || 0 });
    } catch { setDnsData([]); setDnsPagination({}); }
  };

  const loadSubdomainResults = async (assetId = selectedAsset, options = {}) => {
    try {
      const { page = subdomainPage, search = subdomainSearch, activeFilter = subdomainActiveFilter } = options;
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (activeFilter !== "") params.active = activeFilter;
      const data = await resultsAPI.getSubdomains(assetId, params);
      setSubdomainData(data.data || []);
      setSubdomainPagination({ total: data.total || 0, page: data.page || page, page_size: data.page_size || pageSize, total_pages: data.total_pages || 0 });
    } catch { setSubdomainData([]); setSubdomainPagination({}); }
  };

  const loadIPResults = async (assetId = selectedAsset) => {
    try {
      const data = await resultsAPI.getIP(assetId);
      setIpData(data.data || (Array.isArray(data) ? data : []));
    } catch { setIpData([]); }
  };

  const loadSSLResults = async (assetId = selectedAsset) => {
    try {
      const data = await resultsAPI.getSSL(assetId);
      setSslData(data.data || (Array.isArray(data) ? data : []));
    } catch { setSslData([]); }
  };

  const loadTechResults = async (assetId = selectedAsset) => {
    try {
      const data = await resultsAPI.getTech(assetId);
      setTechData(data.data || (Array.isArray(data) ? data : []));
    } catch { setTechData([]); }
  };

  const loadCertTransResults = async (assetId = selectedAsset, options = {}) => {
    try {
      const { page = certTransPage } = options;
      const data = await resultsAPI.getCertTrans(assetId, { page, page_size: pageSize });
      setCertTransData(data.data || []);
      setCertTransPagination({ total: data.total || 0, page: data.page || page, page_size: data.page_size || pageSize, total_pages: data.total_pages || 0 });
    } catch { setCertTransData([]); setCertTransPagination({}); }
  };

  const loadPortResults = async (assetId = selectedAsset, options = {}) => {
    try {
      const { page = portPage } = options;
      const data = await resultsAPI.getPort(assetId, { page, page_size: pageSize });
      setPortData(data.data || []);
      setPortPagination({ total: data.total || 0, page: data.page || page, page_size: data.page_size || pageSize, total_pages: data.total_pages || 0 });
    } catch { setPortData([]); setPortPagination({}); }
  };

  const loadSingleTypeResults = async () => {
    if (!selectedAsset) return;
    try {
      setLoading(true); setError("");
      if (resultType === "dns") await loadDNSResults();
      else if (resultType === "subdomains") await loadSubdomainResults();
      else if (resultType === "whois") await loadWhoisResults();
      else if (resultType === "ip") await loadIPResults();
      else if (resultType === "ssl") await loadSSLResults();
      else if (resultType === "tech") await loadTechResults();
      else if (resultType === "cert_trans") await loadCertTransResults();
      else if (resultType === "port") await loadPortResults();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const selectedAssetData = assets.find((a) => a.id === selectedAsset);

  // ============================================================
  // PAGINATION COMPONENT
  // ============================================================
  const renderPagination = (pagination, currentPage, setPage) => {
    if (!pagination || !pagination.total_pages || pagination.total_pages <= 1) return null;
    const generatePageNumbers = () => {
      const pages = [];
      const totalPages = pagination.total_pages;
      if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
      } else {
        pages.push(1);
        if (currentPage > 3) pages.push("...");
        for (let i = Math.max(2, currentPage - 1); i <= Math.min(currentPage + 1, totalPages - 1); i++) pages.push(i);
        if (currentPage < totalPages - 2) pages.push("...");
        pages.push(totalPages);
      }
      return pages;
    };
    return (
      <div className="flex items-center justify-between mt-4 px-4 pb-4">
        <div className="text-sm text-muted">
          Showing {(currentPage - 1) * pageSize + 1} to{" "}
          {Math.min(currentPage * pageSize, pagination.total || 0)} of {pagination.total || 0} results
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary btn-sm" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>
            <ChevronLeft size={16} /> Previous
          </button>
          {generatePageNumbers().map((pageNum, idx) =>
            pageNum === "..." ? (
              <span key={`ellipsis-${idx}`} className="px-2 text-muted">...</span>
            ) : (
              <button key={pageNum} className={`btn btn-sm ${pageNum === currentPage ? "btn-primary" : "btn-secondary"}`} onClick={() => setPage(pageNum)}>
                {pageNum}
              </button>
            )
          )}
          <button className="btn btn-secondary btn-sm" disabled={currentPage === pagination.total_pages} onClick={() => setPage(currentPage + 1)}>
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    );
  };

  // ============================================================
  // RENDER — DNS
  // ============================================================
  const renderDNSRecords = (records, showFilters = false) => (
    <>
      {showFilters && (
        <div className="p-4 border-b">
          <div className="grid grid-2 gap-4">
            <div>
              <label className="form-label">Search DNS Records</label>
              <div style={{ position: "relative" }}>
                <Search style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)", pointerEvents: "none", zIndex: 1 }} size={18} />
                <input type="text" className="form-input" style={{ paddingLeft: "40px" }} placeholder="Search by name or value..." value={dnsSearch}
                  onChange={(e) => { setDnsSearch(e.target.value); setDnsPage(1); }} />
              </div>
            </div>
            <div>
              <label className="form-label">Filter by Type</label>
              <select className="form-select" value={dnsTypeFilter} onChange={(e) => { setDnsTypeFilter(e.target.value); setDnsPage(1); }}>
                <option value="">All Types</option>
                {["A","AAAA","MX","NS","TXT","CNAME"].map(t => <option key={t} value={t}>{t} Records</option>)}
              </select>
            </div>
          </div>
        </div>
      )}
      {!records || records.length === 0 ? (
        <div className="p-4"><p className="text-muted">No DNS records found</p></div>
      ) : (
        <>
          <div className="table-container">
            <table className="table">
              <thead><tr><th>Type</th><th>Name</th><th>Value</th><th>TTL</th></tr></thead>
              <tbody>
                {records.map((record, idx) => (
                  <tr key={record.id || idx}>
                    <td><span className="badge badge-primary">{record.record_type}</span></td>
                    <td className="font-medium">{record.name}</td>
                    <td className="text-sm">{record.value}</td>
                    <td className="text-sm text-muted">{record.ttl}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {showFilters && renderPagination(dnsPagination, dnsPage, setDnsPage)}
        </>
      )}
    </>
  );

  // ============================================================
  // RENDER — SUBDOMAINS
  // ============================================================
  const renderSubdomains = (subdomains, showFilters = false) => (
    <>
      {showFilters && (
        <div className="p-4 border-b">
          <div className="grid grid-2 gap-4">
            <div>
              <label className="form-label">Search Subdomains</label>
              <div style={{ position: "relative" }}>
                <Search style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)", pointerEvents: "none", zIndex: 1 }} size={18} />
                <input type="text" className="form-input" style={{ paddingLeft: "40px" }} placeholder="Search subdomain..." value={subdomainSearch}
                  onChange={(e) => { setSubdomainSearch(e.target.value); setSubdomainPage(1); }} />
              </div>
            </div>
            <div>
              <label className="form-label">Filter by Status</label>
              <select className="form-select" value={subdomainActiveFilter} onChange={(e) => { setSubdomainActiveFilter(e.target.value); setSubdomainPage(1); }}>
                <option value="">All Status</option>
                <option value="true">Active Only</option>
                <option value="false">Inactive Only</option>
              </select>
            </div>
          </div>
        </div>
      )}
      {!subdomains || subdomains.length === 0 ? (
        <div className="p-4"><p className="text-muted">No subdomains found</p></div>
      ) : (
        <>
          <div className="table-container">
            <table className="table">
              <thead><tr><th>Subdomain</th><th>Source</th><th>Active</th><th>Discovered</th></tr></thead>
              <tbody>
                {subdomains.map((s, idx) => (
                  <tr key={s.id || idx}>
                    <td className="font-medium">{s.name}</td>
                    <td><span className="badge badge-info">{s.source}</span></td>
                    <td><span className={`badge ${s.is_active ? "badge-success" : "badge-secondary"}`}>{s.is_active ? "Yes" : "No"}</span></td>
                    <td className="text-sm text-muted">{s.created_at ? new Date(s.created_at).toLocaleDateString() : "N/A"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {showFilters && renderPagination(subdomainPagination, subdomainPage, setSubdomainPage)}
        </>
      )}
    </>
  );

  // ============================================================
  // RENDER — WHOIS
  // ============================================================
  const renderWHOIS = (whois) => {
    if (!whois) return <div className="p-4"><p className="text-muted">No WHOIS data found</p></div>;
    return (
      <div className="p-4 space-y-4">
        <div className="grid grid-2">
          {[["Registrar", whois.registrar], ["Status", whois.status],
            ["Created", whois.created_date ? new Date(whois.created_date).toLocaleDateString() : null],
            ["Expires", whois.expiry_date ? new Date(whois.expiry_date).toLocaleDateString() : null]
          ].map(([label, val]) => (
            <div key={label}>
              <label className="text-sm font-semibold text-muted">{label}</label>
              <p>{val || "N/A"}</p>
            </div>
          ))}
        </div>
        {whois.name_servers && (
          <div>
            <label className="text-sm font-semibold text-muted">Name Servers</label>
            <div className="flex flex-wrap gap-2 mt-2">
              {(() => { try { const s = typeof whois.name_servers === "string" ? JSON.parse(whois.name_servers) : whois.name_servers; return Array.isArray(s) ? s.map((ns, i) => <span key={i} className="badge badge-info">{ns}</span>) : null; } catch { return null; } })()}
            </div>
          </div>
        )}
        {whois.raw_data && (
          <div>
            <label className="text-sm font-semibold text-muted">Raw WHOIS Data</label>
            <pre className="mt-2 p-4 bg-gray-50 rounded-md text-xs overflow-x-auto">{whois.raw_data}</pre>
          </div>
        )}
      </div>
    );
  };

  // ============================================================
  // RENDER — IP INFO
  // ============================================================
  const renderIPInfo = (records) => {
    if (!records || records.length === 0) return <div className="p-4"><p className="text-muted">No IP info found. Run an IP scan first.</p></div>;
    return (
      <div className="p-4 space-y-6">
        {records.map((record, idx) => (
          <div key={record.id || idx} className="border rounded-md p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="badge badge-primary font-mono">{record.ip_address}</span>
              {record.reverse_dns && <span className="text-sm text-muted">↔ {record.reverse_dns}</span>}
            </div>
            <div className="grid grid-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-muted">Geolocation</label>
                <p className="text-sm">{[record.geolocation?.city, record.geolocation?.region, record.geolocation?.country].filter(Boolean).join(", ") || "N/A"}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">ISP / Org</label>
                <p className="text-sm">{record.isp || record.geolocation?.isp || "N/A"}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">ASN</label>
                <p className="text-sm font-mono">
                  {record.asn?.number ? `AS${record.asn.number}` : "N/A"}
                  {record.asn?.name && <span className="ml-2 text-muted">({record.asn.name})</span>}
                </p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">Coordinates</label>
                <p className="text-sm">{record.geolocation?.lat != null ? `${record.geolocation.lat}, ${record.geolocation.lon}` : "N/A"}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  // ============================================================
  // RENDER — SSL/TLS
  // ============================================================
  const renderSSLInfo = (records) => {
    if (!records || records.length === 0) return <div className="p-4"><p className="text-muted">No SSL/TLS data found. Run an SSL scan first.</p></div>;
    return (
      <div className="p-4 space-y-4">
        {records.map((record, idx) => (
          <div key={record.id || idx} className="border rounded-md p-4">
            <div className="grid grid-2 gap-4 mb-3">
              <div>
                <label className="text-sm font-semibold text-muted">Subject</label>
                <p className="text-sm font-mono">{record.subject || "N/A"}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">Issuer</label>
                <p className="text-sm">{record.issuer || "N/A"}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">Valid From</label>
                <p className="text-sm">{record.valid_from ? new Date(record.valid_from).toLocaleDateString() : "N/A"}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">Valid Until</label>
                <p className="text-sm">{record.valid_until ? new Date(record.valid_until).toLocaleDateString() : "N/A"}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">Protocol</label>
                <p className="text-sm"><span className="badge badge-info">{record.protocol || "N/A"}</span></p>
              </div>
              <div>
                <label className="text-sm font-semibold text-muted">Cipher Suite</label>
                <p className="text-sm font-mono text-xs">{record.cipher_suite || "N/A"}</p>
              </div>
            </div>
            {record.san && record.san.length > 0 && (
              <div>
                <label className="text-sm font-semibold text-muted">Subject Alternative Names</label>
                <div className="flex flex-wrap gap-1 mt-1">
                  {record.san.map((name, i) => <span key={i} className="badge badge-secondary text-xs">{name}</span>)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // ============================================================
  // RENDER — TECH STACK
  // ============================================================
  const renderTechStack = (records) => {
    if (!records || records.length === 0) return <div className="p-4"><p className="text-muted">No tech stack data found. Run a Tech scan first.</p></div>;
    return (
      <div className="p-4 space-y-6">
        {records.map((record, idx) => (
          <div key={record.id || idx} className="border rounded-md p-4">
            <p className="font-medium mb-3">{record.domain}</p>

            {/* Technologies */}
            {record.technologies && record.technologies.length > 0 && (
              <div className="mb-4">
                <label className="text-sm font-semibold text-muted">Detected Technologies</label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {record.technologies.map((tech, i) => (
                    <span key={i} className="badge badge-primary">
                      {tech.name}{tech.version ? ` ${tech.version}` : ""}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* HTTP Headers */}
            {record.headers && Object.keys(record.headers).length > 0 && (
              <div className="mb-4">
                <label className="text-sm font-semibold text-muted">HTTP Headers</label>
                <div className="table-container mt-2">
                  <table className="table">
                    <thead><tr><th>Header</th><th>Value</th></tr></thead>
                    <tbody>
                      {Object.entries(record.headers).map(([k, v]) => (
                        <tr key={k}><td className="font-mono text-xs">{k}</td><td className="text-xs">{v}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Meta Tags */}
            {record.meta_tags && Object.keys(record.meta_tags).length > 0 && (
              <div>
                <label className="text-sm font-semibold text-muted">Meta Tags</label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {Object.entries(record.meta_tags).map(([k, v]) => (
                    <span key={k} className="badge badge-info text-xs">{k}: {v}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // ============================================================
  // RENDER — CERTIFICATE TRANSPARENCY
  // ============================================================
  const renderCertTrans = (records, showPagination = false) => {
    if (!records || records.length === 0) return <div className="p-4"><p className="text-muted">No certificate transparency logs found. Run a CertTrans scan first.</p></div>;
    return (
      <>
        <div className="table-container">
          <table className="table">
            <thead><tr><th>Domain</th><th>Issuer</th><th>Not Before</th><th>Not After</th></tr></thead>
            <tbody>
              {records.map((record, idx) => (
                <tr key={record.id || idx}>
                  <td className="font-medium">{record.domain}</td>
                  <td className="text-sm">{record.issuer_name}</td>
                  <td className="text-sm text-muted">{record.not_before ? new Date(record.not_before).toLocaleDateString() : "N/A"}</td>
                  <td className="text-sm text-muted">{record.not_after ? new Date(record.not_after).toLocaleDateString() : "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {showPagination && renderPagination(certTransPagination, certTransPage, setCertTransPage)}
      </>
    );
  };

  // ============================================================
  // RENDER — PORT SCAN
  // ============================================================
  const renderPortScan = (records, showPagination = false) => {
    if (!records || records.length === 0) return <div className="p-4"><p className="text-muted">No port scan data found. Run a Port scan first.</p></div>;
    return (
      <>
        <div className="table-container">
          <table className="table">
            <thead><tr><th>Port</th><th>State</th><th>Service</th><th>Response Time</th></tr></thead>
            <tbody>
              {records.map((record, idx) => (
                <tr key={record.id || idx}>
                  <td className="font-mono font-medium">{record.port}</td>
                  <td>
                    <span className={`badge ${record.state === "open" ? "badge-success" : record.state === "filtered" ? "badge-warning" : "badge-secondary"}`}>
                      {record.state}
                    </span>
                  </td>
                  <td className="text-sm">{record.service || "unknown"}</td>
                  <td className="text-sm text-muted">{record.response_time_ms != null ? `${record.response_time_ms}ms` : "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {showPagination && renderPagination(portPagination, portPage, setPortPage)}
      </>
    );
  };

  // ============================================================
  // RENDER ALL
  // ============================================================
  const renderAllResults = () => (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Server size={20} className="mr-2" />WHOIS Information</h3></div>
        {renderWHOIS(whoisData)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Globe size={20} className="mr-2" />DNS Records ({dnsPagination.total || 0})</h3></div>
        {renderDNSRecords(dnsData, true)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Globe size={20} className="mr-2" />Subdomains ({subdomainPagination.total || 0})</h3></div>
        {renderSubdomains(subdomainData, true)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Network size={20} className="mr-2" />IP Information ({ipData.length})</h3></div>
        {renderIPInfo(ipData)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Shield size={20} className="mr-2" />SSL/TLS Certificates ({sslData.length})</h3></div>
        {renderSSLInfo(sslData)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Cpu size={20} className="mr-2" />Technology Stack ({techData.length})</h3></div>
        {renderTechStack(techData)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Award size={20} className="mr-2" />Certificate Transparency ({certTransPagination.total || certTransData.length})</h3></div>
        {renderCertTrans(certTransData, true)}
      </div>

      <div className="card">
        <div className="card-header"><h3 className="card-title flex items-center"><Server size={20} className="mr-2" />Port Scan ({portPagination.total || portData.length})</h3></div>
        {renderPortScan(portData, true)}
      </div>
    </div>
  );

  // ============================================================
  // MAIN RENDER
  // ============================================================
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Scan Results</h1>
        <p className="page-description">View and analyze reconnaissance data collected from scans</p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Filters */}
      <div className="card mb-4">
        <div className="grid grid-2 gap-4">
          <div className="form-group">
            <label className="form-label">Select Asset</label>
            <select className="form-select" value={selectedAsset} onChange={(e) => setSelectedAsset(e.target.value)}>
              {assets.length === 0 ? (
                <option>No assets available</option>
              ) : (
                assets.map((asset) => (
                  <option key={asset.id} value={asset.id}>{asset.name} ({asset.type})</option>
                ))
              )}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Result Type</label>
            <select className="form-select" value={resultType} onChange={(e) => setResultType(e.target.value)}>
              <option value="all">All Results</option>
              <option value="dns">DNS Records</option>
              <option value="subdomains">Subdomains</option>
              <option value="whois">WHOIS Information</option>
              <option value="ip">IP Information</option>
              <option value="ssl">SSL/TLS Certificates</option>
              <option value="tech">Technology Stack</option>
              <option value="cert_trans">Certificate Transparency</option>
              <option value="port">Port Scan</option>
            </select>
          </div>
        </div>

        {selectedAssetData && (
          <div className="mt-4 p-4 bg-gray-50 rounded-md">
            <h4 className="font-semibold text-sm mb-2">Asset Details:</h4>
            <div className="flex items-center gap-4 text-sm text-muted">
              <span><strong>Name:</strong> {selectedAssetData.name}</span>
              <span><strong>Type:</strong> {selectedAssetData.type}</span>
              <span><strong>Status:</strong> {selectedAssetData.status}</span>
            </div>
          </div>
        )}
      </div>

      {/* Results Display */}
      {loading ? (
        <div className="card">
          <div className="loading">
            <div className="spinner"></div>
            <span>Loading results...</span>
          </div>
        </div>
      ) : !selectedAsset ? (
        <div className="card">
          <div className="empty-state">
            <FileText className="empty-state-icon" size={64} />
            <h3 className="empty-state-title">No asset selected</h3>
            <p className="empty-state-description">Select an asset to view its scan results</p>
          </div>
        </div>
      ) : (
        <>
          {resultType === "all" && renderAllResults()}

          {resultType === "dns" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Globe size={20} className="inline mr-2" />DNS Records</h3></div>
              {renderDNSRecords(dnsData, true)}
            </div>
          )}

          {resultType === "subdomains" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Globe size={20} className="inline mr-2" />Subdomains</h3></div>
              {renderSubdomains(subdomainData, true)}
            </div>
          )}

          {resultType === "whois" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Server size={20} className="inline mr-2" />WHOIS Information</h3></div>
              {renderWHOIS(whoisData)}
            </div>
          )}

          {resultType === "ip" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Network size={20} className="inline mr-2" />IP Information</h3></div>
              {renderIPInfo(ipData)}
            </div>
          )}

          {resultType === "ssl" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Shield size={20} className="inline mr-2" />SSL/TLS Certificates</h3></div>
              {renderSSLInfo(sslData)}
            </div>
          )}

          {resultType === "tech" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Cpu size={20} className="inline mr-2" />Technology Stack</h3></div>
              {renderTechStack(techData)}
            </div>
          )}

          {resultType === "cert_trans" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Award size={20} className="inline mr-2" />Certificate Transparency</h3></div>
              {renderCertTrans(certTransData, true)}
            </div>
          )}

          {resultType === "port" && (
            <div className="card">
              <div className="card-header"><h3 className="card-title"><Server size={20} className="inline mr-2" />Port Scan Results</h3></div>
              {renderPortScan(portData, true)}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Results;
