import { randomUUID } from "crypto";
import type {
  Asset, InsertAsset,
  Project, InsertProject,
  Deal, InsertDeal,
  Investor, InsertInvestor,
  Allocation, InsertAllocation,
  Milestone, InsertMilestone,
  Vendor, InsertVendor,
  WorkOrder, InsertWorkOrder,
  RiskFlag, Portfolio,
} from "@shared/schema";

export interface IStorage {
  getPortfolios(): Promise<Portfolio[]>;
  getAssets(): Promise<Asset[]>;
  getAsset(id: string): Promise<Asset | undefined>;
  createAsset(asset: InsertAsset): Promise<Asset>;
  getProjects(): Promise<Project[]>;
  getProject(id: string): Promise<Project | undefined>;
  createProject(project: InsertProject): Promise<Project>;
  getDeals(): Promise<Deal[]>;
  getDeal(id: string): Promise<Deal | undefined>;
  createDeal(deal: InsertDeal): Promise<Deal>;
  getInvestors(): Promise<Investor[]>;
  getInvestor(id: string): Promise<Investor | undefined>;
  createInvestor(investor: InsertInvestor): Promise<Investor>;
  getAllocations(): Promise<Allocation[]>;
  getAllocation(id: string): Promise<Allocation | undefined>;
  createAllocation(allocation: InsertAllocation): Promise<Allocation>;
  getMilestones(): Promise<Milestone[]>;
  getMilestonesByProject(projectId: string): Promise<Milestone[]>;
  createMilestone(milestone: InsertMilestone): Promise<Milestone>;
  getVendors(): Promise<Vendor[]>;
  getVendor(id: string): Promise<Vendor | undefined>;
  createVendor(vendor: InsertVendor): Promise<Vendor>;
  getWorkOrders(): Promise<WorkOrder[]>;
  getWorkOrdersByVendor(vendorId: string): Promise<WorkOrder[]>;
  createWorkOrder(workOrder: InsertWorkOrder): Promise<WorkOrder>;
  getRiskFlags(): Promise<RiskFlag[]>;
  getRiskFlagsByProject(projectId: string): Promise<RiskFlag[]>;
  getDashboardStats(): Promise<{
    totalAssets: number;
    activeProjects: number;
    totalCapitalRequired: number;
    totalCapitalRaised: number;
    activeDeals: number;
    totalInvestors: number;
    openWorkOrders: number;
    riskFlags: number;
  }>;
}

export class MemStorage implements IStorage {
  private portfolios: Map<string, Portfolio> = new Map();
  private assets: Map<string, Asset> = new Map();
  private projects: Map<string, Project> = new Map();
  private deals: Map<string, Deal> = new Map();
  private investors: Map<string, Investor> = new Map();
  private allocations: Map<string, Allocation> = new Map();
  private milestones: Map<string, Milestone> = new Map();
  private vendors: Map<string, Vendor> = new Map();
  private workOrders: Map<string, WorkOrder> = new Map();
  private riskFlags: Map<string, RiskFlag> = new Map();

  constructor() {
    this.seed();
  }

