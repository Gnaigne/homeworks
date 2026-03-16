import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Shield, Home, Database, Activity, FileText } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Assets from "./pages/Assets";
import Scanning from "./pages/Scanning";
import Results from "./pages/Results";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <div className="container">
            <div className="nav-content">
              <div className="nav-brand">
                <Shield className="nav-icon" />
                <span>EASM Platform</span>
              </div>
              <div className="nav-links">
                <Link to="/" className="nav-link">
                  <Home size={18} />
                  Dashboard
                </Link>
                <Link to="/assets" className="nav-link">
                  <Database size={18} />
                  Assets
                </Link>
                <Link to="/scanning" className="nav-link">
                  <Activity size={18} />
                  Scanning
                </Link>
                <Link to="/results" className="nav-link">
                  <FileText size={18} />
                  Results
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <div className="container">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/assets" element={<Assets />} />
              <Route path="/scanning" element={<Scanning />} />
              <Route path="/results" element={<Results />} />
            </Routes>
          </div>
        </main>

        <footer className="footer">
          <div className="container">
            <p className="text-muted text-sm">
              © 2026 EASM Platform - CMC Intern Program
            </p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
