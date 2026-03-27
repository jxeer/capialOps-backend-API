/**
 * LoginPage Component
 * 
 * Purpose: Simple login form for the backend client.
 * This is the login page for the lightweight backend auth app.
 * 
 * FLOW:
 * 1. User enters username/password
 * 2. Calls api.login() which POSTs to backend
 * 3. On success: stores token and navigates to /dashboard
 * 4. On failure: shows error message
 * 
 * NOTE: This is the OLD login page. The main CapitalOps frontend
 * is in the frontend/ repository and has a more sophisticated login flow.
 */

import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "@/lib/api";

/**
 * LoginPage Component
 * 
 * State:
 * - username/password: Form fields
 * - error: Error message to display
 * - loading: Disable button while submitting
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  /**
   * Handle form submission
   * 
   * Calls the API login endpoint with credentials.
   * On success, stores the JWT token and redirects to dashboard.
   * On failure, displays an error message.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Call backend login API
      const data = await api.login(username, password);
      
      // Store JWT token for subsequent authenticated requests
      setToken(data.accessToken);
      
      // Redirect to dashboard on success
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      // Display error message to user
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="login-card">
        {/* Branding */}
        <h1>CapitalOps</h1>
        <p className="subtitle">Sign in to your account</p>

        {/* Error message display */}
        {error && <div className="error-msg">{error}</div>}

        {/* Login form */}
        <form onSubmit={handleSubmit}>
          {/* Username field */}
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          {/* Password field */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {/* Submit button with loading state */}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