  private seed() {
    const portfolioId = "port-001";
    this.portfolios.set(portfolioId, {
      id: portfolioId,
      name: "Coral Capital Portfolio",
      description: "Primary real estate development portfolio",
    });

    const assets: Asset[] = [
      { id: "asset-001", portfolioId, name: "The Meridian Tower", location: "Austin, TX", assetType: "Mixed-Use", squareFootage: 285000, status: "Active", assetManager: "Sarah Chen" },
      { id: "asset-002", portfolioId, name: "Parkview Residences", location: "Denver, CO", assetType: "Multifamily", squareFootage: 180000, status: "Pre-dev", assetManager: "Marcus Rivera" },
      { id: "asset-003", portfolioId, name: "Commerce Square", location: "Nashville, TN", assetType: "Office", squareFootage: 120000, status: "Active", assetManager: "Emily Watson" },
      { id: "asset-004", portfolioId, name: "Harbor Point", location: "Charleston, SC", assetType: "Retail", squareFootage: 95000, status: "Stabilized", assetManager: "James Okafor" },
    ];
    assets.forEach(a => this.assets.set(a.id, a));

    const projects: Project[] = [
      { id: "proj-001", assetId: "asset-001", portfolioId, phase: "Construction", startDate: "2025-03-01", targetCompletion: "2026-09-30", budgetTotal: 45000000, budgetActual: 18500000, status: "In Progress", pmAssigned: "David Kim" },
      { id: "proj-002", assetId: "asset-002", portfolioId, phase: "Pre-Development", startDate: "2025-06-15", targetCompletion: "2027-12-31", budgetTotal: 32000000, budgetActual: 2800000, status: "Planning", pmAssigned: "Lisa Tran" },
      { id: "proj-003", assetId: "asset-003", portfolioId, phase: "Renovation", startDate: "2025-01-10", targetCompletion: "2025-11-30", budgetTotal: 8500000, budgetActual: 5200000, status: "In Progress", pmAssigned: "Robert Hayes" },
    ];
    projects.forEach(p => this.projects.set(p.id, p));

    const deals: Deal[] = [
      { id: "deal-001", projectId: "proj-001", portfolioId, capitalRequired: 15000000, capitalRaised: 11200000, returnProfile: "18-22% IRR", duration: "36 months", riskLevel: "Medium", complexity: "Complex", phase: "Fundraising", status: "Active" },
      { id: "deal-002", projectId: "proj-002", portfolioId, capitalRequired: 10000000, capitalRaised: 3500000, returnProfile: "15-18% IRR", duration: "48 months", riskLevel: "High", complexity: "Moderate", phase: "Pre-Marketing", status: "Draft" },
      { id: "deal-003", projectId: "proj-003", portfolioId, capitalRequired: 3000000, capitalRaised: 3000000, returnProfile: "12-15% IRR", duration: "18 months", riskLevel: "Low", complexity: "Simple", phase: "Closed", status: "Funded" },
    ];
    deals.forEach(d => this.deals.set(d.id, d));

    const investors: Investor[] = [
      { id: "inv-001", name: "Westfield Capital Partners", accreditationStatus: "Qualified Purchaser", checkSizeMin: 500000, checkSizeMax: 5000000, assetPreference: "Mixed-Use", geographyPreference: "Sun Belt", riskTolerance: "Moderate", structurePreference: "LP Equity", timelinePreference: "24-48 months", strategicInterest: "Value-Add", tierLevel: "Tier 2", status: "Active" },
      { id: "inv-002", name: "Angela Moretti", accreditationStatus: "Accredited", checkSizeMin: 100000, checkSizeMax: 500000, assetPreference: "Multifamily", geographyPreference: "Southeast", riskTolerance: "Conservative", structurePreference: "Preferred Equity", timelinePreference: "12-36 months", strategicInterest: "Cash Flow", tierLevel: "Tier 1", status: "Active" },
      { id: "inv-003", name: "Horizon Family Office", accreditationStatus: "Qualified Purchaser", checkSizeMin: 1000000, checkSizeMax: 10000000, assetPreference: "Office", geographyPreference: "National", riskTolerance: "Aggressive", structurePreference: "JV Equity", timelinePreference: "36-60 months", strategicInterest: "Development", tierLevel: "Tier 2", status: "Active" },
      { id: "inv-004", name: "Thomas Blackwell", accreditationStatus: "Accredited", checkSizeMin: 250000, checkSizeMax: 1000000, assetPreference: "Retail", geographyPreference: "Mid-Atlantic", riskTolerance: "Moderate", structurePreference: "LP Equity", timelinePreference: "18-36 months", strategicInterest: "Stabilized", tierLevel: "Tier 1", status: "Prospect" },
      { id: "inv-005", name: "Pacific Ridge Investments", accreditationStatus: "Qualified Purchaser", checkSizeMin: 2000000, checkSizeMax: 15000000, assetPreference: "Mixed-Use", geographyPreference: "West Coast", riskTolerance: "Aggressive", structurePreference: "Co-GP", timelinePreference: "48-72 months", strategicInterest: "Ground-Up", tierLevel: "Tier 2", status: "Active" },
    ];
    investors.forEach(i => this.investors.set(i.id, i));

    const allocations: Allocation[] = [
      { id: "alloc-001", investorId: "inv-001", dealId: "deal-001", softCommitAmount: 2000000, hardCommitAmount: 1500000, status: "Hard Commit", timestamp: "2025-04-15T10:30:00Z", notes: "Completed DD, signed subscription" },
      { id: "alloc-002", investorId: "inv-002", dealId: "deal-001", softCommitAmount: 350000, hardCommitAmount: 350000, status: "Funded", timestamp: "2025-03-28T14:00:00Z", notes: "Wire confirmed" },
      { id: "alloc-003", investorId: "inv-003", dealId: "deal-001", softCommitAmount: 5000000, hardCommitAmount: 0, status: "Soft Commit", timestamp: "2025-05-02T09:15:00Z", notes: "Awaiting IC approval" },
      { id: "alloc-004", investorId: "inv-005", dealId: "deal-001", softCommitAmount: 3000000, hardCommitAmount: 3000000, status: "Funded", timestamp: "2025-03-10T11:45:00Z" },
      { id: "alloc-005", investorId: "inv-003", dealId: "deal-003", softCommitAmount: 2000000, hardCommitAmount: 2000000, status: "Funded", timestamp: "2025-01-20T16:00:00Z" },
      { id: "alloc-006", investorId: "inv-001", dealId: "deal-003", softCommitAmount: 1000000, hardCommitAmount: 1000000, status: "Funded", timestamp: "2025-01-22T10:00:00Z" },
      { id: "alloc-007", investorId: "inv-004", dealId: "deal-002", softCommitAmount: 500000, hardCommitAmount: 0, status: "Pending", timestamp: "2025-06-01T08:30:00Z", notes: "Initial interest expressed" },
    ];
    allocations.forEach(a => this.allocations.set(a.id, a));

    const milestones: Milestone[] = [
      { id: "ms-001", projectId: "proj-001", name: "Foundation Complete", category: "Construction", targetDate: "2025-06-30", completionDate: "2025-07-05", status: "Completed", delayExplanation: "Weather delays", riskFlag: false },
      { id: "ms-002", projectId: "proj-001", name: "Steel Structure", category: "Construction", targetDate: "2025-10-15", status: "In Progress", riskFlag: false },
      { id: "ms-003", projectId: "proj-001", name: "MEP Rough-In", category: "Construction", targetDate: "2026-01-30", status: "Pending", riskFlag: false },
      { id: "ms-004", projectId: "proj-001", name: "Building Envelope", category: "Construction", targetDate: "2026-04-15", status: "Pending", riskFlag: true },
      { id: "ms-005", projectId: "proj-002", name: "Entitlements Secured", category: "Pre-Development", targetDate: "2025-09-30", status: "In Progress", riskFlag: true },
      { id: "ms-006", projectId: "proj-002", name: "Design Development", category: "Design", targetDate: "2025-12-15", status: "Pending", riskFlag: false },
      { id: "ms-007", projectId: "proj-003", name: "Demo Complete", category: "Renovation", targetDate: "2025-03-15", completionDate: "2025-03-12", status: "Completed", riskFlag: false },
      { id: "ms-008", projectId: "proj-003", name: "Tenant Improvements", category: "Renovation", targetDate: "2025-08-30", status: "Delayed", delayExplanation: "Supply chain issues with custom millwork", riskFlag: true },
    ];
    milestones.forEach(m => this.milestones.set(m.id, m));

    const vendors: Vendor[] = [
      { id: "vend-001", assetId: "asset-001", name: "Turner Construction", type: "General Contractor", coiStatus: "Current", slaType: "Fixed Price", performanceScore: 92 },
      { id: "vend-002", assetId: "asset-001", name: "Apex Mechanical", type: "HVAC", coiStatus: "Current", slaType: "Time & Materials", performanceScore: 87 },
      { id: "vend-003", assetId: "asset-003", name: "Summit Electric", type: "Electrical", coiStatus: "Expired", slaType: "Fixed Price", performanceScore: 78 },
      { id: "vend-004", assetId: "asset-002", name: "GreenScape Solutions", type: "Landscaping", coiStatus: "Pending", slaType: "Service Agreement", performanceScore: 85 },
      { id: "vend-005", assetId: "asset-004", name: "SecureGuard Systems", type: "Security", coiStatus: "Current", slaType: "Monthly Retainer", performanceScore: 95 },
    ];
    vendors.forEach(v => this.vendors.set(v.id, v));

    const workOrders: WorkOrder[] = [
      { id: "wo-001", vendorId: "vend-001", assetId: "asset-001", type: "Construction", priority: "High", cost: 125000, capExFlag: true, status: "In Progress", description: "Floor 8-12 framing and concrete pour" },
      { id: "wo-002", vendorId: "vend-002", assetId: "asset-001", type: "HVAC Installation", priority: "Medium", cost: 45000, capExFlag: true, status: "Open", description: "Ductwork installation floors 1-5" },
      { id: "wo-003", vendorId: "vend-003", assetId: "asset-003", type: "Electrical Upgrade", priority: "High", cost: 32000, capExFlag: true, status: "In Progress", description: "Panel upgrade and new circuit installation" },
      { id: "wo-004", vendorId: "vend-005", assetId: "asset-004", type: "Security System", priority: "Low", cost: 8500, capExFlag: false, status: "Completed", completionDate: "2025-05-20", description: "Camera system maintenance and firmware update" },
      { id: "wo-005", vendorId: "vend-004", assetId: "asset-002", type: "Site Prep", priority: "Urgent", cost: 18000, capExFlag: true, status: "Open", description: "Initial site clearing and grading" },
    ];
    workOrders.forEach(w => this.workOrders.set(w.id, w));

    const riskFlags: RiskFlag[] = [
      { id: "rf-001", projectId: "proj-001", category: "Schedule", severity: "Medium", description: "Building envelope timeline at risk due to steel delivery delays", status: "Open", createdAt: "2025-07-15" },
      { id: "rf-002", projectId: "proj-002", category: "Regulatory", severity: "High", description: "Entitlement hearing postponed, potential 60-day delay", status: "Open", createdAt: "2025-08-01" },
      { id: "rf-003", projectId: "proj-003", category: "Supply Chain", severity: "Medium", description: "Custom millwork vendor experiencing production delays", status: "Open", createdAt: "2025-06-20" },
      { id: "rf-004", projectId: "proj-001", category: "Budget", severity: "Low", description: "Minor cost overrun on foundation work, within contingency", status: "Mitigated", createdAt: "2025-05-10" },
    ];
    riskFlags.forEach(r => this.riskFlags.set(r.id, r));
  }

