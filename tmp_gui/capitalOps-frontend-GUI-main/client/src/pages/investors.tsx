import { useQuery } from "@tanstack/react-query";
import { Users, DollarSign, MapPin, Shield, Star } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatCurrency, getStatusColor } from "@/lib/formatters";
import type { Investor, Allocation } from "@shared/schema";

export default function Investors() {
  const { data: investors, isLoading } = useQuery<Investor[]>({ queryKey: ["/api/investors"] });
  const { data: allocations } = useQuery<Allocation[]>({ queryKey: ["/api/allocations"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-52" />)}
        </div>
      </div>
    );
  }

  const activeInvestors = investors?.filter(i => i.status === "Active").length || 0;
  const tier2Investors = investors?.filter(i => i.tierLevel === "Tier 2").length || 0;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Investor Profiles"
        description="Investor alignment and relationship management"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Total Investors" value={investors?.length || 0} icon={Users} testId="stat-total-investors" />
        <StatCard title="Active" value={activeInvestors} icon={Shield} testId="stat-active-investors" />
        <StatCard title="Priority (Tier 2)" value={tier2Investors} icon={Star} testId="stat-tier2" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {investors?.map((investor) => {
          const investorAllocations = allocations?.filter(a => a.investorId === investor.id) || [];
          const totalCommitted = investorAllocations.reduce((sum, a) => sum + a.hardCommitAmount, 0);

          return (
            <Card key={investor.id} className="hover-elevate" data-testid={`card-investor-${investor.id}`}>
              <CardContent className="p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <Users className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold truncate" data-testid={`text-investor-name-${investor.id}`}>{investor.name}</h3>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <Badge variant="secondary" className={getStatusColor(investor.status)}>
                          {investor.status}
                        </Badge>
                        <Badge variant="secondary" className={investor.tierLevel === "Tier 2" ? "bg-chart-4/15 text-chart-4" : "bg-accent text-accent-foreground"}>
                          {investor.tierLevel}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Check Size</p>
                    <p className="text-sm font-medium">{formatCurrency(investor.checkSizeMin)} - {formatCurrency(investor.checkSizeMax)}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Risk Tolerance</p>
                    <p className="text-sm font-medium">{investor.riskTolerance}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Asset Pref</p>
                    <p className="text-sm font-medium">{investor.assetPreference}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Geography</p>
                    <div className="flex items-center gap-1">
                      <MapPin className="h-3 w-3 text-muted-foreground" />
                      <p className="text-sm font-medium">{investor.geographyPreference}</p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Structure</p>
                    <p className="text-sm font-medium">{investor.structurePreference}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Timeline</p>
                    <p className="text-sm font-medium">{investor.timelinePreference}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-border flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] text-muted-foreground">Strategic Interest</p>
                    <p className="text-xs font-medium">{investor.strategicInterest}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-muted-foreground">Total Committed</p>
                    <p className="text-xs font-semibold text-chart-2">{formatCurrency(totalCommitted)}</p>
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
