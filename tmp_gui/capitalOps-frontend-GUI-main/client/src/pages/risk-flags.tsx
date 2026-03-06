import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatDate, getStatusColor, getRiskColor } from "@/lib/formatters";
import type { RiskFlag, Project, Asset } from "@shared/schema";

export default function RiskFlags() {
  const { data: riskFlags, isLoading } = useQuery<RiskFlag[]>({ queryKey: ["/api/risk-flags"] });
  const { data: projects } = useQuery<Project[]>({ queryKey: ["/api/projects"] });
  const { data: assets } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    );
  }

  const openFlags = riskFlags?.filter(r => r.status === "Open") || [];
  const mitigated = riskFlags?.filter(r => r.status === "Mitigated") || [];
  const highSeverity = riskFlags?.filter(r => r.severity === "High" || r.severity === "Critical") || [];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Risk Flags"
        description="Governance risk monitoring and mitigation tracking"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Open Risks" value={openFlags.length} icon={ShieldAlert} testId="stat-open-risks" />
        <StatCard title="High/Critical" value={highSeverity.length} icon={AlertTriangle} testId="stat-high-risks" />
        <StatCard title="Mitigated" value={mitigated.length} icon={ShieldCheck} testId="stat-mitigated" />
      </div>

      <div className="space-y-3">
        {riskFlags?.map((flag) => {
          const project = projects?.find(p => p.id === flag.projectId);
          const asset = project ? assets?.find(a => a.id === project.assetId) : undefined;

          return (
            <Card key={flag.id} className="hover-elevate" data-testid={`card-risk-${flag.id}`}>
              <CardContent className="p-5">
                <div className="flex items-start gap-4">
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
                    flag.severity === "High" || flag.severity === "Critical"
                      ? "bg-destructive/10"
                      : flag.severity === "Medium"
                      ? "bg-chart-3/10"
                      : "bg-chart-2/10"
                  }`}>
                    <AlertTriangle className={`h-4 w-4 ${getRiskColor(flag.severity)}`} />
                  </div>
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0 flex-wrap">
                        <span className="text-sm font-semibold">{flag.category}</span>
                        <Badge variant="secondary" className={getStatusColor(flag.severity)}>
                          {flag.severity}
                        </Badge>
                        <Badge variant="secondary" className={getStatusColor(flag.status)}>
                          {flag.status}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">{flag.description}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                      <span>{asset?.name || "Unknown"} - {project?.phase}</span>
                      <span>{formatDate(flag.createdAt)}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