  async getPortfolios(): Promise<Portfolio[]> {
    return Array.from(this.portfolios.values());
  }

  async getAssets(): Promise<Asset[]> {
    return Array.from(this.assets.values());
  }

  async getAsset(id: string): Promise<Asset | undefined> {
    return this.assets.get(id);
  }

  async createAsset(asset: InsertAsset): Promise<Asset> {
    const id = randomUUID();
    const newAsset: Asset = { ...asset, id };
    this.assets.set(id, newAsset);
    return newAsset;
  }

  async getProjects(): Promise<Project[]> {
    return Array.from(this.projects.values());
  }

  async getProject(id: string): Promise<Project | undefined> {
    return this.projects.get(id);
  }

  async createProject(project: InsertProject): Promise<Project> {
    const id = randomUUID();
    const newProject: Project = { ...project, id };
    this.projects.set(id, newProject);
    return newProject;
  }

  async getDeals(): Promise<Deal[]> {
    return Array.from(this.deals.values());
  }

  async getDeal(id: string): Promise<Deal | undefined> {
    return this.deals.get(id);
  }

  async createDeal(deal: InsertDeal): Promise<Deal> {
    const id = randomUUID();
    const newDeal: Deal = { ...deal, id };
    this.deals.set(id, newDeal);
    return newDeal;
  }

