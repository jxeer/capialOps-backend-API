import { useQuery } from "@tanstack/react-query";
import { Handshake, TrendingUp, Clock, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatCurrency, getStatusColor, getRiskColor } from "@/lib/formatters";
import type { Deal, Project, Asset, Allocation, Investor } from "@shared/schema";

export default function Deals() {
  const { data: deals, isLoading } = useQuery<Deal[]>({ queryKey: ["/api/deals"] });
  const { data: projects } = useQuery<Project[]>({ queryKey: ["/api/projects"] });
  const { data: assets } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });
  const { data: allocations } = useQuery<Allocation[]>({ queryKey: ["/api/allocations"] });
  const { data: investors } = useQuery<Investor[]>({ queryKey: ["/api/investors"] });

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

  const totalRequired = deals?.reduce((sum, d) => sum + d.capitalRequired, 0) || 0;
  const totalRaised = deals?.reduce((sum, d) => sum + d.capitalRaised, 0) || 0;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Deal Pipeline"
        description="Capital distribution and deal management"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Total Capital Required"
          value={formatCurrency(totalRequired)}
          icon={Handshake}
          testId="stat-total-required"
        />
        <StatCard
          title="Total Capital Raised"
          value={formatCurrency(totalRaised)}
          subtitle={`${totalRequired > 0 ? Math.round((totalRaised / totalRequired) * 100) : 0}% of target`}
          icon={TrendingUp}
          testId="stat-total-raised"
        />
        <StatCard
          title="Active Deals"
          value={deals?.filter(d => d.status === "Active").length || 0}
          icon={Handshake}
          testId="stat-active-deals"
        />
      </div>

      <div className="space-y-4">
        {deals?.map((deal) => {
          const project = projects?.find(p => p.id === deal.projectId);
          const asset = project ? assets?.find(a => a.id === project.assetId) : undefined;
          const dealAllocations = allocations?.filter(a => a.dealId === deal.id) || [];
          const progress = deal.capitalRequired > 0 ? Math.round((deal.capitalRaised / deal.capitalRequired) * 100) : 0;

          return (
            <Card key={deal.id} data-testid={`card-deal-${deal.id}`}>
              <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                    <Handshake className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <CardTitle className="text-base truncate">{asset?.name || "Unknown"} - {deal.phase}</CardTitle>
                    <p className="text-xs text-muted-foreground">{asset?.location} | {deal.returnProfile}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="secondary" className={getStatusColor(deal.status)}>
                    {deal.status}
                  </Badge>
                  <Badge variant="secondary" className={getStatusColor(deal.riskLevel)}>
                    {deal.riskLevel} Risk
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Required</p>
                    <p className="text-sm font-semibold">{formatCurrency(deal.capitalRequired)}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Raised</p>
                    <p className="text-sm font-semibold text-chart-2">{formatCurrency(deal.capitalRaised)}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Duration</p>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <p className="text-sm font-medium">{deal.duration}</p>
                    </div>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Complexity</p>
                    <p className="text-sm font-medium">{deal.complexity}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Investors</p>
                    <p className="text-sm font-medium">{dealAllocations.length}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-muted-foreground">Capital Progress</span>
                    <span className="font-medium">{progress}%</span>
                  </div>
                  <Progress value={progress} className="h-2" />
                </div>

                {dealAllocations.length > 0 && (
                  <div className="pt-3 border-t border-border">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Allocations</p>
                    <div className="space-y-2">
                      {dealAllocations.map((alloc) => {
                        const investor = investors?.find(i => i.id === alloc.investorId);
                        return (
                          <div key={alloc.id} className="flex items-center justify-between gap-3 p-2 rounded-md bg-accent/30" data-testid={`deal-allocation-${alloc.id}`}>
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate">{investor?.name || "Unknown"}</p>
                              <p className="text-[10px] text-muted-foreground">
                                Soft: {formatCurrency(alloc.softCommitAmount)} | Hard: {formatCurrency(alloc.hardCommitAmount)}
                              </p>
                            </div>
                            <Badge variant="secondary" className={getStatusColor(alloc.status)}>
                              {alloc.status}
                            </Badge>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
