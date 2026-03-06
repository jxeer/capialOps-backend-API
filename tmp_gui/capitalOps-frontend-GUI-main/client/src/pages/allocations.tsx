import { useQuery } from "@tanstack/react-query";
import { TrendingUp, DollarSign, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatCurrency, formatDate, getStatusColor } from "@/lib/formatters";
import type { Allocation, Investor, Deal, Project, Asset } from "@shared/schema";

export default function Allocations() {
  const { data: allocations, isLoading } = useQuery<Allocation[]>({ queryKey: ["/api/allocations"] });
  const { data: investors } = useQuery<Investor[]>({ queryKey: ["/api/investors"] });
  const { data: deals } = useQuery<Deal[]>({ queryKey: ["/api/deals"] });
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

  const totalSoft = allocations?.reduce((sum, a) => sum + a.softCommitAmount, 0) || 0;
  const totalHard = allocations?.reduce((sum, a) => sum + a.hardCommitAmount, 0) || 0;
  const funded = allocations?.filter(a => a.status === "Funded").length || 0;

  const getDealName = (dealId: string) => {
    const deal = deals?.find(d => d.id === dealId);
    const project = deal ? projects?.find(p => p.id === deal.projectId) : undefined;
    const asset = project ? assets?.find(a => a.id === project.assetId) : undefined;
    return asset?.name || "Unknown Deal";
  };

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Allocations"
        description="Investor commitment tracking and capital flow"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Total Soft Commits" value={formatCurrency(totalSoft)} icon={TrendingUp} testId="stat-soft-commits" />
        <StatCard title="Total Hard Commits" value={formatCurrency(totalHard)} icon={DollarSign} testId="stat-hard-commits" />
        <StatCard title="Funded Allocations" value={funded} icon={Users} testId="stat-funded" />
      </div>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-semibold">All Allocations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {allocations?.map((alloc) => {
              const investor = investors?.find(i => i.id === alloc.investorId);
              return (
                <div
                  key={alloc.id}
                  className="flex items-center justify-between gap-4 p-4 rounded-md bg-accent/30"
                  data-testid={`allocation-row-${alloc.id}`}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <Users className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{investor?.name || "Unknown"}</p>
                      <p className="text-xs text-muted-foreground">{getDealName(alloc.dealId)}</p>
                    </div>
                  </div>

                  <div className="hidden sm:flex items-center gap-6 shrink-0">
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground">Soft</p>
                      <p className="text-sm font-medium">{formatCurrency(alloc.softCommitAmount)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground">Hard</p>
                      <p className="text-sm font-semibold">{formatCurrency(alloc.hardCommitAmount)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground">Date</p>
                      <p className="text-xs">{formatDate(alloc.timestamp)}</p>
                    </div>
                  </div>

                  <Badge variant="secondary" className={getStatusColor(alloc.status)}>
                    {alloc.status}
                  </Badge>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
