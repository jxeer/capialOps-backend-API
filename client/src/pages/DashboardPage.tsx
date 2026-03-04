import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearToken, User, ProjectWithMetrics } from "@/lib/api";

export default function DashboardPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<ProjectWithMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
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

  function handleLogout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  function formatCurrency(val: number): string {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(val);
  }

  function statusClass(status: string): string {
    const s = status.toLowerCase().replace(/\s+/g, "-");
    if (s === "on-track") return "on-track";
    if (s === "at-risk") return "at-risk";
    if (s === "complete") return "complete";
    return "";
  }

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="loading">{error}</div>;
  }

  return (
    <div className="dashboard">
      <header>
        <h1>Project Dashboard</h1>
        <div className="user-info">
          <span>{user?.full_name} ({user?.role})</span>
          <button className="btn-logout" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </header>

      <table className="projects-table">
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
        <tbody>
          {projects.map((p) => (
            <tr key={p.project.id}>
              <td>{p.project.asset_name}</td>
              <td>{p.project.phase}</td>
              <td>
                <span className={`status-badge ${statusClass(p.project.status)}`}>
                  {p.project.status}
                </span>
              </td>
              <td>{p.progress}%</td>
              <td>{formatCurrency(p.project.budget_total)}</td>
              <td>{formatCurrency(p.project.budget_actual)}</td>
              <td>{p.project.pm_assigned}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
