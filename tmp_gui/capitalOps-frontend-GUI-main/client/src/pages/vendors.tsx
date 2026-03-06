import { useQuery } from "@tanstack/react-query";
import { Truck, Shield, Star, FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { getStatusColor } from "@/lib/formatters";
import type { Vendor, Asset, WorkOrder } from "@shared/schema";

export default function Vendors() {
  const { data: vendors, isLoading } = useQuery<Vendor[]>({ queryKey: ["/api/vendors"] });
  const { data: assets } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });
  const { data: workOrders } = useQuery<WorkOrder[]>({ queryKey: ["/api/work-orders"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-44" />)}
        </div>
      </div>
    );
  }

  const currentCOI = vendors?.filter(v => v.coiStatus === "Current").length || 0;
  const avgScore = vendors?.length
    ? Math.round(vendors.reduce((sum, v) => sum + v.performanceScore, 0) / vendors.length)
    : 0;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Vendors"
        description="Vendor management and performance tracking"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Total Vendors" value={vendors?.length || 0} icon={Truck} testId="stat-total-vendors" />
        <StatCard title="COI Current" value={currentCOI} icon={Shield} testId="stat-coi-current" />
        <StatCard title="Avg Performance" value={`${avgScore}/100`} icon={Star} testId="stat-avg-score" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {vendors?.map((vendor) => {
          const asset = assets?.find(a => a.id === vendor.assetId);
          const vendorWOs = workOrders?.filter(w => w.vendorId === vendor.id) || [];
          const openWOs = vendorWOs.filter(w => w.status === "Open" || w.status === "In Progress").length;

          return (
            <Card key={vendor.id} className="hover-elevate" data-testid={`card-vendor-${vendor.id}`}>
              <CardContent className="p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <Truck className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold truncate" data-testid={`text-vendor-name-${vendor.id}`}>{vendor.name}</h3>
                      <p className="text-xs text-muted-foreground">{vendor.type}</p>
                    </div>
                  </div>
                  <Badge variant="secondary" className={getStatusColor(vendor.coiStatus)}>
                    COI: {vendor.coiStatus}
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Asset</p>
                    <p className="text-sm font-medium truncate">{asset?.name || "Unknown"}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">SLA</p>
                    <p className="text-sm font-medium">{vendor.slaType}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Open WOs</p>
                    <p className="text-sm font-medium">{openWOs}</p>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-muted-foreground">Performance Score</span>
                    <span className={`font-semibold ${
                      vendor.performanceScore >= 90 ? "text-chart-2" :
                      vendor.performanceScore >= 80 ? "text-chart-1" :
                      "text-chart-5"
                    }`}>{vendor.performanceScore}/100</span>
                  </div>
                  <Progress value={vendor.performanceScore} className="h-1.5" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
