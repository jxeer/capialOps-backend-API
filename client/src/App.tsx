/**
 * Backend Client App
 * 
 * This is a separate, lightweight React app used by the backend for
 * the initial authentication flow. It provides login and dashboard pages
 * for the first version of the authentication system.
 * 
 * NOTE: The main CapitalOps frontend is in the frontend/ repository.
 * This client is a fallback/minimal UI used during development.
 */

import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ProtectedRoute from "./components/ProtectedRoute";

/**
 * Main App Component
 * 
 * Routes:
 * - /login - Login page (public)
 * - /dashboard - Dashboard (protected, requires auth)
 * - * (default) - Redirects to /dashboard
 */
export default function App() {
  return (
    <Routes>
      {/* Public login route */}
      <Route path="/login" element={<LoginPage />} />
      
      {/* Protected dashboard route - wraps in ProtectedRoute to check auth */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      
      {/* Default route - redirect to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
