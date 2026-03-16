import { useState, useEffect } from "react";
import {
  Plus,
  Search,
  Trash2,
  Edit,
  Globe,
  Server,
  Link as LinkIcon,
  Database,
} from "lucide-react";
import { assetsAPI } from "../services/api";

function Assets() {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });
  const [filters, setFilters] = useState({
    type: "",
    status: "",
    search: "",
  });
  const [showModal, setShowModal] = useState(false);
  const [editingAsset, setEditingAsset] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    type: "domain",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    loadAssets();
  }, [pagination.page, filters]);

  const loadAssets = async () => {
    try {
      setLoading(true);
      setError("");
      const params = {
        page: pagination.page,
        page_size: pagination.page_size,
        ...filters,
      };
      const data = await assetsAPI.list(params);
      setAssets(data.data || []);
      setPagination((prev) => ({
        ...prev,
        total: data.total,
        total_pages: data.total_pages,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError("");
      if (editingAsset) {
        await assetsAPI.update(editingAsset.id, formData);
      } else {
        await assetsAPI.create(formData);
      }
      setShowModal(false);
      setFormData({ name: "", type: "domain" });
      setEditingAsset(null);
      loadAssets();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this asset?")) return;
    try {
      await assetsAPI.delete(id);
      loadAssets();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (asset) => {
    setEditingAsset(asset);
    setFormData({
      name: asset.name,
      type: asset.type,
      status: asset.status,
    });
    setShowModal(true);
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case "domain":
        return <Globe size={16} />;
      case "ip":
        return <Server size={16} />;
      case "service":
        return <LinkIcon size={16} />;
      default:
        return null;
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Assets Management</h1>
        <p className="page-description">
          Manage your external assets (domains, IPs, and services)
        </p>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Actions Bar */}
      <div className="actions-bar">
        <div className="search-box">
          <input
            type="text"
            className="form-input"
            placeholder="Search assets..."
            value={filters.search}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, search: e.target.value }))
            }
          />
          <select
            className="form-select"
            value={filters.type}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, type: e.target.value }))
            }
          >
            <option value="">All Types</option>
            <option value="domain">Domain</option>
            <option value="ip">IP</option>
            <option value="service">Service</option>
          </select>
          <select
            className="form-select"
            value={filters.status}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, status: e.target.value }))
            }
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <div className="actions-group">
          <button
            className="btn btn-primary"
            onClick={() => {
              setEditingAsset(null);
              setFormData({ name: "", type: "domain" });
              setShowModal(true);
            }}
          >
            <Plus size={18} />
            Add Asset
          </button>
        </div>
      </div>

      {/* Assets Table */}
      <div className="card">
        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
            <span>Loading assets...</span>
          </div>
        ) : assets.length === 0 ? (
          <div className="empty-state">
            <Database className="empty-state-icon" size={64} />
            <h3 className="empty-state-title">No assets found</h3>
            <p className="empty-state-description">
              Get started by adding your first asset
            </p>
            <button
              className="btn btn-primary"
              onClick={() => setShowModal(true)}
            >
              <Plus size={18} />
              Add First Asset
            </button>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {assets.map((asset) => (
                    <tr key={asset.id}>
                      <td>
                        <div className="flex items-center gap-2">
                          {getTypeIcon(asset.type)}
                          <span className="font-medium">{asset.name}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`badge badge-primary`}>
                          {asset.type}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            asset.status === "active"
                              ? "badge-success"
                              : "badge-secondary"
                          }`}
                        >
                          {asset.status}
                        </span>
                      </td>
                      <td className="text-sm text-muted">
                        {new Date(asset.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => handleEdit(asset)}
                          >
                            <Edit size={14} />
                          </button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => handleDelete(asset.id)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagination.page === 1}
                onClick={() =>
                  setPagination((prev) => ({ ...prev, page: prev.page - 1 }))
                }
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {pagination.page} of {pagination.total_pages} (
                {pagination.total} total)
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagination.page === pagination.total_pages}
                onClick={() =>
                  setPagination((prev) => ({ ...prev, page: prev.page + 1 }))
                }
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">
                {editingAsset ? "Edit Asset" : "Add New Asset"}
              </h3>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => setShowModal(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Name *</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g., example.com, 192.168.1.1"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, name: e.target.value }))
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Type *</label>
                  <select
                    className="form-select"
                    value={formData.type}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, type: e.target.value }))
                    }
                    required
                  >
                    <option value="domain">Domain</option>
                    <option value="ip">IP Address</option>
                    <option value="service">Service/URL</option>
                  </select>
                </div>
                {editingAsset && (
                  <div className="form-group">
                    <label className="form-label">Status</label>
                    <select
                      className="form-select"
                      value={formData.status}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          status: e.target.value,
                        }))
                      }
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingAsset ? "Save Changes" : "Add Asset"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Assets;
