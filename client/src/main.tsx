/**
 * Backend Client Entry Point
 * 
 * This is the React entry point for the lightweight backend auth client.
 * It mounts the App component inside React Router's BrowserRouter.
 * 
 * NOTE: This is for the OLD backend client. The main CapitalOps
 * frontend is in the frontend/ repository.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

/**
 * Mount the React app to the #root DOM element.
 * 
 * React.StrictMode enables additional development checks in development mode.
 * BrowserRouter provides client-side routing.
 */
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
