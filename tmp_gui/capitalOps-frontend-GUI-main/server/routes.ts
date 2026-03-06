import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { log } from "./index";

const BACKEND_URL = process.env.BACKEND_URL || "";

async function proxyToBackend(path: string, method: string, body?: unknown): Promise<{ ok: boolean; status: number; data: unknown }> {
  if (!BACKEND_URL) return { ok: false, status: 0, data: null };

  try {
    const url = `${BACKEND_URL}${path}`;
    const options: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
    };
    if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    if (response.ok) {
      const data = await response.json();
      return { ok: true, status: response.status, data };
    }
    return { ok: false, status: response.status, data: null };
  } catch (err) {
    log(`Backend proxy error for ${path}: ${err}`, "proxy");
    return { ok: false, status: 0, data: null };
  }
}

async function withBackendFallback(
  req: Request,
  res: Response,
  localHandler: () => Promise<void>
) {
  const backendPath = req.originalUrl;
  const result = await proxyToBackend(backendPath, req.method, req.body);

  if (result.ok) {
    log(`Proxied ${req.method} ${backendPath} -> backend (${result.status})`, "proxy");
    return res.status(result.status).json(result.data);
  }

  log(`Backend unavailable for ${backendPath}, using local storage`, "proxy");
  await localHandler();
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  app.get("/api/backend-status", async (_req, res) => {
    if (!BACKEND_URL) {
      return res.json({ connected: false, url: null, mode: "local" });
    }
    try {
      const response = await fetch(BACKEND_URL);
      const data = await response.json();
      res.json({ connected: response.ok, url: BACKEND_URL, mode: "proxy", backendInfo: data });
    } catch {
      res.json({ connected: false, url: BACKEND_URL, mode: "local-fallback" });
    }
  });

  app.get("/api/dashboard/stats", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const stats = await storage.getDashboardStats();
      res.json(stats);
    });
  });

  app.get("/api/portfolios", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const portfolios = await storage.getPortfolios();
      res.json(portfolios);
    });
  });

  app.get("/api/assets", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const assets = await storage.getAssets();
      res.json(assets);
    });
  });

  app.get("/api/assets/:id", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const asset = await storage.getAsset(req.params.id);
      if (!asset) return res.status(404).json({ message: "Asset not found" });
      res.json(asset);
    });
  });

  app.post("/api/assets", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const asset = await storage.createAsset(req.body);
      res.status(201).json(asset);
    });
  });

  app.get("/api/projects", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const projects = await storage.getProjects();
      res.json(projects);
    });
  });

  app.get("/api/projects/:id", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const project = await storage.getProject(req.params.id);
      if (!project) return res.status(404).json({ message: "Project not found" });
      res.json(project);
    });
  });

  app.post("/api/projects", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const project = await storage.createProject(req.body);
      res.status(201).json(project);
    });
  });

  app.get("/api/deals", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const deals = await storage.getDeals();
      res.json(deals);
    });
  });

  app.get("/api/deals/:id", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const deal = await storage.getDeal(req.params.id);
      if (!deal) return res.status(404).json({ message: "Deal not found" });
      res.json(deal);
    });
  });

  app.post("/api/deals", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const deal = await storage.createDeal(req.body);
      res.status(201).json(deal);
    });
  });

  app.get("/api/investors", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const investors = await storage.getInvestors();
      res.json(investors);
    });
  });

  app.get("/api/investors/:id", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const investor = await storage.getInvestor(req.params.id);
      if (!investor) return res.status(404).json({ message: "Investor not found" });
      res.json(investor);
    });
  });

  app.post("/api/investors", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const investor = await storage.createInvestor(req.body);
      res.status(201).json(investor);
    });
  });

  app.get("/api/allocations", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const allocations = await storage.getAllocations();
      res.json(allocations);
    });
  });

  app.post("/api/allocations", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const allocation = await storage.createAllocation(req.body);
      res.status(201).json(allocation);
    });
  });

  app.get("/api/milestones", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const milestones = await storage.getMilestones();
      res.json(milestones);
    });
  });

  app.get("/api/milestones/project/:projectId", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const milestones = await storage.getMilestonesByProject(req.params.projectId);
      res.json(milestones);
    });
  });

  app.post("/api/milestones", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const milestone = await storage.createMilestone(req.body);
      res.status(201).json(milestone);
    });
  });

  app.get("/api/vendors", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const vendors = await storage.getVendors();
      res.json(vendors);
    });
  });

  app.get("/api/vendors/:id", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const vendor = await storage.getVendor(req.params.id);
      if (!vendor) return res.status(404).json({ message: "Vendor not found" });
      res.json(vendor);
    });
  });

  app.post("/api/vendors", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const vendor = await storage.createVendor(req.body);
      res.status(201).json(vendor);
    });
  });

  app.get("/api/work-orders", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const workOrders = await storage.getWorkOrders();
      res.json(workOrders);
    });
  });

  app.get("/api/work-orders/vendor/:vendorId", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const workOrders = await storage.getWorkOrdersByVendor(req.params.vendorId);
      res.json(workOrders);
    });
  });

  app.post("/api/work-orders", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const workOrder = await storage.createWorkOrder(req.body);
      res.status(201).json(workOrder);
    });
  });

  app.get("/api/risk-flags", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const riskFlags = await storage.getRiskFlags();
      res.json(riskFlags);
    });
  });

  app.get("/api/risk-flags/project/:projectId", async (req, res) => {
    await withBackendFallback(req, res, async () => {
      const riskFlags = await storage.getRiskFlagsByProject(req.params.projectId);
      res.json(riskFlags);
    });
  });

  return httpServer;
}
