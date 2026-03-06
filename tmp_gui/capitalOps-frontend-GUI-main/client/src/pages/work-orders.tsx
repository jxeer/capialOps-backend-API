import { useQuery } from "@tanstack/react-query";
import { ClipboardList, DollarSign, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatCurrency, formatDate, getStatusColor } from "@/lib/formatters";
import type { WorkOrder, Vendor, Asset } from "@shared/schema";

export default function WorkOrders() {
  const { data: workOrders, isLoading } = useQuery<WorkOrder[]>({ queryKey: ["/api/work-orders"] });
  const { data: vendors } = useQuery<Vendor[]>({ queryKey: ["/api/vendors"] });
  const { data: assets } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    );
  }

  const openOrders = workOrders?.filter(w => w.status === "Open" || w.status === "In Progress") || [];
  const totalCost = workOrders?.reduce((sum, w) => sum + w.cost, 0) || 0;
  const capExCount = workOrders?.filter(w => w.capExFlag).length || 0;
  const completedCount = workOrders?.filter(w => w.status === "Completed").length || 0;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Work Orders"
        description="Work order management and cost tracking"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Open Orders" value={openOrders.length} icon={ClipboardList} testId="stat-open-orders" />
        <StatCard title="Total Cost" value={formatCurrency(totalCost)} icon={DollarSign} testId="stat-total-cost" />
        <StatCard title="CapEx Items" value={capExCount} icon={AlertCircle} testId="stat-capex" />
        <StatCard title="Completed" value={completedCount} icon={CheckCircle2} testId="stat-completed" />
      </div>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-semibold">All Work Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {workOrders?.map((wo) => {
              const vendor = vendors?.find(v => v.id === wo.vendorId);
              const asset = assets?.find(a => a.id === wo.assetId);

              return (
                <div
                  key={wo.id}
                  className="p-4 rounded-md bg-accent/30 space-y-3"
                  data-testid={`work-order-row-${wo.id}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
                        <ClipboardList className="h-4 w-4 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{wo.type}</p>
                        <p className="text-xs text-muted-foreground">{vendor?.name || "Unknown"} | {asset?.name || "Unknown"}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 flex-wrap">
                      <Badge variant="secondary" className={getStatusColor(wo.priority)}>
                        {wo.priority}
                      </Badge>
                      <Badge variant="secondary" className={getStatusColor(wo.status)}>
                        {wo.status}
                      </Badge>
                    </div>
                  </div>

                  {wo.description && (
                    <p className="text-xs text-muted-foreground">{wo.description}</p>
                  )}

                  <div className="flex items-center justify-between gap-3 text-xs flex-wrap">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="font-semibold">{formatCurrency(wo.cost)}</span>
                      {wo.capExFlag && (
                        <Badge variant="secondary" className="bg-chart-4/15 text-chart-4 text-[10px]">
                          CapEx
                        </Badge>
                      )}
                    </div>
                    {wo.completionDate && (
                      <span className="text-muted-foreground">Completed: {formatDate(wo.completionDate)}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
