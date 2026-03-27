/**
 * DashboardPage Component
 * 
 * Purpose: Simple dashboard showing user's projects and account info.
 * This is the dashboard for the lightweight backend auth app.
 * 
 * DATA FLOW:
 * 1. On mount, fetches user profile and projects via API
 * 2. Displays projects in a table with status, budget, progress
 * 3. Provides logout functionality
 * 
 * NOTE: This is the OLD dashboard. The main CapitalOps frontend
 * in the frontend/ repository has a much more sophisticated dashboard.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearToken, User, ProjectWithMetrics } from "@/lib/api";

/**
 * DashboardPage Component
 * 
 * Fetches and displays:
 * - Current user info (name, role)
 * - List of projects with metrics (status, budget, progress)
 */
export default function DashboardPage() {
  const navigate = useNavigate();
  
  // User state - null until loaded
  const [user, setUser] = useState<User | null>(null);
  
  // Projects list
  const [projects, setProjects] = useState<ProjectWithMetrics[]>([]);
  
  // Loading/error state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /**
   * Load user and projects on component mount.
   * 
   * Uses Promise.all to fetch both in parallel for performance.
   */
  useEffect(() => {
    async function load() {
      try {
        // Fetch user profile and projects concurrently
        const [meRes, projRes] = await Promise.all([
          api.getMe(),
          api.getProjects(),
        ]);
        setUser(meRes.user);
        setProjects(projRes.projects);
      } catch (err: any) {
        setError(err.message || "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  /**
   * Handle logout
   * 
   * Clears stored token and redirects to login.
   */
  function handleLogout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  /**
   * Format a number as USD currency.
   * Uses Intl.NumberFormat for proper currency display.
   */
  function formatCurrency(val: number): string {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,  // No cents for large amounts
    }).format(val);
  }

  /**
   * Convert status string to CSS class name.
   * Maps status strings to styling classes.
   */
  function statusClass(status: string): string {
    // Normalize status: lowercase and replace spaces with hyphens
    const s = status.toLowerCase().replace(/\s+/g, "-");
    if (s === "on-track") return "on-track";
    if (s === "at-risk") return "at-risk";
    if (s === "complete") return "complete";
    return "";
  }

  // Show loading state
  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  // Show error state
  if (error) {
    return <div className="loading">{error}</div>;
  }

  // Render dashboard with user info and projects table
  return (
    <div className="dashboard">
      {/* Header with title and user info */}
      <header>
        <h1>Project Dashboard</h1>
        <div className="user-info">
          {/* Display user's full name and role */}
          <span>{user?.full_name} ({user?.role})</span>
          {/* Logout button */}
          <button className="btn-logout" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </header>

      {/* Projects table */}
      <table className="projects-table">
        {/* Table header */}
        <thead>
          <tr>
            <th>Asset</th>
            <th>Phase</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Budget</th>
            <th>Spent</th>
            <th>PM</th>
          </tr>
        </thead>
        
        {/* Table body - render each project */}
        <tbody>
          {projects.map((p) => (
            <tr key={p.project.id}>
              {/* Asset name */}
              <td>{p.project.asset_name}</td>
              {/* Project phase */}
              <td>{p.project.phase}</td>
              {/* Status with badge styling */}
              <td>
                <span className={`status-badge ${statusClass(p.project.status)}`}>
                  {p.project.status}
                </span>
              </td>
              {/* Progress percentage */}
              <td>{p.progress}%</td>
              {/* Budget (total) */}
              <td>{formatCurrency(p.project.budget_total)}</td>
              {/* Spent (actual) */}
              <td>{formatCurrency(p.project.budget_actual)}</td>
              {/* Project manager */}
              <td>{p.project.pm_assigned}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
