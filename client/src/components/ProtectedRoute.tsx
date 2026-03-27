/**
 * ProtectedRoute Component
 * 
 * Purpose: Route wrapper that redirects to login if user is not authenticated.
 * This is a simple auth guard for protected routes.
 * 
 * SECURITY: This is a basic token check. For production, consider:
 * - Token expiration validation
 * - Refresh token handling
 * - More sophisticated auth state management
 * 
 * USAGE:
 * <ProtectedRoute>
 *   <DashboardPage />
 * </ProtectedRoute>
 */

import { Navigate } from "react-router-dom";
import { getToken } from "@/lib/api";

/**
 * Props for ProtectedRoute component.
 * 
 * @param children - The child components to render if authenticated
 */
interface Props {
  children: React.ReactNode;
}

/**
 * ProtectedRoute Component
 * 
 * Checks for an auth token. If no token exists,
 * redirects to /login. Otherwise renders children.
 */
export default function ProtectedRoute({ children }: Props) {
  // Get token from storage
  const token = getToken();

  // If no token, redirect to login
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Token exists - render protected content
  return <>{children}</>;
}
