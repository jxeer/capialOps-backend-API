import { z } from "zod";

export const portfolioSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
});
export type Portfolio = z.infer<typeof portfolioSchema>;

export const assetSchema = z.object({
  id: z.string(),
  portfolioId: z.string(),
  name: z.string(),
  location: z.string(),
  assetType: z.string(),
  squareFootage: z.number(),
  status: z.enum(["Pre-dev", "Active", "Stabilized"]),
  assetManager: z.string(),
});
export type Asset = z.infer<typeof assetSchema>;
export const insertAssetSchema = assetSchema.omit({ id: true });
export type InsertAsset = z.infer<typeof insertAssetSchema>;

export const projectSchema = z.object({
  id: z.string(),
  assetId: z.string(),
  portfolioId: z.string(),
  phase: z.string(),
  startDate: z.string(),
  targetCompletion: z.string(),
  budgetTotal: z.number(),
  budgetActual: z.number(),
  status: z.enum(["Planning", "In Progress", "On Hold", "Completed"]),
  pmAssigned: z.string(),
});
export type Project = z.infer<typeof projectSchema>;
export const insertProjectSchema = projectSchema.omit({ id: true });
export type InsertProject = z.infer<typeof insertProjectSchema>;

export const dealSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  portfolioId: z.string(),
  capitalRequired: z.number(),
  capitalRaised: z.number(),
  returnProfile: z.string(),
  duration: z.string(),
  riskLevel: z.enum(["Low", "Medium", "High"]),
  complexity: z.enum(["Simple", "Moderate", "Complex"]),
  phase: z.string(),
  status: z.enum(["Draft", "Active", "Funded", "Closed"]),
});
export type Deal = z.infer<typeof dealSchema>;
export const insertDealSchema = dealSchema.omit({ id: true });
export type InsertDeal = z.infer<typeof insertDealSchema>;

export const investorSchema = z.object({
  id: z.string(),
  name: z.string(),
  accreditationStatus: z.enum(["Accredited", "Qualified Purchaser", "Pending"]),
  checkSizeMin: z.number(),
  checkSizeMax: z.number(),
  assetPreference: z.string(),
  geographyPreference: z.string(),
  riskTolerance: z.enum(["Conservative", "Moderate", "Aggressive"]),
  structurePreference: z.string(),
  timelinePreference: z.string(),
  strategicInterest: z.string(),
  tierLevel: z.enum(["Tier 1", "Tier 2"]),
  status: z.enum(["Active", "Inactive", "Prospect"]),
});
export type Investor = z.infer<typeof investorSchema>;
export const insertInvestorSchema = investorSchema.omit({ id: true });
export type InsertInvestor = z.infer<typeof insertInvestorSchema>;

export const allocationSchema = z.object({
  id: z.string(),
  investorId: z.string(),
  dealId: z.string(),
  softCommitAmount: z.number(),
  hardCommitAmount: z.number(),
  status: z.enum(["Pending", "Soft Commit", "Hard Commit", "Funded", "Withdrawn"]),
  timestamp: z.string(),
  notes: z.string().optional(),
});
export type Allocation = z.infer<typeof allocationSchema>;
export const insertAllocationSchema = allocationSchema.omit({ id: true });
export type InsertAllocation = z.infer<typeof insertAllocationSchema>;

export const milestoneSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  name: z.string(),
  category: z.string(),
  targetDate: z.string(),
  completionDate: z.string().optional(),
  status: z.enum(["Pending", "In Progress", "Completed", "Delayed"]),
  delayExplanation: z.string().optional(),
  riskFlag: z.boolean(),
});
export type Milestone = z.infer<typeof milestoneSchema>;
export const insertMilestoneSchema = milestoneSchema.omit({ id: true });
export type InsertMilestone = z.infer<typeof insertMilestoneSchema>;

export const vendorSchema = z.object({
  id: z.string(),
  assetId: z.string(),
  name: z.string(),
  type: z.string(),
  coiStatus: z.enum(["Current", "Expired", "Pending"]),
  slaType: z.string(),
  performanceScore: z.number(),
});
export type Vendor = z.infer<typeof vendorSchema>;
export const insertVendorSchema = vendorSchema.omit({ id: true });
export type InsertVendor = z.infer<typeof insertVendorSchema>;

export const workOrderSchema = z.object({
  id: z.string(),
  vendorId: z.string(),
  assetId: z.string(),
  type: z.string(),
  priority: z.enum(["Low", "Medium", "High", "Urgent"]),
  cost: z.number(),
  capExFlag: z.boolean(),
  status: z.enum(["Open", "In Progress", "Completed", "Cancelled"]),
  completionDate: z.string().optional(),
  description: z.string().optional(),
});
export type WorkOrder = z.infer<typeof workOrderSchema>;
export const insertWorkOrderSchema = workOrderSchema.omit({ id: true });
export type InsertWorkOrder = z.infer<typeof insertWorkOrderSchema>;

export const riskFlagSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  category: z.string(),
  severity: z.enum(["Low", "Medium", "High", "Critical"]),
  description: z.string(),
  status: z.enum(["Open", "Mitigated", "Resolved"]),
  createdAt: z.string(),
});
export type RiskFlag = z.infer<typeof riskFlagSchema>;

export type User = { id: string; username: string; password: string };
export type InsertUser = { username: string; password: string };