  async getInvestors(): Promise<Investor[]> {
    return Array.from(this.investors.values());
  }

  async getInvestor(id: string): Promise<Investor | undefined> {
    return this.investors.get(id);
  }

  async createInvestor(investor: InsertInvestor): Promise<Investor> {
    const id = randomUUID();
    const newInvestor: Investor = { ...investor, id };
    this.investors.set(id, newInvestor);
    return newInvestor;
  }

  async getAllocations(): Promise<Allocation[]> {
    return Array.from(this.allocations.values());
  }

  async getAllocation(id: string): Promise<Allocation | undefined> {
    return this.allocations.get(id);
  }

  async createAllocation(allocation: InsertAllocation): Promise<Allocation> {
    const id = randomUUID();
    const newAllocation: Allocation = { ...allocation, id };
    this.allocations.set(id, newAllocation);
    return newAllocation;
  }

  async getMilestones(): Promise<Milestone[]> {
    return Array.from(this.milestones.values());
  }

  async getMilestonesByProject(projectId: string): Promise<Milestone[]> {
    return Array.from(this.milestones.values()).filter(m => m.projectId === projectId);
  }

  async createMilestone(milestone: InsertMilestone): Promise<Milestone> {
    const id = randomUUID();
    const newMilestone: Milestone = { ...milestone, id };
    this.milestones.set(id, newMilestone);
    return newMilestone;
  }

  async getVendors(): Promise<Vendor[]> {
    return Array.from(this.vendors.values());
  }

  async getVendor(id: string): Promise<Vendor | undefined> {
    return this.vendors.get(id);
  }

  async createVendor(vendor: InsertVendor): Promise<Vendor> {
    const id = randomUUID();
    const newVendor: Vendor = { ...vendor, id };
    this.vendors.set(id, newVendor);
    return newVendor;
  }

  async getWorkOrders(): Promise<WorkOrder[]> {
    return Array.from(this.workOrders.values());
  }

  async getWorkOrdersByVendor(vendorId: string): Promise<WorkOrder[]> {
    return Array.from(this.workOrders.values()).filter(w => w.vendorId === vendorId);
  }

  async createWorkOrder(workOrder: InsertWorkOrder): Promise<WorkOrder> {
    const id = randomUUID();
    const newWorkOrder: WorkOrder = { ...workOrder, id };
    this.workOrders.set(id, newWorkOrder);
    return newWorkOrder;
  }

  async getRiskFlags(): Promise<RiskFlag[]> {
    return Array.from(this.riskFlags.values());
  }

  async getRiskFlagsByProject(projectId: string): Promise<RiskFlag[]> {
    return Array.from(this.riskFlags.values()).filter(r => r.projectId === projectId);
  }

  async getDashboardStats() {
    const deals = await this.getDeals();
    const workOrders = await this.getWorkOrders();
    const riskFlags = await this.getRiskFlags();
    return {
      totalAssets: this.assets.size,
      activeProjects: Array.from(this.projects.values()).filter(p => p.status === "In Progress").length,
      totalCapitalRequired: deals.reduce((sum, d) => sum + d.capitalRequired, 0),
      totalCapitalRaised: deals.reduce((sum, d) => sum + d.capitalRaised, 0),
      activeDeals: deals.filter(d => d.status === "Active").length,
      totalInvestors: this.investors.size,
      openWorkOrders: workOrders.filter(w => w.status === "Open" || w.status === "In Progress").length,
      riskFlags: riskFlags.filter(r => r.status === "Open").length,
    };
  }
}

export const storage = new MemStorage();
